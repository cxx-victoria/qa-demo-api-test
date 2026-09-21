"""
第一个大模型测试：验证客服回答的正确性。
运行方式： deepeval test run test_chatbot.py
"""
import os

import pytest
import requests
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

API = "http://127.0.0.1:8000/chat"


def ask(question: str) -> str:
    """调用被测应用（demo-api 的 /chat 接口）。"""
    resp = requests.post(API, json={"q": question}, timeout=90)
    resp.raise_for_status()
    return resp.json()["answer"]


@pytest.mark.parametrize(
    "question,expected",
    [
        ("你们的退货政策是什么？", "签收后 7 天内无理由退货，需保留发票，退款 3-5 个工作日到账"),
        ("支持哪些支付方式？", "微信、支付宝、银行卡"),
        ("运费怎么算？", "满 99 元包邮，否则 8 元"),
        ("客服几点上班？", "每天 9:00-21:00"),
    ],
)
def test_correctness(question, expected):
    """正确性测试：回答内容是否与知识库一致。"""
    metric = GEval(
        name="Correctness",
       criteria="""
对比 actual_output 和 expected_output 的核心事实实体：
1. 只校验关键业务事实：数字、时间、物品列表、政策规则；
2. 允许actual_output增加主语、动词、开场白、修饰描述、标点换行，这些修饰文字**不算新增事实，不能扣分**；
3. 只有出现【额外业务事实】【错误数字/时间】【遗漏关键信息】才算不通过；
4. 字面不完全一样、措辞改写完全接受。
最终判断：核心业务事实等价 → 通过；核心事实错/漏 → 失败。
"""
,
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        threshold=0.7,
        model="qwen-plus"
    )
    test_case = LLMTestCase(
        input=question,
        actual_output=ask(question),
        expected_output=expected,
    )
    assert_test(test_case, [metric])