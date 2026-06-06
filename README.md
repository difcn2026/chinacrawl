<p align="center">
  <img src="https://img.shields.io/badge/License-AGPLv3-blue.svg" alt="AGPLv3">
  <img src="https://img.shields.io/badge/Python-3.10+-green.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Status-Alpha-orange.svg" alt="Alpha">
</p>

# xhls_scraper · 小黑爬虫

> **中国可用的 Firecrawl 平替 —— 零外部付费依赖的 11 合 1 Web 数据引擎。**

*Firecrawl alternative that works in China. 11-in-1 web data engine with zero external API cost.*

---

## 为什么需要 xhls_scraper？

| | Firecrawl | xhls_scraper |
|---|---|---|
| 🇨🇳 中国可用 | ❌ 被墙 + 无中文搜索 | ✅ 阿里云/本地自建 |
| 🔍 中文搜索 | Google 为主 | 百度/搜狗/SearXNG 可配 |
| 🧠 LLM 提取 | 按 credits 收费 (OpenAI) | 本地 Ollama，零边际成本 |
| 💰 成本 | API 付费 | 完全免费 (AGPL) |

> Firecrawl 是硅谷最好的 web scraping 引擎。但它在中国不可用。xhls_scraper 填补这个真空。

---

## 能力矩阵

| # | 能力 | 对标 Firecrawl | 命令示例 |
|---|------|:---:|---|
| 1 | **scrape** | `/scrape` | `scrape("https://example.com")` |
| 2 | **search** | `/search` | `search_web("keyword")` |
| 3 | **map** | `/map` | `map_site("https://example.com")` |
| 4 | **crawl** | `/crawl` | `crawl_site("https://example.com")` |
| 5 | **download** | — | `download_site("url", "output/")` |
| 6 | **monitor** | `/monitor` | `monitor_page("url")` |
| 7 | **monitor-ai** | — | `monitor_page_ai("url")` |
| 8 | **extract** | `/extract` | `extract_structured("url", schema)` |
| 9 | **extract-llm** | `/extract` (credits) | `extract_llm("url", schema)` ✨ |
| 10 | **interact** | `/interact` | `browser_interact("url", actions)` |
| 11 | **session** | — | `browser_session_save/load("name")` |

> `extract-llm` 用本地 Ollama (qwen2.5:7b) 做语义提取。零 API 费用，无限量调用。

---

## 快速开始

### 安装

```bash
# 基础安装（scrape / search / map / crawl / download / monitor）
pip install xhls_scraper

# 完整安装（含 Playwright 浏览器交互）
pip install xhls_scraper[full]

# 本地 LLM 提取（可选，需 Ollama）
ollama pull qwen2.5:7b
```

### 3 行代码上手

```python
from xhls_scraper import scrape, search_web, extract_llm

# 抓取任意网页 → Markdown
result = scrape("https://example.com")
print(result.content[:200])

# 搜索 Web
results = search_web("Python web scraping", max_results=5)
for r in results:
    print(f"{r.title}: {r.url}")

# LLM 结构化提取（零成本）
data = extract_llm("https://news.ycombinator.com", {
    "top_story": "h1",
    "all_headlines": "a.storylink"
})
print(data.data)
```

### CLI 模式

```bash
python xhls_scraper.py  # 运行内置 11 项全能力测试
```

---

## 架构

```
xhls_scraper
├── Scrape:   jina.ai + trafilatura  →  Markdown
├── Search:   SearXNG (自建/公开)     →  List[Result]
├── Map:      trafilatura links      →  List[PageLink]
├── Crawl:    BFS 递归               →  CrawlResult
├── Download: Map + Scrape           →  {url}.md 文件树
├── Monitor:  Hash + AI Judge        →  MonitorResult
├── Extract:  CSS + Ollama qwen      →  dict/JSON
└── Interact: Playwright             →  BrowserResult
```

---

## 商业场景

- 📈 **金融数据** — 批量抓取央行/证监会公告，结构化入仓
- 🛒 **电商竞品** — 京东/天猫对手定价与库存监控
- ⚖️ **法规合规** — 政府法规站全量归档 + 版本对比
- 🎯 **招标监控** — 政府采购网新标讯即时推送 (AI 去噪)
- 🧠 **RAG 数据** — 任意文档站 → 离线 markdown → Dify/LangChain

---

## 免责声明

> **xhls_scraper 是数据提取工具，不是 AI 服务。**
>
> **重要: 使用者自行承担全部法律责任。** xhls_scraper 提供的是通用数据采集能力。使用者必须：
> - 遵守目标网站的 robots.txt 和服务条款
> - 确保数据采集行为符合当地法律法规（含《网络安全法》《数据安全法》《个人信息保护法》）
> - 获取必要的授权和同意
> - 不将本工具用于任何非法目的
>
> xhls_scraper 作者及贡献者不对使用者的任何行为承担法律责任。
>
> `extract-llm` 功能依赖用户自行安装的 Ollama 模型。用户应确保所使用的模型许可证（如 Apache 2.0、MIT、Llama Community License）允许其预期用途。xhls_scraper 默认使用 qwen2.5:7b（Apache 2.0，商用无限制）。
>
> 请遵守目标网站的 robots.txt 和服务条款。本工具仅供合法用途。

---

## 许可证

GNU Affero General Public License v3.0 — 自由使用、修改、分发。但如果你改了代码并通过网络提供服务，必须公开源码。

---

## 路线图

- [x] 11 合 1 核心能力
- [x] SearXNG 搜索集成
- [x] AI Judge 噪声过滤
- [ ] 中文搜索引擎配置（百度/搜狗）
- [ ] PyPI 发布
- [ ] Docker 一键部署
- [ ] 托管版 API (xhls_scraper.cloud)

---

<p align="center">
  <sub>Built with ❤️ by Xiao Hei · XHLS v3.0 · 2026</sub>
</p>
