"""Fix SearXNG: edit host settings.yml + restart."""
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

# Check current state
print("=== Container Status ===")
print(run("podman ps -a"))

print("=== Host settings.yml formats ===")
print(run("grep -A5 'formats:' /opt/searxng/settings.yml"))

print("=== ls /opt/searxng/ ===")
print(run("ls -la /opt/searxng/"))

# Edit host settings.yml to add json format
print("=== Editing /opt/searxng/settings.yml to add json ===")
print(run("sed -i 's/^    - html$/    - html\\n    - json/' /opt/searxng/settings.yml"))

print("=== Verify edit ===")
print(run("grep -A5 'formats:' /opt/searxng/settings.yml"))

# Restart searxng
print("=== Restarting searxng ===")
print(run("podman restart searxng"))
time.sleep(5)

# Check it's running
print("=== Container Status After Restart ===")
print(run("podman ps -a"))

# Test
print("=== Internal POST test ===")
print(run("curl -s -w '\\nHTTP:%{http_code}' -X POST 'http://localhost:9999/search?q=test&format=json' | tail -5"))

client.close()
print("=== DONE ===")
