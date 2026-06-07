"""XHLS Context Guardian v3.0 — Full Context Engineering Engine

Based on Context Engineering 6 principles applied to 小黑's 258K window:
  1. Context Budgeting    — 5-zone allocation (Core/Working/Cache/Reserve/Headroom)
  2. Context Compression  — Dual-layer: Semantic + Representational (new!)
  3. Context Structuring  — Front-load essential, section-ordered prompts
  4. Context Pruning      — Phase1 zero-cost scoring (recency+relevance+dependency+priority)
  5. Context Forecasting  — Pre-load knowledge by pipeline stage
  6. Context Archiving    — Feishu as external L2 cache

v3.0 changes:
  - ContextEngine ABC: pluggable engine architecture (context_engine.py)
  - XHLSContextEngine: dual compression + Phase1 pruning (xhls_engine.py)
  - New CLI: score-items, prune, engine-status, diagnose, list-engines

Usage:
  python context_guardian.py status [turns]    — Full budget status
  python context_guardian.py check [turns]     — Quick check + advice
  python context_guardian.py compress          — Compression cycle
  python context_guardian.py forecast <stage>  — Predict context needs
  python context_guardian.py engine-status [turns] — Engine-powered status
  python context_guardian.py score-example     — Pruning score demo (interactive)
  python context_guardian.py budget            — Budget allocation
  python context_guardian.py list-engines      — Available engine plugins
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
GUARDIAN_DIR = os.path.dirname(os.path.abspath(__file__))
BUDGET_FILE = os.path.join(GUARDIAN_DIR, "context_budget.json")
STATUS_FILE = os.path.join(GUARDIAN_DIR, "context_status.json")

# Ensure .codex/xhls is importable
sys.path.insert(0, os.path.dirname(GUARDIAN_DIR))

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _now():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M")


def load_budget():
    with open(BUDGET_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "last_check": _now(),
        "estimated_usage_percent": 0,
        "compression_count": 0,
        "archive_count": 0,
        "current_level": "green",
        "active_turns": 0,
    }


def save_status(data):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
# Engine factory (lazy load to keep imports clean)
# ═══════════════════════════════════════════════════════════

_engine = None


def get_engine():
    """Lazy-load the XHLS context engine."""
    global _engine
    if _engine is None:
        # Import engine modules from sibling xhls/ directory
        from xhls.context_engine import ContextItem, list_engines
        from xhls.xhls_engine import XHLSContextEngine
        _engine = XHLSContextEngine()
    return _engine


# ═══════════════════════════════════════════════════════════
# 1. CONTEXT BUDGETING
# ═══════════════════════════════════════════════════════════

def estimate_usage_percent(turns_estimate):
    """Rough estimate: ~8K tokens per turn with tool output."""
    budget = load_budget()
    core = budget["zones"]["core"]["tokens"]
    cache_est = 15000
    turn_est = turns_estimate * 8000
    total_est = core + cache_est + turn_est
    return min(95, int(total_est / budget["total_budget"] * 100))


def get_warning_level(percent):
    budget = load_budget()
    warnings = budget["warnings"]
    if percent <= warnings["green"]["max_percent"]:
        return "green"
    elif percent <= warnings["yellow"]["max_percent"]:
        return "yellow"
    elif percent <= warnings["orange"]["max_percent"]:
        return "orange"
    else:
        return "red"


# ═══════════════════════════════════════════════════════════
# 2. CONTEXT COMPRESSION
# ═══════════════════════════════════════════════════════════

def get_compression_advice(level, turns):
    budget = load_budget()

    if level == "green":
        return "✓ Normal operation. No compression needed."
    elif level == "yellow":
        lines = ["🟡 Light compression advised:"]
        if turns > 10:
            n = max(1, turns - 10)
            lines.append(f"  - Compress oldest {n} turns to L2_bullets (via dual-compress)")
        lines.append("  - Check for large tool outputs (>5K) → compress to L2_bullets")
        lines.append("  - Review knowledge cache — drop LRU entries below threshold")
        return "\n".join(lines)
    elif level == "orange":
        return ("🟠 AGGRESSIVE compression required:\n"
                "  - Compress all but last 8 turns to L2_bullets (dual-compress)\n"
                "  - Run Phase1 prune on knowledge cache\n"
                "  - Archive current state to Feishu NOW\n"
                "  - Ask user: continue or new session?")
    else:
        return ("🔴 CRITICAL — Must start new session:\n"
                "  - Full Feishu archive immediately\n"
                "  - Save all project state to disk\n"
                "  - Run session-save\n"
                "  - Tell user: fresh session required")


# ═══════════════════════════════════════════════════════════
# 3. CONTEXT STRUCTURING
# ═══════════════════════════════════════════════════════════

def get_structuring_guide():
    budget = load_budget()
    structuring = budget["structuring"]
    lines = ["\n📐 Prompt Structure Guide:"]
    for i, section in enumerate(structuring["prompt_format"]):
        lines.append(f"  {i+1}. {section}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# 4. CONTEXT PRUNING (Phase1)
# ═══════════════════════════════════════════════════════════

def cmd_score_example():
    """Interactive scoring demo using the engine."""
    budget = load_budget()
    pruning = budget["pruning"]
    scoring = pruning["scoring"]

    print("=" * 55)
    print("PHASE1 PRUNING SCORE — Formula:")
    print(f"  Score = recency({scoring['recency_weight']})"
          f" + relevance({scoring['relevance_weight']})"
          f" + dependency({scoring['dependency_weight']})"
          f" + priority({scoring['priority_weight']})")
    print(f"  Prune threshold: {pruning['threshold']}")
    print()

    # Show recency curve
    print("  Recency decay (half-life = 30 min):")
    for age_m in [0, 5, 15, 30, 60, 120]:
        score = 2.0 ** (-age_m / 30.0)
        bar = "█" * int(score * 20)
        print(f"    {age_m:>4}min ago: {score:.2f} {bar}")

    # Show priority mapping
    print("\n  Priority → score:")
    for p, s in [("critical", 1.0), ("high", 0.8), ("normal", 0.5), ("low", 0.2)]:
        bar = "█" * int(s * 20)
        print(f"    {p:>10}: {s:.1f} {bar}")

    # Show dependency boost
    print("\n  Dependency boost (per dependent):")
    for n in range(0, 5):
        boost = min(1.0, n * 0.25)
        bar = "█" * int(boost * 20)
        print(f"    {n} dependents: {boost:.2f} {bar}")

    # Engine-powered example
    print("\n  ── Live Engine Example ──")
    try:
        eng = get_engine()
        from xhls.context_engine import ContextItem
        import time
        now = time.time()

        samples = [
            ContextItem("turn-1", "用户要求实现双压缩层", "turn", 500,
                        now - 60, "high", ["task-1"], ["compression", "architecture"]),
            ContextItem("turn-5", "旧对话：问了天气", "turn", 200,
                        now - 3600, "low", [], ["chat"]),
            ContextItem("tool-1", "文件读取: context_engine.py (300行)", "tool_output", 3000,
                        now - 120, "normal", ["turn-1"], ["code", "context"]),
            ContextItem("mem-1", "pattern-python-context: ContextEngine ABC pattern", "memory", 400,
                        now - 300, "high", [], ["pattern", "architecture"]),
        ]
        eng.score_items(samples, active_topic_tags=["compression", "architecture", "context"])
        for item in samples:
            print(f"    [{item.score:.3f}] {item.id} ({item.category}/{item.priority}) — {item.content[:60]}...")
    except Exception as e:
        print(f"    Engine not available: {e}")
    print("=" * 55)


# ═══════════════════════════════════════════════════════════
# 5. CONTEXT FORECASTING
# ═══════════════════════════════════════════════════════════

def forecast_context(stage):
    """Predict context needs for a pipeline stage."""
    try:
        eng = get_engine()
        tags = eng.forecast(stage)
        print("=" * 55)
        print(f"📡 Context Forecast for [{stage}]:")
        for tag in tags:
            print(f"  → {tag}")
        print("=" * 55)
        return tags
    except Exception:
        # Fallback to static config
        budget = load_budget()
        forecast = budget.get("forecast", {})
        info = forecast.get(stage)
        if not info:
            print(f"Unknown stage: {stage}")
            return []
        print("=" * 55)
        print(f"📡 Context Forecast for [{stage}]:")
        lines = [f"  Preload: {', '.join(info['preload'])}",
                 f"  Brain tags: {', '.join(info['knowledge_tags'])}",
                 f"  → Load into cache BEFORE starting {stage}"]
        print("\n".join(lines))
        print("=" * 55)
        return info.get("knowledge_tags", [])


# ═══════════════════════════════════════════════════════════
# 6. CONTEXT ARCHIVING
# ═══════════════════════════════════════════════════════════

ARCHIVE_TEMPLATE = """# XHLS Context Archive — {timestamp}

## Session State
- Level: {level}
- Usage: {usage}%
- Turns: {turns}
- Compression cycles: {compressions}
- Archive count: {archives}
- Engine: {engine}

## Action Required
{actions}
"""


# ═══════════════════════════════════════════════════════════
# CLI Commands
# ═══════════════════════════════════════════════════════════

def cmd_status(turns=None):
    status = load_status()
    if turns is None:
        turns = status.get("active_turns", 0)

    percent = estimate_usage_percent(turns)
    level = get_warning_level(percent)

    print("=" * 55)
    print("XHLS CONTEXT GUARDIAN v3.0 — Budget Status")
    print(f"Total budget: 258K tokens")
    print(f"Est. turns: {turns}  |  Est. usage: {percent}%  |  Level: {level.upper()}")
    print(f"Compressions: {status['compression_count']}  |  Archives: {status['archive_count']}")
    print()

    budget = load_budget()
    for zone_id, zone in budget["zones"].items():
        bar = "█" * int(zone["percentage"] / 2)
        print(f"  {zone['label']:20s} {bar} {zone['tokens']:>6,}t ({zone['percentage']}%)")

    print()
    print(get_compression_advice(level, turns))
    print()
    print(get_structuring_guide())
    print("=" * 55)

    return level


def cmd_check(turns=None):
    status = load_status()
    if turns is None:
        turns = status.get("active_turns", 0)

    percent = estimate_usage_percent(turns)
    level = get_warning_level(percent)

    status["estimated_usage_percent"] = percent
    status["current_level"] = level
    status["active_turns"] = turns
    status["last_check"] = _now()
    save_status(status)

    emoji = {"green": "✓", "yellow": "🟡", "orange": "🟠", "red": "🔴"}
    print(f"{emoji[level]} Context: {percent}% | {turns} turns | Level: {level}")

    if level in ("orange", "red"):
        print(get_compression_advice(level, turns))

    return level


def cmd_compress():
    status = load_status()
    status["compression_count"] += 1
    save_status(status)

    print(f"🗜️ Compression Cycle #{status['compression_count']}")
    print()
    print("Dual Compression Layers:")
    print("  Layer 1 (Semantic):  Score → threshold filter → deduplicate → dependency boost → budget fit")
    print("  Layer 2 (Representation):  Apply L0→L1→L2→L3 progressive summarization")
    print()
    print("Compression Rules:")
    budget = load_budget()
    for trigger, action in budget["compression"]["rules"].items():
        print(f"  - {trigger} → {action}")
    print()
    print("Agent steps:")
    print("  1. Collect all context items into ContextItem list")
    print("  2. Run engine.dual_compress(items, budget_tokens, level='L2_bullets')")
    print("  3. Review pruned items for false positives")
    print("  4. Run session-save if near orange level")


def cmd_forecast(stage):
    forecast_context(stage)


def cmd_engine_status(turns=None):
    """Engine-powered status report with dual compression info."""
    status = load_status()
    if turns is None:
        turns = status.get("active_turns", 0)

    eng = get_engine()
    state = eng.estimate_usage(turns)
    print(eng.status_report(turns))
    print()
    print(get_compression_advice(state.warning_level, turns))


def cmd_score_items():
    """Demo: score sample items using the engine."""
    try:
        eng = get_engine()
        from xhls.context_engine import ContextItem
        import time
        now = time.time()

        items = [
            ContextItem("turn-1", "实现ContextEngine ABC基类，定义双压缩层接口", "turn", 600,
                        now - 60, "high", ["task-1"], ["compression", "architecture", "abc"]),
            ContextItem("turn-2", "检查依赖关系：context_guardian.py引用旧API", "turn", 400,
                        now - 30, "high", ["turn-1"], ["compression", "refactor"]),
            ContextItem("tool-out-1", "ReadFile: context_budget.json (60 lines)", "tool_output", 2000,
                        now - 45, "normal", ["turn-1"], ["config", "json"]),
            ContextItem("mem-1", "pattern-context-engine: ABC + register decorator", "memory", 350,
                        now - 300, "high", [], ["pattern", "architecture"]),
            ContextItem("mem-2", "preference-python-path: ComfyUI python.exe", "memory", 150,
                        now - 3600, "high", [], ["config", "python"]),
            ContextItem("old-chat", "闲聊：问小黑今天心情怎么样", "turn", 100,
                        now - 7200, "low", [], ["chat"]),
            ContextItem("file-read-1", "已读取: AGENTS.md (宪法文件)", "file_read", 5000,
                        now - 90, "normal", ["task-1"], ["core", "identity"]),
        ]

        print("=" * 55)
        print("PHASE1 SCORING — Sample Items")
        print()
        eng.score_items(items, active_topic_tags=["compression", "architecture", "context", "refactor"])
        for item in items:
            marker = "✓" if item.score >= eng.weights.threshold else "✗ PRUNE"
            print(f"  [{item.score:.3f}] {marker:>10s} {item.id:15s} {item.category:12s} "
                  f"p={item.priority:6s} t={item.token_estimate:>5d}  {item.content[:50]}...")

        # Show what gets pruned
        kept, pruned = eng.phase1_prune(items, budget_tokens=8000,
                                         active_topic_tags=["compression", "architecture"])
        print(f"\n  Result: {len(kept)} kept, {len(pruned)} pruned (budget=8000t, threshold={eng.weights.threshold})")
        print("=" * 55)

    except Exception as e:
        print(f"Engine error: {e}")


def cmd_diagnose():
    """Show engine diagnostics."""
    eng = get_engine()
    print("=" * 55)
    print("CONTEXT ENGINE DIAGNOSTICS")
    print(f"  Engine: {eng.__class__.__name__}")
    print(f"  Weights: recency={eng.weights.recency} relevance={eng.weights.relevance} "
          f"dependency={eng.weights.dependency} priority={eng.weights.priority}")
    print(f"  Threshold: {eng.weights.threshold}")
    print(f"  Compressions run: {eng.compression_count}")
    print(f"  Prunes run: {eng.prune_count}")
    print()
    print("  Pipeline Forecast Stages:")
    for stage in eng.FORECAST_MAP:
        tags = eng.FORECAST_MAP[stage]["knowledge_tags"]
        print(f"    {stage:20s} → {', '.join(tags)}")
    print("=" * 55)



def cmd_self_check(turns=None):
    """Full self-check: engine status + budget + advice + action items.
    This is the agent''s automatic health check called every 5 turns."""
    status = load_status()
    if turns is None:
        turns = status.get("active_turns", 0)

    eng = get_engine()
    state = eng.estimate_usage(turns)

    print("=" * 55)
    print("XHLS SELF-CHECK v3.0 ? Engine-Powered")
    print(f"Turns: {turns}  |  Usage: {state.usage_percent:.0f}%  |  Level: {state.warning_level.upper()}")
    print(f"Compressions: {eng.compression_count}  |  Prunes: {eng.prune_count}")
    print()

    # Zone health
    budget = load_budget()
    for zone_id, zone in budget["zones"].items():
        bar = "?" * int(zone["percentage"] / 2)
        print(f"  {zone['label']:20s} {bar} {zone['tokens']:>6,}t ({zone['percentage']}%)")

    print()
    print(get_compression_advice(state.warning_level, turns))

    # Action items
    actions = {
        "green": ["continue"],
        "yellow": ["compress_oldest_turns", "check_large_outputs", "review_cache"],
        "orange": ["aggressive_compress", "phase1_prune", "feishu_archive", "ask_user_new_session"],
        "red": ["stop_immediately", "full_feishu_archive", "session_save", "tell_user_new_session"],
    }
    print(f"\nAction items: {', '.join(actions[state.warning_level])}")

    # MCP equivalent hint
    print(f"\n(MCP: call xhls_context_check {{\"turns\": {turns}}}}} for structured JSON)")
    print("=" * 55)

    # Save status
    status["estimated_usage_percent"] = state.usage_percent
    status["current_level"] = state.warning_level
    status["active_turns"] = turns
    status["last_check"] = _now()
    save_status(status)

    return state.warning_level


def cmd_list_engines():
    """List all registered engine plugins."""
    get_engine()  # trigger lazy registration
    from xhls.context_engine import list_engines
    print("Registered Context Engines:")
    for name in list_engines():
        from xhls.context_engine import _ENGINE_REGISTRY
        cls = _ENGINE_REGISTRY[name]
        doc = (cls.__doc__ or "").strip().split("\n")[0]
        print(f"  - {name}: {doc}")


# ═══════════════════════════════════════════════════════════
# CLI Entry
# ═══════════════════════════════════════════════════════════

USAGE = """XHLS Context Guardian v3.0
Usage: python context_guardian.py <command> [args]

Commands:
  status [turns]      Full budget status + zone breakdown + advice
  check [turns]       Quick check: level + action needed
  compress            Run compression cycle (dual-layer rules)
  forecast <stage>    Predict context needs for pipeline stage
  score-example       Pruning score explained + live demo
  score-items         Phase1 scoring on sample items (engine demo)
  engine-status [t]   Engine-powered full status report
  diagnose            Engine diagnostics + config
  budget              Show budget allocation only
  self-check [turns]  Full engine-powered health check (for every-5-turn auto-check)
  list-engines        List registered engine plugins

Forecast stages: S1_topic, S2_script, S3_assets, S4_composite, S5_publish,
                 architecture, security
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        turns = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        cmd_status(turns)
    elif cmd == "check":
        turns = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        cmd_check(turns)
    elif cmd == "compress":
        cmd_compress()
    elif cmd == "forecast" and len(sys.argv) >= 3:
        cmd_forecast(sys.argv[2])
    elif cmd == "score-example":
        cmd_score_example()
    elif cmd == "score-items":
        cmd_score_items()
    elif cmd == "engine-status":
        turns = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        cmd_engine_status(turns)
    elif cmd == "diagnose":
        cmd_diagnose()
    elif cmd == "budget":
        budget = load_budget()
        print(json.dumps(budget["zones"], indent=2, ensure_ascii=False))
    elif cmd == "self-check":
        turns = int(sys.argv[2]) if len(sys.argv) >= 3 else None
        cmd_self_check(turns)
    elif cmd == "list-engines":
        cmd_list_engines()
    else:
        print(USAGE)
        sys.exit(1)
