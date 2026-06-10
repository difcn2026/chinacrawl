# XHLS Session 2026-06-06 · 代码审查与开源推进

> 小黑 · XHLS v3.0 | 归档: 飞书云文档
> 关联: `knowledge/pipeline-decisions/xhls-scraper-commercial-use-cases-2026-06-06.md`

---

## 一、今日头条财经搜索实战对比

### 测试结果

用 `xhls_scraper.search_web` 搜索"金融 财经 A股 央行 股市"：

- **SearXNG 公开实例**: 返回 10 条 → 全是英文结果（wordpress.org、IMDb、BBC Wales）——中文搜索失效
- **直接抓取头条财经频道**: `scrape("https://www.toutiao.com/ch/news_finance/")` → 成功提取 16 条金融新闻
  - 美股黑天鹅、比特币破6万、金价跳水、科技股回调、兰州银行被罚、住房价值新政、中澳贸易战等

### 结论

- SearXNG 公共实例（searx.be 等）对中文搜索不友好，必须自建 SearXNG + 配百度/搜狗引擎
- Jina AI 直接抓取头条页面效果良好，可以作为中文搜索的替代路径

---

## 二、xhls_scraper vs 豆包搜索

| 维度 | xhls_scraper | 豆包搜索 |
|------|-------------|---------|
| 内容源权限 | 公共 Web 接口抓取 | 字节内部 API，直接读推荐流 |
| 中文搜索质量 | 依赖 SearXNG（当前中文弱） | 原生中文语义理解 |
| 今日头条覆盖 | 财经频道公开渲染 ~16 篇 | 全站内容 + 个性化推荐 |
| 成本 | 零成本 | 商业产品，有限额 |
| 隐私 | 数据在阿里云 SG | 搜索行为回传字节 |
| 能力广度 | 11 合 1 | 专注搜索+对话 |

**定位**: 互补关系。搜头条内容豆包主场，搜 GitHub/竞品/海外 xhls_scraper 无人能替。

---

## 三、开源风险分析

### 风险矩阵

```
致命: 大厂白嫖 → AGPLv3 防住了代码层
致命: SearXNG 被薅 → 已修复（环境变量替代硬编码 IP）
中等: 代码被抄闭源 → AGPLv3 禁止
中等: 法律连带 → README 免责已强化
中等: Jina AI 断供 → trafilatura fallback 已备
可控: Issue 洪水 → 已加 ISSUE_TEMPLATE + CONTRIBUTING.md
可控: 安全漏洞 → 已加 SECURITY.md
```

### 已修复的三个槽位

1. **硬编码 IP 删除**: `47.236.24.76:9999` → `os.environ["SEARXNG_URL"]` + 公开实例回退
2. **社区治理文件**: ISSUE_TEMPLATE (bug+feature) + SECURITY.md + CONTRIBUTING.md
3. **免责声明强化**: 使用者自负 + 网安法/数安法/个保法 + 不用于非法目的

---

## 四、开源仓库状态

### 文件结构

```
xhls_scraper/
├── .github/ISSUE_TEMPLATE/
│   ├── bug_report.md
│   └── feature_request.md
├── examples/basic_usage.py       (7 个示例)
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE                       (AGPLv3)
├── README.md                     (中英双语 + 免责)
├── SECURITY.md
├── pyproject.toml                (pip install 配置)
└── xhls_scraper.py               (1053行, 24函数, 7类)
```

### Git 提交历史

```
cd0757e  Security hardening: remove hardcoded IP + SECURITY + legal disclaimer
1e18099  Initial commit: xhls_scraper v0.1.0 - 11-in-1 web data engine, AGPLv3
```

### 待完成

- [ ] 用户提供 GitHub/Gitee 用户名 → 创建仓库 + 推送
- [ ] PyPI 发布
- [ ] Docker 一键部署

---

## 五、代码改进审计

### P0 — 功能缺失 / 会踩坑

| # | 问题 | 影响 | 改法 |
|---|------|------|------|
| 1 | 没有 logging，只有 print | 批处理时满屏输出，无法重定向/分级 | 引入 logging，print → logger.info |
| 2 | search_web 中文搜索弱 | 公共 SearXNG 实例对中文返回英文结果 | 文档注明需自建 SearXNG + 配百度/搜狗 |
| 3 | download_site 无断点续传 | 抓 50 页到 48 页失败 → 重来 | 加进度文件记录已完成 URL |
| 4 | monitor_page 用内容 hash 而非语义 | 换个 CSS 就触发告警 | AI Judge 已有，但默认 monitor 应标注区别 |

### P1 — 工程健壮性

| # | 问题 | 改法 |
|---|------|------|
| 5 | 每次 `_make_client()` 新建 httpx.Client | 连接池复用或模块级单例 |
| 6 | crawl_site 无 robots.txt 检查 | 加检查逻辑 |
| 7 | 无请求间隔（单次 scrape） | 加最低 0.1s 延迟 |
| 8 | 错误处理只记录最后错误 | 收集所有重试错误 |
| 9 | `_safe_err` 用 ascii 编码丢中文 | 改为 backslashreplace 或不转 |

### P2 — 功能的最后 10%

| # | 问题 | 改法 |
|---|------|------|
| 10 | extract_llm 只支持 Ollama | 加 OpenAI 兼容 API 选项 |
| 11 | 无结果缓存 | 加 LRU 缓存 |
| 12 | monitor 无通知机制 | 加 webhook/callback 参数 |
| 13 | browser_interact 超时无 fallback | 加 try/except + 返回部分结果 |

### P3 — 打磨

- type hints 覆盖不全
- 测试套件覆盖不足
- download_site 中文 print 国际化差
- 无 CLI argparse 入口

---

## 六、关键决策记录

1. **今年不开源只是时间问题**: 代码已就绪，待用户提供 GitHub/Gitee 仓库地址即可推送
2. **AGPLv3 是最佳选择**: 防同等体量竞品闭源，不防大厂（大厂不需要你的代码）
3. **Ollama 商用合法**: MIT + qwen2.5 Apache 2.0 + 工具定位 = 四层法规模块全绿
4. **托管版定价**: 社区版免费 → 托管版 ¥199/月 → 企业 Pro ¥5-20万/年
5. **最大护城河不是代码是定位**: "中国版 Firecrawl" 这个坑还没人占

---

> *归档时间: 2026-06-06 | 作者: 小黑 (XHLS v3.0)*
> *本地文档: `knowledge/pipeline-decisions/xhls-scraper-commercial-use-cases-2026-06-06.md`*
