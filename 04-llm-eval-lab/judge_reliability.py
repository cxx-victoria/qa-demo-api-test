"""
judge 可靠性验证：
1) 准备 30 条问题，你自己先人工判断"回答好不好"（label 列）
2) 跑 DeepEval 得到机器判定
3) 计算一致率
第 1 步需要你手工填 label：1=好，0=差。可以先跑一轮看回答，再回来填。
"""
import requests
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

API = "http://127.0.0.1:8000/chat"

# (问题, 期望答案, 我的人工标注 1/0)
DATASET = [
    ("你们的退货政策是什么？", "签收后7天内无理由退货", 1),
    ("支持哪些支付方式？", "微信、支付宝、银行卡", 1),
    ("你们支持货到付款吗？", "应当回答无法确定/知识库没有", 1),
    ("运费怎么算？", "满99元包邮，否则8元", 1),
    # ... 建议你补到 30~100 条
]

metric = GEval(
    name="Quality",
    criteria="回答是否准确、与知识库一致、没有编造；准确且不编造为通过。",
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT,
                       SingleTurnParams.EXPECTED_OUTPUT],
    threshold=0.7,
    model="qwen-plus"
)

agree = 0
total = 0
for q, expected, human_label in DATASET:
    answer = requests.post(API, json={"q": q}, timeout=120).json()["answer"]
    tc = LLMTestCase(input=q, actual_output=answer, expected_output=expected)
    metric.measure(tc)
    machine_label = 1 if metric.is_successful() else 0
    total += 1
    same = machine_label == human_label
    agree += same
    print(f"{'✅一致' if same else '❌不一致'} | 人评={human_label} 机评={machine_label} 得分={metric.score:.2f} | {q}")
    if not same:
        print(f"      模型回答：{answer[:120]}")

print(f"\n样本数 {total}，一致 {agree}，一致率 {agree / total * 100:.1f}%")