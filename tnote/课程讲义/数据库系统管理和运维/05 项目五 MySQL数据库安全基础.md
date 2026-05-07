# 05 项目五 MySQL 数据库安全基础

🎯 **本项目学习目标**

- 能在 Ubuntu 24.04 LTS 环境下完成 MySQL 8.0 的安装、启动与基础验证
- 能理解 Ubuntu 默认认证方式，并完成 root 初始登录与基础安全加固
- 能基于内网场景创建受限账号，并配置远程访问权限
- 能按最小权限原则完成账号授权、查询、撤销与删除
- 能识别错误日志、慢查询日志、通用查询日志和 binlog 的用途，并完成 binlog 开启与基础恢复思路演练

<aside>
🧭

**主线地图（先记这一句）**：装得起来 → 配得安全（边界/基线）→ 管得住人（最小权限）→ 出事能追溯/能恢复（日志）。

</aside>

<aside>
🖥️

**实验拓扑（虚拟机 + 宿主机 Navicat）**

- 虚拟机（VM）：运行 MySQL Server（示例 IP：`192.168.100.20`）
- 宿主机（Windows）：使用 Navicat 远程连接虚拟机中的 MySQL
- 宿主机与虚拟机需能互相 ping 通；远程连接走 TCP/3306

**课堂产出**

- 虚拟机能通过 `sudo mysql` 登录并查看版本
- MySQL 基线配置生效：监听地址、字符集、时区均可验证
- 宿主机 Navicat 能使用 `app@192.168.100.%` 远程登录，但不能越权建库或删表
- 能说清四类日志的用途，并完成 binlog 开启验证

</aside>

---

## 第 1 课 安装与验证：让 MySQL "能跑起来"

### 1.1 本课要解决的问题

把 MySQL 在 Ubuntu 24.04 上装起来，并能验证：**服务在跑、能登录、能看到版本与数据库列表**。

### 1.2 本课交付物

- `mysql --version` 输出
- `sudo systemctl status mysql --no-pager` 显示 active(running)
- MySQL 内执行成功：
    - `SELECT VERSION();`
    - `SHOW DATABASES;`

### 1.3 MySQL 简介

MySQL 是世界上最流行的**开源关系型数据库管理系统（RDBMS）**，大量 Web 系统使用它作为核心数据存储。安全运维从安装开始：**安装 ≠ 安全，安装只是第一步**。

<aside>
💬

**一句话理解**：如果把 Web 应用比作餐厅，MySQL 就是后厨的"仓库管理系统"——所有数据的存、取、改、删都由它负责。

</aside>

#### MySQL 8.0 核心特性速览

| 特性 | 说明 |
| --- | --- |
| **默认认证插件** | `caching_sha2_password`（取代旧版 `mysql_native_password`） |
| **默认字符集** | `utf8mb4`（支持 Emoji 等四字节字符） |
| **窗口函数** | `ROW_NUMBER()`、`RANK()` 等分析函数 |
| **CTE（公共表表达式）** | `WITH ... AS` 语法，提升复杂查询可读性 |
| **角色管理** | `CREATE ROLE` / `GRANT role TO user`，简化批量权限管理 |
| **数据字典** | 元数据存储在 InnoDB 表中，不再依赖 `.frm` 文件 |

<aside>
⚠️

**认证插件兼容性提醒**

MySQL 8.0 默认使用 `caching_sha2_password`，部分旧版客户端（如老版本 Navicat12、PHP 7.1 以下的 `mysql_connect`）可能连接失败。解决方案：

- 升级客户端到支持新插件的版本（推荐）
- 对特定账号降级认证插件：`ALTER USER 'app'@'192.168.100.%' IDENTIFIED WITH mysql_native_password BY '123456';`

</aside>

### 1.4 安装前准备：拍快照 + 换源（Ubuntu 24.04）

#### 第 1 步：拍摄 VMware 快照（安全网）

<aside>
📸

**为什么先拍快照？** 安装或配置出错时可一键恢复。
**操作**：VMware 菜单 → 虚拟机 → 快照 → 拍摄快照 → 命名为"安装MySQL前"

</aside>

#### 第 2 步：换源加速

- Ubuntu 24.04 LTS 换源（DEB822 格式）
    
    Ubuntu 24.04 使用 `/etc/apt/sources.list.d/ubuntu.sources`（DEB822 格式）。
    
    ```bash
    # 1) 备份原文件
    sudo cp /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.bak
    
    # 2) 编辑配置文件
    sudo nano /etc/apt/sources.list.d/ubuntu.sources
    ```
    
    将文件内容**全部替换**为以下内容（阿里云镜像示例）：
    
    ```
    Types: deb
    URIs: https://mirrors.aliyun.com/ubuntu
    Suites: noble noble-updates noble-backports
    Components: main restricted universe multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
    
    Types: deb
    URIs: https://mirrors.aliyun.com/ubuntu
    Suites: noble-security
    Components: main restricted universe multiverse
    Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
    ```
    
    保存退出后更新索引：
    
    ```bash
    sudo apt update
    ```
    
- Ubuntu 22.04 LTS 换源（传统 sources.list 格式）
    
    Ubuntu 22.04 使用传统的 `/etc/apt/sources.list` 文件。
    
    ```bash
    # 1) 备份原文件
    sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
    
    # 2) 编辑配置文件
    sudo nano /etc/apt/sources.list
    ```
    
    将文件内容**全部替换**为以下内容（阿里云镜像示例）：
    
    ```
    deb https://mirrors.aliyun.com/ubuntu/ jammy main restricted universe multiverse
    deb https://mirrors.aliyun.com/ubuntu/ jammy-updates main restricted universe multiverse
    deb https://mirrors.aliyun.com/ubuntu/ jammy-backports main restricted universe multiverse
    deb https://mirrors.aliyun.com/ubuntu/ jammy-security main restricted universe multiverse
    ```
    
    保存退出后更新索引：
    
    ```bash
    sudo apt update
    ```
    

#### 第 3 步：检查系统时间与网络

MySQL 安全运维会频繁涉及日志时间、远程连接和软件源访问。安装前建议先确认系统时间和网络状态：

```bash
# 查看系统时间与时区
timedatectl

# 若时区不是 Asia/Shanghai，可设置为上海时区
sudo timedatectl set-timezone Asia/Shanghai

# 测试网络连通性
ping -c 4 mirrors.aliyun.com
```

<aside>
💬

**为什么先校准时间？**

后续排查错误日志、慢查询日志和 binlog 时都依赖时间线。如果系统时间不准，就很难判断"谁在什么时候做了什么"。

</aside>

### 1.5 安装与验证

```bash
# 0) 更新索引
sudo apt update

# 1) 安装 MySQL Server
sudo apt install -y mysql-server

# 2) 启动并设置开机自启
sudo systemctl enable --now mysql

# 3) 验证版本与服务状态
mysql --version
sudo systemctl status mysql --no-pager
```

#### 第 4 步：运行安全加固向导

```bash
sudo mysql_secure_installation
```

<aside>
✅

**向导建议选项（零基础按这个选）**

1. 设置 / 修改 root 密码 → 输入 `123456`（课堂统一密码，方便后续操作）
2. 删除匿名用户 → Yes
3. 禁止 root 远程登录 → Yes
4. 删除 test 数据库 → Yes
5. 刷新权限表 → Yes

**如果向导没有提示设置密码**（部分 Ubuntu 版本跳过此步），安装完成后手动执行：

```sql
sudo mysql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
FLUSH PRIVILEGES;
exit;
```

> 这一步同时将 root 的认证插件从 `auth_socket` 改为 `mysql_native_password`，后续就可以用 `mysql -u root -p123456` 密码方式登录了。

</aside>

#### 第 5 步：首次登录验证

```bash
# 方式一：如果刚才已将 root 改为密码认证，用密码登录
mysql -u root -p123456

# 方式二：如果还没改认证插件，用 sudo 登录
sudo mysql
```

```sql
SELECT VERSION();
SHOW DATABASES;
exit;
```

<aside>
💬

**为什么 `sudo mysql` 不用密码就能登录？**

Ubuntu 的 apt 安装默认将 root 的认证插件设为 `auth_socket`，该插件不检查密码，而是验证"当前 Linux 用户是否为 root"。所以 `sudo mysql` 能直接进入，这是安全设计——只有 root 能登录数据库管理员。

**但这只适合本机操作**。如果想让 root 也能用密码登录（方便脚本和远程维护），需要在上一步中用 `ALTER USER` 将认证插件改为 `mysql_native_password`。

</aside>

<aside>
✅

**第 1 课小结**

- 安装的目标不是"看懂所有概念"，而是完成：安装→启动→加固→验证
- `sudo mysql` 能进是因为 Ubuntu 默认 auth_socket；改为密码认证后用 `mysql -u root -p123456` 登录
- 课堂统一密码：`123456`，后续所有账号都用这个密码
</aside>

---

## 第 2 课 配置文件与安全基线：把"边界"和"默认坑"补齐

### 2.1 与上一课的衔接（过渡）

我们已经让 MySQL **能跑起来**。下一步要让它**在正确的边界内运行**：远程访问是否允许、字符集是否正确、时间是否一致。否则会出现：**远程连不上、乱码、时间错位**等常见问题。

### 2.2 本课要解决的问题

- 找到 Ubuntu 24.04 的主配置文件位置
- 完成三件"必改且可验证"的基线配置：**bind-address / utf8mb4 / time_zone**
- 修改后能重启并验证变量生效

### 2.3 配置文件入口与结构

MySQL 配置文件采用 INI 格式。Ubuntu 24.04 的配置文件分散在多个路径，按优先级从高到低排列：

| 路径 | 说明 | 建议 |
| --- | --- | --- |
| `/etc/mysql/my.cnf` | 全局入口，通常只做 `!includedir` | 不要动 |
| `/etc/mysql/mysql.conf.d/mysqld.cnf` | **服务端主配置** | **主要编辑这个文件** |
| `/etc/mysql/conf.d/` | 自定义补充配置（`.cnf` 后缀） | 可新建文件做模块化配置 |
| `~/.my.cnf` | 用户级客户端配置 | 可选，简化个人操作 |

<aside>
📍

**记住这个路径**：`/etc/mysql/mysql.conf.d/mysqld.cnf`

后面所有修改配置的操作都在这个文件里进行。

</aside>

配置文件中有两种配置段：

```ini
[mysqld]      # 服务端配置（mysqld 进程读取）
[client]      # 客户端配置（mysql、mysqldump 等工具读取）
```

<aside>
💬

**分不清 [mysqld] 和 [client]？**

- `[mysqld]` 影响的是"数据库服务进程怎么跑"——端口、绑定地址、日志、字符集等
- `[client]` 影响的是"连接工具怎么连"——默认字符集、默认端口等

写错段不会报错但不会生效，这是新手最常踩的坑。

</aside>

### 2.4 三件必改

#### A. 远程访问边界：bind-address

MySQL 默认只监听 `127.0.0.1`（本机回环），意味着其他机器无法连接。

```ini
[mysqld]
bind-address = 0.0.0.0
port = 3306
```

| 值 | 含义 | 安全性 | 适用场景 |
| --- | --- | --- | --- |
| `127.0.0.1` | 仅本机可连接 | 最高 | 单机开发、不需要远程访问 |
| `0.0.0.0` | 监听所有网卡 | 需配合防火墙 | 内网实验、生产环境 |
| 具体内网 IP | 只监听指定网卡 | 中等 | 多网卡服务器、精细化控制 |

<aside>
⚠️

**安全提示**：`bind-address = 0.0.0.0` 会监听所有网卡。只用于内网实验环境；真实生产必须结合防火墙/安全组，并禁用公网暴露。

</aside>

#### B. 字符集：utf8mb4（避免乱码 / Emoji 问题）

```ini
[mysqld]
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[client]
default-character-set = utf8mb4
```

<aside>
💬

**MySQL 中的 `utf8` ≠ 真正的 UTF-8**

MySQL 的 `utf8` 只支持最多 3 字节的字符（基本多语言平面 BMP），无法存储 Emoji 等 4 字节字符。`utf8mb4` 才是完整的 UTF-8 实现。

**结论**：永远用 `utf8mb4`，忘记 `utf8` 的存在。

</aside>

#### C. 时区：+08:00（避免时间错 8 小时）

```ini
[mysqld]
default-time-zone = '+08:00'
```

<aside>
💬

**为什么时间会错 8 小时？**

MySQL 默认使用 `SYSTEM` 时区（跟随操作系统）。如果 Ubuntu 的时区配置与预期不符，或者应用服务器和数据库服务器时区不一致，就会出现时间偏差。显式指定 `+08:00` 可以避免这类问题。

</aside>

### 2.5 重启与验证

修改配置后**必须重启服务**才能生效：

```bash
sudo systemctl restart mysql
sudo systemctl status mysql --no-pager
```

用 `SHOW VARIABLES` 逐项验证配置是否生效：

```sql
-- 验证绑定地址
SHOW VARIABLES LIKE 'bind_address';

-- 验证字符集
SHOW VARIABLES LIKE 'character_set_server';
SHOW VARIABLES LIKE 'collation_server';

-- 验证时区
SHOW VARIABLES LIKE 'time_zone';
SELECT NOW();
```

<aside>
🔧

**排错提示**：如果 `SHOW VARIABLES` 的值和你配置的不同，检查：

1. 配置是否写在了正确的 `[mysqld]` 段下（不是 `[client]`）
2. 修改后是否重启了 MySQL 服务
3. 是否有多个配置文件覆盖了你的设置（用 `mysqld --verbose --help | grep -A 1 "Default options"` 查看加载顺序）

</aside>

<aside>
✅

**第 2 课小结**

- 三件必改：bind-address（边界）、utf8mb4（编码）、time_zone（时间一致）
- 修改配置后：重启服务 + SHOW VARIABLES 验证生效
- 配置写错段不会报错但不会生效，这是最常见的坑
</aside>

---

## 第 3 课 账号与权限：远程能连，但不用 root（最小权限）

### 3.1 与上一课的衔接（过渡）

我们已经允许 MySQL 监听内网（bind-address），接下来要让宿主机的 Navicat **能连接**，同时遵循数据库安全核心原则：**不用 root，按最小权限创建业务账号**。

### 3.2 本课要解决的问题

- 理解 MySQL 账户识别方式：`'用户名'@'主机'`
- 理解权限系统的四层结构（全局 → 数据库 → 表 → 列）
- 创建一个只允许内网网段连接的用户
- 给用户授予某个数据库范围内的最小权限
- 从宿主机 Navicat 远程登录验证
- 掌握权限变更的生效机制，知道什么时候需要 `FLUSH PRIVILEGES`
- 掌握账号生命周期管理（查看、修改、撤销、删除）

<aside>
🧭

**本课学习顺序**：先识别账号是谁、从哪里来 → 再决定能做什么 → 然后创建账号并授权 → 用 Navicat 验证边界 → 维护账号、理解权限何时生效。

</aside>

### 3.3 账号身份：先看 `'user'@'host'`

在 MySQL 中，账号不是单独的用户名，而是 **用户名 + 来源主机** 的组合：

```sql
'user'@'host'
```

例如：

| 写法 | 含义 | 安全建议 |
| --- | --- | --- |
| `'app'@'localhost'` | 只允许本机连接 | 适合本机脚本或维护任务 |
| `'app'@'192.168.100.1'` | 只允许宿主机这一台机器连接 | 最精确，推荐用于固定客户端 |
| `'app'@'192.168.100.%'` | 允许 192.168.100.x 网段连接 | 适合课堂内网实验 |
| `'app'@'%'` | 允许任何来源连接 | 风险高，生产环境避免使用 |

同一个用户名搭配不同主机，会被视为**不同的账号**。例如 `'app'@'%'` 和 `'app'@'192.168.100.%'` 是两条独立账号记录，密码和权限也可以不同。

<aside>
💬

**为什么远程账号经常连不上？**

很多同学只记住用户名和密码，却忘了 MySQL 还要匹配来源主机。比如你从宿主机 `192.168.100.1` 登录时，如果只创建了 `'app'@'localhost'`，MySQL 会拒绝连接，因为来源主机不匹配。

</aside>

### 3.4 MySQL 权限体系：再看"能做什么"

MySQL 的权限不是"一个用户一个开关"，而是分层逐级检查的：

```
第一层：连接验证
  → 用户名 + 主机名 是否存在？密码对不对？
  → 失败直接拒绝，不进入下一层

第二层：全局权限（mysql.user 表）
  → GRANT ALL ON *.*
  → 超级管理员才给，普通业务账号跳过

第三层：数据库级权限（mysql.db 表）
  → GRANT SELECT ON mydb.*
  → 大多数业务账号授在这一层

第四层：表级 / 列级权限（mysql.tables_priv / mysql.columns_priv）
  → GRANT SELECT ON mydb.orders
  → 更精细的访问控制
```

权限授权时通常按**全局 → 数据库 → 表 → 列**逐步收窄；执行某条 SQL 时，MySQL 会综合匹配这些层级中的权限，只要没有找到可用授权就会拒绝。

<aside>
⚠️

**注意：MySQL 权限没有"显式 DENY"语法。** 如果数据库级授予了某表的 `SELECT`，不能再通过表级权限"拒绝"同一张表。要实现更细粒度控制，应从一开始就只授予需要的表级或列级权限。

</aside>

<aside>
💬

**类比理解**：

把 MySQL 想象成一栋大楼——

- **全局权限** = 大楼门禁卡（能进大楼不代表能进每间办公室）
- **数据库级** = 楼层门禁卡（能进某个楼层的所有房间）
- **表级** = 某间办公室的钥匙
- **列级** = 办公桌抽屉的钥匙

业务账号通常只需要"某个楼层"的权限就够了，不需要"大楼管理员"的万能卡。

</aside>

#### 权限速查表

| 分类 | 权限 | 说明 | 常见场景 |
| --- | --- | --- | --- |
| **数据操作** | `SELECT` | 读取数据 | 只读报表账号 |
| | `INSERT` | 插入数据 | 应用写入 |
| | `UPDATE` | 修改数据 | 应用更新 |
| | `DELETE` | 删除数据 | 应用删除 |
| **结构管理** | `CREATE` | 创建数据库/表 | 开发者 |
| | `ALTER` | 修改表结构 | 开发者 |
| | `DROP` | 删除数据库/表 | **生产环境慎给** |
| | `INDEX` | 创建/删除索引 | 性能优化 |
| **管理权限** | `GRANT OPTION` | 允许该用户授权给别人 | 仅限管理员 |
| | `SUPER` | 管理服务器级操作 | 仅限 DBA |
| | `PROCESS` | 查看所有连接 | 排查问题 |
| | `FILE` | 读写服务器文件 | **高危，不建议给** |

<aside>
⚠️

**高危权限黑名单**：以下权限在教学环境可以了解，但**生产环境绝不应该授予业务账号**：

- `SUPER`：可以修改全局变量、杀死任何连接
- `FILE`：可以读写服务器文件系统
- `GRANT OPTION`：可以把权限再授予别人，导致权限失控
- `ALL PRIVILEGES`：包含以上所有危险权限

</aside>

### 3.5 远程连接三要素（排错顺序）

<aside>
🔧

**从宿主机 Navicat 连不上？按这个顺序查：**

1) MySQL 是否监听 0.0.0.0:3306

```bash
sudo ss -tlnp | grep 3306
```

2) 防火墙是否放通

```bash
sudo ufw status
```

3) 账号 host 是否匹配来源 IP

```sql
SELECT user, host, plugin FROM mysql.user;
```

</aside>

### 3.6 创建数据库与远程账号（完整流程）

> 下面以数据库 `stusta` 为例，账号只允许 `192.168.100.%` 网段连接（覆盖宿主机所在网段）。

在虚拟机中登录 MySQL：

```bash
sudo mysql
```

```sql
-- 0) 降低密码策略（课堂环境必须，否则 123456 无法通过 MEDIUM 策略）
-- 先检查密码验证组件是否已安装
SELECT COMPONENT_ID, COMPONENT_URN FROM mysql.component;
-- 如果没有 component_validate_password 的记录，才执行下面这行安装：
INSTALL COMPONENT 'file://component_validate_password';

SET GLOBAL validate_password.policy = LOW;
SET GLOBAL validate_password.length = 6;

-- 1) 准备示例库和示例表
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

-- 2) 创建远程账号（网段限制，使用 mysql_native_password 确保 Navicat 兼容）
CREATE USER IF NOT EXISTS 'app'@'192.168.100.%' IDENTIFIED WITH mysql_native_password BY '123456';

-- 3) 最小权限授权（只对 stusta.* 的 CRUD）
GRANT SELECT, INSERT, UPDATE, DELETE ON stusta.* TO 'app'@'192.168.100.%';

-- 4) 验证权限
SHOW GRANTS FOR 'app'@'192.168.100.%';
```

<aside>
✅

**这里先用标准授权语句，不直接改系统表**

上面的 `CREATE USER` 和 `GRANT` 属于 MySQL 推荐的账号权限管理语句，执行后权限会自动生效。后面会单独说明：什么时候需要 `FLUSH PRIVILEGES`，什么时候不需要。

</aside>

### 3.7 防火墙（内网实验环境建议）

若启用了 ufw，建议只允许宿主机或内网网段访问 3306，而不是向所有来源开放：

```bash
# 只允许宿主机访问 MySQL（更推荐，把 IP 替换为你宿主机的实际 IP）
sudo ufw allow from 192.168.100.1 to any port 3306 proto tcp

# 或允许整个实验网段访问
sudo ufw allow from 192.168.100.0/24 to any port 3306 proto tcp

sudo ufw status
```

<aside>
💡

**如何确认宿主机 IP？**

在宿主机（Windows）上打开 CMD 或 PowerShell，执行：

```powershell
ipconfig
```

找到与虚拟机同一网段的网卡 IP（通常是 VMware Network Adapter VMnet1 或 VMnet8 对应的 IP）。在虚拟机中也可以用 `ping` 测试连通性。

</aside>

### 3.8 从宿主机 Navicat 远程登录验证

#### Navicat 连接配置

在宿主机打开 Navicat，新建 MySQL 连接，填写以下信息：

| 配置项 | 填写内容 | 说明 |
| --- | --- | --- |
| 连接名 | `MySQL-Lab`（自定义） | 仅用于区分连接 |
| 主机 | `192.168.100.20` | 虚拟机的实际 IP |
| 端口 | `3306` | MySQL 默认端口 |
| 用户名 | `app` | 刚才创建的最小权限账号 |
| 密码 | `123456` | 课堂统一密码 |

点击"测试连接"，成功后保存并双击打开连接。

<aside>
⚠️

**Navicat 连接失败的常见原因**

1. **认证插件不兼容**：如果 Navicat 版本较旧（如 Navicat 12 及以下），可能不支持 `caching_sha2_password`，报错 `2059 - Authentication plugin 'caching_sha2_password' cannot be loaded`。解决方法：

```sql
-- 在虚拟机 MySQL 中降级该账号的认证插件
ALTER USER 'app'@'192.168.100.%' IDENTIFIED WITH mysql_native_password BY '123456';
```

推荐方案是升级 Navicat 到 16+ 版本（原生支持新插件）。

2. **宿主机与虚拟机网络不通**：在宿主机 CMD 中 `ping 192.168.100.20`，确认能通。
3. **防火墙未放通**：回到虚拟机检查 `sudo ufw status`。

</aside>

#### 在 Navicat 中验证权限

连接成功后，在 Navicat 中执行以下验证：

**① 确认能看到授权的数据库**

在左侧数据库列表中，应该能看到 `stusta`，但**不应该**看到 `mysql`、`information_schema` 等系统库。

**② 验证查询操作（应成功）**

双击 `stusta` 数据库 → 双击 `students` 表 → 可以查看数据。

也可以在 Navicat 的查询窗口中执行 SQL：

```sql
-- 确认当前身份
SELECT USER(), CURRENT_USER();

-- 验证查询
SELECT * FROM stusta.students;

-- 验证写入
INSERT INTO stusta.students (name, score) VALUES ('赵六', 85.0);
```

**③ 验证权限边界（应该报错）**

在 Navicat 查询窗口中尝试越权操作：

```sql
-- 以下操作都应该失败
CREATE DATABASE hackdb;         -- ERROR 1044: 权限不足
DROP TABLE stusta.students;     -- ERROR 1142: 权限不足
SELECT * FROM mysql.user;       -- ERROR 1142: 权限不足
```

<aside>
💬

**`USER()` 和 `CURRENT_USER()` 的区别**

- `USER()` 返回"你用谁的名义连上来的"，例如 `'app'@'192.168.100.1'`（宿主机 IP）
- `CURRENT_USER()` 返回"MySQL 实际匹配到的账号记录"，例如 `'app'@'192.168.100.%'`

两者的主机部分可能不同：你从宿主机 `.1` 连接，但匹配到了 `.%` 网段的规则。

</aside>

<aside>
💡

**命令行也能连**

如果想在虚拟机内部用命令行模拟远程登录（或宿主机安装了 MySQL 客户端），同样可以使用：

```bash
mysql -h 192.168.100.20 -u app -p
```

Navicat 只是图形化界面，底层走的仍然是同一个 MySQL 协议。

</aside>

### 3.9 权限变更何时生效：`FLUSH PRIVILEGES` 要不要执行？

很多同学在修改账号权限后会习惯性执行：

```sql
FLUSH PRIVILEGES;
```

这条语句的作用是：**让 MySQL 重新加载权限表，把磁盘中的授权表重新读入内存**。但并不是所有权限修改都需要它。

#### 不需要 `FLUSH PRIVILEGES` 的情况（推荐做法）

只要使用 MySQL 官方账号权限语句，权限会自动刷新并立即生效：

```sql
CREATE USER 'app'@'192.168.100.%' IDENTIFIED BY '123456';
GRANT SELECT ON stusta.* TO 'app'@'192.168.100.%';
REVOKE SELECT ON stusta.* FROM 'app'@'192.168.100.%';
ALTER USER 'app'@'192.168.100.%' IDENTIFIED BY '123456';
DROP USER 'app'@'192.168.100.%';
```

这些语句执行后，MySQL 会自动更新内存中的权限缓存，所以**不用再手动刷新**。

#### 需要 `FLUSH PRIVILEGES` 的情况（不推荐新手这样做）

如果直接修改了系统权限表，例如：

```sql
UPDATE mysql.user SET Host = '192.168.100.%' WHERE User = 'app';
DELETE FROM mysql.user WHERE User = 'olduser';
INSERT INTO mysql.user (...);
```

这类操作绕过了 `CREATE USER` / `GRANT` / `ALTER USER` 等标准语句。MySQL 可能还在使用旧的内存权限缓存，此时才需要：

```sql
FLUSH PRIVILEGES;
```

<aside>
⚠️

**课堂建议**：不要直接 `UPDATE mysql.user`。账号和权限管理优先使用 `CREATE USER`、`ALTER USER`、`GRANT`、`REVOKE`、`DROP USER`。这样语义清晰、风险更低，也通常不需要手动 `FLUSH PRIVILEGES`。

</aside>

#### 一张表记住

| 操作方式 | 是否需要 `FLUSH PRIVILEGES` | 原因 |
| --- | --- | --- |
| `CREATE USER` / `ALTER USER` / `DROP USER` | 不需要 | MySQL 自动刷新权限缓存 |
| `GRANT` / `REVOKE` | 不需要 | MySQL 自动刷新权限缓存 |
| `UPDATE mysql.user` / `DELETE FROM mysql.user` | 需要 | 直接改系统表，需手动让 MySQL 重新加载 |
| `mysql_secure_installation` 最后选择刷新权限表 | 通常选择 Yes | 向导可能修改系统权限表，刷新可确保生效 |

<aside>
💬

**记忆口诀**：

用标准语句，不用 flush；直接改表，必须 flush。

</aside>

### 3.10 账号生命周期管理

账号不是创建完就不管了。安全运维要求对账号进行完整生命周期管理：

#### 查看现有账号

```sql
-- 查看所有账号
SELECT user, host, plugin, account_locked FROM mysql.user;

-- 只看有密码的账号（排除 auth_socket）
SELECT user, host, plugin FROM mysql.user WHERE plugin != 'auth_socket';
```

#### 修改密码

```sql
-- 修改其他用户的密码（推荐方式，MySQL 8.0）
ALTER USER 'app'@'192.168.100.%' IDENTIFIED BY '123456';

-- 修改自己的密码
ALTER USER USER() IDENTIFIED BY '123456';
```

#### 撤销权限

```sql
-- 撤销 DELETE 权限（只保留 SELECT, INSERT, UPDATE）
REVOKE DELETE ON stusta.* FROM 'app'@'192.168.100.%';

-- 验证
SHOW GRANTS FOR 'app'@'192.168.100.%';
```

#### 锁定与解锁账号

```sql
-- 临时锁定账号（禁止登录，但不删除）
ALTER USER 'app'@'192.168.100.%' ACCOUNT LOCK;

-- 解锁
ALTER USER 'app'@'192.168.100.%' ACCOUNT UNLOCK;
```

#### 删除账号

```sql
-- 删除账号（不可逆，先确认没有业务在使用）
DROP USER 'app'@'192.168.100.%';
```

<aside>
⚠️

**删除前先查依赖**：在删除账号前，检查是否有视图、存储过程或定时任务引用了该账号，避免删除后导致业务报错。

</aside>

### 3.11 密码策略与安全加固

MySQL 8.0 内置了密码验证组件 `validate_password`，可以强制密码复杂度。

<aside>
⚠️

**课堂环境必须先降低密码策略**

课堂统一使用 `123456` 作为密码，但 `validate_password` 默认策略为 `MEDIUM`（要求大小写 + 数字 + 特殊字符 + 至少 8 位），`123456` 无法通过。因此需要先降低策略再创建账号：

```sql
-- 先检查密码验证组件是否已安装
SELECT COMPONENT_ID, COMPONENT_URN FROM mysql.component;
-- 如果没有 component_validate_password 的记录，才执行下面这行安装：
INSTALL COMPONENT 'file://component_validate_password';

-- 降低策略为 LOW，允许纯数字短密码
SET GLOBAL validate_password.policy = LOW;
SET GLOBAL validate_password.length = 6;
```

执行以上语句后，后续创建账号时就可以使用 `123456` 了。

</aside>

#### 密码策略参数说明

```sql
-- 查看当前策略
SHOW VARIABLES LIKE 'validate_password%';
```

| 参数 | 含义 | 默认值 | 课堂值 | 生产建议值 |
| --- | --- | --- | --- | --- |
| `validate_password.policy` | 策略等级 | MEDIUM | LOW | MEDIUM |
| `validate_password.length` | 密码最短长度 | 8 | 6 | 8+ |
| `validate_password.mixed_case_count` | 大小写字母最少各几个 | 1 | 0（LOW 模式不检查） | 1 |
| `validate_password.number_count` | 数字最少几个 | 1 | 0（LOW 模式不检查） | 1 |
| `validate_password.special_char_count` | 特殊字符最少几个 | 1 | 0（LOW 模式不检查） | 1 |

策略等级说明：
- `LOW`：只检查长度（课堂环境使用）
- `MEDIUM`：长度 + 大小写 + 数字 + 特殊字符（生产环境推荐）
- `STRONG`：MEDIUM + 字典检查（高安全要求场景）

<aside>
💡

**课堂 vs 生产**

- **课堂**：`policy = LOW`，`length = 6`，密码统一 `123456`，专注学习操作流程
- **生产**：`policy = MEDIUM` 或 `STRONG`，`length ≥ 8`，必须使用强密码

策略的修改是临时生效的（`SET GLOBAL`），重启后恢复默认。如果需要永久生效，在配置文件中添加：

```ini
[mysqld]
validate_password.policy = LOW
validate_password.length = 6
```

</aside>

<aside>
✅

**第 3 课小结**

- 账户身份 = `'user'@'host'`，host 约束"从哪里来"
- 权限分四层：全局 → 数据库 → 表 → 列，授权尽量精确到数据库级
- 远程访问建议：监听边界 + 防火墙边界 + 账号 host 边界 + 最小权限授权
- 标准权限语句会自动生效；直接改 `mysql.user` 等系统表后才需要 `FLUSH PRIVILEGES`
- 账号有完整生命周期：创建 → 授权 → 验证 → 修改 → 锁定 → 删除
- 课堂密码统一 `123456`，创建账号前需先降低 `validate_password` 策略为 LOW
- 生产环境使用 MEDIUM/STRONG 策略，强制密码复杂度
</aside>

---

## 第 4 课 日志：会排错、会定位慢、会恢复（重点：binlog）

### 4.1 与上一课的衔接（过渡）

我们已经实现"远程可用 + 最小权限"。最后要补上安全运维闭环：**出了问题能查、误操作能追溯、必要时能恢复**——这就靠日志。

### 4.2 本课要解决的问题

- 知道四类日志分别在什么场景用
- 能查看错误日志、能开启/查看慢查询日志
- 能开启 binlog，并理解"全量备份 + binlog 回放"的时间点恢复（PITR）思路

### 4.3 四种主要日志（先会选，再会做）

| 日志类型 | 记录内容 | 主要用途 | 性能影响 | 建议 |
| --- | --- | --- | --- | --- |
| **错误日志**（Error Log） | 启动/关闭/运行错误 | 故障排查第一入口 | 无 | 默认开启，必须会看 |
| **通用查询日志**（General Log） | 所有 SQL 语句 | 审计/调试 | 高 | 仅排错时临时开启 |
| **二进制日志**（binlog） | 所有写操作事件 | 复制 + PITR 恢复 | 低-中 | 建议开启（重点） |
| **慢查询日志**（Slow Log） | 超过阈值的 SQL | 性能定位 | 低 | 建议开启（会用即可） |

<aside>
💬

**为什么日志很重要却不能全开？**

通用查询日志会记录每一条 SQL（包括 SELECT），在高并发场景下会产生大量 I/O，严重影响性能。所以它只用于临时排错，排完立即关闭。而 binlog 只记录写操作（INSERT/UPDATE/DELETE/DDL），体积小得多，适合长期开启。

</aside>

### 4.4 错误日志：服务异常先看这里

错误日志是排查 MySQL 故障的**第一入口**。MySQL 启动失败、崩溃、权限错误等都会记录在这里。

```bash
# 查看最近 100 行错误日志
tail -100 /var/log/mysql/error.log

# 实时跟踪（排查启动问题时特别有用）
sudo tail -f /var/log/mysql/error.log
```

```sql
-- 在 MySQL 内查看错误日志路径
SHOW VARIABLES LIKE 'log_error';
```

#### 常见错误日志场景

| 日志关键字 | 含义 | 排查方向 |
| --- | --- | --- |
| `[ERROR] Can't start server` | 服务启动失败 | 检查端口冲突、配置文件语法、磁盘空间 |
| `[ERROR] Access denied` | 认证失败 | 检查用户名/密码/主机权限 |
| `[ERROR] Disk full` | 磁盘满 | 清理日志、扩展磁盘 |
| `[Warning] IP address 'x.x.x.x' could not be resolved` | DNS 反解失败 | 设置 `skip_name_resolve` |

<aside>
🔧

**快速排错步骤**：

1. 先看 `tail -50 /var/log/mysql/error.log`
2. 找到最近的 `[ERROR]` 行
3. 复制错误信息搜索解决方案
4. 如果服务完全启动不了：`sudo systemctl status mysql` 查看 systemd 层面的报错

</aside>

### 4.5 慢查询日志：系统慢了怎么找 SQL

慢查询日志记录执行时间超过阈值的 SQL 语句，是定位"系统为什么慢"的关键工具。

#### 开启与配置

```sql
-- 查看当前状态
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 开启慢查询日志（临时生效，重启后失效）
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 1;   -- 超过 1 秒的 SQL 记录到慢查询日志
SET GLOBAL log_queries_not_using_indexes = 1;  -- 没用索引的也记录
```

```sql
-- 在配置文件中永久生效
-- 编辑 /etc/mysql/mysql.conf.d/mysqld.cnf
-- [mysqld] 段添加：
-- slow_query_log = 1
-- slow_query_log_file = /var/log/mysql/slow.log
-- long_query_time = 1
-- log_queries_not_using_indexes = 1
```

#### 查看慢查询日志

```bash
# 查看慢查询日志
sudo tail -50 /var/log/mysql/slow.log
```

```sql
-- 统计慢查询数量
SHOW GLOBAL STATUS LIKE 'Slow_queries';
```

#### 用 mysqldumpslow 分析

MySQL 自带了慢查询日志分析工具：

```bash
# 按执行次数排序，显示前 10 条
sudo mysqldumpslow -s c -t 10 /var/log/mysql/slow.log

# 按平均执行时间排序
sudo mysqldumpslow -s at -t 10 /var/log/mysql/slow.log

# 按锁定时间排序
sudo mysqldumpslow -s t -t 10 /var/log/mysql/slow.log
```

| 参数 | 含义 |
| --- | --- |
| `-s c` | 按查询次数（count）排序 |
| `-s at` | 按平均查询时间（avg time）排序 |
| `-s t` | 按总锁定时间排序 |
| `-t N` | 只显示前 N 条 |

<aside>
💬

**慢查询日志的实战价值**

假设用户反馈"系统很卡"，排查思路：

1. 查看 `Slow_queries` 数值是否异常增长
2. 用 `mysqldumpslow` 找出最慢的几条 SQL
3. 用 `EXPLAIN` 分析这些 SQL 的执行计划
4. 优化索引或改写 SQL

这个流程是 DBA 日常工作的一部分。

</aside>

### 4.6 通用查询日志：临时排错利器

通用查询日志记录**每一条**到达 MySQL 的 SQL，包括连接、断开、查询。由于日志量巨大，**只在排错时临时开启**。

```sql
-- 查看当前状态
SHOW VARIABLES LIKE 'general_log%';

-- 临时开启（排错时使用）
SET GLOBAL general_log = 1;
SET GLOBAL general_log_file = '/var/log/mysql/general.log';

-- ... 执行需要排查的操作 ...

-- 排查完毕，立即关闭
SET GLOBAL general_log = 0;
```

<aside>
⚠️

**通用查询日志是性能杀手**

在生产环境长期开启通用查询日志，每秒可能产生数 MB 日志，迅速填满磁盘。只用于临时排错，用完即关。

</aside>

### 4.7 Binlog（重点）：开启 + 验证 + PITR 思路

binlog 是 MySQL 最重要的日志之一。它记录了所有**修改数据**的操作（INSERT / UPDATE / DELETE / DDL），用途有两个：

1. **主从复制**：从服务器通过读取主服务器的 binlog 来同步数据（下一章会用到）
2. **数据恢复**：配合全量备份实现时间点恢复（PITR）

#### 开启 binlog

编辑配置文件：

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

在 `[mysqld]` 段添加（或确认存在）：

```ini
[mysqld]
log_bin = /var/lib/mysql/mysql-bin
binlog_format = ROW
server_id = 1
binlog_expire_logs_seconds = 604800
max_binlog_size = 100M
```

| 参数 | 含义 | 建议值 |
| --- | --- | --- |
| `log_bin` | binlog 文件路径前缀 | 保持默认即可 |
| `binlog_format` | 记录格式 | `ROW`（推荐，最安全） |
| `server_id` | 服务器唯一标识 | 单机可随意，主从必须不同 |
| `binlog_expire_logs_seconds` | 自动清理时间，单位秒 | 604800（7 天）- 2592000（30 天） |
| `max_binlog_size` | 单个 binlog 文件最大体积 | 100M-256M |

<aside>
💬

**binlog_format 三种格式的区别**

| 格式 | 记录内容 | 优点 | 缺点 |
| --- | --- | --- | --- |
| `STATEMENT` | 原始 SQL 语句 | 日志体积小 | 某些函数（如 NOW()）在从库执行结果不同 |
| `ROW` | 每行数据变更前后的值 | 最精确、最安全 | 日志体积较大 |
| `MIXED` | 自动选择 | 折中 | 行为不可预测 |

**结论**：生产环境统一用 `ROW`，不需要纠结。

</aside>

重启并验证：

```bash
sudo systemctl restart mysql
```

```sql
-- 验证 binlog 是否开启
SHOW VARIABLES LIKE 'log_bin';             -- 应该是 ON

-- 查看 binlog 格式
SHOW VARIABLES LIKE 'binlog_format';       -- 应该是 ROW

-- 查看所有 binlog 文件
SHOW BINARY LOGS;

-- 查看当前正在写入的 binlog 文件及位置
SHOW BINARY LOG STATUS;
```

#### 查看 binlog 内容

binlog 是二进制格式，不能直接用 `cat` 查看，需要使用 `mysqlbinlog` 工具：

```bash
# 解码查看第一个 binlog 文件的内容
sudo mysqlbinlog --base64-output=DECODE-ROWS -v /var/lib/mysql/mysql-bin.000001 | less
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| `--base64-output=DECODE-ROWS` | 将 base64 编码解码为可读格式 |
| `-v`（或 `--verbose`） | 显示行变更的详细信息（ROW 格式必需） |

按时间范围筛选：

```bash
sudo mysqlbinlog \
  --start-datetime="2026-04-21 08:00:00" \
  --stop-datetime="2026-04-21 10:00:00" \
  /var/lib/mysql/mysql-bin.000001 | less
```

按位置范围筛选（更精确）：

```bash
sudo mysqlbinlog \
  --start-position=154 \
  --stop-position=1024 \
  /var/lib/mysql/mysql-bin.000001 | less
```

<aside>
💬

**按时间 vs 按位置**

- 按时间筛选（`--start-datetime`）：方便但不够精确，同一秒内可能有多条操作
- 按位置筛选（`--start-position`）：精确到每一行，PITR 恢复时推荐用这种方式

**查看 `SHOW BINARY LOG STATUS`** 可以获取当前 binlog 的文件名和位置，记录这个信息可以在恢复时精确定位。

</aside>

#### 时间点恢复（PITR）实战演示

<aside>
🛡️

**PITR（Point-In-Time Recovery）是什么？**

场景：今天上午 10:00 有人误执行了 `DELETE FROM students;`，清空了整张表。你有一个昨晚的全量备份，但恢复备份只能回到昨晚的状态，今天上午的所有正常数据都会丢失。

PITR 的思路：先恢复昨晚的备份 → 再用 binlog "重放"今天 00:00 到 09:59 之间的所有正常操作 → 数据恢复到误操作前一刻。

</aside>

**PITR 三步走**：

```bash
# 第 1 步：恢复全量备份（假设昨晚的 mysqldump 备份）
mysql -u root -p stusta < full_backup_20260420.sql

# 第 2 步：从 binlog 中找到误操作的时间点
# 查看 binlog，定位 DELETE 语句的位置
sudo mysqlbinlog --base64-output=DECODE-ROWS -v /var/lib/mysql/mysql-bin.000002 | grep -B5 "DELETE FROM students"

# 第 3 步：回放 binlog 到误操作前一刻
sudo mysqlbinlog \
  --stop-datetime="2026-04-21 09:59:59" \
  --database=stusta \
  /var/lib/mysql/mysql-bin.000001 \
  /var/lib/mysql/mysql-bin.000002 | mysql -u root -p
```

<aside>
💬

**PITR 操作顺序很重要**

必须先恢复全量备份，再回放 binlog。如果顺序反了（先回放 binlog 再恢复全量备份），全量备份会覆盖掉 binlog 回放的数据，等于白干。

**记忆口诀**：先备后 bin，顺序不能反。

</aside>

#### binlog 管理

```sql
-- 手动切换到新的 binlog 文件（当前文件写满或手动切换）
FLUSH BINARY LOGS;

-- 手动清理 7 天前的 binlog
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 7 DAY);

-- 清理指定文件之前的所有 binlog
PURGE BINARY LOGS TO 'mysql-bin.000005';
```

<aside>
⚠️

**binlog 不清理会怎样？**

binlog 文件会持续增长，直到填满磁盘。MySQL 8.0 建议使用 `binlog_expire_logs_seconds` 设置自动过期时间。在磁盘空间不足时，MySQL 可能无法继续写入，严重时会影响业务。

**建议**：设置 `binlog_expire_logs_seconds = 604800`（7 天，或根据备份策略调整），并定期检查磁盘空间。

</aside>

<aside>
✅

**第 4 课小结**

- **错误日志**：服务异常第一入口，`tail -f /var/log/mysql/error.log`
- **慢查询日志**：会开、会看、会用 `mysqldumpslow` 定位慢 SQL
- **通用查询日志**：临时排错利器，用完即关
- **binlog**：能开启、能验证、能解释 PITR 三步走
- **binlog 管理**：设置自动清理，避免磁盘撑满
</aside>

---

## 项目总结（一张表复盘）

| 课时 | 核心能力 | 验收点（可检查） |
| --- | --- | --- |
| 第 1 课：安装验证 | 装得起来 | 服务 active + `SELECT VERSION()` |
| 第 2 课：配置基线 | 配得安全 | bind-address / utf8mb4 / time_zone 生效 |
| 第 3 课：账号权限 | 管得住人 | 宿主机 Navicat 能用最小权限账号远程登录，且无权执行越权操作 |
| 第 4 课：日志与恢复 | 能追溯/能恢复 | 能查看错误/慢查询；binlog 开启并能解释 PITR 三步走 |

---

## 附录

### 忘记 root 密码：重置方法（Windows / Linux）

<aside>
⚠️

**先判断是不是真的"忘记密码"**

在 Ubuntu apt 安装的 MySQL 中，`root` 常见认证方式是 `auth_socket`。如果下面命令能进入 MySQL，就不需要应急重置：

```bash
sudo mysql
```

进入后直接修改密码即可：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';
```

只有在无法通过任何管理员方式登录时，才使用下面的"初始化文件重置法"。

</aside>

#### 方法一：Linux / Ubuntu 重置 root 密码

思路：停止 MySQL → 准备一条改密 SQL → 用 `--init-file` 临时启动 MySQL → 自动执行改密 → 删除临时文件 → 正常启动服务。

```bash
# 1) 停止 MySQL 服务
sudo systemctl stop mysql

# 2) 创建临时改密文件
sudo nano /tmp/mysql-reset.sql
```

在文件中写入：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';
```

保存后设置权限，并用初始化文件方式启动：

```bash
# 3) 限制临时文件权限
sudo chown mysql:mysql /tmp/mysql-reset.sql
sudo chmod 600 /tmp/mysql-reset.sql

# 4) 临时启动 mysqld，启动时会自动执行改密 SQL
sudo mysqld --user=mysql --init-file=/tmp/mysql-reset.sql --skip-networking &
```

等待几秒后关闭临时 MySQL，再按正常方式启动：

```bash
# 5) 用新密码关闭临时实例
mysqladmin -u root -p shutdown

# 6) 删除临时文件，避免密码泄露
sudo rm -f /tmp/mysql-reset.sql

# 7) 正常启动 MySQL 服务
sudo systemctl start mysql
sudo systemctl status mysql --no-pager
```

验证新密码：

```bash
mysql -u root -p
```

#### 方法二：Windows 重置 root 密码

以下示例以 MySQL 8.0 默认服务名 `MySQL80` 为例。若服务名不同，可在"服务"管理器中查看真实名称。

1. 以管理员身份打开 CMD 或 PowerShell，停止 MySQL 服务：

```powershell
net stop MySQL80
```

2. 创建临时文件 `C:\mysql-reset.sql`，内容如下：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '123456';
```

3. 找到 `mysqld.exe` 所在目录，使用初始化文件临时启动。常见路径示例：

```powershell
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" --init-file=C:\mysql-reset.sql --console --skip-networking
```

看到 MySQL 启动成功后，新开一个管理员 CMD / PowerShell 窗口，测试登录并关闭临时实例：

```powershell
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqladmin.exe" -u root -p shutdown
```

4. 删除临时文件并正常启动服务：

```powershell
del C:\mysql-reset.sql
net start MySQL80
```

<aside>
⚠️

**安全提醒**

- 临时 SQL 文件中包含明文新密码，重置完成后必须删除
- 重置期间建议加 `--skip-networking`，避免网络连接进入临时实例
- 不建议长期使用 `--skip-grant-tables`，它会绕过权限检查，风险更高
- 重置完成后应立即验证登录、记录变更原因，并更换业务系统中相关凭证

</aside>

### 附录 A：MySQL 与 SQL Server 主要差异（对比表）

| 特性 | MySQL | SQL Server |
| --- | --- | --- |
| 许可证 | 开源（GPL）/ 商业双轨 | 商业（微软授权） |
| 运行平台 | Linux、Windows、macOS | 主要 Windows（2017+ 支持 Linux） |
| 主要生态 | LAMP、Web 应用、云原生 | 企业级 Windows 应用 |
| 存储引擎 | 多引擎（InnoDB / MyISAM 等） | 单一引擎 |
| SQL 方言 | 标准 SQL + MySQL 扩展 | T-SQL（Transact-SQL） |
| 价格 | 免费（社区版） | 收费（企业版较贵） |

### 附录 B：安装场景与方法对比（课堂不展开）

| 场景 | 说明 | 推荐安装方式 |
| --- | --- | --- |
| 课程实验 / 个人学习 | VMware 虚拟机中练习 | apt 安装（本项目推荐） |
| Web 项目开发 | 本地或测试服务器 | apt 安装 或 Docker |
| 生产环境部署 | 正式线上服务 | apt / 二进制包 + 加固脚本 |
| 快速验证 / CI 流水线 | 一次性测试环境 | Docker 容器（秒级启停） |
| 高性能调优 | 需要自定义编译参数 | 源码编译安装 |

### 附录 C：MySQL 安装后的目录结构与系统库（速查）

| 路径 | 说明 | 使用场景 |
| --- | --- | --- |
| `/usr/bin/` | 客户端工具（mysql、mysqladmin、mysqldump 等） | 日常操作、备份 |
| `/usr/sbin/mysqld` | MySQL 服务器进程 | 排查进程问题 |
| `/var/lib/mysql/` | 数据目录 | 备份、迁移、磁盘空间排查 |
| `/var/log/mysql/` | 日志目录（错误日志等） | 故障排查 |
| `/etc/mysql/mysql.conf.d/mysqld.cnf` | 主配置文件 | 修改端口、绑定地址、日志等 |

| 数据库 | 说明 | 使用场景 |
| --- | --- | --- |
| mysql | 用户账户、权限、插件配置 | 管理用户权限、排查认证问题 |
| information_schema | 元数据库（只读虚拟库） | 查询表结构、索引信息 |
| performance_schema | 性能监控数据 | 性能调优、慢查询分析 |
| sys | 高级视图 | 快速获取性能摘要 |

### 附录 D：密码管理多方式（旧系统兼容，课堂不作为主线）

- MySQL 8.0 推荐：`ALTER USER ... IDENTIFIED BY ...;`
- `SET PASSWORD ... = PASSWORD()` 为旧语法（8.0 已弃用 PASSWORD()）
- `mysqladmin` 适用于脚本化，但注意密码泄露风险（命令历史/进程列表）
