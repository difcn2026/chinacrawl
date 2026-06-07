"""Debug douyin search page SSR data."""
import sys, json, time, urllib.parse
sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")

from chinacrawl.douyin.browser import launch_browser, _create_context
from chinacrawl.douyin.config import BROWSER_NAV_TIMEOUT

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"

browser = launch_browser(headless=True)
context = _create_context(browser, cookie_file=COOKIE_FILE)
page = context.new_page()

keyword = urllib.parse.quote("碎菜机")
url = f"https://www.douyin.com/search/{keyword}?type=general"
page.goto(url, wait_until="networkidle", timeout=BROWSER_NAV_TIMEOUT)
time.sleep(2)

# Extract RENDER_DATA (Next.js SSR)
render_data = page.evaluate("""
() => {
    var el = document.getElementById('RENDER_DATA');
    return el ? el.textContent : null;
}
""")

if render_data:
    decoded = urllib.parse.unquote(render_data)
    try:
        data = json.loads(decoded)
        print(f"RENDER_DATA keys ({len(data)}):")
        for key in sorted(data.keys()):
            val = data[key]
            if isinstance(val, (dict, list)):
                t = type(val).__name__
                s = len(val) if isinstance(val, list) else len(list(val.keys())[:10])
                print(f"  {key}: {t}({s})")
                # Show structure of interesting keys
                if isinstance(val, dict) and s < 15:
                    print(f"    sub-keys: {list(val.keys())[:10]}")
            else:
                print(f"  {key}: {repr(str(val)[:80])}")
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
        print(decoded[:200])

# Check if search results rendered
has_results = page.evaluate("""
() => {
    var selectors = ['[data-e2e="scroll-list"]', '.search-result-card', '[class*="search-card"]'];
    for (var i = 0; i < selectors.length; i++) {
        var el = document.querySelector(selectors[i]);
        if (el) return selectors[i] + ' children=' + el.children.length;
    }
    return false;
}
""")
print(f"Has results: {has_results}")

# Check for error/message
body_snippet = page.evaluate("() => document.body.innerText.slice(0, 400)")
print(f"Body: {body_snippet}")

page.close()
context.close()
