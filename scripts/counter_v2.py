#!/usr/bin/env python3
"""ChinaCrawl landing page with visitor counter + Feishu new-visitor notification."""
import http.server, json, os, time, urllib.parse, urllib.request

COUNTER_FILE = "/opt/chinacrawl_counter.json"
PORT = 7780
FEISHU_APP_ID = "REPLACE_APP_ID"
FEISHU_APP_SECRET = "REPLACE_APP_SECRET"
FEISHU_OPEN_ID = "REPLACE_OPEN_ID"
FEISHU_HOST = "https://open.feishu.cn"

_token = None
_token_expire = 0

def get_token():
    global _token, _token_expire
    if _token and time.time() < _token_expire:
        return _token
    try:
        data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
        req = urllib.request.Request(f"{FEISHU_HOST}/open-apis/auth/v3/tenant_access_token/internal",
                                     data=data, headers={"Content-Type": "application/json"})
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        _token = resp["tenant_access_token"]
        _token_expire = time.time() + 1800
        return _token
    except Exception as e:
        print(f"Token error: {e}")
        return None

def send_feishu_msg(text):
    try:
        token = get_token()
        if not token:
            return
        content = json.dumps({"text": text})
        body = json.dumps({"receive_id": FEISHU_OPEN_ID, "msg_type": "text", "content": content}).encode()
        req = urllib.request.Request(
            f"{FEISHU_HOST}/open-apis/im/v1/messages?receive_id_type=open_id",
            data=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Feishu send error: {e}")

def load_counter():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            return json.load(f)
    return {"total": 0, "unique_ips": {}, "first_seen": time.strftime("%Y-%m-%d %H:%M")}

def save_counter(data):
    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f)

counter = load_counter()

CSS = """
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); color: #e0e0e0; min-height: 100vh; display: flex; justify-content: center; align-items: center; }}
.card {{ background: rgba(255,255,255,0.05); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; padding: 50px 40px; max-width: 650px; width: 90%; text-align: center; }}
h1 {{ font-size: 2.5em; background: linear-gradient(90deg, #f7971e, #ffd200); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }}
h2 {{ font-size: 1.1em; color: #aaa; font-weight: 400; margin-bottom: 30px; }}
.links {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-bottom: 25px; }}
.links a {{ background: rgba(255,255,255,0.08); color: #c0d0ff; padding: 10px 20px; border-radius: 10px; text-decoration: none; font-size: 0.95em; transition: all 0.2s; border: 1px solid rgba(255,255,255,0.05); }}
.links a:hover {{ background: rgba(255,255,255,0.18); transform: translateY(-2px); }}
.pip {{ background: #1a1a2e; padding: 14px 20px; border-radius: 10px; font-family: monospace; font-size: 1.05em; color: #7ecb7e; margin-bottom: 25px; }}
.counter-box {{ background: rgba(255,255,255,0.04); border-radius: 12px; padding: 16px; margin-top: 20px; display: flex; justify-content: center; gap: 30px; }}
.counter-item {{ text-align: center; }}
.counter-num {{ font-size: 2em; font-weight: 700; color: #ffd200; }}
.counter-label {{ font-size: 0.8em; color: #888; margin-top: 4px; }}
"""

LANDING_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ChinaCrawl | Open-Source Web Data Engine</title>
<meta name="description" content="ChinaCrawl: 11-in-1 OSS web data engine. Baidu/Sogou Chinese search, local Ollama zero-cost LLM. pip install chinacrawl.">
<meta name="keywords" content="chinacrawl,ChinaCrawl,web scraping,Firecrawl alternative,Python scraper,difcn2026">
<style>""" + CSS + """</style>
</head>
<body>
<div class="card">
  <h1>ChinaCrawl</h1>
  <h2>11-in-1 Open-Source Web Data Engine</h2>
  <div class="links">
    <a href="https://github.com/difcn2026/chinacrawl">&#9733; GitHub</a>
    <a href="https://pypi.org/project/chinacrawl/">&#128230; PyPI</a>
    <a href="https://gitee.com/difcn2026/chinacrawl">&#127983; Gitee</a>
  </div>
  <div class="pip">pip install chinacrawl</div>
  <div class="counter-box">
    <div class="counter-item">
      <div class="counter-num">{total}</div>
      <div class="counter-label">Total Views</div>
    </div>
    <div class="counter-item">
      <div class="counter-num">{unique}</div>
      <div class="counter-label">Unique Visitors</div>
    </div>
    <div class="counter-item">
      <div class="counter-num">{since}</div>
      <div class="counter-label">Live Since</div>
    </div>
  </div>
</div>
</body>
</html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global counter
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/chinacrawl" or parsed.path == "/":
            ip = self.client_address[0]
            xff = self.headers.get("X-Forwarded-For", "")
            real_ip = xff.split(",")[0].strip() if xff else ip
            now_str = time.strftime("%Y-%m-%d %H:%M")

            # Skip localhost/container IPs for notification
            is_new = False
            if real_ip not in ("127.0.0.1", "::1", "10.88.0.1"):
                if real_ip not in counter["unique_ips"]:
                    is_new = True
                    counter["unique_ips"][real_ip] = now_str
                    # Notify Feishu
                    total_after = counter["total"] + 1
                    unique_after = len(counter["unique_ips"])
                    notify = "New visitor: " + real_ip + " at " + now_str + " | Total: " + str(total_after) + " views, " + str(unique_after) + " unique"
                    send_feishu_msg(notify)
                else:
                    counter["unique_ips"][real_ip] = now_str

            counter["total"] += 1
            save_counter(counter)

            html = LANDING_HTML.format(
                total=counter["total"],
                unique=len(counter["unique_ips"]),
                since=counter["first_seen"][:10]
            )

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif parsed.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print("ChinaCrawl counter + Feishu notify on :" + str(PORT))
    server.serve_forever()
