# LoRA 训练集成方案 — 短视频控制台

> 创建时间：2026-06-03  
> 项目：AI 短剧/短视频创作流水线  
> 仪表盘：http://localhost:5002

---

## 一、背景与目标

### 问题
- 动漫角色形象在多集/多镜头中难以保持一致
- 纯 prompt 描述无法固化物貌特征（发型、眼镜、服装等）

### 目标
- 为每个角色训练专属 LoRA，固化角色视觉特征
- LoRA 训练与仪表盘深度集成，一键式操作
- 支持外部素材自动抓取，丰富训练数据

---

## 二、整体架构

```
仪表盘 (5002) ──点击 LoRA 训练──→ 收集素材 + 外部抓取
                                      ↓
                               sd-scripts/train_network.py
                                      ↓
                               LoRA 输出 → 自动部署到 ComfyUI
                                      ↓
                               更新 style_profile.json（自动绑定）
                                      ↓
                               下次生成自动注入 LoRA + 触发词
```

---

## 三、环境准备

| 组件 | 路径 | 说明 |
|------|------|------|
| ComfyUI | `C:\ComfyUI-aki-v1.3\` | 图像生成引擎 |
| sd-scripts | `C:\sd-scripts\` | LoRA 训练脚本（kohya-ss） |
| Python | `C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe` | 训练 Python 环境 |
| 仪表盘 | `C:\Users\Administrator\Documents\AI短剧公司\shortvideo\` | Flask 仪表盘 |

### 已下载模型

| 类型 | 模型名称 | 大小 | 用途 |
|------|----------|------|------|
| Checkpoint | `counterfeitV30_v30.safetensors` | 3.95 GB | 动漫底模 |
| Checkpoint | `revAnimated_v122.safetensors` | 5.13 GB | 备用动漫底模 |
| LoRA | `add_detail.safetensors` | 36.1 MB | 细节增强 |
| LoRA | `linwaner_lora_v1.safetensors` | 72.1 MB | 已有角色 LoRA（示例） |
| Upscaler | `4x-AnimeSharp.pth` | 63.9 MB | 动漫放大 |

---

## 四、训练流程

### 4.1 操作步骤

1. 打开仪表盘 → 选择项目 → 页面底部点击 **🧬 LoRA训练**
2. 勾选要作为训练素材的项目分镜图
3. 填写训练配置：
   - **角色名**：触发词，如 `linyue`
   - **底模**：选择 Checkpoint
   - **轮数**：5-10 轮
4. 填写外部抓取配置（可选）：
   - **搜索标签**：Danbooru 标签，如 `1girl short_hair brown_hair glasses white_shirt office_lady`
   - **抓取数量**：15-30 张
5. 点击 **🚀 收集并训练**

### 4.2 自动流程

1. 收集项目 `assets/` 中已生成的分镜图
2. 如填写了搜索标签，自动从 Safebooru 抓取外部图片
3. 合并所有图片到 `C:\sd-scripts\dataset\{角色名}_data\`
4. 自动生成训练配置 TOML 文件
5. 后台启动 `train_network.py`，日志写入 `lora_train_log.txt`
6. 训练完成后自动将 LoRA 复制到 ComfyUI `models\loras\`
7. 自动更新项目 `style_profile.json`，绑定 LoRA 和触发词
8. 后续生成时自动在 prompt 中注入触发词 + 在 workflow 中加载 LoRA 节点

### 4.3 训练参数（默认值）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| network_dim | 32 | LoRA 维度 |
| network_alpha | 16 | LoRA alpha |
| learning_rate | 1e-4 | 学习率 |
| epochs | 5 | 训练轮数 |
| resolution | 512,512 | 训练分辨率 |
| mixed_precision | fp16 | 混合精度 |
| optimizer | AdamW8bit | 优化器 |
| lr_scheduler | cosine | 学习率调度 |

---

## 五、新增 API 端点

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/lora/list` | 列出 ComfyUI 中所有 LoRA |
| GET/POST | `/api/project/{n}/lora/config` | LoRA 训练配置读写 |
| POST | `/api/project/{n}/lora/collect` | 收集选中分镜图到数据集 |
| POST | `/api/project/{n}/lora/scrape` | 从 Safebooru 抓取外部素材 |
| POST | `/api/project/{n}/lora/train` | 启动后台 LoRA 训练 |
| GET | `/api/project/{n}/lora/train/status` | 查询训练进度 |
| GET | `/api/project/{n}/lora/train/log` | 获取最后 30 行训练日志 |

---

## 六、完整工作流文件

改进版 ComfyUI 动漫生成工作流已保存至：

```
C:\Users\Administrator\Documents\New project\projects\整顿职场\workflow_anime_v2.json
```

### 工作流改进要点

| 改进项 | 原值 | 新值 | 效果 |
|--------|------|------|------|
| LoRA | 无 | add_detail (0.55) | 线条更锐利 |
| FreeU | 无 | 1.1/1.2/0.9/0.95 | 纹理细节提升 |
| cfg | 7.0 | 6.5 | 减少过饱和 |
| 二阶段 denoise | 0.55 | 0.38 | 保留更多构图 |
| VAE | 默认 | animevae.pt | 动漫色彩更准确 |
| Negative Prompt | 基础 | 全面增强 | 过滤漫画分格、写实等 |

---

## 七、目录结构

```
C:\Users\Administrator\Documents\AI短剧公司\shortvideo\
├── server.py                    # Flask 后端（含 LoRA API）
├── projects/{项目名}/
│   ├── state.json               # 项目状态
│   ├── style_profile.json       # 风格配置（含绑定 LoRA）
│   ├── lora_config.json         # LoRA 训练配置
│   ├── lora_train_config.toml   # sd-scripts 训练配置
│   ├── lora_train_log.txt       # 训练日志
│   └── assets/                  # 生成的分镜图（训练素材来源）
├── templates/index.html         # 前端界面
├── static/
│   ├── app.js                   # 主逻辑
│   ├── lora.js                  # LoRA 训练面板
│   └── dashboard.css            # 样式
└── compose_video.py             # 视频合成
```

---

## 八、角色提示词模板（已更新）

### 林悦（女）

```
masterpiece, best quality, highres, absurdres, newest,
anime coloring, anime screencap, cel shading, flat color,
clean lineart, sharp lines, painterly shading,

1girl, young woman, early 20s, solo,
short dark brown hair, bob cut, light bangs, neat hairstyle,
oval face, gentle features, thin metal-framed round glasses, intelligent calm eyes, slight smile,
white button-up shirt, long sleeves, dark blue tailored trousers, slim build, office lady,

half-body, upper body, looking at viewer,
simple light beige background, plain background,
warm soft lighting, soft shadows, depth of field, sharp focus
```

### 王总（男）

```
masterpiece, best quality, highres, absurdres, newest,
anime coloring, anime screencap, cel shading, flat color,
clean lineart, sharp lines, painterly shading,

1boy, middle-aged man, 40s, solo,
slightly overweight, double chin,
receding hairline, short black hair with gray streaks,
square face, thick eyebrows, small narrow eyes, frown,
dark gray business suit, white dress shirt, dark necktie, formal attire,
arms crossed, authoritative pose, angry expression,

half-body, upper body, looking at viewer,
simple light beige background, plain background,
warm soft lighting, soft shadows, depth of field, sharp focus
```

### 办公室场景

```
masterpiece, best quality, highres, newest,
anime background, anime coloring, cel shading, flat color,
clean lineart, sharp lines,

modern open-plan office interior, wide shot,
floor-to-ceiling windows showing orange sunset evening sky,
warm yellow ceiling lights, ambient indoor lighting,
neat rows of workstations, computer monitors glowing,
office chairs, potted plants, water cooler,

dusk atmosphere, after hours, quiet, calm before storm,
warm golden hour tones, slight cinematic lens flare,
shallow depth of field, detailed background, 16:9 ratio
```
