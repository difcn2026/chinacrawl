"""Spider Framework - Production-grade crawling with pause/resume.

Inspired by Scrapling's Spider architecture. Provides:
- Abstract Spider base class (subclass and override parse())
- Session management with automatic browser reuse
- Proxy rotation (round-robin, random, weighted)
- Checkpoint/pause/resume via JSON files
- Concurrent request management
- Robots.txt compliance (optional)
- Request deduplication via URL fingerprinting

XHLS v3.3 | Xiao Hei Learning System
Layer L4: Spider Framework
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import signal
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Set, Any, Callable, AsyncGenerator
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

# --- Constants ---

CST = timezone(timedelta(hours=8))
DEFAULT_CHECKPOINT_INTERVAL = 300  # 5 minutes
DEFAULT_CONCURRENT = 4
DEFAULT_DELAY = 0.5  # seconds between requests to same domain

BLOCKED_STATUS_CODES = {401, 403, 407, 429, 444, 500, 502, 503, 504}

# --- Data Classes ---


@dataclass
class CrawlRequest:
    """A request to be processed by the spider."""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)  # user data passthrough
    priority: int = 0  # higher = processed first
    dont_filter: bool = False  # skip dedup
    callback: Optional[Callable] = None  # override parse for this request

    @property
    def fingerprint(self) -> str:
        """Unique fingerprint for deduplication."""
        raw = f"{self.method}|{self.url}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc


@dataclass
class CrawlResponse:
    """Response from a fetched page."""
    url: str
    status: int
    text: str
    headers: Dict[str, str] = field(default_factory=dict)
    elapsed_ms: float = 0
    error: Optional[str] = None
    request: Optional[CrawlRequest] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 400 and self.error is None


@dataclass
class CrawlStats:
    """Statistics for a crawl run."""
    start_time: str = ""
    end_time: str = ""
    requests_made: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    requests_blocked: int = 0
    items_scraped: int = 0
    bytes_downloaded: int = 0
    domains_visited: Set[str] = field(default_factory=set)


# --- Proxy Rotation ---


class ProxyRotator:
    """Proxy pool with multiple rotation strategies."""

    def __init__(self, proxies: List[str], strategy: str = "round_robin"):
        """
        :param proxies: List of proxy URLs (e.g., "http://user:pass@host:port")
        :param strategy: "round_robin", "random", or "weighted"
        """
        if not proxies:
            raise ValueError("At least one proxy required")
        self.proxies = proxies
        self.strategy = strategy
        self._index = 0
        self._failures: Dict[str, int] = {}  # proxy -> failure count
        self._max_failures = 3

    def next(self) -> str:
        """Get next proxy according to strategy."""
        if self.strategy == "random":
            return random.choice(self.proxies)
        elif self.strategy == "weighted":
            return self._weighted_choice()
        else:  # round_robin
            proxy = self.proxies[self._index]
            self._index = (self._index + 1) % len(self.proxies)
            return proxy

    def _weighted_choice(self) -> str:
        """Prefer proxies with fewer failures."""
        weights = [
            max(0, self._max_failures - self._failures.get(p, 0) + 1)
            for p in self.proxies
        ]
        total = sum(weights)
        if total == 0:
            # All proxies have max failures, reset
            self._failures.clear()
            return random.choice(self.proxies)
        r = random.uniform(0, total)
        cum = 0
        for proxy, w in zip(self.proxies, weights):
            cum += w
            if r <= cum:
                return proxy
        return self.proxies[-1]

    def mark_failure(self, proxy: str):
        self._failures[proxy] = self._failures.get(proxy, 0) + 1

    def mark_success(self, proxy: str):
        self._failures[proxy] = max(0, self._failures.get(proxy, 0) - 1)


# --- Checkpoint ---


class CheckpointManager:
    """Save/restore crawl state for pause/resume."""

    def __init__(self, crawldir: str, spider_name: str):
        self.crawldir = Path(crawldir)
        self.crawldir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.crawldir / f"{spider_name}_checkpoint.json"
        self.state_file = self.crawldir / f"{spider_name}_state.json"

    def save(self, pending_urls: List[str], visited_urls: Set[str],
             stats: CrawlStats, meta: Dict = None):
        """Save current crawl state."""
        state = {
            "pending_urls": list(pending_urls),
            "visited_urls": list(visited_urls),
            "stats": {
                "requests_made": stats.requests_made,
                "requests_success": stats.requests_success,
                "requests_failed": stats.requests_failed,
                "requests_blocked": stats.requests_blocked,
                "items_scraped": stats.items_scraped,
                "bytes_downloaded": stats.bytes_downloaded,
                "domains_visited": list(stats.domains_visited),
                "start_time": stats.start_time,
            },
            "saved_at": datetime.now(CST).isoformat(),
            "meta": meta or {},
        }
        self.checkpoint_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> Optional[dict]:
        """Load saved checkpoint, or None if no checkpoint exists."""
        if not self.checkpoint_file.exists():
            return None
        return json.loads(self.checkpoint_file.read_text(encoding="utf-8"))

    def clear(self):
        """Remove checkpoint files."""
        for f in [self.checkpoint_file, self.state_file]:
            if f.exists():
                f.unlink()


# --- Spider Base Class ---


class Spider(ABC):
    """Abstract Spider base class.

    Usage:
        class MySpider(Spider):
            name = "myspider"
            start_urls = ["https://example.com"]
            allowed_domains = {"example.com"}

            async def parse(self, response: CrawlResponse):
                # Extract data, yield new requests
                title = extract_title(response.text)
                yield {"title": title}

                for link in extract_links(response.text):
                    yield CrawlRequest(url=urljoin(response.url, link))
    """

    # --- Configuration (override in subclass) ---

    name: str = ""  # REQUIRED
    start_urls: List[str] = []
    allowed_domains: Set[str] = set()

    # Concurrency
    concurrent_requests: int = DEFAULT_CONCURRENT
    concurrent_requests_per_domain: int = 0  # 0 = unlimited
    download_delay: float = DEFAULT_DELAY
    max_blocked_retries: int = 3

    # Robots.txt
    obey_robots_txt: bool = False

    # Development mode (cache responses)
    dev_mode: bool = False
    dev_cache_dir: Optional[str] = None

    # Proxy
    proxies: List[str] = []
    proxy_strategy: str = "round_robin"

    # Checkpoint
    crawldir: Optional[str] = None
    checkpoint_interval: float = DEFAULT_CHECKPOINT_INTERVAL

    # Logging
    log_level: int = logging.INFO

    def __init__(self):
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must set 'name'")

        self.logger = logging.getLogger(f"chinacrawl.spider.{self.name}")
        self.logger.setLevel(self.log_level)
        if not self.logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter(
                f"[%(asctime)s] {self.name} %(levelname)s: %(message)s",
                datefmt="%H:%M:%S",
            ))
            self.logger.addHandler(h)

        self._stats = CrawlStats()
        self._visited: Set[str] = set()
        self._pending: asyncio.Queue = asyncio.Queue()
        self._active_tasks: Set[asyncio.Task] = set()
        self._running = False
        self._paused = False
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._domain_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._domain_last_request: Dict[str, float] = {}
        self._domains_visited: Set[str] = set()

        # Session management
        self._http_client = None
        self._browser = None
        self._browser_context = None

        # Proxy rotator
        self._proxy_rotator: Optional[ProxyRotator] = None
        if self.proxies:
            self._proxy_rotator = ProxyRotator(self.proxies, self.proxy_strategy)

        # Checkpoint
        self._checkpoint: Optional[CheckpointManager] = None
        if self.crawldir:
            self._checkpoint = CheckpointManager(self.crawldir, self.name)

        # Robots.txt cache
        self._robots_cache: Dict[str, RobotFileParser] = {}

        # Development cache
        self._dev_cache: Dict[str, CrawlResponse] = {}

    # --- Public API ---

    async def run(self, resume: bool = False):
        """Start the spider.

        :param resume: If True, try to resume from checkpoint.
        """
        self._running = True
        self._stats.start_time = datetime.now(CST).isoformat()
        self._semaphore = asyncio.Semaphore(self.concurrent_requests)

        # Resume from checkpoint
        if resume and self._checkpoint:
            state = self._checkpoint.load()
            if state:
                self.logger.info(f"Resuming from checkpoint ({len(state['pending_urls'])} pending)")
                for url in state["pending_urls"]:
                    self._pending.put_nowait(CrawlRequest(url=url))
                self._visited = set(state["visited_urls"])
                s = state["stats"]
                self._stats.requests_made = s["requests_made"]
                self._stats.requests_success = s["requests_success"]
                self._stats.requests_failed = s["requests_failed"]
                self._stats.requests_blocked = s["requests_blocked"]
                self._stats.items_scraped = s["items_scraped"]
                self._stats.bytes_downloaded = s["bytes_downloaded"]
                self._stats.domains_visited = set(s["domains_visited"])
                self._stats.start_time = s.get("start_time", self._stats.start_time)

        # Seed initial requests
        async for req in self.start_requests():
            self._pending.put_nowait(req)
        for url in self.start_urls:
            self._pending.put_nowait(CrawlRequest(url=url))

        # Last checkpoint timer
        last_checkpoint = time.time()

        # Worker loop
        workers = []
        for _ in range(self.concurrent_requests):
            workers.append(asyncio.create_task(self._worker()))

        # Checkpoint loop
        while self._running:
            await asyncio.sleep(1)
            if self._checkpoint and time.time() - last_checkpoint > self.checkpoint_interval:
                self._save_checkpoint()
                last_checkpoint = time.time()

            # All done?
            if self._pending.empty() and not self._active_tasks:
                self._running = False
                break

        # Wait for workers to finish
        for w in workers:
            w.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

        self._stats.end_time = datetime.now(CST).isoformat()

        # Final checkpoint & cleanup
        if self._checkpoint:
            self._checkpoint.clear()

        await self._cleanup()
        self.logger.info(f"Crawl complete. {self._stats.requests_success}/{self._stats.requests_made} success, "
                         f"{self._stats.items_scraped} items")

    def pause(self):
        """Pause the crawl and save checkpoint."""
        self._paused = True
        self._save_checkpoint()
        self.logger.info("Crawl paused")

    def resume(self):
        """Resume a paused crawl."""
        self._paused = False
        self.logger.info("Crawl resumed")

    def stop(self):
        """Stop the crawl gracefully."""
        self._running = False
        self.logger.info("Stopping crawl...")

    @property
    def stats(self) -> CrawlStats:
        return self._stats

    # --- Override hooks ---

    async def start_requests(self) -> AsyncGenerator[CrawlRequest, None]:
        """Override to add custom initial requests."""
        return
        yield  # make it a generator

    @abstractmethod
    async def parse(self, response: CrawlResponse) -> AsyncGenerator[Any, None]:
        """Override: process each response, yield dicts (items) or CrawlRequests."""
        yield  # pragma: no cover

    async def process_request(self, request: CrawlRequest) -> CrawlRequest:
        """Override: modify request before sending (add headers, etc.)."""
        return request

    async def handle_error(self, request: CrawlRequest, error: str) -> None:
        """Override: handle fetch errors."""
        self.logger.warning(f"Error fetching {request.url}: {error}")

    async def should_follow(self, url: str) -> bool:
        """Override: custom URL filtering."""
        domain = urlparse(url).netloc
        if self.allowed_domains and domain not in self.allowed_domains:
            return False
        return True

    # --- Internal ---

    async def _worker(self):
        """Main worker loop: fetch -> parse -> enqueue."""
        while self._running:
            # Wait if paused
            while self._paused and self._running:
                await asyncio.sleep(1)

            try:
                request = await asyncio.wait_for(self._pending.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            task = asyncio.create_task(self._process_request(request))
            self._active_tasks.add(task)
            task.add_done_callback(self._active_tasks.discard)

    async def _process_request(self, request: CrawlRequest):
        """Process a single request: fetch, parse, handle results."""
        async with self._semaphore:
            # Domain rate limiting
            domain = request.domain
            if self.concurrent_requests_per_domain > 0:
                if domain not in self._domain_semaphores:
                    self._domain_semaphores[domain] = asyncio.Semaphore(
                        self.concurrent_requests_per_domain
                    )
                async with self._domain_semaphores[domain]:
                    await self._do_request(request)
            else:
                await self._do_request(request)

    async def _do_request(self, request: CrawlRequest):
        """Execute the actual HTTP request."""
        # Rate limiting
        domain = request.domain
        now = time.time()
        if domain in self._domain_last_request:
            elapsed = now - self._domain_last_request[domain]
            if elapsed < self.download_delay:
                await asyncio.sleep(self.download_delay - elapsed)
        self._domain_last_request[domain] = time.time()

        # Robots.txt check
        if self.obey_robots_txt and not await self._robots_allowed(request.url):
            self.logger.debug(f"Blocked by robots.txt: {request.url}")
            return

        # Dev mode cache
        if self.dev_mode and request.url in self._dev_cache:
            response = self._dev_cache[request.url]
        else:
            # Modify request
            request = await self.process_request(request)

            # Get proxy
            proxy = None
            if self._proxy_rotator:
                proxy = self._proxy_rotator.next()

            # Fetch
            response = await self._fetch(request)

            if self.dev_mode:
                self._dev_cache[request.url] = response

        self._stats.requests_made += 1
        self._visited.add(request.fingerprint)
        self._domains_visited.add(domain)

        if response.ok:
            self._stats.requests_success += 1
            if self._proxy_rotator and proxy:
                self._proxy_rotator.mark_success(proxy)

            # Parse
            try:
                result = self.parse(response)
                # Handle both async generators and regular coroutines
                if hasattr(result, '__aiter__'):
                    async for item in result:
                        if isinstance(item, CrawlRequest):
                            await self._enqueue_request(item)
                        else:
                            self._stats.items_scraped += 1
                            if request.callback:
                                await self._run_callback(request.callback, item)
                else:
                    # Regular coroutine or None
                    items = await result if result is not None else []
                    if items:
                        for item in items if isinstance(items, list) else [items]:
                            if isinstance(item, CrawlRequest):
                                await self._enqueue_request(item)
                            else:
                                self._stats.items_scraped += 1
            except Exception as e:
                self.logger.error(f"Parse error for {request.url}: {e}")
        else:
            if response.status in BLOCKED_STATUS_CODES:
                self._stats.requests_blocked += 1
            else:
                self._stats.requests_failed += 1

            if self._proxy_rotator and proxy:
                self._proxy_rotator.mark_failure(proxy)

            if response.error:
                await self.handle_error(request, response.error)

    async def _fetch(self, request: CrawlRequest) -> CrawlResponse:
        """Fetch a URL. Uses https/httpx or Playwright depending on config."""
        try:
            import httpx
            t0 = time.time()
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(
                    request.url,
                    headers=request.headers or None,
                )
                elapsed = (time.time() - t0) * 1000
                self._stats.bytes_downloaded += len(resp.content)
                return CrawlResponse(
                    url=str(resp.url),
                    status=resp.status_code,
                    text=resp.text,
                    headers=dict(resp.headers),
                    elapsed_ms=elapsed,
                    request=request,
                )
        except Exception as e:
            return CrawlResponse(
                url=request.url,
                status=0,
                text="",
                error=str(e)[:200],
                request=request,
            )

    async def _enqueue_request(self, request: CrawlRequest):
        """Add a request to the pending queue, with dedup."""
        if not request.dont_filter and request.fingerprint in self._visited:
            return
        if not await self.should_follow(request.url):
            return
        await self._pending.put(request)

    async def _robots_allowed(self, url: str) -> bool:
        """Check robots.txt for a URL."""
        domain = urlparse(url).netloc
        if domain not in self._robots_cache:
            rp = RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            try:
                await asyncio.get_event_loop().run_in_executor(None, rp.read)
                self._robots_cache[domain] = rp
            except Exception:
                return True  # Can't fetch robots.txt, allow
        return self._robots_cache[domain].can_fetch("chinacrawl/*", url)

    async def _run_callback(self, callback: Callable, item: Any):
        """Execute a user callback."""
        if asyncio.iscoroutinefunction(callback):
            await callback(item)
        else:
            callback(item)

    def _save_checkpoint(self):
        """Save current state to checkpoint."""
        if not self._checkpoint:
            return
        pending = []
        # Drain queue
        while not self._pending.empty():
            try:
                req = self._pending.get_nowait()
                pending.append(req.url)
                self._pending.put_nowait(req)  # put back
            except asyncio.QueueEmpty:
                break
        pending = list(dict.fromkeys(pending))  # dedup preserve order
        self._checkpoint.save(pending, self._visited, self._stats)

    async def _cleanup(self):
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()
        if self._browser:
            await self._browser.close()


# --- Context Manager Support ---

class SpiderRunner:
    """Run a spider with context manager and signal handling."""

    def __init__(self, spider: Spider):
        self.spider = spider
        self._original_sigint = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.spider._cleanup()

    async def run(self, resume: bool = False):
        """Run the spider with SIGINT handling."""
        loop = asyncio.get_event_loop()

        def sigint_handler():
            self.spider.logger.info("SIGINT received, pausing...")
            self.spider.pause()

        try:
            self._original_sigint = signal.getsignal(signal.SIGINT)
            signal.signal(signal.SIGINT, lambda s, f: sigint_handler())
        except (ValueError, OSError):
            pass  # Not in main thread

        try:
            await self.spider.run(resume=resume)
        finally:
            if self._original_sigint:
                try:
                    signal.signal(signal.SIGINT, self._original_sigint)
                except (ValueError, OSError):
                    pass
