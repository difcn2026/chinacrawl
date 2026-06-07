# ============================================
# VPS Proxy Bootstrap - Run as Admin
# Single script, downloads everything from GitHub
# ============================================
#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"
$Base = "C:\proxy"
$HttpPort = 3128
$SocksPort = 1080

Write-Host "[1/4] Downloading 3proxy..." -ForegroundColor Yellow
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\3p.zip"
Invoke-WebRequest -Uri "https://github.com/3proxy/3proxy/releases/download/0.9.6/3proxy-0.9.6.1-x64.zip" -OutFile $zip -UseBasicParsing

Write-Host "[2/4] Extracting..." -ForegroundColor Yellow
if (Test-Path $Base) { Remove-Item -Recurse -Force $Base }
Expand-Archive $zip "$env:TEMP\3p"
Move-Item "$env:TEMP\3p\3proxy" $Base -Force
Remove-Item $zip -Force
Remove-Item "$env:TEMP\3p" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory "$Base\logs" -Force | Out-Null

Write-Host "[3/4] Configuring..." -ForegroundColor Yellow
$VPS_IP = (Invoke-RestMethod "http://httpbin.org/ip" -UseBasicParsing).origin.Trim()
@"
nserver 8.8.8.8
nserver 1.1.1.1
nscache 65536
timeouts 1 5 30 60 180 1800 15 60
maxconn 1000
log "$Base\logs\proxy.log" D
logformat "L%d-%m-%Y %H:%M:%S %z %N %C %R:%r %Q %O %I %h %T"
internal 0.0.0.0
external $VPS_IP
users "proxyuser:CL:StrongProxyPass2024!"
auth strong
allow * * * * *
proxy -p$HttpPort
socks -p$SocksPort
"@ | Out-File "$Base\cfg\proxy.cfg" -Encoding ascii

Write-Host "[4/4] Installing service..." -ForegroundColor Yellow
netsh advfirewall firewall add rule name="Proxy HTTP" dir=in action=allow protocol=TCP localport=$HttpPort 2>$null
netsh advfirewall firewall add rule name="Proxy SOCKS5" dir=in action=allow protocol=TCP localport=$SocksPort 2>$null
sc.exe stop ProxySvc 2>$null
sc.exe delete ProxySvc 2>$null
New-Service -Name ProxySvc -BinaryPathName "`"$Base\bin64\3proxy.exe`" `"$Base\cfg\proxy.cfg`"" -DisplayName "Proxy Server" -StartupType Automatic
sc.exe failure ProxySvc reset=86400 actions=restart/5000/restart/10000/restart/30000
Start-Service ProxySvc

Write-Host "============================================" -ForegroundColor Green
Write-Host "  PROXY READY" -ForegroundColor Green
Write-Host "  HTTP:   $VPS_IP`:$HttpPort" -ForegroundColor White
Write-Host "  SOCKS5: $VPS_IP`:$SocksPort" -ForegroundColor White
Write-Host "  Auth:   proxyuser / StrongProxyPass2024!" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
