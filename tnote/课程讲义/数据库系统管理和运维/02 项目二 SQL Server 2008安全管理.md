# 02.项目二 SQL Server 2008安全管理

## 🎯 学习目标

通过本项目的学习，你应该能够：

1. **理解并配置 SQL Server 的三种身份验证模式**（Windows 身份验证、SQL Server 身份验证、混合模式），能根据实际场景选择合适的模式
2. **掌握登录名与数据库用户的区别和关系**，能独立完成登录名创建、数据库用户创建及二者的映射操作
3. **掌握权限管理的三种控制语句**（GRANT、DENY、REVOKE），理解权限优先级规则，能为用户精确分配和撤销权限
4. **理解角色的概念和作用**，能区分服务器角色与数据库角色，能创建和管理自定义数据库角色
5. **能够通过 SSMS 界面和 T-SQL 脚本两种方式**完成上述所有安全管理操作

---

# 任务一 SQL Server 身份验证模式

## 🧠 理论知识

### 三种身份验证模式

**身份验证**是识别连接 SQL Server 的操作者身份的过程。SQL Server 提供两种验证方式，组合为三种配置模式：

**① Windows 身份验证模式（Windows Authentication）**

- 使用 Windows 操作系统的用户账户连接 SQL Server，无需再输入单独的密码
- 利用 Windows 的 Kerberos（域环境）或 NTLM（工作组环境）协议进行身份认证
- 优点：统一账户管理，自动继承 Windows 的密码复杂性策略和账户锁定策略，安全性最高
- 适用场景：企业域环境内部应用，所有用户都有 Windows 域账户的情况
- 典型用法：公司内部的 ERP 系统、OA 系统等通过域账号直接访问数据库

**② SQL Server 身份验证（SQL Server Authentication）**

- 用户名和密码由 SQL Server 内部创建和存储（保存在 master 数据库的系统表中）
- 完全独立于 Windows 操作系统的账户体系
- 优点：支持跨平台访问（Linux/macOS 客户端均可使用）、不依赖 Windows 域环境
- 缺点：密码存储和管理完全由 SQL Server 负责，需要单独配置密码策略
- 适用场景：互联网应用、跨平台项目、没有 Windows 域环境的开发测试环境

**③ 混合模式（Mixed Mode）**

- 同时支持 Windows 身份验证和 SQL Server 身份验证
- 用户可以选择任意一种方式登录
- **教学和开发环境推荐使用**，灵活度最高
- 生产环境中建议仅使用 Windows 身份验证（安全性更高）

⚠️

**sa 账户说明**：

- sa（System Administrator）是 SQL Server 安装时自动创建的内置超级管理员账户
- 仅在 SQL Server 身份验证或混合模式下可用
- sa 默认拥有 sysadmin 服务器角色的全部权限，可以执行任何操作
- **安全建议**：生产环境应禁用 sa 账户，另外创建具名管理员账户，便于操作审计和追溯

---

## 🛠️ 实践操作

### 操作一：通过 SSMS 查看当前身份验证模式

📌

**操作目标**：了解当前 SQL Server 实例使用的是哪种身份验证模式。

1. 打开 **SQL Server Management Studio (SSMS)** ，使用 Windows 身份验证连接到本地服务器
2. 在左侧**对象资源管理器**中，找到服务器名称节点（最顶层，通常显示为 `计算机名\实例名`）
3. **右键点击**服务器名称 → 选择 **“属性(Properties)”**
4. 在弹出的 **“服务器属性”** 对话框中，点击左侧的 **“安全性(Security)”** 页
    1. 在右侧面板中查看 **“服务器身份验证”** 区域，可以看到当前选中的模式：
        - **Windows 身份验证模式**：只接受 Windows 账户登录
        - **SQL Server 和 Windows 身份验证模式**：即混合模式，两种方式都接受

### 操作二：将身份验证模式改为混合模式

📌

**操作目标**：将身份验证模式从”仅 Windows”改为”混合模式”，以便后续可以使用 sa 等 SQL Server 登录名。

1. 在 **“服务器属性”** 对话框的 **“安全性”** 页中（同上操作进入）
2. 将 **“服务器身份验证”** 选项改为 **“SQL Server 和 Windows 身份验证模式”**
3. 点击 **“确定”** 关闭对话框
4. 此时 SSMS 会弹出提示： **“更改服务器身份验证模式后，需要重新启动 SQL Server 才能生效”**
5. 重启 SQL Server 服务：
    - **方法一（SSMS 界面）** ：在对象资源管理器中右键服务器名称 → 选择 **“重新启动(Restart)”** → 确认重启
    - **方法二（服务管理器）** ：打开 Windows **“服务”** 管理器（`services.msc`），找到 **SQL Server (实例名)** 服务 → 右键 **“重新启动”**
    - **方法三（SQL Server 配置管理器）** ：打开 SQL Server Configuration Manager → 在左侧选择 **SQL Server 服务** → 右键对应实例 → **“重新启动”**

### 操作三：通过 SSMS 界面启用 sa 账户并设置密码

📌

**操作目标**：启用被禁用的 sa 账户，并为其设置一个强密码，以便使用 SQL Server 身份验证登录。

1. 在 SSMS 的**对象资源管理器**中，展开 **“安全性(Security)”** 节点
2. 展开 **“登录名(Logins)”** 子节点
3. 找到 **sa** 登录名（可能显示一个红色向下箭头 ↓，表示已禁用）
4. **双击** sa 或右键 → **“属性(Properties)”** ，打开 **“登录属性”** 对话框
5. 在 **“常规(General)”** 页中：
    - 确认身份验证方式为 **“SQL Server 身份验证”**
    - 在 **“密码”** 和 **“确认密码”** 栏中输入新密码（需符合密码复杂性要求，如 `StrongP@ssw0rd123!`）
6. 切换到左侧 **“状态(Status)”** 页：
    - 将 **“登录(Login)”** 选项改为 **“已启用(Enabled)”** （如果当前是”已禁用”）
7. 点击 **“确定”** 保存设置
8. 验证：断开当前连接 → 重新连接时选择 **“SQL Server 身份验证”** → 输入用户名 `sa` 和刚设置的密码 → 成功连接即表示 sa 账户已正常启用

### 操作四：使用 T-SQL 脚本启用 sa（补充方法）

💡

以下 T-SQL 脚本与上面的界面操作效果完全相同，适合批量操作或脚本化管理的场景。

```sql
USE master;

-- 启用 sa 账户
ALTER LOGIN sa ENABLE;

-- 设置强密码
ALTER LOGIN sa WITH PASSWORD = 'StrongP@ssw0rd123!';

-- 查看所有登录名状态（验证 sa 是否已启用）
SELECT name, type_desc, is_disabled, create_date
FROM sys.server_principals
WHERE type IN ('S','U','G')
ORDER BY type_desc, name;
```

## 📝 任务一知识点总结

✅

**核心知识点回顾**：

- SQL Server 提供三种身份验证模式：**Windows 身份验证**（最安全，适合域环境）、**SQL Server 身份验证**（跨平台，独立账户）、**混合模式**（两者兼容，教学推荐）
- **sa** 是内置超级管理员账户，拥有 sysadmin 角色全部权限，生产环境建议禁用
- 更改身份验证模式后必须**重启 SQL Server 服务**才能生效
- 可通过 **SSMS 界面**或 **T-SQL 脚本**（`ALTER LOGIN`）两种方式管理登录名和验证模式

---

# 任务二 数据库用户管理

## 🧠 理论知识

### 登录名与数据库用户的区别

这是 SQL Server 安全管理中**最核心的概念**，必须理解清楚：

🔑

**核心要点**：登录名（Login）是”能不能进入 SQL Server 大门”的钥匙；数据库用户（User）是”进入大门后能不能进入某个房间”的通行证。一个登录名想要访问某个数据库，必须在该数据库中有一个对应的数据库用户。

```jsx
SQL Server 实例
├── 登录名（Login）← 服务器级别，控制能否连接到 SQL Server 实例
│       ↓ 映射（一对多）
└── 数据库 A
│       └── 数据库用户（User）← 数据库级别，控制能否访问该数据库
└── 数据库 B
        └── 数据库用户（User）← 同一个登录名可映射到不同数据库的用户
```

| 层级 | 对象 | 作用 | 存储位置 |
| --- | --- | --- | --- |
| **服务器级** | 登录名（Login） | 允许建立到 SQL Server 实例的连接 | master 数据库的 sys.server_principals |
| **数据库级** | 数据库用户（User） | 允许在特定数据库中执行操作 | 各数据库的 sys.database_principals |

⚠️

**关键规则**：一个登录名可以映射到多个数据库中的用户，但在**同一个数据库**中只能映射到**一个**用户。违反此规则时系统会报错。

---

## 🛠️ 实践操作

### 操作一：通过 SSMS 界面创建 SQL Server 登录名

📌

**操作目标**：创建一个名为 `zhang_login` 的 SQL Server 身份验证登录名。

1. 在 SSMS **对象资源管理器**中，展开 **“安全性(Security)”** 节点
2. 右键点击 **“登录名(Logins)”** → 选择 **“新建登录名(New Login…)”**
3. 在弹出的 **“登录名 - 新建”** 对话框中：
    - **常规(General)页**：
        - **登录名**：输入 `zhang_login`
        - 选择 **“SQL Server 身份验证”**
        - 输入**密码**和**确认密码**（如 `P@ssw0rd123!`）
        - 可选：取消勾选”用户在下次登录时必须更改密码”（教学环境方便演示）
        - 可选：勾选”强制实施密码策略”和”强制密码过期”
        - **默认数据库**：选择 `stusta`
    - **服务器角色(Server Roles)页**：
        - 默认只勾选 `public`，暂不添加其他角色
    - **用户映射(User Mapping)页**：
        - 暂时不映射，我们将在下一步手动创建数据库用户
4. 点击 **“确定”** 完成创建
5. 在**登录名**列表中可以看到新创建的 `zhang_login`

### 操作二：通过 SSMS 界面创建 Windows 登录名

📌

**操作目标**：将一个 Windows 用户账户添加为 SQL Server 登录名（仅在域环境或本地 Windows 用户存在时可用）。

1. 右键 **“登录名”** → **“新建登录名”**
2. 在**常规**页中：
    - 选择 **“Windows 身份验证”**
    - 点击 **“搜索”** 按钮 → 在弹出的对话框中输入 Windows 用户名（如 `Administrator`） → 点击 **“检查名称”** 确认 → 点击”确定”
    - 登录名会自动填充为 `计算机名\用户名` 的格式
3. 点击 **“确定”** 完成

### 操作三：通过 SSMS 界面创建数据库用户

📌

**操作目标**：在 stusta 数据库中为 `zhang_login` 创建一个对应的数据库用户。

1. 在对象资源管理器中，展开 **“数据库”** → 展开 **stusta** 数据库
2. 展开 **“安全性(Security)”** → 右键 **“用户(Users)”** → 选择 **“新建用户(New User…)”**
3. 在弹出的 **“数据库用户 - 新建”** 对话框中：
    - **常规(General)页**：
        - **用户类型**：选择”具有登录名的 SQL 用户”
        - **用户名**：输入 `zhang_user`
        - **登录名**：点击右侧 **“…”** 按钮 → 搜索并选择 `zhang_login` → 确定
        - **默认架构**：输入 `dbo`（如果留空则默认也是 dbo）
    - **成员身份(Membership)页**：
        - 暂时不勾选任何数据库角色（后续在权限管理与角色管理中继续配置）
4. 点击 **“确定”**
5. 在 stusta → 安全性 → 用户 列表中可以看到 `zhang_user`

### 操作四：通过 SSMS 界面修改和删除数据库用户

**修改用户名**：

1. 在用户列表中找到 `zhang_user` → **双击**或右键 **“属性”**
2. 在**常规**页中修改**用户名**为 `zhang_new` → 确定

**删除数据库用户**：

1. 右键 `zhang_new` → **“删除(Delete)”** → 确认

**删除登录名**：

1. 回到**安全性 → 登录名**列表，右键 `zhang_login` → **“删除”** → 确认

⚠️

**注意顺序**：删除登录名之前，应先删除所有数据库中与该登录名关联的数据库用户，否则会产生”孤立用户”。

### 操作五：T-SQL 参考脚本（补充）

💡

以下 T-SQL 与上面的界面操作效果相同，供脚本化操作参考。

```sql
-- ===== 服务器级操作 =====
USE master;

-- 创建 SQL Server 登录名
CREATE LOGIN zhang_login
    WITH PASSWORD = 'P@ssw0rd123!',
    DEFAULT_DATABASE = stusta,
    CHECK_EXPIRATION = ON,
    CHECK_POLICY = ON;

-- 创建 Windows 登录名
CREATE LOGIN [计算机名\zhangsan] FROM WINDOWS
    WITH DEFAULT_DATABASE = stusta;

-- ===== 数据库级操作 =====
USE stusta;

-- 创建数据库用户并关联到登录名
CREATE USER zhang_user FOR LOGIN zhang_login
    WITH DEFAULT_SCHEMA = dbo;

-- 修改数据库用户名
ALTER USER zhang_user WITH NAME = zhang_new;

-- 删除数据库用户
DROP USER zhang_new;

-- 删除登录名
USE master;
DROP LOGIN zhang_login;
```

### 操作六：完整用户创建与权限验证流程（综合演示）

📌

**操作目标**：完整走通”创建登录名→创建用户→授权→验证权限”的全流程。

**第一步：创建登录名（SSMS 界面）**

1. 安全性 → 登录名 → 右键”新建登录名”
2. 选择 SQL Server 身份验证，登录名输入 `testuser`，密码 `Test@123456`
3. 取消勾选”用户在下次登录时必须更改密码”→ 确定

**第二步：创建数据库用户（SSMS 界面）**

1. 展开 stusta → 安全性 → 用户 → 右键”新建用户”
2. 用户名 `testuser`，登录名选择 `testuser` → 确定

**第三步：授予权限（SSMS 界面）**

1. 在 stusta → 安全性 → 用户中，双击 `testuser` 打开属性
2. 切换到 **“安全对象(Securables)”** 页
3. 点击 **“搜索”** → 选择”特定对象”→ 对象类型选”表”→ 浏览并勾选 `stu` 表 → 确定
4. 在下方权限列表中，为 `stu` 表勾选 **SELECT** 的”授予”列 → 确定

**第四步：验证权限（T-SQL 测试）**

```sql
-- 切换到 testuser 身份测试
EXECUTE AS USER = 'testuser';
SELECT * FROM stu;          -- ✅ 应成功（已授予 SELECT）
INSERT INTO stu VALUES('X','X','男',20,'X');  -- ❌ 应失败（未授予 INSERT）
REVERT;                     -- 恢复原身份
```

**第五步：查看所有数据库用户（SSMS 界面）**

1. 展开 stusta → 安全性 → 用户，即可看到所有数据库用户列表
2. 双击任意用户可查看其属性、所属角色、权限等信息

## 📝 任务二知识点总结

✅

**核心知识点回顾**：

- **登录名（Login）** 是服务器级别的”大门钥匙”，控制能否连接到 SQL Server 实例
- **数据库用户（User）** 是数据库级别的”房间通行证”，控制能否访问特定数据库
- 一个登录名可以映射到多个数据库中的用户，但在**同一个数据库**中只能映射到**一个**用户
- 登录名存储在 `master.sys.server_principals`，数据库用户存储在各数据库的 `sys.database_principals`
- 删除登录名前应先删除关联的数据库用户，避免产生**孤立用户**
- 完整流程：创建登录名 → 创建数据库用户并映射 → 授权 → 验证

## ⚡ 任务二重难点提示

🔥

**重点**：

- 登录名与数据库用户的**区别和映射关系**
- 创建登录名和数据库用户的完整操作流程（SSMS 界面 + T-SQL 两种方式）

**难点**：

- **两层安全体系的理解**：很多初学者混淆登录名和用户，以为创建了登录名就能访问数据库——实际上还需要在目标数据库中创建对应的用户
- 同一登录名在不同数据库中的用户可以有不同的名称和不同的权限

**易错点**：

- 只创建了登录名而忘记创建数据库用户，导致登录后无法访问任何数据库
- `CREATE USER zhang_user FOR LOGIN zhang_login` 中的 `FOR LOGIN` 关键字不能省略，否则创建的是无登录名的独立用户

---

# 任务三 权限管理

## 🧠 理论知识

💡

在已经完成**登录名创建**和**数据库用户映射**之后，下一步最自然的问题就是：**这个用户到底能做什么？** 因此先掌握 GRANT、DENY、REVOKE 等权限控制，再进入角色的批量授权思路，知识衔接会更顺。

### 权限类型

| 权限类型 | 说明 | 示例 |
| --- | --- | --- |
| **隐含权限** | 固定角色自带的权限，无法单独撤销 | sysadmin 角色成员自动拥有所有权限 |
| **对象权限** | 对表、视图、存储过程等数据库对象的操作权限 | SELECT、INSERT、UPDATE、DELETE、EXECUTE |
| **语句权限** | 执行特定 DDL（数据定义）语句的权限 | CREATE TABLE、CREATE VIEW、CREATE DATABASE |

---

### 三种权限控制语句

| 语句 | 作用 | 效果 |
| --- | --- | --- |
| **GRANT** | 授予权限 | 用户获得指定操作的权限 |
| **DENY** | 明确拒绝权限 | 即使通过角色继承了权限，也被强制拒绝（优先级最高） |
| **REVOKE** | 撤销已有的 GRANT 或 DENY | 恢复为”未授权”的中间状态 |

**权限优先级规则**：

🔑

**DENY > GRANT > 继承自角色的权限 > 无权限（默认拒绝）**

例外：sysadmin 角色成员不受 DENY 限制，始终拥有无条件最高权限。

---

### 三种特殊用户

| 用户类型 | 说明 | 权限特点 |
| --- | --- | --- |
| **系统管理员**（sysadmin 角色成员） | 可执行 SQL Server 中的任何操作 | 不受 DENY 约束，拥有无条件最高权限 |
| **数据库所有者**（dbo） | 创建数据库的账号，映射为该数据库的 dbo 用户 | 拥有该数据库的全部权限 |
| **一般用户** | 普通数据库用户 | 通过 GRANT/DENY/角色来精确控制权限 |

---

## 🛠️ 实践操作

### 操作一：通过 SSMS 界面授予对象权限

📌

**操作目标**：为 `testuser` 授予对 stu 表的 SELECT 和 INSERT 权限，对 course 表的 SELECT 权限。

1. 展开 stusta → 安全性 → 用户 → 双击 `testuser` 打开属性
2. 切换到 **“安全对象(Securables)”** 页
3. 点击 **“搜索”** → 选择 **“特定对象”** → 对象类型选择 **“表”**
4. 点击 **“浏览”** → 勾选 `stu` 和 `course` → 确定
5. 在下方权限列表中：
    - 选中 **stu** 表 → 勾选 **SELECT** 和 **INSERT** 的 **“授予(Grant)”** 列
    - 选中 **course** 表 → 勾选 **SELECT** 的 **“授予(Grant)”** 列
6. 点击 **“确定”** 保存

### 操作二：通过 SSMS 界面拒绝权限（DENY）

📌

**操作目标**：明确拒绝 `testuser` 对 stu 表的 DELETE 权限。

1. 打开 testuser 的用户属性 → 安全对象页
2. 如果 stu 表已在·安全对象列表中，直接选中它
3. 在下方权限列表中，找到 **DELETE** 行 → 勾选 **“拒绝(Deny)”** 列
4. 确定保存

⚠️

**重要**：即使 testuser 后来被加入了 db_datawriter 角色（拥有所有表的写权限），由于 DENY 优先级高于 GRANT，testuser 仍然无法删除 stu 表的数据。

### 操作三：通过 SSMS 界面撤销权限（REVOKE）

1. 打开 testuser 的用户属性 → 安全对象页
2. 选中 stu 表
3. 取消 **INSERT** 的”授予”勾选（变为空白，即撤销 GRANT）
4. 取消 **DELETE** 的”拒绝”勾选（即撤销 DENY）
5. 确定保存

### 操作四：通过 SSMS 界面查看用户的有效权限

1. 展开 stusta → 表 → 右键某张表（如 `stu`）→ **“属性”**
2. 切换到 **“权限(Permissions)”** 页
3. 可以看到对该表拥有权限的所有用户和角色列表
4. 选中某个用户，下方显示其具体权限状态（已授予/已拒绝/继承）

### 操作五：T-SQL 参考脚本（补充）

💡

以下 T-SQL 与上面的界面操作效果相同。

```sql
USE stusta;

-- ===== GRANT 授予权限 =====
GRANT SELECT, INSERT ON stu TO testuser;
GRANT SELECT ON course TO testuser;

-- 使用 WITH GRANT OPTION 允许被授权者将此权限再授予他人
GRANT SELECT ON course TO testuser WITH GRANT OPTION;

-- ===== DENY 明确拒绝 =====
DENY DELETE ON stu TO testuser;

-- ===== REVOKE 撤销 =====
REVOKE INSERT ON stu FROM testuser;       -- 撤销 GRANT
REVOKE DENY DELETE ON stu FROM testuser;  -- 撤销 DENY
```

### 操作六：综合权限验证演示

```sql
USE stusta;

-- 先授予一组权限
GRANT SELECT, INSERT, UPDATE ON stu TO testuser;
GRANT SELECT ON course TO testuser;
DENY DELETE ON stu TO testuser;

-- 验证1：查看用户对某对象的权限明细
SELECT
    dp.state_desc AS 权限状态,
    dp.permission_name AS 权限名称,
    OBJECT_NAME(dp.major_id) AS 对象名称,
    u.name AS 用户名
FROM sys.database_permissions dp
JOIN sys.database_principals u ON dp.grantee_principal_id = u.principal_id
WHERE u.name = 'testuser' AND dp.major_id > 0;

-- 验证2：模拟 testuser 查看有效权限
EXECUTE AS USER = 'testuser';
SELECT * FROM fn_my_permissions('stu', 'OBJECT');
REVERT;

-- 验证3：实际操作测试
EXECUTE AS USER = 'testuser';
SELECT * FROM stu;          -- ✅ 成功
INSERT INTO stu VALUES('X','X','男',20,'X');  -- ✅ 成功（已授予 INSERT）
DELETE FROM stu WHERE 1=0;  -- ❌ 失败（被 DENY）
REVERT;
```

## 📝 任务三知识点总结

✅

**核心知识点回顾**：

- 权限分三类：**隐含权限**（角色自带）、**对象权限**（SELECT/INSERT/UPDATE/DELETE/EXECUTE）、**语句权限**（CREATE TABLE 等 DDL）
- 三种权限控制语句：**GRANT**（授予）、**DENY**（明确拒绝）、**REVOKE**（撤销已有的 GRANT 或 DENY）
- 权限优先级：**DENY > GRANT > 角色继承 > 默认拒绝**（sysadmin 例外，不受 DENY 限制）
- 三种特殊用户：**sysadmin 成员**（无条件最高权限）、**dbo**（数据库所有者）、**一般用户**（需显式授权）
- 使用 `EXECUTE AS USER` 和 `fn_my_permissions()` 可模拟用户身份验证权限是否生效
- `WITH GRANT OPTION` 允许被授权者将权限再转授他人

## ⚡ 任务三重难点提示

🔥

**重点**：

- **GRANT、DENY、REVOKE 三者的区别和用法**，尤其是 DENY 与 REVOKE 的区别（DENY 是“明确禁止”，REVOKE 是“取消之前的授权/拒绝”）
- 权限优先级链：**DENY > GRANT > 角色继承 > 默认拒绝**
- 能够区分隐含权限、对象权限、语句权限三种类型

**难点**：

- **权限叠加与冲突场景**：当用户同时通过角色获得 GRANT 和直接被 DENY 时，最终结果是被拒绝（DENY 优先）——这是最常见的考题场景
- REVOKE 和 DENY 的效果不同：REVOKE 后用户可能仍通过角色拥有权限，而 DENY 会彻底封死
- sysadmin 成员不受 DENY 限制是**特殊例外**，考试中常作为干扰项出现

**易错点**：

- 混淆 REVOKE 和 DENY：想禁止用户某个权限应用 DENY，仅用 REVOKE 可能无效（因为角色仍可提供权限）
- `REVOKE DENY DELETE ON stu FROM testuser` 是撤销之前的 DENY，不是授予 DELETE 权限
- 在中文版 SSMS 中，权限名称显示为中文：SELECT→选择、INSERT→插入、UPDATE→更新、DELETE→删除、EXECUTE→执行

---

# 任务四 角色管理

## 🧠 理论知识

### 为什么需要角色？

💡

当你已经理解了**单个用户的权限如何授予、拒绝和撤销**之后，就会发现：如果很多用户需要同一组权限，逐个授权会非常繁琐。此时就需要引入**角色**，把一组权限打包，再批量分配给多个用户。

### 服务器角色（固定，系统预定义）

作用范围：整个 SQL Server 实例。这些角色是系统内置的，不能新增或删除。

| 服务器角色 | 权限说明 | 典型使用场景 |
| --- | --- | --- |
| **sysadmin** | 超级管理员，可执行任何操作（不受 DENY 限制） | DBA 总管理员 |
| **securityadmin** | 管理登录名和权限（可 GRANT/DENY/REVOKE 服务器权限） | 安全管理员 |
| **serveradmin** | 配置服务器设置（内存、连接数、关闭服务器等） | 运维管理员 |
| **setupadmin** | 管理链接服务器（Linked Server） | 集成管理 |
| **processadmin** | 终止 SQL Server 中正在运行的进程 | 处理阻塞/死锁 |
| **diskadmin** | 管理磁盘文件（备份设备等） | 存储管理 |
| **dbcreator** | 创建、修改、删除和还原数据库 | 开发人员（需建库权限时） |
| **bulkadmin** | 执行 BULK INSERT 批量导入操作 | 数据导入专员 |
| **public** | 最低权限，所有登录名自动成为成员，不可移除 | 默认基础角色 |

---

### 数据库角色（固定，作用于特定数据库）

| 数据库角色 | 权限说明 | 典型使用场景 |
| --- | --- | --- |
| **db_owner** | 数据库所有者，拥有该数据库的全部权限 | 数据库管理员 |
| **db_accessadmin** | 管理数据库用户的访问（添加/删除用户） | 用户管理 |
| **db_securityadmin** | 管理角色成员和数据库权限 | 权限管理 |
| **db_ddladmin** | 执行 DDL 语句（CREATE/ALTER/DROP 表、视图等） | 开发人员 |
| **db_backupoperator** | 备份数据库 | 备份操作员 |
| **db_datareader** | 读取所有用户表的数据（SELECT） | 只读查询用户 |
| **db_datawriter** | 写入所有用户表（INSERT/UPDATE/DELETE） | 数据录入员 |
| **db_denydatareader** | 拒绝读取所有用户表（优先级高于 db_datareader） | 特殊限制场景 |
| **db_denydatawriter** | 拒绝写入所有用户表（优先级高于 db_datawriter） | 特殊限制场景 |
| **public** | 所有数据库用户自动成为成员 | 默认基础角色 |

💡

**组合使用示例**：如果想让用户只能读取数据但不能修改，将其加入 `db_datareader` 角色即可。如果想让用户既能读又能写，则同时加入 `db_datareader` 和 `db_datawriter`。

---

### 用户自定义数据库角色

当固定角色粒度太粗时（例如只想让某些用户读取部分表而非全部表），可以创建自定义角色，实现更精细的权限控制。

---

## 🛠️ 实践操作

### 操作一：通过 SSMS 界面将登录名添加到服务器角色

📌

**操作目标**：将 `testuser` 登录名添加到 `dbcreator` 服务器角色，使其拥有创建数据库的权限。

1. 在对象资源管理器中，展开 **“安全性”** → **“登录名”**
2. 双击 `testuser`（或右键 → 属性），打开 **“登录属性”** 对话框
3. 切换到左侧 **“服务器角色(Server Roles)”** 页
4. 在角色列表中勾选 **dbcreator**（`public` 已默认勾选且不可取消）
5. 点击 **“确定”**
6. 验证：用 testuser 登录后尝试 `CREATE DATABASE test_db;`，应能成功

### 操作二：通过 SSMS 界面将数据库用户添加到数据库角色

📌

**操作目标**：将 stusta 数据库中的 `testuser` 用户添加到 `db_datareader` 角色，使其可以读取所有表。

**方法一：从用户属性进入**

1. 展开 stusta → 安全性 → 用户 → 双击 `testuser`
2. 切换到 **“成员身份(Membership)”** 页
3. 勾选 **db_datareader** → 确定

**方法二：从角色属性进入**

1. 展开 stusta → 安全性 → 角色 → 数据库角色
2. 双击 **db_datareader** 打开属性
3. 点击 **“添加”** 按钮 → 输入 `testuser` → 检查名称 → 确定 → 确定

### 操作三：通过 SSMS 界面创建自定义数据库角色

📌

**操作目标**：创建一个名为 `report_reader` 的只读报表角色，只允许查询 stu、course、score 三张表。

**第一步：创建角色**

1. 展开 stusta → 安全性 → 角色 → 右键 **“数据库角色”** → **“新建数据库角色(New Database Role…)”**
2. **角色名称**输入 `report_reader` → **所有者**保持默认 `dbo`
3. 在 **“成员(Members)”** 区域，点击 **“添加”** → 输入 `testuser` → 检查名称 → 确定
4. 暂时先点击 **“确定”** 创建角色

**第二步：为角色授予权限**

1. 在数据库角色列表中，双击 `report_reader` 打开属性
2. 切换到 **“安全对象(Securables)”** 页
3. 点击 **“搜索”** → 选择 **“特定对象”** → 对象类型选 **“表”**
4. 点击 **“浏览”** → 勾选 `stu`、`course`、`score` 三张表 → 确定
5. 在下方的权限列表中，逐个选择每张表，为其勾选 **SELECT** 的 **“授予(Grant)”** 列
6. 点击 **“确定”** 保存

**第三步：验证**

```sql
-- 模拟 testuser 登录验证
EXECUTE AS USER = 'testuser';
SELECT * FROM stu;      -- ✅ 应成功
SELECT * FROM course;   -- ✅ 应成功
SELECT * FROM score;    -- ✅ 应成功
DELETE FROM stu WHERE 1=0;  -- ❌ 应失败
REVERT;
```

### 操作四：从角色中移除成员和删除角色（SSMS 界面）

1. 双击 `report_reader` 角色 → 在成员列表中选中 `testuser` → 点击 **“删除”** → 确定
2. 右键 `report_reader` → **“删除”** → 确认（如果角色中还有成员，需先全部移除）

### 操作五：T-SQL 参考脚本（补充）

💡

以下 T-SQL 与上面的界面操作效果相同。

```sql
-- 将登录名添加到服务器角色
ALTER SERVER ROLE dbcreator ADD MEMBER testuser;

-- 将数据库用户添加到数据库角色
USE stusta;
ALTER ROLE db_datareader ADD MEMBER testuser;

-- 创建自定义角色并授权
CREATE ROLE report_reader;
GRANT SELECT ON stu TO report_reader;
GRANT SELECT ON course TO report_reader;
GRANT SELECT ON score TO report_reader;
ALTER ROLE report_reader ADD MEMBER testuser;

-- 查看角色成员
EXEC sp_helprolemember 'report_reader';

-- 移除成员并删除角色
ALTER ROLE report_reader DROP MEMBER testuser;
DROP ROLE report_reader;
```

### 操作六：查看服务器和数据库角色成员（SSMS 界面）

**查看服务器角色成员**：

1. 展开 安全性 → 服务器角色 → 双击某个角色（如 `sysadmin`）
2. 在属性对话框中可以看到该角色的所有成员列表

**查看数据库角色成员**：

1. 展开 stusta → 安全性 → 角色 → 数据库角色 → 双击某个角色
2. 在属性对话框的”成员”区域查看

### 操作七：应用程序角色（了解）

💡

应用程序角色是一种特殊角色，不包含成员，仅由应用程序通过密码激活后临时获得权限。适合限制用户只能通过指定应用程序访问数据库。

```sql
-- 创建应用程序角色
CREATE APPLICATION ROLE hr_app
    WITH PASSWORD = 'AppP@ss123!',
    DEFAULT_SCHEMA = dbo;

-- 为应用程序角色授权
GRANT SELECT, INSERT, UPDATE ON stu TO hr_app;

-- 在应用程序代码中激活（连接后执行）
EXEC sp_setapprole 'hr_app', 'AppP@ss123!';
```

## 📝 任务四知识点总结

✅

**核心知识点回顾**：

- 角色是**权限的打包集合**，用于简化批量权限管理，避免逐个用户授权
- **服务器角色**：系统预定义、不可增删，作用于整个 SQL Server 实例（sysadmin、dbcreator、securityadmin 等共 9 个）
- **数据库角色**：系统预定义，作用于特定数据库（db_owner、db_datareader、db_datawriter 等共 10 个）
- **自定义数据库角色**：当固定角色粒度太粗时使用，可实现表级别的精细权限控制
- **应用程序角色**：不含成员，由应用程序通过密码激活，限制只能通过特定应用访问数据库
- 权限组合技巧：db_datareader = 只读；db_datareader + db_datawriter = 读写

## ⚡ 任务四重难点提示

🔥

**重点**：

- **服务器角色与数据库角色的区别**：服务器角色管整个实例（如创建数据库、管理登录名），数据库角色管单个数据库（如读写表数据）
- 熟记常用角色：sysadmin、dbcreator、db_owner、db_datareader、db_datawriter
- 自定义角色的创建→授权→添加成员全流程

**难点**：

- **db_denydatareader / db_denydatawriter** 的优先级问题：如果用户同时属于 db_datareader 和 db_denydatareader，结果是**无法读取**（DENY 优先）——这是最常见的考题场景
- 服务器角色是**固定的**不能新建，而数据库角色可以自定义——不要混淆

**易错点**：

- 服务器角色分配给**登录名**，数据库角色分配给**数据库用户**——不要搞反对象
- 删除角色前必须先移除所有成员，否则删除操作会失败
- public 角色是默认角色，所有用户自动属于它，不能移除成员也不能删除

---

## 🏁 项目总结

📚

**SQL Server 安全管理四大核心**：

- **身份验证**：谁可以连接？→ 三种验证模式
- **用户管理**：谁可以访问哪个数据库？→ 登录名 + 数据库用户映射
- **权限管理**：具体能做什么操作？→ GRANT / DENY / REVOKE 精确控制
- **角色管理**：如何高效分配权限？→ 服务器角色 + 数据库角色 + 自定义角色

安全管理的核心原则是**最小权限原则**：只授予用户完成工作所需的最低权限，避免过度授权带来的安全风险。