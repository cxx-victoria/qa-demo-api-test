# -*- coding: utf-8 -*-
"""
preflight.py —— 跑测试前的 30 秒自检（每次开跑前先运行它）

它会依次检查 4 件事：
    ① 环境变量（BASE_URL / API_KEY / 裁判模型名）
    ② 被测服务是否活着（http://127.0.0.1:8000）
    ③ /chat 是不是真的在调用大模型（而不是返回"兜底回答"）
    ④ 裁判模型名有没有配成 gpt-5.4（DeepEval 的默认值，你的平台上没有）

用法（不是 pytest 测试，直接用 python 跑）：
    cd D:\\qa-projects\\04-llm-eval-lab
    .\\.venv\\Scripts\\Activate.ps1
    python preflight.py

全部通过才去跑 deepeval test run，否则先修问题再跑（省时间省钱）。
"""

import os
import sys
import time

import requests

# Windows 终端默认编码可能是 GBK，先把输出编码设成 UTF-8，避免打印中文/符号时报
# UnicodeEncodeError 直接崩掉（这个坑很多人踩过）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

API_ROOT = "http://127.0.0.1:8000"
CHAT = f"{API_ROOT}/chat"

ok_count = 0
bad_count = 0


def ok(msg):
    global ok_count
    ok_count += 1
    print(f"  [OK]   {msg}")


def bad(msg, fix):
    global bad_count
    bad_count += 1
    print(f"  [FAIL] {msg}")
    print(f"         → 怎么修：{fix}")


print("=" * 66)
print("跑测试前的自检（preflight）")
print("=" * 66)

# ---------------------------------------------------------------- ① 环境变量
print("\n① 环境变量")
base = os.getenv("OPENAI_BASE_URL")
key = os.getenv("OPENAI_API_KEY")
model = os.getenv("OPENAI_MODEL_NAME")

if base:
    ok(f"OPENAI_BASE_URL = {base}")
else:
    bad("OPENAI_BASE_URL 没设置",
        'setx OPENAI_BASE_URL "https://dashscope.aliyuncs.com/compatible-mode/v1" 然后重开终端')

if key:
    ok(f"OPENAI_API_KEY = {key[:8]}...（长度 {len(key)}）")
else:
    bad("OPENAI_API_KEY 没设置",
        'setx OPENAI_API_KEY "sk-你的Key" 然后重开终端')

if not model:
    bad("OPENAI_MODEL_NAME 没设置（DeepEval 会默认用 gpt-5.4，你平台上没有这个模型）",
        'setx OPENAI_MODEL_NAME "qwen-plus" 然后重开终端；或在测试文件里 os.environ.setdefault(...)')
elif model.strip().lower().startswith("gpt-"):
    bad(f"OPENAI_MODEL_NAME = {model}，这看起来是 OpenAI 的模型名，你的平台上大概率没有",
        'setx OPENAI_MODEL_NAME "qwen-plus" 然后重开终端')
else:
    ok(f"OPENAI_MODEL_NAME = {model}（裁判模型）")

# ---------------------------------------------------------------- ② 服务是否活着
print("\n② 被测服务（终端 A 要一直开着）")
try:
    r = requests.get(f"{API_ROOT}/tasks", timeout=5)
    ok(f"GET /tasks → HTTP {r.status_code}（服务活着）")
    service_up = True
except Exception as e:
    service_up = False
    bad(f"连不上 {API_ROOT}/tasks（{type(e).__name__}）",
        "另开一个终端（终端 A）执行：cd D:\\qa-projects\\00-demo-api; "
        ".\\.venv\\Scripts\\Activate.ps1; python -m uvicorn app:app --port 8000 --log-level warning *> uvicorn.log")

# ---------------------------------------------------------------- ③ /chat 是否真调模型
print("\n③ /chat 是不是真的在调用大模型")
if not service_up:
    bad("服务不可达，跳过本项检查", "先按上面把服务启动起来")
else:
    try:
        t0 = time.time()
        resp = requests.post(CHAT, json={"q": "你们的退货政策是什么？"}, timeout=60)
        cost = time.time() - t0
        data = resp.json()
        answer = data.get("answer", "")
        used_model = data.get("model")
        if used_model == "fallback" or "兜底回答" in answer:
            bad(f"/chat 返回的是兜底回答（model={used_model}）——说明【终端 A】没读到 API Key",
                "关掉终端 A 重开（setx 只对新终端生效），再重新启动 uvicorn")
        else:
            ok(f"/chat 真调了模型：model={used_model}，耗时 {cost:.1f} 秒")
            ok(f"回答片段：{answer[:40]}...")
    except Exception as e:
        bad(f"调用 /chat 失败：{type(e).__name__}: {str(e)[:80]}", "检查终端 A 的日志 uvicorn.log")

# ---------------------------------------------------------------- 汇总
print("\n" + "=" * 66)
print(f"自检结果：通过 {ok_count} 项，失败 {bad_count} 项")
if bad_count == 0:
    print("[OK] 全部通过，可以执行：deepeval test run test_extra_cases.py")
else:
    print("[FAIL] 先把上面标 FAIL 的问题修掉，再跑测试（否则用例会全挂，白花时间）")
print("=" * 66)

sys.exit(0 if bad_count == 0 else 1)
