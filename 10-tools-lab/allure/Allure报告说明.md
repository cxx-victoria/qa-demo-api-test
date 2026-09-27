# Allure 测试报告说明

## 1. 目标

把 pytest 的命令行输出，变成一份**可以交付、可以给面试官直接打开的 HTML 测试报告**：
用例总数、通过率、执行耗时、失败详情与附件一目了然。

---

## 2. 环境

| 项目 | 内容 |
|------|------|
| 报告工具 | **Allure Commandline 2.x**（解压即用，需 Java） |
| 运行时 | Eclipse Temurin JDK 17（与 JMeter 共用同一套 Java） |
| 采集插件 | `allure-pytest`（装在 `00-demo-api` 的虚拟环境里） |
| 被测用例 | `07-db-lab/test_db_consistency.py`、`09-rag-lab/test_rag_quality.py` |
| 报告目录 | `10-tools-lab/allure/report/`（单次）、`results-all/`（合并结果） |

---

## 3. 执行命令

```powershell
$py  = 'D:\qa-projects\00-demo-api\.venv\Scripts\python.exe'
$out = 'D:\qa-projects\10-tools-lab\allure\results-all'

# ① 采集结果（--alluredir 指向同一个目录即可合并多套用例）
cd D:\qa-projects\07-db-lab
& $py -m pytest test_db_consistency.py -v --alluredir=$out

cd D:\qa-projects\09-rag-lab
& $py -m pytest test_rag_quality.py -v --alluredir=$out

# ② 渲染成 HTML 报告
allure generate $out -o 'D:\qa-projects\10-tools-lab\allure\report' --clean

# ③ 打开报告（会临时起本地服务）
allure open 'D:\qa-projects\10-tools-lab\allure\report'
```

> ⚠️ **不要直接双击 `report/index.html`** —— Allure 报告需要 http 服务才能加载，双击会白屏。

---

## 4. 实测结果

**总计 17 条用例：14 条通过、3 条预期失败**（pytest 的 `xfail` 在 Allure 中显示为 `skipped`）

### 4.1 通过（14 条）

| 用例 | 所属 |
|------|------|
| `test_test_db_is_same_file_service_writes` | 数据库一致性（同源自检） |
| `test_create_persists_to_db` | 数据库一致性 |
| `test_delete_removes_row_from_db` | 数据库一致性 |
| `test_delete_twice_keeps_db_clean` | 数据库一致性 |
| `test_api_list_matches_db_rows` | 数据库一致性 |
| `test_list_pagination_is_consistent` | 数据库一致性 |
| `test_title_100_chars_is_persisted` | 数据库一致性（边界内） |
| `test_title_101_chars_is_not_persisted` | 数据库一致性（边界外） |
| `test_done_field_type_in_db` | 数据库一致性 |
| `test_all_ids_are_valid_uuid_hex` | 数据库一致性（全表完整性） |
| `test_all_titles_are_non_null` | 数据库一致性（全表完整性） |
| `test_concurrent_creates_all_persisted` | 数据库一致性（并发写入） |
| `test_answers_contain_key_facts` | RAG 质量 |
| `test_deepeval_rag_metrics` | RAG 质量（DeepEval 指标） |

### 4.2 预期失败（3 条，`xfail`）

| 用例 | 对应的已知缺陷 |
|------|--------------|
| `test_unauthorized_delete_should_be_rejected` | **D3**：`DELETE /tasks/{id}` 未校验身份，未授权请求返回 204 |
| `test_unauthorized_delete_must_not_touch_data` | **D3**：未授权删除不仅返回码错，**数据真的被删了** |
| `test_empty_title_should_not_be_persisted` | 空标题 / 纯空格未被校验，会作为脏数据落库（Navicat 侧查到 2 条） |

> **为什么要用 `xfail` 而不是删掉这三条？**
> 因为它们是**已知缺陷的守护网**：
> * 缺陷还在 → 用例继续标记为预期失败，**测试套件保持绿色**；
> * 缺陷被修复 → 用例变成 `XPASS`，**立刻提醒我更新标记并把它转成普通断言**；
> * 万一修复引入了回归 → 用例直接失败。
>
> 这比"把已知问题注释掉"专业得多。

---

## 5. 报告怎么看

| 区域 | 内容 |
|------|------|
| **Overview** | 用例总数、通过 / 失败 / 预期失败、总耗时、状态饼图 |
| **Suites** | 按测试文件分组列出用例 |
| **单条用例** | 执行耗时、失败堆栈、附件（如控制台输出） |
| **Trends** | 多次执行才有（需要保留历史结果目录） |

> 💡 面试时可以直接 `allure open` 打开报告演示 ——
> **不需要现场跑代码就能证明"这些用例真的存在、真的跑过"**。

---

## 6. 结论

1. 17 条用例全部有明确状态：**14 通过、3 条为已标记的已知缺陷**，没有"被隐藏的失败"；
2. 报告把"预期失败"这种语义**正大光明地展示**出来（skipped），
   并说明原因（对应 D3 越权 / 空标题脏数据）；
3. 报告可离线打开、可提交进仓库，形成"**代码 + 报告 + 证据截图**"的完整交付物。

---

## 7. 局限

| 局限 | 说明 |
|------|------|
| 只覆盖两个测试文件 | Agent 行为、MCP 协议、大模型评测等未纳入同一份报告 |
| 无历史趋势 | 未保留多轮 `results/` 目录，Trends 页暂无数据 |
| 未加用例级标注 | 还没有用 `@allure.title` / `@allure.step` 做中文用例名与步骤分解 |

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `report/index.html` | HTML 报告入口（用 `allure open` 查看） |
| `results/` | 数据库一致性用例的原始结果 |
| `results-all/` | 合并结果（数据库一致性 + RAG） |
| `01-Allure报告总览.png` | Overview 截图 |
| `02-Allure用例列表.png` | Suites 用例列表截图 |
