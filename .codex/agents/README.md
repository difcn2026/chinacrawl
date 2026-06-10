# Sub-Agent 分工系统 · Agent Division

## 设计原则
- **上下文干净** — 每个 Agent 只接受自己职责范围内的上下文
- **职责清晰** — 输入/输出定义明确，边界不重叠
- **可独立升级** — 修改一个 Agent 的提示词不影响其他 Agent
- **可组合** — 四个 Agent 可串联为完整流水线，也可单独调用

## Agent 角色矩阵
| 角色 | 文件 | 职责 | 触发场景 |
|------|------|------|----------|
| **Planner** | `planner.md` | 任务拆解、方案设计、风险预判 | 复杂任务开始前 / 需求模糊时 |
| **Executor** | `executor.md` | 代码/内容生成执行 | Plan 确认后执行具体操作 |
| **Reviewer** | `reviewer.md` | 质量审查、安全检查、门禁判定 | 执行完成后 / 阶段切换前 |
| **Integrator** | `integrator.md` | 多模块合并、冲突解决 | 并行任务完成后 / 交付前 |

## 标准流水线
```
用户请求
  │
  ▼
┌──────────┐   Plan    ┌──────────┐  Artifacts  ┌──────────┐  Report  ┌────────────┐
│ Planner  │──────────▶│ Executor │────────────▶│ Reviewer │─────────▶│ Integrator │
│ 拆解需求  │           │ 生成产物  │             │ 审查打分  │          │ 合并交付    │
└──────────┘           └──────────┘             └──────────┘          └────────────┘
     │                       │                        │                     │
     │  任务规格              │  执行报告               │  审查报告             │  整合报告
     ▼                       ▼                        ▼                     ▼
  [plan.md]              [产出文件]               [review.md]          [最终交付]
```

## Agent 间握手协议

### 协议 1：Planner → Executor
Planner 输出任务规格到工作区。Executor 读取该文件，不自行补充任务。
如果 Executor 发现任务规格不可执行，向用户报告并附 Planner 的输出原文。

### 协议 2：Executor → Reviewer
Executor 输出执行报告 + 产物文件列表。
Reviewer 读取执行报告、产物文件、以及 Planner 的任务规格，三向对照评分。

### 协议 3：Reviewer → Integrator（可选）
如果 Reviewer 给出"有条件通过"，Integrator 负责协调修复。
如果 Reviewer 给出"不通过"，退回 Executor，Integrator 不介入。

### 协议 4：Integrator → 用户
最终交付前，Integrator 确认合并无冲突、风格统一、产物完整。
输出整合报告 + 最终产物清单。

## 调用方式
- **完整流水线**："按流水线完成 {任务}" → 依次激活 P→E→R→I
- **单独规划**："先分析规划 {需求}" → 只激活 Planner
- **单独审查**："审查一下 {文件}" → 只激活 Reviewer
- **单独合并**："合并这些产出" → 只激活 Integrator

## Agent 状态码
| 状态 | 含义 | 后续动作 |
|------|------|----------|
| `PASS` | 通过 | 进入下一阶段 |
| `PASS_WITH_NOTES` | 有条件通过 | Integrator 协调修复后进入下一阶段 |
| `REJECT` | 不通过 | 退回上一阶段，附带改进清单 |
| `BLOCKED` | 阻塞 | 需要用户决策或外部资源 |
| `ERROR` | 执行异常 | 记录到 corrections/ 并通知用户 |
