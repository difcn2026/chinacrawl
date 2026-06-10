"""XHLS ContextEngine ABC v1.0 — Pluggable Context Engineering Base

Design principles:
  - ABC defines the contract; implementations are swappable.
  - Dual compression: Layer 1 (semantic) + Layer 2 (representation).
  - Phase1 pruning: zero-cost scoring BEFORE context injection.
  - All engines share budget config from context_budget.json.

Usage:
  from context_engine import ContextEngine
  engine = XHLSContextEngine()  # concrete impl
  scores = engine.score_items(items)
  pruned = engine.phase1_prune(items, budget_tokens)
  compressed = engine.dual_compress(pruned, level="L2_bullets")
"""

from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional

CST = timezone(timedelta(hours=8))

# ──────────────────────────────────────────────
# Data model
# ──────────────────────────────────────────────


@dataclass
class ContextItem:
    """Single context unit: a turn, a tool output, a memory, a file read, etc."""

    id: str
    content: str
    category: str  # turn | tool_output | memory | file_read | knowledge_node
    token_estimate: int = 0
    timestamp: float = field(default_factory=time.time)
    priority: str = "normal"  # critical | high | normal | low
    dependencies: list[str] = field(default_factory=list)  # ids this item depends on
    tags: list[str] = field(default_factory=list)

    # Computed after scoring
    score: float = 0.0
    compression_level: str = "L0_raw"


@dataclass
class BudgetState:
    total: int = 258000
    used: int = 0
    zones: dict = field(default_factory=dict)
    warning_level: str = "green"  # green | yellow | orange | red

    @property
    def usage_percent(self) -> float:
        return (self.used / self.total * 100) if self.total > 0 else 0.0


# ──────────────────────────────────────────────
# Scoring weights dataclass
# ──────────────────────────────────────────────


@dataclass
class PruningWeights:
    recency: float = 0.4
    relevance: float = 0.3
    dependency: float = 0.2
    priority: float = 0.1
    threshold: float = 0.3

    def validate(self):
        total = self.recency + self.relevance + self.dependency + self.priority
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


# ──────────────────────────────────────────────
# ABC
# ──────────────────────────────────────────────


class ContextEngine(ABC):
    """Pluggable context engineering engine.

    Subclass and override methods to swap compression/pruning/forecasting
    strategies without changing the guardian CLI.
    """

    def __init__(self, budget_path: Optional[str] = None):
        self._budget_path = budget_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "context_budget.json"
        )
        self.budget = self._load_budget()
        self.weights = self._load_weights()
        self._compression_count = 0
        self._prune_count = 0

    # ── Budget ─────────────────────────────────

    def _load_budget(self) -> dict:
        with open(self._budget_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_weights(self) -> PruningWeights:
        scoring = self.budget.get("pruning", {}).get("scoring", {})
        return PruningWeights(
            recency=scoring.get("recency_weight", 0.4),
            relevance=scoring.get("relevance_weight", 0.3),
            dependency=scoring.get("dependency_weight", 0.2),
            priority=scoring.get("priority_weight", 0.1),
            threshold=self.budget.get("pruning", {}).get("threshold", 0.3),
        )

    @property
    def compression_count(self) -> int:
        return self._compression_count

    @property
    def prune_count(self) -> int:
        return self._prune_count

    # ── Budget estimation ──────────────────────

    def estimate_usage(self, turns: int) -> BudgetState:
        """Estimate token usage given turn count."""
        zones = self.budget["zones"]
        core = zones["core"]["tokens"]
        cache_est = 15000
        turn_est = turns * 8000
        used = core + cache_est + turn_est

        state = BudgetState(
            total=self.budget["total_budget"],
            used=used,
            zones=zones,
        )
        state.warning_level = self._calc_warning_level(state.usage_percent)
        return state

    def _calc_warning_level(self, percent: float) -> str:
        warnings = self.budget["warnings"]
        if percent <= warnings["green"]["max_percent"]:
            return "green"
        elif percent <= warnings["yellow"]["max_percent"]:
            return "yellow"
        elif percent <= warnings["orange"]["max_percent"]:
            return "orange"
        return "red"

    # ── Scoring (Phase1 Pruning) ───────────────

    def score_item(self, item: ContextItem, current_time: Optional[float] = None,
                   active_topic_tags: Optional[list[str]] = None) -> float:
        """Calculate pruning score for a single item. Score ∈ [0, 1].

        Formula: score = recency*w_r + relevance*w_rl + dependency*w_d + priority*w_p
        """
        now = current_time or time.time()
        w = self.weights

        # ── Recency (0..1): exponential decay, half-life = 30 min ──
        age_minutes = (now - item.timestamp) / 60.0
        recency = 2.0 ** (-age_minutes / 30.0)  # 0.5 at 30 min, 0.25 at 60 min

        # ── Relevance (0..1): tag overlap with active topic ──
        relevance = 0.5  # neutral default
        if active_topic_tags and item.tags:
            overlap = len(set(item.tags) & set(active_topic_tags))
            total = len(set(item.tags) | set(active_topic_tags))
            if total > 0:
                relevance = overlap / total

        # ── Dependency (0..1): more dependents → higher score ──
        dependency = min(1.0, len(item.dependencies) * 0.25)

        # ── Priority (0..1): categorical mapping ──
        priority_map = {"critical": 1.0, "high": 0.8, "normal": 0.5, "low": 0.2}
        priority = priority_map.get(item.priority, 0.5)

        score = (
            w.recency * recency
            + w.relevance * relevance
            + w.dependency * dependency
            + w.priority * priority
        )
        item.score = round(score, 4)
        return item.score

    def score_items(self, items: list[ContextItem],
                    active_topic_tags: Optional[list[str]] = None) -> list[ContextItem]:
        """Score all items and return sorted (highest first)."""
        now = time.time()
        for item in items:
            self.score_item(item, current_time=now, active_topic_tags=active_topic_tags)
        items.sort(key=lambda x: x.score, reverse=True)
        return items

    # ── Phase1 Pruning ─────────────────────────

    def phase1_prune(self, items: list[ContextItem],
                     budget_tokens: int,
                     active_topic_tags: Optional[list[str]] = None) -> tuple[list[ContextItem], list[ContextItem]]:
        """Zero-cost pruning: score all items, keep those above threshold
        AND within budget. Returns (kept, pruned)."""
        scored = self.score_items(items, active_topic_tags)

        kept: list[ContextItem] = []
        pruned: list[ContextItem] = []
        tokens_used = 0

        for item in scored:
            if item.score < self.weights.threshold:
                pruned.append(item)
                continue
            if tokens_used + item.token_estimate > budget_tokens:
                pruned.append(item)
                continue
            kept.append(item)
            tokens_used += item.token_estimate

        self._prune_count += 1
        return kept, pruned

    # ── Dual Compression (ABC: subclasses implement) ──

    @abstractmethod
    def semantic_compress(self, items: list[ContextItem],
                          budget_tokens: int) -> list[ContextItem]:
        """Layer 1: Semantic compression. Understand WHAT matters,
        rank by importance, drop semantically redundant items."""
        ...

    @abstractmethod
    def representational_compress(self, items: list[ContextItem],
                                  level: str) -> list[ContextItem]:
        """Layer 2: Representation compression. Compress HOW items
        are stored (L0→L1→L2→L3)."""
        ...

    def dual_compress(self, items: list[ContextItem],
                      budget_tokens: int,
                      level: str = "L2_bullets") -> list[ContextItem]:
        """Full dual compression pipeline: Semantic → Representational."""
        items = self.semantic_compress(items, budget_tokens)
        items = self.representational_compress(items, level)
        self._compression_count += 1
        return items

    # ── Forecasting ────────────────────────────

    @abstractmethod
    def forecast(self, stage: str) -> list[str]:
        """Predict knowledge needed for a pipeline stage."""
        ...

    # ── Archiving ──────────────────────────────

    @abstractmethod
    def archive(self, state: dict) -> str:
        """Produce archive content for external storage (Feishu)."""
        ...

    # ── Status report ──────────────────────────

    def status_report(self, turns: int, active_topic_tags: Optional[list[str]] = None) -> str:
        """Full status report string."""
        state = self.estimate_usage(turns)
        lines = [
            "=" * 55,
            f"ContextEngine Status  |  {self.__class__.__name__}",
            f"Budget: {state.total:,}t  |  Est. used: {state.used:,}t ({state.usage_percent:.0f}%)  |  {state.warning_level.upper()}",
            f"Compressions: {self._compression_count}  |  Prunes: {self._prune_count}",
            f"Weights: recency={self.weights.recency} relevance={self.weights.relevance} "
            f"dependency={self.weights.dependency} priority={self.weights.priority}",
            f"Threshold: {self.weights.threshold}",
            "=" * 55,
        ]
        return "\n".join(lines)


# ──────────────────────────────────────────────
# Engine registry
# ──────────────────────────────────────────────

_ENGINE_REGISTRY: dict[str, type[ContextEngine]] = {}


def register_engine(name: str):
    """Decorator to register a ContextEngine subclass."""
    def decorator(cls: type[ContextEngine]):
        _ENGINE_REGISTRY[name] = cls
        return cls
    return decorator


def get_engine(name: str, **kwargs) -> ContextEngine:
    """Factory: instantiate a registered engine by name."""
    if name not in _ENGINE_REGISTRY:
        raise KeyError(f"Unknown engine '{name}'. Registered: {list(_ENGINE_REGISTRY)}")
    return _ENGINE_REGISTRY[name](**kwargs)


def list_engines() -> list[str]:
    return list(_ENGINE_REGISTRY.keys())
