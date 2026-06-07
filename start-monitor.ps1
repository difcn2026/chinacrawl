# XHLS Live Monitor — 后台持续运行
# 每5分钟扫描 GitHub + 全网声量，变更即时推送飞书

Set-Location "C:\Users\Administrator\Documents\New project"

$env:PYTHONIOENCODING = "utf-8"

Write-Host "🕷️ XHLS Live Monitor 启动中..."
Write-Host "   扫描间隔: 5 分钟"
Write-Host "   推送目标: 飞书手机端"
Write-Host "   关闭窗口即停止"
Write-Host ""

C:\ComfyUI-aki-v1.3\python\python.exe scripts\live_monitor.py --daemon
