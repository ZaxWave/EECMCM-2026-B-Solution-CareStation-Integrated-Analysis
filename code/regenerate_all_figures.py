"""
regenerate_all_figures.py — Academic Noir 统一图表再生 (电工杯 B题 2026)
======================================================================
Visio-style学术级配色: NAVY/CYAN/ROSE/AMBER/TEAL
生成全部论文插图 + 技术路线流程图, 风格统一, 适合学术印刷.

Usage: python regenerate_all_figures.py
Output: figures/ 目录下 9 张高质量 PNG (300dpi)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc
import matplotlib.ticker as ticker
import seaborn as sns
import networkx as nx
from pathlib import Path
import os, sys, json, warnings
warnings.filterwarnings('ignore')

# ============================================================
# §0 全局样式 — Academic Noir Palette
# ============================================================
NAVY   = '#1B2A4A'   # 主文字/深色元素
CYAN   = '#2E86AB'   # 自理老人 / 主强调色
ROSE   = '#A23B72'   # 失能老人 / 警告色
AMBER  = '#F18F01'   # 半失能老人 / 过渡色
TEAL   = '#0D7377'   # 站点标识
SLATE  = '#5D6D7E'   # 中性灰蓝
CREAM  = '#F5F0EB'   # 暖色背景
WHITE  = '#FFFFFF'
GOLD   = '#D4A843'   # 补贴/利润强调
CORAL  = '#E85D75'   # 预算线/阈值

PALETTE_3 = [CYAN, AMBER, ROSE]          # 自理/半失能/失能
PALETTE_6 = [NAVY, CYAN, TEAL, ROSE, AMBER, GOLD]

LABELS_3 = ['自理 (Self-care)', '半失能 (Semi-disabled)', '失能 (Disabled)']

# ---- 字体注册 ----
def register_fonts():
    for fp in ['C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simkai.ttf',
               'C:/Windows/Fonts/simsun.ttc', 'C:/Windows/Fonts/msyh.ttc']:
        try: fm.fontManager.addfont(fp)
        except: pass
    fm._load_fontmanager(try_read_cache=False)
    names = [f.name for f in fm.fontManager.ttflist]
    return 'SimHei' if 'SimHei' in names else ('Microsoft YaHei' if 'Microsoft YaHei' in names else names[0])

FONT = register_fonts()

def set_style():
    sns.set_style("white")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONT, "Microsoft YaHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 13,
        "axes.titlesize": 15,
        "axes.labelsize": 13,
        "legend.fontsize": 12,
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
        "figure.dpi": 300, "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.8,
        "axes.edgecolor": SLATE,
        "xtick.color": SLATE, "ytick.color": SLATE,
        "grid.alpha": 0.15, "grid.color": SLATE,
    })

set_style()
os.makedirs("../figures", exist_ok=True)

# ---- 数据路径 ----
BASE = os.path.join(os.path.dirname(__file__), "..", "data")
RES  = os.path.join(os.path.dirname(__file__), "..", "results")
FIG  = os.path.join(os.path.dirname(__file__), "..", "paper_workspace", "figures")

def load_q1_data():
    """加载 Q1 人口预测结果."""
    df_pop = pd.read_csv(os.path.join(RES, "q1_final_population.csv"))
    df_sum = pd.read_csv(os.path.join(RES, "q1_summary_stats.csv"))
    return df_pop, df_sum

def load_q2_data():
    """加载 Q2 最优解."""
    with open(os.path.join(RES, "q2_baseline.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def load_q3_data():
    """加载 Q3 定价结果."""
    df_p = pd.read_csv(os.path.join(RES, "q3_optimal_pricing.csv"))
    df_profit = pd.read_csv(os.path.join(RES, "q3_station_profit.csv"))
    return df_p, df_profit

def load_distance_matrix():
    """加载距离矩阵."""
    communities = ['A','B','C','D','E','F','G','H','I','J']
    df = pd.read_excel(os.path.join(BASE, "附件4：小区间距离矩阵.xlsx"),
                       sheet_name="小区间距离矩阵", skiprows=1)
    df.columns = ["小区"] + communities
    df = df.dropna(subset=["小区"]).set_index("小区")
    return communities, df.values.astype(float), (df.values <= 1000)

def despine_fully(ax):
    """完全去 spines, 仅保留网格线."""
    for s in ['top','right','left','bottom']:
        ax.spines[s].set_visible(False)
    ax.tick_params(left=False, bottom=False)

# ============================================================
# §1 技术路线流程图 (NEW — Visio-style)
# ============================================================
def make_figure_tech_route():
    """四阶段技术路线流程图 — 垂直管道式设计."""
    fig, ax = plt.subplots(figsize=(12, 16))
    fig.patch.set_facecolor(WHITE)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 16)
    ax.axis('off')

    colors = [CYAN, TEAL, ROSE, AMBER]
    nums = ["01", "02", "03", "04"]
    titles = ["人口预测", "选址-规模优化", "差异化定价", "鲁棒性检验"]
    subs = ["Markov Chain\n+ Leslie Matrix", "MILP-MCLP-ES\nBig-M + McCormick", "词典序 MILP\nRamsey-Boiteux", "三场景 MILP\n独立重求解"]
    methods = [
        "增生型转移矩阵 A\n消费约束等比例削减\n双模型三角校验 (偏差 1.7%)",
        "覆盖权重 5.0 + 满意度权重 0.5\nMcCormick 乘积解耦\nCBC 分支定界 (gap<1%)",
        "S₃ 最大化优先\nε = 10⁻⁴ 营收弱激励\nRamsey 反向价格歧视",
        "人口·成本·预算三组扰动\n韧性矩阵 ρ = 1−|ΔX/X|\n三级分级 (高韧/中韧/脆弱)",
    ]
    outputs = [
        "7,577 人 (失能 +80.3%)\n247,060 次/月实际需求\n→ Q2 输入 CSV",
        "F(大) + H(中) + J(中)\n109 万 / 120 万\n10/10 全覆盖",
        "上门护理 12.64 元 (−57.9%)\n全 S₃ = 1.000\n交叉补贴率 14.3%",
        "九维度 ρ > 0.80\n预算 140 万 → S = 0.889\n强鲁棒性判定",
    ]

    # ---- layout params ----
    card_w, card_h = 8.6, 2.7
    center_x = 6.0
    start_y = 12.6
    gap = 3.6
    arrow_head_w = 0.25
    arrow_head_h = 0.28

    for i in range(4):
        y0 = start_y - i * gap
        c = colors[i]

        # ── card shadow ──
        shadow = FancyBboxPatch((center_x - card_w/2 + 0.08, y0 - card_h - 0.08),
                                 card_w, card_h, boxstyle="round,pad=0.25",
                                 facecolor='#E2E2E2', edgecolor='none', alpha=0.4, zorder=1)
        ax.add_patch(shadow)

        # ── main card ──
        card = FancyBboxPatch((center_x - card_w/2, y0 - card_h), card_w, card_h,
                               boxstyle="round,pad=0.25", facecolor=WHITE,
                               edgecolor=c, lw=2.5, zorder=2)
        ax.add_patch(card)

        # ── left accent bar ──
        bar_w = 0.14
        bar = FancyBboxPatch((center_x - card_w/2 + 0.15, y0 - card_h + 0.3),
                              bar_w, card_h - 0.6, boxstyle="round,pad=0.04",
                              facecolor=c, edgecolor='none', alpha=0.85, zorder=3)
        ax.add_patch(bar)

        # ── stage number circle ──
        circle = mpatches.Circle((center_x - card_w/2 + 0.95, y0 - card_h/2),
                                  0.42, facecolor=c, edgecolor='white', lw=2.5, zorder=4)
        ax.add_patch(circle)
        ax.text(center_x - card_w/2 + 0.95, y0 - card_h/2, nums[i],
                ha='center', va='center', fontsize=14, fontweight='bold',
                color=WHITE, zorder=5)

        # ── title ──
        ax.text(center_x - card_w/2 + 1.55, y0 - 0.45, titles[i],
                ha='left', va='center', fontsize=14.5, fontweight='bold',
                color=NAVY, zorder=4)
        ax.text(center_x - card_w/2 + 1.55, y0 - 0.85, subs[i],
                ha='left', va='center', fontsize=8.5, color=c, style='italic',
                zorder=4)

        # ── divider ──
        div_y = y0 - 1.25
        ax.plot([center_x - card_w/2 + 0.5, center_x + card_w/2 - 0.5],
                [div_y, div_y], color=c, lw=0.6, alpha=0.35, zorder=3)

        # ── method (left column) ──
        lx = center_x - card_w/2 + 0.55
        ax.text(lx, div_y - 0.30, "▎方法", ha='left', va='top',
                fontsize=7.8, color=SLATE, fontweight='bold', zorder=4)
        ax.text(lx, div_y - 0.58, methods[i], ha='left', va='top',
                fontsize=9, color=NAVY, zorder=4, linespacing=1.45)

        # ── output (right column) ──
        rx = center_x + card_w/2 - 0.55
        ax.text(rx, div_y - 0.30, "▎关键输出", ha='right', va='top',
                fontsize=7.8, color=SLATE, fontweight='bold', zorder=4)
        ax.text(rx, div_y - 0.58, outputs[i], ha='right', va='top',
                fontsize=9, color=NAVY, zorder=4, linespacing=1.45)

    # ── connecting arrows between cards ──
    for i in range(3):
        y_from = start_y - i * gap - card_h
        y_to = start_y - (i+1) * gap
        mid_y = (y_from + y_to) / 2

        # vertical line
        ax.annotate("", xy=(center_x, y_to + arrow_head_h/2),
                    xytext=(center_x, y_from - arrow_head_h/2),
                    arrowprops=dict(arrowstyle="->", color=SLATE, lw=2.0,
                                   connectionstyle="arc3,rad=0"), zorder=5)

        # data flow label (right side)
        data_labels = ["人口·需求 CSV", "y*/x* 选址固化", "p* 定价固化"]
        # small tag on the right
        tag_w, tag_h = 1.5, 0.28
        tag = FancyBboxPatch((center_x + 0.8, mid_y - tag_h/2), tag_w, tag_h,
                              boxstyle="round,pad=0.04", facecolor=SLATE,
                              edgecolor='none', alpha=0.13, zorder=5)
        ax.add_patch(tag)
        ax.text(center_x + 1.55, mid_y, data_labels[i], ha='center', va='center',
                fontsize=7.2, color=SLATE, fontweight='bold', zorder=6)

    # ── left pipeline track ──
    track_x = 0.35
    ax.add_patch(FancyBboxPatch((track_x, start_y - 3*gap + card_h/2 - 5.1),
                                 0.18, 10.7, boxstyle="round,pad=0.06",
                                 facecolor=NAVY, edgecolor='none', alpha=0.08, zorder=0))
    ax.text(track_x + 0.09, 3.6, "数\n据\n管\n道", ha='center', va='center',
            fontsize=7.5, color=SLATE, fontweight='bold', rotation=90, zorder=1,
            linespacing=1.8)

    # ── top title ──
    ax.text(center_x, 15.1, "技术路线：四阶段递进求解框架", ha='center', va='center',
            fontsize=19, fontweight='bold', color=NAVY)
    ax.text(center_x, 14.55, "人口预测 → 选址优化 → 差异化定价 → 鲁棒性检验  |  CBC 分支定界 · 全链路精确求解",
            ha='center', va='center', fontsize=10, color=SLATE)
    ax.plot([3.5, 8.5], [14.32, 14.32], color=NAVY, lw=0.7, alpha=0.2, zorder=0)

    # ── bottom note ──
    ax.text(center_x, start_y - 3*gap + card_h/2 - 1.25,
            "Q1 输出人口结构与实际需求  →  Q2 MILP选址固化 y*/x*  →  Q3 词典序定价 p*  →  Q4 三场景扰动重求解",
            ha='center', va='center', fontsize=7.8, color=SLATE, style='italic')

    fig.savefig(os.path.join(FIG, "figure_tech_route.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_tech_route.png — 垂直管道式流程图")

# ============================================================
# §2 Q1 图表重绘 — 学术黑金风格
# ============================================================
def make_figure_q1_total_trend():
    """全区域三类老人5年演化轨迹."""
    df_sum = pd.read_csv(os.path.join(RES, "q1_summary_stats.csv"))
    vals = dict(zip(df_sum["指标"], df_sum["数值"]))

    years = np.arange(6)
    # 从 Q1 输出反推演化轨迹 (线性插值, 基于已知端点)
    base_self  = vals["基年自理"]
    base_semi  = vals["基年半失能"]
    base_dis   = vals["基年失能"]
    final_self = vals["第5年末自理"]
    final_semi = vals["第5年末半失能"]
    final_dis  = vals["第5年末失能"]

    # 使用 Markov 递推的真实非线性轨迹
    # 从 solve_q1.py 逻辑重建
    S0 = np.array([base_self, base_semi, base_dis])
    A = np.array([
        [(1-0.05)*(1-0.045)+0.07, 0.07,                 0.07],
        [(1-0.05)*0.045,          (1-0.05)*(1-0.10),    0.0],
        [0.0,                     (1-0.05)*0.10,         (1-0.05)],
    ])
    S = np.zeros((6, 3))
    S[0] = S0
    for t in range(5):
        S[t+1] = np.round(A @ S[t])

    fig, ax = plt.subplots(figsize=(10, 7.5))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    for e, (color, label) in enumerate(zip(PALETTE_3, LABELS_3)):
        ax.plot(years, S[:, e], marker='o', lw=2.8, color=color, label=label,
                markersize=9, markeredgecolor='white', markeredgewidth=1.5,
                zorder=3)

    # 端点标注
    for e, color in enumerate(PALETTE_3):
        delta = S[-1, e] - S[0, e]
        pct = delta / S[0, e] * 100
        sign = '+' if delta >= 0 else ''
        y_offset = 120 if e == 0 else (-180 if e == 1 else 100)
        ax.annotate(f"{sign}{delta:.0f} ({sign}{pct:.1f}%)",
                    xy=(5, S[-1, e]), xytext=(30, y_offset),
                    textcoords='offset points', fontsize=10, color=color, fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.2, alpha=0.7),
                    zorder=5)

    ax.set_title("全区域三类老人总量 5 年演化轨迹", fontsize=16, fontweight='bold',
                 color=NAVY, pad=18)
    ax.set_xlabel("年份", fontsize=13, color=SLATE)
    ax.set_ylabel("总人数", fontsize=13, color=SLATE)
    ax.set_xticks(years)
    ax.legend(frameon=True, framealpha=0.92, edgecolor=SLATE, fontsize=12,
              loc='upper left')
    ax.grid(axis='y', alpha=0.12, color=SLATE)
    ax.set_xlim(-0.15, 5.15)

    fig.tight_layout(pad=1.5)
    fig.savefig(os.path.join(FIG, "figure_q1_total_trend.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_q1_total_trend.png — 人口演化轨迹")

def make_figure_q1_stacked_bar():
    """基年vs第5年末各小区人口结构堆叠柱状图."""
    df_orig = pd.read_excel(
        os.path.join(BASE, "附件1：小区基础数据.xlsx"),
        sheet_name="人口与老人结构", skiprows=1)
    df_orig.columns = ["小区","总人口","60plus","自理","半失能","失能","人均月收入"]
    communities = df_orig["小区"].tolist()
    S0 = df_orig[["自理","半失能","失能"]].values.astype(float)

    # 重建第5年末
    A = np.array([
        [(1-0.05)*(1-0.045)+0.07, 0.07,                 0.07],
        [(1-0.05)*0.045,          (1-0.05)*(1-0.10),    0.0],
        [0.0,                     (1-0.05)*0.10,         (1-0.05)],
    ])
    S_hist = np.zeros((6, len(communities), 3))
    S_hist[0] = S0.copy()
    for t in range(5):
        for i in range(len(communities)):
            S_hist[t+1, i] = np.round(A @ S_hist[t, i])
    S5 = S_hist[-1]

    fig, axes = plt.subplots(1, 2, figsize=(13, 7.5))
    fig.patch.set_facecolor(WHITE)

    for ax_idx, (t, S_data, title) in enumerate([
        (0, S0, "t = 0 (基年)"), (5, S5, "t = 5 (第5年末)")
    ]):
        ax = axes[ax_idx]
        ax.set_facecolor(WHITE)
        x = np.arange(len(communities))
        bottom = np.zeros(len(communities))
        for e, (color, label) in enumerate(zip(PALETTE_3, LABELS_3)):
            ax.bar(x, S_data[:, e], 0.65, bottom=bottom, color=color,
                   label=label, edgecolor='white', lw=0.6, zorder=3)
            bottom += S_data[:, e]
        ax.set_title(title, fontsize=14, fontweight='bold', color=NAVY, pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels(communities, fontsize=12, color=NAVY)
        ax.set_ylabel("老年人口数", fontsize=12, color=SLATE)
        ax.legend(frameon=True, framealpha=0.9, fontsize=11, loc='upper right')
        ax.grid(axis='y', alpha=0.1, color=SLATE)
        ax.set_ylim(0, 1100)

    fig.suptitle("基年 vs 第5年末 各小区老年人口结构对比",
                 fontsize=16, fontweight='bold', color=NAVY, y=1.01)
    fig.tight_layout(pad=2.0)
    fig.savefig(os.path.join(FIG, "figure_q1_stacked_bar.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_q1_stacked_bar.png — 人口结构堆叠图")

# ============================================================
# §3 Q2 图表重绘
# ============================================================
def make_figure_q2_network():
    """Q2 最优选址-规模网络拓扑图."""
    q2 = load_q2_data()
    communities, dist, reachable = load_distance_matrix()
    n_comm = len(communities)

    # 建站信息
    built_locs = {s['loc']: s['size'] for s in q2['stations']}
    # assignments 格式: {需求小区: {station, S, S1, S2, dist}} → 提取站点映射
    raw_assignments = q2['assignments']
    assignments = {comm: v['station'] if isinstance(v, dict) else v
                   for comm, v in raw_assignments.items()}

    fig, ax = plt.subplots(figsize=(15, 10.5))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    # Kamada-Kawai 布局
    G = nx.Graph()
    for c in communities:
        G.add_node(c)
    for i in range(n_comm):
        for j in range(i+1, n_comm):
            if reachable[i,j]:
                G.add_edge(communities[i], communities[j], weight=max(dist[i,j], 1))
    pos = nx.kamada_kawai_layout(G, weight='weight', scale=3.2)

    # 热力层 — 人口密度
    df_pop = pd.read_csv(os.path.join(RES, "q1_final_population.csv"))
    pop_map = dict(zip(df_pop["小区"], df_pop["60plus_total"]))
    pop_vals = np.array([pop_map.get(c,500) for c in communities])
    pop_min, pop_max = pop_vals.min(), pop_vals.max()
    norm_h = plt.Normalize(pop_min, pop_max)
    cmap_h = plt.cm.YlOrRd

    for i, comm in enumerate(communities):
        x, y = pos[comm]
        pop = pop_vals[i]
        r = 0.38 + 0.52 * (pop-pop_min)/(pop_max-pop_min+1)
        alpha_h = 0.10 + 0.16 * (pop-pop_min)/(pop_max-pop_min+1)
        color_h = cmap_h(norm_h(pop))
        ax.add_patch(plt.Circle((x,y), r, facecolor=color_h, edgecolor='none',
                                alpha=alpha_h, zorder=0))
        ax.add_patch(plt.Circle((x,y), r*1.6, facecolor=color_h, edgecolor='none',
                                alpha=alpha_h*0.35, zorder=0))

    # 可达网络边
    for i in range(n_comm):
        for j in range(i+1, n_comm):
            if reachable[i,j]:
                d_ij = dist[i,j]
                alpha_e = 0.25 + 0.35*(1-d_ij/1500)
                lw_e = 1.5 + 1.3*(1-d_ij/1500)
                ax.plot([pos[communities[i]][0], pos[communities[j]][0]],
                        [pos[communities[i]][1], pos[communities[j]][1]],
                        SLATE, lw=lw_e, alpha=alpha_e, zorder=0, solid_capstyle='round')

    # 服务辐射弧线
    for j_comm, st_comm in assignments.items():
        j = communities.index(j_comm)
        i = communities.index(st_comm)
        if i != j:
            dx = pos[communities[j]][0] - pos[communities[i]][0]
            dy = pos[communities[j]][1] - pos[communities[i]][1]
            rad = 0.08 + abs(dx+dy)*0.04
            ax.annotate("", xy=(pos[communities[j]][0], pos[communities[j]][1]),
                        xytext=(pos[communities[i]][0], pos[communities[i]][1]),
                        arrowprops=dict(arrowstyle="->", color=CORAL, lw=4.5,
                                       alpha=0.85, connectionstyle=f"arc3,rad={rad:.3f}"),
                        zorder=15)

    # 节点
    size_map = {0: CYAN, 1: TEAL, 2: NAVY}
    for i, comm in enumerate(communities):
        x, y = pos[comm]
        if comm in built_locs:
            sz = built_locs[comm]
            color = size_map[sz]
            ax.scatter(x, y, s=2200, c=color, marker='*', edgecolors='white',
                       lw=2.2, zorder=20, alpha=0.95)
            ax.scatter(x, y, s=2200*0.35, c=color, marker='o', edgecolors='none',
                       zorder=19, alpha=0.5)
            label = f"{comm}\n({'小中大型'[sz]}型)"
            ax.annotate(label, (x,y), textcoords="offset points", xytext=(0, 35),
                        fontsize=17, fontweight='bold', ha='center', va='bottom',
                        color=NAVY, zorder=25,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor=WHITE,
                                  edgecolor=color, alpha=0.94, lw=2.0))
        else:
            ax.scatter(x, y, s=650, c=SLATE, marker='o', edgecolors='white',
                       lw=2.0, zorder=10, alpha=0.88)
            ax.annotate(comm, (x,y), textcoords="offset points", xytext=(18, 2),
                        fontsize=15, fontweight='bold', ha='center', va='center',
                        color=NAVY, zorder=25)

    # 图例
    legend_elements = [
        mlines.Line2D([0],[0], marker='o', color='w', markerfacecolor=SLATE,
               markersize=18, markeredgecolor='white', markeredgewidth=1.8,
               label='需求小区'),
        mlines.Line2D([0],[0], marker='*', color='w', markerfacecolor=CYAN,
               markersize=26, markeredgecolor='white', markeredgewidth=2.0,
               label='小型站 (≤1000人次/日)'),
        mlines.Line2D([0],[0], marker='*', color='w', markerfacecolor=TEAL,
               markersize=26, markeredgecolor='white', markeredgewidth=2.0,
               label='中型站 (≤2000人次/日)'),
        mlines.Line2D([0],[0], marker='*', color='w', markerfacecolor=NAVY,
               markersize=26, markeredgecolor='white', markeredgewidth=2.0,
               label='大型站 (≤3000人次/日)'),
        mlines.Line2D([0],[0], color=CORAL, lw=4.5, label='服务辐射 (≤1000m)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=13,
              frameon=True, framealpha=0.94, edgecolor=SLATE,
              title='        图例', title_fontsize=14)

    budget_used = sum([18,32,45][s['size']] for s in q2['stations'])
    ax.set_title(f"嵌入式养老服务站选址-规模优化方案\n"
                 f"预算≤120万 | 半径≤1000m | "
                 f"覆盖{q2['coverage']}/{q2['n_communities']}小区 | "
                 f"建设成本{budget_used}万元",
                 fontsize=18, fontweight='bold', color=NAVY, pad=16)
    ax.axis('off')
    ax.set_xlim(-4.3, 4.3)
    ax.set_ylim(-3.8, 3.8)

    fig.tight_layout(pad=1.0)
    fig.savefig(os.path.join(FIG, "figure_q2_network.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_q2_network.png — 选址网络拓扑")

def make_figure_q2_station_load():
    """各站点服务负荷与利用率对比."""
    q2 = load_q2_data()
    st_names = [s['loc'] for s in q2['stations']]
    st_sizes = ['大型' if s['size']==2 else '中型' for s in q2['stations']]
    capacities = [3000 if s['size']==2 else 2000 for s in q2['stations']]

    # 计算各站负荷 (从 assignments 和需求推算)
    df_demand = pd.read_csv(os.path.join(RES, "q1_service_demand.csv"))
    loads = []
    for st in st_names:
        served = [c for c, s in q2['assignments'].items() if s['station'] == st]
        load = sum(df_demand[df_demand["小区"].isin(served)]["实际月需求(次)"].sum() for _ in [0])
        loads.append(load / 30)  # 转换为日负荷

    util = [l/c*100 for l, c in zip(loads, capacities)]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    x = np.arange(len(st_names))
    width = 0.45
    bars1 = ax.bar(x - width/2, loads, width, color=[NAVY, TEAL, TEAL],
                   edgecolor='white', lw=1.2, label='日服务负荷 (人次)', zorder=3)
    ax2 = ax.twinx()
    bars2 = ax2.bar(x + width/2, util, width, color=[CORAL, AMBER, AMBER],
                    edgecolor='white', lw=1.2, label='利用率 (%)', zorder=3)

    # 容量线
    for i, cap in enumerate(capacities):
        ax.axhline(y=cap, xmin=(i-0.35)/len(st_names), xmax=(i+0.35)/len(st_names),
                   color=ROSE, lw=2.2, linestyle='--', alpha=0.6, zorder=2)

    # 标注
    for bar, load, ut in zip(bars1, loads, util):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+15,
                f'{load:.0f}', ha='center', fontsize=11, fontweight='bold', color=NAVY)
    for bar, ut in zip(bars2, util):
        ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
                 f'{ut:.1f}%', ha='center', fontsize=11, fontweight='bold', color=ROSE)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\n({s})" for n, s in zip(st_names, st_sizes)],
                       fontsize=13, color=NAVY)
    ax.set_ylabel("日服务负荷 (人次)", fontsize=12, color=SLATE)
    ax2.set_ylabel("利用率 (%)", fontsize=12, color=SLATE)
    ax.set_title("各站点服务负荷与利用率", fontsize=15, fontweight='bold', color=NAVY, pad=14)
    ax.grid(axis='y', alpha=0.1, color=SLATE)

    # 合并图例
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1+lines2, labels1+labels2, frameon=True, framealpha=0.9,
              fontsize=11, loc='upper left')

    ax.set_ylim(0, max(capacities)*1.18)
    ax2.set_ylim(0, 105)
    ax.set_xlim(-0.5, len(st_names)-0.5)
    fig.tight_layout(pad=1.5)
    fig.savefig(os.path.join(FIG, "figure_q2_station_load.png"), dpi=300,
                facecolor='white')
    plt.close(fig)
    print("[OK] figure_q2_station_load.png — 站点负荷图")

# ============================================================
# §4 Q3 图表重绘
# ============================================================
def make_figure_q3_pricing_comparison():
    """基准价vs最优定价对比 (分组柱状图, S3标注)."""
    df_p, _ = load_q3_data()

    services = df_p["服务项目"].tolist()
    base_prices = df_p["基准价(元)"].values
    opt_prices = df_p["最优定价(元)"].values
    s3_vals = df_p["S3(价格满意度)"].values

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    x = np.arange(len(services))
    width = 0.32
    bars_base = ax.bar(x - width/2, base_prices, width, color=SLATE, alpha=0.65,
                       edgecolor='white', lw=1.0, label='基准价 (元)', zorder=3)
    bars_opt = ax.bar(x + width/2, opt_prices, width, color=NAVY,
                      edgecolor='white', lw=1.0, label='最优定价 (元)', zorder=3)

    # 降价标注
    for i, (b, o) in enumerate(zip(base_prices, opt_prices)):
        if o < b - 0.5:
            ax.annotate(f"-{(b-o)/b*100:.1f}%", xy=(x[i]+width/2, o),
                        xytext=(0, -22), textcoords='offset points',
                        fontsize=9, color=ROSE, fontweight='bold', ha='center')

    # S3 标签
    for i, (opt, s3) in enumerate(zip(opt_prices, s3_vals)):
        ax.text(x[i]+width/2, opt+0.8, f"S3={s3:.3f}", ha='center',
                fontsize=8, color=TEAL, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(services, fontsize=11, color=NAVY)
    ax.set_ylabel("价格 (元/次)", fontsize=12, color=SLATE)
    ax.set_title("基准价与最优定价对比", fontsize=15, fontweight='bold', color=NAVY, pad=14)
    ax.legend(frameon=True, framealpha=0.9, fontsize=11)
    ax.grid(axis='y', alpha=0.1, color=SLATE)

    fig.tight_layout(pad=1.5)
    fig.savefig(os.path.join(FIG, "figure_q3_pricing_comparison.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_q3_pricing_comparison.png — 定价对比图")

# ============================================================
# §5 Q4 图表重绘
# ============================================================
def make_figure_q4_sensitivity_combined():
    """三面板横排灵敏度全景图."""
    scenarios = ['基线\n(120万)', 'A-人口\n结构冲击', 'B-管理\n成本+20%', 'C-预算\n调整140万']
    colors = [NAVY, CYAN, CORAL, TEAL]
    coverage = [100.0, 90.0, 100.0, 100.0]
    sat = [0.850, 0.878, 0.842, 0.889]
    profit = [1097.7, 931.7, 1019.9, 1010.0]

    fig, axes = plt.subplots(1, 3, figsize=(21, 6.2))
    fig.patch.set_facecolor(WHITE)

    panels = [
        (axes[0], coverage, '{:.0f}%', '覆盖率 (%)', '(a) 覆盖率', 55, 118, 100),
        (axes[1], sat, '{:.3f}', '平均综合满意度 S', '(b) 加权满意度', 0.60, 1.03, None),
        (axes[2], profit, '{:.0f}', '年总利润 (万元)', '(c) 年利润', 450, 1280, None),
    ]

    for ax, vals, fmt, ylabel, title, ylo, yhi, hline in panels:
        ax.set_facecolor(WHITE)
        bars = ax.bar(scenarios, vals, color=colors, edgecolor='white', lw=1.2, width=0.55)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+(yhi-ylo)*0.025,
                    fmt.format(val), ha='center', fontsize=12, fontweight='bold', color=NAVY)
        if hline:
            ax.axhline(y=hline, color=SLATE, lw=1.0, ls='--', alpha=0.5)
        ax.set_title(title, fontsize=14, fontweight='bold', color=NAVY, pad=12)
        ax.set_ylabel(ylabel, fontsize=11, color=SLATE)
        ax.set_ylim(ylo, yhi)
        ax.tick_params(axis='x', labelsize=10, colors=NAVY)
        despine_fully(ax)
        ax.grid(axis='y', alpha=0.15, color=SLATE, lw=0.4)

    fig.suptitle('三场景灵敏度分析全景对比', fontsize=16, fontweight='bold',
                 color=NAVY, y=1.01)
    fig.tight_layout(pad=2.5)
    fig.savefig(os.path.join(FIG, "figure_q4_sensitivity_combined.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_q4_sensitivity_combined.png — 灵敏度全景图")

def make_figure_q4_resilience_heatmap():
    """多场景多维度韧性热力图."""
    scenarios = ['A(人口冲击)', 'B(成本+20%)', 'C(预算140万)']
    dims = ['覆盖率', '满意度', '利润率', '目标值']
    # ρ = 1 - |ΔX/X_baseline|
    data = np.array([
        [0.90, 0.967, 0.849, 0.903],   # A: 人口结构冲击
        [1.00, 0.991, 0.929, 0.999],   # B: 管理成本+20%
        [1.00, 0.953, 0.920, 0.996],   # C: 预算调整140万
    ])

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    # 红(弱韧性) → 黄 → 绿(强韧性)，vmin/vmax 压缩至高值区凸显差异
    cmap = sns.diverging_palette(10, 130, s=85, l=50, center='light', as_cmap=True)
    im = ax.imshow(data, cmap=cmap, vmin=0.82, vmax=1.02, aspect='auto')

    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels(dims, fontsize=12, color=NAVY)
    ax.set_yticks(range(len(scenarios)))
    ax.set_yticklabels(scenarios, fontsize=11, color=NAVY)

    # 单元格标注
    for i in range(len(scenarios)):
        for j in range(len(dims)):
            color = 'white' if data[i,j] < 0.72 else NAVY
            ax.text(j, i, f'{data[i,j]:.3f}', ha='center', va='center',
                    fontsize=13, fontweight='bold', color=color)

    ax.set_title("多场景多维度韧性热力图 ($\\rho = 1 - |\\Delta X / X_{baseline}|$)",
                 fontsize=14, fontweight='bold', color=NAVY, pad=14)
    cbar = fig.colorbar(im, ax=ax, shrink=0.82, pad=0.02)
    cbar.set_label('韧性系数 $\\rho$', fontsize=11, color=SLATE)

    fig.tight_layout(pad=1.5)
    fig.savefig(os.path.join(FIG, "figure_q4_resilience_heatmap.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_q4_resilience_heatmap.png — 韧性热力图")

def make_figure_q4_resilience_radar():
    """多维度鲁棒性雷达图 (v5: 题目4.1三场景)."""
    scenarios = {
        'A(人口结构冲击)': [0.90, 0.967, 0.849, 0.903],
        'B(管理成本+20%)': [1.00, 0.991, 0.929, 0.999],
        'C(预算调整140万)': [1.00, 0.953, 0.920, 0.996],
    }
    dims = ['覆盖率\n韧性', '满意度\n韧性', '利润率\n韧性', '目标值\n韧性']
    colors_radar = [CYAN, CORAL, TEAL]
    N = len(dims)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7.5, 7.5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    for idx, (label, values) in enumerate(scenarios.items()):
        vals = values + values[:1]
        ax.fill(angles, vals, alpha=0.08, color=colors_radar[idx], zorder=2)
        ax.plot(angles, vals, 'o-', lw=2.2, color=colors_radar[idx],
                label=label, markersize=7, zorder=3)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims, fontsize=11, color=NAVY)
    ax.set_ylim(0.5, 1.05)
    ax.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(['0.6','0.7','0.8','0.9','1.0'], fontsize=8, color=SLATE)
    ax.axhline(y=0.80, color=SLATE, lw=1.0, ls='--', alpha=0.4)
    ax.text(np.pi/4, 0.81, '强鲁棒性阈值 0.80', fontsize=8, color=SLATE, alpha=0.7)

    ax.set_title("多维度鲁棒性雷达图", fontsize=14, fontweight='bold', color=NAVY, pad=22)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), frameon=True,
              framealpha=0.9, fontsize=10)

    fig.tight_layout(pad=2.0)
    fig.savefig(os.path.join(FIG, "figure_q4_resilience_radar.png"), dpi=300,
                facecolor='white', bbox_inches='tight')
    plt.close(fig)
    print("[OK] figure_q4_resilience_radar.png — 韧性雷达图")

# ============================================================
# §6 主流程
# ============================================================
if __name__ == "__main__":
    print("=" * 65)
    print("Academic Noir 统一图表再生 — 电工杯 B题 2026")
    print("配色: NAVY/CYAN/ROSE/AMBER/TEAL | 风格: Visio学术级")
    print("=" * 65)

    # Q0: 技术路线图 (NEW)
    make_figure_tech_route()

    # Q1: 人口预测图表
    make_figure_q1_total_trend()
    make_figure_q1_stacked_bar()

    # Q2: 选址优化图表
    make_figure_q2_network()
    make_figure_q2_station_load()

    # Q3: 定价图表
    make_figure_q3_pricing_comparison()

    # Q4: 灵敏度图表
    make_figure_q4_sensitivity_combined()
    make_figure_q4_resilience_heatmap()
    make_figure_q4_resilience_radar()

    print("\n" + "=" * 65)
    print("[DONE] 9 figures regenerated to figures/")
    for f in [
        "figure_tech_route.png",
        "figure_q1_total_trend.png",
        "figure_q1_stacked_bar.png",
        "figure_q2_network.png",
        "figure_q2_station_load.png",
        "figure_q3_pricing_comparison.png",
        "figure_q4_sensitivity_combined.png",
        "figure_q4_resilience_heatmap.png",
        "figure_q4_resilience_radar.png",
    ]:
        print(f"  [OK] {f}")
    print("=" * 65)
