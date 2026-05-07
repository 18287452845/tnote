# 实验三 数据文件说明

本目录存放项目三（数据库维护）所需的所有初始数据文件。

---

## 文件清单

| 文件名 | 用途 | 适用实验 |
| --- | --- | --- |
| `stusta_init.sql` | 初始化脚本：创建 stusta 数据库、3张表、初始数据 | 实验1~实验12 |
| `students.csv` | CSV 测试文件：4条学生记录 | 实验10（BULK INSERT） |

---

## 使用说明

### 1. 执行初始化脚本

**前置条件**：确保 D: 目录已存在（用于存放备份文件）。

```sql
-- 在 SSMS 中连接到 SQL Server（服务器名填 .，选 Windows 身份验证）
-- 打开 stusta_init.sql 并执行（F5 或 Alt+X）

-- 执行顺序：
--   第一部分：创建/重建 stusta 数据库（连接到 master）
--   第二部分：创建 stu / course / score 三张表（自动切换到 stusta）
--   第三部分：插入初始数据
--   第四部分：验证数据（输出各表行数）
```

**初始数据量**：

- `stu` 学生表：10 行
- `course` 课程表：6 行
- `score` 成绩表：30 行

### 2. 使用 CSV 进行 BULK INSERT

将 `students.csv` 复制到 `D:\Data\` 目录（需先新建该文件夹），然后执行实验10的 BULK INSERT 语句。

> 注意：CSV 文件必须保存为 **UTF-8 编码**（用记事本 → 文件 → 另存为 → 编码选 UTF-8），否则中文会乱码。
> 

---

## 表结构参考

```sql
-- stu（学生表）
sno   CHAR(10)      PK  -- 学号
sname NVARCHAR(20)       -- 姓名
gender CHAR(2)           -- 性别（男/女）
age   TINYINT            -- 年龄
dept  NVARCHAR(30)       -- 系别

-- course（课程表）
cno   CHAR(6)       PK  -- 课程号
cname NVARCHAR(50)      -- 课程名
credit TINYINT           -- 学分

-- score（成绩表）
sno   CHAR(10)  FK + PK -- 学号（引用 stu）
cno   CHAR(6)   FK + PK -- 课程号（引用 course）
grade DECIMAL(5,2)       -- 成绩（0~100）
```

---

## 各实验依赖关系

```
执行顺序：
  stusta_init.sql（一次性） → 实验1~12 均可直接使用

CSV 数据文件：
  students.csv → 实验10（BULK INSERT）→ 追加 S001~S004 到 stu 表
```