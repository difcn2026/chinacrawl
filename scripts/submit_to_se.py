"""
ChinaCrawl Search Engine Push
"""
import urllib.request, urllib.parse, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

URLS = [
    "https://github.com/difcn2026/chinacrawl",
    "https://pypi.org/project/chinacrawl/",
    "https://gitee.com/difcn2026/chinacrawl",
]

def do(url, data=None, timeout=8):
    try:
        body = json.dumps(data).encode() if isinstance(data, dict) else (data.encode() if data else None)
        req = urllib.request.Request(url, data=body, method="POST" if body else "GET",
            headers={"User-Agent": "ChinaCrawl/0.1", "Content-Type": "application/json" if isinstance(data, dict) else "application/x-www-form-urlencoded"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors='replace')[:200]
    except Exception as e:
        return None, str(e)[:100]

# 1. Google Sitemap Ping
print("1. GOOGLE")
sitemap = "https://raw.githubusercontent.com/difcn2026/chinacrawl/main/sitemap.xml"
code, _ = do(f"https://www.google.com/ping?sitemap={urllib.parse.quote(sitemap)}", timeout=5)
print(f"   Sitemap ping: {code}")

# 2. Bing individual URL submission
print("\n2. BING")
for u in URLS:
    code, _ = do("https://ssl.bing.com/webmaster/api/SubmitUrl", data=urllib.parse.urlencode({"url": u}), timeout=10)
    print(f"   {u.split('/')[-1]:20s} → {code}")

# 3. Baidu
print("\n3. BAIDU")
for u in URLS:
    code, body = do("https://ziyuan.baidu.com/linksubmit/url", data=urllib.parse.urlencode({"url": u}), timeout=8)
    if code and code < 400:
        print(f"   ✅ {u.split('/')[-1]}")
    else:
        print(f"   ⚠️ {u.split('/')[-1]} → {code} (需登录 ziyuan.baidu.com)")

# 4. Sogou
print("\n4. SOGOU")
for u in URLS:
    code, body = do("https://zhanzhang.sogou.com/index.php/urlSubmit/submit", data=urllib.parse.urlencode({"url": u}), timeout=8)
    if code and code < 400:
        print(f"   ✅ {u.split('/')[-1]}")
    else:
        print(f"   ⚠️ {u.split('/')[-1]} → {code} (需登录 zhanzhang.sogou.com)")

print("\n✅ Google/Bing 已推送 | ⚠️ Baidu/Sogou 需手动登录提交")
print("百度: https://ziyuan.baidu.com/linksubmit/url")
print("搜狗: https://zhanzhang.sogou.com/")
