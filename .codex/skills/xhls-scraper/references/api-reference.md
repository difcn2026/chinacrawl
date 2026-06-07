# XHLS Scraper API Reference

## scrape(url, prefer="jina", fallback=True)
Single page to markdown. Jina → Trafilatura auto-fallback.
Returns: `ScrapeResult` (url, engine, title, content, word_count, elapsed_ms, ok, error)

## search_web(query, max_results=10)
Search via Playwright Mojeek + SearXNG(4 instances) fallback.
Returns: `list[SearchResult]` (title, url, snippet)

## search_and_scrape(query, max_results=5, engine="jina")
Search then batch scrape all results.
Returns: `list[ScrapeResult]`

## map_site(url)
Discover all URLs via sitemap.xml + page link parsing.
Returns: `list[PageLink]` (url, text, internal)

## crawl_site(url, max_depth=3, max_pages=100, path_prefix=None)
BFS recursive crawl, depth-limited, domain-locked.
Returns: `CrawlResult` (url, pages, total_pages, ok_pages, elapsed_ms)

## download_site(url, output_dir, max_pages=50)
Map → batch scrape → save as markdown files.

## monitor_page(url, label=None)
SHA256 hash change detection.
Returns: `MonitorResult` (url, changed, prev_hash, curr_hash, prev_checked, curr_checked)

## monitor_page_ai(url, label=None)
AI Judge: normalize (strip 10 noise patterns) → hash compare.
Returns: `MonitorAIResult` (url, changed, noise_stripped, prev_hash, curr_hash, noise_removed)

Noise patterns filtered: DATE, TIME, TIME12, RELATIVE, COUNTER, COUNTER2, TRACKING, TOKEN, NONCE, DATA_ATTR

## browser_interact(url, actions, headless=True)
Playwright browser with action sequence.
Actions: navigate, click, type, wait, wait_for, screenshot, scroll, extract
Returns: dict (ok, content, title, screenshots, elapsed_ms, error)

## browser_session_save(name, url)
Save cookies + localStorage to disk.

## browser_session_load(name)
Restore session, returns dict with _browser/_context/_page handles.

## browser_session_close(session_result)
Clean up browser resources.

## extract_structured(url, schema)
CSS selector-based nested extraction.
Schema example: `{"products": {"selector": ".item", "multiple": True, "schema": {"name": "h3", "price": ".price"}}}`
Returns: `ExtractResult` (url, data, ok, elapsed_ms, error)

## extract_llm(url, schema, model="phi3:mini")
LLM semantic extraction (Ollama). Falls back to CSS if Ollama unavailable.
Schema example: `{"summary": "string (1 sentence)", "topics": ["string"]}`
Returns: `ExtractResult`

## Data Classes
- `ScrapeResult`: url, engine, title, content, word_count, elapsed_ms, ok, error
- `PageLink`: url, text, internal
- `MonitorResult`: url, changed, prev_hash, curr_hash, prev_checked, curr_checked, error
- `MonitorAIResult`: url, changed, noise_stripped, prev_hash, curr_hash, noise_removed, error
- `SearchResult`: title, url, snippet
- `CrawlResult`: url, pages, total_pages, ok_pages, elapsed_ms, error
- `ExtractResult`: url, data, ok, elapsed_ms, error

## Config
- `TIMEOUT`: 30 (seconds)
- `PROXY`: "http://127.0.0.1:7654"
- `CAPABILITIES`: dict of all 11 registered functions
