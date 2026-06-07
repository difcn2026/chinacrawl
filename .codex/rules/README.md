# 路径规则系统 · Path Rules

## 规则层级
规则按作用域从宽到窄分为三级，窄作用域规则优先：

1. **全局规则** (`base.rules.md`) — 所有任务都遵循
2. **领域规则** (`*.rules.md`) — 按模块/目录激活
3. **目录级 AGENTS.md** — 放在子目录中，只对该子树生效

## 激活机制
- 全局规则始终加载
- 领域规则按任务涉及的目录自动匹配
- 目录级 AGENTS.md 按文件作用域自动继承

## 规则文件清单
| 文件 | 层级 | 适用场景 |
|------|------|----------|
| `base.rules.md` | 全局 | 所有任务 |
| `naming.rules.md` | 全局 | 文件/变量/分支/commit 命名 |
| `quality.rules.md` | 全局 | 代码/内容质量检查和分阶段质量门 |
| `security.rules.md` | 领域 | 处理用户数据、密钥、权限时激活 |
| `pipeline.rules.md` | 领域 | 短剧流水线阶段切换时激活 |

## 规则优先级（冲突时）
```
pipeline.rules > security.rules > quality.rules > naming.rules > base.rules
```

## 如何新增规则
1. 在此目录下创建 `{domain}.rules.md`
2. 在 `README.md` 清单中注册
3. 在 `evolution-log.md` 记录新增决策
