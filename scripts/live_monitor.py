#!/usr/bin/env python3
"""
XHLS Live Monitor — 实时 GitHub + 全网声量监控，变更即时推送飞书手机端

Usage:
    python live_monitor.py                 # 单次扫描
    python live_monitor.py --watch 10      # 每10分钟扫描+推送
    python live_monitor.py --daemon        # 后台持续运行(5分钟间隔)
"""

import json, os, sys, time, hashlib, subprocess
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Feishu push script
PUSH_NOW = os.path.join(
    os.path.expanduser("~"), ".codex", "skills", "feishu-bridge", "scripts", "push_now.py"
)

STATE_FILE = os.path.join(ROOT, "live_state.json")
SEEN_FILE = os.path.join(ROOT, "live_seen.json")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"github": {"stars": 0, "forks": 0, "issues": 0}, "mentions": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)


def push_feishu(title, body):
    """Send push notification to Feishu (appears on phone)."""
    try:
        result = subprocess.run(
            [sys.executable, PUSH_NOW, title],
            input=body,
            capture_output=True,
            text=True,
            timeout=15,
            encoding="utf-8",
        )
        return result.returncode == 0
    except Exception as e:
        print(f"  [Feishu push failed: {e}]")
        return False


# ── GitHub Check ──────────────────────────────────────

def check_github(state):
    """Check GitHub API for changes in stars/forks/issues."""
    import httpx

    client = httpx.Client(timeout=15, follow_redirects=True)
    headers = {"User-Agent": "XHLS/3.0", "Accept": "application/vnd.github+json"}

    r = client.get(
        "https://api.github.com/repos/difcn2026/chinacrawl", headers=headers
    )
    if r.status_code != 200:
        client.close()
        return None

    data = r.json()
    r2 = client.get(
        "https://api.github.com/repos/difcn2026/chinacrawl/issues?state=all",
        headers=headers,
    )
    issues = r2.json() if r2.status_code == 200 else []
    client.close()

    current = {
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "watchers": data.get("watchers_count", 0),
        "issues": len(issues),
        "open_issues": data.get("open_issues_count", 0),
    }

    prev = state.get("github", {})
    alerts = []

    if current["stars"] > prev.get("stars", 0):
        delta = current["stars"] - prev["stars"]
        alerts.append(f"⭐ +{delta} star{'s' if delta > 1 else ''} → 总计 {current['stars']}")

    if current["forks"] > prev.get("forks", 0):
        delta = current["forks"] - prev["forks"]
        alerts.append(f"🔀 +{delta} fork{'s' if delta > 1 else ''} → 总计 {current['forks']}")

    if current["issues"] > prev.get("issues", 0):
        delta = current["issues"] - prev["issues"]
        # Get the new issue titles
        new_issues = [
            i for i in issues if i.get("created_at", "") > state.get("last_check", "")
        ]
        for iss in new_issues[:3]:
            alerts.append(
                f"📝 New issue: #{iss['number']} {iss['title'][:60]}"
            )
        if not new_issues:
            alerts.append(f"📝 +{delta} new issue{'s' if delta > 1 else ''}")

    state["github"] = current
    return alerts


# ── Web Mention Check ─────────────────────────────────

def check_mentions(state):
    """Search web for new mentions of chinacrawl/xhls_scraper."""
    sys.path.insert(0, os.path.join(ROOT, ".codex", "xhls"))
    from xhls_scraper import search_web

    seen = load_seen()
    alerts = []
    queries = [
        ("GitHub", 'site:github.com "chinacrawl" OR "xhls_scraper" -repo:difcn2026'),
        ("V2EX", 'site:v2ex.com chinacrawl OR xhls_scraper'),
        ("Zhihu", 'site:zhihu.com chinacrawl OR xhls_scraper'),
        ("Web", '"china crawl" OR "chinacrawl" scraper -repo:difcn2026'),
    ]

    for platform, query in queries:
        try:
            results = search_web(query, max_results=5)
            for r in results:
                uid = hashlib.md5(r.url.encode()).hexdigest()
                if uid not in seen:
                    seen.add(uid)
                    alerts.append(
                        f"🔍 [{platform}] {r.title[:60]}\n{r.url}"
                    )
            time.sleep(1.5)
        except Exception as e:
            pass

    save_seen(seen)
    return alerts


# ── Main Loop ─────────────────────────────────────────

def scan():
    """Run one scan cycle. Returns list of alert strings."""
    state = load_state()
    now = datetime.now(CST).isoformat()
    state["last_check"] = now
    all_alerts = []

    print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] Scanning...")

    # GitHub
    gh_alerts = check_github(state)
    if gh_alerts:
        all_alerts.extend(gh_alerts)
        print(f"  GitHub: {len(gh_alerts)} changes")

    # Mentions
    mention_alerts = check_mentions(state)
    if mention_alerts:
        all_alerts.extend(mention_alerts)
        print(f"  Mentions: {len(mention_alerts)} new")

    save_state(state)

    if all_alerts:
        body = "\n\n".join(all_alerts)
        title = f"🚀 ChinaCrawl 监控 [{datetime.now(CST).strftime('%H:%M')}]"
        print(f"  PUSHING {len(all_alerts)} alerts to Feishu...")
        ok = push_feishu(title, body)
        if ok:
            print(f"  ✅ Pushed to phone")
        else:
            print(f"  ❌ Push failed")
    else:
        print(f"  No changes")

    # Always print status line
    gs = state.get("github", {})
    print(
        f"  Status: ⭐{gs.get('stars',0)} 🔀{gs.get('forks',0)} 📝{gs.get('issues',0)}"
    )
    return all_alerts


def main():
    import argparse

    ap = argparse.ArgumentParser(description="XHLS Live Monitor")
    ap.add_argument("--watch", type=int, default=0, help="Interval in minutes")
    ap.add_argument("--daemon", action="store_true", help="Run as daemon (5min interval)")
    args = ap.parse_args()

    print("🕷️ XHLS Live Monitor — GitHub + Web Mentions")
    print(f"   推送目标: 飞书手机端")
    print()

    interval = args.watch or (5 if args.daemon else 0)

    if interval > 0:
        print(f"   每 {interval} 分钟扫描一次 (Ctrl+C 停止)")
        try:
            while True:
                scan()
                print(f"   下次扫描: {interval} 分钟后...")
                time.sleep(interval * 60)
        except KeyboardInterrupt:
            print("\n   监控已停止")
    else:
        scan()


if __name__ == "__main__":
    main()
