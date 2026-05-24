"""
generate_q4_combined.py — Q4灵敏度分析三面板横排组合图 (a)(b)(c)
v5: 题目4.1三场景校正 — 人口结构冲击/管理成本+20%/预算140万
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

# ---- 中文注册 + Academic Noir 配色 ----
fm.fontManager.addfont('C:/Windows/Fonts/simhei.ttf')
fm._load_fontmanager(try_read_cache=False)

FONT_NAME = 'SimHei'
NAVY  = '#1B2A4A'
CYAN  = '#2E86AB'
ROSE  = '#A23B72'
AMBER = '#F18F01'
TEAL  = '#0D7377'
CORAL = '#E85D75'
SLATE = '#5D6D7E'
WHITE = '#FFFFFF'

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [FONT_NAME, "Microsoft YaHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 15,
    "axes.titlesize": 17,
    "axes.labelsize": 14,
    "legend.fontsize": 13,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
})

Path("../figures").mkdir(exist_ok=True)

# ---- 数据: 题目4.1三场景 + 基线 (v5校正) ----
scenarios_labels = ['基线\n(120万)', 'A-人口\n结构冲击', 'B-管理\n成本+20%', 'C-预算\n调整140万']
bar_colors = [NAVY, CYAN, CORAL, TEAL]

# 覆盖率 (%)
coverage_vals = [100.0, 90.0, 100.0, 100.0]
# 满意度
sat_vals = [0.850, 0.878, 0.842, 0.889]
# 年利润 (万元)
profit_vals = [1097.7, 931.7, 1019.9, 1010.0]

# ---- 组合三面板图 (1行×3列 横排) ----
fig, axes = plt.subplots(1, 3, figsize=(21, 6.2))
fig.patch.set_facecolor(WHITE)

def draw_panel(ax, labels, values, colors, fmt, ylabel, title, ylim_bot, ylim_top, hline=None):
    bars = ax.bar(labels, values, color=colors, edgecolor='white', lw=1.2, width=0.55)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (ylim_top-ylim_bot)*0.025,
                fmt.format(val), ha='center', fontsize=12, fontweight='bold', color=NAVY)
    if hline is not None:
        ax.axhline(y=hline, color=SLATE, lw=1.0, ls='--', alpha=0.5)
    ax.set_title(title, fontsize=14, fontweight='bold', pad=12, color=NAVY)
    ax.set_ylabel(ylabel, fontsize=11, color=SLATE)
    ax.set_ylim(ylim_bot, ylim_top)
    ax.tick_params(axis='x', labelsize=10, colors=NAVY)
    ax.tick_params(axis='y', labelsize=10, colors=SLATE)
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False)
    ax.grid(axis='y', alpha=0.15, color=SLATE, lw=0.4)

# (a) 覆盖率
draw_panel(axes[0], scenarios_labels, coverage_vals, bar_colors,
           '{:.0f}%', '覆盖率 (%)', '(a) 覆盖率', 55, 118, hline=100)

# (b) 满意度
draw_panel(axes[1], scenarios_labels, sat_vals, bar_colors,
           '{:.3f}', '平均综合满意度 S', '(b) 加权满意度', 0.60, 1.03)

# (c) 年利润
draw_panel(axes[2], scenarios_labels, profit_vals, bar_colors,
           '{:.0f}', '年总利润 (万元)', '(c) 年利润', 450, 1280)

fig.suptitle('三场景灵敏度分析全景对比', fontsize=16, fontweight='bold', y=1.01, color=NAVY)
fig.tight_layout(pad=2.5)
fig.savefig("../figures/figure_q4_sensitivity_combined.png", dpi=300, facecolor='white', bbox_inches='tight')
plt.close(fig)
print("[OK] figures/figure_q4_sensitivity_combined.png — 三面板横排 (v5校正)")
