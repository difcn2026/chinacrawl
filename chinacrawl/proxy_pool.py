"""Proxy Pool Manager with health checking and rotation.

Supports:
- Static proxy lists (HTTP/HTTPS/SOCKS5)
- Proxy health checking with test URLs
- Weighted random rotation
- Auto-expiry of dead proxies
- Residential/mobile proxy integration

XHLS v3.4 | Xiao Hei Learning System
Layer L3.7: Proxy Engine
"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse

log = logging.getLogger("chinacrawl.proxy")


# ============================================================
# Types
# ============================================================

class ProxyProtocol(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyHealth(Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    SLOW = "slow"        # Slower than threshold but still working
    DEAD = "dead"        # Failed health check
    BANNED = "banned"    # Got CAPTCHA/block page


@dataclass
class Proxy:
    """A single proxy entry with health tracking."""

    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: str = ""
    password: str = ""
    health: ProxyHealth = ProxyHealth.UNKNOWN
    latency_ms: int = 0
    fail_count: int = 0
    success_count: int = 0
    last_check: float = 0.0
    last_used: float = 0.0
    tags: List[str] = field(default_factory=list)
    region: str = ""         # Geographic region hint
    source: str = ""         # Where this proxy came from

    @property
    def url(self) -> str:
        """Full proxy URL."""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"

    @property
    def key(self) -> str:
        """Unique identifier."""
        return f"{self.protocol.value}://{self.host}:{self.port}"

    @property
    def is_healthy(self) -> bool:
        return self.health in (ProxyHealth.HEALTHY, ProxyHealth.SLOW)

    @property
    def weight(self) -> float:
        """Score for weighted selection (higher = better)."""
        if self.health == ProxyHealth.DEAD or self.health == ProxyHealth.BANNED:
            return 0.0
        base = {
            ProxyHealth.HEALTHY: 10.0,
            ProxyHealth.SLOW: 5.0,
            ProxyHealth.UNKNOWN: 3.0,
        }.get(self.health, 0.0)
        # Penalize high fail ratio
        total = self.fail_count + self.success_count + 1
        fail_ratio = self.fail_count / total
        return base * (1.0 - fail_ratio)


# ============================================================
# Proxy Pool
# ============================================================

class ProxyPool:
    """Thread-safe proxy pool with auto health checking.

    Usage:
        pool = ProxyPool()
        pool.add("http://127.0.0.1:8080")
        pool.add("socks5://user:pass@proxy.example.com:1080")

        proxy = pool.get()          # Weighted random
        proxy = pool.get_best()     # Best latency
        await pool.health_check()   # Check all proxies
    """

    # Common test URLs for health checking
    TEST_URLS = {
        "global": [
            "https://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "https://www.baidu.com",
            "https://www.taobao.com",
        ],
        "china": [
            "https://www.baidu.com",
            "https://www.taobao.com",
            "https://www.jd.com",
            "https://www.douyin.com",
        ],
        "ecommerce": [
            "https://www.taobao.com",
            "https://www.jd.com",
            "https://mobile.yangkeduo.com",
        ],
    }

    # Response patterns indicating we're blocked
    BLOCK_PATTERNS = [
        "访问过于频繁",
        "请输入验证码",
        "验证码",
        "captcha",
        "Access Denied",
        "403 Forbidden",
        "您的IP已被",
        "滑块验证",
        "人机验证",
    ]

    def __init__(self, check_interval: int = 300,
                 max_fails: int = 5,
                 latency_threshold_ms: int = 3000):
        self._proxies: Dict[str, Proxy] = {}
        self._check_interval = check_interval
        self._max_fails = max_fails
        self._latency_threshold_ms = latency_threshold_ms
        self._lock = asyncio.Lock()

    # --- CRUD ---

    def add(self, proxy_url: str, tags: List[str] = None,
            region: str = "", source: str = "") -> Optional[Proxy]:
        """Add a proxy by URL string."""
        try:
            p = self._parse_url(proxy_url)
            p.tags = tags or []
            p.region = region
            p.source = source
            self._proxies[p.key] = p
            return p
        except ValueError as e:
            log.warning("Invalid proxy URL '%s': %s", proxy_url, e)
            return None

    def add_raw(self, host: str, port: int, protocol: ProxyProtocol = ProxyProtocol.HTTP,
                username: str = "", password: str = "", **kwargs) -> Proxy:
        """Add a proxy by components."""
        p = Proxy(
            host=host, port=port, protocol=protocol,
            username=username, password=password,
            tags=kwargs.get("tags", []),
            region=kwargs.get("region", ""),
            source=kwargs.get("source", ""),
        )
        self._proxies[p.key] = p
        return p

    def remove(self, key: str) -> bool:
        """Remove a proxy by key."""
        if key in self._proxies:
            del self._proxies[key]
            return True
        return False

    def clear(self):
        """Remove all proxies."""
        self._proxies.clear()

    # --- Selection ---

    def get(self, protocol: Optional[ProxyProtocol] = None,
            tags: List[str] = None, require_healthy: bool = True) -> Optional[Proxy]:
        """Weighted random proxy selection.

        Args:
            protocol: Filter by protocol
            tags: Filter by tags (ANY match)
            require_healthy: Only return healthy proxies
        """
        candidates = list(self._proxies.values())

        if require_healthy:
            candidates = [p for p in candidates if p.is_healthy]

        if protocol:
            candidates = [p for p in candidates if p.protocol == protocol]

        if tags:
            candidates = [p for p in candidates
                         if any(t in p.tags for t in tags)]

        if not candidates:
            # Fallback: return any proxy even if unhealthy
            all_proxies = list(self._proxies.values())
            if all_proxies:
                log.warning("No healthy proxies, falling back to any")
                return random.choice(all_proxies)
            return None

        # Weighted random selection
        weights = [p.weight for p in candidates]
        total = sum(weights)
        if total <= 0:
            return random.choice(candidates)

        r = random.uniform(0, total)
        cumulative = 0
        for p, w in zip(candidates, weights):
            cumulative += w
            if r <= cumulative:
                p.last_used = time.time()
                return p

        return candidates[-1]

    def get_best(self, protocol: Optional[ProxyProtocol] = None) -> Optional[Proxy]:
        """Get the proxy with best (lowest) latency."""
        candidates = [p for p in self._proxies.values()
                     if p.is_healthy and p.latency_ms > 0]
        if protocol:
            candidates = [p for p in candidates if p.protocol == protocol]
        if candidates:
            return min(candidates, key=lambda p: p.latency_ms)
        return self.get(protocol=protocol)

    def get_all(self, healthy_only: bool = False) -> List[Proxy]:
        """Get all proxies."""
        proxies = list(self._proxies.values())
        if healthy_only:
            proxies = [p for p in proxies if p.is_healthy]
        return sorted(proxies, key=lambda p: p.weight, reverse=True)

    def get_playwright_config(self, proxy: Proxy) -> dict:
        """Convert a Proxy to Playwright proxy config."""
        config = {
            "server": f"{proxy.protocol.value}://{proxy.host}:{proxy.port}",
        }
        if proxy.username:
            config["username"] = proxy.username
            config["password"] = proxy.password
        return config

    # --- Health Check ---

    async def health_check(self, test_urls: List[str] = None,
                           region: str = "china") -> Dict[str, int]:
        """Check health of all proxies.

        Returns:
            Dict with counts: {healthy, slow, dead, banned, total}
        """
        test_urls = test_urls or self.TEST_URLS.get(region, self.TEST_URLS["china"])

        results = {"healthy": 0, "slow": 0, "dead": 0, "banned": 0, "total": 0}

        async with self._lock:
            proxies = list(self._proxies.values())
            results["total"] = len(proxies)

        # Check in parallel
        tasks = [
            self._check_one(proxy, random.choice(test_urls))
            for proxy in proxies
        ]

        checked = await asyncio.gather(*tasks, return_exceptions=True)

        async with self._lock:
            for proxy, result in zip(proxies, checked):
                if isinstance(result, Exception):
                    proxy.health = ProxyHealth.DEAD
                    proxy.fail_count += 1
                    results["dead"] += 1
                    continue

                health, latency = result
                proxy.health = health
                proxy.latency_ms = latency
                proxy.last_check = time.time()

                if health == ProxyHealth.HEALTHY:
                    proxy.success_count += 1
                    results["healthy"] += 1
                elif health == ProxyHealth.SLOW:
                    results["slow"] += 1
                elif health == ProxyHealth.BANNED:
                    proxy.fail_count += 1
                    results["banned"] += 1
                else:
                    proxy.fail_count += 1
                    results["dead"] += 1

        # Remove persistently dead proxies
        async with self._lock:
            dead = [k for k, p in self._proxies.items()
                   if p.fail_count >= self._max_fails and p.health == ProxyHealth.DEAD]
            for k in dead:
                del self._proxies[k]

        return results

    async def _check_one(self, proxy: Proxy,
                         test_url: str) -> Tuple[ProxyHealth, int]:
        """Check a single proxy's health."""
        try:
            import httpx
            start = time.time()
            async with httpx.AsyncClient(
                proxy=proxy.url,
                timeout=10.0,
                follow_redirects=True,
            ) as client:
                resp = await client.get(
                    test_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                      "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
                    },
                )
                latency = int((time.time() - start) * 1000)

                # Check for block signals
                text = resp.text[:5000].lower()
                for pattern in self.BLOCK_PATTERNS:
                    if pattern.lower() in text:
                        return ProxyHealth.BANNED, latency

                if resp.status_code == 200:
                    if latency > self._latency_threshold_ms:
                        return ProxyHealth.SLOW, latency
                    return ProxyHealth.HEALTHY, latency

                return ProxyHealth.DEAD, latency

        except Exception:
            return ProxyHealth.DEAD, 0

    # --- Helpers ---

    @staticmethod
    def _parse_url(url: str) -> Proxy:
        """Parse a proxy URL string into a Proxy object."""
        parsed = urlparse(url.strip())

        protocol_map = {
            "http": ProxyProtocol.HTTP,
            "https": ProxyProtocol.HTTPS,
            "socks5": ProxyProtocol.SOCKS5,
        }

        protocol = protocol_map.get(parsed.scheme)
        if not protocol:
            raise ValueError(f"Unsupported protocol: {parsed.scheme}")

        host = parsed.hostname
        port = parsed.port
        if not host:
            raise ValueError("Missing host")
        if not port:
            port = {"http": 80, "https": 443, "socks5": 1080}.get(
                parsed.scheme, 8080
            )

        return Proxy(
            host=host,
            port=port,
            protocol=protocol,
            username=parsed.username or "",
            password=parsed.password or "",
        )

    @property
    def count(self) -> int:
        return len(self._proxies)

    @property
    def healthy_count(self) -> int:
        return sum(1 for p in self._proxies.values() if p.is_healthy)

    def __len__(self) -> int:
        return self.count

    def __repr__(self) -> str:
        return f"ProxyPool(proxies={self.count}, healthy={self.healthy_count})"


# ============================================================
# Convenience factory
# ============================================================

_default_pool: Optional[ProxyPool] = None


def get_proxy_pool() -> ProxyPool:
    """Get or create the default proxy pool."""
    global _default_pool
    if _default_pool is None:
        _default_pool = ProxyPool()
    return _default_pool
