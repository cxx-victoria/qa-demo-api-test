# Allure 测试报告手册（零基础 · 点哪一下都写清楚）

> **本次目标**：把已经写好的 pytest 用例，用 **Allure** 生成一份
> **能直接给面试官看的 HTML 测试报告**（用例数、通过率、耗时、失败详情）。
>
> 你现在的 pytest 只能输出一堆黑底白字，Allure 就是把它变成"**报告**"的那一层。

---

## 第 0 章 · 前置检查

Allure 命令本身是 **Java 写的**，所以第一件事是确认 Java 在：

```powershell
java -version
```

* 有版本号 → 跳到第 1 章
* 报"无法将 java 项识别为…" → 先做 **10-5（JMeter）手册的第 0 章** 装 Java
  （装一次，JMeter 和 Allure 都能用）

还需要：一个**已经能跑通的 pytest 测试集**。你手上有三个：

| 目录 | 测试文件 | 之前的结果 |
|------|---------|-----------|
| `D:\qa-projects\07-db-lab` | `test_db_consistency.py` | 12 passed, 3 xfailed |
| `D:\qa-projects\08-agent-lab` | `test_agent_behavior.py` + `test_agent_adversarial.py` | 17 passed |
| `D:\qa-projects\09-rag-lab` | `test_rag_quality.py` | 全部通过 |

---

## 第 1 章 · 安装 allure-commandline（约 5 分钟）

### 1.1 下载

1. 浏览器打开：`https://github.com/allure-framework/allure2/releases`
2. 在最新版本那一栏找 **`Assets`** → 下载 **`allure-2.x.x.zip`**
   （**不要**下 `.jar`，也不要下 Source code）
3. 解压到：`D:\tools\allure-2.30.0`

   > 解压后确认里面有一个 **`bin`** 文件夹，`bin` 里有 **`allure.bat`**。
   > 路径同样**不要带中文和空格**。

### 1.2 加到 PATH（永久生效，推荐）

打开 PowerShell，执行下面这一整段：

```powershell
[Environment]::SetEnvironmentVariable(
  'Path',
  [Environment]::GetEnvironmentVariable('Path','User') + ';D:\tools\allure-2.30.0\bin',
  'User')
```

**然后把 PowerShell 关掉重新开一个**，执行：

```powershell
allure --version
```

看到版本号就成功了。

> 不想改 PATH 也行，**每次用完整路径**：
> `& 'D:\tools\allure-2.30.0\bin\allure.bat' --version`

---

## 第 2 章 · 给 pytest 装 Allure 插件（1 分钟）

pytest 要靠一个插件才能把结果写成 Allure 认识的格式。
**用你已有的那个虚拟环境**（不用新建）：

```powershell
& 'D:\qa-projects\00-demo-api\.venv\Scripts\python.exe' -m pip install allure-pytest
```

---

## 第 3 章 · 跑一个测试集，生成"原始结果"（约 2 分钟）

```powershell
cd D:\qa-projects\07-db-lab
New-Item -ItemType Directory -Force -Path 'D:\qa-projects\10-tools-lab\allure\results' | Out-Null
& 'D:\qa-projects\00-demo-api\.venv\Scripts\python.exe' -m pytest test_db_consistency.py -v `
  --alluredir='D:\qa-projects\10-tools-lab\allure\results'
```

**期望**：和之前一样 **12 passed, 3 xfailed**。

跑完之后 `results` 目录里会多出一堆 `.json` / `.txt` 文件 ——
这些是 Allure 的**原始数据，人看不懂是正常的**，下一步才渲染成报告。

---

## 第 4 章 · 生成并打开 HTML 报告（1 分钟）

```powershell
allure generate 'D:\qa-projects\10-tools-lab\allure\results' `
  -o 'D:\qa-projects\10-tools-lab\allure\report' --clean

allure open 'D:\qa-projects\10-tools-lab\allure\report'
```

第二条命令会自动**在浏览器里打开报告**（它会临时起一个本地小服务）。

> ⚠️ **不要直接双击 `report\index.html`** —— Allure 报告需要 http 服务才能正常加载，
> 双击大概率白屏。**一定要用 `allure open`**。

---

## 第 5 章 · 报告里要看什么（面试会问）

| 区域 | 看什么 |
|------|-------|
| **Overview 首页** | 用例总数、通过 / 失败 / 预期失败、总耗时、饼图 |
| **Suites / Behaviors** | 按类名或功能分组看用例列表 |
| **单个用例** | 执行时间、参数、失败时的完整堆栈 |
| **Trends** | 多次运行才有的通过率趋势 |

👉 **截图**：Overview 首页 → `01-Allure报告总览.png`
👉 **截图**：Suites 用例列表 → `02-Allure用例列表.png`

---

## 第 6 章 · 把几个测试集合到一份报告里（约 5 分钟）

把多次运行的结果**写进同一个目录**，就能生成一份合并报告：

```powershell
$py  = 'D:\qa-projects\00-demo-api\.venv\Scripts\python.exe'
$out = 'D:\qa-projects\10-tools-lab\allure\results-all'

# ① 数据库一致性
cd D:\qa-projects\07-db-lab
& $py -m pytest test_db_consistency.py -v --alluredir=$out

# ② RAG 质量
cd D:\qa-projects\09-rag-lab
& $py -m pytest test_rag_quality.py -v --alluredir=$out

# ③ 生成合并报告
allure generate $out -o 'D:\qa-projects\10-tools-lab\allure\report-all' --clean
allure open 'D:\qa-projects\10-tools-lab\allure\report-all'
```

> 💡 想把 Agent 那套（`08-agent-lab`）也加进来，要先设环境变量
> `$env:DEMO_API = 'http://127.0.0.1:8000'`，而且它跑得慢（约 50 秒），跑不跑都行。

---

## 第 7 章 · 产出清单

放进 `D:\qa-projects\10-tools-lab\allure\`：

| 文件 | 内容 |
|------|------|
| `results\` | 原始结果（可以提交，也可以忽略） |
| `report\index.html` | **单测试集的 HTML 报告**（提交 Git） |
| `report-all\index.html` | 合并报告 |
| `01-Allure报告总览.png` | Overview 截图 |
| `02-Allure用例列表.png` | 用例列表截图 |
| `Allure报告说明.md` | 说明文档（我可以帮你生成） |

> 💡 提交到 GitHub 时，`report/` 里会有几十个 js/css 静态文件，这是正常的，
> 全部提交进去；别人 clone 下来用 `allure open` 就能看。

---

## 第 8 章 · 常见问题

| 现象 | 原因 | 怎么办 |
|------|------|-------|
| `allure` 不是内部或外部命令 | PATH 没生效 | **重开** PowerShell；或用完整路径 `& 'D:\tools\allure-2.30.0\bin\allure.bat'` |
| 报 `JAVA_HOME is not set` | Java 没装好 | 回 10-5 第 0 章，注意勾 `JAVA_HOME` |
| 报目录已存在 / 结果残留 | 上次结果还在 | 生成时加 **`--clean`** |
| 报告打开是白屏 | 直接双击了 `index.html` | 用 **`allure open`** |
| `results` 目录是空的 | 没装 `allure-pytest`，或 `--alluredir` 路径写错 | 重做第 2、3 章 |
| 用例数不对 | 跑的是别的测试文件 | 看清 `cd` 到了哪个目录、pytest 后面跟的文件名 |
