"""PHASE 8: Get frontierSign result details and trace msToken generation."""
import sys, json, time
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import BROWSER_NAV_TIMEOUT

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"

browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Test 1: what does frontierSign return?
print("=== Test 1: frontierSign return value ===")
result = page.evaluate("""
() => {
    var r = window.byted_acrawler.frontierSign({"X-MS-STUB": "test123"});
    // Deep inspect
    var info = {};
    info.type = typeof r;
    info.keys = Object.keys(r);
    info.prototype = Object.prototype.toString.call(r);
    info.constructor = r.constructor ? r.constructor.name : 'none';
    
    // Try to stringify
    try {
        info.json = JSON.stringify(r);
    } catch(e) {
        info.json = 'NOT SERIALIZABLE: ' + e.message;
    }
    
    // Check for msToken in result
    if (r.msToken) info.msToken = r.msToken.slice(0, 80);
    if (r.token) info.token = r.token.slice(0, 80);
    
    // Check all enumerable properties
    info.props = {};
    for (var k in r) {
        try {
            info.props[k] = String(r[k]).slice(0, 200);
        } catch(e) {
            info.props[k] = 'ERROR: ' + e.message;
        }
    }
    
    return info;
}
""")
print(json.dumps(result, indent=2, ensure_ascii=False))

# Test 2: Does frontierSign store result in localStorage?
print("\n=== Test 2: Check localStorage after frontierSign ===")
xmst_before = page.evaluate("() => localStorage.getItem('xmst')")
print(f"xmst before: {xmst_before}")

# Call frontierSign with a proper-looking request stub
page.evaluate("""
() => {
    window.byted_acrawler.frontierSign({
        "X-MS-STUB": "AB2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6a7b8c9d0e1f2",
        "url": "https://www.douyin.com/aweme/v1/web/search/item/?keyword=test"
    });
}
""")
time.sleep(1)
xmst_after = page.evaluate("() => localStorage.getItem('xmst')")
print(f"xmst after: {xmst_after[:100] if xmst_after else 'NOT SET'}")

# Test 3: What about the init() function?
print("\n=== Test 3: SDK init() ===")
# The init function takes a config object
init_result = page.evaluate("""
() => {
    try {
        var r = window.byted_acrawler.init({"url": "https://www.douyin.com/"});
        return {type: typeof r, keys: Object.keys(r || {}), json: JSON.stringify(r).slice(0, 300)};
    } catch(e) {
        return {error: e.message.slice(0, 200)};
    }
}
""")
print(json.dumps(init_result, indent=2, ensure_ascii=False))

# Test 4: Check the web_secsdk_runtime_cache after frontierSign
print("\n=== Test 4: web_secsdk_runtime_cache ===")
cache = page.evaluate("""
() => {
    var raw = localStorage.getItem('web_secsdk_runtime_cache');
    if (raw) {
        try {
            var parsed = JSON.parse(raw);
            return {keys: Object.keys(parsed), webSign: parsed.webSign, csrfWebToken: parsed.csrfWebToken};
        } catch(e) {
            return {raw: raw.slice(0, 500)};
        }
    }
    return null;
}
""")
print(json.dumps(cache, indent=2, ensure_ascii=False))

# Test 5: Trace msToken flow - navigate to search to see what happens
print("\n=== Test 5: Navigate to search, trace msToken flow ===")

# Hook localStorage.setItem to see when xmst is set
page.evaluate("""
() => {
    var orig = localStorage.setItem;
    window.__ls_trace = [];
    localStorage.setItem = function(key, value) {
        if (key === 'xmst' || key.includes('ms') || key.includes('token')) {
            window.__ls_trace.push({key: key, value: value.slice(0, 80), time: Date.now(), stack: new Error().stack.slice(0, 300)});
        }
        return orig.apply(this, arguments);
    };
}
""")

# Navigate to search
import urllib.parse
encoded = urllib.parse.quote("人工智能")
page.goto(f"https://www.douyin.com/search/{encoded}?type=general",
          wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Scroll
for i in range(3):
    page.evaluate("window.scrollBy(0, 500)")
    time.sleep(2)

traces = page.evaluate("() => window.__ls_trace || []")
print(f"\nlocalStorage setItem traces for msToken keys: {len(traces)}")
for t in traces[:10]:
    print(f"  {t.get('key')}: {t.get('value', '')[:80]}")
    if "stack" in t:
        # Show first few lines of stack
        stack_lines = t["stack"].split("\n")[:5]
        for sl in stack_lines:
            print(f"    {sl.strip()[:120]}")

# Check final xmst
xmst_final = page.evaluate("() => localStorage.getItem('xmst')")
print(f"\nFinal xmst: {xmst_final[:100] if xmst_final else 'NOT SET'}")

page.close()
context.close()
print("\nDone!")
