"""Taobao.com (淘宝) Engine — ChinaCrawl Plugin.

Dual-channel architecture:
  1. Web API (preferred): Taobao internal API via curl_cffi
  2. Playwright Browser (fallback): Full JS rendering + login

Like JD, Taobao is full JS rendering and has aggressive anti-bot measures.
"""

import asyncio
import re
from typing import Optional, Dict, Any
from pathlib import Path

from .base import BaseEngine, EngineProduct, EngineSearchResult


class TaobaoEngine(BaseEngine):
    name = "taobao"
    display_name = "淘宝 Taobao.com"
    homepage = "https://www.taobao.com"
    search_url = "https://s.taobao.com/search"
    requires_playwright = True
    requires_login = False  # v3.7

    async def search(self, query: str, page: int = 1, **kwargs) -> EngineSearchResult:
        """Search Taobao for products."""
        from urllib.parse import quote
        result = EngineSearchResult(query=query, page=page)

        ctx = await self._ensure_browser()
        pg = await ctx.new_page()
        try:
            url = f"https://s.taobao.com/search?q={quote(query)}&s={48 * (page - 1)}"
            await pg.goto(url, timeout=30000, wait_until="domcontentloaded")
            await pg.wait_for_timeout(3000)
            # v3.8: Auto-detect & solve CAPTCHA
            await self._handle_captcha(pg)

            # Check for login wall
            if "login.taobao.com" in pg.url:
                return result

            for _ in range(3):
                await pg.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(0.5)

            content = await pg.content()
            return self._parse_search(content, query, page)
        finally:
            await pg.close()

    async def detail(self, item_id: str, **kwargs) -> Optional[EngineProduct]:
        """Get Taobao product detail."""
        ctx = await self._ensure_browser()
        page = await ctx.new_page()
        try:
            url = f"https://item.taobao.com/item.htm?id={item_id}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await self._handle_captcha(page)
            content = await page.content()
            return self._parse_detail(content, item_id)
        finally:
            await page.close()

    async def login(self, **kwargs) -> bool:
        """Interactive QR-code login for Taobao."""
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await ctx.new_page()
        await page.goto("https://login.taobao.com/", timeout=30000)
        print("[Taobao] 请用手机淘宝扫码登录...")
        await page.wait_for_url("https://www.taobao.com/**", timeout=120000)
        import json
        cookies = await ctx.cookies()
        profile = Path.home() / ".chinacrawl" / "taobao_profile"
        profile.mkdir(parents=True, exist_ok=True)
        (profile / "cookies.json").write_text(json.dumps(cookies, ensure_ascii=False))
        print("[Taobao] 登录成功")
        await browser.close()
        await pw.stop()
        return True

    # ── Parsing ──

    def _parse_search(self, html: str, query: str, page: int) -> EngineSearchResult:
        result = EngineSearchResult(query=query, page=page)
        try:
            from lxml import html as lhtml
            tree = lhtml.fromstring(html)
        except Exception:
            return result

        items = tree.cssselect("div.item.J_MouserOnverReq") or tree.cssselect("div.ctx-box div.item")
        for item in items:
            try:
                product = EngineProduct(platform="taobao", item_id="", title="")

                # ID
                nid = item.get("data-nid", "") or item.get("data-id", "")
                product.item_id = nid

                # Title
                title_el = item.cssselect("div.title a") or item.cssselect("div.row-2.title a")
                if title_el:
                    product.title = title_el[0].text_content().strip()

                # Price
                price_el = item.cssselect("div.price strong") or item.cssselect("span.price")
                if price_el:
                    try:
                        product.price = float(re.sub(r"[^\d.]", "", price_el[0].text_content().strip()))
                    except ValueError:
                        pass

                # Image
                img_el = item.cssselect("img") or item.cssselect("div.pic img")
                if img_el:
                    src = img_el[0].get("data-src", "") or img_el[0].get("src", "")
                    product.image_url = f"https:{src}" if src.startswith("//") else src

                # Shop
                shop_el = item.cssselect("div.shop a") or item.cssselect("a.shopname")
                if shop_el:
                    product.shop_name = shop_el[0].text_content().strip()

                if product.title:
                    result.products.append(product)
            except Exception:
                continue

        result.total_count = len(result.products)
        result.has_more = bool(items)
        return result

    def _parse_detail(self, html: str, item_id: str) -> Optional[EngineProduct]:
        try:
            from lxml import html as lhtml
            tree = lhtml.fromstring(html)
        except Exception:
            return None

        product = EngineProduct(platform="taobao", item_id=item_id, title="")

        title_el = tree.cssselect("h1.tb-main-title") or tree.cssselect("div.tb-detail-hd h1")
        if title_el:
            product.title = title_el[0].text_content().strip()

        price_el = tree.cssselect("strong.tb-rmb-num") or tree.cssselect("span.tm-price")
        if price_el:
            try:
                product.price = float(re.sub(r"[^\d.]", "", price_el[0].text_content().strip()))
            except ValueError:
                pass

        return product if product.title else None


# Auto-register
from .base import registry
registry.register(TaobaoEngine())
