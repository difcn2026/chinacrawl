# 竞品全景分析：xhls_scraper 市场定位

| 属性 | 值 |
|------|-----|
| **文档编号** | COMP-2026-06-06-001 |
| **日期** | 2026-06-06 |
| **作者** | 小黑 (XHLS v3.0 总架构师) |
| **关联文档** | `adr-2026-06-06-xhls-scraper-commercialization.md`, `deep-2026-06-06-three-step-path.md` |
| **数据来源** | SearXNG 私有实例搜索 + Bright Data 竞品综述 + Firecrawl 官方博客 + StatCounter |

---

## 一、全球竞品矩阵

| 产品 | 类型 | 定价 | GitHub Stars | 搜索 | LLM提取 | 自托管 | 中文搜索 |
|------|------|:--:|:--:|:--:|:--:|:--:|:--:|
| **Firecrawl** | 开源+托管 | $16-333/月 | 70k+ | ✅ | ✅ | ✅ | ❌ |
| **Bright Data** | 企业代理 | 按量 | — | ❌ | ❌ | ❌ | ❌ |
| **Skrape.ai** | 托管API | $15-250/月 | — | ❌ | ✅ | ❌ | ❌ |
| **ScrapeGraphAI** | AI抓取 | $0-500/月 | — | ✅ | ✅ | ❌ | ❌ |
| **Oxylabs** | 企业代理 | 按量 | — | ❌ | ❌ | ❌ | ❌ |
| **Browse AI** | 无代码 | $0-500/月 | — | ❌ | ❌ | ❌ | ❌ |
| **Zyte** | 传统抓取 | 按量 | — | ❌ | ⚠️(新增) | ❌ | ❌ |
| **Crawl4AI** | 开源 | 免费 | 38.7k | ❌ | ✅ | ✅ | ❌ |
| **Jina AI Reader** | 免费API | 免费 | — | ❌ | ❌ | ❌ | ❌ |
| **OpenClaw** | 开源 | 免费 | — | ✅(SearXNG) | ✅ | ✅ | ⚠️(可配/无文档) |
| **xhls_scraper** | 开源 | 免费→¥29+ | — | ✅(百度/360/SearXNG) | ✅(qwen2.5:7b) | ✅ | ✅ |

---

## 二、逐家拆解

### Firecrawl — 唯一真正对标物

- **定位**：AI 时代的基础设施层——"The API to search, scrape, and interact with the web at scale"
- **优势**：70k+ Stars、完整 REST API + SDK ×5 语言、视频教程、活跃社区、MCP 支持
- **劣势（对中国市场）**：
  - 搜索引擎仅 Google/Bing 国际版 → 只覆盖中国 1.4% 流量
  - API endpoint 在中国大陆间歇性不可达
  - Stripe 支付，不支持支付宝/微信
  - 无中文 LLM 提取能力
- **威胁等级**：⭐⭐⭐⭐⭐（如果推出中国版，窗口立即关闭）

### Bright Data — 企业代理帝国

- **定位**：4亿+ IP 代理池 + 抓取工具套件，面向企业数据需求
- **优势**：G2 评分 4.6、MCP 服务器、浏览器渲染、验证码破解、数据集订阅
- **劣势**：不提供搜索功能、无 LLM 提取、按量收费无免费 tier、对个人开发者门槛极高
- **威胁等级**：⭐⭐（市场不重叠，他们是企业代理，我们是开发工具）

### ScrapeGraphAI — AI 抓取新贵

- **定位**：输入 prompt → 获取结构化数据，最简单的 AI 抓取体验
- **优势**：Markdownify、SmartScraper、SearchScraper、Spidy Agent 生成代码
- **劣势**：大规模使用时价格是 Firecrawl 的 2 倍、锁定自家 LLM 堆栈、无自托管、无中文引擎
- **威胁等级**：⭐⭐⭐（功能重叠但路线不同）

### Crawl4AI — 最接近的开源竞品

- **定位**：开源 LLM 友好爬虫，面向 RAG 和数据管线
- **优势**：38.7k Stars、Python 原生、支持动态内容、LLM 集成
- **劣势**：无搜索功能（纯 crawl，不 search）、无 LLM 提取引擎（需外接）、无中文搜索源
- **威胁等级**：⭐⭐⭐（如果加上搜索就是直接对手）

### OpenClaw — 最近的邻居

- **定位**：基于 SearXNG 的自托管隐私搜索引擎 + AI 代理
- **优势**：同样用 SearXNG、同样可自托管、同样零成本
- **劣势**：文档全英文、面向隐私搜索引擎用户而非 AI 开发者、中文引擎配置无文档、无商业化意愿（纯社区项目）
- **威胁等级**：⭐⭐（路线不同但技术栈类似，可能被收购或 fork 后商业化）

### Jina AI Reader — 免费但单一

- **定位**：任何 URL → LLM 友好的 Markdown，免费 API
- **优势**：免费、简单（`r.jina.ai/URL`）、被广泛集成
- **劣势**：只抓取不搜索、无 LLM 提取、无自托管、依赖 Jina 云服务
- **威胁等级**：⭐（功能互补而非竞争，xhls_scraper 内部已集成 Jina 作为抓取引擎之一）

---

## 三、功能覆盖对比（三合一能力）

「搜索 + 抓取 + LLM 提取」三合一的只有三个：

| 能力 | Firecrawl | OpenClaw | xhls_scraper |
|------|:--:|:--:|:--:|
| 网页搜索 | Google/Bing | SearXNG（通用） | SearXNG + **百度/360/搜狗** |
| 网页抓取 | trafilatura + 浏览器 | trafilatura + 浏览器 | trafilatura + Jina + Playwright |
| LLM 提取 | OpenAI (付费) | 可接任意 LLM | **qwen2.5:7b (本地免费)** |
| 监控 | ✅ | ❌ | ✅ (Hash + AI Judge) |
| 浏览器交互 | ✅ | ❌ | ✅ (Playwright) |
| 结构化提取 | ✅ | ❌ | ✅ (CSS + LLM) |
| 会话保持 | ❌ | ❌ | ✅ |
| 整站下载 | ❌ | ❌ | ✅ |
| **中文搜索** | ❌ | ⚠️ | ✅ |

---

## 四、我们的护城河 = 三元交集

```
          Firecrawl 的功能集合
               │
     ┌─────────┼─────────┐
     │                   │
OpenClaw 的开源自托管     中文搜索独占（百度/360/搜狗 + qwen）
     │                   │
     └─────────┼─────────┘
               │
        xhls_scraper 唯一的定位
```

**三个圈的交集：**

| 圈 | 覆盖的竞品 | xhls_scraper 的差异 |
|---|---|---|
| 「搜+抓+LLM」三合一 | Firecrawl, OpenClaw | 比 Firecrawl 多中文搜索、比 OpenClaw 多产品化 |
| 零成本自托管 | Crawl4AI, OpenClaw, Firecrawl | 比 Crawl4AI 多搜索、比 Firecrawl 多中文搜索 |
| 中文内容原生支持 | — 无 — | **独占** |

---

## 五、差距与弥补路径

| 维度 | Firecrawl (标杆) | xhls_scraper (现状) | 弥补方案 |
|------|:--|:--|------|
| 代码工程化 | 模块化、CI/CD、测试覆盖 | 1040行单文件 | 阶段1拆模块 + tests |
| API 设计 | RESTful + SDK ×5 | Python函数调用 | 阶段2 FastAPI + SDK |
| 文档 | 完整教程+视频+社区 | 无 | 阶段1产出 |
| 品牌认知 | 70k Stars | 零 | 阶段1 GitHub + Gitee 推广 |
| 中文搜索 | ❌ | ✅ | **已是优势，无需弥补** |
| 边际成本 | $0.02-0.05/次 | ¥0.001/次 | **已是优势，无需弥补** |

---

## 六、结论

> **同类产品不少，但在「中文搜索 + 零成本 + 自托管 + 本地 LLM」四合一这个交叉点上，一个都没有。**

Firecrawl 等于 xhls_scraper **减去**中文引擎和 qwen。Crawl4AI 等于 xhls_scraper **减去**搜索和中文 LLM。OpenClaw 最接近但走的是隐私搜索引擎路线而非 AI 开发者工具路线。

**我们的定位**：Firecrawl 的功能 × OpenClaw 的自托管 × 中文搜索独占 = **中国开发者的 Firecrawl**。

**最大风险**：Firecrawl 推出中国版（加百度后端 + 中文 LLM）。一旦发生，窗口关闭。预估窗口期 12-18 个月。

---

> *"竞品围了一圈，但没一个会说中文。这不是护城河，这是护城楼。"* — 小黑
