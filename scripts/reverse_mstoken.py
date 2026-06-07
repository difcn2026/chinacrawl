"""
Deep Dive: Extract and analyze byted_acrawler SDK for msToken reverse engineering.

Strategy:
  1. Navigate to douyin.com to load the security SDK
  2. Extract byted_acrawler source from <script> tags
  3. Hook byted_acrawler.sign() to capture I/O
  4. Trace msToken generation pipeline
  5. Save everything for offline analysis
"""
import sys, json, time, urllib.parse, os, re, base64
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import BROWSER_NAV_TIMEOUT

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"
OUTPUT_DIR = r"C:\Users\Administrator\Documents\New project\knowledge\security\douyin-sdk"

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("PHASE 1: Extract byted_acrawler SDK source")
print("=" * 60)

browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

# Intercept ALL script requests to capture the SDK source
sdk_scripts = []

def on_response(response):
    if response.request.resource_type == "script":
        url = response.url
        if any(kw in url for kw in ["secsdk", "acrawler", "webmssdk", "security", "byted"]):
            try:
                body = response.text()
                sdk_scripts.append({"url": url, "size": len(body), "body": body})
                print(f"  Captured SDK script: {url} ({len(body)} bytes)")
            except:
                pass

page.on("response", on_response)

page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Navigate to search to trigger msToken generation
encoded = urllib.parse.quote("碎菜机")
page.goto(f"https://www.douyin.com/search/{encoded}?type=general",
          wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Scroll to trigger more API calls
for i in range(3):
    page.evaluate("window.scrollBy(0, 500)")
    time.sleep(2)

print(f"\nTotal SDK scripts captured: {len(sdk_scripts)}")
for s in sdk_scripts:
    print(f"  {s['url'][:100]} -> {s['size']} bytes")

# Save SDK scripts
for i, s in enumerate(sdk_scripts):
    # Extract filename from URL
    fname = os.path.basename(urllib.parse.urlparse(s["url"]).path) or f"sdk_script_{i}.js"
    fpath = os.path.join(OUTPUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(s["body"])
    print(f"  Saved: {fpath}")

# ================================================================
# PHASE 2: Analyze byted_acrawler API surface
# ================================================================
print("\n" + "=" * 60)
print("PHASE 2: Analyze byted_acrawler API surface")
print("=" * 60)

acrawler_info = page.evaluate("""
() => {
    var result = {};
    var bd = window.byted_acrawler;
    if (!bd) return {error: 'byted_acrawler not found'};
    
    result.type = typeof bd;
    
    // Enumerate all properties
    result.keys = Object.keys(bd);
    result.ownKeys = Object.getOwnPropertyNames(bd);
    
    // Try to get prototype methods
    try {
        result.protoKeys = Object.getOwnPropertyNames(Object.getPrototypeOf(bd));
    } catch(e) {
        result.protoKeys = ['error: ' + e.message];
    }
    
    // Check for sign function
    result.hasSign = typeof bd.sign === 'function';
    result.hasInit = typeof bd.init === 'function';
    
    // Get sign.toString() (function signature reveal)
    if (result.hasSign) {
        try {
            result.signToString = bd.sign.toString().slice(0, 500);
        } catch(e) {
            result.signToString = 'error: ' + e.message;
        }
    }
    
    // Enumerate all methods
    result.methods = [];
    for (var k in bd) {
        if (typeof bd[k] === 'function') {
            try {
                result.methods.push(k + ': ' + bd[k].toString().slice(0, 200));
            } catch(e) {
                result.methods.push(k + ': [native code]');
            }
        }
    }
    
    return result;
}
""")

print(f"byted_acrawler type: {acrawler_info.get('type')}")
print(f"Keys: {acrawler_info.get('keys', [])}")
print(f"Proto keys: {acrawler_info.get('protoKeys', [])}")
print(f"hasSign: {acrawler_info.get('hasSign')}")
print(f"hasInit: {acrawler_info.get('hasInit')}")

if acrawler_info.get("signToString"):
    print(f"\nsign.toString():")
    print(acrawler_info["signToString"][:500])

if acrawler_info.get("methods"):
    print(f"\nMethods:")
    for m in acrawler_info["methods"]:
        print(f"  {m}")

# ================================================================
# PHASE 3: Hook byted_acrawler.sign() to capture I/O
# ================================================================
print("\n" + "=" * 60)
print("PHASE 3: Hook byted_acrawler.sign() calls")
print("=" * 60)

sign_calls = []

# Inject hook script
page.evaluate("""
() => {
    if (!window.byted_acrawler || !window.byted_acrawler.sign) return;
    
    var originalSign = window.byted_acrawler.sign;
    window.__sign_calls = [];
    
    window.byted_acrawler.sign = function() {
        var args = Array.prototype.slice.call(arguments);
        var result = originalSign.apply(this, arguments);
        window.__sign_calls.push({
            args: args.map(function(a) {
                if (typeof a === 'string') return a.slice(0, 200);
                if (typeof a === 'object') return JSON.stringify(a).slice(0, 200);
                return String(a).slice(0, 200);
            }),
            result: typeof result === 'string' ? result.slice(0, 200) : String(result).slice(0, 200),
            resultType: typeof result,
            time: Date.now()
        });
        return result;
    };
}
""")

# Trigger a search to force sign() calls
print("Triggering search to generate sign calls...")
encoded = urllib.parse.quote("人工智能")
page.goto(f"https://www.douyin.com/search/{encoded}?type=general",
          wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Scroll
for i in range(3):
    page.evaluate("window.scrollBy(0, 500)")
    time.sleep(2)

# Collect sign calls
collected_calls = page.evaluate("() => window.__sign_calls || []")
print(f"\nCaptured {len(collected_calls)} sign() calls")

for i, call in enumerate(collected_calls[:10]):
    print(f"\n  Call {i+1}:")
    print(f"    resultType: {call.get('resultType')}")
    print(f"    result[:100]: {call.get('result', '')[:100]}")
    for j, arg in enumerate(call.get("args", [])):
        print(f"    arg[{j}]: {arg[:120]}")

# Save sign calls
with open(os.path.join(OUTPUT_DIR, "sign_calls.json"), "w", encoding="utf-8") as f:
    json.dump(collected_calls, f, ensure_ascii=False, indent=2)
print(f"\nSaved {len(collected_calls)} sign calls to sign_calls.json")

# ================================================================
# PHASE 4: Full runtime state dump
# ================================================================
print("\n" + "=" * 60)
print("PHASE 4: Full runtime state dump")
print("=" * 60)

runtime_dump = page.evaluate("""
() => {
    var dump = {};
    
    // localStorage
    dump.localStorage = {};
    for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        var val = localStorage.getItem(key);
        dump.localStorage[key] = val.slice(0, 500);
    }
    
    // sessionStorage
    dump.sessionStorage = {};
     for (var i = 0; i < sessionStorage.length; i++) {
        var key = sessionStorage.key(i);
        var val = sessionStorage.getItem(key);
        dump.sessionStorage[key] = val.slice(0, 500);
    }
    
    // byted_acrawler internals
    dump.acrawlerInternals = {};
    if (window.byted_acrawler) {
        for (var k in window.byted_acrawler) {
            if (typeof window.byted_acrawler[k] !== 'function') {
                try {
                    dump.acrawlerInternals[k] = JSON.stringify(window.byted_acrawler[k]).slice(0, 500);
                } catch(e) {
                    dump.acrawlerInternals[k] = String(window.byted_acrawler[k]).slice(0, 500);
                }
            }
        }
    }
    
    // bdms
    dump.bdmsInfo = {};
    if (window.bdms) {
        dump.bdmsInfo.type = typeof window.bdms;
        dump.bdmsInfo.keys = Object.keys(window.bdms);
    }
    
    return dump;
}
""")

with open(os.path.join(OUTPUT_DIR, "runtime_dump.json"), "w", encoding="utf-8") as f:
    json.dump(runtime_dump, f, ensure_ascii=False, indent=2)
print(f"Saved runtime dump to runtime_dump.json")

# ================================================================
# PHASE 5: Extract msToken + related runtime values
# ================================================================
print("\n" + "=" * 60)
print("PHASE 5: msToken extraction context")
print("=" * 60)

mstoken_context = page.evaluate("""
() => {
    var ctx = {};
    ctx.msToken = localStorage.getItem('xmst');
    ctx.web_secsdk_runtime_cache = localStorage.getItem('web_secsdk_runtime_cache');
    ctx.SLARDARdouyin_web = localStorage.getItem('SLARDARdouyin_web');
    ctx.msuuid = localStorage.getItem('__msuuid__');
    ctx.userAgent = navigator.userAgent;
    ctx.platform = navigator.platform;
    
    // Decode web_secsdk_runtime_cache
    try {
        var cache = JSON.parse(ctx.web_secsdk_runtime_cache);
        ctx.cacheParsed = cache;
    } catch(e) {}
    
    // Decode SLARDAR
    try {
        var slardar = ctx.SLARDARdouyin_web;
        if (slardar) {
            ctx.slardarDecoded = JSON.parse(decodeURIComponent(atob(slardar)));
        }
    } catch(e) {}
    
    return ctx;
}
""")

print(f"msToken: {(mstoken_context.get('msToken') or 'NOT FOUND')[:80]}")
print(f"msuuid: {mstoken_context.get('msuuid')}")
print(f"UA: {mstoken_context.get('userAgent')[:80]}")

if mstoken_context.get("cacheParsed"):
    cache = mstoken_context["cacheParsed"]
    print(f"\nweb_secsdk_runtime_cache keys: {list(cache.keys())}")
    for k, v in cache.items():
        print(f"  {k}: {str(v)[:120]}")

if mstoken_context.get("slardarDecoded"):
    print(f"\nSLARDAR decoded: {json.dumps(mstoken_context['slardarDecoded'], indent=2)}")

with open(os.path.join(OUTPUT_DIR, "mstoken_context.json"), "w", encoding="utf-8") as f:
    json.dump(mstoken_context, f, ensure_ascii=False, indent=2)
print(f"\nSaved msToken context to mstoken_context.json")

page.close()
context.close()

print("\n" + "=" * 60)
print(f"All artifacts saved to: {OUTPUT_DIR}")
print("=" * 60)
print("\nNext: Analyze SDK source for msToken generation algorithm")
