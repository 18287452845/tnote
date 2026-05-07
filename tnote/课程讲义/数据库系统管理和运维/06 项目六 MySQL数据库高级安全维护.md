# 06 项目六 MySQL 数据库高级安全维护

🎯 **本项目学习目标**

- 能使用 Navicat 完成 MySQL 的连接管理、导入导出、备份还原与权限管理
- 能结合命令行和图形化工具完成权限审计、账号管理与资源限制配置
- 能使用 mysqldump 完成逻辑备份与还原，并理解脚本化备份的基本思路
- 能理解 MySQL 主从复制、GTID 复制与常见高可用方案的基本原理
- 能识别常见攻击面，并给出对应的安全加固措施

<aside>
🧭

**主线地图**：图形化管理 → 权限精细化 → 备份还原 → 复制扩展 → 攻防加固。

</aside>

<aside>
🖥️

**前置条件**

- VM-A 已安装 MySQL 8.0（项目五已完成）
- VM-A 已安装 Navicat for MySQL（或 Navicat Premium）
- 已完成项目五中的数据库 `stusta` 与账号 `app@192.168.100.%`

**课堂产出**

- 能用 Navicat 成功连接 VM-A，并完成数据导入导出
- 能创建多个角色账号并验证权限边界
- 能使用 `mysqldump` 完成备份与还原
- 能解释主从复制流程和常见攻击防御思路

</aside>

---

# 第 1 课 Navicat 图形化管理：用得顺手

## 1.1 本课要解决的问题

- 能通过 Navicat 连接 MySQL 服务器
- 能用 Navicat 完成数据导入导出
- 能用 Navicat 完成备份还原
- 能用 Navicat 管理用户权限

## 1.2 为什么还要学 Navicat

命令行适合精确操作和脚本自动化，Navicat 适合日常浏览、批量操作和快速备份。两者不是替代关系，而是互补关系。

<aside>
💬

**使用建议**

- 命令行：适合生产排错、脚本自动化、远程批处理
- Navicat：适合查看数据、快速导入导出、可视化权限管理
- 面试或工作中，DBA 往往两种方式都要会

</aside>

## 1.3 Navicat 核心功能

| 功能模块 | 说明 | 使用频率 |
| --- | --- | --- |
| 连接管理 | 管理多个 MySQL 连接，支持 SSH 隧道 | 每次使用 |
| 数据编辑 | 表格化查看与编辑数据 | 高 |
| 查询编辑器 | SQL 编写与执行 | 高 |
| 导入/导出 | 支持 CSV、Excel、SQL、JSON 等格式 | 中 |
| 备份/还原 | 支持数据库备份与恢复 | 高 |
| 用户权限管理 | 图形化管理账号和权限 | 中 |
| ER 图 | 可视化表结构和关系 | 低 |

## 1.4 建立连接

### 连接 MySQL 服务器

1. 打开 Navicat → 点击左上角 **连接** → 选择 **MySQL**
2. 填写连接信息：

| 字段 | 值（示例） | 说明 |
| --- | --- | --- |
| 连接名 | VM-A-MySQL | 自定义名称 |
| 主机 | 192.168.100.20 | MySQL 服务器 IP |
| 端口 | 3306 | 默认端口 |
| 用户名 | app | 项目五创建的账号 |
| 密码 | App@Pass123! | 对应密码 |

3. 点击 **测试连接** → 显示“连接成功” → 点击 **确定**

<aside>
🔧

**连接失败排查清单**

| 现象 | 可能原因 | 解决方法 |
| --- | --- | --- |
| Can't connect to MySQL server | MySQL 未启动或 bind-address 未开放 | `sudo systemctl status mysql` 检查 |
| Access denied for user | 用户名、密码或主机不匹配 | `SELECT user, host FROM mysql.user;` |
| Authentication plugin error | 客户端版本不支持 `caching_sha2_password` | 升级 Navicat 或调整认证插件 |
| Host is not allowed | 账号 host 不允许该 IP | 修改 host 或创建新账号 |

</aside>

### 使用 SSH 隧道连接（推荐）

生产环境中，不建议直接暴露 MySQL 端口。Navicat 支持通过 SSH 隧道连接：

1. 新建连接 → 切换到 **SSH** 选项卡
2. 勾选 **使用 SSH 通道**
3. 填写 SSH 信息：

| 字段 | 值（示例） |
| --- | --- |
| 主机 | 192.168.100.20 |
| 端口 | 22 |
| 用户名 | ubuntu |
| 认证方式 | 密码 / 密钥文件 |

4. 返回 **常规** 选项卡，主机改为 `127.0.0.1`

<aside>
💬

**SSH 隧道的优势**：MySQL 端口不需要直接对外开放，所有流量通过 SSH 加密传输。

</aside>

## 1.5 导入测试数据

在实际操作前，先导入一个示例数据库。MySQL 官方提供了 `employees` 示例数据库：

```bash
# 在 VM-A 上下载并导入
git clone https://github.com/datacharmer/test_db.git
cd test_db

# 导入
mysql -u root -p < employees.sql

# 验证导入
mysql -u root -p -e "USE employees; SELECT COUNT(*) AS '员工总数' FROM employees;"
```

导入完成后，在 Navicat 中右键连接名 → **刷新**，即可看到 `employees` 数据库及其表结构。

### 数据导入（CSV / Excel → MySQL）

1. 在 Navicat 中展开目标数据库
2. 右键目标表 → **导入向导**
3. 选择文件格式（CSV / Excel / JSON 等）
4. 选择源文件 → 预览数据
5. 字段映射：确认文件列与表字段对应关系
6. 选择导入模式：
   - **添加**：追加新记录
   - **更新**：根据主键更新已有记录
   - **添加或更新**：不存在则插入，存在则更新
7. 点击 **开始** → 查看导入结果

### 数据导出（MySQL → CSV / Excel / SQL）

1. 在 Navicat 中右键表名或数据库名
2. 选择 **导出向导**
3. 选择导出格式：
   - **SQL 文件**：适合迁移和恢复
   - **CSV / Excel**：适合分析和报表
   - **JSON / XML**：适合程序读取
4. 配置选项（字段分隔符、是否含表头等）
5. 选择保存路径 → **开始**

<aside>
💬

**导出 SQL vs 导出 CSV**

- 导出 SQL：保留表结构和数据类型，适合迁移和恢复
- 导出 CSV：便于分析和交换数据，但不保留结构信息

</aside>

## 1.6 备份与还原

### 方式一：数据库转储（生成 SQL 文件）

这是最通用的备份方式，生成的 `.sql` 文件可以在任何 MySQL 实例上恢复。

**备份**：

1. 右键数据库名 → **转储 SQL 文件** → **结构和数据**
2. 选择保存路径，生成 `.sql` 文件

**还原**：

1. 右键连接名 → **运行 SQL 文件**
2. 选择之前导出的 `.sql` 文件
3. 等待执行完成

### 方式二：Navicat 备份模块

Navicat 内置的备份模块支持计划任务，更适合日常运维。

**创建备份**：

1. 点击顶部 **备份** 图标
2. 点击 **新建备份** → 选择要备份的数据库
3. 点击 **开始** → 生成 `.nb3` 格式备份文件

**还原备份**：

1. 点击 **备份** 图标 → 选择备份文件
2. 右键 → **还原备份**
3. 确认目标数据库 → **开始**

### 设置自动计划任务

1. Navicat 顶部工具栏 → **自动运行**
2. 点击 **新建批处理作业** → 添加备份任务
3. 点击 **设置任务计划** → 配置执行频率
   - 每天凌晨 2:00
   - 每周日凌晨 3:00
4. 保存并启用

<aside>
⚠️

**备份文件安全提醒**

- 备份文件本身也是敏感资产
- 不要把备份和数据库放在同一台服务器上
- 定期验证备份是否能成功还原

</aside>

## 1.7 数据库维护工具

| 操作 | 等价 SQL | 作用 | 何时使用 |
| --- | --- | --- | --- |
| 分析表 | `ANALYZE TABLE` | 更新索引统计信息 | 查询变慢时 |
| 检查表 | `CHECK TABLE` | 检查表是否损坏 | 异常断电后 |
| 优化表 | `OPTIMIZE TABLE` | 整理碎片、回收空间 | 大量 DELETE 后 |
| 修复表 | `REPAIR TABLE` | 修复损坏的 MyISAM 表 | 仅限旧引擎 |

<aside>
💬

**InnoDB 与 MyISAM 的差异**

MySQL 8.0 默认使用 InnoDB，支持事务和崩溃恢复，一般不需要手工修复；MyISAM 是旧引擎，已不适合作为新项目默认选择。

</aside>

<aside>
✅

**第 1 课小结**

- 能用 Navicat 连接 MySQL，并理解 SSH 隧道的意义
- 能完成数据导入导出和数据库转储
- 能使用备份模块和计划任务做日常备份
- 能根据场景选择 ANALYZE / CHECK / OPTIMIZE / REPAIR

</aside>

---

# 第 2 课 权限精细化管理：管得住人

## 2.1 本课要解决的问题

- 能在 Navicat 中管理用户权限
- 能用命令行完成完整的权限管理流程
- 能理解权限排查的基本思路
- 能说出常见高危权限与常见攻击面的防御措施

## 2.2 权限验证流程

客户端发起连接后，MySQL 先做身份验证，再做权限验证：

```text
连接请求
  ↓
认证：用户名 + 主机 + 密码
  ↓
授权：全局 → 数据库 → 表 → 列
  ↓
允许或拒绝操作
```

<aside>
💬

**排查权限问题的顺序**

1. 看当前连接身份：`SELECT USER(), CURRENT_USER();`
2. 看账号拥有哪些权限：`SHOW GRANTS;`
3. 看账号是否被锁定：`SELECT user, host, account_locked FROM mysql.user;`
4. 看密码是否过期：`SELECT user, host, password_expired FROM mysql.user;`

</aside>

### 权限存储表

| 表名 | 存储内容 | 查看方式 |
| --- | --- | --- |
| `mysql.user` | 全局权限 + 账号信息 | `SELECT * FROM mysql.user WHERE user='app'\G` |
| `mysql.db` | 数据库级权限 | `SELECT * FROM mysql.db WHERE user='app'\G` |
| `mysql.tables_priv` | 表级权限 | `SELECT * FROM mysql.tables_priv WHERE user='app'\G` |
| `mysql.columns_priv` | 列级权限 | `SELECT * FROM mysql.columns_priv WHERE user='app'\G` |

## 2.3 在 Navicat 中管理用户权限

### 创建新用户

1. 在 Navicat 中点击顶部 **用户** 图标
2. 点击 **新建用户**
3. 填写账号信息：

| 字段 | 示例值 | 说明 |
| --- | --- | --- |
| 用户名 | `report` | 账号名 |
| 主机 | `192.168.100.%` | 允许连接的来源 |
| 密码 | `Report@Pass123!` | 密码 |
| 密码过期 | 90 天 | 建议定期更换 |

4. 切换到 **权限** 选项卡 → 勾选允许的权限
5. 点击 **保存**

### 修改已有用户权限

1. 在用户列表中双击目标用户
2. 切换到 **权限** 选项卡
3. 添加或移除数据库权限
4. 保存

## 2.4 命令行完整权限管理演练

### 创建多角色账号

```sql
-- 只读账号
CREATE USER 'reader'@'192.168.100.%' IDENTIFIED BY 'Read@Pass123!';
GRANT SELECT ON employees.* TO 'reader'@'192.168.100.%';

-- 读写账号
CREATE USER 'writer'@'192.168.100.%' IDENTIFIED BY 'Write@Pass123!';
GRANT SELECT, INSERT, UPDATE, DELETE ON employees.* TO 'writer'@'192.168.100.%';

-- 开发者账号
CREATE USER 'developer'@'192.168.100.%' IDENTIFIED BY 'Dev@Pass123!';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, CREATE TEMPORARY TABLES
  ON employees.*
  TO 'developer'@'192.168.100.%';

SHOW GRANTS FOR 'reader'@'192.168.100.%';
SHOW GRANTS FOR 'writer'@'192.168.100.%';
SHOW GRANTS FOR 'developer'@'192.168.100.%';
```

### 权限修改：授权 + 撤权

```sql
-- 给 writer 添加 CREATE 权限
GRANT CREATE ON employees.* TO 'writer'@'192.168.100.%';

-- 撤销 developer 的 ALTER 权限
REVOKE ALTER ON employees.* FROM 'developer'@'192.168.100.%';

-- 撤销所有权限但不删除账号
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'reader'@'192.168.100.%';
```

### 账号生命周期管理

```sql
-- 查看所有账号
SELECT user, host, account_locked, password_expired, password_lifetime
FROM mysql.user
WHERE plugin != 'auth_socket'
ORDER BY user;

-- 锁定账号
ALTER USER 'developer'@'192.168.100.%' ACCOUNT LOCK;

-- 解锁账号
ALTER USER 'developer'@'192.168.100.%' ACCOUNT UNLOCK;

-- 设置密码过期
ALTER USER 'writer'@'192.168.100.%' PASSWORD EXPIRE;

-- 删除账号
DROP USER 'reader'@'192.168.100.%';
```

### 资源限制

```sql
CREATE USER 'limited_app'@'192.168.100.%' IDENTIFIED BY 'Limited@Pass123!';
GRANT SELECT, INSERT, UPDATE, DELETE ON employees.* TO 'limited_app'@'192.168.100.%'
WITH MAX_QUERIES_PER_HOUR 1000
     MAX_UPDATES_PER_HOUR 100
     MAX_CONNECTIONS_PER_HOUR 50
     MAX_USER_CONNECTIONS 5;
```

<aside>
💬

**资源限制适合什么场景**

- 面向外部系统的 API 账号
- 第三方合作伙伴的只读账号
- 测试环境中的公共账号

</aside>

## 2.5 MySQL 安全加固清单

| 加固措施 | 命令 / 操作 | 防御什么 |
| --- | --- | --- |
| 禁止 root 远程登录 | `mysql_secure_installation` | 远程暴力破解 |
| 限制账号来源 IP | `'user'@'192.168.100.%'` | 未知网络连接 |
| 启用密码验证组件 | `INSTALL COMPONENT 'file://component_validate_password'` | 弱密码 |
| 定期轮换密码 | `ALTER USER ... IDENTIFIED BY ...` | 密码泄露后的窗口期 |
| 锁定不用的账号 | `ALTER USER ... ACCOUNT LOCK` | 废弃账号被利用 |
| 最小权限原则 | 只授予业务所需权限 | 权限滥用 / 提权 |
| 删除匿名用户 | `DROP USER ''@'localhost'` | 匿名访问 |
| 删除 test 数据库 | `DROP DATABASE test` | 测试库被利用 |
| 限制 FILE 权限 | 不授予业务账号 FILE 权限 | 读写服务器文件系统 |
| 开启 binlog | 项目五已配置 | 数据恢复 / 审计追溯 |

<aside>
✅

**第 2 课小结**

- 权限管理主线是查、改、锁、删
- 多角色账号应遵循最小权限原则
- 资源限制可用于防止账号滥用
- 安全加固需要定期审计，不是一劳永逸

</aside>

---

# 第 3 课 命令行备份与还原：丢不了数据

## 3.1 本课要解决的问题

- 掌握 `mysqldump` 的常用备份语法
- 掌握备份还原的完整流程
- 理解逻辑备份的适用场景和局限性
- 能写出简单的定时备份脚本

## 3.2 为什么还要学命令行备份

Navicat 备份适合图形化操作，但服务器生产环境更常见的是脚本化、自动化备份。因此，命令行备份是必学技能。

<aside>
💬

**备份方式对比**

| 方式 | 适合场景 | 是否需要 GUI |
| --- | --- | --- |
| Navicat 备份模块 | 本地快速备份、开发环境 | 需要 |
| mysqldump | 服务器自动化备份、生产环境 | 不需要 |
| 物理备份（XtraBackup） | 大数据量、热备份 | 不需要 |

</aside>

## 3.3 mysqldump 备份详解

```bash
# 单库备份
mysqldump -u root -p stusta > stusta_backup.sql

# 带时间戳的备份
mysqldump -u root -p stusta > stusta_$(date +%Y%m%d_%H%M%S).sql

# 多库备份
mysqldump -u root -p --databases stusta employees > multi_db_backup.sql

# 全库备份
mysqldump -u root -p --all-databases > all_db_backup.sql
```

### 常用参数

| 参数 | 作用 | 推荐使用 |
| --- | --- | --- |
| `--single-transaction` | InnoDB 一致性备份，不锁表 | 必加 |
| `--routines` | 包含存储过程和函数 | 建议加 |
| `--triggers` | 包含触发器 | 默认已包含 |
| `--events` | 包含定时事件 | 有事件时加 |
| `--flush-logs` | 备份前切换 binlog | PITR 使用 |
| `--master-data=2` | 记录 binlog 位置 | 主从复制使用 |

<aside>
💬

**为什么 InnoDB 备份建议加 `--single-transaction`**

它会开启快照事务，在不锁表的情况下获得一致性数据，适合业务在线运行时备份。

</aside>

### 推荐的备份命令

```bash
mysqldump -u root -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --flush-logs \
  stusta > stusta_daily_$(date +%Y%m%d).sql
```

## 3.4 备份还原

### 还原整个数据库

```bash
mysql -u root -p stusta < stusta_backup.sql

mysql -u root -p
> SOURCE /path/to/stusta_backup.sql;
```

### 还原到新数据库

```bash
mysql -u root -p -e "CREATE DATABASE stusta_restored;"
mysql -u root -p stusta_restored < stusta_backup.sql
```

<aside>
💬

**还原前注意事项**

1. 如果 `.sql` 文件包含 `CREATE DATABASE` 和 `USE`，会直接作用于同名数据库
2. 如果只导出单库结构，则需要先手动创建目标数据库
3. 大文件还原时，可能需要调整 `max_allowed_packet`

</aside>

## 3.5 逻辑备份 vs 物理备份

| 维度 | 逻辑备份（mysqldump） | 物理备份（XtraBackup） |
| --- | --- | --- |
| 输出格式 | SQL 文本文件 | 数据文件的二进制副本 |
| 备份速度 | 慢 | 快 |
| 还原速度 | 慢 | 快 |
| 可读性 | 可读 | 不可读 |
| 跨版本 | 支持 | 不支持 |
| 适用规模 | 中小型 | 大型 |
| 热备份 | 支持 | 支持 |

<aside>
💬

**初学者用 mysqldump 就够了**

课程阶段重点掌握逻辑备份的流程，等数据量增长到更大规模后，再考虑物理备份方案。

</aside>

## 3.6 自动化备份脚本

```bash
#!/bin/bash
# /opt/mysql_backup.sh — MySQL 每日备份脚本

BACKUP_DIR="/var/backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="stusta"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

# 方式一：交互输入密码（课堂演示更安全）
mysqldump -u root -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --flush-logs \
  "$DB_NAME" > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

# 方式二：生产脚本使用 --defaults-extra-file 指定凭证文件
# mysqldump --defaults-extra-file=/root/.my.cnf \
#   --single-transaction \
#   --routines \
#   --triggers \
#   --events \
#   --flush-logs \
#   "$DB_NAME" > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

if [ $? -eq 0 ]; then
    echo "[$(date)] Backup OK: ${DB_NAME}_${DATE}.sql" >> "$BACKUP_DIR/backup.log"
else
    echo "[$(date)] Backup FAILED!" >> "$BACKUP_DIR/backup.log"
fi

find "$BACKUP_DIR" -name "*.sql" -mtime +$KEEP_DAYS -delete
```

设置定时执行：

```bash
chmod +x /opt/mysql_backup.sh
sudo crontab -e
# 每天凌晨 2 点执行
0 2 * * * /opt/mysql_backup.sh
```

<aside>
⚠️

**脚本中的密码安全**

生产环境建议使用 `~/.my.cnf` 或 `--defaults-extra-file` 保存凭证，并确保文件权限为 600。

</aside>

<aside>
✅

**第 3 课小结**

- `mysqldump` 是 MySQL 最基础的备份工具
- InnoDB 备份推荐加 `--single-transaction`
- 还原前要确认目标库状态，避免误覆盖
- 生产环境用 cron + 脚本实现自动备份

</aside>

---

# 第 4 课 主从复制与攻防加固：扩得了容、防得住攻击

## 4.1 本课要解决的问题

- 理解 MySQL 主从复制的原理
- 能配置基于 binlog 的主从复制
- 了解常见的 MySQL 攻击方式和对应防御措施
- 了解 GTID 复制和 MySQL 高可用方案

## 4.2 主从复制原理

MySQL 复制是将主服务器的数据变更同步到一个或多个从服务器的技术。

**复制流程图**：

```text
主服务器                      从服务器
写操作 → binlog  → 网络传输 → IO Thread → Relay Log → SQL Thread → 数据更新
```

| 线程 | 所在 | 作用 |
| --- | --- | --- |
| Binlog Dump Thread | 主服务器 | 读取 binlog 并发送给从服务器 |
| IO Thread | 从服务器 | 接收 binlog 并写入 Relay Log |
| SQL Thread | 从服务器 | 读取 Relay Log 并执行 SQL |

<aside>
💬

**类比理解**

主库像“老师”，把写操作记在流水账里；从库像“学生”，先抄写流水账，再按账本内容执行。

</aside>

### 复制的应用场景

| 场景 | 说明 |
| --- | --- |
| 读写分离 | 写操作发给主库，读操作发给从库 |
| 数据备份 | 从库作为热备，主库故障时可快速切换 |
| 数据分析 | 在从库执行耗时查询，不影响主库 |
| 地理分布 | 在不同地区部署从库提供就近访问 |

## 4.3 主从复制配置思路

### 主库配置

```ini
[mysqld]
server-id = 1
log_bin = /var/lib/mysql/mysql-bin
binlog_format = ROW
```

创建复制账号：

```sql
CREATE USER IF NOT EXISTS 'repl'@'192.168.100.%' IDENTIFIED BY 'Repl@Pass123!';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'192.168.100.%';
SHOW BINARY LOG STATUS;
```

### 从库配置

```ini
[mysqld]
server-id = 2
relay_log = /var/lib/mysql/relay-bin
read_only = 1
```

配置连接主库：

```sql
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = 'Repl@Pass123!',
    SOURCE_LOG_FILE = 'mysql-bin.000003',
    SOURCE_LOG_POS = 154;

START REPLICA;
SHOW REPLICA STATUS\G
```

### 验证复制状态

确认 `Replica_IO_Running` 和 `Replica_SQL_Running` 都为 `Yes`，并且 `Seconds_Behind_Source` 接近 0。

<aside>
💬

**术语兼容说明**：MySQL 8.0.22 以后推荐使用 Source / Replica 术语；旧资料中的 `MASTER` / `SLAVE` 命令仍常见，课程中优先使用新语法，遇到旧环境时再查对应旧命令。

</aside>

## 4.4 GTID 复制

GTID 为每个事务分配全局唯一 ID，减少手动记录 File + Position 的麻烦。

```ini
# 主从均配置
[mysqld]
gtid_mode = ON
enforce_gtid_consistency = ON
```

```sql
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = 'Repl@Pass123!',
    SOURCE_AUTO_POSITION = 1;

START REPLICA;
```

<aside>
💬

**GTID 的价值**：更适合故障切换与自动化运维，MySQL 8.0 场景中推荐优先考虑。

</aside>

## 4.5 MySQL 常见攻击与防御

### SQL 注入

**防御措施**：参数化查询、输入验证、WAF、最小权限。

### 弱密码暴力破解

**防御措施**：强密码策略、限制来源 IP、账户锁定、禁用 root 远程登录。

### 未授权访问

**防御措施**：限制 `bind-address`、只开放内网访问、配合防火墙或安全组。

### UDF 提权

**防御措施**：不授予业务账号 `FILE` 权限，限制文件读写路径，定期审计。

## 4.6 MySQL 高可用方案

| 方案 | 原理 | 适用场景 |
| --- | --- | --- |
| InnoDB Cluster | 基于 Group Replication 的自动故障转移 | 官方推荐的高可用方案 |
| PXC | 同步多主复制 | 强一致性要求场景 |
| MHA | 自动主从切换 | 传统主从复制升级 |
| ProxySQL / MySQL Router | 读写分离中间件 | 配合主从复制使用 |

<aside>
💬

**初学者掌握重点**

当前阶段重点是理解主从复制和基本加固思路即可，高可用方案了解名称和用途就够了。

</aside>

<aside>
✅

**第 4 课小结**

- 能解释主从复制三个线程的作用
- 能说出 GTID 与传统 File + Position 的差别
- 能列出常见攻击与对应防御措施
- 能理解主从复制、高可用和安全加固之间的关系

</aside>

---

# 📝 项目总结（一张表复盘）

| 课时 | 核心能力 | 验收点（可检查） |
| --- | --- | --- |
| 第 1 课：Navicat 管理 | 用得顺手 | 能连接、导入、导出、备份 |
| 第 2 课：权限管理 | 管得住人 | 能创建多角色账号并验证权限边界 |
| 第 3 课：命令行备份 | 丢不了数据 | 能用 mysqldump 完成备份还原并写定时脚本 |
| 第 4 课：复制与加固 | 扩得了容、防得住攻击 | 能解释主从复制流程并说出常见攻击防御 |

---

# 附录

## 附录 A：Navicat 常用快捷键

| 操作 | 快捷键 |
| --- | --- |
| 新建查询 | `Ctrl + Q` |
| 执行查询 | `Ctrl + R` |
| 注释/取消注释 | `Ctrl + /` |
| 切换数据库 | `Ctrl + D` |
| 刷新对象列表 | `F5` |

## 附录 B：mysqldump 常用参数速查

| 参数 | 作用 |
| --- | --- |
| `--single-transaction` | InnoDB 一致性不锁表备份 |
| `--databases db1 db2` | 指定备份的数据库 |
| `--all-databases` | 备份所有数据库 |
| `--routines` | 包含存储过程和函数 |
| `--triggers` | 包含触发器 |
| `--events` | 包含定时事件 |
| `--flush-logs` | 备份前切换 binlog |
| `--master-data=2` | 记录 binlog 位置 |
| `--where="条件"` | 只备份符合条件的数据 |
| `--no-data` | 只备份表结构，不备份数据 |
