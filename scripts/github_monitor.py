"""GitHub repo monitor - track stars, forks, issues over time."""
import json, os, time
from datetime import datetime, timezone, timedelta
import httpx

CST = timezone(timedelta(hours=8))
REPO = "difcn2026/chinacrawl"
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "github_stats.json")

def fetch_stats():
    client = httpx.Client(timeout=15, follow_redirects=True)
    headers = {"User-Agent": "XHLS/3.0", "Accept": "application/vnd.github+json"}
    
    r = client.get(f"https://api.github.com/repos/{REPO}", headers=headers)
    if r.status_code != 200:
        client.close()
        return None
    
    data = r.json()
    
    r2 = client.get(f"https://api.github.com/repos/{REPO}/issues?state=all", headers=headers)
    issues = r2.json() if r2.status_code == 200 else []
    
    client.close()
    
    return {
        "time": datetime.now(CST).isoformat(),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "watchers": data.get("watchers_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "total_issues": len(issues),
        "subscribers": data.get("subscribers_count", 0),
        "network_count": data.get("network_count", 0),
    }

def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"repo": REPO, "history": [], "milestones": []}

def save_history(history):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def check_milestones(history, new_stats):
    milestones = []
    if history["history"]:
        prev = history["history"][-1]
        if new_stats["stars"] > prev["stars"]:
            milestones.append(f"Stars: +{new_stats['stars'] - prev['stars']} stars (total: {new_stats['stars']})")
        if new_stats["forks"] > prev["forks"]:
            milestones.append(f"🔀 +{new_stats['forks'] - prev['forks']} forks")
        if new_stats["total_issues"] > prev["total_issues"]:
            milestones.append(f"📝 +{new_stats['total_issues'] - prev['total_issues']} issues")
    elif new_stats["stars"] > 0:
        milestones.append(f"🎉 First star!")
    return milestones

def scan():
    history = load_history()
    stats = fetch_stats()
    if stats is None:
        print("Failed to fetch stats")
        return
    
    milestones = check_milestones(history, stats)
    history["history"].append(stats)
    
    for ms in milestones:
        print(f"  🆕 {ms}")
        history["milestones"].append({"time": stats["time"], "event": ms})
    
    save_history(history)
    
    delta = ""
    if len(history["history"]) >= 2:
        prev = history["history"][-2]
        d_stars = stats["stars"] - prev["stars"]
        if d_stars != 0:
            delta = f" ({'+' if d_stars > 0 else ''}{d_stars})"
    
    print(f"  Stars: {stats['stars']}{delta} | Forks: {stats['forks']} | Issues: {stats['total_issues']} | Watchers: {stats['watchers']}")
    return stats

def report():
    history = load_history()
    print(f"\n{'='*50}")
    print(f"  {REPO} — GitHub 监控报告")
    print(f"{'='*50}")
    print(f"  数据点: {len(history['history'])}")
    
    if history["history"]:
        latest = history["history"][-1]
        first = history["history"][0]
        print(f"  首次: {first['time'][:16]}")
        print(f"  最新: {latest['time'][:16]}")
        print(f"  Stars: Stars:  {latest['stars']}  (起始: {first['stars']})")
        print(f"  🔀 Forks:  {latest['forks']}")
        print(f"  📝 Issues: {latest['total_issues']}")
    
    if history["milestones"]:
        print(f"\n  里程碑:")
        for m in history["milestones"]:
            print(f"    [{m['time'][:16]}] {m['event']}")
    
    return history

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=int, default=0, help="Watch interval in minutes")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    
    if args.report:
        report()
    elif args.watch > 0:
        print(f"Monitoring {REPO} every {args.watch} min...")
        while True:
            scan()
            time.sleep(args.watch * 60)
    else:
        scan()
