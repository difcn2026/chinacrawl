# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Session Management (Login/Cookie/State)
# Created: 2026-06-07
# Updated: 2026-06-10 - Improved QR login flow + cookie export

"""
登录态管理层。

支持:
  - QR码扫码登录 (可视化)
  - Cookie 持久化 (JSON文件)
  - Cookie 导出为 Netscape 格式（用于 yt-dlp 等工具）
  - Cookie 合并与去重
  - 登录态校验

经验记录 (2026-06-10):
  - QR 登录后 cookies 包含 sessionid 即表示成功
  - 关键 cookies: sessionid, sid_tt, ttwid, passport_csrf_token
  - yt-dlp 需要 Netscape 格式 cookie 文件
  - Cookies 过期后扫码重登即可刷新
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

# 抖音登录必须的关键 cookie 名称
KEY_COOKIES = {"sessionid", "sessionid_ss", "sid_guard", "sid_tt", "uid_tt", "ttwid", "passport_csrf_token"}


def login(method: str = "qr", cookie_file: Optional[str] = None,
          headless: bool = False, timeout: int = 120) -> dict:
    """
    登录抖音.

    Args:
        method: 登录方式 - "qr" (QR码扫码)
        cookie_file: Cookie 保存路径 (默认 .cache/sessions/douyin_default.json)
        headless: 是否无头模式 (登录需要可视化, 默认False)
        timeout: 等待扫码超时秒数 (默认120s)

    Returns:
        {
            "ok": True/False,
            "cookies": int,       # 保存的cookie数量
            "has_session": bool,  # 是否有 sessionid
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
        browser = launch_browser(headless=False)
        context = _create_context(browser)
        page = context.new_page()
        page.goto("https://www.douyin.com/",
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(3)

        # Check if already logged in
        cookies = context.cookies()
        has_session = any(c.get("name") == "sessionid" and c.get("value") for c in cookies)
        if has_session:
            log.info("✅ Already logged in (sessionid found)")
        else:
            log.info("⏳ Waiting for QR scan... (timeout=%ds)", timeout)
            # Wait for sessionid to appear (poll every 3s)
            start = time.time()
            logged_in = False
            while time.time() - start < timeout:
                time.sleep(3)
                cookies = context.cookies()
                has_session = any(c.get("name") == "sessionid" and c.get("value") for c in cookies)
                if has_session:
                    elapsed = int(time.time() - start)
                    log.info("✅ Login detected after %ds!", elapsed)
                    logged_in = True
                    break
                elapsed = int(time.time() - start)
                if elapsed % 15 == 0:
                    log.info("   Still waiting... (%ds)", elapsed)

            if not logged_in:
                return {"ok": False, "error": f"Login timeout after {timeout}s"}

        # Save cookies (merge with existing if any)
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

        # Merge with existing cookies (preserve old ones, overwrite with new)
        existing = {}
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                for c in old_data.get("cookies", []):
                    existing[c["name"]] = c
            except (json.JSONDecodeError, KeyError):
                pass

        for c in cookies_serializable:
            existing[c["name"]] = c

        merged = list(existing.values())

        os.makedirs(os.path.dirname(cookie_file) or ".", exist_ok=True)
        with open(cookie_file, "w", encoding="utf-8") as f:
            json.dump({
                "cookies": merged,
                "saved_at": datetime.now(CST).isoformat(),
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }, f, ensure_ascii=False, indent=2)

        # Get nickname
        nickname = ""
        try:
            nickname = page.evaluate("""() => {
                const el = document.querySelector('[class*="user-name"], [class*="nickname"], [data-e2e="user-info"]');
                return el ? el.innerText.trim().slice(0, 20) : '';
            }""")
        except Exception:
            pass

        page.close()
        context.close()

        return {
            "ok": True,
            "cookies": len(merged),
            "has_session": True,
            "nickname": nickname,
            "file": cookie_file,
        }

    except Exception as e:
        log.error("Login failed: %s", e)
        return {"ok": False, "error": str(e)}


def export_cookies_netscape(cookie_file: str, output_file: Optional[str] = None,
                             include_all: bool = False) -> Optional[str]:
    """
    将抖音 cookies 导出为 Netscape 格式（用于 yt-dlp 等工具）。

    Args:
        cookie_file: 输入 cookie JSON 文件路径
        output_file: 输出文件路径 (默认同目录 douyin_netscape.txt)
        include_all: 是否包含所有 cookies (默认只包含 KEY_COOKIES)

    Returns:
        str: 输出文件路径，失败返回 None

    Example:
        yt-dlp --cookies cookies_netscape.txt <url>
    """
    if not os.path.exists(cookie_file):
        log.error("Cookie file not found: %s", cookie_file)
        return None

    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        log.error("Invalid cookie file: %s", cookie_file)
        return None

    cookies = data.get("cookies", [])
    if not cookies:
        log.warning("No cookies found")
        return None

    if output_file is None:
        base = os.path.splitext(cookie_file)[0]
        output_file = base + "_netscape.txt"

    future_ts = str(int(time.time()) + 86400 * 30)  # 30 days from now

    lines = ["# Netscape HTTP Cookie File", "# Generated by chinacrawl.douyin.session"]
    for c in cookies:
        name = c.get("name", "")
        if not include_all and name not in KEY_COOKIES:
            continue
        domain = c.get("domain", "")
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        value = c.get("value", "")
        if not name or not value or not domain:
            continue
        if not domain.startswith("."):
            domain = "." + domain
        lines.append(f"{domain}\tTRUE\t{path}\t{secure}\t{future_ts}\t{name}\t{value}")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    count = len(lines) - 2
    log.info("Exported %d cookies to %s", count, output_file)
    return output_file


def validate_cookies(cookie_file: str) -> dict:
    """
    检查 cookie 文件是否有效，报告关键 cookie 状态。

    Returns:
        {
            "valid": bool,
            "has_sessionid": bool,
            "total": int,
            "key_cookies_present": [str],
            "age_days": float,
        }
    """
    result = {"valid": False, "has_sessionid": False, "total": 0, "key_cookies_present": [], "age_days": 0}

    if not os.path.exists(cookie_file):
        return result

    try:
        with open(cookie_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return result

    cookies = data.get("cookies", [])
    names = {c.get("name", "") for c in cookies}
    result["total"] = len(cookies)
    result["has_sessionid"] = "sessionid" in names
    result["key_cookies_present"] = sorted(KEY_COOKIES & names)
    result["valid"] = result["has_sessionid"]

    saved_at = data.get("saved_at", "")
    if saved_at:
        try:
            saved = datetime.fromisoformat(saved_at)
            result["age_days"] = round((datetime.now(CST) - saved).total_seconds() / 86400, 1)
        except ValueError:
            pass

    return result


def save_session(cookie_file: str) -> bool:
    """从当前浏览器保存登录 Session。"""
    try:
        browser = launch_browser(headless=False)
        context = _create_context(browser)
        page = context.new_page()
        page.goto("https://www.douyin.com/", wait_until="domcontentloaded",
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
    """检查 cookie 文件是否存在且有效。"""
    result = validate_cookies(cookie_file)
    if result["valid"]:
        age = result["age_days"]
        if age > 7:
            log.warning("Session is %.1f days old, may need refresh", age)
        log.info("Session loaded: %s (%d cookies, %d key present)",
                 cookie_file, result["total"], len(result["key_cookies_present"]))
        return True
    log.warning("Session invalid: %s", cookie_file)
    return False


def check_session() -> bool:
    """检查当前默认登录态是否有效（浏览器验证）。"""
    default_file = os.path.join(DEFAULT_COOKIE_DIR, "douyin_default.json")
    if not os.path.exists(default_file):
        log.info("No default session found")
        return False
    if not load_session(default_file):
        return False

    try:
        browser = launch_browser(headless=True)
        context = _create_context(browser, cookie_file=default_file)
        page = context.new_page()
        page.goto("https://www.douyin.com/",
                  wait_until="domcontentloaded",
                  timeout=BROWSER_NAV_TIMEOUT)
        time.sleep(2)

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
    """获取默认 cookie 文件路径。"""
    os.makedirs(DEFAULT_COOKIE_DIR, exist_ok=True)
    return os.path.join(DEFAULT_COOKIE_DIR, "douyin_default.json")
