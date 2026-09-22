# -*- coding: utf-8 -*-
"""
flaky_report.py —— 统计多轮 Playwright 执行结果，算每条用例的通过率和整体 flaky 率

用法：
    1) 先跑 5 轮（生成 run1.json ~ run5.json）：
       1..5 | ForEach-Object {
         Write-Host "===== 第 $_ 轮 =====" -ForegroundColor Cyan
         $env:PLAYWRIGHT_JSON_OUTPUT_NAME = "run$_.json"
         npx playwright test 02_todo_full --reporter=json
       }
    2) 再执行：python flaky_report.py

⚠️ 踩坑记录（v2 修复）：Playwright JSON 报告里有两个容易混淆的字段
    - tests[0].status   = "expected"  ← 表示"这个用例期望通过"（不是执行结果！）
    - results[0].status = "passed"    ← 这才是本次执行的真实结果
    v1 脚本错把 "expected" 当成了"通过"，导致所有用例都被判成 0%。
    v2 优先使用 spec.ok（布尔值），最可靠。
"""
import glob
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def collect_results(node, out):
    """递归遍历 Playwright JSON 报告，收集 {用例标题: [每轮是否通过]}。"""
    if not isinstance(node, dict):
        return
    for spec in node.get("specs", []) or []:
        title = spec.get("title") or "(无标题)"
        # ✅ 首选 spec.ok —— Playwright 直接给出的布尔结果
        ok = spec.get("ok")
        if ok is None:
            # 回退：results[].status 是否都是 "passed"
            tests = spec.get("tests") or []
            if tests:
                results = tests[0].get("results") or []
                statuses = [r.get("status") for r in results]
                ok = bool(statuses) and all(s == "passed" for s in statuses)
            else:
                ok = False
        out.setdefault(title, []).append(bool(ok))
    for child in node.get("suites", []) or []:
        collect_results(child, out)


files = sorted(glob.glob("run*.json"))
if not files:
    print("❌ 没找到 run*.json，请先跑那 5 轮测试")
    sys.exit(1)

rounds = len(files)
print("=" * 74)
print(f"统计数据：{rounds} 轮")
print("=" * 74)

# 每轮总览（来自各轮的 stats 字段）
for path in files:
    try:
        st = (json.load(open(path, encoding="utf-8")) or {}).get("stats") or {}
    except Exception:
        st = {}
    if st:
        print(f"  {os.path.basename(path)}: 通过 {st.get('expected', '?')}"
              f" / 失败 {st.get('unexpected', '?')}"
              f" / flaky {st.get('flaky', '?')}"
              f" / 跳过 {st.get('skipped', '?')}")

results = {}
for path in files:
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ {path} 解析失败：{e}")
        continue
    collect_results(data, results)

if not results:
    print("❌ 报告里没有解析到任何用例。请把 run1.json 的前 500 个字符发我，我按实际结构调整脚本。")
    sys.exit(1)

print()
print(f"共 {len(results)} 条用例")
print("-" * 74)
print(f"{'用例':<46}{'通过轮次':<12}{'通过率'}")
print("-" * 74)

unstable = []
for title, flags in results.items():
    n = len(flags)
    passed = sum(flags)
    rate = passed / n * 100 if n else 0
    name = title if len(title) <= 44 else title[:43] + "…"
    print(f"{name:<46}{f'{passed}/{n}':<12}{rate:>6.1f}%")
    if rate < 100:
        unstable.append((title, rate, passed, n))

print("-" * 74)
total = len(results)
flaky_rate = len(unstable) / total * 100 if total else 0
print(f"整体 flaky 率：{flaky_rate:.1f}%（{len(unstable)}/{total} 条不稳定）")

if unstable:
    print("\n不稳定的用例（要重点分析根因）：")
    for title, rate, passed, n in sorted(unstable, key=lambda x: x[1]):
        print(f"  {rate:5.1f}%  ({passed}/{n})  {title}")

print("\n" + "=" * 74)
print("可直接粘进报告的表格：")
print("=" * 74)
print("| 用例 | 通过轮次 | 通过率 |")
print("|------|----------|--------|")
for title, flags in results.items():
    n = len(flags)
    passed = sum(flags)
    print(f"| {title} | {passed}/{n} | {passed / n * 100:.1f}% |")
print(f"| **整体 flaky 率** | — | **{flaky_rate:.1f}%**（{len(unstable)}/{total} 条不稳定） |")
