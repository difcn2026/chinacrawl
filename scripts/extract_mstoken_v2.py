"""Extract msToken from browser XHR interception for direct API use.

Strategy:
  1. Launch browser with existing cookies
  2. Navigate to douyin.com to initialize security SDK
  3. Intercept ALL XHR requests to douyin API
  4. Navigate to a search page to trigger search requests
  5. Capture the full URL including msToken parameter
  6. Extract msToken for reuse in direct API calls
  7. Test: use extracted msToken in a direct httpx call
"""
import sys, json, time, urllib.parse, re, base64
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import BROWSER_NAV_TIMEOUT

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"

browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

# --- Step 1: Navigate to douyin.com first to get document access ---
print("=" * 60)
print("STEP 1: Navigate to douyin.com to initialize SDK")
print("=" * 60)

page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(3)

# --- Step 2: Extract security SDK runtime data ---
print("\n" + "=" * 60)
print("STEP 2: Extract security SDK runtime data")
print("=" * 60)

runtime_data = page.evaluate("""
() => {
    var result = {};
    
    // web_secsdk_runtime_cache
    try {
        var cache = localStorage.getItem('web_secsdk_runtime_cache');
        if (cache) {
            result.web_secsdk_runtime_cache = JSON.parse(cache);
        }
    } catch(e) {}
    
    // SLARDARdouyin_web (Base64)
    try {
        var slardar = localStorage.getItem('SLARDARdouyin_web');
        if (slardar) {
            var decoded = decodeURIComponent(atob(slardar));
            result.SLARDARdouyin_web_decoded = JSON.parse(decoded);
        }
    } catch(e) {}
    
    // Check window globals for security SDK
    result.window_keys = [];
    for (var k in window) {
        if (k.toLowerCase().indexOf('sec') >= 0 || 
            k.toLowerCase().indexOf('sign') >= 0 ||
            k.toLowerCase().indexOf('byted') >= 0 ||
            k.toLowerCase().indexOf('acrawler') >= 0 ||
            k.toLowerCase().indexOf('bdms') >= 0 ||
            k.toLowerCase().indexOf('xmst') >= 0) {
            result.window_keys.push(k);
        }
    }
    
    // Check document cookies (skip if not accessible)
    result.cookies_with_ms = [];
    try {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var c = cookies[i].trim();
            if (c.toLowerCase().indexOf('ms') >= 0 || 
                c.toLowerCase().indexOf('token') >= 0) {
                result.cookies_with_ms.push(c.slice(0, 100));
            }
        }
    } catch(e) {
        result.cookies_error = e.message;
    }
    
    return result;
}
""")

print(f"window security keys: {runtime_data.get('window_keys', [])}")
cookies_with_ms = runtime_data.get('cookies_with_ms', [])
cookies_error = runtime_data.get('cookies_error', '')
if cookies_error:
    print(f"cookie access error: {cookies_error}")
print(f"cookies with ms/token: {cookies_with_ms}")

if 'web_secsdk_runtime_cache' in runtime_data:
    ws = runtime_data['web_secsdk_runtime_cache']
    if isinstance(ws, dict):
        print(f"\nweb_secsdk_runtime_cache keys: {list(ws.keys())}")
        if 'webSign' in ws:
            signs = ws['webSign']
            print(f"webSign entries: {len(signs) if isinstance(signs, list) else 'not a list'}")
            if isinstance(signs, list):
                for s in signs[:3]:
                    print(f"  {str(s)[:120]}")

if 'SLARDARdouyin_web_decoded' in runtime_data:
    print(f"\nSLARDARdouyin_web decoded: {json.dumps(runtime_data['SLARDARdouyin_web_decoded'], indent=2, ensure_ascii=False)[:500]}")

# --- Step 3: Setup XHR interception + navigate to search ---
print("\n" + "=" * 60)
print("STEP 3: Intercept search XHR to capture msToken")
print("=" * 60)

captured_urls = []

def on_request(request):
    url = request.url
    if '/aweme/v1/web/' in url or '/aweme/v1/web/discover/' in url:
        captured_urls.append({
            'url': url,
            'method': request.method,
            'headers': dict(request.headers),
        })

page.on('request', on_request)

# Also capture responses for debugging
captured_responses = []

def on_response(response):
    url = response.url
    if '/aweme/v1/web/' in url or '/aweme/v1/web/discover/' in url:
        try:
            body = response.text()
        except:
            body = "<binary or unavailable>"
        captured_responses.append({
            'url': url,
            'status': response.status,
            'body_preview': body[:300] if body else "<empty>",
        })

page.on('response', on_response)

# Navigate to search page
search_keyword = "碎菜机"
encoded = urllib.parse.quote(search_keyword)
page.goto(f"https://www.douyin.com/search/{encoded}?type=general", 
          wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Scroll to trigger more requests
for i in range(3):
    page.evaluate("window.scrollBy(0, 500)")
    time.sleep(2)

print(f"\nCaptured {len(captured_urls)} API requests and {len(captured_responses)} responses")

# --- Step 4: Analyze captured requests for msToken ---
print("\n" + "=" * 60)
print("STEP 4: Analyze captured data for msToken")
print("=" * 60)

ms_token = None
ms_token_params = {}

for req in captured_urls:
    url = req['url']
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)
    
    if 'msToken' in params:
        ms_token = params['msToken'][0]
        print(f"\nFOUND msToken in URL!")
        print(f"  msToken: {ms_token}")
        
        # Show all interesting params
        for k, v in params.items():
            if k not in ['device_platform', 'screen_width', 'screen_height', 'cpu_core_num', 
                         'device_memory', 'browser_name', 'browser_version', 'os_name', 'os_version',
                         'browser_language', 'browser_online', 'browser_platform', 'channel',
                         'cookie_enabled', 'engine_name', 'engine_version']:
                print(f"  {k}: {v[0][:80]}")
        ms_token_params = {k: v[0] for k, v in params.items()}
        break

# Also check the search responses
print(f"\nSearch responses:")
for resp in captured_responses:
    if 'search' in resp['url'] or 'discover' in resp['url']:
        print(f"  [{resp['status']}] {resp['url'][:150]}")
        print(f"    Body preview: {resp['body_preview'][:200]}")

# --- Step 5: Extract msToken from runtime after search ---
if not ms_token:
    print("\nNo msToken in URL params. Checking runtime...")
    
    ms_from_runtime = page.evaluate("""
    () => {
        // Check all possible msToken locations
        var results = {};
        try {
            // method 1: localStorage xmst
            results.xmst = localStorage.getItem('xmst');
        } catch(e) {}
        try {
            // method 2: window._msToken
            results._msToken = window._msToken || null;
        } catch(e) {}
        try {
            // method 3: extract from web_secsdk_runtime_cache
            var cache = localStorage.getItem('web_secsdk_runtime_cache');
            if (cache) {
                var parsed = JSON.parse(cache);
                results.cache_keys = Object.keys(parsed);
                // look for msToken in any stringified value
                var cacheStr = JSON.stringify(parsed);
                var idx = cacheStr.indexOf('msToken');
                if (idx >= 0) {
                    results.cache_has_msToken = true;
                    results.cache_snippet = cacheStr.slice(Math.max(0, idx - 20), idx + 80);
                }
            }
        } catch(e) {}
        try {
            // method 4: check all localStorage keys
            results.ls_keys = [];
            for (var i = 0; i < localStorage.length; i++) {
                var key = localStorage.key(i);
                if (key && key.toLowerCase().indexOf('ms') >= 0) {
                    results.ls_keys.push(key + '=' + localStorage.getItem(key).slice(0, 60));
                }
            }
        } catch(e) {}
        return JSON.stringify(results);
    }
    """)
    print(f"Runtime after search: {ms_from_runtime[:800]}")
else:
    print(f"\nSUCCESS: msToken captured!")

# --- Final: Save msToken ---
if ms_token:
    print("\n" + "=" * 60)
    print("STEP 5: Save and test msToken")
    print("=" * 60)
    
    # Save msToken for reuse
    ms_token_data = {
        'msToken': ms_token,
        'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'search_keyword': search_keyword,
        'msToken_source': 'XHR interception',
        'full_params': ms_token_params,
    }
    
    output_file = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_mstoken.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(ms_token_data, f, ensure_ascii=False, indent=2)
    print(f"msToken saved to: {output_file}")
    
    # Also print all search params for reference
    print(f"\nFull API params for search request:")
    for k, v in ms_token_params.items():
        print(f"  {k}: {v}")
else:
    print("\n" + "=" * 60)
    print("msToken NOT FOUND in any captured request")
    print("=" * 60)
    
    # Dump ALL captured URLs for debugging
    print(f"\nAll captured API URLs ({len(captured_urls)}):")
    for req in captured_urls[:15]:
        print(f"  {req['method']} {req['url'][:200]}")
    
    print(f"\nAll captured responses ({len(captured_responses)}):")
    for resp in captured_responses[:10]:
        print(f"  [{resp['status']}] {resp['url'][:150]}")

page.close()
context.close()
print("\nDone!")
