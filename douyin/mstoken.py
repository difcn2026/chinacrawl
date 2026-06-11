"""
msToken Extraction Utility for Douyin API.

Extracts msToken from browser's localStorage['xmst'] by:
1. Launching a headless browser
2. Navigating to douyin.com to initialize security SDK
3. Navigate to a search page to trigger msToken generation
4. Extract xmst from localStorage

Usage:
    from chinacrawl.douyin.mstoken import extract_mstoken, get_cached_mstoken
    
    # Get fresh msToken
    ms_token = extract_mstoken(cookie_file="path/to/cookies.json")
    
    # Or use cached version (auto-refresh if expired)
    ms_token = get_cached_mstoken(cookie_file="path/to/cookies.json")
    
Note: msToken is needed for SOME API endpoints but the search API 
specifically requires the full byted_acrawler SDK (Shark anti-bot).
For search, use browser.search_via_xhr() instead.
"""
import json
import logging
import os
import time
import urllib.parse
from typing import Optional

log = logging.getLogger("chinacrawl.douyin.mstoken")

# Cache settings
_MSTOKEN_CACHE = {}
_MSTOKEN_TTL = 300  # 5 minutes

# Default cookie paths to try
_DEFAULT_COOKIE_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "sessions", "douyin_default.json"),
    os.path.join(os.path.dirname(__file__), "..", ".cache", "sessions", "douyin_default.json"),
]


def _find_cookie_file(cookie_file: Optional[str] = None) -> Optional[str]:
    """Find the douyin cookie file."""
    if cookie_file and os.path.exists(cookie_file):
        return cookie_file
    for path in _DEFAULT_COOKIE_PATHS:
        if os.path.exists(path):
            return path
    return None


def extract_mstoken(cookie_file: Optional[str] = None,
                    headless: bool = True,
                    timeout: int = 30) -> str:
    """
    Extract a fresh msToken from browser.
    
    Args:
        cookie_file: Path to saved Playwright cookies JSON
        headless: Run browser in headless mode
        timeout: Max wait time in seconds
        
    Returns:
        msToken string (or empty string if extraction fails)
    """
    cookie_file = _find_cookie_file(cookie_file)
    
    try:
        from .browser import launch_browser, _create_context
        from .config import BROWSER_NAV_TIMEOUT
    except ImportError as e:
        log.error("Browser module not available: %s", e)
        return ""
    
    browser = None
    context = None
    page = None
    
    try:
        browser = launch_browser(headless=headless)
        context = _create_context(browser, cookie_file=cookie_file)
        page = context.new_page()
        
        # Navigate to douyin.com to init security SDK
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(3)
        
        # Navigate to a search page to trigger msToken generation
        encoded = urllib.parse.quote("test")
        page.goto(f"https://www.douyin.com/search/{encoded}?type=general",
                  wait_until="domcontentloaded", timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(5)
        
        # Scroll to trigger API calls
        for i in range(3):
            page.evaluate("window.scrollBy(0, 500)")
            time.sleep(1.5)
            
            # Check if msToken appeared
            xmst = page.evaluate("() => localStorage.getItem('xmst')")
            if xmst:
                break
        
        ms_token = page.evaluate("() => localStorage.getItem('xmst')") or ""
        
        if ms_token:
            log.info("Extracted msToken: %s...", ms_token[:30])
        else:
            log.warning("msToken not found after search + scroll")
        
        return ms_token
        
    except Exception as e:
        log.error("msToken extraction failed: %s", e)
        return ""
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass
        if context:
            try:
                context.close()
            except Exception:
                pass


def get_cached_mstoken(cookie_file: Optional[str] = None,
                       force_refresh: bool = False) -> str:
    """
    Get msToken from cache or extract fresh one.
    
    Args:
        cookie_file: Path to cookie file
        force_refresh: Force fresh extraction
        
    Returns:
        msToken string
    """
    cookie_file = cookie_file or "default"
    
    now = time.time()
    cached = _MSTOKEN_CACHE.get(cookie_file)
    
    if not force_refresh and cached:
        token, timestamp = cached
        if now - timestamp < _MSTOKEN_TTL:
            log.debug("Using cached msToken (age: %.0fs)", now - timestamp)
            return token
    
    token = extract_mstoken(cookie_file=cookie_file)
    if token:
        _MSTOKEN_CACHE[cookie_file] = (token, now)
    
    return token


def clear_cache():
    """Clear msToken cache."""
    _MSTOKEN_CACHE.clear()
