"""End-to-end verification of Douyin adapter for ChinaCrawl v0.2.0."""
import sys, logging, os, json, time

sys.path.insert(0, r"C:\Users\Administrator\Documents\xhls_scraper")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("verify")

from chinacrawl.douyin.api import load_cookies, fetch_user_info, fetch_user_posts, close_client

COOKIE_FILE = r"C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json"
SEC_UID = "MS4wLjABAAAA_FX11UDBw7gopcoMWiGn1b8DgdPv5z4Lh_fN5V-WsuQ"  # 小冰

results = {}

# === Test 1: API layer - user_info ===
print("\n" + "=" * 60)
print("TEST 1: API Layer — fetch_user_info")
print("=" * 60)
try:
    load_cookies(COOKIE_FILE)
    data = fetch_user_info(SEC_UID)
    user = data.get("user", {})
    nickname = user.get("nickname", "?")
    followers = user.get("follower_count", 0)
    aweme_count = user.get("aweme_count", 0)
    print(f"  Nickname: {nickname}")
    print(f"  Followers: {followers:,}")
    print(f"  Aweme count: {aweme_count}")
    results["user_info"] = "PASS"
except Exception as e:
    print(f"  FAIL: {e}")
    results["user_info"] = f"FAIL: {e}"

# === Test 2: API layer - user_posts ===
print("\n" + "=" * 60)
print("TEST 2: API Layer — fetch_user_posts")
print("=" * 60)
try:
    data = fetch_user_posts(SEC_UID, max_cursor=0, count=10)
    aweme_list = data.get("aweme_list", [])
    has_more = data.get("has_more", 0)
    print(f"  Posts: {len(aweme_list)}, has_more={has_more}")
    for a in aweme_list[:3]:
        desc = a.get("desc", "?")[:50]
        stats = a.get("statistics", {})
        likes = stats.get("digg_count", 0)
        print(f"    [{likes:,} likes] {desc}")
    results["user_posts"] = "PASS" if aweme_list else "WARN: empty"
except Exception as e:
    print(f"  FAIL: {e}")
    results["user_posts"] = f"FAIL: {e}"

close_client()

# === Test 3: Scraper layer - user_info ===
print("\n" + "=" * 60)
print("TEST 3: Scraper Layer — user_info()")
print("=" * 60)
try:
    from chinacrawl.douyin.scraper import user_info
    info = user_info(SEC_UID)
    print(f"  Nickname: {info.nickname}")
    print(f"  Followers: {info.follower_count:,}")
    print(f"  Aweme: {info.aweme_count}")
    print(f"  Verified: {info.verified}")
    results["scraper_user_info"] = "PASS"
except Exception as e:
    print(f"  FAIL: {e}")
    results["scraper_user_info"] = f"FAIL: {e}"

# === Test 4: Scraper layer - user_posts (API channel only, no XHR) ===
print("\n" + "=" * 60)
print("TEST 4: Scraper Layer — user_posts() API-only")
print("=" * 60)
try:
    from chinacrawl.douyin.scraper import user_posts as scraper_user_posts
    from chinacrawl.douyin.scraper import AwemeInfo
    count = 0
    for aweme in scraper_user_posts(SEC_UID, max_pages=1, use_xhr=False):
        count += 1
        if count <= 3:
            print(f"  [{aweme.digg_count:,} likes] {aweme.desc[:50]}")
    print(f"  Total: {count} posts")
    results["scraper_user_posts_api"] = "PASS" if count > 0 else "WARN: empty"
except Exception as e:
    print(f"  FAIL: {e}")
    results["scraper_user_posts_api"] = f"FAIL: {e}"

# === Test 5: Scraper layer - search (uses XHR via browser, skip if no Playwright) ===
print("\n" + "=" * 60)
print("TEST 5: Scraper Layer — search() XHR channel")
print("=" * 60)
try:
    from chinacrawl.douyin.scraper import search
    results_list = search("碎菜机", max_results=10, use_xhr=True,
                          cookie_file=COOKIE_FILE)
    print(f"  Results: {len(results_list)}")
    for r in results_list[:5]:
        if r.result_type == "video":
            print(f"  [video] {r.aweme.desc[:40] if r.aweme else '?'}")
        elif r.result_type == "user":
            print(f"  [user] {r.user.nickname if r.user else '?'}")
    results["search_xhr"] = "PASS" if results_list else "WARN: empty"
except Exception as e:
    print(f"  FAIL: {e}")
    results["search_xhr"] = f"FAIL: {e}"

# === Summary ===
print("\n" + "=" * 60)
print("VERIFICATION SUMMARY")
print("=" * 60)
for test, result in results.items():
    status = "✅" if result == "PASS" else ("⚠️" if "WARN" in str(result) else "❌")
    print(f"  {status} {test}: {result}")

print(f"\nTotal: {len(results)} tests, "
      f"{sum(1 for r in results.values() if r == 'PASS')} passed, "
      f"{sum(1 for r in results.values() if 'WARN' in str(r))} warnings, "
      f"{sum(1 for r in results.values() if 'FAIL' in str(r))} failures")
