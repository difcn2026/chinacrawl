import json, httpx

with open(r"C:\Users\Administrator\.codex\skills\feishu-bridge\.env", "r", encoding="utf-8") as f:
    env = {}
    for line in f:
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"): continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

client = httpx.Client(timeout=30)
r = client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]})
token = r.json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

r = client.post("https://open.feishu.cn/open-apis/docx/v1/documents", headers=headers, json={"title": "上游代理部署文档"})
doc_id = r.json()["data"]["document"]["document_id"]
print(f"Doc: {doc_id}")

r = client.get(f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks", headers=headers)
root_id = r.json()["data"]["items"][0]["block_id"]

content = [
    (3, "上游代理部署文档"),
    (4, "代理信息"),
    (2, "SOCKS5: 107.172.62.24:1080（已可用）"),
    (2, "HTTP:   107.172.62.25:3128（待修复）"),
    (2, "账号: proxyuser / 密码: StrongProxyPass2024!"),
    (4, "VPS 信息"),
    (2, "提供商: RackNerd / Windows VPS 2GB"),
    (2, "IP: 107.172.62.24 / 107.172.62.25, RDP: 3389"),
    (2, "面板: https://nerdvm.racknerd.com/ 账号: vmuser339307"),
    (4, "代理软件"),
    (2, "3proxy v0.9.6, C:\\proxy\\bin64\\3proxy.exe"),
    (2, "配置: C:\\proxy\\cfg\\proxy.cfg"),
    (4, "启动命令"),
    (2, "C:\\proxy\\bin64\\3proxy.exe C:\\proxy\\cfg\\proxy.cfg"),
    (4, "测试"),
    (2, "curl -x socks5h://proxyuser:StrongProxyPass2024!@107.172.62.24:1080 https://github.com"),
    (4, "注意事项"),
    (2, "1. Defender排除: Add-MpPreference -ExclusionPath C:\\proxy"),
    (2, "2. 仅107.172.62.24对外可访问, .25不通"),
    (2, "3. 重启VPS后需手动启动"),
    (4, "日期: 2026-06-04"),
]

blocks = []
for bt, text in content:
    if bt == 3:
        blocks.append({"block_type": 3, "heading1": {"elements": [{"text_run": {"content": text}}], "style": {}}})
    elif bt == 4:
        blocks.append({"block_type": 4, "heading2": {"elements": [{"text_run": {"content": text}}], "style": {}}})
    else:
        blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": text}}], "style": {}}})

url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_id}/children/batch_create"
r = client.post(url, headers=headers, json={"children": blocks, "index": -1})
d = r.json()
print(f"Result: code={d.get('code')} msg={d.get('msg','')}")

print(f"URL: https://n4uo7q5a7i.feishu.cn/docx/{doc_id}")
