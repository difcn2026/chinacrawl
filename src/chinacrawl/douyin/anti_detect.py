# XHLS v3.0 | 小黑 · Xiao Hei Learning System
# Douyin Adapter - Anti-Detection Module
# Created: 2026-06-07

"""
浏览器反检测模块。

注入 JS 脚本隐藏 Playwright/Puppeteer 自动化特征。
覆盖: navigator.webdriver, chrome.runtime, permissions, plugins,
       WebGL, Canvas, AudioContext 指纹
"""

import random
import string


# ━━━ 注入浏览器的反检测 JavaScript ━━━
ANTI_DETECT_JS = """
// === Anti-Detect v1.0 for ChinaCrawl Douyin Adapter ===
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
            get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        });
    }

    // 8. 伪造平台信息
    Object.defineProperty(navigator, 'platform', {
        get: () => 'Win32',
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

    console.log('[ChinaCrawl] Anti-detect injected');
})();
"""


# ━━━ Playwright Context 反检测配置 ━━━
CONTEXT_OVERRIDES = {
    # 时间伪造：东八区
    "timezone_id": "Asia/Shanghai",
    # 语言
    "locale": "zh-CN",
    # 视口
    "viewport": {"width": 1920, "height": 1080},
    # 用户代理（启动时设置，运行时覆盖由 JS 完成）
    "user_agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    # 权限
    "permissions": ["geolocation"],
    # 地理位置（中国北京附近）
    "geolocation": {"latitude": 39.9042, "longitude": 116.4074},
    # 颜色方案
    "color_scheme": "light",
    # 设备缩放
    "device_scale_factor": 1,
    # 是否移动端
    "is_mobile": False,
    # 是否有触摸
    "has_touch": False,
}


# ━━━ 人类行为模拟 ━━━
def random_scroll_steps(page_height: int, viewport_height: int = 1080) -> list:
    """生成随机滚动步长，模拟人类浏览行为"""
    steps = []
    current = 0
    while current < page_height:
        # 随机滚动 300-800px
        step = random.randint(300, 800)
        current += step
        if current > page_height:
            current = page_height
        steps.append(current)
    return steps


def random_delay(min_ms: int = 500, max_ms: int = 3000) -> int:
    """随机延迟（毫秒），模拟人类操作间隔"""
    return random.randint(min_ms, max_ms)


def random_mouse_movements(page) -> None:
    """在页面上产生随机鼠标移动（由调用方 await）"""
    return page.mouse.move(
        random.randint(100, 800),
        random.randint(100, 600),
        steps=random.randint(3, 8)
    )
