# ChinaCrawl 搜索引擎收录推送 — 会话记录

## 时间
2026-06-06 16:00 - 17:30

## 完成事项

### 1. SearXNG 三槽位修复（阿里云 SG VPS 47.236.24.76）

| # | 问题 | 修复 | 状态 |
|---|------|------|:--:|
| 1 | nginx 反代 $变量被 shell 吞 | 重写 /opt/nginx_default.conf, proxy_pass → SearXNG 容器 IP + 正确保留 $proxy_add_x_forwarded_for 等变量 | ✅ |
| 2 | JSON 格式缺失 | /opt/searxng/settings.yml 添加 json 到 formats | ✅ |
| 3 | chinacrawl.py GET→403 | 改为 POST 请求, params→data | ✅ |

**搜索引擎可用状态**:
- Google ✅ | Bing ✅ | Sogou ✅ | 百度 ❌ CAPTCHA

### 2. 搜索引擎收录推送

**已完成**:
- sitemap.xml 推送到 GitHub/Gitee (master 分支)
- README.md 添加 SEO 关键词（中英双语, HTML meta 注释）
- VPS Landing Page: http://47.236.24.76:7777/chinacrawl
- Landing Page 含 GitHub/PyPI/Gitee 外链
- Googlebot/Bingbot/Baiduspider/Sogou Spider 四爬虫验证通过(200)

**未完成（需手动）**:
- 百度站长: 登录 ziyuan.baidu.com/linksubmit/url 粘贴URL
- 搜狗站长: 登录 zhanzhang.sogou.com（卡在域验证，github.com 无法放验证文件）

**核心瓶颈**: 四大搜索引擎均要求域验证。github.com/pypi.org/gitee.com 非自有域名，无法放验证文件。

**替代策略**: VPS Landing Page → 爬虫自然发现 → 顺链爬取 GitHub/PyPI/Gitee

### 3. V2EX 推广帖

- 文案已准备: docs/v2ex-post.md
- V2EX 浏览器打不开（被墙），需手动复制粘贴

### 4. chinacrawl.py 修改

- SearXNG fallback: `client.get` → `client.post`
- 默认实例列表新增: `http://47.236.24.76:9999`
- 已推送到 GitHub/Gitee

## 关键资产

| 资产 | 地址 |
|------|------|
| GitHub | https://github.com/difcn2026/chinacrawl |
| PyPI | https://pypi.org/project/chinacrawl/ |
| Gitee | https://gitee.com/difcn2026/chinacrawl |
| SearXNG | http://47.236.24.76:9999 (POST) |
| Nginx 反代 | http://47.236.24.76:7777 |
| Landing Page | http://47.236.24.76:7777/chinacrawl |
| VPS SSH | root@47.236.24.76 / DiFCN2026-2026 |

## 搜索关键词预测

收录后有效关键词:
- chinacrawl / ChinaCrawl
- 中国版Firecrawl
- difcn2026
- Firecrawl alternative
- pip install chinacrawl

## 下一步

1. 等待 24-72h，验证 Google/Bing 收录
2. 手动登录百度/搜狗站长提交（可选）
3. V2EX/知乎发推广帖
4. 给 GitHub 仓库加 Topics 标签
