# 你的第一个测试项目：Hurl 接口测试

## 这个文件夹是什么

这是**测试代码**（不是被测系统）。被测系统是隔壁的 `../demo-api`。

```
outputs/demo-api/   ← 被测系统（被测试的那个程序）
outputs/hurl-lab/   ← 测试代码（你写的用例）
```

## 用之前先确认两件事

1. **被测服务必须在运行**（另开一个终端）：
   ```powershell
   cd D:\qa-projects\00-demo-api
   .\.venv\Scripts\Activate.ps1
   uvicorn app:app --port 8000
   ```
   看到 `Uvicorn running on http://127.0.0.1:8000` 就对了，**这个窗口不要关**。

2. **hurl 必须可用**：
   ```powershell
   hurl --version        # 没装就：winget install hurl
   ```

## 怎么跑

```powershell
cd D:\qa-projects\01-hurl-lab
.\run.ps1
```

或者一条条来，第一次建议这样，看得更清楚（**注意：PowerShell 不会给 hurl 展开通配符，
所以下面每条都写全文件名，不要用 `cases\*.hurl`**）：

```powershell
hurl --test cases\00_smoke.hurl                       # 冒烟：应该 PASS
hurl --test cases\10_flow_login_create_query.hurl      # 业务流：应该 PASS
hurl --test cases\20_boundary_login_fail.hurl          # 异常：应该 PASS
hurl --test cases\30_defect_D1_long_title.hurl         # 找缺陷：预期 FAIL
hurl --test cases\31_defect_D2_missing_id.hurl         # 找缺陷：预期 FAIL
hurl --test cases\32_defect_D3_delete_without_auth.hurl# 找缺陷：预期 FAIL
hurl --test cases\33_defect_D4_done_type.hurl          # 找缺陷：预期 FAIL
```

> 如果嫌麻烦，直接用 `.\run.ps1`，它已经帮你把文件列表和报告都处理好了。

## 怎么读结果

hurl 的输出里：

* `Success: 2, Failed: 0` → 用例通过，系统行为符合预期
* `Success: 1, Failed: 1` → **有失败，说明发现了问题或环境不对**
* 失败时会打印 `Assert failure` 或 `HTTP 500` 之类的对比信息

**关键认知：测试用例失败不是你的错，失败=你发现了缺陷。** 一个永远全绿的测试套件，往往是不敢断言的测试套件。

## 你这次能找到的 4 个缺陷（都写在 app.py 末尾的答案卡里）

| 文件 | 缺陷 | 期望 | 实际 |
|------|------|------|------|
| 30_defect_D1 | 契约与实现不一致（超长标题） | 201 创建成功 | 422 未文档化错误 |
| 31_defect_D2 | 查不存在的 id 返回 500 | 404 | 500 |
| 32_defect_D3 | 删除接口没有鉴权 | 401 | 204（真删掉了） |
| 33_defect_D4 | done 返回整数而非布尔 | true/false | 0/1 |

## 找到之后要做什么（这才是完整的测试工作）

1. 每条缺陷写一条**缺陷报告**（模板见下）
2. 用 `hurl --test --report-junit` 生成报告，放进 `reports/`
3. 在 `Bugs.md` 里汇总成一个表格（面试官爱看这个）

**缺陷报告模板**：

```markdown
### BUG-001 查询不存在的任务返回 500 而非 404

* 严重程度：中（线上会产生错误告警、泄漏堆栈）
* 复现环境：Windows 11 / demo-api 1.0.0 / 本地 8000 端口
* 复现步骤：
  1. 启动服务 uvicorn app:app --port 8000
  2. 执行 GET http://127.0.0.1:8000/tasks/this-id-does-not-exist
* 期望结果：返回 404 Not Found
* 实际结果：返回 500 Internal Server Error，日志出现 AttributeError
* 证据：cases/31_defect_D2_missing_id.hurl 执行失败的截图
* 建议：查询结果为空时显式 raise HTTPException(404)
```
