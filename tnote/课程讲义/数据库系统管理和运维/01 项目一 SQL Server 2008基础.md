# 01.项目一 SQL Server 2008基础

🎯

**本项目学习目标**

- 了解数据库、关系模型的基本概念，能说出”表、主键、外键”是什么
- 知道 SQL Server 2008 有哪些常用版本，能根据场景选择合适版本
- 独立完成 SQL Server 2008 R2 的安装
- 熟悉 SSMS 界面，能新建查询并执行简单 SQL 语句
- 用图形化方式和 SQL 语句两种方法创建数据库和数据表

> 💡 **先想一想**：你平时用的 QQ、微信、淘宝——这些 App 里成千上万条聊天记录、订单数据，存在哪里？怎么管理的？今天我们就来揭开答案。
> 

# 任务一 SQL Server 2008 概述

## 🧠 理论知识

> 🗣️ **学习导入**：数据库就像一个超级智能的”电子档案柜”，不仅能存数据，还能快速查找、统计、保护数据。SQL Server 是微软做的这样一套系统，在企业里非常常见。
> 

### SQL Server 是关系型数据库管理系统

SQL Server 是微软开发的关系型数据库管理系统（RDBMS），基于**关系模型**存储和管理数据，使用 SQL（Structured Query Language）作为查询语言。

**关系模型核心概念**（用”学生成绩表”来理解）：

- **表（Table）** ：就像 Excel 里的一张工作表，有行（每条记录）和列（每个字段）
- **主键（Primary Key）** ：每行的”唯一身份证”，比如学号，绝对不能重复也不能为空
- **外键（Foreign Key）** ：跨表的”关联线”，比如成绩表里的学号要对应学生表里真实存在的学号
- **事务（Transaction）** ：一组”要么全做、要么全不做”的操作，比如银行转账

**ACID 原则**：

| 原则 | 英文 | 含义 |
| --- | --- | --- |
| 原子性 | Atomicity | 事务中的操作要么全部成功，要么全部回滚 |
| 一致性 | Consistency | 事务执行前后，数据库始终处于合法状态 |
| 隔离性 | Isolation | 并发事务互不干扰 |
| 持久性 | Durability | 提交后的数据永久保存 |

---

### Microsoft SQL Server 发展历程

> 📌 **考点提示**：重点记忆 **2008** 和 **2022** 两个版本的特性即可，历程表了解即可。
> 

| 版本 | 年份 | 重要特性 |
| --- | --- | --- |
| SQL Server 6.5 | 1996 | 第一个成熟企业级版本 |
| SQL Server 2000 | 2000 | XML支持，全文搜索 |
| SQL Server 2005 | 2005 | .NET CLR集成，列级加密，Service Broker |
| **SQL Server 2008** | 2008 | **TDE透明加密**、数据压缩、Policy管理 |
| SQL Server 2012 | 2012 | Always On可用性组，列存储索引 |
| SQL Server 2016 | 2016 | Always Encrypted，Row-Level Security，动态数据屏蔽 |
| SQL Server 2019 | 2019 | 大数据集群，智能查询处理，Linux全面支持 |
| **SQL Server 2022** | 2022 | Azure Arc集成，账本表，S3对象存储 |

---

### SQL Server 2008 新特性（了解即可，重点是 TDE）

1. **简单的数据加密（TDE）** ：对整个数据库文件透明加密，应用程序无需修改代码
2. **增强审查（Enhanced Auditing）** ：细粒度审计，可跟踪SELECT等读取操作
3. **自动修复页面（Automatic Page Repair）** ：与数据库镜像配合，自动从镜像恢复损坏数据页
4. **精简的安装（Streamlined Installation）** ：改进的安装向导，基于策略的管理（Policy-Based Management）

---

### SQL Server 2008 版本对比

| 版本 | 适用场景 | 主要限制 |
| --- | --- | --- |
| **企业版（Enterprise）** | 大型企业，全功能 | 无限制 |
| **标准版（Standard）** | 中型企业 | 4核CPU，64GB内存 |
| **工作组版（Workgroup）** | 小型企业 | 2核CPU，4GB内存 |
| **开发者版（Developer）** | 开发/测试（不可商用） | 功能同Enterprise |
| **简化版（Express）** | 学习/小型应用，**免费** | 1核，1GB内存，10GB数据库大小 |

---

### 安装前的软硬件环境要求

> ⚠️ **安装前必做**：先安装 **.NET Framework 3.5 SP1**，否则安装程序会报错！
> 

**硬件**：

- CPU：1GHz以上（推荐2GHz+，多核）
- 内存：最低512MB（企业版推荐2GB+）
- 磁盘：NTFS格式，至少2GB系统空间 + 数据存储空间

**软件依赖**：

- **.NET Framework 3.5 SP1**（必需，安装前需提前安装）
- SQL Server Native Client
- Windows Installer 4.5 及以上

---

### NT AUTHORITY 账户区别

SQL Server 服务可以使用不同的内置 Windows 账户运行：

| 账户 | 说明 | SQL Server服务建议 |
| --- | --- | --- |
| `NT AUTHORITY\SYSTEM` | 操作系统内核账户，权限最高 | **不建议**（权限过大） |
| `NT AUTHORITY\NETWORK SERVICE` | 低权限网络服务账户，可访问网络 | 简单环境可用 |
| `NT AUTHORITY\LOCAL SERVICE` | 最低权限本地服务账户，无网络访问 | 不适合SQL Server |
| **专用服务账户** | 单独创建的低权限域/本地账户 | **推荐**（最小权限原则） |

---

## 🛠️ 实践操作

### SQL Server 2008 R2 安装步骤

1. 挂载ISO，以管理员运行 `setup.exe`
2. 左侧选择”安装” → “全新SQL Server独立安装或向现有安装添加功能”
3. 安装程序支持规则检查
4. 输入产品密钥（或选择免费评估版）
5. 接受许可条款
6. 安装程序支持文件
7. **功能选择**（建议勾选）：
    - ☑ 数据库引擎服务
    - ☑ SQL Server复制（Replication）
    - ☑ 管理工具 - 基本（Management Tools Basic）
    - ☑ 管理工具 - 完整（Management Tools Complete）
8. 实例配置：默认实例（MSSQLSERVER）
9. 磁盘空间要求确认
10. **服务器配置**：各服务配置账户（建议各服务独立账户）
11. **数据库引擎配置**：
    
    ---
    
- 身份验证模式选”混合模式”
- 设置 sa 账户密码（需符合复杂度）
- 添加当前Windows用户为管理员
1. 完成安装，可能需重启

# 任务二 SQL Server 2008 管理工具

## 🧠 理论知识

> 🗣️ **学习导入**：装好 SQL Server 之后，我们要用两个工具来管理它：**配置管理器**（负责”开关机”和网络设置）和 **SSMS**（写 SQL、看数据的主战场）。
> 

### SQL Server 配置管理器

配置管理器（SQL Server Configuration Manager）负责：

- 管理SQL Server各服务（启动/停止/暂停）
- 配置网络协议（TCP/IP、Named Pipes、Shared Memory）
- 配置服务账户和启动参数

**重要网络协议**：

| 协议 | 说明 | 默认状态 |
| --- | --- | --- |
| Shared Memory | 本机进程间通信，无需网络 | 启用 |
| Named Pipes | 局域网通信，基于Windows命名管道 | 禁用 |
| TCP/IP | 标准网络通信，端口1433 | 启用（生产环境） |

---

### SSMS（SQL Server Management Studio）

SSMS 是SQL Server的综合图形化管理界面：

**主要组成部分**：

- **对象资源管理器（Object Explorer）** ：树形浏览服务器/数据库/表等所有对象，快捷键 `F8`
- **查询编辑器（Query Editor）** ：编写和执行T-SQL，快捷键 `Alt+N` 新建
- **结果窗格**：显示查询结果（网格/文本/文件模式）
- **属性窗口**：查看选中对象属性，快捷键 `F4`

**SSMS 常用快捷键**：

| 快捷键 | 功能 |
| --- | --- |
| `F5` | 执行全部查询 |
| `Ctrl+E` | 执行选中代码 |
| `Ctrl+F5` | 分析查询语法（不执行） |
| `F8` | 显示/隐藏对象资源管理器 |
| `F4` | 显示属性窗口 |
| `Alt+N` | 新建查询窗口 |
| `Ctrl+K, Ctrl+C` | 注释选中代码 |
| `Ctrl+K, Ctrl+U` | 取消注释 |
| `Ctrl+L` | 显示预估执行计划 |
| `Ctrl+M` | 启用实际执行计划 |

---

### SQL Server 数据库对象

| 对象类型 | 说明 |
| --- | --- |
| **数据库（Database）** | 相关对象的集合，数据的逻辑容器 |
| **数据表（Table）** | 行列结构的数据存储单元 |
| **视图（View）** | 基于SELECT查询定义的虚拟表，简化复杂查询 |
| **存储过程（Stored Procedure）** | 预编译的SQL代码块，提升性能和安全性 |
| **函数（Function）** | 返回值的可重用代码（标量函数/表值函数） |
| **触发器（Trigger）** | 数据变化时自动执行（INSERT/UPDATE/DELETE触发） |
| **索引（Index）** | 加速查询的B树数据结构 |
| **数据库关系图（Diagram）** | 可视化ER关系图 |

---

### SQL 语言分类

| 分类 | 全称 | 主要语句 | 功能 |
| --- | --- | --- | --- |
| DDL | 数据定义语言 | CREATE、ALTER、DROP、TRUNCATE | 定义数据库结构 |
| DML | 数据操作语言 | INSERT、UPDATE、DELETE | 增删改数据 |
| DQL | 数据查询语言 | SELECT | 查询数据 |
| DCL | 数据控制语言 | GRANT、DENY、REVOKE | 权限管理 |
| TCL | 事务控制语言 | BEGIN TRAN、COMMIT、ROLLBACK | 事务管理 |

---

## 🛠️ 实践操作

### 打开配置管理器和管理服务

```bash
# 打开配置管理器（图形界面）
# 开始 → SQL Server 2008 → 配置工具 → SQL Server 配置管理器
# 或运行：SQLServerManager10.msc

# 命令行启动/停止服务
net start MSSQLSERVER       # 启动默认实例
net stop MSSQLSERVER        # 停止默认实例

# 若为命名实例（如MSSQLSERVER\MYINSTANCE）
net start "MSSQL$MYINSTANCE"
```

### SSMS 基本操作

```sql
-- 连接服务器后，新建查询（Alt+N）
-- 执行以下代码测试连接
SELECT @@VERSION AS SQLServerVersion;
SELECT @@SERVERNAME AS ServerName;
SELECT GETDATE() AS CurrentDateTime;
SELECT DB_NAME() AS CurrentDatabase;

-- 显示行号：工具 → 选项 → 文本编辑器 → Transact-SQL → 行号 勾选
-- 设置字体大小：工具 → 选项 → 字体和颜色
```

---

# 任务三 SQL Server 2008 数据库图形化操作

## 🧠 理论知识

> 🗣️ **学习导入**：本任务我们用”鼠标操作”来完成建库建表，先建立直观感受，任务四再用 SQL 语句实现同样的效果。两种方式都要掌握！
> 

### 系统数据库

> ⚠️ **注意**：永远不要手动修改或删除 `master` 数据库！
> 

SQL Server 安装后自动创建4个系统数据库：

| 数据库 | 说明 | 备份必要性 |
| --- | --- | --- |
| **master** | 记录所有数据库信息、登录账户、系统配置，是SQL Server的核心 | 必须定期备份 |
| **tempdb** | 临时表、排序操作的工作区，每次SQL Server重启都会重建 | 无需备份 |
| **model** | 新建数据库的模板，新库继承model的设置和对象 | 若有自定义则备份 |
| **msdb** | SQL Server代理服务使用，存储作业、警报、备份历史 | 建议备份 |

---

### 数据完整性

| 类型 | 说明 | 实现方式 |
| --- | --- | --- |
| **实体完整性** | 每行有唯一标识符 | PRIMARY KEY |
| **域完整性** | 列值在有效范围内 | CHECK约束、数据类型、NOT NULL |
| **引用完整性** | 外键值必须在被引用表中存在 | FOREIGN KEY |
| **用户定义完整性** | 特定业务规则 | 触发器、存储过程 |

---

### 约束类型详解

| 约束 | 作用 | 示例 |
| --- | --- | --- |
| NOT NULL | 禁止空值 | `sname NVARCHAR(20) NOT NULL` |
| PRIMARY KEY | 主键（唯一+非空） | `CONSTRAINT PK_stu PRIMARY KEY(sno)` |
| UNIQUE | 唯一性（允许一个NULL） | `CONSTRAINT UQ_email UNIQUE(email)` |
| CHECK | 值域检查 | `CHECK(age BETWEEN 15 AND 60)` |
| DEFAULT | 默认值 | `score DECIMAL(5,2) DEFAULT 0` |
| FOREIGN KEY | 外键引用 | `FOREIGN KEY(cno) REFERENCES course(cno)` |

---

### SQL Server 主要数据类型

| 类别 | 数据类型 | 说明 |
| --- | --- | --- |
| 整数 | `TINYINT`(0~255), `SMALLINT`, `INT`, `BIGINT` | 1/2/4/8字节 |
| 小数 | `DECIMAL(p,s)`, `NUMERIC(p,s)` | 精确小数；`FLOAT`/`REAL` 近似 |
| 字符串 | `CHAR(n)`, `VARCHAR(n)`, `TEXT` | 定长/可变长/大文本 |
| Unicode | `NCHAR(n)`, `NVARCHAR(n)`, `NTEXT` | **中文必须用N前缀类型** |
| 日期时间 | `DATE`, `TIME`, `DATETIME`, `DATETIME2` | 推荐用DATETIME2（精度更高） |
| 二进制 | `BINARY(n)`, `VARBINARY(n)` | 存储加密数据、图片等 |
| 其他 | `BIT`(0/1), `UNIQUEIDENTIFIER`(GUID), `XML` | 布尔/GUID/XML |

> 🆕 **新技术补充**：SQL Server 2022 中 `JSON` 类型已被原生支持。存储中文字符串推荐 `NVARCHAR(MAX)` 代替已废弃的 `NTEXT`，日期时间推荐 `DATETIME2` 代替 `DATETIME`（精度从毫秒提升到100纳秒）。
> 

---

## 🛠️ 实践操作

### 创建 stusta 数据库及三张数据表

```sql
-- 创建数据库
CREATE DATABASE stusta
ON PRIMARY (
    NAME = 'stusta_data',
    FILENAME = 'C:\SQLData\stusta.mdf',
    SIZE = 10MB, MAXSIZE = 500MB, FILEGROWTH = 10MB
)
LOG ON (
    NAME = 'stusta_log',
    FILENAME = 'C:\SQLData\stusta_log.ldf',
    SIZE = 5MB, FILEGROWTH = 5MB
);
GO

USE stusta;
GO

-- 创建学生表
CREATE TABLE stu (
    sno     CHAR(10)        NOT NULL,
    sname   NVARCHAR(20)    NOT NULL,
    gender  CHAR(2)         CHECK(gender IN ('男','女')),
    age     TINYINT         CHECK(age BETWEEN 15 AND 60),
    dept    NVARCHAR(30),
    CONSTRAINT PK_stu PRIMARY KEY(sno)
);

-- 创建课程表
CREATE TABLE course (
    cno     CHAR(6)         NOT NULL,
    cname   NVARCHAR(50)    NOT NULL,
    credit  TINYINT         CHECK(credit BETWEEN 1 AND 10),
    CONSTRAINT PK_course PRIMARY KEY(cno)
);

-- 创建成绩表（含外键）
CREATE TABLE score (
    sno     CHAR(10)        NOT NULL,
    cno     CHAR(6)         NOT NULL,
    grade   DECIMAL(5,2)    CHECK(grade BETWEEN 0 AND 100),
    CONSTRAINT PK_score PRIMARY KEY(sno, cno),
    CONSTRAINT FK_score_stu    FOREIGN KEY(sno) REFERENCES stu(sno),
    CONSTRAINT FK_score_course FOREIGN KEY(cno) REFERENCES course(cno)
);
```

> 💡 **补充说明**：创建数据库时**不是必须**指定文件位置和日志位置。如果省略 `ON PRIMARY` 和 `LOG ON` 子句,SQL Server 会使用默认设置:
> 
- **默认数据文件位置**:通常在 `C:\Program Files\Microsoft SQL Server\MSSQL10_50.MSSQLSERVER\MSSQL\DATA\`
- **默认文件名**:数据库名.mdf(数据文件)和数据库名_log.ldf(日志文件)
- **默认初始大小**:继承 `model` 数据库的设置
- **默认增长方式**:数据文件按 1MB 增长,日志文件按 10% 增长

```sql
-- 最简化的创建数据库语句(推荐新手使用)
CREATE DATABASE stusta;
GO

-- 等价于以下完整语句(使用默认设置)
CREATE DATABASE stusta
ON PRIMARY (
    NAME = 'stusta',
    FILENAME = 'C:\Program Files\Microsoft SQL Server\...\DATA\stusta.mdf',
    SIZE = 5MB,
    FILEGROWTH = 1MB
)
LOG ON (
    NAME = 'stusta_log',
    FILENAME = 'C:\Program Files\Microsoft SQL Server\...\DATA\stusta_log.ldf',
    SIZE = 1MB,
    FILEGROWTH = 10%
);
GO
```

> ⚠️ **生产环境建议**:虽然可以使用默认设置,但在企业项目中建议**明确指定**文件位置和大小,原因如下:
> 
- C盘空间有限,大型数据库应放在专用数据盘(如D盘或E盘)
- 便于备份管理和磁盘I/O优化
- 避免数据文件自动增长导致的性能问题
- 符合企业数据库管理规范

### 修改表结构

```sql
-- 添加列
ALTER TABLE stu ADD phone NVARCHAR(20);

-- 修改列数据类型（注意：修改类型可能导致数据丢失）
ALTER TABLE stu ALTER COLUMN phone VARCHAR(20);

-- 删除列
ALTER TABLE stu DROP COLUMN phone;

-- 设置表约束（添加CHECK约束）
ALTER TABLE stu ADD CONSTRAINT CK_gender CHECK(gender IN ('男','女'));
```

---

# 任务四 SQL Server 2008 SQL语句操作

## 🧠 理论知识

> 🗣️ **学习导入**：之前用鼠标点出来的操作，现在用”代码”来完成。SQL 是通用语言——不管是 MySQL、Oracle 还是 SQL Server，核心语法几乎一样！学会了终身受益。
> 

📚

**SQL 语言记忆口诀**：**增删改查**对应 `INSERT / DELETE / UPDATE / SELECT`；**建改删**结构对应 `CREATE / ALTER / DROP`

### DDL 语句语法

```sql
-- 创建数据库
CREATE DATABASE teasta;

-- 删除数据库
DROP DATABASE teasta;

-- 创建表
CREATE TABLE class (
    class_id  INT            NOT NULL IDENTITY(1,1),  -- 自增主键
    class_name NVARCHAR(50)  NOT NULL,
    teacher    NVARCHAR(20),
    CONSTRAINT PK_class PRIMARY KEY(class_id)
);

-- 修改表
ALTER TABLE class ADD description NVARCHAR(200);   -- 加列
ALTER TABLE class DROP COLUMN description;          -- 删列

-- 删除表
DROP TABLE class;
```

---

### DML 语句

```sql
-- 插入单行
INSERT INTO stu(sno, sname, gender, age, dept)
VALUES('2024001', '张三', '男', 20, '计算机系');

-- 批量插入
INSERT INTO stu VALUES
    ('2024002', '李四', '女', 19, '数学系'),
    ('2024003', '王五', '男', 21, '物理系');

-- 更新数据
UPDATE stu SET age = 21, dept = '软件工程系'
WHERE sno = '2024001';

-- 删除指定数据
DELETE FROM stu WHERE sno = '2024001';

-- 清空表（不记录日志，无法回滚，速度快）
TRUNCATE TABLE stu;
```

---

### SELECT 查询语句详解

```sql
-- 1. 查询全部列
SELECT * FROM stu;

-- 2. 查询指定列
SELECT sno, sname, age FROM stu;

-- 3. 列别名
SELECT sno AS '学号', sname AS '姓名', age AS '年龄' FROM stu;

-- 4. 计算表达式
SELECT sname, age, age + 1 AS '明年年龄' FROM stu;

-- 5. 去重
SELECT DISTINCT dept FROM stu;

-- 6. WHERE 条件
SELECT * FROM stu WHERE gender = '男' AND age > 20;
SELECT * FROM stu WHERE age BETWEEN 18 AND 22;
SELECT * FROM stu WHERE dept IN ('计算机系', '软件工程系');
SELECT * FROM stu WHERE sname LIKE '张%';   -- 以张开头
SELECT * FROM stu WHERE sname LIKE '_三';   -- 第二个字是三

-- 7. 聚合函数
SELECT COUNT(*) AS 总人数,
       AVG(CAST(age AS FLOAT)) AS 平均年龄,
       MAX(age) AS 最大年龄,
       MIN(age) AS 最小年龄
FROM stu;

-- 8. GROUP BY 分组
SELECT dept, COUNT(*) AS 人数, AVG(CAST(age AS FLOAT)) AS 平均年龄
FROM stu
GROUP BY dept
HAVING COUNT(*) >= 2;

-- 9. ORDER BY 排序
SELECT * FROM stu ORDER BY age DESC, sname ASC;

-- 10. 多表JOIN查询
SELECT s.sno, s.sname, c.cname, sc.grade
FROM stu s
INNER JOIN score sc ON s.sno = sc.sno
INNER JOIN course c ON sc.cno = c.cno
WHERE sc.grade >= 60
ORDER BY sc.grade DESC;

-- 11. 子查询（成绩高于平均分的学生）
SELECT sname, sno FROM stu
WHERE sno IN (
    SELECT sno FROM score
    WHERE grade > (SELECT AVG(grade) FROM score)
);
```