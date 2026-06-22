# chinacrawl/market/scanner.py - Cross-platform market scanner
# Uses pinduoduo + douyin adapters to generate market intelligence.

import json, logging, os, time
from datetime import datetime, timezone, timedelta
from typing import Optional
from .report import MarketReport, TrendSignal

log = logging.getLogger("chinacrawl.market.scanner")
CST = timezone(timedelta(hours=8))

SHORT_DRAMA_KEYWORDS = [
    "短剧", "微短剧", "付费短剧", "竖屏短剧",
    "霸总", "穿越", "逆袭", "复仇", "甜宠", "神医", "战神", "豪门",
    "AI短剧", "动漫短剧",
]


def _score_trend(keyword, platform_results):
    count = len(platform_results)
    score = 40 if count >= 10 else (25 if count >= 5 else (10 if count >= 1 else 0))
    titles = " ".join(str(r) for r in platform_results)
    if keyword in titles:
        score += 10
    return min(score, 100)


def _classify_strength(score):
    if score >= 60: return "hot"
    if score >= 30: return "rising"
    return "declining"


class MarketScanner:
    """Cross-platform market scanner → feeds into 短剧工程1 P0"""
    
    def __init__(self, pdd_cookie=None, douyin_cookie=None):
        self.pdd_cookie = pdd_cookie
        self.douyin_cookie = douyin_cookie
    
    def scan_pinduoduo(self, keywords=None, max_results=30):
        keywords = keywords or SHORT_DRAMA_KEYWORDS
        findings = []
        try:
            from ..pinduoduo import product_search
            for kw in keywords[:5]:
                try:
                    results = product_search(kw, max_results=max_results, cookie_file=self.pdd_cookie)
                    findings.append({
                        "keyword": kw, "result_count": len(results),
                        "top_products": [{"title": p.title, "price": p.price, "sales": p.sales} for p in results[:5]] if results else [],
                    })
                    time.sleep(2)
                except Exception as e:
                    log.warning("PDD '%s': %s", kw, e)
                    findings.append({"keyword": kw, "error": str(e)})
        except ImportError:
            log.warning("pinduoduo adapter not available")
        return findings
    
    def scan_douyin(self, video_ids=None, keywords=None):
        findings = []
        try:
            from ..douyin import batch_fetch_video_meta
            if video_ids:
                meta_list = batch_fetch_video_meta(video_ids[:20], cookie_file=self.douyin_cookie, headless=True, delay=1.5)
                for m in meta_list:
                    parsed = m.get("meta_parsed", {})
                    findings.append({
                        "aweme_id": m.get("aweme_id"),
                        "author": parsed.get("author"),
                        "hashtags": parsed.get("hashtags", []),
                        "likes": parsed.get("digg_count"),
                        "date": parsed.get("publish_date"),
                        "title": m.get("page_title", ""),
                    })
        except ImportError:
            log.warning("douyin adapter not available")
        return findings
    
    def scan_short_drama(self, keywords=None, douyin_video_ids=None, output_dir=None):
        keywords = keywords or SHORT_DRAMA_KEYWORDS
        scan_id = datetime.now(CST).strftime("scan_%Y%m%d_%H%M%S")
        report = MarketReport(scan_id=scan_id, category="短剧")
        
        log.info("Scanning Pinduoduo...")
        report.pdd_findings = self.scan_pinduoduo(keywords)
        report.raw_pdd_data = report.pdd_findings
        
        log.info("Scanning Douyin...")
        report.douyin_findings = self.scan_douyin(video_ids=douyin_video_ids)
        report.raw_douyin_data = report.douyin_findings
        
        log.info("Analyzing trends...")
        for f in report.pdd_findings:
            if "error" in f: continue
            kw = f.get("keyword", "")
            score = _score_trend(kw, f.get("top_products", []))
            if score > 0:
                report.trend_signals.append(TrendSignal(keyword=kw, platform="pinduoduo", signal_type="product", strength=_classify_strength(score), evidence=f.get("top_products",[])[:3], score=score))
        
        for f in report.douyin_findings:
            hashtags = f.get("hashtags", [])
            likes = f.get("likes") or 0
            for tag in hashtags:
                score = min(50 + (likes // 10000), 100) if likes else 30
                report.trend_signals.append(TrendSignal(keyword=tag, platform="douyin", signal_type="hashtag", strength=_classify_strength(score), evidence=[f.get("title","")[:80]], score=int(score)))
            author = f.get("author")
            if author:
                report.competitor_accounts.append({"author": author, "likes": likes, "aweme_id": f.get("aweme_id")})
        
        report.trend_signals.sort(key=lambda x: x.score, reverse=True)
        
        kw_counts = {}
        for s in report.trend_signals:
            kw_counts[s.keyword] = kw_counts.get(s.keyword, 0) + s.score
        report.hot_keywords = sorted(kw_counts, key=kw_counts.get, reverse=True)
        
        archetypes = ["霸总", "穿越", "逆袭", "复仇", "甜宠", "神医", "战神", "豪门"]
        top = [kw for kw in report.hot_keywords if kw in archetypes]
        report.recommended_characters = top[:5] if top else archetypes[:3]
        
        genres = ["短剧", "微短剧", "AI短剧", "动漫短剧"]
        top_g = [kw for kw in report.hot_keywords if kw in genres]
        report.recommended_themes = top_g[:3] if top_g else ["短剧品类待进一步扫描"]
        
        declining = [s.keyword for s in report.trend_signals if s.strength == "declining"]
        if declining:
            report.risk_warnings = [f"关键词'{k}'热度下降，选题时注意" for k in set(declining)[:3]]
        
        style_tags = ["AI", "动漫"]
        detected = [t for t in report.hot_keywords if t in style_tags]
        report.visual_style_notes = f"检测到视觉风格: {', '.join(detected)}" if detected else "未检测到明显视觉风格趋势"
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            for name in [f"{scan_id}.json", "latest.json"]:
                with open(os.path.join(output_dir, name), "w", encoding="utf-8") as f:
                    json.dump(report.to_pipeline_input(), f, ensure_ascii=False, indent=2)
            log.info("Saved to %s", output_dir)
        
        return report


def scan_short_drama_market(pdd_cookie=None, douyin_cookie=None, douyin_video_ids=None, output_dir="A:\\XDLS\\market_scan"):
    """Convenience entry point for 短剧工程1 P0."""
    scanner = MarketScanner(pdd_cookie=pdd_cookie, douyin_cookie=douyin_cookie)
    return scanner.scan_short_drama(douyin_video_ids=douyin_video_ids, output_dir=output_dir)
