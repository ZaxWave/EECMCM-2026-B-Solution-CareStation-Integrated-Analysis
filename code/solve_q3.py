"""
solve_q3.py — Q3 服务定价与政府补贴 MILP 优化 (电工杯 B题 2026)
================================================================
Stage 05 | 求解器: PuLP + CBC (含Gurobi/Mosek备用接口) | Big-M S3线性化
关键策略:
  1. 固化 Q2 选址-分配决策 (y*, x*) → 变量降维
  2. S3 四段 Big-M 离散化 (平价/微溢价/中溢价/高溢价)
  3. 利润率 ≤ 8% 硬约束 + 每日补贴上限
  4. 紧急救助免费 (p=0, 无补贴), 仅核算成本 → 交叉补贴机制
"""

import numpy as np
import pandas as pd
import pulp
import os, warnings
warnings.filterwarnings('ignore')

# ============================================================
# §1 数据挂载：固化 Q2 选址-分配结果
# ============================================================
df_pop = pd.read_csv("../results/q1_final_population.csv")
communities = df_pop["小区"].tolist()
n_comm = len(communities)

df_demand = pd.read_csv("../results/q1_service_demand.csv")
services = list(df_demand["服务项目"].unique())
n_svc = len(services)

# 固化 Q2 选址决策 (randomSeed=42 确定解)
# Q2 结果: F(大型, idx=5), H(中型, idx=7), J(中型, idx=9)
STATION_LOCS = {'F': 5, 'H': 7, 'J': 9}
STATION_SIZES = {'F': 2, 'H': 1, 'J': 1}  # 2=大, 1=中

# Q2 服务分配: {需求小区 → 服务站} (全覆盖 10/10)
ASSIGNMENTS = {
    'A': 'J', 'B': 'H', 'C': 'F', 'D': 'J', 'E': 'H',
    'F': 'F', 'G': 'F', 'H': 'H', 'I': 'F', 'J': 'J'
}

size_label = ['小型', '中型', '大型']
build_cost_arr = np.array([18, 32, 45], dtype=float)
daily_op_arr = np.array([2000, 3200, 4400], dtype=float)
daily_cap_arr = np.array([1000, 2000, 3000], dtype=float)
SUBSIDY_CAP = {0: 1000, 1: 1800, 2: 2600}  # 元/日, 按规模

MONTHLY = 30
ANNUAL_DAYS = 360

# ============================================================
# §2 提取每站点服务需求与财务基线
# ============================================================
# 服务营收/成本基线 (附件2)
revenue_base = {'助餐': 10, '日间照料': 20, '上门护理': 30, '康复理疗': 28, '助浴': 25, '紧急救助': 0}
cost_per_svc = {'助餐': 8, '日间照料': 16, '上门护理': 24, '康复理疗': 23, '助浴': 20, '紧急救助': 8}

# 按站点聚合需求
station_demand = {}  # station_demand[station_name][svc] = monthly count
for st_name in ['F', 'H', 'J']:
    station_demand[st_name] = {}
    for svc in services:
        total = 0
        for comm, assigned_st in ASSIGNMENTS.items():
            if assigned_st == st_name:
                mask = (df_demand["小区"] == comm) & (df_demand["服务项目"] == svc)
                total += df_demand[mask]["实际月需求(次)"].sum()
        station_demand[st_name][svc] = total

# 全系统各服务总需求 (仅已覆盖小区)
total_demand_by_svc = {}
for svc in services:
    total_demand_by_svc[svc] = sum(
        station_demand[st][svc] for st in ['F', 'H', 'J']
    )

print("=" * 60)
print("Q3 定价与补贴 MILP 优化器")
print("=" * 60)
print(f"\n[固化] Q2 选址: F(大型), H(中型), J(中型)")
print(f"[固化] 覆盖小区: {list(ASSIGNMENTS.keys())} (10/10)")
print(f"[固化] 未覆盖: 无 (全覆盖)")

# 基线财务 (Q2 定价, 利润率校验)
print("\n[基线] Q2 当前定价下的站点利润率:")
for st_name in ['F', 'H', 'J']:
    sz = STATION_SIZES[st_name]
    ann_rev = sum(station_demand[st_name][svc] * revenue_base[svc] * 12 for svc in services)
    ann_cost = sum(station_demand[st_name][svc] * cost_per_svc[svc] * 12 for svc in services)
    # 补贴: 非紧急救助 × 2元/次, 受日上限约束
    daily_non_em = sum(station_demand[st_name][svc] for svc in services if svc != '紧急救助') / MONTHLY
    daily_sub_raw = daily_non_em * 2
    daily_sub_actual = min(daily_sub_raw, SUBSIDY_CAP[sz])
    ann_sub = daily_sub_actual * ANNUAL_DAYS
    ann_op = daily_op_arr[sz] * ANNUAL_DAYS
    ann_dep = build_cost_arr[sz] * 10000 / 20
    total_cost = ann_op + ann_dep + ann_cost
    profit = ann_rev + ann_sub - total_cost
    margin = profit / total_cost * 100
    print(f"  {st_name}({size_label[sz]}): 营收={ann_rev/10000:.1f}万, "
          f"补贴={ann_sub/10000:.1f}万(上限{SUBSIDY_CAP[sz]}元/日), "
          f"利润={profit/10000:.1f}万, 利润率={margin:.1f}%")

print(f"\n[需求] 全系统各服务月需求 (仅已覆盖8小区):")
for svc in services:
    print(f"  {svc}: {total_demand_by_svc[svc]:.0f} 次/月")

# ============================================================
# §3 MILP 模型: 定价优化
# ============================================================
prob = pulp.LpProblem("Q3_Pricing_Subsidy", pulp.LpMaximize)

# ---- 3a. 决策变量 ----
# 各服务定价 p_s (连续)
p = pulp.LpVariable.dicts("p", services, lowBound=0)

# S3 分段指示变量 (4段, 6服务 = 24 binaries)
S3_lo_ratio = [0.0, 1.001, 1.101, 1.201]  # 加 epsilon 处理严格不等式
S3_hi_ratio = [1.0, 1.1, 1.2, 2.0]         # 高溢价上界设 2×基准价
S3_val = [1.00, 0.90, 0.75, 0.60]

delta_s3 = {}
for svc in services:
    if svc == '紧急救助':
        continue  # 紧急救助免费, S3 固定=1.0
    for ell in range(4):
        delta_s3[(svc, ell)] = pulp.LpVariable(f"d3_{svc}_{ell}", cat=pulp.LpBinary)

# S3 满意度 (连续, 每服务)
s3 = pulp.LpVariable.dicts("s3", services, lowBound=0.6, upBound=1.0)

# 紧急救助: 固定 p=0, S3=1.0
# (在约束中单独处理)

# ---- 3b. S3 价格满意度 Big-M 线性化 ----
BIG_M_PRICE = 500  # 足够大 (基准价最高30, 2×基准=60)

for svc in services:
    if svc == '紧急救助':
        prob += p[svc] == 0
        prob += s3[svc] == 1.0
        continue

    base = revenue_base[svc]

    # 恰好选一段
    prob += pulp.lpSum([delta_s3[(svc, ell)] for ell in range(4)]) == 1

    for ell in range(4):
        lo = base * S3_lo_ratio[ell]
        hi = base * S3_hi_ratio[ell]
        # 下界: p ≥ lo - M·(1-δ)
        prob += p[svc] >= lo - BIG_M_PRICE * (1 - delta_s3[(svc, ell)])
        # 上界: p ≤ hi + M·(1-δ)
        prob += p[svc] <= hi + BIG_M_PRICE * (1 - delta_s3[(svc, ell)])

    # S3 = Σ val[ell] · delta[ell]
    prob += s3[svc] == pulp.lpSum([S3_val[ell] * delta_s3[(svc, ell)] for ell in range(4)])

    # 价格非负
    prob += p[svc] >= 0

# ---- 3c. 利润率 ≤ 8% 约束 (每站点) ----
for st_name in ['F', 'H', 'J']:
    sz = STATION_SIZES[st_name]

    # 年度营收 = Σ demand × p_s × 12 (紧急救助 p=0, 营收=0)
    ann_rev_expr = pulp.lpSum([
        station_demand[st_name][svc] * p[svc] * 12
        for svc in services
    ])

    # 年度补贴: 非紧急救助 × min(2元/次, 受日上限约束)
    # 日补贴 = min(日非紧急需求×2, cap)
    daily_non_em_demand = sum(
        station_demand[st_name][svc] for svc in services if svc != '紧急救助'
    ) / MONTHLY
    subsidy_pool_annual = min(daily_non_em_demand * 2, SUBSIDY_CAP[sz]) * ANNUAL_DAYS

    # 年度直接成本 (与价格无关, 需求固定)
    ann_direct_cost = sum(
        station_demand[st_name][svc] * cost_per_svc[svc] * 12
        for svc in services
    )

    # 年度固定成本
    ann_op = daily_op_arr[sz] * ANNUAL_DAYS
    ann_dep = build_cost_arr[sz] * 10000 / 20

    total_cost_base = ann_op + ann_dep + ann_direct_cost

    # 利润率约束: (营收 + 补贴 - 总成本) / 总成本 ≤ 0.08
    # → 营收 + 补贴 ≤ 1.08 × 总成本
    # → Σ demand·p_s·12 ≤ 1.08 × total_cost_base - subsidy_pool_annual
    max_allowed_revenue = 1.08 * total_cost_base - subsidy_pool_annual
    prob += ann_rev_expr <= max_allowed_revenue, f"MarginCap_{st_name}"

    # 非负利润 (可持续性)
    prob += ann_rev_expr + subsidy_pool_annual >= total_cost_base, f"NonNegProfit_{st_name}"

    print(f"\n[约束] {st_name}: 总成本基线={total_cost_base/10000:.1f}万, "
          f"补贴池={subsidy_pool_annual/10000:.1f}万, "
          f"营收上限={max_allowed_revenue/10000:.1f}万")

# ---- 3d. 目标函数: 词典序 (主: S3最大化, 次: 营收最大化) ----
# 综合满意度 S = 0.2·S1 + 0.3·S2 + 0.5·S3
# S1, S2 已由 Q2 固定, 故等价于最大化 Σ demand_s × S3_s
# 次要目标: 在同等 S3 水平下, 偏好更高营收 (保证定价不低于必要水平)
primary_obj = pulp.lpSum([
    total_demand_by_svc[svc] * s3[svc] * 0.5
    for svc in services
])
# 次要目标: 营收项 (权重极小, 仅用于打破 S3 平坦区域的对称性)
secondary_obj = 0.0001 * pulp.lpSum([
    total_demand_by_svc[svc] * p[svc] * 12
    for svc in services
])
prob += primary_obj + secondary_obj

print(f"\n[MILP] 变量={len(prob.variables())}, 约束={len(prob.constraints)}")

# ============================================================
# §4 求解 (含三级求解器级联备用)
# ============================================================
# Q3 模型极轻量 (<40变量), CBC默认求解即秒级收敛
# 备用接口预置以应对未来扩展至区级规划 (n>100) 的大规模场景
try:
    prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=60))
except Exception:
    print("[Solver] CBC失败, 尝试Gurobi...")
    try:
        import gurobipy
        prob.solve(pulp.GUROBI(msg=False, timeLimit=60))
    except (ImportError, Exception):
        print("[Solver] Gurobi不可用. 请检查授权或联系管理员算号.")
        raise
print(f"状态: {pulp.LpStatus[prob.status]}, 目标={pulp.value(prob.objective):.4f}")

# ============================================================
# §5 结果提取与导出
# ============================================================
print("\n" + "=" * 60)
print("§5 Q3 最优定价方案")
print("=" * 60)

results = []
for svc in services:
    p_opt = pulp.value(p[svc]) if svc != '紧急救助' else 0.0
    s3_opt = pulp.value(s3[svc])
    base = revenue_base[svc]
    ratio = p_opt / base if base > 0 else 0.0

    segment_name = ''
    if svc == '紧急救助':
        segment_name = '公益免费'
    elif ratio <= 1.0:
        segment_name = '平价'
    elif ratio <= 1.1:
        segment_name = '微溢价'
    elif ratio <= 1.2:
        segment_name = '中溢价'
    else:
        segment_name = '高溢价'

    row = {
        '服务项目': svc,
        '基准价(元)': base,
        '最优定价(元)': round(p_opt, 2),
        '溢价率(%)': round((ratio - 1) * 100, 1) if base > 0 else 0,
        '价格区间': segment_name,
        'S3(价格满意度)': round(s3_opt, 3),
        '月需求(次)': round(total_demand_by_svc[svc], 0),
    }
    results.append(row)
    print(f"  {svc}: 基准{base}元 → 最优{row['最优定价(元)']}元 "
          f"({row['价格区间']}, S3={s3_opt:.3f}), 月需求={total_demand_by_svc[svc]:.0f}次")

# ---- 站点利润核算 ----
print(f"\n{'='*60}")
print("§5.1 最优定价下的站点运营指标")
print(f"{'='*60}")

profit_rows = []
for st_name in ['F', 'H', 'J']:
    sz = STATION_SIZES[st_name]
    ann_rev = sum(station_demand[st_name][svc] * pulp.value(p[svc]) * 12 for svc in services)
    ann_direct = sum(station_demand[st_name][svc] * cost_per_svc[svc] * 12 for svc in services)
    daily_non_em = sum(station_demand[st_name][svc] for svc in services if svc != '紧急救助') / MONTHLY
    ann_sub = min(daily_non_em * 2, SUBSIDY_CAP[sz]) * ANNUAL_DAYS
    ann_op = daily_op_arr[sz] * ANNUAL_DAYS
    ann_dep = build_cost_arr[sz] * 10000 / 20
    total_cost = ann_op + ann_dep + ann_direct
    profit = ann_rev + ann_sub - total_cost
    margin = profit / total_cost * 100

    # 计算加权 S (S1/S2 来自 Q2)
    # Q2: S1 per assignment, S2 per station
    # 用 Q2 的值做固定输入
    s1_map = {'A': 0.900, 'B': 0.900, 'C': 0.600, 'D': 0.900, 'E': 0.600,
              'F': 1.000, 'G': 0.750, 'H': 1.000, 'I': 0.600, 'J': 1.000}
    s2_map = {'F': 0.600, 'H': 0.600, 'J': 0.600}

    total_weighted_s = 0
    total_demand_count = 0
    for comm, assigned_st in ASSIGNMENTS.items():
        if assigned_st == st_name:
            for svc in services:
                d = df_demand[(df_demand["小区"] == comm) & (df_demand["服务项目"] == svc)]["实际月需求(次)"].sum()
                s_val = 0.2 * s1_map[comm] + 0.3 * s2_map[st_name] + 0.5 * pulp.value(s3[svc])
                total_weighted_s += d * s_val
                total_demand_count += d

    avg_s = total_weighted_s / total_demand_count if total_demand_count > 0 else 0

    profit_rows.append({
        '站点': st_name,
        '规模': size_label[sz],
        '年营收(万元)': round(ann_rev / 10000, 2),
        '年补贴(万元)': round(ann_sub / 10000, 2),
        '年总成本(万元)': round(total_cost / 10000, 2),
        '年利润(万元)': round(profit / 10000, 2),
        '利润率(%)': round(margin, 1),
        '加权综合满意度': round(avg_s, 3),
    })

    print(f"  {st_name}({size_label[sz]}): 营收={ann_rev/10000:.1f}万, "
          f"补贴={ann_sub/10000:.1f}万, 成本={total_cost/10000:.1f}万, "
          f"利润={profit/10000:.1f}万, 利润率={margin:.1f}%, 加权S={avg_s:.3f}")

# ---- 导出 ----
df_pricing = pd.DataFrame(results)
df_pricing.to_csv("../results/q3_optimal_pricing.csv", index=False, encoding="utf-8-sig")
print(f"\n[导出] results/q3_optimal_pricing.csv")

df_profit = pd.DataFrame(profit_rows)
df_profit.to_csv("../results/q3_station_profit.csv", index=False, encoding="utf-8-sig")
print(f"[导出] results/q3_station_profit.csv")

# ---- 交叉补贴分析 ----
print(f"\n{'='*60}")
print("§5.2 交叉补贴机制分析")
print(f"{'='*60}")
for st_name in ['F', 'H', 'J']:
    emergency_demand = station_demand[st_name]['紧急救助']
    emergency_cost_annual = emergency_demand * 8 * 12  # 紧急救助无营收、无补贴
    print(f"  {st_name}: 紧急救助月需求={emergency_demand:.0f}次, "
          f"年净支出={emergency_cost_annual/10000:.2f}万 (由营利性服务交叉补贴)")

# 各站点有效补贴率
print(f"\n  有效补贴率 (受日上限约束):")
for st_name in ['F', 'H', 'J']:
    sz = STATION_SIZES[st_name]
    daily_non_em = sum(station_demand[st_name][svc] for svc in services if svc != '紧急救助') / MONTHLY
    raw_sub = daily_non_em * 2
    actual_sub = min(raw_sub, SUBSIDY_CAP[sz])
    effective_rate = actual_sub / daily_non_em if daily_non_em > 0 else 0
    print(f"    {st_name}({size_label[sz]}): 理论{raw_sub:.0f}元/日 → "
          f"实际{actual_sub:.0f}元/日 (上限{SUBSIDY_CAP[sz]}), "
          f"有效补贴率={effective_rate:.2f}元/次")

print("\nQ3 完成")
