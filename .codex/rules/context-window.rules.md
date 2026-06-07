# Context Window Management Rule

## 硬约束
- **窗口上限**：258K tokens
- **预警线**：150K tokens（约 15 轮对话）
- **危险线**：200K tokens（约 20 轮对话）
- **致命线**：240K tokens（必须立即归档并开启新会话）

## 会话生命周期

```
新会话开始 → 加载记忆(session-init) → 执行任务
    │
    ├── 每 5 轮自动执行 self-check（引擎驱动）
    ├── 达预警线(150K) → 飞书归档当前状态 → 3句话摘要 → 询问是否继续
    ├── 达危险线(200K) → 强制飞书全量归档 → 保存所有状态 → 建议新会话
    └── 会话结束 → session-save → 飞书归档 → 确认记忆已写入
```

## 归档内容（每次归档必须包含）

1. 会话摘要（做了什么、关键决策、产出文件列表）
2. 当前项目状态快照（哪个阶段、卡在哪里、下一步）
3. 新写入的记忆列表（key + value）
4. 纠正记录（如果有）
5. 未完成事项清单
6. AGENTS.md 变更记录（如果有）

## 新会话启动流程

1. `python .codex/skills/memory/scripts/memory.py session-init`
2. 阅读输出（上次摘要 + 高优先级记忆 + 最近纠正）
3. `python .codex/skills/memory/scripts/memory.py evolution-check`
4. 检查飞书归档，确认上次会话已完整保存
5. 从上次中断处继续，不重复已完成工作

## 飞书归档规范

- 每次归档创建独立飞书文档，标题格式：`XHLS-Session-{date}-{序号}`
- 使用飞书 API（已有凭证 `cli_a9461fbb010adcdb`）
- 归档后记录文档 URL 到记忆（key: `archive-{date}`）

## 小黑自检清单（每5轮必执行）

### 方法一：CLI 直接调用（始终可用）

```powershell
python .codex/xhls/context_guardian.py self-check <当前轮数>
```

输出：引擎状态 + 五区预算 + 告警级别 + 动作清单

### 方法二：MCP 工具调用（XHLS MCP 服务器运行时）

```
MCP Tool: xhls_context_check { "turns": <当前轮数> }
```

返回：结构化 JSON（level / usage_percent / advice / action_items）

### 自检项目

```
[xhls_context_check] 引擎自动输出:
  - 当前用量: ____% / 258K
  - 告警级别: GREEN | YELLOW | ORANGE | RED
  - 压缩次数: ____  |  剪枝次数: ____
  - 动作清单: [continue] | [compress, archive] | [aggressive_compress, feishu_archive, ask_user] | [stop, full_archive, new_session]

[ ] 是否 >= 150K (黄色预警) → 归档 + 双压缩
[ ] 是否 >= 200K (橙色危险) → 强制全量归档 + Phase1 剪枝 + 建议新会话
[ ] 是否 >= 240K (红色致命) → 立即结束，告诉用户开新会话
[ ] AGENTS.md 是否已精简（只保留 Core 区 30K）
[ ] 最近一次飞书归档 URL: ____
```

### 自动动作表

| 级别 | 用量 | 自动动作 |
|------|------|---------|
| GREEN | <=50% | 继续（无动作） |
| YELLOW | <=65% | 双压缩最旧轮次 + 检查大输出 + 审查缓存 |
| ORANGE | <=80% | 激进双压缩 + Phase1 剪枝 + 飞书归档 + 询问用户 |
| RED | <=90% | **立即停止** + 全量飞书归档 + session-save + 告知用户新会话 |

## 禁止行为

- ❌ 上下文接近危险线仍不归档
- ❌ 归档后不记录飞书 URL
- ❌ 新会话不加载记忆就从头开始
- ❌ 归档内容遗漏关键决策或项目状态
- ❌ 超过 20 轮后继续复杂任务
- ❌ 跳过每5轮自检（self-check / xhls_context_check）
