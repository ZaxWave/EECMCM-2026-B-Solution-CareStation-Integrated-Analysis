"""Fix abstract in main.tex — trim to fit 1 page."""
with open('../main.tex', 'r', encoding='utf-8') as f:
    content = f.read()

# Find second vspace{0.2cm} occurrence (the one before actual abstract text)
needle = 'vspace{0.2cm}'
v1 = content.find(needle)
v2 = content.find(needle, v1 + 1)

# After the second vspace line, skip past \n\n to get to the text
after_vline = content.find('\n', v2) + 1
after_blank = content.find('\n', after_vline) + 1
text_start = after_blank

# End: blank line before \textbf{关键词：}
kw = content.find(r'\textbf{关键词：}', text_start)
text_end = content.rfind('\n\n', text_start, kw)

# Build replacement (using raw-like approach: double the backslashes for LaTeX commands)
new_body = (
    "面对人口老龄化加速背景下社区养老服务\"建在哪、建多大、收多少钱\"的全链条决策难题，"
    "本文以某城市10个连片小区为实证场景，构建四阶段递进求解框架，"
    "在120万元总预算与1000m服务半径硬约束下完成从需求预测到方案落地的闭环求解。\n"
    "\n"
    "\\textbf{问题1——人口与服务需求预测}：构造增生型3状态Markov转移矩阵，"
    "以7\\%年注入率与5\\%死亡率刻画系统开放性；同步建立Leslie矩阵双模型三角校验，"
    "两范式5年60+人口预测偏差仅1.7\\%。核心发现：失能老人因棘轮效应从625人飙升至1,125人（+80.3\\%），"
    "失能率从9.1\\%攀升至14.8\\%；半失能群体充当自理向失能的加速通道。"
    "消费约束预诊断表明失能老人全10小区触发等比例削减，缺口23.9\\%--49.1\\%。\n"
    "\n"
    "\\textbf{问题2——选址与规模优化}：将Church\\&ReVelle经典MCLP扩展为MILP-MCLP-ES模型，"
    "引入Big-M与McCormick包络等价线性化，CBC分支定界求解。"
    "最优方案F大型+H中型+J中型，成本109万元，10/10全覆盖，加权满意度0.850，年总利润1,097.7万元。"
    "三站平均利用率94.3\\%，确定解目标值较非确定解提升24\\%。\n"
    "\n"
    "\\textbf{问题3——服务定价与政府补贴}：构建词典序MILP定价模型，"
    "优先最大化$S_3$、次优先弱激励营收最大化，利润率$\\le8\\%$红线。"
    "全6项服务$S_3=1.000$平价，仅上门护理从30元降至12.64元吸收F站紧约束。"
    "三层交叉补贴使紧急救助年净支出47.42万元由营利利润完全吸收，交叉补贴率仅14.3\\%。\n"
    "\n"
    "\\textbf{问题4——灵敏度与鲁棒性}：三场景6组MILP重求解。"
    "场景A预算扩张满意度单调递增边际递减，130万为甜点；"
    "场景B成本通胀20\\%击穿全覆盖防线；"
    "场景C银发海啸下系统从3站跃迁至4站，维持90\\%覆盖率。"
    "各维度韧性系数均>0.80，系统鲁棒性为强。"
    "框架可迁移至分级诊疗、冷链前置仓等公共设施优化场景。"
)

old_body = content[text_start:text_end]
print(f"Old: {len(old_body)} chars")
print(f"New: {len(new_body)} chars")
print(f"Saved: {len(old_body) - len(new_body)} chars")

assert len(new_body) < len(old_body), "New body is NOT shorter!"

content = content[:text_start] + new_body + content[text_end:]
with open('../main.tex', 'w', encoding='utf-8') as f:
    f.write(content)
print("Abstract replaced successfully.")
