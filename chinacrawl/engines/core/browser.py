# chinacrawl/core/browser.py - Shared Playwright browser layer
# Used by all platform adapters: pinduoduo, douyin, etc.

import json
import logging
import os
from typing import Optional

log = logging.getLogger("chinacrawl.core.browser")

_playwright = None
_browser = None

# Default browser args - platform adapters can override
DEFAULT_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--disable-web-security",
    "--disable-features=VizDisplayCompositor",
    "--disable-gpu",
]


def _get_playwright():
    """Lazy import Playwright (optional dependency)"""
    global _playwright
    if _playwright is None:
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright().start()
    return _playwright


def launch_browser(headless: bool = True, extra_args: Optional[list] = None, channel: Optional[str] = None):
    """
    Launch Chromium browser with anti-detection config.
    
    Args:
        headless: Run in headless mode
        extra_args: Additional Chromium args (appended to defaults)
        channel: Browser channel (chrome, msedge, or None for bundled chromium)
    
    Returns:
        Playwright Browser instance (singleton)
    """
    global _browser
    pw = _get_playwright()
    if _browser is None or not _browser.is_connected():
        args = list(DEFAULT_BROWSER_ARGS)
        if extra_args:
            args.extend(extra_args)
        _browser = pw.chromium.launch(
            headless=headless,
            args=args,
            channel=channel,
        )
    return _browser


def close_browser():
    """Close the browser singleton."""
    global _browser
    try:
        if _browser and _browser.is_connected():
            _browser.close()
    except Exception:
        pass
    _browser = None


def create_context(browser, cookie_file: Optional[str] = None,
                   context_overrides: Optional[dict] = None,
                   anti_detect_js: Optional[str] = None):
    """
    Create a browser context with anti-detection and cookie loading.
    
    Args:
        browser: Playwright Browser instance
        cookie_file: Path to JSON cookie file
        context_overrides: Dict of context options (viewport, user_agent, etc.)
        anti_detect_js: JavaScript string to inject for anti-detection
    
    Returns:
        Playwright BrowserContext
    """
    from .anti_detect import CONTEXT_OVERRIDES as DEFAULT_OVERRIDES, ANTI_DETECT_JS as DEFAULT_JS
    
    overrides = context_overrides or DEFAULT_OVERRIDES
    js = anti_detect_js or DEFAULT_JS
    
    context = browser.new_context(**overrides)
    
    # Inject anti-detection script
    context.add_init_script(js)
    
    # Load cookies if provided
    if cookie_file and os.path.exists(cookie_file):
        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                cookies_data = json.load(f)
            cookie_list = cookies_data.get("cookies", cookies_data) if isinstance(cookies_data, dict) else cookies_data
            if isinstance(cookie_list, list):
                context.add_cookies(cookie_list)
                log.info("Loaded %d cookies from %s", len(cookie_list), cookie_file)
        except Exception as e:
            log.warning("Failed to load cookies from %s: %s", cookie_file, e)
    
    return context
