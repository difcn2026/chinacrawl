# Chinacrawl-PDD 拼多多抓取器 · 架构与状态

> 更新: 2026-06-13 v0.3.0 | 位置: A:\chinacrawl\pinduoduo\

## 数据通道全景

```
入口层 (scraper.py)
├─ product_search()        SSR搜索 ✅ 100%命中率 | flip-token翻页 | ~4s/次
├─ product_feed()          推荐流 ✅ 免登录 | hub/v3 API | 批量关键词过滤
├─ product_detail()        API详情 ✅ oak/integration/render | ~2s | SKU列表
├─ product_detail_ssr()    SSR详情 ✅ 真实价格 | 完整SKU | 图库
├─ product_detail_full()   API+SSR融合 ✅ 最佳数据 | 价格反混淆
├─ product_reviews()       评价数据 ✅ 浏览器内fetch | 分页 | 绕anti_content
├─ mall_products()         店铺商品 ✅ SSR+滚动翻页 | 店铺全量
├─ shop_info()             店铺信息 ✅ SSR提取
├─ flash_sale()            秒杀/特卖 ✅ API+Browser
├─ product_download()      商品数据导出 ✅ JSON
├─ generate_report()       品牌情报报告 ★新增 | 一键出报告
├─ monitor_product()       商品监控 ✅ Hash对比
└─ monitor_shop()          店铺监控 ✅ Hash对比

浏览器层 (browser.py)
├─ open_search_page()      SSR搜索 + flip翻页
├─ open_product_page()     SSR详情 + 评价预览
├─ open_mall_page()        店铺基础信息
├─ open_mall_with_products() 店铺+商品+翻页 ★新增
├─ open_feed()             首页推荐流批量
├─ fetch_reviews_via_browser() 评价API浏览器fetch ★新增
├─ collect_products_via_xhr()  XHR拦截(备用)
└─ _extract_product_ssr()   详情SSR三层提取 ★新增
```

## 核心数据模型

| 模型 | 关键字段 |
|------|---------|
| `ProductInfo` | goods_id, title, price, sales, images, skus[], specs[], stock |
| `SkuInfo` ★新增 | sku_id, spec_text, normal_price, group_price, quantity, is_default |
| `ShopInfo` | mall_id, shop_name, rating, goods_count |
| `ReviewInfo` | review_id, text, rating, user_name, reply_text, images[], specs |

## 关键突破

### 搜索 (SSR)
- 渠道: `window.rawData.stores.store.data.ssrListData`
- 命中率: 100% (5/5关键词)
- 翻页: flip token 多页
- 价格: 清晰 (元)

### 详情 (SSR)
- 渠道: `window.rawData` → `__INITIAL_STATE__` → script JSON
- 价格: 分→元, 绕过混淆
- SKU: 完整列表 (规格+单买价+拼单价+库存)
- 图库: 19张

### 评价 (Browser Fetch)
- 渠道: 浏览器内 fetch `/proxy/api/api/reviews/list`
- 绕过: anti_content 签名 (浏览器自动带cookie+origin+referer)
- 复用: hub/v3 feed 的 page.evaluate(fetch) 模式

### 店铺 (SSR)
- 渠道: `window.rawData` → `__INITIAL_STATE__` → DOM
- 翻页: 滚动加载 (scroll + 重提取)
- 注意: 店铺商品列表API返回403

## 已知问题

1. 详情页价格混淆 (PDD移动Web策略) → SSR走rawData解决
2. random_touch_events 可能触发商品点击导航
3. wait_for_selector 可能触发自动重定向
4. 店铺商品列表API 403 → 浏览器SSR绕行
5. Session约3天有效，需刷新

## 文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| `__init__.py` | 2KB | 模块导出 |
| `scraper.py` | 44KB | 核心编排 (13个公共函数) |
| `browser.py` | 49KB | Playwright浏览器层 (10+函数) |
| `api.py` | 7KB | Web API直连层 (备用) |
| `anti_detect.py` | 7KB | 反检测脚本 |
| `config.py` | 4KB | UA池/端点/限速配置 |
| `session.py` | 10KB | 登录态管理 |
| `export.py` | 15KB | 数据导出 |
| `monitor.py` | 8KB | 监控告警 |
