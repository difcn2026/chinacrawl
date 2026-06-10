import paramiko, base64, time
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('47.236.24.76', username='root', password='DiFCN2026-2026', timeout=15)
def run(cmd, t=10):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
    return stdout.read().decode() + stderr.read().decode()

# Check current IP
ip = run("podman inspect searxng --format '{{.NetworkSettings.IPAddress}}'").strip()
print(f"SearXNG IP: {ip}")

# Rebuild nginx config with current IP
landing_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>ChinaCrawl - 中国版 Firecrawl | 开源网页数据引擎</title>
<meta name="description" content="ChinaCrawl: 11合1开源网页数据引擎，Firecrawl中国替代品。支持百度搜狗中文搜索、本地Ollama零成本LLM提取。pip install chinacrawl即刻上手。">
<meta name="keywords" content="chinacrawl,ChinaCrawl,web scraping,Firecrawl alternative,Python scraper,中国版Firecrawl,网页抓取,爬虫,开源爬虫,中文搜索,difcn2026">
</head>
<body style="font-family:sans-serif;max-width:700px;margin:40px auto;padding:20px">
<h1>ChinaCrawl</h1>
<h2>中国版 Firecrawl - 11合1开源网页数据引擎</h2>
<p>零外部API成本，一行命令即可使用的企业级网页抓取框架。</p>
<ul>
<li><a href="https://github.com/difcn2026/chinacrawl">GitHub: github.com/difcn2026/chinacrawl</a></li>
<li><a href="https://pypi.org/project/chinacrawl/">PyPI: pypi.org/project/chinacrawl</a></li>
<li><a href="https://gitee.com/difcn2026/chinacrawl">Gitee: gitee.com/difcn2026/chinacrawl</a></li>
</ul>
<pre style="background:#f5f5f5;padding:10px">pip install chinacrawl</pre>
</body>
</html>"""

escaped = landing_html.replace('"', '\\"').replace('\n', ' ')

nginx_conf = f'''server {{
    listen 7777;
    location = /chinacrawl {{
        default_type text/html;
        return 200 "{escaped}";
    }}
    location / {{
        proxy_pass http://{ip}:8080;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
    }}
}}'''

b64 = base64.b64encode(nginx_conf.encode()).decode()
print(f"Deploying config with IP {ip}...")
print(run(f"echo {b64} | base64 -d > /opt/nginx_default.conf"))
print("Restarting nginx...")
print(run("podman restart searxng-proxy"))
time.sleep(2)
print("=== Verify nginx root ===")
print(run('curl -s -o /dev/null -w "%{http_code}" http://localhost:7777/'))
print("=== Verify landing ===")
print(run('curl -s -o /dev/null -w "%{http_code}" http://localhost:7777/chinacrawl'))
print("=== SearXNG search via proxy ===")
print(run('curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:7777/search?q=test&format=json'))
c.close()
print("\nAll fixed!")
