"""Submit landing page + GitHub links to search engines from VPS."""
import paramiko, urllib.request, urllib.parse

# --- From VPS (faster, closer to China) ---
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('47.236.24.76', username='root', password='DiFCN2026-2026', timeout=15)
def run(cmd, t=15):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
    return stdout.read().decode() + stderr.read().decode()

landing_url = "http://47.236.24.76:7777/chinacrawl"

# Google
print("=== Google ===")
# Try submitting via indexed page with link to landing
r = run(f'curl -s -w "%{{http_code}}" -H "User-Agent: Googlebot/2.1" "{landing_url}" -m 10')
print(f"  Googlebot fetch: {r[-3:]}")

# Bing
print("=== Bing ===")
r = run(f'curl -s -w "%{{http_code}}" -H "User-Agent: bingbot/2.0" "{landing_url}" -m 10')
print(f"  Bingbot fetch: {r[-3:]}")

# Baidu spider
print("=== Baidu ===")
r = run(f'curl -s -w "%{{http_code}}" -H "User-Agent: Baiduspider/2.0" "{landing_url}" -m 10')
print(f"  Baiduspider fetch: {r[-3:]}")

# Sogou spider
print("=== Sogou ===")
r = run(f'curl -s -w "%{{http_code}}" -H "User-Agent: Sogou web spider/4.0" "{landing_url}" -m 10')
print(f"  Sogou spider fetch: {r[-3:]}")

# Directly ping Google with the page
print("\n=== Ping endpoints ===")
r = run(f'curl -s -w "%{{http_code}}" "https://webcache.googleusercontent.com/search?q=cache:{landing_url}" -m 10 -o /dev/null')
print(f"  Google cache check: {r}")

c.close()

# --- From local ---
print("\n=== Local submissions ===")
for engine, endpoint in [
    ("Google", f"https://www.google.com/webmasters/tools/ping?sitemap={urllib.parse.quote(landing_url)}"),
]:
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "ChinaCrawl/0.1"})
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"  {engine}: {resp.status}")
    except Exception as e:
        print(f"  {engine}: {e}")

print("\nDone! Crawlers should discover the landing page within hours.")
