# EECMCM 2026 B题 — 嵌入式社区养老服务站的建设与优化问题

> 竞赛：中国电机工程学会杯 (电工杯) · 2026 · B题  
> 参赛编号：014508  
> 仓库：[EECMCM-2026-B-Solution-CareStation-Integrated-Analysis](https://github.com/ZaxWave/EECMCM-2026-B-Solution-CareStation-Integrated-Analysis)

## 项目结构

```
EECMCM2026/
├── paper_workspace/                  # LaTeX 论文源文件 + 提交产物
│   ├── main_backup.tex               # 论文主文件 (xelatex 三编)
│   ├── 014508B.pdf                   # 参赛论文 (终稿, ≤20MB)
│   ├── 014508Bshuju.zip              # 支撑材料 (代码+数据+结果+图表+LaTeX)
│   ├── section_1_problem_background.tex
│   ├── section_2_data_preprocessing.tex
│   ├── section_3_model_formulation.tex
│   ├── section_4_assumptions.tex
│   ├── section_5_1_q1_results.tex
│   ├── section_5_2_q2_results.tex
│   ├── section_5_3_q3_results.tex
│   ├── section_5_4_q4_robustness.tex
│   ├── section_6_model_evaluation.tex
│   ├── section_7_engineering_recommendations.tex
│   ├── appendix_code.tex             # 附录 (代码+推导+补充表)
│   └── figures/                      # 论文插图 (14 张 PNG, 300dpi)
├── code/                             # 核心求解器与图表生成
│   ├── config.py                     # 共享配置 (路径/调色板/字体)
│   ├── solve_q1.py                   # Q1: Markov链人口预测 + Leslie互证
│   ├── solve_q2.py                   # Q2: MILP-MCLP-ES 选址-规模优化
│   ├── solve_q3.py                   # Q3: 词典序MILP 定价与补贴优化
│   ├── solve_q4_sensitivity.py       # Q4: 三场景灵敏度与鲁棒性检验
│   ├── regenerate_all_figures.py     # 论文全部图表统一生成 (总控)
│   ├── generate_extra_figures.py     # 韧性热力图 + 雷达图
│   └── generate_q4_combined.py       # Q4 三场景组合图
├── utils/                            # 工具脚本
│   ├── fix_matplotlib_font.py        # matplotlib 中文字体修复
│   ├── fix_abstract.py               # 摘要篇幅压缩
│   └── _verify_font.png              # 字体验证截图
├── data/                             # B题赛题数据 (5附件 + 赛题PDF)
├── results/                          # 模型中间输出 (CSV/JSON, Q1→Q4)
├── references/                       # 参考文献与外部资料
├── docs/                             # 论文规范
├── state/                            # 建模决策日志
└── README.md
```

## 模型方法概览

| 问题 | 方法 | 核心内容 |
|------|------|----------|
| Q1 人口预测 | 增生型Markov链 + Leslie矩阵互证 | 3状态转移矩阵, 5年递推, 消费约束需求削减 |
| Q2 选址优化 | MILP-MCLP-ES (混合整数线性规划) | Big-M分段满意度线性化, McCormick包络, CBC分支定界 |
| Q3 定价策略 | 词典序MILP + Ramsey-Boiteux定价 | S3最大化优先, ε=10⁻⁴营收激励, 三层交叉补贴 |
| Q4 鲁棒性 | 三场景独立MILP重求解 | 韧性系数矩阵 ρ=1−\|ΔX/X\|, 三级分级标准 |

## 快速开始

### 编译论文

```bash
cd paper_workspace
xelatex main_backup.tex
xelatex main_backup.tex
xelatex main_backup.tex
# 输出: main_backup.pdf (73页, 正文≤25页)
```

### 运行求解器

```bash
# 安装依赖
pip install numpy scipy pandas matplotlib openpyxl pulp

# 按 Q1→Q2→Q3→Q4 顺序执行 (数据流串行依赖)
python code/solve_q1.py
python code/solve_q2.py
python code/solve_q3.py
python code/solve_q4_sensitivity.py

# 重新生成全部论文图表
python code/regenerate_all_figures.py
python code/generate_extra_figures.py
python code/generate_q4_combined.py
```

## 提交文件

| 文件 | 说明 | 大小限制 |
|------|------|----------|
| `paper_workspace/014508B.pdf` | 参赛论文 | ≤20MB |
| `paper_workspace/014508Bshuju.zip` | 支撑材料 (代码+数据+结果+图表+LaTeX) | ≤20MB |

## 竞赛规范

- 论文格式参见 `docs/论文规范` (2024年修订稿, 10条规则)
- 封面页: 参赛编号 + 论文题目 (毋自拟)
- 正文 ≤ 25页, 附录不限
- 参考文献按正文引用次序列出
