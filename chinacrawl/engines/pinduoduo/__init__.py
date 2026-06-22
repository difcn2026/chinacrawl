# XHLS v3.0 | Xiao Hei Learning System
# Pinduoduo (拼多多) Platform Adapter for ChinaCrawl
# Created: 2026-06-08 | v0.2.0 — Feed channel added 2026-06-13

"""
ChinaCrawl Pinduoduo Adapter - 拼多多电商平台数据采集模块

双通道架构:
  1. Hub/v3 Feed (主力) — 无需登录，批量采集推荐流，关键词过滤
  2. Web API (备用) — 需要 anti_content 签名，受限
  3. Playwright Browser (降级) — DOM 解析兜底

Quick start:
    from chinacrawl.pinduoduo import product_search, product_feed

    # 批量采集推荐流
    for product in product_feed(max_sn=20):
        print(product.title, product.price)

    # Feed 关键词过滤搜索
    for product in product_search("蓝牙耳机", max_results=20):
        print(product.title, product.price)
"""

from .brand_report import BrandAnalyzer, BrandReport, DimensionResult, analyze_brand, generate_report
from .scraper import (
    product_search,
    product_feed,
    product_detail,
    product_detail_ssr,
    product_detail_full,
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
from .brand_report import BrandAnalyzer, BrandReport, DimensionResult, analyze_brand, generate_report
from .scraper import (
    ProductInfo,
    ShopInfo,
    ReviewInfo,
    SkuInfo,
    SearchResult,
    SearchResult as pinduoduo_search_result_t,
)

__all__ = [
    # Data models
    "ProductInfo", "ShopInfo", "ReviewInfo", "SearchResult", "pinduoduo_search_result_t",
    "BrandAnalyzer", "BrandReport", "DimensionResult", "analyze_brand", "generate_report",
    "SkuInfo",
    # Feed operations (no login required!)
    "product_feed",
    # Product operations
    "product_search", "product_detail", "product_detail_ssr", "product_detail_full", "product_reviews",
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
