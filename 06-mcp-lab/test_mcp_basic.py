"""MCP Server 协议自动化测试（pytest）。

用法（PowerShell，在项目目录下）：
    cd D:\\qa-projects\\06-mcp-lab
    python -m pytest test_mcp_basic.py -v       # 推荐用 python -m pytest，见下方说明

    $env:MCP_SERVER_FILE="server_fixed.py"; python -m pytest test_mcp_basic.py -v   # 测加固版

设计要点：
  · 脚本会自动挑选"带 mcp 的解释器"去跑被测 server（优先项目里的 .venv），
    所以即使你不小心用全局 pytest 运行，也不会出现"13 errors"那种连着不上的问题。
    报错时会直接把 server 的 stderr 打出来，不用猜。
  · 每条测试都在临时目录里跑一份 server.py 副本 —— 不污染项目里的 mcp_tasks.db，
    且重复执行结果一致（可回归）。
  · 客户端手写 JSON-RPC over stdio：先 initialize，再发 notifications/initialized，
    这是 MCP 协议规定的握手顺序，少了会拿不到响应。
  · 已知缺陷（空标题/超长标题/删除不存在的 id 不报错）用 xfail 标记：
    缺陷还在 → XFAIL（符合预期）；缺陷修好 → XPASS（说明修复有效）。
    这样同一个文件既能"记录缺陷"，又能"验证修复"。
"""
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import ast
from pathlib import Path

import pytest

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
SERVER_FILE = os.environ.get("MCP_SERVER_FILE", "server.py")


def pick_server_python() -> str:
    """挑选用来运行被测 server 的解释器。

    为什么不能直接用 sys.executable：如果你用"全局 pytest"运行本文件，
    sys.executable 就是全局 Python —— 它通常没装 mcp，server 会秒退，
    表现就是一片 errors。所以这里优先用项目自带的虚拟环境。
    """
    for rel in (Path(".venv/Scripts/python.exe"), Path(".venv/bin/python")):
        cand = HERE / rel
        if cand.exists():
            return str(cand)
    return sys.executable


def assert_mcp_available(python_exe: str) -> None:
    """提前检查：这个解释器到底能不能 import mcp。不行就给一句人话。"""
    r = subprocess.run([python_exe, "-c", "import mcp"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"\n本次要用这个解释器运行被测 server，但它没有安装 mcp：\n"
            f"    {python_exe}\n"
            f"解决办法（任选其一）：\n"
            f"    1) 装到该解释器：\"{python_exe}\" -m pip install mcp\n"
            f"    2) 激活项目虚拟环境后再跑：cd {HERE}; .\\.venv\\Scripts\\Activate.ps1; python -m pytest test_mcp_basic.py -v\n"
        )


PY = pick_server_python()


class McpClient:
    """极简 MCP 客户端：只实现测试需要的 initialize / tools/list / tools/call。"""

    def __init__(self, server_path: Path, work_dir: Path, python_exe: str):
        self.server_path = server_path
        self.python_exe = python_exe
        self.proc = subprocess.Popen(
            [python_exe, "-u", str(server_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1, cwd=str(work_dir),
        )
        self.q: queue.Queue = queue.Queue()
        self.err_buf: list[str] = []
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._err_reader, daemon=True).start()
        self._id = 0
        self.init_result = self.handshake()

    def _reader(self):
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if line:
                    try:
                        self.q.put(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass

    def _err_reader(self):
        """把 server 的 stderr 留在内存里（只留最后 40 行），出错时打出来。"""
        try:
            for line in self.proc.stderr:
                self.err_buf.append(line)
                del self.err_buf[:-40]
        except Exception:
            pass

    def server_stderr(self) -> str:
        return "".join(self.err_buf).strip() or "(server 没有输出任何错误信息)"

    def _read(self, timeout=25):
        """等一条响应。进程要是已经死了就立刻报错，不干等超时。"""
        deadline = time.monotonic() + timeout
        while True:
            try:
                return self.q.get(timeout=0.2)
            except queue.Empty:
                if self.proc.poll() is not None and self.q.empty():
                    raise RuntimeError(
                        "\n被测 server 进程已退出，且没有返回任何响应。\n"
                        f"启动命令：{self.python_exe} -u {self.server_path}\n"
                        f"退出码：{self.proc.returncode}\n"
                        f"server 的 stderr（最后几行）：\n{self.server_stderr()}\n"
                        "最常见原因：该解释器没装 mcp，或 server.py 本身有语法错误。\n"
                    )
                if time.monotonic() > deadline:
                    return {"_timeout": True}

    def send(self, method, params=None, notify=False, timeout=25):
        self._id += 1
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            msg["id"] = self._id
        try:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                "\n被测 server 进程已经退出，无法再发送请求 —— 说明它启动就失败了。\n"
                f"启动命令：{self.python_exe} -u {self.server_path}\n"
                f"server 的 stderr（最后几行）：\n{self.server_stderr()}\n"
                "最常见原因：用来运行 server 的解释器没装 mcp（见文件开头的 pick_server_python 说明）。\n"
            ) from exc
        return None if notify else self._read(timeout)

    def handshake(self):
        r = self.send("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1.0"},
        })
        self.send("notifications/initialized", notify=True)
        return (r or {}).get("result") or {}

    def list_tools(self):
        r = self.send("tools/list")
        return ((r or {}).get("result") or {}).get("tools", [])

    def call(self, name, args, timeout=25):
        return self.send("tools/call", {"name": name, "arguments": args}, timeout=timeout)

    def text_of(self, name, args, timeout=25):
        """取出工具返回的文本；被拒绝时返回 ""。"""
        r = self.call(name, args, timeout) or {}
        if r.get("error"):
            return ""
        res = r.get("result") or {}
        if res.get("isError"):
            return ""
        try:
            return (res.get("content") or [{}])[0].get("text", "")
        except Exception:
            return ""

    def rejected(self, name, args, timeout=25):
        """工具调用是否被拒绝（JSON-RPC 层 error 或 result.isError 都算）。"""
        r = self.call(name, args, timeout) or {}
        if r.get("error"):
            return True
        return bool((r.get("result") or {}).get("isError"))

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def task_titles(text):
    """把 list_tasks 的返回文本解析成标题列表。

    未加固版的 list_tasks 返回的是 Python repr（单引号、转义反斜杠），
    加固版返回的是标准 JSON —— 两种都兼容，这样测试脚本本身能跨版本复用。
    解析失败时返回空列表（由断言给出清晰失败信息）。
    """
    try:
        data = json.loads(text)
    except Exception:
        try:
            data = ast.literal_eval(text)
        except Exception:
            return []
    return [str(item.get("title")) for item in data if isinstance(item, dict)]


@pytest.fixture(scope="module")
def server_dir(request):
    """把被测 server 复制到一个独立临时目录，保证测试之间互不干扰。

    刻意**不使用 pytest 的 tmp_path_factory**：它依赖系统临时根目录
    `…\\AppData\\Local\\Temp\\pytest-of-<用户名>`，那个目录一旦出问题，
    18 条用例会集体报 ERROR —— 看起来像"被测代码有缺陷"，实际是环境问题，
    极具迷惑性（2026-09-22 实际踩到过）。这里用 tempfile.mkdtemp() 自己建目录，
    让被测对象与 pytest 的临时目录机制彻底解耦。
    """
    src = HERE / SERVER_FILE
    if not src.exists():
        raise RuntimeError(
            f"\n找不到被测文件：{src}\n"
            f"当前 MCP_SERVER_FILE = {SERVER_FILE!r}，该路径下实际有："
            f"{[p.name for p in HERE.glob('*.py')]}\n"
            "（如果不小心设置了环境变量 MCP_SERVER_FILE，可以先执行 Remove-Item Env:MCP_SERVER_FILE）\n"
        )
    d = Path(tempfile.mkdtemp(prefix="mcp_srv_"))
    request.addfinalizer(lambda: shutil.rmtree(d, ignore_errors=True))
    shutil.copy2(src, d / "server.py")
    return d


@pytest.fixture(scope="module")
def client(server_dir):
    assert_mcp_available(PY)
    c = McpClient(server_dir / "server.py", server_dir, PY)
    yield c
    c.close()


# ---------------- 协议层 ----------------

def test_initialize_returns_server_info(client):
    """用例 1：握手成功，返回 serverInfo 与协议版本。"""
    assert client.init_result.get("serverInfo"), "initialize 未返回 serverInfo"
    assert client.init_result.get("protocolVersion"), "initialize 未返回 protocolVersion"


def test_tools_list_returns_three_tools(client):
    """用例 2：tools/list 返回 3 个工具，名称正确。"""
    names = [t["name"] for t in client.list_tools()]
    assert sorted(names) == ["add_task", "delete_task", "list_tasks"], f"实际工具列表={names}"


def test_every_tool_has_valid_input_schema(client):
    """用例 3：每个工具的 inputSchema 是合法 JSON Schema，且声明了必填参数。"""
    for t in client.list_tools():
        schema = t.get("inputSchema") or {}
        assert schema.get("type") == "object", f"{t['name']} 的 inputSchema.type 不是 object"
        assert "properties" in schema, f"{t['name']} 的 inputSchema 缺 properties"
    by_name = {t["name"]: t for t in client.list_tools()}
    assert by_name["add_task"]["inputSchema"].get("required") == ["title"]
    assert by_name["delete_task"]["inputSchema"].get("required") == ["task_id"]


def test_every_tool_has_description(client):
    """用例 4：工具描述非空 —— 模型靠描述决定选哪个工具，空描述会导致误调用。"""
    for t in client.list_tools():
        assert (t.get("description") or "").strip(), f"{t['name']} 缺少 description"


def test_unknown_tool_is_rejected_without_closing_connection(client):
    """用例 17：调用不存在的工具要明确报错，且连接不能被断开。"""
    assert client.rejected("not_exist_tool", {}), "未知工具竟然没有报错"
    assert client.list_tools(), "报错之后连接已失效（后续 tools/list 无响应）"


def test_repeated_tools_list_is_stable(client):
    """用例 16：连续 20 次 tools/list 都要成功。"""
    for i in range(20):
        assert client.list_tools(), f"第 {i + 1} 次 tools/list 返回空"


# ---------------- 正常路径 ----------------

def test_add_task_with_valid_title(client):
    """用例 5：合法标题应返回 created: <id>。"""
    text = client.text_of("add_task", {"title": "pytest-正常任务"})
    assert text.startswith("created: "), f"实际返回={text!r}"


def test_list_tasks_contains_created_task(client):
    """用例 6：list_tasks 能查到刚创建的任务。"""
    client.text_of("add_task", {"title": "pytest-可查询任务"})
    assert "pytest-可查询任务" in task_titles(client.text_of("list_tasks", {}))


def test_delete_existing_task(client):
    """用例 7：删除存在的 id 应返回 deleted，且列表里消失。"""
    created = client.text_of("add_task", {"title": "pytest-待删除任务"})
    task_id = created.split("created: ")[-1]
    assert client.text_of("delete_task", {"task_id": task_id}) == "deleted"
    assert "pytest-待删除任务" not in task_titles(client.text_of("list_tasks", {}))


def test_special_characters_round_trip(client):
    """用例 12：emoji / 中文 / 引号 / 换行都要原样存回，不能乱码。"""
    payload = "emoji🚀 中文 <>&\"' 结束"
    client.text_of("add_task", {"title": payload})
    assert payload in task_titles(client.text_of("list_tasks", {})), "特殊字符回查不一致"


def test_numeric_title_is_rejected(client):
    """用例 9：title 传数字应被类型校验拦住（schema 声明的是 string）。"""
    assert client.rejected("add_task", {"title": 12345}), "数字标题竟然通过了类型校验"


def test_missing_title_is_rejected(client):
    """用例 8：缺少必填参数 title 应报错，且服务不能崩。"""
    assert client.rejected("add_task", {}), "缺少 title 竟然没有报错"
    assert client.list_tools(), "参数校验失败后服务已不可用"


def test_large_payload_does_not_crash_server(client):
    """用例 20：100KB 超大参数不能让服务崩溃。"""
    client.call("add_task", {"title": "A" * 100_000}, timeout=30)
    assert client.list_tools(), "超大参数之后服务已不可用"


# ---------------- 已知缺陷（修好会自动变成 XPASS） ----------------

@pytest.mark.xfail(reason="MCP-001 缺陷：add_task 未校验空标题，当前会创建成功", strict=False)
def test_empty_title_is_rejected(client):
    """用例 10：空标题应被拒绝。"""
    assert client.rejected("add_task", {"title": ""}), "空标题被创建成功了（MCP-001）"


@pytest.mark.xfail(reason="MCP-002 缺陷：add_task 未校验超长标题，当前会创建成功", strict=False)
def test_overlong_title_is_rejected(client):
    """用例 11：10000 字符标题应被拒绝或截断。"""
    assert client.rejected("add_task", {"title": "x" * 10_000}), "超长标题被创建成功了（MCP-002）"


@pytest.mark.xfail(reason="MCP-003 缺陷：delete_task 对不存在的 id 仍返回 deleted", strict=False)
def test_delete_nonexistent_id_reports_error(client):
    """用例 14：删除不存在的 id 应返回"未找到"，而不是成功。"""
    assert client.rejected("delete_task", {"task_id": "not-exist-id"}), \
        "不存在的 id 竟返回 deleted（MCP-003）"


@pytest.mark.xfail(reason="MCP-004 缺陷：delete_task 对空 id 仍返回 deleted", strict=False)
def test_delete_with_empty_id_reports_error(client):
    """用例 15：删除时传空 id 应报错。"""
    assert client.rejected("delete_task", {"task_id": ""}), "空 id 竟返回 deleted（MCP-004）"


@pytest.mark.xfail(reason="MCP-005 缺陷：list_tasks 返回 Python repr，不是合法 JSON", strict=False)
def test_list_tasks_text_is_valid_json(client):
    """用例 25（附加）：工具返回的文本内容应是合法 JSON，下游程序才能直接解析。"""
    text = client.text_of("list_tasks", {})
    json.loads(text)   # 未加固版这里是 Python repr，会抛 JSONDecodeError
