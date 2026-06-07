# HANDOFF — 抖音适配器 搜索替代通道 v2

## 2026-06-08 会话交接

---

## 一、本次完成

### 核心突破：浏览器内 fetch() 绕过所有反爬 ✅

**发现**：在 Playwright 浏览器上下文中通过 `page.evaluate()` 执行 `fetch()` 调用抖音搜索 API，浏览器安全 SDK 自动处理所有签名（X-Bogus / msToken / Shark），完全绕过反爬。

**对比**：

| 通道 | X-Bogus | msToken | Cookie | 状态 |
|------|---------|---------|--------|------|
| 直接 HTTP API | 需要 | 需要 | 一次即焚 | ❌ |
| XHR 拦截 (旧方案) | 自动 | 自动 | 浏览器 | ✅ 慢 |
| **浏览器内 fetch (新)** | **自动** | **自动** | **浏览器** | ✅✅ 快 |

### 代码变更

| 文件 | 变更 | 说明 |
|------|------|------|
| `browser.py` | +`search_via_fetch()` | 新搜索函数 — 浏览器内 fetch |
| `scraper.py` | 修改 `search()` | 新增 Channel 0: fetch 优先 |
| `scraper.py` | 修改 `search_user()` | 新增 Channel 0: fetch 优先 |
| `scraper.py` | 修改 `use_xhr` → `use_xhr or use_fetch` | Cookie 自动检测兼容两种通道 |

### 集成测试结果

```
[1/2] 短剧:   10 results in 18.4s ✅
[2/2] 人工智能: 10 results in 22.5s ✅
```

### 探索过的死路

| 方案 | 结果 | 原因 |
|------|------|------|
| SSR 提取 | ❌ | 页面纯 SPA，72KB HTML 零内嵌数据 |
| 移动端 API | ❌ | iesdouyin.com 403 拦截 |
| 直接 HTTP + Cookie | ❌ | Cookie 一次即焚，session 立即失效 |
| 直接 HTTP + X-Bogus + Cookie | ❌ | 同上 |

---

## 二、当前状态矩阵

| 功能 | 通道 | 状态 |
|------|------|------|
| `user_info` | 直接 API + X-Bogus | ✅ PASS |
| `user_posts` | 直接 API + X-Bogus | ✅ PASS |
| `user_posts` (全量) | XHR 拦截 | ✅ 435/437 |
| `search` | **浏览器内 fetch** | ✅ **NEW! 10/10** |
| `search` | XHR 拦截 | ✅ 5/5 |
| `search` | 直接 API | ❌ Shark/Cookie 烧 |
| msToken 提取 | Browser → xmst | ✅ mstoken.py |
| X-Bogus 签名 | Node.js bridge | ✅ xbogus_bridge.js |

---

## 三、下一步建议

1. **持久化浏览器** — 复用 browser/page 跨多次搜索（~40% 提速）
2. **PyPI 发布 v0.2.0** — token 就绪
3. **VPS SSH 修复** — 密码验证
4. **自动化测试套件** — search_via_fetch 加入 pytest

## 四、关键路径

```
Python: C:\ComfyUI-aki-v1.3\python\python.exe
Node:   C:\Program Files\nodejs\node.exe
主包:   C:\Users\Administrator\Documents\xhls_scraper\
项目:   C:\Users\Administrator\Documents\New project\
Cookie: C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json
SDK:    C:\Users\Administrator\Documents\New project\knowledge\security\douyin-sdk\
小冰:   MS4wLjABAAAA_FX11UDBw7gopcoMWiGn1b8DgdPv5z4Lh_fN5V-WsuQ
```
