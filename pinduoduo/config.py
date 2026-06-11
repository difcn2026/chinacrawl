# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Platform Constants & Rate Limits
# Created: 2026-06-08

"""平台配置：UA 池、端点 URL、风控阈值、速率限制"""

import random

# ━━━ User-Agent 池（桌面端 Chrome）━━━
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Mobile UA for mobile.yangkeduo.com
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
]


def random_ua(mobile: bool = False) -> str:
    if mobile:
        return random.choice(USER_AGENTS[-2:])
    return random.choice(USER_AGENTS[:5])


# ━━━ Common Headers ━━━
COMMON_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

# ━━━ Pinduoduo Web API Endpoints ━━━
# Primary: mobile.yangkeduo.com (mobile web - easier to scrape)
# Fallback: pinduoduo.com (desktop web - more anti-bot)
API_BASE_MOBILE = "https://mobile.yangkeduo.com"
API_BASE_DESKTOP = "https://www.pinduoduo.com"
API_BASE_SEARCH = "https://mobile.yangkeduo.com"

API_ENDPOINTS = {
    # Search
    "search":             "/search_result.html",
    "search_api":         "/proxy/api/api/search/query",
    # Product
    "product_detail":     "/goods.html",
    "product_detail_api": "/proxy/api/api/oak/integration/render",
    # Shop/Mall
    "mall_page":          "/mall_page.html",
    "mall_api":           "/proxy/api/api/mall/info",
    # Category
    "category":           "/catelist.html",
    # Reviews (via mobile API)
    "reviews_api":        "/proxy/api/api/reviews/list",
    # Flash sale / promotions
    "promotion_api":      "/proxy/api/api/promotion/query",
    # Login
    "login":              "/login.html",
    "login_api":          "/proxy/api/api/login/mobile",
}

# ━━━ Rate Limits（安全阈值）━━━
RATE_LIMITS = {
    "search_per_minute": 3,
    "product_per_minute": 10,
    "reviews_per_minute": 8,
    "download_per_minute": 5,
    "concurrent_browsers": 1,  # PDD is more strict
    "retry_delay_base": 10,     # Longer base delay
    "retry_delay_max": 180,     # 3 min max
    "request_interval_min": 3.0,
    "request_interval_max": 8.0,
}

# ━━━ Browser Args ━━━
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-setuid-sandbox",
    "--window-size=412,915",  # Mobile viewport for mobile.yangkeduo.com
]

# ━━━ Timers ━━━
DEFAULT_TIMEOUT = 45            # HTTP 请求超时 (PDD slower)
BROWSER_TIMEOUT = 90000         # Playwright 页面加载超时 (ms)
BROWSER_NAV_TIMEOUT = 60000     # Playwright 导航超时 (ms)
