# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Core Scraper Orchestrator
# Created: 2026-06-07

"""
核心采集编排层。

双通道策略:
  API Channel (优先) -> Browser Channel (降级)

公共 API:
  from chinacrawl.douyin import user_posts, video_download, search, ...
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Generator, List, Optional
from urllib.parse import urlparse

import httpx

from . import api
from . import browser
from .config import RATE_LIMITS as RL

log = logging.getLogger("chinacrawl.douyin.scraper")

CST = timezone(timedelta(hours=8))


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

@dataclass
class UserInfo:
    """抖音用户信息"""
    sec_uid: str
    nickname: str = ""
    unique_id: str = ""
    avatar_url: str = ""
    signature: str = ""
    follower_count: int = 0
    following_count: int = 0
    aweme_count: int = 0
    total_favorited: int = 0
    verified: bool = False
    enterprise: bool = False
    region: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "UserInfo":
        user = data.get("user", data)
        avatar = user.get("avatar_thumb", user.get("avatar_medium", {}))
        avatar_url = ""
        if isinstance(avatar, dict):
            for k in ("url_list", "url"):
                urls = avatar.get(k, [])
                if isinstance(urls, list) and urls:
                    avatar_url = urls[0]
                    break

        return cls(
            sec_uid=user.get("sec_uid", ""),
            nickname=user.get("nickname", ""),
            unique_id=user.get("unique_id", user.get("short_id", "")),
            avatar_url=avatar_url,
            signature=user.get("signature", ""),
            follower_count=user.get("follower_count", 0),
            following_count=user.get("following_count", 0),
            aweme_count=user.get("aweme_count", 0),
            total_favorited=user.get("total_favorited", 0),
        verified=bool(user.get("custom_verify") or user.get("verification_type", 0) > 0),
            enterprise=user.get("enterprise_verify_reason", "") != "",
            region=user.get("region", "").replace("IP属地：", ""),
            raw=user,
        )

    @classmethod
    def from_browser(cls, data: dict) -> "UserInfo":
        user = data.get("user", data)
        return cls(
            sec_uid=user.get("sec_uid", user.get("secUid", "")),
            nickname=user.get("nickname", user.get("nickName", "")),
            unique_id=user.get("unique_id", user.get("shortId", user.get("uniqueId", ""))),
            avatar_url=user.get("avatar_thumb", user.get("avatar_url", "")),
            signature=user.get("signature", ""),
            follower_count=user.get("follower_count", user.get("followerCount", 0)),
            following_count=user.get("following_count", user.get("followingCount", 0)),
            aweme_count=user.get("aweme_count", user.get("awemeCount", 0)),
            total_favorited=user.get("total_favorited", user.get("totalFavorited", 0)),
            raw=user,
        )


@dataclass
class AwemeInfo:
    """单条抖音作品"""
    aweme_id: str
    desc: str = ""
    create_time: Optional[datetime] = None
    duration: int = 0  # ms
    video_url: str = ""
    cover_url: str = ""
    digg_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    play_count: int = 0
    music_title: str = ""
    hashtags: List[str] = field(default_factory=list)
    is_top: bool = False
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "AwemeInfo":
        video = data.get("video", {})
        play_addr = video.get("play_addr", video.get("play_addr_h264", {}))
        video_url = ""
        if isinstance(play_addr, dict):
            urls = play_addr.get("url_list", [])
            if urls:
                video_url = urls[0]

        cover = video.get("cover", {})
        cover_url = ""
        if isinstance(cover, dict):
            cover_urls = cover.get("url_list", [])
            if cover_urls:
                cover_url = cover_urls[0]

        music = data.get("music", {})
        stats = data.get("statistics", {})

        ct = data.get("create_time", 0)
        create_time = datetime.fromtimestamp(ct, tz=CST) if ct else None

        hashtags = []
        text_extra = data.get("text_extra", [])
        for t in text_extra:
            tag = t.get("hashtag_name", "")
            if tag:
                hashtags.append(tag)

        return cls(
            aweme_id=str(data.get("aweme_id", "")),
            desc=data.get("desc", ""),
            create_time=create_time,
            duration=data.get("duration", 0),
            video_url=video_url,
            cover_url=cover_url,
            digg_count=stats.get("digg_count", 0),
            comment_count=stats.get("comment_count", 0),
            share_count=stats.get("share_count", 0),
            play_count=stats.get("play_count", 0),
            music_title=music.get("title", music.get("author", "")),
            hashtags=hashtags,
            is_top=data.get("is_top", 0) == 1,
            raw=data,
        )

    @classmethod
    def from_browser(cls, data: dict) -> "AwemeInfo":
        video = data.get("video", {})
        play_addr = video.get("playAddr", video.get("play_addr", {}))
        video_url = ""
        if isinstance(play_addr, dict):
            urls = play_addr.get("urlList", play_addr.get("url_list", []))
            if urls:
                video_url = urls[0]

        cover = video.get("cover", {})
        cover_url = ""
        if isinstance(cover, dict):
            urls = cover.get("urlList", cover.get("url_list", []))
            if urls:
                cover_url = urls[0]

        stats = data.get("statistics", data.get("stats", {}))
        ct = data.get("createTime", data.get("create_time", 0))
        create_time = datetime.fromtimestamp(ct, tz=CST) if ct else None

        return cls(
            aweme_id=str(data.get("awemeId", data.get("aweme_id", ""))),
            desc=data.get("desc", data.get("description", "")),
            create_time=create_time,
            duration=data.get("duration", 0),
            video_url=video_url,
            cover_url=cover_url,
            digg_count=stats.get("diggCount", stats.get("digg_count", 0)),
            comment_count=stats.get("commentCount", stats.get("comment_count", 0)),
            share_count=stats.get("shareCount", stats.get("share_count", 0)),
            play_count=stats.get("playCount", stats.get("play_count", 0)),
            is_top=data.get("isTop", data.get("is_top", 0)) == 1,
            raw=data,
        )


@dataclass
class CommentInfo:
    """评论信息"""
    cid: str
    text: str = ""
    create_time: Optional[datetime] = None
    digg_count: int = 0
    reply_count: int = 0
    user_nickname: str = ""
    user_avatar: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "CommentInfo":
        user = data.get("user", {})
        ct = data.get("create_time", 0)
        return cls(
            cid=str(data.get("cid", "")),
            text=data.get("text", ""),
            create_time=datetime.fromtimestamp(ct, tz=CST) if ct else None,
            digg_count=data.get("digg_count", 0),
            reply_count=data.get("reply_comment_total", 0),
            user_nickname=user.get("nickname", ""),
            user_avatar=user.get("avatar_thumb", {}).get("url_list", [""])[0] if isinstance(user.get("avatar_thumb"), dict) else "",
            raw=data,
        )


@dataclass
class SearchResult:
    """搜索结果项"""
    result_type: str = ""  # "video", "user", "hashtag"
    aweme: Optional[AwemeInfo] = None
    user: Optional[UserInfo] = None
    hashtag_name: str = ""
    hashtag_view_count: int = 0
    raw: dict = field(default_factory=dict, repr=False)


# ═══════════════════════════════════════════════════════════════
# Dual-Channel Fallback Engine
# ═══════════════════════════════════════════════════════════════

def _api_then_browser(api_fn, browser_fn, *args, **kwargs):
    """
    双通道降级引擎: API优先 → Browser兜底.

    Args:
        api_fn: API层函数
        browser_fn: Playwright降级函数
        *args, **kwargs: 传递给两个函数的参数

    Returns:
        成功时返回API结果，失败时降级到Browser结果
    """
    channel = "api"
    try:
        result = api_fn(*args, **kwargs)
        log.info("Channel %s OK", channel)
        return result, channel
    except (api.DouyinRateLimitError, api.DouyinAPIError) as e:
        log.warning("API failed (%s), falling back to browser...", e)
        channel = "browser"
        try:
            result = browser_fn(*args, **kwargs)
            log.info("Browser fallback OK")
            return result, channel
        except Exception as be:
            log.error("Both channels failed. API: %s, Browser: %s", e, be)
            raise RuntimeError(f"Douyin data collection failed: API={e}, Browser={be}") from be

    except Exception as e:
        log.error("Unexpected error: %s", e)
        raise


# ═══════════════════════════════════════════════════════════════
# User Operations
# ═══════════════════════════════════════════════════════════════

def user_info(sec_uid: str) -> UserInfo:
    """
    获取用户主页信息.

    Args:
        sec_uid: 用户加密ID (如 MS4wLjABAAAAxxx)

    Returns:
        UserInfo 对象
    """
    try:
        data = api.fetch_user_info(sec_uid)
        return UserInfo.from_api(data)
    except (api.DouyinRateLimitError, api.DouyinAPIError):
        data = browser.open_user_page(sec_uid)
        return UserInfo.from_browser(data)


def user_posts(sec_uid: str, max_pages: int = 0,
             cookie_file: Optional[str] = None,
             use_xhr: bool = True) -> Generator[AwemeInfo, None, None]:
    """
    迭代获取用户所有作品 (XHR拦截优先 -> API -> Browser三级降级).

    策略:
      1. XHR拦截 (推荐): 拦截浏览器内部API请求, 绕过X-Bogus签名, 全量采集
      2. API直连: 调用douyin.com内部API (需要X-Bogus签名, 常被拦截)
      3. Browser DOM: Playwright打开用户页提取 (仅首屏, 需登录)

    Args:
        sec_uid: 用户加密ID
        max_pages: 最大页数 (0=全部, 仅API/Browser通道使用)
        cookie_file: Cookie文件路径 (XHR通道需要, 默认自动查找)
        use_xhr: 优先使用XHR拦截通道 (默认True)

    Yields:
        AwemeInfo 对象
    """
    total = 0
    
    # Auto-detect cookie file
    if cookie_file is None and use_xhr:
        for candidate in [
            os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "sessions", "douyin_default.json"),
            os.path.join(os.path.dirname(__file__), "..", ".cache", "sessions", "douyin_default.json"),
        ]:
            if os.path.exists(candidate):
                cookie_file = candidate
                break
    
    # Channel 1: XHR Interception (Plan B - bypasses X-Bogus)
    if use_xhr and cookie_file:
        try:
            log.info("user_posts: Trying XHR interception channel...")
            raw_posts = browser.collect_user_posts_via_xhr(
                sec_uid, cookie_file=cookie_file, max_posts=max_pages * 35 if max_pages else 0
            )
            for rp in raw_posts:
                yield AwemeInfo.from_api(rp)
                total += 1
            log.info("user_posts XHR complete: %d posts", total)
            return
        except Exception as e:
            log.warning("XHR channel failed: %s, falling back...", e)
    
    # Channel 2: API direct (needs X-Bogus signature)
    cursor = 0
    page = 0
    while max_pages == 0 or page < max_pages:
        page += 1
        try:
            data = api.fetch_user_posts(sec_uid, max_cursor=cursor, count=35)
        except (api.DouyinRateLimitError, api.DouyinAPIError) as e:
            log.warning("API failed at page %d: %s, trying browser...", page, e)
            # Channel 3: Browser DOM fallback
            try:
                browser_data = browser.open_user_page(sec_uid, cookie_file=cookie_file)
                posts = browser_data.get("posts", [])
                for p in posts:
                    yield AwemeInfo.from_browser(p)
                    total += 1
                break
            except Exception:
                log.error("All channels failed at page %d", page)
                break

        aweme_list = data.get("aweme_list", [])
        if not aweme_list:
            break

        for aweme in aweme_list:
            yield AwemeInfo.from_api(aweme)
            total += 1

        has_more = data.get("has_more", 0)
        if not has_more:
            break

        cursor = data.get("max_cursor", 0)
        if cursor == 0:
            break

        time.sleep(2.0)

    log.info("user_posts complete: %d posts from %d pages", total, page)


def user_likes(sec_uid: str, max_pages: int = 0) -> Generator[AwemeInfo, None, None]:
    """获取用户喜欢的作品 (需要登录态)."""
    # Likes require authentication - use browser with cookies
    page = 0
    total = 0
    while max_pages == 0 or page < max_pages:
        page += 1
        try:
            data = api._get("user_likes",
                            sec_user_id=sec_uid,
                            max_cursor=0 if page == 1 else data.get("max_cursor", 0),
                            count=35)
        except Exception:
            break

        aweme_list = data.get("aweme_list", [])
        if not aweme_list:
            break
        for aweme in aweme_list:
            yield AwemeInfo.from_api(aweme)
            total += 1
        if not data.get("has_more", 0):
            break

    log.info("user_likes complete: %d posts", total)


# ═══════════════════════════════════════════════════════════════
# Video Operations
# ═══════════════════════════════════════════════════════════════

def video_info(aweme_id: str) -> AwemeInfo:
    """获取单条视频详情."""
    try:
        data = api.fetch_video_detail(aweme_id)
        detail = data.get("aweme_detail", data)
        return AwemeInfo.from_api(detail)
    except (api.DouyinRateLimitError, api.DouyinAPIError):
        data = browser.open_video_page(aweme_id)
        return AwemeInfo.from_browser(data)


def video_download(aweme_id: str, output_dir: str = "./downloads/",
                   filename: Optional[str] = None) -> str:
    """
    下载视频到本地.

    Args:
        aweme_id: 视频ID
        output_dir: 输出目录
        filename: 自定义文件名 (不含扩展名)

    Returns:
        保存的文件路径
    """
    info = video_info(aweme_id)
    if not info.video_url:
        raise ValueError(f"No video URL found for aweme_id={aweme_id}")

    os.makedirs(output_dir, exist_ok=True)
    if filename is None:
        # Sanitize desc for filename
        safe_desc = re.sub(r'[\\/:*?"<>|]', '_', info.desc[:40])
        filename = f"{safe_desc}_{aweme_id}"

    ext = ".mp4"
    parsed = urlparse(info.video_url)
    path_ext = os.path.splitext(parsed.path)[1]
    if path_ext in (".mp4", ".mov", ".webm"):
        ext = path_ext

    filepath = os.path.join(output_dir, f"{filename}{ext}")

    # Download with httpx
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.douyin.com/",
    }

    with httpx.Client(timeout=120, follow_redirects=True, headers=headers) as client:
        with client.stream("GET", info.video_url) as resp:
            resp.raise_for_status()
            total_bytes = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

    log.info("Downloaded: %s (%.1f MB)", filepath, downloaded / 1024 / 1024)
    return filepath


def video_comments(aweme_id: str, max_pages: int = 5) -> Generator[CommentInfo, None, None]:
    """迭代获取视频评论."""
    cursor = 0
    page = 0
    total = 0

    while page < max_pages:
        page += 1
        try:
            data = api.fetch_video_comments(aweme_id, cursor=cursor, count=50)
        except (api.DouyinRateLimitError, api.DouyinAPIError):
            break

        comments = data.get("comments", [])
        if not comments:
            break

        for c in comments:
            yield CommentInfo.from_api(c)
            total += 1

        has_more = data.get("has_more", 0)
        if not has_more:
            break
        cursor = data.get("cursor", 0)

    log.info("video_comments: %d comments from %d pages", total, page)


# ═══════════════════════════════════════════════════════════════
# Search Operations
# ═══════════════════════════════════════════════════════════════

def search(keyword: str, max_results: int = 20) -> List[SearchResult]:
    """
    通用搜索 (视频+用户+话题混合).

    Args:
        keyword: 搜索关键词
        max_results: 最大结果数

    Returns:
        SearchResult 列表
    """
    results: List[SearchResult] = []
    offset = 0

    while len(results) < max_results:
        try:
            data = api.search_general(keyword, offset=offset, count=min(20, max_results - len(results)))
        except (api.DouyinRateLimitError, api.DouyinAPIError):
            try:
                browser_results = browser.search(keyword, max_results)
                for r in browser_results:
                    sr = SearchResult(raw=r)
                    if "aweme" in r or "aweme_info" in r:
                        sr.result_type = "video"
                        aweme_data = r.get("aweme_info", r.get("aweme", r))
                        if aweme_data:
                            sr.aweme = AwemeInfo.from_browser(aweme_data)
                    elif "user_info" in r:
                        sr.result_type = "user"
                        sr.user = UserInfo.from_browser(r["user_info"])
                    results.append(sr)
                return results[:max_results]
            except Exception:
                return results

        items = data.get("data", [])
        if not items:
            break

        for item in items:
            sr = SearchResult(raw=item)
            item_type = item.get("type", "")

            if item_type == 1 or "aweme_info" in item:
                sr.result_type = "video"
                aweme_data = item.get("aweme_info", item)
                if aweme_data:
                    sr.aweme = AwemeInfo.from_api(aweme_data)
            elif item_type == 2 or "user_info" in item:
                sr.result_type = "user"
                user_data = item.get("user_info", item)
                if user_data:
                    sr.user = UserInfo.from_api(user_data)
            elif item_type == 3 or "challenge_info" in item:
                sr.result_type = "hashtag"
                challenge = item.get("challenge_info", {})
                sr.hashtag_name = challenge.get("cha_name", "")
                sr.hashtag_view_count = challenge.get("view_count", 0)

            results.append(sr)

        offset += len(items)
        if len(items) < 20:
            break

    return results[:max_results]


def search_user(keyword: str, max_results: int = 10) -> List[UserInfo]:
    """搜索用户."""
    results = []
    offset = 0

    while len(results) < max_results:
        try:
            data = api.search_user(keyword, offset=offset, count=min(10, max_results - len(results)))
        except (api.DouyinRateLimitError, api.DouyinAPIError):
            try:
                browser_results = browser.search(keyword, max_results)
                for r in browser_results:
                    if "user_info" in r:
                        results.append(UserInfo.from_browser(r["user_info"]))
                return results[:max_results]
            except Exception:
                return results

        items = data.get("user_list", data.get("data", []))
        if not items:
            break
        for item in items:
            user_data = item.get("user_info", item)
            if user_data:
                results.append(UserInfo.from_api(user_data))
        offset += len(items)

    return results[:max_results]


def search_hashtag(keyword: str, max_results: int = 10) -> List[dict]:
    """搜索话题标签."""
    results = []
    offset = 0
    while len(results) < max_results:
        try:
            data = api.search_general(keyword, offset=offset, count=min(10, max_results - len(results)))
        except Exception:
            break
        items = data.get("data", [])
        if not items:
            break
        for item in items:
            if item.get("type") == 3 or "challenge_info" in item:
                challenge = item.get("challenge_info", {})
                results.append({
                    "name": challenge.get("cha_name", ""),
                    "view_count": challenge.get("view_count", 0),
                    "user_count": challenge.get("user_count", 0),
                    "desc": challenge.get("desc", ""),
                })
        offset += len(items)
    return results[:max_results]


# ═══════════════════════════════════════════════════════════════
# Monitor Operations
# ═══════════════════════════════════════════════════════════════

def monitor_user(sec_uid: str, label: str = "") -> dict:
    """
    监控用户变化 (Hash-based).

    Args:
        sec_uid: 用户加密ID
        label: 监控标签

    Returns:
        {
            "label": str,
            "changed": bool,
            "new_posts": int,
            "prev_hash": str,
            "curr_hash": str,
        }
    """
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "douyin_monitor")
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = label or f"user_{sec_uid}"
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")

    # Collect current state snapshot
    posts_data = []
    try:
        for post in user_posts(sec_uid, max_pages=3):
            posts_data.append({
                "aweme_id": post.aweme_id,
                "desc": post.desc,
                "digg_count": post.digg_count,
                "comment_count": post.comment_count,
            })
    except Exception as e:
        log.error("Monitor collection failed: %s", e)
        return {"label": cache_key, "changed": False, "error": str(e)}

    curr_hash = hashlib.sha256(
        json.dumps(posts_data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    result = {
        "label": cache_key,
        "changed": False,
        "new_posts": 0,
        "prev_hash": "",
        "curr_hash": curr_hash,
        "total_posts": len(posts_data),
    }

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            prev = json.load(f)
        prev_hash = prev.get("hash", "")
        result["prev_hash"] = prev_hash
        if curr_hash != prev_hash:
            prev_ids = {p["aweme_id"] for p in prev.get("posts", [])}
            curr_ids = {p["aweme_id"] for p in posts_data}
            new_ids = curr_ids - prev_ids
            result["changed"] = True
            result["new_posts"] = len(new_ids)
    else:
        result["prev_hash"] = "(first run)"

    # Save current state
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"hash": curr_hash, "posts": posts_data, "updated": datetime.now(CST).isoformat()},
                  f, ensure_ascii=False, indent=2)

    return result


def monitor_hashtag(keyword: str, label: str = "") -> dict:
    """
    监控话题标签变化 (Hash-based).

    Args:
        keyword: 话题关键词
        label: 监控标签

    Returns:
        同 monitor_user 结构
    """
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "douyin_monitor")
    os.makedirs(cache_dir, exist_ok=True)
    cache_key = label or f"tag_{keyword}"
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")

    try:
        results = search(keyword, max_results=20)
    except Exception as e:
        return {"label": cache_key, "changed": False, "error": str(e)}

    posts_data = []
    for r in results:
        if r.aweme:
            posts_data.append({
                "aweme_id": r.aweme.aweme_id,
                "desc": r.aweme.desc,
                "digg_count": r.aweme.digg_count,
            })

    curr_hash = hashlib.sha256(
        json.dumps(posts_data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    result = {
        "label": cache_key,
        "changed": False,
        "new_posts": 0,
        "prev_hash": "",
        "curr_hash": curr_hash,
        "total_posts": len(posts_data),
    }

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            prev = json.load(f)
        prev_hash = prev.get("hash", "")
        result["prev_hash"] = prev_hash
        if curr_hash != prev_hash:
            prev_ids = {p["aweme_id"] for p in prev.get("posts", [])}
            curr_ids = {p["aweme_id"] for p in posts_data}
            new_ids = curr_ids - prev_ids
            result["changed"] = True
            result["new_posts"] = len(new_ids)
    else:
        result["prev_hash"] = "(first run)"

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({"hash": curr_hash, "posts": posts_data, "updated": datetime.now(CST).isoformat()},
                  f, ensure_ascii=False, indent=2)

    return result


# ═══════════════════════════════════════════════════════════════
# Session Management (thin wrappers, real logic in session.py)
# ═══════════════════════════════════════════════════════════════

def login(method: str = "qr", cookie_file: Optional[str] = None) -> dict:
    """登录抖音 (QR码扫码)."""
    from . import session as ses
    return ses.login(method=method, cookie_file=cookie_file)


def save_session(cookie_file: str) -> bool:
    """保存当前登录态."""
    from . import session as ses
    return ses.save_session(cookie_file)


def load_session(cookie_file: str) -> bool:
    """加载已保存的登录态."""
    from . import session as ses
    return ses.load_session(cookie_file)


def check_session() -> bool:
    """检查登录态是否有效."""
    from . import session as ses
    return ses.check_session()
