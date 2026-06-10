"""ChinaCrawl - Chinese Web Search & Scraping Engine.

12-in-1 open-source alternative to Firecrawl for the Chinese internet.
Zero external API dependencies. AGPLv3 licensed.

Quick start:
    from chinacrawl import scrape, search_web
    result = scrape("https://example.com")
    results = search_web("Python 爬虫", max_results=10)

Douyin (TikTok China) adapter (v0.2.0):
    from chinacrawl import douyin_login, douyin_user_posts
    douyin_login()  # QR code login
    for post in douyin_user_posts("user_sec_uid"):
        print(post.desc, post.digg_count)
"""

from .scraper import (
    ScrapeResult, PageLink, SearchResult, MonitorResult,
    MonitorAIResult, CrawlResult, ExtractResult,
    scrape, scrape_jina, scrape_trafilatura, scrape_many,
    map_site, search_web, search_and_scrape,
    monitor_page, monitor_page_ai,
    crawl_site, download_site,
    browser_interact,
    browser_session_save, browser_session_load, browser_session_close,
    extract_structured, extract_llm,
    CAPABILITIES, SEARXNG_INSTANCES, PROXY, TIMEOUT,
)

# ── Douyin (TikTok China) Adapter ──────────────────────────
DOUYIN_AVAILABLE = False
try:
    from .douyin import (
        UserInfo as DouyinUserInfo,
        AwemeInfo as DouyinAwemeInfo,
        CommentInfo as DouyinCommentInfo,
        douyin_search_result_t as DouyinSearchResult,
        user_info as douyin_user_info,
        user_posts as douyin_user_posts,
        user_likes as douyin_user_likes,
        video_info as douyin_video_info,
        video_download as douyin_video_download,
        video_comments as douyin_video_comments,
        search as douyin_search,
        search_user as douyin_search_user,
        search_hashtag as douyin_search_hashtag,
        monitor_user as douyin_monitor_user,
        monitor_hashtag as douyin_monitor_hashtag,
        login as douyin_login,
        save_session as douyin_save_session,
        load_session as douyin_load_session,
        check_session as douyin_check_session,
    )
    DOUYIN_AVAILABLE = True
except ImportError:
    pass

__version__ = "0.2.0"
__all__ = [
    "ScrapeResult", "PageLink", "SearchResult", "MonitorResult",
    "MonitorAIResult", "CrawlResult", "ExtractResult",
    "scrape", "scrape_jina", "scrape_trafilatura", "scrape_many",
    "map_site", "search_web", "search_and_scrape",
    "monitor_page", "monitor_page_ai",
    "crawl_site", "download_site",
    "browser_interact",
    "browser_session_save", "browser_session_load", "browser_session_close",
    "extract_structured", "extract_llm",
    "CAPABILITIES", "SEARXNG_INSTANCES", "PROXY", "TIMEOUT",
    "DOUYIN_AVAILABLE",
    "douyin_login", "douyin_user_posts", "douyin_user_info",
    "douyin_video_info", "douyin_video_download", "douyin_video_comments",
    "douyin_search", "douyin_search_user", "douyin_search_hashtag",
    "douyin_monitor_user", "douyin_monitor_hashtag",
    "douyin_save_session", "douyin_load_session", "douyin_check_session",
    "DouyinUserInfo", "DouyinAwemeInfo", "DouyinCommentInfo",
]
