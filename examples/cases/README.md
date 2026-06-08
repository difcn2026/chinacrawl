# ChinaCrawl 产品案例

> 真实数据 · 完整方法论 · 可复现

## 案例列表

### 1. 抖音「碎菜机」竞品分析报告（增强版 v2）

- **文件**: `抖音碎菜机竞品分析报告-增强版.md`
- **数据源**: 抖音 35 个账号实时采集 + 191 条帖子互动数据 + SearXNG 搜索
- **工具**: ChinaCrawl v0.2.0 抖音适配器（XHR 拦截 + X-Bogus API）
- **核心发现**:
  - 品类互动率中位数 0.35%（抖音均值 3-5%）→ 蓝海信号
  - 91.4% 账号未认证 → 认证即壁垒
  - 抖音"碎菜机"= 养殖饲料粉碎机 ≠ 厨房小家电（关键语义差异）
- **产出**: 9 章完整报告，含品牌矩阵、账号深度剖析、互动率分析、策略建议

### 2. 维燕牌碎菜机抖音推广方案

- **文件**: `维燕牌碎菜机抖音推广方案.md`
- **数据基础**: 基于竞品分析报告的 35 账号 + 191 帖子数据
- **核心内容**:
  - 双账号矩阵（厨房旗舰 + 工厂侧翼）
  - 30 天内容日历
  - 投放策略（三阶段）
  - KPI 框架（30/90 天）
  - 预算概算（首月 ¥30,200）
- **方法论**: 所有决策均有数据锚点，可复制到其他品类

## 工具链

```
ChinaCrawl (SearXNG → Browser XHR → Trafilatura/Jina)
  ├── 抖音适配器 (collect_user_posts_via_xhr)
  ├── 搜索聚合 (SearXNG 多引擎)
  └── 内容抓取 (Jina + Trafilatura)
```

## 复现指南

```bash
# 安装
pip install chinacrawl

# 抖音账号采集
python -c "
from chinacrawl import douyin_user_posts
for post in douyin_user_posts('sec_uid', max_pages=3):
    print(post.digg_count, post.desc)
"

# SearXNG 搜索
python -c "
from chinacrawl import search_web
results = search_web('碎菜机 品牌 排行', max_results=10)
for r in results:
    print(r.title, r.url)
"
```

---

> 更多案例和文档: [github.com/difcn2026/chinacrawl](https://github.com/difcn2026/chinacrawl)
