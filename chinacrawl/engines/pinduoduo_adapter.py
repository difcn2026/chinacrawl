"""Pinduoduo (拼多多) Engine Adapter — wraps chinacrawl.pinduoduo into BaseSiteEngine.

Delegates to the existing pinduoduo/ scraper module. Falls back to skeleton
implementations when the pinduoduo module is unavailable.
"""

from __future__ import annotations

from typing import Optional, List, Any

from .base import BaseSiteEngine, EngineProduct, EngineSearchResult, registry


# ── Try importing pinduoduo scraper ─────────────────────────────
try:
    from chinacrawl.pinduoduo import scraper as _pdd
    _PDD_AVAILABLE = True
except ImportError:
    _PDD_AVAILABLE = False


class PinduoduoEngine(BaseSiteEngine):
    name = "pinduoduo"
    display_name = "拼多多 Pinduoduo"
    homepage = "https://www.pinduoduo.com"
    requires_playwright = True
    requires_login = True

    # ── Core: search ─────────────────────────────────────────

    async def search(self, query: str, page: int = 1, **kwargs) -> EngineSearchResult:
        """Search pinduoduo for products."""
        result = EngineSearchResult(query=query, page=page)

        if not _PDD_AVAILABLE:
            return result

        max_results = kwargs.pop("max_results", 20)
        cookie_file = kwargs.pop("cookie_file", None) or self.cookie_file or self.get_default_cookie_path()
        raw_products: List[Any] = _pdd.product_search(query, max_results=max_results, cookie_file=cookie_file)

        for pi in raw_products:
            product = EngineProduct(platform=self.name, item_id="", title="")
            product.item_id = getattr(pi, "goods_id", "")
            product.title = getattr(pi, "title", "") or ""
            product.price = float(getattr(pi, "price", 0.0) or 0.0)
            product.original_price = float(getattr(pi, "original_price", 0.0) or 0.0)
            product.image_url = getattr(pi, "img_url", "")
            product.shop_name = getattr(pi, "shop_name", "")
            product.sales_count = int(getattr(pi, "sales", 0) or 0)
            product.rating = float(getattr(pi, "rating", 0.0) or 0.0)
            product.detail_url = f"https://mobile.yangkeduo.com/goods.html?goods_id={product.item_id}"
            product.raw = getattr(pi, "raw", {})

            if product.item_id or product.title:
                result.products.append(product)

        result.total_count = len(result.products)
        result.has_more = len(raw_products) >= max_results
        return result

    # ── Detail ───────────────────────────────────────────────

    async def detail(self, item_id: str, **kwargs) -> Optional[EngineProduct]:
        """Get pinduoduo product detail by goods_id."""
        if not _PDD_AVAILABLE:
            return None

        cookie_file = kwargs.pop("cookie_file", None) or self.cookie_file or self.get_default_cookie_path()
        try:
            pi = _pdd.product_detail(item_id, cookie_file=cookie_file)
        except Exception:
            return None

        if pi is None:
            return None

        product = EngineProduct(platform=self.name, item_id="", title="")
        product.item_id = getattr(pi, "goods_id", item_id)
        product.title = getattr(pi, "title", "") or ""
        product.price = float(getattr(pi, "price", 0.0) or 0.0)
        product.original_price = float(getattr(pi, "original_price", 0.0) or 0.0)
        product.image_url = getattr(pi, "img_url", "")
        product.shop_name = getattr(pi, "shop_name", "")
        product.sales_count = int(getattr(pi, "sales", 0) or 0)
        product.rating = float(getattr(pi, "rating", 0.0) or 0.0)
        product.detail_url = f"https://mobile.yangkeduo.com/goods.html?goods_id={product.item_id}"
        product.raw = getattr(pi, "raw", {})
        return product if product.title or product.item_id else None

    # ── Session management ───────────────────────────────────

    async def login(self, **kwargs) -> bool:
        """QR-code login for pinduoduo."""
        if not _PDD_AVAILABLE:
            return False
        try:
            method = kwargs.pop("method", "qr")
            cookie_file = kwargs.pop("cookie_file", None) or self.cookie_file or self.get_default_cookie_path()
            result = _pdd.login(method=method, cookie_file=cookie_file)
            return bool(result)
        except Exception:
            return False

    def save_session(self, cookie_file=None) -> bool:
        """Save pinduoduo session cookies via the scraper module."""
        if not _PDD_AVAILABLE:
            return super().save_session(cookie_file)
        target = cookie_file or self.cookie_file or self.get_default_cookie_path()
        try:
            return _pdd.save_session(target)
        except Exception:
            return super().save_session(cookie_file)

    def load_session(self, cookie_file=None) -> bool:
        """Load pinduoduo session cookies via the scraper module."""
        if not _PDD_AVAILABLE:
            return super().load_session(cookie_file)
        target = cookie_file or self.cookie_file or self.get_default_cookie_path()
        try:
            return _pdd.load_session(target)
        except Exception:
            return super().load_session(cookie_file)

    def check_session(self) -> bool:
        """Check if pinduoduo session is valid."""
        if not _PDD_AVAILABLE:
            return super().check_session()
        try:
            return _pdd.check_session()
        except Exception:
            return super().check_session()


# Auto-register
registry.register(PinduoduoEngine())

# Backward-compat alias for engines/__init__.py import
PinduoduoEngineAdapter = PinduoduoEngine
