# 综合实验四 MySQL 性能优化与数据管理实战

🎯 **本实验学习目标**

- 能使用存储过程批量生成测试数据，模拟真实业务量
- 能通过慢查询日志和 `EXPLAIN` 深入分析 SQL 执行计划
- 能设计和验证索引策略（单列索引、复合索引、最左前缀原则）
- 能进行 MySQL 服务器参数调优并编写健康检查脚本
- 能完成数据导入导出全流程（CSV、Excel、SQL 转储）
- 能编写安全审计脚本并完成安全事件应急响应演练

<aside>
🧭

**实验主线**：批量数据生成 → 慢查询分析 → EXPLAIN 深入 → 索引优化 → 参数调优 → 数据导入导出 → 安全审计与应急

本实验将前三个综合实验的性能监控、索引优化和安全审计知识进一步深化，通过七个完整的实战任务，掌握数据库运维从"数据准备 → 性能调优 → 数据管理 → 安全保障"的全流程能力。

</aside>

<aside>
🖥️

**前置条件**

- 已完成综合实验一~三（MySQL 已安装加固、ecommerce 数据库和账号已创建）
- 虚拟机 Ubuntu 24.04 + MySQL 8.0（IP：`192.168.100.20`）
- 宿主机 Windows + Navicat，已能远程连接
- `ecommerce` 数据库中已有 `users`、`products`、`orders` 三张表及示例数据
- 所有密码统一使用 `123456`

**课堂产出**

- 10000 条订单测试数据 + 500 条用户测试数据
- 4 条慢查询的 EXPLAIN 分析对比报告
- 索引优化前后执行计划对比表
- 一份服务器健康检查脚本
- 数据导入导出操作记录
- 一份安全审计报告和应急响应演练记录

</aside>

---

## 实验背景

公司电商系统运行数月后，订单量持续增长。DBA 团队面临三个核心挑战：一是数据库查询性能下降，需要通过大量测试数据定位和优化慢查询；二是数据管理需求增加，需要频繁进行数据导入导出；三是安全团队要求定期进行安全审计和应急演练。你需要在一个实验中系统解决这三个问题。

**环境准备**：先确认 `ecommerce` 数据库和基础数据就绪。

```sql
sudo mysql

USE ecommerce;

-- 确认三张表存在且有数据
SELECT 'users' AS 表名, COUNT(*) AS 行数 FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;

-- 查看表结构
DESCRIBE users;
DESCRIBE products;
DESCRIBE orders;
```

<aside>
💡

**如果 orders 表数据较少（< 100 条），不用担心**。任务一将批量生成 10000 条测试数据，为后续所有优化任务提供足够的数据量。

</aside>

---

## 任务一 批量数据生成（30 分钟）

### 1.1 创建订单数据生成存储过程

使用存储过程批量插入 10000 条订单数据。为了控制事务日志大小，每 1000 条提交一次。

```sql
USE ecommerce;

-- 查看当前 orders 表的行数和结构
SELECT COUNT(*) AS '当前订单数' FROM orders;
DESCRIBE orders;

-- 创建批量数据生成存储过程
DELIMITER //
CREATE PROCEDURE generate_test_data(IN num_rows INT)
BEGIN
    DECLARE i INT DEFAULT 0;
    DECLARE prod_count INT;
    DECLARE user_count INT;

    -- 获取商品总数和用户总数，用于生成随机引用
    SELECT COUNT(*) INTO prod_count FROM products;
    SELECT COUNT(*) INTO user_count FROM users;

    -- 禁用自动提交，提升插入速度
    SET autocommit = 0;

    WHILE i < num_rows DO
        INSERT INTO orders (user_id, product_id, quantity, total_amount, order_status)
        VALUES (
            FLOOR(1 + RAND() * user_count),              -- 随机用户 ID
            FLOOR(1 + RAND() * prod_count),              -- 随机商品 ID
            FLOOR(1 + RAND() * 10),                       -- 数量 1~10
            ROUND(10 + RAND() * 9990, 2),                 -- 金额 10~10000
            FLOOR(RAND() * 4)                              -- 状态 0~3
        );
        SET i = i + 1;

        -- 每 1000 条提交一次，避免事务日志过大
        IF i % 1000 = 0 THEN
            COMMIT;
        END IF;
    END WHILE;

    COMMIT;
    SET autocommit = 1;
END //
DELIMITER ;
```

<aside>
💬

**为什么要分批提交？**

如果一次性在一个事务中插入 10000 条数据，会产生巨大的 undo 日志和 redo 日志，可能撑满磁盘或导致锁等待。每 1000 条提交一次，既能保证一定的批量效率，又能控制日志大小。

</aside>

### 1.2 调用存储过程生成数据

```sql
-- 生成 10000 条测试订单
CALL generate_test_data(10000);

-- 验证数据量
SELECT COUNT(*) AS '订单总数' FROM orders;

-- 查看数据分布示例
SELECT * FROM orders ORDER BY order_id DESC LIMIT 10;
```

### 1.3 创建扩展用户表

为了后续多表 JOIN 测试，额外生成 500 条用户数据。

```sql
-- 创建扩展用户表（复制 users 表结构）
CREATE TABLE IF NOT EXISTS users_expanded LIKE users;

-- 创建用户数据生成存储过程
DELIMITER //
CREATE PROCEDURE generate_users(IN num_rows INT)
BEGIN
    DECLARE i INT DEFAULT 0;
    DECLARE base_id INT;

    -- 获取当前最大 user_id 作为偏移
    SELECT IFNULL(MAX(user_id), 0) INTO base_id FROM users;

    SET autocommit = 0;

    WHILE i < num_rows DO
        INSERT INTO users_expanded (user_id, username, email, phone, password_hash)
        VALUES (
            base_id + i + 1,
            CONCAT('user_', base_id + i + 1),
            CONCAT('user_', base_id + i + 1, '@example.com'),
            CONCAT('138', LPAD(FLOOR(RAND() * 100000000), 8, '0')),
            SHA2(CONCAT('password_', i), 256)
        );
        SET i = i + 1;

        IF i % 500 = 0 THEN
            COMMIT;
        END IF;
    END WHILE;

    COMMIT;
    SET autocommit = 1;
END //
DELIMITER ;

-- 生成 500 条用户数据
CALL generate_users(500);

-- 验证
SELECT COUNT(*) AS '扩展用户总数' FROM users_expanded;
SELECT * FROM users_expanded LIMIT 5;
```

### 1.4 验证数据分布

```sql
-- 订单状态分布（应大致均匀）
SELECT
    order_status AS '订单状态',
    CASE order_status
        WHEN 0 THEN '待付款'
        WHEN 1 THEN '已付款'
        WHEN 2 THEN '已发货'
        WHEN 3 THEN '已完成'
    END AS '状态说明',
    COUNT(*) AS '数量',
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2) AS '占比(%)'
FROM orders
GROUP BY order_status
ORDER BY order_status;

-- 用户下单量分布（前 10 名）
SELECT
    user_id AS '用户ID',
    COUNT(*) AS '订单数',
    SUM(total_amount) AS '总消费金额',
    ROUND(AVG(total_amount), 2) AS '平均订单金额'
FROM orders
GROUP BY user_id
ORDER BY 订单数 DESC
LIMIT 10;

-- 订单金额分布
SELECT
    CASE
        WHEN total_amount < 100 THEN '0-100'
        WHEN total_amount < 500 THEN '100-500'
        WHEN total_amount < 1000 THEN '500-1000'
        WHEN total_amount < 5000 THEN '1000-5000'
        ELSE '5000+'
    END AS '金额区间',
    COUNT(*) AS '订单数',
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2) AS '占比(%)'
FROM orders
GROUP BY 金额区间
ORDER BY MIN(total_amount);
```

<aside>
💬

**数据分布的重要性**

如果数据分布不均匀（比如所有订单状态都是 0），后续测试索引效果时可能出现偏差。随机数据虽然不代表真实业务，但能帮助我们验证索引在不同选择性下的效果。

</aside>

### 1.5 清理存储过程

```sql
-- 生成完数据后清理存储过程（不再需要）
DROP PROCEDURE IF EXISTS generate_test_data;
DROP PROCEDURE IF EXISTS generate_users;
```

<aside>
✅

**检查点 1**：orders 表行数 ≥ 10000、users_expanded 表行数 ≥ 500、数据分布大致均匀。

</aside>

---

## 任务二 慢查询分析（20 分钟）

### 2.1 开启慢查询日志

```sql
-- 查看当前慢查询日志配置
SHOW VARIABLES LIKE 'slow_query_log%';
SHOW VARIABLES LIKE 'long_query_time';
SHOW VARIABLES LIKE 'log_queries_not_using_indexes';

-- 开启慢查询日志（临时生效，重启后失效）
SET GLOBAL slow_query_log = 1;

-- 设置阈值为 1 秒（超过 1 秒的查询记录到日志）
SET GLOBAL long_query_time = 1;

-- 记录未使用索引的查询（即使不慢也记录）
SET GLOBAL log_queries_not_using_indexes = 1;
```

<aside>
⚠️

`SET GLOBAL` 设置的变量在 MySQL 重启后会恢复默认值。如果需要永久生效，需要在 `/etc/mysql/mysql.conf.d/mysqld.cnf` 的 `[mysqld]` 段中添加：

```ini
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1
log_queries_not_using_indexes = 1
```

课堂环境用临时设置即可。

</aside>

### 2.2 执行典型慢查询

以下四条查询分别代表四种常见的性能问题模式：

```sql
-- ========== 慢查询 1：全表扫描 + 排序 ==========
-- 场景：查询最近的订单明细，按金额降序排列
-- 问题：created_at 无索引导致全表扫描，ORDER BY 额外排序
SELECT o.order_id, u.username, p.name AS product_name,
       o.quantity, o.total_amount, o.created_at
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN products p ON o.product_id = p.product_id
WHERE o.created_at >= '2026-01-01'
ORDER BY o.total_amount DESC
LIMIT 100;

-- ========== 慢查询 2：聚合统计 ==========
-- 场景：统计每个用户的订单数和消费总额
-- 问题：GROUP BY 在无索引情况下需要临时表和文件排序
SELECT
    u.username,
    COUNT(o.order_id) AS '订单数',
    SUM(o.total_amount) AS '总消费金额',
    ROUND(AVG(o.total_amount), 2) AS '平均金额'
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.order_status = 1
GROUP BY u.username
ORDER BY 总消费金额 DESC;

-- ========== 慢查询 3：子查询 ==========
-- 圩景：查找特定用户的大额订单
-- 问题：IN 子查询可能导致外层全表扫描
SELECT order_id, user_id, total_amount, created_at
FROM orders
WHERE user_id IN (
    SELECT user_id FROM users WHERE username LIKE 'zhang%'
)
AND total_amount > 100;

-- ========== 慢查询 4：多表 JOIN 无索引 ==========
-- 场景：三表关联查询特定状态的订单
-- 问题：多表 JOIN 中关联字段无索引，导致嵌套循环效率极低
SELECT
    u.username,
    p.name AS product_name,
    p.category,
    o.quantity,
    o.total_amount,
    o.order_status,
    o.created_at
FROM orders o
INNER JOIN users u ON o.user_id = u.user_id
INNER JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 2
ORDER BY o.created_at DESC
LIMIT 50;
```

### 2.3 查看慢查询日志

```bash
# 查看慢查询日志文件位置
sudo mysql -u root -p123456 -e "SHOW VARIABLES LIKE 'slow_query_log_file';"

# 查看最近的慢查询记录
sudo tail -100 /var/log/mysql/slow.log
```

### 2.4 使用 mysqldumpslow 分析

```bash
# 按执行次数排序（找出执行最频繁的慢查询模式）
sudo mysqldumpslow -s c -t 10 /var/log/mysql/slow.log

# 按平均执行时间排序（找出最慢的查询）
sudo mysqldumpslow -s at -t 10 /var/log/mysql/slow.log

# 按扫描行数排序（找出扫描量最大的查询）
sudo mysqldumpslow -s r -t 10 /var/log/mysql/slow.log
```

<aside>
💬

**mysqldumpslow 输出中的关键字段**

| 字段 | 含义 |
| --- | --- |
| `Count` | 该模式的 SQL 执行了多少次 |
| `Time` | 总执行时间 / 平均执行时间 / 最大执行时间 |
| `Lock` | 锁等待时间 |
| `Rows` | 扫描行数 / 发送行数 |

mysqldumpslow 会将参数不同但模式相同的 SQL 归为一类。例如 `WHERE user_id = 1` 和 `WHERE user_id = 2` 会被合并为 `WHERE user_id = N`，这样可以发现真正的性能瓶颈 SQL 模式。

</aside>

### 2.5 查看慢查询计数

```sql
-- 查看慢查询计数（每次执行都会累加）
SHOW GLOBAL STATUS LIKE 'Slow_queries';
```

<aside>
✅

**检查点 2**：慢查询日志已开启，4 条查询已执行，mysqldumpslow 分析结果已记录。

</aside>

---

## 任务三 EXPLAIN 深入分析（30 分钟）

### 3.1 对四条慢查询逐一执行 EXPLAIN

```sql
-- ========== EXPLAIN 慢查询 1 ==========
EXPLAIN
SELECT o.order_id, u.username, p.name AS product_name,
       o.quantity, o.total_amount, o.created_at
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN products p ON o.product_id = p.product_id
WHERE o.created_at >= '2026-01-01'
ORDER BY o.total_amount DESC
LIMIT 100;

-- ========== EXPLAIN 慢查询 2 ==========
EXPLAIN
SELECT
    u.username,
    COUNT(o.order_id) AS '订单数',
    SUM(o.total_amount) AS '总消费金额',
    ROUND(AVG(o.total_amount), 2) AS '平均金额'
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.order_status = 1
GROUP BY u.username
ORDER BY 总消费金额 DESC;

-- ========== EXPLAIN 慢查询 3 ==========
EXPLAIN
SELECT order_id, user_id, total_amount, created_at
FROM orders
WHERE user_id IN (
    SELECT user_id FROM users WHERE username LIKE 'zhang%'
)
AND total_amount > 100;

-- ========== EXPLAIN 慢查询 4 ==========
EXPLAIN
SELECT
    u.username, p.name AS product_name, p.category,
    o.quantity, o.total_amount, o.order_status, o.created_at
FROM orders o
INNER JOIN users u ON o.user_id = u.user_id
INNER JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 2
ORDER BY o.created_at DESC
LIMIT 50;
```

### 3.2 EXPLAIN 核心字段解读

#### type：访问类型（最重要的字段）

`type` 表示 MySQL 如何查找数据，从差到好排列如下：

| type 值 | 含义 | 说明 |
| --- | --- | --- |
| `ALL` | 全表扫描 | 最差！MySQL 从头到尾扫描每一行。数据量大时性能极差 |
| `index` | 全索引扫描 | 扫描整个索引树，比 `ALL` 好一些（索引文件通常比数据文件小） |
| `range` | 索引范围扫描 | 使用索引查找某个范围，如 `WHERE id > 100`、`WHERE created_at >= '2026-01-01'` |
| `ref` | 非唯一索引查找 | 使用非唯一索引精确匹配，可能返回多行。如 `WHERE order_status = 1` |
| `eq_ref` | 唯一索引查找 | 多表 JOIN 中使用主键或唯一索引关联，每行最多匹配一行。性能很好 |
| `const` | 常量查找 | 通过主键或唯一索引查找一个常量值，最多返回一行。最优之一 |
| `system` | 系统表 | 表只有一行数据（系统表），几乎不会遇到 |

<aside>
💡

**优化目标**：至少将 `type` 从 `ALL` 提升到 `range` 或 `ref`。`const` 和 `eq_ref` 在特定场景下才可能达到。

**经验法则**：看到 `ALL` 就要考虑建索引；看到 `index` 也要检查是否可以优化为 `range`。

</aside>

#### key：实际使用的索引

| key 值 | 含义 |
| --- | --- |
| `NULL` | 没有使用任何索引（通常意味着全表扫描） |
| 具体索引名 | 使用了指定的索引，如 `idx_created_at` |

#### rows：预估扫描行数

`rows` 是 MySQL 估算需要扫描的行数。这个数字越小越好。注意这是一个估算值，不一定精确，但数量级有参考意义。

#### Extra：额外信息

| Extra 值 | 含义 | 优化方向 |
| --- | --- | --- |
| `Using filesort` | MySQL 需要额外排序，无法利用索引排序 | 考虑让 ORDER BY 字段走索引 |
| `Using temporary` | 使用临时表（常见于 GROUP BY） | 考虑优化 GROUP BY 的索引 |
| `Using where` | 在存储引擎返回数据后，还需要在 server 层过滤 | 正常现象，但如果 rows 很大则需要优化 |
| `Using index` | 覆盖索引——索引包含查询所需的所有列，不需要回表 | 最佳情况，查询只涉及索引列 |
| `Using index condition` | 索引条件下推（ICP），在存储引擎层就完成了部分过滤 | MySQL 5.6+ 的优化特性，比 `Using where` 好 |

### 3.3 填写 EXPLAIN 分析对比表

<aside>
📝

**课堂任务**：将四条慢查询的 EXPLAIN 结果填入下表。

</aside>

| 查询 | type | key | rows | Extra | 问题分析 |
| --- | --- | --- | --- | --- | --- |
| 慢查询 1 | （填写） | （填写） | （填写） | （填写） | （填写） |
| 慢查询 2 | （填写） | （填写） | （填写） | （填写） | （填写） |
| 慢查询 3 | （填写） | （填写） | （填写） | （填写） | （填写） |
| 慢查询 4 | （填写） | （填写） | （填写） | （填写） | （填写） |

<aside>
💡

**如何解读结果**

- 如果 `type` 是 `ALL` 且 `key` 是 `NULL`：说明完全没有使用索引，需要创建索引
- 如果 `Extra` 出现 `Using filesort`：说明 ORDER BY 没有走索引
- 如果 `Extra` 出现 `Using temporary`：说明 GROUP BY 使用了临时表
- 如果 `rows` 接近 10000：说明几乎扫描了全表

</aside>

### 3.4 使用 EXPLAIN FORMAT=JSON 获取更详细的执行计划

```sql
-- 获取 JSON 格式的执行计划（可查看更详细的成本估算）
EXPLAIN FORMAT=JSON
SELECT o.order_id, u.username, p.name AS product_name,
       o.quantity, o.total_amount, o.created_at
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN products p ON o.product_id = p.product_id
WHERE o.created_at >= '2026-01-01'
ORDER BY o.total_amount DESC
LIMIT 100;
```

<aside>
💬

**JSON 格式的优势**

JSON 输出包含了 `cost_info`（成本估算）和更详细的索引使用情况。普通表格格式看大局，JSON 格式看细节。课堂上以表格格式为主，工作中遇到复杂查询可以用 JSON 格式深入分析。

</aside>

<aside>
✅

**检查点 3**：四条慢查询的 EXPLAIN 结果已记录，对比表已填写，能够口头解释每条查询的性能问题。

</aside>

---

## 任务四 索引优化实战（30 分钟）

### 4.1 查看当前索引

```sql
-- 查看 orders 表的当前索引
SHOW INDEX FROM orders;

-- 查看 users 表的当前索引
SHOW INDEX FROM users;

-- 查看 products 表的当前索引
SHOW INDEX FROM products;
```

<aside>
💬

**索引类型说明**

| 索引类型 | Key_name 特征 | 说明 |
| --- | --- | --- |
| 主键索引 | `PRIMARY` | 自动创建，唯一且非空 |
| 普通索引 | 自定义名称 | 最基本的索引类型 |
| 唯一索引 | 自定义名称，Non_unique=0 | 值必须唯一 |
| 复合索引 | 自定义名称，多行 | 包含多个列的索引 |

</aside>

### 4.2 创建索引

根据任务三的 EXPLAIN 分析结果，为关键字段创建索引：

```sql
-- ========== 索引 1：created_at 单列索引 ==========
-- 解决慢查询 1 和慢查询 4 中 WHERE created_at >= '2026-01-01' 的全表扫描
ALTER TABLE orders ADD INDEX idx_created_at (created_at);

-- ========== 索引 2：order_status + user_id 复合索引 ==========
-- 解决慢查询 2 中 WHERE order_status = 1 + GROUP BY user_id
-- 注意列顺序：等值查询字段在前（order_status），分组/关联字段在后（user_id）
ALTER TABLE orders ADD INDEX idx_status_user (order_status, user_id);

-- ========== 索引 3：total_amount 单列索引 ==========
-- 解决慢查询 4 中 WHERE total_amount BETWEEN 500 AND 1000 的范围查询
ALTER TABLE orders ADD INDEX idx_total_amount (total_amount);

-- 查看创建后的索引列表
SHOW INDEX FROM orders;
```

### 4.3 重新执行 EXPLAIN 对比优化效果

```sql
-- ========== 优化后：慢查询 1 ==========
EXPLAIN
SELECT o.order_id, u.username, p.name AS product_name,
       o.quantity, o.total_amount, o.created_at
FROM orders o
JOIN users u ON o.user_id = u.user_id
JOIN products p ON o.product_id = p.product_id
WHERE o.created_at >= '2026-01-01'
ORDER BY o.total_amount DESC
LIMIT 100;

-- ========== 优化后：慢查询 2 ==========
EXPLAIN
SELECT
    u.username,
    COUNT(o.order_id) AS '订单数',
    SUM(o.total_amount) AS '总消费金额',
    ROUND(AVG(o.total_amount), 2) AS '平均金额'
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.order_status = 1
GROUP BY u.username
ORDER BY 总消费金额 DESC;

-- ========== 优化后：慢查询 3 ==========
EXPLAIN
SELECT order_id, user_id, total_amount, created_at
FROM orders
WHERE user_id IN (
    SELECT user_id FROM users WHERE username LIKE 'zhang%'
)
AND total_amount > 100;

-- ========== 优化后：慢查询 4 ==========
EXPLAIN
SELECT
    u.username, p.name AS product_name, p.category,
    o.quantity, o.total_amount, o.order_status, o.created_at
FROM orders o
INNER JOIN users u ON o.user_id = u.user_id
INNER JOIN products p ON o.product_id = p.product_id
WHERE o.order_status = 2
ORDER BY o.created_at DESC
LIMIT 50;
```

<aside>
📝

**课堂任务**：填写优化前后对比表。

</aside>

| 查询 | 优化前 type | 优化前 key | 优化后 type | 优化后 key | 改善效果 |
| --- | --- | --- | --- | --- | --- |
| 慢查询 1 | ALL | NULL | （填写） | （填写） | （填写） |
| 慢查询 2 | ALL | NULL | （填写） | （填写） | （填写） |
| 慢查询 3 | ALL | NULL | （填写） | （填写） | （填写） |
| 慢查询 4 | ALL | NULL | （填写） | （填写） | （填写） |

### 4.4 复合索引最左前缀原则验证

复合索引 `idx_status_user (order_status, user_id)` 遵循最左前缀原则。我们来验证哪些查询能命中索引：

```sql
-- ========== 场景 1：使用最左列（命中索引） ==========
EXPLAIN SELECT * FROM orders WHERE order_status = 1;
-- 预期：type = ref, key = idx_status_user

-- ========== 场景 2：使用最左列 + 第二列（命中索引） ==========
EXPLAIN SELECT * FROM orders WHERE order_status = 1 AND user_id = 2;
-- 预期：type = ref, key = idx_status_user

-- ========== 场景 3：跳过最左列，只用第二列（不命中索引） ==========
EXPLAIN SELECT * FROM orders WHERE user_id = 2;
-- 预期：type = ALL, key = NULL（因为跳过了最左列 order_status）

-- ========== 场景 4：使用最左列的范围查询（命中索引） ==========
EXPLAIN SELECT * FROM orders WHERE order_status >= 1 AND order_status <= 2;
-- 预期：type = range, key = idx_status_user
```

<aside>
💡

**最左前缀原则**

复合索引 `(A, B, C)` 的查询匹配规则：

| WHERE 条件 | 是否命中索引 | 原因 |
| --- | --- | --- |
| `WHERE A = ?` | 命中 | 使用了最左列 |
| `WHERE A = ? AND B = ?` | 命中 | 使用了最左前缀 |
| `WHERE A = ? AND B = ? AND C = ?` | 完全命中 | 使用了全部列 |
| `WHERE B = ?` | 不命中 | 跳过了最左列 A |
| `WHERE B = ? AND C = ?` | 不命中 | 跳过了最左列 A |
| `WHERE A = ? AND C = ?` | 部分命中 | 只利用了 A 列 |

**口诀**：复合索引像查字典——必须从第一个字开始查，不能跳过中间的字。

</aside>

### 4.5 索引代价分析

索引不是免费的，我们来实测索引对写入操作的影响。

```sql
-- ========== 测试 1：有索引时插入 1000 条数据 ==========
-- 记录开始时间
SET @start_time = NOW(6);

INSERT INTO orders (user_id, product_id, quantity, total_amount, order_status)
SELECT
    FLOOR(1 + RAND() * (SELECT COUNT(*) FROM users_expanded)),
    FLOOR(1 + RAND() * (SELECT COUNT(*) FROM products)),
    FLOOR(1 + RAND() * 10),
    ROUND(10 + RAND() * 9990, 2),
    FLOOR(RAND() * 4)
FROM (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
      UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) a,
     (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
      UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) b,
     (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5
      UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10) c;

SELECT TIMESTAMPDIFF(SECOND, @start_time, NOW(6)) AS '有索引-插入耗时(秒)';

-- ========== 测试 2：删除刚插入的数据 ==========
SET @start_time = NOW(6);
DELETE FROM orders WHERE order_id > (SELECT MAX(order_id) - 1000 FROM orders2_ref);
SELECT TIMESTAMPDIFF(SECOND, @start_time, NOW(6)) AS '有索引-删除耗时(秒)';
```

```sql
-- 查看索引占用空间
SELECT
    index_name AS '索引名',
    seq_in_index AS '列序号',
    column_name AS '列名',
    cardinality AS '基数(区分度)',
    ROUND(index_length / 1024, 2) AS '索引大小(KB)'
FROM information_schema.statistics
WHERE table_schema = 'ecommerce' AND table_name = 'orders'
ORDER BY index_name, seq_in_index;

-- 查看索引总体大小
SELECT
    table_name AS '表名',
    ROUND(data_length / 1024 / 1024, 2) AS '数据大小(MB)',
    ROUND(index_length / 1024 / 1024, 2) AS '索引大小(MB)',
    table_rows AS '估算行数'
FROM information_schema.tables
WHERE table_schema = 'ecommerce' AND table_name = 'orders';
```

<aside>
💬

**索引的代价总结**

| 方面 | 查询（SELECT） | 写入（INSERT/UPDATE/DELETE） |
| --- | --- | --- |
| 有索引 | 快速定位，只扫描少量行 | 每次写操作都要更新所有相关索引 |
| 无索引 | 全表扫描，慢 | 直接写数据，快 |
| 权衡 | 索引越多，查询越快 | 索引越多，写入越慢 |

**经验值**：

- 读多写少的表（如商品表、用户表）：多建索引没关系
- 读写均衡的表（如订单表）：只建必要的索引
- 写多读少的表（如日志表）：尽量少建索引

**口诀**：WHERE 常用建索引，区分度高放前面，频繁更新慎重建。

</aside>

<aside>
✅

**检查点 4**：至少 2 条慢查询的 EXPLAIN 中 `type` 从 `ALL` 提升为 `range` 或 `ref`，最左前缀原则验证完成。

</aside>

---

## 任务五 服务器参数调优（30 分钟）

### 5.1 性能基线采集

```sql
-- ========== 连接相关状态 ==========
SHOW GLOBAL STATUS LIKE 'Threads_connected';     -- 当前连接数
SHOW GLOBAL STATUS LIKE 'Threads_running';        -- 正在执行的线程
SHOW GLOBAL STATUS LIKE 'Connections';            -- 历史总连接数
SHOW GLOBAL STATUS LIKE 'Max_used_connections';   -- 历史最大并发数
SHOW GLOBAL STATUS LIKE 'Aborted_connects';       -- 中断的连接数

-- ========== 核心变量 ==========
SHOW GLOBAL VARIABLES LIKE 'max_connections';           -- 最大连接数
SHOW GLOBAL VARIABLES LIKE 'innodb_buffer_pool_size';   -- 缓冲池大小
SHOW GLOBAL VARIABLES LIKE 'innodb_log_file_size';      -- redo 日志文件大小
SHOW GLOBAL VARIABLES LIKE 'innodb_flush_log_at_trx_commit';  -- 事务刷盘策略
```

### 5.2 innodb_buffer_pool_size 配置

<aside>
💬

**innodb_buffer_pool_size 是什么？**

可以把 `innodb_buffer_pool_size` 理解为 MySQL 的"内存工作台"。当 MySQL 需要读取数据时，会先到缓冲池（Buffer Pool）中找：

- 如果数据在缓冲池中（命中），直接从内存读取，速度极快
- 如果不在（未命中），需要从磁盘读取，速度慢 100 倍以上

因此，缓冲池越大，能缓存的数据越多，命中率越高，查询越快。

</aside>

#### 查看当前缓冲池配置

```sql
-- 查看当前缓冲池大小
SHOW GLOBAL VARIABLES LIKE 'innodb_buffer_pool_size';

-- 查看缓冲池命中率
SELECT
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests') AS '逻辑读次数',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') AS '物理读次数',
    CONCAT(
        ROUND(
            (1 - (
                (SELECT VARIABLE_VALUE FROM performance_schema.global_status
                 WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads')
                /
                NULLIF((SELECT VARIABLE_VALUE FROM performance_schema.global_status
                 WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'), 0)
            )) * 100, 2
        ),
        '%'
    ) AS '缓冲池命中率';
```

#### 计算建议值

```bash
# 在虚拟机中查看物理内存
free -h
```

根据物理内存计算建议值：

| 物理内存 | 建议 innodb_buffer_pool_size | 说明 |
| --- | --- | --- |
| 2 GB | 1 GB（50%） | 留足够内存给 OS 和其他进程 |
| 4 GB | 2~3 GB（50%~70%） | 专用数据库服务器可以给多一些 |
| 8 GB | 4~6 GB（50%~70%） | 同上 |
| 16 GB+ | 10~12 GB（60%~75%） | 比例可以更高 |

<aside>
⚠️

课堂虚拟机环境通常内存有限，不建议修改 `innodb_buffer_pool_size`。本节重点在于理解原理、学会计算建议值和解读命中率。实际生产环境中再进行调整。

</aside>

#### 命中率判断标准

| 命中率 | 评估 | 建议 |
| --- | --- | --- |
| > 99% | 优秀 | 保持当前配置 |
| 95% ~ 99% | 正常 | 可以适当增大缓冲池 |
| < 95% | 需要关注 | 必须增大缓冲池或优化查询 |

### 5.3 连接数管理

```sql
-- 查看当前连接使用率
SELECT
    (SELECT VARIABLE_VALUE FROM performance_schema.global_status
     WHERE VARIABLE_NAME = 'Threads_connected') AS '当前连接数',
    (SELECT VARIABLE_VALUE FROM performance_schema.global_variables
     WHERE VARIABLE_NAME = 'max_connections') AS '最大连接数',
    CONCAT(
        ROUND(
            (SELECT VARIABLE_VALUE FROM performance_schema.global_status
             WHERE VARIABLE_NAME = 'Threads_connected') * 100.0 /
            (SELECT VARIABLE_VALUE FROM performance_schema.global_variables
             WHERE VARIABLE_NAME = 'max_connections'), 2
        ),
        '%'
    ) AS '连接使用率';

-- 查看 Sleep 状态的连接（可能的连接泄漏）
SELECT
    user AS '用户',
    host AS '来源主机',
    db AS '数据库',
    command AS '命令',
    time AS '持续时间(秒)'
FROM information_schema.processlist
WHERE command = 'Sleep' AND time > 300
ORDER BY time DESC;
```

<aside>
💬

**max_connections 的含义**

`max_connections` 定义了 MySQL 允许的最大并发连接数。默认值通常是 151。

- 连接数用完时，新的连接请求会报 `Too many connections` 错误
- 每个连接都会占用一定内存（`thread_stack` + `net_buffer` 等），所以不是越大越好
- 出现大量 Sleep 且持续时间长的连接，可能是应用没有正确关闭连接（连接泄漏）

</aside>

### 5.4 健康检查脚本

将以上各项检查整合为一个完整的健康检查脚本：

```sql
-- ========== MySQL 服务器健康检查脚本 ==========
SELECT '========== MySQL 服务器健康检查 ==========' AS '';
SELECT CONCAT('检查时间：', NOW()) AS '';
SELECT CONCAT('MySQL 版本：', VERSION()) AS '';
SELECT '' AS '';

-- 1. 连接使用率
SELECT '【1】连接使用率' AS '检查项';
SELECT
    CONCAT(Threads_connected, ' / ', max_connections, ' (',
        ROUND(Threads_connected * 100.0 / max_connections, 2), '%)') AS '当前值',
    CASE
        WHEN Threads_connected * 1.0 / max_connections > 0.8
        THEN '警告：连接数超过 80%'
        WHEN Threads_connected * 1.0 / max_connections > 0.5
        THEN '关注：连接数超过 50%'
        ELSE '正常'
    END AS '状态'
FROM (
    SELECT
        (SELECT VARIABLE_VALUE FROM performance_schema.global_status
         WHERE VARIABLE_NAME = 'Threads_connected') AS Threads_connected,
        (SELECT VARIABLE_VALUE FROM performance_schema.global_variables
         WHERE VARIABLE_NAME = 'max_connections') AS max_connections
) t;

-- 2. 慢查询数量
SELECT '【2】慢查询数量' AS '检查项';
SELECT
    VARIABLE_VALUE AS '当前值',
    CASE
        WHEN VARIABLE_VALUE > 100 THEN '警告：慢查询过多，需优化'
        WHEN VARIABLE_VALUE > 50 THEN '关注：慢查询偏多'
        ELSE '正常'
    END AS '状态'
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Slow_queries';

-- 3. 缓冲池命中率
SELECT '【3】缓冲池命中率' AS '检查项';
SELECT
    CONCAT(ROUND(hit_rate * 100, 2), '%') AS '当前值',
    CASE
        WHEN hit_rate > 0.99 THEN '优秀'
        WHEN hit_rate > 0.95 THEN '正常'
        ELSE '警告：命中率低于 95%，考虑增大 innodb_buffer_pool_size'
    END AS '状态'
FROM (
    SELECT
        1 - (
            (SELECT VARIABLE_VALUE FROM performance_schema.global_status
             WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads')
            /
            NULLIF((SELECT VARIABLE_VALUE FROM performance_schema.global_status
             WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests'), 0)
        ) AS hit_rate
) t;

-- 4. 表锁等待
SELECT '【4】表锁等待' AS '检查项';
SELECT
    VARIABLE_VALUE AS '当前值',
    CASE
        WHEN VARIABLE_VALUE > 100 THEN '警告：表锁等待频繁，检查长事务'
        WHEN VARIABLE_VALUE > 0 THEN '关注：存在表锁等待'
        ELSE '正常'
    END AS '状态'
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Table_locks_waited';

-- 5. 中断连接数
SELECT '【5】中断连接数' AS '检查项';
SELECT
    VARIABLE_VALUE AS '当前值',
    CASE
        WHEN VARIABLE_VALUE > 50 THEN '警告：中断连接过多，检查网络或暴力破解'
        WHEN VARIABLE_VALUE > 10 THEN '关注：中断连接偏多'
        ELSE '正常'
    END AS '状态'
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Aborted_connects';

SELECT '========== 健康检查完成 ==========' AS '';
```

<aside>
✅

**检查点 5**：健康检查脚本执行成功，5 项指标结果已记录，能解释每项指标的含义和判断标准。

</aside>

---

## 任务六 数据导入导出全流程（30 分钟）

### 6.1 准备 CSV 数据文件

```bash
# 在虚拟机中创建 CSV 测试文件
cat > /tmp/sample_products.csv << 'EOF'
商品名,分类,价格,库存
"机械键盘","电子配件",599.00,200
"无线鼠标","电子配件",129.00,500
"4K显示器","电子设备",2999.00,100
"USB-C扩展坞","电子配件",259.00,300
"降噪耳机","电子设备",899.00,150
"人体工学椅","办公家具",1599.00,80
"升降桌","办公家具",2399.00,50
"护眼台灯","办公用品",199.00,400
"多屏支架","办公家具",399.00,120
"笔记本散热器","电子配件",89.00,600
"便携投影仪","电子设备",3299.00,60
"智能插座","智能家居",49.00,800
"蓝牙音箱","电子设备",349.00,250
"硬盘柜","存储设备",299.00,180
"固态硬盘1TB","存储设备",499.00,350
EOF

# 查看文件内容
cat /tmp/sample_products.csv

# 确认文件编码（应为 UTF-8）
file -i /tmp/sample_products.csv
```

### 6.2 检查 secure_file_priv

```sql
-- 查看 secure_file_priv 配置（决定 LOAD DATA 的文件路径限制）
SHOW VARIABLES LIKE 'secure_file_priv';
```

<aside>
⚠️

**secure_file_priv 的含义**

| 值 | 含义 |
| --- | --- |
| 空字符串 `''` | 只允许从 MySQL 数据目录导入导出 |
| 特定路径如 `/var/lib/mysql-files/` | 只允许该目录下的文件 |
| `NULL` | 完全禁止 LOAD DATA 和 SELECT ... INTO OUTFILE |

如果值为 `/var/lib/mysql-files/`，需要把 CSV 文件复制到该目录下：

```bash
sudo cp /tmp/sample_products.csv /var/lib/mysql-files/
```

</aside>

### 6.3 使用 LOAD DATA INFILE 导入 CSV

先创建目标表：

```sql
USE ecommerce;

-- 创建与 CSV 对应的导入表
CREATE TABLE IF NOT EXISTS products_imported (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    stock INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

根据 `secure_file_priv` 的值执行导入：

```sql
-- 如果 secure_file_priv = '/var/lib/mysql-files/'（需先复制文件）
-- sudo cp /tmp/sample_products.csv /var/lib/mysql-files/

LOAD DATA INFILE '/tmp/sample_products.csv'
INTO TABLE products_imported
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(name, category, price, stock);

-- 验证导入结果
SELECT COUNT(*) AS '导入行数' FROM products_imported;
SELECT * FROM products_imported;
```

<aside>
💬

**LOAD DATA 参数说明**

| 参数 | 含义 |
| --- | --- |
| `FIELDS TERMINATED BY ','` | 字段以逗号分隔 |
| `ENCLOSED BY '"'` | 字段值用双引号包裹（处理含逗号的值） |
| `LINES TERMINATED BY '\n'` | 每行以换行符结束 |
| `IGNORE 1 ROWS` | 跳过第一行（标题行） |
| `CHARACTER SET utf8mb4` | 指定文件编码为 UTF-8 |
| `(name, category, price, stock)` | 指定列的映射顺序（跳过自增主键） |

`LOAD DATA INFILE` 比逐条 INSERT 快 20~100 倍，是大批量导入数据的首选方案。

</aside>

### 6.4 使用 INSERT ... SELECT 验证

```sql
-- 用另一种方式导入到另一张表，交叉验证数据
CREATE TABLE IF NOT EXISTS products_backup LIKE products_imported;

INSERT INTO products_backup (name, category, price, stock)
SELECT name, category, price, stock FROM products_imported;

-- 对比两张表的行数
SELECT 'products_imported' AS 表名, COUNT(*) AS 行数 FROM products_imported
UNION ALL
SELECT 'products_backup', COUNT(*) FROM products_backup;
```

### 6.5 使用 Navicat 导出数据

在 Navicat 中执行以下导出操作：

#### 导出 CSV

1. 在左侧导航栏中，右键 `ecommerce` → `products_imported` 表
2. 选择 **导出向导**
3. 选择 **CSV 文件（*.csv）**
4. 设置选项：
   - **编码**：UTF-8
   - **包含标题行**：勾选（首行为字段名）
   - **字段分隔符**：逗号
   - **文本限定符**：双引号
5. 选择保存路径（如桌面），点击 **开始**

#### 导出 Excel

1. 右键表 → **导出向导**
2. 选择 **Excel 文件（*.xlsx）**
3. 选择保存路径，点击 **开始**

#### 导出 SQL 转储（结构 + 数据）

1. 右键 `ecommerce` 数据库 → **转储 SQL 文件**
2. 选择 **结构和数据**
3. 选择保存路径

### 6.6 数据完整性验证

```sql
-- 源表行数
SELECT COUNT(*) AS '源表行数' FROM products_imported;
```

<aside>
📝

**课堂任务**：打开导出的 CSV 文件，用文本编辑器统计行数（减去标题行），与源表行数对比。打开导出的 Excel 文件，抽查前 3 行数据是否与数据库一致。

</aside>

### 6.7 常见导入导出问题

<aside>
⚠️

**问题 1：中文乱码**

| 原因 | 解决方案 |
| --- | --- |
| CSV 文件不是 UTF-8 编码 | 用 `file -i 文件名` 检查编码，用 `iconv` 转换 |
| MySQL 表字符集不是 utf8mb4 | `ALTER TABLE ... CONVERT TO CHARACTER SET utf8mb4` |
| LOAD DATA 未指定编码 | 添加 `CHARACTER SET utf8mb4` 子句 |

```bash
# 转换编码（GBK → UTF-8）
iconv -f GBK -t UTF-8 input.csv -o output.csv
```

**问题 2：字段不匹配**

CSV 中的列数或列顺序与表结构不一致。解决方案：在 `LOAD DATA` 中显式指定列映射 `(col1, col2, ...)`，或用 `SET` 跳过自增列。

**问题 3：外键约束导致导入失败**

如果表有外键约束，导入数据的顺序可能影响成功与否。临时解决方案：

```sql
SET FOREIGN_KEY_CHECKS = 0;
-- 执行导入
LOAD DATA INFILE ...
SET FOREIGN_KEY_CHECKS = 1;
```

</aside>

<aside>
✅

**检查点 6**：CSV 数据导入成功（15 行），Navicat 导出 CSV/Excel/SQL 转储完成，数据完整性已验证。

</aside>

---

## 任务七 安全审计与应急响应（50 分钟）

### 7.1 综合安全审计脚本

```sql
-- ========== MySQL 综合安全审计脚本 ==========
-- 执行方式：sudo mysql -u root -p123456 < security_audit.sql

-- 输出审计标题
SELECT '========== MySQL 安全审计报告 ==========' AS '';
SELECT CONCAT('审计时间：', NOW()) AS '';
SELECT CONCAT('MySQL 版本：', VERSION()) AS '';
SELECT '' AS '';

-- ========== 检查 1：匿名用户 ==========
SELECT '【1】匿名用户检查' AS '审计项';
SELECT
    CASE WHEN COUNT(*) = 0 THEN '通过：无匿名用户'
         ELSE CONCAT('风险：发现 ', COUNT(*), ' 个匿名用户 —— ', GROUP_CONCAT(user, '@', host))
    END AS '结果'
FROM mysql.user WHERE user = '';

-- ========== 检查 2：root 远程登录 ==========
SELECT '【2】root 远程登录检查' AS '审计项';
SELECT
    CASE WHEN COUNT(*) = 0 THEN '通过：root 仅限本地登录'
         ELSE CONCAT('风险：root 可从以下主机远程登录：', GROUP_CONCAT(host))
    END AS '结果'
FROM mysql.user WHERE user = 'root' AND host != 'localhost';

-- ========== 检查 3：空密码账号 ==========
SELECT '【3】空密码账号检查' AS '审计项';
SELECT
    CASE WHEN COUNT(*) = 0 THEN '通过：无空密码账号'
         ELSE CONCAT('风险：发现 ', COUNT(*), ' 个空密码账号 —— ',
             GROUP_CONCAT(user, '@', host))
    END AS '结果'
FROM mysql.user
WHERE (authentication_string = '' OR authentication_string IS NULL)
    AND user NOT IN ('mysql.sys', 'mysql.session', 'mysql.infoschema');

-- ========== 检查 4：高危权限 ==========
SELECT '【4】高危权限检查' AS '审计项';
SELECT
    CONCAT('''', user, '''@''', host, '''') AS '拥有高危权限的账号',
    CONCAT(
        IF(Super_priv = 'Y', 'SUPER ', ''),
        IF(File_priv = 'Y', 'FILE ', ''),
        IF(Grant_priv = 'Y', 'GRANT_OPTION ', ''),
        IF(Shutdown_priv = 'Y', 'SHUTDOWN ', '')
    ) AS '危险权限'
FROM mysql.user
WHERE (Super_priv = 'Y' OR File_priv = 'Y' OR Grant_priv = 'Y' OR Shutdown_priv = 'Y')
    AND user NOT IN ('root', 'mysql.sys', 'mysql.session', 'debian-sys-maint');

-- ========== 检查 5：认证失败统计 ==========
SELECT '【5】认证失败统计' AS '审计项';
SELECT
    VARIABLE_VALUE AS '中断连接总数',
    CASE
        WHEN VARIABLE_VALUE > 50 THEN '严重：可能存在暴力破解攻击'
        WHEN VARIABLE_VALUE > 10 THEN '警告：中断连接偏多'
        ELSE '正常'
    END AS '评估'
FROM performance_schema.global_status
WHERE VARIABLE_NAME = 'Aborted_connects';

-- ========== 检查 6：bind-address 配置 ==========
SELECT '【6】bind-address 配置' AS '审计项';
SELECT
    VARIABLE_VALUE AS '当前值',
    CASE
        WHEN VARIABLE_VALUE = '127.0.0.1' THEN 'OK：仅监听本地'
        WHEN VARIABLE_VALUE = '0.0.0.0' THEN '需配合防火墙控制访问'
        ELSE VARIABLE_VALUE
    END AS '评估'
FROM performance_schema.global_variables
WHERE VARIABLE_NAME = 'bind_address';

-- ========== 检查 7：binlog 状态 ==========
SELECT '【7】binlog 状态' AS '审计项';
SELECT
    VARIABLE_VALUE AS '当前值',
    CASE
        WHEN VARIABLE_VALUE = 'ON' THEN 'OK：binlog 已开启，支持数据恢复'
        ELSE '风险：binlog 未开启，无法进行时间点恢复'
    END AS '评估'
FROM performance_schema.global_variables
WHERE VARIABLE_NAME = 'log_bin';

-- ========== 检查 8：权限摘要 ==========
SELECT '【8】各账号权限摘要' AS '审计项';
SELECT
    grantee AS '账号',
    GROUP_CONCAT(DISTINCT privilege_type ORDER BY privilege_type SEPARATOR ', ') AS '权限列表'
FROM information_schema.schema_privileges
WHERE grantee NOT LIKE '%root%'
    AND grantee NOT LIKE '%mysql.%'
    AND grantee NOT LIKE '%sys%'
    AND grantee NOT LIKE '%session%'
    AND grantee NOT LIKE '%infoschema%'
GROUP BY grantee
ORDER BY grantee;

SELECT '========== 审计完成 ==========' AS '';
```

<aside>
💬

**八项安全检查的意义**

| 检查项 | 风险 | 严重程度 |
| --- | --- | --- |
| 匿名用户 | 任何人都可以空用户名连接 | 高 |
| root 远程登录 | 攻击者可以暴力破解 root | 高 |
| 空密码账号 | 无需密码即可登录 | 高 |
| 高危权限 | 可读写服务器文件、关闭数据库 | 高 |
| 认证失败统计 | 暴力破解的直接证据 | 中 |
| bind-address | 网络暴露面评估 | 中 |
| binlog 状态 | 影响数据恢复能力 | 中 |
| 权限摘要 | 审计最小权限原则 | 低 |

</aside>

### 7.2 安全事件模拟

#### 事件 1：暴力破解尝试

```bash
# 在虚拟机终端中执行，模拟暴力破解
for i in $(seq 1 5); do
    echo "=== 第 ${i} 次尝试 ==="
    mysql -u root -pwrong_password 2>&1 | head -1
done

# 用不存在的用户尝试连接
mysql -u hacker -pwrong_password -h 192.168.100.20 2>&1 | head -1
```

#### 事件 2：可疑的越权操作

```sql
-- 先创建一个低权限的 dev_user（如果还没有的话）
CREATE USER IF NOT EXISTS 'dev_user'@'%' IDENTIFIED BY '123456';
GRANT SELECT, INSERT, UPDATE ON ecommerce.* TO 'dev_user'@'%';
FLUSH PRIVILEGES;

-- 在 Navicat 中用 dev_user 连接执行以下操作（预期被拒绝）
-- 以下操作在 dev_user 连接中执行：

-- 尝试读取系统用户表（越权）
SELECT * FROM mysql.user;

-- 尝试读取服务器文件（越权）
SELECT LOAD_FILE('/etc/passwd');

-- 尝试创建数据库（越权）
CREATE DATABASE hacked_db;

-- 尝试修改其他用户的密码（越权）
ALTER USER 'root'@'localhost' IDENTIFIED BY 'hacked';
```

<aside>
⚠️

以上 SQL 需要在 Navicat 中新建一个 `dev_user` 的连接来执行。`dev_user` 只有 `ecommerce` 库的 `SELECT`、`INSERT`、`UPDATE` 权限，所以以上操作都应该被拒绝并记录在错误日志中。

</aside>

#### 事件 3：检测安全事件

```bash
# 查看错误日志中的认证失败记录
sudo grep "Access denied" /var/log/mysql/error.log | tail -20
```

```sql
-- 查看当前所有连接（排除系统内部线程）
SELECT
    id AS '连接ID',
    user AS '用户名',
    host AS '来源主机',
    db AS '数据库',
    command AS '命令',
    time AS '持续秒数',
    LEFT(info, 80) AS 'SQL 语句'
FROM information_schema.processlist
WHERE user NOT IN ('system user', 'event_scheduler')
ORDER BY time DESC;

-- 查看异常的 Sleep 连接（超过 5 分钟未活动）
SELECT
    user, host, db, time AS '持续秒数', command
FROM information_schema.processlist
WHERE command = 'Sleep' AND time > 300;
```

### 7.3 应急响应五步法演练

<aside>
🛡️

**发现安全事件时的标准响应流程**

1. **确认**：确认是否真的是安全事件（排除误报）
2. **止损**：立即采取措施阻止损害扩大
3. **取证**：保留证据用于后续分析
4. **修复**：消除安全隐患
5. **复盘**：总结经验，完善防护

</aside>

#### 第 1 步：确认——发现异常

```sql
-- 发现未知账号
SELECT user, host, plugin, account_locked, created
FROM mysql.user
WHERE user NOT IN (
    'root', 'mysql.sys', 'mysql.session', 'mysql.infoschema',
    'debian-sys-maint', 'dev_user', 'app_ecom'
);
```

假设审计脚本发现了可疑账号 `'suspicious_user'@'%'`。

#### 第 2 步：止损——立即锁定

```sql
-- 锁定可疑账号（先锁定，不删除，保留证据）
ALTER USER 'suspicious_user'@'%' ACCOUNT LOCK;

-- 确认已锁定
SELECT user, host, account_locked
FROM mysql.user WHERE user = 'suspicious_user';
```

#### 第 3 步：取证——收集证据

```sql
-- 查看可疑账号的权限
SHOW GRANTS FOR 'suspicious_user'@'%';

-- 查看该账号是否有活动连接
SELECT * FROM information_schema.processlist WHERE user = 'suspicious_user';

-- 如果有活动连接，记录连接 ID 后结束它
-- KILL <连接ID>;

-- 查看该账号相关的错误日志
-- sudo grep "suspicious_user" /var/log/mysql/error.log
```

```bash
# 在终端中查看错误日志中该账号的登录记录
sudo grep "suspicious_user" /var/log/mysql/error.log | tail -20
```

#### 第 4 步：修复——删除可疑账号

```sql
-- 确认没有业务依赖后删除
DROP USER 'suspicious_user'@'%';

-- 确认已删除
SELECT user, host FROM mysql.user WHERE user = 'suspicious_user';
```

#### 第 5 步：复盘——全量安全检查

```sql
-- 再次执行完整的安全审计脚本
-- 确认没有其他异常

-- 检查是否还有账号权限过大
SELECT user, host FROM mysql.user
WHERE (Super_priv = 'Y' OR File_priv = 'Y')
    AND user NOT IN ('root', 'mysql.sys', 'mysql.session', 'debian-sys-maint');

-- 检查是否有空密码账号
SELECT user, host FROM mysql.user
WHERE (authentication_string = '' OR authentication_string IS NULL)
    AND user NOT IN ('mysql.sys', 'mysql.session', 'mysql.infoschema');

-- 确认防火墙状态
-- sudo ufw status
```

### 7.4 应急响应报告模板

<aside>
📝

**课堂任务**：根据演练过程，完整填写以下应急响应报告。如有模拟事件未发生的内容，可以填写"未发现"或根据假设场景推理填写。

</aside>

| 项目 | 内容 |
| --- | --- |
| **事件编号** | SEC-`______`（自行编号，如 SEC-001） |
| **发现时间** | `______` 年 `______` 月 `______` 日 `______` 时 `______` 分 |
| **事件类型** | `______`（可疑账号入侵 / 暴力破解 / 越权操作） |
| **发现方式** | `______`（安全审计脚本 / 错误日志 / 进程列表） |
| **影响范围** | `______`（涉及的数据库、表、数据量） |
| **第 1 步-确认** | 发现了什么异常？`______` |
| **第 2 步-止损** | 采取了什么措施？`______` |
| **第 3 步-取证** | 获取了什么证据？`______` |
| **第 4 步-修复** | 如何消除隐患？`______` |
| **第 5 步-复盘** | 发现了什么其他问题？`______` |
| **根本原因** | `______` |
| **改进建议** | `______` |

<aside>
✅

**检查点 7**：安全审计脚本执行成功（8 项检查全部完成），暴力破解和越权操作已模拟并检测到，应急响应五步法演练完成，报告已填写。

</aside>

---

## 实验总结

| 任务 | 核心能力 | 关键验证点 |
| --- | --- | --- |
| 任务一：批量数据生成 | 存储过程 + 批量插入 | orders 表 ≥ 10000 行，users_expanded ≥ 500 行 |
| 任务二：慢查询分析 | 慢查询日志 + mysqldumpslow | 4 条慢查询已执行，日志分析完成 |
| 任务三：EXPLAIN 深入 | 执行计划解读 | 四字段（type/key/rows/Extra）分析表已填写 |
| 任务四：索引优化 | 单列索引 + 复合索引 | 至少 2 条查询从 ALL 提升到 range/ref |
| 任务五：参数调优 | 基线采集 + 命中率计算 | 健康检查脚本 5 项指标完成 |
| 任务六：数据导入导出 | LOAD DATA + Navicat 导出 | CSV 导入 15 行，三种格式导出完成 |
| 任务七：安全审计与应急 | 审计脚本 + 五步法响应 | 8 项审计检查 + 完整应急响应演练 |

<aside>
💬

**本实验核心收获**

1. **性能优化闭环**：批量造数据 → 慢查询定位 → EXPLAIN 分析 → 索引优化 → 验证效果
2. **EXPLAIN 四字段是 SQL 优化的核心**：`type` 看访问方式，`key` 看是否用索引，`rows` 看扫描量，`Extra` 看额外开销
3. **复合索引遵循最左前缀原则**：像查字典一样，必须从第一个字开始查
4. **索引是双刃剑**：提升查询速度的同时降低写入速度，需要根据业务场景权衡
5. **innodb_buffer_pool_size 是最重要的性能参数**：命中率 > 99% 是目标
6. **数据导入导出要注意编码一致性**：CSV 用 UTF-8，LOAD DATA 比 INSERT 快 20~100 倍
7. **安全审计要定期执行**：8 项检查是安全基线，不是出了事才做
8. **应急响应五步法**：确认 → 止损 → 取证 → 修复 → 复盘，顺序不能乱

</aside>
