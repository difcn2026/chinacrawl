"""JD.com (京东) Engine - ChinaCrawl Plugin v3.7.

XHLS v3.7 FUSED: Multi-strategy bypass + TLS rotation + Rate intelligence.
Corrigenda #13,#14,#17 resolved: requires_login removed, multi-fingerprint approach.

Dual-channel:
  1. curl_cffi API: rotating TLS fingerprints (chrome131/124/120/110)
  2. Playwright Browser: JS rendering with stealth injection
"""

import asyncio
import re
import json
import random
from typing import Optional, Dict, Any
from pathlib import Path

from .base import BaseEngine, EngineProduct, EngineSearchResult


class JDEngine(BaseEngine):
    name = "jd"
    display_name = "京东 JD.com"
    homepage = "https://www.jd.com"
    search_url = "https://search.jd.com/Search"
    requires_playwright = True
    requires_login = False  # v3.7: multi-strategy bypass

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        default = str(Path.home() / ".chinacrawl" / "jd_profile")
        self.profile_dir = Path(config.get("profile_dir", default)) if config else Path(default)
        self._rl = {"min_delay": 1.0, "max_delay": 8.0, "delay": 1.5, "blocks": 0}
        self._tls_fps = ["chrome131", "chrome124", "chrome120", "chrome110"]

        self._evo_scores = {fp: 1.0 for fp in self._tls_fps}
        self._evo_rounds = 0
    # -- Public API --

    async def search(self, query: str, page: int = 1, **kwargs) -> EngineSearchResult:
        """v3.7: Rotate TLS fingerprints; browser fallback with stealth."""
        result = EngineSearchResult(query=query, page=page)

        if self._rl["blocks"] > 2:
            self._rl["delay"] = min(self._rl["delay"] * 1.5, self._rl["max_delay"])
            await asyncio.sleep(self._rl["delay"])

        sorted_fps = sorted(self._tls_fps, key=lambda f: -self._evo_scores.get(f, 1.0))
        for fp in sorted_fps:
            try:
                r = await self._search_api(query, page, fp)
                if r and r.products:
                    self._rl["blocks"] = 0
                    self._rl["delay"] = max(self._rl["delay"] * 0.9, 1.0)
                    self._evo_scores[fp] = min(self._evo_scores.get(fp,1.0)*1.2, 5.0)
                    return r
            except Exception:
                continue

        self._rl["blocks"] += 1
        for f in self._tls_fps: self._evo_scores[f] = max(self._evo_scores.get(f,1.0)*0.8, 0.1)
        return await self._search_browser(query, page)

    async def detail(self, item_id: str, **kwargs) -> Optional[EngineProduct]:
        ctx = await self._ensure_browser()
        url = f"https://item.jd.com/{item_id}.html"
        page = await ctx.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await self._handle_captcha(page)
            return self._parse_detail(await page.content(), item_id)
        finally:
            await page.close()

    async def login(self, **kwargs) -> bool:
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await ctx.new_page()
        await page.goto("https://passport.jd.com/new/login.aspx", timeout=30000)
        print("[JD] Please scan QR code with JD app...")
        await page.wait_for_url("https://www.jd.com/**", timeout=120000)
        cookies = await ctx.cookies()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        (self.profile_dir / "cookies.json").write_text(json.dumps(cookies, ensure_ascii=False))
        print("[JD] Login success, cookies saved")
        await browser.close()
        await pw.stop()
        return True

    async def save_session(self, path: Optional[Path] = None) -> bool:
        target = path or self.profile_dir
        target.mkdir(parents=True, exist_ok=True)
        if self._context:
            storage = await self._context.storage_state()
            (target / "state.json").write_text(json.dumps(storage, ensure_ascii=False))
            return True
        return False

    async def load_session(self, path: Optional[Path] = None) -> bool:
        target = path or self.profile_dir
        state_file = target / "state.json"
        if state_file.exists() and self._context:
            await self._context.add_cookies(json.loads(state_file.read_text()))
            return True
        return False

    # -- curl_cffi API --

    async def _search_api(self, query: str, page: int, fp: str) -> Optional[EngineSearchResult]:
        try:
            from curl_cffi import requests
        except ImportError:
            return None

        from urllib.parse import quote
        url = f"https://search.jd.com/Search?keyword={quote(query)}&enc=utf-8&page={page}"

        session = requests.Session()
        ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{fp.replace('chrome','')}.0.0.0 Safari/537.36"
        session.headers.update({
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
        })

        # Load saved cookies if available
        cookie_file = self.profile_dir / "cookies.json"
        if cookie_file.exists():
            try:
                for ck in json.loads(cookie_file.read_text()):
                    session.cookies.set(ck.get("name",""), ck.get("value",""), domain=ck.get("domain",""))
            except Exception:
                pass

        resp = session.get(url, timeout=15, impersonate=fp)
        if resp.status_code == 200 and len(resp.text) > 500:
            return self._parse_search(resp.text, query, page)
        return None

    # -- Browser fallback --

    async def _search_browser(self, query: str, page: int) -> EngineSearchResult:
        from urllib.parse import quote
        ctx = await self._ensure_browser()
        await self.load_session()

        pg = await ctx.new_page()
        try:
            url = f"https://search.jd.com/Search?keyword={quote(query)}&enc=utf-8&page={page}"
            await pg.goto(url, timeout=30000, wait_until="domcontentloaded")
            await pg.wait_for_timeout(3000)

            # v3.8: CAPTCHA auto-detect & solve before checking redirect
            captcha_handled = await self._handle_captcha(pg)
            if captcha_handled:
                await pg.wait_for_timeout(2000)  # Wait for page to settle after captcha

            if "passport.jd.com" in pg.url:
                return EngineSearchResult(query=query, page=page)

            for _ in range(3):
                await pg.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(0.5)

            return self._parse_search(await pg.content(), query, page)
        finally:
            await pg.close()

    # -- Parsing --

    def _parse_search(self, html: str, query: str, page: int) -> EngineSearchResult:
        result = EngineSearchResult(query=query, page=page)
        try:
            from lxml import html as lhtml
            tree = lhtml.fromstring(html)
        except Exception:
            return result

        items = tree.cssselect("li.gl-item") or tree.cssselect("div.gl-i-wrap")
        for item in items:
            try:
                product = EngineProduct(platform="jd", item_id="", title="")
                sku = item.get("data-sku", "") or item.get("data-pid", "")
                product.item_id = sku

                title_el = (item.cssselect("div.p-name a em") or
                           item.cssselect("div.p-name") or
                           item.cssselect("a[title]"))
                if title_el:
                    product.title = (title_el[0].get("title","") or title_el[0].text_content()).strip()

                price_el = item.cssselect("div.p-price i") or item.cssselect("div.p-price strong")
                if price_el:
                    try:
                        product.price = float(re.sub(r"[^\d.]", "", price_el[0].text_content().strip()))
                    except ValueError:
                        pass

                img_el = item.cssselect("img[data-lazy-img]") or item.cssselect("img")
                if img_el:
                    src = img_el[0].get("data-lazy-img","") or img_el[0].get("src","")
                    product.image_url = f"https:{src}" if src.startswith("//") else src

                link_el = item.cssselect("a[href]")
                if link_el:
                    href = link_el[0].get("href","")
                    product.detail_url = f"https:{href}" if href.startswith("//") else href

                shop_el = item.cssselect("div.p-shop a") or item.cssselect("span.J_im_icon a")
                if shop_el:
                    product.shop_name = shop_el[0].text_content().strip()

                if product.title or product.item_id:
                    result.products.append(product)
            except Exception:
                continue

        result.total_count = len(result.products)
        result.has_more = len(result.products) >= 20
        return result

    def _parse_detail(self, html: str, item_id: str) -> Optional[EngineProduct]:
        try:
            from lxml import html as lhtml
            tree = lhtml.fromstring(html)
        except Exception:
            return None

        product = EngineProduct(platform="jd", item_id=item_id, title="")
        title_el = tree.cssselect("div.sku-name") or tree.cssselect("div.itemInfo-wrap div.sku-name")
        if title_el:
            product.title = title_el[0].text_content().strip()

        price_el = tree.cssselect("span.p-price span") or tree.cssselect("span.price")
        if price_el:
            try:
                product.price = float(re.sub(r"[^\d.]", "", price_el[0].text_content().strip()))
            except ValueError:
                pass

        img_el = tree.cssselect("#spec-img") or tree.cssselect("img#spec-img")
        if img_el:
            src = img_el[0].get("src","")
            product.image_url = f"https:{src}" if src.startswith("//") else src

        return product if product.title else None


from .base import registry
registry.register(JDEngine())
