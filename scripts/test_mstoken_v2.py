"""Test: Extract msToken from browser and test with X-Bogus + msToken cookie."""
import sys, json, time, urllib.parse, os, subprocess
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

import httpx
from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import API_BASE, API_ENDPOINTS, COMMON_HEADERS, random_ua, BROWSER_NAV_TIMEOUT
from chinacrawl.douyin.api import load_cookies

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"

# Step 1: Extract fresh msToken from browser
print("Extracting msToken from browser...")
browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(3)

encoded = urllib.parse.quote("碎菜机")
page.goto(f"https://www.douyin.com/search/{encoded}?type=general",
          wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Scroll to trigger more API calls (SDK generates msToken during API requests)
print("Scrolling to trigger API calls...")
for i in range(5):
    page.evaluate("window.scrollBy(0, 800)")
    time.sleep(2)
    xmst_now = page.evaluate("() => localStorage.getItem('xmst')")
    if xmst_now:
        print(f"  xmst appeared after {i+1} scrolls!")
        break

# Check all localStorage keys
ls_keys = page.evaluate("""() => {
    var keys = [];
    for (var i = 0; i < localStorage.length; i++) {
        keys.push(localStorage.key(i));
    }
    return keys;
}""")
print(f"localStorage keys after search+scroll: {len(ls_keys)}")
for k in ls_keys:
    if "ms" in k.lower() or "xmst" in k.lower() or "token" in k.lower():
        val = page.evaluate(f"() => localStorage.getItem('{k}')")
        print(f"  {k}: {(val[:80] + '...') if val and len(val) > 80 else val}")

ms_token = page.evaluate("() => localStorage.getItem('xmst')")
cookies_raw = page.evaluate("() => document.cookie")
print(f"\nmsToken: {(ms_token[:60] + '...') if ms_token else 'NOT FOUND'}")

page.close()
context.close()

if not ms_token:
    print("ERROR: Could not extract msToken!")
    sys.exit(1)

# Step 2: Test with X-Bogus + msToken cookie
print("\n" + "=" * 60)
print("Testing with X-Bogus + msToken cookie...")
print("=" * 60)
load_cookies(COOKIE_FILE)

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
query_str = (
    f"keyword={urllib.parse.quote(keyword)}"
    "&search_source=normal_search"
    "&search_channel=aweme_general"
    "&enable_history=1"
    "&offset=0"
    "&count=10"
)
full_query = f"{query_str}&{_BROWSER_PARAMS}"

_XBOGUS_BRIDGE = r"C:\Users\Administrator\Documents\xhls_scraper\scripts\xbogus_bridge.js"
ua = random_ua()

result = subprocess.run(
    ["node", _XBOGUS_BRIDGE, full_query, ua],
    capture_output=True, text=True, timeout=10,
    cwd=os.path.dirname(_XBOGUS_BRIDGE)
)
xbogus = result.stdout.strip() if result.returncode == 0 else None

endpoint = API_ENDPOINTS["search_general"]
url = (
    f"{API_BASE}{endpoint}?{full_query}"
    f"&X-Bogus={urllib.parse.quote(xbogus, safe='')}"
)

from chinacrawl.douyin.api import _get_client, _get_headers, _apply_cookies

client = _get_client()
_apply_cookies(client)
headers = _get_headers(referer=API_BASE + "/")
headers["User-Agent"] = ua

# Add msToken to cookies
existing_cookies = client.headers.get("Cookie", "")
headers["Cookie"] = f"{existing_cookies}; msToken={ms_token}"

print(f"  URL: {url[:120]}")
resp = client.get(url, headers=headers)
print(f"  Status: {resp.status_code}")

data = resp.json()
print(f"  status_code: {data.get('status_code')}")
print(f"  aweme_list: {data.get('aweme_list')}")
if data.get("search_nil_info"):
    print(f"  search_nil_info: {json.dumps(data['search_nil_info'], ensure_ascii=False)}")
if data.get("data"):
    print(f"  data count: {len(data['data'])}")
    for item in data["data"][:3]:
        if "aweme_info" in item:
            print(f"    [{item['aweme_info'].get('aweme_id')}] {item['aweme_info'].get('desc', '')[:60]}")

print("\nDone!")
