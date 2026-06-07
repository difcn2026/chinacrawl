"""ChinaCrawl - Chinese Web Search & Scraping Engine.

11-in-1 open-source alternative to Firecrawl for the Chinese internet.
Zero external API dependencies. AGPLv3 licensed.

Quick start:
    from chinacrawl import scrape, search_web

    result = scrape("https://example.com")
    results = search_web("Python 爬虫", max_results=10)
    
    # Douyin adapter
    from chinacrawl import douyin_login, douyin_user_posts

    douyin_login()  # QR code login
    for post in douyin_user_posts("user_sec_uid"):
        print(post.desc, post.digg_count)

    # Pinduoduo adapter
    from chinacrawl import pinduoduo_product_search, pinduoduo_product_detail

    for product in pinduoduo_product_search("蓝牙耳机"):
        print(product.title, product.price)
"""

from .scraper import (
    # Data classes
    ScrapeResult,
    PageLink,
    SearchResult,
    MonitorResult,
    MonitorAIResult,
    CrawlResult,
    ExtractResult,
    # Core capabilities
    scrape,
    scrape_jina,
    scrape_trafilatura,
    scrape_many,
    map_site,
    search_web,
    search_and_scrape,
    monitor_page,
    monitor_page_ai,
    crawl_site,
    download_site,
    browser_interact,
    browser_session_save,
    browser_session_load,
    browser_session_close,
    extract_structured,
    extract_llm,
    # Config
    CAPABILITIES,
    SEARXNG_INSTANCES,
    PROXY,
    TIMEOUT,
)

# ═══════════════════════════════════════════════════════════════
# ━━━ Douyin (TikTok China) Adapter ━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Requires: playwright, login cookies
DOUYIN_AVAILABLE = False
try:
    from .douyin import (  # noqa: E402
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

# ═══════════════════════════════════════════════════════════════
# ━━━ Pinduoduo (拼多多) E-Commerce Adapter ━━━━━━━━━━━━━━━━━━━
# Requires: playwright, login cookies
PINDUODUO_AVAILABLE = False
try:
    from .pinduoduo import (  # noqa: E402
        ProductInfo as PinduoduoProductInfo,
        ShopInfo as PinduoduoShopInfo,
        ReviewInfo as PinduoduoReviewInfo,
        SearchResult as PinduoduoSearchResult,
        product_search as pinduoduo_product_search,
        product_detail as pinduoduo_product_detail,
        product_reviews as pinduoduo_product_reviews,
        shop_info as pinduoduo_shop_info,
        mall_products as pinduoduo_mall_products,
        category_list as pinduoduo_category_list,
        flash_sale as pinduoduo_flash_sale,
        product_download as pinduoduo_product_download,
        monitor_product as pinduoduo_monitor_product,
        monitor_shop as pinduoduo_monitor_shop,
        login as pinduoduo_login,
        save_session as pinduoduo_save_session,
        load_session as pinduoduo_load_session,
        check_session as pinduoduo_check_session,
    )
    PINDUODUO_AVAILABLE = True
except ImportError:
    pass

__version__ = "0.2.1"
__all__ = [
    # Core
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
    # Douyin
    "DOUYIN_AVAILABLE",
    "douyin_login", "douyin_user_posts", "douyin_user_info",
    "douyin_video_info", "douyin_video_download", "douyin_video_comments",
    "douyin_search", "douyin_search_user", "douyin_search_hashtag",
    "douyin_monitor_user", "douyin_monitor_hashtag",
    "douyin_save_session", "douyin_load_session", "douyin_check_session",
    "DouyinUserInfo", "DouyinAwemeInfo", "DouyinCommentInfo",
    # Pinduoduo
    "PINDUODUO_AVAILABLE",
    "pinduoduo_login", "pinduoduo_product_search", "pinduoduo_product_detail",
    "pinduoduo_product_reviews", "pinduoduo_shop_info", "pinduoduo_mall_products",
    "pinduoduo_category_list", "pinduoduo_flash_sale", "pinduoduo_product_download",
    "pinduoduo_monitor_product", "pinduoduo_monitor_shop",
    "pinduoduo_save_session", "pinduoduo_load_session", "pinduoduo_check_session",
    "PinduoduoProductInfo", "PinduoduoShopInfo", "PinduoduoReviewInfo",
]
