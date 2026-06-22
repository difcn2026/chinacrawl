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
import random
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
class SkuInfo:
    """SKU 信息（规格+价格+库存）"""
    sku_id: str = ""
    spec_text: str = ""         # 规格组合文字，如 "颜色:白色;尺码:M"
    thumb_url: str = ""         # SKU 缩略图
    normal_price: float = 0.0   # 单独购买价
    group_price: float = 0.0    # 拼单价
    quantity: int = 0           # 库存
    is_default: bool = False    # 默认选中 SKU
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_raw(cls, data: dict) -> "SkuInfo":
        """从 API/SSR 原始 sku 数据构造"""
        # 规格文字
        specs = data.get("specs", data.get("spec", ""))
        if isinstance(specs, list):
            specs = ";".join(str(s.get("spec_value", s.get("value", s))) for s in specs if isinstance(s, dict))

        # 价格（PDD 内部分为计价单位）
        np_val = data.get("normal_price", data.get("normalPrice", 0))
        gp_val = data.get("group_price", data.get("groupPrice", 0))

        return cls(
            sku_id=str(data.get("sku_id", data.get("skuId", ""))),
            spec_text=str(specs),
            thumb_url=data.get("thumb_url", data.get("thumbUrl", "")),
            normal_price=_cent_to_yuan(np_val),
            group_price=_cent_to_yuan(gp_val),
            quantity=int(data.get("quantity", data.get("stock", 0))),
            is_default=bool(data.get("is_default", data.get("isDefault", False))),
            raw=data,
        )

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
    skus: list = field(default_factory=list)     # SKU 列表 [SkuInfo, ...]
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
    def from_feed(cls, data: dict) -> "ProductInfo":
        """从 hub/v3 Feed API 数据构造（价格单位为分，需÷100）"""
        price_val = data.get("group_price", data.get("normal_price", 0))
        orig_price_val = data.get("market_price", 0)
        # PDD hub/v3 价格单位为分（e.g. 249 = 2.49元）
        def _cent_to_yuan(v):
            if isinstance(v, (int, float)) and v > 0:
                return round(v / 100, 2)
            return 0.0
        return cls(
            goods_id=str(data.get("goods_id", "")),
            title=data.get("goods_name", data.get("short_name", "")),
            price=_cent_to_yuan(price_val),
            original_price=_cent_to_yuan(orig_price_val),
            sales=int(data.get("cnt", 0)),
            sales_text=str(data.get("sales_tip", "")),
            img_url=data.get("thumb_url", data.get("hd_thumb_url", "")),
            images=[data.get("hd_thumb_url", ""), data.get("thumb_url", "")] if data.get("hd_thumb_url") else [],
            shop_name=data.get("mall_name", ""),
            mall_id=str(data.get("mall_id", "")),
            has_coupon=bool(data.get("has_coupon", False)),
            raw=data,
        )


    @classmethod
    def from_search_ssr(cls, data: dict) -> "ProductInfo":
        """从搜索页 SSR (window.rawData.ssrListData) 数据构造"""
        sales = _parse_sales_text(data.get("sales_text", ""))
        return cls(
            goods_id=str(data.get("goods_id", "")),
            title=data.get("title", ""),
            price=float(data.get("price", 0)),
            sales=sales,
            sales_text=data.get("sales_text", ""),
            img_url=data.get("img_url", ""),
            images=[data.get("img_url", "")] if data.get("img_url") else [],
            raw=data,
        )

    @classmethod
    def from_detail_ssr(cls, data: dict) -> "ProductInfo":
        """从详情页 SSR (window.rawData 或 __INITIAL_STATE__) 数据构造"""
        # 兼容多种 SSR 嵌套结构
        g = data.get("goods", data.get("goodsDetail", data.get("goodsDetailVO", data)))
        if not isinstance(g, dict):
            g = data

        # 价格——SSR 中的价格通常是真实值（分→元）
        # SSR 中价格单位为分，统一转换为元
        def _to_yuan(v):
            if isinstance(v, (int, float)) and v > 0:
                return round(v / 100, 2)
            if isinstance(v, str):
                try: return round(float(v.replace("¥","").replace("￥","").strip()) / 100, 2)
                except: return 0.0
            return 0.0
        price_raw = g.get("min_on_sale_group_price",
                          g.get("minGroupPrice",
                          g.get("min_group_price",
                          g.get("price", g.get("mallPrice", 0)))))
        orig_price_raw = g.get("market_price", g.get("marketPrice", g.get("originalPrice", 0)))

        # 图片
        gallery = g.get("top_gallery", g.get("gallery", g.get("goods_gallery_urls", [])))
        if isinstance(gallery, str):
            gallery = [u.strip() for u in gallery.split(",") if u.strip()]
        elif not isinstance(gallery, list):
            gallery = []

        # SKU 列表
        sku_list = []
        raw_skus = data.get("sku", data.get("skuList", data.get("skus", [])))
        if not raw_skus:
            raw_skus = g.get("sku", g.get("skuList", g.get("skus", [])))
        if isinstance(raw_skus, list):
            for sku in raw_skus:
                if isinstance(sku, dict):
                    sku_list.append(SkuInfo.from_raw(sku))

        # 总库存
        stock = int(g.get("quantity", g.get("stock", g.get("totalStock", 0))))
        if not stock and sku_list:
            stock = sum(s.quantity for s in sku_list)

        return cls(
            goods_id=str(g.get("goods_id", g.get("goodsId", ""))),
            title=g.get("goods_name", g.get("goodsName", g.get("title", ""))),
            price=_to_yuan(price_raw),
            original_price=_to_yuan(orig_price_raw),
            sales=int(g.get("sold_quantity", g.get("sales", g.get("cnt", 0)))),
            sales_text=str(g.get("sales_tip", g.get("salesTip", ""))),
            img_url=gallery[0] if gallery else "",
            images=gallery,
            shop_name=g.get("mall_name", g.get("mallName", "")),
            mall_id=str(g.get("mall_id", g.get("mallId", data.get("mall_id", data.get("mallId", ""))))),
            skus=sku_list,
            specs=[s.spec_text for s in sku_list if s.spec_text],
            stock=stock,
            rating=float(g.get("avgRating", g.get("score", 0))),
            has_coupon=bool(g.get("has_coupon", data.get("has_coupon", False))),
            free_shipping=bool(g.get("free_shipping", data.get("freeShipping", False))),
            raw=data,
        )

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
            review_id=str(data.get("reviewId", data.get("id", data.get("review_id", "")))),
            text=data.get("comment", data.get("text", data.get("content", ""))),
            create_time=_parse_timestamp(data.get("createTime", data.get("created_at", data.get("create_time", 0)))),
            rating=int(data.get("star", data.get("rating", data.get("commentScore", 5)))),
            user_name=data.get("userName", data.get("user_name",
                         data.get("maskName", "匿名用户"))),
            user_avatar=data.get("userAvatar", data.get("user_avatar", "")),
            reply_text=data.get("replyText", data.get("reply", data.get("reply_text", ""))),
            images=data.get("images", data.get("pics", [])),
            specs=data.get("spec", data.get("skuInfo", data.get("specification", data.get("specs", "")))),
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

def product_feed(max_sn: int = 20, max_pages_per_sn: int = 2,
                 headless: bool = True) -> list[ProductInfo]:
    """
    批量采集首页推荐流商品（无需登录）。

    通过 hub/v3 Feed API 拉取，page_sn 10002-10020，
    每个 sn 翻页 max_pages_per_sn 次，每页约 20 商品。

    Args:
        max_sn: 拉取的 page_sn 数量（默认20）
        max_pages_per_sn: 每 sn 翻页数（默认2）
        headless: 是否无头模式

    Returns:
        ProductInfo 列表
    """
    log.info("Feed: page_sn 10002..%d x %d pages",
             10002 + max_sn - 1, max_pages_per_sn)
    feed = browser.open_feed(max_sn=max_sn, max_pages_per_sn=max_pages_per_sn,
                             headless=headless)
    products = [ProductInfo.from_feed(p) for p in feed["products"]]
    log.info("Feed: %d products (%d API calls)", len(products), feed["api_calls"])
    return products


def product_search(keyword: str, max_results: int = 20,
                   cookie_file: Optional[str] = None) -> list[ProductInfo]:
    """
    搜索商品.

    策略:
      1. 搜索页 SSR（需登录 cookie）— 精准搜索，支持翻页
      2. Feed 通道（hub/v3 批量拉取+关键词过滤）— 无需登录，降级方案
      3. Browser XHR 拦截 — 备用
      4. Browser DOM — 最终降级

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
        cookie_file: Cookie 文件路径

    Returns:
        ProductInfo 列表
    """
    
    # ═══ 搜索页 SSR（需登录，精准搜索+翻页）═══
    if cookie_file and os.path.exists(cookie_file):
        try:
            all_prods = []
            seen = set()
            sr = browser.open_search_page(keyword, cookie_file=cookie_file, headless=True)
            for p in sr.get("products", []):
                gid = p.get("goods_id", "")
                if gid and gid not in seen:
                    seen.add(gid); all_prods.append(p)
            has_more = sr.get("has_more", False)
            flip = sr.get("flip", "")
            pg = 2
            max_pg = max(1, max_results // 20 + 1)
            while has_more and len(all_prods) < max_results and pg <= max_pg:
                time.sleep(random.uniform(2.0, 4.0))
                more = browser.open_search_page(keyword, cookie_file=cookie_file, flip=flip, headless=True)
                new_p = more.get("products", [])
                if not new_p: break
                for p in new_p:
                    gid = p.get("goods_id", "")
                    if gid and gid not in seen:
                        seen.add(gid); all_prods.append(p)
                has_more = more.get("has_more", False)
                flip = more.get("flip", ""); pg += 1
            if all_prods:
                results = [ProductInfo.from_search_ssr(p) for p in all_prods[:max_results]]
                log.info("Search (SSR): %d results for '%s'", len(results), keyword)
                return results
        except Exception as e:
            log.warning("SSR search failed, fallback to feed: %s", e)
    log.info("Searching: '%s' (max=%d)", keyword, max_results)

    # ━━ Feed 通道（无需登录，2026-06-13 攻克）━━
    try:
        sn = min(20, max(5, max_results // 2))  # 搜索结果越多，拉取越广
        pp = max(1, max_results // 40 + 1)
        feed = browser.open_feed(max_sn=sn, max_pages_per_sn=pp, headless=True)
        all_products = feed["products"]

        # 关键词过滤
        keywords = keyword.lower().split()
        matched = []
        for p in all_products:
            title = (p.get("goods_name", "") + " " + p.get("short_name", "")).lower()
            if all(kw in title for kw in keywords):
                matched.append(p)

        if matched:
            results = [ProductInfo.from_feed(p) for p in matched[:max_results]]
            log.info("Search (feed): %d matched / %d fetched for '%s'",
                     len(results), len(all_products), keyword)
            return results

        # 无精确匹配时尝试单字匹配
        matched_single = []
        for p in all_products:
            title = (p.get("goods_name", "") + " " + p.get("short_name", "")).lower()
            if any(kw in title for kw in keywords):
                matched_single.append(p)
        if matched_single:
            results = [ProductInfo.from_feed(p) for p in matched_single[:max_results]]
            log.info("Search (feed): %d partial match for '%s'", len(results), keyword)
            return results

        # 完全无匹配，返回空列表
        log.info("Search (feed): no match for '%s' in %d products", keyword, len(all_products))
        return []
    except Exception as e:
        log.warning("Feed search failed, falling back to XHR: %s", e)

    # ━━ Browser XHR 拦截 — 备用方案 ━━
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
    """获取商品详情。通过 oak/integration/render API（需登录 cookie）。
    注意：PDD 移动端详情页价格被混淆，详细价格请从搜索结果获取。"""
    if cookie_file and os.path.exists(cookie_file):
        try:
            import httpx
            with open(cookie_file, encoding="utf-8") as f:
                session_data = json.load(f)
            cookies = {c["name"]: c["value"] for c in session_data.get("cookies", [])}
            pdduid = cookies.get("pdd_user_id", "")

            body = {"page_version": 7, "goods_id": int(goods_id), "page_from": 0,
                    "hostname": "mobile.yangkeduo.com",
                    "client_time": int(time.time() * 1000),
                    "extend_map": {}, "page_sn": 10014,
                    "page_id": f"10014_{int(time.time()*1000)}_api",
                    "front_supports": ["community_purchase", "split_info_section",
                                       "render_opt_2022", "new_price_bottom"]}

            resp = httpx.post(
                f"{API_BASE_MOBILE}/proxy/api/api/oak/integration/render",
                params={"pdduid": pdduid}, json=body, cookies=cookies, timeout=30,
                headers={"Content-Type": "application/json;charset=UTF-8",
                         "Accept": "application/json",
                         "Origin": "https://mobile.yangkeduo.com",
                         "Referer": f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"})

            if resp.status_code == 200:
                data = resp.json()
                g = data.get("goods", {})

                ui_price = data.get("ui", {}).get("new_price_section", {})
                price_str = ui_price.get("price", "")
                try:
                    price_val = -1.0 if "?" in price_str else float(price_str)
                except (ValueError, TypeError):
                    price_val = -1.0

                gallery = [img.get("url", "") for img in g.get("gallery", [])]
                # Parse SKUs from API response
                sku_list = []
                raw_skus = data.get("sku", [])
                if isinstance(raw_skus, list):
                    for sku in raw_skus:
                        if isinstance(sku, dict):
                            sku_list.append(SkuInfo.from_raw(sku))

                stock = int(g.get("quantity", g.get("stock", 0)))
                if not stock and sku_list:
                    stock = sum(s.quantity for s in sku_list)

                result = ProductInfo(
                    goods_id=str(goods_id),
                    title=g.get("goods_name", ""),
                    price=price_val,
                    sales=int(g.get("sold_quantity", 0)),
                    img_url=gallery[0] if gallery else "",
                    images=gallery,
                    mall_id=str(g.get("mall_id", "")),
            skus=sku_list,
            specs=[s.spec_text for s in sku_list if s.spec_text],
                    stock=stock,
                    raw={"api_data": data})

                log.info("Product detail (API): %s - %d imgs, %d skus, price=%s",
                         result.title[:30], len(gallery), len(sku_list), price_val)
                return result

        except Exception as e:
            log.warning("API product detail failed: %s", e)

    # Browser fallback
    try:
        data = browser.open_product_page(goods_id=goods_id, cookie_file=cookie_file, headless=True)
        product_data = data.get("product", {})
        if product_data:
            return ProductInfo(**product_data)
    except Exception as e:
        log.error("Product detail failed: %s", e)

    return None


def product_detail_ssr(goods_id: str, cookie_file: Optional[str] = None, headless: bool = True) -> Optional[ProductInfo]:
    """通过浏览器 SSR 获取商品详情（含 SKU 和真实价格）。
    
    与 product_detail 不同，本函数优先使用浏览器 SSR 通道，
    可获取到 API 中被混淆的真实价格和完整 SKU 列表。
    """
    log.info("Fetching product via SSR: %s", goods_id)
    try:
        data = browser.open_product_page(goods_id=goods_id, cookie_file=cookie_file, headless=headless)
        product_data = data.get("product", {})
        if product_data and product_data.get("title"):
            result = ProductInfo.from_detail_ssr(product_data.get("raw", product_data))
            result.goods_id = goods_id
            # Merge shop info if available
            shop_data = data.get("shop", {})
            if shop_data:
                result.shop_name = shop_data.get("shop_name", result.shop_name)
            # Merge reviews if available
            reviews = data.get("reviews", [])
            if reviews:
                result.raw["reviews_preview"] = reviews
            log.info("Product detail (SSR): %s - %d imgs, %d skus, price=%s",
                     result.title[:30], len(result.images), len(result.skus), result.price)
            return result
    except Exception as e:
        log.error("Product detail SSR failed: %s", e)
    return None


def product_detail_full(goods_id: str, cookie_file: Optional[str] = None, headless: bool = True) -> Optional[ProductInfo]:
    """获取商品详情（API + SSR 融合）。
    
    策略：
    1. API 先行获取基础信息（快， ~2s）
    2. SSR 补充 SKU + 真实价格（慢， ~5s）
    3. 合并结果
    """
    log.info("Fetching product full: %s", goods_id)

    result = None

    # Step 1: API
    try:
        result = product_detail(goods_id, cookie_file)
    except Exception as e:
        log.warning("API detail failed, will try SSR: %s", e)

    # Step 2: SSR enrichment (SKU + real price)
    try:
        ssr_data = browser.open_product_page(goods_id=goods_id, cookie_file=cookie_file, headless=headless)
        ssr_product = ssr_data.get("product", {})
        ssr_raw = ssr_product.get("raw", ssr_product)

        if not result:
            if ssr_product.get("title"):
                result = ProductInfo.from_detail_ssr(ssr_raw)
                result.goods_id = goods_id
        else:
            # Merge: use SSR for SKU + real price
            ssr_parsed = ProductInfo.from_detail_ssr(ssr_raw) if ssr_raw else None
            if ssr_parsed:
                if ssr_parsed.skus:
                    result.skus = ssr_parsed.skus
                    result.specs = ssr_parsed.specs
                    log.info("Merged %d skus from SSR", len(ssr_parsed.skus))
                if ssr_parsed.price > 0 and (result.price < 0 or "?" in str(result.price)):
                    result.price = ssr_parsed.price
                    log.info("Replaced obfuscated price with SSR: %s", ssr_parsed.price)
                if ssr_parsed.original_price > 0 and result.original_price <= 0:
                    result.original_price = ssr_parsed.original_price
                if ssr_parsed.stock > 0:
                    result.stock = ssr_parsed.stock
                if not result.images and ssr_parsed.images:
                    result.images = ssr_parsed.images
                    result.img_url = ssr_parsed.img_url
                # Merge raw data
                result.raw["ssr_data"] = ssr_raw
    except Exception as e:
        log.warning("SSR enrichment failed: %s", e)

    # Step 3: Shop info merge
    if result and not result.shop_name:
        try:
            # Reuse ssr_data from Step 2 if available, otherwise fetch
            ssr_shop = ssr_data.get("shop", {})
            if not ssr_shop:
                ssr_data_shop = browser.open_product_page(goods_id=goods_id, cookie_file=cookie_file, headless=headless)
                ssr_shop = ssr_data_shop.get("shop", {})
            shop = ssr_shop
            if shop:
                result.shop_name = shop.get("shop_name", "")
                result.mall_id = shop.get("mall_id", result.mall_id)
        except Exception:
            pass

    return result


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

    # Browser fetch (primary: in-browser API call bypasses anti_content)
    try:
        raw_reviews = browser.fetch_reviews_via_browser(
            goods_id=goods_id, max_reviews=max_reviews,
            cookie_file=cookie_file, headless=True
        )
        for r in raw_reviews:
            results.append(ReviewInfo.from_api(r))
        log.info("Reviews (browser fetch): %d for %s", len(results), goods_id)
    except Exception as e:
        log.warning("Browser fetch reviews failed, trying API: %s", e)
        # API fallback
        for page_num in range(1, min(max_pages, 3)):
            try:
                data = api.fetch_product_reviews(goods_id, page=page_num, size=min(20, max_reviews - len(results)))
                review_list = data.get("reviews", data.get("list", []))
                for r in review_list:
                    results.append(ReviewInfo.from_api(r))
                if not data.get("has_more", False):
                    break
                time.sleep(2.0)
            except Exception:
                break
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
        data = browser.open_mall_with_products(mall_id=mall_id, cookie_file=cookie_file,
                                                max_products=max_results, headless=True)
        products = data.get("products", [])
        return [ProductInfo.from_search_ssr(p) for p in products[:max_results]]
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



def _cent_to_yuan(val) -> float:
    """分→元（PDD API/SSR 价格单位为分，如 8990 → 89.90）"""
    if isinstance(val, (int, float)):
        if val > 0:
            return round(val / 100, 2)
        return 0.0
    if isinstance(val, str):
        val = val.replace("¥", "").replace("￥", "").replace("元", "").strip()
        try:
            return round(float(val) / 100, 2)
        except ValueError:
            return 0.0
    return 0.0
def _parse_sales_text(text: str) -> int:
    """解析 PDD 销量文案: '已拼1.1万+件' -> 11000, '全店总售900万+' -> 9000000"""
    import re
    text = text.strip().replace("+", "").replace(",", "")
    m = re.search(r'(\d+\.?\d*)', text)
    if not m:
        return 0
    num = float(m.group(1))
    if '万' in text:
        num *= 10000
    return int(num)
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
