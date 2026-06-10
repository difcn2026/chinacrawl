---
name: xhls-scraper
description: Complete Firecrawl replacement. 11-in-1 web scraping toolkit: scrape, map, search, monitor, crawl, download, interact, extract (CSS+LLM), AI Judge, persistent sessions. Use when the user needs to scrape web pages, search the web, extract structured data, monitor page changes, crawl sites, download documentation, or interact with browser-based workflows. Triggered by requests to fetch, scrape, search, crawl, monitor, extract data from websites.
metadata:
  short-description: 11-in-1 web scraper — Firecrawl replacement
---

# XHLS Scraper — 完整 Web Scraping 工具包

零外部付费依赖的 Firecrawl 平替。11 项功能覆盖全链路 web 数据采集。

## 导入

```python
import sys
sys.path.insert(0, r"C:\Users\Administrator\Documents\New project\.codex\xhls")
from xhls_scraper import *
```

或通过小丫桥接：
```python
from tools.scraper import *
```

## 11 功能速查

| 函数 | 用途 | FC |
|------|------|----|
| `scrape(url)` | 单页→Markdown (Jina→Trafilatura) | `/scrape` |
| `search_web(q)` | 搜索 (Mojeek+SearXNG) | `/search` |
| `search_and_scrape(q, n)` | 搜索+批量抓取 | — |
| `map_site(url)` | 全站链接发现 | `/map` |
| `crawl_site(url, depth, pages)` | 深度递归爬取 | `/crawl` |
| `download_site(url, dir)` | 整站下载到本地md | `/download` |
| `monitor_page(url)` | SHA256变化检测 | `/monitor` |
| `monitor_page_ai(url)` | AI去噪监控 (10噪声模式) | `/monitor-ai` |
| `browser_interact(url, actions)` | Playwright浏览器交互 | `/interact` |
| `browser_session_save/load/close` | 持久登录会话 | `/session` |
| `extract_structured(url, schema)` | CSS嵌套提取 | `/extract` |
| `extract_llm(url, schema, model)` | LLM语义提取 (qwen2.5:7b) | `/extract-llm` |

## 关键模式

### 编剧调研（搜索→抓取→LLM提取）
```python
results = search_and_scrape("短剧爆款趋势 2026", max_results=10)
data = extract_llm(results[0].url, {
    "标题": ["string"], "核心冲突": "string"
}, model="qwen2.5:7b")
```

### 文档站下载
```python
download_site("https://docs.example.com", "./mirror/", max_pages=50)
```

### 监控价格变化（AI去噪）
```python
mr = monitor_page_ai("https://shop.com/price", label="watch")
if mr.changed and not mr.noise_stripped:
    print("真实变化!")
```

### 登录态持久化
```python
browser_session_save("mysite", "https://site.com/login")
s = browser_session_load("mysite")  # 已登录
browser_session_close(s)
```

## 依赖

- `httpx` + `trafilatura` — HTTP + 内容提取
- `playwright` (Chromium) — 浏览器渲染/搜索/交互
- `ollama` (qwen2.5:7b) — LLM语义提取（可选，无则fallback CSS）

## 文件位置

- 主模块: `.codex/xhls/xhls_scraper.py`
- 小丫桥接: `.codex/xyls/tools/scraper.py`
- 自检: `python .codex/xhls/xhls_scraper.py` → 11项全测试
