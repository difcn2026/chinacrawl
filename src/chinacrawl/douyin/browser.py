# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Playwright Browser Layer
# Created: 2026-06-07

"""
Playwright 浏览器交互层。

当 API 层被风控拦截时，降级到真实浏览器。
通过注入反检测脚本模拟真人行为来绕过检测。
"""

import json
import logging
import os
import time
from typing import Optional

from .config import (
    BROWSER_ARGS, BROWSER_TIMEOUT, BROWSER_NAV_TIMEOUT,
    random_ua, RATE_LIMITS as RL,
)
from .anti_detect import (
    ANTI_DETECT_JS, CONTEXT_OVERRIDES,
    random_delay, random_mouse_movements, random_scroll_steps,
)

log = logging.getLogger("chinacrawl.douyin.browser")

# ━━━ Playwright singleton ━━━
_playwright = None
_browser = None


def _get_playwright():
    """延迟导入 Playwright（可选依赖）"""
    global _playwright
    if _playwright is None:
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright().start()
    return _playwright


def launch_browser(headless: bool = True) -> "Browser":
    """启动 Chromium 浏览器（反检测配置）"""
    global _browser
    pw = _get_playwright()
    if _browser is None or not _browser.is_connected():
        _browser = pw.chromium.launch(
            headless=headless,
            args=BROWSER_ARGS,
        )
    return _browser


def close_browser():
    global _browser, _playwright
    try:
        if _browser and _browser.is_connected():
            _browser.close()
    except Exception:
        pass
    _browser = None
    # Don't stop playwright - keep it alive for reuse


def _create_context(browser, cookie_file: Optional[str] = None):
    """创建带反检测配置的浏览器上下文"""
    context = browser.new_context(**CONTEXT_OVERRIDES)

    # 注入反检测脚本（每个新页面自动注入）
    context.add_init_script(ANTI_DETECT_JS)

    # 加载 cookies
    if cookie_file and os.path.exists(cookie_file):
        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            cookie_list = cookies.get("cookies", cookies) if isinstance(cookies, dict) else cookies
            context.add_cookies(cookie_list)
            log.info("Loaded %d cookies from %s", len(cookie_list), cookie_file)
        except Exception as e:
            log.warning("Failed to load cookies: %s", e)

    return context


# ━━━ Page Navigation ━━━

def open_user_page(sec_uid: str, cookie_file: Optional[str] = None,
                   headless: bool = True) -> dict:
    """
    通过浏览器打开用户主页，提取数据。

    从 window.__INITIAL_STATE__ 或 SSR 数据中解析。

    Args:
        sec_uid: 用户加密 ID
        cookie_file: Cookie 文件路径
        headless: 是否无头模式

    Returns:
        {
            "user": {...},
            "posts": [{...}, ...],
            "has_more": true,
            "max_cursor": "..."
        }
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()

    try:
        # 导航到用户主页
        url = f"https://www.douyin.com/user/{sec_uid}"
        log.info("Navigating to: %s", url)

        page.goto(url,
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

        # 模拟人类行为：随机延迟 + 鼠标移动
        time.sleep(random_delay(1000, 2500) / 1000)
        random_mouse_movements(page)

        # 等待内容加载
        try:
            page.wait_for_selector("[data-e2e=\"user-post-list\"]",
                                   timeout=15000)
        except Exception:
            log.warning("Post list selector not found, trying scroll...")

        # 滚动加载更多内容
        _human_scroll(page, scrolls=3)

        # 从页面提取数据
        data = _extract_from_page(page)
        return data

    finally:
        page.close()
        context.close()


def open_video_page(aweme_id: str, cookie_file: Optional[str] = None,
                    headless: bool = True) -> dict:
    """
    通过浏览器打开单个视频页面，提取详情。

    Args:
        aweme_id: 视频 ID
        cookie_file: Cookie 文件路径
        headless: 是否无头模式
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()

    try:
        url = f"https://www.douyin.com/video/{aweme_id}"
        page.goto(url, wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(random_delay(1000, 2500) / 1000)

        data = _extract_from_page(page)
        return data
    finally:
        page.close()
        context.close()


def browse_search(keyword: str, max_results: int = 20,
                  cookie_file: Optional[str] = None,
                  headless: bool = True) -> list:
    """
    通过浏览器搜索关键词。

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        cookie_file: Cookie 文件路径
        headless: 是否无头模式
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()

    results = []
    try:
        # 使用抖音搜索 URL
        encoded = __import__("urllib.parse").quote(keyword)
        url = f"https://www.douyin.com/search/{encoded}"
        page.goto(url, wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(random_delay(1500, 3000) / 1000)

        # 滚动加载更多
        _human_scroll(page, scrolls=5)

        # 提取搜索结果
        data = _extract_from_page(page)
        if data and "search_result" in data:
            results = data["search_result"]
        return results[:max_results]
    finally:
        page.close()
        context.close()


# ━━━ Internal Helpers ━━━

def _human_scroll(page, scrolls: int = 3):
    """模拟人类滚动行为"""
    for _ in range(scrolls):
        step = __import__("random").randint(300, 800)
        page.evaluate(f"window.scrollBy(0, {step})")
        time.sleep(random_delay(500, 2000) / 1000)
        if _ % 2 == 0:
            random_mouse_movements(page)


def _extract_from_page(page) -> dict:
    """
    从抖音页面提取结构化数据。

    策略：
    1. 尝试从 __INITIAL_STATE__ 获取（SSR 数据，最完整）
    2. 回退到 DOM 选择器提取
    """
    try:
        # 方法1：提取 SSR 初始化数据
        init_state = page.evaluate("""
            () => {
                const scripts = document.querySelectorAll('script');
                for (const script of scripts) {
                    const text = script.textContent || '';
                    if (text.includes('__INITIAL_STATE__')) {
                        const match = text.match(/self\\.__pace_f\\.push\\(\\[1,"s:[\\\\s\\\\S]*?\\\\}\\\\}\\":({[\\\\s\\\\S]*?})\\]\\)/);
                        if (match) {
                            try { return JSON.parse(match[1]); } catch(e) {}
                        }
                    }
                }
                // 尝试 window.__INITIAL_STATE__
                if (window.__INITIAL_STATE__) {
                    return window.__INITIAL_STATE__;
                }
                return null;
            }
        """)

        if init_state:
            return _normalize_state(init_state)

    except Exception as e:
        log.warning("SSR extraction failed: %s", e)

    # 方法2：DOM 回退提取
    return _extract_from_dom(page)


def _normalize_state(raw: dict) -> dict:
    """标准化 __INITIAL_STATE__ 数据结构"""
    result = {"raw": raw}

    # 尝试提取用户信息
    for key in ["user", "userInfo", "user_info"]:
        if key in raw:
            result["user"] = raw[key]
            break

    # 尝试提取作品列表
    for key in ["post", "awemeList", "aweme_list"]:
        if key in raw:
            data = raw[key]
            if isinstance(data, dict):
                result["posts"] = data.get("list", data.get("aweme_list", []))
                result["has_more"] = data.get("hasMore", data.get("has_more", False))
                result["max_cursor"] = data.get("maxCursor", data.get("max_cursor", 0))
            elif isinstance(data, list):
                result["posts"] = data
            break

    return result


def _extract_from_dom(page) -> dict:
    """DOM 选择器回退提取"""
    result = {"posts": [], "user": {}}

    try:
        # 提取用户名
        title_el = page.query_selector("[data-e2e=\"user-title\"]")
        if title_el:
            result["user"]["nickname"] = title_el.inner_text()

        # 提取粉丝数等
        stats = page.query_selector_all("[data-e2e=\"user-info-stats\"] span")
        if len(stats) >= 3:
            result["user"]["following_count"] = _parse_count(stats[0].inner_text())
            result["user"]["follower_count"] = _parse_count(stats[1].inner_text())
            result["user"]["total_favorited"] = _parse_count(stats[2].inner_text())

        # 提取作品列表
        post_items = page.query_selector_all("[data-e2e=\"user-post-item\"]")
        for item in post_items:
            post = {}
            try:
                desc_el = item.query_selector("[data-e2e=\"user-post-desc\"]")
                if desc_el:
                    post["desc"] = desc_el.inner_text()
            except Exception:
                pass
            result["posts"].append(post)

    except Exception as e:
        log.warning("DOM extraction failed: %s", e)

    return result


def _parse_count(text: str) -> int:
    """解析 '1.2w' / '1234' 格式的数字"""
    text = text.strip().lower().replace(",", "")
    try:
        if "w" in text:
            return int(float(text.replace("w", "")) * 10000)
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        return int(text)
    except (ValueError, TypeError):
        return 0



# XHR Interception based user posts collection (Plan B - bypasses X-Bogus)
def collect_user_posts_via_xhr(sec_uid: str, cookie_file: str = None,
                               max_posts: int = 0, headless: bool = True) -> list[dict]:
    """
    Collect ALL user posts by intercepting browser XHR API calls.
    
    The browser makes properly-signed API requests internally.
    We intercept the responses, avoiding X-Bogus reverse engineering.
    Uses scrollIntoView to trigger IntersectionObserver-based lazy loading.
    
    Args:
        sec_uid: User encrypted ID
        cookie_file: Path to saved cookies JSON (from login())
        max_posts: Max posts to collect (0=unlimited)
        headless: Run browser in headless mode
    
    Returns:
        List of aweme dicts with keys: aweme_id, desc, create_time, duration,
        digg_count, comment_count, share_count, play_count, video_url, cover_url,
        hashtags, music_title
    """
    import time as _time
    
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file=cookie_file)
    page = context.new_page()
    
    collected = []
    seen_ids = set()
    
    def _on_response(response):
        url = response.url
        if '/aweme/v1/web/aweme/post/' not in url:
            return
        if response.status != 200:
            return
        try:
            data = response.json()
        except Exception:
            return
        aweme_list = data.get('aweme_list', [])
        for a in aweme_list:
            aid = str(a.get('aweme_id', ''))
            if aid and aid not in seen_ids:
                seen_ids.add(aid)
                collected.append(a)  # Pass raw API dict - scraper will parse it
    
    page.on("response", _on_response)
    
    try:
        url = f"https://www.douyin.com/user/{sec_uid}"
        page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
        _time.sleep(3)
        
        log.info("XHR collection: initial count=%d", len(collected))
        
        no_new = 0
        prev_count = 0
        max_rounds = 80
        
        for round_num in range(max_rounds):
            # Trigger IntersectionObserver by scrolling last card into view
            page.evaluate("""() => {
                const cards = document.querySelectorAll('li a[href*="/video/"]');
                if (cards.length > 0) {
                    cards[cards.length - 1].scrollIntoView({ behavior: 'instant', block: 'end' });
                }
            }""")
            _time.sleep(1.0)
            
            # Also scroll container
            page.evaluate("""() => {
                const container = document.querySelector('.route-scroll-container');
                if (container) {
                    container.scrollTo(0, container.scrollHeight);
                }
                window.scrollTo(0, document.body.scrollHeight);
            }""")
            _time.sleep(1.5)
            
            total = len(collected)
            if total > prev_count:
                prev_count = total
                no_new = 0
                if total % 50 == 0:
                    log.info("XHR collection: %d posts", total)
            else:
                no_new += 1
            
            if no_new >= 10:
                log.info("XHR collection complete: %d posts (no new data)", total)
                break
            
            if max_posts > 0 and total >= max_posts:
                log.info("XHR collection: reached max_posts=%d", max_posts)
                break
    
    finally:
        page.close()
        context.close()
        # Don't close browser - let caller manage it
    
    return collected
