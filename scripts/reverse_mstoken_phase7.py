"""PHASE 7: Hook frontierSign to capture real I/O during search."""
import sys, json, time, urllib.parse
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import BROWSER_NAV_TIMEOUT

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"

browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Test frontierSign with various inputs
print("Testing frontierSign with different inputs...")

test_inputs = [
    ("X-MS-STUB only", '{"X-MS-STUB": "test123"}'),
    ("url only", '{"url": "https://www.douyin.com/aweme/v1/web/search/item/?keyword=test"}'),
    ("full request", '{"X-MS-STUB": "abc", "url": "https://www.douyin.com/aweme/v1/web/search/item/", "method": "GET"}'),
    ("headers map", '{"headers": {"X-MS-STUB": "test"}}'),
]

for name, js_obj in test_inputs:
    try:
        result = page.evaluate(f"""
        () => {{
            try {{
                var r = window.byted_acrawler.frontierSign({js_obj});
                return {{type: typeof r, value: String(r).slice(0, 300)}};
            }} catch(e) {{
                return {{error: e.message.slice(0, 200)}};
            }}
        }}
        """)
        print(f"  {name}: {json.dumps(result, ensure_ascii=False)}")
    except Exception as e:
        print(f"  {name}: EVAL ERROR: {e}")

# Hook frontierSign and trigger real calls
print("\nHooking frontierSign for real calls...")

page.evaluate("""
() => {
    if (!window.__fs_hooked) {
        var orig = window.byted_acrawler.frontierSign;
        window.__fs_calls = [];
        window.byted_acrawler.frontierSign = function() {
            var args = Array.prototype.slice.call(arguments);
            window.__fs_calls.push({
                numArgs: args.length,
                arg0Type: typeof args[0],
                arg0Keys: args[0] ? Object.keys(args[0]).slice(0, 20) : null,
                arg0Str: JSON.stringify(args[0]).slice(0, 800)
            });
            return orig.apply(this, arguments);
        };
        window.__fs_hooked = true;
    }
}
""")

# Navigate to search page to trigger frontierSign
encoded = urllib.parse.quote("test")
page.goto(f"https://www.douyin.com/search/{encoded}?type=general",
          wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

for i in range(3):
    page.evaluate("window.scrollBy(0, 500)")
    time.sleep(2)

calls = page.evaluate("() => window.__fs_calls || []")
print(f"\nCaptured {len(calls)} frontierSign calls during search")

for i, call in enumerate(calls[:5]):
    print(f"\n  Call {i+1}:")
    print(f"    numArgs: {call.get('numArgs')}")
    print(f"    arg0Keys: {call.get('arg0Keys')}")
    print(f"    arg0Str: {call.get('arg0Str', '')[:500]}")

# Also try to call frontierSign with reconstructing the actual input format
if calls:
    call0 = calls[0]
    arg0_str = call0.get("arg0Str", "")
    if arg0_str:
        print(f"\nReplaying first call with captured args...")
        try:
            # Parse the captured args and re-use them
            result = page.evaluate(f"""
            () => {{
                try {{
                    var r = window.byted_acrawler.frontierSign({arg0_str});
                    return {{type: typeof r, value: String(r).slice(0, 300)}};
                }} catch(e) {{
                    return {{error: e.message.slice(0, 200)}};
                }}
            }}
            """)
            print(f"  Result: {json.dumps(result, ensure_ascii=False)}")
        except Exception as e:
            print(f"  Error: {e}")

# Check for X-MS-STUB in document/network
print("\nLooking for X-MS-STUB references...")
xms_info = page.evaluate("""
() => {
    var result = {};
    // Check localStorage
    for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        var val = localStorage.getItem(key);
        if (val && (val.includes('X-MS-STUB') || val.includes('msToken'))) {
            result['ls:' + key] = val.slice(0, 200);
        }
    }
    // Check window globals
    if (window.__MS_STUB__) result.ms_stub_window = String(window.__MS_STUB__).slice(0, 200);
    if (window._msToken) result._msToken = window._msToken.slice(0, 200);
    
    // Check byted_acrawler internals
    var bd = window.byted_acrawler;
    if (bd) {
        result.acrawlerState = {};
        for (var k in bd) {
            try {
                if (typeof bd[k] !== 'function') {
                    result.acrawlerState[k] = String(bd[k]).slice(0, 200);
                }
            } catch(e) {}
        }
    }
    return result;
}
""")
print(json.dumps(xms_info, indent=2, ensure_ascii=False))

page.close()
context.close()
print("\nDone!")
