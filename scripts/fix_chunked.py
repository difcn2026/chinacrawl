"""Fix chunked encoding parsing in search_via_xhr."""
import re

path = r"C:\Users\Administrator\Documents\xhls_scraper\chinacrawl\douyin\browser.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix: strip all chunk headers (not just the first one with ^)
old_pattern = r"body = re\.sub\(r'\^\[0-9a-fA-F\]\+\\\\r\?\\\\n', '', body\)"
new_code = "body = re.sub(r'[0-9a-fA-F]+\\r?\\n', '', body).strip()  # strip ALL chunk headers"

if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_code, content)
    print("Replaced!")
else:
    print("Pattern not found as-is, trying simpler find...")
    # Try finding just "body = re.sub"
    idx = content.find("body = re.sub")
    if idx >= 0:
        end = content.find("\n", idx)
        print(f"Found at {idx}: {repr(content[idx:end])}")
        
        # Replace the line
        old_line = content[idx:end]
        content = content.replace(old_line, new_code)
        print("Replaced via line match!")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
