# XHLS Network Guardian
# Monitors proxy health, auto-restarts on failure, logs everything.
# Run this in background: powershell -WindowStyle Hidden -File network-guardian.ps1

$CheckInterval = 60  # seconds between checks
$LogFile = "$PSScriptRoot\network-guardian.log"

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line
}

Log "=== XHLS Network Guardian started ==="

while ($true) {
    $issues = @()

    # 1. Check sslocal (VPS tunnel - primary path)
    $sslocal = Get-Process sslocal -ErrorAction SilentlyContinue
    if (-not $sslocal) {
        $issues += "sslocal not running"
        Log "sslocal dead - restarting..."
        try {
            Start-Process -WindowStyle Hidden -FilePath "C:\ss-client\sslocal.exe" -ArgumentList "-c", "C:\ss-client\config.json"
            Log "  sslocal restarted"
        } catch {
            Log "  sslocal restart FAILED: $_"
        }
    }

    # 2. Check socks-bridge (SOCKS5 relay)
    $bridge = Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*socks-bridge*" } 2>$null
    # Simple check: is there a node process and port 3128 listening?
    $port3128 = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq 3128 }
    if (-not $port3128) {
        $issues += "socks-bridge not listening"
        Log "socks-bridge dead - restarting..."
        try {
            $cwd = "$env:USERPROFILE\Documents\New project"
            Start-Process -WindowStyle Hidden -FilePath "node" -ArgumentList "tools/socks-bridge.js" -WorkingDirectory $cwd
            Log "  socks-bridge restarted"
        } catch {
            Log "  socks-bridge restart FAILED: $_"
        }
    }

    # 3. Check 3proxy (fallback SOCKS5)
    $p3 = Get-Process 3proxy -ErrorAction SilentlyContinue
    if (-not $p3) {
        $issues += "3proxy not running"
        Log "3proxy dead - restarting..."
        try {
            Start-Process -WindowStyle Hidden -FilePath "C:\proxy\bin64\3proxy.exe" -ArgumentList "C:\proxy\cfg\proxy.cfg"
            Log "  3proxy restarted"
        } catch {
            Log "  3proxy restart FAILED: $_"
        }
    }

    # 4. Test VPS reachability
    $vps24 = $false; $vps25 = $false
    try { $t = New-Object Net.Sockets.TcpClient; $t.Connect("107.172.62.24", 5985); $t.Close(); $vps24 = $true } catch {}
    try { $t = New-Object Net.Sockets.TcpClient; $t.Connect("107.172.62.25", 1080); $t.Close(); $vps25 = $true } catch {}
    if (-not $vps24 -and -not $vps25) {
        $issues += "Both VPS unreachable"
    }

    # 5. Test internet
    try {
        $r = Invoke-WebRequest -Uri "https://www.google.com" -TimeoutSec 10 -UseBasicParsing
        $internetOk = $true
    } catch {
        $internetOk = $false
        $issues += "Google unreachable"
    }

    # Summary
    $status = if ($issues.Count -eq 0) { "OK" } else { "ISSUES: " + ($issues -join ", ") }
    Log "Check: sslocal=$($sslocal -ne $null) bridge=$($port3128 -ne $null) p3=$($p3 -ne $null) vps24=$vps24 vps25=$vps25 net=$internetOk | $status"

    Start-Sleep $CheckInterval
}
