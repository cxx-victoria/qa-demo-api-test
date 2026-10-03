-- 业务表：id 用 VARCHAR(32)，title 长度和接口约束的 100 对齐
CREATE TABLE IF NOT EXISTS tasks (
  id         VARCHAR(32)  NOT NULL PRIMARY KEY,
  title      VARCHAR(100) NOT NULL,
  done       TINYINT(1)   NOT NULL DEFAULT 0,
  created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 测试专用只读账号（等价于 SQLite 的 mode=ro）
CREATE USER IF NOT EXISTS 'qa_ro'@'%' IDENTIFIED BY 'qa_ro_pwd';
GRANT SELECT ON qa_demo.tasks TO 'qa_ro'@'%';
FLUSH PRIVILEGES;

