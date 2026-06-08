# ChinaCrawl 🕷️

**中国版 Firecrawl — 11合1开源网页数据引擎，零外部API成本**

[![License](https://img.shields.io/badge/license-AGPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![PyPI](https://img.shields.io/badge/pypi-chinacrawl-orange)](https://pypi.org/project/chinacrawl/)

Firecrawl 是硅谷最火的网页抓取引擎，但在中国有两个致命问题：
1. **没有中文搜索引擎支持**
2. **LLM 提取走 OpenAI API（按量计费）**

ChinaCrawl 填这个坑。

## 11 合 1 能力

| 能力 | 一行代码 |
|------|---------|
| 网页抓取 | `scrape("https://example.com")` |
| 网页搜索 | `search_web("关键词")` |
| 站点地图 | `map_site("https://example.com")` |
| 整站爬取 | `crawl_site("https://example.com")` |
| 整站下载 | `download_site("url", "output/")` |
| 变化监控 | `monitor_page("url")` |
| AI 去噪监控 | `monitor_page_ai("url")` |
| 结构化提取 | `extract_structured("url", schema)` |
| LLM 提取 | `extract_llm("url", schema)` |
| 浏览器交互 | `browser_interact("url", actions)` |
| 会话保持 | `browser_session_save("url")` |

## 快速开始

## 平台适配器（中国平台专用）

ChinaCrawl 内置了中国主流平台的专用适配器，处理登录、反爬、签名等平台特有逻辑。

### 抖音（Douyin）

```python
from chinacrawl.douyin import search, user_info, login

# QR扫码登录（30天内有效）
login()  # 打开浏览器 → 扫码 → 自动保存cookie

# 搜索用户
results = search("碎菜机", search_type="user", max_results=20)
for r in results:
    print(r.nickname, r.follower_count)

# 获取用户详情
info = user_info("MS4wLjABAAAAxxx")
print(info.nickname, info.signature)
```

| 功能 | 状态 | 说明 |
|------|:--:|------|
| QR扫码登录 | ✅ | 浏览器可视化，cookie持久化 |
| 用户搜索 | ✅ | XHR拦截 + fetch_user_info API |
| 用户详情 | ✅ | X-Bogus签名通道 |
| 用户作品 | ✅ | API / XHR双通道 |

> ⚠️ **代理要求**：抖音会根据IP地理位置返回不同版本。非中国/香港IP会得到「抖音精选电脑版」轻量版（无搜索功能）。使用前确保代理节点有中国或香港IP。适配器会在检测到轻量版时自动输出警告。

### 拼多多（PDD）

> 适配器中，登录方案开发中。详见 `projects/碎菜机分析/PDD_ADAPTER_STATUS.md`

```bash
pip install chinacrawl
```

```python
from chinacrawl import scrape, search_web

# 抓网页
result = scrape("https://example.com")
print(result.title, result.word_count)

# 搜中文（SearXNG 自托管）
results = search_web("Python 爬虫工具", max_results=10)
for r in results:
    print(r.title, r.url)

# LLM 结构化提取（本地 Ollama，零成本）
from chinacrawl import extract_llm
data = extract_llm("https://example.com/product", {"title": "str", "price": "float"})
```

## vs Firecrawl

| | Firecrawl | ChinaCrawl |
|---|---|---|
| 中国可用 | ❌ 被墙 + 无中文搜索 | ✅ 阿里云/自托管 |
| 中文搜索 | 仅 Google | 百度/搜狗/SearXNG 可配 |
| LLM 提取 | OpenAI API（付费） | 本地 Ollama（零成本） |
| 费用 | Paid API | 免费开源 AGPLv3 |
| 私有部署 | 企业版 | 自带 |

## 安装选项

```bash
# 基础安装 (scrape/search/map/monitor/crawl/download)
pip install chinacrawl

# 带浏览器交互支持
pip install chinacrawl[browser]

# 带本地 LLM 提取
pip install chinacrawl[llm]

# 全部
pip install chinacrawl[all]
```

## 配置 SearXNG（中文搜索）

编辑默认实例：
```python
from chinacrawl import SEARXNG_INSTANCES
SEARXNG_INSTANCES.append("http://your-searxng:8888")
```

或本地部署：
```bash
docker run -d --name searxng -p 8888:8080 searxng/searxng
```

## License

GNU AGPLv3 — 开源使用，但云托管必须开源修改。

## Links

- GitHub: https://github.com/difcn2026/chinacrawl
- Gitee: https://gitee.com/difcn2026/chinacrawl
- PyPI: https://pypi.org/project/chinacrawl/
