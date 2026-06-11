# V2EX 分享创造帖 — ChinaCrawl

## 发布信息

- **节点**：分享创造 (create)
- **标题**：[开源] ChinaCrawl — 给中国开发者用的 Firecrawl，支持百度搜索 + 本地 Ollama + 抖音适配器
- **标签**：开源、Python、爬虫、LLM

---

## 正文

Firecrawl 应该是 GitHub 上最火的网页抓取引擎了——搜索、爬取、LLM 提取一条龙，好用是真的好用。但我在国内用的时候踩了两个坑：

1. **没有中文搜索引擎**：它后端只有 Google / Bing，百度、搜狗这些国内搜索源一概不支持。搜出来的结果跟国内用户看到的完全对不上。
2. **LLM 提取走 OpenAI API**：按量计费，随便爬几百页就是几十刀。想用本地模型？没这选项。

所以写了个替代品：**ChinaCrawl**。定位就是"在中国能跑、用本地 LLM、不花一分钱 API 费"的网页数据引擎。

---

### 和 Firecrawl 的关键区别

- **中文搜索**：后端接 SearXNG，可配百度/搜狗/Bing/Google 任意组合。搜索行为跟国内用户一致。
- **LLM 零成本**：直接对接本地 Ollama（qwen2.5 实测可用），结构化提取不花 token 钱。
- **自部署即用**：`pip install chinacrawl`，一行代码开搞。AGPLv3 开源，没有"企业版才给私有部署"那一套。
- **自带抖音适配器**：这是目前开源自部署里独一份——国内还没有其他开源引擎能做抖音账号级全量数据采集（视频下载 + 元数据 + 评论 + 变化监控）。对标飞瓜/新榜的采集能力，但完全本地化、可审计。

GitHub: https://github.com/difcn2026/chinacrawl  
PyPI: https://pypi.org/project/chinacrawl/  
Gitee: https://gitee.com/difcn2026/chinacrawl

---

### 11 合 1 — 一个库搞定整条数据流水线

```
scrape()            网页抓取
search_web()        中文搜索（百度/搜狗/SearXNG）
map_site()          站点地图
crawl_site()        整站爬取
download_site()     整站离线下载
monitor_page()      页面变化监控
monitor_page_ai()   AI 智能监控（语义变更检测）
extract_structured() 结构化提取（CSS/XPath）
extract_llm()       LLM 提取 → 本地 Ollama 零成本
browser_interact()  Playwright 浏览器交互（反爬绕过）
browser_session()   会话保持 + 登录态管理
```

---

### 快速上手

```bash
pip install chinacrawl
```

```python
from chinacrawl import scrape, search_web, extract_llm

# 抓网页
result = scrape("https://example.com")

# 中文搜索
results = search_web("Python 爬虫实例", max_results=10)

# LLM 结构化提取 — 走本地 Ollama，不花一分钱
schema = {"title": "str", "price": "float", "desc": "str"}
data = extract_llm("https://example.com/product", schema)
```

---

### 技术栈

- **核心引擎**：Python 3.10+，asyncio 异步架构
- **搜索后端**：SearXNG 私有实例（Docker 自托管，47.236.24.76:9999）
- **浏览器引擎**：Playwright headless + 浏览器池管理
- **LLM 层**：Ollama 本地部署 qwen2.5，无需外部 API
- **Landing Page**：http://47.236.24.76:7777/chinacrawl

---

### 当前状态 & 接下来的计划

项目刚发不到 48 小时，11 项核心能力已可用，但说实话还处于非常早期的阶段：

- ✅ 核心引擎 v0.1.0 已发布 PyPI / GitHub / Gitee 三通道
- ✅ SearXNG 搜索后端可用（百度/搜狗/Google/Bing）
- 🔨 CI/CD + 自动化测试正在搭建
- 🔨 中文文档站 + 视频教程在路上了
- 🔨 抖音适配器 API 逆向中

如果有正在做数据采集、舆情监控、AI 训练数据准备的朋友，非常欢迎来试试看。遇到的问题直接提 Issue，我会尽量响应。

同时也特别欢迎贡献代码——尤其是反爬策略、浏览器指纹对抗、验证码识别这些方向，一个人搞属实有点吃力 😂

---

## 发布备注

- 发布时删掉本行及以下元信息
- 建议发布时间：工作日上午 10:00-11:00 或晚上 20:00-22:00（V2EX 流量高峰）
- 发布后 1 小时内不要回复自己的帖子（社区规范），有人评论后正常互动
- 如有产品截图，用 V2EX 图床或 imgur，不要用 GitHub raw（国内可能加载慢）
