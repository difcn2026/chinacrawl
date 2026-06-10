---
name: memory
description: "XHLS persistent long-term memory engine. Supports add/recall/search/forget/session continuity/correction loop/evolution logs. Use when remembering, recalling, saving, or when the user mentions preferences, corrections, or past work."
allowed-tools:
  - Bash(python .codex/skills/memory/scripts/memory.py *)
---

# XHLS Memory Engine

小黑记忆系统——从小K XDLS memory.py进化而来。

## Core Principles

- **先存档再继续** — 不让任何工作白费
- **原子写入** — temp + rename，崩溃安全
- **自动压缩** — 超阈值自动压缩旧记忆
- **纠正循环** — 每次错误变成永久规则
- **演化日志** — 每周自动生成进化报告

## Commands

```bash
# Session lifecycle
python scripts/memory.py session-init          # 会话启动（自动加载上下文）
python scripts/memory.py session-save "<摘要>"  # 会话结束保存

# Memory operations
python scripts/memory.py add <key> <value>              # 记住某事
python scripts/memory.py add-priority <key> <value>     # 高优先级记忆
python scripts/memory.py recall <key>                    # 查找记忆
python scripts/memory.py list                            # 列出所有记忆
python scripts/memory.py forget <key>                    # 删除记忆
python scripts/memory.py search <query>                  # 模糊搜索

# Correction loop (核心进化机制)
python scripts/memory.py correction "<error>" "<rule>"                      # 记录纠正
python scripts/memory.py correction --tag bug "<error>" "<rule>"            # 按标签
python scripts/memory.py corrections [count]                                  # 查看纠正
python scripts/memory.py correction-stats                                     # 纠正统计

# Evolution
python scripts/memory.py evolution "<summary>"    # 生成演化日志
python scripts/memory.py evolution-check            # 检查是否需要生成

# Maintenance
python scripts/memory.py compact                    # 手动压缩
python scripts/memory.py daily-log [date]           # 查看日日志
```

## Storage

- `memory.json` — 结构化 KV 存储（频繁更新）
- `sessions.json` — 会话连续性
- `daily/YYYY-MM-DD.md` — 日会话日志（只追加）
- `corrections/` — 纠正记录
- `evolution/` — 演化日志
