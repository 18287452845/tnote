# 06 项目六 MySQL 数据库高级安全维护

🎯 **本项目学习目标**

- 能使用 Navicat 图形化完成数据库、数据表、字段、索引和外键的日常管理
- 能使用 Navicat 管理用户权限，并与命令行 `GRANT` / `REVOKE` 结果相互验证
- 能使用 Navicat 完成数据导入导出、备份还原、结构同步和数据维护
- 能通过 Navicat 监控连接、进程、服务器变量和日志相关状态
- 能基于项目五的安全基础，形成数据库日常维护与安全加固清单

<aside>
🧭

**主线地图**：图形化建库建表 → 图形化管用户权限 → 图形化备份维护 → 监控排错 → 安全加固与高可用认知。

</aside>

<aside>
🖥️

**前置条件**

- 已完成项目五：Ubuntu 虚拟机中的 MySQL 已安装并能运行
- 宿主机 Windows 已安装 Navicat，并能连接虚拟机 MySQL
- 已有 `root@localhost` 管理员账号，课堂密码统一为 `123456`
- 已理解项目五中的最小权限、日志、binlog 和账号来源主机概念

**课堂产出**

- 能用 Navicat 创建 `employees_lab` 数据库、数据表、索引和外键
- 能用 Navicat 创建只读、读写、开发三类账号，并验证权限边界
- 能完成一次表数据导入导出、一次 SQL 转储备份、一次还原验证
- 能查看服务器进程、变量、状态和日志路径，完成基础维护检查

</aside>

---

## 第 1 课 Navicat 连接与界面认知：从命令行走向图形化管理

### 1.1 本课要解决的问题

项目五已经解决了 MySQL “能装、能连、能授权、能看日志”。本项目进一步解决：**如何像数据库管理员一样，用图形化工具完成日常管理与维护**。

本课重点不是替代命令行，而是建立对应关系：

| 命令行操作 | Navicat 中的位置 | 用途 |
| --- | --- | --- |
| `SHOW DATABASES;` | 左侧连接树 | 查看数据库列表 |
| `CREATE DATABASE ...` | 右键连接 → 新建数据库 | 创建业务库 |
| `CREATE TABLE ...` | 右键表 → 新建表 | 设计表结构 |
| `GRANT ...` | 用户管理 / 权限页 | 授权 |
| `SHOW PROCESSLIST;` | 工具 → 服务器监控 / 进程列表 | 查看连接与执行中的 SQL |
| `mysqldump` | 转储 SQL 文件 / 运行 SQL 文件 | 备份与还原 |

<aside>
💬

**一句话理解**：Navicat 是“可视化操作台”，MySQL Server 仍然在虚拟机里运行。界面上点的每一步，底层最终都会变成 SQL 或 MySQL 协议操作。

</aside>

### 1.2 新建和测试连接

在宿主机 Windows 打开 Navicat：

1. 点击 **连接** → **MySQL**
2. 填写连接信息：

| 配置项 | 示例值 | 说明 |
| --- | --- | --- |
| 连接名 | `MySQL-Ubuntu-Root` | 自定义名称 |
| 主机 | `192.168.100.20` | Ubuntu 虚拟机 IP |
| 端口 | `3306` | MySQL 默认端口 |
| 用户名 | `root` 或项目五创建的管理账号 | 管理操作建议使用管理员账号 |
| 密码 | `123456` | 课堂统一密码 |

3. 点击 **测试连接**
4. 成功后点击 **确定** 保存

<aside>
⚠️

**如果 root 不能远程登录，这是正常的安全设计。** 项目五中建议禁止 root 远程登录。课堂中更推荐创建一个专门的管理员账号，例如：

```sql
CREATE USER 'dba'@'192.168.100.%' IDENTIFIED WITH mysql_native_password BY '123456';
GRANT ALL PRIVILEGES ON *.* TO 'dba'@'192.168.100.%' WITH GRANT OPTION;
```

生产环境不要给远程账号 `ALL PRIVILEGES`，这里仅用于课堂管理演示。

</aside>

### 1.3 认识 Navicat 主界面

连接成功后，重点认识以下区域：

| 区域 | 作用 |
| --- | --- |
| 左侧连接树 | 查看连接、数据库、表、视图、函数、事件等对象 |
| 对象工具栏 | 新建表、设计表、打开表、删除对象 |
| 查询窗口 | 编写并执行 SQL，适合验证界面操作结果 |
| 表设计器 | 图形化维护字段、主键、索引、外键 |
| 用户管理 | 创建账号、分配权限、锁定账号 |
| 工具菜单 | 导入导出、转储 SQL、运行 SQL、数据传输、结构同步 |

### 1.4 图形化操作后的命令行验证

每完成一个图形化操作，都建议在查询窗口中验证：

```sql
-- 查看当前连接身份
SELECT USER(), CURRENT_USER();

-- 查看数据库
SHOW DATABASES;

-- 查看当前服务器版本
SELECT VERSION();
```

<aside>
✅

**第 1 课小结**

- Navicat 是图形化客户端，不是数据库本身
- 管理操作建议使用专门的 `dba` 管理账号，不建议开放 root 远程登录
- 图形化操作后要用 SQL 验证结果，避免“点了但不知道是否生效”

</aside>

---

## 第 2 课 Navicat 图形化建库建表：管理数据库对象

### 2.1 本课要解决的问题

掌握数据库管理员最常见的对象维护任务：建库、建表、改字段、建索引、建外键、查看表数据。

本课用 Navicat 创建一个员工管理实验库：`employees_lab`。

### 2.2 创建数据库

在 Navicat 左侧连接上右键：

1. 选择 **新建数据库**
2. 填写：

| 配置项 | 值 |
| --- | --- |
| 数据库名 | `employees_lab` |
| 字符集 | `utf8mb4` |
| 排序规则 | `utf8mb4_unicode_ci` |

3. 点击 **确定**
4. 在左侧连接上右键 **刷新**

在查询窗口验证：

```sql
SHOW CREATE DATABASE employees_lab;
```

<aside>
💬

**为什么仍然选 utf8mb4？**

项目五已经说明 MySQL 的 `utf8` 不是真正完整 UTF-8。图形化建库时也要主动选择 `utf8mb4`，避免中文、特殊符号或 Emoji 存储异常。

</aside>

### 2.3 创建部门表 `departments`

展开 `employees_lab` → 右键 **表** → **新建表**。

添加字段：

| 字段名 | 类型 | 长度 | 允许空 | 键 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `dept_id` | `varchar` | 10 | 否 | 主键 | 部门编号 |
| `dept_name` | `varchar` | 50 | 否 | 唯一索引 | 部门名称 |
| `created_at` | `timestamp` |  | 否 |  | 创建时间 |

设置建议：

- 将 `dept_id` 设置为主键
- `created_at` 默认值设置为 `CURRENT_TIMESTAMP`
- 给 `dept_name` 创建唯一索引，防止部门重名
- 保存表名为 `departments`

对应 SQL 可在查询窗口验证：

```sql
SHOW CREATE TABLE employees_lab.departments\G
```

### 2.4 创建员工表 `employees`

继续新建表 `employees`：

| 字段名 | 类型 | 长度 | 允许空 | 键 | 说明 |
| --- | --- | --- | --- | --- | --- |
| `emp_id` | `int` |  | 否 | 主键 | 员工编号 |
| `emp_name` | `varchar` | 50 | 否 |  | 员工姓名 |
| `dept_id` | `varchar` | 10 | 否 | 普通索引 / 外键 | 所属部门 |
| `salary` | `decimal` | 10,2 | 是 |  | 薪资 |
| `hire_date` | `date` |  | 否 |  | 入职日期 |
| `updated_at` | `timestamp` |  | 否 |  | 更新时间 |

表设计器中注意：

- `emp_id` 设置为主键并勾选自动递增
- `salary` 使用 `DECIMAL(10,2)`，不要用 `FLOAT` 存钱
- `updated_at` 默认值设置为 `CURRENT_TIMESTAMP`，并设置更新时自动刷新
- `dept_id` 建普通索引，后面用于外键

对应 SQL 示例：

```sql
CREATE TABLE employees_lab.employees (
    emp_id INT PRIMARY KEY AUTO_INCREMENT,
    emp_name VARCHAR(50) NOT NULL,
    dept_id VARCHAR(10) NOT NULL,
    salary DECIMAL(10,2),
    hire_date DATE NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_dept_id (dept_id),
    CONSTRAINT fk_emp_dept FOREIGN KEY (dept_id)
        REFERENCES employees_lab.departments(dept_id)
);
```

### 2.5 图形化创建外键

在 `employees` 表设计器中：

1. 切换到 **外键** 页签
2. 新建外键，名称填写 `fk_emp_dept`
3. 字段选择 `dept_id`
4. 参考数据库选择 `employees_lab`
5. 参考表选择 `departments`
6. 参考字段选择 `dept_id`
7. 保存表结构

<aside>
⚠️

**外键创建失败常见原因**

- 两边字段类型或长度不一致，例如一个是 `varchar(10)`，另一个是 `varchar(20)`
- 被引用字段不是主键或唯一索引
- 表引擎不是 InnoDB
- 已有数据违反外键约束

</aside>

### 2.6 录入和编辑数据

打开 `departments` 表，添加示例数据：

| dept_id | dept_name |
| --- | --- |
| d001 | 技术部 |
| d002 | 财务部 |
| d003 | 运营部 |

打开 `employees` 表，添加示例数据：

| emp_name | dept_id | salary | hire_date |
| --- | --- | --- | --- |
| 张三 | d001 | 8500.00 | 2024-03-01 |
| 李四 | d002 | 7800.00 | 2024-04-15 |
| 王五 | d003 | 6900.00 | 2024-05-20 |

用查询窗口验证：

```sql
SELECT e.emp_id, e.emp_name, d.dept_name, e.salary, e.hire_date
FROM employees_lab.employees e
JOIN employees_lab.departments d ON e.dept_id = d.dept_id;
```

### 2.7 修改表结构的安全流程

图形化改表很方便，但也容易误操作。建议遵循：

1. 修改前右键表 → **转储 SQL 文件**，先备份
2. 在测试库验证修改
3. 使用 **设计表** 修改字段或索引
4. 保存前查看 Navicat 生成的 SQL
5. 保存后用 `SHOW CREATE TABLE` 验证

<aside>
✅

**第 2 课小结**

- Navicat 可以完成建库、建表、字段、索引、外键等对象管理
- 金额字段用 `DECIMAL`，中文库表统一 `utf8mb4`
- 图形化改表前先备份，保存前看 SQL，保存后再验证

</aside>

---

## 第 3 课 Navicat 用户与权限管理：图形化落实最小权限

### 3.1 本课要解决的问题

项目五已经讲过 `CREATE USER`、`GRANT`、`REVOKE`。本课重点是：**如何在 Navicat 中完成同样的权限管理，并验证权限边界**。

### 3.2 角色设计

以 `employees_lab` 为例，设计三类账号：

| 账号 | 来源主机 | 密码 | 权限范围 | 适用角色 |
| --- | --- | --- | --- | --- |
| `reader` | `192.168.100.%` | `123456` | `SELECT` | 数据分析、报表查询 |
| `writer` | `192.168.100.%` | `123456` | `SELECT, INSERT, UPDATE, DELETE` | 应用系统 |
| `developer` | `192.168.100.%` | `123456` | `SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX` | 开发测试 |

<aside>
⚠️

**不要为了省事给业务账号 ALL PRIVILEGES。** 图形化工具会让授权变得很容易，但越容易越要谨慎。

</aside>

### 3.3 在 Navicat 中创建用户

进入用户管理界面：

1. 右键连接 → **管理用户**，或菜单中打开用户管理
2. 点击 **新建用户**
3. 填写：
   - 用户名：`reader`
   - 主机：`192.168.100.%`
   - 密码：`123456`
4. 认证插件优先选择兼容 Navicat 的 `mysql_native_password`
5. 保存

按同样方式创建 `writer` 和 `developer`。

如果界面创建失败，回到查询窗口先降低课堂密码策略：

```sql
SET GLOBAL validate_password.policy = LOW;
SET GLOBAL validate_password.length = 6;
```

### 3.4 在 Navicat 中分配权限

在用户管理中选择 `reader@192.168.100.%`：

1. 打开 **权限** 页签
2. 找到数据库 `employees_lab`
3. 只勾选 `SELECT`
4. 保存

`writer` 勾选：

- `SELECT`
- `INSERT`
- `UPDATE`
- `DELETE`

`developer` 勾选：

- `SELECT`
- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `INDEX`

保存后用 SQL 验证：

```sql
SHOW GRANTS FOR 'reader'@'192.168.100.%';
SHOW GRANTS FOR 'writer'@'192.168.100.%';
SHOW GRANTS FOR 'developer'@'192.168.100.%';
```

### 3.5 用不同连接验证权限边界

在 Navicat 中分别新建三个连接：

- `MySQL-reader`
- `MySQL-writer`
- `MySQL-developer`

每个连接使用对应账号登录，然后执行测试：

| 测试操作 | reader | writer | developer |
| --- | --- | --- | --- |
| `SELECT * FROM employees_lab.employees;` | 应成功 | 应成功 | 应成功 |
| `INSERT INTO employees_lab.departments VALUES ('d004','人事部',NOW());` | 应失败 | 应成功 | 应成功 |
| `UPDATE employees_lab.employees SET salary=salary+100 WHERE emp_id=1;` | 应失败 | 应成功 | 应成功 |
| `CREATE TABLE employees_lab.tmp_test (id INT);` | 应失败 | 应失败 | 应成功 |
| `DROP DATABASE employees_lab;` | 应失败 | 应失败 | 应失败 |

<aside>
💬

**为什么要用不同连接验证？**

权限是连接时按账号身份匹配的。只在管理员连接里看 `SHOW GRANTS` 不够，必须真的用目标账号登录，才能确认权限边界是否符合预期。

</aside>

### 3.6 图形化锁定、解锁和删除账号

在用户管理中可以完成账号生命周期维护：

| 场景 | Navicat 操作 | SQL 对应 |
| --- | --- | --- |
| 员工离职但不确定是否仍被系统使用 | 锁定账号 | `ALTER USER ... ACCOUNT LOCK;` |
| 账号恢复使用 | 解锁账号 | `ALTER USER ... ACCOUNT UNLOCK;` |
| 账号确认废弃 | 删除用户 | `DROP USER ...;` |
| 怀疑密码泄露 | 修改密码 | `ALTER USER ... IDENTIFIED BY ...;` |

删除前先在查询窗口检查依赖：

```sql
SELECT * FROM information_schema.VIEWS WHERE DEFINER LIKE '%reader%';
SELECT * FROM information_schema.ROUTINES WHERE DEFINER LIKE '%reader%';
```

<aside>
✅

**第 3 课小结**

- Navicat 能创建用户、分配权限、锁定账号和删除账号
- 权限设计仍然遵循最小权限原则
- 图形化授权后必须用 `SHOW GRANTS` 和不同账号连接双重验证

</aside>

---

## 第 4 课 Navicat 数据维护：导入、导出、备份、还原

### 4.1 本课要解决的问题

数据库日常维护不只是建表授权，还包括数据迁移、备份、还原和批量处理。本课用 Navicat 完成常见维护动作。

### 4.2 表数据导出

右键 `employees_lab.employees` 表 → **导出向导**。

常见导出格式：

| 格式 | 适用场景 |
| --- | --- |
| Excel / CSV | 给业务人员、数据分析师查看 |
| SQL | 迁移到另一台 MySQL 或备份表数据 |
| JSON | 与接口、脚本、文档系统交换数据 |

导出 CSV 时建议：

- 字符编码选择 `UTF-8`
- 勾选字段名作为首行
- 日期时间格式保持默认或统一为 `YYYY-MM-DD`

### 4.3 表数据导入

右键目标表 → **导入向导**。

导入前检查：

1. CSV / Excel 字段名是否和表字段对应
2. 字符编码是否为 UTF-8
3. 日期格式是否能被 MySQL 识别
4. 外键字段是否存在对应主表记录
5. 主键是否重复

<aside>
🔧

**导入失败排错顺序**

1. 看错误提示中的行号
2. 检查该行是否有空值、乱码、日期格式错误
3. 检查主键是否重复
4. 检查外键字段是否在主表存在
5. 必要时先导入临时表，再用 SQL 清洗后写入正式表

</aside>

### 4.4 转储 SQL 文件备份

右键数据库 `employees_lab` → **转储 SQL 文件** → **结构和数据**。

建议文件名：

```text
employees_lab_20260512.sql
```

备份时建议勾选：

- 包含表结构和数据
- 使用 UTF-8 编码
- 如果只想备份单个库并还原到同名库，可以勾选 `CREATE DATABASE`
- 如果后面要还原到 `employees_lab_restore` 这样的测试库，**不要勾选 `CREATE DATABASE`**，避免 SQL 文件重新切回原库名

<aside>
⚠️

**还原到测试库时要注意库名**

如果 SQL 文件中包含：

```sql
CREATE DATABASE employees_lab;
USE employees_lab;
```

即使你在 Navicat 中对 `employees_lab_restore` 执行“运行 SQL 文件”，数据也可能被还原到原来的 `employees_lab`。课堂建议：备份用于还原演练时，不勾选 `CREATE DATABASE`；如果已经勾选，需要先把 SQL 文件中的库名改成 `employees_lab_restore`。

</aside>

<aside>
⚠️

**备份文件不要只放在数据库服务器上。** 如果服务器磁盘损坏，备份也会一起丢失。至少要复制到宿主机或其他安全位置。

</aside>

### 4.5 运行 SQL 文件还原

还原前建议新建一个测试库：`employees_lab_restore`。

操作步骤：

1. 右键连接 → **新建数据库** → `employees_lab_restore`
2. 右键该数据库 → **运行 SQL 文件**
3. 选择刚才导出的 `.sql` 文件
4. 执行完成后刷新数据库
5. 查询验证：

```sql
SELECT COUNT(*) FROM employees_lab_restore.employees;
SELECT COUNT(*) FROM employees_lab_restore.departments;
```

### 4.6 数据传输与结构同步

Navicat 的 **数据传输** 和 **结构同步** 常用于测试库、正式库之间迁移对象。

| 功能 | 作用 | 风险点 |
| --- | --- | --- |
| 数据传输 | 把表结构和数据从一个库复制到另一个库 | 可能覆盖目标库对象 |
| 结构同步 | 比较两个库的表结构差异并生成同步 SQL | 可能执行 `DROP` / `ALTER` |
| 数据同步 | 比较两边数据并同步差异 | 可能误删或覆盖目标数据 |

课堂建议流程：

1. 先从源库传输到测试库
2. 查看 Navicat 生成的 SQL
3. 确认没有危险 `DROP` 操作
4. 再执行同步

### 4.7 日常维护操作清单

| 维护事项 | Navicat 操作 | 验证方式 |
| --- | --- | --- |
| 备份数据库 | 转储 SQL 文件 | 新建测试库并还原 |
| 批量导入数据 | 导入向导 | `COUNT(*)` 和抽样查询 |
| 给业务导出数据 | 导出向导 | 打开 CSV / Excel 检查乱码 |
| 修改表结构 | 设计表 | `SHOW CREATE TABLE` |
| 同步测试库结构 | 结构同步 | 先查看生成 SQL |

<aside>
✅

**第 4 课小结**

- 导入导出解决数据交换问题，SQL 转储解决备份还原问题
- 备份是否有效，必须通过还原验证
- 数据传输、结构同步很方便，但执行前必须检查生成 SQL

</aside>

---

## 第 5 课 Navicat 监控与排错：图形化看运行状态

### 5.1 本课要解决的问题

项目五已经学过错误日志、慢查询日志、通用查询日志和 binlog。本课不重复日志原理，重点学习：**如何用 Navicat 快速查看数据库当前状态，并辅助排错**。

### 5.2 查看连接和进程

在 Navicat 中打开服务器监控或进程列表，可以看到当前连接、用户、来源主机和正在执行的 SQL。

对应 SQL：

```sql
SHOW PROCESSLIST;
```

重点关注：

| 字段 | 含义 | 排查价值 |
| --- | --- | --- |
| `Id` | 连接 ID | 必要时用于结束连接 |
| `User` | 当前用户 | 判断是否异常账号 |
| `Host` | 来源主机 | 判断是否异常来源 IP |
| `db` | 当前数据库 | 判断影响范围 |
| `Command` | 当前命令 | Query / Sleep 等 |
| `Time` | 持续时间 | 长时间运行可能有问题 |
| `Info` | 正在执行的 SQL | 排查慢 SQL 或锁等待 |

如需结束异常连接：

```sql
KILL 连接ID;
```

<aside>
⚠️

**不要随便 KILL。** 结束连接可能导致事务回滚、业务报错。课堂环境可以演示，生产环境必须先确认 SQL、来源和影响范围。

</aside>

### 5.3 查看服务器变量和状态

Navicat 的服务器信息界面可以查看变量和状态。也可以在查询窗口执行：

```sql
-- 查看关键变量
SHOW VARIABLES LIKE 'version';
SHOW VARIABLES LIKE 'character_set_server';
SHOW VARIABLES LIKE 'time_zone';
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'general_log';

-- 查看关键状态
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Slow_queries';
SHOW GLOBAL STATUS LIKE 'Connections';
SHOW GLOBAL STATUS LIKE 'Uptime';
```

常见判断：

| 现象 | 可能原因 | 下一步 |
| --- | --- | --- |
| `Threads_connected` 很高 | 连接池配置不当 / 连接泄漏 | 看进程列表来源 |
| `Slow_queries` 增长快 | SQL 慢或缺索引 | 开慢查询日志并分析 |
| `log_bin` 为 OFF | binlog 未开启 | 回到项目五配置 binlog |
| 字符集不是 `utf8mb4` | 建库或配置不规范 | 检查库表字符集 |

### 5.4 查看表信息和索引

在 Navicat 中右键表 → **设计表** → 查看字段、索引、外键。

常用 SQL 验证：

```sql
-- 查看表结构
DESC employees_lab.employees;

-- 查看索引
SHOW INDEX FROM employees_lab.employees;

-- 查看表大小和行数估计
SELECT table_name, table_rows,
       ROUND(data_length / 1024 / 1024, 2) AS data_mb,
       ROUND(index_length / 1024 / 1024, 2) AS index_mb
FROM information_schema.tables
WHERE table_schema = 'employees_lab';
```

### 5.5 用 EXPLAIN 辅助查询优化

在 Navicat 查询窗口执行：

```sql
EXPLAIN
SELECT e.emp_name, d.dept_name
FROM employees_lab.employees e
JOIN employees_lab.departments d ON e.dept_id = d.dept_id
WHERE d.dept_id = 'd001';
```

重点看：

| 字段 | 说明 |
| --- | --- |
| `type` | 访问类型，越接近 `const` / `ref` 越好 |
| `key` | 实际使用的索引 |
| `rows` | 预计扫描行数，越少越好 |
| `Extra` | 是否出现 `Using filesort`、`Using temporary` 等提示 |

<aside>
💬

**初学者记住一句话**：慢 SQL 先看有没有合适索引，再看 `EXPLAIN` 有没有用上索引。

</aside>

### 5.6 图形化维护不要替代安全审计

Navicat 能让管理更方便，但安全审计仍应保留 SQL 证据：

```sql
-- 查看用户和来源
SELECT user, host, plugin, account_locked FROM mysql.user;

-- 查看某个账号权限
SHOW GRANTS FOR 'writer'@'192.168.100.%';

-- 查看 binlog 状态
SHOW BINARY LOG STATUS;

-- 查看慢查询数量
SHOW GLOBAL STATUS LIKE 'Slow_queries';
```

<aside>
✅

**第 5 课小结**

- Navicat 可以查看进程、变量、状态、表结构和索引
- 排错先看当前连接和正在执行的 SQL
- 图形化查看很方便，但关键维护结论要用 SQL 留痕验证

</aside>

---

## 第 6 课 安全加固、主从复制与高可用认知：从会操作到会维护

### 6.1 本课要解决的问题

前面已经学会了 Navicat 图形化管理数据库。本课把操作上升为维护规范：**哪些操作可以做，哪些操作要谨慎，生产环境如何防风险**。

### 6.2 Navicat 使用安全规范

| 风险操作 | 风险 | 建议 |
| --- | --- | --- |
| 远程使用 root | 一旦泄露就是最高权限 | 禁止 root 远程，使用专门 DBA 账号 |
| 保存生产密码 | 本机被入侵会泄露凭证 | 生产连接谨慎保存密码 |
| 图形化删除表 / 库 | 点击错误可能导致数据丢失 | 删除前先备份、再二次确认 |
| 结构同步直接执行 | 可能生成 `DROP` / `ALTER` | 先查看 SQL，再测试库演练 |
| 长期开启通用查询日志 | 影响性能、撑满磁盘 | 只在排错时临时开启 |

### 6.3 MySQL 安全加固清单

| 加固措施 | 检查方式 | 防御什么 |
| --- | --- | --- |
| 禁止 root 远程登录 | `SELECT user, host FROM mysql.user WHERE user='root';` | 远程暴力破解 |
| 限制账号来源 IP | 查看用户 host 是否为内网网段 | 未授权来源连接 |
| 强密码策略 | `SHOW VARIABLES LIKE 'validate_password%';` | 弱密码 |
| 最小权限原则 | `SHOW GRANTS` | 权限滥用 |
| 删除匿名用户 | `SELECT user, host FROM mysql.user WHERE user='';` | 匿名访问 |
| 删除 test 数据库 | `SHOW DATABASES LIKE 'test';` | 测试库滥用 |
| 不授予 FILE 权限 | `SHOW GRANTS` | UDF 提权 / 文件读写风险 |
| 开启 binlog | `SHOW VARIABLES LIKE 'log_bin';` | 恢复和审计 |
| 定期备份并验证还原 | Navicat 转储 + 测试库还原 | 误删和故障恢复 |

### 6.4 常见攻击与防御回顾

| 攻击方式 | 表现 | 防御措施 |
| --- | --- | --- |
| SQL 注入 | 应用拼接 SQL，攻击者绕过认证或拖库 | 参数化查询 + 最小权限 |
| 弱密码爆破 | 反复尝试 root / 123456 等密码 | 强密码 + 限制来源 + 防火墙 |
| 未授权访问 | 3306 暴露到公网 | 内网访问 + 安全组 / 防火墙 |
| 权限过大 | 普通账号可删库、读系统表 | 按角色授权，不给 ALL |
| UDF 提权 | 借助 FILE 权限写入恶意库文件 | 禁止业务账号 FILE 权限 |

### 6.5 主从复制入门：让数据库具备热备能力

单机 MySQL 即使配置再规范，也存在单点故障。主从复制要解决的问题是：**主库负责写入，从库持续同步主库数据，用于备份、读查询或故障切换准备**。

#### 主从复制的基本角色

| 角色 | 作用 | 初学者理解 |
| --- | --- | --- |
| 主库（Primary / Source） | 接收业务写入，产生 binlog | “原始账本” |
| 从库（Replica） | 拉取并回放主库 binlog | “抄账本的人” |
| 复制账号 | 专门给从库连接主库使用 | “只允许抄账的账号” |
| binlog | 主库记录数据变更的日志 | “账本流水” |
| relay log | 从库本地保存的中继日志 | “抄回来的草稿本” |

<aside>
💬

**一句话理解主从复制**

主库把所有写操作记录到 binlog；从库连接主库，把 binlog 拉到本地，再按顺序执行一遍，因此从库的数据会逐步追上主库。

</aside>

#### 主从复制的基本流程

```text
应用写入主库
   ↓
主库写入 binlog
   ↓
从库 I/O 线程连接主库并拉取 binlog
   ↓
从库写入 relay log
   ↓
从库 SQL 线程回放 relay log
   ↓
从库数据与主库保持同步
```

#### 搭建前必须满足的条件

| 条件                | 检查方式                                      | 说明            |
| ----------------- | ----------------------------------------- | ------------- |
| 主库开启 binlog       | `SHOW VARIABLES LIKE 'log_bin';`          | 必须为 `ON`      |
| 主从 `server_id` 不同 | `SHOW VARIABLES LIKE 'server_id';`        | 每台 MySQL 必须唯一 |
| 主库允许从库访问 3306     | 防火墙 / 安全组 / 网络连通性检查                       | 从库要能连到主库      |
| 存在复制账号            | `SHOW GRANTS FOR 'repl'@'192.168.100.%';` | 只授予复制权限       |
| 初始数据一致            | 全量备份还原到从库                                 | 否则复制起点不一致     |

复制账号示例：

```sql
CREATE USER 'repl'@'192.168.100.%' IDENTIFIED WITH mysql_native_password BY '123456';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'192.168.100.%';
```

<aside>
⚠️

**复制账号不要给 ALL PRIVILEGES。** 它只需要读取主库 binlog 的能力，授予 `REPLICATION SLAVE` 即可。

</aside>

#### 课堂环境规划

本次实验使用两台 Ubuntu 虚拟机模拟主从环境：

| 角色 | 主机名 | IP 地址 | server_id | 说明 |
| --- | --- | --- | --- | --- |
| 主库（Source） | mysql-primary | `192.168.100.20` | 1 | 项目五已有的 MySQL 实例 |
| 从库（Replica） | mysql-replica | `192.168.100.21` | 2 | 克隆或新建一台虚拟机 |

<aside>
💬

**没有第二台虚拟机怎么办？**

可以克隆项目五的虚拟机，修改 IP 和 `server_id` 即可。克隆后记得修改主机名和网络配置，避免 IP 冲突。

</aside>

#### 第一步：配置主库（192.168.100.20）

在主库 Ubuntu 上编辑 MySQL 配置文件：

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

在 `[mysqld]` 段中确认或添加以下配置：

```ini
[mysqld]
server-id = 1
log_bin = /var/log/mysql/mysql-bin
binlog_format = ROW
bind-address = 0.0.0.0
```

配置说明：

| 参数 | 值 | 作用 |
| --- | --- | --- |
| `server-id` | `1` | 主库唯一标识，集群内不能重复 |
| `log_bin` | `/var/log/mysql/mysql-bin` | 开启 binlog 并指定路径前缀 |
| `binlog_format` | `ROW` | 推荐行级复制，数据一致性最好 |
| `bind-address` | `0.0.0.0` | 允许远程连接（从库需要连入） |

保存后重启 MySQL：

```bash
sudo systemctl restart mysql
```

验证配置生效：

```sql
SHOW VARIABLES LIKE 'server_id';
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
```

#### 第二步：配置从库（192.168.100.21）

在从库 Ubuntu 上编辑同样的配置文件：

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

在 `[mysqld]` 段中确认或添加：

```ini
[mysqld]
server-id = 2
relay_log = /var/log/mysql/mysql-relay
read_only = ON
bind-address = 0.0.0.0
```

配置说明：

| 参数 | 值 | 作用 |
| --- | --- | --- |
| `server-id` | `2` | 从库唯一标识，必须和主库不同 |
| `relay_log` | `/var/log/mysql/mysql-relay` | 中继日志路径前缀 |
| `read_only` | `ON` | 从库设为只读，防止误写入 |
| `bind-address` | `0.0.0.0` | 允许 Navicat 远程连接查看状态 |

保存后重启 MySQL：

```bash
sudo systemctl restart mysql
```

验证配置生效：

```sql
SHOW VARIABLES LIKE 'server_id';
SHOW VARIABLES LIKE 'relay_log';
SHOW VARIABLES LIKE 'read_only';
```

<aside>
⚠️

**克隆虚拟机必做：删除 `auto.cnf` 重新生成 UUID**

如果从库是通过克隆主库虚拟机得到的，两台机器的 MySQL `server_uuid` 会完全相同。复制启动时会报错：

```text
Fatal error: The replica I/O thread stops because source and replica have
equal MySQL server UUIDs; these UUIDs must be different for replication to work.
```

`server_uuid` 存储在数据目录下的 `auto.cnf` 文件中，克隆虚拟机时被原样复制过来。解决方法是在**从库**删除该文件并重启，MySQL 会自动生成新的 UUID：

```bash
# 停止 MySQL
sudo systemctl stop mysql

# 删除 auto.cnf（MySQL 重启时会自动生成新 UUID）
sudo rm /var/lib/mysql/auto.cnf

# 重启 MySQL
sudo systemctl start mysql
```

重启后验证两边 UUID 已不同（分别在主库和从库执行）：

```sql
SHOW VARIABLES LIKE 'server_uuid';
```

确认两台机器的 UUID 不同后，再继续后续步骤。

</aside>

#### 第三步：在主库创建复制账号

在主库执行（如果项目五已降低密码策略则可直接创建）：

```sql
-- 创建复制专用账号
CREATE USER 'repl'@'192.168.100.%' IDENTIFIED WITH mysql_native_password BY '123456';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'192.168.100.%';
FLUSH PRIVILEGES;

-- 验证账号权限
SHOW GRANTS FOR 'repl'@'192.168.100.%';
```

在从库测试能否用该账号连接主库：

```bash
mysql -h 192.168.100.20 -u repl -p123456 -e "SELECT 1;"
```

如果连接失败，检查：
1. 主库防火墙是否放行 3306 端口：`sudo ufw allow 3306`
2. 主库 `bind-address` 是否为 `0.0.0.0`
3. 账号的 host 是否匹配从库 IP

#### 第四步：备份主库数据并还原到从库

主从复制要求从库的初始数据和主库一致。使用 `mysqldump` 做全量备份：

在主库执行：

```sql
-- 锁定主库并记录 binlog 位置
FLUSH TABLES WITH READ LOCK;
```sql
SHOW BINARY LOGS;

-- 查看当前正在写入的 binlog 文件及位置
SHOW MASTER STATUS;
```
```

记录输出中的两个关键值（后面配置从库要用）：

```text
+------------------+----------+
| File             | Position |
+------------------+----------+
| mysql-bin.000014 |      849 |
+------------------+----------+
```

<aside>
⚠️

**务必记录 File 和 Position！** 这两个值告诉从库"从哪里开始抄"。记错或漏记会导致复制数据不一致。

</aside>

打开另一个终端窗口，执行全量备份：

```bash
sudo mysqldump -u root -p123456 --all-databases --source-data=2 > /tmp/full_backup.sql
```

备份完成后，回到第一个终端解锁主库：

```sql
UNLOCK TABLES;
```

将备份文件传输到从库：

```bash
scp /tmp/full_backup.sql admin@192.168.100.21:/tmp/
```

在从库还原备份：

```bash
mysql -u root -p123456 < /tmp/full_backup.sql
```

<aside>
💬

**为什么要先备份再配置复制？**

从库必须有和主库一样的初始数据，复制只同步"从某个 binlog 位置之后"的增量变更。如果初始数据不一致，后续复制的数据也会错乱。

</aside>

#### 第五步：在从库配置并启动复制

在从库 MySQL 中执行以下命令，将第四步记录的 File 和 Position 填入：

```sql
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.1.136',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = '123456',
    SOURCE_LOG_FILE = 'mysql-bin.000014',
    SOURCE_LOG_POS = 849,
    SOURCE_PORT = 3306;
```

参数说明：

| 参数 | 含义 |
| --- | --- |
| `SOURCE_HOST` | 主库 IP 地址 |
| `SOURCE_USER` | 复制账号用户名 |
| `SOURCE_PASSWORD` | 复制账号密码 |
| `SOURCE_LOG_FILE` | 第四步记录的 binlog 文件名 |
| `SOURCE_LOG_POS` | 第四步记录的 binlog 位置 |
| `SOURCE_PORT` | 主库端口 |

启动复制：

```sql
START REPLICA;
```

<aside>
⚠️

**旧版本命令对照**

MySQL 8.0.22 之前使用旧语法，课堂可能在旧资料中看到：

| 新语法（推荐） | 旧语法 |
| --- | --- |
| `CHANGE REPLICATION SOURCE TO` | `CHANGE MASTER TO` |
| `SOURCE_HOST` | `MASTER_HOST` |
| `SOURCE_LOG_FILE` | `MASTER_LOG_FILE` |
| `SOURCE_LOG_POS` | `MASTER_LOG_POS` |
| `START REPLICA` | `START SLAVE` |
| `SHOW REPLICA STATUS` | `SHOW SLAVE STATUS` |

两种写法功能完全相同，课堂统一使用新语法。

</aside>

#### 第六步：验证复制状态

启动复制后，在从库立即检查状态：

```sql
SHOW REPLICA STATUS;
```

重点看这些字段：

| 字段                      | 正常值 / 关注点 | 含义            |
| ----------------------- | --------- | ------------- |
| `Replica_IO_Running`    | `Yes`     | 从库能否连接主库并拉取日志 |
| `Replica_SQL_Running`   | `Yes`     | 从库能否正常回放日志    |
| `Seconds_Behind_Source` | 越小越好      | 从库落后主库多少秒     |
| `Last_IO_Error`         | 应为空       | 拉取日志错误原因      |
| `Last_SQL_Error`        | 应为空       | 回放日志错误原因      |

**两个 Running 都是 Yes 才算复制正常。** 如果有一个是 No，看对应的 Error 字段排查原因。

MySQL 8.0 中推荐使用 `REPLICA` 术语；旧资料里常见 `SLAVE`，含义基本对应。课堂看到旧命令时要能认出来，例如 `SHOW SLAVE STATUS\G` 是旧写法。

<aside>
🔧

**常见复制启动失败排错**

| 现象 | 可能原因 | 解决方法 |
| --- | --- | --- |
| `Replica_IO_Running: No` | 从库连不上主库 | 检查网络、防火墙、复制账号密码 |
| `Replica_IO_Running: Connecting` | 正在尝试连接 | 等几秒再查；若持续则检查主库 IP 和端口 |
| `Replica_SQL_Running: No` | 回放 SQL 出错 | 查看 `Last_SQL_Error`，通常是数据冲突 |
| `Last_IO_Error` 提示认证失败 | 账号或密码错误 | 停止复制，重新 `CHANGE REPLICATION SOURCE TO` |
| `Last_IO_Error` 提示找不到 binlog | File 或 Position 填错 | 回主库重新 `SHOW BINARY LOG STATUS` 确认 |

修复后重新启动复制的流程：

```sql
-- 停止复制
STOP REPLICA;

-- 重新配置（修正错误参数）
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = '123456',
    SOURCE_LOG_FILE = 'mysql-bin.000003',
    SOURCE_LOG_POS = 857,
    SOURCE_PORT = 3306;

-- 重新启动
START REPLICA;

-- 再次检查
SHOW REPLICA STATUS\G
```

</aside>

#### 第七步：实际数据同步测试

复制状态正常后，做一次写入测试验证数据确实能同步。

在**主库**执行写入：

```sql
-- 在主库插入测试数据
INSERT INTO employees_lab.departments VALUES ('d005', '测试部-主从验证', NOW());

-- 确认主库已写入
SELECT * FROM employees_lab.departments WHERE dept_id = 'd005';
```

在**从库**查询验证（等待 1-2 秒）：

```sql
-- 在从库查询，应该能看到刚才主库写入的数据
SELECT * FROM employees_lab.departments WHERE dept_id = 'd005';
```

如果从库能查到 `d005` 这条记录，说明主从复制工作正常。

再验证从库的只读保护：

```sql
-- 在从库尝试写入，应该被拒绝（因为配置了 read_only）
INSERT INTO employees_lab.departments VALUES ('d006', '从库写入测试', NOW());
-- 预期报错：The MySQL server is running with the --read-only option
```

<aside>
💬

**为什么从库要设置 read_only？**

如果从库也能写入，就会出现主从数据不一致。从库的职责是"只抄不写"，`read_only = ON` 从配置层面防止误操作。注意 `read_only` 对 `SUPER` 权限用户无效，生产环境可用 `super_read_only = ON` 进一步限制。

</aside>

#### Navicat 中如何辅助查看主从状态

Navicat 主要用于图形化观察和验证：

1. 在 Navicat 中分别建立主库连接（`MySQL-Primary`）和从库连接（`MySQL-Replica`）
2. 在主库连接中打开 `employees_lab.departments` 表，插入一行新数据
3. 切换到从库连接，刷新同一张表，确认数据是否同步出现
4. 在从库查询窗口执行 `SHOW REPLICA STATUS
5. 查看 `Replica_IO_Running`、`Replica_SQL_Running` 和延迟字段

#### 主从复制搭建流程总结

```text
┌─────────────────────────────────────────────────────────┐
│  主从复制搭建六步法                                       │
├─────────────────────────────────────────────────────────┤
│  1. 配置主库：server-id + log_bin + binlog_format        │
│  2. 配置从库：server-id + relay_log + read_only          │
│  3. 主库创建复制账号：REPLICATION SLAVE 权限              │
│  4. 主库全量备份 → 传输 → 从库还原（保证初始数据一致）    │
│  5. 从库 CHANGE REPLICATION SOURCE TO（填 File + Pos）   │
│  6. START REPLICA → SHOW REPLICA STATUS 验证双 Yes       │
└─────────────────────────────────────────────────────────┘
```

<aside>
✅

**课堂掌握到这里即可**

本项目不要求完整搭建生产级主从集群，但要理解：项目五的 binlog 是复制基础；项目六的备份还原用于准备从库初始数据；Navicat 可以辅助验证数据是否同步、复制线程是否正常。能按六步法说出搭建流程、能看懂 `SHOW REPLICA STATUS` 输出，即为达标。

</aside>

### 6.6 高可用方案认知

主从复制只是高可用的基础，不等于完整高可用。完整高可用还要解决：**主库故障后，谁来判断故障、谁来切换新主库、应用如何连接到新主库**。

| 方案 | 原理 | 初学者理解 |
| --- | --- | --- |
| 主从复制 | 主库写 binlog，从库回放同步数据 | 热备和读写分离基础 |
| MHA | 监控主库，故障时提升从库为主库 | 传统主从自动切换 |
| InnoDB Cluster | 基于 Group Replication 自动选主 | MySQL 官方高可用方案 |
| MySQL Router / ProxySQL | 应用连接中间件，由中间件分发请求 | 配合主从或集群使用 |

<aside>
💬

**当前阶段掌握重点**

先把“单机安全 + 备份还原 + binlog + 主从复制基本原理”学扎实。后续再学习自动故障切换和集群方案时，才能理解为什么高可用不是只多装一台 MySQL。

</aside>

### 6.7完成以下综合任务：

1. 用 Navicat 新建 `employees_lab` 数据库
2. 创建 `departments` 和 `employees` 两张表，包含主键、索引和外键
3. 插入不少于 5 条员工数据
4. 创建 `reader`、`writer`、`developer` 三个账号
5. 分别用三个账号登录，验证权限边界
6. 导出 `employees_lab` 为 SQL 文件
7. 新建 `employees_lab_restore` 并还原 SQL 文件
8. 查看当前连接进程、慢查询数量和 binlog 状态
9. 写出 5 条本机 MySQL 安全加固建议
10. 说明主从复制中 binlog、复制账号、复制线程和从库延迟的作用

<aside>
✅

**第 6 课小结**

- 图形化工具提升效率，但不能降低安全要求
- 数据库维护核心是：权限可控、数据可备、问题可查、故障可恢复
- 主从复制依赖 binlog、复制账号和复制线程，是热备和读写分离的基础
- 高可用不是单独技术点，而是建立在备份、日志、复制、监控和权限管理之上

</aside>

---

## 项目总结（一张表复盘）

| 课时 | 核心能力 | 验收点（可检查） |
| --- | --- | --- |
| 第 1 课：连接与界面 | 会使用 Navicat 管理入口 | 能连接 MySQL，能识别主要功能区 |
| 第 2 课：建库建表 | 会管理数据库对象 | 能创建库、表、索引、外键并插入数据 |
| 第 3 课：用户权限 | 会图形化落实最小权限 | 能创建多角色账号并验证权限边界 |
| 第 4 课：数据维护 | 会导入导出和备份还原 | 能转储 SQL 并还原到测试库 |
| 第 5 课：监控排错 | 会查看运行状态 | 能查看连接、变量、状态、索引和慢查询数量 |
| 第 6 课：安全维护 | 会形成维护规范和主从复制认知 | 能列出安全加固清单，并说明主从复制与高可用的关系 |

---

## 附录

### 附录 A：Navicat 常用操作与 SQL 对照表

| Navicat 操作 | SQL / 工具命令 |
| --- | --- |
| 新建数据库 | `CREATE DATABASE ...` |
| 删除数据库 | `DROP DATABASE ...` |
| 新建表 | `CREATE TABLE ...` |
| 设计表 | `ALTER TABLE ...` |
| 查看表数据 | `SELECT * FROM ...` |
| 新建用户 | `CREATE USER ...` |
| 授权 | `GRANT ... ON ... TO ...` |
| 撤权 | `REVOKE ... ON ... FROM ...` |
| 锁定账号 | `ALTER USER ... ACCOUNT LOCK` |
| 转储 SQL 文件 | `mysqldump` 类似功能 |
| 运行 SQL 文件 | `mysql < backup.sql` 类似功能 |
| 查看进程 | `SHOW PROCESSLIST` |
| 查看变量 | `SHOW VARIABLES` |
| 查看状态 | `SHOW STATUS` |

### 附录 B：课堂统一账号建议

| 用途 | 用户名 | 主机 | 密码 | 权限 |
| --- | --- | --- | --- | --- |
| 管理演示 | `dba` | `192.168.100.%` | `123456` | 课堂可给管理权限 |
| 只读验证 | `reader` | `192.168.100.%` | `123456` | `SELECT` |
| 读写验证 | `writer` | `192.168.100.%` | `123456` | `SELECT, INSERT, UPDATE, DELETE` |
| 开发验证 | `developer` | `192.168.100.%` | `123456` | DML + `CREATE, ALTER, INDEX` |

### 附录 C：备份文件命名规范

建议格式：

```text
数据库名_用途_日期.sql
```

示例：

```text
employees_lab_full_20260512.sql
employees_lab_before_alter_20260512.sql
employees_lab_restore_test_20260512.sql
```

命名要能看出：哪个库、什么用途、哪一天生成。
