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
from .anti_detect import (
    ANTI_DETECT_JS, CONTEXT_OVERRIDES,
    random_delay, random_touch_events, random_scroll_steps,
)

log = logging.getLogger("chinacrawl.pinduoduo.browser")

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


def launch_browser(headless: bool = True):
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
    global _browser
    try:
        if _browser and _browser.is_connected():
            _browser.close()
    except Exception:
        pass
    _browser = None


def _create_context(browser, cookie_file: Optional[str] = None):
    """创建带反检测配置的浏览器上下文"""
    context = browser.new_context(**CONTEXT_OVERRIDES)

    # 注入反检测脚本（每个新页面自动注入）
    context.add_init_script(ANTI_DETECT_JS)

    # 加载 cookies
    if cookie_file and os.path.exists(cookie_file):
        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies_data = json.load(f)
            cookie_list = cookies_data.get("cookies", cookies_data) if isinstance(cookies_data, dict) else cookies_data
            context.add_cookies(cookie_list)
            log.info("Loaded %d cookies from %s", len(cookie_list), cookie_file)
        except Exception as e:
            log.warning("Failed to load cookies: %s", e)

    return context


# ━━━ Page Navigation ━━━

def open_search_page(keyword: str, cookie_file: Optional[str] = None,
                     headless: bool = True) -> dict:
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
        search_url = f"https://mobile.yangkeduo.com/search_result.html?search_key={keyword}"
        log.info("Navigating to search: %s", search_url)

        page.goto(search_url,
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

        # 模拟人类行为：随机延迟 + 触摸
        _time.sleep(random_delay(1500, 3000) / 1000)
        random_touch_events(page)

        # 等待结果加载
        try:
            page.wait_for_selector("[data-active=\"search-list\"] li, .search-results li",
                                   timeout=20000)
        except Exception:
            log.warning("Search results selector not found, trying alternative...")
            try:
                page.wait_for_selector(".goods-item, [class*=\"goods\"]",
                                       timeout=10000)
            except Exception:
                pass

        # 滚动加载更多
        _human_scroll(page, scrolls=4)

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
        ssr = page.evaluate("""() => {
            try {
                return window.__INITIAL_STATE__ || {};
            } catch(e) { return {}; }
        }""")
        if ssr:
            search_data = ssr.get("search", ssr)
            items = search_data.get("items", search_data.get("goodsList", []))
            for item in items:
                product = _parse_product_from_api(item)
                if product and product.get("goods_id"):
                    result["products"].append(product)
            if result["products"]:
                result["total_count"] = search_data.get("totalCount", len(result["products"]))
                result["has_more"] = search_data.get("hasMore", False)
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


def _extract_product_detail(page, goods_id: str) -> dict:
    """从商品详情页提取完整信息"""
    result = {
        "product": {"goods_id": goods_id},
        "shop": {},
        "reviews": []
    }

    try:
        # SSR 数据提取
        ssr = page.evaluate("""() => {
            try {
                return window.__INITIAL_STATE__ || {};
            } catch(e) { return {}; }
        }""")
        if ssr:
            goods_detail = ssr.get("goodsDetail", ssr.get("goods", ssr))
            if goods_detail:
                result["product"] = _parse_product_from_api(goods_detail)
                result["product"]["goods_id"] = goods_id

            mall_info = ssr.get("mallInfo", ssr.get("mall", ssr.get("shop", {})))
            if mall_info:
                result["shop"] = {
                    "mall_id": str(mall_info.get("mallId", mall_info.get("mall_id", ""))),
                    "shop_name": mall_info.get("mallName", mall_info.get("shop_name", "")),
                    "shop_logo": mall_info.get("mallLogo", mall_info.get("logo", "")),
                    "rating": mall_info.get("rating", mall_info.get("score", 0)),
                    "goods_count": mall_info.get("goodsCount", mall_info.get("goods_count", 0)),
                }
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
