# 拼多多适配器 — ChinaCrawl Pinduoduo Adapter

> 小黑 · XHLS v3.0 | 创建: 2026-06-08 | v0.1.0-dev

---

## 📦 概述

在 `chinacrawl` 框架下实现了完整的拼多多电商平台数据采集适配器，遵循与抖音适配器相同的双通道架构设计。

**架构**: API Channel (优先) → Browser Channel (降级)

**目录**: `src/chinacrawl/pinduoduo/`

---

## 🧩 模块清单 (8个核心模块)

| 模块 | 文件 | 大小 | 职责 |
|------|------|------|------|
| `__init__.py` | `__init__.py` | 1.4KB | 公共 API 导出 |
| `config.py` | `config.py` | 3.8KB | 平台常量/UA池/端点/速率限制 |
| `api.py` | `api.py` | 6.8KB | HTTP API 逆向工程层 |
| `browser.py` | `browser.py` | 22.3KB | Playwright 浏览器交互 (主力通道) |
| `anti_detect.py` | `anti_detect.py` | 6.7KB | 反检测 JS 注入 + 人类行为模拟 |
| `session.py` | `session.py` | 10.5KB | 登录态管理 (QR码/短信) |
| `scraper.py` | `scraper.py` | 25.3KB | 核心编排层 + 数据模型 |
| `export.py` | `export.py` | 15.8KB | CSV/JSON/MD/SQLite 多格式导出 |
| `monitor.py` | `monitor.py` | 7.8KB | Hash + AI Judge 变化监控 |

---

## 📊 数据模型

### ProductInfo — 商品信息
| 字段 | 类型 | 说明 |
|------|------|------|
| `goods_id` | str | 商品ID |
| `title` | str | 商品标题 |
| `price` | float | 拼团价 |
| `original_price` | float | 市场原价 |
| `sales` | int | 销量 |
| `sales_text` | str | 销量文案 (如"10万+") |
| `img_url` | str | 主图URL |
| `images` | list | 全部图片 |
| `shop_name` | str | 店铺名称 |
| `mall_id` | str | 店铺ID |
| `has_coupon` | bool | 是否有优惠券 |
| `free_shipping` | bool | 是否包邮 |
| `rating` | float | 评分 |

### ShopInfo — 店铺信息
| 字段 | 类型 | 说明 |
|------|------|------|
| `mall_id` | str | 店铺ID |
| `shop_name` | str | 店铺名称 |
| `shop_logo` | str | 店铺Logo |
| `rating` | float | 店铺评分 |
| `goods_count` | int | 商品数量 |

### ReviewInfo — 评价信息
| 字段 | 类型 | 说明 |
|------|------|------|
| `review_id` | str | 评价ID |
| `text` | str | 评价内容 |
| `rating` | int | 星级 (1-5) |
| `user_name` | str | 用户名 |
| `reply_text` | str | 商家回复 |
| `specs` | str | 购买规格 |

---

## 🔌 公共 API

```python
from chinacrawl.pinduoduo import (
    # 商品操作
    product_search,      # 搜索商品 (XHR拦截+Browser降级)
    product_detail,      # 商品详情
    product_reviews,     # 商品评价

    # 店铺操作
    shop_info,           # 店铺信息
    mall_products,       # 店铺商品列表

    # 分类与促销
    category_list,       # 商品分类
    flash_sale,          # 秒杀商品

    # 其他
    product_download,    # 下载商品信息
    monitor_product,     # 商品价格监控
    monitor_shop,        # 店铺变化监控

    # 会话管理
    login, save_session, load_session, check_session,
)
```

---

## 🛡️ 反检测策略 (拼多多增强版)

由于拼多多风控比抖音更严格，反检测模块做了特别增强:

1. **移动端伪装** — Android Chrome mobile UA + 移动端视口 (412x915)
2. **15 项 JS 注入** — 完整的 navigator/webdriver/chrome/plugins 隐藏
3. **Canvas 指纹随机化** — 微妙修改像素 alpha 值
4. **WebGL 指纹伪造** — 伪装 Qualcomm Adreno 750 GPU
5. **触摸事件模拟** — touchstart/touchmove/touchend
6. **电池/连接 API 伪造** — 伪装 4G 网络 + 常规电量
7. **延迟增加** — PDD 模式默认延迟更长 (800-4000ms)

---

## ⚡ 双通道策略

| 通道 | 适用场景 | 优势 | 劣势 |
|------|----------|------|------|
| **API Channel** (api.py) | 轻量查询、评价列表 | 速度快10x | anti-content签名限制 |
| **Browser Channel** (browser.py) | 搜索、详情、XHR拦截 | 绕过签名 | 较慢，需资源 |

**主力方案**: Browser XHR 拦截 (collect_products_via_xhr / collect_product_via_xhr)
- 浏览器内部发出正确签名的 API 请求
- 我们拦截响应，完全绕过 anti-content 逆向

---

## 🔗 主入口注册

已在 `chinacrawl/__init__.py` 注册，通过 `PINDUODUO_AVAILABLE` 标志位暴露。

```python
from chinacrawl import (
    PINDUODUO_AVAILABLE,
    pinduoduo_product_search,
    pinduoduo_product_detail,
    pinduoduo_login,
    ...
)
```

`CAPABILITIES` 注册表中新增 4 个能力:
- `pdd-search` — 拼多多商品搜索
- `pdd-detail` — 商品详情
- `pdd-reviews` — 商品评价
- `pdd-monitor` — 商品监控

---

## 📝 与抖音适配器的对应关系

| 抖音 (Douyin) | 拼多多 (Pinduoduo) |
|---------------|-------------------|
| `UserInfo` | `ProductInfo` + `ShopInfo` |
| `AwemeInfo` | `ProductInfo` |
| `CommentInfo` | `ReviewInfo` |
| `user_posts()` | `product_search()` |
| `video_info()` | `product_detail()` |
| `video_comments()` | `product_reviews()` |
| `search()` | `product_search()` |
| `monitor_user()` | `monitor_product()` |
| `login()` (QR扫码) | `login()` (QR扫码 + SMS) |

---

## 🚧 已知限制

1. **anti-content 签名** — PDD 的 API 签名算法不开源，API Channel 受限
2. **登录态有效期** — Cookie 通常 7 天过期
3. **速率限制更严** — 默认搜索 3次/分钟，并发浏览器 1 个
4. **IP 风控** — 频繁请求可能触发验证码

---

## 🔮 下一步建议

- [ ] 接入代理池解决 IP 风控
- [ ] 增加验证码自动识别 (OCR)
- [ ] 实现批量商品比价功能
- [ ] 添加拼多多直播数据采集
- [ ] 商家后台数据采集 (需要商家登录)
