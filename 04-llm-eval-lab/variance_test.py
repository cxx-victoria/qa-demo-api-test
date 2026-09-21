"""非确定性量化：同一批问题跑 N 轮，统计指标波动。"""
import statistics

import requests
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

API = "http://127.0.0.1:8000/chat"
ROUNDS = 3
QUESTIONS = [
    ("你们的退货政策是什么？", "签收后 7 天内无理由退货，需保留发票，退款 3-5 个工作日到账"),
    ("支持哪些支付方式？", "微信、支付宝、银行卡"),
    ("运费怎么算？", "满 99 元包邮，否则 8 元"),
]


def ask(q):
    return requests.post(API, json={"q": q}, timeout=120).json()["answer"]


metric = GEval(
    name="Correctness",
    criteria="判断实际输出是否与期望输出表达的事实一致。",
    evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
    threshold=0.7,
    model="qwen-plus"
)

all_scores = []
pass_flags = []

for rnd in range(1, ROUNDS + 1):
    print(f"\n===== 第 {rnd} 轮 =====")
    for q, expected in QUESTIONS:
        answer = ask(q)
        tc = LLMTestCase(input=q, actual_output=answer, expected_output=expected)
        metric.measure(tc)
        score = metric.score
        ok = metric.is_successful()
        all_scores.append(score)
        pass_flags.append(ok)
        print(f"  [{ 'PASS' if ok else 'FAIL' }] 得分 {score:.3f}  问题：{q}")

print("\n===== 汇总 =====")
print(f"总样本数     : {len(all_scores)}")
print(f"指标均值     : {statistics.mean(all_scores):.3f}")
print(f"指标标准差   : {statistics.pstdev(all_scores):.3f}   ← 这就是'非确定性'的量化")
print(f"通过率       : {sum(pass_flags) / len(pass_flags) * 100:.1f}%")
