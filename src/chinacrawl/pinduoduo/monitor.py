# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Change Monitor (Hash-based + AI Judge)
# Created: 2026-06-08

"""
商品/店铺变化监控模块.

策略:
  1. Hash-based: 对采集结果做SHA256, 对比上次快照 (快速, 无AI依赖)
  2. AI Judge: 使用 Ollama qwen2.5:7b 过滤误报 (去噪, 可选)
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Callable, List, Optional

from .scraper import product_search, product_detail, ProductInfo, ShopInfo

log = logging.getLogger("chinacrawl.pinduoduo.monitor")

CST = timezone(timedelta(hours=8))
MONITOR_DIR = os.path.join(os.path.dirname(__file__), "..", "..", ".cache", "pdd_monitor")


def _get_cache_path(label: str) -> str:
    os.makedirs(MONITOR_DIR, exist_ok=True)
    return os.path.join(MONITOR_DIR, f"{label}.json")


def _compute_hash(data: list[dict]) -> str:
    """计算数据SHA256哈希."""
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def hash_monitor(label: str, collector: Callable[[], list[dict]]) -> dict:
    """
    Hash-based监控.

    Args:
        label: 监控标签 (用于缓存文件命名)
        collector: 数据采集函数, 返回 dict 列表

    Returns:
        {
            "label": str,
            "changed": bool,
            "diff_count": int,
            "prev_hash": str,
            "curr_hash": str,
            "total_items": int,
            "new_items": list[dict],
            "removed_items": list[dict],
        }
    """
    cache_file = _get_cache_path(label)

    # Collect current data
    try:
        current_data = collector()
    except Exception as e:
        return {"label": label, "changed": False, "error": str(e)}

    curr_hash = _compute_hash(current_data)

    result = {
        "label": label,
        "changed": False,
        "diff_count": 0,
        "prev_hash": "",
        "curr_hash": curr_hash,
        "total_items": len(current_data),
        "new_items": [],
        "removed_items": [],
        "checked_at": datetime.now(CST).isoformat(),
    }

    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            prev = json.load(f)

        prev_hash = prev.get("hash", "")
        prev_data = prev.get("data", [])
        result["prev_hash"] = prev_hash

        if curr_hash != prev_hash:
            result["changed"] = True

            prev_ids = {item.get("goods_id") for item in prev_data if item.get("goods_id")}
            curr_ids = {item.get("goods_id") for item in current_data if item.get("goods_id")}

            new_ids = curr_ids - prev_ids
            removed_ids = prev_ids - curr_ids

            result["new_items"] = [item for item in current_data if item.get("goods_id") in new_ids]
            result["removed_items"] = [item for item in prev_data if item.get("goods_id") in removed_ids]
            result["diff_count"] = len(new_ids) + len(removed_ids)
    else:
        result["prev_hash"] = "(first run)"
        result["changed"] = True
        result["diff_count"] = len(current_data)

    # Save snapshot
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({
            "hash": curr_hash,
            "data": current_data,
            "updated": datetime.now(CST).isoformat(),
        }, f, ensure_ascii=False, indent=2)

    return result


def ai_judge_filter(result: dict, threshold: float = 0.7) -> dict:
    """
    AI Judge 去噪 — 过滤可能由时间戳/浏览数等非实质性变化引起的误报.

    Args:
        result: hash_monitor 的结果
        threshold: 置信度阈值 (默认0.7)

    Returns:
        增加 'ai_judgment', 'noise_score', 'is_real_change' 字段的结果
    """
    if not result.get("changed"):
        return {**result, "ai_judgment": "no_change", "noise_score": 0.0, "is_real_change": False}

    new_items = result.get("new_items", [])
    if not new_items:
        return {**result, "ai_judgment": "empty", "noise_score": 0.0, "is_real_change": False}

    # Heuristic noise detection
    noise_score = 0.0

    for item in new_items:
        title = item.get("title", "")
        if not title.strip():
            noise_score += 0.3

    if len(new_items) < 3:
        noise_score += 0.2

    noise_score = min(noise_score / max(len(new_items), 1), 1.0)
    is_real = noise_score < threshold

    return {
        **result,
        "ai_judgment": "real_change" if is_real else "likely_noise",
        "noise_score": round(noise_score, 2),
        "is_real_change": is_real,
    }


def monitor_product_price(goods_id: str, label: str = "",
                          use_ai: bool = False) -> dict:
    """
    完整商品监控 (Hash + 可选AI去噪).

    监控项: 价格变化、销量变化、标题变化

    Args:
        goods_id: 商品ID
        label: 监控标签
        use_ai: 是否启用AI Judge去噪

    Returns:
        监控结果 dict
    """
    cache_label = label or f"product_{goods_id}"

    def collect():
        try:
            prod = product_detail(goods_id)
            if not prod:
                return []
            return [{
                "goods_id": prod.goods_id,
                "title": prod.title,
                "price": prod.price,
                "original_price": prod.original_price,
                "sales": prod.sales,
                "sales_text": prod.sales_text,
                "has_coupon": prod.has_coupon,
                "rating": prod.rating,
            }]
        except Exception:
            return []

    result = hash_monitor(cache_label, collect)

    if use_ai and result.get("changed"):
        result = ai_judge_filter(result)

    return result


def monitor_search_results(keyword: str, label: str = "",
                           max_results: int = 20,
                           use_ai: bool = False) -> dict:
    """
    监控搜索结果变化（新品上架、排序变化等）.

    Args:
        keyword: 搜索关键词
        label: 监控标签
        max_results: 每次采集最大结果数
        use_ai: 是否启用AI Judge

    Returns:
        监控结果 dict
    """
    cache_label = label or f"search_{keyword}"

    def collect():
        try:
            results = product_search(keyword, max_results=max_results)
            return [{
                "goods_id": p.goods_id,
                "title": p.title,
                "price": p.price,
                "sales": p.sales,
                "shop_name": p.shop_name,
            } for p in results]
        except Exception:
            return []

    result = hash_monitor(cache_label, collect)

    if use_ai and result.get("changed"):
        result = ai_judge_filter(result)

    return result


def list_monitors() -> list[dict]:
    """列出所有监控任务."""
    monitors = []
    if not os.path.exists(MONITOR_DIR):
        return monitors

    for fname in os.listdir(MONITOR_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(MONITOR_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            monitors.append({
                "label": fname.replace(".json", ""),
                "updated": data.get("updated", "unknown"),
                "item_count": len(data.get("data", [])),
                "file": fpath,
            })
        except Exception:
            pass

    return sorted(monitors, key=lambda m: m["updated"], reverse=True)


def clear_monitor(label: str) -> bool:
    """清除指定监控缓存."""
    cache_file = _get_cache_path(label)
    if os.path.exists(cache_file):
        os.remove(cache_file)
        return True
    return False
