# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Data Export (CSV/JSON/Markdown/SQLite)
# Created: 2026-06-07

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

from .scraper import UserInfo, AwemeInfo, CommentInfo, SearchResult

log = logging.getLogger("chinacrawl.douyin.export")

CST = timezone(timedelta(hours=8))


# ═══════════════════════════════════════════════════════════════
# CSV Export
# ═══════════════════════════════════════════════════════════════

def to_csv(items: list, filepath: str, item_type: str = "aweme") -> str:
    """
    导出为CSV文件.

    Args:
        items: UserInfo/AwemeInfo/CommentInfo 对象列表
        filepath: CSV文件路径
        item_type: "aweme", "user", "comment"

    Returns:
        文件路径
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    if item_type == "aweme":
        fieldnames = [
            "aweme_id", "desc", "create_time", "duration_sec",
            "digg_count", "comment_count", "share_count", "play_count",
            "music_title", "hashtags", "video_url", "is_top"
        ]
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "aweme_id": item.aweme_id,
                    "desc": item.desc.replace("\n", " "),
                    "create_time": item.create_time.strftime("%Y-%m-%d %H:%M") if item.create_time else "",
                    "duration_sec": round(item.duration / 1000, 1) if item.duration else 0,
                    "digg_count": item.digg_count,
                    "comment_count": item.comment_count,
                    "share_count": item.share_count,
                    "play_count": item.play_count,
                    "music_title": item.music_title,
                    "hashtags": "|".join(item.hashtags) if item.hashtags else "",
                    "video_url": item.video_url,
                    "is_top": item.is_top,
                })

    elif item_type == "user":
        fieldnames = [
            "sec_uid", "nickname", "unique_id", "signature",
            "follower_count", "following_count", "aweme_count",
            "total_favorited", "verified", "enterprise", "region"
        ]
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "sec_uid": item.sec_uid,
                    "nickname": item.nickname,
                    "unique_id": item.unique_id,
                    "signature": item.signature.replace("\n", " "),
                    "follower_count": item.follower_count,
                    "following_count": item.following_count,
                    "aweme_count": item.aweme_count,
                    "total_favorited": item.total_favorited,
                    "verified": item.verified,
                    "enterprise": item.enterprise,
                    "region": item.region,
                })

    elif item_type == "comment":
        fieldnames = [
            "cid", "text", "create_time", "digg_count",
            "reply_count", "user_nickname"
        ]
        with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "cid": item.cid,
                    "text": item.text.replace("\n", " "),
                    "create_time": item.create_time.strftime("%Y-%m-%d %H:%M") if item.create_time else "",
                    "digg_count": item.digg_count,
                    "reply_count": item.reply_count,
                    "user_nickname": item.user_nickname,
                })

    log.info("CSV exported: %s (%d rows)", filepath, len(items))
    return filepath


# ═══════════════════════════════════════════════════════════════
# JSON Export
# ═══════════════════════════════════════════════════════════════

def to_json(items: list, filepath: str, pretty: bool = True) -> str:
    """
    导出为JSON文件.

    Args:
        items: 数据对象列表
        filepath: JSON文件路径
        pretty: 是否格式化 (indent=2)

    Returns:
        文件路径
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    # Convert dataclasses to dicts
    data = []
    for item in items:
        if hasattr(item, "__dataclass_fields__"):
            d = {}
            for field_name in item.__dataclass_fields__:
                val = getattr(item, field_name)
                if isinstance(val, datetime):
                    val = val.isoformat()
                elif field_name == "raw":
                    continue
                d[field_name] = val
            data.append(d)
        elif isinstance(item, dict):
            data.append(item)
        else:
            data.append(str(item))

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(CST).isoformat(),
            "total": len(data),
            "items": data,
        }, f, ensure_ascii=False, indent=2 if pretty else None)

    log.info("JSON exported: %s (%d items)", filepath, len(data))
    return filepath


# ═══════════════════════════════════════════════════════════════
# Markdown Export
# ═══════════════════════════════════════════════════════════════

def to_markdown(items: list, filepath: str, title: str = "Douyin Export",
                item_type: str = "aweme") -> str:
    """
    导出为Markdown可读报告.

    Args:
        items: 数据对象列表
        filepath: MD文件路径
        title: 报告标题
        item_type: "aweme", "user", "comment"

    Returns:
        文件路径
    """
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

    lines = [
        f"# {title}",
        f"> 导出时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 总数: {len(items)}",
        "",
    ]

    if item_type == "aweme":
        lines.append("| # | 描述 | 点赞 | 评论 | 分享 | 时长 | 发布时间 |")
        lines.append("|:--:|------|:----:|:----:|:----:|:----:|----------|")
        for i, item in enumerate(items, 1):
            desc = item.desc[:50].replace("\n", " ").replace("|", "\\|")
            ct = item.create_time.strftime("%m-%d %H:%M") if item.create_time else ""
            dur = f"{item.duration // 1000}s" if item.duration else ""
            lines.append(
                f"| {i} | {desc} | {item.digg_count} | {item.comment_count} "
                f"| {item.share_count} | {dur} | {ct} |"
            )

    elif item_type == "user":
        lines.append("| # | 昵称 | 粉丝 | 关注 | 作品 | 获赞 | 认证 |")
        lines.append("|:--:|------|:----:|:----:|:----:|:----:|:----:|")
        for i, item in enumerate(items, 1):
            lines.append(
                f"| {i} | {item.nickname} | {item.follower_count} "
                f"| {item.following_count} | {item.aweme_count} "
                f"| {item.total_favorited} | {'✓' if item.verified else ''} |"
            )

    elif item_type == "comment":
        lines.append("| # | 用户 | 内容 | 点赞 | 时间 |")
        lines.append("|:--:|------|------|:----:|------|")
        for i, item in enumerate(items, 1):
            text = item.text[:60].replace("\n", " ").replace("|", "\\|")
            ct = item.create_time.strftime("%m-%d %H:%M") if item.create_time else ""
            lines.append(
                f"| {i} | {item.user_nickname} | {text} | {item.digg_count} | {ct} |"
            )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    log.info("Markdown exported: %s", filepath)
    return filepath


# ═══════════════════════════════════════════════════════════════
# SQLite Export
# ═══════════════════════════════════════════════════════════════

def to_sqlite(items: list, db_path: str, table_name: str = "awemes",
              item_type: str = "aweme", replace: bool = False) -> str:
    """
    导出到SQLite数据库.

    Args:
        items: 数据对象列表
        db_path: SQLite文件路径
        table_name: 表名
        item_type: "aweme", "user", "comment"
        replace: 是否替换已存在的表

    Returns:
        数据库文件路径
    """
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    if item_type == "aweme":
        if replace:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                aweme_id TEXT PRIMARY KEY,
                desc TEXT,
                create_time TEXT,
                duration_ms INTEGER,
                digg_count INTEGER,
                comment_count INTEGER,
                share_count INTEGER,
                play_count INTEGER,
                music_title TEXT,
                hashtags TEXT,
                video_url TEXT,
                is_top INTEGER,
                exported_at TEXT
            )
        """)
        now = datetime.now(CST).isoformat()
        for item in items:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item.aweme_id,
                    item.desc,
                    item.create_time.isoformat() if item.create_time else "",
                    item.duration,
                    item.digg_count,
                    item.comment_count,
                    item.share_count,
                    item.play_count,
                    item.music_title,
                    "|".join(item.hashtags) if item.hashtags else "",
                    item.video_url,
                    1 if item.is_top else 0,
                    now,
                )
            )

    elif item_type == "user":
        if replace:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                sec_uid TEXT PRIMARY KEY,
                nickname TEXT,
                unique_id TEXT,
                signature TEXT,
                follower_count INTEGER,
                following_count INTEGER,
                aweme_count INTEGER,
                total_favorited INTEGER,
                verified INTEGER,
                enterprise INTEGER,
                region TEXT,
                exported_at TEXT
            )
        """)
        now = datetime.now(CST).isoformat()
        for item in items:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item.sec_uid,
                    item.nickname,
                    item.unique_id,
                    item.signature,
                    item.follower_count,
                    item.following_count,
                    item.aweme_count,
                    item.total_favorited,
                    1 if item.verified else 0,
                    1 if item.enterprise else 0,
                    item.region,
                    now,
                )
            )

    elif item_type == "comment":
        if replace:
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                cid TEXT PRIMARY KEY,
                text TEXT,
                create_time TEXT,
                digg_count INTEGER,
                reply_count INTEGER,
                user_nickname TEXT,
                exported_at TEXT
            )
        """)
        now = datetime.now(CST).isoformat()
        for item in items:
            conn.execute(
                f"INSERT OR REPLACE INTO {table_name} VALUES (?,?,?,?,?,?,?)",
                (
                    item.cid,
                    item.text,
                    item.create_time.isoformat() if item.create_time else "",
                    item.digg_count,
                    item.reply_count,
                    item.user_nickname,
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

def export_all(items: list, output_dir: str, basename: str = "douyin_export",
               item_type: str = "aweme") -> dict:
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
        results["sqlite"] = to_sqlite(items, db_path, item_type, item_type, replace=True)
    except Exception as e:
        results["sqlite"] = f"ERROR: {e}"

    log.info("Export all complete: %d items -> %s", len(items), output_dir)
    return results
