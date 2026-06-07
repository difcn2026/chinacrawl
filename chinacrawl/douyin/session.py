# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Session Management (Login/Cookie/State)
# Created: 2026-06-07

"""
登录态管理层。

支持:
  - QR码扫码登录 (可视化)
  - Cookie 持久化 (JSON文件)
  - 登录态校验 (访问个人主页验证)
  - 自动刷新检测
"""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from .browser import launch_browser, _create_context
from .config import BROWSER_NAV_TIMEOUT

log = logging.getLogger("chinacrawl.douyin.session")

CST = timezone(timedelta(hours=8))
DEFAULT_COOKIE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "sessions")


def login(method: str = "qr", cookie_file: Optional[str] = None,
          headless: bool = False) -> dict:
    """
    登录抖音.

    Args:
        method: 登录方式 - "qr" (QR码扫码) 或 "phone" (手机验证码, 未实现)
        cookie_file: Cookie 保存路径 (默认 .cache/sessions/douyin_default.json)
        headless: 是否无头模式 (登录需要可视化, 默认False)

    Returns:
        {
            "ok": True/False,
            "cookies": int,       # 保存的cookie数量
            "nickname": str,      # 登录用户昵称
            "file": str,          # cookie文件路径
            "error": str,         # 错误信息
        }
    """
    if cookie_file is None:
        os.makedirs(DEFAULT_COOKIE_DIR, exist_ok=True)
        cookie_file = os.path.join(DEFAULT_COOKIE_DIR, "douyin_default.json")

    if method != "qr":
        return {"ok": False, "error": f"Login method '{method}' not yet supported. Use 'qr'."}

    try:
        browser = launch_browser(headless=False)  # Login always needs visible browser
        context = _create_context(browser)

        page = context.new_page()
        page.goto("https://www.douyin.com/",
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

        # Click the login button
        log.info("Waiting for QR code login... (60s timeout)")
        try:
            # Try finding and clicking login button
            login_btn = page.wait_for_selector(
                'text=登录, [data-e2e="login"], #login-pannel',
                timeout=10000
            )
            if login_btn:
                login_btn.click()
                log.info("Clicked login button")
        except Exception:
            log.info("Login panel may already be visible or auto-triggered")

        # Wait for login to complete (detect user info loaded)
        try:
            # Wait up to 120 seconds for login
            page.wait_for_selector(
                '[data-e2e="user-info"], [data-e2e="user-avatar"], .user-info',
                timeout=120000
            )
        except Exception:
            log.warning("Login timeout - no user info detected after 120s")

        # Extract cookies
        cookies = context.cookies()
        if not cookies:
            return {"ok": False, "error": "No cookies collected - login may have failed"}

        # Save cookies
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

        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump({
                "cookies": cookies_serializable,
                "saved_at": datetime.now(CST).isoformat(),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }, f, ensure_ascii=False, indent=2)

        # Try to get nickname
        nickname = ""
        try:
            nickname_el = page.query_selector('[data-e2e="user-info"] .nickname, .user-name')
            if nickname_el:
                nickname = nickname_el.inner_text()
        except Exception:
            pass

        page.close()
        context.close()

        return {
            "ok": True,
            "cookies": len(cookies_serializable),
            "nickname": nickname,
            "file": cookie_file,
        }

    except Exception as e:
        log.error("Login failed: %s", e)
        return {"ok": False, "error": str(e)}


def save_session(cookie_file: str) -> bool:
    """
    从当前浏览器保存登录Session.

    这是 login() 的补充 — 如果已经通过其他方式登录, 可以直接保存cookies.
    """
    try:
        browser = launch_browser(headless=False)
        context = _create_context(browser)
        page = context.new_page()
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

        # Wait a bit for any redirects/session restore
        time.sleep(3)

        cookies = context.cookies()

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

        page.close()
        context.close()
        log.info("Session saved: %s (%d cookies)", cookie_file, len(cookies_serializable))
        return True

    except Exception as e:
        log.error("Failed to save session: %s", e)
        return False


def load_session(cookie_file: str) -> bool:
    """
    检查cookie文件是否存在且可读.

    Returns:
        True if cookie file is valid
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

        # Check if session is too old (>7 days)
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


def check_session() -> bool:
    """
    检查当前默认登录态是否有效.

    使用默认cookie文件 + 浏览器快速验证.
    """
    default_file = os.path.join(DEFAULT_COOKIE_DIR, "douyin_default.json")

    if not os.path.exists(default_file):
        log.info("No default session found")
        return False

    if not load_session(default_file):
        return False

    # Quick validation: open douyin.com and check if logged in
    try:
        browser = launch_browser(headless=True)
        context = _create_context(browser, cookie_file=default_file)
        page = context.new_page()
        page.goto("https://www.douyin.com/",
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(2)

        # Check for login indicators
        is_logged = page.evaluate("""() => {
            const userMenu = document.querySelector('[data-e2e="user-info"]');
            const loginBtn = document.querySelector('[data-e2e="login"]');
            return !!userMenu && !loginBtn;
        }""")

        page.close()
        context.close()
        return is_logged

    except Exception as e:
        log.warning("Session check failed: %s", e)
        return False


def get_default_cookie_path() -> str:
    """获取默认cookie文件路径."""
    os.makedirs(DEFAULT_COOKIE_DIR, exist_ok=True)
    return os.path.join(DEFAULT_COOKIE_DIR, "douyin_default.json")
