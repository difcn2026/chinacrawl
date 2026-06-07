"""Fix the broken _on_response in search_via_xhr (manual fix for wrong offset)."""
import re

path = r"C:\Users\Administrator\Documents\xhls_scraper\chinacrawl\douyin\browser.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# The broken code (after bad fix):
broken = """        if response.status != 200:
            try:
                # Handle chunked transfer encoding (stream/ endpoint)
                # Body may look like: 18d9a\\r\\n{...json...}\\r\\n0\\r\\n\\r\\n
                # Extract JSON by finding first { and last }
                body = response.text()
                start = body.find('{')
                end = body.rfind('}')
                if start >= 0 and end > start:
                    data = json.loads(body[start:end+1])
                else:
                    data = json.loads(body)
            except Exception:
                return"""

fixed = """        if response.status != 200:
            return
        try:
            # Handle chunked transfer encoding (stream/ endpoint)
            # Body may look like: 18d9a\\r\\n{...json...}\\r\\n0\\r\\n\\r\\n
            # Extract JSON by finding first { and last }
            body = response.text()
            start = body.find('{')
            end = body.rfind('}')
            if start >= 0 and end > start:
                data = json.loads(body[start:end+1])
            else:
                data = json.loads(body)
        except Exception:
            return"""

# Use a more flexible match (handle varying whitespace)
import re as _re
# Find the pattern in the file
pattern = r'if response\.status != 200:\s+try:'
match = _re.search(pattern, content)
if match:
    # Find the block end
    block_start = match.start()
    # Find "except Exception:\n            return"
    except_match = _re.search(r'except Exception:\s+return', content[block_start:])
    if except_match:
        block_end = block_start + except_match.end()
        old_block_content = content[block_start:block_end]
        print(f"Found broken block ({len(old_block_content)} chars):")
        print(old_block_content[:300])
        
        content = content[:block_start] + fixed + content[block_end:]
        print("\nReplaced with:")
        print(fixed[:300])
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("\nDone!")
    else:
        print("Could not find except/return pattern")
else:
    print("Pattern not found")
