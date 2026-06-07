"""Extract msToken from browser localStorage for API search."""
import sys, json, time, urllib.parse
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import BROWSER_NAV_TIMEOUT

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"

browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

# First, go to douyin home to get msToken generated
print("Step 1: Visiting douyin.com to get msToken...")
page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(3)

# Extract msToken from localStorage
ms_token = page.evaluate("""
() => {
    // Check various storage locations
    var ls = localStorage.getItem('xmst');
    if (ls) return ls;
    
    // Check all localStorage keys for msToken
    for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        if (key && key.toLowerCase().indexOf('ms') >= 0) {
            return key + '=' + localStorage.getItem(key);
        }
    }
    
    // Check sessionStorage
    for (var i = 0; i < sessionStorage.length; i++) {
        var key = sessionStorage.key(i);
        if (key && key.toLowerCase().indexOf('ms') >= 0) {
            return 'SS:' + key + '=' + sessionStorage.getItem(key);
        }
    }
    
    // Check cookies for msToken
    var cookies = document.cookie.split(';');
    for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.indexOf('msToken') >= 0 || c.indexOf('ms_token') >= 0) {
            return 'COOKIE:' + c;
        }
    }
    
    return null;
}
""")

print(f"msToken: {ms_token}")

# Also dump all localStorage keys
ls_keys = page.evaluate("""
() => {
    var keys = [];
    for (var i = 0; i < localStorage.length; i++) {
        var key = localStorage.key(i);
        var val = localStorage.getItem(key);
        keys.push(key + '=' + val.slice(0, 60));
    }
    return keys;
}
""")
print(f"\nlocalStorage keys ({len(ls_keys)}):")
for k in ls_keys[:20]:
    print(f"  {k}")

# Also check for any token-like cookies
cookies = page.evaluate("""
() => {
    return document.cookie.split(';').map(function(c) {
        var parts = c.trim().split('=');
        return parts[0] + '=' + (parts[1] || '').slice(0, 30);
    });
}
""")
print(f"\nDocument cookies ({len(cookies)}):")
for c in cookies[:15]:
    print(f"  {c}")

page.close()
context.close()
print("\nDone!")
