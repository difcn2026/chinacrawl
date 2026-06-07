"""
小黑 · XHLS v3.0 — 飞书云文档推送工具 (v2)
用法: python push_doc.py <标题> <markdown文件路径>
示例: python push_doc.py "ADR: scraper商业化" "knowledge/pipeline-decisions/adr-xxx.md"
"""
import json, httpx, sys

env_path = r"C:\Users\Administrator\.codex\skills\feishu-bridge\.env"
env = {}
with open(env_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

client = httpx.Client(timeout=60)

# Auth
r = client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]})
token = r.json()["tenant_access_token"]
H = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

# Args
if len(sys.argv) >= 3:
    title = sys.argv[1]
    doc_path = sys.argv[2]
else:
    print("用法: python push_doc.py <标题> <markdown文件路径>")
    sys.exit(1)

# Create doc
r = client.post("https://open.feishu.cn/open-apis/docx/v1/documents", headers=H,
    json={"title": title})
d = r.json()
if d.get("code") != 0:
    print(f"创建文档失败: {d}")
    sys.exit(1)
doc_id = d["data"]["document"]["document_id"]
print(f"Doc created: {doc_id}")

# Get root block
r = client.get(f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks", headers=H)
root_id = r.json()["data"]["items"][0]["block_id"]

# Read markdown
with open(doc_path, "r", encoding="utf-8") as f:
    lines = f.read().split("\n")

# Convert to blocks
blocks = []
in_code = False
for line in lines:
    stripped = line.rstrip()

    if stripped.startswith("```"):
        in_code = not in_code
        continue
    if in_code:
        blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": "    " + stripped}}], "style": {}}})
        continue
    if not stripped:
        blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": ""}}], "style": {}}})
        continue
    if stripped.startswith("|---"):
        continue
    if stripped.startswith("|") and "|" in stripped[2:]:
        blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": stripped}}], "style": {}}})
        continue
    if stripped.startswith("# "):
        blocks.append({"block_type": 3, "heading1": {"elements": [{"text_run": {"content": stripped[2:]}}], "style": {}}})
    elif stripped.startswith("## "):
        blocks.append({"block_type": 4, "heading2": {"elements": [{"text_run": {"content": stripped[3:]}}], "style": {}}})
    elif stripped.startswith("### "):
        blocks.append({"block_type": 5, "heading3": {"elements": [{"text_run": {"content": stripped[4:]}}], "style": {}}})
    else:
        blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": stripped}}], "style": {}}})

# Push in batches
api = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{root_id}/children"
done = 0
for i in range(0, len(blocks), 30):
    batch = blocks[i:i+30]
    r = client.post(api, headers=H, json={"children": batch, "index": -1})
    d = r.json()
    if d.get("code") == 0:
        done += len(batch)
        print(f"  Batch {i//30+1}: OK ({len(batch)} blocks)")
    else:
        print(f"  Batch {i//30+1} err {d.get('code')}: {r.text[:200]}")
        break

url = f"https://n4uo7q5a7i.feishu.cn/docx/{doc_id}"
print(f"\nDone: {done}/{len(blocks)} blocks")
print(f"URL: {url}")
