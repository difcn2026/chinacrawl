"""Fix search_via_xhr _on_response to handle chunked encoding properly."""
import re

path = r"C:\Users\Administrator\Documents\xhls_scraper\chinacrawl\douyin\browser.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the search _on_response: the one with "chunked transfer encoding"
in_search = False
response_start = None
for i, line in enumerate(lines):
    if "def search_via_xhr" in line:
        in_search = True
    elif in_search and "def " in line and "search_via_xhr" not in line and "_on_response" not in line:
        in_search = False
    if in_search and "chunked transfer encoding" in line:
        response_start = i - 2  # go back to "try:" line
        break

if response_start:
    print(f"Found search _on_response at line {response_start}")
    # Print current code
    for j in range(response_start, min(response_start + 12, len(lines))):
        print(f"  {j}: {lines[j].rstrip()}")
    
    # Find the "try:" line and the "except Exception:" line
    try_line = response_start
    except_line = None
    for j in range(response_start, response_start + 15):
        if "except Exception:" in lines[j]:
            except_line = j
            break
    
    if except_line and except_line > try_line:
        # Replace lines try_line through except_line+1 (the return)
        indent = "            "
        new_code = [
            f"{indent}try:\n",
            f"{indent}    # Handle chunked transfer encoding (stream/ endpoint)\n",
            f"{indent}    # Body may look like: 18d9a\\r\\n{{...json...}}\\r\\n0\\r\\n\\r\\n\n",
            f"{indent}    # Extract JSON by finding first {{ and last }}\n",
            f"{indent}    body = response.text()\n",
            f"{indent}    start = body.find('{{')\n",
            f"{indent}    end = body.rfind('}}')\n",
            f"{indent}    if start >= 0 and end > start:\n",
            f"{indent}        data = json.loads(body[start:end+1])\n",
            f"{indent}    else:\n",
            f"{indent}        data = json.loads(body)\n",
            f"{indent}except Exception:\n",
            f"{indent}    return\n",
        ]
        lines[try_line:except_line+2] = new_code
        print("\nReplaced! New code:")
        for j in range(try_line, try_line + len(new_code)):
            print(f"  {j}: {lines[j].rstrip()}")
        
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print("\nFile saved!")
    else:
        print("Couldn't find except line")
else:
    print("search _on_response not found")
