# chinacrawl/market/report.py - Unified market report format
# One report to rule them all: PDD + Douyin → 选题建议

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

CST = timezone(timedelta(hours=8))


@dataclass
class TrendSignal:
    """A single trend detection from any platform."""
    keyword: str
    platform: str          # "pinduoduo" | "douyin"
    signal_type: str       # "product" | "hashtag" | "account" | "video"
    strength: str          # "rising" | "hot" | "declining"
    evidence: list = field(default_factory=list)
    score: int = 0


@dataclass
class MarketReport:
    """Unified cross-platform market intelligence report."""
    
    scan_id: str = ""
    generated_at: str = ""
    category: str = "短剧"
    
    pdd_findings: list = field(default_factory=list)
    douyin_findings: list = field(default_factory=list)
    
    trend_signals: list = field(default_factory=list)
    hot_keywords: list = field(default_factory=list)
    competitor_accounts: list = field(default_factory=list)
    
    recommended_themes: list = field(default_factory=list)
    recommended_characters: list = field(default_factory=list)
    visual_style_notes: str = ""
    risk_warnings: list = field(default_factory=list)
    
    raw_pdd_data: list = field(default_factory=list)
    raw_douyin_data: list = field(default_factory=list)
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now(CST).isoformat()
    
    def to_pipeline_input(self) -> dict:
        """Convert to format expected by 短剧工程1 P0."""
        return {
            "source": "chinacrawl-market-scan",
            "scan_id": self.scan_id,
            "generated_at": self.generated_at,
            "category": self.category,
            "market_signals": {
                "top_keywords": self.hot_keywords[:10],
                "trending_themes": [
                    {"theme": s.keyword, "strength": s.strength, "score": s.score}
                    for s in self.trend_signals if s.strength in ("rising", "hot")
                ][:5],
                "saturated_topics": [
                    s.keyword for s in self.trend_signals if s.strength == "declining"
                ],
            },
            "content_signals": {
                "recommended_themes": self.recommended_themes,
                "recommended_characters": self.recommended_characters,
                "visual_style_notes": self.visual_style_notes,
            },
            "visual_refs": {
                "competitor_accounts": self.competitor_accounts[:5],
                "style_notes": self.visual_style_notes,
            },
            "distribution_signals": {
                "hot_hashtags": [k for k in self.hot_keywords if len(k) <= 10][:10],
                "platform_breakdown": {
                    "pinduoduo_products": len(self.pdd_findings),
                    "douyin_videos": len(self.douyin_findings),
                },
            },
            "risk_warnings": self.risk_warnings,
        }
    
    def to_summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"=== 市场扫描报告 [{self.category}] ===",
            f"时间: {self.generated_at}",
            "",
            f"拼多多: {len(self.pdd_findings)} 结果 | 抖音: {len(self.douyin_findings)} 视频",
            "",
            "热门趋势:",
        ]
        for s in sorted(self.trend_signals, key=lambda x: x.score, reverse=True)[:5]:
            emoji = {"rising": "📈", "hot": "🔥", "declining": "📉"}.get(s.strength, "•")
            lines.append(f"  {emoji} [{s.platform}] {s.keyword} (score:{s.score})")
        
        lines += ["", "选题建议:"]
        for t in self.recommended_themes[:3]:
            lines.append(f"  → {t}")
        
        if self.risk_warnings:
            lines += ["", "⚠️ 风险:"]
            for w in self.risk_warnings:
                lines.append(f"  ⚠ {w}")
        
        return "\n".join(lines)
