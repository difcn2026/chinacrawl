# 命名规则 · Naming Rules

## 文件命名规范

### 剧本文件
```
ep{NN}_{title-slug}.md
示例：ep01_overtime-revenge.md
```

### 素材文件
```
{project}/{ep}/{shot-seq}_{desc}.{ext}
示例：overtime-revenge/ep01/s03_office-wide.png
```

### 配音文件
```
{project}/{ep}/voice_{char}_{shot-seq}.mp3
示例：overtime-revenge/ep01/voice_linyue_s03.mp3
```

### 记忆文件
```
corrections/{YYYY-MM-DD}_{short-slug}.md
observations/{YYYY-MM-DD}_{short-slug}.md
示例：corrections/2026-06-03_script-timing-overflow.md
```

## 变量命名
- 英文小写 + 下划线（snake_case）：`character_name`, `shot_duration`
- 类名：PascalCase：`ScriptParser`, `VideoRenderer`
- 常量：UPPER_SNAKE_CASE：`MAX_DURATION_SEC`, `TARGET_PLATFORM`
- 布尔变量：`is_` / `has_` / `should_` 前缀

## 分支命名
```
codex/<type>/<short-desc>
类型：feat / fix / refactor / chore
示例：codex/feat/add-script-review-skill
```

## Commit 信息
```
<type>(<scope>): <描述>
类型：feat / fix / refactor / docs / chore
范围：pipeline / script / assets / voice / compose / agents / rules
示例：feat(rules): 添加命名规范和流水线转阶段规则
```
