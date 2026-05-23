# EECMCM 2026 B题 — 嵌入式社区养老服务站的建设与优化问题

> 竞赛：中国电机工程学会杯 (电工杯) · 2026 · B题  
> 仓库：[EECMCM-2026-B-Solution-CareStation-Integrated-Analysis](https://github.com/ZaxWave/EECMCM-2026-B-Solution-CareStation-Integrated-Analysis)

## 项目结构

```
EECMCM2026/
├── main.tex                          # 论文主文件 (xelatex 编译)
├── main.pdf                          # 编译后论文
├── fix_abstract.py                   # 摘要修正脚本
├── solve_q1.py                       # 问题1：需求预测 (灰色GM(1,1) + 多元回归)
├── solve_q2.py                       # 问题2：选址优化 (MCLP + 网络流)
├── solve_q3.py                       # 问题3：定价策略 (双层规划)
├── solve_q4_sensitivity.py           # 问题4：鲁棒性与灵敏度分析
├── generate_extra_figures.py         # 论文图表生成
├── generate_q4_combined.py           # 问题4组合图生成
├── data/                             # B题赛题数据 (本文 + 5个附件)
│   ├── B题：嵌入式社区养老服务站的建设与优化问题.pdf
│   ├── 附件1：小区基础数据.xlsx
│   ├── 附件2：服务需求数据.xlsx
│   ├── 附件3：服务站建设与运营成本.xlsx
│   ├── 附件4：小区间距离矩阵.xlsx
│   └── 附件5：满意度评分规则.xlsx
├── figures/                          # 论文插图 (PNG)
├── results/                          # 模型输出数据 (CSV/JSON)
├── paper_workspace/                  # 论文分章节 tex 源文件
│   ├── section_1_problem_background.tex
│   ├── section_2_data_preprocessing.tex
│   ├── section_3_model_formulation.tex
│   ├── section_4_assumptions.tex
│   ├── section_5_1_q1_results.tex
│   ├── section_5_2_q2_results.tex
│   ├── section_5_3_q3_results.tex
│   ├── section_5_4_q4_robustness.tex
│   ├── section_6_model_evaluation.tex
│   └── section_7_engineering_recommendations.tex
├── references/                       # 参考文献 PDF
│   ├── 004799B.pdf
│   └── example.pdf
├── docs/
│   └── 论文规范                       # 竞赛论文格式规范
├── utils/
│   └── fix_matplotlib_font.py        # matplotlib 中文字体修复
├── state/
│   └── decision_log.json             # 建模决策日志
└── .gitignore
```

## 快速开始

### 编译论文

```bash
xelatex main.tex
xelatex main.tex
xelatex main.tex
```

### 运行求解器

```bash
# 安装依赖
pip install numpy scipy pandas matplotlib openpyxl

# 按顺序运行
python solve_q1.py
python solve_q2.py
python solve_q3.py
python solve_q4_sensitivity.py
```

## 模型方法概览

| 问题 | 方法 | 核心内容 |
|------|------|----------|
| Q1 需求预测 | 灰色GM(1,1)、多元回归 | 老年人口与服务需求时空分布预测 |
| Q2 选址优化 | MCLP、设施选址网络流 | 服务站最优选址与容量分配 |
| Q3 定价策略 | 双层规划、盈亏平衡 | 差异化服务定价与交叉补贴 |
| Q4 鲁棒性 | 灵敏度分析、情景分析 | 参数扰动下的方案稳定性验证 |

## 竞赛要求

- 论文格式参见 `docs/论文规范`
- 参赛论文：`main.pdf`
- 支撑材料：源码、数据及结果文件（压缩为 ZIP/RAR，≤20MB）
