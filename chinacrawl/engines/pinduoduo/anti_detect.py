# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Pinduoduo Adapter - Anti-Detection Module
# Created: 2026-06-08

"""
浏览器反检测模块.
注入 JS 脚本隐藏 Playwright/Puppeteer 自动化特征.
覆盖: navigator.webdriver, chrome.runtime, permissions, plugins,
       WebGL, Canvas, AudioContext 指纹.

拼多多增强:
  - 更严格的 Canvas/WebGL 指纹伪装
  - 模拟移动设备触摸事件
  - 伪装电池状态 API
  - 伪造 Connection 类型
"""

import random


# ━━━ 注入浏览器的反检测 JavaScript ━━━
ANTI_DETECT_JS = """
// === Anti-Detect v1.0 for ChinaCrawl Pinduoduo Adapter ===
(function() {
    'use strict';

    // 1. 隐藏 webdriver 标记
    Object.defineProperty(navigator, 'webdriver', {
        get: () => false,
        configurable: true
    });
    delete Object.getPrototypeOf(navigator).webdriver;

    // 2. 伪造 chrome.runtime
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };

    // 3. 覆盖权限查询（防止检测自动化）
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = function(parameters) {
        if (parameters.name === 'notifications') {
            return Promise.resolve({ state: Notification.permission });
        }
        return originalQuery.call(this, parameters);
    };

    // 4. 伪造插件数量
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
        configurable: true
    });

    // 5. 伪造 languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en'],
        configurable: true
    });

    // 6. 修补 PhantomJS 特征
    if (window.callPhantom || window._phantom) {
        delete window.callPhantom;
        delete window._phantom;
    }

    // 7. 覆盖 headless 检测
    if (navigator.userAgent.includes('Headless')) {
        Object.defineProperty(navigator, 'userAgent', {
            get: () => 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.135 Mobile Safari/537.36'
        });
    }

    // 8. 伪造平台信息 (Android mobile for PDD)
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Linux armv8l',
        configurable: true
    });

    // 9. 伪造硬件并发数
    Object.defineProperty(navigator, 'hardwareConcurrency', {
        get: () => 8,
        configurable: true
    });

    // 10. 伪造 deviceMemory
    Object.defineProperty(navigator, 'deviceMemory', {
        get: () => 8,
        configurable: true
    });

    // 11. 伪造 maxTouchPoints（PDD 检测移动端）
    Object.defineProperty(navigator, 'maxTouchPoints', {
        get: () => 5,
        configurable: true
    });

    // 12. 伪造 Connection API
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

    // 13. 伪造 Canvas 指纹 (轻度随机化)
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {
        const context = this.getContext('2d');
        if (context) {
            const imageData = context.getImageData(0, 0, this.width, this.height);
            // 微妙地修改第一个像素的 alpha 值
            if (imageData.data.length > 3) {
                imageData.data[3] = imageData.data[3] ^ 1;
                context.putImageData(imageData, 0, 0);
            }
        }
        return originalToDataURL.apply(this, arguments);
    };

    // 14. 伪造 WebGL 指纹
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // UNMASKED_VENDOR_WEBGL / UNMASKED_RENDERER_WEBGL
        if (parameter === 37445) { return 'Qualcomm'; }
        if (parameter === 37446) { return 'Adreno (TM) 750'; }
        return getParameter.call(this, parameter);
    };

    // 15. 隐藏 Playwright 特有标记
    delete window.__playwright;
    delete window.__pw_manual;
    delete window.__PW_inspect;

    console.log('[ChinaCrawl] Anti-detect injected (PDD mode)');
})();
"""


# ━━━ Playwright Context 反检测配置 ━━━
CONTEXT_OVERRIDES = {
    # 时区伪造：东八区
    "timezone_id": "Asia/Shanghai",
    # 语言
    "locale": "zh-CN",
    # 视口（移动端比例 412x915）适配拼多多手机版
    "viewport": {"width": 412, "height": 915},
    # 用户代理（启动时设置，运行时覆盖由 JS 完成）
    "user_agent": (
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.6778.135 Mobile Safari/537.36"
    ),
    # 权限
    "permissions": ["geolocation"],
    # 地理位置（中国上海附近）
    "geolocation": {"latitude": 31.2304, "longitude": 121.4737},
    # 颜色方案
    "color_scheme": "light",
    # 设备缩放
    "device_scale_factor": 2.75,  # Mobile DPR
    # 是移动端
    "is_mobile": True,
    # 有触摸
    "has_touch": True,
}


# ━━━ 人类行为模拟 ━━━
def random_scroll_steps(page_height: int, viewport_height: int = 915) -> list:
    """生成随机滚动步长，模拟人类浏览行为"""
    steps = []
    current = 0
    while current < page_height:
        # 随机滚动 200-600px (移动端短滚动)
        step = random.randint(200, 600)
        current += step
        if current > page_height:
            current = page_height
        steps.append(current)
    return steps


def random_delay(min_ms: int = 800, max_ms: int = 4000) -> int:
    """随机延迟（毫秒），模拟人类操作间隔 (PDD: longer delays)"""
    return random.randint(min_ms, max_ms)


def random_touch_events(page) -> None:
    """在页面上产生随机触摸事件（模拟移动端滑动）"""
    x = random.randint(50, 360)
    y_start = random.randint(200, 600)
    y_end = y_start - random.randint(100, 400)

    page.touchscreen.tap(x, y_start)
    # 模拟滑动
    # dispatch via JS (playwright dispatch_event needs a selector, use evaluate instead)
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
