"""
config.py — Shared configuration for B题 codebase (电工杯 2026)
===============================================================
Academic Noir palette, font registration, path resolution, style setup.
Import from solve_*.py and regenerate_all_figures.py.
"""
import os
import glob
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# ---- Academic Noir Palette ----
NAVY   = '#1B2A4A'
CYAN   = '#2E86AB'
ROSE   = '#A23B72'
AMBER  = '#F18F01'
TEAL   = '#0D7377'
SLATE  = '#5D6D7E'
WHITE  = '#FFFFFF'
GOLD   = '#D4A843'
CORAL  = '#E85D75'

PALETTE_3 = [CYAN, AMBER, ROSE]
LABELS_3 = ['自理 (Self-care)', '半失能 (Semi-disabled)', '失能 (Disabled)']

# ---- Path resolution ----
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, '..', 'data')
RES  = os.path.join(ROOT, '..', 'results')
FIG  = os.path.join(ROOT, '..', 'figures')

for d in [RES, FIG]:
    os.makedirs(os.path.join(ROOT, '..', d.lstrip('./')), exist_ok=True)

# ---- Font registration ----
def register_chinese_font():
    cache_dir = matplotlib.get_cachedir()
    for f in glob.glob(os.path.join(cache_dir, '*font*')):
        try: os.remove(f)
        except: pass
    for fp in ['C:/Windows/Fonts/simhei.ttf', 'C:/Windows/Fonts/simkai.ttf',
               'C:/Windows/Fonts/simsun.ttc', 'C:/Windows/Fonts/msyh.ttc']:
        try: fm.fontManager.addfont(fp)
        except: pass
    fm._load_fontmanager(try_read_cache=False)
    names = [f.name for f in fm.fontManager.ttflist]
    return 'SimHei' if 'SimHei' in names else ('Microsoft YaHei' if 'Microsoft YaHei' in names else names[0])

FONT_NAME = register_chinese_font()

# ---- Global style ----
def set_academic_style():
    sns.set_style("white")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [FONT_NAME, "Microsoft YaHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 14,
        "axes.titlesize": 16,
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
        "grid.alpha": 0.12, "grid.color": SLATE,
    })
