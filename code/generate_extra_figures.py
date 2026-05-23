"""
generate_extra_figures.py — 补充高级可视化图表 (电工杯 B题 2026)
=============================================================
Stage 08 | 生成Q3定价对比图、交叉补贴图、Q4雷达图、Q2站点负荷图

输出:
  figures/figure_q3_pricing_comparison.png  — Q3基准价vs最优定价对比
  figures/figure_q3_profit_breakdown.png    — Q3各站点营收/成本/利润分解
  figures/figure_q3_cross_subsidy.png       — Q3三层交叉补贴机制图
  figures/figure_q4_resilience_radar.png    — Q4多维度鲁棒性雷达图
  figures/figure_q2_station_load.png        — Q2各站点服务负荷与利用率
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns
from pathlib import Path
import os, warnings
warnings.filterwarnings('ignore')

# ---- 字体注册 ----
fm.fontManager.addfont('C:/Windows/Fonts/simhei.ttf')
fm._load_fontmanager(try_read_cache=False)

sns.set_style("whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["SimHei", "Microsoft YaHei", "DejaVu Sans"],
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

Path("../figures").mkdir(exist_ok=True)

# ============================================================
# 学术配色
# ============================================================
C_SELFCARE  = '#2E86AB'  # 自理 - 蓝
C_SEMI      = '#D64045'  # 半失能 - 红
C_DISABLED  = '#F18F01'  # 失能 - 橙
C_BENCHMARK = '#95A5A6'  # 基准价 - 灰
C_OPTIMAL   = '#27AE60'  # 最优价 - 绿
C_REVENUE   = '#2980B9'  # 营收 - 蓝
C_COST      = '#E74C3C'  # 成本 - 红
C_PROFIT    = '#27AE60'  # 利润 - 绿
C_SUBSIDY   = '#F39C12'  # 补贴 - 橙

PALETTE_3 = [C_SELFCARE, C_SEMI, C_DISABLED]
PALETTE_STATION = ['#2980B9', '#27AE60', '#E74C3C']  # F/H/J

# ============================================================
# 图1: Q3 基准价 vs 最优定价对比 + S3满意度
# ============================================================
def fig_q3_pricing():
    services = ['助餐', '日间照料', '上门护理', '康复理疗', '助浴', '紧急救助']
    base_prices = [10, 20, 30, 28, 25, 0]
    opt_prices = [10.00, 20.00, 12.64, 28.00, 25.00, 0.00]
    s3_values = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    monthly_demand = [118443, 49073, 19608, 51086, 24403, 4940]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7),
                                    gridspec_kw={'width_ratios': [1.2, 1]})

    x = np.arange(len(services))
    width = 0.35

    # 左图: 基准价 vs 最优价
    bars1 = ax1.bar(x - width/2, base_prices, width, color=C_BENCHMARK,
                    edgecolor='white', lw=1.2, label='基准价', zorder=3)
    bars2 = ax1.bar(x + width/2, opt_prices, width, color=C_OPTIMAL,
                    edgecolor='white', lw=1.2, label='最优定价', zorder=3)

    # 标注上门护理降价
    for i in range(len(services)):
        if opt_prices[i] < base_prices[i]:
            ax1.annotate(f'-{base_prices[i]-opt_prices[i]:.1f}元\n(-{100*(base_prices[i]-opt_prices[i])/base_prices[i]:.0f}%)',
                        xy=(i + width/2, opt_prices[i]),
                        xytext=(i + width/2 + 0.25, opt_prices[i] + 8),
                        fontsize=9, fontweight='bold', color='#C0392B',
                        ha='center',
                        arrowprops=dict(arrowstyle='->', color='#C0392B', lw=1.5))

    ax1.set_xticks(x)
    ax1.set_xticklabels(services, fontsize=11)
    ax1.set_ylabel('单价 (元/次)', fontsize=13)
    ax1.set_title('基准价 vs 最优定价对比', fontsize=15, fontweight='bold', pad=14)
    ax1.legend(fontsize=12, loc='upper right')
    ax1.grid(axis='y', alpha=0.25)
    ax1.set_ylim(0, 38)

    # 右图: S3满意度 + 月需求气泡
    colors_s3 = ['#27AE60' if s >= 1.0 else '#F39C12' if s >= 0.9 else '#E74C3C'
                 for s in s3_values]
    ax2.bar(x, s3_values, 0.55, color=colors_s3, edgecolor='white', lw=1.5, zorder=3)
    ax2.set_xticks(x)
    ax2.set_xticklabels(services, fontsize=11)
    ax2.set_ylabel('S3 价格满意度', fontsize=13)
    ax2.set_ylim(0.5, 1.1)
    ax2.set_title('S3价格满意度 (全部平价区间)', fontsize=15, fontweight='bold', pad=14)
    ax2.axhline(y=1.0, color='#27AE60', linestyle='--', lw=1.2, alpha=0.4)
    ax2.grid(axis='y', alpha=0.25)

    for i, (s, d) in enumerate(zip(s3_values, monthly_demand)):
        ax2.annotate(f'{d/10000:.1f}万次/月',
                    xy=(i, s), xytext=(0, -28),
                    textcoords='offset points',
                    fontsize=7.5, ha='center', color='#555')

    fig.suptitle('Q3 服务定价优化结果', fontsize=17, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig('../figures/figure_q3_pricing_comparison.png', dpi=300, facecolor='white')
    plt.close()
    print('[图表] figure_q3_pricing_comparison.png 已保存')


# ============================================================
# 图2: Q3 各站点营收-成本-补贴-利润分解
# ============================================================
def fig_q3_profit_breakdown():
    stations = ['F (大型)', 'H (中型)', 'J (中型)']
    revenue = [1967.1, 1265.6, 1226.3]
    subsidy = [93.6, 64.8, 64.8]
    cost = [1908.1, 1239.6, 1203.2]
    profit = [152.6, 90.8, 87.9]
    margin = [8.0, 7.3, 7.3]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    x = np.arange(len(stations))
    width = 0.55

    # 左图: 堆叠柱状图 (营收 + 补贴 = 总收入, 成本在下)
    bottom_rev = np.zeros(len(stations))
    bars_rev = ax1.bar(x, revenue, width, color=C_REVENUE, edgecolor='white',
                       lw=1.5, label='年营收', zorder=3)
    bars_sub = ax1.bar(x, subsidy, width, bottom=revenue, color=C_SUBSIDY,
                       edgecolor='white', lw=1.5, label='年补贴', zorder=3)
    total_income = np.array(revenue) + np.array(subsidy)
    bars_cost = ax1.bar(x, cost, width, color='#ECF0F1', edgecolor=C_COST,
                        lw=2.0, linestyle='--', label='年总成本', zorder=2, hatch='///')

    # 标注总收入和总成本
    for i in range(len(stations)):
        ax1.text(i, total_income[i] + 60, f'{total_income[i]:.0f}万',
                ha='center', fontsize=11, fontweight='bold', color='#2C3E50')
        ax1.text(i, cost[i] - 80, f'{cost[i]:.0f}万',
                ha='center', fontsize=11, fontweight='bold', color=C_COST)

    ax1.set_xticks(x)
    ax1.set_xticklabels(stations, fontsize=13)
    ax1.set_ylabel('万元/年', fontsize=13)
    ax1.set_title('站点收入与成本结构', fontsize=15, fontweight='bold', pad=14)
    ax1.legend(fontsize=11, loc='upper left')
    ax1.grid(axis='y', alpha=0.2)

    # 右图: 利润 + 利润率
    colors_bar = ['#C0392B' if m >= 8.0 else '#E67E22' if m >= 7.3 else '#2980B9'
                  for m in margin]
    bars = ax2.bar(x, profit, width, color=colors_bar, edgecolor='white', lw=1.5, zorder=3)

    for i, (p, m) in enumerate(zip(profit, margin)):
        ax2.text(i, p + 5, f'{p:.1f}万\n({m:.1f}%)',
                ha='center', fontsize=12, fontweight='bold', color='#2C3E50')

    ax2.axhline(y=0, color='#555', lw=1.2)
    ax2.axhline(y=152.6, color='#C0392B', linestyle='--', lw=1.0, alpha=0.35)
    ax2.set_xticks(x)
    ax2.set_xticklabels(stations, fontsize=13)
    ax2.set_ylabel('年利润 (万元)', fontsize=13)
    ax2.set_title('站点利润与利润率 ($\\leq$8%红线)', fontsize=15, fontweight='bold', pad=14)
    ax2.grid(axis='y', alpha=0.2)

    fig.suptitle('Q3 各站点运营财务指标', fontsize=17, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig('../figures/figure_q3_profit_breakdown.png', dpi=300, facecolor='white')
    plt.close()
    print('[图表] figure_q3_profit_breakdown.png 已保存')


# ============================================================
# 图3: Q3 三层交叉补贴机制图 (学术架构框图风格)
# ============================================================
def fig_q3_cross_subsidy():
    from matplotlib.patches import Rectangle, FancyArrow

    fig, ax = plt.subplots(figsize=(18, 11))
    ax.set_xlim(0, 18)
    ax.set_ylim(0, 11)
    ax.axis('off')
    ax.set_facecolor('white')

    # 学术配色 — 低饱和、印刷友好
    C1 = '#3A6B8C'   # 第一层 深蓝灰
    C1B = '#D6E4EE'  # 第一层背景
    C2 = '#4A8C5C'   # 第二层 深绿灰
    C2B = '#D8EADB'  # 第二层背景
    C3 = '#8B4A5A'   # 第三层 深红褐
    C3B = '#ECD5DA'  # 第三层背景
    C_ARROW = '#5A5A5A'
    C_BORDER = '#444444'

    BOX_L = 1.0        # 左边距
    BOX_W = 16.0       # 框宽
    BOX_H = 2.1        # 框高
    LABEL_X = 0.6      # 层级标签 x

    # ---- 标题 ----
    ax.text(9, 10.65, '嵌入式养老服务站三层交叉补贴机制',
            fontsize=17, fontweight='bold', ha='center', va='center',
            color='#1A1A2E', fontfamily='sans-serif')

    # ============ 第一层 ============
    y1 = 7.8
    rect1 = Rectangle((BOX_L, y1), BOX_W, BOX_H, facecolor=C1B, edgecolor=C1,
                       lw=2.2, zorder=2)
    ax.add_patch(rect1)
    # 层级标签 (左侧竖排)
    ax.text(LABEL_X, y1 + BOX_H/2, '第一层', fontsize=13, fontweight='bold',
            ha='center', va='center', color=C1, rotation=90)
    # 标题行
    ax.text(BOX_L + 1.8, y1 + BOX_H - 0.55, '站内营利养公益 (Cross-subsidy Layer I)',
            fontsize=13.5, fontweight='bold', ha='left', va='center', color=C1)
    ax.plot([BOX_L + 1.8, BOX_L + 11.5], [y1 + BOX_H - 0.9, y1 + BOX_H - 0.9],
            color=C1, lw=0.8, alpha=0.5)
    # 内容
    ax.text(BOX_L + 1.8, y1 + BOX_H - 1.45,
            '紧急救助年净支出 47.42 万元', fontsize=11.5, ha='left', va='center',
            color='#222', fontfamily='sans-serif')
    ax.text(BOX_L + 8.8, y1 + BOX_H - 1.45,
            r'$\longleftarrow$', fontsize=14, ha='center', va='center', color=C_ARROW)
    ax.text(BOX_L + 10.5, y1 + BOX_H - 1.45,
            '由营利服务年利润 331.3 万元全额吸收', fontsize=11.5, ha='left', va='center',
            color='#222', fontfamily='sans-serif')
    # 站点明细
    detail1 = ('F站: 2,202次/月紧急救助 (净支出21.14万/年)    |    '
               'H站: 1,399次/月 (13.43万/年)    |    '
               'J站: 1,339次/月 (12.85万/年)')
    ax.text(BOX_L + 1.8, y1 + 0.55, detail1, fontsize=9.5, ha='left', va='center',
            color='#555', fontfamily='monospace')

    # 下行箭头 1→2
    arrow_y1 = y1 - 0.05
    ax.annotate('', xy=(9, arrow_y1 - 0.9), xytext=(9, arrow_y1),
                arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=2.8))
    ax.text(11.2, arrow_y1 - 0.45, '交叉补贴率 14.3%', fontsize=11,
            fontweight='bold', ha='left', va='center', color='#6B3A3A')

    # ============ 第二层 ============
    y2 = 4.7
    rect2 = Rectangle((BOX_L, y2), BOX_W, BOX_H, facecolor=C2B, edgecolor=C2,
                       lw=2.2, zorder=2)
    ax.add_patch(rect2)
    ax.text(LABEL_X, y2 + BOX_H/2, '第二层', fontsize=13, fontweight='bold',
            ha='center', va='center', color=C2, rotation=90)
    ax.text(BOX_L + 1.8, y2 + BOX_H - 0.55, '站间补贴效率错配 (Cross-subsidy Layer II)',
            fontsize=13.5, fontweight='bold', ha='left', va='center', color=C2)
    ax.plot([BOX_L + 1.8, BOX_L + 11.5], [y2 + BOX_H - 0.9, y2 + BOX_H - 0.9],
            color=C2, lw=0.8, alpha=0.5)

    # 补贴数据表格式
    table_y = y2 + BOX_H - 1.45
    ax.text(BOX_L + 1.8, table_y, '站点', fontsize=10.5, fontweight='bold',
            ha='center', va='center', color='#222')
    ax.text(BOX_L + 4.5, table_y, '理论补贴 (元/日)', fontsize=10.5, fontweight='bold',
            ha='center', va='center', color='#222')
    ax.text(BOX_L + 7.8, table_y, '补贴上限 (元/日)', fontsize=10.5, fontweight='bold',
            ha='center', va='center', color='#222')
    ax.text(BOX_L + 10.8, table_y, '截断损失 (%)', fontsize=10.5, fontweight='bold',
            ha='center', va='center', color='#222')
    ax.text(BOX_L + 13.5, table_y, '有效补贴率 (元/次)', fontsize=10.5, fontweight='bold',
            ha='center', va='center', color='#222')

    row_data = [
        ('F (大型)', '7,118', '2,600', '63.5', '0.73'),
        ('H (中型)', '4,582', '1,800', '60.7', '0.79'),
        ('J (中型)', '4,442', '1,800', '59.5', '0.81'),
    ]
    for ri, (st, th, cap, loss, er) in enumerate(row_data):
        ry = table_y - 0.42 * (ri + 1)
        cols = [st, th, cap, loss, er]
        xs = [BOX_L + 1.8, BOX_L + 4.5, BOX_L + 7.8, BOX_L + 10.8, BOX_L + 13.5]
        for cx, val in zip(xs, cols):
            ax.text(cx, ry, val, fontsize=10, ha='center', va='center',
                    color='#333', fontfamily='monospace')

    # 关键发现
    ax.text(BOX_L + 1.8, y2 + 0.45,
            '核心发现: 大型站因需求密集触发补贴帽更早，有效补贴率最低 (0.73 < 0.79 < 0.81)，形成逆向再分配',
            fontsize=10, ha='left', va='center', color='#6B3A3A', fontstyle='italic')

    # 下行箭头 2→3
    arrow_y2 = y2 - 0.05
    ax.annotate('', xy=(9, arrow_y2 - 0.9), xytext=(9, arrow_y2),
                arrowprops=dict(arrowstyle='->', color=C_ARROW, lw=2.8))
    ax.text(11.2, arrow_y2 - 0.45, '补贴帽效率损失\n触发定价调整', fontsize=10,
            fontweight='bold', ha='left', va='center', color='#6B3A3A')

    # ============ 第三层 ============
    y3 = 1.6
    rect3 = Rectangle((BOX_L, y3), BOX_W, BOX_H, facecolor=C3B, edgecolor=C3,
                       lw=2.2, zorder=2)
    ax.add_patch(rect3)
    ax.text(LABEL_X, y3 + BOX_H/2, '第三层', fontsize=13, fontweight='bold',
            ha='center', va='center', color=C3, rotation=90)
    ax.text(BOX_L + 1.8, y3 + BOX_H - 0.55,
            'Ramsey-Boiteux 反向价格歧视 (Cross-subsidy Layer III)',
            fontsize=13.5, fontweight='bold', ha='left', va='center', color=C3)
    ax.plot([BOX_L + 1.8, BOX_L + 11.5], [y3 + BOX_H - 0.9, y3 + BOX_H - 0.9],
            color=C3, lw=0.8, alpha=0.5)

    ax.text(BOX_L + 1.8, y3 + BOX_H - 1.45,
            '调节变量: 上门护理  30 → 12.64 元 (降幅 57.9%)', fontsize=11.5,
            ha='left', va='center', color='#222', fontfamily='sans-serif')
    ax.text(BOX_L + 1.8, y3 + BOX_H - 1.85,
            '受保护服务: 助餐 (10元×11.8万次/月) | 日间照料 | 康复理疗 | 助浴 — 均维持基准价',
            fontsize=10, ha='left', va='center', color='#555', fontfamily='sans-serif')
    ax.text(BOX_L + 1.8, y3 + 0.55,
            '结果: 全部6项服务 S3 = 1.000 (平价区间)，F站利润率恰好绑定 8% 监管红线',
            fontsize=10, ha='left', va='center', color='#6B3A3A', fontstyle='italic')

    # ---- 左侧因果链标注 ----
    ax.annotate('微利约束', xy=(0.1, 9.7), fontsize=8.5, color='#666', rotation=90)
    ax.annotate('补贴效率', xy=(0.1, 6.6), fontsize=8.5, color='#666', rotation=90)
    ax.annotate('定价弹性', xy=(0.1, 3.5), fontsize=8.5, color='#666', rotation=90)
    # 大括号示意因果不可逆
    ax.plot([0.35, 0.35], [9.85, 1.5], color='#999', lw=1.2)
    ax.text(0.18, 5.7, '因果\n不可\n逆', fontsize=7.5, ha='center', va='center',
            color='#999', rotation=90)

    plt.tight_layout(pad=0.5)
    fig.savefig('../figures/figure_q3_cross_subsidy.png', dpi=300, facecolor='white')
    plt.close()
    print('[图表] figure_q3_cross_subsidy.png 已保存')


# ============================================================
# 图4: Q4 多维度鲁棒性雷达图
# ============================================================
def fig_q4_resilience_radar():
    scenarios = ['基线\n(Q2确定解)', 'A1\n预算130万', 'A2\n预算140万',
                 'A3\n预算150万', 'B\n成本+20%', 'C\n银发海啸']
    rho_c = [1.00, 1.00, 1.00, 1.00, 0.80, 0.90]    # 覆盖率韧性
    rho_s = [1.00, 0.961, 0.954, 0.927, 0.934, 0.947]  # 满意度韧性
    rho_pi = [1.00, 0.960, 0.920, 0.893, 0.609, 0.809] # 利润率韧性
    rho_avg = [1.00, 0.974, 0.958, 0.940, 0.781, 0.885] # 综合韧性

    fig, ax = plt.subplots(figsize=(12, 10), subplot_kw=dict(polar=True))

    N = 3  # 维度数
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    dims = ['覆盖率韧性 $\\rho_c$', '满意度韧性 $\\rho_s$', '利润率韧性 $\\rho_\\pi$']

    colors = ['#2980B9', '#27AE60', '#E67E22', '#8E44AD', '#C0392B', '#16A085']
    lw_map = [3.5, 1.8, 1.8, 1.8, 2.2, 2.2]
    ls_map = ['-', '--', '--', '--', '-.', '-.']

    for idx, (sc, rho, c, lw, ls) in enumerate(
        zip(scenarios,
            [[rho_c[i], rho_s[i], rho_pi[i]] for i in range(6)],
            colors, lw_map, ls_map)):
        values = rho + rho[:1]
        ax.fill(angles, values, alpha=0.06, color=c)
        ax.plot(angles, values, 'o-', lw=lw, color=c, linestyle=ls,
                markersize=7, label=sc.replace('\n', ' '), zorder=5-idx*0.5)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims, fontsize=12, fontweight='bold')

    ax.set_ylim(0.5, 1.05)
    ax.set_yticks([0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_yticklabels(['0.6', '0.7', '0.8', '0.9', '1.0'], fontsize=9)
    ax.set_rlabel_position(30)

    # 强鲁棒性阈值线
    ax.plot(angles, [0.75]*len(angles), '--', color='#BDC3C7', lw=1.5, alpha=0.7)
    ax.text(angles[1], 0.76, '强鲁棒性阈值 (0.75)',
            fontsize=9, ha='center', color='#999')

    ax.legend(loc='upper right', bbox_to_anchor=(1.32, 1.08),
             fontsize=10, title='场景', title_fontsize=11,
             frameon=True, framealpha=0.9, edgecolor='#CCC')

    ax.set_title('Q4 多维度鲁棒性雷达图\n($\\rho = 1 - |\\Delta X / X_{baseline}|$)',
                 fontsize=16, fontweight='bold', pad=24, color='#2C3E50')

    plt.tight_layout()
    fig.savefig('../figures/figure_q4_resilience_radar.png', dpi=300, facecolor='white')
    plt.close()
    print('[图表] figure_q4_resilience_radar.png 已保存')


# ============================================================
# 图5: Q2 各站点服务负荷与利用率对比
# ============================================================
def fig_q2_station_load():
    stations = ['F (大型)', 'H (中型)', 'J (中型)']
    daily_cap = [3000, 2000, 2000]
    daily_load = [2877, 1877, 1825]
    util_rate = [95.9, 93.9, 91.3]

    served_communities = ['C, F, G, I', 'B, E, H', 'A, D, J']
    n_served = [4, 3, 3]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    x = np.arange(len(stations))
    width = 0.5

    # 左图: 容量 vs 实际负荷
    bars_cap = ax1.bar(x, daily_cap, width, color='#ECF0F1', edgecolor='#7F8C8D',
                       lw=2.0, linestyle='--', label='日容量上限', zorder=2)
    bars_load = ax1.bar(x, daily_load, width*0.7, color=PALETTE_STATION,
                        edgecolor='white', lw=1.5, label='实际日负荷', zorder=3)

    for i in range(len(stations)):
        ax1.text(i, daily_load[i] + 60, f'{daily_load[i]:.0f}\n({util_rate[i]:.1f}%)',
                ha='center', fontsize=12, fontweight='bold', color='#2C3E50')
        ax1.text(i, daily_cap[i] + 90, f'上限{daily_cap[i]:.0f}',
                ha='center', fontsize=10, color='#7F8C8D')

    ax1.set_xticks(x)
    ax1.set_xticklabels(stations, fontsize=13)
    ax1.set_ylabel('人次/日', fontsize=13)
    ax1.set_title('站点容量 vs 实际负荷', fontsize=15, fontweight='bold', pad=14)
    ax1.legend(fontsize=11)
    ax1.grid(axis='y', alpha=0.2)

    # 右图: 服务小区数与利用率气泡图
    bubble_sizes = [n * 900 for n in n_served]
    scatter = ax2.scatter(x, util_rate, s=bubble_sizes, c=PALETTE_STATION,
                         alpha=0.75, edgecolors='white', lw=2.5, zorder=5)

    for i in range(len(stations)):
        ax2.annotate(f'{stations[i]}\n{n_served[i]}个小区\n利用率{util_rate[i]:.1f}%',
                    xy=(i, util_rate[i]), xytext=(0, -50),
                    textcoords='offset points',
                    fontsize=11, fontweight='bold', ha='center', color='#2C3E50')

    ax2.set_xticks(x)
    ax2.set_xticklabels(stations, fontsize=13)
    ax2.set_ylabel('利用率 (%)', fontsize=13)
    ax2.set_ylim(85, 100)
    ax2.set_title('站点服务小区数与利用率\n(气泡大小 = 服务小区数)',
                  fontsize=15, fontweight='bold', pad=14)
    ax2.grid(axis='y', alpha=0.2)

    fig.suptitle('Q2 各站点服务负荷与运营效率', fontsize=17, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig('../figures/figure_q2_station_load.png', dpi=300, facecolor='white')
    plt.close()
    print('[图表] figure_q2_station_load.png 已保存')


# ============================================================
# 图6: Q4 综合韧性指标热力图
# ============================================================
def fig_q4_resilience_heatmap():
    scenarios_short = ['基线', 'A1\n预算130', 'A2\n预算140', 'A3\n预算150', 'B\n成本+20%', 'C\n银发海啸']
    dims = ['覆盖率\n韧性', '满意度\n韧性', '利润率\n韧性', '综合\n韧性']

    data = np.array([
        [1.000, 1.000, 1.000, 1.000],
        [1.000, 0.961, 0.960, 0.974],
        [1.000, 0.954, 0.920, 0.958],
        [1.000, 0.927, 0.893, 0.940],
        [0.800, 0.934, 0.609, 0.781],
        [0.900, 0.947, 0.809, 0.885],
    ])

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(data, annot=True, fmt='.3f', cmap='RdBu_r', vmin=0.6, vmax=1.0,
                xticklabels=dims, yticklabels=scenarios_short,
                linewidths=1.5, linecolor='white', cbar_kws={'label': '韧性系数 $\\rho$'},
                annot_kws={'fontsize': 12, 'fontweight': 'bold'},
                ax=ax, center=0.85)

    ax.set_title('Q4 多场景多维度鲁棒性韧性热力图\n($\\rho = 1 - |\\Delta X / X_{baseline}|$, 蓝色越深越强，红色越深越弱)',
                 fontsize=15, fontweight='bold', pad=16, color='#2C3E50')
    ax.set_xlabel('韧性维度', fontsize=13)
    ax.set_ylabel('场景', fontsize=13)

    plt.tight_layout()
    fig.savefig('../figures/figure_q4_resilience_heatmap.png', dpi=300, facecolor='white')
    plt.close()
    print('[图表] figure_q4_resilience_heatmap.png 已保存')


# ============================================================
# 主流程
# ============================================================
if __name__ == '__main__':
    print('=' * 60)
    print('生成补充高级可视化图表')
    print('=' * 60)

    fig_q3_pricing()
    fig_q3_profit_breakdown()
    fig_q3_cross_subsidy()
    fig_q4_resilience_radar()
    fig_q2_station_load()
    fig_q4_resilience_heatmap()

    print('\n全部图表生成完成:')
    print('  figures/figure_q3_pricing_comparison.png')
    print('  figures/figure_q3_profit_breakdown.png')
    print('  figures/figure_q3_cross_subsidy.png')
    print('  figures/figure_q4_resilience_radar.png')
    print('  figures/figure_q2_station_load.png')
    print('  figures/figure_q4_resilience_heatmap.png')
