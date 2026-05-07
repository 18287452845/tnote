---
color: "linear-gradient(45deg, #fc8ec5 0%, #ff8dd3 25%, #ffa1d8 50%, #ffc1d2 75%, #ffe0c3 100%)"
---
# 实验一：服务器信息收集与SNMP枚举渗透

> 对应章节：项目一 走进Windows服务器
实验目标：掌握针对Windows Server的信息收集方法，包括端口扫描、服务识别、SNMP枚举等，理解信息泄露的安全风险
预计用时：90分钟（知识讲解30分钟 + 动手实验60分钟）
难度等级：⭐⭐（初级）
> 

---

# 第一部分：前置知识讲解

<aside>
📚

本部分为实验前的理论知识储备，建议在动手操作之前完整阅读。理解"为什么这样做"远比"怎样做"更重要，知识点与后续实验步骤一一对应。

</aside>

## 0. 渗透测试中的信息收集方法论

### 0.1 为什么信息收集是渗透测试的第一步？

在真实攻防场景中，**信息收集（Reconnaissance）** 往往占据渗透测试 60% 以上的时间。一个经验丰富的攻击者在尚未发送任何攻击载荷之前，就已经通过信息收集勾勒出目标的完整轮廓：

- **操作系统与版本** → 决定可利用的漏洞范围（如 MS17-010 只影响特定 Windows 版本）
- **开放端口与服务** → 决定攻击入口（445 端口意味着 SMB，3389 意味着 RDP）
- **服务版本号** → 精确匹配 CVE 漏洞库
- **运行中的进程与软件** → 发现第三方软件漏洞（如旧版 Adobe、Java）
- **网络拓扑与其他主机** → 横向移动的基础

> **核心理念**："未知攻，焉知防"——只有理解攻击者如何收集信息，才能知道该保护什么、该隐藏什么。
> 

### 0.2 信息收集

| 类型         | 特点            | 典型技术                      | 是否与目标交互 |
| ---------- | ------------- | ------------------------- | ------- |
| **主动信息收集** | 直接与目标交互，会留下日志 | Nmap 扫描、SNMP 枚举、Banner 抓取 | 是       |

本实验聚焦于**主动信息收集**，在受控的实验环境中进行，不会对任何外部系统产生影响。

---

## 1. Windows 服务器基础回顾

### 1.1 Windows Server 与普通 Windows 的区别

Windows Server 并不是普通 Windows 的简单"加强版"，它在服务组件和默认配置上有本质差别：

- **默认启用更多网络服务**：SMB、RPC、WinRM 等服务默认开启，攻击面大
- **支持服务器角色（Role）**：AD 域控、DNS、DHCP、IIS、文件共享等以"角色"形式模块化安装
- **存在域环境**：一旦加入 Active Directory 域，单点失陷可能导致整域失陷
- **远程管理通道多**：RDP (3389)、WinRM (5985/5986)、SMB Admin 共享 (C$, ADMIN$)

### 1.2 服务器用途分类（与扫描结果对应）

当你扫到一台 Windows Server，可以根据开放端口快速判断它的角色：

| 开放端口组合   | 可能的服务器角色           |
| -------- | ------------------ |
| 80, 443  | Web 服务器（IIS）       |
| 1433     | 数据库服务器（SQL Server） |
| 161, 162 | 网管/监控服务器（本实验重点）    |

---

## 2. 网络扫描基础

### 2.1 TCP/IP协议栈回顾

网络扫描的基础是TCP/IP协议栈。扫描工具通过发送特定协议的数据包并分析响应来判断目标主机的状态。理解TCP三次握手（SYN → SYN-ACK → ACK）是理解Nmap扫描原理的前提：

```
扫描方                          目标主机
  |---- SYN（我要连接）---------->|
  |<--- SYN-ACK（同意，你呢？）----|
  |---- ACK（我也同意）---------->|
  |                              |
  |===== 连接建立，开始通信 =====|
```

**Nmap扫描类型对比**：

| 扫描类型         | 原理                      | 优点           | 缺点       |
| ------------ | ----------------------- | ------------ | -------- |
| `-sS`（SYN扫描） | 只发送SYN，收到SYN-ACK后发RST断开 | 快速隐蔽，不完成完整连接 | 需要root权限 |
| `-sT`（全连接扫描） | 完成完整TCP三次握手             | 无需root权限     | 易被日志记录   |
| `-sU`（UDP扫描） | 发送UDP数据包                | 能发现UDP服务     | 速度慢，准确性低 |
| `-sn`（主机发现）  | 只发送ICMP或ARP请求           | 快速发现存活主机     | 无法获取端口信息 |

### 2.2 Nmap常用参数速记卡

```
# 基础扫描组合

# 快速扫描常用端口
nmap -sS -sV -A 192.168.1.20

# 全端口扫描（较慢）
nmap -p- -T4 192.168.1.20

# 只扫描常见高危端口
nmap -p 21,22,23,80,135,139,443,445,3389 192.168.1.20
```

**参数逐个拆解**：

- `-sS`：SYN 半开扫描（默认且推荐）
- `-sV`：探测服务版本，对应发送 Nmap 探针并匹配指纹
- `-A`：Aggressive 模式，等价于 `-sV -O --script=default --traceroute`
- `-p-`：扫描全部 65535 个端口（区别于默认的前 1000 个）
- `-T0` ~ `-T5`：扫描速度，T4 是实验环境常用，T0/T1 用于隐蔽扫描
- `-Pn`：跳过主机存活检测，直接扫端口（目标禁 ping 时必用）

### 2.3 扫描的三层递进思路

```
第一层：发现存活主机    →  -sn（快速，只判断是否在线）
第二层：发现开放端口    →  -sS / -sT / -sU
第三层：识别服务与版本  →  -sV / -A / --script
```

理解这个递进关系，你就能根据实验目标选择合适的扫描深度，而不是一股脑 `nmap -A -p-`。

---

## 3. SNMP 协议精讲

前面通过 Nmap 能回答两个问题：**目标是否在线**、**开放了哪些服务**。当扫描结果中出现 `161/udp open snmp` 时，信息收集就进入了更深一层：不再只是看“门开没开”，而是尝试询问 SNMP Agent：这台服务器的系统版本、主机名、进程、软件、网卡和路由表分别是什么。

因此，本节的学习顺序是：

```
发现 UDP/161 开放
        ↓
理解 SNMP 如何通信：Manager 查询 Agent
        ↓
理解 Agent 里有哪些可查询对象：MIB 定义对象
        ↓
理解如何定位某个对象：OID 是对象编号
        ↓
使用 snmpget/snmpwalk 按 OID 读取信息
        ↓
分析默认团体名 public 导致的信息泄露
```

### 3.1 SNMP 是什么？

**SNMP（Simple Network Management Protocol，简单网络管理协议）** 是一种用于管理和监控网络设备、服务器、打印机、UPS 等设备的应用层协议。它通常运行在 UDP 上，最常见的查询端口是 **UDP 161**。

一句话概括：**SNMP 是运维系统向设备“问状态”的协议。**

例如，监控平台可能会不断向服务器询问：

- 你现在运行了多久？
- CPU、内存、磁盘使用情况如何？
- 网卡流量是多少？
- 当前有哪些进程和服务？
- 系统版本和主机名是什么？

这些问题对运维很有价值，但如果 SNMP 配置不当，同样会变成攻击者的信息来源。

**核心特点**：

- **端口**：Agent 默认监听 UDP **161**；Trap 告警默认发往 UDP **162**
- **通信模型**：管理站（Manager）向被管理设备上的代理（Agent）发起查询
- **认证方式**：SNMPv1/v2c 使用团体名（Community String），常见默认值是 `public`
- **数据定位方式**：可查询的数据由 **MIB** 定义，并通过 **OID** 编号定位

可以把 SNMP 理解成一套“远程查表系统”：

```
Manager：我想查 1.3.6.1.2.1.1.5.0 这个编号对应的值
Agent：这个编号是 sysName.0，当前值是 WIN-SERVER01
```

**版本演进历史**：

| 版本      | 发布年份 | 核心特点                        | 安全性         |
| ------- | ---- | --------------------------- | ----------- |
| SNMPv1  | 1988 | 最早版本，定义 Get/Set/Trap 基础操作   | 极差（明文团体名）   |
| SNMPv2c | 1996 | 增加 GetBulk 和 Inform，错误处理更完善 | 仍差（仍然明文团体名） |
| SNMPv3  | 2004 | 引入用户认证、消息加密、访问控制            | 好（推荐生产使用）   |

> 注：SNMPv2c 虽然比 v1 功能更强，但仍然使用明文团体名模型。因此在安全性上，SNMPv1/v2c 通常被放在同一类风险中讨论。
> 

---

### 3.2 SNMP 的典型应用场景

SNMP 虽然存在安全风险，但因为轻量、通用、设备支持广泛，仍然是企业网络运维中的常见协议。典型场景包括：

1. **服务器与网络设备监控**
    - Zabbix、PRTG、SolarWinds、Cacti 等平台常用 SNMP 拉取状态数据
    - 常见指标包括 CPU、内存、磁盘、网口流量、设备温度等
2. **网络拓扑自动发现**
    - 通过 SNMP 获取路由表、ARP 表、接口表、邻居信息，辅助绘制网络拓扑
3. **打印机、UPS、摄像头等设备管理**
    - 打印机耗材余量、UPS 电池状态、摄像头设备状态等常通过 SNMP 暴露
4. **告警上报（Trap）**
    - 设备故障、端口 down、登录失败等事件可由 Agent 主动推送给 NMS
5. **配置修改（Set，较少使用）**
    - SNMP 也支持修改部分配置，但生产环境中风险较高，通常应严格限制或禁用

<aside>
💡

举例：一个企业有 500 台路由器，运维不可能每天逐台登录查看状态。只要在 Zabbix 中配置 SNMP 模板，就能统一读取设备状态，并在端口 down 或 CPU 异常时自动告警。这就是 SNMP 的价值。

</aside>

从攻击者视角看，问题也出在这里：**运维为了方便集中读取状态而开放的接口，如果认证弱，就可能被未授权人员读取。**

---

### 3.3 SNMP 工作模型：谁问、问谁、怎么问？

SNMP 采用 **Manager-Agent** 架构：

```
┌──────────────┐    Get/GetNext/GetBulk/Set   ┌──────────────┐
│  Manager     │ ───────────────────────────► │  Agent       │
│  Kali / NMS  │ ◄─────────────────────────── │  Windows     │
└──────────────┘        Response（数据）       └──────────────┘
                               ◄── Trap（主动告警）──┘
```

**两个角色的分工**：

- **Manager（管理站）**：发出查询的一端，例如 Zabbix 服务器，或本实验中的 Kali Linux
- **Agent（代理）**：运行在被管理设备上的 SNMP 服务，例如 Windows Server 的 SNMP Service

**通信过程可以拆成四步**：

1. Manager 知道目标 IP、SNMP 版本和团体名
2. Manager 指定一个想读取的 OID
3. Agent 判断团体名和访问来源是否允许
4. 如果允许，Agent 返回该 OID 对应的当前值

例如：

```
Kali:    使用 public 询问 192.168.1.20 的 1.3.6.1.2.1.1.5.0
Windows: 团体名 public 允许只读，返回主机名 WIN-SERVER01
```

**SNMP 的 5 种核心 PDU（操作）**：

| 操作                | 方向              | 作用                  | 实验中的理解        |
| ----------------- | --------------- | ------------------- | ------------- |
| `Get`             | Manager → Agent | 读取指定 OID 的值         | 查一个明确字段，如主机名  |
| `GetNext`         | Manager → Agent | 读取当前 OID 后面的下一个 OID | 沿着 MIB 树向后走一步 |
| `GetBulk`（v2c+）   | Manager → Agent | 一次读取多个后续 OID        | 批量遍历，效率更高     |
| `Set`             | Manager → Agent | 修改指定 OID 的值         | 需要读写权限，风险更高   |
| `Trap` / `Inform` | Agent → Manager | Agent 主动上报告警        | 设备主动通知管理站     |

理解 `GetNext` 很重要：实验中使用的 `snmpwalk` 并不是一次性“下载数据库”，而是从某个 OID 开始，不断执行类似 `GetNext` 的操作，把能访问的子树逐项走出来。

---

### 3.4 MIB 和 OID：SNMP 如何给“可查询信息”编号？

SNMP 最容易混淆的概念就是 **MIB** 和 **OID**。可以先记住一句话：

> **MIB 是说明书，OID 是说明书里每个项目的编号，Agent 返回的是编号对应的实时值。**
> 

也就是说：

- MIB 负责说明“有哪些字段可以查、字段叫什么、字段类型是什么”
- OID 负责给每个字段一个全局唯一编号
- Agent 负责保存或实时生成这些字段的值
- Manager 负责按 OID 发起查询

#### 3.4.1 什么是 MIB？

**MIB（Management Information Base，管理信息库）** 不是传统意义上的数据库，而是一套 SNMP 管理对象的定义集合。

它回答的是：

- 设备有哪些信息可以被 SNMP 查询？
- 这些信息的名称是什么？
- 每个信息的数据类型是什么？
- 这些信息在 OID 树中的位置在哪里？

例如，MIB 会定义：

```
sysName 表示系统名称
sysDescr 表示系统描述
hrSWRunName 表示运行中的进程名称
ifDescr 表示网络接口描述
```

**关键澄清**：MIB 本身通常是 `.mib` 文本文件，使用 ASN.1 语法描述对象结构。它不是存放真实 CPU 使用率、进程列表的数据库。真实数据来自目标主机上的 SNMP Agent。

可以类比为：

| 类比对象 | 在 SNMP 中对应什么 |
| --- | --- |
| 字典目录 | MIB |
| 字典条目的编号 | OID |
| 字典条目的当前内容 | Agent 返回的值 |
| 查字典的人 | Manager / snmpget / snmpwalk |

**常见 MIB**：

- **RFC1213-MIB / MIB-II**：最基础的标准 MIB，包含系统信息、接口、IP、TCP、UDP 等
- **HOST-RESOURCES-MIB**：主机资源 MIB，包含磁盘、进程、已安装软件等，本实验重点使用
- **厂商私有 MIB**：厂商扩展信息，例如 Microsoft、Cisco、Net-SNMP 等各自的私有对象

#### 3.4.2 什么是 OID？

**OID（Object Identifier，对象标识符）** 是 MIB 中每个管理对象的唯一编号，写成用点分隔的数字序列。

例如：

```
1.3.6.1.2.1.1.1.0
```

它对应的是 `sysDescr.0`，也就是“系统描述”这个值。

可以把 OID 看成一条树形路径：

```
1.3.6.1.2.1.1.1.0
│ │ │ │ │ │ │ │ └─ .0 表示标量对象的实例
│ │ │ │ │ │ │ └─── sysDescr(1)：系统描述
│ │ │ │ │ │ └───── system(1)：系统信息分支
│ │ │ │ │ └─────── mib-2(1)：标准 MIB-II
│ │ │ │ └───────── mgmt(2)：管理对象
│ │ │ └─────────── internet(1)
│ │ └───────────── dod(6)
│ └─────────────── org(3)
└───────────────── iso(1)
```

如果用文件系统类比，OID 就像路径：

```
/iso/org/dod/internet/mgmt/mib-2/system/sysDescr/0
```

如果用数据库类比，OID 就像“表名 + 字段名 + 行号”的组合。不同的是，SNMP 使用数字树来保证全球唯一、层级清晰、便于厂商扩展。

**一些重要根 OID**：

- `1.3.6.1.2.1`：标准 MIB-II，对应大量通用系统与网络信息
- `1.3.6.1.2.1.25`：HOST-RESOURCES-MIB，主机资源信息，如进程、软件、存储
- `1.3.6.1.4.1`：厂商私有扩展，后面跟 IANA 分配的厂商编号
    - `1.3.6.1.4.1.9` = Cisco
    - `1.3.6.1.4.1.311` = Microsoft
    - `1.3.6.1.4.1.2021` = Net-SNMP

#### 3.4.3 MIB、OID、Agent 返回值之间的关系

三者关系可以用下面这张图理解：

```
MIB 文件：定义对象名称、类型、树中位置
   │
   ├─ sysDescr  → OID: 1.3.6.1.2.1.1.1
   ├─ sysName   → OID: 1.3.6.1.2.1.1.5
   └─ hrSWRunName → OID: 1.3.6.1.2.1.25.4.2.1.2

Manager 查询 OID
   │
   ▼
Agent 返回该 OID 在当前设备上的实际值
```

具体例子：

```
snmpget -v2c -c public 192.168.1.20 1.3.6.1.2.1.1.5.0
```

这条命令的含义是：

| 部分 | 含义 |
| --- | --- |
| `snmpget` | 读取单个 OID 的值 |
| `-v2c` | 使用 SNMPv2c |
| `-c public` | 使用团体名 public |
| `192.168.1.20` | 目标 Agent 地址 |
| `1.3.6.1.2.1.1.5.0` | 要查询的对象：sysName.0，即主机名 |

Agent 可能返回：

```
SNMPv2-MIB::sysName.0 = STRING: WIN-SERVER01
```

这说明：OID 只是“问哪个字段”，真正泄露的是 Agent 返回的字段值。

#### 3.4.4 为什么有些 OID 后面要加 `.0`？

SNMP 中对象大致分为两类：

| 类型   | 特点        | 示例              |
| ---- | --------- | --------------- |
| 标量对象 | 一台设备只有一个值 | 主机名、系统描述、运行时间   |
| 表格对象 | 一台设备有多行值  | 进程列表、网卡列表、ARP 表 |

对于标量对象，查询时通常要在对象 OID 后加 `.0`，表示“取这个对象的唯一实例”。

例如：

```
1.3.6.1.2.1.1.5     表示 sysName 这个对象
1.3.6.1.2.1.1.5.0   表示 sysName 的具体值
```

对于表格对象，后面跟的是行索引。例如进程名对象 `hrSWRunName` 的 OID 是：

```
1.3.6.1.2.1.25.4.2.1.2
```

某一行可能显示为：

```
1.3.6.1.2.1.25.4.2.1.2.244 = STRING: "svchost.exe"
```

其中最后的 `244` 通常对应这一行的索引，在进程表中可以理解为某个进程条目。

---

### 3.5 从 OID 到命令：snmpget 和 snmpwalk 的区别

理解了 MIB 和 OID 后，再看 SNMP 工具就很清楚了：工具只是帮我们按 OID 查询 Agent。

Kali 默认安装了 **Net-SNMP** 工具套件，常用命令如下：

| 命令 | 作用 | 使用场景 |
| --- | --- | --- |
| `snmpget` | 读取指定 OID 的单个值 | 已知明确 OID，例如读取主机名 |
| `snmpgetnext` | 读取紧跟在指定 OID 后面的下一个 OID | 探索树结构 |
| `snmpwalk` | 从指定 OID 开始连续读取后续对象 | 枚举一个分支或整棵可访问子树 |
| `snmpbulkwalk` | 使用 GetBulk 批量遍历 | 表很大时提高效率 |
| `snmpset` | 修改指定 OID 的值 | 需要读写团体名，风险较高 |
| `snmptranslate` | OID 与文字名称互转 | 学习和排查 OID 时使用 |

**通用格式**：

```
snmp<command> -v<版本> -c <团体名> <目标IP> [OID]
```

**查询单个字段：snmpget**

```
# 用数字 OID 查询系统描述
snmpget -v2c -c public 192.168.1.20 1.3.6.1.2.1.1.1.0

# 用文字名称查询同一个对象，前提是本机能解析对应 MIB
snmpget -v2c -c public 192.168.1.20 sysDescr.0
```

**遍历一个分支：snmpwalk**

```
# 遍历 system 分支，获取系统描述、主机名、运行时间等
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.1

# 遍历运行进程名称分支
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.25.4.2.1.2
```

二者的区别可以这样记：

| 工具 | 像什么 | 适合做什么 |
| --- | --- | --- |
| `snmpget` | 精确查一个门牌号 | 验证某个具体信息是否可读 |
| `snmpwalk` | 沿着一条街逐户敲门 | 批量枚举一个分支下的信息 |

**OID 与名称转换：snmptranslate**

```
snmptranslate -On SNMPv2-MIB::sysDescr.0
# 输出：.1.3.6.1.2.1.1.1.0

snmptranslate -Of .1.3.6.1.2.1.1.1.0
# 输出：.iso.org.dod.internet.mgmt.mib-2.system.sysDescr.0
```

**SNMPv3 查询示例**（生产环境推荐）：

```
snmpwalk -v3 -u 用户名 -l authPriv -a SHA -A "认证密码" -x AES -X "加密密码" 192.168.1.20
```

<aside>
⚠️

**常见问题**：`snmpwalk` 返回 `Timeout: No Response` 不一定表示 SNMP 没开，还可能是：
① 版本不匹配；
② 团体名错误；
③ 防火墙拦截 UDP 161；
④ Windows SNMP 的 PermittedManagers 限制了来源 IP。

</aside>

---

### 3.6 MIB 树结构与常用 OID

SNMP 信息以树形结构组织。下面这棵树只展示本实验最常用的分支：

```
iso(1)
└── org(3)
    └── dod(6)
        └── internet(1)
            ├── mgmt(2)
            │   └── mib-2(1)                         ← 标准 MIB-II
            │       ├── system(1)                    ← 系统基础信息
            │       │   ├── sysDescr(1).0            ← 系统描述
            │       │   ├── sysObjectID(2).0         ← 设备对象 ID
            │       │   ├── sysUpTime(3).0           ← 运行时间
            │       │   └── sysName(5).0             ← 主机名
            │       ├── interfaces(2)                ← 网卡接口信息
            │       ├── ip(4)                        ← IP 地址、路由、ARP
            │       ├── tcp(6)                       ← TCP 统计与连接信息
            │       ├── udp(7)                       ← UDP 监听信息
            │       └── host(25)                     ← 主机资源
            │           ├── hrStorage(2)             ← 存储信息
            │           ├── hrSWRun(4)               ← 运行进程
            │           └── hrSWInstalled(6)         ← 已安装软件
            └── private(4)
                └── enterprises(1)                   ← 厂商私有 MIB
```

本实验中最常用的 OID 可以按“攻击者想知道什么”来记：

| 想获取的信息       | OID                      | 命令示例                                                | 风险          |
| ------------ | ------------------------ | --------------------------------------------------- | ----------- |
| 系统描述 / OS 版本 | `1.3.6.1.2.1.1.1.0`      | `snmpget -v2c -c public IP 1.3.6.1.2.1.1.1.0`       | 匹配系统漏洞      |
| 主机名          | `1.3.6.1.2.1.1.5.0`      | `snmpget -v2c -c public IP 1.3.6.1.2.1.1.5.0`       | 判断系统角色      |
| 系统运行时间       | `1.3.6.1.2.1.1.3.0`      | `snmpget -v2c -c public IP 1.3.6.1.2.1.1.3.0`       | 判断补丁或重启情况   |
| 运行进程名称       | `1.3.6.1.2.1.25.4.2.1.2` | `snmpwalk -v2c -c public IP 1.3.6.1.2.1.25.4.2.1.2` | 发现安全软件和业务组件 |
| 进程路径         | `1.3.6.1.2.1.25.4.2.1.4` | `snmpwalk -v2c -c public IP 1.3.6.1.2.1.25.4.2.1.4` | 判断软件安装位置    |
| 已安装软件        | `1.3.6.1.2.1.25.6.3`     | `snmpwalk -v2c -c public IP 1.3.6.1.2.1.25.6.3`     | 对照 CVE 查漏洞  |
| IP 地址表       | `1.3.6.1.2.1.4.20`       | `snmpwalk -v2c -c public IP 1.3.6.1.2.1.4.20`       | 发现多网卡和内网地址  |
| ARP 缓存表      | `1.3.6.1.2.1.4.22`       | `snmpwalk -v2c -c public IP 1.3.6.1.2.1.4.22`       | 辅助内网横向发现    |

**从理论到实验的对应关系**：

```
Nmap 发现 161/UDP
        ↓
snmpget 查询 sysDescr/sysName 等单个 OID
        ↓
snmpwalk 遍历 hrSWRun/hrSWInstalled/ipNetToMedia 等分支
        ↓
整理泄露出的系统版本、进程、软件、网卡和 ARP 信息
        ↓
说明为什么默认 public 团体名需要删除或替换
```

---

### 3.7 SNMP安全性分析

```
安全性排序：SNMPv3 >> SNMPv2c = SNMPv1

SNMPv1/v2c 的致命弱点：
┌────────────────────────────────────────────────────┐
│ 1. 团体名（Community String）= 明文"密码"          │
│    默认 public（只读）、private（读写）            │
│    可通过网络嗅探直接捕获                         │
│                                                    │
│ 2. 无数据加密                                      │
│    所有MIB数据明文传输，包含系统版本、进程列表等     │
│                                                    │
│ 3. 无消息认证                                      │
│    攻击者可伪造SNMP响应，发送虚假告警              │
│                                                    │
│ 4. 默认配置极弱                                    │
│    大多数设备安装后使用默认public团体名            │
└────────────────────────────────────────────────────┘

SNMPv3 的安全增强：
- USM（User-based Security Model）：用户名+密码认证
- 支持MD5/SHA认证 + DES/AES加密
- 支持访问控制（View-based Access Control）
```

### 3.8 SNMP 枚举能拿到多"离谱"的信息？

相比单纯的端口扫描，SNMP 枚举的信息密度要高得多。一次成功的 `snmpwalk` 可能直接暴露：

- 操作系统精确版本（精确到 Build 号）
- 主机名、域名、系统管理员联系方式
- **所有正在运行的进程**（包括杀软进程名，可用于规避）
- 已安装软件及版本号（直接对照 CVE 库）
- 所有网卡、IP、路由表、ARP 表（内网横向移动地图）
- 共享文件夹、打印机、用户账户

可以说，一个配置不当的 SNMP 服务，等同于把服务器的"身份证"交给任何人查看。

---

## 4. Windows高危端口速记

在做信息收集实验时，以下端口发现意味着什么：

| 端口        | 服务          | 发现后的攻击思路           |
| --------- | ----------- | ------------------ |
| 21        | FTP         | 匿名登录？弱口令？嗅探明文密码？   |
| 23        | Telnet      | 明文传输，可嗅探凭据，应禁用     |
| 80/443    | HTTP/HTTPS  | Web漏洞扫描、目录遍历、SQL注入 |
| 135       | RPC         | 可能存在远程代码执行漏洞       |
| 139/445   | SMB/NetBIOS | MS17-010永恒之蓝、空会话枚举 |
| 161       | SNMP        | 默认团体名枚举（本实验重点）     |
| 389/636   | LDAP        | 域控制器，域渗透入口         |
| 1433      | SQL Server  | 弱口令爆破、SQL注入        |
| 3306      | MySQL       | 弱口令爆破              |
| 3389      | RDP         | 弱口令暴力破解（BlueKeep）  |
| 5985/5986 | WinRM       | 远程PowerShell执行     |

---

## 5. 本实验的知识链路图

```mermaid
flowchart LR
    A[信息收集方法论] --> B[主动扫描]
    B --> C[Nmap 主机发现]
    C --> D[Nmap 端口/服务识别]
    D --> E{发现 161/UDP?}
    E -->|是| F[SNMP 枚举]
    F --> G[默认团体名 public]
    G --> H[泄露系统信息]
    H --> I[安全加固]
    I --> J[验证加固效果]
    E -->|否| K[其他攻击面]
```

<aside>
🎯

**实验关键提示**：本实验的核心在于理解 SNMPv1/v2c 使用默认团体名 `public` 可泄露大量系统信息。实验流程为：
发现SNMP服务（nmap -sU）→ 使用默认团体名枚举（snmpwalk）→ 分析泄露信息的安全影响 → 修改团体名加固 → 验证加固效果。

</aside>

---

# 第二部分：实验操作

```
┌─────────────────────┐              NAT模式                 ┌─────────────────────┐
│    Kali Linux       │           192.168.1.0/24             │  Windows Server     │
│   2025.4（攻击机）   │◄─────────────────────────────────►  │    2025（靶机）     │
│  IP: 192.168.1.10   │                                      │  IP: 192.168.1.20   │
└─────────────────────┘                                      └─────────────────────┘
```

**虚拟机设置**（靶机）：

| 项目 | 配置 |
| --- | --- |
| 内存 | 4 GB |
| 网络适配器 | NAT模式 |
| 快照 | 实验前创建快照（命名：实验一-初始状态） |

**靶机初始配置脚本**（以管理员身份在PowerShell中执行）：

```powershell
# ============================================
# 靶机环境初始化脚本 - 实验一
# ============================================

# 1. 安装SNMP服务
Install-WindowsFeature SNMP-Service, SNMP-WMI-Provider -IncludeManagementTools

# 2. 配置防火墙放行SNMP（UDP 161）
New-NetFirewallRule -DisplayName "SNMP Service" -Direction Inbound -Protocol UDP -LocalPort 161 -Action Allow

# 3. 创建测试账户
net user admin P@ssw0rd /add
net localgroup Administrators admin /add

# 4. 启用远程注册表（默认已启用）
Set-Service -Name "RemoteRegistry" -StartupType Automatic

# 5. 重启
Restart-Computer -Force
```

**SNMP服务配置**（重启后在图形界面完成）：

1. WIN+R运行 `services.msc`，找到 **SNMP Service**
2. 右键 → 属性 → **安全** 选项卡
3. 添加团体名 `public`，权限设为 **READ ONLY**
4. 勾选 **接受来自任何主机的 SNMP 数据包**
5. 点击确定，重启SNMP服务

**攻击机配置**：

| 项目 | 配置 |
| --- | --- |
| 内存 | 2 GB |
| 网络适配器 | NAT模式 |

**攻击机网络配置**：

```
# 编辑网络配置文件
sudo nano /etc/network/interfaces

# 或者使用 NetworkManager
sudo nmcli connection show
sudo nmcli connection modify "Wired connection 1" ipv4.addresses 192.168.1.10/24 ipv4.gateway 192.168.1.2
sudo nmcli connection up "Wired connection 1"

# 验证IP
ip addr show
ping 192.168.1.20
```

---

## 任务一：主机发现与端口扫描

**步骤1：使用Nmap进行主机发现**

```
# 扫描整个网段，发现存活主机
nmap -sn 192.168.1.0/24

# 预期输出：
# Nmap scan report for 192.168.1.20
# Host is up (0.0010s latency).
# Nmap done: 256 IP addresses (2 hosts up) scanned in 2.5 seconds

# 也可以使用快速主机发现
nmap -sn -PE -PA 192.168.1.0/24
```

**步骤2：使用ARP扫描发现主机**

```
# 使用arp-scan进行二层发现
sudo arp-scan -l

# 预期输出：
# 192.168.1.1  xx:xx:xx:xx:xx:xx  VMware
# 192.168.1.20 xx:xx:xx:xx:xx:xx  VMware
# 192.168.1.10 xx:xx:xx:xx:xx:xx  (本机)

# 使用netdiscover
sudo netdiscover -r 192.168.1.0/24
```

> **知识关联**：对应讲义中”服务器用途分类”——通过扫描确认目标是一台服务器而非普通工作站。
> 

---

**步骤3：全端口扫描**

```
# 扫描全部65535个端口
sudo nmap -p- -T4 192.168.1.20

# 预期输出：
# PORT     STATE SERVICE
# 135/tcp  open  msrpc
# 139/tcp  open  netbios-ssn
# 445/tcp  open  microsoft-ds
# 161/udp  open  snmp
# 3389/tcp open  ms-wbt-server

# 也可以只扫描常见端口（更快）
nmap -p 1-1024 -T4 192.168.1.20
```

> **知识关联**：对应讲义中”Windows服务端口分类”和”高危端口重点关注”——139/445是SMB端口，3389是RDP端口，161是SNMP端口。
> 

**步骤4：服务版本探测**

```
# 探测开放端口的服务版本信息
nmap -sV -p 135,139,445,161,3389 192.168.1.20

# 预期输出：
# PORT     STATE SERVICE     VERSION
# 135/tcp  open  msrpc       Microsoft Windows RPC
# 139/tcp  open  netbios-ssn Windows Server 2025 netbios-ssn
# 445/tcp  open  microsoft-ds Windows Server 2025 microsoft-ds
# 3389/tcp open  ms-wbt-server Microsoft Terminal Services

# 使用-A参数同时执行脚本扫描和OS识别
nmap -A 192.168.1.20
```

**步骤5：使用Nmap脚本进行漏洞扫描**

```
# 扫描常见服务漏洞
nmap --script vuln 192.168.1.20

# 也可以针对特定服务进行漏洞扫描
nmap --script smb-vuln* -p 445 192.168.1.20
nmap --script ftp-vuln* -p 21 192.168.1.20
nmap --script http-vuln* -p 80 192.168.1.20

# 注意：漏洞扫描可能触发安全设备告警，仅在授权环境使用
```

> **知识关联**：对应讲义中”Windows系统服务”——通过扫描识别目标运行的哪些服务，评估攻击面。
> 

---

## 任务二：SNMP 枚举渗透

任务一已经确认目标存在 `161/udp open snmp`。接下来不再继续扩大端口扫描范围，而是围绕 SNMP 的三个关键要素展开：

```
目标 IP：192.168.1.20
SNMP 版本：v2c
团体名：public
查询对象：OID
```

只要 `public` 团体名有效，攻击机就可以像管理平台一样向 Windows Server 的 SNMP Agent 查询信息。

**步骤6：验证默认团体名并读取系统基础信息**

先不要直接 `snmpwalk` 全部信息。初学时建议先用 `snmpget` 查询单个 OID，理解“一个 OID 对应一个返回值”的关系。

```
# 读取系统描述：sysDescr.0
snmpget -v2c -c public 192.168.1.20 1.3.6.1.2.1.1.1.0

# 读取主机名：sysName.0
snmpget -v2c -c public 192.168.1.20 1.3.6.1.2.1.1.5.0

# 读取系统运行时间：sysUpTime.0
snmpget -v2c -c public 192.168.1.20 1.3.6.1.2.1.1.3.0
```

可能看到类似输出：

```
SNMPv2-MIB::sysDescr.0 = STRING: Hardware: Intel64 Family ... Windows Server ...
SNMPv2-MIB::sysName.0 = STRING: WIN-SERVER01
DISMAN-EVENT-MIB::sysUpTimeInstance = Timeticks: (123456) 0:20:34.56
```

这一步对应前置知识中的关系：

```
OID：1.3.6.1.2.1.1.5.0
        ↓
MIB 名称：sysName.0
        ↓
Agent 返回值：WIN-SERVER01
```

> **安全分析**：攻击者仅凭默认团体名 `public`，无需系统账号密码，就能确认操作系统版本、主机名和运行时间。这些信息可以继续用于漏洞匹配、资产识别和攻击路径规划。
> 

**步骤7：从单点查询过渡到分支遍历**

当我们知道某个分支下有一组相关信息时，就不需要一个个 `snmpget`，而是使用 `snmpwalk` 从该分支开始连续读取。

```
# 遍历 system 分支，集中获取系统描述、主机名、运行时间、联系人等
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.1
```

理解方式：

| 命令 | 查询方式 | 适合场景 |
| --- | --- | --- |
| `snmpget ... 1.3.6.1.2.1.1.5.0` | 只查主机名这一个对象 | 已知目标字段 |
| `snmpwalk ... 1.3.6.1.2.1.1` | 遍历 system 整个分支 | 想枚举一类系统信息 |

**步骤8：枚举运行中的进程**

运行进程属于 HOST-RESOURCES-MIB 中的 `hrSWRun` 分支。这里使用的是表格对象，所以末尾不是 `.0`，而是会返回多行进程记录。

```
# 获取正在运行的进程名称
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.25.4.2.1.2

# 预期输出：
# HOST-RESOURCES-MIB::hrSWRunName.1 = STRING: "System Idle Process"
# HOST-RESOURCES-MIB::hrSWRunName.4 = STRING: "System"
# HOST-RESOURCES-MIB::hrSWRunName.244 = STRING: "svchost.exe"
# ...

# 获取进程路径信息
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.25.4.2.1.4
```

这里要注意最后一段数字的含义：

```
1.3.6.1.2.1.25.4.2.1.2.244 = "svchost.exe"
                            │
                            └─ 表格行索引，表示某一条进程记录
```

> **安全分析**：进程列表可能暴露杀毒软件、EDR、数据库、中间件、备份软件等关键信息。攻击者可以据此判断目标防护能力和业务组件。
> 

**步骤9：枚举已安装软件**

已安装软件位于 HOST-RESOURCES-MIB 的 `hrSWInstalled` 分支：

```
# 获取已安装软件列表
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.25.6.3
```

分析输出时重点关注：

- 是否存在旧版本 Java、Adobe、Office、数据库客户端等高风险软件
- 是否存在远程管理、备份、杀毒、安全代理等运维或安全软件
- 软件版本是否可以和 CVE 漏洞库对应

**步骤10：枚举网络接口与邻居信息**

网络信息主要位于 `interfaces` 和 `ip` 分支。它们可以帮助攻击者判断这台服务器是否连接多个网段，以及同网段中还可能有哪些主机。

```
# 获取网络接口详细信息
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.2.2

# 获取 IP 地址表
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.4.20

# 获取 ARP 表，辅助发现同网段其他主机
snmpwalk -v2c -c public 192.168.1.20 1.3.6.1.2.1.4.22
```

> **知识关联**：这一步对应前置知识中的 MIB 树结构。`1.3.6.1.2.1.2` 是接口信息，`1.3.6.1.2.1.4` 是 IP 信息，`1.3.6.1.2.1.25` 是主机资源信息。不同 OID 分支对应不同类型的资产信息。
> 

**步骤11：完整枚举并保存结果**

理解单个 OID 和常用分支之后，可以再执行完整枚举，并把结果保存为文件，便于后续分析。

```
# 遍历所有当前团体名可访问的信息，输出可能很多
snmpwalk -v2c -c public 192.168.1.20

# 保存结果
snmpwalk -v2c -c public 192.168.1.20 > snmp-public-result.txt
```

建议在结果中重点搜索以下关键词：

```
sysDescr
sysName
hrSWRunName
hrSWInstalledName
ipAdEntAddr
ipNetToMediaPhysAddress
```

**步骤12：使用 Nmap SNMP 脚本进行自动化枚举**

```
# 自动化枚举Windows系统信息
nmap -sU -p 161 --script snmp-sysdescr 192.168.1.20
nmap -sU -p 161 --script snmp-processes 192.168.1.20
nmap -sU -p 161 --script snmp-win32-services 192.168.1.20
nmap -sU -p 161 --script snmp-netstat 192.168.1.20

# 使用onesixtyone工具爆破SNMP团体名
onesixtyone -c /usr/share/wordlists/onesixtyone/wordlist.txt 192.168.1.20
```

- `-sU`：UDP 扫描模式。SNMP 使用 UDP/161，因此需要 UDP 扫描才能触发相应的探测。
- `-p 161`：指定只扫描/探测 161 端口（SNMP Agent 默认监听端口），速度快且目标明确。
- `--script <脚本名>`：调用 Nmap NSE（Nmap Scripting Engine）脚本，对 SNMP 服务进行“更高层”的自动化枚举。
    - `snmp-sysdescr`：读取系统描述 `sysDescr`（操作系统/版本/设备信息），用于快速指纹识别。
    - `snmp-processes`：枚举运行中的进程列表（常用于发现安全软件进程、第三方服务、可疑组件）。
    - `snmp-win32-services`：枚举 Windows 服务列表（可用于定位高危/可被利用的服务，或识别系统角色）。
    - `snmp-netstat`：枚举网络连接/监听端口（类似 `netstat` 信息），可辅助发现更多可攻击的服务端口。
- `onesixtyone -c <wordlist> <IP>`：使用字典批量尝试 SNMP 团体名（Community String）。
如果命中（例如 `public`），目标会返回 SNMP 响应，说明该团体名有效。团体名相当于 SNMPv1/v2c 的“口令”，配置弱或使用默认值会导致严重信息泄露。

<aside>
⚠️

注意：上述 NSE 脚本和 onesixtyone 在默认情况下通常会尝试使用 `public` 团体名。若靶机修改了团体名或配置了 PermittedManagers（只允许指定管理站 IP），则会出现超时无响应，需要改用正确团体名并确认访问来源 IP 在允许列表中。

</aside>

---

## 任务三：安全加固与验证

**步骤13：修改团体名并限制访问来源**

在Windows Server靶机上执行：

```powershell
# 方法一：通过注册表修改
# 修改团体名
reg add "HKLM\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\ValidCommunities" /v "MyS3cret@2024" /t REG_DWORD /d 4 /f

# 删除默认public团体名
reg delete "HKLM\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\ValidCommunities" /v "public" /f

# 限制仅允许指定IP访问
reg add "HKLM\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\PermittedManagers" /v "1" /t REG_SZ /d "192.168.1.10" /f

# 重启SNMP服务
Restart-Service SNMP
```

**步骤14：验证加固效果**

```
# 使用旧团体名public，应超时无响应
snmpwalk -v2c -c public 192.168.1.20
# 预期输出：Timeout: No Response from 192.168.1.20

# 使用新团体名，正常获取数据
snmpwalk -v2c -c "MyS3cret@2024" 192.168.1.20
# 预期输出：正常返回SNMP信息

# 从非授权IP尝试，应超时（需换一台机器测试）
```

---

# 第三部分：实验记录与思考

## 实验记录清单

| 序号 | 记录项 | 说明 |
| --- | --- | --- |
| 1 | Nmap扫描结果截图 | 包含端口列表和服务版本 |
| 2 | SNMP枚举结果 | 系统版本、主机名、进程列表、安装软件 |
| 3 | 安全风险评估 | 基于枚举信息分析存在的安全风险 |
| 4 | 加固前后对比 | 修改团体名前后的访问效果对比截图 |

## 思考题

1. 为什么SNMP默认团体名`public`如此危险？它能泄露哪些信息？
2. 结合讲义中的”最小化服务原则”，分析靶机上哪些服务是不必要的？
3. 如果生产环境必须使用SNMP，应该采取哪些安全措施？
4. SNMPv3相比v1/v2c有哪些安全增强？

## 环境清理脚本

```powershell
# 恢复靶机到初始快照，或手动执行以下清理：
# 1. 卸载SNMP服务
Uninstall-WindowsFeature -Name SNMP-Service, SNMP-WMI-Provider

# 2. 删除测试账户
net user admin /delete

# 3. 启用防火墙
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# 4. 关闭远程注册表
Set-Service -Name "RemoteRegistry" -StartupType Disabled
Stop-Service "RemoteRegistry"
```

> **免责声明**：本实验仅用于授权的安全教学环境。对任何未授权系统进行扫描或渗透测试属于违法行为。
>