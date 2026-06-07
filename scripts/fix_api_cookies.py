"""Add cookie support to api.py."""
import re

path = r"C:\Users\Administrator\Documents\xhls_scraper\chinacrawl\douyin\api.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add _load_cookies and set_cookies functions right after _get_client/close_client section
# Find the close_client function and add after it
insertion = '''
# Cookie management
_cookies: dict = {}  # name -> value dict for httpx

def load_cookies(cookie_file: str) -> int:
    """Load cookies from Playwright-format JSON file."""
    global _cookies
    with open(cookie_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    cookies = data.get("cookies", data if isinstance(data, list) else [])
    _cookies = {}
    for c in cookies:
        _cookies[c["name"]] = c["value"]
    log.info("Loaded %d cookies from %s", len(_cookies), cookie_file)
    return len(_cookies)

def _apply_cookies(client: httpx.Client) -> None:
    """Apply loaded cookies to httpx client."""
    if _cookies:
        # Build cookie header string
        cookie_str = "; ".join(f"{k}={v}" for k, v in _cookies.items())
        client.headers["Cookie"] = cookie_str
'''

# Insert after close_client function
# Find "def close_client():" block and insert after it
pattern = r'(def close_client\(\):.*?\n    _session = None\n)'
match = re.search(pattern, content, re.DOTALL)
if match:
    insert_pos = match.end()
    content = content[:insert_pos] + insertion + content[insert_pos:]
    print("Cookie functions inserted after close_client()")
else:
    print("ERROR: Could not find close_client()")

# 2. Modify _get_client to call _apply_cookies
content = content.replace(
    "        _session = httpx.Client(\n            timeout=DEFAULT_TIMEOUT,\n            follow_redirects=True,\n            headers={**COMMON_HEADERS, \"User-Agent\": random_ua()},\n            proxy=proxy,\n        )\n    return _session",
    "        _session = httpx.Client(\n            timeout=DEFAULT_TIMEOUT,\n            follow_redirects=True,\n            headers={**COMMON_HEADERS, \"User-Agent\": random_ua()},\n            proxy=proxy,\n        )\n    _apply_cookies(_session)\n    return _session"
)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done!")

# Verify
import ast
with open(path, "r", encoding="utf-8") as f:
    source = f.read()
try:
    compile(source, path, "exec")
    print("Compile OK!")
except SyntaxError as e:
    print(f"SyntaxError at line {e.lineno}: {e.msg}")
