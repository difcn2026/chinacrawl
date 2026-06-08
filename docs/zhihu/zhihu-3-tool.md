# 为了写一份碎菜机竞品分析，我写了一个开源爬虫工具

> 这是系列最终篇。前两篇讲了数据和洞察，这一篇讲讲工具——以及为什么我要自己造轮子。

---

## 一、为什么不用现成的？

市面上不是没有爬虫工具。Firecrawl 很强，但对中国互联网的支持约等于零。

我用 Firecrawl 搜过"碎菜机"，返回的结果是淘宝、京东的英文翻译页面——中文内容几乎不可用。它的搜索引擎覆盖以 Google 为主，而中文互联网的大量信息在百度、搜狗、抖音、小红书这些平台上。

这就像拿着一把瑞士军刀去砍一棵中国的大树——不是刀不好，是用错了地方。

所以我写了 [ChinaCrawl](https://github.com/difcn2026/chinacrawl)，一个专门面向中国互联网的开源搜索引擎+爬虫框架。

---

## 二、ChinaCrawl 是什么？

简而言之：**中国开发者的 Firecrawl 平替。**

- 零外部付费依赖（不需要 OpenAI API、不需要 Firecrawl 订阅）
- 11种核心能力（搜索、抓取、监听、爬取、下载、交互、提取……）
- 两个平台适配器（抖音 + 拼多多）
- AGPLv3 开源协议

```bash
pip install chinacrawl
```

---

## 三、核心能力一览

| 能力 | 说明 | 一行代码 |
|------|------|---------|
| `search_web` | SearXNG多引擎搜索 | `search_web("关键词")` |
| `scrape` | 网页内容抓取 | `scrape("https://...")` |
| `map_site` | 网站结构发现 | `map_site("https://...")` |
| `monitor_page` | 页面变化监控 | `monitor_page("url", interval=3600)` |
| `crawl_site` | 全站爬取 | `crawl_site("https://...")` |
| `download_site` | 整站下载 | `download_site("https://...")` |
| `douyin_user_posts` | 抖音用户帖子采集 | `douyin_user_posts("sec_uid")` |
| `douyin_search` | 抖音搜索 | `douyin_search("关键词")` |
| `pinduoduo_product_search` | 拼多多商品搜索 | `pinduoduo_product_search("商品")` |

---

## 四、技术架构

```
ChinaCrawl
  ├── SearXNG 引擎层（Google + Bing + DuckDuckGo + Wikipedia 聚合搜索）
  ├── 内容抓取层（Jina AI Reader + Trafilatura 双引擎降级）
  ├── 抖音适配器
  │   ├── XHR 拦截通道（浏览器内拦截 API 请求，绕过 X-Bogus 签名）
  │   ├── API 直连通道（X-Bogus + msToken 签名）
  │   └── Browser DOM 通道（Playwright 兜底）
  ├── 拼多多适配器（浏览器 + API 双通道）
  └── 监控层（Hash + AI Judge 双重变化检测）
```

### 抖音适配器的技术挑战

抖音的反爬是业界最难的之一。它的核心防护有三层：

1. **X-Bogus 签名**: 每个 API 请求都需要一个动态生成的签名，缺失则返回 status_code=5
2. **msToken**: 浏览器指纹生成的令牌，存储在 localStorage.xmst
3. **Shark 防护**: 字节跳动的全站风控系统

传统的做法是逆向这三层防护，但成本极高且随版本更新而失效。

我选择了一个不同的思路：**不破解签名，而是让浏览器自己签名。**

具体做法是：启动一个真实的 Playwright 浏览器，登录抖音，然后拦截浏览器内部发出的 XHR 请求——这些请求是浏览器自己签名的，天然带有正确的 X-Bogus 和 msToken。我们只需要截获响应即可。

这个方案的代价是需要一个真实的浏览器环境，但好处是完全不需要逆向工程，也不会因为抖音更新而失效。

---

## 五、三行代码复现碎菜机分析

```python
from chinacrawl import search_web, scrape, douyin_user_posts

# 1. 搜索行业数据
brands = search_web("碎菜机 十大品牌 排行榜", max_results=10)
for b in brands:
    print(b.title, b.url)

# 2. 抓取品牌排行页面
page = scrape("https://www.chinapp.com/paihang/suicaiji")
print(page.content[:500])

# 3. 采集抖音账号帖子互动数据
for post in douyin_user_posts(
    "MS4wLjABAAAAj4wg3MxRk0RuY26E6y_uws5xwbWh2trr...",
    max_pages=3
):
    print(f"{post.desc[:40]} | ❤️ {post.digg_count}")
```

完整的复现指南在 GitHub 的 `examples/cases/README.md`。

---

## 六、为什么开源？

我在研究碎菜机这个品类时发现：**中国开发者缺少一个好用的、面向中文互联网的数据采集工具。**

Firecrawl 很好，但它的中国覆盖是真空。我们自己写脚本，每次都要处理反爬、代理、签名——重复造轮子。

所以我把它开源了。AGPLv3 协议，你可以自由使用、修改、分发。如果你用它做了有意思的分析，欢迎 PR 到 `examples/cases/`。

---

## 七、后续计划

- 小红书适配器（搜索 + 笔记采集）
- 淘宝/天猫商品数据适配器
- 微信公众号文章采集
- 数据导出面板（Web UI）

如果你有想采集的平台，欢迎在 GitHub 提 Issue。

---

> **系列文章**:
> - 上篇: [我在抖音搜"碎菜机"，结果发现了一个所有人都搞错了的品类](#)
> - 中篇: [35个账号、191条帖子：抖音碎菜机品类真实互动数据全揭秘](#)
>
> GitHub: [github.com/difcn2026/chinacrawl](https://github.com/difcn2026/chinacrawl)
>
> 如果这篇文章对你有帮助，欢迎 Star ⭐
