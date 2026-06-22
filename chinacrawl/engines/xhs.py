"""Xiaohongshu (小红书) Engine - ChinaCrawl Plugin v3.7.

XHLS v3.7: New platform adapter for 小红书 - Chinese lifestyle/content platform.
Critical for short drama: trend discovery, competitor analysis, audience sentiment.

Dual-channel:
  1. Web API: XHS internal search API
  2. Playwright Browser: JS rendering with mobile UA
"""

import asyncio
import re
import json
from typing import Optional, Dict, Any
from pathlib import Path
from urllib.parse import quote

from .base import BaseEngine, EngineProduct, EngineSearchResult


class XHSEngine(BaseEngine):
    name = "xhs"
    display_name = "小红书 Xiaohongshu"
    homepage = "https://www.xiaohongshu.com"
    search_url = "https://www.xiaohongshu.com/search_result/"
    requires_playwright = True
    requires_login = False

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        default = str(Path.home() / ".chinacrawl" / "xhs_profile")
        self.profile_dir = Path(config.get("profile_dir", default)) if config else Path(default)
        self._rl = {"min_delay": 2.0, "max_delay": 15.0, "delay": 3.0, "blocks": 0}

        # XHS uses mobile-first design; use mobile UA
        self._mobile_ua = (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.6778.135 Mobile Safari/537.36"
        )

    # -- Public API --

    async def search(self, query: str, page: int = 1, sort: str = "general",
                     **kwargs) -> EngineSearchResult:
        """Search XHS for notes/posts.

        sort: general (综合), popularity (最热), latest (最新)
        """
        result = EngineSearchResult(query=query, page=page)

        if self._rl["blocks"] > 2:
            self._rl["delay"] = min(self._rl["delay"] * 2.0, self._rl["max_delay"])
            await asyncio.sleep(self._rl["delay"])

        # XHS is heavily JS-rendered; browser-only approach
        try:
            browser_result = await self._search_browser(query, page, sort)
            if browser_result and browser_result.products:
                self._rl["blocks"] = 0
                self._rl["delay"] = max(self._rl["delay"] * 0.9, 2.0)
                return browser_result
        except Exception:
            pass

        self._rl["blocks"] += 1
        return result

    async def detail(self, note_id: str, **kwargs) -> Optional[EngineProduct]:
        """Get XHS note detail by note ID."""
        ctx = await self._ensure_browser()
        page = await ctx.new_page()
        try:
            url = f"https://www.xiaohongshu.com/explore/{note_id}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            return self._parse_detail(await page.content(), note_id)
        finally:
            await page.close()

    async def user_notes(self, user_id: str, limit: int = 20,
                         **kwargs) -> list[EngineProduct]:
        """Get notes from a XHS user."""
        ctx = await self._ensure_browser()
        page = await ctx.new_page()
        results = []
        try:
            url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 600)")
                await asyncio.sleep(1.0)

            content = await page.content()
            notes = self._parse_user_notes(content, user_id)
            results.extend(notes[:limit])
        finally:
            await page.close()
        return results

    async def login(self, **kwargs) -> bool:
        """Interactive QR-code login for XHS."""
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=False)
        ctx = await browser.new_context(
            user_agent=self._mobile_ua,
            viewport={"width": 390, "height": 844},
        )
        page = await ctx.new_page()
        await page.goto("https://www.xiaohongshu.com", timeout=30000)
        print("[XHS] Please scan QR code with XHS app...")
        await asyncio.sleep(60)  # Wait for manual login

        cookies = await ctx.cookies()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        (self.profile_dir / "cookies.json").write_text(
            json.dumps(cookies, ensure_ascii=False))
        print("[XHS] Login success, cookies saved")
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

    # -- Browser search --

    async def _search_browser(self, query: str, page: int,
                              sort: str) -> EngineSearchResult:
        ctx = await self._ensure_browser()
        await self.load_session()

        pg = await ctx.new_page()
        try:
            sort_map = {"general": "general", "popularity": "popularity_descending",
                       "latest": "time_descending"}
            sort_param = sort_map.get(sort, "general")

            url = (f"https://www.xiaohongshu.com/search_result/"
                   f"?keyword={quote(query)}&source=web_search_result_notes"
                   f"&sort={sort_param}&page={page}")

            await pg.goto(url, timeout=30000, wait_until="domcontentloaded")
            await pg.wait_for_timeout(3000)

            # XHS anti-bot: check for captcha
            if "captcha" in pg.url.lower() or "verify" in pg.url.lower():
                return EngineSearchResult(query=query, page=page)

            # Scroll to load more
            for _ in range(3):
                await pg.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1.0)

            return self._parse_search(await pg.content(), query, page)
        finally:
            await pg.close()

    # -- Parsing --

    def _parse_search(self, html: str, query: str,
                      page: int) -> EngineSearchResult:
        result = EngineSearchResult(query=query, page=page)

        # XHS note cards have various selectors
        note_patterns = [
            r'"noteId":"([^"]+)"',
            r'data-id="([^"]+)"',
            r'/explore/([a-f0-9]+)',
        ]

        # Extract note IDs
        note_ids = set()
        for pattern in note_patterns:
            found = re.findall(pattern, html)
            note_ids.update(found)

        for nid in list(note_ids)[:30]:
            product = EngineProduct(platform="xhs", item_id=nid, title="")
            product.detail_url = f"https://www.xiaohongshu.com/explore/{nid}"

            # Try to extract title from nearby context
            title_match = re.search(
                rf'{nid}.*?"title":"([^"]+)"', html)
            if title_match:
                product.title = title_match.group(1)

            # Extract like count
            likes_match = re.search(
                rf'{nid}.*?"likes":(\d+)', html)
            if likes_match:
                product.price = float(likes_match.group(1))  # Use price field for likes

            result.products.append(product)

        result.total_count = len(result.products)
        result.has_more = len(result.products) >= 20
        return result

    def _parse_detail(self, html: str, note_id: str) -> Optional[EngineProduct]:
        product = EngineProduct(platform="xhs", item_id=note_id, title="")

        # Title
        title_match = re.search(r'"title":"([^"]+)"', html)
        if title_match:
            product.title = title_match.group(1)

        # Description
        desc_match = re.search(r'"desc":"([^"]*?)"', html)
        if desc_match:
            product.shop_name = desc_match.group(1)[:200]  # Use shop_name for desc

        # Like count
        likes_match = re.search(r'"likedCount":(\d+)', html)
        if likes_match:
            product.price = float(likes_match.group(1))

        # Author
        author_match = re.search(r'"nickname":"([^"]+)"', html)
        if author_match:
            product.shop_name = f"{author_match.group(1)}: {product.shop_name}"

        return product if product.title else None

    def _parse_user_notes(self, html: str,
                          user_id: str) -> list[EngineProduct]:
        results = []
        note_ids = set(re.findall(r'/explore/([a-f0-9]+)', html))

        for nid in list(note_ids)[:30]:
            product = EngineProduct(platform="xhs", item_id=nid, title="")
            product.detail_url = f"https://www.xiaohongshu.com/explore/{nid}"

            title_match = re.search(rf'{nid}.*?"title":"([^"]+)"', html)
            if title_match:
                product.title = title_match.group(1)

            results.append(product)

        return results


from .base import registry
registry.register(XHSEngine())
