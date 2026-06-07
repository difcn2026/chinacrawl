"""Test ChinaCrawl search with our VPS SearXNG."""
import sys
sys.path.insert(0, r'C:\Users\Administrator\Documents\xhls_scraper')
from chinacrawl import search_web, SEARXNG_INSTANCES

print("SearXNG instances:", SEARXNG_INSTANCES[:3])
print()

results = search_web('今日头条 金融 最新消息', max_results=10)
print(f"Got {len(results)} results:")
for i, r in enumerate(results):
    print(f"{i+1}. {r.title[:80]}")
    print(f"   {r.url}")
    if r.snippet:
        print(f"   {r.snippet[:150]}...")
    print()
