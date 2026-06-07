# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Web API Layer (Reverse Engineered)
# Created: 2026-06-08

"""
拼多多 Web 版内部 API 调用层.

警告: 拼多多 API 使用 anti-content (anti-token) 签名机制.
      签名算法不开源，因此 API 层主要用于轻量查询.
      遇到风控时自动抛出异常，由 scraper.py 降级到 browser.py.

API 端点发现方式:
  - mobile.yangkeduo.com 的 XHR 请求捕获
  - /proxy/api/api/* 为移动端 API 网关路径
"""

import json
import logging
import time
import urllib.parse
from typing import Optional, Generator

import httpx

from .config import (
    API_BASE_MOBILE, API_BASE_DESKTOP, API_ENDPOINTS,
    COMMON_HEADERS, random_ua, DEFAULT_TIMEOUT,
    RATE_LIMITS as RL,
)

log = logging.getLogger("chinacrawl.pinduoduo.api")

# ━━━ Session ━━━
_session: Optional[httpx.Client] = None


def _get_client(proxy: Optional[str] = None) -> httpx.Client:
    """获取或创建 HTTP 客户端（复用连接池）"""
    global _session
    if _session is None or _session.is_closed:
        _session = httpx.Client(
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            headers={**COMMON_HEADERS, "User-Agent": random_ua(mobile=True)},
            proxy=proxy,
        )
    return _session


def close_client():
    global _session
    if _session and not _session.is_closed:
        _session.close()
        _session = None


# ━━━ Helpers ━━━
def _build_url(endpoint_key: str, base: str = None, **params) -> str:
    """构建完整 API URL"""
    if base is None:
        base = API_BASE_MOBILE
    path = API_ENDPOINTS[endpoint_key]
    url = base + path
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        qs = urllib.parse.urlencode(clean)
        url += "?" + qs
    return url


def _get_headers(referer: str = "") -> dict:
    """生成请求头（每次轮换 UA）"""
    headers = {**COMMON_HEADERS, "User-Agent": random_ua(mobile=True)}
    if referer:
        headers["Referer"] = referer
    return headers


def _parse_response(resp: httpx.Response) -> dict:
    """解析拼多多 API 响应，统一错误处理"""
    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise PinduoduoAPIError(
            code=-1,
            message=f"Invalid JSON response: {resp.text[:200]}",
            url=str(resp.url),
            status=resp.status_code,
        )

    # 拼多多 API 错误处理
    # 常见错误码: 40001=需要登录, 40002=参数错误, 50001=风控拦截
    err_code = data.get("error_code", data.get("server_time", 0) > 0 and 0 or -1)
    if isinstance(err_code, int) and err_code != 0 and "error_code" in data:
        raise PinduoduoAPIError(
            code=data["error_code"],
            message=data.get("error_msg", "Unknown API error"),
            url=str(resp.url),
            status=resp.status_code,
            raw=data,
        )

    return data


# ━━━ Exceptions ━━━
class PinduoduoAPIError(Exception):
    """拼多多 API 调用错误"""
    def __init__(self, code: int, message: str, url: str = "",
                 status: int = 0, raw: dict = None):
        self.code = code
        self.message = message
        self.url = url
        self.status = status
        self.raw = raw or {}
        super().__init__(f"[{code}] {message}")


class PinduoduoRateLimitError(PinduoduoAPIError):
    """触发限流/风控"""
    pass


# ━━━ Core API Methods ━━━
def _get(endpoint: str, **params) -> dict:
    """通用 GET 请求"""
    url = _build_url(endpoint, **params)
    headers = _get_headers(referer=API_BASE_MOBILE + "/")
    client = _get_client()

    for attempt in range(3):
        try:
            resp = client.get(url, headers=headers)
            if resp.status_code == 429:
                wait = min(RL["retry_delay_base"] * (2 ** attempt), RL["retry_delay_max"])
                log.warning("Rate limited, waiting %ds...", wait)
                time.sleep(wait)
                continue
            if resp.status_code in (403, 407, 418):
                raise PinduoduoRateLimitError(
                    code=resp.status_code,
                    message=f"Blocked by anti-bot (HTTP {resp.status_code})",
                    url=url,
                    status=resp.status_code,
                )
            resp.raise_for_status()
            return _parse_response(resp)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt == 2:
                raise PinduoduoAPIError(code=-1, message=str(e), url=url)
            time.sleep(RL["retry_delay_base"] * (2 ** attempt))

    raise PinduoduoAPIError(code=-1, message="Max retries exceeded", url=url)


# ━━━ Search API ━━━
def search_product(keyword: str, page: int = 1, size: int = 20) -> dict:
    """
    搜索商品 (通过移动端 API).

    Args:
        keyword: 搜索关键词
        page: 页码
        size: 每页数量

    Returns:
        { "items": [...], "total_count": 12345, "has_more": true }
    """
    return _get("search_api",
                 q=keyword,
                 page=page,
                 size=min(size, 50),
                 source="search",
                 pdduid=0)


# ━━━ Product Detail API ━━━
def fetch_product_detail(goods_id: str) -> dict:
    """
    获取商品详情 (移动端 API).

    Args:
        goods_id: 商品 ID (如 "123456789")

    Returns:
        { "goods": {...}, "shop": {...}, "reviews": {...} }
    """
    return _get("product_detail_api",
                 goods_id=goods_id,
                 pdduid=0)


# ━━━ Mall/Shop API ━━━
def fetch_mall_info(mall_id: str) -> dict:
    """
    获取店铺信息.

    Args:
        mall_id: 店铺 ID

    Returns:
        { "mall": {...}, "goods_list": [...] }
    """
    return _get("mall_api",
                 mall_id=mall_id,
                 pdduid=0)


# ━━━ Reviews API ━━━
def fetch_product_reviews(goods_id: str, page: int = 1, size: int = 20) -> dict:
    """
    获取商品评价列表.

    Args:
        goods_id: 商品 ID
        page: 页码
        size: 每页数量

    Returns:
        { "reviews": [...], "total": int, "has_more": bool }
    """
    return _get("reviews_api",
                 goods_id=goods_id,
                 page=page,
                 size=min(size, 50))


# ━━━ Promotion/Flash Sale API ━━━
def fetch_promotions(activity_type: str = "flash_sale") -> dict:
    """
    获取促销/秒杀活动.

    Args:
        activity_type: 活动类型

    Returns:
        { "promotions": [...] }
    """
    return _get("promotion_api",
                 activity_type=activity_type,
                 pdduid=0)
