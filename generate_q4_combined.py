"""
generate_q4_combined.py — 生成 Q4 灵敏度分析三面板横排组合图 (a)(b)(c)
复用 solve_q4_sensitivity.py 的数据接口, 避免重跑 MILP.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path

# ---- 中文注册 ----
fm.fontManager.addfont('C:/Windows/Fonts/simhei.ttf')
fm._load_fontmanager(try_read_cache=False)

FONT_NAME = 'SimHei'

sns.set_style("white")
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

Path("figures").mkdir(exist_ok=True)

# ---- 数据: 与 solve_q4_sensitivity.py §7 完全一致 ----
scenarios_labels = ['基线\n120万', 'A-130\n预算放松', 'A-140\n预算放松', 'A-150\n预算放松',
                    'B-成本\n通胀+20%', 'C-银发\n海啸']

C_BASE    = '#2C3E50'
C_BUDGET  = '#3498DB'
C_SHOCK   = '#E74C3C'
C_TSUNAMI = '#E67E22'
bar_colors = [C_BASE, C_BUDGET, C_BUDGET, C_BUDGET, C_SHOCK, C_TSUNAMI]

# 覆盖率 (%)
coverage_vals = [100.0, 100.0, 100.0, 100.0, 80.0, 90.0]
# 满意度
sat_vals = [0.850, 0.883, 0.889, 0.912, 0.906, 0.895]
# 年利润 (万元)
profit_vals = [1097.7, 1053.8, 1010.0, 980.9, 667.7, 887.9]

# ---- 组合三面板图 (1行×3列 横排) ----
fig, axes = plt.subplots(1, 3, figsize=(22, 6.5))
fig.patch.set_facecolor('white')

def draw_panel(ax, labels, values, colors, fmt, ylabel, title, ylim_bot, ylim_top, hline=None):
    bars = ax.bar(labels, values, color=colors, edgecolor='white', lw=1.2, width=0.55)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (ylim_top-ylim_bot)*0.02,
                fmt.format(val), ha='center', fontsize=13, fontweight='bold', color='#2C3E50')
    if hline is not None:
        ax.axhline(y=hline, color='#BDC3C7', linestyle='--', lw=1.2, alpha=0.7)
    ax.set_title(title, fontsize=15, fontweight='bold', pad=14, color='#2C3E50')
    ax.set_ylabel(ylabel, fontsize=13, color='#34495E')
    ax.set_ylim(ylim_bot, ylim_top)
    ax.tick_params(axis='x', labelsize=11, colors='#2C3E50')
    ax.tick_params(axis='y', labelsize=10, colors='#7F8C8D')
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False)
    ax.grid(axis='y', alpha=0.25, color='#BDC3C7', lw=0.5)

# (a) 覆盖率
draw_panel(axes[0], scenarios_labels, coverage_vals, bar_colors,
           '{:.0f}%', '覆盖率 (%)', '(a) 覆盖率', 50, 118, hline=100)

# (b) 满意度
draw_panel(axes[1], scenarios_labels, sat_vals, bar_colors,
           '{:.3f}', '平均综合满意度 S', '(b) 加权满意度', 0.55, 1.05)

# (c) 年利润
draw_panel(axes[2], scenarios_labels, profit_vals, bar_colors,
           '{:.0f}', '年总利润 (万元)', '(c) 年利润', 400, 1300)

fig.suptitle('三场景灵敏度分析全景对比', fontsize=17, fontweight='bold', y=1.01, color='#2C3E50')
fig.tight_layout(pad=2.5)
fig.savefig("figures/figure_q4_sensitivity_combined.png", dpi=300, facecolor='white', bbox_inches='tight')
plt.close(fig)
print("[OK] figures/figure_q4_sensitivity_combined.png 已保存 (三面板横排)")
