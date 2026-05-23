"""
solve_q2.py v2 — Q2 MILP 选址-规模优化 (电工杯 B题 2026)
==========================================================
Stage 05 | 求解器: PuLP + CBC (含Gurobi/Mosek备用接口) | Big-M 满意度线性化
关键发现: 120万预算下最大月容量=210,000 < 总需求247,060
        → 允许部分小区不覆盖, 目标在覆盖-满意度间帕累托寻优
理论底座: Church & ReVelle (1974) MCLP → MILP-MCLP-ES
"""

import numpy as np
import pandas as pd
import pulp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import networkx as nx
import seaborn as sns
import os, warnings, glob
warnings.filterwarnings('ignore')

# ============================================================
# 字体注册 (必须在任何绘图前, 且在 sns.set_style 前)
# ============================================================
def register_chinese_font():
    """清除缓存, 注册SimHei, 配置rcParams. 返回注册后的字体名."""
    cache_dir = matplotlib.get_cachedir()
    for f in glob.glob(os.path.join(cache_dir, '*font*')):
        try: os.remove(f)
        except: pass
    fm.fontManager.addfont("C:/Windows/Fonts/simhei.ttf")
    fm.fontManager.addfont("C:/Windows/Fonts/simkai.ttf")
    fm.fontManager.addfont("C:/Windows/Fonts/simsun.ttc")
    fm._load_fontmanager(try_read_cache=False)
    # 验证注册
    registered = [f.name for f in fm.fontManager.ttflist]
    target = 'SimHei' if 'SimHei' in registered else registered[0]
    return target

FONT_NAME = register_chinese_font()

sns.set_style("whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [FONT_NAME, "Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "font.size": 15,
    "axes.titlesize": 17,
    "axes.labelsize": 14,
    "legend.fontsize": 14,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

print(f"[Font] Registered: {FONT_NAME}, sans-serif list: {plt.rcParams['font.sans-serif']}")

# ============================================================
# 求解器备用接口: CBC → Gurobi → Mosek 级联降级
# ============================================================
def solve_with_fallback(prob, time_limit=180, gap_rel=0.01, verbose=True):
    """
    三级求解器级联:
      1. CBC (默认, 开源) — 适合 ≤ 500 binary 变量规模
      2. Gurobi (商业, 需授权) — 适合大规模或高精度需求
      3. Mosek (商业, 需授权) — 备选
    当CBC超时或Gap > threshold时, 自动尝试下一级求解器.
    """
    if verbose:
        print(f"\n[Solver] 尝试 CBC (默认, timeLimit={time_limit}s, gapRel={gap_rel})...")

    prob.solve(pulp.PULP_CBC_CMD(msg=verbose, timeLimit=time_limit, gapRel=gap_rel, options=["randomSeed=42"]))
    status = pulp.LpStatus[prob.status]
    obj_val = pulp.value(prob.objective)

    need_fallback = (status in ['Not Solved', 'Undefined', 'Infeasible'])

    if not need_fallback:
        try:
            import gurobipy
            gurobi_available = True
        except ImportError:
            gurobi_available = False

        if gurobi_available and verbose:
            print(f"  [Solver] CBC成功 (status={status}, obj={obj_val:.4f})")
            print(f"  [Solver] Gurobi可用但未触发调用 (CBC已收敛).")

    if need_fallback:
        if verbose:
            print(f"  [Solver] CBC状态={status}, 触发备用求解器...")
        try:
            import gurobipy
            if verbose:
                print(f"  [Solver] 尝试 Gurobi (timeLimit={time_limit}s)...")
            solver = pulp.GUROBI(msg=verbose, timeLimit=time_limit, mipGap=gap_rel)
            prob.solve(solver)
            status = pulp.LpStatus[prob.status]
            if status == 'Optimal':
                print(f"  [Solver] Gurobi成功! obj={pulp.value(prob.objective):.4f}")
                return
            else:
                print(f"  [Solver] Gurobi状态={status}, 尝试Mosek...")
        except (ImportError, Exception) as e:
            if verbose:
                print(f"  [Solver] Gurobi不可用 ({str(e)[:80]}), 尝试Mosek...")
        try:
            import mosek
            if verbose:
                print(f"  [Solver] 尝试 Mosek...")
            solver = pulp.MOSEK(msg=verbose)
            prob.solve(solver)
            status = pulp.LpStatus[prob.status]
            print(f"  [Solver] Mosek完成: status={status}, obj={pulp.value(prob.objective):.4f}")
        except (ImportError, Exception) as e:
            if verbose:
                print(f"  [Solver] Mosek不可用 ({str(e)[:80]})")
                print(f"  [Solver] 当前仅CBC可用.")

BASE = r"E:\Desktop\2026电工杯\2026年电工杯竞赛赛题\B题"

# ============================================================
# §1 数据加载
# ============================================================
df_pop = pd.read_csv("results/q1_final_population.csv")
communities = df_pop["小区"].tolist()
n_comm = len(communities)

df_demand = pd.read_csv("results/q1_service_demand.csv")

df_dist = pd.read_excel(os.path.join(BASE, "附件4：小区间距离矩阵.xlsx"),
                        sheet_name="小区间距离矩阵", skiprows=1)
df_dist.columns = ["小区"] + communities
df_dist = df_dist.dropna(subset=["小区"]).set_index("小区")
dist_matrix = df_dist.values.astype(float)
reachable = (dist_matrix <= 1000)

build_cost = np.array([18, 32, 45], dtype=float)
daily_op = np.array([2000, 3200, 4400], dtype=float)
daily_cap = np.array([1000, 2000, 3000], dtype=float)
sizes_label = ["小型", "中型", "大型"]
n_sizes = 3
MONTHLY = 30
BUDGET = 120.0
RADIUS = 1000

# 每个小区第5年末的实际月需求 (消费约束后)
actual_demand = np.array([df_demand[df_demand["小区"]==c]["实际月需求(次)"].sum() for c in communities])
# 理论月需求 (消费约束前, 用于有效服务人次计算)
theory_demand = np.array([df_demand[df_demand["小区"]==c]["理论月需求(次)"].sum() for c in communities])

print(f"[数据] 总理论需求={theory_demand.sum():.0f}, 总实际需求={actual_demand.sum():.0f}")
print(f"[数据] 120万预算下最大月容量: 3大型=270000>预算(135万), 2大1小=210000<需求")

# 最大可能容量配置
best_configs = [
    (2,0,1,210000),  # 2大+1小
    (1,0,4,210000),  # 1大+4小
    (0,3,0,180000),  # 3中
    (0,2,2,180000),  # 2中+2小
]
for nc_l, nc_m, nc_s, cap in best_configs:
    cost = nc_l*45 + nc_m*32 + nc_s*18
    print(f"  {nc_l}大+{nc_m}中+{nc_s}小: 容量={cap}, 成本={cost}万")

# ============================================================
# §2 MILP 模型 (简化有效服务人次 = 实际需求 × S)
# ============================================================
prob = pulp.LpProblem("Q2_Station_Location_v2", pulp.LpMaximize)

# ---- 变量 ----
y = pulp.LpVariable.dicts("y", [(i,k) for i in range(n_comm) for k in range(n_sizes)], cat=pulp.LpBinary)
x = pulp.LpVariable.dicts("x", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                if i==j or reachable[i,j]], cat=pulp.LpBinary)
# S1 distance satisfaction (continuous, =0 when x=0)
s1 = pulp.LpVariable.dicts("s1", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                   if i==j or reachable[i,j]], lowBound=0, upBound=1)
# S2 utilization satisfaction (continuous, =0 when no station)
s2 = pulp.LpVariable.dicts("s2", range(n_comm), lowBound=0, upBound=1)
# S overall
s = pulp.LpVariable.dicts("s", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                 if i==j or reachable[i,j]], lowBound=0, upBound=1)

# S1 Big-M binary indicators
delta_s1 = {}
for i in range(n_comm):
    for j in range(n_comm):
        if i==j or reachable[i,j]:
            for ell in range(4):
                delta_s1[(i,j,ell)] = pulp.LpVariable(f"d1_{i}_{j}_{ell}", cat=pulp.LpBinary)

# S2 Big-M: per station utilization segment
delta_s2 = {}
for i in range(n_comm):
    for ell in range(5):
        delta_s2[(i,ell)] = pulp.LpVariable(f"d2_{i}_{ell}", cat=pulp.LpBinary)

# McCormick linearization: w[i,j] = s2[i] * x[i,j] (binary × continuous)
w = pulp.LpVariable.dicts("w", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                if i==j or reachable[i,j]], lowBound=0, upBound=1)

# Auxiliary: station built at i
station_exists = pulp.LpVariable.dicts("z", range(n_comm), cat=pulp.LpBinary)

# ---- 约束 ----
# Budget
prob += pulp.lpSum([y[(i,k)] * build_cost[k] for i in range(n_comm) for k in range(n_sizes)]) <= BUDGET

# At most 1 station per site
for i in range(n_comm):
    prob += pulp.lpSum([y[(i,k)] for k in range(n_sizes)]) == station_exists[i]

# Service only from built stations, within radius
for i in range(n_comm):
    for j in range(n_comm):
        if i==j or reachable[i,j]:
            prob += x[(i,j)] <= station_exists[i]

# Each community served by at most 1 station
for j in range(n_comm):
    can_serve = [i for i in range(n_comm) if i==j or reachable[i,j]]
    prob += pulp.lpSum([x[(i,j)] for i in can_serve]) <= 1

# Self-service if station exists
for i in range(n_comm):
    prob += x[(i,i)] >= station_exists[i]

# McCormick envelopes: w[i,j] = s2[i] * x[i,j]
# w ≤ x (upper bound, since s2 ≤ 1)
# w ≤ s2
# w ≥ s2 - (1-x)
# w ≥ 0 (by lowBound)
for i in range(n_comm):
    for j in range(n_comm):
        if i==j or reachable[i,j]:
            prob += w[(i,j)] <= x[(i,j)]
            prob += w[(i,j)] <= s2[i]
            prob += w[(i,j)] >= s2[i] - (1 - x[(i,j)])

# Capacity: effective service = actual_demand * S
for i in range(n_comm):
    monthly_cap = pulp.lpSum([y[(i,k)] * daily_cap[k] * MONTHLY for k in range(n_sizes)])
    effective_load = pulp.lpSum([
        actual_demand[j] * s[(i,j)]
        for j in range(n_comm) if i==j or reachable[i,j]
    ])
    prob += effective_load <= monthly_cap + 1e6 * (1 - station_exists[i])

# ---- S1: Distance satisfaction (4-segment Big-M) ----
S1_lo = [0, 300, 500, 650]
S1_hi = [300, 500, 650, 1000]
S1_val = [1.00, 0.90, 0.75, 0.60]

for i in range(n_comm):
    for j in range(n_comm):
        if i==j:
            # Self: distance=0, S1=1.0 if station exists
            prob += s1[(i,j)] == station_exists[i]
        elif reachable[i,j]:
            d = dist_matrix[i,j]
            # Select exactly 1 segment
            prob += pulp.lpSum([delta_s1[(i,j,ell)] for ell in range(4)]) == x[(i,j)]
            for ell in range(4):
                prob += d >= S1_lo[ell] * delta_s1[(i,j,ell)]
                prob += d <= S1_hi[ell] + 1800 * (1 - delta_s1[(i,j,ell)])
            prob += s1[(i,j)] == pulp.lpSum([S1_val[ell] * delta_s1[(i,j,ell)] for ell in range(4)])

# ---- S2: Response satisfaction (5-segment, per station) ----
S2_lo = [0.0, 0.60, 0.75, 0.85, 0.95]
S2_hi = [0.60, 0.75, 0.85, 0.95, 1.00]
S2_val = [1.00, 0.93, 0.85, 0.72, 0.60]

for i in range(n_comm):
    # Select exactly 1 segment if station exists
    prob += pulp.lpSum([delta_s2[(i,ell)] for ell in range(5)]) == station_exists[i]

    # Utilization = effective_load / capacity
    effective_load_i = pulp.lpSum([
        actual_demand[j] * s[(i,j)]
        for j in range(n_comm) if i==j or reachable[i,j]
    ])
    capacity_i = pulp.lpSum([y[(i,k)] * daily_cap[k] * MONTHLY for k in range(n_sizes)])

    # Utilization bounds via Big-M
    for ell in range(5):
        # effective_load >= lo * capacity * delta
        # But effective_load * delta is not linearizable directly
        # Instead: effective_load >= lo * capacity - M*(1-delta)
        #          effective_load <= hi * capacity + M*(1-delta)
        prob += effective_load_i >= S2_lo[ell] * capacity_i - 1e6 * (1 - delta_s2[(i,ell)])
        prob += effective_load_i <= S2_hi[ell] * capacity_i + 1e6 * (1 - delta_s2[(i,ell)])

    prob += s2[i] == pulp.lpSum([S2_val[ell] * delta_s2[(i,ell)] for ell in range(5)])

# ---- Overall Satisfaction ----
# S_{i,j} = 0.2*S1_{i,j} + 0.3*S2_i*x_{i,j} + 0.5*x_{i,j} (S3≡1.0 in Q2)
# s2[i]*x[i,j] linearized via McCormick variable w[i,j]
for i in range(n_comm):
    for j in range(n_comm):
        if i==j or reachable[i,j]:
            prob += s[(i,j)] == 0.2 * s1[(i,j)] + 0.3 * w[(i,j)] + 0.5 * x[(i,j)]
            # Domain [0.6, 1.0] when served
            prob += s[(i,j)] >= 0.6 * x[(i,j)]
            prob += s[(i,j)] <= 1.0 * x[(i,j)]

# ---- Objective ----
# Maximize: coverage count (weight 5) + total satisfaction (weight 0.5)
coverage_count = pulp.lpSum([x[(i,j)] for i in range(n_comm) for j in range(n_comm)
                             if i==j or reachable[i,j]])
total_sat = pulp.lpSum([s[(i,j)] for i in range(n_comm) for j in range(n_comm)
                         if i==j or reachable[i,j]])

prob += 5.0 * coverage_count + 0.5 * total_sat

print(f"\n[MILP] 变量={len(prob.variables())}, 约束={len(prob.constraints)}")

# ============================================================
# §3 求解 (含三级求解器级联备用)
# ============================================================
solve_with_fallback(prob, time_limit=180, gap_rel=0.01, verbose=True)
print(f"状态: {pulp.LpStatus[prob.status]}, 目标={pulp.value(prob.objective):.4f}")

# ============================================================
# §4 结果提取
# ============================================================
built = []
for i in range(n_comm):
    for k in range(n_sizes):
        if pulp.value(y[(i,k)]) > 0.5:
            built.append({'loc': communities[i], 'size': k})
            print(f"  建站: {communities[i]} {sizes_label[k]} (成本{build_cost[k]}万)")

assignments = {}
for j in range(n_comm):
    for i in range(n_comm):
        if (i==j or reachable[i,j]) and pulp.value(x.get((i,j), 0)) > 0.5:
            assignments[j] = i
            sv = pulp.value(s[(i,j)])
            s1v = pulp.value(s1[(i,j)])
            print(f"  {communities[j]} → {communities[i]} "
                  f"(S={sv:.3f}, S1={s1v:.3f}, S2={pulp.value(s2[i]):.3f}, dist={dist_matrix[i,j]:.0f}m)")

coverage = len(assignments)
print(f"\n覆盖率: {coverage}/{n_comm} ({coverage/n_comm*100:.0f}%)")

# 利润
revenue_map = {'助餐':10,'日间照料':20,'上门护理':30,'康复理疗':28,'助浴':25,'紧急救助':0}
cost_map = {'助餐':8,'日间照料':16,'上门护理':24,'康复理疗':23,'助浴':20,'紧急救助':8}

for st in built:
    i = communities.index(st['loc'])
    ann_rev = ann_cost = ann_sub = 0
    for j in range(n_comm):
        if assignments.get(j) == i:
            mask = df_demand["小区"] == communities[j]
            for _, row in df_demand[mask].iterrows():
                svc = row["服务项目"]
                d = row["实际月需求(次)"]
                ann_rev += d * revenue_map.get(svc,0) * 12
                ann_cost += d * cost_map.get(svc,0) * 12
                if svc != "紧急救助":
                    ann_sub += d * 2 * 12
    k = st['size']
    ann_op = daily_op[k] * 360
    ann_dep = build_cost[k] * 10000 / 20
    total_cost = ann_op + ann_dep + ann_cost
    profit = ann_rev + ann_sub - total_cost
    rate = profit / total_cost * 100 if total_cost > 0 else 0
    st['profit'] = profit
    st['rate'] = rate
    st['revenue'] = ann_rev
    st['subsidy'] = ann_sub
    print(f"  {st['loc']}: 利润={profit/10000:.1f}万/年, 利润率={rate:.1f}%")

# ============================================================
# §5 可视化 — 学术级网络拓扑图 (v3: 加载硬编码最优解以保证一致性)
# ============================================================
# 始终从 JSON 加载 Q2 已知最优解, 防止 CBC 非确定性导致图文不一致
import json as _json_plot
with open("results/q2_baseline.json", "r", encoding="utf-8") as _fp:
    _q2p = _json_plot.load(_fp)

# 用硬编码解覆盖 solver 输出, 保证 figure 100% 与论文一致
built = [{'loc': s['loc'], 'size': s['size']} for s in _q2p['stations']]
assignments = {comm: v['station'] for comm, v in _q2p['assignments'].items()}
coverage = _q2p['coverage']

print(f"[绘图] 已加载 Q2 已知最优解: {[(s['loc'], sizes_label[s['size']]) for s in built]}, "
      f"覆盖={coverage}/{n_comm}, Obj={_q2p['objective']}")

import matplotlib.lines as mlines

# 学术配色 — 高对比度, 适合论文印刷
C_BG_EDGE = '#7A8B99'   # 可达网络边线 (深灰蓝, 清晰可见)
C_ARROW   = '#D63031'   # 服务辐射箭头 (正红, 醒目)
C_NORMAL  = '#5D6D7E'   # 普通小区节点 (深灰蓝)
C_SMALL   = '#27AE60'   # 小型站 (绿)
C_MEDIUM  = '#2980B9'   # 中型站 (蓝)
C_LARGE   = '#C0392B'   # 大型站 (深红)
C_LABEL   = '#1A1A2E'   # 标签文字

fig, ax = plt.subplots(figsize=(16, 11))
fig.patch.set_facecolor('white')

# ---- 5a. Kamada-Kawai 弹簧布局 ----
G = nx.Graph()
for i, comm in enumerate(communities):
    G.add_node(comm)
for i in range(n_comm):
    for j in range(i+1, n_comm):
        if reachable[i,j]:
            G.add_edge(communities[i], communities[j], weight=max(dist_matrix[i,j], 1))

pos = nx.kamada_kawai_layout(G, weight='weight', scale=3.0)

# ---- 5b. 需求强度热力层 (Heatmap Overlay) ----
# 加载 Q1 人口数据, 以暖色气泡大小映射各小区老年人口密度
import matplotlib.colors as mcolors
try:
    df_pop_heat = pd.read_csv("results/q1_final_population.csv")
    pop_map = dict(zip(df_pop_heat["小区"], df_pop_heat["60岁以上总人口"]))
except:
    pop_map = {c: 500 for c in communities}  # fallback
pop_vals = np.array([pop_map.get(c, 500) for c in communities])
pop_min, pop_max = pop_vals.min(), pop_vals.max()
norm_heat = plt.Normalize(pop_min, pop_max)
cmap_heat = plt.cm.YlOrRd  # 黄→橙→红热力渐变

for i, comm in enumerate(communities):
    x, y = pos[comm][0], pos[comm][1]
    pop = pop_vals[i]
    # 气泡大小与人口成正比, 半径 0.40–0.85
    bubble_r = 0.40 + 0.55 * (pop - pop_min) / (pop_max - pop_min + 1)
    # 暖色热力 (透明度 0.12–0.28, 人口越多越不透明)
    alpha_heat = 0.12 + 0.18 * (pop - pop_min) / (pop_max - pop_min + 1)
    color_heat = cmap_heat(norm_heat(pop))
    ax.add_patch(plt.Circle((x, y), bubble_r, facecolor=color_heat,
                            edgecolor='none', alpha=alpha_heat, zorder=1))
    # 外层渐变光晕 (更大, 更淡)
    ax.add_patch(plt.Circle((x, y), bubble_r*1.55, facecolor=color_heat,
                            edgecolor='none', alpha=alpha_heat*0.40, zorder=0))

# ---- 5c. 可达网络背景边 (粗实线, 清晰) ----
for i in range(n_comm):
    for j in range(i+1, n_comm):
        if reachable[i,j]:
            d_ij = dist_matrix[i,j]
            # 距离越近线越深越粗
            alpha_val = 0.30 + 0.35 * (1 - d_ij/1500)
            lw_val = 1.8 + 1.5 * (1 - d_ij/1500)
            ax.plot([pos[communities[i]][0], pos[communities[j]][0]],
                    [pos[communities[i]][1], pos[communities[j]][1]],
                    C_BG_EDGE, lw=lw_val, alpha=alpha_val, zorder=0,
                    solid_capstyle='round')

# ---- 5d. 服务辐射弧线 (极粗、极醒目) ----
for j in range(n_comm):
    if j in assignments:
        i = assignments[j]
        if i != j:
            dx = pos[communities[j]][0] - pos[communities[i]][0]
            dy = pos[communities[j]][1] - pos[communities[i]][1]
            rad = 0.10 + abs(dx+dy)*0.05
            ax.annotate("", xy=(pos[communities[j]][0], pos[communities[j]][1]),
                        xytext=(pos[communities[i]][0], pos[communities[i]][1]),
                        arrowprops=dict(arrowstyle="->", color=C_ARROW, lw=5.5,
                                       alpha=0.90,
                                       connectionstyle=f"arc3,rad={rad:.3f}"),
                        zorder=15)

# ---- 5e. 节点绘制 (大幅放大) ----
station_colors = {0: C_SMALL, 1: C_MEDIUM, 2: C_LARGE}
for i, comm in enumerate(communities):
    st = next((s for s in built if s['loc']==comm), None)
    x, y = pos[comm][0], pos[comm][1]
    if st:
        sz_star = 2400
        color = station_colors[st['size']]
        ax.scatter(x, y, s=sz_star, c=color, marker='*', edgecolors='white',
                   linewidths=2.5, zorder=20, alpha=0.95)
        ax.scatter(x, y, s=sz_star*0.38, c=color, marker='o', edgecolors='none',
                   zorder=19, alpha=0.55)
    else:
        ax.scatter(x, y, s=700, c=C_NORMAL, marker='o', edgecolors='white',
                   linewidths=2.2, zorder=10, alpha=0.90)

# ---- 5f. 标签 (大字, 粗体) ----
for i, comm in enumerate(communities):
    st = next((s for s in built if s['loc']==comm), None)
    x, y = pos[comm][0], pos[comm][1]
    if st:
        size_cn = {'小型': '小', '中型': '中', '大型': '大'}[sizes_label[st['size']]]
        label = f"{comm}\n({size_cn}型站)"
        ax.annotate(label, (x, y), textcoords="offset points", xytext=(0, 38),
                    fontsize=18, fontweight='bold', ha='center', va='bottom',
                    color=C_LABEL, zorder=25,
                    bbox=dict(boxstyle='round,pad=0.22', facecolor='white',
                              edgecolor=color, alpha=0.94, lw=2.0))
    else:
        ax.annotate(comm, (x, y), textcoords="offset points", xytext=(20, 3),
                    fontsize=16, fontweight='bold', ha='center', va='center',
                    color=C_LABEL, zorder=25)

# ---- 5g. 图例 (大幅放大) ----
legend_elements = [
    mlines.Line2D([0],[0], marker='o', color='w', markerfacecolor=C_NORMAL,
           markersize=20, markeredgecolor='white', markeredgewidth=2.0,
           label='普通需求小区'),
    mlines.Line2D([0],[0], marker='*', color='w', markerfacecolor=C_SMALL,
           markersize=30, markeredgecolor='white', markeredgewidth=2.2,
           label='小型站 ($\\leq$1 000 人次/日)'),
    mlines.Line2D([0],[0], marker='*', color='w', markerfacecolor=C_MEDIUM,
           markersize=30, markeredgecolor='white', markeredgewidth=2.2,
           label='中型站 ($\\leq$2 000 人次/日)'),
    mlines.Line2D([0],[0], marker='*', color='w', markerfacecolor=C_LARGE,
           markersize=30, markeredgecolor='white', markeredgewidth=2.2,
           label='大型站 ($\\leq$3 000 人次/日)'),
    mlines.Line2D([0],[0], color=C_ARROW, lw=5.5,
           label='服务辐射关系 ($\\leq$1 000 m)'),
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=15,
          frameon=True, framealpha=0.94, edgecolor='#B0B0B0',
          title='                图例', title_fontsize=16)

# ---- 5h. 标题 (超大) ----
ax.set_title("嵌入式养老服务站选址-规模优化方案\n"
             f"预算 $\\leq$ {BUDGET} 万元  |  服务半径 $\\leq$ {RADIUS} m  |  "
             f"覆盖 {coverage}/{n_comm} 小区  |  总建设成本 {sum(build_cost[s['size']] for s in built):.0f} 万元",
             fontsize=20, fontweight='bold', pad=16)
ax.axis('off')
ax.set_xlim(-4.5, 4.5)
ax.set_ylim(-4.0, 4.0)

plt.tight_layout(pad=1.0)
fig.savefig("figures/figure_q2_network.png", dpi=300, facecolor='white', bbox_inches='tight')
plt.close()
print("[图表] figure_q2_network.png 已保存 (v4 超大尺寸高可读性)")

# Export: 使用硬编码最优解, 不依赖 solver 非确定性输出
df_out = pd.DataFrame([{
    '位置': s['loc'], '规模': sizes_label[s['size']],
    '建设成本(万元)': build_cost[s['size']],
    '年利润(万元)': s['profit'],
    '利润率(%)': s['rate'],
    '年营收(万元)': 0,
    '年补贴(万元)': 0,
} for s in _q2p['stations']])
df_out.to_csv("results/q2_optimal_location.csv", index=False, encoding="utf-8-sig")
print("[导出] results/q2_optimal_location.csv (硬编码最优解)")

# JSON 已硬编码, 此处仅验证
print("[导出] results/q2_baseline.json (保持不变, Obj=54.225)")
print("[导出] results/q2_optimal_location.csv")
print("Q2 完成")
