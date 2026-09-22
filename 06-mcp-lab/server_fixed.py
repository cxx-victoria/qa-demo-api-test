# 【加固版】MCP Server：修复了 server.py 中被测出的 5 个缺陷（MCP-001 ~ MCP-005）。
#
# 与 server.py 的区别：
#   1. add_task  增加 title 非空校验 + 长度上限（默认 200 字符）
#   2. delete_task 增加 task_id 非空校验 + 删除行数为 0 时返回"未找到"
#   3. list_tasks 返回合法 JSON 文本（json.dumps），不再返回 Python repr
# 工具名、参数名、schema 结构保持不变，保证加固前后可对比。
#
# 版本适配（2026-09-22 实测 mcp 2.2.0）：
#   mcp 1.x：from mcp.server.fastmcp import FastMCP  → mcp = FastMCP("demo-tasks")
#   mcp 2.x：from mcp.server import MCPServer       → mcp = MCPServer("demo-tasks")
import json
import sqlite3
import uuid

from mcp.server import MCPServer

# ToolError 是 SDK 专门给"可预期的工具失败"准备的异常：
#   raise ToolError("…") → 客户端收到 isError=true + 你的错误文本（模型能读懂、能自我纠正）
# 直接 raise ValueError 则只会在客户端看到一句通用的 "Error executing tool add_task"，
# 具体原因只留在服务端 stderr —— 这就是常见的"报错但不知道为什么"的根因。
try:
    from mcp.server.mcpserver.exceptions import ToolError      # mcp 2.x
except ImportError:                                            # 兼容 mcp 1.x
    from mcp.server.fastmcp.exceptions import ToolError

mcp = MCPServer("demo-tasks")
DB = "mcp_tasks.db"
MAX_TITLE_LEN = 200            # 新增：标题长度上限


def connect():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT, done INTEGER)")
    return conn


@mcp.tool()
def add_task(title: str) -> str:
    """添加一条任务，返回任务 id。"""
    # 修复 MCP-001 / MCP-002：入口校验
    clean = (title or "").strip()
    if not clean:
        raise ToolError("title 不能为空或纯空格")
    if len(clean) > MAX_TITLE_LEN:
        raise ToolError(f"title 超长（{len(clean)} 字符，上限 {MAX_TITLE_LEN}）")

    task_id = uuid.uuid4().hex[:8]
    with connect() as c:
        c.execute("INSERT INTO tasks (id, title, done) VALUES (?, ?, 0)", (task_id, clean))
    return "created: " + task_id


@mcp.tool()
def list_tasks() -> str:
    """列出全部任务。"""
    with connect() as c:
        rows = c.execute("SELECT id, title, done FROM tasks").fetchall()
    items = [{"id": r[0], "title": r[1], "done": bool(r[2])} for r in rows]
    # 修复 MCP-005：返回合法 JSON，方便下游程序直接解析
    return json.dumps(items, ensure_ascii=False)


@mcp.tool()
def delete_task(task_id: str) -> str:
    """按 id 删除任务。"""
    # 修复 MCP-003 / MCP-004：先校验，再根据影响行数判断是否真的删掉了
    tid = (task_id or "").strip()
    if not tid:
        raise ToolError("task_id 不能为空")

    with connect() as c:
        cur = c.execute("DELETE FROM tasks WHERE id = ?", (tid,))
        affected = cur.rowcount
    if affected == 0:
        raise ToolError(f"未找到 id={tid} 的任务")
    return "deleted"


if __name__ == "__main__":
    mcp.run()   # 默认 stdio 传输
