-- ============================================================
-- 项目五 第4课 课堂演示脚本（教师按步骤执行）
-- 前置条件：已执行 05_log_data_prepare.sql 完成数据准备
-- ============================================================

USE stusta;

-- ============ 演示 1：慢查询日志 ============
-- 步骤 1：开启慢查询日志
SET GLOBAL slow_query_log = 1;
SET GLOBAL long_query_time = 1;
SET GLOBAL log_queries_not_using_indexes = 1;

-- 步骤 2：执行一条慢查询（无索引全表扫描 + SLEEP 模拟）
-- 这条查询会被记录到慢查询日志
SELECT s.name, s.major, a.action, a.access_time
FROM students s
JOIN access_log a ON a.user_id = s.id
WHERE a.response_ms > 3000
ORDER BY a.access_time DESC;

-- 步骤 3：用 SLEEP 制造一条确定超时的慢查询
SELECT SLEEP(2), COUNT(*) FROM access_log WHERE url LIKE '%export%';

-- 步骤 4：查看慢查询统计
SHOW GLOBAL STATUS LIKE 'Slow_queries';

-- 然后在终端执行：
-- sudo tail -20 /var/log/mysql/slow.log
-- sudo mysqldumpslow -s at -t 5 /var/log/mysql/slow.log

-- ============ 演示 2：通用查询日志 ============
-- 步骤 1：开启通用查询日志
SET GLOBAL general_log = 1;
SET GLOBAL general_log_file = '/var/log/mysql/general.log';

-- 步骤 2：执行一些操作（这些都会被记录）
SELECT * FROM students WHERE major = '网络安全';
UPDATE students SET gpa = 3.50 WHERE name = '王五';
SELECT COUNT(*) FROM scores WHERE score < 60;

-- 步骤 3：在终端查看日志内容
-- sudo tail -30 /var/log/mysql/general.log

-- 步骤 4：关闭通用查询日志
SET GLOBAL general_log = 0;

-- ============ 演示 3：Binlog 验证 ============
-- 步骤 1：确认 binlog 已开启（需提前配置好 mysqld.cnf）
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
SHOW BINARY LOGS;
SHOW BINARY LOG STATUS;

-- 步骤 2：执行写操作产生 binlog 事件
INSERT INTO students (name, gender, age, major, gpa, enrollment_date, email, phone, address)
VALUES ('测试用户', '男', 20, '网络安全', 3.50, '2025-09-01', 'test@stu.edu', '13800009999', '测试地址');

UPDATE students SET gpa = 3.60 WHERE name = '测试用户';

DELETE FROM students WHERE name = '测试用户';

-- 步骤 3：在终端查看 binlog 内容
-- sudo mysqlbinlog --base64-output=DECODE-ROWS -v /var/lib/mysql/mysql-bin.000001 | tail -60

-- ============ 演示 4：PITR 时间点恢复模拟 ============
-- 【重要】此演示需要按顺序执行，模拟"全量备份 → 正常操作 → 误操作 → 恢复"

-- 步骤 1：确认当前数据（40 条学生记录）
SELECT COUNT(*) AS '恢复前学生总数' FROM students;

-- 步骤 2：做一次全量备份（在终端执行）
-- sudo mysqldump -u root stusta > /tmp/full_backup_stusta.sql

-- 步骤 3：切换 binlog（标记备份点）
FLUSH BINARY LOGS;
SHOW BINARY LOG STATUS;
-- 记下当前 File 和 Position

-- 步骤 4：模拟"备份之后的正常业务操作"
INSERT INTO students (name, gender, age, major, gpa, enrollment_date, email, phone, address)
VALUES ('新生甲', '男', 18, '网络安全', 3.70, '2025-09-01', 'newA@stu.edu', '13800008001', '北京市朝阳区');

INSERT INTO students (name, gender, age, major, gpa, enrollment_date, email, phone, address)
VALUES ('新生乙', '女', 19, '软件工程', 3.85, '2025-09-01', 'newB@stu.edu', '13800008002', '上海市徐汇区');

UPDATE students SET gpa = 3.90 WHERE name = '张三';

SELECT COUNT(*) AS '正常操作后学生总数' FROM students;
-- 应该是 42 条

-- 步骤 5：模拟误操作！！！
-- ⚠️ 注意：这一步会清空 students 表
DELETE FROM students;
SELECT COUNT(*) AS '误操作后学生总数' FROM students;
-- 应该是 0 条

-- 步骤 6：PITR 恢复（在终端执行）
-- 6a. 先恢复全量备份
-- mysql -u root stusta < /tmp/full_backup_stusta.sql
--
-- 6b. 查看 binlog 定位误操作时间点
-- sudo mysqlbinlog --base64-output=DECODE-ROWS -v /var/lib/mysql/mysql-bin.000002 | grep -B5 "DELETE FROM"
--
-- 6c. 回放 binlog 到误操作前（用 --stop-datetime 或 --stop-position）
-- sudo mysqlbinlog --stop-datetime="替换为DELETE前的时间" --database=stusta /var/lib/mysql/mysql-bin.000002 | mysql -u root
--
-- 6d. 验证恢复结果

-- 步骤 7：验证恢复（恢复完成后执行）
SELECT COUNT(*) AS '恢复后学生总数' FROM students;
-- 应该是 42 条（包含新生甲、新生乙）
SELECT * FROM students WHERE name IN ('新生甲','新生乙','张三');
