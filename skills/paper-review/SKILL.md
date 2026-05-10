---
name: paper-review
description: 严格审查论文。强制溯源、禁止猜测/记忆/关键词检索；按 /paper 标准 + A–J 全维度 + 新增 K（现代物理学审查 M1–M9 内嵌）+ L（系统性不一致 / 上下文断层）+ M（数学物理怀疑式反复 3-pass）逐项审查；硬性零问题收敛闭环；收敛后强制以隔离上下文（Agent worktree）调用 user-level modern-physics-review 做独立二次终验，发现新问题回灌重启。
disable-model-invocation: false
argument-hint: "<file_path> [--max-iter N] [--no-fix] [--skip-final-mpr] [--field <name>] — 指定论文文件 (.tex/.md)，可选最大迭代轮数 / 只审不改 / 跳过最终 modern-physics-review 隔离终验 / 显式 field"
---

> **v3 — integrates host-level `modern-physics-review` (M1–M9) into in-process review
> as dimension K, adds dimension L (systemic inconsistency / context discontinuity)
> and dimension M (mathematical / physical adversarial 3-pass), formalizes the
> zero-issue convergence loop, and adds an isolated-context modern-physics-review
> final verification stage that runs the user-level skill in a sub-agent worktree.**
> When this plugin is loaded, references to "/paper" mean the sibling skill
> `/sci-paper:paper`. The grep targets and review dimensions are field-agnostic
> and worth keeping as-is.

## 论文严格审查 — 执行规范（v3）

当用户调用 `/paper-review <file>` 时，按本规范对论文进行**强制溯源式**审查。
本 skill 不是"快速 lint"，是**审查 + 修复迭代器 + 隔离上下文终验器**：
- 在 paper-review 进程内合并并执行 modern-physics-review 的全部物理审查维度（§2.K）。
- 用户的程度词"完全没有任何遗留问题 / 零问题收敛"被落实为 §4.3 硬循环 + §4.4 隔离上下文独立二次验证；只有两者都通过才算完。

写作标准（含 anti-AI-isms 硬规则）由 `/paper` 提供，本 skill 强制依赖。

> **风格约束 (附加，仅当 `style-profile/<field>/style_dossier.md` 存在时启用):**
> 解析 `style-profile/` 下的 field 子目录：恰好 1 个 → 自动选；多个 → 要求
> 调用方传入 `--field <name>`；0 个 → 跳过此条不阻塞审查。
> 选定 field 后，Read `style-profile/<field>/style_dossier.md` 一次，将其
> 作为"正向"风格基线注入审查上下文。审查时除现有 anti-AI-isms 黑名单外，
> 还要以 dossier 中给出的 corpus 实际惯用词、句长分布、过渡词清单作为
> "应当像这样写"的对照标准。当前默认 field = `wgl`。

---

## 0. 顶层禁令（违反即审查无效）

> **以下行为绝对禁止；违反即等于没审：**

1. **禁止使用记忆 / 缓存 / 历史对话作为事实依据。**
   每个数字、公式、引用、时间、章节内容都必须**当轮重新打开源文件读取**。
   "印象中""上次说过""我记得""我相信"都不算证据。

2. **禁止使用关键词 grep 作为唯一证据。**
   grep 只能用来定位行号；定位后必须 Read 上下文（前后 20 行起步）确认语义。
   "grep 没找到 → 不存在"是 false negative — 用其他拼写、别名、字符替换重试，必要时全文 Read。

3. **禁止猜测、推断、外推。**
   - 不知道源 → 写"NEEDS SOURCE"，不写"应该是 X"。
   - 数字对不上 → 写"INCONSISTENT (paper says X, source says Y)"，不写"X 大致对应 Y"。
   - 引用不确定真伪 → 标 `[NEEDS VERIFICATION]`，不写"可能是 Smith+2020"。

4. **数据溯源强制链：**
   论文里每个数字必须能回溯到 (a) 一个具体 CSV / npz / 脚本输出，或 (b) 一个具体 DOI / arXiv ID 的具体 Table / Figure / 公式编号，或 (c) 同论文内一个标了号的公式经一行算术得出。三者都不行就是**未溯源**，写入 🔴 必改清单。

5. **图表强制核对：**
   每个 figure 的实际 PDF / PNG 内容必须 **Read（图像）确认** vs caption 描述一致；
   每个 table 的数字必须与生成脚本 / 上游 CSV 对位 cell-by-cell；
   表内数字与正文叙述的同名数字必须 byte-for-byte 一致。

6. **物理优先于文字、格式、风格。**
   当物理正确性（量纲 / 对称性 / 守恒律 / 渐近极限 / 统计假设）与表达方式冲突时，**物理胜**。
   **严禁**用"添加 disclaimer / 软化表述 / 改写为 schematic 不标注"绕过物理错误；必须改公式、改数值或改假设到正确。
   schematic 公式必须显式标 `(schematic, illustrative)`，否则视为 🔴。

7. **怀疑式审查（adversarial mandatory）。**
   对每一个数学推导块、每一个物理推导链、每一个数值结果，**必须以"这里有问题"的预设进行至少 3 次独立 pass**（详§2.M）：
   - Pass-1：量纲 + 代数 + 边界
   - Pass-2：对手 reviewer 视角（"这是 WRONG；列出 3 条最致命的反驳"）
   - Pass-3：不变量（守恒律 / 对称性 / 渐近极限 / 统计假设）审查

   三 pass 必须**全独立**（不允许后一 pass 引用前一 pass 的"OK"结论作为证据）。任一 pass 命中 → 修复后**重跑全部 3 pass**，直到三连 0 命中才允许结案。

8. **零问题收敛是唯一合法终止条件。**
   合法终止 = §4.3 进程内收敛（0 🔴 / 0 🟡 / 0 LaTeX error / 数字溯源全绿 / AI-isms 全清 / 3-pass 三连胜）
   **AND** §4.4 隔离上下文终验通过（独立子代理 0 🔴 / 0 🟡）。
   "基本干净 / 剩下都是 minor / 看起来差不多了 / 关键问题都修了 / 没时间做最后一轮"**一律视为未收敛**。

---

## 1. 第一阶段：准备（必做，不可跳过）

1. **读 sibling skill `paper/SKILL.md`** — 内化写作标准，**特别是 Anti-AI-isms 节**。
2. **解析 field 并读 `style-profile/<field>/style_dossier.md`（若存在）** — 单 field 时自动选；多 field 时要求 `--field`；把 corpus 风格基线纳入审查标准。
3. **从头到尾 Read 论文全文**（不抽样、不关键词跳读）。超过 2000 行用 offset/limit 分块读完，**全部读过为止**。
4. **读取 `references.bib`** 以备后续逐条核对。
5. **生成"数字溯源清单"**：从论文里抽出所有数值（abstract / table / figure caption / 正文），列成待溯源 list。每条标记：值、出现位置、声称的来源、待核对状态。
6. **生成"图表清单"**：每个 `\includegraphics` / `\begin{table}` / `\begin{figure}` 的：图文件路径、caption 关键声明、引用的源脚本（grep `make_figures.py` / 项目内 figure 生成脚本）。
7. **生成"公式清单"**（新增，与§2.K 对齐）：每个 displayed equation（`\begin{equation}` / `\[...\]` / `align` / `eqnarray`）的左右端量纲、涉及的物理量定义、相关的数值常数（如 `σ_T`, `m_e c²`, `k_B`, `G`, `Σ_crit`）。本清单是§2.K 物理审查的索引。
8. **执行编译基线**（新增）：`pdflatex × 2 + bibtex + pdflatex × 2` 完整链；记录 0/N undef refs / multiply-defined labels / overfull hboxes / missing-number warnings。此基线作为§2.K8 + §4.3 收敛判据的对照。
9. **读取 CLAUDE.md（项目根 + 用户全局）+ memory/MEMORY.md** 仅用于"找到源文件路径"，**不用于核对内容**（核对走源文件本身）。
10. 列出**接口对齐清单**：所有论文里的物理量符号 → 代码里的变量名 → 数据列名。三者必须 1:1 映射。

---

## 2. 第二阶段：逐维度审查

### A. 数学审查

- [ ] **维度一致性**：每个公式的量纲（左右单位一致），含各因子。
- [ ] **符号定义完整性**：每个符号首次出现是否定义？文末附录是否漏定义？
- [ ] **符号一致性**：同一物理量全文同符号；不同物理量不复用符号；下标含义全文统一。
- [ ] **推导每一步可重现**：把关键推导手算或用 sympy 复跑（必要时写 1-shot 脚本验证），不接受"显然""容易看出"。
- [ ] **数学计算过程**：所有数值算例必须当轮重算，不接受"跟之前一致就行"。
- [ ] **近似声明**：每处近似明确说明被忽略量 + 量级估计 + 何时失效。
- [ ] **边界 / 极限行为**：相关极限是否物理合理？
- [ ] **符号排版**：`\mathrm{}` 给算子/常量；变量斜体；矢量/张量统一约定。
- [ ] **方程编号 + 交叉引用**：所有 `\eqref{}` 编号实际存在；新加的方程有 label；删除的方程的 label 没残留 reference。

### B. 物理审查

- [ ] **物理图像**：核心物理量定义与描述准确。
- [ ] **物理推导**：所有"由…得到…"的链式推理必须每步物理意义清楚（不只是数学正确）。
- [ ] **领域近似**：是否声明所用近似的适用范围？
- [ ] **滤波器/算子物理含义**：描述与代码定义一致。
- [ ] **统计量定义**：在不同模式下定义一致。
- [ ] **结论合理性**：每个 conclusion 必须能从已陈述的物理 + 数据合法导出，**不能跳越**。
- [ ] **因果 vs 关联**：相关不是因果；任何因果声明需有机制说明。
- [ ] **caveat 完整性**：本论文涉及的物理 caveat 是否都说到？

### C. 逻辑审查

- [ ] **整体叙事逻辑**：abstract → intro → method → results → discussion → conclusion 的故事线是否连贯？是否有跳跃？
- [ ] **论证链完整性**：每个结论是否前提充分？
- [ ] **隐含假设显式化**：所有未明说的假设全部列出。
- [ ] **不当推广**：小样本是否合理推广？
- [ ] **循环论证**：禁止用结论支持前提。
- [ ] **自相矛盾 / 上下文一致性**：abstract / intro / body / conclusion 跨章节内容必须一致；同一物理量、定义、声明全文统一。
- [ ] **过度声称**：避免 "first", "best", "only" 类词没有 caveat。
- [ ] **充分必要条件**："if" / "iff" / "only if" 使用正确。
- [ ] **统计严谨性**：CI 来自哪种估计（jackknife / bootstrap / asymptotic）？n 是多少？多重比较是否纠正？

### D. 语言审查

- [ ] **学术英语质量**：达到目标期刊（PRD / JCAP / ApJ / MNRAS）水平。
- [ ] **叙述表达**：每段主旨明确；句子长短合理；技术细节与解释比例合适。
- [ ] **时态一致性**：method = present / results = past / discussion = present。
- [ ] **被动语态**：方法可用，结果尽量主动。
- [ ] **术语一致性**：同一概念全文同术语。
- [ ] **缩写定义**：首次使用全称在前，括号缩写。
- [ ] **冗余 / 重复**：删除无信息增量段落；同一观点不在多处重述。
- [ ] **模糊词**："some", "various", "significant", "large", "approximately" 必须替换为数值或删除。
- [ ] **过渡连接**：段间 / 节间过渡平滑。

### D2. 去 AI 表达 / AI 标点审查（**强制 grep 全文清零**）

> 引自 `/paper` 的 Anti-AI-isms 节。本 skill 强制每轮跑以下 grep。

**em-dash 是最强 AI tell — 必须 0 残留：**
```bash
grep -n -E '—|---|\\textemdash' <file>.tex
```
所有出现：替换为 `,` / `;` / `:` / 括号 / `.` / `--` (en-dash 用于范围)。
学术写作传统上不用 em-dash 做插入语；连续 reviewer 第一眼就识破 LLM 痕迹。

**Tier A — 真零容忍（顶刊 corpus 0 出现）**：grep 命中 = 🔴 必删
```bash
grep -n -E -i '(delve|leveraged|leverages|leveraging|paved?|paves|paving|shed[s]?|shedding|showcase[sd]?|showcasing|seamless(ly)?|holistic(ally)?|comprehensively|crucially|utilizes|utilizing|recent advances|despite significant|with the advent|in recent years|it is worth|in summary,|in conclusion,)' <file>.tex
```

**Tier B — 顶刊偶用，限频**：每段命中数需人工核对，超 1 次/节 → 🟡
```bash
# 段首套话（dossier §3 显示 corpus 中段首仅 0-3 次出现）
grep -n -E -i '^\s*(Furthermore|Moreover|Additionally|Importantly|Interestingly|Notably),' <file>.tex
# 全文频次（顶刊正文偶用，但需控制密度）
grep -n -E -i '\b(robust|robustly|comprehensive|utilize[sd]?|leverage)\b' <file>.tex
```

**顽固替换组（不分级，全删/改）**：
```bash
grep -n -E -i '\b(in order to|aim to|facilitate)\b' <file>.tex
```

Tier A 命中：要么删除、要么改为具体数字 / 直接动词、要么重写为去 boilerplate 句子。
**Tier A 不接受"语境合适保留"**——学术读者宁可朴素也不要 LLM tell。
Tier B 命中：检查每段密度。corpus 实测频率详见 `style-profile/<field>/style_dossier.md` §4。

**自动汇总**（建议每轮跑一次）：
```bash
python tools/ai_ism_lint.py <file>.tex --summary
```
`--summary` 在 line-by-line hits 之后追加聚合视图：分 tier 计数 +
Tier B 各 `\section{}` 密度（cap = 1 / section / word）+ verdict 行。
当 verdict 出现 `🟡 N Tier B excess` 时，把对应 `[<section>] <word>: N` 整理
进 🟡 修改清单；`🔴 Tier A / em-dash hits present` → 所有 Tier A / em-dash
命中纳入 🔴 必改清单。

**结构 tell：**
- 三平行结构 (`not only X, but also Y, and furthermore Z`)：每节 ≤ 1 处。
- "X — that is, Y" 重述模式：em-dash + 重述 = 双重 tell，重写。
- 段落开头 `Recent advances in...` / `Despite significant progress...` / `With the advent of...` / `In recent years,...`：禁用。

**D3. Corpus-driven 风格对照（仅当 `style-profile/<field>/style_dossier.md` 存在时）：**

- 跑 `python tools/ai_ism_lint.py <file>.tex --field <field>` 输出 corpus 加权 AI-ism 报告（`--field` 可省略时自动选单 field）
- 比较句长分布 vs dossier 中各章节基线（>2σ 偏离 → 标 🟡）
- 比较段间过渡词使用 vs dossier whitelist；用了 dossier blacklist 的词 → 🔴

### E. 结构审查

- [ ] **三幕**：动机 → 方法 → 验证。
- [ ] **章节平衡**：方法 / 结果 / 讨论篇幅合理。
- [ ] **依赖顺序**：先定义后使用。
- [ ] **Figure / Table 位置**：紧邻首次引用。
- [ ] **Abstract 完整性**：问题 / 方法 / 关键数值 / 结论 / 影响。
- [ ] **Intro 漏斗**：宏观 → 微观逐步聚焦。
- [ ] **Conclusion 回应 Intro**：开头提的问题在结尾给答案。

### F. 引用审查

- [ ] **引用真实性**：每个 bibitem 必须可查（DOI / arXiv ID / ADS link）。**禁止用关键词搜数据库代替验证**——必须 WebFetch DOI / arxiv abs 页确认作者 / 年份 / 标题至少匹配。无法核对就标 `[NEEDS VERIFICATION]`，绝不假定真实。
- [ ] **引用相关性**：每个 `\cite{}` 在所在 sentence 真支持论点（不是凑数）。
- [ ] **引用完整性**：本论文话题的关键文献无遗漏。
- [ ] **自引比例**：< 30%（除 companion paper 系列）。
- [ ] **格式**：符合目标期刊。
- [ ] **bib 内冗余**：未引用的 bibitem 删除。逐条 grep 每个 `@xxx{key,` 在 .tex 内 `\cite{...}` 内是否出现。

### G. 数据与结果审查（**强制 cell-by-cell 溯源**）

- [ ] **数据集描述**：来源 / 选择标准 / 大小完整。
- [ ] **评估协议**：可复现（split / CV / metric definition）。
- [ ] **指标定义**：所有指标有数学定义（不仅是缩写）。
- [ ] **数据来源可追踪**：每个数字必须 link 到一个 file:line 或 DOI:Table。无法 link 即写 NEEDS SOURCE。
- [ ] **表格自洽**：每个 cell 与生成脚本 / CSV 对位（**强制 Read 源 CSV，不接受"印象中"**）。
- [ ] **正文-表格-caption 三方一致**：同一数字在三处必须相同（含小数位）；不一致即 🔴。
- [ ] **正文与图表数据一致**：figure 上的数字 / 曲线值与正文报数完全一致；不一致即 🔴。
- [ ] **Figure 质量**：清晰 / 标签 / 图例 / 单位完整；**Read 实际 PDF/PNG 内容**核对 caption 描述（不接受只看 caption）。
- [ ] **Figure 数据来源**：每个 fig 必须能指向一个生成脚本 + 上游 CSV / 脚本输出。
- [ ] **图表引用正确**：每个 `\ref{fig:..}` / `\ref{tab:..}` 实际指向正确对象；编号与数字论文呈现一致。
- [ ] **误差估计**：CI / SE / σ 来源明示（jackknife / bootstrap / asymptotic / Fisher）。
- [ ] **比较公平性**：与 baseline 同 protocol。

### G2. 跨章节数据一致性（**强制对位**）

- [ ] **Abstract 数字 → 正文数字**：每个 abstract 数字（AUC, p, n, σ）在正文 / 表格里至少出现一次且完全一致。
- [ ] **Intro 数字 → method/results**：intro 里 promise 的所有数字在后文兑现。
- [ ] **Conclusion 数字 → results**：结论引用的每个数字在 results 节有出处。
- [ ] **Caption 数字 → fig 内容**：caption 报的数字与图上 / 数据上一致。
- [ ] **跨论文一致性**（companion）：被 cite 的 companion 数字必须与该 companion 当前版本同步（Read companion 论文确认）。

### H. 接口对齐审查

- [ ] **符号 ↔ 代码变量 ↔ CSV 列名**：1:1 三元映射表存在且对得上。
- [ ] **公式中物理量 ↔ 代码实现**：同一物理量在论文公式与代码 function 中实现完全一致（含因子 / 单位 / 截断）。
- [ ] **数据接口 ↔ 推导接口对齐**：论文中数据预处理 / 选样准则与代码读 CSV 时的过滤条件一致。
- [ ] **Pipeline 顺序 ↔ 代码执行顺序**：论文里描述的步骤顺序与代码 main script 一致。

### I. 冗余 / 重复 / 过时审查（**轻量 pass；深度版见 §2.N + §2.O**）

> 本节作为快速 sweep 入口；任何此处命中需在 §2.N（深度 staleness sweep）与 §2.O（过程残影移除）中再次彻底处理，**不允许停在此节判 PASS**。

- [ ] **重复段落**：相同信息在不同节是否重复说？合并。
- [ ] **过时数据**：检查每个数字 vs 当前 source；任何 stale 数必须更新或删除。（深度对位 → §2.N1）
- [ ] **被 supersede 的方法 / 结论**：旧推导 / 旧结果若已被新版替代，是否在论文里残留？删除。（深度 → §2.N3 / §2.N4）
- [ ] **死引用**：定义但未使用的符号 / 公式 / table / figure 删除。（深度 → §2.N5 / §2.N6）
- [ ] **多余 placeholder**：TODO / TBD / [PLACEHOLDER] / `\textcolor{red}{...}` 注释残留检查。（深度 grep → §2.N7）
- [ ] **没有任何过时/错误的数据/推导/结果**：上一轮 audit 里被标记 SUPERSEDED 的内容必须从论文里清除。（深度 sweep → §2.N + §2.O）

### J. 可复现性审查

- [ ] 所有超参数列出（含随机种子）。
- [ ] 数据预处理步骤完整。
- [ ] Code/Data Availability section 存在且 link 实际可用（如 Zenodo / GitHub）。
- [ ] 软件 / 硬件版本声明（如 GPU 训练）。

---

### K. 现代物理学审查（**内嵌自 user-level `modern-physics-review` M1–M9**）

> 本节是 host-level skill `modern-physics-review` 的进程内并行整合：跑过本节后，§4.4 仍会用**隔离上下文**的独立子代理再跑一次 modern-physics-review 做双重验证（避免本进程的"框架偏见"漏检）。

#### K1. 维度一致性（dimensional analysis）

- [ ] 每个 displayed equation 左右两端的物理量纲是否一致？（用§1 的"公式清单"逐条对照）
- [ ] 出现的常数因子（`σ_T`, `m_e c²`, `k_B`, `G`, `Σ_crit`, `M_⊙`, `h`, `c` 等）是否正确？
- [ ] Fisher 矩阵 `𝓕_θθ` 的量纲应为 `[θ]⁻²`；inverse `𝓕⁻¹` 量纲为 `[θ]²`；CRLB σ²(θ̂) ≥ 𝓕⁻¹ 两端量纲一致。
- [ ] schematic / illustrative 公式必须显式标注；未标的视为 🔴。

#### K2. 渐近行为（asymptotic limits）

- [ ] 关键量在 `d→0` / `M→∞` / `ρ→1` / `N→∞` / `κ→0` / `ν→∞` 等极限下行为合理？
- [ ] 极限是否对应已知解析结果（如 NFW 内外渐近、isothermal、Gaussian noise CLT、CDM linear regime）？
- [ ] "saturation" 声明给出方向（从上 / 从下）？
- [ ] 极端尺度行为不合理 = 🔴。

#### K3. 对称性 / 宇称 / 守恒律

- [ ] 显式对称性（rotation / parity / translation / gauge / Lorentz）被尊重？
- [ ] "parity argument" 有数学根据，不是"by inspection"？
- [ ] 概率不等式（Fisher additivity / DPI / KL ≥ 0 / P_e ≥ 0 / TV ≤ 1）满足？
- [ ] sign 约定（`b/a=−1` vs `|b/a|=1`）全文一致？

#### K4. 统计假设 / 概率论

- [ ] iid / Gaussian / 有限矩 / 平稳性 等假设在 theorem / proposition 中**显式**声明？
- [ ] CLT vs LDP regime 正确区分（`1/√N` 还是 `1/N` scaling）？
- [ ] Pinsker / Fano / Cramér-Rao / DPI / Le Cam 应用满足各自前提？
- [ ] Bayes 推断说明 prior（log-uniform / flat / informative / Jeffreys）？

#### K5. 公式导出（algebraic correctness）

- [ ] 多步推导每一步可重现，必要时手算 + 用 sympy / numpy 脚本 verify。
- [ ] 关键代数（如 Pinsker `TV² ≤ KL/2` + Gaussian KL = ½Δθᵀ𝓕Δθ → TV ≤ ½√(𝓕Δθ²)）逐步检查。
- [ ] "`α_F` 化简" / "`λ_crit = √(2k)`" 等的代数从原始公式出发可重得？
- [ ] 量纲在化简过程中全程保持？

#### K6. 数值溯源（numerical traceability，与 §2.G 联合执行）

- [ ] 每个数字 → 一个具体脚本输出 / DOI Table/Figure / 已标号公式 + 一行算术。
- [ ] **当轮重新跑脚本**确认数字仍能复现（脚本演变后可能漂移）。
- [ ] Abstract / 正文 / 图表 caption 三方一致到所有有效数字（与§2.G2 联合）。
- [ ] Companion paper 数字与该 companion 当前版本同步。

#### K7. 引用真实性（与 §2.F 联合）

- [ ] 已在 §2.F 处理；本节复检"物理 / 数学 / 统计核心文献"是否遗漏（Pinsker / DPI / NFW / Sheth-Tormen / matched filter / Fisher / Le Cam 等领域关键参考）。

#### K8. 编译完整性（与 §1 准备阶段 step 8 + §4.3 联合）

- [ ] `pdflatex × 2 + bibtex + pdflatex × 2` → 0 errors。
- [ ] 0 undefined references。
- [ ] 0 multiply-defined labels。
- [ ] 0 overfull hboxes。
- [ ] 0 missing-number warnings。

#### K9. AI-isms（与 §2.D2 联合执行）

> 本节是 §2.D2 的物理审查角度复检；执行 §2.D2 已规定的 grep 命令即可。

---

### L. 系统性不一致 / 上下文断层（**强制全文逐节对位**）

> 这是 v3 新增维度，专门捕获跨章节的"漂移"——单点审查看不出来、但读者通读时必然崩塌的问题。

#### L1. 符号 / 定义跨章节一致性

- [ ] 同一物理量在所有章节同符号；同一符号不复用于不同物理量；下标含义全文统一。
- [ ] 任何**重新定义**（"now we define X as ..."）必须显式声明覆盖了哪个旧定义；否则 🔴。
- [ ] 缩写在 abstract / intro / body / appendix 各处第一次出现都是否全称 + 缩写？还是中途突然出现新缩写？

#### L2. 概念引入 / 消费链

- [ ] 每个引入的概念 / 算子 / 数据集 / 假设是否在后文**被实际使用**？引入但未消费 = 死引入 → 🟡。
- [ ] 每个使用的概念是否在前文已定义（先定义后使用）？前向引用 = 🔴 除非显式 forward-ref 并在后文兑现。
- [ ] 任何"as we will see in §X"必须在 §X 真的兑现。

#### L3. 跨章节数值 / 假设漂移

- [ ] 某个常数（如 `H_0=67.4`, `Ω_m=0.315`, `N_eff=3.044`）在论文不同节使用值是否一致？
- [ ] 数据集大小 / split / cut 在 method / results / appendix 三处声明是否一致？
- [ ] 一个假设（如 "Gaussian noise"）在某节用、另一节悄悄改成 "Poisson"？

#### L4. 跨论文 / Companion 漂移

- [ ] 引用 companion paper 的数字 / 公式 / 图表必须与该 companion **当前版本**一致（Read companion 论文确认，不接受"我们之前协调过的"）。
- [ ] 若 companion 在演变中，必须显式标注哪个 commit / version 被引用。

#### L5. method ↔ result ↔ discussion ↔ conclusion 闭环

- [ ] method 里描述的每一个 step 在 results 里有对应输出？
- [ ] results 里报的每一个数字 / 现象在 discussion 里有解读？
- [ ] discussion 里讨论的每一个 caveat 在 conclusion 里有 propagate？
- [ ] conclusion 里宣称的每一个 claim 在 results / discussion 里有支撑？
- [ ] 任意单向断链 = 上下文断层 → 🔴。

#### L6. abstract ↔ intro ↔ conclusion 三方对位

- [ ] 三处提到的"研究问题"必须可映射到同一问题陈述。
- [ ] 三处提到的"关键数字"必须 byte-for-byte 一致（含小数位）。
- [ ] 三处提到的"主要贡献"必须为同一组 claims，仅 phrasing 不同；不能 intro 说 3 点贡献、conclusion 说 4 点。

---

### M. 数学计算 / 物理推导 — 怀疑式反复检查（**强制 3-pass**）

> 用户要求："对于数学计算/物理推导，必须多次反复以'这里有问题'这种怀疑式态度进行全面检查，直至零问题收敛。"
> 落实方式：每一个数学推导块 / 物理推导链 / 数值结果，**强制以下 3 个独立 pass 全部跑过且全部 0 命中**，才允许标记该块"已验证"。

#### M.pass-1：量纲 + 代数 + 边界（baseline scrutiny）

- 对该推导块逐行检查量纲、代数化简、近似展开、边界 / 极限。
- 必要时用 sympy / numpy 脚本独立重做（不接受"显然""易得"）。
- 预设态度：**"这里量纲一定错了；这里近似一定漏了高阶项；这里边界一定 ill-defined"**。
- 写下命中条目（即使最后无命中也要显式列"已检查 / 0 命中"+ 检查方法）。

#### M.pass-2：Adversarial reviewer（红队视角）

- 假设你是想发文反驳本结果的 reviewer，列出**最致命的 3 条反驳**。
- 反驳必须具体：指向行号 / 公式编号 / 假设 / 数值；不接受"general 怀疑"。
- 对每条反驳，必须给出："本文当前如何回应该反驳" + "回应是否充分（具体证据）"。
- 任一条反驳缺乏充分回应 = 🔴。

#### M.pass-3：不变量审查（守恒 / 对称 / 渐近 / 统计假设）

- 该推导是否破坏任何已知守恒律（能量 / 动量 / 角动量 / charge / probability mass / Fisher information additivity）？
- 是否破坏对称性约束（rotation / parity / gauge / Lorentz）？
- 渐近极限是否给出已知解析结果？
- 统计假设（iid / Gaussian / 有限矩）是否在前文已声明且本推导真的满足？

#### M-pass 执行约束（硬性）

1. **三 pass 必须独立**：后一 pass 不能引用前一 pass 的"OK"作为前提；每 pass 重新从公式 / 数据出发。
2. **任一 pass 命中 → 修复 → 重跑全部 3 pass**（不是只重跑命中那一 pass）。
3. **三连 0 命中**才允许该推导块状态改为 `VERIFIED`；否则保持 `UNDER_SCRUTINY`。
4. **整篇论文所有 displayed equation + 所有数值结论**都必须达到 `VERIFIED`，才允许进入 §4.3 进程内收敛判定。
5. **报告中保留 3-pass 痕迹**：每个推导块至少列出 3 行（pass-1 / pass-2 / pass-3 各自的检查方法 + 命中数）；不允许只写一句"已验证"。

---

### N. 过时 / 错误 / 冗余 / 漂移内容审查（**绝对零容忍，6 类内容深度 sweep**）

> 用户原话："**检查确认绝对没有过时/错误/冗余/漂移的内容，包括叙述、数字、推导、结论、图片、表格等等。**"
> 落实：本节是 §2.I（轻量冗余）的**深度版**。覆盖 6 类内容 + 残留 markup；任何"上一版本残留"全部视为 🔴 必删/必改。修复原则：**能删则删，不能删则 update 到当前真值**。

#### N1. 数字 staleness（dynamic numerical drift）

- [ ] 每个数字与当前 source（CSV / npz / 脚本最新输出）byte-for-byte 一致？
- [ ] 数字所依赖的脚本 / 数据集是否在最近 commits 中改过（用 `git log --since=<draft_start> -- <source_path>` 查）？若改过 → **当轮重跑该脚本**并对位，不接受"印象中没变"。
- [ ] 含数字的 abstract / 正文 / table / caption / conclusion 5 处全部对位；任一偏离 = 🔴。
- [ ] "X% better than the previous baseline Y"：若 Y 是本论文先前 draft 自身数字 → 删除（过程残影，转 §2.O 处理）；若 Y 是已发表的外部基线 → 保留。

#### N2. 叙述 staleness

- [ ] "as we showed in §X" / "as discussed below" / "see Fig. Z" 等指向式叙述：§X / Fig Z 仍存在、编号未变、内容仍支持该指向？
- [ ] "X is now Y" / "the current standard is Z" / "this approach is becoming dominant" 类含时间含义的句子是否仍属实？过期 → 改为 plain statement 或删除。
- [ ] "recent" / "new" / "novel" / "state-of-the-art" 类宣称：发表 timeline 下仍成立？发表时已不"recent"的删 / 改为具体年份 / 改为 plain。
- [ ] 任何"将在后文 §X 中讨论"：§X 真的还在并且真的讨论？

#### N3. 推导 staleness

- [ ] 公式编号被引用（`\eqref{eq:..}`）：被引用的公式仍存在且形式未改？被改过的上游公式，所有下游推导是否同步改？
- [ ] 推导依赖的假设：在前文是否被放宽 / 收紧 / 删除过？若假设变了，依赖它的推导整段重审。
- [ ] 一个推导是否曾被替换为简化版后旧版仍在残留？只保留当前用的版本；不留 "alternative derivation" 作 "for completeness"，除非真有对照意义且明确标注。

#### N4. 结论 staleness

- [ ] 每条 conclusion 是否能从**当前** results 节重新合法导出？老结论残留 = 🔴。
- [ ] Discussion 中提到的 limitation / caveat 是否仍适用于当前方法？已修复 / 已绕开的 caveat 必须删除（否则等于自我否定当前 method）。
- [ ] Abstract 中的"我们发现 / 我们证明"主张：与 results 当前最终版本一致？

#### N5. 图片 staleness

- [ ] 每个 `\includegraphics` 引用的 PDF / PNG：生成脚本是否在最近 commits 中改过？若是 → **当轮重跑该脚本**，对位"图上数字 / 曲线 / 误差棒 vs 正文叙述"。
- [ ] 图标题 / 颜色规则 / 轴标签 / 单位与正文一致？
- [ ] 图存在但**未被任何 `\ref{fig:..}` 引用** = dead figure → 删除（或补 ref，若图本身仍有价值）。
- [ ] 图被 `\ref{}` 引用但**实际未生成 / 路径错** = 🔴 编译错。
- [ ] 子图（panels）数量与 caption 描述一致？删过某个 panel 后 caption 没更新 = 🔴。

#### N6. 表格 staleness

- [ ] 每个 cell 与当前生成脚本输出对位（与 §2.G 联合执行）。
- [ ] 表格存在但未被任何 `\ref{tab:..}` 引用 = dead table → 删除。
- [ ] 表头术语与正文使用术语一致？术语漂移 = 🔴。
- [ ] 表格 row / column 数量与正文叙述一致？删过某 row 后正文叙述没更新 = 🔴。

#### N7. 残留 markup（必须 0 残留）

强制 grep：
```bash
grep -nE '\\todo\{|\\fixme\{|\\note\{|\\textcolor\{red\}|\\textcolor\{blue\}|\\hl\{|\\TODO|\\FIXME|\[PLACEHOLDER\]|\[TBD\]|\[TODO\]|XXX|FIXME' <file>
grep -nE '%\s*(TODO|FIXME|XXX|HACK|NOTE:|REVIEW:|TEMP)' <file>
grep -nE 'example-image-(a|b|c)|\\rule\{' <file>      # placeholder figures
grep -nE '\\iffalse|\\fi\s*%\s*(old|removed|deprecated|hidden)' <file>  # commented-out blocks
```

- [ ] 上述 grep 命中数 = 0。
- [ ] LaTeX 注释（`% ...`）中的"old version" / "TODO" / 注释掉的段落 = 0 残留。

#### N8. 删除 vs 修改决策树（对每个 N1–N7 命中）

1. **首选：删除**。若"删除后科学完整性不受影响" → 删。
2. **次选：update 到当前真值**。若内容必要但版本过时 → 改为当前真值。
3. **绝不允许**："保留 + 加注释解释为什么是 stale" / "保留 + 在 footnote 说明已过时" / "保留 + 标 'historical interest'"。

---

### O. 过程残影移除（**update-not-accumulate；强制全文清零**）

> 用户原话："**移除所有"过程残影"……所有的论点、结果、叙述全部都是最新的，只写有意义、有信息量的内容。换句话说就是"更新，而不是叠加"。**"
> 落实：LLM-assisted 写作和迭代研究中，作者/Claude 容易把"研究路径"写进正文（"发现 X 研究 X 得到 Y；发现 Z 推翻 Y"；"发散 5 方向最终采用 2 个"）。读者**只关心当前最新的科学声明**。本节专门 sweep 这类过程残影，**默认全删**。

#### O1. 过程叙事 grep（强制全文 4 层）

```bash
# Tier-1 显式自我回顾（"我们一开始 / 最初 / 之前"）
grep -nE -i '(initially,?|originally,?|at first,?|previously,?|in an earlier|we first |our first |first attempt|earlier version|an earlier version|prior to this|before we |we used to|we had thought|we initially|in a previous (draft|version)|early on,?)' <file>

# Tier-2 路径选择（"考虑了 ABC，最终选 B"）
grep -nE -i '(we (also )?considered|we (also )?tried|we (also )?explored|alternative approaches?|other (approaches|methods) (were|we)|we rejected|we discarded|we abandoned|ultimately (chose|adopted|settled|opted)|after (some |much )?experimentation|we ended up|we settled on)' <file>

# Tier-3 自我反驳（"后来意识到 / 进一步分析后 / 在 retrospect"）
grep -nE -i '(however,? this turned out|on closer inspection|upon further analysis|we (later |then )?realized|we (later |then )?found that|in retrospect|it became clear|this approach did not|this hypothesis was (refuted|disproved|rejected)|did not pan out|did not work as)' <file>

# Tier-4 版本 / 迭代痕迹
grep -nE -i '(in this (revised|updated|new) version|compared to (our )?(earlier|previous) (version|draft|preprint)|in v[12]\b|version (1|2|one|two)|the (revised|updated) (analysis|approach|method)|after (revision|review|feedback))' <file>
```

#### O2. 判定规则（每个命中 1 类）

| 类别 | 是否保留 | 修复方式 |
|---|---|---|
| **类 1：纯过程残影** ("我们一开始 X 后来 Y") | **删除** | 只保留 Y；删除 X 与 transition |
| **类 2：方法论文有意做的方法对比** | **保留但重写** | 改为"contrast with method M_baseline"，不出现"we initially tried" 等自传痕迹 |
| **类 3：引用外部 prior literature** | **保留** | 与本论文进程无关；标注是外部文献，不是本文进程 |
| **类 4：自我反驳但反驳本身是 contribution** | **保留但重写** | 改为"prior intuition would suggest X; we show Y"——不出现"we initially thought" 等第一人称过程描述 |

**默认决策 = 类 1 删除**；判为 2/3/4 需提供具体证据（指向 method paper 对比表 / 外部 cite / paper 主 contribution 句）。

#### O3. "update-not-accumulate" 硬约束

- [ ] **同一断言不在两处出现两个版本**（旧的 + 新的）。若发现 → 只保留新的，删除旧的。
- [ ] **一个结论的演化历史不出现在 paper body**。如必要可入 supplementary "history of analysis"；默认不写。
- [ ] **"we tried X but it didn't work" 类陈述**：默认删除。除非 X 是本领域 well-known baseline 且本文做了正式 head-to-head 对照 → 改写为正式 baseline 对比。
- [ ] **一个 method 的多个 variant 若最终只用 1 个 → 只描述那一个**。其它 variant 不提，除非有显式对照实验。

#### O4. 信息量自检（每段执行；任 1 题判"是" → 整段 🟡 重写或删除）

对论文中**每一段**问 4 题：
1. **过程描述**：这段是描述当前论文的科学声明，还是描述研究过程（旅程 / 试错 / 演变）？
2. **删除不减损**：这段删除后，读者对当前结论的理解是否减损？
3. **他处重复**：这段是否在论文别处已重复（哪怕用不同 phrasing）？
4. **零信息过渡**：这段是否仅起"过渡 / 缓冲 / 总结过去段" 作用而无新信息？

- 题 1 答"是过程描述" → **整段删除**（不做软化保留）。
- 题 2 答"删除不减损" → **整段删除**。
- 题 3 答"已重复" → **合并到首次出现处**，删除当前段。
- 题 4 答"零信息" → **删除**。

#### O5. 与 N 维度的协同

- N 找的是"应该是 latest 但混入了 stale 副本" → 修复方式 = **update**。
- O 找的是"latest 之外还混入了 process 描述" → 修复方式 = **remove**。
- 同一行可同时命中两维度（如 "we initially used H_0=70 but now use H_0=67.4" — 既是过程残影 (O) 又是 stale 数字残留 (N1)）。处理顺序：**先 O 删除过程描述，再 N 确认当前数字唯一且最新**。
- 修复后必须重跑两维度 grep / sweep 确认无残留。

---

### P. 内部开发 / 研究 / 草稿语言审查（**强制 0 残留**）

> 用户原话："**检查是否有开发/研究/草稿阶段的内部使用语言、表述，如果有，必须替换为泛用学术语言。**"
> 与 §2.O（过程残影）的区别：O 处理"叙事过程"（"we initially tried" 这种自传痕迹）；本节 P 处理"内部语言 / 草稿口吻 / jargon / 占位"——读者**看不懂**或**会出戏**的内部表达。
> 落实：grep 4 类清单 + Read 复核判定 + 默认替换为泛用学术语言（不允许"语境合适保留"）。

#### P1. 内部代号 / 路径 / 文件名 / 工具链名（草稿期 placeholder）

强制 grep（命中后必须 Read 上下文判定是否泄漏到正文）：
```bash
# 显式 placeholder / TODO marker
grep -nE -i '(@TODO|@FIXME|@NOTE|XXX|HACK|placeholder|tmp_|temp_|test_only|debug_|scratch_)' <file>

# 草稿期工程名 / 版本名 / 路径残留
grep -nE -i '\b(run_v[0-9]+|v[0-9]+_final|v[0-9]+_clean|v[0-9]+_new|attempt_[0-9]+|trial_[0-9]+|exp_[0-9]+)\b' <file>

# 项目 / 仓库 / pipeline 内部代号（在正文里直呼项目内部名）
grep -nE -i '\b(our pipeline|our codebase|our repo|our project|our github|our scripts?|our framework)\b' <file>

# 项目特有缩写 / 代号在论文体系内未给外部读者可懂的定义即出现
grep -nE -i '\b(WGL|sci-paper|escnn|the (paper-?review|brainstorm|mainline) (skill|module))\b' <file>
```

- [ ] 上述 grep 全 0 命中（或命中后有显式正文 within-paper 定义）。
- [ ] 修复规则：
  - 内部 placeholder / TODO 标记 → 删除或替换为正式术语
  - 草稿期工程名（`run_v3 / v2_final`）→ 替换为论文体系命名（"the production pipeline" / "the final analysis"）
  - "our pipeline / our codebase" → 改 "the framework introduced in §X" / "the pipeline of [cite companion paper]"
  - 项目特有缩写 → 首次出现给完整定义 + 缩写（与 §2.D 缩写定义协同）；或彻底改为学术通用术语

#### P2. 草稿口语 / 解说式 / 第一人称叙述

强制 grep：
```bash
# 草稿期口语化解说
grep -nE -i '(basically|essentially|let me|let us\b|let's\b|so to summarize|as we said|like I said|like we said|kind of|sort of|something like|here\'s|here is the)' <file>

# 解说员式叙述
grep -nE -i '(in this paper we will|in this section we will|now we will|next we will|now let us|we will (see|show|discuss|describe) (below|next|now)|we will see|we have seen)' <file>

# 草稿期占位句 / 软化措辞
grep -nE -i '(in some sense|in a way|more or less|roughly speaking|loosely speaking|so to speak|if you will)' <file>

# 实验日志风格
grep -nE -i '(we tried|we played with|we messed with|we experimented with|we fiddled with|tinker|tweak)' <file>
```

- [ ] 修复规则：
  - `basically / essentially` → **删除**（信息量 0）或量化（"to first order" / "at leading order"）
  - `let me / let us / let's` → 删除；论文不用第一人称口语
  - `in this paper we will / now we will see / we will discuss next` → 改一般现在时主动陈述（"§3 describes ..." / "We show that ..."）；不预告未来章节
  - `kind of / sort of / something like` → 必须删除或量化（"approximately 1.5σ" / "within 10%"）
  - `we tried / we played with / experimented with / fiddled` → 改正式动词（"We evaluated / tested / compared"）
  - `as we said / like we said` → 删除或改 `"as shown in §X"` 带具体定位

#### P3. 实验日志 / commit-message 风格残留

- [ ] 论文正文中**不应**出现的句式（grep + Read 复核）：
  - 时间戳式陈述（"last week we ran ..." / "yesterday's run shows ..." / "the latest version gives ..."）
  - commit-message 式（"fixed bug in X" / "updated Y" / "refactored Z" — 这是 git log 语言，不是 paper 语言）
  - 待办事项式（"need to verify ..." / "should double-check ..." / "to be confirmed"）
- 修复：彻底改写为客观陈述，去除时间标签、去除作者动作描写、去除待办语气。

#### P4. 内部约定符号 / 占位变量名

- [ ] 正文中是否出现仅项目内部有意义的符号 / 变量名（`X1, X2 / data1, data2 / method_A, method_B`），且未在论文体系内给完整 operational 定义？
- 修复：要么补充正式定义（与 §2.A 符号定义协同），要么用论文体系内有意义的命名（`κ_NFW / Σ_crit / M_200`）替换。

#### P5. 修复后强制 0 残留再验证

- 修完 P1–P4 后**必须重跑全部 grep** + 重 Read 全文一遍（不接受抽样）；命中数 = 0 才允许判 P 维度 PASS。
- 与 §2.D / §2.D2 AI-isms 协同：本节是 D 语言审查的**草稿层补充**；D 管学术英语质量，本节管"是否泄漏内部 jargon"。

---

### Q. 参考文献查漏补缺 + 引用精确度（**深化 §2.F；强制实际验证**）

> 用户原话："**检查参考文献，是否有缺失/错用，查漏补缺，实际验证引用精确度。**"
> §2.F 已检查"每条 bibitem 真实性"；本节 Q 把它推到更彻底：(a) 应引但**未引**的关键文献，(b) 每条 `\cite{}` 是否真正支持引用句的具体声明（不只是真实存在）。

#### Q1. 查漏（missing key references）

执行步骤（顺序、每步必做）：

1. **抽取论文主题关键词**（≥ 5 个，从 abstract + intro 推断）。
2. **对每个关键词，WebSearch 该领域的高引用度文献**（用 `arxiv` / `ads.harvard.edu` / `Google Scholar` 关键词；除非 `--no-online`）。
3. **WebFetch 每个候选的 arXiv abs / DOI 页**确认主题相关性；至少 3 篇相关 hit。
4. **检查每个 hit 是否在本论文 `references.bib`**：
   - 已引 → 跳过
   - 未引但**与论文核心 claim 直接相关** → 🔴 关键文献遗漏，列建议添加
   - 未引但**与论文边缘相关** → 🟡 候选补充，列入"作者判断清单"
5. **逐领域检查必引清单**（field-aware）：
   - 若 `--field <name>` 提供 + `style-profile/<field>/style_dossier.md` 存在 → 读 dossier 中的"领域基石文献"清单作为应引基准
   - 否则按论文主题手工列出 3-5 篇"该领域该 sub-topic 几乎必须引"的 seminal works
   - 缺任一 = 🔴

#### Q2. 错用（misuse / citation precision）

对论文中**每个 `\cite{key}`** 命中位置：

1. **Read 引用所在 sentence** 看本论文如何描述该引用支持的内容。
2. **找到该 key 在 `references.bib` 中的完整条目**（取 DOI / arXiv ID / title / authors / year）。
3. **WebFetch 该 paper 的 arXiv abs 页 / DOI landing 页 / 公开 PDF**。
4. **比对**：
   - 本论文 sentence X 说"prior work [cite] showed Y" → 该 paper 摘要 / conclusion 是否真的 showed Y？
   - 本论文说"following [cite], we use method M" → 该 paper 是否真的提出 / 使用 method M？
   - 本论文说"[cite] argues for assumption A" → 该 paper 是否真的 argue for A，还是 against A，还是无关？

5. **判定**：
   - **CORRECT**：引用内容与原 paper 主张匹配 → 跳过
   - **WEAK**：原 paper 提到但不是主要主张 → 🟡 建议改引更相关的 paper 或弱化措辞
   - **MISUSED**：原 paper 不支持本论文的描述（甚至反对）→ 🔴 必改 — 这是学术诚信问题
   - **UNVERIFIABLE**：因 paywall / 内容缺失等原因无法核实 → 标 `[NEEDS PHYSICAL ACCESS]` + 列入 §4.4 隔离 MPR 终验前的硬性 NEEDS-MORE-INFO 阻塞；与 §0.8 一致**不允许永久挂起**——必须设法获取或显式改弱引用

#### Q3. 自引与 companion 文献精确度

- [ ] 每个**自引**（同作者 / 同组）的 `\cite{key}`：原 paper 当前版本（不一定是发表版；可能 v2 / v3）声明是否仍与本论文使用方式一致？版本漂移 = 🔴（与 §2.L4 联合）。
- [ ] 每个 **companion paper** 引用：companion 当前版本（如本会话仍 in preparation）的 claim 是否与本论文一致？

#### Q4. 引用格式 / 编号 / 标点（最后的轻量 sweep）

- [ ] `\cite{}` 风格全文一致（`\citep / \citet / \cite` 不混用，除非约定）
- [ ] 多引用排序（按年 / 按作者）全文一致
- [ ] DOI / arXiv ID 完整无 typo（每条至少有一种 unique identifier）

#### Q5. 修复后强制重验

- 任何 🔴 / 🟡 修复后**重跑 Q1 Q2 全部步骤**（不接受抽样）。
- 与 §2.F（引用真实性）合并报告时：F 检查"存在"，Q 检查"应引 + 精准引用"——两层在 §4.3 收敛硬判据中独立计数。

---

## 3. 第三阶段：交叉验证

每个论文 vs 代码 / 数据要做 4 个对位：

1. **架构 vs 代码**：论文描述 = 项目 config / 模块结构。
2. **数值 vs 输出**：论文数字 = 脚本输出 / CSV cell。
3. **公式 vs 实现**：论文公式 = code function（必要时手动验证 1-2 个 corner case）。
4. **流程 vs 顺序**：论文 pipeline = main script 执行序列。

---

## 4. 第四阶段：输出报告 + 零问题收敛闭环 + 隔离上下文终验

### 4.1 单轮报告格式

```
## 论文审查报告: <filename> — Iter <N>

### 总体评估
- 整体质量：[优 / 良 / 中 / 差]
- Top 3 关键问题：[...]
- 投稿状态：[可投 / 小修 / 大修 / 重写]

### A–Q 各维度
[逐项 PASS / FAIL，FAIL 项给具体行号 + 证据 + 建议修改]
- A 数学 / B 物理 / C 逻辑 / D 语言 / D2 AI-isms / D3 Corpus-style
- E 结构 / F 引用 / G 数据 / G2 跨章节数据一致 / H 接口 / I 冗余（轻量） / J 可复现
- K1–K9 现代物理学审查（M1–M9 内嵌）
- L1–L6 系统性不一致 / 上下文断层
- M.pass-1 / M.pass-2 / M.pass-3 数学物理怀疑式 3-pass（每个推导块单列）
- N1–N8 过时/错误/冗余/漂移内容深度 sweep（6 类内容 + 残留 markup + 删/改决策树）
- O1–O5 过程残影移除（4 层 grep + 4 类判定 + update-not-accumulate 硬约束 + 每段 4 题信息量自检）
- **P1–P5 内部开发/研究/草稿语言审查（草稿期 placeholder / 内部代号 / 口语化解说 / 实验日志风格 / 内部占位变量名 — 强制 0 残留替换为泛用学术语言）**
- **Q1–Q5 参考文献查漏补缺 + 引用精确度（应引未引检测 + 每条 \cite{} WebFetch 原文验证主张匹配 + CORRECT/WEAK/MISUSED/UNVERIFIABLE 判定）**

### 交叉验证发现
[paper vs code/data 不一致清单，每条给 paper 行号 + source 路径行号]

### 修改清单（按优先级）
1. 🔴 必改：[file:line + 当前文本 + 建议文本]（影响科学正确性）
2. 🟡 建议改：[同上]（影响可读性 / 表达 / AI-isms）
3. 🟢 可选改：[同上]（风格 / polish）

### 3-pass 状态表（M 维度专用）
| equation/derivation id | M.pass-1 | M.pass-2 | M.pass-3 | status |
|---|---|---|---|---|
| eq:fisher | ✓ 0 hits | ✓ 0 hits | ✓ 0 hits | VERIFIED |
| eq:pinsker | ✗ 量纲在化简漏因子 | — | — | UNDER_SCRUTINY |
```

### 4.2 修复阶段（默认开启，除非传 `--no-fix`）

1. **修复优先级**：🔴 优先；同级内**物理优先**（K / M 维度命中优先于 D / E）。
2. 按 🔴 → 🟡 顺序逐条 Edit。
3. 每条修改后**重新读改动区域**确认改动符合预期。
4. 全部 🔴 / 🟡 修完后，**重新跑 LaTeX 编译**完整链（`pdflatex × 2 + bibtex + pdflatex × 2`），确认 0 error / 0 new warning（K8 判据）。
5. 跑 `grep -n -E '—|---|\\textemdash' <file>` 确认 em-dash 全清。
6. 跑 AI-isms grep 确认全清。
7. **修了任意公式 / 数值 / 物理推导 → 重跑该块的 3-pass**（§2.M）；不接受"修小处不重跑"。
8. **严禁的修复反模式**（与§0.6 一致）：
   - ❌ 给量纲错的公式"加 disclaimer"绕过
   - ❌ 把物理错误改写为"schematic"但不加显式标注
   - ❌ 通过软化表述（"可能 / 大致 / 在某些情况下"）掩盖原症状
   - ❌ 注释掉失败的检查 / 删除有问题的章节假装不存在
   命中任一 → 修复无效，回到 §4.2 第 1 步重新选项。

### 4.3 零问题收敛硬循环（核心）

用户原话："**规范化执行约定：检查一次 → 发现问题 n 个 → 修复 → 再检查（iter 2），以此循环，直到完全没有任何遗留问题。**" 落实为：

```
ITER_BUDGET = --max-iter N (default 5; 但下面的收敛优先于预算)
for iter in 1..∞:
    report_k = full_review(file)            # 重新跑 §1 + §2.A–§2.M 全套，不复用上一轮印象
    n_red   = count(report_k.🔴)
    n_yellow = count(report_k.🟡)
    n_under_scrutiny = count(M-pass derivations not yet VERIFIED)

    print f"Iter {iter}: 🔴={n_red} 🟡={n_yellow} UNDER_SCRUTINY={n_under_scrutiny}"

    if n_red == 0 and n_yellow == 0 and n_under_scrutiny == 0 \
       and compile_clean and ai_isms_clean and number_traceability_all_green:
        print f"Process-internal CONVERGED at iter {iter}"
        break

    apply_fixes(report_k.🔴 ∪ report_k.🟡)   # §4.2
    rerun_compile()
    rerun_M_pass_for_changed_blocks()

    if iter >= ITER_BUDGET:
        print "ITER_BUDGET reached but NOT CONVERGED"
        print "未收敛问题清单:"
        print report_k.unresolved
        # 不允许偷偷提升 budget；让用户决定继续还是 stop
        BREAK_WITH_USER_DECISION()
```

**进程内收敛硬判据**（必须**全部**满足；任一不满足即未收敛）：

| 判据 | 阈值 |
|---|---|
| 🔴 issue 数 | = 0 |
| 🟡 issue 数 | = 0 |
| M-pass UNDER_SCRUTINY 推导块数 | = 0（全部 VERIFIED） |
| LaTeX 编译错误 | = 0 |
| LaTeX undef refs / multiply-defined / overfull / missing-number | 全 0 |
| 数字溯源清单 | 全绿 |
| AI-isms grep 命中（含 em-dash + Tier A） | = 0 |
| 跨章节数值漂移（§2.L3 / §2.L6） | = 0 |
| (若有 dossier) corpus-style lint 命中 | = 0 |
| **§2.N 6 类内容 staleness + 残留 markup**（N1–N7 全部 sweep） | **全 0 命中** |
| **§2.O 过程残影 4 层 grep + 每段 4 题信息量自检** | **全 0 命中** |
| **§2.P 内部开发/草稿语言 4 类 grep**（P1–P4 全部 sweep） | **全 0 命中** |
| **§2.Q 引用精确度** — MISUSED 引用数 | **= 0** |
| **§2.Q 引用查漏** — 🔴 关键文献遗漏数 | **= 0** |
| **§2.Q UNVERIFIABLE 引用** | **= 0**（必须获取原文或显式改弱措辞） |

**绝对禁止的"软收敛"出口**（与§0.8 一致）：
- ❌ "基本干净，剩下都是 minor"
- ❌ "🟡 可保留，不影响科学正确性"
- ❌ "已经修了大部分，剩余作为 future work"
- ❌ "用户没时间，提前结束"

### 4.4 隔离上下文 modern-physics-review 终验（**强制，除非 `--skip-final-mpr`**）

> 用户原话："**最终执行隔离上下文的 modern-physics-review 技能。**"
> 这一步的意义：本进程的 §2.K 已合并了 M1–M9 的检查项，但**同一进程的审查会带框架偏见**（用同一套上下文找不出自己的盲区）。所以即使 §4.3 已"零问题收敛"，仍必须用**完全独立的子代理在隔离上下文**中再跑一次 modern-physics-review，作为第三方双重验证。

#### 4.4.1 触发条件

- §4.3 已达成进程内零问题收敛（所有硬判据通过）；
- 用户未传 `--skip-final-mpr`（默认未传）。

若 §4.3 未收敛 → **不允许**进入 §4.4（避免把半成品送进独立审）。

#### 4.4.2 子代理调用规范

主代理用 **Agent tool** 启动子代理，参数：

- `subagent_type`: `general-purpose`（modern-physics-review 是 host-level skill，不是 sci-paper 插件 skill，子代理需用 general-purpose 然后**显式加载** user-level skill 的 SKILL.md）
- `isolation`: `worktree`（在隔离 git worktree 中跑，避免污染主工作树；若子代理无改动，worktree 自动清理）
- `description`: `"Isolated modern-physics-review final verification"`
- `prompt`: 自包含，包含以下内容（不允许省略）：
  1. 路径："Target file: `<absolute path>`"
  2. 加载指令："Read `C:/Users/skyma/.claude/skills/modern-physics-review/SKILL.md` and follow its full protocol (§0–§5) end-to-end. Do not skip phases."
  3. 上下文边界："You are running in an isolated context. Do NOT rely on any prior conversation, prior review reports, or prior 'this was already verified' claims. Re-Read every file, re-run every script, re-grep every pattern. cc-enslaver rules apply."
  4. 期望产出："Run modern-physics-review's own automatic fix loop to convergence (its §3 / §4). Return the final convergence report (file:line evidence + numerical anchors verified + 0 🔴 / 0 🟡 / 0 compile errors) OR the unresolved issues if its loop hits MAX_ITER."
  5. 报告格式回执："Return only: (a) final status (CONVERGED / NOT_CONVERGED), (b) any 🔴/🟡 still present with file:line, (c) any disagreements with the main-process review (i.e., issues that main process marked OK but you find suspicious)."

#### 4.4.3 子代理报告处理

主代理拿到子代理报告后：

| 子代理状态 | 主代理动作 |
|---|---|
| CONVERGED + 0 disagreements | 终态达成；输出 §4.5 最终报告 |
| CONVERGED + N disagreements（子代理认为某些项可疑） | 把 disagreements 注入主队列；**回到 §4.3 重启**（iter 计数继续累加） |
| NOT_CONVERGED + 仍有 🔴/🟡 | 把所有未解项注入主队列；**回到 §4.3 重启** |
| 子代理调用失败 / 超时 | 报告 `MPR_AGENT_FAILED`；不允许伪装"已通过 §4.4"；要求用户介入决定是否手工跑或允许跳过 |

#### 4.4.4 重启上限

- 每次回 §4.3 重启后，再次到达进程内收敛 → 再次跑 §4.4
- 这样的"§4.3 ↔ §4.4 往返"上限为 `--max-iter` 的 2 倍（默认 10）
- 若仍不收敛 → 报告 `NOT CONVERGED (process+isolated)`，列全部残留项；不允许声称完成

### 4.5 最终终态报告（仅当 §4.3 + §4.4 双双通过）

```markdown
# Paper Review v3 — Final Convergence Report

**Target**: <file_path> (N pages)
**Process-internal iters**: K
**Isolated MPR re-verifications**: J
**Final state**: ✅ 0 🔴 / 0 🟡 / 0 LaTeX errors / 0 AI-isms / all M-pass VERIFIED / 0 N (stale/drift) hits / 0 O (process artifact) hits / 0 P (internal/draft language) hits / 0 Q MISUSED + 0 missing-key-ref + 0 UNVERIFIABLE / isolated MPR CONVERGED

## A–Q dimension summary
[每维度一行：PASS + 关键证据]
- N (staleness sweep): N1 数字 / N2 叙述 / N3 推导 / N4 结论 / N5 图 / N6 表 / N7 残留 markup — 全 0 命中
- O (process artifact): O1 4-Tier grep / O2 4-类判定 / O3 update-not-accumulate / O4 每段 4 题 — 全 0 命中
- P (internal/draft language): P1 内部代号 / P2 草稿口语 / P3 实验日志风格 / P4 占位变量名 — 全 0 命中
- Q (reference precision): Q1 缺失关键文献 / Q2 \cite{} 精确度（CORRECT count + MISUSED 0 + UNVERIFIABLE 0）/ Q3 自引漂移 / Q4 格式一致

## M-pass 3-pass 痕迹（所有 VERIFIED 推导块）
| eq id | pass-1 method + result | pass-2 reviewer objections + responses | pass-3 invariant check |
|---|---|---|---|

## Numerical anchors verified
| Quantity | Paper claim | Source value | Status |

## Isolated MPR sub-agent report
[贴入子代理最终报告全文 — 不允许摘要]

## Convergence verification (cc-enslaver rule 06 + rule 07 自答)
1. 是不是真的解决了问题？✓ (具体证据: ...)
2. 有没有更好的解决方法？✓ (chosen min-effective-change at each fix)
3. 改动是否经过验证？✓ (re-compile + re-script + re-grep + 3-pass + isolated MPR)
4. 验证是否合理？✓ (covers root-cause causal chain at A–M 全维度)
5. (rule 07 覆盖性) 用户原始请求每一项均落实？✓
6. (rule 07 标准性) "完全没有任何遗留问题" / "直至零问题收敛" → 已落实为 §4.3 硬判据 + §4.4 隔离终验
7. (rule 07 忠实性) 无静默降级、无 TODO、无 future-work
```

---

## 5. 特别注意事项

- **不替用户改未授权的内容**：所有 🔴 修复要简短列在用户确认的 priority list 内；用户对争议项有最终决定权。
- **标注确定性**：审查者不确定的项必标 `[NEEDS EXPERT REVIEW]` 或 `[NEEDS VERIFICATION]`。
- **客观 vs 主观**：客观错误（数学错 / 物理错 / 数值不一致 / AI-ism）必标 🔴 / 🟡；纯风格偏好仅 🟢。
- **尊重作者意图**：理解论文核心信息，审查"是否有效传达"而不是"重写"。
- **每轮迭代独立**：iter k+1 不能依赖 iter k 的"印象"；必须从头再走第 1-3 阶段，重新打开所有源。
- **报告必须可执行**：每条 🔴 / 🟡 给 file:line + 当前文本 + 建议文本，不接受"全文检查 X" 类无定位反馈。

---

## 6. 反模式（绝对避免）

### 通用反模式（沿用 v2）

- ❌ "我 grep 了，没找到 X，所以没问题。" — grep 是定位工具不是验证工具。
- ❌ "根据上次对话，这个数应该是 Y。" — 上次对话不算证据，重新 Read 源文件。
- ❌ "abstract 和正文应该一致，跳过详细对比。" — 必须逐字 byte-for-byte 对比。
- ❌ "整体看起来还行，给个高分。" — 没有具体逐项证据的总评是无效的。
- ❌ "minor 问题忽略。" — 没有 minor，要么收敛要么继续修。
- ❌ "图我看了 caption 没问题。" — 必须 Read 实际图像内容。
- ❌ "引用我相信用户加的，没核对。" — 每条 bibitem 都要核对真实性。
- ❌ "em-dash 是合理标点保留。" — 学术写作不用 em-dash，必须 0 残留。

### v3 新增反模式（K / L / M / §4.4 相关）

- ❌ "公式量纲不严格但读者会理解。" — 量纲错误就是 🔴；改公式或显式标 `(schematic, illustrative)`。
- ❌ "schematic 公式不需要量纲一致。" — schematic 必须显式标注；未标 = 🔴。
- ❌ "改物理错误时加 disclaimer 绕过。" — 违反 §0.6；必须改公式 / 数值 / 假设到正确。
- ❌ "M.pass-1 看着没问题，pass-2 / pass-3 也大概率 OK 跳过。" — 违反 §0.7 + §2.M；3 pass 必须全独立跑，全 0 命中。
- ❌ "M.pass-2 adversarial 反驳列了 3 条，本文都没回应但 reviewer 不一定会问。" — 任一未回应反驳 = 🔴。
- ❌ "L 维度跨章节对位太繁琐，抽查几节就够。" — L 必须全章对位；漏一节就是上下文断层 🔴。
- ❌ "L4 companion paper 数字之前协调过的，跳过重读。" — 必须 Read companion 当前版本；记忆不算证据。
- ❌ "§4.3 还有 1 个 🟡 但是无关紧要，宣布收敛。" — 与 §0.8 / §4.3 硬判据不符；🟡 = 0 才算收敛。
- ❌ "§4.4 跳了，因为主进程已经合并了 M1–M9，跑两次没必要。" — 错；§4.4 的价值正是**独立上下文**消除框架偏见。除非用户显式传 `--skip-final-mpr`，否则必须跑。
- ❌ "§4.4 子代理调用失败，主代理直接声明 CONVERGED。" — 违反 §4.4.3；必须报 `MPR_AGENT_FAILED` 给用户决定。
- ❌ "§4.4 子代理报了 1 条 disagreement，但我看了不重要，丢弃。" — 必须注入主队列回 §4.3；不允许主代理单方面判子代理报告无效。
- ❌ "数学推导反复检查耗时太长，简化为 1 次 pass。" — 违反 §0.7 + §2.M；用户原话"必须多次反复"= 强制 3-pass 不可降级。
- ❌ "iter 用满 5 轮还没收敛，宣布完成附上未解清单。" — 违反 §4.3 末尾；ITER_BUDGET 用满 = 未收敛，必须 `BREAK_WITH_USER_DECISION`，不允许偷偷宣布完成。

### v3.1 新增反模式（N / O 维度专用）

- ❌ "§2.N7 残留 markup grep 命中 3 个 TODO，但都在 appendix 不影响主结论，保留。" — 违反 §2.N7 + §2.N8；残留 markup 必须 0 残留，无论位置。
- ❌ "这个数字 source 脚本没动过，复用上一轮的对位结果。" — 违反 §2.N1；必须当轮重跑、当轮对位；"印象中没变"不算证据。
- ❌ "dead figure / dead table 留着可能后续 reviewer 会问。" — 违反 §2.N5 / §2.N6；未被引用 = 删；reviewer 问的时候再加，不是"先囤着"。
- ❌ "stale 内容加个 footnote 说'之前的版本是这样'即可，不删。" — 违反 §2.N8 第 3 条；解释 stale 不算修复 stale。
- ❌ "保留 'we initially used method A but then adopted B' 让 reviewer 看到我们的思考过程。" — 违反 §2.O 类 1；过程残影默认删除，reviewer 关心的是当前科学声明不是作者旅程。
- ❌ "讨论了 abc 三个 alternative method 凸显本文方法的优越性。" — 仅当本文做了正式 head-to-head baseline 对照才允许（§2.O2 类 2）；否则属过程残影。
- ❌ "we tried X but it didn't work — 这句话信息量很大，留着。" — 违反 §2.O3；除非 X 是 well-known baseline 且有正式对照，否则默认删除（读者不需要知道未走通的弯路）。
- ❌ "每段 4 题信息量自检太繁琐，按经验只查感觉啰嗦的段。" — 违反 §2.O4；必须**每段**执行，不允许抽查。
- ❌ "N + O 命中很多，先标记着，下一 iter 再说。" — 违反 §4.3 硬判据表；N / O 命中数 = 0 是收敛硬条件之一，与 🔴/🟡 同级，必须当轮清零。
- ❌ "N 改了数字 + O 删了过程描述，但没重跑 grep 验证 0 残留。" — 违反 §2.O5 末句；修完两维度必须同时 re-sweep 确认 0 残留。
- ❌ "把 stale 内容移到 supplementary 当 'history of analysis' 保命。" — 违反 §2.O3 第 2 条；默认 supplementary 也不放过程历史；只有真有 retrospective 价值（如 method ablation）才允许，且必须显式标 'methodology history' section。

### v3.2 新增反模式（P / Q 维度专用）

- ❌ "`basically` 在这句话里是连接副词，删了不顺。" — 违反 §2.P2；不顺就重写，不靠草稿期口语补气。
- ❌ "`our pipeline` 是简洁表达，读者读得懂。" — 违反 §2.P1；外部读者不知道 "our" 指什么；改 "the pipeline described in §X"。
- ❌ "`v3_final` 是 git tag，不算 placeholder。" — 违反 §2.P1；git tag 是工程层；论文不暴露内部版本号。
- ❌ "`let me explain` 是友好语气，留着。" — 违反 §2.P2；论文不需要友好语气，需要客观陈述。
- ❌ "`We tried 5 methods` 是诚实记录。" — 违反 §2.P2（也可能 §2.O）；改为 `"We evaluated 5 methods"` 或正式 method 列表。
- ❌ "草稿期 placeholder `[PLACEHOLDER]` 在 appendix 不影响主结论。" — 违反 §2.N7 + §2.P1；任意位置 0 残留，无论 appendix / main body。
- ❌ "Q1 应引文献清单太长，挑 3 篇加。" — 违反 §2.Q1；🔴 关键文献遗漏必须**全部**补齐，不允许抽样。
- ❌ "我 WebSearch 了引用的 paper 摘要，主张大致对得上。" — 违反 §2.Q2；必须 WebFetch 该 paper 的 arXiv abs / DOI 页（不只摘要 search snippet），比对**具体**主张。
- ❌ "MISUSED 引用太敏感，软化措辞绕过。" — 违反 §2.Q2 + §0.6 物理优先（学术诚信类比）；MISUSED 必须改引正确文献，**不允许**软化措辞掩盖事实错误。
- ❌ "UNVERIFIABLE 引用因为 paywall 跳过。" — 违反 §0.8；必须或者获取原文（馆际互借 / 联系作者 / open-access 版本），或者**显式改弱**引用措辞使其不依赖未验证的具体主张。
- ❌ "P / Q 命中很多，本轮先修一部分，下轮再说。" — 违反 §4.3 硬判据表；P / Q 命中数 = 0 是收敛硬条件，必须当轮清零。
