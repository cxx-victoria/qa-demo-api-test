"""数据库适配层：同一套业务代码，可跑在 SQLite 或 MySQL 上。

设计目标：
  · 对外暴露和 sqlite3 一致的用法（execute / fetchone / fetchall / with 事务）
  · 用 DB_BACKEND 环境变量切换后端，业务代码零改动
  · SQL 里的 ? 占位符自动转成 MySQL 的 %s
"""
import os
import sqlite3

DB_BACKEND = os.getenv("DB_BACKEND", "sqlite")      # sqlite | mysql
SQLITE_PATH = os.getenv("DEMO_DB", "tasks.db")

MYSQL_CONF = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "qa"),
    password=os.getenv("DB_PASSWORD", "qa123456"),
    database=os.getenv("DB_NAME", "qa_demo"),
    charset="utf8mb4",
)

DDL_MYSQL = (
    "CREATE TABLE IF NOT EXISTS tasks ("
    "  id VARCHAR(32) PRIMARY KEY,"
    "  title VARCHAR(100) NOT NULL,"
    "  done TINYINT(1) NOT NULL DEFAULT 0,"
    "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
)
DDL_SQLITE = (
    "CREATE TABLE IF NOT EXISTS tasks ("
    "  id TEXT PRIMARY KEY, title TEXT NOT NULL, done INTEGER DEFAULT 0,"
    "  created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
)


class _Conn:
    """把 pymysql 连接包装成 sqlite3 的用法，业务代码不用改。"""

    def __init__(self, raw):
        self._raw = raw

    def execute(self, sql, params=None):
        cur = self._raw.cursor()
        cur.execute(sql.replace("?", "%s"), params or ())    # 占位符转换
        return cur

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._raw.commit()
        else:
            self._raw.rollback()
        self._raw.close()
        return False


def db(readonly: bool = False):
    """拿数据库连接。readonly=True 时用只读账号（给测试用）。"""
    if DB_BACKEND == "mysql":
        import pymysql
        from pymysql.cursors import DictCursor

        conf = dict(MYSQL_CONF)
        if readonly:
            conf.update(user=os.getenv("DB_RO_USER", "qa_ro"),
                        password=os.getenv("DB_RO_PASSWORD", "qa_ro_pwd"),
                        autocommit=True)
        conn = pymysql.connect(cursorclass=DictCursor, **conf)
        if not readonly:
            with conn.cursor() as cur:
                cur.execute(DDL_MYSQL)
            conn.commit()
        return _Conn(conn)

    # ---------- SQLite（默认，保持原有行为） ----------
    uri = f"file:{SQLITE_PATH}?mode=ro" if readonly else SQLITE_PATH
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    if not readonly:
        conn.execute(DDL_SQLITE)
    return conn