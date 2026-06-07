# ChinaCrawl Douyin Adapter — 技术架构设计

> 制定：小黑 (XHLS v3.0) | 日期：2026-06-07 | 版本：v0.1-draft
>
> 目标：在 ChinaCrawl 框架内新增抖音平台适配器，实现账号级全量数据采集

---

## 一、设计原则

```
1. 兼容 ChinaCrawl 现有 11 项能力接口（scrape/search/monitor...）
2. 双通道策略：API 优先 + Browser 兜底
3. 对抗升级设计：签名算法 → Playwright → 代理池 三层降级
4. 自用验证：小冰 342 条视频必须能用 Chinacrawl+Douyin 复现采集
```

---

## 二、模块架构

```
src/chinacrawl/douyin/
├── __init__.py          # chinacrawl.douyin.* 公共 API
├── api.py               # Web API 逆向层
├── browser.py           # Playwright 浏览器交互
├── scraper.py           # 核心采集编排
├── monitor.py           # 变化监控 + Webhook
├── session.py           # 登录态管理
├── export.py            # 数据导出格式化
├── anti_detect.py       # 反检测模块
└── config.py            # 平台配置（UA池、延迟策略、代理规则）
```

### 2.1 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| `api.py` | 构造/发送 HTTP 请求，处理签名算法，解析 JSON 响应 | `httpx` |
| `browser.py` | Playwright headless 启动、反检测注入、页面操作 | `playwright` |
| `scraper.py` | 编排采集流程，API→Browser 自动降级，速率控制 | `api` + `browser` |
| `monitor.py` | 哈希对比 + AI Judge 噪声过滤（复用 scraper.py 已有逻辑） | `scraper` |
| `session.py` | Cookie/Token 持久化、登录态校验、自动刷新 | `browser` |
| `export.py` | 结构化输出：CSV / JSON / Markdown / SQLite | — |
| `anti_detect.py` | 浏览器指纹隐藏、Canvas/WebGL 伪造、行为模拟 | `playwright` |
| `config.py` | 平台常量（UA 池、端点 URL、风控阈值） | — |

---

## 三、双通道采集策略

### Channel A: Web API（优先）

抖音 Web 版 (`douyin.com`) 提供内部 API，解析 JSON 响应比浏览器 DOM 快 10x。

```
User
  │
  ▼
douyin_user_posts("user_sec_uid")
  │
  ▼
api.py: GET douyin.com/aweme/v1/web/aweme/post/?
        ?sec_user_id=xxx&count=20&max_cursor=0
  │
  ├─ 200 OK → 解析 JSON → 结构化提取
  │
  ├─ 403/风控 → 触发 Channel B 降级
  │
  └─ 429 限流 → 退避重试（指数退避 + 代理切换）
```

**API 层核心能力**：
- `_build_sign(url, params)` — 签名算法（X-Bogus / _signature 参数）
- `_rotate_user_agent()` — UA 池轮换
- `_parse_aweme(aweme_json)` — 单条视频结构化
- `_paginate()` — 游标分页，自动翻页直到数据为空

### Channel B: Playwright Browser（降级）

当 API 被风控拦截时，自动切换到浏览器模式。

```
api.py 返回 403
  │
  ▼
browser.py: launch Playwright (headless)
  │
  ├─ inject anti_detect.js（隐藏 webdriver 标记）
  ├─ 设置浏览器指纹（navigator.webdriver=false, chrome.runtime）
  ├─ 加载 douyin.com/user/xxx
  ├─ 滚动加载更多视频
  ├─ 从 window.__INITIAL_STATE__ 提取数据
  └─ 返回结构化结果
```

**反检测注入**：
```javascript
// anti_detect.js 核心 Hook
Object.defineProperty(navigator, 'webdriver', { get: () => false });
delete navigator.__proto__.webdriver;
window.chrome = { runtime: {} };
// 覆盖 PhantomJS / HeadlessChrome 特征检测
```

### 降级链路

```
API请求 ──成功──▶ 返回结果
    │
    │ 风控/403
    ▼
Playwright Browser ──成功──▶ 返回结果
    │
    │ 验证码/CAPTCHA
    ▼
代理IP切换 + 延迟增加 ──成功──▶ 返回结果
    │
    │ 持续失败
    ▼
返回错误 + 日志告警
```

---

## 四、公共 API 设计

```python
from chinacrawl.douyin import (
    # 用户相关
    user_info,              # 用户主页信息
    user_posts,             # 用户所有作品（分页迭代器）
    user_likes,             # 用户喜欢的作品（需登录）

    # 视频相关
    video_info,             # 单条视频详情
    video_download,         # 下载无水印视频
    video_comments,         # 视频评论

    # 搜索相关
    search,                 # 关键词搜索
    search_user,            # 搜索用户
    search_hashtag,         # 话题/标签搜索

    # 监控相关
    monitor_user,           # 监控用户新作品
    monitor_hashtag,        # 监控话题新内容

    # 会话管理
    login,                  # 扫码/手机号登录
    save_session,           # 保存登录态
    load_session,           # 加载登录态
    check_session,          # 检查登录态是否有效
)
```

### 使用示例

```python
from chinacrawl.douyin import user_posts, video_download, monitor_user

# 1. 下载某个用户全部视频
for post in user_posts("MS4wLjABAAAAxxx"):
    video_download(post.video_id, output_dir="./downloads/")
    # post 包含: title, like_count, comment_count, share_count,
    #           create_time, duration, cover_url, video_url, music_info...

# 2. 监控用户新作品
monitor_user("MS4wLjABAAAAxxx",
             webhook="https://my-server.com/hook",
             interval_minutes=30)

# 3. 搜索 + 批量采集
from chinacrawl.douyin import search, video_download
for result in search("AI短剧", max_results=50):
    video_download(result.video_id)
```

---

## 五、反爬对抗体系

### 5.1 检测维度 × 对抗策略

| 检测维度 | 抖音风控手段 | 我们的对抗 |
|----------|-------------|-----------|
| 浏览器指纹 | Canvas/WebGL/字体/AudioContext | `anti_detect.py` 全覆盖伪造 |
| WebDriver 标记 | `navigator.webdriver=true` | Hook 注入，设为 false |
| 请求频率 | 单 IP + 短时间 + 高并发 | 延迟 2-5s 随机 + 代理池轮换 |
| 行为模式 | 鼠标轨迹、滚动速度、停留时间 | Playwright 模拟人类行为 |
| 签名算法 | X-Bogus / _signature / msToken | 持续逆向维护 |
| 账号风控 | 新号/异常设备登录 | 老号 + 设备指纹复用 + 养号策略 |

### 5.2 速率限制策略

```python
# config.py — 安全阈值（经过实战验证）
RATE_LIMITS = {
    "user_posts_per_hour": 20,      # 每小时最多采集20个用户
    "videos_per_user_per_min": 10,  # 每个用户每分钟最多10条视频
    "search_per_minute": 5,         # 每分钟最多5次搜索
    "download_per_minute": 15,      # 每分钟最多15个视频下载
    "concurrent_browsers": 2,       # 最多同时2个浏览器实例
    "retry_delay_base": 5,          # 重试基础延迟（秒）
    "retry_delay_max": 120,         # 重试最大延迟（秒）
}
```

---

## 六、数据模型

### 6.1 `UserInfo`

```python
@dataclass
class UserInfo:
    sec_uid: str            # 加密用户ID
    nickname: str           # 昵称
    avatar_url: str         # 头像
    signature: str          # 个人签名
    follower_count: int     # 粉丝数
    following_count: int    # 关注数
    aweme_count: int        # 作品数
    total_favorited: int    # 获赞总数
    verified: bool          # 是否认证
    enterprise: bool        # 是否企业号
```

### 6.2 `AwemeInfo`（单条作品）

```python
@dataclass
class AwemeInfo:
    aweme_id: str           # 视频ID
    desc: str               # 文案描述
    create_time: datetime   # 发布时间
    duration: int           # 时长（毫秒）
    video_url: str          # 无水印视频地址
    cover_url: str          # 封面图
    digg_count: int         # 点赞数
    comment_count: int      # 评论数
    share_count: int        # 分享数
    play_count: int         # 播放数
    music_title: str        # 背景音乐
    hashtags: List[str]     # 话题标签
    is_top: bool            # 是否置顶
```

---

## 七、开发排期

| 阶段 | 内容 | 时间 | 产出 |
|------|------|:--:|------|
| Day 1-2 | API 逆向调研 | 2d | API 端点清单 + 签名算法分析 |
| Day 3-5 | `api.py` 核心实现 | 3d | `user_posts` / `video_info` / `search` 可调通 |
| Day 6-8 | `browser.py` + `anti_detect.py` | 3d | Playwright 降级通道 + 反检测 |
| Day 9-10 | `scraper.py` 编排 + 降级 | 2d | 双通道自动切换 |
| Day 11-12 | `monitor.py` + `export.py` | 2d | 监控 + 五格式导出 |
| Day 13-14 | 集成测试 + 小冰全量复现 | 2d | 342条视频全量采集验证 |
| Day 15 | 文档 + 发布 | 1d | API文档 + PyPI 0.2.0 |

**总计：15 个工作日**

---

## 八、风险与缓解

| 风险 | 概率 | 缓解 |
|------|:--:|------|
| 签名算法频繁变更 | 高 | 模块化签名层，隔离变更影响 |
| 大规模风控封号 | 中 | 速率限制 + 代理池 + 老号养号 |
| Web API 接口下线 | 低 | Playwright Browser 兜底 |
| 登录态失效 | 中 | `session.py` 自动检测 + 刷新 |
| 法律风险 | 中 | 仅采集公开数据，合规声明，robots.txt 尊重 |

---

## 九、自用验证标准

> 这是最硬的验收条件：**必须能用 ChinaCrawl+Douyin 复现上次小冰 342 条视频的全量采集。**

```
from chinacrawl.douyin import user_posts, video_download

count = 0
for post in user_posts("小冰的抖音sec_uid"):
    video_download(post.aweme_id, output_dir="./xiaobing_downloads/")
    count += 1

assert count == 342  # 必须 = 342
```

---

> **小黑的原则**：先让它能跑通小冰，再让它能跑通全世界。15天，一个可用模块，一个 GitHub 爆炸点。
