# ============================================
# 3proxy Setup for Windows VPS
# Run as Administrator on: 107.172.62.25
# ============================================
#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"
$ProxyBase = "C:\3proxy"
$ProxyPort = 3128
$SocksPort = 1080
$VPS_IP = "107.172.62.25"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  3proxy v0.9.6 Setup" -ForegroundColor Cyan
Write-Host "  HTTP: $VPS_IP`:$ProxyPort | SOCKS5: $VPS_IP`:$SocksPort" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# --- 1. Download ---
Write-Host "[1/5] Downloading 3proxy 0.9.6..." -ForegroundColor Yellow
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ZipUrl = "https://github.com/3proxy/3proxy/releases/download/0.9.6/3proxy-0.9.6.1-x64.zip"
$ZipPath = "$env:TEMP\3proxy.zip"
Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing

# --- 2. Extract ---
Write-Host "[2/5] Extracting..." -ForegroundColor Yellow
if (Test-Path $ProxyBase) { Remove-Item -Recurse -Force $ProxyBase }
Expand-Archive -Path $ZipPath -DestinationPath "$env:TEMP\3proxy_extract" -Force
# The zip contains a '3proxy' subfolder
Move-Item -Path "$env:TEMP\3proxy_extract\3proxy" -Destination $ProxyBase -Force
Remove-Item -Recurse -Force "$env:TEMP\3proxy_extract" -ErrorAction SilentlyContinue
Remove-Item $ZipPath -ErrorAction SilentlyContinue
Write-Host "  Extracted to $ProxyBase" -ForegroundColor Green

# --- 3. Config ---
Write-Host "[3/5] Writing config..." -ForegroundColor Yellow
$CfgPath = "$ProxyBase\cfg\3proxy.cfg"
New-Item -ItemType Directory -Path "$ProxyBase\logs" -Force | Out-Null

@"
# ============================================
# 3proxy config — HTTP/SOCKS5 upstream proxy
# ============================================
service
nserver 8.8.8.8
nserver 1.1.1.1
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
maxconn 1000

# Plugin path (required for SSL, auth plugins)
plugin "$ProxyBase\bin64\SSLPlugin.dll"
plugin "$ProxyBase\bin64\StringsPlugin.dll"
plugin "$ProxyBase\bin64\TrafficPlugin.dll"

# Logging
log "$ProxyBase\logs\3proxy.log" D
logformat "L%d-%m-%Y %H:%M:%S %z %N %C %R:%r %Q %O %I %h %T"

# Network: listen on all, use VPS IP for outgoing
internal 0.0.0.0
external $VPS_IP

# Authentication
users "proxyuser:CL:StrongProxyPass2024!"
auth strong

# Allow all authenticated users
allow * * * * *

# HTTP/HTTPS proxy
proxy -p$ProxyPort

# SOCKS5 proxy
socks -p$SocksPort
"@ | Out-File -FilePath $CfgPath -Encoding ascii

Write-Host "  Config written" -ForegroundColor Green

# --- 4. Firewall ---
Write-Host "[4/5] Configuring Firewall..." -ForegroundColor Yellow
netsh advfirewall firewall delete rule name="3proxy HTTP" 2>$null
netsh advfirewall firewall delete rule name="3proxy SOCKS5" 2>$null
netsh advfirewall firewall add rule name="3proxy HTTP" dir=in action=allow protocol=TCP localport=$ProxyPort
netsh advfirewall firewall add rule name="3proxy SOCKS5" dir=in action=allow protocol=TCP localport=$SocksPort
Write-Host "  Ports $ProxyPort + $SocksPort opened" -ForegroundColor Green

# --- 5. Install Service ---
Write-Host "[5/5] Installing Windows Service..." -ForegroundColor Yellow

Stop-Process -Name "3proxy" -Force -ErrorAction SilentlyContinue
sc.exe stop 3proxy 2>$null
sc.exe delete 3proxy 2>$null
Start-Sleep 2

$Bin = "$ProxyBase\bin64\3proxy.exe"
New-Service -Name "3proxy" `
    -BinaryPathName "`"$Bin`" `"$CfgPath`"" `
    -DisplayName "3proxy Proxy Server" `
    -Description "HTTP/HTTPS + SOCKS5 upstream proxy" `
    -StartupType Automatic

sc.exe failure 3proxy reset=86400 actions=restart/5000/restart/10000/restart/30000
Start-Service 3proxy
Write-Host "  Service running" -ForegroundColor Green

# --- Done ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Proxy Ready!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  HTTP:   $VPS_IP`:$ProxyPort" -ForegroundColor White
Write-Host "  SOCKS5: $VPS_IP`:$SocksPort" -ForegroundColor White
Write-Host "  User:   proxyuser" -ForegroundColor White
Write-Host "  Pass:   StrongProxyPass2024!" -ForegroundColor White
Write-Host ""
Write-Host "  Test: curl -x http://proxyuser:StrongProxyPass2024!@$VPS_IP`:$ProxyPort https://www.google.com" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Config: $CfgPath" -ForegroundColor Yellow
Write-Host "  Logs:   $ProxyBase\logs\" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
