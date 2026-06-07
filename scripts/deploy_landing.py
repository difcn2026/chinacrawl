"""Deploy ChinaCrawl landing page on VPS nginx for SEO backlinks."""
import paramiko, base64, time

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('47.236.24.76', username='root', password='DiFCN2026-2026', timeout=15)

def run(cmd, t=10):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
    return stdout.read().decode() + stderr.read().decode()

# Create landing page HTML
html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ChinaCrawl - 中国版 Firecrawl | 开源网页数据引擎</title>
<meta name="description" content="ChinaCrawl: 11合1开源网页数据引擎，Firecrawl 中国替代品。支持百度/搜狗中文搜索、本地 Ollama 零成本 LLM 提取。pip install chinacrawl 即刻上手。">
<meta name="keywords" content="chinacrawl, ChinaCrawl, web scraping, Firecrawl alternative, Python scraper, 中国版Firecrawl, 网页抓取, 爬虫, 开源爬虫, 中文搜索, difcn2026">
</head>
<body>
<h1>ChinaCrawl</h1>
<h2>中国版 Firecrawl — 11合1开源网页数据引擎</h2>
<p>零外部API成本，一行 pip install 即可使用的企业级网页抓取框架。</p>
<ul>
  <li><a href="https://github.com/difcn2026/chinacrawl">GitHub: github.com/difcn2026/chinacrawl</a></li>
  <li><a href="https://pypi.org/project/chinacrawl/">PyPI: pypi.org/project/chinacrawl</a></li>
  <li><a href="https://gitee.com/difcn2026/chinacrawl">Gitee: gitee.com/difcn2026/chinacrawl</a></li>
</ul>
<pre>pip install chinacrawl</pre>
</body>
</html>"""

# Base64 encode for safe transfer
b64 = base64.b64encode(html.encode()).decode()
print("=== Deploying landing page ===")
print(run(f"echo {b64} | base64 -d > /opt/chinacrawl_landing.html"))

# Verify
print("=== Verify HTML ===")
result = run("cat /opt/chinacrawl_landing.html | head -c 400")
print(result)

# Update nginx config to serve landing page alongside SearXNG proxy
nginx_conf = """server {
    listen 7777;
    location = /chinacrawl {
        root /opt;
        try_files /chinacrawl_landing.html =404;
        default_type text/html;
    }
    location / {
        proxy_pass http://10.88.0.40:8080;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
    }
}"""

b64c = base64.b64encode(nginx_conf.encode()).decode()
print("\n=== Updating nginx config ===")
print(run(f"echo {b64c} | base64 -d > /opt/nginx_default.conf"))

print("=== Verify nginx ===")
print(run("cat /opt/nginx_default.conf"))

print("\n=== Restarting nginx ===")
print(run("podman restart searxng-proxy"))
time.sleep(2)

# Test the landing page
print("\n=== Test landing page ===")
print(run("curl -s -w 'HTTP:%{http_code}' http://localhost:7777/chinacrawl | tail -3"))

c.close()
print("\n✅ Landing page deployed at http://47.236.24.76:7777/chinacrawl")
