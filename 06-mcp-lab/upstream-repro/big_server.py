"""复现用测试夹具：一个只会吐出超大 JSON 的 MCP Server。

用途：让 Inspector CLI 的 stdout 输出超过管道缓冲区（Windows 默认 64KB），
这样"下游提前关闭管道"才会真正触发写入端的 EPIPE —— 与上游 issue #2412 描述一致。
"""
from mcp.server import MCPServer

mcp = MCPServer("big-payload-fixture")


@mcp.tool()
def blob(size_kb: int = 512) -> str:
    """返回一段指定大小的文本，用于制造超大响应。"""
    return "A" * (size_kb * 1024)


if __name__ == "__main__":
    mcp.run()
