# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Web API Reverse Engineering Layer
# Created: 2026-06-07

"""
抖音 Web 版内部 API 调用层。

通过 HTTP 直接调用 douyin.com 的内部 JSON API。
优先使用此层，速度比浏览器快 10x。
遇到风控时自动抛出异常，由 scraper.py 降级到 browser.py。
"""

import hashlib
import json
import logging
import os
import subprocess
import time
import urllib.parse
from typing import Optional, Generator

import httpx

from .config import (
    API_BASE, API_ENDPOINTS, COMMON_HEADERS,
    random_ua, DEFAULT_TIMEOUT,
    RATE_LIMITS as RL,
)

log = logging.getLogger("chinacrawl.douyin.api")

# ━━━ Session ━━━


# X-Bogus signing bridge (Node.js)
_XBOGUS_BRIDGE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "scripts", "xbogus_bridge.js")
# Fallback paths
if not os.path.exists(_XBOGUS_BRIDGE):
    _XBOGUS_BRIDGE = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "xbogus_bridge.js")
_XBOGUS_CACHE = {}  # Simple cache: query_string -> xbogus

# Browser params required by douyin API
_BROWSER_PARAMS = (
    "device_platform=webapp&aid=6383&channel=channel_pc_web"
    "&update_version_code=170400&pc_client_type=1"
    "&version_code=190600&version_name=19.6.0"
    "&cookie_enabled=true&screen_width=1920&screen_height=1080"
    "&browser_language=zh-CN&browser_platform=Win32"
    "&browser_name=Chrome&browser_version=131.0.0.0"
    "&browser_online=true&engine_name=Blink&engine_version=131.0.0.0"
    "&os_name=Windows&os_version=10&cpu_core_num=8&device_memory=8&platform=PC"
)


def _sign_xbogus(query_string: str) -> str:
    """Generate X-Bogus via Node.js bridge (with caching)."""
    if query_string in _XBOGUS_CACHE:
        return _XBOGUS_CACHE[query_string]
    try:
        result = subprocess.run(
            ["node", _XBOGUS_BRIDGE, query_string, random_ua()],
            capture_output=True, text=True, timeout=5,
            cwd=os.path.dirname(_XBOGUS_BRIDGE)
        )
        if result.returncode == 0 and result.stdout.strip():
            xb = result.stdout.strip()
            _XBOGUS_CACHE[query_string] = xb
            return xb
    except Exception:
        pass
    raise DouyinAPIError(code=-2, message="X-Bogus signing failed")
_session: Optional[httpx.Client] = None


def _get_client(proxy: Optional[str] = None) -> httpx.Client:
    """获取或创建 HTTP 客户端（复用连接池）"""
    global _session
    if _session is None or _session.is_closed:
        _session = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            headers={**COMMON_HEADERS, "User-Agent": random_ua()},
            proxy=proxy,
        )
    _apply_cookies(_session)
    return _session


def close_client():
    global _session
    if _session and not _session.is_closed:
        _session.close()
        _session = None


# Cookie management
_cookies: dict = {}  # name -> value dict for httpx

def load_cookies(cookie_file: str) -> int:
    """Load cookies from Playwright-format JSON file."""
    global _cookies
    with open(cookie_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    cookies = data.get("cookies", data if isinstance(data, list) else [])
    _cookies = {}
    for c in cookies:
        _cookies[c["name"]] = c["value"]
    log.info("Loaded %d cookies from %s", len(_cookies), cookie_file)
    return len(_cookies)

def _apply_cookies(client: httpx.Client) -> None:
    """Apply loaded cookies to httpx client."""
    if _cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in _cookies.items())
        client.headers["Cookie"] = cookie_str

# ━━━ Helpers ━━━

def _build_url(endpoint_key: str, **params) -> str:
    """构建完整 API URL"""
    path = API_ENDPOINTS[endpoint_key]
    url = API_BASE + path
    if params:
        # 过滤 None 值
        clean = {k: v for k, v in params.items() if v is not None}
        qs = urllib.parse.urlencode(clean)
        url += "?" + qs
    return url


def _get_headers(referer: str = "") -> dict:
    """生成请求头（每次轮换 UA）"""
    headers = {**COMMON_HEADERS, "User-Agent": random_ua()}
    if referer:
        headers["Referer"] = referer
    return headers


def _parse_response(resp: httpx.Response) -> dict:
    """解析抖音 API 响应，统一错误处理"""
    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise DouyinAPIError(
            code=-1,
            message=f"Invalid JSON response: {resp.text[:200]}",
            url=str(resp.url),
            status=resp.status_code,
        )

    # 抖音 API 通用状态码
    status_code = data.get("status_code", 0)
    if status_code != 0:
        raise DouyinAPIError(
            code=status_code,
            message=data.get("status_msg", "Unknown API error"),
            url=str(resp.url),
            status=resp.status_code,
            raw=data,
        )

    return data


# ━━━ Exceptions ━━━

class DouyinAPIError(Exception):
    """抖音 API 调用错误"""
    def __init__(self, code: int, message: str, url: str = "",
                 status: int = 0, raw: dict = None):
        self.code = code
        self.message = message
        self.url = url
        self.status = status
        self.raw = raw or {}
        super().__init__(f"[{code}] {message}")


class DouyinRateLimitError(DouyinAPIError):
    """触发限流/风控"""
    pass


# ━━━ Core API Methods ━━━

def _get(endpoint: str, **params) -> dict:
    """通用 GET 请求"""
    url = _build_url(endpoint, **params)
    # Append browser params + X-Bogus signing
    parsed = urllib.parse.urlparse(url)
    q = parsed.query
    q = (q + "&" + _BROWSER_PARAMS) if q else _BROWSER_PARAMS
    try:
        xb = _sign_xbogus(q)
        q = q + "&X-Bogus=" + urllib.parse.quote(xb, safe="")
    except DouyinAPIError:
        pass
    url = API_BASE + API_ENDPOINTS[endpoint] + "?" + q
    headers = _get_headers(referer=API_BASE + "/")
    client = _get_client()

    for attempt in range(3):
        try:
            resp = client.get(url, headers=headers)
            if resp.status_code == 429:
                wait = min(RL["retry_delay_base"] * (2 ** attempt), RL["retry_delay_max"])
                log.warning("Rate limited, waiting %ds...", wait)
                time.sleep(wait)
                continue
            if resp.status_code in (403, 407):
                raise DouyinRateLimitError(
                    code=resp.status_code,
                    message=f"Blocked (HTTP {resp.status_code})",
                    url=url,
                    status=resp.status_code,
                )
            resp.raise_for_status()
            return _parse_response(resp)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt == 2:
                raise DouyinAPIError(code=-1, message=str(e), url=url)
            time.sleep(RL["retry_delay_base"] * (2 ** attempt))

    raise DouyinAPIError(code=-1, message="Max retries exceeded", url=url)


# ━━━ User API ━━━

def fetch_user_info(sec_uid: str) -> dict:
    """
    获取用户主页信息。

    Args:
        sec_uid: 用户加密 ID（如 MS4wLjABAAAAxxx）

    Returns:
        {
            "user": {
                "sec_uid": "...",
                "nickname": "...",
                "avatar_thumb": {...},
                "signature": "...",
                "follower_count": 12345,
                "following_count": 100,
                "aweme_count": 342,
                "total_favorited": 50000,
                ...
            }
        }
    """
    return _get("user_info", sec_user_id=sec_uid)


def fetch_user_posts(sec_uid: str, max_cursor: int = 0,
                     count: int = 20) -> dict:
    """
    获取用户作品列表（分页）。

    Args:
        sec_uid: 用户加密 ID
        max_cursor: 分页游标（0=第一页）
        count: 每页数量（最大 35）

    Returns:
        {
            "aweme_list": [{aweme_info...}, ...],
            "max_cursor": 1234567890,
            "has_more": 1
        }
    """
    return _get("user_posts",
                sec_user_id=sec_uid,
                max_cursor=max_cursor,
                count=min(count, 35))


def fetch_user_posts_all(sec_uid: str) -> Generator[dict, None, None]:
    """
    迭代获取用户全部作品（自动翻页）。

    Yields:
        每页的 aweme 列表
    """
    cursor = 0
    page = 0
    while True:
        page += 1
        try:
            data = fetch_user_posts(sec_uid, max_cursor=cursor, count=35)
        except DouyinAPIError:
            log.error("Failed to fetch page %d (cursor=%s)", page, cursor)
            break

        aweme_list = data.get("aweme_list", [])
        if not aweme_list:
            break

        yield aweme_list

        has_more = data.get("has_more", 0)
        if not has_more:
            break

        cursor = data.get("max_cursor", 0)
        if cursor == 0:
            break

        # 速率保护
        time.sleep(2.0)


# ━━━ Video API ━━━

def fetch_video_detail(aweme_id: str) -> dict:
    """
    获取单条视频详情。

    Args:
        aweme_id: 视频 ID（数字字符串）

    Returns:
        { "aweme_detail": {...} }
    """
    return _get("video_detail", aweme_id=aweme_id)


# ━━━ Comment API ━━━

def fetch_video_comments(aweme_id: str, cursor: int = 0,
                         count: int = 20) -> dict:
    """
    获取视频评论。

    Args:
        aweme_id: 视频 ID
        cursor: 分页游标
        count: 每页数量

    Returns:
        {
            "comments": [{text, digg_count, user: {...}, ...}, ...],
            "cursor": 123,
            "has_more": 1
        }
    """
    return _get("video_comments",
                aweme_id=aweme_id,
                cursor=cursor,
                count=min(count, 50))


# ━━━ Search API ━━━

def search_general(keyword: str, offset: int = 0,
                   count: int = 10) -> dict:
    """
    通用搜索（视频+用户+话题混合）。

    Args:
        keyword: 搜索关键词
        offset: 偏移量
        count: 数量

    Returns:
        { "data": [{type, aweme_info/user_info...}, ...] }
    """
    return _get("search_general",
                keyword=keyword,
                offset=offset,
                count=min(count, 20),
                search_source="normal_search")


def search_user(keyword: str, offset: int = 0,
                count: int = 10) -> dict:
    """
    搜索用户。

    Args:
        keyword: 搜索关键词
        offset: 偏移量
        count: 数量
    """
    return _get("search_user",
                keyword=keyword,
                offset=offset,
                count=min(count, 20),
                type=1)  # type=1 = user search
