# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Data Export (CSV/JSON/Markdown/SQLite)
# Created: 2026-06-08

"""
多格式数据导出层.

支持:
  - CSV: Excel兼容, 适合数据分析
  - JSON: 结构化原始数据
  - Markdown: 可读报告
  - SQLite: 持久化数据库
"""

import csv
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .scraper import ProductInfo, ShopInfo, ReviewInfo, SearchResult

log = logging.getLogger("chinacrawl.pinduoduo.export")

CST = timezone(timedelta(hours=8))


# ═══════════════════════════════════════════════════════════════
# CSV Export
# ═══════════════════════════════════════════════════════════════

def to_csv(items: list, filepath: str, item_type: str = "product") -> str:
    """
    导出为CSV文件.

    Args:
        items: ProductInfo/ShopInfo/ReviewInfo 对象列表
        filepath: CSV文件路径
        item_type: "product", "shop", "review"

    Returns:
        文件路径
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    if item_type == "product":
        fieldnames = [
            "goods_id", "title", "price", "original_price",
            "sales", "sales_text", "shop_name", "mall_id",
            "has_coupon", "free_shipping", "rating", "img_url"
        ]
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "goods_id": item.goods_id,
                    "title": item.title.replace("\n", " "),
                    "price": item.price,
                    "original_price": item.original_price,
                    "sales": item.sales,
                    "sales_text": item.sales_text,
                    "shop_name": item.shop_name,
                    "mall_id": item.mall_id,
                    "has_coupon": item.has_coupon,
                    "free_shipping": item.free_shipping,
                    "rating": item.rating,
                    "img_url": item.img_url,
                })

    elif item_type == "shop":
        fieldnames = [
            "mall_id", "shop_name", "rating", "goods_count", "description"
        ]
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "mall_id": item.mall_id,
                    "shop_name": item.shop_name,
                    "rating": item.rating,
                    "goods_count": item.goods_count,
                    "description": item.description.replace("\n", " "),
                })

    elif item_type == "review":
        fieldnames = [
            "review_id", "text", "create_time", "rating",
            "user_name", "reply_text", "specs"
        ]
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "review_id": item.review_id,
                    "text": item.text.replace("\n", " "),
                    "create_time": item.create_time.strftime("%Y-%m-%d %H:%M") if item.create_time else "",
                    "rating": item.rating,
                    "user_name": item.user_name,
                    "reply_text": item.reply_text.replace("\n", " "),
                    "specs": item.specs,
                })

    log.info("CSV exported: %s (%d rows)", filepath, len(items))
    return filepath


# ═══════════════════════════════════════════════════════════════
# JSON Export
# ═══════════════════════════════════════════════════════════════

def to_json(items: list, filepath: str) -> str:
    """
    导出为JSON文件.

    Args:
        items: 数据对象列表
        filepath: JSON文件路径

    Returns:
        文件路径
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    data = []
    for item in items:
        if isinstance(item, ProductInfo):
            data.append({
                "goods_id": item.goods_id,
                "title": item.title,
                "price": item.price,
                "original_price": item.original_price,
                "sales": item.sales,
                "sales_text": item.sales_text,
                "img_url": item.img_url,
                "images": item.images,
                "shop_name": item.shop_name,
                "mall_id": item.mall_id,
                "desc": item.desc,
                "specs": item.specs,
                "has_coupon": item.has_coupon,
                "free_shipping": item.free_shipping,
                "rating": item.rating,
            })
        elif isinstance(item, ShopInfo):
            data.append({
                "mall_id": item.mall_id,
                "shop_name": item.shop_name,
                "shop_logo": item.shop_logo,
                "rating": item.rating,
                "goods_count": item.goods_count,
                "description": item.description,
            })
        elif isinstance(item, ReviewInfo):
            data.append({
                "review_id": item.review_id,
                "text": item.text,
                "create_time": item.create_time.isoformat() if item.create_time else None,
                "rating": item.rating,
                "user_name": item.user_name,
                "reply_text": item.reply_text,
                "specs": item.specs,
            })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "count": len(data),
            "exported_at": datetime.now(CST).isoformat(),
            "items": data,
        }, f, ensure_ascii=False, indent=2)

    log.info("JSON exported: %s (%d items)", filepath, len(data))
    return filepath


# ═══════════════════════════════════════════════════════════════
# Markdown Export
# ═══════════════════════════════════════════════════════════════

def to_markdown(items: list, filepath: str, title: str = "拼多多数据导出",
                item_type: str = "product") -> str:
    """
    导出为Markdown报告.

    Args:
        items: 数据对象列表
        filepath: MD文件路径
        title: 报告标题
        item_type: 数据类型

    Returns:
        文件路径
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    lines = [
        f"# {title}",
        "",
        f"> 导出时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 数量: {len(items)} 条",
        "",
        "---",
        "",
    ]

    if item_type == "product":
        lines.append("## 商品列表")
        lines.append("")
        lines.append("| # | 商品名称 | 价格 | 原价 | 销量 | 店铺 | 评分 |")
        lines.append("|---|----------|------|------|------|------|------|")
        for i, item in enumerate(items, 1):
            price_str = f"¥{item.price:.2f}" if item.price else "-"
            orig_str = f"~~¥{item.original_price:.2f}~~" if item.original_price > 0 else "-"
            sales_str = item.sales_text or f"{item.sales}" if item.sales else "-"
            rating_str = f"★ {item.rating:.1f}" if item.rating > 0 else "-"
            lines.append(
                f"| {i} | {item.title[:40]} | {price_str} | {orig_str} | {sales_str} | "
                f"{item.shop_name[:15]} | {rating_str} |"
            )

    elif item_type == "review":
        lines.append("## 商品评价")
        lines.append("")
        for i, item in enumerate(items, 1):
            rating_str = "★" * item.rating + "☆" * (5 - item.rating)
            lines.append(f"### {i}. {item.user_name} ({rating_str})")
            lines.append("")
            lines.append(f"> {item.text}")
            if item.reply_text:
                lines.append(f"")
                lines.append(f"**商家回复**: {item.reply_text}")
            if item.specs:
                lines.append(f"")
                lines.append(f"规格: `{item.specs}`")
            lines.append("")

    elif item_type == "shop":
        lines.append("## 店铺列表")
        lines.append("")
        lines.append("| # | 店铺名称 | 评分 | 商品数 | 描述 |")
        lines.append("|---|----------|------|--------|------|")
        for i, item in enumerate(items, 1):
            lines.append(f"| {i} | {item.shop_name} | {item.rating} | {item.goods_count} | {item.description[:30]} |")

    lines.append("")
    lines.append("---")
    lines.append(f"*由 ChinaCrawl Pinduoduo Adapter 生成*")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log.info("Markdown exported: %s", filepath)
    return filepath


# ═══════════════════════════════════════════════════════════════
# SQLite Export
# ═══════════════════════════════════════════════════════════════

def to_sqlite(items: list, db_path: str, table_name: str = "products",
              item_type: str = "product", replace: bool = False) -> str:
    """
    导出为SQLite数据库.

    Args:
        items: 数据对象列表
        db_path: 数据库文件路径
        table_name: 表名
        item_type: 数据类型
        replace: 是否替换已有表

    Returns:
        数据库路径
    """
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    now = datetime.now(CST).isoformat()

    if item_type == "product":
        if replace:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                goods_id TEXT PRIMARY KEY,
                title TEXT,
                price REAL,
                original_price REAL,
                sales INTEGER,
                sales_text TEXT,
                shop_name TEXT,
                mall_id TEXT,
                has_coupon INTEGER,
                free_shipping INTEGER,
                rating REAL,
                img_url TEXT,
                exported_at TEXT
            )
        """)
        for item in items:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item.goods_id,
                    item.title,
                    item.price,
                    item.original_price,
                    item.sales,
                    item.sales_text,
                    item.shop_name,
                    item.mall_id,
                    1 if item.has_coupon else 0,
                    1 if item.free_shipping else 0,
                    item.rating,
                    item.img_url,
                    now,
                )
            )

    elif item_type == "review":
        if replace:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                review_id TEXT PRIMARY KEY,
                text TEXT,
                create_time TEXT,
                rating INTEGER,
                user_name TEXT,
                reply_text TEXT,
                specs TEXT,
                exported_at TEXT
            )
        """)
        for item in items:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} VALUES (?,?,?,?,?,?,?,?)",
                (
                    item.review_id,
                    item.text,
                    item.create_time.isoformat() if item.create_time else "",
                    item.rating,
                    item.user_name,
                    item.reply_text,
                    item.specs,
                    now,
                )
            )

    elif item_type == "shop":
        if replace:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                mall_id TEXT PRIMARY KEY,
                shop_name TEXT,
                rating REAL,
                goods_count INTEGER,
                description TEXT,
                exported_at TEXT
            )
        """)
        for item in items:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} VALUES (?,?,?,?,?,?)",
                (
                    item.mall_id,
                    item.shop_name,
                    item.rating,
                    item.goods_count,
                    item.description,
                    now,
                )
            )

    conn.commit()
    conn.close()
    log.info("SQLite exported: %s -> %s (%d rows)", db_path, table_name, len(items))
    return db_path


# ═══════════════════════════════════════════════════════════════
# Convenience: Export All Formats
# ═══════════════════════════════════════════════════════════════

def export_all(items: list, output_dir: str, basename: str = "pdd_export",
               item_type: str = "product") -> dict:
    """
    一键导出所有格式.

    Args:
        items: 数据对象列表
        output_dir: 输出目录
        basename: 文件名基础
        item_type: 数据类型

    Returns:
        {"csv": path, "json": path, "md": path, "sqlite": path}
    """
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    try:
        results["csv"] = to_csv(items, os.path.join(output_dir, f"{basename}.csv"), item_type)
    except Exception as e:
        results["csv"] = f"ERROR: {e}"

    try:
        results["json"] = to_json(items, os.path.join(output_dir, f"{basename}.json"))
    except Exception as e:
        results["json"] = f"ERROR: {e}"

    try:
        results["md"] = to_markdown(items, os.path.join(output_dir, f"{basename}.md"),
                                    title=basename, item_type=item_type)
    except Exception as e:
        results["md"] = f"ERROR: {e}"

    try:
        db_path = os.path.join(output_dir, f"{basename}.db")
        results["sqlite"] = to_sqlite(items, db_path, table_name=item_type + "s",
                                      item_type=item_type, replace=True)
    except Exception as e:
        results["sqlite"] = f"ERROR: {e}"

    log.info("Export all complete: %d items -> %s", len(items), output_dir)
    return results
