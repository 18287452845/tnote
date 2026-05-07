# SQL 基础语法讲义

🎯

**本讲目标：** 掌握 SQL 的核心基础语法，能够对数据库进行基本的增、删、改、查操作，为后续数据库安全管理课程打下基础。本讲义以 **SQL Server 2008** 为主要环境，所有示例均可在 SSMS 中直接运行。

🧪

**贯穿实验：校园图书借阅系统**

本讲义以「校园图书借阅系统」为唯一贯穿场景，涵盖三张表：图书表 `books`、读者表 `readers`、借阅记录表 `borrow_records`。**每个语法知识点都直接用这三张表来讲解和演练**，学完即练、边学边做，最终构建一个完整可运行的数据库系统。

---

# 一、SQL 是什么？

SQL（Structured Query Language，结构化查询语言）是用于管理和操作**关系型数据库**的标准语言，几乎所有主流数据库（SQL Server、MySQL、Oracle 等）都支持 SQL。

SQL 语句按功能分为以下几类：

| **分类** | **全称** | **说明** | **常用语句** |
| --- | --- | --- | --- |
| DQL | 数据查询语言 | 查询数据 | `SELECT` |
| DML | 数据操作语言 | 增、删、改数据 | `INSERT` / `UPDATE` / `DELETE` |
| DDL | 数据定义语言 | 定义数据库结构 | `CREATE` / `ALTER` / `DROP` |
| DCL | 数据控制语言 | 权限管理 | `GRANT` / `REVOKE` |

💡

SQL 语句**不区分大小写**，但建议关键字大写、表名/列名小写，以提高可读性。SQL Server 中语句末尾的分号 `;` 可省略（但建议保留，养成良好习惯）。

---

# 二、创建图书借阅系统（DDL）

本章我们直接动手，用 DDL 语句从零搭建「校园图书借阅系统」的数据库结构。

## 2.1 创建数据库

```sql
-- 查看所有数据库
SELECT name FROM sys.databases;

-- 创建图书借阅系统数据库
CREATE DATABASE library;

-- 切换到该数据库
USE library;
```

🔄

**与 MySQL 的区别：**

- MySQL 用 `SHOW DATABASES;` 列出所有数据库；SQL Server 没有此命令，需查询系统视图 `sys.databases`。
- 同理，MySQL 用 `SHOW TABLES;` 查看当前库中的表，SQL Server 改为：

```sql
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';
```

## 2.2 创建图书表 books

我们的第一张表用来存储图书信息。创建表时需要考虑：每列存什么数据、用什么类型、是否允许为空。

```sql
CREATE TABLE books (
    book_id   INT           NOT NULL IDENTITY(1,1),  -- 自增主键
    title     NVARCHAR(100) NOT NULL,                -- 书名（支持中文）
    author    NVARCHAR(50),                          -- 作者
    category  NVARCHAR(30),                          -- 分类（计算机/文学...）
    price     DECIMAL(6,2),                          -- 定价
    stock     INT DEFAULT 5,                         -- 库存数量，默认5
    CONSTRAINT PK_books PRIMARY KEY (book_id)
);
```

💡

**关键语法说明：**

- `IDENTITY(1,1)`：SQL Server 的自增语法，表示从 1 开始、每次加 1。MySQL 用的是 `AUTO_INCREMENT`。
- `NVARCHAR(100)`：支持 Unicode 的可变长字符串，存储中文时不会乱码。推荐用 `NVARCHAR` 代替 `VARCHAR`。
- `DEFAULT 5`：未指定值时自动填入 5。

## 2.3 创建读者表 readers 和借阅记录表 borrow_records

```sql
-- 读者表
CREATE TABLE readers (
    reader_id INT           NOT NULL IDENTITY(1,1),
    name      NVARCHAR(50)  NOT NULL,          -- 姓名
    dept      NVARCHAR(50),                    -- 学院/部门
    phone     VARCHAR(20),                     -- 联系电话
    CONSTRAINT PK_readers PRIMARY KEY (reader_id)
);

-- 借阅记录表
CREATE TABLE borrow_records (
    record_id     INT  NOT NULL IDENTITY(1,1),
    reader_id     INT  NOT NULL,               -- 外键 → readers.reader_id
    book_id       INT  NOT NULL,               -- 外键 → books.book_id
    borrow_date   DATE NOT NULL,               -- 借阅日期
    return_date   DATE,                        -- 应还日期（借期 30 天）
    actual_return DATE,                        -- 实际归还日期（未还则为 NULL）
    CONSTRAINT PK_borrow PRIMARY KEY (record_id)
);
```

✅

**动手验证：** 三张表创建完成后，运行以下语句确认它们都已存在：

```sql
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';
```

还可以用 `EXEC sp_help 'books';` 查看 books 表的详细结构（列名、类型、约束等）。

## 2.4 修改表结构

系统上线后，如果需要调整表结构怎么办？用 `ALTER TABLE`。

以 books 表为例：

```sql
-- 给图书表新增一列「出版社」
ALTER TABLE books ADD publisher NVARCHAR(100);

-- 修改 stock 列的类型为 SMALLINT（节省空间）
ALTER TABLE books ALTER COLUMN stock SMALLINT;

-- 发现出版社列暂时不需要，删掉
ALTER TABLE books DROP COLUMN publisher;
```

🔄

**与 MySQL 的区别：** MySQL 修改列类型用 `MODIFY`；SQL Server 用 `ALTER COLUMN`。

```sql
-- MySQL 写法（SQL Server 不支持）
ALTER TABLE books MODIFY stock SMALLINT;
-- SQL Server 写法
ALTER TABLE books ALTER COLUMN stock SMALLINT;
```

🏋️

**即学即练：** 尝试给 readers 表新增一列 `email NVARCHAR(100)`，然后再删掉它。执行后用 `EXEC sp_columns 'readers';` 验证列的变化。

---

# 三、填充与管理数据（DML）

表结构就绪，接下来用 DML 语句为图书借阅系统填入数据，并学习如何修改和删除。

## 3.1 插入数据 INSERT

```sql
USE library;

-- 插入图书（指定列名，推荐写法）
INSERT INTO books (title, author, category, price, stock) VALUES
(N'SQL Server 数据库管理',   N'王建华', N'计算机', 59.00, 4),
(N'Windows Server 运维实战', N'刘明宇', N'计算机', 75.00, 3),
(N'网络安全攻防实战',        N'陈小洋', N'计算机', 88.00, 2),
(N'百年孤独',                N'余华',   N'文学',   32.00, 6),
(N'三体',                    N'刘慈欣', N'文学',   45.00, 5);

-- 插入读者
INSERT INTO readers (name, dept, phone) VALUES
(N'张伟',   N'计算机学院',   N'13800001111'),
(N'李娜',   N'计算机学院',   N'13800002222'),
(N'王建国', N'信息工程学院', N'13800003333'),
(N'赵明',   N'信息工程学院', N'13800004444');

-- 插入借阅记录
INSERT INTO borrow_records (reader_id, book_id, borrow_date, return_date, actual_return) VALUES
(1, 1, '2026-01-10', '2026-02-09', '2026-02-05'),   -- 张伟借《SQL Server 数据库管理》，已还
(1, 3, '2026-02-01', '2026-03-03', NULL),            -- 张伟借《网络安全攻防实战》，未还
(2, 2, '2026-01-15', '2026-02-14', '2026-02-14'),   -- 李娜借《Windows Server 运维实战》，已还
(3, 5, '2026-02-10', '2026-03-12', NULL),            -- 王建国借《三体》，未还
(4, 1, '2026-02-20', '2026-03-22', NULL);            -- 赵明借《SQL Server 数据库管理》，未还
```

💡

**N 前缀：** 在 SQL Server 中，插入中文等 Unicode 字符时，字符串前需加 `N` 前缀（如 `N'张三'`），告诉 SQL Server 这是 Unicode 字符串，避免中文乱码。使用 `NVARCHAR` 类型的列时尤其重要。

✅

**动手验证：** 插入完成后，分别查询三张表确认数据已正确写入：

```sql
SELECT * FROM books;
SELECT * FROM readers;
SELECT * FROM borrow_records;
```

## 3.2 修改数据 UPDATE

场景：张伟归还了《网络安全攻防实战》，我们需要更新他的借阅记录。

```sql
-- 记录张伟的还书日期
UPDATE borrow_records
SET actual_return = '2026-03-07'
WHERE reader_id = 1 AND book_id = 3;
```

再来一个场景：《三体》涨价了，更新定价：

```sql
UPDATE books
SET price = 49.80
WHERE title = N'三体';
```

⚠️

**警告：** `UPDATE` 和 `DELETE` 语句如果不加 `WHERE` 条件，将会影响表中**所有行**！操作前务必先用 `SELECT` 确认数据范围。

```sql
-- ❌ 危险！这会把所有图书价格都改成 49.80
UPDATE books SET price = 49.80;
-- ✅ 安全！只改指定图书
UPDATE books SET price = 49.80 WHERE title = N'三体';
```

## 3.3 删除数据 DELETE

场景：发现赵明的借阅记录（record_id = 5）录入有误，需要删除。

```sql
-- 先查询确认要删除的记录
SELECT * FROM borrow_records WHERE record_id = 5;

-- 确认无误后删除
DELETE FROM borrow_records WHERE record_id = 5;
```

**DELETE 与 TRUNCATE 的区别：**

```sql
-- 删除所有行（逐行删除，可回滚，保留自增计数）
DELETE FROM borrow_records;

-- 快速清空表（整体删除，效率更高，重置自增计数）
TRUNCATE TABLE borrow_records;
```

🏋️

**即学即练：**

1. 给 readers 表新增一位读者 `(N'孙丽', N'外国语学院', N'13800005555')`
2. 将李娜的联系电话更新为 `N'13900002222'`
3. 查询确认修改结果：`SELECT * FROM readers;`

---

# 四、查询数据（DQL）

查询是 SQL 中**最核心、最常用**的操作。本章所有示例都基于我们已经填好数据的图书借阅系统。

`SELECT` 语句的完整结构：

```sql
SELECT   列名
FROM     表名
WHERE    过滤条件
GROUP BY 分组列
HAVING   分组后过滤
ORDER BY 排序列;
```

> 执行顺序：`FROM` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY`
> 

## 4.1 基础查询

```sql
-- 查询所有图书信息
SELECT * FROM books;

-- 只查书名和价格
SELECT title, price FROM books;

-- 列别名：让输出更易读
SELECT title AS 书名, price AS 定价 FROM books;

-- 去重：查看系统中有哪些图书分类
SELECT DISTINCT category FROM books;
```

## 4.2 条件查询 WHERE

```sql
-- 查询计算机类图书
SELECT * FROM books WHERE category = N'计算机';

-- 查询定价在 40～80 元之间的图书
SELECT title, price FROM books WHERE price BETWEEN 40 AND 80;

-- 查询指定的几本书（集合查询）
SELECT * FROM books WHERE book_id IN (1, 3, 5) AND price BETWEEN 40 AND 80;

-- 模糊查询：书名包含「实战」的图书（% 匹配任意字符）
SELECT title, author FROM books WHERE title LIKE N'实战%';

-- 查找尚未归还的借阅记录（actual_return 为 NULL）
SELECT * FROM borrow_records WHERE actual_return IS NULL;

-- 多条件组合：计算机学院 且 姓名以「张」开头的读者
SELECT * FROM readers WHERE dept = N'计算机学院' AND name LIKE N'张%';
```

🏋️

**即学即练：**

1. 查询库存小于 4 本的图书（需要补购的图书）
2. 查询信息工程学院的所有读者
3. 查询所有已归还的借阅记录（`actual_return IS NOT NULL`）

## 4.3 排序 ORDER BY

```sql
-- 图书按价格升序排列（默认）
SELECT title, price FROM books ORDER BY price;

-- 图书按价格降序排列
SELECT title, price FROM books ORDER BY price DESC;

-- 先按分类排序，同分类内再按价格降序
SELECT title, category, price FROM books ORDER BY category, price DESC;
```

## 4.4 限制返回行数 TOP

```sql
-- 取出定价最高的前 2 本书
SELECT TOP 2 title, price FROM books ORDER BY price DESC;

-- 返回前 50% 的图书
SELECT TOP 50 PERCENT title, price FROM books ORDER BY price DESC;
```

🔄

**与 MySQL 的区别：** MySQL 用 `LIMIT` 放在语句末尾限制行数；SQL Server **没有** `LIMIT`，改用 `TOP` 关键字放在 `SELECT` 之后。

```sql
-- MySQL 写法（SQL Server 不支持）
SELECT * FROM books ORDER BY price DESC LIMIT 2;
-- SQL Server 写法
SELECT TOP 2 * FROM books ORDER BY price DESC;
```

**分页查询：** MySQL 可用 `LIMIT offset, count` 实现分页；SQL Server 2008 需借助 `ROW_NUMBER()` 窗口函数：

```sql
-- 查询第 3～4 本书（第 2 页，每页 2 条）
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (ORDER BY book_id) AS rn
    FROM books
) AS t
WHERE rn BETWEEN 3 AND 4;
```

## 4.5 聚合函数与分组

**常用聚合函数：**

| **函数** | **说明** | **示例** |
| --- | --- | --- |
| `COUNT()` | 计数 | `COUNT(*)` 统计总行数 |
| `SUM()` | 求和 | `SUM(price)` 总价格 |
| `AVG()` | 平均值 | `AVG(price)` 平均定价 |
| `MAX()` | 最大值 | `MAX(price)` 最高价 |
| `MIN()` | 最小值 | `MIN(price)` 最低价 |

直接用图书表来练习聚合与分组：

```sql
-- 统计图书总数
SELECT COUNT(*) AS 图书总数 FROM books;

-- 各分类的图书数量和平均定价
SELECT category AS 分类, COUNT(*) AS 图书数量, AVG(price) AS 平均定价
FROM books
GROUP BY category;

-- 只显示平均定价超过 50 元的分类（HAVING 筛选分组后的结果）
SELECT category AS 分类, AVG(price) AS 平均定价
FROM books
GROUP BY category
HAVING AVG(price) > 50;
```

🏋️

**即学即练：**

1. 查询图书的最高价和最低价
2. 统计每位读者的借阅次数（提示：对 `borrow_records` 按 `reader_id` 分组）
3. 找出借阅次数大于 1 的读者编号（用 `HAVING`）

---

# 五、多表联合查询（JOIN）

前面的查询都是单表操作。但在借阅系统中，借阅记录只存了 `reader_id` 和 `book_id`，看不到读者姓名和书名——这时就需要 `JOIN` 把多张表关联起来。

## 5.1 内连接 INNER JOIN

只返回两表中**都有匹配**的行。

**场景：查询所有借阅明细（显示读者姓名、书名、日期）**

```sql
SELECT r.name         AS 读者,
       b.title        AS 书名,
       br.borrow_date AS 借阅日期,
       br.return_date AS 应还日期,
       br.actual_return AS 实际归还日期
FROM borrow_records br
INNER JOIN readers r ON br.reader_id = r.reader_id
INNER JOIN books   b ON br.book_id   = b.book_id;
```

**场景：只查尚未归还的借阅记录**

```sql
SELECT r.name AS 读者, b.title AS 书名, br.return_date AS 应还日期
FROM borrow_records br
INNER JOIN readers r ON br.reader_id = r.reader_id
INNER JOIN books   b ON br.book_id   = b.book_id
WHERE br.actual_return IS NULL;
```

💡

**表别名：** `borrow_records br` 中的 `br` 是表别名，用于简化多表查询中的列引用。`br.reader_id` 比 `borrow_records.reader_id` 更简洁。

## 5.2 左连接 LEFT JOIN

返回左表所有行，右表无匹配则填 `NULL`。

**场景：查看所有读者及其借阅情况（包括从未借过书的读者）**

```sql
SELECT r.name AS 读者, b.title AS 借阅书名
FROM readers r
LEFT JOIN borrow_records br ON r.reader_id = br.reader_id
LEFT JOIN books          b  ON br.book_id  = b.book_id;
```

如果某位读者从未借过书，其「借阅书名」列会显示 `NULL`——这正是 LEFT JOIN 的作用，保证左表（readers）的数据不丢失。

**场景：统计每位读者的借阅次数（含从未借过书的读者，显示 0 次）**

```sql
SELECT r.name AS 读者, COUNT(br.record_id) AS 借阅次数
FROM readers r
LEFT JOIN borrow_records br ON r.reader_id = br.reader_id
GROUP BY r.reader_id, r.name
ORDER BY 借阅次数 DESC;
```

🏋️

**即学即练：**

1. 用 INNER JOIN 查询所有已归还图书的读者姓名、书名和实际归还日期
2. 用 LEFT JOIN 找出所有图书及其被借阅的次数（包括从未被借出的图书，显示 0 次）
3. 思考：如果用 INNER JOIN 替代上面的 LEFT JOIN，结果会有什么不同？

---

# 六、常用内置函数

## 6.1 字符串函数

用图书数据来演示常见字符串操作：

```sql
-- 查询书名的字符个数
SELECT title, LEN(title) AS 书名字数 FROM books;

-- 拼接显示「作者: 书名」格式
SELECT author + N': ' + title AS 图书信息 FROM books;

-- 书名转大写（英文部分）
SELECT UPPER(title) FROM books;

-- 截取书名前 4 个字符
SELECT title, SUBSTRING(title, 1, 4) AS 书名前缀 FROM books;

-- 把分类中的「计算机」替换为「IT」
SELECT title, REPLACE(category, N'计算机', N'IT') AS 新分类 FROM books;
```

🔄

**与 MySQL 的区别（字符串函数）：**

| **功能** | **MySQL** | **SQL Server 2008** |
| --- | --- | --- |
| 字符串长度 | `LENGTH()` | `LEN()` |
| 字符串拼接 | `CONCAT('a','b')` | `'a' + 'b'`（用 `+` 运算符，2008 无 `CONCAT`） |
| 去除首尾空格 | `TRIM()` | `LTRIM(RTRIM())`（需嵌套两个函数） |

注意：`CONCAT()` 函数从 **SQL Server 2012** 起才支持，2008 中必须用 `+` 拼接。

## 6.2 数值函数

```sql
-- 将图书价格四舍五入到整数
SELECT title, price, ROUND(price, 0) AS 取整价格 FROM books;

-- 向下取整 / 向上取整
SELECT FLOOR(59.80) AS 向下取整, CEILING(59.80) AS 向上取整;

-- 绝对值（计算价格差可能用到）
SELECT ABS(32.00 - 88.00) AS 价格差;
```

🔄

**与 MySQL 的区别：** MySQL 向上取整用 `CEIL()`；SQL Server 用 `CEILING()`（多一个字母）。

## 6.3 日期函数

日期函数在借阅系统中特别实用——计算借期、判断超期都要用到。

```sql
-- 当前日期时间
SELECT GETDATE();

-- 只取日期部分
SELECT CAST(GETDATE() AS DATE);

-- 查询每笔借阅的年份和月份
SELECT b.title,
       YEAR(br.borrow_date) AS 借阅年,
       MONTH(br.borrow_date) AS 借阅月
FROM borrow_records br
INNER JOIN books b ON br.book_id = b.book_id;

-- 🔑 核心应用：计算未归还图书的超期天数
SELECT r.name    AS 读者,
       b.title   AS 书名,
       br.return_date AS 应还日期,
       DATEDIFF(day, br.return_date, CAST(GETDATE() AS DATE)) AS 超期天数
FROM borrow_records br
INNER JOIN readers r ON br.reader_id = r.reader_id
INNER JOIN books   b ON br.book_id   = b.book_id
WHERE br.actual_return IS NULL
  AND br.return_date < CAST(GETDATE() AS DATE);

-- 给借阅日期加 30 天算出应还日期
SELECT borrow_date,
       DATEADD(day, 30, borrow_date) AS 计算应还日期
FROM borrow_records;
```

🔄

**与 MySQL 的区别（日期函数）：**

| **功能** | **MySQL** | **SQL Server 2008** |
| --- | --- | --- |
| 当前日期时间 | `NOW()` | `GETDATE()` |
| 当前日期 | `CURDATE()` | `CAST(GETDATE() AS DATE)` |
| 日期差 | `DATEDIFF(date1, date2)`（结果为天数） | `DATEDIFF(day, start, end)`（需指定单位：day/month/year） |

🏋️

**即学即练：**

1. 用字符串拼接输出格式为「[计算机] SQL Server 数据库管理 — 59.00元」的图书信息
2. 查询所有 2026 年 2 月借出的图书记录（提示：用 `YEAR()` 和 `MONTH()` 组合筛选）
3. 计算每笔已还图书的实际借阅天数（`DATEDIFF(day, borrow_date, actual_return)`）

---

# 七、子查询

子查询是嵌套在另一条 SQL 语句中的查询，可以解决「查询中需要依赖另一个查询结果」的问题。

**场景 1：找出定价最高的图书是谁借的**

```sql
-- 先想：定价最高的书是哪本？
SELECT TOP 1 book_id FROM books ORDER BY price DESC;

-- 子查询：一步到位，找出借阅过定价最高图书的读者
SELECT DISTINCT r.name AS 读者
FROM readers r
WHERE r.reader_id IN (
    SELECT br.reader_id
    FROM borrow_records br
    WHERE br.book_id = (
        SELECT TOP 1 book_id FROM books ORDER BY price DESC
    )
);
```

**场景 2：找出借阅次数高于平均值的读者**

```sql
SELECT r.name AS 读者, COUNT(*) AS 借阅次数
FROM borrow_records br
INNER JOIN readers r ON br.reader_id = r.reader_id
GROUP BY r.reader_id, r.name
HAVING COUNT(*) > (
    SELECT AVG(cnt) FROM (
        SELECT COUNT(*) AS cnt
        FROM borrow_records
        GROUP BY reader_id
    ) AS sub
);
```

**场景 3：找出从未借过任何书的读者**

```sql
SELECT name AS 未借阅读者
FROM readers
WHERE reader_id NOT IN (
    SELECT DISTINCT reader_id FROM borrow_records
);
```

🏋️

**即学即练：**

1. 用子查询找出价格高于所有图书平均价格的图书
2. 查询与「张伟」借过同一本书的其他读者姓名（提示：先子查询张伟借过的 book_id 集合）

---

# 八、SQL Server 常用系统对象速查

📋

SQL Server 通过**系统视图**和**系统存储过程**提供数据库元数据，以下是常用查询：

```sql
-- 查看所有数据库
SELECT name FROM sys.databases;

-- 查看当前库中所有用户表
SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE = 'BASE TABLE';

-- 查看表的列信息（以 books 表为例）
SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'books';

-- 查看所有登录名
SELECT name, type_desc FROM sys.server_principals
WHERE type IN ('S','U');

-- 查看当前使用的数据库
SELECT DB_NAME();

-- 查看当前登录用户
SELECT SYSTEM_USER;
```

---

# 九、综合练习题

📌

以下练习使用一张全新的 `employees` 表，目的是检验你能否将前面学到的 SQL 技能**迁移到新场景**。先执行建表和插入语句，再独立完成查询任务。

```sql
CREATE TABLE employees (
    id         INT PRIMARY KEY IDENTITY(1,1),
    name       NVARCHAR(50),
    dept       NVARCHAR(50),
    salary     DECIMAL(8,2),
    hire_date  DATE
);

INSERT INTO employees (name, dept, salary, hire_date) VALUES
(N'Alice',  N'研发部', 12000, '2020-03-15'),
(N'Bob',    N'销售部',  8000, '2019-07-01'),
(N'Carol',  N'研发部', 15000, '2018-11-20'),
(N'David',  N'销售部',  9500, '2021-01-10'),
(N'Eve',    N'人事部',  7000, '2022-06-30'),
(N'Frank',  N'研发部', 11000, '2020-08-08');
```

- [ ]  查询所有员工的姓名和薪资，按薪资从高到低排列
- [ ]  查询研发部工资高于 11000 的员工
- [ ]  统计每个部门的人数和平均薪资，只显示平均薪资 > 9000 的部门
- [ ]  查询薪资高于公司平均薪资的员工姓名（用子查询）
- [ ]  将销售部所有员工薪资提高 10%
- [ ]  查询薪资最高的前 3 名员工（用 `TOP` 实现）
- [ ]  查询入职日期距今超过 1000 天的员工（用 `DATEDIFF` 实现）

---

📌

**学习建议：** SQL 语法不难，关键在于**多动手实践**。本讲义的每个知识点都配有基于图书借阅系统的即时练习，建议在 SSMS 中跟着敲完每一条 SQL 后，再独立完成蓝色的「🏋️ 即学即练」部分，最后挑战第九章的综合练习题。遇到报错不要慌，仔细阅读错误信息，大多数都能快速定位问题。注意本讲义中标注”🔄 与 MySQL 的区别”的部分，这些是 SQL Server 与其他数据库最容易混淆的地方。