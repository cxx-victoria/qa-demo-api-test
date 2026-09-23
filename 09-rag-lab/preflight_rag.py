"""RAG 预检：在跑测试之前，先确认最脆弱的三个环节是通的。

为什么要预检：
    RAG 链路比前面任何一个模块都长：embedding 接口 → 本地缓存 → 余弦检索 → 生成接口。
    任何一环不通，测试都会报出一堆看不懂的错。
    所以先花 30 秒跑这个脚本，把"环境问题"和"真实的 RAG 质量问题"分开。

检查项：
    1. 环境变量是否配置
    2. **embedding 接口是否可用**（最容易出问题的一环）
    3. 知识库能否加载、分块是否合理
    4. 索引能否构建（第一次会调用接口，之后走本地缓存）
    5. 一次真实检索的抽查
    6. 生成接口是否可用

用法：
    cd D:\\qa-projects\\09-rag-lab
    python preflight_rag.py
"""
import statistics
import sys

import rag

OK = "[OK]  "
FAIL = "[FAIL]"
WARN = "[WARN]"

problems = []


def check(name, func):
    try:
        detail = func()
        print(f"{OK} {name}" + (f" —— {detail}" if detail else ""))
        return True
    except Exception as exc:
        print(f"{FAIL} {name} —— {type(exc).__name__}: {exc}")
        problems.append((name, exc))
        return False


print("=" * 72)
print("RAG 环境预检")
print("=" * 72)


def step_env():
    if not rag.BASE_URL:
        raise RuntimeError("OPENAI_BASE_URL 为空")
    if not rag.API_KEY:
        raise RuntimeError("OPENAI_API_KEY 为空")
    masked = rag.API_KEY[:8] + "****"
    return f"BASE_URL={rag.BASE_URL}  KEY={masked}  EMBED={rag.EMBED_MODEL}  CHAT={rag.CHAT_MODEL}"


def step_docs():
    docs = rag.load_documents()
    if len(docs) < 7:
        raise RuntimeError(f"只加载到 {len(docs)} 个文档，期望 ≥7（检查 kb/ 目录）")
    chunks = rag.build_chunks()
    lengths = [len(c["text"]) for c in chunks]
    return (f"文档 {len(docs)} 个 / 片段 {len(chunks)} 个 / "
            f"平均 {statistics.mean(lengths):.0f} 字（最短 {min(lengths)}）")


def step_embed():
    vectors = rag.embed_texts(["这是一次 embedding 连通性测试"])
    if not vectors or not vectors[0]:
        raise RuntimeError("embedding 返回为空")
    return f"向量维度 {len(vectors[0])}"


def step_index():
    index = rag.build_index()
    if not index:
        raise RuntimeError("索引为空")
    return f"索引 {len(index)} 条"


def step_retrieve():
    hits = rag.retrieve("运费怎么算？", k=3)
    if not hits:
        raise RuntimeError("检索返回为空")
    summary = " | ".join(f"{h['source']}({h['score']:.3f})" for h in hits)
    if hits[0]["source"] != "02_运费规则.md":
        raise RuntimeError(
            f"抽查未命中预期文档，Top-1 是 {hits[0]['source']}。含义：检索效果不理想，"
            f"后续 Recall@K 可能不达标。Top-3 = {summary}"
        )
    return f"Top-3 = {summary}"


def step_chat():
    result = rag.answer("退货可以退几天？", k=3)
    answer = result["answer"].strip()
    if not answer:
        raise RuntimeError("生成返回为空")
    return f"回答前 40 字：{answer[:40]}"


check("1. 环境变量", step_env)
check("2. 知识库加载与分块", step_docs)
check("3. Embedding 接口", step_embed)
check("4. 索引构建（首次会调用接口，之后走缓存）", step_index)
check("5. 检索抽查：'运费怎么算？'", step_retrieve)
check("6. 生成接口（检索 + 拼上下文 + 生成）", step_chat)

print()
print("=" * 72)
if problems:
    print(f"预检未通过，共 {len(problems)} 项问题：")
    for name, exc in problems:
        print(f"  · {name}: {exc}")
    print()
    print("提示：先解决上面这些问题，再跑 pytest，否则报错会混在一起。")
    sys.exit(1)

print("预检全部通过，可以开始跑测试：")
print("    python -m pytest test_rag_retrieval.py -v -s")
print("    python -m pytest test_rag_quality.py  -v -s")
print("=" * 72)
