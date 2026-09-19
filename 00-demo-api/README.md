# QA Demo API（被测系统）

一个专门用来练测试的极简服务：**5 个接口 + 4 个故意埋的缺陷**。

## 快速开始

```powershell
uv venv --python 3.13
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

* 接口文档（OpenAPI）：http://127.0.0.1:8000/docs
* OpenAPI JSON（喂给 Schemathesis）：http://127.0.0.1:8000/openapi.json

## 接口清单

| 方法 | 路径 | 说明 | 需要鉴权 |
|------|------|------|----------|
| POST | `/login` | 登录，用户名 `tester` / 密码 `123456` | 否 |
| POST | `/tasks` | 创建任务 | 是 |
| GET | `/tasks` | 任务列表（支持 `limit` / `offset`） | 否 |
| GET | `/tasks/{id}` | 任务详情 | 否 |
| DELETE | `/tasks/{id}` | 删除任务 | **（故意没校验）** |
| POST | `/chat` | LLM 客服问答（配了 `OPENAI_BASE_URL`/`OPENAI_API_KEY` 才真调模型） | 否 |

## 埋的 4 个缺陷

**先自己测，找到再回来看。** 答案在 `app.py` 文件末尾的 `DEFECTS` 注释里。

提示：

* 一个用 Schemathesis 跑 `--checks all` 就能自动暴露
* 一个用"查询不存在的 id"就能暴露
* 一个用"不带 token 直接发请求"就能暴露
* 一个需要断言返回值的**类型**，而不是值本身

## 用它练什么

| 测试类型 | 工具 | 目标 |
|----------|------|------|
| 接口功能 | Hurl | 35 条用例覆盖正常/边界/异常/业务流 |
| 契约 & 自动生成 | Schemathesis | 自动生成 1000+ 用例，找出 4 个缺陷 |
| 性能 | Locust | 并发梯度，找拐点，观察 sqlite 并发写锁 |
| 大模型质量 | DeepEval / Promptfoo | 测 `/chat` 的相关性、幻觉、注入防护 |

## 运行时产生的文件（正常现象）

服务启动后会自动生成两个文件/目录，它们**不是代码的一部分**，可以随时删掉，
也可以写进 `.gitignore`：

* `tasks.db` —— SQLite 数据库（存放你创建的任务）
* `__pycache__/` —— Python 的编译缓存

想每次从干净状态开始测试，就停掉服务、删掉 `tasks.db`、再重启。
