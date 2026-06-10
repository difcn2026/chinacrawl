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
print("=== SearXNG /etc/searxng/ files ===")
print(run("podman exec searxng ls /etc/searxng/"))

print("=== limiter.toml ===")
print(run("podman exec searxng cat /etc/searxng/limiter.toml 2>/dev/null || echo 'NO LIMITER FILE'"))

print("=== SearXNG env ===")
print(run("podman exec searxng env | grep -i search"))

print("=== Recent logs with 403/forbidden/limiter/bot ===")
print(run("podman logs searxng 2>&1 | grep -iE '403|forbidden|limiter|botdetect' | tail -20"))

# Check if formats:json is enabled
print("=== settings.yml formats section ===")
print(run("podman exec searxng grep -A5 'formats:' /etc/searxng/settings.yml"))

# Try the search endpoint with different approaches
print("=== Try POST to /search (no format) ===")
print(run("curl -s -o /dev/null -w '%{http_code}' -X POST 'http://localhost:9999/search?q=test'"))

print("=== Try GET to / (main page) ===")
print(run("curl -s -o /dev/null -w '%{http_code}' -X GET 'http://localhost:9999/'"))

print("=== Try POST to / (main page) ===")
print(run("curl -s -o /dev/null -w '%{http_code}' -X POST -d 'q=test' 'http://localhost:9999/'"))

# Maybe the main search form submits to / not /search?
# Let's try the HTML form approach
print("=== Try Search with CSRF token ===")
result = run("curl -s -c /tmp/cookies.txt -b /tmp/cookies.txt 'http://localhost:9999/' 2>&1 | grep -o 'name=\"csrf_token\" value=\"[^\"]*\"' | head -1")
print("CSRF:", result)

client.close()
print("=== DONE ===")
