# ============================================
# Minimal HTTP/SOCKS5 Proxy â€?Zero dependencies
# Usage: powershell -File proxy.ps1 [-HttpPort 3128] [-SocksPort 1080]
# ============================================
param(
    [int]$HttpPort = 3128,
    [int]$SocksPort = 1080,
    [string]$User = "proxyuser",
    [string]$Pass = "StrongProxyPass2024!"
)
$ErrorActionPreference = "Continue"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ZeroDep Proxy" -ForegroundColor Cyan
Write-Host "  HTTP: 0.0.0.0:$HttpPort | SOCKS5: 0.0.0.0:$SocksPort" -ForegroundColor Green
Write-Host "  Auth: $User / $Pass" -ForegroundColor DarkGray
Write-Host "============================================" -ForegroundColor Cyan

# --- HTTP Proxy ---
$httpSrv = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $HttpPort)
$httpSrv.Start()

# --- SOCKS5 Proxy ---
$socksSrv = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $SocksPort)
$socksSrv.Start()

Write-Host "Running. Ctrl+C to stop." -ForegroundColor Yellow

function Tunnel($a, $b) {
    $ab = New-Object byte[] 65536
    $bb = New-Object byte[] 65536
    $tasks = @()
    $tasks += [System.Threading.Tasks.Task]::Run({
        try { while(($n=$a.Read($ab,0,$ab.Length)) -gt 0){$b.Write($ab,0,$n)} } catch {}
    })
    $tasks += [System.Threading.Tasks.Task]::Run({
        try { while(($n=$b.Read($bb,0,$bb.Length)) -gt 0){$a.Write($bb,0,$n)} } catch {}
    })
    [System.Threading.Tasks.Task]::WaitAny($tasks, 120000) | Out-Null
}

function HandleHttp($client) {
    try {
        $s = $client.GetStream()
        # Read full initial payload
        $buf = New-Object byte[] 65536
        $client.ReceiveTimeout = 5000
        $total = 0
        try { $total = $s.Read($buf, 0, $buf.Length) } catch { $client.Close(); return }
        if ($total -eq 0) { $client.Close(); return }
        $header = [System.Text.Encoding]::ASCII.GetString($buf, 0, $total)

        # Auth check
        $authed = $false
        if ($header -match "Proxy-Authorization:\s*Basic\s+(\S+)") {
            $d = [System.Text.Encoding]::ASCII.GetString([System.Convert]::FromBase64String($Matches[1]))
            $parts = $d -split ':', 2
            if ($parts.Count -eq 2 -and $parts[0] -eq $User -and $parts[1] -eq $Pass) {
                $authed = $true
            }
        }
        if (-not $authed) {
            $resp = "HTTP/1.1 407 Proxy Authentication Required`r`nProxy-Authenticate: Basic realm=`"Proxy`"`r`nContent-Length: 0`r`nConnection: close`r`n`r`n"
            $s.Write([System.Text.Encoding]::ASCII.GetBytes($resp), 0, $resp.Length)
            $client.Close(); return
        }

        # Parse target
        if ($header -match "CONNECT\s+([^:\s]+):(\d+)") {
            $host = $Matches[1]; $port = [int]$Matches[2]
            $remote = New-Object System.Net.Sockets.TcpClient
            try { $remote.Connect($host, $port) } catch { $s.Close(); $client.Close(); return }
            $s.Write([System.Text.Encoding]::ASCII.GetBytes("HTTP/1.1 200 Connection Established`r`n`r`n"), 0, 46)
            Tunnel $s $remote.GetStream()
            $remote.Close()
        } elseif ($header -match "^\w+\s+http://([^:/]+)(?::(\d+))?") {
            $host = $Matches[1]; $port = if($Matches[2]){[int]$Matches[2]}else{80}
            $remote = New-Object System.Net.Sockets.TcpClient
            try { $remote.Connect($host, $port) } catch { $s.Close(); $client.Close(); return }
            $rs = $remote.GetStream()
            $rs.Write($buf, 0, $total)
            Tunnel $s $rs
            $remote.Close()
        } elseif ($header -match "^\w+\s+https://([^:/]+)(?::(\d+))?") {
            # Plaintext HTTPS -> treat as CONNECT
            $host = $Matches[1]; $port = if($Matches[2]){[int]$Matches[2]}else{443}
            $remote = New-Object System.Net.Sockets.TcpClient
            try { $remote.Connect($host, $port) } catch { $s.Close(); $client.Close(); return }
            Tunnel $s $remote.GetStream()
            $remote.Close()
        } else {
            $s.Close()
        }
    } catch {}
    finally { try { $client.Close() } catch {} }
}

function HandleSocks($client) {
    try {
        $s = $client.GetStream()
        $buf = New-Object byte[] 512

        # Greeting
        $n = $s.Read($buf, 0, 2)
        if ($n -lt 2 -or $buf[0] -ne 5) { $client.Close(); return }
        $nmethods = $buf[1]
        $s.Read($buf, 0, $nmethods) | Out-Null
        $s.Write([byte[]](5, 2), 0, 2)  # Offer user/pass auth

        # Auth (RFC 1929)
        $s.Read($buf, 0, 2) | Out-Null
        $ulen = $buf[1]; $s.Read($buf, 0, $ulen) | Out-Null
        $ruser = [System.Text.Encoding]::ASCII.GetString($buf, 0, $ulen)
        $s.Read($buf, 0, 1) | Out-Null
        $plen = $buf[0]; $s.Read($buf, 0, $plen) | Out-Null
        $rpass = [System.Text.Encoding]::ASCII.GetString($buf, 0, $plen)
        if ($ruser -ne $User -or $rpass -ne $Pass) {
            $s.Write([byte[]](1, 1), 0, 2); $client.Close(); return
        }
        $s.Write([byte[]](1, 0), 0, 2)

        # Request
        $s.Read($buf, 0, 4) | Out-Null
        if ($buf[1] -ne 1) { # Only CONNECT
            $s.Write([byte[]](5, 7, 0, 1, 0,0,0,0, 0,0), 0, 10); $client.Close(); return
        }
        $atype = $buf[3]
        if ($atype -eq 1) {  # IPv4
            $s.Read($buf, 0, 4) | Out-Null
            $thost = "$($buf[0]).$($buf[1]).$($buf[2]).$($buf[3])"
        } elseif ($atype -eq 3) {  # Domain
            $s.Read($buf, 0, 1) | Out-Null
            $len = $buf[0]; $s.Read($buf, 0, $len) | Out-Null
            $thost = [System.Text.Encoding]::ASCII.GetString($buf, 0, $len)
        } else { $client.Close(); return }
        $s.Read($buf, 0, 2) | Out-Null
        $tport = ($buf[0] -shl 8) -bor $buf[1]

        $remote = New-Object System.Net.Sockets.TcpClient
        try { $remote.Connect($thost, $tport) } catch {
            $s.Write([byte[]](5, 4, 0, 1, 0,0,0,0, 0,0), 0, 10); $client.Close(); return
        }
        $s.Write([byte[]](5, 0, 0, 1, 0,0,0,0, 0,0), 0, 10)
        Tunnel $s $remote.GetStream()
        $remote.Close()
    } catch {}
    finally { try { $client.Close() } catch {} }
}

# Main event loop
while ($true) {
    if ($httpSrv.Pending()) {
        $c = $httpSrv.AcceptTcpClient()
        [System.Threading.ThreadPool]::QueueUserWorkItem({ HandleHttp $args[0] }, $c)
    }
    if ($socksSrv.Pending()) {
        $c = $socksSrv.AcceptTcpClient()
        [System.Threading.ThreadPool]::QueueUserWorkItem({ HandleSocks $args[0] }, $c)
    }
    Start-Sleep -Milliseconds 50
}
