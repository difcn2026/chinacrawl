# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Core Scraper Orchestrator
# Created: 2026-06-08

"""
核心采集编排层.

双通道策略:
  API Channel (优先) → Browser Channel (降级)

公共 API:
  from chinacrawl.pinduoduo import product_search, product_detail, shop_info, ...
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Generator, List, Optional
from urllib.parse import urlparse

import httpx

from . import api
from . import browser
from .config import API_BASE_MOBILE, RATE_LIMITS as RL

log = logging.getLogger("chinacrawl.pinduoduo.scraper")

CST = timezone(timedelta(hours=8))


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class ProductInfo:
    """拼多多商品信息"""
    goods_id: str
    title: str = ""
    price: float = 0.0
    original_price: float = 0.0
    sales: int = 0
    sales_text: str = ""
    img_url: str = ""          # 主图
    images: list = field(default_factory=list)  # 全部图片
    shop_name: str = ""
    mall_id: str = ""
    desc: str = ""             # 商品描述
    specs: list = field(default_factory=list)   # 规格
    has_coupon: bool = False
    free_shipping: bool = False
    stock: int = 0
    rating: float = 0.0        # 评分
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "ProductInfo":
        goods = data.get("goods", data.get("goodsDetail", data))
        price_val = goods.get("min_group_price", goods.get("minGroupPrice",
                              goods.get("price", goods.get("mallPrice", 0))))
        orig_price_val = goods.get("market_price", goods.get("marketPrice",
                                   goods.get("originalPrice", 0)))

        images = []
        gallery = goods.get("top_gallery", goods.get("goods_gallery_urls", []))
        if isinstance(gallery, list):
            images = gallery
        elif isinstance(gallery, str):
            images = [u.strip() for u in gallery.split(",") if u.strip()]

        return cls(
            goods_id=str(goods.get("goods_id", goods.get("goodsId", ""))),
            title=goods.get("goods_name", goods.get("goodsName", goods.get("title", ""))),
            price=_parse_price(price_val),
            original_price=_parse_price(orig_price_val),
            sales=int(goods.get("sales", goods.get("sales_tip", 0))),
            sales_text=str(goods.get("salesTip", goods.get("sales_tip", ""))),
            img_url=goods.get("thumb_url", goods.get("thumbUrl", goods.get("image_url", ""))),
            images=images,
            shop_name=goods.get("mall_name", goods.get("mallName", "")),
            mall_id=str(goods.get("mall_id", goods.get("mallId", ""))),
            has_coupon=bool(goods.get("has_coupon", goods.get("hasCoupon", False))),
            free_shipping=bool(goods.get("free_shipping", goods.get("freeShipping", False))),
            stock=int(goods.get("quantity", goods.get("stock", 0))),
            rating=float(goods.get("avgRating", goods.get("desc_txt", "0").replace("分", ""))),
            raw=goods,
        )

    @classmethod
    def from_browser(cls, data: dict) -> "ProductInfo":
        return cls.from_api(data)

    @classmethod
    def from_xhr(cls, data: dict) -> "ProductInfo":
        return cls(
            goods_id=str(data.get("goods_id", data.get("goodsId", ""))),
            title=data.get("goods_name", data.get("goodsName", data.get("title", ""))),
            price=_parse_price(data.get("min_group_price", data.get("price", 0))),
            original_price=_parse_price(data.get("market_price", data.get("originalPrice", 0))),
            sales=int(data.get("sales", 0)),
            sales_text=str(data.get("salesTip", data.get("sales_tip", ""))),
            img_url=data.get("thumb_url", data.get("thumbUrl", data.get("image_url", ""))),
            shop_name=data.get("mall_name", data.get("mallName", "")),
            mall_id=str(data.get("mall_id", data.get("mallId", ""))),
            has_coupon=bool(data.get("has_coupon", data.get("hasCoupon", False))),
            free_shipping=bool(data.get("free_shipping", data.get("freeShipping", False))),
            raw=data,
        )


@dataclass
class ShopInfo:
    """拼多多店铺信息"""
    mall_id: str
    shop_name: str = ""
    shop_logo: str = ""
    rating: float = 0.0
    goods_count: int = 0
    description: str = ""
    certifications: list = field(default_factory=list)
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "ShopInfo":
        mall = data.get("mall", data.get("mallInfo", data))
        return cls(
            mall_id=str(mall.get("mallId", mall.get("mall_id", ""))),
            shop_name=mall.get("mallName", mall.get("shop_name", mall.get("mall_name", ""))),
            shop_logo=mall.get("mallLogo", mall.get("logo", "")),
            rating=float(mall.get("rating", mall.get("score", 0))),
            goods_count=int(mall.get("goodsCount", mall.get("goods_count", 0))),
            description=mall.get("description", mall.get("desc", "")),
            raw=mall,
        )


@dataclass
class ReviewInfo:
    """商品评价信息"""
    review_id: str = ""
    text: str = ""
    create_time: Optional[datetime] = None
    rating: int = 0            # 1-5 星
    user_name: str = ""
    user_avatar: str = ""
    reply_text: str = ""       # 商家回复
    images: list = field(default_factory=list)  # 评价图片
    specs: str = ""            # 购买的规格
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "ReviewInfo":
        return cls(
            review_id=str(data.get("reviewId", data.get("id", ""))),
            text=data.get("comment", data.get("text", data.get("content", ""))),
            create_time=_parse_timestamp(data.get("createTime", data.get("created_at", 0))),
            rating=int(data.get("star", data.get("rating", data.get("commentScore", 5)))),
            user_name=data.get("userName", data.get("user_name",
                         data.get("maskName", "匿名用户"))),
            user_avatar=data.get("userAvatar", data.get("user_avatar", "")),
            reply_text=data.get("replyText", data.get("reply", "")),
            images=data.get("images", data.get("pics", [])),
            specs=data.get("spec", data.get("skuInfo", data.get("specification", ""))),
            raw=data,
        )


@dataclass
class SearchResult:
    """搜索结果（混合: 商品 + 店铺）"""
    result_type: str = "product"  # "product" | "shop"
    product: Optional[ProductInfo] = None
    shop: Optional[ShopInfo] = None
    raw: dict = field(default_factory=dict, repr=False)


# ═══════════════════════════════════════════════════════════════
# Core Operations
# ═══════════════════════════════════════════════════════════════

def product_search(keyword: str, max_results: int = 20,
                   cookie_file: Optional[str] = None) -> list[ProductInfo]:
    """
    搜索商品.

    策略: Browser (XHR 拦截) 优先 — 拼多多 API 签名复杂

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        cookie_file: Cookie 文件路径

    Returns:
        ProductInfo 列表
    """
    log.info("Searching: '%s' (max=%d)", keyword, max_results)

    # Browser XHR 拦截 — 主力方案
    try:
        raw_items = browser.collect_products_via_xhr(
            keyword=keyword,
            cookie_file=cookie_file,
            max_products=max_results,
            headless=True
        )
        if raw_items:
            results = [ProductInfo.from_xhr(item) for item in raw_items[:max_results]]
            log.info("Search (XHR): %d results for '%s'", len(results), keyword)
            return results
    except Exception as e:
        log.warning("XHR search failed, falling back to DOM: %s", e)

    # Browser DOM 降级
    try:
        data = browser.open_search_page(keyword=keyword, cookie_file=cookie_file, headless=True)
        raw_products = data.get("products", [])
        results = []
        for p in raw_products:
            results.append(ProductInfo(
                goods_id=p.get("goods_id", ""),
                title=p.get("title", ""),
                price=_parse_price(p.get("price", 0)),
                sales=int(p.get("sales", 0) if isinstance(p.get("sales"), (int, float)) else 0),
                sales_text=str(p.get("sales_text", "")),
                img_url=p.get("img_url", ""),
                shop_name=p.get("shop_name", ""),
                mall_id=p.get("mall_id", ""),
            ))
        log.info("Search (DOM): %d results for '%s'", len(results), keyword)
        return results[:max_results]
    except Exception as e:
        log.error("Search failed completely: %s", e)
        return []


def product_detail(goods_id: str, cookie_file: Optional[str] = None) -> Optional[ProductInfo]:
    """
    获取商品详情.

    Args:
        goods_id: 商品 ID
        cookie_file: Cookie 文件路径

    Returns:
        ProductInfo 或 None
    """
    log.info("Fetching product: %s", goods_id)

    # Browser XHR 拦截
    try:
        raw = browser.collect_product_via_xhr(
            goods_id=goods_id,
            cookie_file=cookie_file,
            headless=True
        )
        if raw and raw.get("goods_id") or raw.get("goodsId") or raw.get("goodsDetail"):
            return ProductInfo.from_api(raw)
    except Exception as e:
        log.warning("XHR product detail failed: %s", e)

    # Browser DOM 降级
    try:
        data = browser.open_product_page(
            goods_id=goods_id,
            cookie_file=cookie_file,
            headless=True
        )
        product_data = data.get("product", {})
        if product_data:
            return ProductInfo(**product_data)
    except Exception as e:
        log.error("Product detail failed: %s", e)

    return None


def shop_info(mall_id: str, cookie_file: Optional[str] = None) -> Optional[ShopInfo]:
    """
    获取店铺信息.

    Args:
        mall_id: 店铺 ID
        cookie_file: Cookie 文件路径

    Returns:
        ShopInfo 或 None
    """
    log.info("Fetching shop: %s", mall_id)

    # Browser approach
    try:
        data = browser.open_mall_page(
            mall_id=mall_id,
            cookie_file=cookie_file,
            headless=True
        )
        shop_data = data.get("shop", {})
        if shop_data:
            return ShopInfo(
                mall_id=shop_data.get("mall_id", mall_id),
                shop_name=shop_data.get("shop_name", ""),
                shop_logo=shop_data.get("shop_logo", ""),
                rating=float(shop_data.get("rating", 0)),
                goods_count=int(shop_data.get("goods_count", 0)),
            )
    except Exception as e:
        log.error("Shop info failed: %s", e)

    return None


def product_reviews(goods_id: str, max_reviews: int = 50,
                    cookie_file: Optional[str] = None) -> list[ReviewInfo]:
    """
    获取商品评价列表.

    策略: API Channel 优先 → Browser Channel 降级

    Args:
        goods_id: 商品 ID
        max_reviews: 最大评价数
        cookie_file: Cookie 文件路径

    Returns:
        ReviewInfo 列表
    """
    log.info("Fetching reviews for: %s (max=%d)", goods_id, max_reviews)

    results = []
    page = 1
    max_pages = max((max_reviews + 19) // 20, 5)

    # API Channel
    for page_num in range(1, max_pages + 1):
        try:
            data = api.fetch_product_reviews(goods_id, page=page_num, size=min(20, max_reviews - len(results)))
            review_list = data.get("reviews", data.get("list", []))
            for r in review_list:
                results.append(ReviewInfo.from_api(r))
            if not data.get("has_more", False):
                break
            time.sleep(2.0)
        except Exception as e:
            log.warning("API reviews page %d failed: %s", page_num, e)
            break

    if results:
        log.info("Reviews (API): %d for %s", len(results), goods_id)
        return results[:max_reviews]

    # Browser fallback via product page
    try:
        data = browser.open_product_page(
            goods_id=goods_id,
            cookie_file=cookie_file,
            headless=True
        )
        reviews_data = data.get("reviews", [])
        for r in reviews_data:
            results.append(ReviewInfo(
                text=r.get("text", ""),
                user_name=r.get("user_name", "匿名"),
            ))
        log.info("Reviews (Browser): %d for %s", len(results), goods_id)
    except Exception as e:
        log.warning("Browser reviews failed: %s", e)

    return results[:max_reviews]


def category_list() -> list[dict]:
    """
    获取拼多多商品分类列表.

    Returns:
        [{"id": "...", "name": "...", "sub": [...]}, ...]
    """
    log.info("Fetching category list")
    # PDD categories are best fetched via browser
    try:
        browser_cat = browser.launch_browser(headless=True)
        from .browser import _create_context
        ctx = _create_context(browser_cat)
        page = ctx.new_page()
        page.goto("https://mobile.yangkeduo.com/catelist.html",
                  wait_until="domcontentloaded",
                  timeout=30000)
        time.sleep(3)

        cats = page.evaluate("""() => {
            try {
                const state = window.__INITIAL_STATE__;
                return state?.categoryList || state?.categories || [];
            } catch(e) { return []; }
        }""")

        page.close()
        ctx.close()
        return cats if cats else []
    except Exception as e:
        log.error("Category list failed: %s", e)
        return []


def mall_products(mall_id: str, max_results: int = 50,
                  cookie_file: Optional[str] = None) -> list[ProductInfo]:
    """
    获取店铺内所有商品.

    Args:
        mall_id: 店铺 ID
        max_results: 最大商品数
        cookie_file: Cookie 文件路径

    Returns:
        ProductInfo 列表
    """
    log.info("Fetching mall products: %s", mall_id)

    try:
        data = browser.open_mall_page(mall_id=mall_id, cookie_file=cookie_file, headless=True)
        products = data.get("products", [])
        return [ProductInfo.from_browser(p) for p in products[:max_results]]
    except Exception as e:
        log.error("Mall products failed: %s", e)
        return []


def flash_sale(max_results: int = 30,
               cookie_file: Optional[str] = None) -> list[ProductInfo]:
    """
    获取秒杀/限时特卖商品.

    Args:
        max_results: 最大结果数
        cookie_file: Cookie 文件路径

    Returns:
        ProductInfo 列表
    """
    log.info("Fetching flash sale products")

    try:
        data = api.fetch_promotions(activity_type="flash_sale")
        items = data.get("promotions", data.get("items", []))
        return [ProductInfo.from_api(item) for item in items[:max_results]]
    except Exception as e:
        log.warning("API flash sale failed: %s", e)

    # Browser fallback
    try:
        b = browser.launch_browser(headless=True)
        from .browser import _create_context
        ctx = _create_context(b, cookie_file)
        page = ctx.new_page()
        page.goto("https://mobile.yangkeduo.com/promotion.html",
                  wait_until="domcontentloaded",
                  timeout=30000)
        time.sleep(3)

        raw = page.evaluate("""() => {
            try { return window.__INITIAL_STATE__ || {}; } catch(e) { return {}; }
        }""")

        page.close()
        ctx.close()

        items = raw.get("promotions", raw.get("items", []))
        return [ProductInfo.from_api(item) for item in items[:max_results]]
    except Exception as e:
        log.error("Flash sale failed: %s", e)
        return []


def product_download(goods_id: str, output_dir: str = "./downloads/",
                     cookie_file: Optional[str] = None) -> dict:
    """
    下载商品信息（文本内容 + 图片链接）.

    Args:
        goods_id: 商品 ID
        output_dir: 输出目录
        cookie_file: Cookie 文件路径

    Returns:
        {"product": ProductInfo, "saved_to": str, "images_count": int}
    """
    log.info("Downloading product: %s", goods_id)
    os.makedirs(output_dir, exist_ok=True)

    prod = product_detail(goods_id, cookie_file=cookie_file)
    if not prod:
        return {"error": f"Product {goods_id} not found or fetch failed"}

    # 保存商品信息为 JSON
    output_file = os.path.join(output_dir, f"pdd_{goods_id}.json")
    data = {
        "goods_id": prod.goods_id,
        "title": prod.title,
        "price": prod.price,
        "original_price": prod.original_price,
        "sales": prod.sales,
        "sales_text": prod.sales_text,
        "img_url": prod.img_url,
        "images": prod.images,
        "shop_name": prod.shop_name,
        "mall_id": prod.mall_id,
        "desc": prod.desc,
        "specs": prod.specs,
        "has_coupon": prod.has_coupon,
        "free_shipping": prod.free_shipping,
        "rating": prod.rating,
        "downloaded_at": datetime.now(CST).isoformat(),
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "product": prod,
        "saved_to": output_file,
        "images_count": len(prod.images) if prod.images else 1 if prod.img_url else 0,
    }


# ═══════════════════════════════════════════════════════════════
# Monitor Operations
# ═══════════════════════════════════════════════════════════════

def monitor_product(goods_id: str, label: str = "") -> dict:
    """
    监控商品变化 (价格/销量/库存).

    基于 Hash 对比的快照变更检测.

    Args:
        goods_id: 商品 ID
        label: 监控标签

    Returns:
        {"label": str, "changed": bool, "new_posts": 0, ...}
    """
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "pdd_monitor")
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = label or f"product_{goods_id}"
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")

    try:
        prod = product_detail(goods_id)
    except Exception as e:
        log.error("Monitor product fetch failed: %s", e)
        return {"label": cache_key, "changed": False, "error": str(e)}

    if not prod:
        return {"label": cache_key, "changed": False, "error": "Product not found"}

    product_data = {
        "goods_id": prod.goods_id,
        "price": prod.price,
        "original_price": prod.original_price,
        "sales": prod.sales,
        "sales_text": prod.sales_text,
        "title": prod.title,
    }

    curr_hash = hashlib.sha256(
        json.dumps(product_data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    result = {
        "label": cache_key,
        "changed": False,
        "prev_hash": "",
        "curr_hash": curr_hash,
        "current_price": prod.price,
        "current_sales": prod.sales,
    }

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            prev = json.load(f)
        prev_hash = prev.get("hash", "")
        result["prev_hash"] = prev_hash
        if curr_hash != prev_hash:
            result["changed"] = True
            result["prev_price"] = prev.get("price")
            result["prev_sales"] = prev.get("sales")
    else:
        result["prev_hash"] = "(first run)"

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({
            "hash": curr_hash,
            "price": prod.price,
            "sales": prod.sales,
            "title": prod.title,
            "updated": datetime.now(CST).isoformat(),
        }, f, ensure_ascii=False, indent=2)

    return result


def monitor_shop(mall_id: str, label: str = "") -> dict:
    """
    监控店铺变化（商品数量等）.

    基于 Hash 对比.

    Args:
        mall_id: 店铺 ID
        label: 监控标签

    Returns:
        同 monitor_product 结构
    """
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "pdd_monitor")
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = label or f"shop_{mall_id}"
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")

    try:
        products = mall_products(mall_id, max_results=5)
    except Exception as e:
        return {"label": cache_key, "changed": False, "error": str(e)}

    shop_data = [{"goods_id": p.goods_id, "title": p.title, "price": p.price} for p in products]

    curr_hash = hashlib.sha256(
        json.dumps(shop_data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    result = {
        "label": cache_key,
        "changed": False,
        "prev_hash": "",
        "curr_hash": curr_hash,
        "total_products_seen": len(shop_data),
    }

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            prev = json.load(f)
        prev_hash = prev.get("hash", "")
        result["prev_hash"] = prev_hash
        if curr_hash != prev_hash:
            prev_ids = {p["goods_id"] for p in prev.get("products", [])}
            curr_ids = {p["goods_id"] for p in shop_data}
            new_ids = curr_ids - prev_ids
            result["changed"] = True
            result["new_products"] = len(new_ids)
    else:
        result["prev_hash"] = "(first run)"

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({
            "hash": curr_hash,
            "products": shop_data,
            "updated": datetime.now(CST).isoformat(),
        }, f, ensure_ascii=False, indent=2)

    return result


# ═══════════════════════════════════════════════════════════════
# Session Management (thin wrappers → session.py)
# ═══════════════════════════════════════════════════════════════

def login(method: str = "qr", cookie_file: Optional[str] = None) -> dict:
    """登录拼多多 (QR码扫码)."""
    from . import session as ses
    return ses.login(method=method, cookie_file=cookie_file)


def save_session(cookie_file: str) -> bool:
    """保存当前登录态."""
    from . import session as ses
    return ses.save_session(cookie_file)


def load_session(cookie_file: str) -> bool:
    """加载已保存的登录态."""
    from . import session as ses
    return ses.load_session(cookie_file)


def check_session() -> bool:
    """检查登录态是否有效."""
    from . import session as ses
    return ses.check_session()


# ═══════════════════════════════════════════════════════════════
# Internal Helpers
# ═══════════════════════════════════════════════════════════════

def _parse_price(val) -> float:
    """解析价格：'¥19.90' / 1990(分) → 19.9"""
    if isinstance(val, (int, float)):
        if val > 10000:
            return round(val / 100, 2)
        return float(val)
    if isinstance(val, str):
        val = val.replace("¥", "").replace("￥", "").replace("元", "").strip()
        try:
            price = float(val)
            if price > 10000:
                return round(price / 100, 2)
            return price
        except ValueError:
            m = re.search(r'(\d+\.?\d*)', val)
            if m:
                return float(m.group(1))
    return 0.0


def _parse_timestamp(ts) -> Optional[datetime]:
    """解析时间戳 → datetime"""
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            return datetime.fromisoformat(ts)
        if ts > 1e12:  # milliseconds
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=CST)
    except (TypeError, ValueError, OSError):
        return None
