# 综合实验二 MySQL 备份恢复与灾难恢复综合实战

🎯 **本实验学习目标**

- 能使用 mysqldump 完成全库备份、单库备份和单表备份
- 能模拟多种灾难场景并完成恢复操作
- 能利用 binlog 完成时间点恢复（PITR）
- 能设计并执行完整的备份策略方案

<aside>
🧭

**实验主线**：备份策略设计 → 全量备份 → 灾难场景模拟 → binlog 恢复 → 策略验证

本实验将项目五中的 binlog 知识和项目六中的备份还原操作融合，通过多种真实灾难场景演练，掌握数据恢复的核心能力。

</aside>

<aside>
🖥️

**前置条件**

- 已完成综合实验一（MySQL 已安装、加固、数据库和账号已创建）
- 虚拟机 Ubuntu 24.04 + MySQL 8.0（IP：`192.168.100.20`）
- 宿主机 Windows + Navicat，已能远程连接
- `ecommerce` 数据库中已有 `users`、`products`、`orders` 三张表及示例数据

**课堂产出**

- 完成 3 种备份方式的操作与验证
- 完成 3 种灾难场景的恢复演练
- 一份备份策略方案文档

</aside>

---

## 实验背景

公司电商系统运行一段时间后，管理层意识到数据是核心资产。某天，发生了以下事件：

> 开发人员在调试时误删了 `orders` 表中的所有数据；紧接着，运维工程师发现有人用 DROP 命令删除了 `products` 表。公司需要你制定备份策略并能在各种灾难场景下恢复数据。

---

## 任务一 备份策略设计与准备

### 1.1 理解备份类型

| 备份方式 | 工具 | 特点 | 适用场景 |
| --- | --- | --- | --- |
| 全量逻辑备份 | `mysqldump` | 导出为 SQL 文件，可读性好 | 小中型数据库（< 50GB） |
| 全量物理备份 | `xtrabackup` / 数据文件复制 | 直接复制数据文件，速度快 | 大型数据库（> 50GB） |
| 增量备份 | binlog | 只记录数据变更事件 | 配合全量备份实现 PITR |

### 1.2 创建备份目录

```bash
# 在虚拟机中创建备份目录
sudo mkdir -p /backup/full
sudo mkdir -p /backup/binlog
sudo chown -R ly:ly /backup
```

### 1.3 确认 binlog 已开启

```sql
sudo mysql

-- 确认 binlog 已开启
SHOW VARIABLES LIKE 'log_bin';             -- 应为 ON
SHOW VARIABLES LIKE 'binlog_format';       -- 应为 ROW
SHOW VARIABLES LIKE 'binlog_expire_logs_seconds';  -- 应为 604800

-- 查看当前 binlog 文件和位置
SHOW MASTER STATUS;
```

<aside>
✅

**检查点 1**：binlog 已开启、备份目录已创建、ecommerce 库数据完整。

</aside>

---

## 任务二 执行全量备份

### 2.1 用 mysqldump 备份单个数据库

这是最常用的备份方式——备份指定数据库的结构和数据：

```bash
# 备份 ecommerce 数据库
sudo mysqldump -u root -p123456 \
    --databases ecommerce \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --set-gtid-purged=OFF \
    > /backup/full/ecommerce_full_$(date +%Y%m%d_%H%M%S).sql
```

参数说明：

| 参数                      | 含义                                          |
| ----------------------- | ------------------------------------------- |
| `--databases ecommerce` | 指定备份的数据库，输出中包含 `CREATE DATABASE` 和 `USE` 语句 |
| `--single-transaction`  | InnoDB 一致性快照备份，不锁表（关键参数）                    |
| `--routines`            | 包含存储过程和函数                                   |
| `--triggers`            | 包含触发器                                       |
| `--events`              | 包含定时事件                                      |
| `--set-gtid-purged=OFF` | 不输出 GTID 信息（单机环境推荐）                         |

### 2.2 用 mysqldump 备份所有数据库

```bash
# 备份所有数据库（系统库 + 业务库）
sudo mysqldump -u root -p123456 \
    --all-databases \
    --single-transaction \
    --routines \
    --triggers \
    --events \
    --set-gtid-purged=OFF \
    > /backup/full/all_databases_$(date +%Y%m%d_%H%M%S).sql
```

### 2.3 用 mysqldump 备份单张表

```bash
# 只备份 orders 表
sudo mysqldump -u root -p123456 \
    ecommerce orders \
    --single-transaction \
    --set-gtid-purged=OFF \
    > /backup/full/ecommerce_orders_$(date +%Y%m%d_%H%M%S).sql
```

<aside>
💬

**`--databases` 与不加的区别**

- 加 `--databases ecommerce`：输出文件中包含 `CREATE DATABASE IF NOT EXISTS ecommerce;` 和 `USE ecommerce;`，还原时不需要手动建库
- 不加 `--databases`，只写 `ecommerce`：输出中只有表结构和数据，还原时需要先 `USE ecommerce` 或手动建库

</aside>

### 2.4 查看备份文件内容

```bash
# 查看备份文件头部（前 30 行）
head -30 /backup/full/ecommerce_full_*.sql

# 查看备份文件大小
ls -lh /backup/full/
```

### 2.5 记录备份时的 binlog 位置

```sql
sudo mysql

-- 切换 binlog，让备份后的操作记录到新文件
FLUSH BINARY LOGS;

-- 记录当前 binlog 位置
SHOW MASTER STATUS;
```

输出类似：

```
+------------------+----------+
| File             | Position |
+------------------+----------+
| mysql-bin.000003 |      157 |
+------------------+----------+
```

<aside>
⚠️

**务必记录 File 和 Position！** 这是后续 binlog 恢复的起点。记在记事本中：

- File: `mysql-bin.000003`
- Position: `157`

</aside>

<aside>
✅

**检查点 2**：3 种备份文件均已生成，大小 > 0，binlog 位置已记录。

</aside>

---

## 任务三 灾难场景模拟与恢复

### 场景一 误删表数据（DELETE）——用 binlog 恢复

#### 模拟灾难

```sql
sudo mysql
USE ecommerce;

-- 记录当前数据量
SELECT COUNT(*) AS '恢复前订单数' FROM orders;
SELECT COUNT(*) AS '恢复前用户数' FROM users;

-- 正常业务操作：新增一笔订单
INSERT INTO orders (user_id, product_id, quantity, total_amount, order_status)
VALUES (2, 1, 1, 299.00, 0);

-- 记录这条正常操作的时间
SELECT NOW() AS '正常操作时间';

-- 灾难发生：误删 orders 表所有数据！
DELETE FROM orders;
SELECT COUNT(*) AS '误删后订单数' FROM orders;  -- 结果：0
```

#### 恢复过程

**第 1 步：立即停止业务写入**（课堂模拟中跳过，实际生产必须执行）

**第 2 步：找到误操作在 binlog 中的位置**

```bash
# 查看最新的 binlog 文件
sudo mysql -u root -p123456 -e "SHOW BINARY LOGS;"

# 在 binlog 中搜索 DELETE 操作
sudo mysqlbinlog --base64-output=DECODE-ROWS -v \
    /var/lib/mysql/mysql-bin.000003 | grep -B 5 "DELETE FROM"
```

典型输出如下：

```
# at 316
#260603 10:09:21 server id 1  end_log_pos 382 CRC32 0xc46cad82  Table_map: `ecommerce`.`orders` mapped to number 92
# has_generated_invisible_primary_key=0
# at 382
#260603 10:09:21 server id 1  end_log_pos 525 CRC32 0x3ed3165c  Delete_rows: table id 92 flags: STMT_END_F
### DELETE FROM `ecommerce`.`orders`
```

<aside>
💬

**binlog ROW 格式详解——如何确定 stop-position**

binlog ROW 格式下，一条 SQL 语句（如 `DELETE FROM orders`）会被拆成**多个事件**写入 binlog。以上面的输出为例：

```
# at 316                              ← 事件1：Table_map（标记目标表）
# ... Table_map: `ecommerce`.`orders` ...
# at 382                              ← 事件2：Delete_rows（实际删除的行数据）
# ... Delete_rows: table id 92 ...
### DELETE FROM `ecommerce`.`orders`   ← 被删除的具体行（伪 SQL，仅供阅读）
```

**事件结构说明：**

| 字段 | 含义 |
| --- | --- |
| `# at 316` | 本事件在 binlog 文件中的起始字节位置 |
| `end_log_pos 382` | 本事件结束位置 = 下一个事件的起始位置 |
| `Table_map` | 声明本次操作的目标表（表名 → 内部编号的映射） |
| `Delete_rows` | 包含被删除行的具体数据（ROW 格式的核心） |
| `### DELETE FROM` | `mysqlbinlog -v` 生成的伪 SQL，仅供阅读，不参与回放 |

**关键规则：`# at` 的值就是事件的 position。** `--stop-position=N` 的含义是"回放在位置 N **之前**停止"，即不回放位置 N 处的事件。

**确定 stop-position 的方法：**

1. 用 `grep -B 5 "DELETE FROM"` 找到误操作的位置
2. 找到误操作所属的**第一个事件**（通常是 `Table_map`）的 `# at` 值
3. 这个值就是 `--stop-position`

在上面的例子中，DELETE 操作的事件组从 `# at 316`（Table_map）开始，因此：

- `--stop-position=316` → 回放在 DELETE 事件组**之前**停止，DELETE **不会**被执行 ✅
- `--stop-position=382` → Table_map 事件已被回放，但缺少配对的 Delete_rows，可能导致异常 ❌

**口诀：stop-position 取误操作事件组的第一个 `# at` 值。**

INSERT 和 UPDATE 操作的规则完全相同——找到 `Table_map → Write_rows`（INSERT）或 `Table_map → Update_rows`（UPDATE）事件组的第一个 `# at`，就是 stop-position。

</aside>

```bash
# 更精确地查看该位置附近的内容
sudo mysqlbinlog --base64-output=DECODE-ROWS -v \
    --start-position=157 \
    /var/lib/mysql/mysql-bin.000003 | less
```

找到 INSERT 事件的结束位置和 DELETE 事件的起始位置：

```
# at 380                                     ← INSERT（正常操作）
# at 316                                     ← DELETE 的 Table_map（误操作）← stop-position 用这个
```

**第 3 步：从备份恢复到备份时刻的状态**

```bash
# 先用备份恢复（恢复到备份时的数据状态）
sudo mysql -u root -p123456 < /backup/full/ecommerce_full_*.sql
```

**第 4 步：回放 binlog 到误操作前**

```bash
# 回放 binlog：从备份位置到误操作之前
sudo mysqlbinlog \
    --start-position=157 \
    --stop-position=580 \
    --database=ecommerce \
    /var/lib/mysql/mysql-bin.000003 | sudo mysql -u root -p123456
```

**第 5 步：验证恢复结果**

```sql
sudo mysql
USE ecommerce;

-- 验证数据恢复
SELECT COUNT(*) AS '恢复后订单数' FROM orders;
-- 应包含备份时的数据 + 误删前新增的那笔订单

-- 确认新增的订单已恢复
SELECT * FROM orders ORDER BY order_id DESC LIMIT 3;
```

<aside>
💬

**为什么恢复后多了新增的订单？**

因为 binlog 记录了备份之后的所有写操作。我们回放了从备份位置到误操作之前的所有事件，其中包括那条正常的 INSERT。这就是 PITR 的价值——既恢复了备份时的数据，又保留了备份后的正常操作。

</aside>

---

### 场景二 误删表（DROP TABLE）——用全量备份 + binlog 恢复

#### 模拟灾难

```sql
sudo mysql
USE ecommerce;

-- 先补充一些新数据（模拟备份后的正常业务）
INSERT INTO products (name, category, price, stock) VALUES
    ('蓝牙耳机', '数码配件', 199.00, 80),
    ('充电宝', '数码配件', 129.00, 300);

-- 记录正常数据插入的时间
SELECT NOW() AS '正常操作时间';

-- 灾难发生：误执行了 DROP TABLE！
DROP TABLE products;
```

#### 恢复过程

**第 1 步：确认表已不存在**

```sql
SHOW TABLES LIKE 'products';
-- 预期：空结果集
```

**第 2 步：从备份恢复整个库**

```bash
sudo mysql -u root -p123456 < /backup/full/ecommerce_full_*.sql
```

<aside>
⚠️

**恢复全量备份会覆盖当前数据库的全部数据。** 如果 orders 表在备份后有新的正常数据，需要一并用 binlog 恢复。这正是为什么步骤 3 要回放 binlog。

</aside>

**第 3 步：回放 binlog 恢复备份后的正常操作**

```bash
# 从备份记录的位置开始，回放到 DROP 操作之前
# 假设 DROP 发生在位置 1200
sudo mysqlbinlog \
    --start-position=157 \
    --stop-position=1200 \
    --database=ecommerce \
    /var/lib/mysql/mysql-bin.000003 | sudo mysql -u root -p123456
```

<aside>
💡

**如何确定 DROP 的准确位置？**

```bash
sudo mysqlbinlog --base64-output=DECODE-ROWS -v \
    /var/lib/mysql/mysql-bin.000003 | grep -B 5 "DROP TABLE"
```

输出中 `# at` 后面的数字就是事件起始位置。

</aside>

**第 4 步：验证恢复结果**

```sql
sudo mysql
USE ecommerce;

-- 确认 products 表已恢复
SHOW TABLES;

-- 确认数据完整
SELECT COUNT(*) AS '恢复后商品数' FROM products;
SELECT * FROM products;

-- 确认备份后新增的商品也在
SELECT * FROM products WHERE name IN ('蓝牙耳机', '充电宝');
```

---

### 场景三 误删整个数据库——用全量备份恢复

#### 模拟灾难

```sql
sudo mysql

-- 灾难发生：误删整个数据库
DROP DATABASE ecommerce;

-- 确认数据库已不存在
SHOW DATABASES LIKE 'ecommerce';
-- 预期：空结果集
```

#### 恢复过程

**第 1 步：从备份恢复**

```bash
# 备份文件中包含 CREATE DATABASE 和 USE 语句，直接导入即可
sudo mysql -u root -p123456 < /backup/full/ecommerce_full_*.sql
```

**第 2 步：验证恢复结果**

```sql
sudo mysql

-- 确认数据库已恢复
SHOW DATABASES LIKE 'ecommerce';

USE ecommerce;

-- 确认所有表已恢复
SHOW TABLES;

-- 确认数据完整
SELECT COUNT(*) AS '用户数' FROM users;
SELECT COUNT(*) AS '商品数' FROM products;
SELECT COUNT(*) AS '订单数' FROM orders;

-- 抽样检查数据
SELECT * FROM orders;
```

<aside>
💬

**场景三和场景一二的区别**

场景三中整个库被删除，恢复时直接用包含 `CREATE DATABASE` 的备份文件即可。如果备份时没有加 `--databases` 参数，需要先手动执行 `CREATE DATABASE ecommerce;` 再导入。

</aside>

<aside>
✅

**检查点 3**：三个灾难场景均已成功恢复，数据验证通过。

</aside>

---

## 任务四 Navicat 备份恢复演练

### 4.1 在 Navicat 中备份 ecommerce 数据库

1. 打开 Navicat，连接到虚拟机 MySQL
2. 右键 `ecommerce` 数据库 → **转储 SQL 文件** → **结构和数据**
3. 保存为 `D:\backup\ecommerce_navicat_$(日期).sql`
4. 等待导出完成

### 4.2 在 Navicat 中还原到测试库

1. 右键连接 → **新建数据库** → 名称：`ecommerce_restore_test`，字符集 `utf8mb4`
2. 右键 `ecommerce_restore_test` → **运行 SQL 文件**
3. 选择刚才导出的 `.sql` 文件，执行
4. 刷新数据库，验证表和数据：

```sql
SELECT COUNT(*) FROM ecommerce_restore_test.users;
SELECT COUNT(*) FROM ecommerce_restore_test.products;
SELECT COUNT(*) FROM ecommerce_restore_test.orders;
```

### 4.3 验证备份有效性

<aside>
📝

**核心原则：备份不验证等于没有备份。** 每次备份后都应该还原到测试库验证。

</aside>

| 检查项 | 验证方式 | 预期结果 |
| --- | --- | --- |
| 表结构完整 | `SHOW TABLES;` | 3 张表全部存在 |
| 数据行数一致 | `COUNT(*)` 逐表对比 | 与源库完全一致 |
| 外键约束完整 | `SHOW CREATE TABLE orders;` | 包含 FOREIGN KEY 定义 |
| 数据内容正确 | 抽样查询 | 数据与源库一致 |

---

## 任务五 备份策略方案设计

### 5.1 备份策略设计原则

| 因素 | 考虑点 |
| --- | --- |
| RPO（恢复点目标） | 最多能接受丢失多长时间的数据？ |
| RTO（恢复时间目标） | 从故障到恢复上线，最多允许花多长时间？ |
| 数据量 | 数据量越大，全量备份耗时越长 |
| 业务写入频率 | 写入越频繁，需要越频繁的增量备份 |

### 5.2 推荐备份策略

#### 小型数据库（< 10GB）策略

| 备份类型 | 频率 | 保留时间 | 工具 |
| --- | --- | --- | --- |
| 全量备份 | 每天凌晨 2:00 | 保留 7 天 | `mysqldump` + cron |
| binlog | 持续记录 | 保留 7 天 | MySQL 自动 |

#### 中型数据库（10GB ~ 100GB）策略

| 备份类型 | 频率 | 保留时间 | 工具 |
| --- | --- | --- | --- |
| 全量备份 | 每周日凌晨 2:00 | 保留 4 周 | `mysqldump` / `xtrabackup` |
| 增量（binlog） | 持续记录 | 保留 14 天 | MySQL 自动 |

### 5.3 自动备份脚本示例

```bash
#!/bin/bash
# 文件名：mysql_backup.sh
# 用途：每日自动备份 ecommerce 数据库

# 配置区
BACKUP_DIR="/backup/full"
DB_USER="root"
DB_PASS="123456"
DB_NAME="ecommerce"
DATE=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=7

# 创建备份
sudo mysqldump -u "$DB_USER" -p"$DB_PASS" \
    --databases "$DB_NAME" \
    --single-transaction \
    --routines --triggers --events \
    --set-gtid-purged=OFF \
    > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql"

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "[$(date)] 备份成功：${DB_NAME}_${DATE}.sql" >> /var/log/mysql_backup.log
else
    echo "[$(date)] 备份失败！" >> /var/log/mysql_backup.log
fi

# 清理过期备份
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql" -mtime +$KEEP_DAYS -delete
```

配置定时任务（课堂实操）：

```bash
# 第 1 步：将脚本保存到固定位置
sudo mkdir -p /opt/scripts
sudo nano /opt/scripts/mysql_backup.sh
# 将上面的备份脚本内容粘贴进去，保存退出

# 第 2 步：赋予执行权限
sudo chmod +x /opt/scripts/mysql_backup.sh

# 第 3 步：手动测试一次（确认脚本能正常运行）
sudo /opt/scripts/mysql_backup.sh
ls -lh /backup/full/

# 第 4 步：配置 cron 定时任务
sudo crontab -e
```

在 crontab 编辑器中添加以下内容：

```cron
# 每天凌晨 2:00 自动备份 ecommerce 数据库
0 2 * * * /opt/scripts/mysql_backup.sh >> /var/log/mysql_backup.log 2>&1
```

保存退出后验证 cron 是否生效：

```bash
# 查看当前用户的定时任务列表
sudo crontab -l

# 确认 cron 服务正在运行
sudo systemctl status cron
```

cron 时间格式速查：

| 字段 | 含义 | 取值范围 |
| --- | --- | --- |
| 第 1 个 `0` | 分钟 | 0 ~ 59 |
| 第 2 个 `2` | 小时 | 0 ~ 23 |
| 第 3 个 `*` | 日 | 1 ~ 31 |
| 第 4 个 `*` | 月 | 1 ~ 12 |
| 第 5 个 `*` | 星期 | 0 ~ 7（0 和 7 都是周日） |

常见 cron 示例：

```cron
# 每天凌晨 2 点执行
0 2 * * *

# 每周日凌晨 3 点执行
0 3 * * 0

# 每 6 小时执行一次
0 */6 * * *

# 每月 1 日凌晨 1 点执行
0 1 1 * *
```

<aside>
💬

**课堂任务**：将 cron 时间改为 `*/2 * * * *`（每 2 分钟执行一次），观察备份日志是否有输出，验证后再改回 `0 2 * * *`。这是验证 cron 是否真正生效的最快方法。

</aside>

<aside>
⚠️

**生产环境注意事项**

1. 备份文件不能只放在数据库服务器上，至少要同步到另一台机器或对象存储
2. 定期手动验证备份可还原——自动化备份不能自动化验证是常见管理漏洞
3. 备份脚本中的数据库密码应使用 MySQL 选项文件（`~/.my.cnf`）存储，避免明文暴露在脚本中
4. cron 日志可通过 `grep CRON /var/log/syslog` 查看执行记录

</aside>

---

## 实验总结

| 任务 | 核心能力 | 关键验证点 |
| --- | --- | --- |
| 任务一：备份策略设计 | 理解备份类型与适用场景 | 能说出 RPO 含义 |
| 任务二：全量备份 | mysqldump 三种粒度备份 | 3 个备份文件均已生成并验证 |
| 任务三：灾难恢复 | 三种场景的恢复流程 | 三种场景全部恢复成功 |
| 任务四：Navicat 备份恢复 | 图形化备份还原 | 备份还原验证通过 |
| 任务五：备份策略方案 | 自动化备份方案设计 | 脚本 + cron 可运行 |

<aside>
💬

**本实验核心收获**

1. **备份三要素**：有备份（定期执行）、备份能用（定期验证）、备份能拿到（异地存储）
2. **PITR 的核心步骤**：全量备份恢复 → binlog 回放到误操作前 → 验证
3. **先备后 bin，顺序不能反**：必须先恢复全量备份，再回放 binlog
4. **备份的价值只有在恢复时才能体现**——所以一定要定期演练恢复流程

</aside>
