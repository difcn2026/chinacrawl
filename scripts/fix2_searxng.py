"""Diagnose and fix SearXNG 403 issue on VPS."""
import paramiko
import time

host = '47.236.24.76'
user = 'root'
pw = 'DiFCN2026-2026'

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=user, password=pw, timeout=15)

def run(cmd, timeout=15):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out + err

# Check SearXNG internal files
print("=== /etc/searxng/ files ===")
print(run("podman exec searxng ls /etc/searxng/"))

print("=== limiter.toml ===")
print(run("podman exec searxng cat /etc/searxng/limiter.toml 2>/dev/null || echo 'NO LIMITER FILE'"))

print("=== SearXNG env ===")
print(run("podman exec searxng env | grep -i search"))

print("=== formats in settings.yml ===")
print(run("podman exec searxng grep -A10 'formats:' /etc/searxng/settings.yml"))

print("=== method in settings.yml ===")
print(run("podman exec searxng grep 'method:' /etc/searxng/settings.yml"))

print("=== Try POST to /search ===")
print(run("curl -s -o /dev/null -w '%{http_code}' -X POST 'http://localhost:9999/search?q=test'"))

print("=== Try POST /search with data ===")
print(run("curl -s -o /dev/null -w '%{http_code}' -X POST -d 'q=test' 'http://localhost:9999/search'"))

print("=== Try with content-type form ===")
print(run("curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/x-www-form-urlencoded' -d 'q=test' 'http://localhost:9999/search'"))

# Get actual webpage to see how search works
print("=== HTML page snippet ===")
html = run("curl -s 'http://localhost:9999/'")
import re
form_matches = re.findall(r'<(form|input)[^>]*>', html)
print("Forms/inputs found:", len(form_matches))
for m in form_matches[:5]:
    print(" ", m[:120])

client.close()
print("=== DONE ===")
