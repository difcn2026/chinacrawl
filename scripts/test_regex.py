import re
# Simulate chunked body
body = '12000\r\n{"status_code":0,"data":[{"aweme_id":"123"}]}\r\n0\r\n\r\n'
print("BEFORE:", repr(body[:80]))

# Current regex in browser.py
cleaned = re.sub(r'[0-9a-fA-F]+\r?\n', '', body).strip()
print("AFTER :", repr(cleaned[:80]))

# Alternative: strip all chunk-like lines
cleaned2 = re.sub(r'^[0-9a-fA-F]+\s*\r?\n', '', body, flags=re.MULTILINE).strip()
print("AFTER2:", repr(cleaned2[:80]))

# Alternative: just find JSON
import json
# Find the first { and last }
start = body.find('{')
end = body.rfind('}')
if start >= 0 and end > start:
    cleaned3 = body[start:end+1]
    print("AFTER3:", repr(cleaned3[:80]))
    try:
        data = json.loads(cleaned3)
        print("PARSED:", list(data.keys())[:3], "items:", len(data.get("data", [])))
    except Exception as e:
        print("ERROR:", e)
