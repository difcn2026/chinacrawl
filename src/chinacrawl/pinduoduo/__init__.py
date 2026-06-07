# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo (拼多多) Platform Adapter for ChinaCrawl
# Created: 2026-06-08 | v0.1.0-dev

"""
ChinaCrawl Pinduoduo Adapter - 拼多多电商平台数据采集模块.

双通道架构: Web API (优先) → Playwright Browser (降级)

Quick start:
    from chinacrawl.pinduoduo import product_search, product_detail, shop_info

    for product in product_search("蓝牙耳机", max_results=20):
        print(product.title, product.price)
"""

from .scraper import (
    product_search,
    product_detail,
    shop_info,
    product_reviews,
    category_list,
    mall_products,
    flash_sale,
    product_download,
    monitor_product,
    monitor_shop,
    login,
    save_session,
    load_session,
    check_session,
)
from .scraper import (
    ProductInfo,
    ShopInfo,
    ReviewInfo,
    SearchResult,
    SearchResult as pinduoduo_search_result_t,
)

__all__ = [
    # Data models
    "ProductInfo", "ShopInfo", "ReviewInfo", "SearchResult", "pinduoduo_search_result_t",
    # Product operations
    "product_search", "product_detail", "product_reviews",
    # Shop operations
    "shop_info", "mall_products",
    # Category & promotion
    "category_list", "flash_sale",
    # Download
    "product_download",
    # Monitor operations
    "monitor_product", "monitor_shop",
    # Session management
    "login", "save_session", "load_session", "check_session",
]
