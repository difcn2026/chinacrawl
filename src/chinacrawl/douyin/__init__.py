# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin (抖音) Platform Adapter for ChinaCrawl
# Created: 2026-06-07 | v0.1.0-dev

"""
ChinaCrawl Douyin Adapter - 抖音平台数据采集模块.

双通道架构: Web API (优先) → Playwright Browser (降级)

Quick start:
    from chinacrawl.douyin import user_posts, video_download

    for post in user_posts("user_sec_uid"):
        video_download(post.aweme_id, output_dir="./downloads/")
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
    # Session management
    "login", "save_session", "load_session", "check_session",
]
