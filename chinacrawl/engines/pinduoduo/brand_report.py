# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Brand Competitive Intelligence Engine — Multi-Dimensional Analysis
# Updated: 2026-06-13 v0.4
#
# 品牌竞争情报引擎：六维分析
#   1. 排名可见度 — 多关键词深翻页，精确定位品牌位置
#   2. 价格定位 — vs 品类均价/Top10/区间分布
#   3. 竞品矩阵 — 品牌名提取 + 价格-销量散点
#   4. 关键词策略 — 竞品标题词频 vs 自身覆盖
#   5. 店铺存在感 — 店铺页采集
#   6. 策略建议 — 基于数据的可执行动作

from __future__ import annotations

import logging
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

from .scraper import product_search, ProductInfo
from . import browser

log = logging.getLogger("chinacrawl.pinduoduo.brand_report")

CST = timezone(timedelta(hours=8))


# ━━━ Data Models ━━━

@dataclass
class DimensionResult:
    """单个分析维度的结果"""
    name: str = ""
    score: str = ""        # "critical" | "warning" | "ok" | "good"
    summary: str = ""
    details: list = field(default_factory=list)
    data: dict = field(default_factory=dict)


@dataclass
class BrandReport:
    """品牌竞争情报报告"""
    brand: str
    industry: str
    generated_at: str = ""

    # 各维度结果
    ranking: DimensionResult = field(default_factory=DimensionResult)
    pricing: DimensionResult = field(default_factory=DimensionResult)
    competitors: DimensionResult = field(default_factory=DimensionResult)
    keywords: DimensionResult = field(default_factory=DimensionResult)
    store: DimensionResult = field(default_factory=DimensionResult)

    # 原始数据
    all_results: list = field(default_factory=list, repr=False)
    brand_products: list = field(default_factory=list, repr=False)

    def to_markdown(self) -> str:
        """生成 Markdown 报告"""
        L = []
        L.append(f"# {self.brand}牌 · {self.industry}市场竞争情报报告")
        L.append(f"> 六维分析 | {self.generated_at} | ChinaCrawl BrandAnalyzer v0.4")
        L.append("")

        # 执行摘要
        criticals = [d for d in [self.ranking, self.pricing, self.competitors,
                                  self.keywords, self.store] if d.score == "critical"]
        warnings = [d for d in [self.ranking, self.pricing, self.competitors,
                                 self.keywords, self.store] if d.score == "warning"]

        L.append("## 执行摘要")
        L.append("")
        if criticals:
            L.append(f"### 🔴 紧急问题 ({len(criticals)}项)")
            for d in criticals:
                L.append(f"- **{d.name}**: {d.summary}")
        if warnings:
            L.append(f"### 🟡 需关注 ({len(warnings)}项)")
            for d in warnings:
                L.append(f"- **{d.name}**: {d.summary}")
        if not criticals and not warnings:
            L.append("### 🟢 所有维度正常")
        L.append("")

        # 各维度详情
        for dim in [self.ranking, self.pricing, self.competitors, self.keywords, self.store]:
            if not dim.name:
                continue
            L.append(f"## {dim.name}")
            L.append("")
            L.append(f"**状态**: {dim.score} | {dim.summary}")
            L.append("")
            for detail in dim.details:
                L.append(f"- {detail}")
            L.append("")

        # 数据来源
        L.append("---")
        L.append(f"*报告由 ChinaCrawl 品牌情报系统自动生成 · {self.generated_at}*")
        L.append(f"*采集深度: {len(self.all_results)} 条商品 | {len(self.brand_products)} 条目标品牌商品*")

        return "\n".join(L)


# ━━━ Analysis Engine ━━━

class BrandAnalyzer:
    """品牌竞争情报分析引擎 v0.4

    使用方式:
        analyzer = BrandAnalyzer(cookie_file="pdd.json")
        report = analyzer.analyze(brand="贺江锋", industry="微耕机",
                                   keywords=["微耕机", "旋耕机", "开沟机"],
                                   max_pages=5)
        print(report.to_markdown())
    """

    def __init__(self, cookie_file: Optional[str] = None):
        self.cookie_file = cookie_file

    def analyze(self, brand: str, industry: str,
                keywords: list = None,
                max_pages: int = 5,
                headless: bool = True) -> BrandReport:
        """执行六维品牌分析"""

        if keywords is None:
            keywords = [industry]

        log.info("=" * 50)
        log.info("BrandAnalyzer: %s / %s (max_pages=%d)", brand, industry, max_pages)
        log.info("=" * 50)

        report = BrandReport(
            brand=brand,
            industry=industry,
            generated_at=datetime.now(CST).strftime("%Y-%m-%d %H:%M"),
        )

        # ━━━ Phase 1: Deep Search — 多关键词深翻页 ━━━
        all_results = []
        brand_products = []
        keyword_stats = {}

        for kw in keywords:
            log.info("Deep search: '%s' (max %d pages)...", kw, max_pages)
            try:
                data = browser.search_deep(
                    kw, cookie_file=self.cookie_file,
                    max_pages=max_pages, headless=headless
                )
                products = data.get("products", [])
                pages = data.get("pages", 0)
                log.info("  '%s': %d products across %d pages", kw, pages, len(products))

                # Tag products with keyword and position
                for i, p in enumerate(products):
                    gid = str(p.get("goods_id", p.get("goodsId", "")))
                    p["_keyword"] = kw
                    p["_position"] = i + 1

                all_results.extend(products)

                # Find brand products
                hits = []
                for i, p in enumerate(products):
                    title = (p.get("title", p.get("goods_name", "")) or "").lower()
                    if brand.lower() in title:
                        hits.append(i + 1)

                keyword_stats[kw] = {
                    "total": len(products),
                    "pages": pages,
                    "brand_hits": hits,
                }

                for i, p in enumerate(products):
                    title = (p.get("title", p.get("goods_name", "")) or "").lower()
                    if brand.lower() in title:
                        brand_products.append(p)

                time.sleep(3)  # Rate limit between keywords
            except Exception as e:
                log.warning("Search '%s' failed: %s", kw, e)
                keyword_stats[kw] = {"total": 0, "pages": 0, "brand_hits": [], "error": str(e)}

        report.all_results = all_results
        report.brand_products = brand_products

        # ━━━ Phase 2: Six-Dimensional Analysis ━━━

        # ── Dimension 1: Ranking Visibility ──
        report.ranking = self._analyze_ranking(brand, keywords, keyword_stats)

        # ── Dimension 2: Price Positioning ──
        report.pricing = self._analyze_pricing(brand, brand_products, all_results)

        # ── Dimension 3: Competitive Landscape ──
        report.competitors = self._analyze_competitors(brand, all_results)

        # ── Dimension 4: Keyword Strategy ──
        report.keywords = self._analyze_keywords(brand, brand_products, all_results)

        # ── Dimension 5: Store Presence ──
        report.store = self._analyze_store(brand, brand_products)

        log.info("Analysis complete: brand=%s, products=%d, results=%d",
                 brand, len(brand_products), len(all_results))

        return report

    # ━━━ Dimension Analyzers ━━━

    def _analyze_ranking(self, brand: str, keywords: list, stats: dict) -> DimensionResult:
        dim = DimensionResult(name="排名可见度")

        total_hits = sum(len(s.get("brand_hits", [])) for s in stats.values())
        total_products = sum(s.get("total", 0) for s in stats.values())

        if total_hits == 0:
            dim.score = "critical"
            dim.summary = f"{brand}在所有 {len(keywords)} 个关键词搜索结果中完全不可见"
            dim.details.append(f"扫描关键词: {', '.join(keywords)}")
            dim.details.append(f"扫描深度: 每个关键词多达 {max(s.get('pages',0) for s in stats.values())} 页")
            dim.details.append(f"总扫描商品: {total_products} 条")
            dim.details.append(f"**根因**: {brand}可能未在PDD开设店铺，或商品标题未包含搜索关键词")
            dim.details.append(f"**行动**: 立即检查 {brand} 是否已在PDD上架；如已上架，优化商品标题关键词")
        elif total_hits <= 3:
            dim.score = "warning"
            best_kw = max(stats.items(), key=lambda x: len(x[1].get("brand_hits", [])))
            dim.summary = f"{brand}仅出现 {total_hits} 次，曝光严重不足"
            dim.details.append(f"最佳关键词: '{best_kw[0]}' — 排第 {best_kw[1]['brand_hits']} 位")
        else:
            dim.score = "good"
            dim.summary = f"{brand}在 {total_hits} 个位置出现，覆盖良好"

        for kw, s in stats.items():
            hits = s.get("brand_hits", [])
            error = s.get("error", "")
            if error:
                dim.details.append(f"关键词 '{kw}': 搜索失败 ({error})")
            elif hits:
                dim.details.append(f"关键词 '{kw}': 找到 {len(hits)} 个，排名 {hits}")
            else:
                dim.details.append(f"关键词 '{kw}': 未找到 ({s.get('total',0)}条结果中)")

        dim.data = stats
        return dim

    def _analyze_pricing(self, brand: str, brand_products: list, all_results: list) -> DimensionResult:
        dim = DimensionResult(name="价格定位")

        # Extract prices from all results
        all_prices = []
        for p in all_results:
            price = p.get("price", p.get("group_price", 0))
            if isinstance(price, (int, float)) and price > 0:
                all_prices.append(float(price))

        brand_prices = []
        for p in brand_products:
            price = p.get("price", p.get("group_price", 0))
            if isinstance(price, (int, float)) and price > 0:
                brand_prices.append(float(price))

        if not all_prices:
            dim.score = "unknown"
            dim.summary = "无有效价格数据"
            return dim

        avg_price = sum(all_prices) / len(all_prices)
        min_price = min(all_prices)
        max_price = max(all_prices)

        # Price bands
        sorted_prices = sorted(all_prices)
        p25 = sorted_prices[len(sorted_prices) // 4]
        p50 = sorted_prices[len(sorted_prices) // 2]
        p75 = sorted_prices[3 * len(sorted_prices) // 4]

        dim.details.append(f"品类价格区间: ¥{min_price:.0f} - ¥{max_price:.0f}")
        dim.details.append(f"品类均价: ¥{avg_price:.0f}")
        dim.details.append(f"价格分位: P25=¥{p25:.0f} | P50=¥{p50:.0f} | P75=¥{p75:.0f}")

        if brand_prices:
            brand_avg = sum(brand_prices) / len(brand_prices)
            dim.details.append(f"{brand}价格: ¥{min(brand_prices):.0f} - ¥{max(brand_prices):.0f} (均价¥{brand_avg:.0f})")

            if brand_avg < p25:
                dim.score = "ok"
                dim.summary = f"{brand}定价偏低 (¥{brand_avg:.0f} vs 品类¥{avg_price:.0f})，有提价空间"
            elif brand_avg > p75:
                dim.score = "warning"
                dim.summary = f"{brand}定价偏高 (¥{brand_avg:.0f} vs 品类¥{avg_price:.0f})，可能影响转化"
            else:
                dim.score = "ok"
                dim.summary = f"{brand}定价在品类中位区间 (¥{brand_avg:.0f} vs 品类¥{avg_price:.0f})"
        else:
            dim.score = "critical"
            dim.summary = f"无 {brand} 价格数据，无法分析定位"
            dim.details.append(f"建议: 参考品类均价 ¥{avg_price:.0f} 进行定价")

        dim.data = {"avg": avg_price, "min": min_price, "max": max_price,
                     "p25": p25, "p50": p50, "p75": p75,
                     "brand_avg": sum(brand_prices)/len(brand_prices) if brand_prices else 0}
        return dim

    def _analyze_competitors(self, brand: str, all_results: list) -> DimensionResult:
        dim = DimensionResult(name="竞品矩阵")

        # Extract brand names from titles (simple heuristic: first 2-4 chars before 微耕/旋耕/etc)
        brand_counter = Counter()
        brand_products_map = {}

        for p in all_results:
            title = (p.get("title", p.get("goods_name", "")) or "").strip()
            # Try to extract brand: take chars before first category word
            for sep in ["微耕", "旋耕", "开沟", "除草", "松土", "耕地", "农用", "新款", "小型", "家用"]:
                if sep in title:
                    prefix = title.split(sep)[0].strip()
                    if 2 <= len(prefix) <= 8:
                        brand_counter[prefix] += 1
                        if prefix not in brand_products_map:
                            brand_products_map[prefix] = []
                        brand_products_map[prefix].append(p)
                    break

        top_brands = brand_counter.most_common(10)
        dim.details.append(f"识别到 {len(brand_counter)} 个品牌前缀")
        dim.details.append(f"Top 10 品牌出现次数:")

        # Remove brand itself from competitor list
        competitors = [(b, c) for b, c in top_brands if brand.lower() not in b.lower()]

        for i, (comp_brand, count) in enumerate(competitors[:8]):
            products = brand_products_map.get(comp_brand, [])
            prices = [float(p.get("price", 0)) for p in products if p.get("price", 0) > 0]
            avg_p = sum(prices) / len(prices) if prices else 0
            dim.details.append(f"  {i+1}. **{comp_brand}** — {count}个商品, 均价¥{avg_p:.0f}")

        if brand.lower() in str(top_brands).lower():
            dim.score = "ok"
            dim.summary = f"{brand}在品牌识别中可见"
        else:
            dim.score = "warning"
            dim.summary = f"{brand}未被识别为独立品牌前缀"

        dim.data = {"top_brands": top_brands}
        return dim

    def _analyze_keywords(self, brand: str, brand_products: list, all_results: list) -> DimensionResult:
        dim = DimensionResult(name="关键词策略")

        # Extract keywords from competitor titles
        word_counter = Counter()
        stop_words = {"新款", "小型", "家用", "多功能", "四冲程", "汽油", "柴油", "微耕机",
                       "旋耕机", "开沟机", "松土机", "除草机", "耕地机", "翻地", "开荒",
                       "2025", "2026", "正品", "包邮", "顺丰"}

        for p in all_results:
            title = (p.get("title", p.get("goods_name", "")) or "")
            # Extract meaningful word segments (2-4 chars)
            words = re.findall(r'[\u4e00-\u9fff]{2,4}', title)
            for w in words:
                if w not in stop_words:
                    word_counter[w] += 1

        top_words = word_counter.most_common(15)
        dim.details.append("竞品标题高频词 (Top 15):")
        for word, count in top_words:
            in_brand = "✅" if any(word in (p.get("title", "") or "") for p in brand_products) else "❌"
            dim.details.append(f"  {in_brand} **{word}** ({count}次)")

        # Calculate coverage
        if brand_products:
            brand_titles = " ".join((p.get("title", "") or "") for p in brand_products)
            covered = sum(1 for w, _ in top_words if w in brand_titles)
            total = len(top_words)
            dim.score = "ok" if covered / total > 0.5 else "warning"
            dim.summary = f"高频词覆盖: {covered}/{total}"
            if covered / total <= 0.5:
                missing = [w for w, _ in top_words if w not in brand_titles][:5]
                dim.details.append(f"缺失关键词: {', '.join(missing)}")
        else:
            dim.score = "critical"
            dim.summary = "无品牌商品，无法分析关键词覆盖"

        dim.data = {"top_words": top_words}
        return dim

    def _analyze_store(self, brand: str, brand_products: list) -> DimensionResult:
        dim = DimensionResult(name="店铺存在感")

        mall_ids = set()
        for p in brand_products:
            mid = str(p.get("mall_id", p.get("mallId", "")))
            if mid:
                mall_ids.add(mid)

        if mall_ids:
            dim.score = "ok"
            dim.summary = f"检测到 {len(mall_ids)} 个关联店铺"
            for mid in list(mall_ids)[:3]:
                dim.details.append(f"店铺ID: {mid}")
        else:
            dim.score = "critical"
            dim.summary = f"未检测到 {brand} 关联店铺"

        dim.data = {"mall_ids": list(mall_ids)}
        return dim


def analyze_brand(brand: str, industry: str,
                  keywords: list = None,
                  cookie_file: str = None,
                  max_pages: int = 5,
                  headless: bool = True) -> BrandReport:
    """快捷接口：六维品牌分析"""
    analyzer = BrandAnalyzer(cookie_file=cookie_file)
    return analyzer.analyze(
        brand=brand, industry=industry,
        keywords=keywords, max_pages=max_pages,
        headless=headless,
    )


def generate_report(brand: str, industry: str,
                    keywords: list = None,
                    cookie_file: str = None,
                    output_dir: str = None,
                    max_pages: int = 5,
                    headless: bool = True) -> str:
    """快捷接口：分析 + 保存 Markdown 报告"""
    report = analyze_brand(
        brand=brand, industry=industry,
        keywords=keywords, cookie_file=cookie_file,
        max_pages=max_pages, headless=headless,
    )
    md = report.to_markdown()

    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "reports")
    os.makedirs(output_dir, exist_ok=True)

    safe_brand = brand.replace("/", "_").replace("\\", "_")
    filename = f"{safe_brand}_{industry}_六维分析_{datetime.now(CST).strftime('%Y%m%d_%H%M')}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)

    log.info("Report saved: %s", filepath)
    return filepath
