# AI 客服系统全链路质量保障体系

> 一个**自研 AI 客服系统**作为被测对象，围绕它落地两大测试体系：
> **项目一（传统工程维度）**：接口 → 契约 → 数据库一致性 → 性能 → 持续集成
> **项目二（AI 专项维度）**：RAG → 大模型质量 → 安全红队 → Agent 行为与协议 → AI UI
>
> 全部用例、原始数据、测试报告、证据截图都在本仓库里，**每个数字都能追溯到具体文件**。

---

## 30 秒看结果

| 层次 | 工具 | 规模 | 关键结果 |
|------|------|------|---------|
| 接口测试 | Hurl | **39 条**用例 | 26 通过 / 13 失败 → 逐条归因后 **4 个真缺陷** |
| 契约测试 | Schemathesis | **727 条**自动生成 | 11 条失败 → 归因后 **2 个真缺陷** |
| 数据库一致性 | pytest + sqlite3 | **15 条** API↔DB 交叉校验 | 12 通过 / 3 预期失败，为越权缺陷补齐**数据层证据** |
| 性能测试 | Locust | 5 档并发（10 → 400） | 吞吐 **4.99 → 172.42 RPS**，P95 **14 → 70 ms** |
| 性能对照 | JMeter | 10 并发 / 40 请求 | 平均 **12.2 ms**、P95 **40 ms**、错误率 **0%**，并产出 HTML 报告 |
| 接口调试与抓包 | Postman + Fiddler | — | 越权删除 **204** 双工具复现；响应篡改 **数据库 `false` → 客户端 `true`** |
| 数据质量核查 | Navicat | 8 条核查 SQL | **1830 行**中查出 2 条空标题脏数据；最长标题恰好 **100** |
| 测试报告 | Allure | **17 条**用例 | 14 通过 / 3 预期失败（HTML 报告可离线打开） |
| 大模型质量 | DeepEval | **45 条** / 8 维度 | 逐题标准差 **≤0.05**；裁判可靠人工验证 **一致率 90%** |
| 安全红队 | Promptfoo | OWASP LLM Top10 | 攻击成功率 **26.92% → 0%** |
| 大模型性能 | EvalScope | 7 档并发 | TTFT **385 → 522 ms（+36%）**，7 档吞吐 0.18 → 16.21 RPS |
| RAG 检索评测 | text-embedding-v3 + DeepEval | 13 条 | **Recall@1 = 100%**，5 个 RAG 指标达标；ContextualPrecision **0.625 → 1.000** |
| Agent 行为 | function calling + pytest | **17 条**（11 基础 + 6 对抗） | 挖出 AGENT-001「工具脏数据原样回显」，加固后 17 passed |
| 智能体协议 | MCP Inspector | **24 条** | 定位 **5 个自研缺陷**、复现 **3 个上游 issue**，回归 **81.8% → 100%** |
| AI UI 自动化 | Midscene + Playwright | 7 条 × 5 轮 | **flaky 率 0%**（35 次执行） |

---

## 目录结构

```text
qa-demo-api-test/
├── 00-demo-api/          被测系统（FastAPI + SQLite，6 个接口，内含 4 个已知缺陷）
├── 01-hurl-lab/          Hurl 接口自动化（39 条用例 + JUnit/HTML 报告）
├── 02-api-attr-lab/      Schemathesis 契约测试（727 条自动生成用例）
├── 03-perf-lab/          Locust 性能测试（5 档并发 + 对照实验）
├── 04-llm-eval-lab/      DeepEval 大模型评测 + Promptfoo 红队 + EvalScope 推理压测
├── 05-midscene-lab/      Midscene + Playwright 视觉驱动 UI 自动化
├── 06-mcp-lab/           MCP Server + MCP Inspector 协议一致性测试
├── 07-db-lab/            数据库一致性测试（API ↔ DB 交叉校验）
├── 08-agent-lab/         function calling Agent 行为与对抗测试
├── 09-rag-lab/           RAG 检索增强测试（分块 → embedding → 检索 → 生成）
└── 10-tools-lab/         热门工具链实操（Postman / Fiddler / JMeter / Navicat / Allure）
```

---

## 项目一 · 传统工程维度（5 层）

| 模块 | 层次 | 工具 | 产出 |
|------|------|------|------|
| [01-hurl-lab](01-hurl-lab/) | 接口功能与安全 | Hurl | 39 条用例（正常流 / 边界值 / 参数类型 / 异常码 / 幂等 / 安全）→ [Hurl 测试报告](01-hurl-lab/reports/) |
| [02-api-attr-lab](02-api-attr-lab/) | 契约测试 | Schemathesis | 727 条自动生成用例 + [失败分类归因](02-api-attr-lab/失败分类.md) |
| [03-perf-lab](03-perf-lab/) | 性能测试 | Locust | 5 档并发梯度 + 对照实验 → [性能测试报告](03-perf-lab/性能测试报告.md) |
| [07-db-lab](07-db-lab/) | 数据库一致性 | pytest + sqlite3 | 15 条 API↔DB 交叉校验 → [数据库一致性测试报告](07-db-lab/数据库一致性测试报告.md) |
| [10-tools-lab](10-tools-lab/) | 接口调试 / 抓包 / 性能对照 / 数据核查 / 报告 | Postman、Fiddler、JMeter、Navicat、Allure | [接口调试记录](10-tools-lab/postman/接口调试记录.md)、[抓包分析](10-tools-lab/fiddler/抓包分析.md)、[JMeter 说明](10-tools-lab/jmeter/JMeter性能测试说明.md)、[数据库核查说明](10-tools-lab/navicat/数据库核查说明.md)、[Allure 报告说明](10-tools-lab/allure/Allure报告说明.md) |

**持续集成**：`.github/workflows/` 下有三条流水线（`api-test.yml` 接口回归、`llm-quality.yml` 大模型质量门禁、
`ui-ai-test.yml` AI UI 测试），提交时自动拉起被测服务 → 健康检查 → 执行用例 → 归档报告。

---

## 项目二 · AI 专项维度（5 层）

| 模块 | 层次 | 工具 | 产出 |
|------|------|------|------|
| [09-rag-lab](09-rag-lab/) | RAG 检索与生成质量 | text-embedding-v3、DeepEval | 13 条用例、Recall@K 曲线、5 个 RAG 指标 → [RAG 测试报告](09-rag-lab/RAG测试报告.md) |
| [04-llm-eval-lab](04-llm-eval-lab/) | 大模型质量 / 红队 / 推理性能 | DeepEval、Promptfoo、EvalScope | 45 条 8 维度评测 + 非确定性量化 + 质量门禁 → [评测报告](04-llm-eval-lab/大模型评测与性能测试报告.md)、[门禁说明](04-llm-eval-lab/LLM质量门禁说明书.md) |
| [08-agent-lab](08-agent-lab/) | Agent 行为与对抗 | function calling + pytest | 17 条用例（11 基础 + 6 对抗）→ [Agent 行为测试报告](08-agent-lab/Agent行为测试报告.md) |
| [06-mcp-lab](06-mcp-lab/) | 智能体工具协议 | MCP SDK + MCP Inspector | 24 条协议用例 + 上游复现 → [协议测试记录](06-mcp-lab/协议测试记录.md)、[上游缺陷复现](06-mcp-lab/上游缺陷复现.md) |
| [05-midscene-lab](05-midscene-lab/) | AI UI 自动化 | Midscene + Playwright | 7 条 × 5 轮 flaky 统计 → [AI-UI 自动化测试报告](05-midscene-lab/AI-UI自动化测试报告.md) |

---

## 被测系统（`00-demo-api`）

一个为测试练习而写的 FastAPI 客服系统，**故意埋了 4 个缺陷**（先用测试发现，再去 [app.py](00-demo-api/app.py) 对照答案）。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/login` | POST | 登录，返回 Bearer token（内存态，服务重启失效） |
| `/tasks` | POST | 创建任务（需要 Authorization） |
| `/tasks` | GET | 任务列表（**不需要鉴权**） |
| `/tasks/{id}` | GET | 任务详情 |
| `/tasks/{id}` | DELETE | 删除任务（**未校验 Authorization ← 缺陷 D3**） |
| `/chat` | POST | 大模型客服问答（RAG / Agent 的入口） |

* 测试账号：`tester` / `123456`
* 接口文档：服务启动后访问 `http://127.0.0.1:8000/docs`
* 数据存储：SQLite 单文件 `tasks.db`

---

## 发现的缺陷总表

| 编号 | 缺陷 | 严重级别 | 证据 | 状态 |
|------|------|---------|------|------|
| **D3** | `DELETE /tasks/{id}` 未校验身份，未授权即可删除他人数据 | **高危** | Postman 204 + Fiddler 抓包（请求头无 Authorization）+ Navicat 行数 N→N-1 | 已出报告与修复建议 |
| **D2** | 查询不存在的任务返回 **500**（应为 404） | 中 | [Postman 截图](10-tools-lab/postman/04-不存在的id返回500.png) | 已出报告与修复建议 |
| **D1** | 标题长度限制（>100 字符返回 422）**未写入接口文档** | 中 | 101 字符 422 / 100 字符 201 对照 | 已出报告与修复建议 |
| **D4** | `done` 字段类型不一致（创建返回 `0`，列表/详情返回 `false`） | 低 | 两个接口响应对比 | 已出报告与修复建议 |
| **安全** | 纯 HTTP 下**响应可被中间人篡改**（数据库 `false` → 客户端 `true`） | **高危** | [Fiddler 改包证据](10-tools-lab/fiddler/) | 已给加固建议（HTTPS + 证书校验） |
| **数据** | 空标题 / 纯空格标题未校验，**脏数据落库**（2 条） | 低 | Navicat 核查 + pytest `xfail` 双份证据 | 已出报告与修复建议 |
| **AGENT-001** | Agent 把工具返回数据里的 `<script>` **原样回显给用户** | 中 | [Agent 行为测试报告](08-agent-lab/Agent行为测试报告.md) | ✅ 已加固提示词，17 passed |
| **RAG-注入** | 知识库内嵌指令被模型当命令执行 | **高危** | [RAG 测试报告](09-rag-lab/RAG测试报告.md) | ✅ 已按来源可信度分级修复，模型可主动告警 |
| **RAG-检索** | markdown 标题碎片抢占检索位（Precision 0.625） | 中 | RAG 测试报告 | ✅ 已改切分策略，0.625 → 1.000 |
| **MCP×5** | 含"删除不存在的 id 仍返回成功"等 5 个协议层缺陷 | 中 | [协议测试记录](06-mcp-lab/协议测试记录.md) | ✅ 已修复，回归 81.8% → 100% |

---

## 怎么本地跑起来

**环境要求**：Python 3.13、Node.js 20+、JDK 17（JMeter / Allure 需要）、Git。

```powershell
# ① 启动被测服务（新开一个终端，保持不关）
cd 00-demo-api
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --port 8000

# ② 跑接口用例（Hurl 需要先安装 hurl）
cd ..\01-hurl-lab
.\run.ps1

# ③ 跑数据库一致性用例
cd ..\07-db-lab
..\00-demo-api\.venv\Scripts\python.exe -m pytest test_db_consistency.py -v

# ④ 生成 Allure 报告
..\00-demo-api\.venv\Scripts\python.exe -m pytest test_db_consistency.py -v --alluredir=..\10-tools-lab\allure\results
allure generate ..\10-tools-lab\allure\results -o ..\10-tools-lab\allure\report --clean
allure open ..\10-tools-lab\allure\report

# ⑤ JMeter 对照压测（非 GUI）
jmeter -n -t ..\10-tools-lab\jmeter\qa-demo-api.jmx -l ..\10-tools-lab\jmeter\result.jtl -e -o ..\10-tools-lab\jmeter\report
```

> 详细的分步手册在 `10-tools-lab/**/` 与各模块的 `README.md` / `*报告.md` 里。

---

## 每个模块解决什么问题（速查）

| 问题 | 归属模块 | 一句话 |
|------|---------|-------|
| 接口契约和实现是否一致？ | 01 / 02 / 10-tools-lab | 手工用例发现"业务语义"问题，自动生成补充"机器穷举"边界 |
| 接口返回成功，数据真的对吗？ | 07 / 10-tools-lab(navicat) | 用只读连接做 API↔DB 交叉校验，把"返回码问题"升级为"数据破坏"证据 |
| 服务能扛多少并发？瓶颈在哪？ | 03 / 10-tools-lab(jmeter) | 梯度压测 + **对照实验否定自己的假设** |
| 大模型输出不确定，怎么断言？ | 04 | 用「指标 + 阈值 + 多轮统计」替代等值断言 |
| 怎么证明防护是有效的？ | 04 / 09 | 红队前后对比；并检查"攻击是否真的送达"（警惕安慰剂测试） |
| RAG 答错是检索错还是生成错？ | 09 | 检索层与生成层**分层测**，各自有独立指标 |
| Agent 会不会乱调工具？ | 08 | 行为用例 + 对抗变体（批量破坏、工具结果注入） |
| 工具/协议层是否合规？ | 06 | 协议级一致性用例 + 上游 issue 复现 |
| UI 自动化一改就挂怎么办？ | 05 | 视觉模型 + 确定性 API 的**混合模式** |
| 结果怎么交付？ | 10-tools-lab(allure) | 统一渲染成可离线打开的 HTML 报告 |

---

## 已知不足（主动说明）

* **性能压测是本机单机压测**，压测机与被测机同机，未做分布式压测与生产链路压测；
* **JMeter 那轮只有 40 个请求**，属"接口回归式对照压测"，不是容量压测；
* **Locust 与 JMeter 的脚本口径不同**（一个带思考时间的混合场景，一个无等待的固定流），
  因此**只对比趋势、不做吞吐数值对比**；
* 长上下文的大模型性能维度未覆盖，已在对应报告中说明原因；
* Allure 报告目前只汇总了数据库一致性与 RAG 关键用例，Agent / MCP 用例尚未纳入同一份报告。

---

## 说明

* 被测系统（`00-demo-api`）与 MCP Server、Agent、RAG 链路均为**作者自研代码**，用于测试练习；
  系统内的缺陷是**刻意埋设**的（见 `00-demo-api/app.py` 文末的 DEFECTS 说明），
  目的是让测试能真实地发现并归因问题；
* 用到的第三方工具均为开源或免费版本（Hurl、Locust、Schemathesis、DeepEval、Promptfoo、
  EvalScope、Midscene、Playwright、MCP Inspector、Postman、Fiddler Classic、JMeter、Allure）；
* 仓库中的截图、报告与数字均来自**本仓库代码的真实执行结果**。
