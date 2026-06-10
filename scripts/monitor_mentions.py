"""xhls_scraper 全网声量监控脚本

每 N 分钟搜索一次产品提及，记录到 JSON 日志。
首次发现新提及时标记为 milestone。

Usage: python monitor_mentions.py [--interval 60] [--output mentions.json]
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
PRODUCT_NAMES = ["xhls_scraper", "chinacrawl", "ChinaCrawl"]
PLATFORMS = {
    "GitHub": "site:github.com {}",
    "V2EX": "site:v2ex.com {}",
    "Zhihu": "site:zhihu.com {}",
    "CSDN": "site:csdn.net {}",
    "PyPI": "site:pypi.org {}",
    "Gitee": "site:gitee.com {}",
    "Bilibili": "site:bilibili.com {}",
    "Web": "{}",
}

class MentionMonitor:
    def __init__(self, output_path="mentions.json"):
        self.output_path = output_path
        self.data = self._load()
    
    def _load(self):
        if os.path.exists(self.output_path):
            with open(self.output_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"first_scan": None, "last_scan": None, "mentions": [], "milestones": []}
    
    def _save(self):
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def scan(self):
        """Run one scan cycle."""
        from xhls_scraper import search_web
        
        now = datetime.now(CST).isoformat()
        if self.data["first_scan"] is None:
            self.data["first_scan"] = now
        
        self.data["last_scan"] = now
        
        for platform, template in PLATFORMS.items():
            for name in PRODUCT_NAMES:
                query = template.format(name)
                try:
                    results = search_web(query, max_results=10)
                    for r in results:
                        entry = {
                            "platform": platform,
                            "product": name,
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.snippet,
                            "first_seen": now,
                            "last_seen": now,
                        }
                        # Check if new
                        existing = [m for m in self.data["mentions"] if m["url"] == r.url]
                        if not existing:
                            self.data["mentions"].append(entry)
                            milestone = {
                                "type": "first_mention",
                                "platform": platform,
                                "url": r.url,
                                "title": r.title,
                                "time": now,
                            }
                            self.data["milestones"].append(milestone)
                            print(f"  🆕 FIRST MENTION on {platform}: {r.title[:60]}")
                        else:
                            existing[0]["last_seen"] = now
                    time.sleep(1.5)  # Rate limit
                except Exception as e:
                    print(f"  ⚠️ {platform}/{name}: {e}")
        
        self._save()
        return len(self.data["mentions"])
    
    def report(self):
        """Print summary report."""
        print(f"\n{'='*60}")
        print(f"xhls_scraper 全网声量报告")
        print(f"{'='*60}")
        print(f"  首次扫描: {self.data['first_scan'] or 'N/A'}")
        print(f"  最后扫描: {self.data['last_scan'] or 'N/A'}")
        print(f"  总提及数: {len(self.data['mentions'])}")
        print(f"  里程碑数: {len(self.data['milestones'])}")
        
        if self.data["mentions"]:
            print(f"\n  按平台分布:")
            by_platform = {}
            for m in self.data["mentions"]:
                by_platform[m["platform"]] = by_platform.get(m["platform"], 0) + 1
            for p, c in sorted(by_platform.items(), key=lambda x: -x[1]):
                print(f"    {p}: {c}")
        
        if self.data["milestones"]:
            print(f"\n  里程碑:")
            for ms in self.data["milestones"][-10:]:
                print(f"    [{ms['time'][:16]}] {ms['platform']}: {ms['title'][:60]}")
        
        return self.data


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=0, help="Scan interval in minutes (0=once)")
    ap.add_argument("--output", default="mentions.json")
    ap.add_argument("--report", action="store_true", help="Just show report")
    args = ap.parse_args()
    
    monitor = MentionMonitor(args.output)
    
    if args.report:
        monitor.report()
        sys.exit(0)
    
    print("xhls_scraper 全网声量监控")
    print(f"  监控平台: {', '.join(PLATFORMS)}")
    print(f"  产品名: {', '.join(PRODUCT_NAMES)}")
    print()
    
    if args.interval > 0:
        print(f"  每 {args.interval} 分钟扫描一次...")
        while True:
            count = monitor.scan()
            print(f"  [{datetime.now(CST).strftime('%H:%M:%S')}] 扫描完成，总提及 {count} 条")
            time.sleep(args.interval * 60)
    else:
        print("  单次扫描...")
        count = monitor.scan()
        monitor.report()
