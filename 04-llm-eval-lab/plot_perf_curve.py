# -*- coding: utf-8 -*-
"""
plot_perf_curve.py —— 画并发梯度曲线图（数据已填入你的真实实测值）

用法：
    cd D:\qa-projects\04-llm-eval-lab
    .\.venv312\Scripts\python.exe plot_perf_curve.py

输出：
    outputs/perf_curve.png         并发 vs RPS / TTFT 双轴图
    outputs/perf_curve_2panel.png  RPS 与延迟两个子图
"""
import os
import sys

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
except ImportError:
    print("没有 matplotlib，请先安装：")
    print('  & "$env:APPDATA\\Python\\Python313\\Scripts\\uv.exe" pip install --python .\\.venv312\\Scripts\\python.exe matplotlib')
    sys.exit(1)

# 让中文正常显示（Windows 自带的微软雅黑）
for _name in ("Microsoft YaHei", "SimHei", "Arial Unicode MS"):
    try:
        font_manager.findfont(_name, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [_name]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

# =============================================================
# 实测数据（EvalScope 1.12.0 / openqa / max-tokens=256）
# =============================================================
parallels = [1, 5, 10, 20, 40, 80, 100]
rps = [0.18, 0.84, 1.69, 3.26, 6.55, 13.33, 16.21]
ttft = [385, 393, 420, 497, 521, 518, 522]
tpot = [19.8, 18.0, 17.5, 17.0, 16.6, 16.4, 16.7]
latency = [5.43, 4.98, 4.88, 4.83, 4.75, 4.70, 4.76]

OUT = "outputs"
os.makedirs(OUT, exist_ok=True)

# ---------------- 图 1：双轴图（RPS + TTFT） ----------------
fig, ax1 = plt.subplots(figsize=(9, 5.5))
ax1.plot(parallels, rps, "o-", color="#1f77b4", linewidth=2, markersize=7, label="RPS（吞吐）")
ax1.set_xlabel("并发数 (parallel)", fontsize=12)
ax1.set_ylabel("RPS（请求/秒）", color="#1f77b4", fontsize=12)
ax1.tick_params(axis="y", labelcolor="#1f77b4")
ax1.grid(alpha=0.3)
for x, y in zip(parallels, rps):
    ax1.annotate(f"{y}", (x, y), textcoords="offset points", xytext=(0, 8),
                 ha="center", fontsize=9, color="#1f77b4")

ax2 = ax1.twinx()
ax2.plot(parallels, ttft, "s--", color="#d62728", linewidth=2, markersize=7, label="TTFT（首字延迟）")
ax2.set_ylabel("TTFT 首字延迟 (ms)", color="#d62728", fontsize=12)
ax2.tick_params(axis="y", labelcolor="#d62728")

lines = ax1.get_lines() + ax2.get_lines()
ax1.legend(lines, [l.get_label() for l in lines], loc="upper left", fontsize=10)
plt.title("qwen-plus 并发梯度：吞吐线性增长，TTFT 轻微上升（100 并发内无拐点）", fontsize=12)
fig.tight_layout()
plt.savefig(f"{OUT}/perf_curve.png", dpi=150)
print(f"已保存：{OUT}/perf_curve.png")

# ---------------- 图 2：两个子图 ----------------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))

a1.plot(parallels, rps, "o-", color="#1f77b4", linewidth=2, markersize=7)
a1.set_xlabel("并发数")
a1.set_ylabel("RPS")
a1.set_title("吞吐随并发增长（接近线性，未见拐点）")
a1.grid(alpha=0.3)

a2.plot(parallels, latency, "^-", color="#2ca02c", linewidth=2, markersize=7, label="总延迟(s)")
a2.plot(parallels, [t / 100 for t in tpot], "s--", color="#ff7f0e",
        linewidth=2, markersize=7, label="TPOT(ms) ÷ 100")
a2.set_xlabel("并发数")
a2.set_ylabel("延迟")
a2.set_title("延迟基本平稳（总延迟 4.7~5.4s）")
a2.legend(fontsize=9)
a2.grid(alpha=0.3)

fig.suptitle("qwen-plus 性能压测结果（EvalScope 1.12.0 / openqa / max-tokens=256）", fontsize=13)
fig.tight_layout()
plt.savefig(f"{OUT}/perf_curve_2panel.png", dpi=150)
print(f"已保存：{OUT}/perf_curve_2panel.png")
