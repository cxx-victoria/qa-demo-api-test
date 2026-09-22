"""抓包服务器（spy server）：把"客户端发来的每一条 JSON-RPC 报文"原样录到文件。

用途：验证上游 issue #2403 —— Inspector 的 CLI / TUI 是否在 initialize 里
宣称自己支持 io.modelcontextprotocol/ui（MCP Apps），而它们其实渲染不了。

它不依赖 mcp SDK，只按协议最小实现：
  · initialize  → 回 serverInfo + 原样回客户端请求的 protocolVersion
  · tools/list  → 回空列表
  · 其它请求     → 回空对象
收到的原始报文写入 client_requests.jsonl（一行一条），供离线分析。
"""
import json
import pathlib
import sys

LOG = pathlib.Path(__file__).resolve().with_name("client_requests.jsonl")
LOG.write_text("", encoding="utf-8")


def log(obj):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


while True:
    line = sys.stdin.readline()
    if not line:
        break
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue

    log(msg)                        # ← 关键：原始报文落盘

    if "id" not in msg:             # 通知（notification）不需要回复
        continue

    method = msg.get("method")
    if method == "initialize":
        params = msg.get("params") or {}
        result = {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {},
            "serverInfo": {"name": "spy-server", "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": []}
    else:
        result = {}

    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}) + "\n")
    sys.stdout.flush()
