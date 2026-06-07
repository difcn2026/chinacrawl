"""Test ChinaCrawl visibility on Baidu/Sogou/Bing via different keywords."""
import json, urllib.request, urllib.parse
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = 'http://47.236.24.76:9999/search'

keywords = [
    'chinacrawl',
    'china crawl github',
    'difcn2026',
    'ChinaCrawl 爬虫',
    '中国版Firecrawl',
    'xhls_scraper',
    'chinacrawl pypi',
]

def search(query):
    data = urllib.parse.urlencode({'q': query, 'format': 'json'}).encode()
    req = urllib.request.Request(BASE, data=data, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

for kw in keywords:
    print(f"\n{'='*60}")
    print(f"🔍 [{kw}]")
    print(f"{'='*60}")
    try:
        results = search(kw)
        found = results.get('results', [])
        # Only show results containing relevant terms
        relevant = []
        for r in found[:10]:
            combined = (r.get('title','') + ' ' + r.get('url','') + ' ' + r.get('content','')).lower()
            if any(t in combined for t in ['chinacrawl', 'difcn', 'xhls', 'firecrawl', 'china']):
                relevant.append(r)
        if not relevant:
            relevant = found[:3]  # fallback: show top 3
        
        for i, r in enumerate(relevant[:5]):
            engine = r.get('engine', '?')
            title = r.get('title', '')
            url = r.get('url', '')
            print(f"  [{engine.upper():6s}] {title[:70]}")
            print(f"          {url}")
        if not relevant:
            print("  ❌ 无相关结果")
        engines_used = set(r.get('engine','?') for r in found[:10])
        print(f"  引擎: {engines_used}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*60)
print("Done!")
