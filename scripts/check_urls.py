"""Check if ChinaCrawl appears on search engines with exact URLs."""
import json, urllib.request, urllib.parse
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = 'http://47.236.24.76:9999/search'

def search(query):
    data = urllib.parse.urlencode({'q': query, 'format': 'json'}).encode()
    req = urllib.request.Request(BASE, data=data, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())

tests = [
    ('github.com/difcn2026/chinacrawl', 'GitHub 直达'),
    ('pypi.org/project/chinacrawl', 'PyPI 直达'),
    ('gitee.com/difcn2026/chinacrawl', 'Gitee 直达'),
    ('site:github.com difcn2026 chinacrawl', 'GitHub 站内搜索'),
    ('site:gitee.com difcn2026', 'Gitee 站内搜索'),
    ('site:pypi.org chinacrawl', 'PyPI 站内搜索'),
]

for q, desc in tests:
    print(f"🔍 {desc}: {q}")
    try:
        r = search(q)
        found = r.get('results', [])
        # Check if any result actually contains our project
        hits = []
        for item in found[:10]:
            combined = (item.get('url','') + item.get('title','')).lower()
            if any(t in combined for t in ['difcn2026', 'chinacrawl']):
                hits.append(item)
        
        if hits:
            for h in hits[:3]:
                print(f"  ✅ [{h.get('engine','?'):6s}] {h.get('title','')[:70]}")
                print(f"     {h.get('url','')}")
        else:
            print(f"  ❌ 未找到 ({len(found)} 条结果中无匹配)")
            # Show top 2 anyways
            for item in found[:2]:
                print(f"     (top result: [{item.get('engine','?')}] {item.get('title','')[:60]})")
    except Exception as e:
        print(f"  ⚠️ Error: {e}")
    print()

print("Done!")
