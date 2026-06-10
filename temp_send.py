import json, httpx, os

env = {}
with open(r"C:\Users\Administrator\.codex\skills\feishu-bridge\.env", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"): continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

client = httpx.Client(timeout=30)
r = client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", json={"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]})
token = r.json()["tenant_access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

doc_id = "AgO2dhFQdohWSix463mctdennof"

# Read markdown
md_path = r"C:\Users\Administrator\Documents\New project\docs\LoRA训练集成方案.md"
with open(md_path, "r", encoding="utf-8") as f:
    content = f.read()

# Build blocks
blocks = []
for line in content.split("\n"):
    line = line.rstrip()
    if not line:
        continue
    if line.startswith("# "):
        blocks.append({"block_type": 3, "heading1": {"elements": [{"text_run": {"content": line[2:]}}], "style": {}}})
    elif line.startswith("## "):
        blocks.append({"block_type": 4, "heading2": {"elements": [{"text_run": {"content": line[3:]}}], "style": {}}})
    elif line.startswith("### "):
        blocks.append({"block_type": 5, "heading3": {"elements": [{"text_run": {"content": line[4:]}}], "style": {}}})
    elif line.strip() == "---":
        continue
    else:
        blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": line}}], "style": {}}})

print(f"Total blocks: {len(blocks)}")

# Send in batches of 10
url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children"
total = 0
for i in range(0, len(blocks), 10):
    batch = blocks[i:i+10]
    r = client.post(url, headers=headers, json={"children": batch, "index": -1})
    d = r.json()
    if d.get("code") == 0:
        total += len(batch)
        print(f"  Batch {i//10+1}: OK (+{len(batch)})")
    else:
        print(f"  Batch {i//10+1}: FAIL code={d.get('code')} msg={d.get('msg','')}")
        break

print(f"\nDone! {total}/{len(blocks)} blocks")
url2 = f"https://n4uo7q5a7i.feishu.cn/docx/{doc_id}"
print(f"URL: {url2}")
os.startfile(url2)
