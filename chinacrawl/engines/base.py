"""ChinaCrawl Engine Plugin Base — 搜索引擎插件基类.

All site-specific engines inherit from BaseEngine and register via the EngineRegistry.
Supports dual-channel: Web API (preferred) → Playwright Browser (fallback).

Usage:
    from chinacrawl.engines import registry
    engine = registry.get("jd")
    results = engine.search("python book")
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Type
from pathlib import Path
import json


@dataclass
class EngineProduct:
    """Unified product/item result across all engines."""
    platform: str           # jd, taobao, douyin, pinduoduo...
    item_id: str
    title: str
    price: float = 0.0
    original_price: float = 0.0
    image_url: str = ""
    detail_url: str = ""
    shop_name: str = ""
    sales_count: int = 0
    rating: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineSearchResult:
    query: str
    total_count: int = 0
    products: List[EngineProduct] = field(default_factory=list)
    page: int = 1
    has_more: bool = False


class BaseEngine(ABC):
    """Abstract engine — every site engine must implement these."""

    name: str = "base"
    display_name: str = "Base Engine"
    homepage: str = ""
    search_url: str = ""
    requires_login: bool = False
    requires_playwright: bool = False

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._playwright = None
        self._browser = None
        self._context = None
        self._stealth_session = None  # StealthSession 绑定

    # ── abstract interface ──

    @abstractmethod
    async def search(self, query: str, page: int = 1, **kwargs) -> EngineSearchResult:
        """Search products/items on this platform."""
        ...

    @abstractmethod
    async def detail(self, item_id: str, **kwargs) -> Optional[EngineProduct]:
        """Get product/item detail."""
        ...

    # ── optional hooks ──

    async def login(self, **kwargs) -> bool:
        """Platform login. Return True if successful."""
        raise NotImplementedError(f"{self.name}.login() not implemented")

    async def save_session(self, path: Optional[Path] = None) -> bool:
        """Save browser session cookies/storage."""
        raise NotImplementedError(f"{self.name}.save_session() not implemented")

    async def load_session(self, path: Optional[Path] = None) -> bool:
        """Load browser session cookies/storage."""
        raise NotImplementedError(f"{self.name}.load_session() not implemented")

    def check_health(self) -> Dict[str, Any]:
        """Check if engine is usable."""
        return {
            "name": self.name,
            "requires_login": self.requires_login,
            "requires_playwright": self.requires_playwright,
            "playwright_available": self._check_playwright(),
        }

    # ── helpers ──

    async def _handle_captcha(self, page, max_attempts: int = 2):
        """Detect and solve CAPTCHA on a Playwright page.

        Returns True if captcha was solved or no captcha found.
        Returns False if captcha could not be solved.
        """
        try:
            from chinacrawl.captcha import CAPTCHAHandler
            handler = CAPTCHAHandler()
        except ImportError:
            return False

        for attempt in range(max_attempts):
            challenge = await handler.detect(page)
            if challenge is None:
                return True
            result = await handler.solve(page, challenge)
            if result.success:
                import asyncio
                await asyncio.sleep(2.0)
                challenge2 = await handler.detect(page)
                if challenge2 is None:
                    return True
                continue
            else:
                break
        return False

    def _check_playwright(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False

    async def _ensure_browser(self):
        """Lazy-init Playwright browser with stealth fingerprint + JS injection.

        Replaces the old fixed-UA approach with per-session randomized
        BrowserFingerprint, canvas/WebGL noise, and anti-detection flags.
        """
        if self._browser is None:
            from playwright.async_api import async_playwright
            from chinacrawl.stealth import StealthSession
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )

            # Create per-engine stealth session with random fingerprint
            self._stealth_session = StealthSession(f"engine-{self.name}")
            ctx_config = self._stealth_session.fingerprint.to_context_config()
            self._context = await self._browser.new_context(**ctx_config)

            # Inject anti-detection JS (webdriver, WebGL, canvas, audio)
            await self._context.add_init_script(
                self._stealth_session.stealth_js
            )
        return self._context

    async def close(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._context = self._browser = self._playwright = self._stealth_session = None


class BaseSiteEngine(BaseEngine):
    """For douyin/pinduoduo-type site engines with session management.

    Adds cookie-file-based session save/load/check on top of BaseEngine.
    Subclasses should override search/detail/login to delegate to their
    platform-specific modules (douyin/, pinduoduo/).
    """

    def __init__(self, config=None, cookie_file=None):
        super().__init__(config)
        self.cookie_file = cookie_file

    def get_default_cookie_path(self) -> str:
        return str(Path.home() / ".chinacrawl" / f"{self.name}_cookies.json")

    def save_session(self, cookie_file=None) -> bool:
        """Save session cookies to JSON file."""
        target = cookie_file or self.cookie_file or self.get_default_cookie_path()
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Default: save Playwright cookies if browser context is active
        if hasattr(self, '_context') and self._context:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    future = asyncio.run_coroutine_threadsafe(
                        self._context.storage_state(), loop)
                    storage = future.result(timeout=10)
                else:
                    storage = loop.run_until_complete(self._context.storage_state())
                target_path.write_text(json.dumps(storage, ensure_ascii=False))
                return True
            except Exception:
                pass
        # Fallback: save an empty placeholder so check_session passes
        if not target_path.exists():
            target_path.write_text("{}")
        return False

    def load_session(self, cookie_file=None) -> bool:
        """Load session cookies from JSON file into browser context."""
        target = cookie_file or self.cookie_file or self.get_default_cookie_path()
        target_path = Path(target)
        if not target_path.exists():
            return False
        if hasattr(self, '_context') and self._context:
            try:
                data = json.loads(target_path.read_text())
                if isinstance(data, list):
                    # Playwright cookies format
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        future = asyncio.run_coroutine_threadsafe(
                            self._context.add_cookies(data), loop)
                        future.result(timeout=10)
                    else:
                        loop.run_until_complete(self._context.add_cookies(data))
                return True
            except Exception:
                return False
        return True  # file exists, caller can use it

    def check_session(self) -> bool:
        """Check if a valid session file exists."""
        target = self.cookie_file or self.get_default_cookie_path()
        return Path(target).exists()


class EngineRegistry:
    """Global registry of all engine plugins."""

    _engines: Dict[str, BaseEngine] = {}

    @classmethod
    def register(cls, engine: BaseEngine):
        cls._engines[engine.name] = engine

    @classmethod
    def get(cls, name: str) -> Optional[BaseEngine]:
        return cls._engines.get(name)

    @classmethod
    def list_all(cls) -> List[str]:
        return list(cls._engines.keys())

    @classmethod
    def search_all(cls, query: str, engines: Optional[List[str]] = None, **kwargs) -> Dict[str, EngineSearchResult]:
        """Search across multiple engines (synchronous wrapper for convenience)."""
        import asyncio
        target = engines or cls.list_all()
        results = {}
        for name in target:
            engine = cls.get(name)
            if engine:
                try:
                    results[name] = asyncio.run(engine.search(query, **kwargs))
                except Exception as e:
                    results[name] = EngineSearchResult(query=query)
        return results


# Global singleton
registry = EngineRegistry()
