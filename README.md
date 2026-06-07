<p align="center">
  <img src="https://img.shields.io/badge/License-AGPLv3-blue.svg" alt="AGPLv3">
  <img src="https://img.shields.io/badge/Python-3.10+-green.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Version-0.2.0-orange.svg" alt="v0.2.0">
  <img src="https://img.shields.io/badge/Douyin-✓-ee2255.svg" alt="Douyin Ready">
</p>

# ChinaCrawl

> **The Firecrawl alternative that works in China. 12-in-1 web data engine + Douyin adapter — zero external API cost.**
>
> 中国版 Firecrawl。12 合 1 数据引擎 + 抖音适配器 — 零外部付费依赖。

---

## Why ChinaCrawl?

Firecrawl is the best web scraping engine from Silicon Valley. But it's blocked in China and has no Chinese search optimization. ChinaCrawl fills this gap.

| | Firecrawl | ChinaCrawl |
|---|---|---|
| Works in China | No | ✅ Alibaba Cloud / self-hosted |
| Chinese search | Google only | ✅ SearXNG configurable |
| Douyin (TikTok CN) | ❌ | ✅ Full adapter |
| LLM extraction | Credits (OpenAI) | ✅ Local Ollama — zero cost |
| Cost | Paid API | Free (AGPLv3) |

---

## Capabilities (12-in-1 + Douyin)

| # | Capability | Firecrawl | Usage |
|---|-----------|:---:|---|
| 1 | **scrape** | `/scrape` | `scrape("https://example.com")` |
| 2 | **search** | `/search` | `search_web("keyword")` |
| 3 | **map** | `/map` | `map_site("https://example.com")` |
| 4 | **crawl** | `/crawl` | `crawl_site("https://example.com")` |
| 5 | **download** | — | `download_site("url", "output/")` |
| 6 | **monitor** | `/monitor` | `monitor_page("url")` |
| 7 | **monitor-ai** | — | `monitor_page_ai("url")` |
| 8 | **extract** | `/extract` | `extract_structured("url", schema)` |
| 9 | **extract-llm** | credits | `extract_llm("url", schema)` |
| 10 | **interact** | `/interact` | `browser_interact("url", actions)` |
| 11 | **session** | — | `browser_session_save/load("name")` |
| 🆕 | **douyin** | ❌ | Full TikTok CN adapter |

> `extract-llm` uses local Ollama (qwen2.5:7b). Zero API cost, unlimited calls.

---

## 🆕 Douyin (TikTok CN) Adapter — v0.2.0

The **only open-source Douyin adapter** with full anti-bot bypass.

### Why Douyin is Hard

Douyin employs **three layers** of anti-bot protection:

```
Layer 1: X-Bogus signature      — per-request cryptographic token
Layer 2: msToken                — browser-fingerprinted session token
Layer 3: byted_acrawler Shark   — behavioral anti-bot engine
```

ChinaCrawl's breakthrough: **browser-context `fetch()`** — execute API calls from within a real browser's JavaScript context, where the security SDK transparently signs all requests.

| Channel | X-Bogus | msToken | Shark | Speed | Status |
|---------|:-------:|:-------:|:-----:|:-----:|:------:|
| Direct HTTP API | Need | Need | ❌ | Fast | Blocked |
| Browser XHR Intercept | Auto | Auto | ✅ | Medium | ✅ |
| **Browser fetch()** | Auto | Auto | ✅ | Fast | ✅ |

### Quick Start

```python
from chinacrawl import douyin_search, douyin_user_posts, douyin_login

# 1. Login (QR code — one time)
douyin_login()

# 2. Search
results = douyin_search("AI短视频", max_results=20)
for r in results:
    print(r.desc, r.digg_count)

# 3. Collect all posts from a user
for post in douyin_user_posts("MS4wLjABAAAAu1K73eFX..."):
    print(post.desc, post.digg_count, post.video_url)
    # Download: douyin_video_download(post.video_url, "videos/")
```

### Douyin API Reference

| Function | Description |
|----------|-------------|
| `douyin_login()` | QR code login, saves session |
| `douyin_user_info(sec_uid)` | User profile (nickname, followers, etc.) |
| `douyin_user_posts(sec_uid)` | **All posts** — full pagination |
| `douyin_search(keyword)` | General search (videos + users) |
| `douyin_search_user(keyword)` | User search |
| `douyin_video_info(aweme_id)` | Single video detail |
| `douyin_video_download(url, path)` | Download video file |
| `douyin_monitor_user(sec_uid)` | Monitor user for new posts |
| `douyin_save_session(path)` | Save login session |
| `douyin_load_session(path)` | Load saved session |

### Architecture

```
douyin_search("AI")
  └─ scraper.search()
       ├─ Channel 0: browser.search_via_fetch()  ← NO signing needed!
       ├─ Channel 1: browser.search_via_xhr()     ← XHR intercept
       └─ Channel 2: api.search_general()         ← X-Bogus signed

douyin_user_posts(uid)
  └─ scraper.user_posts()
       ├─ Channel 0: browser.collect_user_posts_via_xhr()  ← scrollIntoView
       ├─ Channel 1: api.fetch_user_posts()                ← X-Bogus signed
       └─ Channel 2: browser.open_user_page()              ← DOM extract
```

### Verified

| Account | Followers | Collected | Method |
|---------|-----------|:---------:|--------|
| 小冰 | 1.03M | 435/437 (99.5%) | XHR intercept |
| AI课代表小明 | 2.20M | 66/66 (100%) | Browser fetch |

### Requirements

```bash
pip install chinacrawl[full]  # includes Playwright
playwright install chromium
```

---

## Quick Start

### Install

```bash
# Basic (scrape / search / map / crawl / download / monitor)
pip install chinacrawl

# Full (includes Playwright for browser + Douyin)
pip install chinacrawl[full]

# LLM extraction (optional)
ollama pull qwen2.5:7b
```

### 3 Lines to Start

```python
from chinacrawl import scrape, search_web, extract_llm

# Any URL → Markdown
result = scrape("https://example.com")
print(result.content[:200])

# Web search
results = search_web("Python web scraping", max_results=5)

# LLM extraction (zero cost!)
data = extract_llm("https://news.ycombinator.com", {
    "top_story": "h1",
    "all_headlines": "a.storylink"
})
```

### CLI

```bash
python chinacrawl.py  # Built-in capability test suite
```

---

## Architecture

```
ChinaCrawl
├── Scrape:   jina.ai + trafilatura  →  Markdown
├── Search:   SearXNG (self-hosted or public)
├── Map:      trafilatura link discovery
├── Crawl:    BFS recursive extraction
├── Download: Map + Scrape → local files
├── Monitor:  Hash + AI Judge (noise-stripped)
├── Extract:  CSS selector + Ollama qwen (semantic)
├── Interact: Playwright browser automation
└── Douyin:   Browser fetch() → 3-layer anti-bot bypass
```

---

## Use Cases

- **Douyin intel** — user collection, search trends, competitive analysis
- Financial data — batch scrape central bank / SEC announcements
- E-commerce intel — monitor competitor pricing on JD / Tmall
- Legal compliance — archive government regulations with version diff
- RAG pipelines — any website → offline markdown → Dify / LangChain

---

## Roadmap

- [x] 12-in-1 core capabilities
- [x] **Douyin adapter** (X-Bogus + msToken + Shark bypass)
- [x] SearXNG search integration
- [x] AI Judge noise filtering
- [x] Browser fetch() anti-bot breakthrough
- [ ] Chinese search engines (Baidu / Sogou)
- [ ] Docker one-click deployment
- [ ] Managed API (chinacrawl.cloud)

---

## Disclaimer

> **ChinaCrawl is a data extraction tool, NOT an AI service.**
>
> Users assume all legal responsibility. Respect robots.txt, terms of service, and applicable laws (China's Cybersecurity Law, Data Security Law, PIPL).

---

## License

GNU Affero General Public License v3.0

---

<p align="center">
  <sub>Built by Xiao Hei · ChinaCrawl · 2026</sub>
</p>
