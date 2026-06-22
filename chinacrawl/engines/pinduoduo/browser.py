# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Playwright Browser Layer
# Created: 2026-06-08

"""
Playwright 浏览器交互层 (拼多多主力通道).

拼多多 Web 版反爬非常严格，API 层仅用于轻量场景。
本层通过注入反检测脚本模拟真实移动端浏览行为来绕过检测。

策略:
  1. 使用 Android Chrome mobile UA + 移动端视口
  2. 注入 ANTI_DETECT_JS 隐藏自动化特征
  3. 模拟人类触摸滚动行为
  4. 优先从 SSR 数据 (window.__INITIAL_STATE__) 提取
  5. 降级到 DOM 解析 (query_selector)
  6. XHR 拦截作为备用方案
"""

import json
import logging
import os
import time as _time
from typing import Optional

from .config import (
    BROWSER_ARGS, BROWSER_TIMEOUT, BROWSER_NAV_TIMEOUT,
    random_ua, RATE_LIMITS as RL,
)
from ..core import launch_browser as _core_launch, close_browser as _core_close, create_context as _core_create_context
from ..core.anti_detect import ANTI_DETECT_JS, CONTEXT_OVERRIDES, random_delay, random_touch_events, random_scroll_steps

log = logging.getLogger("chinacrawl.pinduoduo.browser")

# ━━━ Playwright singleton ━━━
# Delegated to core.browser
def launch_browser(headless: bool = True):
    return _core_launch(headless=headless)
def close_browser():
    _core_close()
def _create_context(browser, cookie_file = None):
    return _core_create_context(browser, cookie_file=cookie_file)


# ━━━ Page Navigation ━━━



def search_deep(keyword: str, cookie_file: Optional[str] = None,
                max_pages: int = 5, headless: bool = True) -> dict:
    """?????flip token ???????? N ??
    
    ??????1?~30???????????????
    """
    all_products = []
    seen_ids = set()
    flip_token = ""
    pages_done = 0
    total_redirects = 0
    
    while pages_done < max_pages:
        data = open_search_page(keyword, cookie_file=cookie_file,
                                headless=headless, flip=flip_token)
        
        # Check for errors
        if data.get("error"):
            log.warning("Page %d error: %s", pages_done + 1, data["error"])
            if "login" in str(data["error"]).lower():
                break
            if "redirect" in str(data["error"]).lower():
                total_redirects += 1
                if total_redirects >= 2:
                    break
                _time.sleep(random_delay(3000, 6000) / 1000)
                continue
        
        products = data.get("products", [])
        if not products:
            log.info("No more products on page %d", pages_done + 1)
            break
        
        new_count = 0
        for p in products:
            gid = str(p.get("goods_id", p.get("goodsId", "")))
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                all_products.append(p)
                new_count += 1
        
        pages_done += 1
        has_more = data.get("has_more", False)
        flip_token = data.get("flip", "")
        
        log.info("Deep search page %d: %d new, total=%d, has_more=%s, flip=%s",
                 pages_done, new_count, len(all_products), has_more,
                 flip_token[:30] if flip_token else "none")
        
        if not has_more or not flip_token or new_count == 0:
            break
        
        _time.sleep(random_delay(2000, 4000) / 1000)
    
    return {
        "products": all_products,
        "total": len(all_products),
        "pages": pages_done,
        "keyword": keyword,
    }

def open_search_page(keyword: str, cookie_file: Optional[str] = None,
                     headless: bool = True, flip: str = "") -> dict:
    """
    通过浏览器执行搜索，提取商品列表.

    Args:
        keyword: 搜索关键词
        cookie_file: Cookie 文件路径
        headless: 是否无头模式

    Returns:
        {
            "products": [{goods_id, title, price, sales, img_url, shop_name, ...}, ...],
            "total_count": int,
            "has_more": bool
        }
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()

    try:
        # 导航到搜索结果页
        import urllib.parse
        search_url = f"https://mobile.yangkeduo.com/search_result.html?search_key={urllib.parse.quote(keyword)}"
        if flip:
            search_url += f"&flip={urllib.parse.quote(flip)}"
        log.info("Navigating to search: %s", search_url)

        page.goto(search_url,
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

        # 模拟人类行为：随机延迟 + 触摸
        _time.sleep(random_delay(1500, 3000) / 1000)
        # Check for redirect (login wall or auto-navigation)
        if "search_result" not in page.url:
            if "login" in page.url:
                return {"products": [], "total_count": 0, "has_more": False, "error": "redirected to login"}
            log.warning("Page redirected away from search: %s", page.url[:120])
            return {"products": [], "total_count": 0, "has_more": False, "error": "redirected"}

        # 从页面提取数据
        data = _extract_search_results(page)
        return data

    finally:
        page.close()
        context.close()


def open_product_page(goods_id: str, cookie_file: Optional[str] = None,
                      headless: bool = True) -> dict:
    """
    通过浏览器打开商品详情页，提取完整信息.

    Args:
        goods_id: 商品 ID
        cookie_file: Cookie 文件路径
        headless: 是否无头模式

    Returns:
        {
            "product": {goods_id, title, price, original_price, sales, stock,
                       images, desc, specs, ...},
            "shop": {mall_id, shop_name, rating, ...},
            "reviews": [{...}, ...]
        }
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()

    try:
        url = f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"
        log.info("Navigating to product: %s", url)

        page.goto(url,
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

        _time.sleep(random_delay(1500, 3500) / 1000)
        random_touch_events(page)

        # 等待商品详情加载
        try:
            page.wait_for_selector(".goods-detail, [class*=\"goods-title\"], .price",
                                   timeout=20000)
        except Exception:
            log.warning("Product detail selectors not found")

        # 滚动加载评价区域
        _human_scroll(page, scrolls=5)

        # 尝试点击评价 tab
        try:
            review_tab = page.query_selector('text=评价, [data-tab="review"], .review-tab')
            if review_tab:
                review_tab.click()
                _time.sleep(2)
        except Exception:
            pass

        data = _extract_product_detail(page, goods_id)
        return data

    finally:
        page.close()
        context.close()


def open_mall_page(mall_id: str, cookie_file: Optional[str] = None,
                   headless: bool = True) -> dict:
    """
    通过浏览器打开店铺页面，提取店铺信息和商品列表.

    Args:
        mall_id: 店铺 ID
        cookie_file: Cookie 文件路径
        headless: 是否无头模式

    Returns:
        {
            "shop": {mall_id, shop_name, logo, rating, goods_count, ...},
            "products": [{...}, ...]
        }
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()

    try:
        url = f"https://mobile.yangkeduo.com/mall_page.html?mall_id={mall_id}"
        log.info("Navigating to mall: %s", url)

        page.goto(url,
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

        _time.sleep(random_delay(1500, 3000) / 1000)
        random_touch_events(page)

        _human_scroll(page, scrolls=4)

        data = _extract_mall_page(page, mall_id)
        return data

    finally:
        page.close()
        context.close()


# ━━━ XHR Interception ━━━

def collect_products_via_xhr(keyword: str, cookie_file: str = None,
                              max_products: int = 0, headless: bool = True) -> list[dict]:
    """
    通过拦截浏览器 XHR API 调用收集搜索结果中的所有商品.

    浏览器内部发出正确签名的 API 请求，我们拦截响应。
    绕过 anti-content 逆向工程。

    Args:
        keyword: 搜索关键词
        cookie_file: Cookie 文件路径
        max_products: 最大采集数量 (0=不限)
        headless: 无头模式

    Returns:
        List of product dicts
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file=cookie_file)
    page = context.new_page()

    collected = []
    seen_ids = set()

    def _on_response(response):
        url = response.url
        if '/proxy/api/api/search/' not in url:
            return
        if response.status != 200:
            return
        try:
            data = response.json()
        except Exception:
            return
        items = data.get('items', data.get('goods_list', []))
        for item in items:
            gid = str(item.get('goods_id', item.get('goodsId', '')))
            if gid and gid not in seen_ids:
                seen_ids.add(gid)
                collected.append(item)

    page.on("response", _on_response)

    try:
        search_url = f"https://mobile.yangkeduo.com/search_result.html?search_key={keyword}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
        _time.sleep(3)

        log.info("XHR collection (search='%s'): initial count=%d", keyword, len(collected))

        no_new = 0
        prev_count = 0

        for round_num in range(60):
            # 触发滚动加载
            page.evaluate("""() => {
                window.scrollTo(0, document.body.scrollHeight);
            }""")
            _time.sleep(2.0)

            # 模拟触摸滑动
            page.evaluate("""() => {
                const container = document.querySelector('.search-results, [data-active="search-list"], .goods-list');
                if (container) {
                    container.scrollTo(0, container.scrollHeight);
                }
            }""")
            _time.sleep(1.5)

            total = len(collected)
            if total > prev_count:
                prev_count = total
                no_new = 0
                if total % 20 == 0:
                    log.info("XHR collection: %d products", total)
            else:
                no_new += 1

            if no_new >= 10:
                log.info("XHR collection complete: %d products", total)
                break

            if max_products > 0 and total >= max_products:
                log.info("XHR collection: reached max=%d", max_products)
                break

    finally:
        page.close()
        context.close()

    return collected


def collect_product_via_xhr(goods_id: str, cookie_file: str = None,
                             headless: bool = True) -> dict:
    """
    通过拦截 XHR 获取单个商品详情.

    Args:
        goods_id: 商品 ID
        cookie_file: Cookie 文件路径
        headless: 无头模式

    Returns:
        商品详情 dict
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file=cookie_file)
    page = context.new_page()

    result = {}

    def _on_response(response):
        url = response.url
        if '/proxy/api/api/oak/' not in url and '/proxy/api/api/goods/' not in url:
            return
        if response.status != 200:
            return
        try:
            data = response.json()
            if not result:
                result.update(data)
        except Exception:
            pass

    page.on("response", _on_response)

    try:
        url = f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"
        page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
        _time.sleep(4)

        # 补充 SSR 数据
        if not result:
            ssr_data = page.evaluate("""() => {
                try {
                    const state = window.__INITIAL_STATE__;
                    return state ? JSON.parse(JSON.stringify(state)) : null;
                } catch(e) {
                    return null;
                }
            }""")
            if ssr_data:
                result.update(ssr_data)

    finally:
        page.close()
        context.close()

    return result


# ━━━ DOM Extraction Helpers ━━━

def _human_scroll(page, scrolls: int = 3):
    """模拟人类滚动行为"""
    for i in range(scrolls):
        _time.sleep(random_delay(500, 1500) / 1000)
        page.evaluate("""() => {
            const scrollY = 200 + Math.floor(Math.random() * 400);
            window.scrollBy(0, scrollY);
        }""")


def _extract_search_results(page) -> dict:
    """从搜索结果页提取商品列表"""
    result = {"products": [], "total_count": 0, "has_more": False}

    try:
        # 优先从 SSR 数据提取
        # PDD search uses window.rawData SSR (only accessible when logged in)
        raw = page.evaluate("""() => {
            var rd = window.rawData;
            if (!rd) return null;
            var ssr = rd.stores && rd.stores.store && rd.stores.store.data && rd.stores.store.data.ssrListData;
            if (!ssr) return null;
            var list = ssr.list || [];
            return {
                list: list,
                page: ssr.page,
                lastPage: ssr.lastPage,
                flip: ssr.flip,
                filterTotalNumStr: ssr.filterTotalNumStr,
                searchKey: ssr.searchKey
            };
        }""")

        if raw and raw.get("list"):
            for item in raw["list"]:
                price_fen = item.get("price", 0)
                price_yuan = price_fen / 100.0 if price_fen else 0.0

                product = {
                    "goods_id": str(item.get("goodsID", "")),
                    "title": item.get("goodsName", ""),
                    "price": price_yuan,
                    "price_info": item.get("priceInfo", ""),
                    "sales_text": item.get("salesTip", ""),
                    "sales": _parse_count(item.get("salesTip", "")),
                    "img_url": item.get("imgUrl", ""),
                    "tags": [t.get("text", "") for t in item.get("tagList", [])],
                }
                if product["goods_id"]:
                    result["products"].append(product)

            total_str = raw.get("filterTotalNumStr", "")
            result["total_count"] = _parse_count(total_str) or len(result["products"])
            result["has_more"] = not raw.get("lastPage", True)
            result["flip"] = raw.get("flip", "")
            result["page"] = raw.get("page", 1)
            return result
    except Exception as e:
        log.debug("SSR extraction failed, falling back to DOM: %s", e)

    # DOM 降级方案 (class name patterns observed on PDD)
    try:
        items = page.query_selector_all(
            '.goods-item, [class*="GoodsItem"], .search-result-item, li[data-goods_id]'
        )
        for item in items:
            product = {}
            try:
                # 商品标题
                title_el = item.query_selector('[class*="title"], [class*="name"], .goods-title, .goods-name')
                if title_el:
                    product["title"] = title_el.inner_text().strip()

                # 价格
                price_el = item.query_selector('[class*="price"], .goods-price, .price')
                if price_el:
                    price_text = price_el.inner_text().strip()
                    product["price"] = _parse_price(price_text)

                # 销量
                sales_el = item.query_selector('[class*="sales"], [class*="sold"], .goods-sales')
                if sales_el:
                    product["sales_text"] = sales_el.inner_text().strip()
                    product["sales"] = _parse_count(sales_el.inner_text())

                # 图片
                img_el = item.query_selector('img')
                if img_el:
                    product["img_url"] = img_el.get_attribute("src") or img_el.get_attribute("data-src") or ""

                # 商品ID (从链接提取)
                link_el = item.query_selector('a')
                if link_el:
                    href = link_el.get_attribute("href") or ""
                    import re
                    m = re.search(r'goods_id=(\d+)', href)
                    if m:
                        product["goods_id"] = m.group(1)

                if product.get("title"):
                    result["products"].append(product)
            except Exception:
                continue

    except Exception as e:
        log.warning("DOM extraction failed: %s", e)

    return result



def _extract_product_ssr(page) -> dict:
    """从商品详情页 SSR 提取完整数据（SKU+真实价格+店铺）"""
    js_code = """() => {
    // PDD 详情页 SSR 数据多层提取
    const result = { product: null, shop: null };
    
    // 1) window.rawData —— PDD 主通道（搜索已验证）
    try {
        const rd = window.rawData;
        if (rd) {
            const stores = rd.stores || rd;
            // 遍历所有 store key 找商品数据
            for (const k of Object.keys(stores)) {
                const store = stores[k];
                if (!store || !store.data) continue;
                const d = store.data;
                // 商品信息
                const g = d.goods || d.goodsDetail || d.goodsDetailVO || d.goodsDetailData || null;
                if (g && (g.goods_name || g.goodsName || g.title)) {
                    result.product = d;
                    result.product.goods = g;
                }
                // 店铺信息
                if (d.mallBasicInfo || d.mall || d.shop) {
                    result.shop = d.mallBasicInfo || d.mall || d.shop;
                }
                if (result.product) break;
            }
        }
    } catch(e) {}
    
    // 2) window.__INITIAL_STATE__ —— 降级
    if (!result.product) {
        try {
            const st = window.__INITIAL_STATE__;
            if (st) {
                const g = st.goods || st.goodsDetail || st.goodsDetailVO || null;
                if (g && (g.goods_name || g.goodsName || g.title)) {
                    result.product = st;
                    result.product.goods = g;
                }
                if (st.mallBasicInfo || st.mall || st.shop) {
                    result.shop = st.mallBasicInfo || st.mall || st.shop;
                }
            }
        } catch(e) {}
    }
    
    // 3) 从内嵌 script 中搜索 SSR JSON（最后降级）
    if (!result.product) {
        try {
            const scripts = document.querySelectorAll('script');
            for (const s of scripts) {
                const t = s.textContent || '';
                if (t.includes('"goods"') && t.includes('"goods_id"')) {
                    // 尝试提取 window.rawData = ... 或 __INITIAL_STATE__ = ...
                    const m = t.match(/(?:window\.rawData|__INITIAL_STATE__)\s*=\s*({[\s\S]*?});?
/);
                    if (m) {
                        try {
                            const parsed = JSON.parse(m[1]);
                            const g = parsed.goods || parsed.goodsDetail || parsed.goodsDetailVO;
                            if (g && (g.goods_name || g.goodsName || g.goods_id || g.goodsId)) {
                                result.product = parsed;
                            }
                        } catch(pe) {}
                    }
                }
            }
        } catch(e) {}
    }
    
    return JSON.parse(JSON.stringify(result));
}"""
    
    try:
        raw = page.evaluate(js_code)
    except Exception as e:
        log.debug("SSR evaluate failed: %s", e)
        return {"product": {}, "shop": {}}
    
    if not raw:
        return {"product": {}, "shop": {}}
    
    out = {"product": {}, "shop": {}}
    
    product_raw = raw.get("product")
    if product_raw:
        g = product_raw.get("goods", product_raw)
        if isinstance(g, dict):
            # 价格——SSR中的价格通常是真实值（分→元）
            price_raw_val = g.get("min_on_sale_group_price", g.get("minGroupPrice",
                                  g.get("min_group_price", g.get("price", g.get("mallPrice", 0)))))
            orig_price_raw_val = g.get("market_price", g.get("marketPrice", g.get("originalPrice", 0)))
            
            # 图片
            gallery = g.get("top_gallery", g.get("gallery", g.get("goods_gallery_urls", [])))
            if isinstance(gallery, str):
                gallery = [u.strip() for u in gallery.split(",") if u.strip()]
            elif not isinstance(gallery, list):
                gallery = []
            
            # SKU 列表
            skus = product_raw.get("sku", product_raw.get("skuList", product_raw.get("skus", [])))
            if not skus:
                skus = g.get("sku", g.get("skuList", g.get("skus", [])))
            
            sku_list = []
            if isinstance(skus, list):
                for sku in skus:
                    if isinstance(sku, dict):
                        spec_text = sku.get("specs", sku.get("spec", ""))
                        if isinstance(spec_text, list):
                            spec_text = ";".join(
                                str(s.get("spec_value", s.get("value", s))) 
                                for s in spec_text if isinstance(s, dict))
                        
                        sku_list.append({
                            "sku_id": str(sku.get("sku_id", sku.get("skuId", ""))),
                            "spec_text": str(spec_text),
                            "thumb_url": sku.get("thumb_url", sku.get("thumbUrl", "")),
                            "normal_price": _parse_price(sku.get("normal_price", sku.get("normalPrice", 0))),
                            "group_price": _parse_price(sku.get("group_price", sku.get("groupPrice", 0))),
                            "quantity": int(sku.get("quantity", sku.get("stock", 0))),
                            "is_default": bool(sku.get("is_default", sku.get("isDefault", False))),
                        })
            
            # 总库存
            stock = int(g.get("quantity", g.get("stock", g.get("totalStock", 0))))
            if not stock and sku_list:
                stock = sum(s["quantity"] for s in sku_list)
            
            out["product"] = {
                "goods_id": str(g.get("goods_id", g.get("goodsId", ""))),
                "title": g.get("goods_name", g.get("goodsName", g.get("title", ""))),
                "price": _parse_price(price_raw_val),
                "original_price": _parse_price(orig_price_raw_val),
                "sales": int(g.get("sold_quantity", g.get("sales", g.get("cnt", 0)))),
                "sales_text": str(g.get("salesTip", g.get("sales_tip", ""))),
                "img_url": gallery[0] if gallery else "",
                "images": gallery,
                "shop_name": g.get("mall_name", g.get("mallName", product_raw.get("mall_name", product_raw.get("mallName", "")))),
                "mall_id": str(g.get("mall_id", g.get("mallId", product_raw.get("mall_id", product_raw.get("mallId", ""))))),
                "desc": str(g.get("goods_desc", g.get("desc", "")))[:3000],
                "skus": sku_list,
                "specs": [s["spec_text"] for s in sku_list if s.get("spec_text")],
                "stock": stock,
                "rating": float(g.get("avgRating", g.get("score", 0))),
                "has_coupon": bool(product_raw.get("has_coupon", g.get("has_coupon", g.get("hasCoupon", False)))),
                "free_shipping": bool(product_raw.get("free_shipping", g.get("freeShipping", False))),
                "raw": product_raw,
            }
    
    shop_raw = raw.get("shop")
    if shop_raw and isinstance(shop_raw, dict):
        out["shop"] = {
            "mall_id": str(shop_raw.get("mallId", shop_raw.get("mall_id", ""))),
            "shop_name": shop_raw.get("mallName", shop_raw.get("mall_name", shop_raw.get("shop_name", ""))),
            "shop_logo": shop_raw.get("mallLogo", shop_raw.get("mall_logo", shop_raw.get("logo", ""))),
            "rating": float(shop_raw.get("rating", shop_raw.get("score", 0))),
            "goods_count": int(shop_raw.get("goodsCount", shop_raw.get("goods_count", 0))),
        }
    
    log.info("SSR product: title=%s, skus=%d, images=%d, price=%s",
             out["product"].get("title", "?")[:30],
             len(out["product"].get("skus", [])),
             len(out["product"].get("images", [])),
             out["product"].get("price", "?"))
    return out


def _extract_product_detail(page, goods_id: str) -> dict:
    """从商品详情页提取完整信息"""
    result = {
        "product": {"goods_id": goods_id},
        "shop": {},
        "reviews": []
    }

    try:
        # SSR 数据提取
        # 1) Try rawData first (PDD preferred SSR store, same pattern as search)
        ssr_data = _extract_product_ssr(page)
        if ssr_data.get("product") and ssr_data["product"].get("title"):
            result["product"] = ssr_data["product"]
            result["product"]["goods_id"] = goods_id
        if ssr_data.get("shop"):
            result["shop"] = ssr_data["shop"]
    except Exception as e:
        log.debug("SSR product extraction failed: %s", e)

    # DOM 降级
    try:
        if not result["product"].get("title"):
            title_el = page.query_selector('.goods-title, [class*="title"], h1')
            if title_el:
                result["product"]["title"] = title_el.inner_text().strip()

        if not result["product"].get("price"):
            price_el = page.query_selector('[class*="price"], .price-text, .current-price')
            if price_el:
                result["product"]["price"] = _parse_price(price_el.inner_text())

        # 轮播图
        img_els = page.query_selector_all('.swiper-slide img, [class*="banner"] img, .goods-image img')
        result["product"]["images"] = []
        for img in img_els:
            src = img.get_attribute("src") or img.get_attribute("data-src") or ""
            if src and not src.endswith(".gif"):
                result["product"]["images"].append(src)

        # 规格
        spec_els = page.query_selector_all('[class*="sku"], [class*="spec"], .spec-item')
        result["product"]["specs"] = []
        for spec in spec_els:
            result["product"]["specs"].append(spec.inner_text().strip())

        # 描述
        desc_el = page.query_selector('[class*="desc"], .goods-desc, .description')
        if desc_el:
            result["product"]["desc"] = desc_el.inner_text().strip()[:3000]

        # 评价摘要
        review_items = page.query_selector_all('.review-item, [class*="comment"], [class*="evaluate"]')
        for rv in review_items[:10]:
            try:
                review_text = rv.inner_text().strip()
                if review_text:
                    result["reviews"].append({"text": review_text[:500]})
            except Exception:
                pass
    except Exception as e:
        log.warning("DOM product extraction failed: %s", e)

    return result


def _extract_mall_page(page, mall_id: str) -> dict:
    """从店铺页提取信息"""
    result = {
        "shop": {"mall_id": mall_id},
        "products": []
    }

    try:
        ssr = page.evaluate("""() => {
            try { return window.__INITIAL_STATE__ || {}; }
            catch(e) { return {}; }
        }""")
        if ssr:
            mall = ssr.get("mall", ssr.get("mallInfo", {}))
            if mall:
                result["shop"] = {
                    "mall_id": str(mall.get("mallId", mall.get("mall_id", mall_id))),
                    "shop_name": mall.get("mallName", mall.get("shop_name", "")),
                    "shop_logo": mall.get("mallLogo", mall.get("logo", "")),
                    "rating": mall.get("rating", 0),
                    "goods_count": mall.get("goodsCount", 0),
                }
            goods_list = ssr.get("goodsList", ssr.get("goods_list", []))
            for item in goods_list:
                parsed = _parse_product_from_api(item)
                if parsed:
                    result["products"].append(parsed)
    except Exception:
        pass

    return result


def _parse_product_from_api(item: dict) -> dict:
    """从 API 返回的原始数据解析商品信息"""
    if not item:
        return {}

    return {
        "goods_id": str(item.get("goods_id", item.get("goodsId", ""))),
        "title": item.get("goods_name", item.get("goodsName", item.get("title", ""))),
        "price": _parse_price(item.get("min_group_price",
                                       item.get("minGroupPrice",
                                                item.get("price", item.get("mallPrice", 0))))),
        "original_price": _parse_price(item.get("market_price",
                                                item.get("marketPrice",
                                                         item.get("originalPrice", 0)))),
        "sales": item.get("sales", item.get("salesTip", item.get("cnt", 0))),
        "sales_text": str(item.get("salesTip", item.get("sales_tip", ""))),
        "img_url": item.get("thumb_url", item.get("thumbUrl",
                           item.get("goods_thumb_url", item.get("image_url", "")))),
        "shop_name": item.get("mall_name", item.get("mallName", item.get("shop_name", ""))),
        "mall_id": str(item.get("mall_id", item.get("mallId", ""))),
        "has_coupon": bool(item.get("has_coupon", item.get("hasCoupon", False))),
        "free_shipping": bool(item.get("free_shipping", item.get("freeShipping", False))),
        "raw": item,
    }


def _parse_price(val) -> float:
    """解析价格：'¥19.90' / 1990(分) → 19.9"""
    if isinstance(val, (int, float)):
        if val > 10000:  # 可能以分为单位
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
            # 提取第一个数字
            import re
            m = re.search(r'(\d+\.?\d*)', val)
            if m:
                return float(m.group(1))
    return 0.0


def _parse_count(text: str) -> int:
    """解析 '1.2万' / '100万+' / '1234' 格式的数字"""
    text = text.strip().lower().replace(",", "").replace("+", "")
    try:
        if "万" in text:
            return int(float(text.replace("万", "")) * 10000)
        if "w" in text:
            return int(float(text.replace("w", "")) * 10000)
        if "k" in text:
            return int(float(text.replace("k", "")) * 1000)
        return int(float(text))
    except (ValueError, TypeError):
        return 0

# ═══════════════════════════════════════════════
# Hub/v3 Feed 批量采集（无需登录，2026-06-13 攻克）
# ═══════════════════════════════════════════════

def open_feed(max_sn=20, max_pages_per_sn=2, headless=True):
    """通过 hub/v3 Feed API 批量采集首页推荐流商品（无需登录）。

    page_sn 10002-10020 对应不同推荐模块，每个支持 page 翻页。
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser)
    page = context.new_page()
    try:
        log.info("Loading homepage to establish session...")
        page.goto("https://mobile.yangkeduo.com/",
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        _time.sleep(random_delay(3000, 6000) / 1000)
        log.info("Fetching feed: page_sn 10002..%d x %d pages",
                 10002 + max_sn - 1, max_pages_per_sn)
        products, api_calls = _fetch_feed_batch(page, max_sn, max_pages_per_sn)
        # 从 page.evaluate 返回值中提取统计
        return {"products": products, "total": len(products), "api_calls": api_calls}
    finally:
        page.close()
        context.close()


def _fetch_feed_batch(page, max_sn, max_pages_per_sn):
    """在 page.evaluate 中批量 fetch hub/v3，返回 (products, api_calls)"""
    sn_end = 10002 + max_sn
    pp = max_pages_per_sn
    result = page.evaluate(f"""async () => {{
        const allProducts = [];
        const seen = new Set();
        let apiCalls = 0;
        const stats = {{ per_sn: [] }};
        for (let sn = 10002; sn < {sn_end}; sn++) {{
            let hasMore = true;
            let snProducts = 0;
            for (let pg = 1; pg <= {pp} && hasMore; pg++) {{
                try {{
                    const url = `https://mobile.yangkeduo.com/proxy/api/api/alexa/cells/hub/v3?pdduid=0&platform=H5&page_sn=${{sn}}&page_id=index_list.html&page=${{pg}}`;
                    const resp = await fetch(url, {{ credentials: "include" }});
                    const data = await resp.json();
                    apiCalls++;
                    hasMore = data && data.has_more;
                    const gl = data && data.data && data.data.goods_list;
                    if (!gl) continue;
                    for (const item of gl) {{
                        const d = item.data || item;
                        const gid = String(d.goods_id || "");
                        if (gid && !seen.has(gid)) {{
                            seen.add(gid);
                            snProducts++; allProducts.push({{
                                goods_id: gid,
                                goods_name: d.goods_name || "",
                                short_name: d.short_name || "",
                                thumb_url: d.thumb_url || "",
                                hd_thumb_url: d.hd_thumb_url || "",
                                group_price: (d.group && d.group.price) || d.normal_price || 0,
                                normal_price: d.normal_price || 0,
                                market_price: d.market_price || 0,
                                sales_tip: d.sales_tip || "",
                                cnt: d.cnt || 0,
                                link_url: d.link_url || "",
                                mall_name: d.mall_name || "",
                                mall_id: String(d.mall_id || ""),
                                tag_list: d.tag_list || [],
                                icon_list: d.icon_list || [],
                                has_coupon: !!(d.icon_list && d.icon_list.some(
                                    i => (i.type === "coupon" || String(i.type).includes("coupon"))
                                )),
                            }});
                        }}
                    }}
                }} catch(e) {{ hasMore = false; }}
            }}
            stats.per_sn.push({{ sn: sn, products: snProducts }});
        }}
        return {{ products: allProducts, api_calls: apiCalls, stats: stats }};
    }}""")
    return result["products"], result["api_calls"]


def search_feed(keyword, max_sn=10, max_pages_per_sn=1, headless=True):
    """通过 Feed 批量采集后按关键词过滤。

    PDD 搜索 API 需要 anti_content 签名，返回 403。
    替代方案：批量拉取首页推荐流 → 标题关键词匹配过滤。
    """
    feed = open_feed(max_sn=max_sn, max_pages_per_sn=max_pages_per_sn,
                     headless=headless)
    all_products = feed["products"]
    keywords = keyword.lower().split()
    matched = []
    for p in all_products:
        title = (p.get("goods_name", "") + " " + p.get("short_name", "")).lower()
        if all(kw in title for kw in keywords):
            matched.append(p)
    log.info("Feed search '%s': %d matched out of %d fetched",
             keyword, len(matched), len(all_products))
    return {
        "products": matched,
        "total_fetched": len(all_products),
        "matched": len(matched),
        "api_calls": feed.get("api_calls", 0),
    }


def fetch_reviews_via_browser(goods_id: str, max_reviews: int = 50,
                              cookie_file: Optional[str] = None,
                              headless: bool = True) -> list[dict]:
    """通过浏览器内 fetch 获取商品评价。
    
    评价 API 直连需要 anti_content 签名，但浏览器内 fetch 自动携带
    cookie + origin + referer，绕过签名校验。复用 hub/v3 feed 模式。
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()
    try:
        # First load the product page to establish session context
        product_url = f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}"
        log.info("Loading product page for reviews context: %s", goods_id)
        page.goto(product_url,
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        _time.sleep(random_delay(2000, 4000) / 1000)

        reviews = _fetch_reviews_from_page(page, goods_id, max_reviews)
        log.info("Reviews (browser fetch): %d for %s", len(reviews), goods_id)
        return reviews
    finally:
        page.close()
        context.close()


def _fetch_reviews_from_page(page, goods_id: str, max_reviews: int) -> list[dict]:
    """在已加载的商品页中，通过 page.evaluate 分页拉取评价 API"""
    page_size = 20
    max_pages = (max_reviews + page_size - 1) // page_size

    result = page.evaluate(f"""async () => {{
        const reviews = [];
        const seen = new Set();
        let hasMore = true;

        for (let pg = 0; pg < {max_pages} && hasMore; pg++) {{
            try {{
                const url = `https://mobile.yangkeduo.com/proxy/api/api/reviews/list?` +
                    `goods_id={goods_id}&page=${{pg}}&size={page_size}&sort_type=1`;
                const resp = await fetch(url, {{ credentials: "include" }});
                if (resp.status === 403 || resp.status === 429) {{
                    hasMore = false;
                    break;
                }}
                const data = await resp.json();
                hasMore = data && data.has_more;

                const items = (data && (data.list || data.reviews || data.data)) || [];
                for (const item of items) {{
                    const rvId = String(item.id || item.review_id || item.comment_id || "");
                    if (rvId && !seen.has(rvId)) {{
                        seen.add(rvId);
                        reviews.push({{
                            review_id: rvId,
                            text: item.comment || item.text || item.content || "",
                            rating: item.star || item.rating || item.score || item.commentScore || 5,
                            user_name: item.maskName || item.user_name || item.userName || "匿名用户",
                            user_avatar: item.avatar || item.userAvatar || item.user_avatar || "",
                            create_time: item.createTime || item.created_at || item.create_time || 0,
                            reply_text: item.replyText || item.reply || "",
                            images: (item.pics || item.images || []).map(
                                img => (typeof img === "string") ? img : (img.url || img.src || "")
                            ).filter(Boolean),
                            specs: item.spec || item.skuInfo || item.specification || "",
                            raw: item,
                        }});
                    }}
                }}
            }} catch(e) {{
                hasMore = false;
            }}
        }}
        return reviews;
    }}""")
    return result or []


def open_mall_with_products(mall_id: str, cookie_file: Optional[str] = None,
                            max_products: int = 100, headless: bool = True) -> dict:
    """打开店铺页，提取 SSR + DOM 商品列表（含翻页）。
    
    店铺商品列表 API 返回 403，通过浏览器直接提取 SSR 数据。
    """
    browser = launch_browser(headless=headless)
    context = _create_context(browser, cookie_file)
    page = context.new_page()
    try:
        url = f"https://mobile.yangkeduo.com/mall_page.html?mall_id={mall_id}"
        log.info("Navigating to mall: %s", url)
        page.goto(url,
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        _time.sleep(random_delay(1500, 3000) / 1000)
        random_touch_events(page)

        # Extract SSR shop info + products
        mall_data = _extract_mall_from_ssr(page, mall_id)

        # Scroll and try to load more products
        products = mall_data.get("products", [])
        seen_ids = set(p.get("goods_id", "") for p in products)

        scroll_attempts = 0
        while len(products) < max_products and scroll_attempts < 8:
            _human_scroll(page, scrolls=3)
            _time.sleep(random_delay(2000, 4000) / 1000)
            # Re-extract (SSR may have updated)
            mall_data = _extract_mall_from_ssr(page, mall_id)
            new_products = mall_data.get("products", [])
            new_count = 0
            for p in new_products:
                gid = p.get("goods_id", "")
                if gid and gid not in seen_ids:
                    seen_ids.add(gid)
                    products.append(p)
                    new_count += 1
            if new_count == 0:
                scroll_attempts += 1

        log.info("Mall products: %d for mall %s", len(products), mall_id)
        return {
            "shop": mall_data.get("shop", {"mall_id": mall_id}),
            "products": products[:max_products],
        }
    finally:
        page.close()
        context.close()


def _extract_mall_from_ssr(page, mall_id: str) -> dict:
    """从店铺页 SSR 提取店铺信息和商品列表"""
    result = {"shop": {"mall_id": mall_id}, "products": []}
    try:
        data = page.evaluate("""() => {
            const result = { shop: null, products: [] };
            try {
                // 1) window.rawData (same as search/products)
                const rd = window.rawData;
                if (rd) {
                    const stores = rd.stores || rd;
                    for (const k of Object.keys(stores)) {
                        const store = stores[k];
                        if (!store || !store.data) continue;
                        const d = store.data;
                        // Shop info
                        if (d.mallBasicInfo || d.mall || d.shopInfo) {
                            result.shop = d.mallBasicInfo || d.mall || d.shopInfo;
                        }
                        // Products
                        const lists = d.goodsList || d.goods_list || d.productList || d.items || [];
                        if (Array.isArray(lists) && lists.length > 0) {
                            for (const item of lists) {
                                const p = item.data || item;
                                result.products.push({
                                    goods_id: String(p.goods_id || p.goodsId || ""),
                                    goods_name: p.goods_name || p.goodsName || p.title || "",
                                    price: p.min_group_price || p.price || p.mallPrice || 0,
                                    original_price: p.market_price || p.originalPrice || 0,
                                    sales: p.sales || p.sales_tip || p.cnt || 0,
                                    sales_text: p.salesTip || p.sales_tip || "",
                                    thumb_url: p.thumb_url || p.hd_thumb_url || p.goods_thumb_url || "",
                                    link_url: p.link_url || "",
                                    mall_name: p.mall_name || p.mallName || "",
                                    mall_id: String(p.mall_id || p.mallId || ""),
                                    has_coupon: !!(p.icon_list && p.icon_list.some(
                                        i => (i.type === "coupon" || String(i.type).includes("coupon"))
                                    )),
                                });
                            }
                        }
                        if (result.shop && result.products.length > 0) break;
                    }
                }
                // 2) window.__INITIAL_STATE__
                if (!result.shop && !result.products.length) {
                    const st = window.__INITIAL_STATE__;
                    if (st) {
                        result.shop = st.mallBasicInfo || st.mall || st.shop;
                        const gl = st.goodsList || st.productList || st.items || [];
                        if (Array.isArray(gl)) {
                            result.products = gl.map(p => ({
                                goods_id: String(p.goods_id || p.goodsId || ""),
                                goods_name: p.goods_name || p.goodsName || p.title || "",
                                price: p.min_group_price || p.price || 0,
                                thumb_url: p.thumb_url || p.img_url || p.image_url || "",
                                sales_text: p.salesTip || p.sales_tip || "",
                            }));
                        }
                    }
                }
                // 3) DOM fallback - scroll and grab product cards
                if (!result.products.length) {
                    const cards = document.querySelectorAll(
                        '[class*="goods-card"], [class*="goods-item"], [class*="product-item"],'
                        + ' a[href*="goods_id"], a[href*="goods.html"]'
                    );
                    for (const card of cards) {
                        const href = card.getAttribute("href") || "";
                        const m = href.match(/goods_id=(\d+)/);
                        const img = card.querySelector("img");
                        const title = (card.querySelector('[class*="name"], [class*="title"]') || card).textContent.trim();
                        const price = (card.querySelector('[class*="price"]') || {}).textContent || "";
                        if (m) {
                            result.products.push({
                                goods_id: m[1],
                                goods_name: title || "unknown",
                                price: price || "0",
                                thumb_url: (img && img.src) || (img && img.getAttribute("data-src")) || "",
                            });
                        }
                    }
                }
            } catch(e) {}
            return JSON.parse(JSON.stringify(result));
        }""")

        if data:
            if data.get("shop"):
                shop = data["shop"]
                result["shop"] = {
                    "mall_id": str(shop.get("mallId", shop.get("mall_id", mall_id))),
                    "shop_name": shop.get("mallName", shop.get("mall_name", shop.get("shop_name", ""))),
                    "shop_logo": shop.get("mallLogo", shop.get("logo", shop.get("shop_logo", ""))),
                    "rating": float(shop.get("rating", shop.get("score", 0))),
                    "goods_count": int(shop.get("goodsCount", shop.get("goods_count", 0))),
                }
            products = data.get("products", [])
            for p in products:
                if isinstance(p, dict):
                    result["products"].append({
                        "goods_id": str(p.get("goods_id", "")),
                        "title": p.get("goods_name", p.get("title", "")),
                        "price": _parse_price(p.get("price", 0)),
                        "original_price": _parse_price(p.get("original_price", 0)),
                        "sales_text": str(p.get("sales_text", "")),
                        "img_url": p.get("thumb_url", ""),
                        "mall_name": p.get("mall_name", ""),
                        "mall_id": str(p.get("mall_id", mall_id)),
                        "has_coupon": bool(p.get("has_coupon", False)),
                    })
    except Exception as e:
        log.debug("Mall SSR extraction failed: %s", e)

    return result
