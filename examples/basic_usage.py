"""xhls_scraper basic usage examples.

Requirements:
    pip install xhls_scraper

Optional (for full features):
    pip install xhls_scraper[full]
    ollama pull qwen2.5:7b
"""

from xhls_scraper import (
    scrape, search_web, map_site, crawl_site,
    download_site, monitor_page, monitor_page_ai,
    extract_structured, extract_llm,
    browser_interact, browser_session_save, browser_session_load,
)


def example_scrape():
    """1. Scrape a single page to Markdown."""
    print("\n[1] Scrape example.com")
    r = scrape("https://example.com")
    print(f"  Title: {r.title}")
    print(f"  Words: {r.word_count}")
    print(f"  Engine: {r.engine}")
    print(f"  Content preview: {r.content[:100]}...")


def example_search():
    """2. Web search via SearXNG."""
    print("\n[2] Search 'Python async patterns'")
    results = search_web("Python async patterns", max_results=5)
    for i, r in enumerate(results, 1):
        print(f"  [{i}] {r.title[:60]}")


def example_map():
    """3. Discover all URLs on a site."""
    print("\n[3] Map example.com")
    links = map_site("https://example.com", timeout=15)
    internal = [l for l in links if l.internal]
    print(f"  Found {len(links)} links ({len(internal)} internal)")


def example_monitor():
    """4. Monitor a page for changes."""
    print("\n[4] Monitor example.com")
    r = monitor_page("https://example.com", label="demo")
    print(f"  Changed: {r.changed}")
    print(f"  Current hash: {r.curr_hash[:16]}...")


def example_monitor_ai():
    """5. AI-powered monitoring (filters noise)."""
    print("\n[5] AI Monitor example.com (noise-stripped)")
    r = monitor_page_ai("https://example.com", label="demo-ai")
    print(f"  Changed: {r.changed}")


def example_extract():
    """6. CSS-selector based extraction."""
    print("\n[6] Extract from example.com")
    r = extract_structured("https://example.com", {
        "heading": "h1",
        "body": "p",
    })
    print(f"  Heading: {r.data.get('heading', 'N/A')[:50]}")


def example_llm_extract():
    """7. LLM-powered semantic extraction (requires Ollama)."""
    print("\n[7] LLM extract from example.com (Ollama required)")
    r = extract_llm("https://example.com", {
        "title": "the main heading text",
        "description": "the main paragraph text",
    })
    print(f"  OK: {r.ok}")
    if r.ok:
        print(f"  Data: {r.data}")
    else:
        print(f"  Error: {r.error}")
        print("  Hint: Install Ollama and pull qwen2.5:7b")


if __name__ == "__main__":
    print("xhls_scraper Examples")
    print("=" * 50)

    example_scrape()
    example_search()
    example_map()
    example_monitor()
    example_monitor_ai()
    example_extract()
    example_llm_extract()

    print("\n" + "=" * 50)
    print("All examples complete. See docs for advanced usage.")
