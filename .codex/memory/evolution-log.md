# 演化日志 · Evolution Log

记录项目架构、流程、规范的所有重要变更。

---

## 2026-06-03 v1.1 — 四层架构细节增强

### L1 认知核心增强
- 新增「明确禁止」清单（4 条硬约束）
- 新增 7 阶段流水线验收标准（S1-S7），每阶段含输入/产出/验收/门禁
- 新增「决策框架」：优先级链 + 常见场景默认选择表
- 新增「常见反模式」：5 个反模式 → 正确做法对照表
- 新增第 6 条工作原则「显性化」
- 更新目录约定为多项目隔离结构

### L2 规则系统增强
- 新增 `naming.rules.md`：文件/变量/分支/commit 命名规范
- 新增 `pipeline.rules.md`：门禁机制、回退规则、并行规则、产物清单
- 细化 `base.rules.md`：任务生命周期 5 步、错误处理、禁止行为扩展
- 细化 `security.rules.md`：10 条核心规则、8 项审查清单、激活条件扩展
- 细化 `quality.rules.md`：按阶段 S1-S5 分别定义内容质量标准
- 规则文件数：3 → 5

### L3 Agent 系统增强
- 新增 Agent 间握手协议（P→E, E→R, R→I, I→User）
- 新增 Agent 状态码（PASS / PASS_WITH_NOTES / REJECT / BLOCKED / ERROR）
- 每个 Agent 新增「短剧项目示例」完整对话示例
- Reviewer 新增 4 维评分量规 + 门禁判定矩阵 + 安全问题一票否决
- Integrator 新增 6 步整合流程 + 5 种冲突策略

### L4 记忆系统增强
- 新增 `decisions.md`：2 条初始决策（D-001/D-002）
- 新增 `patterns.md`：3 条种子模式（P-001/P-002/P-003）
- 新增 `corrections/INDEX.md` + `observations/INDEX.md` 检索索引
- 细化 `learning-rules.md`：4 条种子学习规则（LR-001~LR-004）
- 细化 `memory/README.md`：7 种记忆类型、6 步进化循环、7 条自动触发
- 记忆文件数：5 → 10

### 统计
- 本次增强：新增 6 文件 + 细化 13 文件
- 架构总文件数：16 → 22 个 Markdown 文件

---

## 2026-06-03 v1.0 — 初始化四层自进化架构

### 新增
- L1：创建根目录 `AGENTS.md`
- L2：创建 `.codex/rules/` 规则系统（base/security/quality + README）
- L2 扩展：创建 `.codex/skills/script-review/`
- L3：创建 `.codex/agents/`（Planner/Executor/Reviewer/Integrator + README）
- L4：创建 `.codex/memory/`（corrections/observations + learning-rules + evolution-log）

### 决策
- 采用四层架构作为 Codex 标准协作模式
- 规则采用 Markdown 便于人机共读
- Sub-Agent 通过提示词文件定义，可独立升级
- 记忆系统文件化，便于版本控制和团队共享
