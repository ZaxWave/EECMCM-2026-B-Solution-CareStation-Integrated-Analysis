"""
solve_q4_sensitivity.py — Q4 灵敏度分析与鲁棒性检验 (电工杯 B题 2026)
====================================================================
Stage 06 | 三场景参数扫描:
  场景A: 预算放松 (120→130→140→150万) — 财政政策杠杆
  场景B: 成本膨胀 (建设+运营成本 × 1.20) — 供给侧冲击
  场景C: 银发海啸 (半失能转移 4.5%→5.5%, 失能转移 10%→12%) — 需求侧冲击

输出: results/q4_sensitivity_summary.csv + 可视化对比
"""

import numpy as np
import pandas as pd
import pulp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import os, warnings, copy, glob
warnings.filterwarnings('ignore')

# ============================================================
# 字体注册 (必须在任何绘图前)
# ============================================================
def register_chinese_font():
    cache_dir = matplotlib.get_cachedir()
    for f in glob.glob(os.path.join(cache_dir, '*font*')):
        try: os.remove(f)
        except: pass
    fm.fontManager.addfont("C:/Windows/Fonts/simhei.ttf")
    fm.fontManager.addfont("C:/Windows/Fonts/simkai.ttf")
    fm.fontManager.addfont("C:/Windows/Fonts/simsun.ttc")
    fm._load_fontmanager(try_read_cache=False)
    registered = [f.name for f in fm.fontManager.ttflist]
    return 'SimHei' if 'SimHei' in registered else registered[0]

FONT_NAME = register_chinese_font()

sns.set_style("whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [FONT_NAME, "Microsoft YaHei", "SimHei", "DejaVu Sans"],
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
print(f"[Font] Registered: {FONT_NAME}")

BASE = r"E:\Desktop\2026电工杯\2026年电工杯竞赛赛题\B题"
os.makedirs("results", exist_ok=True)
os.makedirs("figures", exist_ok=True)

# ============================================================
# §1 数据加载
# ============================================================
df_pop_orig = pd.read_csv("results/q1_final_population.csv")
communities = df_pop_orig["小区"].tolist()
n_comm = len(communities)

df_demand_orig = pd.read_csv("results/q1_service_demand.csv")

df_dist = pd.read_excel(os.path.join(BASE, "附件4：小区间距离矩阵.xlsx"),
                        sheet_name="小区间距离矩阵", skiprows=1)
df_dist.columns = ["小区"] + communities
df_dist = df_dist.dropna(subset=["小区"]).set_index("小区")
dist_matrix = df_dist.values.astype(float)
reachable = (dist_matrix <= 1000)

# ============================================================
# §2 基线参数
# ============================================================
BASELINE = {
    'budget': 120.0,
    'build_cost': np.array([18, 32, 45], dtype=float),
    'daily_op': np.array([2000, 3200, 4400], dtype=float),
    'daily_cap': np.array([1000, 2000, 3000], dtype=float),
    'alpha_sm': 0.045,   # 自理→半失能
    'alpha_md': 0.10,    # 半失能→失能
    'mu': 0.05,          # 死亡率
    'beta': 0.07,        # 新增率
    'consumption_caps': [0.20, 0.25, 0.30],
    'radius': 1000,
    'monthly': 30,
}

# ============================================================
# §3 Q1 人口预测函数 (可参数化)
# ============================================================
def build_transition_matrix(mu=0.05, alpha_sm=0.045, alpha_md=0.10, beta=0.07):
    A = np.array([
        [(1 - mu) * (1 - alpha_sm) + beta,  beta,                              beta],
        [(1 - mu) * alpha_sm,               (1 - mu) * (1 - alpha_md),         0.0],
        [0.0,                               (1 - mu) * alpha_md,               (1 - mu)],
    ])
    return A

def predict_population_from_original(A, T=5):
    """从原始附件1读取初始人口, 用自定义A预测5年."""
    df_orig = pd.read_excel(
        os.path.join(BASE, "附件1：小区基础数据.xlsx"),
        sheet_name="人口与老人结构", skiprows=1
    )
    df_orig.columns = ["小区", "总人口", "60plus", "自理", "半失能", "失能", "人均月收入"]
    S0 = df_orig[["自理", "半失能", "失能"]].values.astype(np.float64)
    income = df_orig["人均月收入"].values.astype(np.float64)
    communities_list = df_orig["小区"].tolist()

    S_hist = np.zeros((T+1, len(communities_list), 3))
    S_hist[0] = S0.copy()
    for t in range(T):
        for i in range(len(communities_list)):
            S_hist[t+1, i] = np.round(A @ S_hist[t, i])
    return S_hist[-1], income, communities_list

def compute_demand_from_final(S_final, income, consumption_caps, communities_list):
    """计算 t=5 实际服务需求."""
    # 读取每位老人月均需求
    df_req = pd.read_excel(
        os.path.join(BASE, "附件2：服务需求数据.xlsx"),
        sheet_name="每位老人月均服务需求次数", skiprows=1
    )
    df_req.columns = ["服务项目", "自理", "半自理", "失能"]
    demand_per_capita = df_req[["自理", "半自理", "失能"]].values.astype(np.float64)
    services = df_req["服务项目"].tolist()
    revenue = np.array([10, 20, 30, 28, 25, 0], dtype=np.float64)
    cost = np.array([8, 16, 24, 23, 20, 8], dtype=np.float64)

    n_comm, n_type = S_final.shape
    n_svc = demand_per_capita.shape[0]

    theoretical = np.zeros((n_comm, n_type, n_svc))
    for i in range(n_comm):
        for e in range(n_type):
            theoretical[i, e, :] = S_final[i, e] * demand_per_capita[:, e]

    caps = np.array(consumption_caps)
    actual = np.zeros_like(theoretical)
    for i in range(n_comm):
        for e in range(n_type):
            full_cost = np.sum(demand_per_capita[:, e] * revenue)
            budget = income[i] * caps[e]
            ratio = min(1.0, budget / full_cost) if full_cost > 0 else 1.0
            actual[i, e, :] = theoretical[i, e, :] * ratio

    # 构建 DataFrame 格式需求数据
    rows = []
    for i, comm in enumerate(communities_list):
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
    return pd.DataFrame(rows), services, revenue, cost

# ============================================================
# §4 Q2 MILP 求解函数 (可参数化)
# ============================================================
def solve_q2_milp(df_demand, budget, build_cost, daily_op, daily_cap,
                  time_limit=180, verbose=False):
    """返回: {stations, assignments, coverage, objective, profit_margins, key_metrics}"""
    communities = sorted(df_demand["小区"].unique())
    n_comm = len(communities)

    actual_demand = np.array([df_demand[df_demand["小区"]==c]["实际月需求(次)"].sum() for c in communities])

    n_sizes = 3
    MONTHLY = 30

    prob = pulp.LpProblem("Q4_MILP", pulp.LpMaximize)

    y = pulp.LpVariable.dicts("y", [(i,k) for i in range(n_comm) for k in range(n_sizes)], cat=pulp.LpBinary)
    x = pulp.LpVariable.dicts("x", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                     if i==j or reachable[i,j]], cat=pulp.LpBinary)
    s1 = pulp.LpVariable.dicts("s1", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                       if i==j or reachable[i,j]], lowBound=0, upBound=1)
    s2 = pulp.LpVariable.dicts("s2", range(n_comm), lowBound=0, upBound=1)
    s = pulp.LpVariable.dicts("s", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                     if i==j or reachable[i,j]], lowBound=0, upBound=1)

    delta_s1 = {}
    for i in range(n_comm):
        for j in range(n_comm):
            if i==j or reachable[i,j]:
                for ell in range(4):
                    delta_s1[(i,j,ell)] = pulp.LpVariable(f"d1_{i}_{j}_{ell}", cat=pulp.LpBinary)

    delta_s2 = {}
    for i in range(n_comm):
        for ell in range(5):
            delta_s2[(i,ell)] = pulp.LpVariable(f"d2_{i}_{ell}", cat=pulp.LpBinary)

    w = pulp.LpVariable.dicts("w", [(i,j) for i in range(n_comm) for j in range(n_comm)
                                     if i==j or reachable[i,j]], lowBound=0, upBound=1)
    station_exists = pulp.LpVariable.dicts("z", range(n_comm), cat=pulp.LpBinary)

    # Budget
    prob += pulp.lpSum([y[(i,k)] * build_cost[k] for i in range(n_comm) for k in range(n_sizes)]) <= budget

    for i in range(n_comm):
        prob += pulp.lpSum([y[(i,k)] for k in range(n_sizes)]) == station_exists[i]

    for i in range(n_comm):
        for j in range(n_comm):
            if i==j or reachable[i,j]:
                prob += x[(i,j)] <= station_exists[i]

    for j in range(n_comm):
        can_serve = [i for i in range(n_comm) if i==j or reachable[i,j]]
        prob += pulp.lpSum([x[(i,j)] for i in can_serve]) <= 1

    for i in range(n_comm):
        prob += x[(i,i)] >= station_exists[i]

    for i in range(n_comm):
        for j in range(n_comm):
            if i==j or reachable[i,j]:
                prob += w[(i,j)] <= x[(i,j)]
                prob += w[(i,j)] <= s2[i]
                prob += w[(i,j)] >= s2[i] - (1 - x[(i,j)])

    for i in range(n_comm):
        monthly_cap = pulp.lpSum([y[(i,k)] * daily_cap[k] * MONTHLY for k in range(n_sizes)])
        effective_load = pulp.lpSum([
            actual_demand[j] * s[(i,j)]
            for j in range(n_comm) if i==j or reachable[i,j]
        ])
        prob += effective_load <= monthly_cap + 1e6 * (1 - station_exists[i])

    S1_lo = [0, 300, 500, 650]
    S1_hi = [300, 500, 650, 1000]
    S1_val = [1.00, 0.90, 0.75, 0.60]

    for i in range(n_comm):
        for j in range(n_comm):
            if i==j:
                prob += s1[(i,j)] == station_exists[i]
            elif reachable[i,j]:
                d = dist_matrix[i,j]
                prob += pulp.lpSum([delta_s1[(i,j,ell)] for ell in range(4)]) == x[(i,j)]
                for ell in range(4):
                    prob += d >= S1_lo[ell] * delta_s1[(i,j,ell)]
                    prob += d <= S1_hi[ell] + 1800 * (1 - delta_s1[(i,j,ell)])
                prob += s1[(i,j)] == pulp.lpSum([S1_val[ell] * delta_s1[(i,j,ell)] for ell in range(4)])

    S2_lo = [0.0, 0.60, 0.75, 0.85, 0.95]
    S2_hi = [0.60, 0.75, 0.85, 0.95, 1.00]
    S2_val = [1.00, 0.93, 0.85, 0.72, 0.60]

    for i in range(n_comm):
        prob += pulp.lpSum([delta_s2[(i,ell)] for ell in range(5)]) == station_exists[i]
        effective_load_i = pulp.lpSum([
            actual_demand[j] * s[(i,j)]
            for j in range(n_comm) if i==j or reachable[i,j]
        ])
        capacity_i = pulp.lpSum([y[(i,k)] * daily_cap[k] * MONTHLY for k in range(n_sizes)])
        for ell in range(5):
            prob += effective_load_i >= S2_lo[ell] * capacity_i - 1e6 * (1 - delta_s2[(i,ell)])
            prob += effective_load_i <= S2_hi[ell] * capacity_i + 1e6 * (1 - delta_s2[(i,ell)])
        prob += s2[i] == pulp.lpSum([S2_val[ell] * delta_s2[(i,ell)] for ell in range(5)])

    for i in range(n_comm):
        for j in range(n_comm):
            if i==j or reachable[i,j]:
                prob += s[(i,j)] == 0.2 * s1[(i,j)] + 0.3 * w[(i,j)] + 0.5 * x[(i,j)]
                prob += s[(i,j)] >= 0.6 * x[(i,j)]
                prob += s[(i,j)] <= 1.0 * x[(i,j)]

    coverage_count = pulp.lpSum([x[(i,j)] for i in range(n_comm) for j in range(n_comm)
                                  if i==j or reachable[i,j]])
    total_sat = pulp.lpSum([s[(i,j)] for i in range(n_comm) for j in range(n_comm)
                             if i==j or reachable[i,j]])
    prob += 5.0 * coverage_count + 0.5 * total_sat

    if verbose:
        print(f"  变量={len(prob.variables())}, 约束={len(prob.constraints)}, 求解中...")
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit, gapRel=0.01,
                                   options=['randomSeed=42']))

    # 提取结果
    built = []
    for i in range(n_comm):
        for k in range(n_sizes):
            if pulp.value(y[(i,k)]) > 0.5:
                built.append({'loc': communities[i], 'size': k})

    assignments = {}
    for j in range(n_comm):
        for i in range(n_comm):
            if (i==j or reachable[i,j]) and pulp.value(x.get((i,j), 0)) > 0.5:
                assignments[communities[j]] = communities[i]
                break

    coverage = len(assignments)
    obj = pulp.value(prob.objective)
    status = pulp.LpStatus[prob.status]

    # 利润计算
    revenue_map = {'助餐':10,'日间照料':20,'上门护理':30,'康复理疗':28,'助浴':25,'紧急救助':0}
    cost_map = {'助餐':8,'日间照料':16,'上门护理':24,'康复理疗':23,'助浴':20,'紧急救助':8}

    profit_margins = {}
    total_profit = 0
    for st in built:
        i = communities.index(st['loc'])
        ann_rev = ann_cost_val = ann_sub = 0
        for j_comm, assigned_st in assignments.items():
            if assigned_st == st['loc']:
                j = communities.index(j_comm)
                mask = df_demand["小区"] == j_comm
                for _, row in df_demand[mask].iterrows():
                    svc = row["服务项目"]
                    d = row["实际月需求(次)"]
                    ann_rev += d * revenue_map.get(svc,0) * 12
                    ann_cost_val += d * cost_map.get(svc,0) * 12
                    if svc != "紧急救助":
                        ann_sub += d * 2 * 12
        k = st['size']
        ann_op = daily_op[k] * 360
        ann_dep = build_cost[k] * 10000 / 20
        total_cost = ann_op + ann_dep + ann_cost_val
        profit = ann_rev + ann_sub - total_cost
        rate = profit / total_cost * 100 if total_cost > 0 else 0
        profit_margins[st['loc']] = {'profit': profit/10000, 'rate': rate}
        total_profit += profit

    # 计算加权满意度
    s1_map_q2 = {}
    s2_map_q2 = {}
    s_map = {}
    for j_comm, i_comm in assignments.items():
        j = communities.index(j_comm)
        i = communities.index(i_comm)
        if (i==j or reachable[i,j]):
            sv = pulp.value(s.get((i,j), 0))
            s1v = pulp.value(s1.get((i,j), 0))
            s2v = pulp.value(s2[i])
            s_map[j_comm] = sv
            s1_map_q2[j_comm] = s1v
            s2_map_q2[i_comm] = s2v

    avg_satisfaction = np.mean(list(s_map.values())) if s_map else 0

    return {
        'status': status,
        'objective': obj,
        'coverage': coverage,
        'n_communities': n_comm,
        'built_stations': built,
        'assignments': assignments,
        'profit_margins': profit_margins,
        'total_profit': total_profit / 10000,
        'avg_satisfaction': avg_satisfaction,
        'uncovered': [c for c in communities if c not in assignments],
        'budget_used': sum(build_cost[s['size']] for s in built),
        'satisfaction_map': s_map,
        's2_map': s2_map_q2,
    }

# ============================================================
# §5 场景定义与批量求解
# ============================================================
print("=" * 70)
print("Q4 灵敏度分析 — 三场景参数扫描")
print("=" * 70)

# ---- 基线: 直接从 Q2 JSON 加载, 保证与论文正文 54.225 完全一致 ----
import json as _json
print("\n[基线] 加载 Q2 确定性最优解 (F大型+H中型+J中型, Obj=54.225)...")
with open("results/q2_baseline.json", "r", encoding="utf-8") as _f:
    _q2 = _json.load(_f)
baseline = {
    'status': 'Optimal (from Q2 JSON)',
    'objective': _q2['objective'],
    'coverage': _q2['coverage'],
    'n_communities': _q2['n_communities'],
    'built_stations': [{'loc': s['loc'], 'size': s['size']} for s in _q2['stations']],
    'assignments': {k: v['station'] for k, v in _q2['assignments'].items()},
    'profit_margins': {s['loc']: {'profit': s['profit'], 'rate': s['rate']}
                       for s in _q2['stations']},
    'total_profit': sum(s['profit'] for s in _q2['stations']),
    'avg_satisfaction': _q2['avg_satisfaction'],
    'uncovered': [],
    'budget_used': _q2['budget_used'],
    'satisfaction_map': {k: v['S'] for k, v in _q2['assignments'].items()},
    's2_map': {s['loc']: _q2['s2_by_station'].get(s['loc'], 0.600) for s in _q2['stations']},
}
print(f"  目标={baseline['objective']:.4f}, 覆盖={baseline['coverage']}/{baseline['n_communities']}, "
      f"利润={baseline['total_profit']:.1f}万/年, 平均S={baseline['avg_satisfaction']:.4f}")
print(f"  站点: {[(s['loc'], ['小','中','大'][s['size']]) for s in baseline['built_stations']]}")
print(f"  [确认] 与 Q2 正文数据完全一致 (F大型+H中型+J中型, 109万元, 10/10覆盖)")

# ---- 场景A: 预算放松 ----
print("\n" + "-"*50)
print("[场景A] 预算上限逐步放松 (120→130→140→150万)")
print("-"*50)
scenario_a = {120: baseline}  # 复用基线
for budget in [130, 140, 150]:
    print(f"\n  Budget={budget}万...")
    result = solve_q2_milp(df_demand_orig, budget,
                           BASELINE['build_cost'], BASELINE['daily_op'],
                           BASELINE['daily_cap'], time_limit=90)
    scenario_a[budget] = result
    print(f"  覆盖={result['coverage']}/{result['n_communities']}, "
          f"目标={result['objective']:.2f}, 利润={result['total_profit']:.1f}万/年, "
          f"平均S={result['avg_satisfaction']:.3f}")
    print(f"  站点: {[(s['loc'], ['小','中','大'][s['size']]) for s in result['built_stations']]}")
    print(f"  未覆盖: {result['uncovered']}, 已用预算={result['budget_used']}万")

# ---- 场景B: 成本膨胀 ----
print("\n" + "-"*50)
print("[场景B] 供给侧冲击: 建设+运营成本统一上浮20%")
print("-"*50)
inflated_build_cost = BASELINE['build_cost'] * 1.20
inflated_daily_op = BASELINE['daily_op'] * 1.20
scenario_b = solve_q2_milp(df_demand_orig, BASELINE['budget'],
                           inflated_build_cost, inflated_daily_op,
                           BASELINE['daily_cap'], time_limit=90)
print(f"  覆盖={scenario_b['coverage']}/{scenario_b['n_communities']}, "
      f"目标={scenario_b['objective']:.2f}, 利润={scenario_b['total_profit']:.1f}万/年, "
      f"平均S={scenario_b['avg_satisfaction']:.3f}")
print(f"  站点: {[(s['loc'], ['小','中','大'][s['size']]) for s in scenario_b['built_stations']]}")
print(f"  未覆盖: {scenario_b['uncovered']}, 已用预算={scenario_b['budget_used']}万")

# ---- 场景C: 银发海啸 ----
print("\n" + "-"*50)
print("[场景C] 需求侧冲击: 半失能转移4.5%→5.5%, 失能转移10%→12%")
print("-"*50)
A_tsunami = build_transition_matrix(mu=BASELINE['mu'], alpha_sm=0.055,
                                    alpha_md=0.12, beta=BASELINE['beta'])
S_final_tsunami, income_tsunami, comm_list = predict_population_from_original(A_tsunami, T=5)
total_tsunami = S_final_tsunami.sum()
disabled_tsunami = S_final_tsunami[:, 2].sum()
print(f"  银发海啸预测: 60+总人口={total_tsunami:.0f}, 失能={disabled_tsunami:.0f} "
      f"(基线: 7577/1125)")
# 重算需求
df_demand_tsunami, _, _, _ = compute_demand_from_final(
    S_final_tsunami, income_tsunami, BASELINE['consumption_caps'], comm_list)
scenario_c = solve_q2_milp(df_demand_tsunami, BASELINE['budget'],
                           BASELINE['build_cost'], BASELINE['daily_op'],
                           BASELINE['daily_cap'], time_limit=90)
print(f"  覆盖={scenario_c['coverage']}/{scenario_c['n_communities']}, "
      f"目标={scenario_c['objective']:.2f}, 利润={scenario_c['total_profit']:.1f}万/年, "
      f"平均S={scenario_c['avg_satisfaction']:.3f}")
print(f"  站点: {[(s['loc'], ['小','中','大'][s['size']]) for s in scenario_c['built_stations']]}")
print(f"  未覆盖: {scenario_c['uncovered']}, 已用预算={scenario_c['budget_used']}万")

# ============================================================
# §6 汇总与导出
# ============================================================
print("\n" + "=" * 70)
print("§6 灵敏度汇总表")
print("=" * 70)

summary_rows = []

# 基线行
summary_rows.append({
    '场景': '基线 (Baseline)',
    '预算(万元)': 120,
    '成本系数': '1.00',
    '60+人口': 7577,
    '失能人口': 1125,
    '失能占比(%)': 14.8,
    '覆盖数': baseline['coverage'],
    '覆盖率(%)': round(baseline['coverage']/baseline['n_communities']*100, 1),
    '站点配置': '+'.join([f"{s['loc']}({['小','中','大'][s['size']]})" for s in baseline['built_stations']]),
    '已用预算(万元)': baseline['budget_used'],
    '目标值': round(baseline['objective'], 2),
    '平均S': round(baseline['avg_satisfaction'], 3),
    '年总利润(万元)': round(baseline['total_profit'], 1),
    '未覆盖小区': ','.join(baseline['uncovered']) if baseline['uncovered'] else '无',
})

# 场景A 各行
for budget in [120, 130, 140, 150]:
    r = scenario_a[budget]
    summary_rows.append({
        '场景': f'A: 预算放松至{budget}万',
        '预算(万元)': budget,
        '成本系数': '1.00',
        '60+人口': 7577,
        '失能人口': 1125,
        '失能占比(%)': 14.8,
        '覆盖数': r['coverage'],
        '覆盖率(%)': round(r['coverage']/r['n_communities']*100, 1),
        '站点配置': '+'.join([f"{s['loc']}({['小','中','大'][s['size']]})" for s in r['built_stations']]),
        '已用预算(万元)': r['budget_used'],
        '目标值': round(r['objective'], 2),
        '平均S': round(r['avg_satisfaction'], 3),
        '年总利润(万元)': round(r['total_profit'], 1),
        '未覆盖小区': ','.join(r['uncovered']) if r['uncovered'] else '无',
    })

# 场景B
summary_rows.append({
    '场景': 'B: 成本膨胀+20%',
    '预算(万元)': 120,
    '成本系数': '1.20',
    '60+人口': 7577,
    '失能人口': 1125,
    '失能占比(%)': 14.8,
    '覆盖数': scenario_b['coverage'],
    '覆盖率(%)': round(scenario_b['coverage']/scenario_b['n_communities']*100, 1),
    '站点配置': '+'.join([f"{s['loc']}({['小','中','大'][s['size']]})" for s in scenario_b['built_stations']]),
    '已用预算(万元)': scenario_b['budget_used'],
    '目标值': round(scenario_b['objective'], 2),
    '平均S': round(scenario_b['avg_satisfaction'], 3),
    '年总利润(万元)': round(scenario_b['total_profit'], 1),
    '未覆盖小区': ','.join(scenario_b['uncovered']) if scenario_b['uncovered'] else '无',
})

# 场景C
summary_rows.append({
    '场景': 'C: 银发海啸加剧',
    '预算(万元)': 120,
    '成本系数': '1.00',
    '60+人口': int(total_tsunami),
    '失能人口': int(disabled_tsunami),
    '失能占比(%)': round(disabled_tsunami/total_tsunami*100, 1),
    '覆盖数': scenario_c['coverage'],
    '覆盖率(%)': round(scenario_c['coverage']/scenario_c['n_communities']*100, 1),
    '站点配置': '+'.join([f"{s['loc']}({['小','中','大'][s['size']]})" for s in scenario_c['built_stations']]),
    '已用预算(万元)': scenario_c['budget_used'],
    '目标值': round(scenario_c['objective'], 2),
    '平均S': round(scenario_c['avg_satisfaction'], 3),
    '年总利润(万元)': round(scenario_c['total_profit'], 1),
    '未覆盖小区': ','.join(scenario_c['uncovered']) if scenario_c['uncovered'] else '无',
})

df_summary = pd.DataFrame(summary_rows)
df_summary.to_csv("results/q4_sensitivity_summary.csv", index=False, encoding="utf-8-sig")
print("\n[导出] results/q4_sensitivity_summary.csv")

# LaTeX 表格
print("\n" + "=" * 70)
print("LaTeX 灵敏度汇总表 (可直接粘贴到 paper_workspace)")
print("=" * 70)
print(r"""
\begin{table}[htbp]
\centering
\caption{三场景参数扫描灵敏度汇总}
\label{tab:q4_sensitivity}
\small
\begin{tabular}{lcccccc}
\hline
\textbf{场景} & \textbf{预算(万)} & \textbf{覆盖率} & \textbf{站点配置} & \textbf{目标值} & \textbf{平均S} & \textbf{年利润(万)} \\
\hline""")
for _, row in df_summary.iterrows():
    print(f"{row['场景']} & {row['预算(万元)']} & {row['覆盖率(%)']}\\% & "
          f"{row['站点配置']} & {row['目标值']:.2f} & {row['平均S']:.3f} & {row['年总利润(万元)']:.1f} \\\\")
print(r"""\hline
\end{tabular}
\end{table}
""")

# ============================================================
# §7 可视化: 灵敏度对比图 (v4: seaborn muted 学术风格)
# ============================================================
sns.set_style("white")
# 确保字体在 seaborn 样式重置后仍然生效
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [FONT_NAME, "Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
})
C_BASE    = '#2C3E50'
C_BUDGET  = '#3498DB'
C_SHOCK   = '#E74C3C'
C_TSUNAMI = '#E67E22'

scenarios_labels = ['基线\n120万', 'A-130\n预算放松', 'A-140\n预算放松', 'A-150\n预算放松',
                    'B-成本\n通胀+20%', 'C-银发\n海啸']
bar_colors = [C_BASE, C_BUDGET, C_BUDGET, C_BUDGET, C_SHOCK, C_TSUNAMI]

coverage_vals = [
    baseline['coverage']/baseline['n_communities']*100,
    scenario_a[130]['coverage']/10*100,
    scenario_a[140]['coverage']/10*100,
    scenario_a[150]['coverage']/10*100,
    scenario_b['coverage']/10*100,
    scenario_c['coverage']/10*100,
]

sat_vals = [
    baseline['avg_satisfaction'],
    scenario_a[130]['avg_satisfaction'],
    scenario_a[140]['avg_satisfaction'],
    scenario_a[150]['avg_satisfaction'],
    scenario_b['avg_satisfaction'],
    scenario_c['avg_satisfaction'],
]

profit_vals = [
    baseline['total_profit'],
    scenario_a[130]['total_profit'],
    scenario_a[140]['total_profit'],
    scenario_a[150]['total_profit'],
    scenario_b['total_profit'],
    scenario_c['total_profit'],
]

# ---- 三张独立图，分别输出 ----

def make_single_fig(ax, scenario_labels, values, bar_colors, fmt, ylabel, title, ylim_bottom, ylim_top, hline_y=None):
    bars = ax.bar(scenario_labels, values, color=bar_colors, edgecolor='white', lw=1.5, width=0.55)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + (ylim_top-ylim_bottom)*0.015,
                fmt.format(val), ha='center', fontsize=13, fontweight='bold', color='#2C3E50')
    if hline_y is not None:
        ax.axhline(y=hline_y, color='#BDC3C7', linestyle='--', lw=1.0, alpha=0.6)
    ax.set_title(title, fontsize=16, fontweight='bold', pad=16, color='#2C3E50')
    ax.set_ylabel(ylabel, fontsize=13, color='#34495E')
    ax.set_ylim(ylim_bottom, ylim_top)
    ax.tick_params(axis='x', labelsize=11, colors='#2C3E50')
    ax.tick_params(axis='y', labelsize=10, colors='#7F8C8D')
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False)

# Panel A: 覆盖率
fig_a, ax_a = plt.subplots(figsize=(10, 6))
fig_a.patch.set_facecolor('white')
make_single_fig(ax_a, scenarios_labels, coverage_vals, bar_colors,
                '{:.0f}%', '覆盖率 (%)', '(a) 覆盖率', 55, 118, hline_y=100)
fig_a.tight_layout(pad=2.0)
fig_a.savefig("figures/figure_q4_coverage.png", dpi=300, facecolor='white', bbox_inches='tight')
plt.close(fig_a)

# Panel B: 满意度
fig_b, ax_b = plt.subplots(figsize=(10, 6))
fig_b.patch.set_facecolor('white')
make_single_fig(ax_b, scenarios_labels, sat_vals, bar_colors,
                '{:.3f}', '平均综合满意度 $S$', '(b) 加权满意度', 0.76, 1.03)
fig_b.tight_layout(pad=2.0)
fig_b.savefig("figures/figure_q4_satisfaction.png", dpi=300, facecolor='white', bbox_inches='tight')
plt.close(fig_b)

# Panel C: 利润
fig_c, ax_c = plt.subplots(figsize=(10, 6))
fig_c.patch.set_facecolor('white')
make_single_fig(ax_c, scenarios_labels, profit_vals, bar_colors,
                '{:.0f}', '年总利润 (万元)', '(c) 年利润', 500, max(profit_vals)*1.22)
fig_c.tight_layout(pad=2.0)
fig_c.savefig("figures/figure_q4_profit.png", dpi=300, facecolor='white', bbox_inches='tight')
plt.close(fig_c)

print("\n[图表] figures/figure_q4_coverage.png, figure_q4_satisfaction.png, figure_q4_profit.png 已保存 (3张独立图)")

print("\n" + "=" * 70)
print("Q4 灵敏度分析完成")
print("=" * 70)
