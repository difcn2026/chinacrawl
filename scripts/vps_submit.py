"""Submit URLs from VPS to search engines."""
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('47.236.24.76', username='root', password='DiFCN2026-2026', timeout=15)

def run(cmd, t=15):
    stdin, stdout, stderr = c.exec_command(cmd, timeout=t)
    return stdout.read().decode() + stderr.read().decode()

cmds = {
    "Baidu": '''curl -s -w 'HTTP:%{http_code}' -X POST -d 'url=https://github.com/difcn2026/chinacrawl' -H 'User-Agent: Mozilla/5.0' 'https://ziyuan.baidu.com/linksubmit/url' -m 10''',
    "Sogou": '''curl -s -w 'HTTP:%{http_code}' -X POST -d 'url=https://github.com/difcn2026/chinacrawl' -H 'User-Agent: Mozilla/5.0' 'https://zhanzhang.sogou.com/index.php/urlSubmit/submit' -m 10''',
    "Google": '''curl -s -w 'HTTP:%{http_code}' 'https://www.google.com/ping?sitemap=https://raw.githubusercontent.com/difcn2026/chinacrawl/main/sitemap.xml' -m 10''',
    "Bing": '''curl -s -w 'HTTP:%{http_code}' -X POST -H 'Content-Type: application/json' -d '{"siteUrl":"https://github.com","urlList":["https://github.com/difcn2026/chinacrawl"]}' 'https://ssl.bing.com/webmaster/api.svc/json/SubmitUrlbatch?apikey=' -m 10''',
}

for name, cmd in cmds.items():
    print(f"=== {name} ===")
    result = run(cmd)
    print(result[:300])
    print()

c.close()
