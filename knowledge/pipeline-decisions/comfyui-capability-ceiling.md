# ComfyUI 能力上限评估

> 评估日期：2026-06-05 | 环境：ComfyUI-aki-v1.3 | 硬件：NVIDIA RTX A4000 16GB VRAM

---

## 硬件天花板

| 参数 | 值 |
|------|-----|
| GPU | NVIDIA RTX A4000 |
| VRAM | 16 GB GDDR6 |
| PyTorch | 2.1.2+cu118 |
| CUDA | 11.8 |
| Python | C:\ComfyUI-aki-v1.3\python\python.exe |

## 模型能力矩阵

| 模型类型 | 可行性 | 速度 | 说明 |
|---------|--------|------|------|
| SD 1.5 文生图 | ✅ 完美 | 2-3s / 512px | 主力方案，9 个 ckpt |
| SD 1.5 图生图 | ✅ 完美 | 3-5s | ControlNet + IPAdapter 加持 |
| SD 1.5 Inpainting | ✅ 完美 | 3-5s | 局部重绘 |
| SDXL 文生图 | ✅ 可用 | 8-15s / 1024px | 质量更高但慢 3-5x |
| SDXL + ControlNet | ⚠️ 紧张 | 12-20s | 单 ControlNet 可，双控有风险 |
| SDXL + IPAdapter | ⚠️ 紧张 | 10-18s | 可以，注意 batch size=1 |
| AnimateDiff SD1.5 | ✅ 可用 | 30-60s / 16帧 | 2 个 motion 模块，16帧安全 |
| AnimateDiff SDXL | ⚠️ 边缘 | 90-180s / 8帧 | 仅 8 帧，需 --lowvram |
| AnimateDiff + Motion LoRA | ⚠️ 紧张 | 额外+10-20s | 0 个 motion lora 文件，需下载 |
| Face Swap (Reactor) | ✅ 可用 | 2-5s | 换脸后处理 |
| Upscale (Ultimate SD) | ✅ 可用 | 10-30s | 2x-4x 放大，2 个放大模型 |
| ControlNet 多控 | ⚠️ 紧张 | 叠加耗时 | SD1.5 可 2-3 控，SDXL 仅 1 控 |
| Video Helper Suite | ✅ 可用 | — | 视频帧拆合工具 |
| Flux / SD3 / SD3.5 | ❌ 不可行 | — | 16GB VRAM 严重不足，需 24GB+ |
| HunyuanVideo / CogVideoX | ❌ 不可行 | — | 需 24GB+ VRAM |
| SVD (Stable Video Diffusion) | ❌ 边缘 | — | 需 20GB+ 或重度量化 |

## 已安装关键节点

| 节点 | 用途 | 状态 |
|------|------|------|
| ComfyUI-AnimateDiff-Evolved | 动画生成 | 2 motion models, 0 motion lora |
| ComfyUI-Advanced-ControlNet | 精确控制 | 8 controlnet 模型 |
| ComfyUI-IPAdapter_plus | 图像提示 | 已安装 |
| ComfyUI-VideoHelperSuite | 视频帧处理 | 已安装 |
| ComfyUI-Reactor | 换脸 | 已安装 |
| ComfyUI_UltimateSDUpscale | 高清放大 | 2 放大模型 |
| ComfyUI-WD14-Tagger | 自动打标 | 已安装 |
| ComfyUI-Impact-Pack | 区域提示/检测 | 已安装 |
| ComfyUI-Inspire-Pack | 提示词助手 | 已安装 |
| FreeU_Advanced | 质量增强 | 已安装 |
| ComfyUI-Manager | 节点管理 | 已安装 |
| efficiency-nodes | 效率节点 | 已禁用 |

## 短剧/短视频生产可行方案

| 需求 | 推荐方案 | 预估时间 |
|------|---------|---------|
| 角色静态图 | SD1.5 + IPAdapter 固定角色 | 3-5s / 张 |
| 场景概念图 | SDXL 文生图 | 8-15s / 张 |
| 分镜图序列 | SD1.5 + ControlNet (OpenPose/Canny) | 5-10s / 张 |
| 简单动图 (2-3s) | AnimateDiff SD1.5 | 30-60s / 段 |
| 视频风格转绘 | SD1.5 + ControlNet + VideoHelper | 60-120s / 段 |
| 角色一致性 | IPAdapter + Reactor 组合 | 附加 5-8s |
| 4K 输出 | Ultimate SD Upscale 2x | 附加 15-30s |

## 不可行需求（16GB VRAM 硬伤）

- ❌ Flux 系列文生图（SD3/Flux.dev/Flux.schnell）
- ❌ 原生视频生成模型（SVD/CogVideoX/HunyuanVideo）
- ❌ SDXL 长序列 AnimateDiff（>16帧）
- ❌ 多 ControlNet + IPAdapter 同时作用于 SDXL
- ❌ 批量并行生成（VRAM 不够同时加载多模型）

## 优化建议

1. **--lowvram 模式**：SDXL 大工作流必开，牺牲速度换稳定性
2. **batch size = 1**：永远不要 batch > 1
3. **分辨率上限**：SD1.5 不超 768x768，SDXL 不超 1280x1280
4. **模型预加载策略**：串行加载避免 VRAM 峰值叠加
5. **定期清理**：ComfyUI-Manager 清理未使用的模型释放空间
