# Fiddler Classic 抓包手册（零基础 · 点哪一下都写清楚）

> **为什么还要用 Fiddler**：Postman 是"**自己构造请求**"，Fiddler 是"**录下真实流量**"，
> 两件事不一样。简历上"抓包"这个词用 Fiddler 来撑最省事：
> **免费、不会像 Charles 那样 30 分钟退出、Windows 原生。**
>
> **本次目标**：用一个**完全不同的工具**，独立把上一次的完整业务流再抓一遍，
> 并做一次"**中途改包**" —— 两个工具交叉验证，证据才算硬。

---

## 第 0 章 · 做完这些你要拿到什么

全部放进 `D:\qa-projects\10-tools-lab\fiddler\`：

| 文件 | 内容 |
|------|------|
| `01-Fiddler抓到完整业务流.png` | 列表里四条请求 200 / 201 / 200 / 204 |
| `02-Fiddler里的Authorization头.png` | Inspectors 里看到的请求头 |
| `03-断点改包-请求被拦下.png` | Fiddler 把请求拦住、等你改 |
| `04-响应被篡改-done变true.png` | 改完响应后客户端收到被篡改的数据 |
| `business-flow.saz` | 整个抓包会话存档（面试可现场回放） |
| `business-flow.txt` | 纯文本证据（含完整请求头 / 响应头） |

---

## 第 1 章 · 安装 Fiddler Classic（约 5 分钟）

### 1.1 先看有没有装

按 **Win 键**，打 `fiddler`。

* 出现 Fiddler 图标 → 已装，跳到第 2 章
* 没有 → 继续往下

### 1.2 下载

1. 浏览器打开：`https://www.telerik.com/download/fiddler`
2. 页面会让你**填一个邮箱**才给下载 → 填你自己的邮箱（格式对就行）
3. 在产品下拉框里选 **`Fiddler Classic`**

   > ⚠️ **千万别选 `Fiddler Everywhere`** —— 那个要注册账号、有试用期、会收费。
   > 我们要的 **Classic** 是免费的。

4. 勾选同意条款 → 点 **`Download`** → 得到 `FiddlerSetup.exe`

### 1.3 安装

双击 `FiddlerSetup.exe` → 一路 **Next / I Agree / Install / Finish**（不用改任何选项）。

> 如果下载页找不到 Fiddler Classic 那一栏（Telerik 页面时不时改版），
> 就搜 `Fiddler Classic download`；还搞不定就直接告诉我，别在这儿卡住。

### 1.4 第一次打开

打开后可能弹一个提示，问你要不要**解密 HTTPS 流量**
（类似 `Decrypt HTTPS traffic` / `Configure Windows to trust the Fiddler Root certificate?`）。

👉 **点 `No` / 不启用。**

我们测的是 `http://`（明文），**根本不需要解密 HTTPS**，这样就完全不用装证书。

---

## 第 2 章 · 认识界面（30 秒）

```text
┌──────────────────────────────────────────┬────────────────────────┐
│ ① 会话列表（左边一大片）                    │ ③ Inspectors（右半）    │
│   每一行 = 一条请求                         │  上半 = Request（请求）  │
│   四列：状态码 | 方法 | 主机 | URL           │  下半 = Response（响应） │
├──────────────────────────────────────────┤                        │
│ ② 底部黑色输入框 = QuickExec（打命令的地方）  │                        │
│    左下角：Capturing（表示正在抓）            │                        │
└──────────────────────────────────────────┴────────────────────────┘
```

**只需记住 3 个地方**：

1. **左下角 `Capturing`** —— 有这几个字就是在抓，点一下变空白就暂停
2. **中间那片列表** —— 每多一条请求就多一行
3. **底部黑色输入框（QuickExec）** —— 断点命令打在这里

---

## 第 3 章 · ⚠️ 最大的坑：Fiddler 默认抓不到 localhost

**这是所有人第一次用 Fiddler 抓本地服务都会踩的坑**，先看明白再动手：

Windows 的系统代理默认**绕过"本地地址"**。
所以浏览器 / Postman 访问 `127.0.0.1:8000` 时是**直连**，
流量**根本不经过 Fiddler**，列表里自然什么都没有。

三种解法，**我们用方案 1**：

| 方案 | 做法 | 可靠性 |
|------|------|-------|
| **方案 1** ⭐ | PowerShell 里**显式指定代理**发请求 | **最稳，一定有效** |
| 方案 2 | 浏览器访问 `http://localhost.fiddler:8000/docs` | 有效 |
| 方案 3 | Postman 里把 `127.0.0.1` 换成 `localhost.fiddler` | 有效 |

> `localhost.fiddler` 是 Fiddler 的**专用域名**，会被转发到 `127.0.0.1`，
> 所以接口照常工作，但请求**经过 Fiddler**，就能抓到了。

---

## 第 4 章 · 抓第一波：完整业务流（约 3 分钟）

### 4.1 先做一次"代理通不通"的自检 ⭐

**做正事之前必须先确认能抓到**，否则后面全白干。

1. 打开 Fiddler，确认**左下角显示 `Capturing`**
2. 打开浏览器，地址栏输入：

```
http://localhost.fiddler:8000/tasks
```

3. 浏览器应该**正常显示一串 JSON**（一堆任务）
4. 回头看 Fiddler 列表：**应该多出一行**，主机列是 `localhost.fiddler`，状态码 `200`

👉 **看到这一行，说明代理通了，可以往下做。**

**如果一行都没有**：别往下走，直接看第 9 章对照表。

### 4.2 清空列表，开始正式抓

1. 鼠标点一下 Fiddler **底部那个黑色输入框**
2. 输入 `cls` → 按 **回车**（列表清空）

### 4.3 用 PowerShell 发四条请求（带代理）

打开 PowerShell，**整段复制**下面这段，回车：

```powershell
$proxy = 'http://127.0.0.1:8888'
$base  = 'http://127.0.0.1:8000'

# ① 登录
$login = Invoke-RestMethod "$base/login" -Method Post -Proxy $proxy `
  -ContentType 'application/json' `
  -Body '{"username":"tester","password":"123456"}'
$token = $login.token
"① 登录成功，token = $token"

# ② 创建任务
$c = Invoke-RestMethod "$base/tasks" -Method Post -Proxy $proxy `
  -ContentType 'application/json' `
  -Headers @{ Authorization = "Bearer $token" } `
  -Body '{"title":"fiddler-create-01","done":false}'
$id = $c.id
"② 创建成功：" + ($c | ConvertTo-Json -Compress)

# ③ 查询列表
$n = (Invoke-RestMethod "$base/tasks" -Method Get -Proxy $proxy).Count
"③ 列表条数 = $n"

# ④ 无鉴权删除（故意不带 Authorization）
$r = Invoke-WebRequest "$base/tasks/$id" -Method Delete -Proxy $proxy -SkipHttpErrorCheck
"④ 无鉴权删除 -> $([int]$r.StatusCode)"
```

### 4.4 期望看到什么

PowerShell 里：

```
① 登录成功，token = xxxxxxxx...
② 创建成功：{"id":"xxxx","title":"fiddler-create-01","done":0}
③ 列表条数 = 21
④ 无鉴权删除 -> 204
```

Fiddler 列表里**多出 4 行**，主机列是 `127.0.0.1`，状态码依次是：

```
200   201   200   204
```

👉 **截图**（把四行都框进去），命名 `01-Fiddler抓到完整业务流.png`

> 💡 `-Proxy http://127.0.0.1:8888` 里的 **8888** 是 Fiddler 默认端口。
> 如果 Fiddler 提示端口被占用改成别的（比如 8889），这里同步改。

---

## 第 5 章 · 用 Inspector 看请求和响应

**Inspectors = 检查器**，在右边。

1. 在左边列表**点中那行 `POST 127.0.0.1:8000/tasks`**
2. 右边**上半部分（Request）**：
   * 点 **`Headers`** 标签 → 找 `Authorization: Bearer ...` ⭐ 这就是鉴权头
   * 点 **`JSON`** 标签 → 看请求体 `{"title":"fiddler-create-01","done":false}`
3. 右边**下半部分（Response）**：
   * 点 **`JSON`** 标签 → 看返回 `{"id":"...","title":"...","done":0}`

👉 **截图**（把 Request Headers 那一片框进去），命名 `02-Fiddler里的Authorization头.png`

> ⚠️ **必须记住的一点**：Fiddler 的 `JSON` / `XML` 标签是**只读**的，只能看不能改。
> 后面要改内容，必须切到 **`Raw`** 或 **`TextView`** 标签。

---

## 第 6 章 · 断点改包 —— Fiddler 的招牌功能（约 5 分钟）

这一章是**加分项里最值钱的**：证明你不仅会看流量，还能**在传输中途把它改掉**。

### 6.1 请求断点：把标题改成 101 个字符

**第 1 步 · 设断点**

点 Fiddler 底部黑色输入框，输入下面这行，按回车：

```
bpu /tasks
```

（`bpu` = **b**reak on re**q**uest **u**ri：URL 里含 `/tasks` 的请求一律拦下来）

**第 2 步 · 重新发一次创建请求**

在 PowerShell 里重跑第 4.3 节那段里的 **①② 两步**（登录 + 创建）。

**第 3 步 · 请求会被拦下**

* Fiddler 列表里那行会**停住**，行首图标变成拦截样式
* 列表**下方**出现一排按钮，其中有 **`Run to Completion`**（放行）
* 右下角 **Inspectors 标红**，提示你正在编辑请求

👉 **截图**，命名 `03-断点改包-请求被拦下.png`

**第 4 步 · 改包**

1. 右边**上半部分（Request）** → 点 **`TextView`** 或 **`Raw`** 标签
2. 找到 body 里 title 的值，把它**整段换成下面这串**（正好 101 个 `a`）：

```
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

> ⚠️ **只改引号里面的内容**。别动引号、别动大括号、别动 `done` 那一段。

**第 5 步 · 放行**

点 **`Run to Completion`**。

**第 6 步 · 看结果**

PowerShell 那边会报错，状态码 **422**（因为你发了个超长标题）。

> 这证明了：**Fiddler 能在传输途中把请求改掉，服务端完全不知道。**
> 和我们用 Postman 直接发 101 字符得到的结果一致 —— **两个工具交叉验证**。

**第 7 步 · ⚠️ 清掉断点（非常重要）**

黑色输入框里输入 `bpu`，按回车（**不带参数 = 清除所有请求断点**）。

> 不清的话，后面**每个**带 `/tasks` 的请求都会被卡住，
> 你会以为"Fiddler 又坏了"。

### 6.2 响应断点：改服务端返回的数据

**目的**：证明"纯 HTTP 环境下，响应可以被中间人随意篡改"。

**第 1 步**：黑色输入框输入 `bpafter /tasks` → 回车（拦下**响应**）

**第 2 步**：PowerShell 里执行

```powershell
Invoke-WebRequest 'http://127.0.0.1:8000/tasks' -Proxy 'http://127.0.0.1:8888' -SkipHttpErrorCheck | Select-Object -ExpandProperty Content
```

**第 3 步**：Fiddler 会把响应拦下

* 右边**下半部分（Response）** → 点 **`TextView`**
* 找到任意一个任务的 `"done": false`，改成 **`"done": true`**

**第 4 步**：点 **`Run to Completion`** 放行

**第 5 步**：看客户端收到什么

PowerShell 打印出来的列表里，那条任务已经变成 `"done": true` —— **但数据库里其实没变**。

👉 **截图**，命名 `04-响应被篡改-done变true.png`

**第 6 步**：⚠️ 黑色输入框输入 `bpafter` 回车（清除）

> **写进报告的结论一句话**：
> 纯 HTTP 下响应可被中间人任意篡改，客户端无法察觉。
> 所以真实项目必须上 **HTTPS + 证书校验（必要时证书固定 Pinning）**。

---

## 第 7 章 · 把证据保存下来

### 7.1 保存整个会话（面试可现场回放）

菜单 **`File` → `Save` → `All Sessions`** →
路径选 `D:\qa-projects\10-tools-lab\fiddler\`，文件名 **`business-flow.saz`**

### 7.2 导出纯文本证据（写进报告用）

1. 在列表里按住 **Ctrl** 点选那 4 行业务流请求
2. 菜单 **`File` → `Save` → `Selected Sessions` → `as Text`**
3. 存成 `D:\qa-projects\10-tools-lab\fiddler\business-flow.txt`

这个 txt 里包含**完整的请求头 + 响应头**，比截图更有说服力。

### 7.3 想单独复制一条请求的地址

右键那一行 → **`Copy` → `Just Url`**

---

## 第 8 章 · 收工：一定要把系统代理还原

Fiddler 是**接管整个系统代理**的，所以：

* **正常关闭**：菜单 **`File` → `Exit`**（**别用任务管理器杀进程**）
* **关完后浏览器上不了网** → 系统代理没还原：
  * 重新打开 Fiddler，再用 `File → Exit` 正常关一次
  * 或手动：Windows **设置 → 网络和 Internet → 代理 → 关掉"使用代理服务器"**
* **想临时暂停抓包**：点左下角状态栏的 **`Capturing`**（字消失就是暂停）

---

## 第 9 章 · 报错对照表

| 你看到什么 | 原因 | 怎么办 |
|-----------|------|-------|
| Fiddler 列表里**完全没有** `127.0.0.1:8000` | 本地流量绕过代理（第 3 章的坑） | 先做 4.1 自检；确认加了 `-Proxy`；或换 `localhost.fiddler` |
| 列表里全是 `CONNECT xxx:443` | 没开 HTTPS 解密，**正常** | 无视 |
| 一条请求卡住不动 | 断点没清 | 黑色框里打 `bpu` 和 `bpafter` 回车 |
| PowerShell 报无法连接远程服务器 | Fiddler 没开 / 端口不是 8888 | 确认 Fiddler 在跑，看它用的端口 |
| 改完 body 后服务端说 JSON 错误 | 引号被改坏了 | 用 `TextView` 只改值，不动引号和大括号 |
| 关掉 Fiddler 后浏览器打不开网页 | 系统代理没还原 | 见第 8 章 |
| Fiddler 提示端口被占用 | 8888 被别的程序占了 | 按提示改成新端口，PowerShell 里同步改 |

---

## 第 10 章 · 做完之后

把这几样发我：

1. `01-Fiddler抓到完整业务流.png`
2. `04-响应被篡改-done变true.png`
3. `business-flow.txt`（截图也行）

我给你生成 **`D:\qa-projects\10-tools-lab\fiddler\抓包分析.md`**，
和 Postman 那份 `接口调试记录.md` 一起，构成"**两个工具交叉验证**"的完整证据链。
