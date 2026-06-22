# chinacrawl/core/anti_detect.py - Shared anti-detection
# Platform adapters can override CONTEXT_OVERRIDES and ANTI_DETECT_JS.

import random

# ━━━ Common anti-detection JavaScript (platform-neutral base) ━━━
ANTI_DETECT_JS = """
(function() {
    'use strict';
    
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true
    });
    delete Object.getPrototypeOf(navigator).webdriver;
    
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
    
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = function(parameters) {
        if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission });
        }
        return originalQuery.call(this, parameters);
    };
    
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
        configurable: true
    });
    
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en'],
        configurable: true
    });
    
    if (window.callPhantom || window._phantom) {
        delete window.callPhantom;
        delete window._phantom;
    }
    
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
        configurable: true
    });
    
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
        configurable: true
    });
    
    if (navigator.connection) {
        Object.defineProperty(navigator.connection, 'rtt', {
            get: () => 50 + Math.floor(Math.random() * 50),
            configurable: true
        });
        Object.defineProperty(navigator.connection, 'effectiveType', {
            get: () => '4g',
            configurable: true
        });
    }
    
    // Canvas fingerprint randomization
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const context = this.getContext('2d');
        if (context) {
            const imageData = context.getImageData(0, 0, this.width, this.height);
            if (imageData.data.length > 3) {
                imageData.data[3] = imageData.data[3] ^ 1;
                context.putImageData(imageData, 0, 0);
            }
        }
        return originalToDataURL.apply(this, arguments);
    };
    
    // WebGL fingerprint
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) { return 'Qualcomm'; }
        if (parameter === 37446) { return 'Adreno (TM) 750'; }
        return getParameter.call(this, parameter);
    };
    
    // Hide Playwright markers
    delete window.__playwright;
    delete window.__pw_manual;
    delete window.__PW_inspect;
    
    console.log('[ChinaCrawl] Anti-detect injected');
})();
"""

# ━━━ Default context overrides (mobile Android profile) ━━━
CONTEXT_OVERRIDES = {
    "timezone_id": "Asia/Shanghai",
    "locale": "zh-CN",
    "viewport": {"width": 412, "height": 915},
    "user_agent": (
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.6778.135 Mobile Safari/537.36"
    ),
    "permissions": ["geolocation"],
    "geolocation": {"latitude": 31.2304, "longitude": 121.4737},
    "color_scheme": "light",
    "device_scale_factor": 2.75,
    "is_mobile": True,
    "has_touch": True,
}


# ━━━ Human behavior simulation ━━━
def random_scroll_steps(page_height: int, viewport_height: int = 915) -> list:
    """Generate random scroll steps to simulate human browsing."""
    steps = []
    current = 0
    while current < page_height:
        step = random.randint(200, 600)
        current += step
        if current > page_height:
            current = page_height
        steps.append(current)
    return steps


def random_delay(min_ms: int = 800, max_ms: int = 4000) -> int:
    """Random delay in milliseconds."""
    return random.randint(min_ms, max_ms)


def random_touch_events(page) -> None:
    """Dispatch random touch events to simulate mobile scrolling."""
    x = random.randint(50, 360)
    y_start = random.randint(200, 600)
    y_end = y_start - random.randint(100, 400)
    
    page.touchscreen.tap(x, y_start)
    page.evaluate("""([x, yStart, yEnd]) => {
        const target = document.elementFromPoint(x, yStart) || document.body;
        const touchStart = new TouchEvent('touchstart', {
            touches: [new Touch({ identifier: 1, target, clientX: x, clientY: yStart })],
            bubbles: true, cancelable: true
        });
        target.dispatchEvent(touchStart);
        const touchMove = new TouchEvent('touchmove', {
            touches: [new Touch({ identifier: 1, target, clientX: x, clientY: yStart - 50 })],
            bubbles: true, cancelable: true
        });
        target.dispatchEvent(touchMove);
        const touchEnd = new TouchEvent('touchend', {
            touches: [], bubbles: true, cancelable: true
        });
        target.dispatchEvent(touchEnd);
    }""", [x, y_start, y_end])
