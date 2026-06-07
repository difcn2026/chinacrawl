<p align="center">
  <img src="https://img.shields.io/badge/License-AGPLv3-blue.svg" alt="AGPLv3">
  <img src="https://img.shields.io/badge/Python-3.10+-green.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Status-Alpha-orange.svg" alt="Alpha">
</p>

# ChinaCrawl

> **The Firecrawl alternative that works in China. 12-in-1 web data engine — zero external API cost.**
>
> 中国版 Firecrawl。12 合 1 Web 数据引擎 — 零外部付费依赖。

---

## Why ChinaCrawl?

Firecrawl is the best web scraping engine from Silicon Valley. But it's blocked in China and has no Chinese search optimization. ChinaCrawl fills this gap.

| | Firecrawl | ChinaCrawl |
|---|---|---|
| Works in China | No (blocked + no Chinese search) | Yes (Alibaba Cloud / self-hosted) |
| Chinese search | Google only | Baidu / Sogou / SearXNG configurable |
| LLM extraction | Credits-based (OpenAI API) | Local Ollama — zero marginal cost |
| Cost | Paid API | Free (AGPL) |

---

## Capabilities (12-in-1)

| # | Capability | Firecrawl Equivalent | Usage |
|---|-----------|:---:|---|
| 1 | **scrape** | `/scrape` | `scrape("https://example.com")` |
| 2 | **search** | `/search` | `search_web("keyword")` |
| 3 | **map** | `/map` | `map_site("https://example.com")` |
| 4 | **crawl** | `/crawl` | `crawl_site("https://example.com")` |
| 5 | **download** | — | `download_site("url", "output/")` |
| 6 | **monitor** | `/monitor` | `monitor_page("url")` |
| 7 | **monitor-ai** | — | `monitor_page_ai("url")` |
| 8 | **extract** | `/extract` | `extract_structured("url", schema)` |
| 9 | **extract-llm** | `/extract` (credits) | `extract_llm("url", schema)` |
| 10 | **interact** | `/interact` | `browser_interact("url", actions)` |
| 11 | **session** | — | `browser_session_save/load("name")` |

> `extract-llm` uses local Ollama (qwen2.5:7b) for semantic extraction. Zero API cost, unlimited calls.

---

## Quick Start

### Install

```bash
# Basic (scrape / search / map / crawl / download / monitor)
pip install chinacrawl

# Full (includes Playwright for browser interaction)
pip install chinacrawl[full]

# LLM extraction (optional, requires Ollama)
ollama pull qwen2.5:7b
```

### 3 Lines to Start

```python
from chinacrawl import scrape, search_web, extract_llm

# Any URL -> Markdown
result = scrape("https://example.com")
print(result.content[:200])

# Web search
results = search_web("Python web scraping", max_results=5)
for r in results:
    print(f"{r.title}: {r.url}")

# LLM-powered structured extraction (zero cost!)
data = extract_llm("https://news.ycombinator.com", {
    "top_story": "h1",
    "all_headlines": "a.storylink"
})
print(data.data)
```

### CLI

```bash
python chinacrawl.py  # Run built-in 11-capability test suite
```

---

## Architecture

```
ChinaCrawl
├── Scrape:   jina.ai + trafilatura  ->  Markdown
├── Search:   SearXNG (self-hosted or public)
├── Map:      trafilatura link discovery
├── Crawl:    BFS recursive extraction
├── Download: Map + Scrape -> local {url}.md files
├── Monitor:  Hash + AI Judge (noise-stripped)
├── Extract:  CSS selector + Ollama qwen (semantic)
└── Interact: Playwright browser automation
```

---

## Use Cases

- Financial data — batch scrape central bank / SEC announcements
- E-commerce intel — monitor competitor pricing on JD / Tmall
- Legal compliance — archive government regulations with version diff
- Bid monitoring — real-time government procurement alerts (AI de-noised)
- RAG pipelines — any website -> offline markdown -> Dify / LangChain

---

## Disclaimer

> **ChinaCrawl is a data extraction tool, NOT an AI service.**
>
> **IMPORTANT: Users assume all legal responsibility.** ChinaCrawl provides general-purpose data collection capabilities. Users must:
> - Respect target websites' robots.txt and terms of service
> - Comply with applicable laws (including China's Cybersecurity Law, Data Security Law, Personal Information Protection Law)
> - Obtain necessary permissions and consent
> - Not use this tool for any illegal purpose
>
> ChinaCrawl authors and contributors bear no legal liability for users' actions.
>
> The `extract-llm` feature depends on user-installed Ollama models. Users must ensure their chosen model's license (Apache 2.0, MIT, Llama Community, etc.) permits their intended use. ChinaCrawl defaults to qwen2.5:7b (Apache 2.0, no restrictions).
>
> Respect robots.txt and terms of service. For legitimate use only.

---

## License

GNU Affero General Public License v3.0 — Free to use, modify, and distribute. Modified versions served over a network must disclose source code.

---

## Roadmap

- [x] 11-in-1 core capabilities
- [x] SearXNG search integration
- [x] AI Judge noise filtering
- [ ] Chinese search engine config (Baidu / Sogou)
- [ ] PyPI release
- [ ] Docker one-click deployment
- [ ] Managed API (chinacrawl.cloud)

---

<p align="center">
  <sub>Built by Xiao Hei · ChinaCrawl · 2026</sub>

<!-- SEO Keywords: chinacrawl ChinaCrawl web-scraping Firecrawl-alternative Chinese-web-scraper Python-scraper Ollama-extraction SearXNG AGPLv3 difcn2026 中国版Firecrawl 网页抓取 爬虫 Python爬虫 开源爬虫 中文搜索 本地LLM提取 -->
</p>
