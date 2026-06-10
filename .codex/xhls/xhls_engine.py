"""XHLS Context Engine v1.0 — Dual Compression + Phase1 Pruning

Concrete implementation of ContextEngine ABC for Xiao Hei (XHLS).

Key features:
  - Dual compression: Semantic (Layer 1) → Representational (Layer 2)
  - Phase1 zero-cost pruning with 4-factor scoring
  - Pipeline-aware context forecasting
  - Feishu archive template
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from .context_engine import (
    ContextEngine,
    ContextItem,
    BudgetState,
    PruningWeights,
    register_engine,
    CST,
)


@register_engine("xhls")
class XHLSContextEngine(ContextEngine):
    """XHLS dual-compression context engine.

    Layer 1 (Semantic): Understands WHAT matters — ranks by importance,
    detects redundancy, preserves decision chains.
    Layer 2 (Representation): Compresses HOW items are stored — applies
    L0→L1→L2→L3 progressive summarization rules.
    """

    FORECAST_MAP = {
        "S1_topic": {
            "preload": ["hooks", "target_audience", "competitor_analysis"],
            "knowledge_tags": ["content-formulas/hooks", "competitor-analysis/accounts"],
        },
        "S2_script": {
            "preload": ["structures", "character_settings", "dialogue_patterns"],
            "knowledge_tags": ["content-formulas/structures", "characters"],
        },
        "S3_assets": {
            "preload": ["character_visuals", "style_reference", "scene_design"],
            "knowledge_tags": ["characters", "art-style"],
        },
        "S4_composite": {
            "preload": ["subtitle_templates", "voice_files", "transition_effects"],
            "knowledge_tags": ["voice", "subtitles", "editing"],
        },
        "S5_publish": {
            "preload": ["platform_templates", "hashtag_bank", "publish_schedule"],
            "knowledge_tags": ["content-formulas/platforms", "marketing"],
        },
        "architecture": {
            "preload": ["code_patterns", "system_design", "decision_records"],
            "knowledge_tags": ["code-patterns", "pipeline-decisions"],
        },
        "security": {
            "preload": ["vulnerability_patterns", "attack_surfaces", "mitigation"],
            "knowledge_tags": ["security/vulnerability-patterns", "security/mitigation"],
        },
    }

    def semantic_compress(self, items: list[ContextItem],
                          budget_tokens: int) -> list[ContextItem]:
        """Layer 1: Semantic compression.

        Strategy:
          1. Score all items with current weights
          2. Drop items below prune threshold
          3. Detect and merge near-duplicate items (Jaccard tag overlap > 0.7)
          4. Fit remaining items into budget, highest score first
          5. Preserve dependency chains: if item A depends on B, B gets A's score boost
        """
        if not items:
            return items

        scored = self.score_items(items)
        survivors = [i for i in scored if i.score >= self.weights.threshold]
        deduped = self._deduplicate_by_tags(survivors, overlap_threshold=0.7)

        # Dependency boost
        dep_map: dict[str, list[str]] = {}
        for item in deduped:
            for dep_id in item.dependencies:
                dep_map.setdefault(dep_id, []).append(item.id)

        for item in deduped:
            if item.id in dep_map:
                boost = min(0.15, len(dep_map[item.id]) * 0.05)
                item.score = min(1.0, item.score + boost)

        deduped.sort(key=lambda x: x.score, reverse=True)

        # Budget fit
        result: list[ContextItem] = []
        tokens_used = 0
        for item in deduped:
            if tokens_used + item.token_estimate > budget_tokens:
                if item.priority == "critical" and len(result) < 5:
                    result.append(item)
                continue
            result.append(item)
            tokens_used += item.token_estimate

        return result

    def _deduplicate_by_tags(self, items: list[ContextItem],
                             overlap_threshold: float = 0.7) -> list[ContextItem]:
        """Merge items with high tag overlap. Keep the higher-scored one."""
        if not items:
            return items

        result: list[ContextItem] = []
        seen = set()

        for i, item in enumerate(items):
            if i in seen:
                continue
            for j in range(i + 1, len(items)):
                if j in seen:
                    continue
                other = items[j]
                overlap = self._jaccard(item.tags, other.tags)
                if overlap >= overlap_threshold:
                    seen.add(j)
                    if item.score < other.score:
                        item, other = other, item
                    item.content += f"\n[merged: {other.id}]"
                    item.token_estimate = min(
                        item.token_estimate + other.token_estimate,
                        item.token_estimate * 2
                    )
            result.append(item)

        return result

    @staticmethod
    def _jaccard(a: list[str], b: list[str]) -> float:
        if not a and not b:
            return 1.0
        sa, sb = set(a), set(b)
        union = len(sa | sb)
        if union == 0:
            return 1.0
        return len(sa & sb) / union

    def representational_compress(self, items: list[ContextItem],
                                  level: str = "L2_bullets") -> list[ContextItem]:
        """Layer 2: Representation compression.

        Applies the compression level to each item's content representation.
        """
        level_methods = {
            "L0_raw": self._compress_l0,
            "L1_tldr": self._compress_l1,
            "L2_bullets": self._compress_l2,
            "L3_decisions": self._compress_l3,
        }
        method = level_methods.get(level, self._compress_l2)

        level_order = {"L0_raw": 0, "L1_tldr": 1, "L2_bullets": 2, "L3_decisions": 3}
        for item in items:
            current = level_order.get(item.compression_level, 0)
            target = level_order.get(level, 2)
            if current < target:
                item.content = method(item)
                item.compression_level = level
                item.token_estimate = max(10, len(item.content) // 4)

        return items

    def _compress_l0(self, item: ContextItem) -> str:
        return item.content

    def _compress_l1(self, item: ContextItem) -> str:
        """TL;DR: extract first meaningful sentence or generate summary."""
        lines = [l.strip() for l in item.content.split("\n") if l.strip()]
        for line in lines:
            if len(line) > 20:
                return f"[{item.category}] {line[:200]}"
        return f"[{item.category}] {item.content[:200]}"

    def _compress_l2(self, item: ContextItem) -> str:
        """Bullets: extract key points as markdown bullets."""
        lines = [l.strip() for l in item.content.split("\n") if l.strip()]
        bullets = []
        for line in lines[:10]:
            line = line.lstrip("#-* ").strip()
            if line and len(line) > 10:
                bullets.append(f"- {line[:150]}")
        if not bullets:
            bullets.append(f"- [{item.category}] {item.content[:150]}")
        return f"[{item.category}]\n" + "\n".join(bullets[:8])

    def _compress_l3(self, item: ContextItem) -> str:
        """Decisions only: keep outcome, drop process."""
        decision_keywords = ["decision", "conclusion",
                             "final", "outcome", "result"]
        lines = item.content.split("\n")
        decisions = []
        for line in lines:
            line_stripped = line.strip()
            if any(kw in line_stripped.lower() for kw in decision_keywords):
                decisions.append(line_stripped[:200])
        if not decisions:
            meaningful = [l.strip() for l in lines if len(l.strip()) > 20]
            decisions = meaningful[:1] + meaningful[-1:]
        return f"[{item.category}-decisions]\n" + "\n".join(decisions[:5])

    def forecast(self, stage: str) -> list[str]:
        """Predict knowledge tags needed for a pipeline stage."""
        info = self.FORECAST_MAP.get(stage)
        if not info:
            return [f"Unknown stage: {stage}. Known: {list(self.FORECAST_MAP)}"]
        return info["knowledge_tags"]

    def archive(self, state: dict) -> str:
        """Produce Feishu-ready archive markdown."""
        now = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
        return f"""# XHLS Context Archive — {now}

## Session State
- Level: {state.get('level', 'unknown')}
- Usage: {state.get('usage', 0)}%
- Turns: {state.get('turns', 0)}
- Compressions: {state.get('compressions', 0)}
- Prunes: {state.get('prunes', 0)}
- Engine: XHLSContextEngine v1.0 (dual-compress)

## Actions
{state.get('actions', 'None')}
"""

    def diagnose_items(self, items: list[ContextItem]) -> str:
        """Produce a diagnostic report for a list of context items."""
        if not items:
            return "No items to diagnose."

        scored = self.score_items(items)
        lines = [
            f"Items: {len(scored)} total",
            f"Score range: {scored[-1].score:.3f} ~ {scored[0].score:.3f}",
            f"Below threshold ({self.weights.threshold}): "
            f"{sum(1 for i in scored if i.score < self.weights.threshold)}",
            "",
            "Top 10:",
        ]
        for i, item in enumerate(scored[:10]):
            lines.append(
                f"  {i+1}. [{item.score:.3f}] {item.id} "
                f"({item.category}, {item.priority}, {item.token_estimate}t)"
            )
        lines.append("")
        lines.append("Bottom 5 (prune candidates):")
        for i, item in enumerate(scored[-5:]):
            lines.append(
                f"  {i+1}. [{item.score:.3f}] {item.id} "
                f"({item.category}, {item.priority}, {item.token_estimate}t)"
            )
        return "\n".join(lines)
