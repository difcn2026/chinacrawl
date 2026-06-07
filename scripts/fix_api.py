"""Fix the broken double-quote patterns in api.py _get() method."""
import re

path = r"C:\Users\Administrator\Documents\xhls_scraper\chinacrawl\douyin\api.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Print the problematic lines for debugging
for i, line in enumerate(content.split("\n"), 1):
    if '""' in line and ("urllib" in line or '""&""' in line or '""? ""' in line or 'safe=""' in line):
        print(f"L{i}: {repr(line)}")

# Fixes
original_content = content

# Fix __import__(""urllib.parse"") -> urllib.parse.urlparse (already imported at top)
content = content.replace('__import__(""urllib.parse"")', "urllib.parse")

# Fix ""&"" -> "&"
content = content.replace('""&""', '"&"')

# Fix ""&X-Bogus="" -> "&X-Bogus="
content = content.replace('""&X-Bogus=""', '"&X-Bogus="')

# Fix safe="""" -> safe=""
content = content.replace('safe=""""', 'safe=""')

# Fix + ""?"" + -> + "?" +
content = content.replace('""?""', '"?"')

if content != original_content:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("\nFIXED!")
else:
    print("\nNo changes needed")
