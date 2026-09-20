"""从 Locust 的 CSV 结果里汇总出各档并发指标，并画两张图。"""
import pandas as pd
import matplotlib.pyplot as plt

# 解决matplotlib中文方块问题
plt.rcParams['font.sans-serif']=['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

LEVELS = [10, 50, 100, 200, 400]
rows = []
for u in LEVELS:
    csv_path = f"reports/run_{u}_stats.csv"
    # 容错编码读取
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        print(f"⚠️ 文件 {csv_path} utf‑8读取失败，切换GBK编码")
        df = pd.read_csv(csv_path, encoding="gbk")

    agg = df[df["Name"] == "Aggregated"].iloc[0]
    rows.append({
        "并发用户数": u,
        "RPS": round(float(agg["Requests/s"]), 2),
        "P50(ms)": round(float(agg["50%"]), 1),
        "P95(ms)": round(float(agg["95%"]), 1),
        "请求总数": int(agg["Request Count"]),
        "失败数": int(agg["Failure Count"]),
    })

out = pd.DataFrame(rows)
print("\n====汇总结果====")
print(out.to_string(index=False))
# 输出summary.csv用utf‑8‑sig，Excel双击不乱码
out.to_csv("reports/summary.csv", index=False, encoding="utf-8-sig")

# 画图
fig, ax1 = plt.subplots(figsize=(8, 5))
ax1.plot(out["并发用户数"], out["RPS"], "o-", color="#1f77b4", label="RPS")
ax1.set_xlabel("并发用户数")
ax1.set_ylabel("RPS（吞吐）", color="#1f77b4")
ax2 = ax1.twinx()
ax2.plot(out["并发用户数"], out["P95(ms)"], "s--", color="#d62728", label="P95")
ax2.set_ylabel("P95 响应时间 (ms)", color="#d62728")
plt.title("并发 - 吞吐 / P95 曲线")
fig.tight_layout()
plt.savefig("reports/curve.png", dpi=150)
print("\n✅执行完成！")
print("✅汇总表格文件：reports/summary.csv")
print("✅性能曲线图：reports/curve.png")
