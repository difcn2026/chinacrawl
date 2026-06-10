# -*- coding: utf-8 -*-
"""Push multiple MD files to Feishu docs with surrogate-safe cleaning."""
import sys, os, json, time, httpx

def clean_text(text):
    return text.encode("utf-8", errors="surrogateescape").decode("utf-8", errors="replace")

def load_creds():
    env_file = r"C:\Users\Administrator\.codex\skills\feishu-bridge\.env"
    env = {}
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.lstrip("\ufeff").strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
    app_id = os.environ.get("FEISHU_APP_ID") or env.get("FEISHU_APP_ID", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET") or env.get("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("ERROR: Credentials not found")
        sys.exit(1)
    return app_id, app_secret

def push_doc(title, content):
    APP_ID, APP_SECRET = load_creds()
    FEISHU_HOST = "https://open.feishu.cn"
    
    content = clean_text(content)
    
    client = httpx.Client(timeout=30)
    
    r = client.post(f"{FEISHU_HOST}/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": APP_ID, "app_secret": APP_SECRET})
    data = r.json()
    token = data.get("tenant_access_token", "")
    if not token:
        print(f"Auth failed: {data}")
        return None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Create doc
    r = client.post(f"{FEISHU_HOST}/open-apis/docx/v1/documents",
                    headers=headers, json={"title": title})
    data = r.json()
    if data.get("code") != 0:
        print(f"Create doc failed: {data}")
        return None
    doc_id = data["data"]["document"]["document_id"]
    print(f"Doc: {doc_id}")
    
    r = client.get(f"{FEISHU_HOST}/open-apis/docx/v1/documents/{doc_id}/blocks", headers=headers)
    root_id = r.json()["data"]["items"][0]["block_id"]
    
    blocks = []
    for line in content.split("\n"):
        line = line.rstrip()
        if not line:
            blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": ""}}], "style": {}}})
        elif line.startswith("# "):
            blocks.append({"block_type": 3, "heading1": {"elements": [{"text_run": {"content": line[2:]}}], "style": {}}})
        elif line.startswith("## "):
            blocks.append({"block_type": 4, "heading2": {"elements": [{"text_run": {"content": line[3:]}}], "style": {}}})
        elif line.startswith("### "):
            blocks.append({"block_type": 5, "heading3": {"elements": [{"text_run": {"content": line[4:]}}], "style": {}}})
        elif line.startswith("- "):
            blocks.append({"block_type": 12, "bullet": {"elements": [{"text_run": {"content": line[2:]}}], "style": {}}})
        else:
            blocks.append({"block_type": 2, "text": {"elements": [{"text_run": {"content": line}}], "style": {}}})
    
    total = 0
    url = f"{FEISHU_HOST}/open-apis/docx/v1/documents/{doc_id}/blocks/{root_id}/children"
    
    for i in range(0, len(blocks), 30):
        batch = blocks[i:i+30]
        try:
            payload = json.dumps({"children": batch, "index": i}, ensure_ascii=False)
            r = client.post(url, headers=headers, content=payload.encode("utf-8"))
            d = r.json()
            if d.get("code") == 0:
                total += len(batch)
            elif d.get("code") == 1740005:
                time.sleep(1)
                r = client.post(url, headers=headers, content=payload.encode("utf-8"))
                if r.json().get("code") == 0:
                    total += len(batch)
                    continue
                print(f"  Rate limit, trying individually...")
                for j, b in enumerate(batch):
                    time.sleep(0.3)
                    p2 = json.dumps({"children": [b], "index": i+j}, ensure_ascii=False)
                    r2 = client.post(url, headers=headers, content=p2.encode("utf-8"))
                    if r2.json().get("code") == 0:
                        total += 1
            else:
                print(f"  Batch {i} err: {d.get('code')} {d.get('msg','')}")
        except Exception as e:
            print(f"  Batch {i} exception: {e}")
    
    doc_url = f"https://n4uo7q5a7i.feishu.cn/docx/{doc_id}"
    print(f"  Blocks: {total}/{len(blocks)}")
    print(f"  URL: {doc_url}")
    return doc_url

if __name__ == "__main__":
    files = [
        (r"C:\Users\Administrator\Documents\New project\projects\douyin-xiaobing\data\竞品分析_AI小冰.md",
         "AI小冰·竞品分析报告"),
        (r"C:\Users\Administrator\Documents\New project\projects\douyin-xiaobing\data\自有账号作战方案.md",
         "自有AI账号·从0到1作战方案"),
    ]
    
    for path, title in files:
        print(f"\n{'='*50}")
        print(f"Pushing: {title}")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        url = push_doc(title, content)
