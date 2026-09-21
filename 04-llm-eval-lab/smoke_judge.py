# -*- coding: utf-8 -*-
"""
smoke_judge.py —— 裁判模型自检（先跑这个，再跑 45 条）

作用：用【一条】最小用例验证"裁判模型能不能通"。
      通了，说明配置正确，再去跑 test_extra_cases.py 那 45 条；
      不通，先修配置，别浪费钱跑 45 条。

运行：
    cd D:\\qa-projects\\04-llm-eval-lab
    .\\.venv\\Scripts\\Activate.ps1
    deepeval test run smoke_judge.py

预期：1 passed，并在表格里看到 judge 模型是 qwen-plus 而不是 gpt-5.4。
"""

import os
import sys

# ---------------------------------------------------------------- 裁判模型配置
# 必须在创建 GEval 之前设置，否则 DeepEval 会用默认的 gpt-5.4（你的平台上没有）
os.environ.setdefault("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
os.environ.setdefault("OPENAI_MODEL_NAME", "qwen-plus")

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams


def test_judge_works():
    """最小判定：回答里有没有'你好'。这条能过，说明裁判链路是通的。"""
    metric = GEval(
        name="JudgeSmoke",
        criteria="判断 actual_output 中是否包含问候语（如'你好'）。包含则合格。",
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
        threshold=0.5,
    )
    tc = LLMTestCase(input="打个招呼", actual_output="你好，请问有什么可以帮您？")

    print(f"\n[自检] 裁判模型 = {metric.evaluation_model}")
    assert_test(tc, [metric])


def test_env_is_ready():
    """顺便检查环境变量是否齐了（不调用模型，不花钱）。"""
    base = os.getenv("OPENAI_BASE_URL")
    key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL_NAME")
    print(f"\n[自检] OPENAI_BASE_URL  = {base}")
    print(f"[自检] OPENAI_API_KEY   = {'已设置(长度 %d)' % len(key) if key else '❌ 未设置'}")
    print(f"[自检] OPENAI_MODEL_NAME= {model}")
    assert base, "OPENAI_BASE_URL 没设置"
    assert key, "OPENAI_API_KEY 没设置（裁判模型无法调用）"
    assert model and model != "gpt-5.4", "OPENAI_MODEL_NAME 没配置成你的模型服务上存在的模型名"
