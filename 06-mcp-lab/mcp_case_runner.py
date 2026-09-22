"""MCP Server 协议测试 —— 24 条用例自动执行器。

用法（PowerShell，在项目目录下）：
    cd D:\\qa-projects\\06-mcp-lab
    .\\.venv\\Scripts\\Activate.ps1
    python mcp_case_runner.py                    # 测 server.py（未加固）
    python mcp_case_runner.py server_fixed.py    # 测加固版，做回归对比

结果同时：
  · 打印到终端（[PASS]/[FAIL]/[WARN]/[SKIP]）
  · 落盘到 cases_result.json（可读版本）+ cases_result.csv（可直接粘进 Excel）

设计要点：
  · 用子进程 + JSON-RPC over stdio 直接与 server 对话，不依赖 Inspector 的 CLI 参数差异
  · stdout 读取放在后台线程 + 队列，带超时，避免某条用例卡死拖垮整个脚本
  · 错误判定同时认两种通道：JSON-RPC 层 error、工具层 result.isError
"""
import csv
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent          # 脚本所在目录 = 项目目录
SERVER_FILE = sys.argv[1] if len(sys.argv) > 1 else "server.py"


def pick_server_python() -> str:
    """挑选运行被测 server 的解释器：优先项目里的 .venv。

    不能盲用 sys.executable —— 如果你用全局 Python 跑本脚本，
    全局环境通常没装 mcp，server 会秒退，表现是"连不上/发不出请求"。
    """
    for rel in (Path(".venv/Scripts/python.exe"), Path(".venv/bin/python")):
        cand = HERE / rel
        if cand.exists():
            return str(cand)
    return sys.executable


PY = pick_server_python()

if not (HERE / SERVER_FILE).exists():
    print(f"[错误] 找不到被测文件：{HERE / SERVER_FILE}", flush=True)
    print(f"       当前目录下的 .py 文件：{[p.name for p in HERE.glob('*.py')]}", flush=True)
    sys.exit(2)

_probe = subprocess.run([PY, "-c", "import mcp"], capture_output=True, text=True)
if _probe.returncode != 0:
    print("[错误] 用来运行被测 server 的解释器没有安装 mcp：", PY, flush=True)
    print(f'       解决办法：" {PY} " -m pip install mcp', flush=True)
    sys.exit(2)


class McpClient:
    """极简 MCP 客户端：只实现本测试需要的 initialize / tools/list / tools/call。"""

    def __init__(self, server_path: Path, work_dir: Path):
        self.proc = subprocess.Popen(
            [PY, "-u", str(server_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1, cwd=str(work_dir),
        )
        self.q: queue.Queue = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        self._id = 0
        self.handshake()

    def _reader(self):
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.q.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

    def _read(self, timeout=25):
        """等一条响应。进程要是已经死了就立刻返回，不干等超时。"""
        deadline = time.monotonic() + timeout
        while True:
            try:
                return self.q.get(timeout=0.2)
            except queue.Empty:
                if self.proc.poll() is not None and self.q.empty():
                    print(f"[警告] server 进程已退出（退出码 {self.proc.returncode}），"
                          f"该条用例将判定为超时/失败。", flush=True)
                    return {"_timeout": True}
                if time.monotonic() > deadline:
                    return {"_timeout": True}

    def send(self, method, params=None, notify=False, timeout=25):
        self._id += 1
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            msg["id"] = self._id
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        return None if notify else self._read(timeout)

    def handshake(self):
        """标准握手：initialize 请求 + notifications/initialized 通知。"""
        r = self.send("initialize", {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "case-runner", "version": "1.0"},
        })
        self.send("notifications/initialized", notify=True)
        return r

    def call(self, name, args, timeout=25):
        return self.send("tools/call", {"name": name, "arguments": args}, timeout=timeout)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def tool_error(r):
    """统一判断"这次调用是否被拒绝"。

    MCP 2.x 有两种错误通道：
      · JSON-RPC 层 error   → 协议级错误（如方法不存在）
      · 工具层 result.isError → 参数校验失败 / 工具内部抛异常
    只认 error 会把"参数确实被拒绝了"误判成缺陷。
    """
    if not isinstance(r, dict):
        return None
    if r.get("error"):
        return r["error"]
    res = r.get("result")
    if isinstance(res, dict) and res.get("isError"):
        try:
            return {"layer": "tool", "message": (res.get("content") or [{}])[0].get("text", "")}
        except Exception:
            return {"layer": "tool", "message": ""}
    return None


RESULTS = []


def rec(no, name, expected, actual, verdict):
    RESULTS.append({"no": no, "case": name, "expected": expected,
                    "actual": str(actual)[:400], "verdict": verdict})
    mark = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "SKIP": "[SKIP]"}[verdict]
    print(f"  {mark} #{no:<3} {name[:28]:<30} {str(actual)[:78]}", flush=True)


def main():
    print("=" * 108, flush=True)
    print(f"MCP Server 协议测试 —— 24 条用例   被测文件: {SERVER_FILE}", flush=True)
    print("=" * 108, flush=True)

    c = McpClient(HERE / SERVER_FILE, HERE)

    # ---------- 1-4 协议层 ----------
    res = (c.handshake().get("result")) or {}
    rec(1, "握手成功", "返回 serverInfo + 协议版本",
        f"serverInfo={res.get('serverInfo')} protocolVersion={res.get('protocolVersion')}",
        "PASS" if res.get("serverInfo") else "FAIL")

    r = c.send("tools/list")
    tools = ((r or {}).get("result") or {}).get("tools", [])
    names = [t["name"] for t in tools]
    rec(2, "tools/list 返回 3 个工具", "数量=3 且名称正确",
        f"数量={len(tools)} 名称={names}", "PASS" if len(tools) == 3 else "FAIL")

    bad = [t["name"] for t in tools
           if (t.get("inputSchema") or {}).get("type") != "object"
           or "properties" not in (t.get("inputSchema") or {})]
    rec(3, "inputSchema 合法", "均为 object 且含 properties",
        "全部合法" if not bad else f"异常={bad}", "PASS" if not bad else "FAIL")

    nodesc = [t["name"] for t in tools if not (t.get("description") or "").strip()]
    rec(4, "工具描述非空", "都有 description",
        "全部有描述" if not nodesc else f"缺={nodesc}", "PASS" if not nodesc else "FAIL")

    # ---------- 5-7 正常路径 ----------
    tag = str(int(time.time()))
    title_a, title_b = f"正常任务_{tag}", f"待删除任务_{tag}"

    t = json.dumps(c.call("add_task", {"title": title_a}).get("result"), ensure_ascii=False)
    rec(5, "add_task 合法标题", "返回 created: xxx", t[:80], "PASS" if "created" in t else "FAIL")

    t = json.dumps(c.call("list_tasks", {}).get("result"), ensure_ascii=False)
    rec(6, "list_tasks 返回列表", "包含刚创建的任务", t[:80], "PASS" if title_a in t else "FAIL")

    t = json.dumps(c.call("add_task", {"title": title_b}).get("result"), ensure_ascii=False)
    tid = t.split("created: ")[-1].split('"')[0][:8] if "created: " in t else ""
    d = json.dumps(c.call("delete_task", {"task_id": tid}).get("result"), ensure_ascii=False)
    after = json.dumps(c.call("list_tasks", {}).get("result"), ensure_ascii=False)
    gone = title_b not in after
    rec(7, "delete_task 已存在 id", "返回 deleted 且列表消失",
        f"返回={d[:40]} 列表已消失={gone}", "PASS" if ("deleted" in d and gone) else "FAIL")

    # ---------- 8-13 参数校验 ----------
    e = tool_error(c.call("add_task", {}))
    rec(8, "add_task 缺 title", "参数校验错误（不能崩）",
        (e or {}).get("message", "未报错")[:110], "PASS" if e else "FAIL")

    e = tool_error(c.call("add_task", {"title": 12345}))
    rec(9, "add_task title 传数字", "类型校验失败",
        (e or {}).get("message", "未报错")[:110], "PASS" if e else "FAIL")

    t = json.dumps(c.call("add_task", {"title": ""}).get("result"), ensure_ascii=False)
    rec(10, "add_task 空标题", "应拒绝", t[:110], "FAIL" if "created" in t else "PASS")

    t = json.dumps(c.call("add_task", {"title": "x" * 10000}).get("result"), ensure_ascii=False)
    rec(11, "add_task 10000 字符", "应拒绝或截断", t[:110], "FAIL" if "created" in t else "PASS")

    special = "emoji🚀 中文 <>&\"' 换行\n结束"
    c.call("add_task", {"title": special})
    after = json.dumps(c.call("list_tasks", {}).get("result"), ensure_ascii=False)
    rec(12, "特殊字符 / emoji", "原样存储不乱码",
        f"回查包含={'emoji🚀' in after}", "PASS" if "emoji🚀" in after else "FAIL")

    e = tool_error(c.call("add_task", {"title": f"多余字段_{tag}", "hacker": "x"}))
    rec(13, "多余参数", "被忽略或明确报错",
        "明确报错" if e else "被忽略，正常创建", "PASS")

    # ---------- 14-16 边界 ----------
    r = c.call("delete_task", {"task_id": "not-exist-id"})
    res14 = (r or {}).get("result") or {}
    t = json.dumps(res14, ensure_ascii=False)
    rec(14, "delete_task 不存在的 id", "应返回未找到",
        f"返回={t[:70]} isError={res14.get('isError')}",
        "FAIL" if ("deleted" in t and not res14.get("isError")) else "PASS")

    r = c.call("delete_task", {"task_id": ""})
    res15 = (r or {}).get("result") or {}
    t = json.dumps(res15, ensure_ascii=False)
    rec(15, "delete_task 空 id", "明确报错",
        f"返回={t[:70]} isError={res15.get('isError')}",
        "FAIL" if ("deleted" in t and not res15.get("isError")) else "PASS")

    t0 = time.time()
    ok = all("result" in (c.send("tools/list") or {}) for _ in range(20))
    rec(16, "连续 20 次 tools/list", "不报错",
        f"耗时 {time.time() - t0:.2f}s 全部成功={ok}", "PASS" if ok else "FAIL")

    # ---------- 17-19 错误结构与并发 ----------
    e = tool_error(c.send("tools/call", {"name": "not_exist_tool", "arguments": {}}))
    rec(17, "调用不存在的工具", "明确报错、不断连接",
        f"[{(e or {}).get('layer', 'jsonrpc')} 层] {(e or {}).get('message', '')[:70]}" if e else "未报错",
        "PASS" if e else "WARN")

    r = c.call("add_task", {})
    res18 = (r or {}).get("result") or {}
    structural = (isinstance(r, dict) and r.get("jsonrpc") == "2.0" and "id" in r
                  and (bool(res18.get("isError")) or bool(r.get("error")))
                  and isinstance(res18.get("content"), list))
    rec(18, "错误返回结构规范", "JSON-RPC 信封完整 + isError/content",
        f"keys={list((r or {}).keys())} isError={res18.get('isError')}",
        "PASS" if structural else "WARN")

    ids, t0 = [], time.time()
    for i in range(10):
        t = json.dumps(c.call("add_task", {"title": f"连发_{tag}_{i}"}).get("result"), ensure_ascii=False)
        if "created: " in t:
            ids.append(t.split("created: ")[-1].split('"')[0][:8])
    rec(19, "快速连续 10 次 add_task", "全部成功且 id 唯一",
        f"成功 {len(ids)}/10，去重后 {len(set(ids))}，耗时 {time.time() - t0:.2f}s",
        "PASS" if len(ids) == 10 and len(set(ids)) == 10 else "FAIL")

    # ---------- 20 / 22 / 23 稳定性与安全 ----------
    r = c.call("add_task", {"title": "A" * 100000}, timeout=30)
    alive = c.send("tools/list")
    rec(20, "100KB 超大参数", "服务不崩溃",
        f"之后仍可通信={'result' in (alive or {})}",
        "PASS" if "result" in (alive or {}) else "FAIL")

    c.call("add_task", {"title": "../../etc/passwd"})
    after = json.dumps(c.call("list_tasks", {}).get("result"), ensure_ascii=False)
    rec(22, "路径穿越字符串", "原样存储、服务不受影响",
        f"原样存储={'../../etc/passwd' in after}", "PASS" if "../../etc/passwd" in after else "WARN")

    c.call("add_task", {"title": "; rm -rf / && echo pwned"})
    after = json.dumps(c.call("list_tasks", {}).get("result"), ensure_ascii=False)
    alive = c.send("tools/list")
    rec(23, "命令注入字符串", "不执行且服务存活",
        f"原样存储={'rm -rf' in after} 服务存活={'result' in (alive or {})}",
        "PASS" if ("rm -rf" in after and "result" in (alive or {})) else "FAIL")

    # ---------- 21 / 24 未覆盖 ----------
    rec(21, "工具耗时超过客户端超时", "客户端能感知超时",
        "未覆盖：本 server 无慢工具（见报告说明）", "SKIP")
    rec(24, "长时间运行内存增长", "记录基线判断泄漏",
        "未覆盖：需外部监控工具持续采样（见报告说明）", "SKIP")

    c.close()

    out_dir = HERE
    # 按被测文件名区分结果，这样"未加固 / 加固"两次运行都能留档、不会被覆盖
    stem = Path(SERVER_FILE).stem
    json_out = out_dir / f"cases_result_{stem}.json"
    csv_out = out_dir / f"cases_result_{stem}.csv"
    with open(json_out, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=1)
    with open(csv_out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["no", "case", "expected", "actual", "verdict"])
        w.writeheader()
        w.writerows(RESULTS)

    p = sum(1 for x in RESULTS if x["verdict"] == "PASS")
    fl = sum(1 for x in RESULTS if x["verdict"] == "FAIL")
    wn = sum(1 for x in RESULTS if x["verdict"] == "WARN")
    sk = sum(1 for x in RESULTS if x["verdict"] == "SKIP")
    print("\n" + "=" * 108, flush=True)
    print(f"合计 {len(RESULTS)} 条：PASS {p}   FAIL {fl}   WARN {wn}   SKIP {sk}   "
          f"通过率 {(p + wn) / (len(RESULTS) - sk) * 100:.1f}%（不含 SKIP）", flush=True)
    print(f"明细已落盘：{json_out.name} / {csv_out.name}", flush=True)


if __name__ == "__main__":
    main()
