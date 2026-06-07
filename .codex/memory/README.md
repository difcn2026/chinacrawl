# 记忆与进化循环 · Memory & Evolution

## 设计理念
每次交互都是学习机会。纠正、观察、规则和经验被结构化为文件，从"一次性对话"变成"可积累的工程资产"。

## 记忆类型
| 类型 | 目录/文件 | 说明 | 生命周期 | 积累频率 |
|------|-----------|------|----------|----------|
| **纠正记录** | `corrections/` | 错误及修复方案 | 永久（可被覆盖） | 每次发现错误 |
| **观察记录** | `observations/` | 项目中的模式、痛点、亮点 | 周期性回顾 | 每次任务完成 |
| **学习规则** | `learning-rules.md` | 从经验中提炼的自动化规则 | 持续演化 | 每 10 次交互 |
| **演化日志** | `evolution-log.md` | 架构/流程/规范的变更历史 | 永久追加 | 每次架构变更 |
| **决策记录** | `decisions.md` | 重要架构决策及理由 | 永久追加 | 每个重要决策 |
| **模式目录** | `patterns.md` | 反复出现的问题/解决方案模式 | 持续积累 | 发现新模式时 |
| **索引** | `corrections/INDEX.md` `observations/INDEX.md` | 所有记录的快速检索表 | 每次新增记录 | 每次新增记录时 |

## 进化循环

① 交互：用户请求 → AI 执行 → 产出交付
② 观察：写入 observations/（模式、亮点、痛点）
    └→ 如发现问题 → ③ 纠正
③ 纠正：写入 corrections/（根因+修复+预防）
④ 提炼（每 10 次交互）：corrections + observations → learning-rules.md
⑤ 吸收（同模式 ≥3 次）：learning-rules.md → .codex/rules/ 或 AGENTS.md
⑥ 归档：记录到 evolution-log.md 和 decisions.md → 下次交互更稳

## 自动触发规则

| 触发条件 | 自动动作 |
|----------|----------|
| Executor 任务受阻 | 写入 `corrections/` |
| Reviewer 给出 REJECT | 写入 `corrections/` + 触发模式检查 |
| 阶段完成（S1-S7 任一） | 写入 `observations/` |
| 同一问题出现第 2 次 | 在 `learning-rules.md` 创建待吸收条目 |
| 同一问题出现第 3 次 | 升级为正式规则，移入 `.codex/rules/` |
| 修改 AGENTS.md / rules / agents | 写入 `evolution-log.md` |
| 重要技术选型 | 写入 `decisions.md` |

## 索引维护
- 每次新增 correction → 追加到 `corrections/INDEX.md`
- 每次新增 observation → 追加到 `observations/INDEX.md`
- 索引格式：`| 日期 | 标题 | 严重程度/类别 | 涉及层 |`
