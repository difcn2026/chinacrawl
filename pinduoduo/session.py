# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Session Management (Login/Cookie/State)
# Created: 2026-06-08

"""
登录态管理层.
支持:
  - 手机验证码登录 (最可靠)
  - QR 码扫码登录 (App扫码)
  - Cookie 持久化 (JSON文件)
  - 登录态校验 (访问个人中心验证)
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

log = logging.getLogger("chinacrawl.pinduoduo.session")

CST = timezone(timedelta(hours=8))
DEFAULT_COOKIE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "sessions")


def login(method: str = "qr", phone: Optional[str] = None,
          cookie_file: Optional[str] = None,
          headless: bool = False) -> dict:
    """
    登录拼多多.

    拼多多登录方式:
      - "qr"  : 打开移动端登录页，让用户用拼多多 App 扫码 (推荐)
      - "sms" : 手机验证码登录 (需要手机号和手动输入验证码)

    Args:
        method: 登录方式 - "qr" 或 "sms"
        phone: 手机号 (sms 方式必填)
        cookie_file: Cookie 保存路径 (默认 .cache/sessions/pinduoduo_default.json)
        headless: 无头模式 (登录需要可视化, 默认 False)

    Returns:
        {
            "ok": True/False,
            "cookies": int,
            "nickname": str,
            "file": str,
            "error": str,
        }
    """
    if cookie_file is None:
        os.makedirs(DEFAULT_COOKIE_DIR, exist_ok=True)
        cookie_file = os.path.join(DEFAULT_COOKIE_DIR, "pinduoduo_default.json")

    if method not in ("qr", "sms"):
        return {"ok": False, "error": f"Login method '{method}' not supported. Use 'qr' or 'sms'."}

    try:
        browser = launch_browser(headless=False)
        context = _create_context(browser)
        page = context.new_page()

        if method == "qr":
            # 使用移动端登录页（支持 App 扫码）
            page.goto("https://mobile.yangkeduo.com/login.html",
                      wait_until="domcontentloaded",
                      timeout=BROWSER_NAV_TIMEOUT)
            log.info("Waiting for QR code login... (120s timeout)")

            # 等待用户扫码登录
            try:
                # 检测登录成功 - URL 跳转回首页或个人中心
                page.wait_for_url(
                    lambda url: "login" not in url and "yangkeduo.com" in url,
                    timeout=120000
                )
            except Exception:
                # 超时检查是否已登录
                current_url = page.url
                if "login" in current_url:
                    return {"ok": False, "error": "Login timeout - no QR code scan detected after 120s"}

        elif method == "sms":
            if not phone:
                return {"ok": False, "error": "Phone number required for SMS login"}

            page.goto("https://mobile.yangkeduo.com/login.html",
                      wait_until="domcontentloaded",
                      timeout=BROWSER_NAV_TIMEOUT)

            # 切换到短信登录
            try:
                sms_tab = page.wait_for_selector('text=短信登录, [data-type="sms"], .sms-login',
                                                 timeout=5000)
                if sms_tab:
                    sms_tab.click()
            except Exception:
                pass

            # 输入手机号
            phone_input = page.wait_for_selector('input[type="tel"], input[placeholder*="手机"]',
                                                 timeout=5000)
            if phone_input:
                phone_input.fill(phone)

            # 点击发送验证码
            send_btn = page.query_selector('text=获取验证码, [class*="send-code"], .get-code')
            if send_btn:
                send_btn.click()

            log.info("SMS code sent to %s. Please enter the code in the browser window.", phone)
            log.info("Waiting for login completion... (180s timeout)")

            try:
                page.wait_for_url(
                    lambda url: "login" not in url and "yangkeduo.com" in url,
                    timeout=180000
                )
            except Exception:
                return {"ok": False, "error": "SMS login timeout"}

        # 提取 cookies
        cookies = context.cookies()
        if not cookies:
            return {"ok": False, "error": "No cookies collected - login may have failed"}

        # 保存 cookies
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
                "login_method": method,
                "user_agent": (CONTEXT_OVERRIDES.get("user_agent", "")),
            }, f, ensure_ascii=False, indent=2)

        # 尝试获取昵称
        nickname = ""
        try:
            nickname_el = page.query_selector('.user-name, [class*="nickname"], .nickname')
            if nickname_el:
                nickname = nickname_el.inner_text().strip()
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
    从当前浏览器保存登录 Session.

    这是 login() 的补充 —— 如果已经通过其他方式登录，可以直接保存 cookies.
    """
    try:
        browser = launch_browser(headless=False)
        context = _create_context(browser)
        page = context.new_page()
        page.goto("https://mobile.yangkeduo.com/",
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)

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
    检查 cookie 文件是否存在且可读.

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

    使用默认 cookie 文件 + 浏览器快速验证.
    """
    default_file = os.path.join(DEFAULT_COOKIE_DIR, "pinduoduo_default.json")

    if not os.path.exists(default_file):
        log.info("No default session found")
        return False

    if not load_session(default_file):
        return False

    # Quick validation: open PDD mobile page and check if logged in
    try:
        browser = launch_browser(headless=True)
        context = _create_context(browser, cookie_file=default_file)
        page = context.new_page()
        page.goto("https://mobile.yangkeduo.com/personal.html",
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(2)

        is_logged = page.evaluate("""() => {
            const userEl = document.querySelector('[class*="user"], [class*="nickname"], .personal-info');
            const loginBtn = document.querySelector('text=登录, [class*="login-btn"]');
            return !!userEl && !loginBtn;
        }""")

        page.close()
        context.close()
        return is_logged

    except Exception as e:
        log.warning("Session check failed: %s", e)
        return False


def get_default_cookie_path() -> str:
    """获取默认 cookie 文件路径."""
    os.makedirs(DEFAULT_COOKIE_DIR, exist_ok=True)
    return os.path.join(DEFAULT_COOKIE_DIR, "pinduoduo_default.json")


# Import here to avoid circular dependency
from .anti_detect import CONTEXT_OVERRIDES
