# chinacrawl/core/session.py - Shared session/cookie management
# Platform-agnostic. Adapters pass their own cookie file paths.

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta

log = logging.getLogger("chinacrawl.core.session")

CST = timezone(timedelta(hours=8))
DEFAULT_COOKIE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "sessions")


def get_cookie_dir() -> str:
    """Get default cookie directory, creating it if needed."""
    os.makedirs(DEFAULT_COOKIE_DIR, exist_ok=True)
    return DEFAULT_COOKIE_DIR


def save_session(cookie_file: str, cookies: list) -> bool:
    """
    Save browser cookies to a JSON file.
    
    Args:
        cookie_file: Path to save cookies
        cookies: List of cookie dicts from Playwright context.cookies()
    """
    try:
        cookies_serializable = []
        for c in cookies:
            cookies_serializable.append({
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ""),
                "path": c.get("path", "/"),
                "expires": c.get("expires", -1),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", False),
                "sameSite": c.get("sameSite", "Lax"),
            })
        
        os.makedirs(os.path.dirname(cookie_file) or ".", exist_ok=True)
        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump({
                "cookies": cookies_serializable,
                "saved_at": datetime.now(CST).isoformat(),
            }, f, ensure_ascii=False, indent=2)
        
        log.info("Session saved: %s (%d cookies)", cookie_file, len(cookies_serializable))
        return True
    except Exception as e:
        log.error("Failed to save session: %s", e)
        return False


def load_session(cookie_file: str) -> bool:
    """
    Check if a cookie file exists and is readable.
    
    Returns True if the cookie file is valid.
    """
    if not os.path.exists(cookie_file):
        log.warning("Cookie file not found: %s", cookie_file)
        return False
    
    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = data.get("cookies", [])
        if not cookies:
            log.warning("Cookie file is empty: %s", cookie_file)
            return False
        
        saved_at = data.get("saved_at", "")
        if saved_at:
            try:
                saved_dt = datetime.fromisoformat(saved_at)
                age = datetime.now(CST) - saved_dt
                if age.days > 7:
                    log.warning("Session is %d days old, may need refresh", age.days)
            except ValueError:
                pass
        
        log.info("Session loaded: %s (%d cookies)", cookie_file, len(cookies))
        return True
    except (json.JSONDecodeError, KeyError) as e:
        log.error("Invalid cookie file: %s - %s", cookie_file, e)
        return False


def check_session(cookie_file: str, test_url: str, 
                  logged_in_js: str = "() => { return true; }") -> bool:
    """
    Validate a session by navigating to a test URL and checking login state.
    
    Args:
        cookie_file: Path to cookie JSON
        test_url: URL to visit for validation
        logged_in_js: JavaScript expression that returns true if logged in
    """
    from .browser import launch_browser, create_context
    
    if not load_session(cookie_file):
        return False
    
    try:
        browser = launch_browser(headless=True)
        context = create_context(browser, cookie_file=cookie_file)
        page = context.new_page()
        page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        
        is_logged = page.evaluate(logged_in_js)
        
        page.close()
        context.close()
        return bool(is_logged)
    except Exception as e:
        log.warning("Session check failed: %s", e)
        return False
