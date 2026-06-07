"""Test msToken extraction from browser and injection into direct API calls."""
import sys, json, time, urllib.parse, os
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

import httpx
from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import API_BASE, API_ENDPOINTS, COMMON_HEADERS, BROWSER_NAV_TIMEOUT, random_ua

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"

print("Launching browser...")
browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

print("Navigating to douyin.com...")
page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(3)

print("Searching for 碎菜机...")
encoded = urllib.parse.quote("碎菜机")
page.goto(f"https://www.douyin.com/search/{encoded}?type=general",
          wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Extract msToken
ms_token = page.evaluate("""
() => {
    var result = {};
    var xmst = localStorage.getItem('xmst');
    result.xmst = xmst;
    result.cookies = document.cookie;
    return result;
}
""")

ms_token_value = ms_token.get("xmst")
cookies_raw = ms_token.get("cookies", "")

print(f"msToken: {ms_token_value[:80] if ms_token_value else 'NOT FOUND'}...")
print(f"Cookies length: {len(cookies_raw)}")

page.close()
context.close()

if not ms_token_value:
    print("ERROR: Could not extract msToken!")
    sys.exit(1)

# ===== Test direct API call with msToken =====
print("\n" + "=" * 60)
print("TESTING: Direct API search with msToken injection")
print("=" * 60)

_BROWSER_PARAMS = (
    "device_platform=webapp&aid=6383&channel=channel_pc_web"
    "&update_version_code=170400&pc_client_type=1"
    "&version_code=190600&version_name=19.6.0"
    "&cookie_enabled=true&screen_width=1920&screen_height=1080"
    "&browser_language=zh-CN&browser_platform=Win32"
    "&browser_name=Chrome&browser_version=131.0.0.0"
    "&browser_online=true&engine_name=Blink&engine_version=131.0.0.0"
    "&os_name=Windows&os_version=10&cpu_core_num=8&device_memory=8&platform=PC"
)

keyword = "碎菜机"
query_params = {
    "keyword": keyword,
    "search_source": "normal_search",
    "search_channel": "aweme_general",
    "enable_history": "1",
    "offset": "0",
    "count": "10",
}

query_str = urllib.parse.urlencode(query_params)
full_query = f"{query_str}&{_BROWSER_PARAMS}"

base_url = f"{API_BASE}{API_ENDPOINTS['search_general']}"
base_headers = {
    **COMMON_HEADERS,
    "User-Agent": random_ua(),
    "Referer": f"{API_BASE}/",
}

# Test 1: Without msToken (baseline)
print("\nTest 1: WITHOUT msToken (baseline - should fail)")
url = f"{base_url}?{full_query}"
headers = {**base_headers, "Cookie": cookies_raw}

with httpx.Client(timeout=15) as client:
    resp = client.get(url, headers=headers)
    print(f"  Status: {resp.status_code}")
    try:
        data = resp.json()
        status_code = data.get("status_code", -1)
        aweme_count = len(data.get("data", []))
        print(f"  status_code: {status_code}, aweme_count: {aweme_count}")
        if aweme_count == 0:
            print(f"  Full: {json.dumps(data, ensure_ascii=False)[:300]}")
        else:
            a = data["data"][0]
            if "aweme_info" in a:
                print(f"  First: [{a['aweme_info'].get('desc', '')[:60]}]")
            elif "user_info" in a:
                print(f"  First: [user: {a['user_info'].get('nickname', '')}]")
    except Exception as e:
        print(f"  Parse error: {e}")
        print(f"  Raw: {resp.text[:200]}")

# Test 2: msToken as cookie
print("\nTest 2: msToken as COOKIE")
headers = {**base_headers, "Cookie": f"{cookies_raw}; msToken={ms_token_value}"}

with httpx.Client(timeout=15) as client:
    resp = client.get(url, headers=headers)
    print(f"  Status: {resp.status_code}")
    try:
        data = resp.json()
        status_code = data.get("status_code", -1)
        aweme_count = len(data.get("data", []))
        print(f"  status_code: {status_code}, aweme_count: {aweme_count}")
        if aweme_count == 0:
            print(f"  Full: {json.dumps(data, ensure_ascii=False)[:300]}")
        else:
            a = data["data"][0]
            if "aweme_info" in a:
                print(f"  First: [{a['aweme_info'].get('desc', '')[:60]}]")
    except Exception as e:
        print(f"  Parse error: {e}")
        print(f"  Raw: {resp.text[:200]}")

# Test 3: msToken as URL parameter
print("\nTest 3: msToken as URL PARAMETER")
url_with_ms = f"{url}&msToken={urllib.parse.quote(ms_token_value)}"
headers = {**base_headers, "Cookie": cookies_raw}

with httpx.Client(timeout=15) as client:
    resp = client.get(url_with_ms, headers=headers)
    print(f"  Status: {resp.status_code}")
    try:
        data = resp.json()
        status_code = data.get("status_code", -1)
        aweme_count = len(data.get("data", []))
        print(f"  status_code: {status_code}, aweme_count: {aweme_count}")
        if aweme_count == 0:
            print(f"  Full: {json.dumps(data, ensure_ascii=False)[:300]}")
        else:
            a = data["data"][0]
            if "aweme_info" in a:
                print(f"  First: [{a['aweme_info'].get('desc', '')[:60]}]")
    except Exception as e:
        print(f"  Parse error: {e}")
        print(f"  Raw: {resp.text[:200]}")

# Test 4: msToken as header
print("\nTest 4: msToken as HEADER (X-MS-Token)")
headers = {**base_headers, "Cookie": cookies_raw, "X-MS-Token": ms_token_value}

with httpx.Client(timeout=15) as client:
    resp = client.get(url, headers=headers)
    print(f"  Status: {resp.status_code}")
    try:
        data = resp.json()
        status_code = data.get("status_code", -1)
        aweme_count = len(data.get("data", []))
        print(f"  status_code: {status_code}, aweme_count: {aweme_count}")
        if aweme_count == 0:
            print(f"  Full: {json.dumps(data, ensure_ascii=False)[:300]}")
        else:
            a = data["data"][0]
            if "aweme_info" in a:
                print(f"  First: [{a['aweme_info'].get('desc', '')[:60]}]")
    except Exception as e:
        print(f"  Parse error: {e}")
        print(f"  Raw: {resp.text[:200]}")

# Test 5: Add X-Bogus signing too (like browser does)
print("\nTest 5: msToken as COOKIE + X-Bogus")

# Generate X-Bogus via Node.js bridge
_XBOGUS_BRIDGE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "scripts", "xbogus_bridge.js")
if not os.path.exists(_XBOGUS_BRIDGE):
    _XBOGUS_BRIDGE = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "xbogus_bridge.js")

xbogus = None
try:
    import subprocess
    result = subprocess.run(
        ["node", _XBOGUS_BRIDGE, full_query, random_ua()],
        capture_output=True, text=True, timeout=10,
        cwd=os.path.dirname(_XBOGUS_BRIDGE)
    )
    if result.returncode == 0 and result.stdout.strip():
        xbogus = result.stdout.strip()
        print(f"  X-Bogus generated: {xbogus[:40]}...")
except Exception as e:
    print(f"  X-Bogus failed: {e}")

if xbogus:
    url_with_xb = f"{url}&X-Bogus={urllib.parse.quote(xbogus, safe='')}"
    headers = {**base_headers, "Cookie": f"{cookies_raw}; msToken={ms_token_value}"}
    
    with httpx.Client(timeout=15) as client:
        resp = client.get(url_with_xb, headers=headers)
        print(f"  Status: {resp.status_code}")
        try:
            data = resp.json()
            status_code = data.get("status_code", -1)
            aweme_count = len(data.get("data", []))
            print(f"  status_code: {status_code}, aweme_count: {aweme_count}")
            if aweme_count == 0:
                print(f"  Full: {json.dumps(data, ensure_ascii=False)[:300]}")
            else:
                a = data["data"][0]
                if "aweme_info" in a:
                    print(f"  First: [{a['aweme_info'].get('desc', '')[:60]}]")
                print(f"  SUCCESS! {aweme_count} results!")
        except Exception as e:
            print(f"  Parse error: {e}")
            print(f"  Raw: {resp.text[:200]}")
else:
    print("  Skipped (no X-Bogus)")

print("\nDone!")
