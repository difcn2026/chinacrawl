# 知乎回答：有什么好用的开源网页抓取工具推荐？

## 推荐 ChinaCrawl —— 中国版 Firecrawl

Firecrawl 确实是目前最强的网页抓取引擎，搜索+爬取+LLM 提取一条龙。但它有两个致命问题在中国：

1. **没有中文搜索** — 后端只有 Google/Bing
2. **LLM 提取走 OpenAI API** — 按量计费，抓 1000 页烧几十刀

我花了两周写了个平替：**ChinaCrawl**，11合1，全部免费开源。

### 能做什么

- `scrape(url)` — 任意网页 → Markdown
- `search_web("关键词")` — 中文搜索（SearXNG 后端，百度/搜狗可配）
- `map_site(url)` — 站点地图
- `crawl_site(url)` — 整站爬取
- `download_site(url, "output/")` — 整站下载到本地
- `monitor_page(url)` — 页面变化监控
- `extract_llm(url, schema)` — **本地 Ollama 结构化提取，零 API 成本**

### 和 Firecrawl 的关键区别

**LLM 提取是本地的**。你用 Firecrawl 的 `/extract`，每次调用烧 credits。ChinaCrawl 直接用你本机的 Ollama（qwen2.5:7b），跑一万次不花一分钱。

### 一行安装

```bash
pip install chinacrawl
```

GitHub: https://github.com/difcn2026/chinacrawl （AGPLv3 开源，求 star 🙏）

---

*写在最后：做这个的初衷很简单——中国开发者应该有自己的 Firecrawl。不依赖海外 API，不被墙，中文搜索不用将就。欢迎试用、提 issue、提 PR。*
