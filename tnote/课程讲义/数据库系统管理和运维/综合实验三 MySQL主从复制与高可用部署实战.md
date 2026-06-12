# 综合实验三 MySQL 主从复制与高可用部署实战

🎯 **本实验学习目标**

- 能从零搭建 MySQL 主从复制环境（两台 Ubuntu 虚拟机）
- 能配置主库 binlog 和从库 relay log，实现数据实时同步
- 能通过 SHOW REPLICA STATUS 诊断复制状态
- 能模拟并排除 4 种常见的复制故障
- 能理解 MHA、InnoDB Cluster 等高可用方案的原理与适用场景

<aside>
🧭

**实验主线**：环境准备 → 主库配置 → 从库配置与数据同步 → 复制启动验证 → 故障模拟与排查 → 高可用方案认知

本实验将项目五中的 binlog 知识和项目六中的复制配置融合，通过真实双机环境搭建主从复制，并模拟多种故障场景锻炼排错能力。

</aside>

<aside>
🖥️

**实验拓扑**

| 角色 | 系统 | IP 地址 | MySQL 版本 |
| --- | --- | --- | --- |
| 主库（Master） | Ubuntu 24.04 | `192.168.100.20` | MySQL 8.0 |
| 从库（Slave） | Ubuntu 24.04 | `192.168.100.21` | MySQL 8.0 |
| 管理端 | Windows 宿主机 | — | Navicat |

**前置条件**

- 已完成综合实验一（主库 MySQL 已安装加固、`ecommerce` 数据库和账号已创建）
- 虚拟机 Ubuntu 24.04 + MySQL 8.0
- 宿主机 Windows + Navicat，已能远程连接主库
- `ecommerce` 数据库中已有 `users`、`products`、`orders` 三张表及示例数据
- 所有密码统一使用 `123456`（课堂环境）

**课堂产出**

- 一套正常运行的 MySQL 主从复制环境
- 一份完整的复制状态验证记录
- 4 种故障的排查与修复报告
- 一份高可用方案对比分析

</aside>

---

## 实验背景

公司电商系统上线后，数据量和访问量持续增长。为了保证数据安全和读写分离，管理层要求搭建 MySQL 主从复制架构：主库负责写操作，从库负责读操作并作为热备。作为数据库运维工程师，你需要完成从环境搭建到故障排查的全流程。

---

## 任务一 复制环境准备（30 分钟）

### 1.1 克隆虚拟机

在 VMware 中将主库虚拟机克隆为从库：

1. 关闭主库虚拟机
2. 右键主库虚拟机 → **管理** → **克隆**
3. 选择"创建完整克隆"
4. 虚拟机名称：`Ubuntu-MySQL-Slave`
5. 启动克隆后的虚拟机

<aside>
⚠️

**克隆虚拟机后必须修改以下两项，否则两台机器会产生冲突：**

- IP 地址（不能和主库相同）
- MySQL 的 `server-id`（不能和主库相同）

此外，克隆还会复制 MySQL 的 UUID 文件，导致 MySQL 启动报错，需要一并处理。

</aside>

### 1.2 修改从库网络配置

#### 第 1 步：修改 IP 地址

```bash
# 在从库虚拟机中执行
sudo nano /etc/netplan/01-netcfg.yaml
```

将 IP 地址修改为 `192.168.100.21`（主库是 `.20`，从库用 `.21`）：

```yaml
network:
  version: 2
  ethernets:
    ens33:
      dhcp4: no
      addresses:
        - 192.168.100.21/24
      routes:
        - to: default
          via: 192.168.100.2
      nameservers:
        addresses:
          - 192.168.100.2
          - 8.8.8.8
```

```bash
# 应用网络配置
sudo netplan apply

# 验证 IP 地址
ip addr show ens33 | grep "inet "
```

#### 第 2 步：修改主机名（可选，方便区分）

```bash
# 在从库执行
sudo hostnamectl set-hostname ubuntu-slave

# 在主库执行（如果主机名需要区分）
sudo hostnamectl set-hostname ubuntu-master
```

### 1.3 网络互通验证

```bash
# 在主库上 ping 从库
ping -c 4 192.168.100.21

# 在从库上 ping 主库
ping -c 4 192.168.100.20
```

<aside>
✅

**检查点 1**：两台虚拟机均能互 ping 成通，IP 地址分别为 `.20` 和 `.21`。

</aside>

### 1.4 验证从库 MySQL 安装

克隆的虚拟机应该已经安装了 MySQL，验证一下：

```bash
# 在从库上检查 MySQL 服务状态
sudo systemctl status mysql --no-pager

# 确认 MySQL 版本
mysql --version

# 登录 MySQL 验证
sudo mysql -u root -p123456 -e "SELECT VERSION();"
```

<aside>
💡

如果克隆后 MySQL 无法启动，提示 `Failed to initialize DD Storage Engine` 或 `different UUID`，这是因为克隆复制了主库的 auto.cnf 文件（包含相同的 UUID）。请执行以下修复：

</aside>

#### 修复 UUID 冲突

```bash
# 停止 MySQL 服务
sudo systemctl stop mysql

# 删除 auto.cnf（MySQL 重启后会自动生成新的 UUID）
sudo rm /var/lib/mysql/auto.cnf

# 重新启动 MySQL
sudo systemctl start mysql

# 验证新的 UUID 已生成
sudo cat /var/lib/mysql/auto.cnf
```

<aside>
⚠️

两台 MySQL 实例的 UUID 必须不同。删除 `auto.cnf` 后 MySQL 会在下次启动时自动生成一个新的，确保主从 UUID 不冲突。

</aside>

### 1.5 确认 server_id 唯一性

```bash
# 在主库上执行
sudo mysql -u root -p123456 -e "SHOW VARIABLES LIKE 'server_id';"

# 在从库上执行
sudo mysql -u root -p123456 -e "SHOW VARIABLES LIKE 'server_id';"
```

如果两台的 `server_id` 相同（克隆导致），后续复制会出问题。我们将在任务二和任务三中分别配置。

<aside>
✅

**检查点 2**：从库 MySQL 正常运行，UUID 与主库不同，两台机器可以互相通信。

</aside>

---

## 任务二 主库配置（30 分钟）

### 2.1 编辑主库配置文件

```bash
# 在主库 (192.168.100.20) 上执行
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

在 `[mysqld]` 段中添加或修改以下配置：

```ini
[mysqld]
# ========= 复制相关配置 =========

# 服务器唯一标识（每个节点必须不同）
server-id = 1

# 开启二进制日志（主从复制的基础）
log_bin = /var/lib/mysql/mysql-bin

# binlog 格式：ROW 模式（最安全，推荐）
binlog_format = ROW

# binlog 过期时间（7 天）
binlog_expire_logs_seconds = 604800

# 单个 binlog 文件最大 100MB
max_binlog_size = 100M

# 允许从库远程连接
bind-address = 0.0.0.0
```

<aside>
💬

**binlog_format 三种模式对比**

| 模式 | 记录内容 | 优点 | 缺点 |
| --- | --- | --- | --- |
| `STATEMENT` | SQL 语句本身 | 日志量小 | 某些函数（NOW()、UUID()）可能导致主从不一致 |
| `ROW` | 每行数据的变更 | 最安全，不会不一致 | 日志量大（大批量更新时） |
| `MIXED` | 默认用 STATEMENT，特殊情况用 ROW | 折中方案 | 调试困难 |

**生产环境推荐 ROW 模式**，这也是 MySQL 8.0 的默认值。

</aside>

### 2.2 重启主库 MySQL 并验证配置

```bash
# 在主库上执行
sudo systemctl restart mysql
sudo systemctl status mysql --no-pager
```

```sql
sudo mysql

-- 验证 binlog 已开启
SHOW VARIABLES LIKE 'log_bin';               -- 应为 ON
SHOW VARIABLES LIKE 'binlog_format';         -- 应为 ROW
SHOW VARIABLES LIKE 'server_id';             -- 应为 1

-- 查看当前 binlog 文件和位置（后面要用）
SHOW BINARY LOG STATUS;

SHOW MASTER STATUS;
```

输出类似：

```
+------------------+----------+--------------+------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB |
+------------------+----------+--------------+------------------+
| mysql-bin.000001 |      157 |              |                  |
+------------------+----------+--------------+------------------+
```

<aside>
⚠️

**务必记录 File 和 Position！** 后面配置从库时需要填入这两个值。在记事本中记录：

- File: `mysql-bin.000001`
- Position: `157`

</aside>

### 2.3 创建复制专用账号

```sql
-- 在主库上执行
sudo mysql

-- 创建复制专用账号
CREATE USER 'repl'@'192.168.100.%'
    IDENTIFIED WITH mysql_native_password BY '123456';

-- 授予复制权限
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'192.168.100.%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 验证账号创建成功
SELECT user, host, plugin FROM mysql.user WHERE user = 'repl';
```

<aside>
💬

**为什么使用 `mysql_native_password`？**

MySQL 8.0 默认使用 `caching_sha2_password` 认证插件，但部分复制场景下从库连接可能出现认证问题。使用 `mysql_native_password` 可以确保兼容性。如果客户端（如 Navicat）连接也遇到认证问题，同样可以指定此插件。

</aside>

### 2.4 防火墙放通

```bash
# 在主库上执行
# 查看防火墙状态
sudo ufw status

# 如果防火墙已启用，允许从库所在网段访问 MySQL 端口
sudo ufw allow from 192.168.100.0/24 to any port 3306 proto tcp

# 如果防火墙未启用，跳过此步骤
```

### 2.5 从库测试连接主库

```bash
# 在从库上执行——测试能否连接主库的 MySQL
mysql -h 192.168.100.20 -u repl -p123456 -e "SELECT 1;"
```

预期输出：

```
+---+
| 1 |
+---+
| 1 |
+---+
```

如果连接失败，排查顺序：
1. 主库 `bind-address` 是否为 `0.0.0.0`
2. 主库防火墙是否放通 3306
3. `repl` 账号的 host 是否为 `192.168.100.%`
4. 网络是否互通

<aside>
✅

**检查点 3**：主库 binlog 已开启、`repl` 账号已创建、从库可以远程连接主库 MySQL。

</aside>

---

## 任务三 从库配置与数据同步（30 分钟）

### 3.1 编辑从库配置文件

```bash
# 在从库 (192.168.100.21) 上执行
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

在 `[mysqld]` 段中添加或修改以下配置：

```ini
[mysqld]
# ========= 复制相关配置 =========

# 服务器唯一标识（必须与主库不同）
server-id = 2

# 中继日志（从库接收主库 binlog 后写入的本地日志）
relay_log = /var/lib/mysql/mysql-relay

# 从库设为只读（防止误写入破坏数据一致性）
read_only = ON

# 超级用户也只读（防止 root 误操作）
super_read_only = ON

# 允许远程连接（方便 Navicat 监控）
bind-address = 0.0.0.0
```

<aside>
💬

**`read_only` 与 `super_read_only` 的区别**

| 变量 | 影响范围 |
| --- | --- |
| `read_only = ON` | 普通用户不能写入，但 SUPER 权限用户（如 root）仍可写入 |
| `super_read_only = ON` | 连 root 也不能写入，彻底保护从库数据 |

从库建议两个都开启，防止运维人员误操作。

</aside>

### 3.2 重启从库 MySQL

```bash
# 在从库上执行
sudo systemctl restart mysql
sudo systemctl status mysql --no-pager
```

```sql
-- 验证从库配置
sudo mysql -u root -p123456

SHOW VARIABLES LIKE 'server_id';        -- 应为 2
SHOW VARIABLES LIKE 'relay_log';        -- 应为 /var/lib/mysql/mysql-relay
SHOW VARIABLES LIKE 'read_only';        -- 应为 ON
SHOW VARIABLES LIKE 'super_read_only';  -- 应为 ON
```

<aside>
✅

**检查点 4**：从库 `server_id = 2`，`read_only` 已开启，服务正常运行。

</aside>

### 3.3 主库执行全量备份

在主库上对数据进行加锁备份，确保备份数据的一致性：

```bash
# ====== 在主库上执行以下操作 ======

# 第 1 步：登录 MySQL，加全局读锁
sudo mysql -u root -p123456
```

```sql
-- 加锁（阻止所有写入，确保数据一致性）
FLUSH TABLES WITH READ LOCK;

-- 查看当前 binlog 位置（关键信息！）
--SHOW BINARY LOG STATUS;
SHOW MASTER STATUS;
```

记录输出中的 File 和 Position，例如：

```
+------------------+----------+--------------+------------------+
| File             | Position | Binlog_Do_DB | Binlog_Ignore_DB |
+------------------+----------+--------------+------------------+
| mysql-bin.000001 |      157 |              |                  |
+------------------+----------+--------------+------------------+
```

<aside>
⚠️

**不要关闭这个 MySQL 会话！** `FLUSH TABLES WITH READ LOCK` 在会话关闭后会自动解锁。保持这个会话打开，另开一个终端窗口执行备份。

</aside>

```bash
# 第 2 步：另开一个终端窗口，执行全量备份
# （不要关闭上面的 MySQL 会话！）

sudo mysqldump -u root -p123456 \
    --all-databases \
    --single-transaction \
    --source-data=2 \
    --routines \
    --triggers \
    --events \
    --set-gtid-purged=OFF \
    > /tmp/master_full_backup.sql
```

参数说明：

| 参数 | 含义 |
| --- | --- |
| `--all-databases` | 备份所有数据库（包括系统库，主从复制需要） |
| `--single-transaction` | InnoDB 一致性快照 |
| `--source-data=2` | 在备份文件中以注释形式记录 binlog 位置（方便后续查阅） |
| `--routines` | 包含存储过程和函数 |
| `--triggers` | 包含触发器 |
| `--events` | 包含定时事件 |
| `--set-gtid-purged=OFF` | 不输出 GTID 信息（课堂环境简化） |

```bash
# 第 3 步：确认备份文件生成成功
ls -lh /tmp/master_full_backup.sql

# 查看备份文件中记录的 binlog 位置
grep "CHANGE REPLICATION" /tmp/master_full_backup.sql | head -2
```

```sql
-- 第 4 步：回到之前的 MySQL 会话，解锁
UNLOCK TABLES;
```

<aside>
💬

**备份流程总结**

```
FLUSH TABLES WITH READ LOCK    ← 加锁，暂停写入
    ↓
SHOW BINARY LOG STATUS          ← 记录 binlog 位置
    ↓
mysqldump ... > backup.sql      ← 另开终端执行备份
    ↓
UNLOCK TABLES                    ← 解锁，恢复写入
```

整个过程加锁时间取决于备份速度。对于大型数据库，可以使用 `xtrabackup` 做物理备份来缩短锁定期。

</aside>

### 3.4 将备份文件传输到从库

```bash
# 在主库上执行
scp /tmp/master_full_backup.sql admin@192.168.100.21:/tmp/
```

<aside>
💡

如果 scp 提示连接被拒绝，可能需要在从库上安装 openssh-server：

```bash
# 在从库上执行
sudo apt install -y openssh-server
sudo systemctl enable --now ssh
```

</aside>

### 3.5 从库还原备份

```bash
# 在从库上执行
mysql -u root -p123456 < /tmp/master_full_backup.sql
```

```sql
-- 验证数据还原成功
sudo mysql -u root -p123456

SHOW DATABASES;
USE ecommerce;
SHOW TABLES;
SELECT COUNT(*) AS 'users行数' FROM users;
SELECT COUNT(*) AS 'products行数' FROM products;
SELECT COUNT(*) AS 'orders行数' FROM orders;
```

<aside>
✅

**检查点 5**：从库数据与主库一致，三张表的行数完全相同。

</aside>

---

## 任务四 复制启动与验证（30 分钟）

### 4.1 配置从库连接主库

```sql
-- 在从库上执行
sudo mysql -u root -p123456

-- 停止可能已运行的复制（如果是重新配置）
STOP REPLICA;
RESET REPLICA;

-- 配置从库连接主库
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_PORT = 3306,
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = '123456',
    SOURCE_LOG_FILE = 'mysql-bin.000001',
    SOURCE_LOG_POS = 157,
    SOURCE_CONNECT_RETRY = 10,
    GET_SOURCE_PUBLIC_KEY = 1;
```

参数说明：

| 参数 | 含义 |
| --- | --- |
| `SOURCE_HOST` | 主库 IP 地址 |
| `SOURCE_PORT` | 主库 MySQL 端口（默认 3306） |
| `SOURCE_USER` | 复制账号（之前创建的 repl） |
| `SOURCE_PASSWORD` | 复制账号密码 |
| `SOURCE_LOG_FILE` | 主库的 binlog 文件名（备份时记录的 File） |
| `SOURCE_LOG_POS` | 主库的 binlog 位置（备份时记录的 Position） |
| `SOURCE_CONNECT_RETRY` | 连接失败后重试间隔（秒） |
| `GET_SOURCE_PUBLIC_KEY` | 公钥认证（mysql_native_password 可省略） |

<aside>
⚠️

**`SOURCE_LOG_FILE` 和 `SOURCE_LOG_POS` 必须与备份时记录的值一致！** 填错会导致从库从错误的位置开始同步，造成数据不一致或同步失败。

</aside>

### 4.2 启动复制

```sql
-- 在从库上执行
START REPLICA;

-- 查看复制状态
SHOW REPLICA STATUS\G
```

### 4.3 验证复制状态

`SHOW REPLICA STATUS\G` 的输出中，重点关注以下字段：

| 字段 | 期望值 | 含义 |
| --- | --- | --- |
| `Replica_IO_Running` | **Yes** | IO 线程：从主库拉取 binlog |
| `Replica_SQL_Running` | **Yes** | SQL 线程：回放 relay log 中的事件 |
| `Seconds_Behind_Source` | **0** 或较小值 | 从库落后主库的秒数 |
| `Last_IO_Error` | 空 | IO 线程的最新错误信息 |
| `Last_SQL_Error` | 空 | SQL 线程的最新错误信息 |
| `Source_Log_File` | 与主库一致 | 从库当前读取的主库 binlog 文件 |
| `Read_Source_Log_Pos` | 逐步增长 | 从库读取到的主库 binlog 位置 |

```sql
-- 精简查看关键字段
SHOW REPLICA STATUS\G
```

预期看到：

```
Replica_IO_Running: Yes
Replica_SQL_Running: Yes
Seconds_Behind_Source: 0
Last_IO_Error:
Last_SQL_Error:
```

<aside>
✅

**检查点 6**：`Replica_IO_Running` 和 `Replica_SQL_Running` 均为 **Yes**，无错误信息。

</aside>

### 4.4 新旧语法对照

MySQL 8.0.23 起引入了新的复制语法。以下是对照表：

| 旧语法（8.0.23 前） | 新语法（8.0.23 起） |
| --- | --- |
| `CHANGE MASTER TO` | `CHANGE REPLICATION SOURCE TO` |
| `START SLAVE` | `START REPLICA` |
| `STOP SLAVE` | `STOP REPLICA` |
| `SHOW SLAVE STATUS\G` | `SHOW REPLICA STATUS\G` |
| `MASTER_HOST` | `SOURCE_HOST` |
| `MASTER_USER` | `SOURCE_USER` |
| `MASTER_PASSWORD` | `SOURCE_PASSWORD` |
| `MASTER_LOG_FILE` | `SOURCE_LOG_FILE` |
| `MASTER_LOG_POS` | `SOURCE_LOG_POS` |
| `Slave_IO_Running` | `Replica_IO_Running` |
| `Slave_SQL_Running` | `Replica_SQL_Running` |
| `Seconds_Behind_Master` | `Seconds_Behind_Source` |
| `SQL_SLAVE_SKIP_COUNTER` | `sql_replica_skip_counter` |

<aside>
💬

旧语法在 MySQL 8.0 中仍然可用（向后兼容），但会产生 deprecation 警告。**建议使用新语法**，因为旧语法在未来版本中会被移除。本实验统一使用新语法。

</aside>

---

## 任务五 数据同步验证（20 分钟）

### 5.1 主库写入数据

```sql
-- 在主库上执行
sudo mysql -u root -p123456
USE ecommerce;

-- 记录当前数据量
SELECT COUNT(*) AS '插入前orders行数' FROM orders;

-- 插入一条新订单
INSERT INTO orders (user_id, product_id, quantity, total_amount, order_status)
VALUES (1, 1, 2, 598.00, 0);

-- 再插入一条
INSERT INTO orders (user_id, product_id, quantity, total_amount, order_status)
VALUES (3, 2, 1, 89.90, 1);

-- 确认插入成功
SELECT COUNT(*) AS '插入后orders行数' FROM orders;
SELECT * FROM orders ORDER BY order_id DESC LIMIT 2;
```

### 5.2 从库验证同步

```sql
-- 在从库上执行（稍等 1~2 秒让复制完成）
sudo mysql -u root -p123456
USE ecommerce;

-- 验证数据已同步
SELECT COUNT(*) AS '从库orders行数' FROM orders;
SELECT * FROM orders ORDER BY order_id DESC LIMIT 2;
```

<aside>
💬

**从库数据与主库完全一致，说明复制正常工作！** 数据从主库写入 → 写入 binlog → 从库 IO 线程拉取 → 写入 relay log → 从库 SQL 线程回放 → 数据落盘。整个过程通常在毫秒级别完成。

</aside>

### 5.3 从库写入被拒绝

```sql
-- 在从库上尝试写入
USE ecommerce;

INSERT INTO orders (user_id, product_id, quantity, total_amount, order_status)
VALUES (2, 1, 1, 299.00, 0);
```

预期报错：

```
ERROR 1290 (HY000): The MySQL server is running with the --read-only option
so it cannot execute this statement
```

<aside>
💡

`read_only` 保护机制生效了。从库只能读取，不能写入，这保证了数据只能从主库单向同步到从库，避免数据冲突。

</aside>

### 5.4 Navicat 两边连接对比

1. 打开 Navicat，新建两个 MySQL 连接：
   - **主库**：`192.168.100.20`，端口 `3306`，root / `123456`
   - **从库**：`192.168.100.21`，端口 `3306`，root / `123456`
2. 分别打开 `ecommerce` → `orders` 表
3. 确认两边数据完全一致

<aside>
✅

**检查点 7**：主库新增数据已同步到从库，从库写入被 read_only 拒绝，Navicat 两边数据一致。

</aside>

---

## 任务六 复制故障排查（40 分钟）

<aside>
💬

**排错思路**

复制出问题时，第一步永远是：

```sql
SHOW REPLICA STATUS\G
```

重点关注四个字段：`Replica_IO_Running`、`Replica_SQL_Running`、`Last_IO_Error`、`Last_SQL_Error`。根据错误信息定位问题，修复后重启复制。

</aside>

---

### 故障 1：从库连接不上主库（IO 线程停止）

#### 模拟故障

```bash
# 在主库上执行——用防火墙阻止从库连接
sudo ufw deny from 192.168.100.21 to any port 3306 proto tcp
```

然后在从库上重启复制，观察故障：

```sql
-- 在从库上执行
STOP REPLICA;
START REPLICA;
SHOW REPLICA STATUS\G
```

#### 观察故障现象

关键字段输出：

```
Replica_IO_Running: Connecting
Last_IO_Error: error connecting to master 'repl@192.168.100.20:3306' ...
```

#### 分析错误信息

| 线索 | 判断 |
| --- | --- |
| `Replica_IO_Running: Connecting` | IO 线程正在尝试连接，但连不上 |
| `Last_IO_Error` 中包含 `connection refused` 或 `timeout` | 网络层面的问题 |

常见原因：
- 主库防火墙阻止了连接
- 主库 `bind-address` 不是 `0.0.0.0`
- 主库 MySQL 服务未启动
- IP 地址配置错误

#### 修复

```bash
# 在主库上执行——删除刚才的阻止规则
sudo ufw delete deny from 192.168.100.21 to any port 3306 proto tcp
```

```sql
-- 在从库上执行
STOP REPLICA;
START REPLICA;
SHOW REPLICA STATUS\G
```

确认 `Replica_IO_Running: Yes` 已恢复。

---

### 故障 2：复制账号密码错误

#### 模拟故障

```sql
-- 在从库上执行——故意修改为错误的密码
STOP REPLICA;

CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = 'wrong_password',
    SOURCE_LOG_FILE = 'mysql-bin.000001',
    SOURCE_LOG_POS = 157;

START REPLICA;
SHOW REPLICA STATUS\G
```

#### 观察故障现象

```
Replica_IO_Running: Connecting
Last_IO_Error: Error connecting to source 'repl@192.168.100.20:3306'.
This is attempt 1/86400, ...
Message: Authentication plugin 'mysql_native_password' reported error:
Access denied for user 'repl'@'192.168.100.21' (using password: YES)
```

#### 分析错误信息

| 线索 | 判断 |
| --- | --- |
| `Access denied` | 认证失败，用户名或密码错误 |
| `using password: YES` | 确实传了密码，但密码不正确 |

#### 修复

```sql
-- 在从库上执行
STOP REPLICA;

-- 重新配置正确的密码
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = '123456',
    SOURCE_LOG_FILE = 'mysql-bin.000001',
    SOURCE_LOG_POS = 157;

START REPLICA;
SHOW REPLICA STATUS\G
```

确认 `Replica_IO_Running: Yes` 已恢复。

---

### 故障 3：binlog 位置错误

#### 模拟故障

```sql
-- 在从库上执行——故意填写错误的 binlog 文件名
STOP REPLICA;

CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = '123456',
    SOURCE_LOG_FILE = 'mysql-bin.999999',
    SOURCE_LOG_POS = 1;

START REPLICA;
SHOW REPLICA STATUS\G
```

#### 观察故障现象

```
Replica_IO_Running: No
Replica_SQL_Running: Yes
Last_IO_Error: Got fatal error 1236 from source when reading data from binary log:
'Could not find first log file name in binary log index file'
```

#### 分析错误信息

| 线索 | 判断 |
| --- | --- |
| `Could not find first log file` | 指定的 binlog 文件在主库上不存在 |
| `Replica_IO_Running: No` | IO 线程已停止 |

常见原因：
- binlog 文件名写错了
- 主库 binlog 已经过期被清理
- 备份时记录的 File 值有误

#### 修复

```bash
# 在主库上确认当前的 binlog 文件和位置
sudo mysql -u root -p123456 -e "SHOW BINARY LOG STATUS;"
```

```sql
-- 在从库上执行
STOP REPLICA;

-- 使用正确的 binlog 文件和位置
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST = '192.168.100.20',
    SOURCE_USER = 'repl',
    SOURCE_PASSWORD = '123456',
    SOURCE_LOG_FILE = 'mysql-bin.000001',
    SOURCE_LOG_POS = 157;

START REPLICA;
SHOW REPLICA STATUS\G
```

<aside>
⚠️

如果主库 binlog 已经过期清理，`mysql-bin.000001` 也被删了，那就需要重新做一次全量备份 + 数据同步（回到任务三重新来一遍）。所以 binlog 过期时间不宜设置太短。

</aside>

---

### 故障 4：数据冲突导致 SQL 线程停止

#### 模拟故障

```sql
-- ====== 第 1 步：在主库上创建一张新表 ======
-- 在主库上执行
sudo mysql -u root -p123456
USE ecommerce;

CREATE TABLE test_conflict (
    id INT PRIMARY KEY,
    name VARCHAR(50)
);

INSERT INTO test_conflict VALUES (1, '数据A');
```

```sql
-- ====== 第 2 步：在从库上临时关闭 read_only，插入冲突数据 ======
-- 在从库上执行
sudo mysql -u root -p123456
USE ecommerce;

-- 临时关闭 read_only（需要 root 权限）
SET GLOBAL read_only = OFF;
SET GLOBAL super_read_only = OFF;

-- 手动在从库上插入一条与主库冲突的数据
INSERT INTO test_conflict VALUES (1, '冲突数据B');

-- 恢复 read_only
SET GLOBAL read_only = ON;
SET GLOBAL super_read_only = ON;
```

```sql
-- ====== 第 3 步：在主库上对同一行做更新 ======
-- 在主库上执行
UPDATE test_conflict SET name = '数据A已修改' WHERE id = 1;
```

```sql
-- ====== 第 4 步：观察从库复制状态 ======
-- 在从库上执行
SHOW REPLICA STATUS\G
```

#### 观察故障现象

```
Replica_IO_Running: Yes
Replica_SQL_Running: No
Last_SQL_Error: Could not execute Update_rows event on table ecommerce.test_conflict;
Can't find record in 'test_conflict', Error_code: 1032;
...
```

#### 分析错误信息

| 线索 | 判断 |
| --- | --- |
| `Replica_SQL_Running: No` | SQL 线程已停止，数据不再同步 |
| `Can't find record` | 从库找不到要更新的记录（因为数据不一致） |
| `Error_code: 1032` | 找不到目标行（数据冲突的典型错误码） |

这是最严重的故障类型——数据不一致导致 SQL 线程崩溃，后续所有数据变更都不会再同步。

#### 修复方法 A：跳过单个错误事件

```sql
-- 在从库上执行（适用于仅跳过 1 个事件的情况）
STOP REPLICA;

SET GLOBAL sql_replica_skip_counter = 1;

START REPLICA;
SHOW REPLICA STATUS\G
```

<aside>
💡

`SET GLOBAL sql_replica_skip_counter = 1` 的含义：跳过接下来的 1 个 binlog 事件。适合处理单个偶发的冲突事件。

注意：如果主库执行的是批量操作（如 `UPDATE ... WHERE ...`），可能需要多次执行跳过。

</aside>

#### 修复方法 B：手动修正数据后重启

```sql
-- 在从库上执行——先确认 test_conflict 表中的数据
USE ecommerce;
SELECT * FROM test_conflict;

-- 手动修正从库数据，使其与主库一致
-- （实际应该先查主库的数据，再在从库上修正）
UPDATE test_conflict SET name = '数据A已修改' WHERE id = 1;

-- 重启复制
START REPLICA;
SHOW REPLICA STATUS\G
```

<aside>
⚠️

**跳过错误只是临时手段，根本解决方法是确保数据一致。** 生产环境中，如果频繁出现 SQL 错误，需要检查是否有应用绕过主库直接写从库，或者 binlog_format 是否为 ROW（ROW 模式下冲突概率最低）。

</aside>

### 6.1 故障排查总结

| 故障类型 | IO 线程 | SQL 线程 | 典型错误信息 | 修复思路 |
| --- | --- | --- | --- | --- |
| 连接失败 | Connecting / No | Yes | `connection refused / timeout` | 检查防火墙、bind-address、网络 |
| 认证失败 | Connecting / No | Yes | `Access denied` | 检查用户名、密码、host 限制 |
| binlog 位置错误 | No | Yes | `Could not find ... log file` | 回主库确认正确的 File 和 Position |
| 数据冲突 | Yes | No | `Can't find record` / `Error 1032` | 修正数据或跳过事件 |

<aside>
✅

**检查点 8**：完成 4 种故障的模拟、诊断和修复，所有故障修复后 `SHOW REPLICA STATUS` 显示双 Yes。

</aside>

---

## 任务七 高可用方案认知（30 分钟）

<aside>
💬

**主从复制 ≠ 高可用**

我们搭建的主从复制解决了两个问题：

- **数据热备**：从库有一份实时同步的数据副本
- **读写分离**：主库写、从库读，分担压力

但它**没有解决**一个关键问题：**当主库宕机时，谁来自动把从库提升为新主库？**

目前的方案需要人工介入：
1. 发现主库宕机
2. 手动在从库上执行 `STOP REPLICA`，去掉只读限制
3. 修改应用的数据库连接地址
4. 通知所有业务方

这个过程可能需要几分钟到几十分钟，期间服务不可用。这就是主从复制和"高可用"的核心差距。

</aside>

### 7.1 常见高可用方案

#### 方案一：MHA（Master High Availability）

MHA 是目前最成熟的 MySQL 高可用方案之一，由日本工程师开发。

| 项目 | 说明 |
| --- | --- |
| **原理** | MHA Manager 节点监控主库，当主库故障时自动将数据最新的从库提升为新主库 |
| **切换流程** | 检测到主库宕机 → 从宕机主库的从库中选一个数据最新的 → 将其提升为主库 → 其他从库指向新主库 |
| **数据补偿** | 切换前会尝试从宕机主库获取未同步的 binlog 并应用到新主库，最大程度减少数据丢失 |
| **优点** | 成熟稳定、自动切换、数据损失小 |
| **缺点** | 需要额外部署 MHA Manager 节点、配置较复杂、社区维护减少 |

```
           MHA Manager（监控节点）
                  |
        ┌─────────┼─────────┐
        |         |         |
    主库(M)    从库(S1)   从库(S2)
    .20        .21        .22

主库宕机 → MHA 自动提升 S1 为新主 → S2 改指向 S1
```

#### 方案二：InnoDB Cluster（MySQL 官方方案）

InnoDB Cluster 是 MySQL 官方推出的高可用方案，基于 Group Replication 技术。

| 项目 | 说明 |
| --- | --- |
| **原理** | 多个 MySQL 节点组成一个组，数据在组内自动同步，任意节点故障后自动选主 |
| **组件** | MySQL Shell + MySQL Router + Group Replication |
| **选主机制** | 基于 Paxos 协议投票，超过半数节点同意即可选出新主 |
| **优点** | 官方方案、自动选主、配置工具完善 |
| **缺点** | 至少需要 3 个节点（保证多数派）、对服务器性能有一定要求 |

```
    应用 → MySQL Router（自动路由）
              |
      ┌───────┼───────┐
      |       |       |
  节点1    节点2    节点3
  (Primary) (Secondary) (Secondary)
      ↑____________↑____________↑
         Group Replication（自动同步）
```

#### 方案三：ProxySQL / MySQL Router（中间件）

这类方案不直接管理复制，而是在应用和数据库之间加一个中间件层。

| 项目 | 说明 |
| --- | --- |
| **原理** | 中间件感知后端数据库状态，自动将读请求路由到从库，写请求路由到主库 |
| **故障转移** | 检测到主库不可用时，自动将写流量切换到新的主库 |
| **优点** | 对应用透明、支持读写分离、连接池管理 |
| **缺点** | 增加一层网络延迟、中间件本身也需要高可用 |

### 7.2 方案对比

| 对比维度 | 传统主从复制 | MHA | InnoDB Cluster | 中间件方案 |
| --- | --- | --- | --- | --- |
| **自动故障切换** | 不支持 | 支持 | 支持 | 支持 |
| **数据一致性** | 最终一致 | 接近一致 | 强一致 | 依赖底层复制 |
| **最少节点数** | 2（1主1从） | 3（1 Manager + 1主1从） | 3 | 2 + 中间件 |
| **配置复杂度** | 低 | 中 | 中高 | 中 |
| **适用场景** | 小型项目、学习 | 中大型生产环境 | 企业级、云原生 | 需要读写分离 |
| **初学者理解难度** | ★☆☆ | ★★☆ | ★★★ | ★★☆ |

### 7.3 当前阶段学习建议

<aside>
💡

**分阶段学习路线**

| 阶段 | 内容 | 目标 |
| --- | --- | --- |
| **当前阶段**（本实验） | 掌握主从复制搭建与排错 | 理解复制原理，能手动处理故障 |
| **进阶阶段** | 学习 MHA 部署 | 实现自动故障切换 |
| **高级阶段** | 学习 InnoDB Cluster | 掌握官方高可用方案 |
| **生产实践** | 结合中间件 + 监控 | 构建完整的高可用架构 |

对于初学者来说，**先把主从复制吃透**是最重要的。无论上层方案多复杂，底层都是基于 binlog 的主从复制。理解了 binlog 传输 → relay log → SQL 回放这条链路，再学 MHA 和 InnoDB Cluster 就会轻松很多。

</aside>

<aside>
💬

**课堂讨论问题**

1. 主从复制架构中，如果从库宕机了，对主库有影响吗？
2. 如果主库宕机后，从库的数据还没有完全同步完（`Seconds_Behind_Source > 0`），切换后会丢失多少数据？
3. 为什么 InnoDB Cluster 至少需要 3 个节点？
4. 在你的理解中，什么样的业务场景需要高可用，什么场景主从复制就够了？

</aside>

<aside>
✅

**检查点 9**：能说出主从复制与高可用的区别，能描述 MHA 和 InnoDB Cluster 的基本原理。

</aside>

---

## 实验总结

### 完成情况自评

| 序号 | 任务 | 耗时 | 完成 |
| --- | --- | --- | --- |
| 任务一 | 复制环境准备（克隆、改 IP、改主机名、修 UUID） | 30 min | ☐ |
| 任务二 | 主库配置（binlog、repl 账号、防火墙） | 30 min | ☐ |
| 任务三 | 从库配置与数据同步（relay_log、read_only、mysqldump） | 30 min | ☐ |
| 任务四 | 复制启动与验证（CHANGE REPLICATION SOURCE TO、双 Yes） | 30 min | ☐ |
| 任务五 | 数据同步验证（主库写入、从库只读、Navicat 对比） | 20 min | ☐ |
| 任务六 | 复制故障排查（4 种故障模拟与修复） | 40 min | ☐ |
| 任务七 | 高可用方案认知（MHA、InnoDB Cluster、方案对比） | 30 min | ☐ |

### 核心知识点回顾

| 知识点 | 关键内容 |
| --- | --- |
| 复制原理 | 主库 binlog → 从库 IO 线程拉取 → relay log → SQL 线程回放 |
| binlog_format | ROW 最安全，STATEMENT 日志量小但可能不一致 |
| read_only | 保护从库数据不被误写入 |
| 关键命令 | `CHANGE REPLICATION SOURCE TO`、`START REPLICA`、`SHOW REPLICA STATUS` |
| 排错思路 | `SHOW REPLICA STATUS\G` → 看 IO/SQL 线程状态 → 看 Last_Error → 针对性修复 |
| 高可用 | 主从复制 ≠ 高可用，需要自动故障切换能力 |

### 常见问题速查

| 症状 | 可能原因 | 快速修复 |
| --- | --- | --- |
| IO_Running: Connecting | 网络不通、防火墙、认证失败 | ping → telnet 3306 → 检查账号 |
| IO_Running: No | binlog 位置错误、主库 binlog 已清理 | 重新确认 File 和 Position |
| SQL_Running: No | 数据冲突、表结构不一致 | 跳过事件或手动修正数据 |
| Seconds_Behind_Source 很大 | 从库性能不足、网络延迟大 | 检查从库负载、网络质量 |
| UUID 冲突 | 克隆虚拟机未处理 | 删 auto.cnf 重启 MySQL |

---

## 附录

### 附录 A：MySQL 主从复制数据流向图

```
┌──────────────────────┐         ┌──────────────────────┐
│       主库 (Master)        │         │       从库 (Slave)         │
│     192.168.100.20        │         │     192.168.100.21        │
│                          │         │                          │
│  应用写入 → InnoDB 引擎    │         │                          │
│       ↓                  │         │                          │
│  binlog (ROW 格式)        │ ──TCP──→ │  IO Thread 拉取 binlog    │
│                          │  3306    │       ↓                  │
│                          │         │  relay log (本地中继日志)   │
│                          │         │       ↓                  │
│                          │         │  SQL Thread 回放事件       │
│                          │         │       ↓                  │
│                          │         │  InnoDB 引擎 → 数据落盘    │
│                          │         │                          │
│  read_only = OFF          │         │  read_only = ON           │
└──────────────────────┘         └──────────────────────┘
```

### 附录 B：SHOW REPLICA STATUS 关键字段速查

| 字段名 | 含义 | 正常值 |
| --- | --- | --- |
| `Replica_IO_Running` | IO 线程状态 | Yes |
| `Replica_SQL_Running` | SQL 线程状态 | Yes |
| `Seconds_Behind_Source` | 从库落后主库的秒数 | 0 或很小 |
| `Source_Host` | 主库 IP | 192.168.100.20 |
| `Source_Log_File` | 从库正在读取的主库 binlog 文件 | 与主库一致 |
| `Read_Source_Log_Pos` | 从库读取到的 binlog 位置 | 逐步增长 |
| `Relay_Log_File` | 从库当前的 relay log 文件名 | 有值 |
| `Relay_Log_Pos` | relay log 当前位置 | 逐步增长 |
| `Last_IO_Error` | IO 线程最后的错误 | 空（正常） |
| `Last_SQL_Error` | SQL 线程最后的错误 | 空（正常） |
| `Source_Server_Id` | 主库的 server-id | 1 |
| `Replica_SQL_Running_State` | SQL 线程的详细状态 | Slave has read all relay log |
| `Executed_Gtid_Set` | 已执行的 GTID 集合 | 视配置而定 |
| `Last_IO_Errno` | IO 线程最后的错误码 | 0（正常） |
| `Last_SQL_Errno` | SQL 线程最后的错误码 | 0（正常） |

### 附录 C：复制搭建流程总结

```
  准备阶段                    主库配置                     从库配置
┌────────────┐          ┌──────────────┐          ┌──────────────┐
│ 克隆虚拟机    │          │ 编辑 mysqld.cnf │          │ 编辑 mysqld.cnf │
│ 改 IP (.21)  │          │ server-id = 1  │          │ server-id = 2  │
│ 改主机名      │          │ log_bin = ON   │          │ relay_log = ...│
│ 删 auto.cnf  │          │ binlog_format  │          │ read_only = ON │
│ 互 ping      │          │ bind-address   │          │ bind-address   │
└────────────┘          │ 重启 MySQL     │          │ 重启 MySQL     │
                        │ 创建 repl 账号   │          └──────┬───────┘
                        │ 放通防火墙       │                 │
                        └──────┬───────┘                 │
                               │                          │
                        ┌──────┴───────┐          ┌──────┴───────┐
                        │ SHOW BINARY   │          │ mysqldump 还原 │
                        │ LOG STATUS    │ ──scp──→ │ 到从库         │
                        │ 记录 File/Pos  │  备份文件  └──────┬───────┘
                        └──────────────┘                   │
                                                  ┌──────┴───────┐
                                                  │ CHANGE REPLIC.│
                                                  │ SOURCE TO ...  │
                                                  │ START REPLICA  │
                                                  │ SHOW REPLICA   │
                                                  │ STATUS\G       │
                                                  │ → 双 Yes ✓      │
                                                  └──────────────┘
```

<aside>
✅

**实验完成标志**：主从复制搭建成功（双 Yes）、数据同步验证通过、4 种故障排查完成、高可用方案理解到位。

</aside>
