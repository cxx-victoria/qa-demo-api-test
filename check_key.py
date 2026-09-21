"""验证 API Key 是否可用：调用一次大模型并打印回答。"""
import os
import sys

import requests

base = os.getenv("OPENAI_BASE_URL")
key = os.getenv("OPENAI_API_KEY")
model = os.getenv("DEMO_CHAT_MODEL", "qwen3-max")

if not base or not key:
    print("❌ 环境变量没设置好：OPENAI_BASE_URL / OPENAI_API_KEY")
    print("   设置完记得关掉终端重新打开！")
    sys.exit(1)

print(f"Base URL : {base}")
print(f"模型     : {model}")
print(f"Key      : {key[:8]}...（已隐藏）")
print("正在调用模型，请稍等 ...")

resp = requests.post(
    f"{base.rstrip('/')}/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "model": model,
        "messages": [{"role": "user", "content": "用一句话说明什么是软件测试"}],
        "temperature": 0.7,
    },
    timeout=60,
)

print("HTTP 状态码:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("✅ 调用成功！模型回答：")
    print(data["choices"][0]["message"]["content"])
    print("\n用量：", data.get("usage"))
else:
    print("❌ 调用失败，原始返回：")
    print(resp.text[:800])