# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Platform Constants & Rate Limits
# Created: 2026-06-07

"""平台配置：UA 池、端点 URL、风控阈值、速率限制"""

import random

# ━━━ User-Agent 池（桌面端 Chrome）━━━
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


def random_ua() -> str:
    return random.choice(USER_AGENTS)


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


# ━━━ Douyin Web API Endpoints ━━━
API_BASE = "https://www.douyin.com"
API_ENDPOINTS = {
    # User
    "user_info":       "/aweme/v1/web/user/profile/other/",
    "user_posts":      "/aweme/v1/web/aweme/post/",
    "user_likes":      "/aweme/v1/web/aweme/favorite/",
    # Video
    "video_detail":    "/aweme/v1/web/aweme/detail/",
    "video_comments":  "/aweme/v1/web/comment/list/",
    "video_replies":   "/aweme/v1/web/comment/list/reply/",
    # Search
    "search_general":  "/aweme/v1/web/search/item/",
    "search_user":     "/aweme/v1/web/discover/search/",
    # Live
    "live_info":       "/webcast/room/reflow/info/",
}

# ━━━ Rate Limits（安全阈值）━━━
RATE_LIMITS = {
    "user_posts_per_hour": 20,
    "videos_per_user_per_min": 10,
    "search_per_minute": 5,
    "download_per_minute": 15,
    "concurrent_browsers": 2,
    "retry_delay_base": 5,
    "retry_delay_max": 120,
    "request_interval_min": 2.0,
    "request_interval_max": 5.0,
}


# ━━━ Browser Args ━━━
BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-setuid-sandbox",
    "--window-size=1920,1080",
]

# ━━━ Timers ━━━
DEFAULT_TIMEOUT = 30           # HTTP 请求超时
BROWSER_TIMEOUT = 60000        # Playwright 页面加载超时 (ms)
BROWSER_NAV_TIMEOUT = 45000    # Playwright 导航超时 (ms)
