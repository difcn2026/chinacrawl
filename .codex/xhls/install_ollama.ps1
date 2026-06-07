# Ollama background installer for XHLS
$ProgressPreference = 'SilentlyContinue'
$installer = "$env:TEMP\OllamaSetup.exe"
$readyFile = "$env:TEMP\ollama_ready.txt"

try {
    Write-Host "[XHLS] Downloading Ollama..."
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installer -UseBasicParsing -TimeoutSec 600
    Write-Host "[XHLS] Installing Ollama..."
    Start-Process -FilePath $installer -ArgumentList "/S" -Wait -NoNewWindow
    Remove-Item $installer -Force
    Write-Host "[XHLS] Ollama installed. Pulling phi3:mini..."
    & "ollama" "pull" "phi3:mini"
    "OLLAMA_READY" | Out-File $readyFile -Encoding UTF8
    Write-Host "[XHLS] Done! phi3:mini ready."
} catch {
    "OLLAMA_FAILED: $_" | Out-File $readyFile -Encoding UTF8
    Write-Host "[XHLS] Failed: $_"
}
