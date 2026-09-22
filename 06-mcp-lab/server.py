# 一个用于测试的 MCP Server：暴露 3 个任务管理工具。
# 特意留了 2 个校验缺口，方便你在测试中发现它们（见文件末尾说明）。
#
# ⚠️ 版本适配说明（2026-09-22 实测）：
#   mcp 1.x 写法：from mcp.server.fastmcp import FastMCP   →  mcp = FastMCP("demo-tasks")
#   mcp 2.x 写法：from mcp.server import MCPServer        →  mcp = MCPServer("demo-tasks")
#   （2.x 里 FastMCP 被重命名为 MCPServer，其余 API —— @mcp.tool() 装饰器、docstring 作为描述、
#     mcp.run() 默认 stdio —— 都保持不变）
import sqlite3
import uuid

from mcp.server import MCPServer          # ← mcp 2.x 的新导入路径

mcp = MCPServer("demo-tasks")             # ← 类名由 FastMCP 改为 MCPServer
DB = "mcp_tasks.db"


def connect():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT, done INTEGER)")
    return conn


@mcp.tool()
def add_task(title: str) -> str:
    """添加一条任务，返回任务 id。"""
    # 【缺口 1】没有校验 title 是否为空、是否超长
    task_id = uuid.uuid4().hex[:8]
    with connect() as c:
        c.execute("INSERT INTO tasks (id, title, done) VALUES (?, ?, 0)", (task_id, title))
    return "created: " + task_id


@mcp.tool()
def list_tasks() -> str:
    """列出全部任务。"""
    with connect() as c:
        rows = c.execute("SELECT id, title, done FROM tasks").fetchall()
    items = [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in rows]
    return str(items)


@mcp.tool()
def delete_task(task_id: str) -> str:
    """按 id 删除任务。"""
    # 【缺口 2】不存在的 id 不报错，直接返回成功
    with connect() as c:
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return "deleted"


if __name__ == "__main__":
    mcp.run()   # 默认用 stdio 传输（标准输入输出），符合 MCP 规范
