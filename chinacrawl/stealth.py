"""Unified Anti-Detection & Fingerprint Engine.

Inspired by Scrapling's stealth layer. Provides:
- Random browser fingerprint generation per session
- curl_cffi TLS fingerprint evasion (bypasses JA3 detection)
- Canvas/WebGL/Audio noise injection JS
- Human behavior simulation (scroll, mouse, typing delays)
- Shared across Douyin, Pinduoduo, and future adapters.

XHLS v3.3 | Xiao Hei Learning System
Layer L3.5: Stealth Engine
"""

import hashlib
import random
import string
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple


# ============================================================
# Browser Fingerprint Generator
# ============================================================

# Realistic Chrome versions on Windows
_CHROME_VERSIONS = [
    "131.0.0.0",
    "130.0.0.0",
    "129.0.0.0",
    "128.0.0.0",
    "127.0.0.0",
]

# Common screen resolutions in China
_SCREEN_RESOLUTIONS = [
    (1920, 1080),
    (2560, 1440),
    (1366, 768),
    (1536, 864),
    (1680, 1050),
]

# Common GPU renderers (Windows)
_GPU_RENDERERS = [
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002504) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 (0x00002882) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 (0x00002184) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 (0x00002484) Direct3D11 vs_5_0 ps_5_0, D3D11)",
]

# Common languages
_LANGUAGES = [
    ["zh-CN", "zh", "en-US", "en"],
    ["zh-CN", "zh", "en"],
    ["en-US", "en", "zh-CN", "zh"],
    ["zh-CN", "zh", "ja", "en-US", "en"],
]

# Common hardware concurrency
_HW_CONCURRENCY = [4, 6, 8, 12, 16]

# Common device memory (GB)
_DEVICE_MEMORY = [4, 8, 16, 32]

# Common timezones in China
_TIMEZONES = ["Asia/Shanghai", "Asia/Chongqing", "Asia/Harbin", "Asia/Urumqi"]


@dataclass
class BrowserFingerprint:
    """Randomized browser fingerprint for a scraping session."""

    chrome_version: str = ""
    user_agent: str = ""
    platform: str = "Win32"
    languages: List[str] = field(default_factory=list)
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    hw_concurrency: int = 8
    device_memory: int = 8
    timezone: str = "Asia/Shanghai"
    gpu_renderer: str = ""
    vendor: str = "Google Inc."
    vendor_sub: str = ""
    product_sub: str = "20030107"

    @classmethod
    def randomize(cls) -> "BrowserFingerprint":
        """Generate a random, plausible fingerprint."""
        chrome_ver = random.choice(_CHROME_VERSIONS)
        major = chrome_ver.split(".")[0]
        res = random.choice(_SCREEN_RESOLUTIONS)

        fp = cls(
            chrome_version=chrome_ver,
            user_agent=(
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_ver} Safari/537.36"
            ),
            languages=random.choice(_LANGUAGES),
            screen_width=res[0],
            screen_height=res[1],
            hw_concurrency=random.choice(_HW_CONCURRENCY),
            device_memory=random.choice(_DEVICE_MEMORY),
            timezone=random.choice(_TIMEZONES),
            gpu_renderer=random.choice(_GPU_RENDERERS),
        )
        return fp

    def fingerprint_hash(self) -> str:
        """Deterministic hash of this fingerprint for session tracking."""
        data = f"{self.user_agent}|{self.screen_width}x{self.screen_height}|{self.hw_concurrency}|{self.gpu_renderer}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]

    def to_context_config(self) -> dict:
        """Convert to Playwright browser context configuration."""
        return {
            "user_agent": self.user_agent,
            "viewport": {"width": self.screen_width, "height": self.screen_height},
            "locale": self.languages[0] if self.languages else "zh-CN",
            "timezone_id": self.timezone,
            "color_scheme": random.choice(["light", "dark"]),
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
        }


# ============================================================
# Anti-Detection JavaScript Injections
# ============================================================

def generate_stealth_js(fp: Optional[BrowserFingerprint] = None) -> str:
    """Generate anti-detection JavaScript payload.

    Covers: webdriver, chrome.runtime, permissions, plugins,
    WebGL fingerprint, Canvas noise, AudioContext noise,
    and common automation detection vectors.

    :param fp: BrowserFingerprint for consistent values (random if None)
    """
    if fp is None:
        fp = BrowserFingerprint.randomize()

    # Escape values for JS injection
    hw_concurrency = fp.hw_concurrency
    device_memory = fp.device_memory
    platform = fp.platform
    languages = str(fp.languages)
    vendor = fp.vendor
    gpu_unmasked = fp.gpu_renderer.split("(")[-1].rstrip(")") if "(" in fp.gpu_renderer else "Google Inc. (NVIDIA)"
    gpu_vendor = "NVIDIA Corporation" if "NVIDIA" in fp.gpu_renderer else "Google Inc. (Intel)"

    return f"""// === ChinaCrawl Stealth v2.0 ===
(function() {{
    'use strict';

    // -- WebDriver hiding --
    Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
    delete Object.getPrototypeOf(navigator).webdriver;

    // -- Chrome runtime --
    window.chrome = {{
        runtime: {{}},
        loadTimes: function() {{}},
        csi: function() {{}},
        app: {{}}
    }};

    // -- Permissions --
    const _origQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = function(parameters) {{
        if (parameters.name === 'notifications') {{
            return Promise.resolve({{ state: Notification.permission }});
        }}
        return _origQuery.call(this, parameters);
    }};

    // -- Plugins (random count 3-5) --
    const pluginCount = {random.randint(3, 5)};
    const pluginsArray = Array.from({{length: pluginCount}}, (_, i) => ({{
        name: 'Chrome PDF Plugin',
        filename: 'internal-pdf-viewer',
        description: 'Portable Document Format',
        length: 1
    }}));
    Object.defineProperty(navigator, 'plugins', {{
        get: () => pluginsArray,
        configurable: true
    }});
    Object.defineProperty(navigator, 'mimeTypes', {{
        get: () => pluginsArray,
        configurable: true
    }});

    // -- Languages --
    Object.defineProperty(navigator, 'languages', {{
        get: () => {languages},
        configurable: true
    }});
    Object.defineProperty(navigator, 'language', {{
        get: () => '{fp.languages[0] if fp.languages else 'zh-CN'}',
        configurable: true
    }});

    // -- Platform --
    Object.defineProperty(navigator, 'platform', {{
        get: () => '{platform}',
        configurable: true
    }});

    // -- Hardware --
    Object.defineProperty(navigator, 'hardwareConcurrency', {{
        get: () => {hw_concurrency},
        configurable: true
    }});
    Object.defineProperty(navigator, 'deviceMemory', {{
        get: () => {device_memory},
        configurable: true
    }});

    // -- Vendor --
    Object.defineProperty(navigator, 'vendor', {{
        get: () => '{vendor}',
        configurable: true
    }});

    // -- Connection info --
    if (navigator.connection) {{
        Object.defineProperty(navigator.connection, 'rtt', {{
            get: () => {random.randint(50, 150)},
            configurable: true
        }});
    }}

    // -- WebGL fingerprint spoofing --
    const getParameterProto = WebGLRenderingContext.prototype.getParameter;
    const getParameter2Proto = WebGL2RenderingContext.prototype.getParameter;
    const spoofGetParameter = function(orig) {{
        return function(parameter) {{
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) return '{gpu_vendor}';
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) return '{gpu_unmasked}';
            return orig.call(this, parameter);
        }};
    }};
    WebGLRenderingContext.prototype.getParameter = spoofGetParameter(getParameterProto);
    WebGL2RenderingContext.prototype.getParameter = spoofGetParameter(getParameter2Proto);

    // -- Canvas fingerprint noise --
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    const noiseCanvas = function(canvas) {{
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        const imageData = origGetImageData.call(ctx, 0, 0, canvas.width, canvas.height);
        if (!imageData) return;
        // Add subtle noise to ~1% of pixels
        for (let i = 0; i < imageData.data.length; i += {random.randint(300, 500)}) {{
            imageData.data[i] = imageData.data[i] ^ {random.randint(1, 3)};
        }}
        ctx.putImageData(imageData, 0, 0);
    }};
    HTMLCanvasElement.prototype.toDataURL = function() {{
        noiseCanvas(this);
        return origToDataURL.apply(this, arguments);
    }};
    HTMLCanvasElement.prototype.toBlob = function() {{
        noiseCanvas(this);
        return origToBlob.apply(this, arguments);
    }};

    // -- AudioContext fingerprint noise --
    const origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function() {{
        const data = origGetChannelData.call(this);
        // Add tiny noise to audio fingerprint
        for (let i = 0; i < Math.min(data.length, 10); i++) {{
            data[i] += {random.uniform(0.0000001, 0.000001):.10f};
        }}
        return data;
    }};

    // -- PhantomJS cleanup --
    if (window.callPhantom || window._phantom || window.__phantomas) {{
        delete window.callPhantom;
        delete window._phantom;
        delete window.__phantomas;
    }}

    console.debug('[ChinaCrawl] Stealth v2.0 injected');
}})();
"""


# ============================================================
# curl_cffi TLS Fingerprint Adapter
# ============================================================

class TLSFetcher:
    """HTTP client with JA3/JA4 TLS fingerprint randomization via curl_cffi.

    Falls back to httpx when curl_cffi is not installed.
    Bypasses TLS-based bot detection on Cloudflare, Akamai, etc.
    """

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self.proxy = proxy
        self.timeout = timeout
        self._session = None
        self._use_cffi = False
        self._init_session()

    def _init_session(self):
        """Try to initialize curl_cffi session, fall back to httpx."""
        try:
            from curl_cffi import requests as cffi_requests
            self._session = cffi_requests.Session()
            self._use_cffi = True
        except ImportError:
            import httpx
            self._session = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
            )

    def get(self, url: str, headers: Optional[Dict] = None,
            impersonate: str = "chrome131") -> "TLSResponse":
        """GET request with browser TLS impersonation.

        :param url: Target URL
        :param headers: Custom headers
        :param impersonate: Browser to impersonate:
            chrome131, chrome130, chrome129, chrome120,
            edge101, safari17_0, firefox133, etc.
        """
        default_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if headers:
            default_headers.update(headers)

        if self._use_cffi:
            return self._fetch_cffi(url, default_headers, impersonate)
        else:
            return self._fetch_httpx(url, default_headers)

    def _fetch_cffi(self, url: str, headers: Dict, impersonate: str) -> "TLSResponse":
        try:
            from curl_cffi import requests as cffi_requests
            resp = self._session.get(
                url,
                headers=headers,
                impersonate=impersonate,
                timeout=self.timeout,
                proxy=self.proxy,
            )
            return TLSResponse(
                status=resp.status_code,
                text=resp.text,
                headers=dict(resp.headers),
                url=str(resp.url),
                elapsed_ms=int(resp.elapsed.total_seconds() * 1000),
            )
        except Exception as e:
            return TLSResponse(status=0, text="", headers={}, url=url, elapsed_ms=0, error=str(e))

    def _fetch_httpx(self, url: str, headers: Dict) -> "TLSResponse":
        import httpx
        try:
            t = httpx.HTTPTransport(proxy=self.proxy) if self.proxy else None
            with httpx.Client(transport=t, timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                return TLSResponse(
                    status=resp.status_code,
                    text=resp.text,
                    headers=dict(resp.headers),
                    url=str(resp.url),
                    elapsed_ms=int(resp.elapsed.total_seconds() * 1000),
                )
        except Exception as e:
            return TLSResponse(status=0, text="", headers={}, url=url, elapsed_ms=0, error=str(e))

    def post(self, url: str, data: Optional[Dict] = None, json: Optional[Dict] = None,
             headers: Optional[Dict] = None, impersonate: str = "chrome131") -> "TLSResponse":
        default_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
        }
        if headers:
            default_headers.update(headers)

        if self._use_cffi:
            try:
                resp = self._session.post(
                    url,
                    data=data,
                    json=json,
                    headers=default_headers,
                    impersonate=impersonate,
                    timeout=self.timeout,
                    proxy=self.proxy,
                )
                return TLSResponse(
                    status=resp.status_code,
                    text=resp.text,
                    headers=dict(resp.headers),
                    url=str(resp.url),
                    elapsed_ms=int(resp.elapsed.total_seconds() * 1000),
                )
            except Exception as e:
                return TLSResponse(status=0, text="", headers={}, url=url, elapsed_ms=0, error=str(e))
        else:
            import httpx
            try:
                t = httpx.HTTPTransport(proxy=self.proxy) if self.proxy else None
                with httpx.Client(transport=t, timeout=self.timeout, follow_redirects=True) as client:
                    resp = client.post(url, data=data, json=json, headers=default_headers)
                    return TLSResponse(
                        status=resp.status_code,
                        text=resp.text,
                        headers=dict(resp.headers),
                        url=str(resp.url),
                        elapsed_ms=int(resp.elapsed.total_seconds() * 1000),
                    )
            except Exception as e:
                return TLSResponse(status=0, text="", headers={}, url=url, elapsed_ms=0, error=str(e))


@dataclass
class TLSResponse:
    """Response wrapper for TLSFetcher, compatible with both backends."""
    status: int
    text: str
    headers: Dict[str, str]
    url: str
    elapsed_ms: int
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 400

    @property
    def content(self) -> bytes:
        return self.text.encode("utf-8")


# ============================================================
# Human Behavior Simulation
# ============================================================


class HumanBehavior:
    """Generates realistic human-like interaction patterns."""

    @staticmethod
    def random_delay(min_ms: int = 500, max_ms: int = 3000) -> float:
        """Random delay in seconds, weighted toward shorter delays."""
        return random.triangular(min_ms, max_ms, min_ms * 1.5) / 1000.0

    @staticmethod
    def scroll_steps(page_height: int, viewport_height: int = 1080) -> List[int]:
        """Generate random scroll positions simulating human browsing."""
        steps = []
        current = 0
        while current < page_height:
            step = random.randint(200, 700)
            # Occasionally scroll back up a bit
            if random.random() < 0.1 and current > 500:
                current -= random.randint(100, 300)
            current += step
            if current > page_height:
                current = page_height
            steps.append(current)
        return steps

    @staticmethod
    def mouse_path(start: Tuple[int, int], end: Tuple[int, int],
                   steps: int = 10) -> List[Tuple[int, int]]:
        """Generate a curved mouse movement path using bezier-like interpolation."""
        points = []
        # Control point offset for natural curve
        cx = start[0] + (end[0] - start[0]) // 2 + random.randint(-50, 50)
        cy = start[1] + (end[1] - start[1]) // 2 + random.randint(-30, 30)

        for i in range(steps + 1):
            t = i / steps
            # Quadratic bezier
            x = int((1 - t) ** 2 * start[0] + 2 * (1 - t) * t * cx + t ** 2 * end[0])
            y = int((1 - t) ** 2 * start[1] + 2 * (1 - t) * t * cy + t ** 2 * end[1])
            points.append((x, y))
        return points

    @staticmethod
    def typing_delay(text_length: int) -> float:
        """Simulate human typing speed (seconds per character)."""
        # Average typing speed: ~40 WPM = ~300ms per character
        base = random.gauss(0.15, 0.05)
        return max(0.05, base) * text_length + random.uniform(0, 0.5)


# ============================================================
# Convenience
# ============================================================

def new_stealth_session() -> Tuple[BrowserFingerprint, str, Dict]:
    """Create a new stealth session with random fingerprint.

    Returns:
        (fingerprint, stealth_js, context_config)
    """
    fp = BrowserFingerprint.randomize()
    js = generate_stealth_js(fp)
    config = fp.to_context_config()
    return fp, js, config


# Check if curl_cffi is available
try:
    from curl_cffi import requests as _cffi_requests  # noqa: F401
    TLS_AVAILABLE = True
except ImportError:
    TLS_AVAILABLE = False


"""
TLS Fingerprint Rotation + Session Binding for ChinaCrawl stealth layer.
Appended to stealth.py during build.
"""

TLS_PROFILES = {
    "chrome_131": {
        "ja3": "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21-41,29-23-24,0",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "impersonate": "chrome131",
    },
    "chrome_130": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "impersonate": "chrome130",
    },
    "chrome_124": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "impersonate": "chrome124",
    },
    "edge_131": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "impersonate": "edge101",
    },
    "firefox_133": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "impersonate": "firefox133",
    },
    "safari_18": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
        "impersonate": "safari18_0",
    },
    "mobile_chrome": {
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36",
        "impersonate": "chrome131",
    },
    "mobile_safari": {
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "impersonate": "safari18_0",
    },
}


def random_tls_profile(exclude=None):
    """Get a random TLS profile for fingerprint rotation."""
    import random as _random
    keys = list(TLS_PROFILES.keys())
    if exclude:
        keys = [k for k in keys if k not in exclude]
    if not keys:
        keys = ["chrome_131"]
    name = _random.choice(keys)
    return {"name": name, **TLS_PROFILES[name]}


class TLSRotator:
    """Rotates TLS fingerprints per session to avoid detection.

    Usage:
        rotator = TLSRotator()
        profile = rotator.next()
        fetcher = TLSFetcher(impersonate=profile["impersonate"])
        rotator.mark_success(profile["name"])
    """

    def __init__(self, profiles=None):
        self._profiles = profiles or list(TLS_PROFILES.keys())
        self._idx = 0
        self._success = {}
        self._fail = {}

    def next(self):
        """Get next profile in rotation."""
        name = self._profiles[self._idx % len(self._profiles)]
        self._idx += 1
        return {"name": name, **TLS_PROFILES[name]}

    def random(self, exclude=None):
        """Get random profile."""
        import random as _random
        names = list(TLS_PROFILES.keys())
        if exclude:
            names = [n for n in names if n not in exclude]
        name = _random.choice(names) if names else "chrome_131"
        return {"name": name, **TLS_PROFILES[name]}

    def mark_success(self, name):
        self._success[name] = self._success.get(name, 0) + 1

    def mark_failure(self, name):
        self._fail[name] = self._fail.get(name, 0) + 1

    def best_profile(self):
        """Get profile with best success rate."""
        best = "chrome_131"
        best_ratio = -1
        for name in self._profiles:
            s = self._success.get(name, 0)
            f = self._fail.get(name, 0)
            total = s + f
            if total > 0 and s / total > best_ratio:
                best_ratio = s / total
                best = name
        return best


class StealthSession:
    """Binds a browser fingerprint, TLS profile, and cookie jar together.

    Ensures consistent identity across requests to avoid detection.
    """

    def __init__(self, name="default"):
        self.name = name
        self.fingerprint = BrowserFingerprint.randomize()
        self.tls_profile = random_tls_profile()
        self.stealth_js = generate_stealth_js(self.fingerprint)
        self.context_config = self.fingerprint.to_context_config()
        self._cookies = {}
        import time
        self._created_at = time.time()

    def get_headers(self, referer=""):
        """Get consistent HTTP headers for this session."""
        headers = {
            "User-Agent": self.tls_profile["user_agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            headers["Referer"] = referer
        return headers

    def age_seconds(self):
        import time
        return time.time() - self._created_at

    def __repr__(self):
        return (f"StealthSession(name={self.name!r}, "
                f"tls={self.tls_profile['name']}, "
                f"fp={self.fingerprint.fingerprint_hash()})")


_sessions = {}


def get_session(name="default"):
    """Get or create a named stealth session."""
    if name not in _sessions:
        _sessions[name] = StealthSession(name)
    return _sessions[name]


def rotate_session(name="default"):
    """Force-create a new stealth session."""
    _sessions[name] = StealthSession(name)
    return _sessions[name]

