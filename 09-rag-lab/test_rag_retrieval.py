"""RAG 检索层测试：只测"能不能找对资料"，不测生成。

为什么要把检索层单独测：
    一个 RAG 回答错了，可能是两种完全不同的原因：
        ① **检索没找到对的资料** → 后面生成得再好也没用（这是 RAG 的头号故障）
        ② 检索找到了，但**生成阶段没用上 / 编造** → 是模型忠实度问题
    把这两层分开测，才能一眼定位问题出在哪一段。
    这也是为什么本文件**只调用 embedding 接口**，不调用生成模型 —— 又快又便宜。

6 条用例：
    1. 索引规模合理（文档数、片段数、片段长度分布）
    2. 单条检索：问运费必须命中运费文档
    3. **Recall@K 曲线**：15 条标注问题的召回率曲线（本项目最值钱的一条）
    4. 易混淆问题要落到不同片段（"退货几天" vs "退款多久到账"）
    5. 知识库外的问题，相似度应当明显更低（这是"拒答"能成立的前提）
    6. 索引可复现（同样输入两次建索引结果一致）

前置条件：OPENAI_BASE_URL / OPENAI_API_KEY 已配置（只用到 embedding 接口）。

用法（D:\\qa-projects\\09-rag-lab 下）：
    cd D:\\qa-projects\\00-demo-api
    .\\.venv\\Scripts\\Activate.ps1
    cd ..\\09-rag-lab
    python -m pytest test_rag_retrieval.py -v -s
"""
import statistics

import pytest

import rag

# 标注集：问题 → 应该命中的来源文档（人工标注的"正确答案"）
CASES = [
    ("退货可以退几天？", "01_退货政策.md"),
    ("退款多久能到账？", "01_退货政策.md"),
    ("哪些商品不支持退货？", "01_退货政策.md"),
    ("运费怎么算？", "02_运费规则.md"),
    ("多少钱可以包邮？", "02_运费规则.md"),
    ("新疆西藏的运费加多少？", "02_运费规则.md"),
    ("支持哪些支付方式？", "03_支付方式.md"),
    ("可以分期付款吗？", "03_支付方式.md"),
    ("客服几点上班？", "04_客服时间.md"),
    ("付款后多久发货？", "05_订单与物流.md"),
    ("怎么查我的物流？", "05_订单与物流.md"),
    ("会员有哪些等级？", "06_会员与积分.md"),
    ("积分怎么兑换？", "06_会员与积分.md"),
    ("怎么开发票？", "07_发票与保修.md"),
    ("保修期是多久？", "07_发票与保修.md"),
]

# 知识库里**故意没有**的内容（用于验证"查不到时相似度会低"）
OUT_OF_KB = [
    "你们的延保服务怎么买？",
    "支持以旧换新吗？",
    "有没有海外直邮的仓库？",
]

KS = (1, 3, 5)


@pytest.fixture(scope="session")
def index():
    return rag.build_index()


@pytest.fixture(scope="session")
def recall_report(index):
    """一次性算好 Recall@K，供多条用例共用（embedding 有缓存，重复调用不额外花钱）。"""
    report = {k: {"hit": 0, "miss": []} for k in KS}
    top1_scores = []
    for question, expected_source in CASES:
        hits = rag.retrieve(question, k=max(KS), index=index)
        sources = [h["source"] for h in hits]
        top1_scores.append(hits[0]["score"])
        for k in KS:
            if expected_source in sources[:k]:
                report[k]["hit"] += 1
            else:
                report[k]["miss"].append((question, expected_source, sources[:k]))
    return {"report": report, "top1_scores": top1_scores}


# ==================================================================
# 1. 索引规模
# ==================================================================
def test_index_scale_is_reasonable(index):
    """索引里应该有足够多的文档与片段，且没有异常短的碎片。"""
    sources = {item["source"] for item in index}
    assert len(sources) >= 7, f"来源文档只有 {len(sources)} 个，知识库可能没被完整加载"
    assert len(index) >= 25, f"片段总数只有 {len(index)} 个，切分可能过粗"

    lengths = [len(item["text"]) for item in index]
    assert min(lengths) >= 5, f"存在过短的碎片（{min(lengths)} 字符），切分策略有问题"
    print(f"\n[索引] 文档 {len(sources)} 个 / 片段 {len(index)} 个 / "
          f"平均长度 {statistics.mean(lengths):.0f} 字")


def test_index_is_reproducible(index):
    """同样的文档两次建索引，片段内容与顺序应当一致（可复现性）。"""
    again = rag.build_index()
    assert [item["text"] for item in index] == [item["text"] for item in again], \
        "两次建索引得到的片段不一致，切分逻辑不稳定"
    assert [item["source"] for item in index] == [item["source"] for item in again]


def test_no_heading_only_chunks(index):
    """索引里不能有"只有标题、没有内容"的碎片（回归用例）。

    背景（2026-09-23 实测发现）：
        markdown 的 H1 标题（如 `# 退货政策`）会单独成段、独立成一个 chunk。
        它**不含任何答案**，却因为和用户问题词面高度匹配而抢到 Top-1 检索位，
        把真正回答问题的片段挤到第 2、3 位 —— 直接拉低 ContextualPrecision
        （该指标是位置加权的，相关片段排得越靠后分越低）。

        当时的实测表现：37 个片段里有 7 个是纯标题（18.9%），
        ContextualPrecision 均值只有 0.625 而阈值是 0.70。
        修复方式：切分时把短标题段落与**下一段合并**。

    这条用例把该修复固化下来，防止以后调整切分参数时又退回去。
    """
    bad = [
        item for item in index
        if item["text"].strip().startswith("#") and len(item["text"].strip()) <= rag.MIN_CHUNK_CHARS
    ]
    assert not bad, (
        f"发现 {len(bad)} 个纯标题碎片（不含任何答案却会抢占检索位）："
        f"{[item['text'] for item in bad]}\n"
        "修复方式：在 chunk_text 里把短标题段落与下一段合并。"
    )


# ==================================================================
# 2. 单条检索
# ==================================================================
def test_retrieval_hits_expected_document(index):
    """问运费，Top-1 必须落在运费文档上。"""
    hits = rag.retrieve("运费怎么算？", k=3, index=index)
    assert hits[0]["source"] == "02_运费规则.md", (
        f"Top-1 命中了 {hits[0]['source']}，期望 02_运费规则.md\n"
        f"实际 Top-3：{[(h['source'], round(h['score'], 3)) for h in hits]}"
    )


# ==================================================================
# 3. Recall@K 曲线（核心）
# ==================================================================
def test_recall_at_k_curve(recall_report):
    """计算并打印 Recall@1 / @3 / @5，作为检索质量的量化基线。

    Recall@K 的定义：前 K 个检索结果里**包含正确来源文档**的问题占比。
    这是 RAG 最基础的检索指标 —— 面试问"你怎么评估检索质量"，
    答"算 Recall@K 曲线"比答"感觉挺准的"专业得多。
    """
    report = recall_report["report"]
    total = len(CASES)

    print("\n===== 检索质量基线 =====")
    print(f"标注问题数：{total}")
    for k in KS:
        rate = report[k]["hit"] / total * 100
        print(f"  Recall@{k} = {report[k]['hit']}/{total} = {rate:.1f}%")

    miss = report[3]["miss"]
    if miss:
        print("\n  Recall@3 未命中的问题：")
        for question, expected, got in miss:
            print(f"    - {question}  期望 {expected}  实际 {got}")

    assert report[5]["hit"] / total >= 0.80, (
        f"Recall@5 只有 {report[5]['hit'] / total * 100:.1f}%，检索质量不达标"
    )


# ==================================================================
# 4. 易混淆问题要落到不同片段
# ==================================================================
def test_confusable_questions_hit_different_chunks(index):
    """「退货几天」和「退款多久到账」是两件事，不能命中同一个片段。

    这是 RAG 的经典陷阱：两个问题字面高度相似，
    但答案在知识库的不同小节里。检索配置不对就会张冠李戴。
    """
    first = rag.retrieve("退货可以退几天？", k=1, index=index)[0]
    second = rag.retrieve("退款多久能到账？", k=1, index=index)[0]

    print(f"\n[易混淆] 退货几天  -> [{first['source']}] {first['text'][:40]}...")
    print(f"[易混淆] 退款到账  -> [{second['source']}] {second['text'][:40]}...")

    assert first["text"] != second["text"], (
        "两个不同问题命中了完全相同的片段，检索没有区分能力"
    )


# ==================================================================
# 5. 知识库外的问题，相似度应当明显更低
# ==================================================================
def test_out_of_kb_questions_score_lower(index, recall_report):
    """知识库里没有的问题，最高相似度应当明显低于正常问题。

    这条为什么重要：**"能不能拒答"的前提，是"能不能识别出查不到"**。
    如果知识库外的问题也拿到很高的相似度，模型就会被误导着编答案。
    """
    in_kb_top1 = recall_report["top1_scores"]
    out_top1 = [rag.retrieve(q, k=1, index=index)[0]["score"] for q in OUT_OF_KB]

    in_avg = statistics.mean(in_kb_top1)
    out_avg = statistics.mean(out_top1)

    print(f"\n[相似度对比] 知识库内 Top-1 均值 = {in_avg:.3f}")
    print(f"[相似度对比] 知识库外 Top-1 均值 = {out_avg:.3f}")
    print(f"[相似度对比] 差值 = {in_avg - out_avg:+.3f}")
    for q, score in zip(OUT_OF_KB, out_top1):
        print(f"    {score:.3f}  {q}")

    assert out_avg < in_avg, (
        "知识库外问题的相似度并不低于库内问题，"
        "说明检索无法区分'有没有资料'，拒答就无从谈起"
    )
