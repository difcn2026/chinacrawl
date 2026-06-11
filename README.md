# ChinaCrawl 🕷️

> 11-in-1 Chinese Web Search & Scraping Engine — open-source alternative to Firecrawl for the Chinese internet.

[![CI](https://github.com/difcn2026/chinacrawl/actions/workflows/ci.yml/badge.svg)](https://github.com/difcn2026/chinacrawl/actions/workflows/ci.yml)
[![Docs](https://github.com/difcn2026/chinacrawl/actions/workflows/docs.yml/badge.svg)](https://github.com/difcn2026/chinacrawl/actions/workflows/docs.yml)
[![PyPI](https://img.shields.io/pypi/v/chinacrawl?label=pypi)](https://pypi.org/project/chinacrawl/)
[![Python](https://img.shields.io/pypi/pyversions/chinacrawl)](https://pypi.org/project/chinacrawl/)

Zero external API dependencies. AGPLv3 licensed.

## Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| 1 | **scrape** | Single page → markdown (Jina AI / Trafilatura) |
| 2 | **map** | Discover all URLs on a site |
| 3 | **search** | Web search via Mojeek + SearXNG |
| 4 | **monitor** | Hash-based page change detection |
| 5 | **monitor-ai** | AI Judge noise-stripped monitoring |
| 6 | **crawl** | Depth-limited recursive crawl |
| 7 | **download** | Map + scrape + save to disk |
| 8 | **interact** | Browser interaction (Playwright) |
| 9 | **extract** | Structured data extraction (CSS) |
| 10 | **extract-llm** | LLM semantic extraction (Ollama) |
| 🎵 | **douyin** | TikTok China — user posts, search, download, monitor |
| 🛒 | **pinduoduo** | E-commerce — product search, detail, reviews, monitor |

## Quick Start

```python
from chinacrawl import scrape, search_web

# Scrape a single page
result = scrape("https://example.com")
print(result.title, result.word_count)

# Search the web
results = search_web("Python 爬虫", max_results=10)
for r in results:
    print(r.title, r.url)
```

### Douyin (TikTok China)

```python
from chinacrawl import douyin_login, douyin_user_posts

douyin_login()  # QR code login
for post in douyin_user_posts("user_sec_uid"):
    print(post.desc, post.digg_count)
```

### Pinduoduo

```python
from chinacrawl import pinduoduo_product_search, pinduoduo_product_detail

for product in pinduoduo_product_search("蓝牙耳机"):
    print(product.title, product.price)
```

## Install

```bash
pip install chinacrawl
pip install playwright
python -m playwright install --with-deps chromium
```

## Requirements

- Python 3.10+
- `httpx`, `trafilatura`, `playwright` (browser features)
- `mcp` (optional, for agent integration)

## CI/CD

| Workflow | Trigger | What it does |
|----------|---------|-------------|
| **CI** | push / PR | Python 3.12 lint (py_compile all `.py`) |
| **CI** | tag `v*` | Build & publish to PyPI |
| **Docs** | push on `main` | Build MkDocs Material → GitHub Pages |

### PyPI Publish Setup

Add a secret `PYPI_API_TOKEN` to your GitHub repo (Settings → Secrets and variables → Actions).

## License

AGPLv3 © 2026 Xiao Hei (XHLS v3.0)
