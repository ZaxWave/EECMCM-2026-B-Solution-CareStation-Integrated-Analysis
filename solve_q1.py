"""
solve_q1.py — Q1 马尔可夫链老年人口预测 (电工杯 B题 2026)
============================================================
Stage 05 | 竞赛: diangong | 模式: standard
基于 §3.2 增生型转移矩阵, 递推预测 10 个小区 5 年内三类老人数量变化.
输出: figures/figure_q1_population_trend.png + results/q1_final_population.csv

架构: 数据挂载 → 矩阵构造 → 递推求解 → 需求预测(Q1.2/Q1.3) → 可视化 → CSV导出
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path
import os, sys

# ---- 全局样式 (Windows 强注册中文字体, 消除方框) ----
fm.fontManager.addfont('C:/Windows/Fonts/simhei.ttf')
fm._load_fontmanager(try_read_cache=False)

sns.set_theme(style="whitegrid", context="paper")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Microsoft YaHei", "Noto Sans SC", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 16,
    "axes.titlesize": 18,
    "axes.labelsize": 15,
    "legend.fontsize": 14,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

Path("results").mkdir(exist_ok=True)
Path("figures").mkdir(exist_ok=True)

BASE = os.path.join(os.path.dirname(__file__), "data")

# ============================================================
# §1 数据挂载: 读取附件1 初始状态向量 S_i^(0)
# ============================================================
def load_initial_state():
    """读取附件1 人口与老人结构, 返回基年(t=0)各小区三类老人数."""
    df_pop = pd.read_excel(
        os.path.join(BASE, "附件1：小区基础数据.xlsx"),
        sheet_name="人口与老人结构", skiprows=1
    )
    df_pop.columns = ["小区", "总人口", "60plus", "自理", "半失能", "失能", "人均月收入"]
    communities = df_pop["小区"].tolist()  # A-J

    # 初始状态向量矩阵: (10, 3), 列=[自理, 半失能, 失能]
    S0 = df_pop[["自理", "半失能", "失能"]].values.astype(np.float64)  # (10, 3)
    income = df_pop["人均月收入"].values.astype(np.float64)

    print("[数据挂载] 基年(t=0)各小区老年人口:")
    print(f"  {'小区':<6} {'自理':>6} {'半失能':>6} {'失能':>6} {'60+合计':>8} {'月收入':>6}")
    for i, comm in enumerate(communities):
        total = S0[i].sum()
        print(f"  {comm:<6} {S0[i,0]:6.0f} {S0[i,1]:6.0f} {S0[i,2]:6.0f} {total:8.0f} {income[i]:6.0f}")
    print(f"  {'合计':<6} {S0[:,0].sum():6.0f} {S0[:,1].sum():6.0f} {S0[:,2].sum():6.0f} {S0.sum():8.0f}")

    return communities, S0, income


# ============================================================
# §2 增生型马尔可夫转移矩阵 A (式3.2)
# ============================================================
def build_transition_matrix(mu=0.05, alpha_sm=0.045, alpha_md=0.10, beta=0.07):
    """
    构造 §3.2 式(2) 的 3×3 增生型转移矩阵.
    S^{(t+1)} = A · S^{(t)}  (列向量约定)
    """
    A = np.array([
        [(1 - mu) * (1 - alpha_sm) + beta,  beta,                              beta],
        [(1 - mu) * alpha_sm,               (1 - mu) * (1 - alpha_md),         0.0],
        [0.0,                               (1 - mu) * alpha_md,               (1 - mu)],
    ])
    return A


# ============================================================
# §3 递推预测: 5年逐小区连乘
# ============================================================
def predict_population(S0, A, T=5):
    """
    对每个小区独立运行 T 年递推.
    返回: S_history (T+1, n_communities, 3) — t=0..T 年末状态
    """
    n_comm = S0.shape[0]
    S_history = np.zeros((T + 1, n_comm, 3))
    S_history[0] = S0.copy()

    for t in range(T):
        for i in range(n_comm):
            S_history[t + 1, i] = np.round(A @ S_history[t, i])

    return S_history


# ============================================================
# §4 服务需求预测 (Q1.2 理论 + Q1.3 消费约束)
# ============================================================
def load_service_data():
    """读取附件2 服务需求数据."""
    df_demand = pd.read_excel(
        os.path.join(BASE, "附件2：服务需求数据.xlsx"),
        sheet_name="每位老人月均服务需求次数", skiprows=1
    )
    df_demand.columns = ["服务项目", "自理", "半自理", "失能"]
    # 每人月均需求次数矩阵: (6服务, 3类型)
    demand_per_capita = df_demand[["自理", "半自理", "失能"]].values.astype(np.float64)
    services = df_demand["服务项目"].tolist()

    # 营收数据 (手动录入, 避免字符串解析)
    revenue = np.array([10, 20, 30, 28, 25, 0], dtype=np.float64)   # 紧急救助=0
    cost = np.array([8, 16, 24, 23, 20, 8], dtype=np.float64)

    return services, demand_per_capita, revenue, cost


def compute_demand(S_final, demand_per_capita, revenue, income, consumption_caps):
    """
    Q1.2: 理论需求 = 人口 × 人均需求次数
    Q1.3: 实际需求 = 理论需求 × 消费约束削减因子
    """
    n_comm, n_type = S_final.shape
    n_svc = demand_per_capita.shape[0]

    # Q1.2 理论月需求: (10, 3, 6)
    theoretical = np.zeros((n_comm, n_type, n_svc))
    for i in range(n_comm):
        for e in range(n_type):
            theoretical[i, e, :] = S_final[i, e] * demand_per_capita[:, e]

    # Q1.3 消费约束削减
    caps = np.array(consumption_caps)  # [0.20, 0.25, 0.30]
    actual = np.zeros_like(theoretical)

    for i in range(n_comm):
        for e in range(n_type):
            # 全量消费额
            full_cost = np.sum(demand_per_capita[:, e] * revenue)
            budget = income[i] * caps[e]
            if full_cost <= budget:
                ratio = 1.0
            else:
                ratio = budget / full_cost
            actual[i, e, :] = theoretical[i, e, :] * ratio

    return theoretical, actual


# ============================================================
# §5 可视化: 学术级图表
# ============================================================
def plot_population_trends(communities, S_history):
    """各小区三类老人5年演化折线图 + 总量堆叠图."""
    T_plus_1, n_comm, _ = S_history.shape
    years = np.arange(T_plus_1)

    # ----- 5(a): 分小区子图 (3×4 grid) -----
    fig, axes = plt.subplots(3, 4, figsize=(22, 15))
    axes_flat = axes.flatten()
    colors = ["#2E86AB", "#D64045", "#F18F01"]  # 自理/半失能/失能
    labels = ["自理 (Self-care)", "半失能 (Semi-disabled)", "失能 (Disabled)"]

    for idx in range(n_comm):
        ax = axes_flat[idx]
        for e in range(3):
            ax.plot(years, S_history[:, idx, e], marker='o', linewidth=1.8,
                    color=colors[e], label=labels[e], markersize=4)
        ax.set_title(f"小区 {communities[idx]}", fontweight="bold")
        ax.set_xlabel("年份")
        ax.set_ylabel("人数")
        ax.legend(fontsize=11, loc="upper left")
        ax.set_xticks(years)
        ax.set_xlim(-0.2, T_plus_1 - 1 + 0.2)

    # 隐藏多余子图
    for idx in range(n_comm, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle("各小区老年人口状态演化 (马尔可夫递推预测, t=0~5年)",
                 fontsize=15, fontweight="bold", y=0.995)
    plt.tight_layout()
    fig.savefig("figures/figure_q1_population_trend.png", dpi=300)
    plt.close()
    print("[图表] figure_q1_population_trend.png 已保存")

    # ----- 5(b): 全区域三类老人总量演化 -----
    total_by_type = S_history.sum(axis=1)  # (T+1, 3)

    fig, ax = plt.subplots(figsize=(10, 6))
    for e in range(3):
        ax.plot(years, total_by_type[:, e], marker='s', linewidth=2.5,
                color=colors[e], label=labels[e], markersize=7)
    ax.set_title("全区域三类老人总量演化趋势", fontsize=14, fontweight="bold")
    ax.set_xlabel("年份")
    ax.set_ylabel("总人数")
    ax.legend(fontsize=13)
    ax.set_xticks(years)
    ax.grid(True, alpha=0.3)

    # 标注变化量
    for e in range(3):
        delta = total_by_type[-1, e] - total_by_type[0, e]
        ax.annotate(f"{delta:+.0f} ({delta/total_by_type[0,e]*100:+.1f}%)",
                    xy=(years[-1], total_by_type[-1, e]),
                    xytext=(15, 15), textcoords="offset points",
                    fontsize=9, color=colors[e],
                    arrowprops=dict(arrowstyle="->", color=colors[e], lw=0.8))

    plt.tight_layout()
    fig.savefig("figures/figure_q1_total_trend.png", dpi=300)
    plt.close()
    print("[图表] figure_q1_total_trend.png 已保存")

    # ----- 5(c): 堆叠柱状图 (t=0 vs t=5 对比) -----
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))
    bar_width = 0.6
    x = np.arange(n_comm)

    for ax_idx, t in enumerate([0, T_plus_1 - 1]):
        ax = axes[ax_idx]
        bottom = np.zeros(n_comm)
        for e in range(3):
            ax.bar(x, S_history[t, :, e], bar_width, bottom=bottom,
                   color=colors[e], label=labels[e], edgecolor="white", linewidth=0.5)
            bottom += S_history[t, :, e]
        ax.set_title(f"t={t} 年末" if t > 0 else "t=0 (基年)", fontsize=13, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(communities)
        ax.set_ylabel("老年人口数")
        ax.legend(fontsize=12)

    fig.suptitle("基年 vs 第5年末 各小区老年人口结构对比",
                 fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig("figures/figure_q1_stacked_bar.png", dpi=300)
    plt.close()
    print("[图表] figure_q1_stacked_bar.png 已保存")


# ============================================================
# §6 数据导出: 为 Q2 MILP 提供无缝输入
# ============================================================
def export_results(communities, S_final, theoretical, actual, income,
                   services, revenue, cost):
    """导出 Q1 全部结果到 CSV."""

    # ---- 6a: q1_final_population.csv (Q2选址主输入) ----
    df_pop_export = pd.DataFrame({
        "小区": communities,
        "自理": S_final[:, 0].astype(int),
        "半失能": S_final[:, 1].astype(int),
        "失能": S_final[:, 2].astype(int),
        "60plus_total": S_final.sum(axis=1).astype(int),
        "人均月收入": income.astype(int),
    })
    df_pop_export.to_csv("results/q1_final_population.csv", index=False, encoding="utf-8-sig")
    print(f"[导出] results/q1_final_population.csv — 第5年末各小区人口 ({len(communities)}行)")

    # ---- 6b: q1_service_demand.csv (Q2/Q3需求输入) ----
    n_comm, n_type, n_svc = theoretical.shape
    rows = []
    for i, comm in enumerate(communities):
        for e, etype in enumerate(["自理", "半失能", "失能"]):
            for s, svc in enumerate(services):
                rows.append({
                    "小区": comm,
                    "老人类型": etype,
                    "服务项目": svc,
                    "理论月需求(次)": round(theoretical[i, e, s]),
                    "实际月需求(次)": round(actual[i, e, s]),
                    "单次营收(元)": revenue[s],
                    "单次成本(元)": cost[s],
                })
    df_demand_export = pd.DataFrame(rows)
    df_demand_export.to_csv("results/q1_service_demand.csv", index=False, encoding="utf-8-sig")
    print(f"[导出] results/q1_service_demand.csv — 服务需求明细 ({len(rows)}行)")

    # ---- 6c: q1_summary_stats.csv ----
    summary = {
        "指标": [
            "基年60+总人口", "第5年末60+总人口", "5年净增",
            "基年自理", "第5年末自理", "自理变化",
            "基年半失能", "第5年末半失能", "半失能变化",
            "基年失能", "第5年末失能", "失能变化",
            "基年失能率", "第5年末失能率",
            "理论月需求总量(次)", "实际月需求总量(次)", "消费约束削减率",
        ],
        "数值": [
            S_history[0].sum(),
            S_final.sum(),
            S_final.sum() - S_history[0].sum(),
            S_history[0, :, 0].sum(), S_final[:, 0].sum(),
            S_final[:, 0].sum() - S_history[0, :, 0].sum(),
            S_history[0, :, 1].sum(), S_final[:, 1].sum(),
            S_final[:, 1].sum() - S_history[0, :, 1].sum(),
            S_history[0, :, 2].sum(), S_final[:, 2].sum(),
            S_final[:, 2].sum() - S_history[0, :, 2].sum(),
            S_history[0, :, 2].sum() / S_history[0].sum() * 100,
            S_final[:, 2].sum() / S_final.sum() * 100,
            theoretical.sum(),
            actual.sum(),
            (1 - actual.sum() / theoretical.sum()) * 100,
        ],
    }
    df_summary = pd.DataFrame(summary)
    df_summary.to_csv("results/q1_summary_stats.csv", index=False, encoding="utf-8-sig")
    print(f"[导出] results/q1_summary_stats.csv — 汇总统计")


# ============================================================
# §7 主流程
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Q1 马尔可夫链老年人口预测求解器")
    print("竞赛: 电工杯 B题 | 方法: 增生型Markov chain | 求解器: numpy")
    print("=" * 60)

    # Step 1: 数据挂载
    communities, S0, income = load_initial_state()

    # Step 2: 构造转移矩阵
    A = build_transition_matrix()
    print(f"\n[转移矩阵] A =\n{A}")

    # Step 3: 5年递推预测
    S_history = predict_population(S0, A, T=5)
    S_final = S_history[-1]  # t=5 年末

    print(f"\n[预测结果] 第5年末各小区老年人口:")
    for i, comm in enumerate(communities):
        print(f"  {comm}: 自理={S_final[i,0]:.0f}, 半失能={S_final[i,1]:.0f}, "
              f"失能={S_final[i,2]:.0f}, 合计={S_final[i].sum():.0f}")

    print(f"\n  全区域: 自理={S_final[:,0].sum():.0f}, 半失能={S_final[:,1].sum():.0f}, "
          f"失能={S_final[:,2].sum():.0f}, 合计={S_final.sum():.0f}")

    # Step 4: 服务需求预测
    services, demand_per_capita, revenue, cost = load_service_data()
    theoretical, actual = compute_demand(
        S_final, demand_per_capita, revenue, income,
        consumption_caps=[0.20, 0.25, 0.30]
    )

    print(f"\n[需求预测] 第5年末月服务需求:")
    print(f"  理论需求总量: {theoretical.sum():.0f} 次/月")
    print(f"  实际需求总量: {actual.sum():.0f} 次/月")
    print(f"  消费约束削减率: {(1 - actual.sum()/theoretical.sum())*100:.1f}%")

    # Step 5: 可视化
    plot_population_trends(communities, S_history)

    # Step 6: 导出
    export_results(communities, S_final, theoretical, actual, income,
                   services, revenue, cost)

    print("\n" + "=" * 60)
    print("Q1 求解完成. 输出文件:")
    print("  figures/figure_q1_population_trend.png")
    print("  figures/figure_q1_total_trend.png")
    print("  figures/figure_q1_stacked_bar.png")
    print("  results/q1_final_population.csv     ← Q2 MILP 输入")
    print("  results/q1_service_demand.csv       ← Q2/Q3 需求输入")
    print("  results/q1_summary_stats.csv        ← 汇总统计")
    print("=" * 60)
