# SearXNG 中文搜索引擎配置指南

> xhls_scraper 护城河 L1 — 决定用户第一印象的核心文档

## 概述

xhls_scraper 内置 SearXNG 元搜索引擎作为中文搜索的主引擎。SearXNG 聚合 Google、Bing、Wikipedia 等多个搜索引擎结果，无需 API Key，完全自托管。

## 当前部署

| 配置项 | 值 |
|--------|-----|
| VPS IP | `47.236.24.76` |
| SearXNG 端口 | `9999` |
| 反向代理 | Nginx → SearXNG 容器 |
| 搜索格式 | JSON (`?format=json`) |
| 中文支持 | ✅ (通过 Bing/Google 中文搜索) |

## 三槽位配置

当前 SearXNG 三槽位已启用：

```yaml
# /opt/searxng/settings.yml
search:
  formats:
    - html
    - json          # ← xhls_scraper 使用 JSON API

engines:
  - name: google
    engine: google
    shortcut: g
    
  - name: wikipedia
    engine: wikipedia
    shortcut: wp
    
  - name: duckduckgo
    engine: duckduckgo
    shortcut: ddg
```

## 中文搜索能力

| 搜索引擎 | 中文搜索 | 状态 |
|----------|:--:|:--:|
| Google (via SearXNG) | ✅ 优秀 | 在线 |
| Bing (via SearXNG) | ✅ 良好 | 在线 |
| DuckDuckGo | ⚠️ 一般 | 在线 |
| 百度 | ❌ CAPTCHA | 不可用 |
| 搜狗 | ❌ 需手动提交 | 不可用 |

## 在 xhls_scraper 中使用

```python
from xhls_scraper import search_web, search_and_scrape

# 中文搜索
results = search_web("Python 网页抓取工具", max_results=10)

# 搜索 + 自动抓取内容
pages = search_and_scrape("今日财经新闻", max_results=5)
```

## 搜索降级策略

xhls_scraper 的 `search_web()` 使用三级降级：

```
1. Mojeek (直接搜索，无依赖)
   ↓ 失败
2. SearXNG 实例 (JSON API)
   ↓ 失败
3. Bing 网页抓取 (HTML 解析，via 代理)
```

## 添加自定义 SearXNG 实例

编辑 `SEARXNG_INSTANCES` 列表：

```python
SEARXNG_INSTANCES = [
    "http://47.236.24.76:9999",    # 阿里云 SG VPS (主)
    # "http://your-own-searxng:8888",  # 添加备用实例
]
```

## 本地部署 SearXNG

```bash
# Docker 一键部署
docker run -d --name searxng \
  -p 8888:8080 \
  -v ./searxng:/etc/searxng \
  searxng/searxng:latest

# 配置中文搜索
# 编辑 ./searxng/settings.yml，添加 engines
```

## 已知限制

- **百度**: 严格的 CAPTCHA 验证，SearXNG 无法绕过
- **搜狗**: 域名验证要求，非自有域名无法提交
- **替代方案**: 用户可手动在百度/搜狗站长平台提交 URL

## 更新日期

2026-06-06
