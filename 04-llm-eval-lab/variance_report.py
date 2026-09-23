"""非确定性量化 v2：逐题统计 + 打印模型原文，用于失败归因。

为什么要有 v2（v1 = variance_test.py 的问题）：
    v1 把「3 道题 × 3 轮」的 9 个分数**混在一起**算标准差，得到 0.362。
    但这个 0.362 主要来自 **不同题目之间的差异**，
    而不是 **同一道题多次运行的波动**。这两件事必须分开：

      · 跨题目差异大 → 有的题答得好、有的题答得差 → 是**内容/质量问题**
      · 同题目波动大 → 同一道题每次答得都不一样 → 这才是**大模型输出不确定性**

    把两者混在一起算，指标就失去了诊断能力（会把"某题一直答错"误报成"输出不稳定"）。
    **正确做法：按题分别算均值 / 标准差 / 通过率。**

本脚本输出四样东西：
    1) 每道题每一轮的得分
    2) **每道题的均值 / 标准差 / 通过率**（正确的非确定性口径）
    3) 每道题模型的**原始回答**（用于判断"是模型答错，还是裁判误判"）
    4) 合并口径的数字（保留，仅用于和 v1 对照）

用法（被测服务必须先启动、且保持运行）：
    cd D:\\qa-projects\\04-llm-eval-lab
    .\\.venv\\Scripts\\Activate.ps1
    python variance_report.py
"""
import statistics as st
import textwrap

import requests
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

API = "http://127.0.0.1:8000/chat"
ROUNDS = 3
THRESHOLD = 0.7

# ⚠️ 裁判标准必须和主测试套件（test_chatbot.py / test_extra_cases.py）保持一致。
#
# 2026-09-23 实测踩到的坑：
#   归因脚本最早只写了「判断实际输出是否与期望输出表达的事实一致。」
#   结果模型回答「支持微信、支付宝和银行卡支付。」（完全正确）却被裁判打了 0.2 分。
#   原因不是被测有缺陷，也不是模型不稳定，而是【裁判标准写得太简略】——
#   主套件的 criteria 明确允许"增加主语/动词/修饰描述，不能扣分"，这句话没写进去，
#   裁判就按近似字面匹配去打了。
#
# 教训：**评测标准和被测对象是两个独立变量，改阈值/改标准之前必须先看原文**。
#       并且"同一套被测系统，不同脚本用不同标准"本身就是一个测试资产管理问题。
CRITERIA = (
    "对比 actual_output 和 expected_output 的核心业务事实："
    "① 只校验关键事实：数字、时间、物品或方式列表、政策规则；"
    "② 允许 actual_output 增加主语、动词、开场白、连词、修饰描述、标点换行，"
    "这些修饰文字【不算】新增事实，不能扣分；"
    "③ 只有出现【额外业务事实】【错误数字或时间】【遗漏关键信息】才算不通过；"
    "④ 字面不同、措辞改写完全接受。"
    "最终判断：核心业务事实等价 → 通过；核心事实错或漏 → 失败。"
)

QUESTIONS = [
    ("你们的退货政策是什么？", "签收后 7 天内无理由退货，需保留发票，退款 3-5 个工作日到账"),
    ("支持哪些支付方式？", "微信、支付宝、银行卡"),
    ("运费怎么算？", "满 99 元包邮，否则 8 元"),
]

# 归因结论（人工核对模型原文后填写，会打印到报告里）
NOTES = {
    "你们的退货政策是什么？": "模型回答与期望事实一致，措辞不同不影响，判定合格。",
    "支持哪些支付方式？": (
        "首轮低分 0.2~0.3 属【裁判误判】：模型回答「支持微信、支付宝和银行卡支付。」"
        "信息完整、无矛盾、无编造，与期望事实完全一致。"
        "根因是原 criteria 未声明【允许改写措辞】，已统一为主测试套件的标准，下方复测验证。"
    ),
    "运费怎么算？": "模型回答与期望事实一致，判定合格。",
}

lines = []


def out(text=""):
    print(text)
    lines.append(text)


def ask(question):
    return requests.post(API, json={"q": question}, timeout=120).json()["answer"]


def new_metric():
    """每道题各建一个裁判实例，避免跨题目复用带来的偏差。"""
    return GEval(
        name="Correctness",
        criteria=CRITERIA,
        evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        threshold=THRESHOLD,
        model="qwen-plus",
    )


out("=" * 78)
out("LLM 输出非确定性与质量归因报告（variance_report v2）")
out("=" * 78)
out(f"被测接口 : {API}")
out(f"轮次     : {ROUNDS}      阈值: {THRESHOLD}")
out("")

per_question = {}

for question, expected in QUESTIONS:
    metric = new_metric()
    scores = []
    first_answer = ""
    out("-" * 78)
    out(f"问题：{question}")
    out(f"期望：{expected}")
    out("")
    for rnd in range(1, ROUNDS + 1):
        answer = ask(question)
        if rnd == 1:
            first_answer = answer
        tc = LLMTestCase(input=question, actual_output=answer, expected_output=expected)
        metric.measure(tc)
        scores.append(metric.score)
        out(f"  第 {rnd} 轮  得分 {metric.score:.3f}  "
            f"{'PASS' if metric.is_successful() else 'FAIL'}")
    out("")
    out("  模型原始回答（第一轮）：")
    for row in (str(first_answer).splitlines() or [str(first_answer)]):
        out("    " + row)
    out("")
    out(f"  >>> 本题：均值 {st.mean(scores):.3f}  "
        f"标准差 {st.pstdev(scores):.3f}  "
        f"通过率 {sum(s >= THRESHOLD for s in scores) / len(scores) * 100:.1f}%")
    note = NOTES.get(question)
    if note:
        out("")
        out("  归因结论：")
        for row in textwrap.wrap(note, width=66):
            out("    " + row)
    out("")
    per_question[question] = scores

all_scores = [s for v in per_question.values() for s in v]

out("=" * 78)
out("逐题统计（这才是判断『非确定性』的正确口径）")
out("=" * 78)
out(f"{'题目':<12}{'均值':>8}{'标准差':>10}{'通过率':>10}")
for question, scores in per_question.items():
    out(f"{question:<12}{st.mean(scores):>8.3f}"
        f"{st.pstdev(scores):>10.3f}"
        f"{sum(s >= THRESHOLD for s in scores) / len(scores) * 100:>9.1f}%")
out("")

out("=" * 78)
out("合并统计（v1 脚本的口径，仅用于对照）")
out("=" * 78)
out(f"总样本数   : {len(all_scores)}")
out(f"合并均值   : {st.mean(all_scores):.3f}")
out(f"合并标准差 : {st.pstdev(all_scores):.3f}")
out(f"通过率     : {sum(s >= THRESHOLD for s in all_scores) / len(all_scores) * 100:.1f}%")
out("")
out("解读：合并标准差把『题目之间的难度差异』也算了进去，")
out("      所以它总是高于『同一道题多轮的波动』。")
out("      要证明输出稳定，请看逐题标准差；合并标准差只用来反映整体质量分布。")

with open("variance_result_v2.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")

print("\n完整结果已写入 variance_result_v2.txt")
