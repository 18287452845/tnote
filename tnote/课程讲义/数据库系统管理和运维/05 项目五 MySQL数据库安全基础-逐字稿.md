# 05 项目五 MySQL 数据库安全基础 — 课堂逐字稿

---

## 第 1 课 安装与验证：让 MySQL "能跑起来"

同学们好，今天我们开始第五个项目——MySQL 数据库安全基础。

先看我们这节课要解决什么问题。很简单，三个字：装起来。装完之后要能验证——服务在跑、能登录、能看到版本和数据库列表。

在动手之前，我先说一句最重要的话，你们记住就行：**安装不等于安全，安装只是第一步。** 后面三节课我们会一步步把安全补齐。

### MySQL 是什么？

一句话理解：如果把 Web 应用比作餐厅，MySQL 就是后厨的"仓库管理系统"——所有数据的存、取、改、删都由它负责。

MySQL 是世界上最流行的开源关系型数据库。我们用的 8.0 版本有几个重要的变化，你们现在不需要全记住，但有一个必须知道——**默认认证插件变成了 caching_sha2_password**。什么意思？就是说旧版的客户端可能连不上。等会儿我们会遇到这个问题，到时候再说。

### 第一步：拍快照

打开 VMware，菜单 → 虚拟机 → 快照 → 拍摄快照，名字写"安装MySQL前"。

为什么要先拍快照？因为安装或配置出错的时候可以一键恢复。养成习惯，每次做重大操作之前都拍一个。

### 第二步：换源加速

Ubuntu 24.04 的源配置文件格式变了，用的是 DEB822 格式，路径是 `/etc/apt/sources.list.d/ubuntu.sources`。

先备份：

```bash
sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
```

然后编辑：

```bash
sudo nano /etc/apt/sources.list.d/ubuntu.sources
```

把内容全部替换成阿里云镜像。内容在讲义里有，照着复制就行。保存退出后执行：

```bash
sudo apt update
```

看到索引更新完就 OK 了。

如果你是 Ubuntu 22.04，格式不一样，用的是传统的 `/etc/apt/sources.list`，讲义里也有对应的写法。

### 第三步：检查时间和网络

```bash
timedatectl
ping -c 4 mirrors.aliyun.com
```

为什么要校准时间？因为后面排查日志、看 binlog 的时间线，如果系统时间不准，你就很难判断"谁在什么时候做了什么"。网络不用说了，装软件必须联网。

如果时区不对，设一下：

```bash
sudo timedatectl set-timezone Asia/Shanghai
```

### 第四步：安装 MySQL

三条命令，依次执行：

```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
```

装完之后验证：

```bash
mysql --version
sudo systemctl status mysql --no-pager
```

看到版本号和 active(running) 就说明装好了。

### 第五步：运行安全加固向导

```bash
sudo mysql_secure_installation
```

这个向导会问你几个问题，按讲义上的选：

1. 设置 root 密码 → 输入 `123456`。这是我们课堂的统一密码，后面所有账号都用这个，免得大家设完就忘了。
2. 删除匿名用户 → Yes
3. 禁止 root 远程登录 → Yes
4. 删除 test 数据库 → Yes
5. 刷新权限表 → Yes

注意，有些 Ubuntu 版本的向导不会提示你设密码。如果你遇到了这种情况，安装完手动执行：

```sql
sudo mysql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
FLUSH PRIVILEGES;
exit;
```

这一步做了两件事：一是设了密码 123456，二是把 root 的认证插件从 auth_socket 改成了 mysql_native_password。改完之后就可以用 `mysql -u root -p123456` 登录了。

### 第六步：首次登录验证

```bash
mysql -u root -p123456
```

或者如果你还没改认证插件，用：

```bash
sudo mysql
```

进去之后执行：

```sql
SELECT VERSION();
SHOW DATABASES;
exit;
```

看到版本号和数据库列表，第 1 课就算完成了。

有个问题大家可能会好奇——为什么 `sudo mysql` 不用密码就能登录？因为 Ubuntu 的 apt 安装默认把 root 的认证插件设成了 auth_socket，这个插件不检查密码，而是看你当前的 Linux 用户是不是 root。`sudo` 提权之后就是 root 了，所以直接放行。但这只适合本机操作，想让 root 用密码登录就得改认证插件。

好，第 1 课小结：
- 安装的目标不是"看懂所有概念"，而是完成：安装→启动→加固→验证
- `sudo mysql` 能进是因为 Ubuntu 默认 auth_socket；改为密码认证后用 `mysql -u root -p123456` 登录
- 课堂统一密码：123456，后续所有账号都用这个密码

---

## 第 2 课 配置文件与安全基线：把"边界"和"默认坑"补齐

上节课我们让 MySQL 能跑起来了。但"能跑"不等于"跑得对"。这节课要做三件事，把 MySQL 的运行边界和默认配置调正确，否则会出现远程连不上、中文乱码、时间错位这些常见问题。

### 配置文件在哪？

Ubuntu 24.04 的 MySQL 配置分散在好几个路径，你们不用全记，记住一个就行：

**`/etc/mysql/mysql.conf.d/mysqld.cnf`**

后面所有改配置的操作都在这个文件里。

配置文件里有两种配置段：`[mysqld]` 是服务端配置，`[client]` 是客户端配置。写错段不会报错但不会生效，这是新手最常踩的坑。比如你把 bind-address 写到 `[client]` 段里，MySQL 根本不会读，而且还不告诉你。

### 三件必改

#### 第一件：bind-address — 远程访问边界

MySQL 默认只监听 127.0.0.1，也就是只有本机能连。我们要让它监听所有网卡，这样宿主机的 Navicat 才能连进来：

```ini
[mysqld]
bind-address = 0.0.0.0
port = 3306
```

注意，0.0.0.0 会监听所有网卡，只用于内网实验环境。生产环境必须配合防火墙和安全组，不能直接暴露在公网上。

#### 第二件：字符集 — utf8mb4

```ini
[mysqld]
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[client]
default-character-set = utf8mb4
```

有个容易踩的坑：MySQL 中的 `utf8` 不是真正的 UTF-8，它只支持 3 字节字符，存不了 Emoji。`utf8mb4` 才是完整的 UTF-8。所以结论就是——永远用 utf8mb4，忘记 utf8 的存在。

#### 第三件：时区 — +08:00

```ini
[mysqld]
default-time-zone = '+08:00'
```

MySQL 默认用 SYSTEM 时区。如果操作系统的时区配置和预期不一致，或者应用服务器和数据库服务器时区不一样，时间就会偏。最常见的就是差 8 小时。显式指定 +08:00 可以避免。

### 重启与验证

改完配置必须重启才生效：

```bash
sudo systemctl restart mysql
sudo systemctl status mysql --no-pager
```

然后用 SHOW VARIABLES 逐项验证：

```sql
SHOW VARIABLES LIKE 'bind_address';
SHOW VARIABLES LIKE 'character_set_server';
SHOW VARIABLES LIKE 'collation_server';
SHOW VARIABLES LIKE 'time_zone';
SELECT NOW();
```

如果值和配置的不一样，三个排查方向：配置写没写在 [mysqld] 段下、改完有没有重启、有没有其他配置文件覆盖了。

第 2 课小结：
- 三件必改：bind-address（边界）、utf8mb4（编码）、time_zone（时间一致）
- 修改配置后：重启服务 + SHOW VARIABLES 验证生效
- 配置写错段不会报错但不会生效，这是最常见的坑

---

## 第 3 课 账号与权限：远程能连，但不用 root

上节课我们把 MySQL 的网络边界打开了，bind-address 改成了 0.0.0.0。但这还不够——要远程连上 MySQL，还得有账号。这节课我们要创建一个业务账号，让宿主机的 Navicat 能连进来，同时遵循数据库安全核心原则：**不用 root，按最小权限创建业务账号**。

### 账号身份：'user'@'host'

MySQL 的账号不是单独的用户名，而是 **用户名 + 来源主机** 的组合。比如 `'app'@'192.168.100.%'` 表示用户名是 app，只允许从 192.168.100.x 这个网段连进来。

同一个用户名搭配不同主机，是不同的账号。比如 `'app'@'%'` 和 `'app'@'192.168.100.%'` 是两条独立记录，密码和权限可以不同。

很多同学远程连不上，就是因为只记了用户名和密码，忘了 MySQL 还要匹配来源主机。你从宿主机 192.168.100.1 登录，如果只创建了 `'app'@'localhost'`，MySQL 会直接拒绝。

### 权限体系：四层结构

MySQL 的权限是分层检查的：

1. **连接验证**：用户名 + 主机名对不对？密码对不对？
2. **全局权限**：GRANT ALL ON *.*  — 超级管理员才给
3. **数据库级权限**：GRANT SELECT ON mydb.*  — 大多数业务账号在这层
4. **表级/列级权限**：更精细的控制

类比一下：全局权限是大楼门禁卡，数据库级是楼层门禁卡，表级是办公室钥匙，列级是抽屉钥匙。业务账号通常只需要"某个楼层"就够了。

有个重要的点：MySQL 没有显式 DENY 语法。如果数据库级给了某表的 SELECT，不能再通过表级权限"拒绝"同一张表。要细粒度控制，就从一开始只授需要的权限。

### 创建数据库和远程账号

下面是完整的操作流程，在虚拟机上执行。先登录 MySQL：

```bash
sudo mysql
```

然后依次执行：

首先，降低密码策略。这是课堂环境必须做的一步，因为 validate_password 默认策略是 MEDIUM，要求大小写 + 数字 + 特殊字符 + 至少 8 位，我们的课堂密码 123456 无法通过：

```sql
-- 先检查密码验证组件是否已安装
SELECT COMPONENT_ID, COMPONENT_URN FROM mysql.component;
-- 如果没有 component_validate_password 的记录，才执行安装：
INSTALL COMPONENT 'file://component_validate_password';

SET GLOBAL validate_password.policy = LOW;
SET GLOBAL validate_password.length = 6;
```

然后建库建表：

```sql
CREATE DATABASE IF NOT EXISTS stusta;
USE stusta;

CREATE TABLE IF NOT EXISTS students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    score DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO students (name, score) VALUES
    ('张三', 88.5),
    ('李四', 92.0),
    ('王五', 76.0);
```

创建远程账号：

```sql
CREATE USER IF NOT EXISTS 'app'@'192.168.100.%' IDENTIFIED WITH mysql_native_password BY '123456';
```

这里有两个要点：
1. `192.168.100.%` 限制了只有这个网段能连进来
2. `mysql_native_password` 确保旧版 Navicat 也能连，避免 2059 报错

授权：

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON stusta.* TO 'app'@'192.168.100.%';
```

只给了 stusta 这个库的增删改查权限，不能建库、不能删表、不能看系统库。

验证：

```sql
SHOW GRANTS FOR 'app'@'192.168.100.%';
```

### 防火墙

如果启用了 ufw，需要放通 3306 端口：

```bash
sudo ufw allow from 192.168.100.0/24 to any port 3306 proto tcp
sudo ufw status
```

只允许实验网段访问，不要对所有来源开放。

### 从 Navicat 远程登录验证

在宿主机打开 Navicat，新建 MySQL 连接：

| 配置项 | 填写内容 |
|--------|---------|
| 主机 | 192.168.100.20（虚拟机 IP） |
| 端口 | 3306 |
| 用户名 | app |
| 密码 | 123456 |

点击"测试连接"，成功后保存。

连上之后做两个验证：

**能做的**：查看 stusta.students 表的数据、执行 SELECT、INSERT。

**不能做的**：`CREATE DATABASE hackdb;` 会报 1044 权限不足、`DROP TABLE stusta.students;` 会报 1142 权限不足、`SELECT * FROM mysql.user;` 也会报 1142。

这就是最小权限——能干活的权限给了，越权的操作全部被拦截。

如果连不上，按这个顺序排查：
1. MySQL 有没有监听 0.0.0.0:3306？`sudo ss -tlnp | grep 3306`
2. 防火墙有没有放通？`sudo ufw status`
3. 账号 host 是否匹配？`SELECT user, host, plugin FROM mysql.user;`

### FLUSH PRIVILEGES 要不要执行？

很多同学习惯性执行 FLUSH PRIVILEGES，但并不是每次都需要。

**不需要的情况**：用标准语句操作的时候——CREATE USER、ALTER USER、DROP USER、GRANT、REVOKE，MySQL 会自动刷新权限缓存，不用手动 flush。

**需要的情况**：直接改了系统表，比如 `UPDATE mysql.user SET ...` 或 `DELETE FROM mysql.user WHERE ...`。这时候 MySQL 还在用旧的内存缓存，必须手动 flush。

记个口诀：**用标准语句，不用 flush；直接改表，必须 flush。**

### 账号生命周期管理

账号不是建完就不管了。安全运维要对账号做全生命周期管理：

- **查看账号**：`SELECT user, host, plugin, account_locked FROM mysql.user;`
- **修改密码**：`ALTER USER 'app'@'192.168.100.%' IDENTIFIED BY '123456';`
- **撤销权限**：`REVOKE DELETE ON stusta.* FROM 'app'@'192.168.100.%';`
- **锁定账号**：`ALTER USER 'app'@'192.168.100.%' ACCOUNT LOCK;`  — 临时禁止登录，但不删除
- **解锁**：`ALTER USER 'app'@'192.168.100.%' ACCOUNT UNLOCK;`
- **删除账号**：`DROP USER 'app'@'192.168.100.%';` — 不可逆，删之前确认没有业务在用

### 密码策略

MySQL 8.0 内置了 validate_password 组件，可以强制密码复杂度。

课堂环境我们用 LOW 策略 + 长度 6，密码统一 123456，专注学习操作流程。生产环境要用 MEDIUM 或 STRONG，密码长度至少 8 位，必须有大小写、数字和特殊字符。

注意，SET GLOBAL 的修改是临时的，重启后恢复默认。要永久生效，在配置文件里加：

```ini
[mysqld]
validate_password.policy = LOW
validate_password.length = 6
```

第 3 课小结：
- 账户身份 = 'user'@'host'，host 约束"从哪里来"
- 权限分四层：全局→数据库→表→列，授权尽量精确到数据库级
- 远程访问四重边界：监听边界 + 防火墙边界 + 账号 host 边界 + 最小权限授权
- 标准权限语句会自动生效；直接改系统表才需要 FLUSH PRIVILEGES
- 账号有完整生命周期：创建→授权→验证→修改→锁定→删除
- 课堂密码统一 123456，创建账号前需先降低 validate_password 策略为 LOW

---

## 第 4 课 日志：会排错、会定位慢、会恢复

前三节课我们做了：装起来→配安全→管住人。但还有一环没闭合——**出了问题怎么办？误操作怎么追溯？数据丢了怎么恢复？** 答案就是日志。

这节课我们要掌握四类日志，重点是 binlog。

### 四种主要日志

| 日志 | 用途 | 建议 |
|------|------|------|
| 错误日志 | 故障排查第一入口 | 默认开启，必须会看 |
| 通用查询日志 | 记录所有 SQL，用于审计/调试 | 性能杀手，只临时开 |
| binlog | 记录所有写操作，用于复制和恢复 | 建议长期开启 |
| 慢查询日志 | 记录慢 SQL，用于性能定位 | 建议开启 |

为什么不能全开？通用查询日志会记录每一条 SQL，包括 SELECT，高并发下每秒可能产生几 MB 日志，严重影响性能。binlog 只记录写操作，体积小得多。

### 错误日志

服务异常先看这里：

```bash
tail -100 /var/log/mysql/error.log
```

实时跟踪用：

```bash
sudo tail -f /var/log/mysql/error.log
```

在 MySQL 内查看路径：

```sql
SHOW VARIABLES LIKE 'log_error';
```

常见场景：Can't start server 说明启动失败，Access denied 说明认证失败，Disk full 说明磁盘满了。排错步骤就是：看最近 50 行 → 找 [ERROR] → 搜索解决方案。

### 慢查询日志

系统慢了怎么找 SQL？看慢查询日志。

```sql
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = 1;
```

这样超过 1 秒的 SQL 和没用索引的 SQL 都会被记录。

查看：

```bash
sudo tail -50 /var/log/mysql/slow.log
```

MySQL 自带分析工具 mysqldumpslow：

```bash
sudo mysqldumpslow -s c -t 10 /var/log/mysql/slow.log
```

`-s c` 按执行次数排序，`-s at` 按平均时间排序，`-t 10` 只看前 10 条。

实战流程：用户说系统卡 → 看 Slow_queries 计数 → 用 mysqldumpslow 找最慢的 SQL → EXPLAIN 分析执行计划 → 优化索引或改写 SQL。

### 通用查询日志

记录每一条到达 MySQL 的 SQL，只在排错时临时开：

```sql
SET GLOBAL general_log = 1;
-- 排错...
SET GLOBAL general_log = 0;
```

用完必须关，否则磁盘会被撑满。

### Binlog（重点）

binlog 是这节课的重点。它记录所有修改数据的操作——INSERT、UPDATE、DELETE、DDL。用途两个：主从复制和时间点恢复（PITR）。

#### 开启 binlog

编辑配置文件 `/etc/mysql/mysql.conf.d/mysqld.cnf`，在 [mysqld] 段添加：

```ini
[mysqld]
log_bin = /var/lib/mysql/mysql-bin
binlog_format = ROW
server_id = 1
binlog_expire_logs_seconds = 604800
max_binlog_size = 100M
```

几个参数解释：
- `binlog_format = ROW`：记录每行数据变更前后的值，最精确最安全，生产环境统一用 ROW
- `binlog_expire_logs_seconds = 604800`：7 天自动清理
- `max_binlog_size = 100M`：单个文件最大 100M

重启生效：

```bash
sudo systemctl restart mysql
```

验证：

```sql
SHOW VARIABLES LIKE 'log_bin';          -- 应该是 ON
SHOW VARIABLES LIKE 'binlog_format';    -- 应该是 ROW
SHOW BINARY LOGS;
SHOW BINARY LOG STATUS;
```

#### 查看 binlog 内容

binlog 是二进制的，不能直接 cat，要用 mysqlbinlog 工具：

```bash
sudo mysqlbinlog --base64-output=DECODE-ROWS -v /var/lib/mysql/mysql-bin.000001 | less
```

`--base64-output=DECODE-ROWS` 把 base64 编码解码成可读格式，`-v` 显示行变更详情，ROW 格式必须加这两个参数。

按时间范围筛选：

```bash
sudo mysqlbinlog \
  --start-datetime="2026-04-21 08:00:00" \
  --stop-datetime="2026-04-21 10:00:00" \
  /var/lib/mysql/mysql-bin.000001 | less
```

按位置筛选更精确：

```bash
sudo mysqlbinlog \
  --start-position=154 \
  --stop-position=1024 \
  /var/lib/mysql/mysql-bin.000001 | less
```

#### 时间点恢复 PITR

场景：今天上午 10 点有人误执行了 `DELETE FROM students;`，整张表清空了。你有一个昨晚的全量备份，但恢复备份只能回到昨晚，今天上午的正常数据全丢了。

PITR 的思路：先恢复昨晚的备份 → 再用 binlog 重放今天 00:00 到 09:59 的所有正常操作 → 数据恢复到误操作前一刻。

三步走：

```bash
# 第 1 步：恢复全量备份
mysql -u root -p stusta < full_backup_20260420.sql

# 第 2 步：从 binlog 定位误操作
sudo mysqlbinlog --base64-output=DECODE-ROWS -v /var/lib/mysql/mysql-bin.000002 | grep -B5 "DELETE FROM students"

# 第 3 步：回放 binlog 到误操作前一刻
sudo mysqlbinlog \
  --stop-datetime="2026-04-21 09:59:59" \
  --database=stusta \
  /var/lib/mysql/mysql-bin.000001 \
  /var/lib/mysql/mysql-bin.000002 | mysql -u root -p
```

注意顺序：必须先恢复全量备份，再回放 binlog。顺序反了全量备份会覆盖 binlog 回放的数据，等于白干。记个口诀：**先备后 bin，顺序不能反。**

#### binlog 管理

```sql
FLUSH BINARY LOGS;                    -- 手动切换到新的 binlog 文件
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 7 DAY);  -- 清理 7 天前的
PURGE BINARY LOGS TO 'mysql-bin.000005';  -- 清理指定文件之前的
```

binlog 不清理会怎样？会一直增长，直到磁盘满。所以一定要设自动过期时间。

第 4 课小结：
- 错误日志：服务异常第一入口
- 慢查询日志：会开、会看、会用 mysqldumpslow 定位慢 SQL
- 通用查询日志：临时排错利器，用完即关
- binlog：能开启、能验证、能解释 PITR 三步走
- binlog 管理：设置自动清理，避免磁盘撑满

---

## 项目总结

我们用了四节课，完成了一个完整的安全运维闭环：

| 课时 | 核心能力 | 验收点 |
|------|---------|--------|
| 第 1 课 | 装得起来 | 服务 active + SELECT VERSION() |
| 第 2 课 | 配得安全 | bind-address / utf8mb4 / time_zone 生效 |
| 第 3 课 | 管得住人 | Navicat 能用最小权限账号远程登录，越权操作被拦截 |
| 第 4 课 | 能追溯/能恢复 | 能看错误/慢查询；binlog 开启并能解释 PITR 三步走 |

记住开头那句话：**装得起来 → 配得安全 → 管得住人 → 出事能追溯/能恢复**。这就是数据库安全运维的完整思路。

有什么问题现在可以提问。
