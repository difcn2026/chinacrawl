@echo off
REM Start XHLS MCP Bridge (SSE mode)
cd /d "C:\Users\Administrator\Documents\New project\.codex"
C:\ComfyUI-aki-v1.3\python\python.exe -m xhls.xhls_mcp.cli serve --sse --port 8200
pause
