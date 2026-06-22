"""Douyin (抖音) Engine Adapter — wraps chinacrawl.douyin into BaseSiteEngine.

Delegates to the existing douyin/ scraper module. Falls back to skeleton
implementations when the douyin module is unavailable.
"""

from __future__ import annotations

from typing import Optional, List, Any

from .base import BaseSiteEngine, EngineProduct, EngineSearchResult, registry


# ── Try importing douyin scraper ────────────────────────────────
try:
    from chinacrawl.douyin import scraper as _dy
    _DY_AVAILABLE = True
except ImportError:
    _DY_AVAILABLE = False


class DouyinEngine(BaseSiteEngine):
    name = "douyin"
    display_name = "抖音 Douyin"
    homepage = "https://www.douyin.com"
    requires_playwright = True
    requires_login = True

    # ── Core: search ─────────────────────────────────────────

    async def search(self, query: str, page: int = 1, **kwargs) -> EngineSearchResult:
        """Search douyin for videos/users/hashtags."""
        result = EngineSearchResult(query=query, page=page)

        if not _DY_AVAILABLE:
            return result

        max_results = kwargs.pop("max_results", 20)
        raw_results: List[Any] = _dy.search(query, max_results=max_results)

        for r in raw_results:
            product = EngineProduct(platform=self.name, item_id="", title="")
            rtype = getattr(r, "result_type", "")

            if rtype == "video" and r.aweme:
                aw = r.aweme
                product.item_id = getattr(aw, "aweme_id", "")
                product.title = getattr(aw, "desc", "") or ""
                product.image_url = (
                    getattr(aw, "cover_url", "") or
                    getattr(getattr(aw, "cover", None), "url_list", [""])[0] if hasattr(aw, "cover") and getattr(aw, "cover", None) else ""
                )
                product.detail_url = f"https://www.douyin.com/video/{product.item_id}"
                product.raw = getattr(aw, "raw", {})

            elif rtype == "user" and r.user:
                u = r.user
                product.item_id = getattr(u, "sec_uid", "")
                product.title = getattr(u, "nickname", "") or f"@{getattr(u, 'unique_id', '')}"
                product.image_url = getattr(u, "avatar_url", "")
                product.detail_url = f"https://www.douyin.com/user/{product.item_id}"
                product.raw = getattr(u, "raw", {})

            elif rtype == "hashtag":
                product.item_id = getattr(r, "hashtag_name", "")
                product.title = f"#{getattr(r, 'hashtag_name', '')}"
                product.raw = getattr(r, "raw", {})

            else:
                # Bare dict or unknown type
                product.item_id = str(r.get("aweme_id", r.get("sec_uid", ""))) if isinstance(r, dict) else ""
                product.title = str(r.get("desc", r.get("nickname", ""))) if isinstance(r, dict) else ""
                product.raw = r if isinstance(r, dict) else {}

            if product.item_id or product.title:
                result.products.append(product)

        result.total_count = len(result.products)
        result.has_more = len(raw_results) >= max_results
        return result

    # ── Detail ───────────────────────────────────────────────

    async def detail(self, item_id: str, **kwargs) -> Optional[EngineProduct]:
        """Get douyin video detail by aweme_id."""
        if not _DY_AVAILABLE:
            return None

        try:
            aweme = _dy.video_info(item_id)
        except Exception:
            return None

        if aweme is None:
            return None

        product = EngineProduct(platform=self.name, item_id="", title="")
        product.item_id = getattr(aweme, "aweme_id", item_id)
        product.title = getattr(aweme, "desc", "") or ""
        product.image_url = getattr(aweme, "cover_url", "")
        product.detail_url = f"https://www.douyin.com/video/{product.item_id}"
        product.raw = getattr(aweme, "raw", {})
        return product if product.title or product.item_id else None

    # ── Session management ───────────────────────────────────

    async def login(self, **kwargs) -> bool:
        """QR-code login for douyin."""
        if not _DY_AVAILABLE:
            return False
        try:
            method = kwargs.pop("method", "qr")
            cookie_file = kwargs.pop("cookie_file", None) or self.cookie_file or self.get_default_cookie_path()
            result = _dy.login(method=method, cookie_file=cookie_file)
            return bool(result)
        except Exception:
            return False

    def save_session(self, cookie_file=None) -> bool:
        """Save douyin session cookies via the scraper module."""
        if not _DY_AVAILABLE:
            return super().save_session(cookie_file)
        target = cookie_file or self.cookie_file or self.get_default_cookie_path()
        try:
            return _dy.save_session(target)
        except Exception:
            return super().save_session(cookie_file)

    def load_session(self, cookie_file=None) -> bool:
        """Load douyin session cookies via the scraper module."""
        if not _DY_AVAILABLE:
            return super().load_session(cookie_file)
        target = cookie_file or self.cookie_file or self.get_default_cookie_path()
        try:
            return _dy.load_session(target)
        except Exception:
            return super().load_session(cookie_file)

    def check_session(self) -> bool:
        """Check if douyin session is valid."""
        if not _DY_AVAILABLE:
            return super().check_session()
        try:
            return _dy.check_session()
        except Exception:
            return super().check_session()


# Auto-register
registry.register(DouyinEngine())

# Backward-compat alias for engines/__init__.py import
DouyinEngineAdapter = DouyinEngine
