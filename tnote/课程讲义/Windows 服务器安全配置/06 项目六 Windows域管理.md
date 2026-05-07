### 上节课知识回顾

1. 远程桌面默认端口是多少？修改端口的目的？

> 提示：默认端口是一个四位数，范围在1024-65535之间，修改它可以减少被自动扫描工具发现的风险。

2. 修改远程桌面端口的注册表路径？

> 提示：注册表路径包含 CurrentControlSet、Terminal Server、WinStations、RDP-Tcp 等关键词。

3. 开启远程桌面后如何加固安全性？

> 提示：从端口修改、网络级身份验证、用户限制、防火墙策略、日志审计等多个维度考虑。

> **引入**：上节课我们学习了如何远程管理单台Windows服务器。但如果一个公司有500台电脑，管理员要一台一台去配置吗？有没有办法"一处配置，全网生效"？这就是本节课要学习的——**Windows域管理**。


## 知识图谱总览

```
┌──────────────────────────────────────────────────────────┐
│                     森林 (Forest)                         │
│   ┌──────────────────────────────────────────────────┐   │
│   │                   域树 (Tree)                     │   │
│   │  ┌────────────────────────────────────────────┐  │   │
│   │  │             域 (Domain)                     │  │   │
│   │  │   corp.local                               │  │   │
│   │  │  ┌────────┐ ┌────────┐  ┌────────┐        │  │   │
│   │  │  │  OU   │  │  OU    │  │  OU    │ ← 链接GPO│  │   │
│   │  │  │ 研发部 │  │ 财务部  │ │ 运维部 │        │  │   │
│   │  │  ├────────┤ ├────────┤ ├────────┤        │  │   │
│   │  │  │用户/组 │  │用户/组 │ │用户/组 │        │  │   │
│   │  │  │计算机  │  │计算机  │ │计算机  │        │  │   │
│   │  │  └────────┘ └────────┘ └────────┘        │  │   │
│   │  └────────────────────────────────────────────┘  │   │
│   └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘

核心关系：DC (域控制器) ──运行──→ AD DS ──存储──→ NTDS.dit
           │                              │
           ├── Kerberos (身份认证)         ├── 用户/计算机/组
           ├── DNS (服务定位)              ├── GPO (组策略)
           └── LDAP (目录查询)             └── OU (组织单元)
```


## 学习目标

| 层次 | 内容 |
| --- | --- |
| 知识 | 掌握域、域控制器、Active Directory的概念及相互关系；理解组策略LSDOU处理顺序及继承/强制机制；理解OU、用户、计算机账户、安全组的创建与管理 |
| 技能 | 能使用GUI和PowerShell独立完成域控制器安装配置；能将客户端加入域及退出域；能创建OU、域用户、计算机账户和安全组；能创建和链接组策略对象；能通过GPO批量部署软件、配置环境 |
| 素养 | 树立"集中管理、统一策略"的企业IT运维意识；认识到AD安全的重要性 |

## 重难点提示

| 类型 | 重难点 | 说明 |
| --- | --- | --- |
| 重点 | 域控制器的安装与配置 | 安装AD DS角色 → 提升为域控 → 配置DNS，三个环节缺一不可。DNS未指向DC是加域失败的头号原因 |
| 重点 | 组策略的创建、链接与应用 | GPO创建后必须链接到域/OU才生效；策略变更后需 gpupdate /force 刷新 |
| 重点 | AD对象管理（OU/用户/计算机/组） | 按部门创建OU、按角色创建安全组是精细化管理的基础 |
| 难点 | AD的逻辑结构（森林 → 域树 → 域 → OU → 对象） | 各层级之间的包含关系和信任关系容易混淆 |
| 难点 | LSDOU处理顺序与强制/阻止继承的优先级 | 强制(Enforced) > 阻止继承(Block Inheritance)；OU策略 > 域策略 |
| 难点 | 组策略中计算机配置与用户配置的区别 | 计算机配置开机生效（与用户无关），用户配置登录生效（跟随用户漫游） |


## 任务一 搭建域环境

### 知识点1：域（Domain）的定义和作用

#### 什么是域？

域（Domain）是Windows网络中一种**集中管理**的计算机和用户逻辑组织形式。在域环境中，所有计算机、用户账户、安全策略都由一个或多个**域控制器（Domain Controller, DC）** 进行统一管理和验证。

打个比方：**工作组就像"村民自治"** ，每家自己管自己家的门锁，谁家的钥匙开不了谁家的门；**域就像"物业管理"** ，整个小区由物业统一发门禁卡，一张卡走遍所有大门。

#### 工作组与域的对比

**基础管理对比：**

| 对比项 | 工作组 | 域 |
| --- | --- | --- |
| 管理方式 | 分散管理，每台电脑独立维护 | 集中管理，由DC统一控制 |
| 用户认证 | 本地SAM数据库，每台电脑各有各的账户 | Kerberos协议统一认证，一套账号全网通行 |
| 策略应用 | 逐台手动配置，效率低下 | GPO统一推送，一处配置全网生效 |
| 用户账户 | 仅在本机有效，换一台电脑需要重新创建 | 域内任意一台计算机都可以用域账号登录 |
| 密码修改 | 改一次只改本机，其他机器不受影响 | 改一次全网生效 |

**安全与运维对比：**

| 对比项 | 工作组 | 域 |
| --- | --- | --- |
| 适用规模 | 10台以下的小型网络 | 10台以上的中大型企业网络 |
| 单点故障 | 无，每台计算机独立运行 | 存在，DC宕机影响全网认证 |
| 实施成本 | 低，无需额外服务器 | 较高，需要专用服务器部署DC |
| 安全性 | 较低，策略不统一 | 高，统一安全基线 |

> 口诀：工作组 = 村民自治（每家自己管锁），域 = 物业管理（一张门禁卡走遍小区）

#### 域的四大核心优势

**1. 集中身份认证**

在域环境中，所有用户账户信息存储在域控制器的Active Directory数据库中。用户只需要记住**一个账号和密码**，就可以登录域内任意一台计算机。认证过程使用**Kerberos协议**（默认），该协议采用票据机制，密码不会在网络上明文传输，安全性远高于NTLM。

实际场景：员工张三无论坐在工位A的电脑、会议室B的电脑，还是财务室C的电脑，都用同一个账号 `CORP\zhangsan` 登录，他的桌面壁纸、文件快捷方式、网络驱动器映射都会自动跟随。

**2. 集中策略管理（GPO）**

管理员在域控制器上创建**组策略对象（GPO）** ，可以将安全策略、桌面限制、软件安装等配置统一推送到域内的计算机和用户。不需要逐台电脑去手动配置。

实际场景：公司要求所有员工密码长度至少8位、90天必须更换密码。在工作组环境中，管理员需要登录到500台电脑逐一设置；在域环境中，管理员只需创建一个GPO，链接到域，500台电脑一次性全部生效。

**3. 软件集中部署**

通过组策略的"软件安装"功能，管理员可以将 .msi 安装包发布或分配给域用户/计算机。用户下次登录或计算机下次启动时，软件会自动安装。

实际场景：公司要全员安装杀毒软件，管理员将杀毒软件的.msi包放入组策略，第二天所有员工开机后杀毒软件就已经自动安装好了。

**4. 资源统一管理**

通过**DFS（分布式文件系统）** 和AD权限管理，企业可以统一管理文件服务器、打印机、共享文件夹等资源。用户在域内搜索资源就像访问本地磁盘一样方便。

> 核心协议：Kerberos（认证） + LDAP（目录查询）。Kerberos负责"你是谁"的身份验证，LDAP负责"查找谁在哪里"的目录服务。


### 实验1：理解域环境——查看当前计算机的工作组/域状态

**GUI操作步骤：**

1. 右键桌面上的"此电脑"图标，选择"属性"
2. 在弹出的系统窗口中，找到"计算机名、域和工作组设置"区域
3. 记录当前的工作组名称（默认安装的Windows通常为 WORKGROUP）
4. 注意观察"域："字段，如果是空白则说明当前不在域中

**PowerShell方式：**

```powershell
# 查看当前计算机是否已加入域
Get-WmiObject -Class Win32_ComputerSystem | Select-Object Name, Domain, Workgroup, PartOfDomain
```

输出说明：

- `PartOfDomain = True` 表示已加入域，此时 `Domain` 字段显示域名
- `PartOfDomain = False` 表示在工作组中，此时 `Workgroup` 字段显示工作组名

**预期输出示例（工作组模式）：**

```
Name       Domain     Workgroup  PartOfDomain
----       ------     ---------  -------------
WIN-CLIENT            WORKGROUP          False
```


### 知识点2：域控制器（DC）与Active Directory

#### 域控制器的定义与五大职责

域控制器（Domain Controller，简称DC）是域环境中的**核心服务器**。它运行Active Directory域服务（AD DS），承担以下五大职责：

| 序号 | 职责 | 详细说明 |
| --- | --- | --- |
| 1 | 身份认证 | 验证用户的登录凭据，发放Kerberos票据，决定"谁能进来" |
| 2 | 存储目录 | 将所有用户、计算机、组的账户信息存储在AD数据库中 |
| 3 | 执行GPO | 接收和分发组策略，确保域内所有计算机策略一致 |
| 4 | DNS服务 | 运行DNS服务器，通过SRV记录帮助客户端定位DC和其他服务 |
| 5 | 管理对象 | 管理域内的用户账户、计算机账户、安全组等对象的创建/修改/删除 |

#### Active Directory的逻辑结构

AD采用分层树形结构，从大到小依次为：

```
森林（Forest）                        ← 多棵域树的集合，共享同一套Schema和配置
└── 域树（Tree）                      ← 具有连续DNS命名空间的多个域
    └── 域（Domain）                  ← 管理的基本单位，如 corp.local
        ├── 组织单元（OU）            ← 逻辑容器，用于委派管理和链接GPO
        │   ├── 用户（User）          ← 域用户账户
        │   ├── 计算机（Computer）    ← 加入域的计算机账户
        │   └── 组（Group）           ← 用户/计算机的逻辑集合
        └── 信任关系（Trust）         ← 域之间建立信任，允许跨域访问资源
```

**各层级详解：**

| 层级 | 说明 | 示例 | 类比 |
| --- | --- | --- | --- |
| 森林（Forest） | AD的最高层级容器，所有域树共享同一Schema和配置分区 | 一个集团的所有子公司共用一个森林 | 跨国公司总部 |
| 域树（Tree） | 具有连续DNS命名空间的域的集合 | corp.local、hr.corp.local、it.corp.local | 集团下的某个事业部 |
| 域（Domain） | 管理和安全策略的最基本单位 | corp.local | 一个独立的公司 |
| OU（Organizational Unit） | 域内的逻辑容器，用于组织对象和委派管理权限 | 研发部OU、财务部OU | 公司里的部门 |
| 对象（Object） | AD中的最小管理单元 | 用户zhangsan、计算机PC-001 | 公司里的员工和设备 |

> 记忆口诀：域结构从大到小——"森林域树，域下OU，OU里放对象"

#### 域信任关系

域与域之间通过**信任关系**实现跨域资源访问。信任关系决定了一个域中的用户能否访问另一个域中的资源。

**常见信任类型：**

| 信任类型 | 说明 | 典型场景 |
| --- | --- | --- |
| 父子信任 | 父域自动信任子域，双向可传递 | `corp.local` 自动信任 `asia.corp.local` |
| 林根信任 | 同一森林内的域树之间自动建立信任 | `corp.local`（林根）信任 `subsidiary.local` |
| 林信任 | 不同森林之间手动建立的信任关系 | 集团并购另一公司后，两套AD林需要互通 |
| 外部信任 | 非连续命名空间的域之间手动建立信任 | `corp.local` 与 `partner.local` 建立单向信任 |

> **关键概念**：默认情况下，一个森林内所有域之间存在**双向可传递信任**。A信任B，B信任C，则A自动信任C。但跨森林的信任需要手动建立。

#### Active Directory站点（Site）

站点是AD中基于**物理网络拓扑**的划分单位，与域的逻辑结构不同。

| 对比项 | 域 (Domain) | 站点 (Site) |
| --- | --- | --- |
| 划分依据 | 逻辑组织结构（部门、职能） | 物理网络位置（城市、数据中心） |
| 划分标准 | DNS命名空间 | IP子网 |
| 主要用途 | 管理用户、计算机、策略 | 控制AD复制和客户端认证效率 |

**站点的三大作用：**

1. **优化AD复制**：同一站点内的DC之间复制频率高，跨站点复制频率低，节省广域网带宽
2. **客户端就近认证**：用户登录时优先查找同站点的DC，加快认证速度
3. **控制DFS复制**：跨站点的文件复制可设置带宽限制和日程安排

> **课堂思考**：如果公司有北京和上海两个办公地点，每个地点各有200台电脑和1台DC，应该创建几个域、几个站点？
>
> 答案：通常创建1个域（统一管理）+ 2个站点（按地理位置划分），每个站点包含当地的DC。

#### NTDS.dit数据库

Active Directory的所有数据都存储在 `C:\Windows\NTDS\NTDS.dit` 这个数据库文件中，包括：

- 所有域用户账户及其密码哈希（NTLM Hash）
- 所有计算机账户
- 组成员关系
- 组策略相关数据
- DNS区域数据（如果DC同时是DNS服务器）

> **安全警告**：NTDS.dit是攻击者（特别是内网渗透中）的核心目标。攻击者获取此文件后，可以离线暴力破解密码哈希，获取域管理员权限。因此必须严格控制DC的物理访问权限和网络访问权限。

#### 域控制器部署前检查清单

| 序号 | 检查项 | 要求 | 原因 |
| --- | --- | --- | --- |
| 1 | 静态IP | DC必须使用固定IP地址 | 客户端通过IP地址联系DC，IP变化将导致整个域瘫痪 |
| 2 | DNS服务 | DC必须安装DNS角色，或客户端DNS指向已有DNS | AD DS使用DNS的SRV记录和A记录来定位域控制器 |
| 3 | 计算机名 | 安装AD DS之前确认好计算机名 | 服务器加入域/提升为域控后，修改计算机名非常麻烦 |
| 4 | 磁盘空间 | 系统盘至少预留20GB以上的可用空间 | SYSVOL共享文件夹需要存储GPO模板和登录脚本 |
| 5 | 时间同步 | 与时间服务器偏差小于5分钟 | Kerberos认证协议对时间极其敏感，偏差>5分钟将导致认证失败 |

> 生产环境至少部署2台DC防止单点故障。如果只有一台DC宕机，整个域将无法进行用户认证。


### 实验2：安装Active Directory域服务

#### GUI操作步骤

**第一步：安装AD DS角色**

1. 打开"服务器管理器"——开机自动启动，或者按 `Win+R` 输入 `servermanager` 回车
2. 点击右上角的"管理"按钮，在下拉菜单中选择"添加角色和功能"
3. "添加角色和功能向导"窗口弹出，左侧显示安装进度，点击"下一步"
4. 在"安装类型"页面：保持默认选择"基于角色或基于功能的安装"，点击"下一步"
5. 在"服务器选择"页面：保持默认（已选中本地服务器），点击"下一步"
6. 在"服务器角色"页面：在角色列表中向下滚动，找到并勾选"Active Directory 域服务"
7. 弹出"添加Active Directory 域服务所需的功能？"对话框，点击"添加功能"
8. 确认"Active Directory 域服务"左侧复选框已勾选，点击"下一步"
9. 在"功能"页面：保持默认不做更改，点击"下一步"
10. 在"AD DS"页面：阅读后点击"下一步"
11. 在"确认"页面：勾选左下角"如果需要，自动重新启动目标服务器"，点击"安装"
12. 等待安装完成，点击"关闭"

**第二步：将服务器提升为域控制器**

1. 返回"服务器管理器"，顶部出现**黄色感叹号**，点击"将此服务器提升为域控制器"
2. **"部署配置"页面**：选择 **"添加新林"** ，输入根域名 `corp.local`，点击"下一步"
3. **"域控制器选项"页面**：
    - "域功能级别"选择 **"Windows Server 2016"**
    - "林功能级别"选择 **"Windows Server 2016"**
    - 勾选 **"域名系统(DNS)服务器"**
    - 勾选 **"全局目录(GC)服务器"** （默认勾选）
    - 设置**DSRM密码**（目录服务还原模式密码），**务必记录保存！**
    - 点击"下一步"
4. **"DNS 选项"页面**：可能出现黄色警告"无法创建DNS委派"，这是正常现象，点击"下一步"
5. **"其他选项"页面**：NetBIOS域名自动填充为 "CORP"，点击"下一步"
6. **"路径"页面**：保持默认路径，点击"下一步"
7. **"查看选项"页面**：检查所有配置摘要，点击"下一步"
8. **"先决条件检查"页面**：所有项目应显示绿色勾号，点击"安装"
9. 弹出警告"此服务器将自动重新启动"，点击"是"
10. 等待安装完成，服务器自动重启

**第三步：验证域控安装成功**

1. 重启后登录界面用户名前缀已从"计算机名"变为 **"CORP"** ，说明提升成功
2. 用 `CORP\Administrator` 登录
3. 打开"服务器管理器"，顶部应显示 **"此服务器是域控制器"**

#### PowerShell方式

```powershell
# 第一步：安装AD DS角色
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

# 第二步：将服务器提升为域控制器（创建新森林）
# 参数说明：
#   -DomainName        : 根域名
#   -DomainNetbiosName : NetBIOS名称（用于旧系统兼容）
#   -ForestMode/DomainMode : 林/域功能级别，WinThreshold = Server 2016
#   -InstallDns        : 同时安装DNS服务器角色
#   -SafeModeAdministratorPassword : DSRM密码（DC故障恢复用）
Install-ADDSForest `
  -DomainName "corp.local" `
  -DomainNetbiosName "CORP" `
  -ForestMode "WinThreshold" `
  -DomainMode "WinThreshold" `
  -InstallDns:$true `
  -SafeModeAdministratorPassword (ConvertTo-SecureString "DSRMPassword123!" -AsPlainText -Force) `
  -Force:$true

# 命令执行后服务器将自动重启
```

> DSRM密码务必保存！它是DC出现故障时进入"目录服务还原模式"进行修复的最后手段。


### 实验3：将客户端计算机加入域

#### GUI操作步骤

**第一步：配置客户端DNS指向DC**

1. 在客户端按 `Win+R` 输入 `ncpa.cpl` 回车
2. 右键当前网络适配器 → "属性" → 双击 **"Internet 协议版本 4 (TCP/IPv4)"**
3. 选择"使用下面的DNS服务器地址"，输入DC的IP地址（如 `192.168.1.10`）
4. 点击"确定"

**第二步：验证DNS解析**

1. 按 `Win+R` 输入 `cmd`，执行 `nslookup corp.local`
2. 预期：应返回DC的IP地址

**第三步：执行加入域操作**

1. 按 `Win+R` 输入 `sysdm.cpl` → "计算机名"标签页 → 点击 **"更改…"**
2. 选择 **"域"** ，输入 `corp.local`，点击"确定"
3. 输入域管理员凭据：`CORP\Administrator` + 密码
4. 提示"欢迎加入 corp.local 域"，点击"确定"后重启

**第四步：用域账号登录验证**

1. 重启后登录界面点击"其他用户"
2. 输入 `CORP\Administrator` 或 `Administrator@corp.local`
3. 按 `Win+R` 输入 `sysdm.cpl`，确认"域"字段显示 `corp.local`

#### PowerShell方式

```powershell
# 在客户端执行：将计算机加入域
# -DomainName  : 目标域名
# -Credential  : 具有加域权限的凭据（通常是域管理员）
# -Restart     : 加域后自动重启
Add-Computer -DomainName "corp.local" `
  -Credential (Get-Credential) `
  -Restart
```

#### 常见问题排查表

| 错误提示 | 可能原因 | 解决方法 |
| --- | --- | --- |
| 找不到域 corp.local | 客户端DNS未指向DC | 检查客户端IPv4设置中的首选DNS服务器 |
| 用户名或密码不正确 | 使用了本地管理员账号 | 必须使用 `域名\Administrator` 格式的域凭据 |
| 指定的域不存在或无法联系 | 网络不通或DNS解析失败 | Ping DC的IP + nslookup 域名 |
| 发生安全数据库本地修改 | 之前加域失败留下残留 | 先退域（改回工作组），重启后再加域 |
| 时钟偏差过大 | 客户端与DC时间不同步 | 执行 `w32tm /resync` 同步时间 |

> 客户端加域前**必须**先将DNS指向DC的IP地址，这是加域失败的头号原因。


## 任务一（续）Active Directory 对象管理

### 知识点3：AD对象管理概述

#### 为什么需要手动创建AD对象？

客户端加入域时，计算机会自动在AD中创建计算机账户，但默认存放在 **Computers** 容器中。为了实现精细化的组策略管理，管理员需要：

1. **创建OU（组织单元）** ：按部门分类组织对象，以便针对不同部门部署不同的GPO
2. **创建用户**：为员工创建域用户账号，实现集中身份认证
3. **创建计算机账户**：预创建计算机账号并放入指定OU，控制GPO生效范围

> **关键概念**：默认的 Computers 容器**不是OU**，无法直接链接GPO。必须将对象移到OU中，才能实现基于OU的组策略管理。


### 实验4：创建组织单元（OU）

#### GUI操作步骤

1. 在DC上按 Win+R 输入 dsa.msc 打开 **Active Directory 用户和计算机**
2. 右键点击域名 **corp.local** → **新建** → **组织单元**
3. 输入OU名称（如 研发部），点击确定
4. 重复上述步骤创建更多OU，如 财务部、运维部 等
5. 可在OU下继续创建子OU，如右键 研发部 → 新建 → 组织单元 → 输入 前端组

#### PowerShell方式

```powershell
# 创建一级OU
New-ADOrganizationalUnit -Name "研发部" -Path "DC=corp,DC=local"
New-ADOrganizationalUnit -Name "财务部" -Path "DC=corp,DC=local"
New-ADOrganizationalUnit -Name "运维部" -Path "DC=corp,DC=local"

# 创建子OU（在研发部下创建前端组）
New-ADOrganizationalUnit -Name "前端组" -Path "OU=研发部,DC=corp,DC=local"

# 查看所有OU
Get-ADOrganizationalUnit -Filter * | Select-Object Name, DistinguishedName
```

> **提示**：创建OU时建议勾选"防止容器被意外删除"，避免误操作导致OU及其中所有对象被删除。


### 实验5：创建域用户

#### GUI操作步骤

1. 在DC上打开 dsa.msc
2. 展开目标OU（如 研发部），右键点击 → **新建** → **用户**
3. 填写用户信息：
    - 姓：张
    - 名：三
    - 用户登录名：zhangsan（会自动生成UPN：zhangsan@corp.local）
4. 点击下一步，设置初始密码（密码需满足域密码策略要求，至少8位且含大小写、数字、特殊字符）
5. 勾选 **用户下次登录时须更改密码**，点击下一步 → 完成
6. 在 dsa.msc 中双击新创建的用户 张三，可以进一步配置：
    - 所属部门（组织标签页）
    - 组成员身份（隶属于标签页，如加入研发部安全组）
    - 登录时间（账户标签页 → 登录时间）
    - 登录到（限制只能从指定计算机登录）

#### PowerShell方式

```powershell
# 创建域用户
New-ADUser `
  -Name "张三" `
  -GivenName "三" `
  -Surname "张" `
  -SamAccountName "zhangsan" `
  -UserPrincipalName "zhangsan@corp.local" `
  -Path "OU=研发部,DC=corp,DC=local" `
  -AccountPassword (ConvertTo-SecureString "P@ssw0rd123" -AsPlainText -Force) `
  -Enabled $true `
  -ChangePasswordAtLogon $true

# 查看指定OU中的所有用户
Get-ADUser -Filter * -SearchBase "OU=研发部,DC=corp,DC=local" | Select-Object Name, SamAccountName, Enabled

# 将用户加入安全组
Add-ADGroupMember -Identity "研发部" -Members "zhangsan"

# 重置用户密码
Set-ADAccountPassword -Identity "zhangsan" -Reset -NewPassword (ConvertTo-SecureString "NewP@ss123" -AsPlainText -Force)

# 禁用/启用用户
Disable-ADAccount -Identity "zhangsan"
Enable-ADAccount -Identity "zhangsan"
```

> **安全提醒**：创建用户时应勾选"用户下次登录时须更改密码"，避免使用统一初始密码带来的安全风险。生产环境中应定期检查长时间未登录的账号并及时禁用。


### 实验6：创建计算机账户

> 通常客户端加入域时会自动创建计算机账户。但在某些场景下，管理员需要**预创建**计算机账户并放入指定OU，例如：批量部署时提前规划GPO生效范围、限制哪些计算机可以加入域等。

#### GUI操作步骤

1. 在DC上打开 dsa.msc
2. 展开目标OU（如 研发部），右键点击 → **新建** → **计算机**
3. 输入计算机名（如 DEV-PC001），点击确定
4. 该计算机账户显示为灰色图标（带向下箭头），表示尚未有真实计算机使用此账户加入域

**将已有计算机移到指定OU：**

1. 打开 dsa.msc
2. 在 Computers 容器中找到目标计算机（如 WIN-CLIENT）
3. 右键 → **移动** → 选择目标OU（如 研发部）→ 确定
4. 移动后在客户端执行 gpupdate /force 使OU上的GPO生效

#### PowerShell方式

```powershell
# 预创建计算机账户
New-ADComputer `
  -Name "DEV-PC001" `
  -Path "OU=研发部,DC=corp,DC=local" `
  -Enabled $true

# 批量创建计算机账户（DEV-PC01 到 DEV-PC10）
1..10 | ForEach-Object {
  New-ADComputer `
    -Name "DEV-PC0$_" `
    -Path "OU=研发部,DC=corp,DC=local" `
    -Enabled $true
}

# 将计算机从Computers容器移到指定OU
Move-ADObject `
  -Identity "CN=WIN-CLIENT,CN=Computers,DC=corp,DC=local" `
  -TargetPath "OU=研发部,DC=corp,DC=local"

# 查看指定OU中的所有计算机
Get-ADComputer -Filter * -SearchBase "OU=研发部,DC=corp,DC=local" | Select-Object Name, Enabled
```

> **注意**：预创建的计算机账户在客户端实际加域时，需要使用"重置账户"功能才能正常加入（右键计算机账户 → 重置账户）。否则客户端会因SID不匹配而加域失败。


### 实验7：将用户加入安全组并配置权限

#### GUI操作步骤

**第一步：创建安全组**

1. 打开 dsa.msc，展开目标OU
2. 右键 OU → **新建** → **组**
3. 组名输入 研发部，组作用域选择 全局，组类型选择 安全
4. 点击确定

**第二步：将用户加入组**

1. 双击创建的安全组 研发部，切换到 成员 标签页
2. 点击 添加 → 输入用户名（如 zhangsan、lisi）→ 点击确定
3. 或者在用户属性中操作：双击用户 张三 → 隶属于 标签页 → 添加 → 输入组名

**第三步：将组加入客户端本地Administrators**

1. 在客户端上以管理员身份打开CMD，执行：

    ```bash
    net localgroup administrators "CORP\研发部" /add
    ```

2. 这样 研发部 安全组中的所有成员都拥有了该客户端的管理员权限

#### PowerShell方式

```powershell
# 在DC上执行：创建安全组
New-ADGroup `
  -Name "研发部" `
  -GroupScope Global `
  -GroupCategory Security `
  -Path "OU=研发部,DC=corp,DC=local"

# 批量将用户加入组
Add-ADGroupMember -Identity "研发部" -Members "zhangsan","lisi","wangwu"

# 查看组成员
Get-ADGroupMember -Identity "研发部" | Select-Object Name, SamAccountName

# 在客户端上执行：将域组加入本地管理员（需要客户端已加域）
Add-LocalGroupMember -Group "Administrators" -Member "CORP\研发部"
```

#### 实验4-7操作速查表

| 操作 | GUI方式 | PowerShell命令 |
| --- | --- | --- |
| 创建OU | dsa.msc → 右键域 → 新建 → 组织单元 | `New-ADOrganizationalUnit -Name "OU名" -Path "DC=corp,DC=local"` |
| 创建用户 | dsa.msc → 右键OU → 新建 → 用户 | `New-ADUser -Name "姓名" -SamAccountName "账号" -Path "OU=…,DC=corp,DC=local"` |
| 创建计算机 | dsa.msc → 右键OU → 新建 → 计算机 | `New-ADComputer -Name "计算机名" -Path "OU=…,DC=corp,DC=local"` |
| 创建安全组 | dsa.msc → 右键OU → 新建 → 组 | `New-ADGroup -Name "组名" -GroupScope Global` |
| 移动计算机到OU | dsa.msc → 右键计算机 → 移动 | `Move-ADObject -Identity "…" -TargetPath "OU=…,DC=corp,DC=local"` |
| 用户加入组 | 用户属性 → 隶属于 → 添加 | `Add-ADGroupMember -Identity "组名" -Members "用户名"` |
| 重置密码 | dsa.msc → 右键用户 → 重置密码 | `Set-ADAccountPassword -Identity "用户名" -Reset` |
| 禁用/启用账户 | dsa.msc → 右键用户 → 禁用/启用 | `Disable-ADAccount` / `Enable-ADAccount` |

> **最佳实践**：建议按部门创建OU，按角色创建安全组，将用户放入对应OU和组中。这样可以通过GPO对不同OU部署不同策略，通过安全组控制资源访问权限，实现精细化管理。


## 任务二 使用组策略管理域环境

### 知识点4：组策略（Group Policy）详解

#### 什么是组策略？

组策略（Group Policy）是Windows域环境中用于**集中配置和管理**用户及计算机行为的核心技术。管理员通过创建**组策略对象（GPO）** ，将安全设置、桌面限制、软件安装等配置统一推送到域内的计算机和用户。

**GPO的两大配置节点：**

| 节点 | 应用时机 | 跟随对象 | 典型配置项 |
| --- | --- | --- | --- |
| **计算机配置** | 计算机启动（开机）时 | 跟随计算机，不管谁登录都生效 | 密码策略、防火墙规则、软件安装、注册表限制 |
| **用户配置** | 用户登录时 | 跟随用户，无论在哪台电脑登录都生效 | 桌面壁纸、开始菜单布局、文件夹重定向、登录脚本 |

> **关键区别**：计算机配置在开机时自动应用，不需要用户登录；用户配置在用户登录时应用，跟随用户漫游。

#### 组策略安全筛选

默认情况下，链接到OU的GPO会应用到该OU内的所有用户和计算机。管理员可以通过**安全筛选**精确控制GPO的生效范围。

**配置方法：**

1. 在 `gpmc.msc` 中，选中目标GPO
2. 切换到 **"作用域"** 标签页 → **"安全筛选"** 区域
3. 默认显示 `Authenticated Users`（所有已认证用户）
4. 移除 `Authenticated Users`，添加特定组（如仅"研发部"安全组）

> **课堂思考**：公司要求财务部密码长度12位，其他部门8位即可。如何配置？
>
> 答案：在域级创建密码长度=8的GPO，再在"财务部OU"上链接一个密码长度=12的GPO。由于OU优先级高于域，财务部实际生效为12位。或者通过安全筛选，将"密码长度=12"的GPO仅应用于"财务部"安全组。


### 实验8：创建和链接组策略对象

#### GUI操作步骤

**第一步：打开组策略管理工具**

1. 在DC上按 `Win+R` 输入 `gpmc.msc` 回车
2. 展开：**森林 → 域 → corp.local**

**第二步：创建新GPO并链接到域**

1. 右键点击 **"corp.local"** → **"在这个域中创建GPO并在此链接"**
2. 名称输入：`Security-PasswordPolicy`，点击"确定"

**第三步：编辑GPO——配置密码策略**

1. 右键 `Security-PasswordPolicy` → **"编辑"**
2. 依次展开：**计算机配置 → 策略 → Windows 设置 → 安全设置 → 账户策略 → 密码策略**
3. 配置以下四项：
    - **密码必须符合复杂性要求** → 已启用
    - **密码最小长度** → 8 个字符
    - **密码最短使用期限** → 30 天
    - **密码最长使用期限** → 90 天

**第四步：配置账户锁定策略**

1. 导航到：**计算机配置 → 策略 → Windows 设置 → 安全设置 → 账户策略 → 账户锁定策略**
2. **账户锁定阈值** → 5 次无效登录
3. 确认锁定持续时间自动设为 30 分钟

**第五步：强制刷新策略**

1. 在客户端以管理员身份打开CMD，执行 `gpupdate /force`

**第六步：验证策略生效**

1. 在客户端按 `Win+R` 输入 `secpol.msc`
2. 确认密码策略和锁定策略已更新

#### PowerShell方式

```powershell
# 创建新GPO
New-GPO -Name "Security-PasswordPolicy" -Comment "企业统一密码安全策略"

# 链接GPO到域
New-GPLink -Name "Security-PasswordPolicy" -Target "DC=corp,DC=local"

# 在客户端强制刷新策略
gpupdate /force

# 查看当前应用的策略结果（摘要）
gpresult /r

# 导出详细HTML报告
gpresult /H C:\gp-report.html
```

#### 备份与恢复组策略对象

在生产环境中，GPO误操作可能导致全域配置异常。定期备份GPO是重要的运维习惯。

```powershell
# 备份所有GPO到指定目录
Backup-GPO -All -Path "C:\GPO-Backup"

# 备份指定的单个GPO
Backup-GPO -Name "Security-PasswordPolicy" -Path "C:\GPO-Backup"

# 从备份恢复GPO
Restore-GPO -Name "Security-PasswordPolicy" -Path "C:\GPO-Backup"

# 查看备份中的GPO列表
Get-GPOBackup -Path "C:\GPO-Backup" | Select-Object Name, BackupTime
```

> **最佳实践**：每次修改GPO前先备份，修改后验证。保留多个时间点的备份，以便在出现问题时快速回滚。


### 知识点5：组策略处理顺序（LSDOU）

#### LSDOU原则详解

当多个GPO可能应用于同一台计算机或用户时，Windows按照固定顺序处理，**越靠后应用的策略优先级越高（后者覆盖前者）** ：

```
本地策略（Local）                    <-- 优先级最低，始终被覆盖
    ↓
站点策略（Site）                     <-- 范围：同一物理站点
    ↓
域策略（Domain）                     <-- 范围：整个域
    ↓
组织单元策略（OU）                   <-- 优先级最高（子OU > 父OU）
```

| 层级 | 缩写 | 说明 | 优先级 |
| --- | --- | --- | --- |
| 本地 | L | 每台计算机本地存储的组策略（通过gpedit.msc编辑） | 最低 |
| 站点 | S | Active Directory站点级别的GPO | 较低 |
| 域 | D | 链接到域根节点的GPO，影响域内所有计算机和用户 | 较高 |
| 组织单元 | OU | 链接到OU的GPO，只影响该OU及其子OU内的对象 | 最高 |

#### 强制（Enforced）与阻止继承（Block Inheritance）

**强制（Enforced）** ：在某层级的GPO链接上设置"强制"后，该GPO的策略**不会被子级覆盖**，即使子OU设置了"阻止继承"也会穿透。

```
域级GPO（密码长度=8） [已强制]
    ↓
  研发部OU GPO（密码长度=6）  <-- 研发部的设置无效
    ↓
  实际生效：密码长度=8
```

**阻止继承（Block Inheritance）** ：在某个OU上设置"阻止继承"后，该OU将**不再从父级继承**GPO，但被"强制"的GPO策略仍然会穿透。

**关键规则总结：**

| 规则 | 说明 |
| --- | --- |
| 基本规则 | 后应用的覆盖先应用的（LSDOU，OU > 域 > 站点 > 本地） |
| 强制（Enforced） | 强制往下传递，即使子级阻止继承也会穿透 |
| 阻止继承 | 阻止父级策略传递下来，但被"强制"的策略不受影响 |
| 同级GPO | 同一层级如果有多个GPO冲突，最后链接的GPO优先 |

> 记忆口诀：强制 > 阻止继承；OU > 域 > 站点 > 本地

#### 组策略不生效的完整排查流程

```
步骤1：检查GPO是否已链接到目标域/OU
       gpmc.msc → 查看目标域/OU下的"链接的组策略对象"

步骤2：检查OU是否有"阻止继承"设置
       gpmc.msc → 右键OU → 属性 → 确认未勾选"阻止继承"

步骤3：检查GPO链接是否有"强制"设置
       gpmc.msc → 检查父级GPO链接是否设置了"已强制"

步骤4：检查安全筛选是否包含目标用户/计算机
       gpmc.msc → 选中GPO → "作用域" → "安全筛选"

步骤5：在客户端执行 gpresult /r 查看实际应用的GPO列表
       确认目标GPO是否出现在"应用的组策略对象"中

步骤6：执行 gpupdate /force 强制刷新策略

步骤7：检查客户端时间是否与DC同步
       Kerberos认证要求时间偏差 < 5分钟
       执行 w32tm /resync 手动同步
```


## 任务三 通过组策略批量部署软件

### 知识点6：GPO软件安装原理

#### 软件安装概述

组策略的"软件安装"功能是域环境中**批量部署软件**的核心手段。管理员只需在DC上配置一次，域内的计算机或用户就会在启动/登录时自动安装指定的软件，无需逐台手动操作。

#### 发布（Publish）vs 分配（Assign）的区别

| 对比项 | 分配（Assign） | 发布（Publish） |
| --- | --- | --- |
| 部署位置 | 计算机配置 或 用户配置 | 仅用户配置 |
| 安装时机 | 计算机：开机时自动安装；用户：登录后桌面出现快捷方式，首次点击时安装 | 用户登录后，在"控制面板→程序和功能"中手动选择安装 |
| 用户感知 | 计算机分配：无感知；用户分配：看到快捷方式 | 需主动到控制面板查找并安装 |
| 强制程度 | 高（自动安装或半自动） | 低（用户自行决定） |
| 适用场景 | 杀毒软件、办公套件、VPN客户端等必须安装的软件 | 辅助工具、可选插件等非强制软件 |
| 安装包格式 | 仅支持 .msi 格式 | 仅支持 .msi 格式 |

#### 前置条件

1. **安装包必须是 .msi 格式**（Windows Installer包）。.exe 安装包不能直接用于GPO部署
2. **安装包必须存放在网络共享文件夹中**，且域用户/计算机有读取权限
3. **共享路径使用UNC格式**：`\\DC主机名\共享名\安装包.msi`

> 如何将 .exe 转为 .msi？可使用工具如 **Advanced Installer**、**WiX Toolset** 等。实际教学中可下载软件的 .msi 版本（如 7-Zip、Notepad++ 等均提供 .msi 格式）。


### 实验9：准备软件安装包与共享文件夹

> 本实验为后续实验10和实验11做准备，需在域控制器上完成。

#### GUI操作步骤

**第一步：创建共享文件夹**

1. 在DC上，打开"文件资源管理器"
2. 进入 `C:\` 盘，新建文件夹，命名为 `SoftwareShare`
3. 将准备好的 .msi 安装包（如 7-Zip 的 .msi 文件）复制到 `C:\SoftwareShare` 中
4. 右键 `SoftwareShare` 文件夹 → **"属性"** → **"共享"** 标签页
5. 点击 **"高级共享…"**
6. 勾选 **"共享此文件夹"**
7. 点击 **"权限"** 按钮，确认 **"Everyone"** 组至少拥有 **"读取"** 权限，点击"确定"
8. 点击"确定"关闭所有窗口

**第二步：验证共享文件夹可访问**

1. 在客户端按 `Win+R` 输入 `\\DC的主机名\SoftwareShare`（如 `\\WIN-DC\SoftwareShare`）
2. 应能看到 .msi 安装包文件
3. 如果提示输入凭据，使用 `CORP\用户名` + 密码

#### PowerShell方式

```powershell
# 在DC上执行：创建共享文件夹
New-Item -Path "C:\SoftwareShare" -ItemType Directory -Force
Copy-Item "C:\temp\7z-x64.msi" -Destination "C:\SoftwareShare\"

# 创建共享并授权Everyone读取
New-SmbShare -Name "SoftwareShare" -Path "C:\SoftwareShare" -FullAccess "Everyone"

# 验证共享
Get-SmbShare -Name "SoftwareShare"
```

> 注意：生产环境中应使用专门的域组而非Everyone，并仅授予"读取"权限，遵循最小权限原则。


### 实验10：通过组策略分配软件——计算机启动自动安装

> 本实验将 .msi 软件包通过"分配"方式部署到域内计算机。客户端**下次开机时自动安装**，用户无需任何操作。

#### GUI操作步骤

**第一步：创建专用的软件部署GPO**

1. 在DC上按 `Win+R` 输入 `gpmc.msc` 回车
2. 展开：**森林 → 域 → corp.local**
3. 右键 **"corp.local"** → **"在这个域中创建GPO并在此链接"**
4. 名称输入：`Software-Deploy-7Zip`，点击"确定"

**第二步：配置软件安装策略**

1. 右键 `Software-Deploy-7Zip` → **"编辑"**
2. 依次展开：**计算机配置 → 策略 → 软件安装**
3. 右键 **"软件安装"** → **"新建"** → **"数据包…"**
4. 在"打开"对话框的地址栏中输入UNC路径：`\\WIN-DC\SoftwareShare`（替换为实际的DC主机名）
5. 选择 .msi 安装包文件（如 `7z-x64.msi`），点击"打开"
6. 弹出"部署软件"对话框：
    - 部署方式选择： **"已分配"**
    - 点击 **"确定"**
7. 在"软件安装"窗格中应看到已添加的软件包，图标上有一个**向下的箭头**（表示"已分配"）

**第三步：在客户端验证自动安装**

1. 在客户端以管理员身份打开CMD，执行 `gpupdate /force`
2. **重启客户端计算机**
3. 重启后观察——开机过程中（登录前），应看到软件安装进度提示
4. 登录后检查：开始菜单或桌面应出现已安装的 7-Zip 快捷方式
5. 验证方式：按 `Win+R` 输入 `appwiz.cpl`，在"程序和功能"列表中确认 7-Zip 已安装

#### PowerShell方式

```powershell
# 在DC上执行：创建GPO
New-GPO -Name "Software-Deploy-7Zip" -Comment "通过GPO分配部署7-Zip"

# 链接GPO到域
New-GPLink -Name "Software-Deploy-7Zip" -Target "DC=corp,DC=local"
```

> 注意：GPO软件安装的PowerShell配置较复杂（需要操作AD中的软件安装容器），实际教学中建议使用GUI方式完成软件安装策略的配置。


### 实验11：通过组策略发布软件——用户按需安装

> 本实验将软件通过"发布"方式提供给域用户。用户登录后可在"控制面板"中**自行选择安装**。

#### GUI操作步骤

**第一步：创建发布软件的GPO**

1. 在DC上打开 `gpmc.msc`
2. 右键 **"corp.local"** → **"在这个域中创建GPO并在此链接"**
3. 名称输入：`Software-Publish-NotepadPP`，点击"确定"

**第二步：配置发布策略（用户配置）**

1. 右键 `Software-Publish-NotepadPP` → **"编辑"**
2. 依次展开：**用户配置 → 策略 → 软件安装**
3. 右键 **"软件安装"** → **"新建"** → **"数据包…"**
4. 在地址栏输入UNC路径：`\\WIN-DC\SoftwareShare`
5. 选择 .msi 安装包（如 Notepad++ 的 .msi 文件），点击"打开"
6. 弹出"部署软件"对话框：
    - 部署方式选择： **"已发布"**
    - 点击 **"确定"**
7. 在"软件安装"窗格中应看到已添加的软件包，图标上有一个**公文包/信封**图标（表示"已发布"）

**第三步：在客户端验证发布安装**

1. 在客户端以管理员身份打开CMD，执行 `gpupdate /force`
2. **注销当前用户，重新登录**（或重启）
3. 登录后验证：
    - 按 `Win+R` 输入 `control` 打开控制面板
    - 切换查看方式为 **"大图标"** 或 **"小图标"**
    - 找到并点击 **"程序和功能"**
    - 点击左侧 **"从网络安装程序"** （或"从组织安装应用程序"）
    - 列表中应显示已发布的 Notepad++
4. 选择该软件，点击 **"安装"** ，等待安装完成
5. 验证：在开始菜单中应可找到 Notepad++

#### 实验10与实验11对比总结

| 对比项 | 实验10（分配） | 实验11（发布） |
| --- | --- | --- |
| GPO位置 | 计算机配置 → 软件安装 | 用户配置 → 软件安装 |
| 部署方式 | 已分配 | 已发布 |
| 触发条件 | 客户端开机时自动触发 | 用户登录后在控制面板手动安装 |
| 用户操作 | 无需操作（自动安装） | 需主动到控制面板选择安装 |
| 适用场景 | 全员必须安装的软件 | 可选安装的辅助工具 |

#### 常见问题排查

| 问题 | 可能原因 | 解决方法 |
| --- | --- | --- |
| 客户端开机后未自动安装软件 | GPO链接在域但客户端在某个OU中，且该OU阻止了继承 | 检查OU的"阻止继承"设置，或将GPO直接链接到目标OU |
| 打开"从网络安装程序"为空 | 使用的是计算机配置而非用户配置 | 确认GPO中软件包配置在"用户配置"下 |
| 安装时提示找不到安装包 | 共享文件夹权限不足或网络不通 | 检查UNC路径可访问性，确认Everyone有读取权限 |
| gpupdate后仍无变化 | 组策略需要时间传播 | 等待5-10分钟或重启客户端 |

> **安全提醒**：通过GPO部署软件虽然方便，但也存在安全风险。攻击者如果获得GPO编辑权限，可以将恶意软件批量部署到全域。因此，GPO的编辑权限应严格控制，仅授予受信任的管理员。


## 任务四 域管理综合实验：统一部署与配置

### 实验12：通过GPO统一安装JDK

> 本实验演示如何通过域组策略将JDK（Java Development Kit）批量部署到域内所有计算机，实现"一次配置，全域生效"的软件统一安装。

#### 前置准备

1. 从Oracle或Adoptium官网下载JDK的 `.msi` 格式安装包（推荐使用 Eclipse Temurin，官方提供标准 .msi 包）
    - 示例文件名：`OpenJDK21U-jdk_x64_windows_hotspot_21.msi`
2. 将 .msi 文件复制到DC的共享文件夹（如 `C:\SoftwareShare`）
3. 确认共享路径可访问：`\\WIN-DC\SoftwareShare`

#### GUI操作步骤

**第一步：创建JDK部署GPO**

1. 在DC上按 `Win+R` 输入 `gpmc.msc`
2. 展开：**森林 → 域 → corp.local**
3. 右键 **corp.local** → **"在这个域中创建GPO并在此链接"**
4. 名称输入：`Software-Deploy-JDK21`，点击"确定"

**第二步：配置软件安装（计算机配置——自动安装）**

1. 右键 `Software-Deploy-JDK21` → **"编辑"**
2. 依次展开：**计算机配置 → 策略 → 软件安装**
3. 右键 **"软件安装"** → **"新建"** → **"数据包…"**
4. 在地址栏输入UNC路径：`\\WIN-DC\SoftwareShare`，选择JDK的 .msi 文件，点击"打开"
5. 部署方式选择 **"已分配"**，点击"确定"

**第三步：验证安装**

1. 在客户端执行 `gpupdate /force`，然后**重启**
2. 开机过程中会自动执行JDK安装
3. 登录后打开CMD，执行以下命令验证：

```powershell
java -version
```

预期输出示例：

```
openjdk version "21.0.x" 2024-xx-xx
OpenJDK Runtime Environment ...
```

#### PowerShell方式

```powershell
# 在DC上执行：将JDK安装包复制到共享目录
Copy-Item "C:\temp\OpenJDK21U-jdk_x64_windows_hotspot_21.msi" -Destination "C:\SoftwareShare\"

# 创建GPO并链接
New-GPO -Name "Software-Deploy-JDK21" -Comment "通过GPO统一部署JDK 21"
New-GPLink -Name "Software-Deploy-JDK21" -Target "DC=corp,DC=local"

# 在客户端验证Java版本
java -version
```

| 常见问题 | 可能原因 | 解决方法 |
| --- | --- | --- |
| 开机后未自动安装JDK | 安装包不是 .msi 格式 | 改用官方 .msi 包或使用 Advanced Installer 重新打包 |
| java -version 提示找不到命令 | 安装成功但PATH未刷新 | 重新打开CMD，或注销重新登录 |
| 安装过程中弹出UAC提示 | GPO作用于用户而非计算机 | 确认软件包放在"计算机配置"下，而非"用户配置" |

> **实际场景**：公司全员统一部署Java开发环境，避免因版本不一致导致的"在我机器上能跑，在你机器上不行"问题。

---

### 实验13：通过GPO统一设置桌面壁纸

> 本实验演示如何通过域组策略将企业定制壁纸强制推送到域内所有用户的桌面，实现品牌统一和安全提示展示。

#### 前置准备

1. 准备好壁纸图片文件（推荐 `.jpg` 或 `.bmp` 格式，分辨率建议1920×1080）
2. 将图片放入DC的共享目录，路径如：`C:\SoftwareShare\wallpaper.jpg`
3. 确保所有域用户对该共享有**读取权限**

> **重要**：壁纸路径必须使用 **UNC网络路径**（如 `\\WIN-DC\SoftwareShare\wallpaper.jpg`），不能使用本地路径，否则客户端找不到图片。

#### GUI操作步骤

**第一步：创建壁纸部署GPO**

1. 在DC上打开 `gpmc.msc`
2. 右键 **corp.local** → **"在这个域中创建GPO并在此链接"**
3. 名称输入：`Desktop-Wallpaper-Policy`，点击"确定"

**第二步：配置桌面壁纸策略（用户配置）**

1. 右键 `Desktop-Wallpaper-Policy` → **"编辑"**
2. 依次展开：**用户配置 → 策略 → 管理模板 → 桌面 → 桌面**
3. 双击右侧的 **"桌面壁纸"**
4. 选择 **"已启用"**
5. 在"壁纸名称"中输入UNC路径：

    `\\WIN-DC\SoftwareShare\wallpaper.jpg`

6. "壁纸样式"选择 **"填充"**（或"适应"、"拉伸"）
7. 点击"确定"

**第三步：防止用户修改壁纸（可选）**

1. 在同一路径下，双击 **"防止更改桌面背景"**
2. 选择 **"已启用"**，点击"确定"
3. 这样用户右键桌面后"个性化"中的壁纸选项将变为灰色，无法修改

**第四步：验证壁纸生效**

1. 在客户端执行 `gpupdate /force`
2. **注销后重新登录**（壁纸策略属于用户配置，需重新登录才生效）
3. 确认桌面壁纸已变为指定图片

#### PowerShell方式

```powershell
# 在DC上执行：创建GPO并链接
New-GPO -Name "Desktop-Wallpaper-Policy" -Comment "统一设置企业桌面壁纸"
New-GPLink -Name "Desktop-Wallpaper-Policy" -Target "DC=corp,DC=local"

# 通过注册表策略设置壁纸（配合GPO注册表策略）
Set-GPRegistryValue -Name "Desktop-Wallpaper-Policy" `
  -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" `
  -ValueName "Wallpaper" `
  -Type String `
  -Value "\\WIN-DC\SoftwareShare\wallpaper.jpg"

# 壁纸样式：10=填充, 6=适应, 2=拉伸, 0=居中
Set-GPRegistryValue -Name "Desktop-Wallpaper-Policy" `
  -Key "HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System" `
  -ValueName "WallpaperStyle" `
  -Type String `
  -Value "10"

# 客户端刷新并重新登录
gpupdate /force
```

| 常见问题 | 可能原因 | 解决方法 |
| --- | --- | --- |
| 壁纸未更新 | 策略属于用户配置，仅刷新不生效 | 必须注销后重新登录，gpupdate /force 不够 |
| 壁纸显示为黑屏/空白 | UNC路径写错或共享权限不足 | 检查路径格式和Everyone读取权限 |
| 用户仍可修改壁纸 | 未启用"防止更改桌面背景"策略 | 补充启用该策略项 |

> **实际场景**：企业统一设置带有公司logo和安全声明的壁纸，如"本设备仅供公司业务使用，所有操作均在监控中"，既体现品牌形象，也起到安全警示作用。

---

### 实验14：通过GPO统一设置系统环境变量

> 本实验演示如何通过域组策略统一为域内所有计算机配置系统环境变量，例如将JDK的 `JAVA_HOME` 和 `PATH` 批量写入，确保全域环境一致。

#### 配置思路

Windows组策略支持通过以下两种方式配置环境变量：

| 方式 | 路径 | 适用范围 | 推荐场景 |
| --- | --- | --- | --- |
| **组策略首选项（GP Preferences）** | 计算机/用户配置 → 首选项 → Windows设置 → 环境 | 计算机或用户 | 推荐，灵活且支持增量更新 |
| **注册表策略** | 修改 `HKLM\SYSTEM\...\Environment` 注册表项 | 计算机（系统级） | 适用于高版本限制场景 |

#### GUI操作步骤（使用组策略首选项——推荐方式）

**第一步：创建环境变量配置GPO**

1. 在DC上打开 `gpmc.msc`
2. 右键 **corp.local** → **"在这个域中创建GPO并在此链接"**
3. 名称输入：`System-EnvVars-Java`，点击"确定"

**第二步：配置 JAVA_HOME 环境变量**

1. 右键 `System-EnvVars-Java` → **"编辑"**
2. 依次展开：**计算机配置 → 首选项 → Windows 设置 → 环境**
3. 右键右侧空白区域 → **"新建"** → **"环境变量"**
4. 填写以下信息：
    - **操作**：更新
    - **用户变量/系统变量**：选择 **系统变量**
    - **变量名**：`JAVA_HOME`
    - **变量值**：`C:\Program Files\Java\jdk-21`（根据实际安装路径填写）
5. 点击"确定"

**第三步：将Java添加到PATH**

1. 再次右键 → **"新建"** → **"环境变量"**
2. 填写以下信息：
    - **操作**：更新
    - **用户变量/系统变量**：选择 **系统变量**
    - **变量名**：`Path`
    - **变量值**：`%JAVA_HOME%\bin`
    - **勾选**："将此值附加到现有值末尾"（避免覆盖原有PATH内容）
3. 点击"确定"

**第四步：验证环境变量生效**

1. 在客户端执行 `gpupdate /force`
2. **重启客户端**（系统变量需重启才能全局生效）
3. 重启后打开CMD验证：

```powershell
# 查看JAVA_HOME
echo %JAVA_HOME%

# 查看PATH中是否包含Java路径
echo %PATH%

# 验证java命令可用
java -version
```

#### PowerShell方式

```powershell
# 在DC上执行：创建GPO并链接
New-GPO -Name "System-EnvVars-Java" -Comment "统一设置Java环境变量"
New-GPLink -Name "System-EnvVars-Java" -Target "DC=corp,DC=local"

# 通过注册表策略设置JAVA_HOME（计算机级系统变量）
Set-GPRegistryValue -Name "System-EnvVars-Java" `
  -Key "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" `
  -ValueName "JAVA_HOME" `
  -Type String `
  -Value "C:\Program Files\Eclipse Adoptium\jdk-21"
```

| 常见问题                | 可能原因             | 解决方法                         |
| ------------------- | ---------------- | ---------------------------- |
| 环境变量未生效             | 仅刷新策略未重启         | 系统变量需重启后才对所有进程生效             |
| PATH被覆盖导致系统命令失效     | 未勾选"追加到现有值末尾"    | 在首选项中勾选追加选项，或先备份PATH再操作      |
| java -version仍显示旧版本 | PATH中旧JDK路径优先级更高 | 将新JDK路径放在PATH最前面，或删除旧版PATH条目 |

> **最佳实践**：环境变量的设置建议配合实验12（JDK统一安装）一起使用，先通过GPO安装JDK，再通过GPO配置JAVA_HOME和PATH，实现"安装+配置"一体化自动完成。


## 任务五 退出域与域管理维护

### 实验15：将客户端退出域（退域）

> 当计算机需要脱离域管理（如设备报废、转移到其他部门或域），管理员需要执行退域操作。退域后，计算机的AD计算机账户仍保留在域中，需要手动清理。

#### GUI操作步骤

**第一步：执行退域操作**

1. 使用**本地管理员账号**（而非域账号）登录客户端
   - 如果没有本地管理员账号，需要先用域管理员在CMD中创建：`net user localadmin P@ss123 /add` 和 `net localgroup administrators localadmin /add`
2. 按 `Win+R` 输入 `sysdm.cpl` → "计算机名"标签页 → 点击 **"更改…"**
3. 选择 **"工作组"**，输入工作组名（如 `WORKGROUP`）
4. 点击"确定"，弹出对话框要求输入**域管理员凭据**（`CORP\Administrator` + 密码）确认退域
5. 提示"欢迎加入 WORKGROUP 工作组"，点击"确定"
6. 重启计算机

**第二步：清理AD中的残留计算机账户（在DC上操作）**

1. 在DC上打开 `dsa.msc`
2. 在 Computers 容器（或之前所在的OU）中找到已退域的计算机账户
3. 右键 → **删除**
4. 确认删除

> **注意**：退域时需要域管理员凭据确认。如果DC已不可用（如DC已关机），可使用 `sysdm.cpl` 中"网络ID"按钮或强制退域方式。

#### PowerShell方式

```powershell
# 在客户端执行：退出域，重新加入工作组
# -WorkgroupName : 要加入的工作组名称
# -Credential    : 用于确认退域的域管理员凭据
# -Restart       : 退域后自动重启
Remove-Computer -WorkgroupName "WORKGROUP" `
  -Credential (Get-Credential) `
  -Restart

# 在DC上执行：删除已退域的残留计算机账户
Remove-ADComputer -Identity "WIN-CLIENT" -Confirm:$false
```

#### 退域常见问题排查

| 问题 | 可能原因 | 解决方法 |
| --- | --- | --- |
| 退域时提示"拒绝访问" | 当前登录的域账号无权退域 | 使用本地管理员账号登录后再操作 |
| 找不到本地管理员账号 | 从未创建过本地管理员 | 先用域管理员创建：`net user localadmin P@ss /add && net localgroup administrators localadmin /add` |
| 退域后无法用域账号登录 | 计算机已不在域中 | 使用本地管理员账号登录（或重启后选择"其他用户"输入本地凭据） |
| 重新加域时提示"计算机名已存在" | AD中残留了旧的计算机账户 | 在DC的dsa.msc中删除旧计算机账户，或在客户端加域前执行重置账户 |

> **最佳实践**：退域前应做好以下准备：①确保有可用的本地管理员账号；②确认退域原因并记录；③退域后在DC上清理残留的计算机账户，保持AD数据库整洁。


## 本项目总结

### 核心操作速查表

| 操作 | GUI方式 | PowerShell / 命令行 |
| --- | --- | --- |
| 安装AD DS角色 | 服务器管理器 → 添加角色和功能 | `Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools` |
| 提升为域控制器 | 服务器管理器 → 提升为域控制器 → 添加新林 | `Install-ADDSForest -DomainName "corp.local" -InstallDns:$true` |
| 将计算机加入域 | 此电脑 → 属性 → 更改 → 域 | `Add-Computer -DomainName "corp.local" -Credential (Get-Credential) -Restart` |
| 将计算机退出域 | 此电脑 → 属性 → 更改 → 工作组 | `Remove-Computer -WorkgroupName "WORKGROUP" -Credential (Get-Credential) -Restart` |
| 创建OU | dsa.msc → 右键域 → 新建 → 组织单元 | `New-ADOrganizationalUnit -Name "OU名" -Path "DC=corp,DC=local"` |
| 创建域用户 | dsa.msc → 右键OU → 新建 → 用户 | `New-ADUser -Name "姓名" -SamAccountName "账号" -Path "OU=…,DC=corp,DC=local"` |
| 创建新GPO | gpmc.msc → 右键域/OU → 创建GPO并链接 | `New-GPO -Name "GPO名称"` |
| 链接GPO到目标 | gpmc.msc → 右键域/OU → 链接现有GPO | `New-GPLink -Name "GPO名称" -Target "DC=corp,DC=local"` |
| 备份GPO | gpmc.msc → 右键GPO → 备份 | `Backup-GPO -Name "GPO名称" -Path "C:\GPO-Backup"` |
| 恢复GPO | gpmc.msc → 右键GPO → 管理 → 还原 | `Restore-GPO -Name "GPO名称" -Path "C:\GPO-Backup"` |
| 刷新组策略 | CMD → `gpupdate /force` | `gpupdate /force` |
| 查看策略结果 | CMD → `gpresult /r` | `gpresult /r` |

### 常见错误速查表

| 错误现象 | 最可能原因 | 解决方法 |
| --- | --- | --- |
| 找不到域 corp.local | 客户端DNS未指向DC | 检查客户端首选DNS服务器，设置为DC的IP |
| 用户名或密码不正确 | 使用了本地管理员账号 | 使用 `域名\Administrator` 格式的域管理员凭据 |
| GPO不生效 | GPO未链接或未刷新 | 确认GPO已链接 + 客户端执行 `gpupdate /force` |
| 加域失败提示残留 | 之前加域留下的计算机账户 | 在DC上删除旧计算机账户后重试 |
| Kerberos认证失败 | 客户端与DC时间偏差>5分钟 | 执行 `w32tm /resync` 同步时间 |

### 实验12-14综合对比

| 实验 | 目标 | GPO节点 | 生效时机 |
| --- | --- | --- | --- |
| 实验12：统一安装JDK | 批量部署Java运行环境 | 计算机配置 → 软件安装 | 计算机启动时 |
| 实验13：统一设置壁纸 | 强制企业桌面视觉统一 | 用户配置 → 管理模板 → 桌面 | 用户登录时 |
| 实验14：统一设置环境变量 | 批量配置系统PATH/JAVA_HOME等 | 计算机配置 → 首选项 → 环境 | 计算机启动时 |


## 安全意识

域控制器是整个企业IT基础设施的"心脏"。一旦域控制器被攻陷，攻击者将获得整个域的控制权。因此，域安全是Windows服务器安全的重中之重。

### 域环境常见攻击与防御

| 攻击方式 | 原理 | 防御措施 |
| --- | --- | --- |
| Pass-the-Hash | 直接使用NTLM哈希认证，无需明文密码即可登录 | 禁用NTLM，强制Kerberos；限制管理员权限 |
| Golden Ticket | 伪造Kerberos票据（利用krbtgt账户），获取持久域控权限 | 定期更换krbtgt密码（至少两次）；监控异常票据 |
| DCSync | 模拟DC复制行为，远程窃取所有密码哈希 | 监控异常复制请求；限制可复制DC的权限组 |
| GPO篡改 | 修改组策略推送恶意软件或后门 | 审计GPO修改日志；严格限制GPO编辑权限 |
| Mimikatz | 内存中提取明文密码和哈希 | 启用 Credential Guard；限制域管理员登录普通终端 |

### 核心安全原则

1. **保护NTDS.dit**：严格控制DC的物理和网络访问权限
2. **管理DSRM密码**：使用强密码并安全保存，定期更换
3. **建立GPO安全基线**：密码长度8位以上、90天更换、5次锁定30分钟
4. **定期审计域安全**：检查Domain Admins组成员、查看新创建的账户、监控GPO变更
5. **部署多台DC**：生产环境至少2台，防止单点故障
6. **最小权限原则**：日常使用普通域用户账号，不使用域管理员日常操作
7. **保护krbtgt账户**：定期更换密码，限制访问，防止Golden Ticket攻击

> **安全底线**：域控制器是整个域的安全根基。保护DC就是保护整个企业网络。一旦DC被攻陷，相当于整个企业的所有门禁卡都被复制了。


## 课堂思考

1. 如果公司有北京和上海两个办公地点，每个地点各有200台电脑和1台DC，应该创建几个域、几个站点？为什么？
2. 研发部的密码策略要求比域默认策略更严格（密码长度10位），应该如何配置GPO？
3. 如何让某个GPO只对"财务部OU"生效，不影响其他OU？列举至少两种方法。
4. 一台客户端加域失败，提示"指定的域不存在"，请列出排查步骤。
5. 如果误操作删除了一个重要的GPO，如何恢复？平时应该养成什么习惯？


## 知识关联

本项目与上节课"Windows远程服务管理"的关联：

- 在域环境中，可通过**GPO统一推送远程桌面配置**，包括启用RDP、修改端口、配置NLA等
- 无需逐台手动修改注册表，一个GPO即可让全域计算机统一应用安全的远程桌面策略
- GPO路径：计算机配置 → 管理模板 → Windows组件 → 远程桌面服务
