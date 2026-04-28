---
name: paper-review
description: 严格审查论文。强制溯源、禁止猜测/记忆/关键词检索；按 /paper 标准 + 新增维度（数学/物理/逻辑/语言/AI-isms/数据一致性/图表对齐/接口对齐/冗余检测）逐项审查；支持迭代收敛 loop。
disable-model-invocation: false
argument-hint: "<file_path> [--max-iter N] [--no-fix] — 指定论文文件 (.tex/.md)，可选最大迭代轮数与只审不改"
---

> **v0 — ported verbatim from `weak-gravitational-lensing/.claude/skills/paper-review/SKILL.md`.**
> When this plugin is loaded, references to "/paper" mean the sibling skill
> `/sci-paper:paper`. The grep targets and review dimensions are field-agnostic
> and worth keeping as-is.

## 论文严格审查 — 执行规范（v2）

当用户调用 `/paper-review <file>` 时，按本规范对论文进行**强制溯源式**审查。
本 skill 不是"快速 lint"，是**审查 + 修复迭代器**。
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

---

## 1. 第一阶段：准备（必做，不可跳过）

1. **读 sibling skill `paper/SKILL.md`** — 内化写作标准，**特别是 Anti-AI-isms 节**。
2. **解析 field 并读 `style-profile/<field>/style_dossier.md`（若存在）** — 单 field 时自动选；多 field 时要求 `--field`；把 corpus 风格基线纳入审查标准。
3. **从头到尾 Read 论文全文**（不抽样、不关键词跳读）。超过 2000 行用 offset/limit 分块读完，**全部读过为止**。
4. **读取 `references.bib`** 以备后续逐条核对。
5. **生成"数字溯源清单"**：从论文里抽出所有数值（abstract / table / figure caption / 正文），列成待溯源 list。每条标记：值、出现位置、声称的来源、待核对状态。
6. **生成"图表清单"**：每个 `\includegraphics` / `\begin{table}` / `\begin{figure}` 的：图文件路径、caption 关键声明、引用的源脚本（grep `make_figures.py` / 项目内 figure 生成脚本）。
7. **读取 CLAUDE.md（项目根 + 用户全局）+ memory/MEMORY.md** 仅用于"找到源文件路径"，**不用于核对内容**（核对走源文件本身）。
8. 列出**接口对齐清单**：所有论文里的物理量符号 → 代码里的变量名 → 数据列名。三者必须 1:1 映射。

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

### I. 冗余 / 重复 / 过时审查

- [ ] **重复段落**：相同信息在不同节是否重复说？合并。
- [ ] **过时数据**：检查每个数字 vs 当前 source；任何 stale 数必须更新或删除。
- [ ] **被 supersede 的方法 / 结论**：旧推导 / 旧结果若已被新版替代，是否在论文里残留？删除。
- [ ] **死引用**：定义但未使用的符号 / 公式 / table / figure 删除。
- [ ] **多余 placeholder**：TODO / TBD / [PLACEHOLDER] / `\textcolor{red}{...}` 注释残留检查。
- [ ] **没有任何过时/错误的数据/推导/结果**：上一轮 audit 里被标记 SUPERSEDED 的内容必须从论文里清除。

### J. 可复现性审查

- [ ] 所有超参数列出（含随机种子）。
- [ ] 数据预处理步骤完整。
- [ ] Code/Data Availability section 存在且 link 实际可用（如 Zenodo / GitHub）。
- [ ] 软件 / 硬件版本声明（如 GPU 训练）。

---

## 3. 第三阶段：交叉验证

每个论文 vs 代码 / 数据要做 4 个对位：

1. **架构 vs 代码**：论文描述 = 项目 config / 模块结构。
2. **数值 vs 输出**：论文数字 = 脚本输出 / CSV cell。
3. **公式 vs 实现**：论文公式 = code function（必要时手动验证 1-2 个 corner case）。
4. **流程 vs 顺序**：论文 pipeline = main script 执行序列。

---

## 4. 第四阶段：输出报告 + 修复迭代

### 4.1 单轮报告格式

```
## 论文审查报告: <filename> — Iter <N>

### 总体评估
- 整体质量：[优 / 良 / 中 / 差]
- Top 3 关键问题：[...]
- 投稿状态：[可投 / 小修 / 大修 / 重写]

### A-J 各维度
[逐项 PASS / FAIL，FAIL 项给具体行号 + 证据 + 建议修改]

### 交叉验证发现
[paper vs code/data 不一致清单，每条给 paper 行号 + source 路径行号]

### 修改清单（按优先级）
1. 🔴 必改：[file:line + 当前文本 + 建议文本]（影响科学正确性）
2. 🟡 建议改：[同上]（影响可读性 / 表达 / AI-isms）
3. 🟢 可选改：[同上]（风格 / polish）
```

### 4.2 修复阶段（默认开启，除非传 `--no-fix`）

1. 用户确认 priority list 后，按 🔴 → 🟡 顺序逐条 Edit。
2. 每条修改后**重新读改动区域**确认改动符合预期。
3. 全部 🔴 / 🟡 修完后，**重新跑 LaTeX 编译**（`pdflatex` 或 `latexmk`）确认 0 error / 0 new warning。
4. 跑 `grep -n -E '—|---|\\textemdash' <file>` 确认 em-dash 全清。
5. 跑 AI-isms grep 确认全清。

### 4.3 收敛迭代（核心）

在用户传 `--max-iter N`（默认 N=5）下：

```
for iter in 1..N:
    report = full_review(file)
    if report.has_red() or report.has_yellow():
        apply_fixes(report)
        recompile()
    else:
        print "Converged at iter {iter}"
        break
else:
    print "NOT CONVERGED after {N} iter; remaining issues:"
    print report.unresolved
```

**收敛判据**（必须全部满足）：
- 0 个 🔴 issue
- 0 个 🟡 issue（🟢 可保留）
- LaTeX 编译 0 error / 0 new warning
- 数字溯源清单全绿
- AI-isms grep 0 命中
- em-dash 0 残留
- (若有 dossier) corpus-style lint 0 命中

**不接受**："基本干净，剩下都是 minor" — 必须收敛到 0 才算完。

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

- ❌ "我 grep 了，没找到 X，所以没问题。" — grep 是定位工具不是验证工具。
- ❌ "根据上次对话，这个数应该是 Y。" — 上次对话不算证据，重新 Read 源文件。
- ❌ "abstract 和正文应该一致，跳过详细对比。" — 必须逐字 byte-for-byte 对比。
- ❌ "整体看起来还行，给个高分。" — 没有具体逐项证据的总评是无效的。
- ❌ "minor 问题忽略。" — 没有 minor，要么收敛要么继续修。
- ❌ "图我看了 caption 没问题。" — 必须 Read 实际图像内容。
- ❌ "引用我相信用户加的，没核对。" — 每条 bibitem 都要核对真实性。
- ❌ "em-dash 是合理标点保留。" — 学术写作不用 em-dash，必须 0 残留。
