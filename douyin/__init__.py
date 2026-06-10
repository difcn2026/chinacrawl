# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Public API
# Created: 2026-06-07
# Updated: 2026-06-10 - Added browser_fetch fallbacks

"""
抖音适配器 - 公开 API

用法:
    from chinacrawl.douyin import user_posts, user_info
    from chinacrawl.douyin import browser_extract_video_ids
"""

from .scraper import (
    user_info,
    user_posts,
    user_likes,
    video_info,
    video_download,
    video_comments,
    search,
    search_user,
    search_hashtag,
    monitor_user,
    monitor_hashtag,
    # Browser fallback (2026-06经验: API返回二进制,以下绕过)
    browser_extract_video_ids,
    browser_download_video,
    login,
    save_session,
    load_session,
    check_session,
)

from .scraper import (
    UserInfo,
    AwemeInfo,
    CommentInfo,
    SearchResult,
    SearchResult as douyin_search_result_t,
)

__all__ = [
    # Data models
    "UserInfo", "AwemeInfo", "CommentInfo", "SearchResult", "douyin_search_result_t",
    # User operations
    "user_info", "user_posts", "user_likes",
    # Video operations
    "video_info", "video_download", "video_comments",
    # Search operations
    "search", "search_user", "search_hashtag",
    # Monitor operations
    "monitor_user", "monitor_hashtag",
    # Browser fallback (2026-06)
    "browser_extract_video_ids", "browser_download_video",
    # Session management
    "login", "save_session", "load_session", "check_session",
]
