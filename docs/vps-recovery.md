# VPS 恢复检查清单 — ChinaCrawl 基础设施

> 最后更新：2026-06-11 | 适用：VPS 107.172.62.24 离线恢复 + 附属服务验证

---

## 〇、基础设施总览

| 资产 | 地址 | 用途 | 系统 |
|------|------|------|------|
| **VPS 代理** | `107.172.62.24` | 3proxy (SOCKS5:1080 + HTTP:3128)，RDP:3389 | Windows |
| **云服务器** | `47.236.24.76` | SearXNG :9999，Landing Page :7777 | Linux |
| **管理面板** | https://nerdvm.racknerd.com/ | VPS 控制台 (vmuser339307) | Web |
| **本地代理** | `127.0.0.1:3128` | socks-bridge → VPS SOCKS5 | Windows |

---

## 一、VPS 可达性诊断（由浅入深）

### 1.1 Ping 通性

```powershell
# 本地执行
Test-Connection -ComputerName 107.172.62.24 -Count 3
```

- **通** → VPS 在线，网络层正常，跳到 1.2
- **不通** → 登录管理面板 https://nerdvm.racknerd.com/ 查看 VPS 状态
  - 若 VPS 显示 Running：检查 Windows 防火墙是否拦截 ICMP
  - 若 VPS 显示 Stopped/Off：点击 Start 开机，等待 2 分钟后重试 ping

### 1.2 RDP 端口探测

```powershell
Test-NetConnection -ComputerName 107.172.62.24 -Port 3389
```

- **TcpTestSucceeded: True** → RDP 服务在线，跳到 1.3
- **False** → 可能原因：
  - VPS 刚开机，Windows 尚未完全启动（等待 3-5 分钟）
  - Windows 防火墙未放行 3389
  - RDP 服务未运行 → 通过管理面板 VNC 登录手动启动

### 1.3 RDP 登录

```
地址: 107.172.62.24:3389
用户名: Administrator
密码:   (VPS 管理员密码，见密码管理器)
```

> **备选**: 管理面板内置 VNC 控制台，可在 RDP 不通时作为救命通道。

### 1.4 WinRM 远程管理（可选，推荐）

```powershell
# 首次需添加 TrustedHosts
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "107.172.62.24"

# 测试连接
Test-WSMan -ComputerName 107.172.62.24 -Port 5985
```

连接成功后，后续所有 VPS 操作可用远程命令执行，无需 RDP 桌面。

---

## 二、3proxy 代理服务恢复

### 2.1 检查 3proxy 是否运行

**通过 RDP 登录后在 VPS 上执行：**

```cmd
# 方法1：检查进程
tasklist | findstr 3proxy

# 方法2：检查端口监听
netstat -an | findstr ":1080"
netstat -an | findstr ":3128"
```

**通过 WinRM 远程执行：**

```powershell
$cred = New-Object PSCredential("Administrator", (ConvertTo-SecureString "密码" -AsPlainText -Force))
Invoke-Command -ComputerName 107.172.62.24 -Credential $cred -Port 5985 -ScriptBlock {
    Get-Process -Name "3proxy" -ErrorAction SilentlyContinue
    netstat -an | Select-String ":1080|:3128"
}
```

### 2.2 启动 3proxy

```cmd
:: VPS 上执行
C:\proxy\bin64\3proxy.exe C:\proxy\cfg\proxy.cfg
```

或在 WinRM 中：

```powershell
Invoke-Command -ComputerName 107.172.62.24 -Credential $cred -Port 5985 -ScriptBlock {
    $p = [WMIClass]"\\localhost\ROOT\CIMV2:Win32_Process"
    $p.Create('C:\proxy\bin64\3proxy.exe C:\proxy\cfg\proxy.cfg')
}
```

### 2.3 验证 Registry Run 自启键（防止重启后丢失）

```powershell
# VPS 上执行
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" | Select-Object 3proxy
```

期望输出包含: `C:\proxy\bin64\3proxy.exe C:\proxy\cfg\proxy.cfg`

若无此键，写入：

```powershell
Set-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "3proxy" -Value 'C:\proxy\bin64\3proxy.exe C:\proxy\cfg\proxy.cfg'
```

### 2.4 代理连通性验证

```powershell
# 本地执行 — SOCKS5 直连
curl -x socks5h://proxyuser:StrongProxyPass2024!@107.172.62.24:1080 -s -o NUL -w "SOCKS5: %{http_code}\n" https://www.google.com

# 本地执行 — HTTP 直连
curl -x http://proxyuser:StrongProxyPass2024!@107.172.62.24:3128 -s -o NUL -w "HTTP:   %{http_code}\n" https://github.com

# 本地执行 — 本地桥接（无认证，推荐日常用）
curl -x http://127.0.0.1:3128 -s -o NUL -w "Bridge: %{http_code}\n" https://www.google.com
```

期望：全部返回 `200`。

---

## 三、SearXNG 搜索后端恢复（47.236.24.76）

### 3.1 检查 SearXNG 是否响应

```powershell
# 本地执行
curl -s -o NUL -w "%{http_code}" http://47.236.24.76:9999/search?q=test
```

期望: `200` 或 `3xx`

### 3.2 重启 SearXNG（Docker）

SSH 到 47.236.24.76 后执行：

```bash
# 检查容器状态
docker ps -a | grep searxng

# 重启
docker restart searxng

# 若容器不存在（极端情况），重新创建
docker run -d --name searxng \
  -p 9999:8080 \
  -v /etc/searxng:/etc/searxng:rw \
  --restart unless-stopped \
  searxng/searxng
```

### 3.3 功能验证

```bash
# 在 VPS 上（经代理）或直接 curl
curl -X POST http://47.236.24.76:9999/search \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "q=测试&format=json"
```

期望返回 JSON 结果数组。

---

## 四、Landing Page 验证（47.236.24.76:7777）

### 4.1 检查 HTTP 服务

```powershell
# 本地执行
curl -s -o NUL -w "Status: %{http_code}" http://47.236.24.76:7777/chinacrawl/
```

期望: `200`

### 4.2 Landing Page 服务恢复

SSH 到 47.236.24.76 后：

```bash
# 检查 nginx/apache 状态
systemctl status nginx   # 或 apache2

# 重启 Web 服务
systemctl restart nginx

# 验证文件存在
ls -la /var/www/chinacrawl/index.html   # 路径以实际部署为准
```

---

## 五、完整恢复流程（推荐顺序）

```
┌─────────────────────────────────────────────────┐
│ ① 登录管理面板 → 确认 VPS 状态 (Running)          │
│ ② Ping 107.172.62.24 → 确认网络可达              │
│ ③ RDP / WinRM 登录 → 进入系统                    │
│ ④ 检查/启动 3proxy → 恢复代理                     │
│ ⑤ 验证代理端口 (1080, 3128) → 外部连通性确认      │
│ ⑥ SSH 47.236.24.76 → 检查 SearXNG + Web 服务     │
│ ⑦ 全面端到端验证 → 搜素 + 爬取实测                │
└─────────────────────────────────────────────────┘
```

---

## 六、故障排查树

### A. VPS 完全不通

```
VPS 不通
├─ 管理面板显示 Stopped → 开机，等 2 分钟
├─ 管理面板显示 Running 但 ping 不通
│  ├─ 换用 VNC 登录 → 检查 Windows 防火墙
│  │  netsh advfirewall firewall show rule name=all | findstr "ICMP"
│  └─ 检查网络配置 → ipconfig /all，确认 IP 未变
└─ 管理面板也打不开 → 联系 RackNerd 支持
```

### B. 代理端口不通

```
curl 代理返回 000 / timeout
├─ VPS 本地 netstat -an | findstr "1080" → 无输出
│  └─ 3proxy 未运行 → 手动启动或检查 Registry Run 键
├─ VPS 本地 netstat 有监听，外部不通
│  └─ Windows 防火墙未放行 → 添加入站规则
│     netsh advfirewall firewall add rule name="3proxy" dir=in action=allow protocol=tcp localport=1080,3128
└─ 外部可连但认证失败 (407)
   └─ 检查 proxy.cfg 中用户密码是否正确
      type C:\proxy\cfg\proxy.cfg | findstr "proxyuser"
```

### C. SearXNG 无响应

```
http://47.236.24.76:9999 不通
├─ SSH 到 47.236.24.76 → docker ps | grep searxng
│  ├─ 容器不在 → docker start searxng 或重建
│  └─ 容器在但端口不通 → docker logs searxng 查看日志
├─ SSH 也不通 → 阿里云控制台检查 ECS 实例状态
└─ 本地能访问但返回错误 → 检查 SearXNG settings.yml 引擎配置
```

### D. Landing Page 不响应

```
http://47.236.24.76:7777/chinacrawl/ 不通
├─ SSH → systemctl status nginx → 未运行则 restart
├─ nginx 运行但 404 → 检查站点配置和文件路径
└─ 502 Bad Gateway → 检查 nginx error.log
```

---

## 七、快速验证一键脚本

恢复完成后，本地执行：

```powershell
# 保存为 check-vps.ps1 运行
.\chinacrawl\docs\check-vps.ps1
```

应输出全部绿色 ✓ 状态。

---

## 八、关键文件索引

| 文件 | 位置 | 说明 |
|------|------|------|
| 3proxy 配置 | `C:\proxy\cfg\proxy.cfg` (VPS) | 代理主配置 |
| 3proxy 日志 | `C:\proxy\logs\proxy.log` (VPS) | 故障诊断 |
| 3proxy 可执行 | `C:\proxy\bin64\3proxy.exe` (VPS) | v0.9.6 |
| 本机 3proxy | `C:\proxy\cfg\proxy.cfg` (本地) | SOCKS5 :1080 |
| socks-bridge | `tools/socks-bridge.js` (本地) | HTTP→SOCKS5 桥接 |
| Landing Page | `chinacrawl/docs/index.html` (本地) | 源文件 |

---

## 九、联系与备用

- **RackNerd 管理面板**: https://nerdvm.racknerd.com/ — 账号 `vmuser339307`
- **VPS 密码**: 见密码管理器（`!` 在 PowerShell 中需单引号转义）
- **备用代理**: 本地 `127.0.0.1:1080` (3proxy SOCKS5 直接代理，无认证)
