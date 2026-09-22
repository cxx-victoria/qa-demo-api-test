# MCP Server 协议测试（智能体工具协议）

围绕 **MCP（Model Context Protocol）** 做的协议级测试实践：
自己写一个 MCP Server，再当它的测试方，用 24 条用例把协议合规性、
参数校验、边界、错误结构、并发与安全全部覆盖一遍，最后去上游官方工具里做真实缺陷复现。

> MCP 是"AI 智能体怎么调用外部工具"的协议标准。协议层出问题，
> Agent 会**静默失败或调错工具**，比 UI 层的问题更难排查 —— 这是本项目的测试价值所在。

---

## 被测对象

`server.py` —— 一个任务管理 MCP Server，暴露 3 个工具：

| 工具 | 参数 | 说明 |
|------|------|------|
| `add_task` | `title: str` | 添加任务，返回 `created: <id>` |
| `list_tasks` | 无 | 列出全部任务 |
| `delete_task` | `task_id: str` | 按 id 删除任务 |

> 该 Server **故意保留了 5 个校验缺口**，用于演示完整测试流程；
> 修复后的版本见 `server_fixed.py`，两者用同一套用例做前后对比。

---

## 快速开始

```powershell
cd D:\qa-projects\06-mcp-lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install mcp pytest

# ① 24 条协议用例（结果落盘为 cases_result_server.json / .csv）
python mcp_case_runner.py

# ② 加固版回归对比（预期 24 条全部通过）
python mcp_case_runner.py server_fixed.py

# ③ pytest 自动化（已知缺陷标记为 xfail，修好后自动变 xpassed）
pytest test_mcp_basic.py -v
$env:MCP_SERVER_FILE="server_fixed.py"; pytest test_mcp_basic.py -v; Remove-Item Env:MCP_SERVER_FILE
```

### 用官方 Inspector 手动调试 / 抓包

```powershell
# Web UI：浏览器打开 http://localhost:6274
npx -y @modelcontextprotocol/inspector python server.py

# CLI：把工具清单输出成 JSON
npx -y @modelcontextprotocol/inspector --cli python server.py --method tools/list --format json
```

---

## 测试结果摘要

同一套 24 条用例，对两个版本各执行一次：

| 指标 | 未加固 `server.py` | 加固后 `server_fixed.py` |
|------|-------------------|-------------------------|
| PASS | 18 | **22** |
| FAIL | **4** | **0** |
| SKIP（未覆盖，已说明原因） | 2 | 2 |
| 通过率（不含 SKIP） | 81.8% | **100.0%** |

### 测出的 5 个缺陷

| 编号 | 缺陷 | 严重度 |
|------|------|--------|
| MCP-001 | `add_task` 不校验空标题，空字符串照样创建成功 | 中 |
| MCP-002 | `add_task` 不限制标题长度，10000 字符照单全收 | 中 |
| MCP-003 | `delete_task` 删除不存在的 id 仍返回 `deleted`（**假成功**，最危险） | 高 |
| MCP-004 | `delete_task` 传空 id 仍返回 `deleted` | 中 |
| MCP-005 | `list_tasks` 返回的是 Python repr 而不是合法 JSON，跨语言客户端无法解析 | 低 |

详细复现步骤、影响与修复建议见 [`协议测试记录.md`](./协议测试记录.md)。

---

## 上游缺陷复现

在官方 `@modelcontextprotocol/inspector` **2.7.0** 上做真实复现（Windows 11 / Node v22.23.2）：

| 上游 issue | 内容 | 我的结果 |
|-----------|------|---------|
| [#2412](https://github.com/modelcontextprotocol/inspector/issues/2412) | CLI 流式路径未捕获 EPIPE 导致进程崩溃 | **复现成功**，并把触发条件精确定位到"单次输出 > 64 KB 管道缓冲区" |
| [#2403](https://github.com/modelcontextprotocol/inspector/issues/2403) | CLI/TUI 宣称支持 MCP Apps 但渲染不了 | **复现成功**，抓到原始 `initialize` 报文，其中确实声明了 `io.modelcontextprotocol/ui` |
| [#2416](https://github.com/modelcontextprotocol/inspector/issues/2416) | Windows 路径分隔符缺少测试覆盖 | **未复现出故障**，判定为测试盲区而非运行时缺陷 |

完整证据、对照实验与给上游的留言模板见 [`上游缺陷复现.md`](./上游缺陷复现.md)，
复现脚本在 [`upstream-repro/`](./upstream-repro/)。

---

## 目录结构

```text
06-mcp-lab/
├─ server.py                     被测对象（保留 5 个故意的校验缺口）
├─ server_fixed.py               加固版（修复全部 5 个缺陷）
├─ mcp_case_runner.py            24 条协议用例自动执行器（纯 JSON-RPC，不依赖 CLI 参数差异）
├─ test_mcp_basic.py             pytest 自动化用例（xfail 表达已知缺陷）
├─ tools.json                    Inspector CLI 导出的工具清单
├─ cases_result_*.json / .csv    两次执行的真实结果原始数据
├─ 协议测试记录.md                24 条用例结果 + 5 个缺陷详情 + 加固前后对比
├─ 上游缺陷复现.md                3 个上游 issue 的复现报告与证据
└─ upstream-repro/
   ├─ big_server.py              夹具：返回超大响应，用于触发 EPIPE
   ├─ repro_driver.js            驱动器：建立真实 OS 管道并提前关闭读端
   └─ spy_server.py              抓包服务器：录下客户端发来的原始 JSON-RPC 报文
```

---

## 用到的知识与技术

* **协议**：MCP 2025-06-18 / 2025-11-25，JSON-RPC 2.0，stdio 传输，
  `initialize` 握手 + `notifications/initialized` 顺序
* **两层错误通道**：JSON-RPC 层 `error` vs 工具层 `result.isError`（判定用例时必须都认）
* **测试设计**：等价类 / 边界值（空值、超长、特殊字符）、错误处理、幂等与假成功、
  稳定性（连续调用、超大 payload）、安全（路径穿越、命令注入）
* **自动化**：pytest + 子进程 stdio 客户端、`xfail` 表达已知缺陷、结果落 JSON/CSV
* **工具**：MCP Inspector（Web / CLI）、MCP Python SDK 2.x

## 已知限制（如实记录）

1. **真实并发未覆盖** —— stdio 是单连接串行，用例 19 只是"快速连续调用"；
   真并发需切换 HTTP/SSE 传输后压测
2. **stdio 下服务端日志不可见** —— stdout 被协议占用，调试信息只能走 stderr 或文件
3. **超时与内存未覆盖（用例 21 / 24）** —— 需要额外夹具与外部监控工具，已在报告中说明补齐方式
