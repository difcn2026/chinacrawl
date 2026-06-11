<#
.SYNOPSIS
    ChinaCrawl VPS 健康监控 — 一键检查所有基础设施服务状态

.DESCRIPTION
    检查 VPS 可达性、代理端口、SearXNG 搜索后端、Landing Page，输出彩色状态报告。

.PARAMETER Quiet
    静默模式，仅输出摘要行，适合 cron / 计划任务

.PARAMETER Json
    输出 JSON 格式结果，适合接入监控系统

.PARAMETER Timeout
    单项检查超时(秒)，默认 10

.EXAMPLE
    .\check-vps.ps1
    .\check-vps.ps1 -Quiet
    .\check-vps.ps1 -Json

.NOTES
    最后更新: 2026-06-11 | 作者: 小黑 (Xiao Hei)
#>

param(
    [switch]$Quiet,
    [switch]$Json,
    [int]$Timeout = 10
)

# ── 配置 ────────────────────────────────────────────────────────────────
$VPS_HOST       = "107.172.62.24"
$CLOUD_HOST     = "47.236.24.76"
$PROXY_USER     = "proxyuser"
$PROXY_PASS     = 'StrongProxyPass2024!'
$SOCKS5_PORT    = 1080
$HTTP_PORT      = 3128
$RDP_PORT       = 3389
$WINRM_PORT     = 5985
$SEARXNG_URL    = "http://47.236.24.76:9999"
$LANDING_URL    = "http://47.236.24.76:7777/chinacrawl/"
$LOCAL_BRIDGE   = "127.0.0.1"
$LOCAL_PORT     = 3128
$TEST_URL       = "https://www.google.com"
$TEST_URL_CN    = "https://www.baidu.com"

# ── 状态收集 ────────────────────────────────────────────────────────────
$results = [System.Collections.ArrayList]::new()

function Add-Result {
    param([string]$Name, [string]$Status, [string]$Detail, [int]$LatencyMs = 0)
    [void]$results.Add(@{
        Name      = $Name
        Status    = $Status   # pass / fail / warn / skip
        Detail    = $Detail
        LatencyMs = $LatencyMs
    })
}

# ── 输出辅助 ────────────────────────────────────────────────────────────
function Write-Status {
    param([string]$Name, [string]$Status, [string]$Detail, [int]$LatencyMs = 0)
    if ($Quiet) { return }

    $icon = switch ($Status) {
        "pass" { "✓" }
        "fail" { "✗" }
        "warn" { "⚠" }
        "skip" { "○" }
    }
    $color = switch ($Status) {
        "pass" { "Green" }
        "fail" { "Red" }
        "warn" { "Yellow" }
        "skip" { "DarkGray" }
    }

    $latencyStr = if ($LatencyMs -gt 0) { " (${LatencyMs}ms)" } else { "" }
    Write-Host "  $icon " -NoNewline -ForegroundColor $color
    Write-Host "$Name" -NoNewline
    Write-Host "$latencyStr" -NoNewline -ForegroundColor DarkGray
    if ($Detail) {
        Write-Host " — $Detail" -NoNewline -ForegroundColor DarkGray
    }
    Write-Host ""
}

# ── 检查函数 ────────────────────────────────────────────────────────────
function Test-Port {
    param([string]$HostName, [int]$Port, [string]$Label)
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $tcp = Test-NetConnection -ComputerName $HostName -Port $Port -WarningAction SilentlyContinue -ErrorAction Stop
        $sw.Stop()
        if ($tcp.TcpTestSucceeded) {
            Add-Result -Name $Label -Status "pass" -Detail "端口开放" -LatencyMs $sw.ElapsedMilliseconds
            Write-Status -Name $Label -Status "pass" -Detail "端口开放" -LatencyMs $sw.ElapsedMilliseconds
            return $true
        } else {
            Add-Result -Name $Label -Status "fail" -Detail "端口不通"
            Write-Status -Name $Label -Status "fail" -Detail "端口不通"
            return $false
        }
    } catch {
        Add-Result -Name $Label -Status "fail" -Detail "连接异常: $($_.Exception.Message)"
        Write-Status -Name $Label -Status "fail" -Detail "连接异常"
        return $false
    }
}

function Test-ProxyHTTP {
    param([string]$ProxyUrl, [string]$Label)
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $response = curl -x $ProxyUrl -s -o NUL -w "%{http_code}" --max-time $Timeout $TEST_URL 2>$null
        $sw.Stop()
        if ($response -eq "200") {
            Add-Result -Name $Label -Status "pass" -Detail "HTTP 200" -LatencyMs $sw.ElapsedMilliseconds
            Write-Status -Name $Label -Status "pass" -Detail "HTTP 200" -LatencyMs $sw.ElapsedMilliseconds
            return $true
        } elseif ($response -match '^[23]\d\d$') {
            Add-Result -Name $Label -Status "pass" -Detail "HTTP $response" -LatencyMs $sw.ElapsedMilliseconds
            Write-Status -Name $Label -Status "pass" -Detail "HTTP $response" -LatencyMs $sw.ElapsedMilliseconds
            return $true
        } else {
            Add-Result -Name $Label -Status "fail" -Detail "HTTP $response"
            Write-Status -Name $Label -Status "fail" -Detail "HTTP $response"
            return $false
        }
    } catch {
        Add-Result -Name $Label -Status "fail" -Detail "请求失败"
        Write-Status -Name $Label -Status "fail" -Detail "请求失败"
        return $false
    }
}

function Test-HTTPEndpoint {
    param([string]$Url, [string]$Label)
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $response = curl -s -o NUL -w "%{http_code}" --max-time $Timeout $Url 2>$null
        $sw.Stop()
        if ($response -eq "200") {
            Add-Result -Name $Label -Status "pass" -Detail "HTTP 200" -LatencyMs $sw.ElapsedMilliseconds
            Write-Status -Name $Label -Status "pass" -Detail "HTTP 200" -LatencyMs $sw.ElapsedMilliseconds
            return $true
        } elseif ($response -match '^[23]\d\d$') {
            Add-Result -Name $Label -Status "pass" -Detail "HTTP $response" -LatencyMs $sw.ElapsedMilliseconds
            Write-Status -Name $Label -Status "pass" -Detail "HTTP $response" -LatencyMs $sw.ElapsedMilliseconds
            return $true
        } else {
            Add-Result -Name $Label -Status "fail" -Detail "HTTP $response"
            Write-Status -Name $Label -Status "fail" -Detail "HTTP $response"
            return $false
        }
    } catch {
        Add-Result -Name $Label -Status "fail" -Detail "请求失败"
        Write-Status -Name $Label -Status "fail" -Detail "请求失败"
        return $false
    }
}

# ── 主检查流程 ──────────────────────────────────────────────────────────
function Start-Check {
    if (-not $Quiet) {
        Write-Host ""
        Write-Host "╔══════════════════════════════════════════════════╗"
        Write-Host "║   ChinaCrawl VPS 健康监控                         ║"
        Write-Host "║   检查时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')                  ║"
        Write-Host "╚══════════════════════════════════════════════════╝"
        Write-Host ""
    }

    # ── 第1组: VPS 基础可达性 ──
    if (-not $Quiet) { Write-Host "── VPS 基础可达性 ($VPS_HOST) ──" -ForegroundColor Cyan }

    # Ping
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $ping = Test-Connection -ComputerName $VPS_HOST -Count 2 -Quiet -ErrorAction Stop
        $sw.Stop()
        if ($ping) {
            Add-Result -Name "VPS Ping" -Status "pass" -Detail "可达" -LatencyMs $sw.ElapsedMilliseconds
            Write-Status -Name "VPS Ping" -Status "pass" -Detail "可达" -LatencyMs $sw.ElapsedMilliseconds
        } else {
            Add-Result -Name "VPS Ping" -Status "fail" -Detail "不可达"
            Write-Status -Name "VPS Ping" -Status "fail" -Detail "不可达 — 检查管理面板"
        }
    } catch {
        Add-Result -Name "VPS Ping" -Status "fail" -Detail "超时/无响应"
        Write-Status -Name "VPS Ping" -Status "fail" -Detail "超时/无响应"
    }

    # RDP & WinRM 端口
    Test-Port -HostName $VPS_HOST -Port $RDP_PORT -Label "RDP (3389)"
    Test-Port -HostName $VPS_HOST -Port $WINRM_PORT -Label "WinRM (5985)"

    # ── 第2组: 代理服务 ──
    if (-not $Quiet) { Write-Host ""; Write-Host "── 代理服务 ($VPS_HOST) ──" -ForegroundColor Cyan }

    # SOCKS5 端口
    Test-Port -HostName $VPS_HOST -Port $SOCKS5_PORT -Label "SOCKS5 端口 (1080)"

    # SOCKS5 代理实测
    $socks5Proxy = "socks5h://${PROXY_USER}:${PROXY_PASS}@${VPS_HOST}:${SOCKS5_PORT}"
    Test-ProxyHTTP -ProxyUrl $socks5Proxy -Label "SOCKS5 代理实测"

    # HTTP 端口
    Test-Port -HostName $VPS_HOST -Port $HTTP_PORT -Label "HTTP 代理端口 (3128)"

    # HTTP 代理实测
    $httpProxy = "http://${PROXY_USER}:${PROXY_PASS}@${VPS_HOST}:${HTTP_PORT}"
    Test-ProxyHTTP -ProxyUrl $httpProxy -Label "HTTP 代理实测"

    # ── 第3组: 本地桥接 ──
    if (-not $Quiet) { Write-Host ""; Write-Host "── 本地桥接 (127.0.0.1:3128) ──" -ForegroundColor Cyan }

    Test-Port -HostName $LOCAL_BRIDGE -Port $LOCAL_PORT -Label "本地桥接端口"
    $localProxy = "http://${LOCAL_BRIDGE}:${LOCAL_PORT}"
    Test-ProxyHTTP -ProxyUrl $localProxy -Label "本地桥接实测"

    # ── 第4组: 云服务器服务 ──
    if (-not $Quiet) { Write-Host ""; Write-Host "── 云服务器 ($CLOUD_HOST) ──" -ForegroundColor Cyan }

    # SearXNG
    Test-HTTPEndpoint -Url "$SEARXNG_URL/search?q=test&format=json" -Label "SearXNG (:9999)"

    # Landing Page
    Test-HTTPEndpoint -Url $LANDING_URL -Label "Landing Page (:7777)"

    # ── 汇总 ──
    if (-not $Quiet) { Write-Host "" }

    $total   = $results.Count
    $passed  = ($results | Where-Object { $_.Status -eq "pass" }).Count
    $failed  = ($results | Where-Object { $_.Status -eq "fail" }).Count
    $warned  = ($results | Where-Object { $_.Status -eq "warn" }).Count

    if (-not $Quiet) {
        Write-Host "── 汇总 ──" -ForegroundColor Cyan
        Write-Host "  总计: $total  通过: " -NoNewline
        Write-Host $passed -NoNewline -ForegroundColor Green
        Write-Host "  失败: " -NoNewline
        Write-Host $failed -NoNewline -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "DarkGray" })
        if ($warned -gt 0) {
            Write-Host "  警告: " -NoNewline
            Write-Host $warned -NoNewline -ForegroundColor Yellow
        }
        Write-Host ""
        Write-Host ""

        if ($failed -eq 0) {
            Write-Host "  全部服务正常 ✓" -ForegroundColor Green
        } else {
            Write-Host "  $failed 项服务异常 — 请参考 chinacrawl/docs/vps-recovery.md" -ForegroundColor Red
        }
        Write-Host ""
    } else {
        # 静默模式一行输出
        $statusIcon = if ($failed -eq 0) { "✓" } else { "✗" }
        $statusColor = if ($failed -eq 0) { "Green" } else { "Red" }
        Write-Host "$statusIcon VPS: $passed/$total passed" -ForegroundColor $statusColor
    }
}

function Out-JsonReport {
    $report = @{
        timestamp    = (Get-Date -Format 'o')
        total        = $results.Count
        passed       = ($results | Where-Object { $_.Status -eq "pass" }).Count
        failed       = ($results | Where-Object { $_.Status -eq "fail" }).Count
        healthy      = ($results | Where-Object { $_.Status -eq "fail" }).Count -eq 0
        checks       = $results | ForEach-Object {
            @{
                name       = $_.Name
                status     = $_.Status
                detail     = $_.Detail
                latency_ms = $_.LatencyMs
            }
        }
    }
    $report | ConvertTo-Json -Depth 3
}

# ── 入口 ────────────────────────────────────────────────────────────────
Start-Check

if ($Json) {
    Out-JsonReport
}

# 退出码: 非0 表示有失败项
$failedCount = ($results | Where-Object { $_.Status -eq "fail" }).Count
exit $failedCount
