# 04‑llm‑eval‑lab｜LLM应用评测实验室
> 项目4 DeepEval大模型质量测试，基于`pytest + DeepEval GEval(LLM‑as‑Judge)`，对demo‑api电商客服LLM应用做自动化质量评测。
被测对象：本地uvicorn启动 `http://127.0.0.1:8000/chat` 电商客服接口
裁判模型：阿里云百炼 `qwen‑plus`（OpenAI兼容接口）
被测模型：`qwen3‑max`

## 📋 前置依赖准备
### 1. 两套独立虚拟环境（重点，不要混淆）
1. `../00‑demo‑api/.venv`：运行被测客服后端，依赖uvicorn、requests等
2. `./.venv`：本评测项目，安装deepeval、pytest、requests
```powershell
# 进入评测目录，激活评测虚拟环境
cd D:\qa-projects\04-llm-eval-lab
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
