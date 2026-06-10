# HANDOFF — 抖音适配器 X-Bogus 集成状态
## 2026-06-08 会话交接

### 完成

1. **xbogus npm 包安装** `scripts/node_modules/xbogus/`
2. **Node.js 桥接脚本** `scripts/xbogus_bridge.js` — 接收 query_string + UA，输出 X-Bogus
3. **api.py 修复**
   - 双引号语法错误：`""urllib.parse""` → `urllib.parse`、`""&""` → `"&"` 等
   - 新增 `load_cookies()` / `_apply_cookies()` — 从 Playwright JSON 加载 Cookie 注入 httpx
   - `_get()` 方法自动附加 `_BROWSER_PARAMS` + X-Bogus 签名
4. **API 通道验证** ✅
   - `fetch_user_info`: 小冰, 103.5万粉, 437作品, HTTP 200
   - `fetch_user_posts`: 36条/页, X-Bogus签名+Cookie通过
5. **scraper 层验证** ✅
   - `user_info()` → UserInfo 对象完整
   - `user_posts(use_xhr=False)` → API 通道 36 posts

### 搜索限制

- `search_general`/`search_user` 返回 `aweme_list=null`, `search_nil_type=params_check`
- 原因：msToken 缺失（客户端 JS 动态生成，不在 localStorage/cookie 中持久化）
- 浏览器搜索页是 SSR 渲染 (`RENDER_DATA` URL-encoded)，`networkidle` 超时（反爬信标）
- msToken 相关：`web_secsdk_runtime_cache`、`SLARDARdouyin_web`（Base64）、`xmst` key

### 文件状态

| 文件 | 说明 |
|------|------|
| `xhls_scraper/scripts/xbogus_bridge.js` | ✅ 新建 |
| `xhls_scraper/scripts/node_modules/xbogus/` | ✅ 新建 |
| `xhls_scraper/chinacrawl/douyin/api.py` | ✅ 已修复+增强 |
| `xhls_scraper/scripts/verify_douyin.py` | 验证脚本 |
| `xhls_scraper/scripts/extract_mstoken.py` | msToken诊断 |
| `xhls_scraper/scripts/fix_api.py` | 临时(可删) |
| `xhls_scraper/scripts/fix_api_cookies.py` | 临时(可删) |
| `New project/src/.cache/sessions/douyin_default.json` | Cookie文件(61条) |

### 下一步

1. **msToken 逆向** — 从 `web_secsdk_runtime_cache` 入手，逆向 JS 生成逻辑（路径 A）
2. **搜索 SSR 提取** — `RENDER_DATA` URL-decode + JSON parse（路径 B）
3. **全量采集验证** — `user_posts(use_xhr=True)` 复现小冰 437 条（路径 C，验证 XHR 通道）
4. **PyPI 发布** — token 已就绪 `pypi-AgEIcHlwaS5vcmc...`，`pip install chinacrawl==0.2.0`
5. **VPS 推送** — SSH 密码 `difcn2026-2026` 需验证

### 关键路径

- Python: `C:\ComfyUI-aki-v1.3\python\python.exe`
- Node: `C:\Program Files\nodejs\node.exe`
- 主包: `C:\Users\Administrator\Documents\xhls_scraper\`
- 项目: `C:\Users\Administrator\Documents\New project\`
- Cookie: `C:\Users\Administrator\Documents\New project\src\.cache\sessions\douyin_default.json`
- 小冰 sec_uid: `MS4wLjABAAAA_FX11UDBw7gopcoMWiGn1b8DgdPv5z4Lh_fN5V-WsuQ`
