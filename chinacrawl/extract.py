# XHLS v3.3 | 小黑 · Extract Module
# Structured data extraction from web pages (CSS selectors + optional LLM).
# Extracted from scraper.py — standalone extract functions.

import json
import time

import httpx

try:
    from .scraper import ExtractResult  # package import
except ImportError:
    from scraper import ExtractResult    # direct run

USER_AGENT = "XHLS/3.3 (Xiao Hei Extract)"
DEFAULT_TIMEOUT = 30


def extract_structured(url, schema, timeout=DEFAULT_TIMEOUT, proxy=None) -> ExtractResult:
    """Extract structured data from a web page using CSS selectors.

    Simplified implementation: fetches the page, returns empty data.
    Full CSS-selector extraction logic lives in scraper.py's
    extract_structured; this standalone version provides the skeleton.

    Args:
        url: Target page URL.
        schema: Dict mapping field names to CSS selectors.
        timeout: HTTP request timeout in seconds.
        proxy: Optional proxy URL.

    Returns:
        ExtractResult with ok=True if page was fetched, data={} placeholder.
    """
    start = time.time()

    try:
        transport = httpx.HTTPTransport(proxy=proxy) if proxy else None
        with httpx.Client(transport=transport, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            # In the full implementation, parse HTML and apply CSS selectors.
            # For now, return empty data with ok=True.
            elapsed_ms = (time.time() - start) * 1000
            return ExtractResult(
                url=url,
                data={},
                ok=True,
                elapsed_ms=elapsed_ms,
                error=None,
            )
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return ExtractResult(
            url=url,
            data={},
            ok=False,
            elapsed_ms=elapsed_ms,
            error=str(e)[:200],
        )


def extract_llm(url, schema, model="qwen2.5:7b", content=None, timeout=DEFAULT_TIMEOUT, proxy=None) -> ExtractResult:
    """Extract structured data using an LLM (Ollama).

    Simplified implementation: returns ok=False with a note that LLM
    integration is pending. Full implementation in scraper.py calls
    Ollama's /api/generate endpoint.

    Args:
        url: Target page URL.
        schema: Dict describing the desired output structure.
        model: Ollama model name (e.g. 'qwen2.5:7b').
        content: Pre-fetched page content (optional; fetches if None).
        timeout: HTTP request timeout in seconds.
        proxy: Optional proxy URL.

    Returns:
        ExtractResult with ok=False and placeholder error message.
    """
    return ExtractResult(
        url=url,
        data={},
        ok=False,
        elapsed_ms=0,
        error="LLM extraction not yet wired — use scraper.extract_llm for full implementation",
    )
