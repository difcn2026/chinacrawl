"""
PHASE 6: Capture the encrypted bytecode passed to webmssdk.
Hook the _$webrt_1668687510 call to capture all 3 parameters.
"""
import sys, json, time, os
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import BROWSER_NAV_TIMEOUT

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"
OUTPUT_DIR = r"C:\Users\Administrator\Documents\New project\knowledge\security\douyin-sdk"

print("=" * 60)
print("PHASE 6: Capture webmssdk bytecode")
print("=" * 60)

browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

# Hook the SDK call BEFORE any SDK scripts load
# We need to intercept the call to _$webrt_1668687510
# But since scripts load before we can hook, let's use a different approach:
# After page loads, extract the bytecode from the SDK's internal state

page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(5)

# Extract the SDK's internal string table (the bytecode)
# The SDK stores the decoded string table internally
bytecode_info = page.evaluate("""
() => {
    var result = {};
    var sdk = window._$webrt_1668687510;
    if (!sdk) return {error: 'SDK not on window'};
    
    // The SDK stores the string table in a closure variable
    // Let's try to access internal state through the exported API
    result.sdkType = typeof sdk;
    result.sdkKeys = Object.keys(sdk);
    
    // Check for the SDK's module system
    if (window._SdkGlueInit) {
        result.hasGlue = true;
    }
    
    // Check for webpack modules
    if (window.webpackJsonp) {
        result.hasWebpack = true;
    }
    
    // The SDK exposes frontSign, init, etc. through the glue
    // Let's check if byted_acrawler has the sign function
    var bd = window.byted_acrawler;
    if (bd) {
        result.acrawlerKeys = Object.keys(bd);
        if (bd.sign) {
            result.hasSign = true;
        }
        if (bd.frontierSign) {
            result.hasFrontierSign = true;
        }
    }
    
    // Check for webmssdk global
    if (window._webmssdk) {
        result.hasWebmssdkGlobal = true;
        result.webmssdkKeys = Object.keys(window._webmssdk);
    }
    
    // Check window for any object with frontierSign
    for (var k in window) {
        try {
            if (window[k] && typeof window[k] === 'object' && window[k].frontierSign) {
                result.frontierSignOwner = k;
                result.frontierSignType = typeof window[k].frontierSign;
                break;
            }
        } catch(e) {}
    }
    
    return result;
}
""")

print(f"SDK state: {json.dumps(bytecode_info, indent=2, ensure_ascii=False)}")

# Try to call frontierSign if found
if bytecode_info.get("frontierSignOwner"):
    owner_name = bytecode_info["frontierSignOwner"]
    print(f"\nCalling {owner_name}.frontierSign()...")
    
    sign_result = page.evaluate(f"""
    () => {{
        try {{
            var result = window['{owner_name}'].frontierSign();
            return {{
                type: typeof result,
                value: String(result).slice(0, 200)
            }};
        }} catch(e) {{
            return {{error: e.message}};
        }}
    }}
    """)
    print(f"frontierSign result: {json.dumps(sign_result, ensure_ascii=False)}")

# Now search for the actual bytecode array
# The bytecode is passed to the SDK function and is an array of hex strings
print("\nSearching for bytecode in page scripts...")

bytecode_search = page.evaluate("""
() => {
    var scripts = document.querySelectorAll('script:not([src])');
    var result = [];
    for (var i = 0; i < scripts.length; i++) {
        var text = scripts[i].textContent;
        if (text && text.includes('HNOJ@?RC')) {
            result.push({index: i, length: text.length, snippet: text.slice(0, 500)});
        }
    }
    return result;
}
""")

print(f"Scripts with magic number: {len(bytecode_search)}")
for s in bytecode_search:
    print(f"  Script {s['index']} ({s['length']} chars): {s['snippet'][:200]}")

# Also check all scripts for the SDK call pattern
print("\nSearching for SDK call (_$webrt_1668687510...)")
sdk_calls = page.evaluate("""
() => {
    var scripts = document.querySelectorAll('script');
    var result = [];
    for (var i = 0; i < scripts.length; i++) {
        var text = scripts[i].textContent || '';
        if (text.includes('_$webrt_1668687510')) {
            result.push({
                index: i,
                src: scripts[i].src || '(inline)',
                length: text.length,
                snippet: text.slice(0, 1000)
            });
        }
    }
    return result;
}
""")

print(f"Scripts calling SDK: {len(sdk_calls)}")
for s in sdk_calls:
    print(f"  [{s['src'][:80]}] ({s['length']} chars):")
    print(f"    {s['snippet'][:500]}")
    
    # Save full script
    fname = f"sdk_call_script_{s['index']}.js"
    fpath = os.path.join(OUTPUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(s["snippet"])
    print(f"    Saved to: {fpath}")

page.close()
context.close()

print("\nDone!")
