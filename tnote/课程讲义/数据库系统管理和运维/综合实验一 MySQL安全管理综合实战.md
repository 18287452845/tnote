# 综合实验一 MySQL 数据库安全管理综合实战

🎯 **本实验学习目标**

- 能从零完成 MySQL 安装、安全加固、账号体系搭建和权限验证的全流程
- 能模拟真实企业场景，设计并实施多角色账号权限方案
- 能使用审计手段验证安全配置的有效性
- 能编写安全加固检查脚本并输出检查报告

<aside>
🧭

**实验主线**：安装与加固 → 账号体系设计 → 权限实施与验证 → 安全审计与报告

本实验将项目五中分散的知识点串联为一个完整的安全管理流程，模拟企业新服务器上线前的安全配置场景。

</aside>

<aside>
🖥️

**实验拓扑**

- 虚拟机（VM）：Ubuntu 22.04 LTS，运行 MySQL 8.0（IP：`192.168.100.20`）
- 宿主机（Windows）：使用 Navicat 远程连接虚拟机中的 MySQL
- 所有密码统一使用 `123456`（课堂环境）

**课堂产出**

- 一份完整的企业数据库安全加固配置
- 一套多角色账号权限方案及验证记录
- 一份安全审计检查报告

</aside>

---

## 实验背景

某创业公司新购一台 Ubuntu 服务器，需要部署 MySQL 数据库，为公司的电商系统提供数据存储服务。公司有以下几类人员需要访问数据库：

| 角色 | 职责 | 数据访问需求 |
| --- | --- | --- |
| 运维工程师（DBA） | 数据库管理、备份恢复 | 全库管理权限 |
| 后端开发 | 编写业务代码、调试 | 开发库的读写 + 建表权限 |
| 数据分析师 | 生成报表 | 生产库只读 |
| 客户端应用 | 电商系统运行 | 特定库的 CRUD 权限 |

你的任务是以安全运维工程师的身份，完成从安装到安全审计的全部流程。

---

## 任务一 服务器安全初始化

### 1.1 环境准备

#### 第 1 步：拍摄快照

<aside>
📸

在 VMware 中拍摄快照，命名为"综合实验一-初始状态"。后续操作出错时可快速恢复。

</aside>

#### 第 2 步：更换 APT 软件源

<aside>
🪞

默认的 Ubuntu 软件源服务器在国外，下载速度较慢。替换为国内镜像源（以阿里云为例）可大幅提升 `apt install` 速度。

</aside>

```bash
# 备份原始源文件
sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak

# 替换为阿里云镜像源（Ubuntu 22.04 Jammy）
sudo tee /etc/apt/sources.list > /dev/null <<'EOF'
deb https://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
deb https://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
EOF

# 更新软件包索引
sudo apt update
```

#### 第 3 步：系统更新与时间校准

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 确认时区为上海
sudo timedatectl set-timezone Asia/Shanghai
timedatectl

# 测试网络连通性
ping -c 4 mirrors.aliyun.com
```

### 1.2 MySQL 安装与加固

#### 第 1 步：安装 MySQL

```bash
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
mysql --version
```

#### 第 2 步：运行安全加固向导

```bash
sudo mysql_secure_installation
```

按以下选项配置：

| 选项 | 选择 | 原因 |
| --- | --- | --- |
| VALIDATE PASSWORD COMPONENT | No | 课堂统一简单密码 |
| root 密码 | `123456` | 课堂统一密码 |
| 删除匿名用户 | Yes | 安全基线 |
| 禁止 root 远程登录 | Yes | 安全基线 |
| 删除 test 数据库 | Yes | 安全基线 |
| 刷新权限表 | Yes | 确保生效 |

#### 第 3 步：验证加固结果

```sql
sudo mysql

-- 1. 确认匿名用户已删除
SELECT user, host FROM mysql.user WHERE user = '';
-- 预期：空结果集

-- 2. 确认 root 只能本机登录
SELECT user, host FROM mysql.user WHERE user = 'root';
-- 预期：host 列只有 localhost

-- 3. 确认 test 数据库已删除
SHOW DATABASES LIKE 'test';
-- 预期：空结果集

-- 4. 确认版本
SELECT VERSION();
```

<aside>
✅

**检查点 1**：匿名用户为空、root 只有 localhost、test 库已删除、服务正常运行。

</aside>

---

## 任务二 安全基线配置

### 2.1 修改配置文件

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

在 `[mysqld]` 段中确认或添加以下配置：

```ini
[mysqld]
# 网络边界：监听所有网卡（内网实验）
bind-address = 0.0.0.0
port = 3306

# 字符集
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

# 时区
default-time-zone = '+08:00'

# 日志配置
log_error = /var/log/mysql/error.log
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2

# binlog（数据恢复基础）
log_bin = /var/lib/mysql/mysql-bin
binlog_format = ROW
server_id = 1
binlog_expire_logs_seconds = 604800
max_binlog_size = 100M
```

在 `[client]` 段添加：

```ini
[client]
default-character-set = utf8mb4
```

### 2.2 重启并验证所有配置

```bash
sudo systemctl restart mysql
sudo systemctl status mysql --no-pager
```

```sql
sudo mysql

-- 逐项验证
SHOW VARIABLES LIKE 'bind_address';          -- 0.0.0.0
SHOW VARIABLES LIKE 'character_set_server';  -- utf8mb4
SHOW VARIABLES LIKE 'collation_server';      -- utf8mb4_unicode_ci
SHOW VARIABLES LIKE 'time_zone';             -- +08:00
SHOW VARIABLES LIKE 'log_bin';               -- ON
SHOW VARIABLES LIKE 'binlog_format';         -- ROW
SHOW VARIABLES LIKE 'slow_query_log';        -- ON
SHOW VARIABLES LIKE 'long_query_time';       -- 2
```

### 2.3 配置防火墙

```bash
# 查看防火墙状态
sudo ufw status

# 如果防火墙已启用，只允许内网访问 MySQL
sudo ufw allow from 192.168.100.0/24 to any port 3306 proto tcp

# 如果防火墙未启用，跳过此步骤
```

<aside>
✅

**检查点 2**：所有 8 项配置变量验证通过，防火墙规则已配置。

</aside>

---

## 任务三 企业账号体系搭建

### 3.1 创建业务数据库

```sql
sudo mysql

-- 降低密码策略（课堂环境）
SET GLOBAL validate_password.policy = LOW;
SET GLOBAL validate_password.length = 6;

-- 创建电商系统数据库
CREATE DATABASE IF NOT EXISTS ecommerce
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 切换到电商库
USE ecommerce;

-- 创建用户表
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    status TINYINT DEFAULT 1 COMMENT '1=正常 0=禁用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建商品表
CREATE TABLE products (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10,2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    status TINYINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建订单表
CREATE TABLE orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    total_amount DECIMAL(10,2) NOT NULL,
    order_status TINYINT DEFAULT 0 COMMENT '0=待付款 1=已付款 2=已发货 3=已完成',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- 插入示例数据
INSERT INTO users (username, email, phone, password_hash) VALUES
    ('zhangsan', 'zhangsan@example.com', '13800000001', 'hash_value_1'),
    ('lisi', 'lisi@example.com', '13800000002', 'hash_value_2'),
    ('wangwu', 'wangwu@example.com', '13800000003', 'hash_value_3');

INSERT INTO products (name, category, price, stock) VALUES
    ('机械键盘', '电脑外设', 299.00, 100),
    ('无线鼠标', '电脑外设', 99.00, 200),
    ('显示器', '电脑配件', 1599.00, 50),
    ('USB-C 扩展坞', '电脑外设', 199.00, 150);

INSERT INTO orders (user_id, product_id, quantity, total_amount, order_status) VALUES
    (1, 1, 1, 299.00, 1),
    (1, 2, 2, 198.00, 3),
    (2, 3, 1, 1599.00, 1),
    (3, 4, 1, 199.00, 0);
```

### 3.2 设计并创建账号体系

按照最小权限原则，为四类角色创建账号：

| 账号 | 主机 | 权限范围 | 对应角色 |
| --- | --- | --- | --- |
| `dba_admin` | `192.168.100.%` | 所有库的管理权限 | 运维工程师 |
| `dev_user` | `192.168.100.%` | ecommerce 的 DML + DDL | 后端开发 |
| `analyst` | `192.168.100.%` | ecommerce 的只读 | 数据分析师 |
| `app_ecom` | `192.168.100.%` | ecommerce 的 CRUD | 客户端应用 |

```sql
-- 1. DBA 管理账号
CREATE USER 'dba_admin'@'192.168.100.%'
    IDENTIFIED WITH mysql_native_password BY '123456';
GRANT ALL PRIVILEGES ON *.* TO 'dba_admin'@'192.168.100.%'
    WITH GRANT OPTION;

-- 2. 开发账号（仅限 ecommerce 库）
CREATE USER 'dev_user'@'192.168.100.%'
    IDENTIFIED WITH mysql_native_password BY '123456';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, CREATE VIEW, SHOW VIEW
    ON ecommerce.* TO 'dev_user'@'192.168.100.%';

-- 3. 分析师账号（只读）
CREATE USER 'analyst'@'192.168.100.%'
    IDENTIFIED WITH mysql_native_password BY '123456';
GRANT SELECT ON ecommerce.* TO 'analyst'@'192.168.100.%';

-- 4. 应用账号（CRUD，不含 DDL）
CREATE USER 'app_ecom'@'192.168.100.%'
    IDENTIFIED WITH mysql_native_password BY '123456';
GRANT SELECT, INSERT, UPDATE, DELETE ON ecommerce.* TO 'app_ecom'@'192.168.100.%';

-- 验证所有账号
SELECT user, host, plugin, account_locked FROM mysql.user
WHERE user NOT IN ('root', 'mysql.sys', 'mysql.session', 'debian-sys-maint');
```

### 3.3 逐角色验证权限边界

在宿主机 Navicat 中创建四个连接，分别用不同账号登录，执行以下验证：

#### DBA 账号验证

```sql
-- 以下操作都应该成功
SELECT USER(), CURRENT_USER();
SHOW DATABASES;
SELECT * FROM ecommerce.users;
CREATE DATABASE test_dba_verify;
DROP DATABASE test_dba_verify;
SHOW GRANTS;
```

#### 开发账号验证

```sql
-- 应成功：DML 和 DDL
SELECT * FROM ecommerce.products;
INSERT INTO ecommerce.products (name, category, price, stock)
    VALUES ('测试商品', '测试', 1.00, 1);
DELETE FROM ecommerce.products WHERE name = '测试商品';

-- 应成功：建表
CREATE TABLE ecommerce.dev_test (id INT);
DROP TABLE ecommerce.dev_test;

-- 应失败：访问系统库
SELECT * FROM mysql.user;
-- 预期：ERROR 1142

-- 应失败：创建新数据库
CREATE DATABASE hack_db;
-- 预期：ERROR 1044
```

#### 分析师账号验证

```sql
-- 应成功：查询
SELECT o.order_id, u.username, p.name, o.total_amount
FROM ecommerce.orders o
JOIN ecommerce.users u ON o.user_id = u.user_id
JOIN ecommerce.products p ON o.product_id = p.product_id;

-- 应失败：修改数据
INSERT INTO ecommerce.users (username, email, phone, password_hash)
    VALUES ('hack', 'hack@x.com', '000', 'hack');
-- 预期：ERROR 1142

-- 应失败：删表
DROP TABLE ecommerce.orders;
-- 预期：ERROR 1142
```

#### 应用账号验证

```sql
-- 应成功：CRUD
SELECT * FROM ecommerce.products WHERE stock > 0;
INSERT INTO ecommerce.orders (user_id, product_id, quantity, total_amount)
    VALUES (1, 2, 1, 99.00);

-- 应失败：DDL 操作
ALTER TABLE ecommerce.products ADD COLUMN test_col INT;
-- 预期：ERROR 1142

-- 应失败：删除数据表
DROP TABLE ecommerce.orders;
-- 预期：ERROR 1142
```

#### 补充验证：存储过程的 EXECUTE 权限

先由 DBA 创建一个简单的存储过程，再授权给 dev_user 执行：

```sql
-- 用 dba_admin 连接，创建存储过程
DELIMITER //
CREATE PROCEDURE ecommerce.get_order_count(IN p_status INT)
BEGIN
    SELECT COUNT(*) AS '订单数量' FROM orders WHERE order_status = p_status;
END //
DELIMITER ;

-- 授权 dev_user 执行该存储过程
GRANT EXECUTE ON PROCEDURE ecommerce.get_order_count TO 'dev_user'@'192.168.100.%';
```

切换到 dev_user 连接验证：

```sql
-- 应成功：已获得 EXECUTE 权限
CALL ecommerce.get_order_count(1);

-- 应失败：没有 GRANT OPTION，无法再授权给别人
GRANT EXECUTE ON PROCEDURE ecommerce.get_order_count TO 'analyst'@'192.168.100.%';
-- 预期：ERROR 1044
```

<aside>
💬

**GRANT EXECUTE 权限的意义**

生产环境中，开发账号通常不能直接操作业务表数据，而是通过存储过程封装的业务逻辑来操作。这时需要单独授予 `EXECUTE ON PROCEDURE` 权限，让账号只能"按流程执行"而不能"随意读写"。

</aside>

<aside>
✅

**检查点 3**：四个账号均已创建，权限边界验证全部通过——允许的操作成功，越权操作被拒绝。

</aside>

---

## 任务四 安全审计与加固报告

### 4.1 执行安全审计检查

使用 root 账号执行以下审计 SQL，记录结果：

```sql
-- ========== 审计项 1：匿名用户检查 ==========
SELECT '匿名用户' AS 检查项,
    CASE WHEN COUNT(*) = 0 THEN '通过' ELSE '风险' END AS 结果,
    CONCAT('共 ', COUNT(*) , ' 个匿名用户') AS 详情
FROM mysql.user WHERE user = '';

-- ========== 审计项 2：root 远程登录检查 ==========
SELECT 'root远程登录' AS 检查项,
    CASE WHEN COUNT(*) = 0 THEN '通过' ELSE '风险' END AS 结果,
    CONCAT('root 可从 ', CONVERT(GROUP_CONCAT(host) USING utf8mb4), ' 登录') AS 详情
FROM mysql.user WHERE user = 'root' AND host != 'localhost';

-- ========== 审计项 3：空密码账号检查 ==========
SELECT '空密码账号' AS 检查项,
    CASE WHEN COUNT(*) = 0 THEN '通过' ELSE '风险' END AS 结果,
    CONCAT('共 ', COUNT(*), ' 个空密码账号') AS 详情
FROM mysql.user WHERE authentication_string = '' OR authentication_string IS NULL;

-- ========== 审计项 4：ALL PRIVILEGES 账号检查 ==========
-- 注意：SHOW GRANTS 结果需要人工查看
SELECT user, host FROM mysql.user
WHERE Super_priv = 'Y' AND user NOT IN ('root', 'mysql.sys', 'mysql.session');

-- ========== 审计项 5：FILE 权限检查 ==========
SELECT 'FILE权限' AS 检查项,
    CASE WHEN COUNT(*) = 0 THEN '通过' ELSE '风险' END AS 结果,
    CONCAT(COUNT(*), ' 个非管理员账号拥有 FILE 权限') AS 详情
FROM mysql.user WHERE File_priv = 'Y' AND user NOT IN ('root');

-- ========== 审计项 6：bind-address 检查 ==========
SELECT 'bind-address' AS 检查项,
    CASE
        WHEN VARIABLE_VALUE = '0.0.0.0' THEN '需配合防火墙'
        WHEN VARIABLE_VALUE = '127.0.0.1' THEN '仅本机'
        ELSE VARIABLE_VALUE
    END AS 结果
FROM performance_schema.global_variables
WHERE VARIABLE_NAME = 'bind_address';

-- ========== 审计项 7：binlog 状态检查 ==========
SELECT 'binlog状态' AS 检查项,
    CASE WHEN VARIABLE_VALUE = 'ON' THEN '通过' ELSE '风险' END AS 结果
FROM performance_schema.global_variables
WHERE VARIABLE_NAME = 'log_bin';

-- ========== 审计项 8：字符集检查 ==========
SELECT '字符集' AS 检查项,
    VARIABLE_VALUE AS 结果
FROM performance_schema.global_variables
WHERE VARIABLE_NAME = 'character_set_server';

-- ========== 审计项 9：test 数据库检查 ==========
SELECT 'test数据库' AS 检查项,
    CASE WHEN COUNT(*) = 0 THEN '通过' ELSE '风险' END AS 结果
FROM information_schema.schemata WHERE schema_name = 'test';

-- ========== 审计项 10：密码策略检查 ==========
SELECT '密码策略' AS 检查项,
    VARIABLE_VALUE AS 结果
FROM performance_schema.global_variables
WHERE VARIABLE_NAME = 'validate_password.policy';
```

### 4.2 查看当前所有账号的权限摘要

```sql
-- 输出所有非系统账号的授权信息
SELECT
    grantee,
    GROUP_CONCAT(DISTINCT privilege_type ORDER BY privilege_type) AS 权限列表
FROM information_schema.schema_privileges
WHERE grantee NOT LIKE '%root%'
    AND grantee NOT LIKE '%mysql.%'
    AND grantee NOT LIKE '%sys%'
    AND grantee NOT LIKE '%session%'
GROUP BY grantee
ORDER BY grantee;
```

### 4.3 生成安全加固检查报告

<aside>
📝

**课堂任务**：根据以上审计结果，填写以下安全加固检查报告。

</aside>

| 序号 | 检查项目 | 期望状态 | 实际结果 | 是否通过 |
| --- | --- | --- | --- | --- |
| 1 | 匿名用户 | 已删除 | （填写） | （填写） |
| 2 | root 远程登录 | 禁止 | （填写） | （填写） |
| 3 | 空密码账号 | 无 | （填写） | （填写） |
| 4 | 高危权限账号 | 仅 root | （填写） | （填写） |
| 5 | FILE 权限 | 仅 root | （填写） | （填写） |
| 6 | bind-address | 0.0.0.0 + 防火墙 | （填写） | （填写） |
| 7 | binlog | ON | （填写） | （填写） |
| 8 | 字符集 | utf8mb4 | （填写） | （填写） |
| 9 | test 数据库 | 已删除 | （填写） | （填写） |
| 10 | 密码策略 | 已配置 | （填写） | （填写） |

---

## 实验总结

| 任务 | 核心能力 | 关键验证点 |
| --- | --- | --- |
| 任务一：安装加固 | MySQL 安全安装 | 匿名用户删除、root 禁止远程、test 库删除 |
| 任务二：基线配置 | 安全配置文件管理 | 8 项配置变量全部验证通过 |
| 任务三：账号体系 | 最小权限设计与实施 | 四类账号权限边界全部验证通过 |
| 任务四：安全审计 | 安全检查与报告 | 10 项审计检查全部完成 |

<aside>
💬

**本实验核心收获**

1. 安全不是某一个配置项，而是从安装到账号到配置到审计的完整链条
2. 最小权限原则：每个账号只获得完成工作所需的最小权限集
3. 安全配置必须可验证——"配了"不等于"生效了"，必须用审计手段确认
4. 养成安全加固报告的习惯，是企业合规和安全运维的基本要求

</aside>
