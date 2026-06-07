"""XHLS Memory — Persistent long-term memory with session continuity, context compaction, crash-safety, and correction loop.

Inherited from XDLS v2.0 memory.py and enhanced for 小黑 the hacker-engineer architect.

Architecture:
  memory.json        - Structured key-value store (frequently updated)
  sessions.json      - Session summaries for continuity across restarts
  daily/YYYY-MM-DD.md - Daily session logs (append-only, audit trail)
  corrections/       - User correction records (system learning)
  evolution/         - Weekly evolution reports
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
MEMORY_DIR = os.path.join(os.environ.get("CODEX_HOME", os.path.expanduser("~/.codex")), "memory")
MEMORY_FILE = os.path.join(MEMORY_DIR, "memory.json")
SESSIONS_FILE = os.path.join(MEMORY_DIR, "sessions.json")
DAILY_LOG_DIR = os.path.join(MEMORY_DIR, "daily")
CORRECTIONS_DIR = os.path.join(MEMORY_DIR, "corrections")
EVOLUTION_DIR = os.path.join(MEMORY_DIR, "evolution")

# Fix Windows GBK encoding issues
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MAX_CONTEXT_SUMMARY = 600   # Max chars for session context summary
MAX_COMPACTED_VALUE = 200   # Max chars per compacted memory value
COMPACT_THRESHOLD = 20      # Number of memories before auto-compacting old ones


def _now():
    return datetime.now(CST).strftime("%Y-%m-%d %H:%M")


def _today():
    return datetime.now(CST).strftime("%Y-%m-%d")


def _timestamp():
    return int(time.time())


# ── Atomic file I/O ──

def _atomic_save(filepath, data):
    """Write JSON atomically: temp file + rename. Survives crashes."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, filepath)  # atomic on same filesystem


def _load_json(filepath, default=None):
    """Load JSON with crash recovery."""
    if default is None:
        default = {}
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Try recovering from .tmp if main file is corrupted
        tmp = filepath + ".tmp"
        if os.path.exists(tmp):
            try:
                with open(tmp, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        print("[WARN] Memory file corrupted, starting fresh.", file=sys.stderr)
        return default


# ── Memory operations ──

def load_memories():
    return _load_json(MEMORY_FILE, {})


def save_memories(data):
    _atomic_save(MEMORY_FILE, data)


def load_sessions():
    return _load_json(SESSIONS_FILE, {"sessions": [], "last_summary": ""})


def save_sessions(data):
    _atomic_save(SESSIONS_FILE, data)


# ── Core commands ──

def cmd_add(key, value):
    data = load_memories()
    data[key] = {"value": value, "updated": _now(), "priority": "normal"}
    # Auto-compact if too many memories
    if len(data) > COMPACT_THRESHOLD:
        data = _compact_old(data)
    save_memories(data)
    print(f"[OK] Remembered: {key}")


def cmd_add_priority(key, value):
    """Add a high-priority memory that won't be auto-compacted."""
    data = load_memories()
    data[key] = {"value": value, "updated": _now(), "priority": "high"}
    save_memories(data)
    print(f"[OK] Remembered (high priority): {key}")


def cmd_recall(key):
    data = load_memories()
    if key in data:
        entry = data[key]
        pflag = " ★" if entry.get("priority") == "high" else ""
        print(f"[{entry['updated']}]{pflag} {key}: {entry['value']}")
    else:
        print(f"No memory found for: {key}")


def cmd_list():
    data = load_memories()
    if not data:
        print("No memories stored yet.")
        return
    for key, entry in sorted(data.items()):
        pflag = " ★" if entry.get("priority") == "high" else ""
        print(f"[{entry['updated']}]{pflag} {key}: {entry['value']}")


def cmd_forget(key):
    data = load_memories()
    if key in data:
        del data[key]
        save_memories(data)
        print(f"[OK] Forgotten: {key}")
    else:
        print(f"No memory found for: {key}")


def cmd_search(query):
    data = load_memories()
    q = query.lower()
    matches = [(k, v) for k, v in data.items() if q in k.lower() or q in v["value"].lower()]
    if not matches:
        print(f"No memories match: {query}")
        return
    for key, entry in sorted(matches):
        pflag = " ★" if entry.get("priority") == "high" else ""
        print(f"[{entry['updated']}]{pflag} {key}: {entry['value']}")


# ── Session continuity (anti-amnesia) ──

def cmd_session_init():
    """Called at start of every new session. Outputs context for the agent."""
    data = load_memories()
    sessions = load_sessions()

    print("=" * 50)
    print("XHLS MEMORY — Session Context")

    # 1. Last session summary
    last = sessions.get("last_summary", "")
    if last:
        print(f"\n📋 Last Session ({sessions.get('last_time', 'unknown')}):")
        print(f"   {last}")

    # 2. High-priority memories (always shown in full)
    high_priority = [(k, v) for k, v in data.items() if v.get("priority") == "high"]
    if high_priority:
        print(f"\n⭐ High Priority Memories ({len(high_priority)}):")
        for key, entry in sorted(high_priority):
            print(f"   {key}: {entry['value']}")

    # 3. Recent memories (last 10)
    recent = sorted(data.items(), key=lambda x: x[1]["updated"], reverse=True)[:10]
    if recent:
        print(f"\n🕐 Recent Memories:")
        for key, entry in recent:
            if entry.get("priority") != "high":
                print(f"   [{entry['updated']}] {key}: {entry['value'][:100]}")

    # 4. Recent corrections
    _print_recent_corrections(5)

    # 5. Memory stats
    print(f"\n📊 Stats: {len(data)} memories | {len(sessions.get('sessions', []))} sessions")
    print("=" * 50)


def cmd_session_save(summary):
    """Save current session summary for next time."""
    sessions = load_sessions()
    sessions["last_summary"] = summary[:MAX_CONTEXT_SUMMARY]
    sessions["last_time"] = _now()
    sessions.setdefault("sessions", []).append({
        "time": _now(),
        "summary": summary[:MAX_CONTEXT_SUMMARY]
    })
    # Keep only last 50 sessions
    if len(sessions["sessions"]) > 50:
        sessions["sessions"] = sessions["sessions"][-50:]
    save_sessions(sessions)
    print(f"[OK] Session saved: {summary[:80]}...")


# ── Daily log ──

def cmd_daily_log(date_str=None):
    """Read or write daily session log."""
    if date_str is None:
        date_str = _today()
    log_file = os.path.join(DAILY_LOG_DIR, f"{date_str}.md")
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            print(f.read())
    else:
        print(f"No log for {date_str}")


# ── Correction loop (self-evolution) ──

def cmd_correction(error_desc, corrected_rule, tag=None):
    """Record a user correction — the core self-evolution mechanism.

    Inherited from XDLS: every time user says 'wrong', we learn permanently.
    """
    os.makedirs(CORRECTIONS_DIR, exist_ok=True)
    correction_id = _timestamp()
    record = {
        "id": correction_id,
        "time": _now(),
        "error": error_desc,
        "rule": corrected_rule,
        "tag": tag or "general",
    }

    # Save as individual JSON for structured query
    corr_file = os.path.join(CORRECTIONS_DIR, f"corr-{correction_id}.json")
    with open(corr_file, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    # Also append to daily log
    daily_file = os.path.join(DAILY_LOG_DIR, f"{_today()}.md")
    os.makedirs(DAILY_LOG_DIR, exist_ok=True)
    with open(daily_file, "a", encoding="utf-8") as f:
        tag_str = f" [{tag}]" if tag else ""
        f.write(f"\n## Correction{tag_str} — {_now()}\n")
        f.write(f"- **Error**: {error_desc}\n")
        f.write(f"- **Rule**: {corrected_rule}\n")

    # Store in memory with high priority (never auto-compact)
    data = load_memories()
    data[f"correction-{correction_id}"] = {
        "value": f"{error_desc} → {corrected_rule}",
        "updated": _now(),
        "priority": "high",
    }
    save_memories(data)

    print(f"[OK] Correction #{correction_id} recorded{tag_str}: {error_desc[:60]}...")


def cmd_list_corrections(count=10):
    """List recent corrections."""
    _print_recent_corrections(count)


def _print_recent_corrections(count=10):
    if not os.path.exists(CORRECTIONS_DIR):
        return
    files = sorted(
        [f for f in os.listdir(CORRECTIONS_DIR) if f.endswith(".json")],
        reverse=True
    )[:count]
    if files:
        print(f"\n🔧 Recent Corrections ({len(files)}):")
        for f in files:
            with open(os.path.join(CORRECTIONS_DIR, f), "r", encoding="utf-8") as fp:
                c = json.load(fp)
                tag_str = f" [{c.get('tag', '')}]" if c.get('tag') else ""
                print(f"   {c['time']}{tag_str} {c['error'][:60]}")


def cmd_correction_stats():
    """Show correction statistics by tag."""
    if not os.path.exists(CORRECTIONS_DIR):
        print("No corrections recorded yet.")
        return
    stats = {}
    for f in os.listdir(CORRECTIONS_DIR):
        if f.endswith(".json"):
            with open(os.path.join(CORRECTIONS_DIR, f), "r", encoding="utf-8") as fp:
                c = json.load(fp)
                tag = c.get("tag", "general")
                stats[tag] = stats.get(tag, 0) + 1
    print("\nCorrection Stats by Tag:")
    for tag, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")


# ── Evolution logs ──

def cmd_evolution(summary):
    """Generate weekly evolution log."""
    os.makedirs(EVOLUTION_DIR, exist_ok=True)
    date_str = _today()
    evo_file = os.path.join(EVOLUTION_DIR, f"evolution-{date_str}.md")

    content = f"""# XHLS Evolution Log — {date_str}

## Summary
{summary}

## System State
- Memory engine: ACTIVE
- Brain: XHLS v1.0
- Agents: 7-person team

---
Generated by XHLS Memory Engine
"""
    with open(evo_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Also record in memory
    data = load_memories()
    data[f"evolution-{date_str}"] = {
        "value": summary[:200],
        "updated": _now(),
        "priority": "high",
    }
    save_memories(data)

    print(f"[OK] Evolution log saved: {evo_file}")


def cmd_evolution_check():
    """Check if evolution log is due (7+ days since last)."""
    os.makedirs(EVOLUTION_DIR, exist_ok=True)
    files = sorted([f for f in os.listdir(EVOLUTION_DIR) if f.endswith(".md")])
    if not files:
        print("[EVOLUTION] No evolution logs yet. Run: memory.py evolution '<summary>'")
        return

    last_file = files[-1]
    try:
        date_str = last_file.replace("evolution-", "").replace(".md", "")
        last_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=CST)
        now = datetime.now(CST)
        days_since = (now - last_date).days
        if days_since >= 7:
            print(f"[EVOLUTION] Last log was {days_since} days ago ({date_str}). Time for a new one!")
        else:
            print(f"[EVOLUTION] Log is up to date ({days_since} days ago, {date_str}).")
    except ValueError:
        print("[EVOLUTION] Cannot parse last log date. Check manually.")


# ── Context compaction ──

def _compact_old(data):
    """Compress old, low-priority memories into summaries."""
    keys_by_date = sorted(
        [(k, v) for k, v in data.items() if v.get("priority") != "high"],
        key=lambda x: x[1]["updated"]
    )

    to_compact = len(keys_by_date) - COMPACT_THRESHOLD + 5
    if to_compact <= 0:
        return data

    compacted_keys = keys_by_date[:to_compact]
    summary_parts = []
    for key, entry in compacted_keys:
        summary_parts.append(f"{key}: {entry['value'][:80]}")
        del data[key]

    compact_key = f"compacted-{_today()}"
    data[compact_key] = {
        "value": " | ".join(summary_parts)[:MAX_COMPACTED_VALUE],
        "updated": _now(),
        "priority": "low",
    }

    print(f"[INFO] Compacted {len(compacted_keys)} old memories into '{compact_key}'", file=sys.stderr)
    return data


def cmd_compact():
    """Manually trigger compaction."""
    data = load_memories()
    data = _compact_old(data)
    save_memories(data)
    print("[OK] Compaction complete.")


# ── Migrations ──

def cmd_migrate():
    """Migrate old memory format to new format."""
    data = load_memories()
    changed = False
    for key, entry in data.items():
        if isinstance(entry, dict) and "priority" not in entry:
            entry["priority"] = "high" if key.startswith(("preference-", "security-")) else "normal"
            changed = True
    if changed:
        save_memories(data)
        print("[OK] Migrated memory format.")
    else:
        print("[OK] Already up to date.")


# ── CLI ──

USAGE = """XHLS Memory Engine — Usage: memory.py <command> [args]

Commands:
  add <key> <value>         Remember something
  add-priority <key> <val>  Remember with high priority (never auto-compacted)
  recall <key>              Look up a memory
  list                      Show all memories
  forget <key>              Delete a memory
  search <query>            Fuzzy search
  session-init              Called at session start — loads all context
  session-save <summary>    Save session summary for next time
  daily-log [date]          Read daily session log (default: today)
  correction <error> <rule> Record a user correction (system learning)
  correction --tag <t> <e> <r> Record with tag (bug/style/process/rule/security/content)
  corrections [count]       List recent corrections (default: 10)
  correction-stats          Show correction statistics by tag
  evolution <summary>       Generate weekly evolution log
  evolution-check           Check if evolution log is due
  compact                   Manually compact old memories
  migrate                   Migrate old memory format to new
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "add" and len(sys.argv) >= 4:
        cmd_add(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "add-priority" and len(sys.argv) >= 4:
        cmd_add_priority(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "recall" and len(sys.argv) >= 3:
        cmd_recall(sys.argv[2])
    elif cmd == "list":
        cmd_list()
    elif cmd == "forget" and len(sys.argv) >= 3:
        cmd_forget(sys.argv[2])
    elif cmd == "search" and len(sys.argv) >= 3:
        cmd_search(" ".join(sys.argv[2:]))
    elif cmd == "session-init":
        cmd_session_init()
    elif cmd == "session-save" and len(sys.argv) >= 3:
        cmd_session_save(" ".join(sys.argv[2:]))
    elif cmd == "daily-log":
        date_arg = sys.argv[2] if len(sys.argv) >= 3 else None
        cmd_daily_log(date_arg)
    elif cmd == "correction" and len(sys.argv) >= 4:
        # Check for --tag flag
        if sys.argv[2] == "--tag" and len(sys.argv) >= 6:
            cmd_correction(sys.argv[4], " ".join(sys.argv[5:]), tag=sys.argv[3])
        else:
            cmd_correction(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "corrections":
        count = int(sys.argv[2]) if len(sys.argv) >= 3 else 10
        cmd_list_corrections(count)
    elif cmd == "correction-stats":
        cmd_correction_stats()
    elif cmd == "evolution" and len(sys.argv) >= 3:
        cmd_evolution(" ".join(sys.argv[2:]))
    elif cmd == "evolution-check":
        cmd_evolution_check()
    elif cmd == "compact":
        cmd_compact()
    elif cmd == "migrate":
        cmd_migrate()
    else:
        print(USAGE)
        sys.exit(1)
