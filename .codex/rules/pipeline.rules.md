# 流水线规则 · Pipeline Rules

## 激活条件
当任务涉及短剧/短视频制作的阶段切换时自动激活。

## 阶段转换规则

### 门禁机制
每个阶段有明确的"门禁"（Gate），必须通过才能进入下一阶段：

| 当前阶段 | 门禁条件 | 下一阶段 |
|----------|----------|----------|
| S1 选题 | 选题验收通过 | S2 剧本 |
| S2 剧本 | 全部 7 集剧本审查通过 | S3 素材 |
| S3 素材 | 角色一致性检查通过 | S4 合成 |
| S4 合成 | 全片预览通过 | S5 发布 |

### 禁止行为
- ❌ 不允许"边拍边写"——前一阶段全部完成后再进下一阶段
- ❌ 不允许跳过门禁——即使"看起来没问题"也必须走审查流程
- ❌ 不允许回退时覆盖已有文件——回退修改必须写新文件或明确 patch

### 回退规则
当某阶段发现问题需要回退时：
1. S4 发现问题 → 回退到 S3（补素材），不回退到 S2
2. S5 发布后数据差 → 回退到 S1（重新选题），不回退到 S2
3. 最小回退原则：只回退到能修复问题的最近阶段

### 并行规则
- S1 可并行处理多个选题方案
- S2 的 7 集剧本可并行创作（但共用一个角色设定文件）
- S3 的分镜素材可并行生成（但共用一个角色参考图）
- S4、S5 必须串行
- 并行任务完成后必须经过 Integrator Agent 合并

## 阶段产物清单

每次阶段完成时，必须输出以下文件（以项目 `overtime-revenge` 为例）：

### S1 产物
```
projects/overtime-revenge/topic/topic-card.md
```

### S2 产物
```
projects/overtime-revenge/characters/characters.md
projects/overtime-revenge/scripts/ep01.md
projects/overtime-revenge/scripts/ep02.md
... projects/overtime-revenge/scripts/ep07.md
```

### S3 产物
```
projects/overtime-revenge/assets/ep01/s01_*.png
projects/overtime-revenge/assets/ep01/s02_*.png
... (按分镜)
```

### S4 产物
```
projects/overtime-revenge/voice/ep01/s01.mp3
...
projects/overtime-revenge/outputs/ep01_final.mp4
```

### S5 产物
```
projects/overtime-revenge/outputs/ep01_douyin.md
projects/overtime-revenge/outputs/ep01_kuaishou.md
```
