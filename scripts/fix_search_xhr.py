"""
Fix search_via_xhr in browser.py:
1. Fix API path mapping (discover -> general)
2. Fix chunked encoding handling in _on_response
"""
import re

path = r"C:\Users\Administrator\Documents\xhls_scraper\chinacrawl\douyin\browser.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: API paths - /discover/search/ -> /general/search/
content = content.replace(
    '"/aweme/v1/web/discover/search/"',
    '"/aweme/v1/web/general/search/"'
)

# Fix 2: Replace the _on_response handler in search_via_xhr
# Old: just response.json() which fails on chunked encoding
old_handler = """        try:
            data = response.json()
        except Exception:
            return"""

# New handler that handles chunked encoding
new_handler = """        try:
            # Handle chunked transfer encoding (stream endpoint)
            # Body may look like: 18d9a\\r\\n{...json...}\\r\\n0\\r\\n\\r\\n
            body = response.text()
            start = body.find("{")
            end = body.rfind("}")
            if start >= 0 and end > start:
                data = json.loads(body[start:end+1])
            else:
                data = json.loads(body)
        except Exception:
            return"""

# We need to be specific: only fix the SECOND occurrence (search _on_response)
# Find all occurrences
occurrences = list(re.finditer(re.escape(old_handler), content))
print(f"Found {len(occurrences)} occurrences of old_handler")

if len(occurrences) >= 2:
    # Replace the second occurrence (search _on_response)
    idx = occurrences[1].start()
    content = content[:idx] + new_handler + content[idx + len(old_handler):]
    print(f"Replaced second occurrence at offset {idx}")
elif len(occurrences) == 1:
    print("Only one occurrence found (user_posts _on_response)")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done!")
# Verify
count_discover = content.count('"/aweme/v1/web/discover/search/"')
count_general = content.count('"/aweme/v1/web/general/search/"')
print(f"discover references remaining: {count_discover}")
print(f"general references: {count_general}")
