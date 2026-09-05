# Codex gpt-6-astra/max review of v0.36.0 / v0.36.1 (2026-09-04)

Read-only review of `git diff 9f0b920..edd480c`; session `01a06ebe-b4c5-7802-bfef-716f6310a097`. User decision 2026-09-04: record only, no code change in this pass. Part 1 is the first-party verification; Part 2 is the Codex report verbatim.

---

# Part 1 —— 第一方核实


来源：`out_A_scipaper.md`（32,525 B，16 条缺陷 + 投影不对称表 + 统计评估 + 缺失测试 + 漂移表）。
核实方式：逐条读代码 + 在内存中复现（`python - <<PY` 调 tools/），未改任何文件。

## 已复现（runtime）

| # | 声明 | 复现结果 | 代码位置 |
|---|---|---|---|
| A4 | `--require-shrink 100%` 被读成 1 个词；`10%`×5 词 → 0；`inf` 抛 OverflowError | `parse_required_shrink("100%")→1`，`"200%"→2`，`required_shrink_words(0.1,5)→0`，`"inf"`→OverflowError | tools/length_gate.py:197-218 |
| A5 | `$a$ $b$` 计 2 个 prose 词（占位符 `[math]` 进入 split） | `prose_word_count(M+"$a$ $b$") = 2` | tools/length_gate.py:44-45, extract_sections.py:193-210 |
| A2 | restatement 词袋忽略 negation/数字 | "is significant" vs "is not significant" → condense-restatement 14 词；`not` 在 STOPWORDS，RE_WORD 不含数字 | tools/condense_map.py:97-99,137-144; deai_collocation.py:73-79 |
| A1 | 预算重复计数 | 3 句重复：prose 46 词，target 75 词（restatement 30 + zero-gain 45 直接相加） | tools/condense_map.py:333-343 |
| A3 | Conclusion 里 `In summary, …` 整句零增益、无 carve-out | target 10 词，finding `genre_carve_out=None` | tools/condense_map.py:173-197,341 |

## 代码核实（读代码确认，未跑）

| # | 声明 | 判定 | 证据 |
|---|---|---|---|
| A6 | float 内空行 → caption 成独立段落进入 collocation/reference units | 成立 | deai_reference.py:203-214 `units()` 只 blank heading，不 blank float；collocation_findings 用 `reference.units` |
| A7 | heading/caption 里的 `TODO` 被 body_only 吞掉 | 成立 | deai_residue.py:310 `edit_meta_findings(body, path)`，body=register.body_only 已 blank heading+float |
| A8 | diff rule 按单个词干判"删除"，非完整对象 | 成立 | deai_residue.py:287-289 `removed=[s for s in stems if s in old_body and s not in new_body]` |
| A9 | 无 section 文档 / `\section {X}` / `\section[S]{X}` 静默漏检 | 成立 | deai_metrics.py:25-27 RE_SECTION_HEADER 无 `\s*`、无 `[..]`；deai_reference.py:159-164 丢弃 `(document)` |
| A10 | `p_absent_by_chance` 是 passage 共现而非相邻 | 成立（只影响排序/展示，不影响 gate） | deai_collocation.py:145-149, 203-212 |
| A11 | 定义句豁免全句所有词 | 成立 | deai_register.py:428-429 `defined.update(... for word in words)` |
| A12 | `^\s*\\newcommand` 吃掉前面空行 → 行号偏移 | 成立（`^\s*` 跨行） | deai_register.py:355-356 |
| A13 | `\input` 装配丢同一行前后文字；第二次 `\input` 同文件返回空 | 成立 | extract_sections.py:366-381 |
| A14 | `alpha/beta`、`alpha 500 beta` 连成 pair | 成立 | deai_collocation.py:104-115 RE_PAIR_BREAK 无 `/`、`.`、数字 |
| A15 | AUC 样本量门槛在 NaN 过滤前 | 成立 | eval_findings.py:161-166, 295 |
| A16 | control 排除用 `evidence.text`（不存在） | 成立 | label_findings.py:257-263 |
| 结构 | `structure_findings` 不 blank heading → wh-cleft 与标题融合 | 成立 | deai_structure.py:262-266 无 without_headings |
| 口径 | `/1k` 分母是 raw `text.split()`，非正文词 | 成立 | eval_findings.py:133,149 |
| 漂移 | collocation finding `scope/calibration_unit="paragraph"` 但 unit="sentence" | 成立 | deai_collocation.py:218-224 |
| 漂移 | RE_PAPER_AGENT 无 `presents`，文档/CHANGELOG 说有 | 成立 | deai_structure.py:59-63 |

## 不成立 / 需要打折

- "unittest 465 项报 141 errors"：A 的 sandbox 禁止建临时目录导致；本机 2026-09-04 已跑 465 OK（发布前）。validator 同理。
- "非星号 deluxetable 未覆盖"：A 自己也确认已覆盖（extract_sections.py:103-104）。
- p90/p95 plateau 顶端读法：是文档化的设计选择（deai_reference.py:77-84），A 复算的实际 strong 率 4.4–5.4%，advisory 12–15%，偏差有限；值得在 EVALUATION 记录 tie policy，不算 bug。
- 主表数值（held-out zero 2.212/1k、AUC .246；collocation 2.031/1k、AUC .691）A 只读复算一致。

## 建议动作分级

1. **应修（行为错误）**：A4 shrink 解析；A5 占位符计词；A1/A3 预算并集 + zero-gain carve-out；A2 negation/数字守卫；A7 edit-meta 扫可见 heading/caption；A8 完整对象比较；A9 sectionless/`\section {`/`[S]`；A12 `^[ \t]*`；A13 include 行内装配；结构 heading blank。
2. **应改文档/元数据**：`/1k` 分母口径；collocation scope=sentence；`presents`；定义豁免、名字豁免写进 standard；p_absent 降为 co-presence heuristic 或改名；tie policy。
3. **可延后**：A10 相邻 null；A15/A16 评估器与标注器；A14 pair 边界；统一 TeX 分解层（大工程）。

---

# Part 2 —— Codex 报告原文

## 1. 结论摘要

- 删除预算可重复计数；`--require-shrink` 可把百分比误读成词数，也可接受实际零删减。当前 gate 不能可靠证明完成了目标。`tools/condense_map.py:337`、`tools/length_gate.py:200`
- 投影仍不对称：逐行 citation、按空行切开的 floats、section 识别和二次 macro 展开均有可复现差异。`tools/deai_register.py:370`、`tools/deai_reference.py:210`、`tools/deai_register.py:599`
- residue 会漏掉 heading/caption 中的 `TODO`；diff rule 又可把未曾存在的完整对象判为“被删除”。`tools/deai_residue.py:310`、`tools/deai_residue.py:288`
- register/collocation 主表及 AUC 已只读复算复现；“每千正文词”实际使用 raw text 的 `split()` 分母。`tools/eval_findings.py:133`、`tools/eval_findings.py:161`
- 已尝试两项检查：validator 在临时目录创建处中断；unittest 执行 465 项，报 141 errors，存在 sandbox 临时目录错误，不能宣称通过。相关 fixture 创建处：`tools/validate_plugin.py:642`。单独只读执行 residue mirror check 通过。`tools/deai_residue.py:343`
- 受版本控制的文本文件无超限；四个文件只剩 0–1 行余量，拆分建议见 §7。`README.md:750`、`docs/SCIPAPER_STANDARD.md:749`、`tools/extract_sections.py:750`、`tools/fetch_arxiv_abstracts.py:750`

## 2. 缺陷清单

以下 `M = "\\section{Methods}\n"`；字符串中的 `\n` 表示实际换行。数值均由当前代码在内存中复现，未修改文件。

1. **major · [tools/condense_map.py:337](D:/Projects/sci-paper/tools/condense_map.py:337) · 删除预算重复计算同一文字。**  
   触发：令 `s = "In this section we describe precise galaxy cluster signal maps calibrated against independent external measurements."`，输入 `M + "\n\n".join([s] * 3)`。实际 `prose_words=46`，默认目标 **75 words**：三个 zero-gain 加两个 restatement 重叠计数。建议：保存可删除字符区间，计算区间并集；分别报告候选质量和确认可删除质量。`tools/condense_map.py:328`、`tools/condense_map.py:343`

2. **major · [tools/condense_map.py:144](D:/Projects/sci-paper/tools/condense_map.py:144) · 相同词袋被当作相同科学声明。**  
   触发：在 Methods 中依次写 `The calibrated galaxy cluster mass signal measurement across independent radial apertures is significant.` 和把 `is significant` 改成 `is not significant` 的版本。第二句被判 restatement，计入 14 words 目标；数字变化也不会进入该词集合。建议：先核对 negation、numbers、units、comparisons 等 protected invariants；仅有 lexical overlap 时不能生成整句删除目标。`tools/condense_map.py:97`、`tools/condense_map.py:150`

3. **major · [tools/condense_map.py:173](D:/Projects/sci-paper/tools/condense_map.py:173) · 开头套语被等同于整句无信息，且 zero-gain 没有 genre carve-out。**  
   触发：`\section{Conclusion}\nIn summary, we measure a galaxy mass of five units.` 被要求删除全部 **10 words**；`M + "In this paper we measure a galaxy mass of five units."` 被计入 **11 words**。建议：默认只预算删除 opener；整句删除须确认无独有声明；对 zero-gain 同样应用 abstract/conclusion carve-out。`tools/condense_map.py:178`、`tools/condense_map.py:183`、`tools/condense_map.py:341`

4. **major · [tools/length_gate.py:200](D:/Projects/sci-paper/tools/length_gate.py:200) · shrink 参数的单位、取整及边界不可靠。**  
   触发：`100% → int(1)`、`200% → int(2)`；5-word 文档的 `10% → 0 words`；无候选时 map 返回目标 `0`，parser 却拒绝；`inf`/`1e309` 抛出未捕获的 `OverflowError`。建议：显式区分 percentage、fraction、word count；验证有限值和范围；最低删减用 `ceil`；允许零词目标完成 dry sweep。`tools/length_gate.py:208`、`tools/length_gate.py:221`、`tools/length_gate.py:277`、`tools/condense_map.py:348`

5. **major · [tools/length_gate.py:45](D:/Projects/sci-paper/tools/length_gate.py:45) · gate 的计数和输入范围不符合“rendered prose”。**  
   触发：`M + "$a$ $b$"` 被计为 **2 words**；删除两条公式便产生两词“删减”。此外，`main.tex` 只有 `\input{body}` 时，修改 child 不改变 gate 的输入；map 却分析组装后的全文。建议：对两版使用相同的 document assembly 和 prose-only 计数，移除 math/float placeholders；快照必须覆盖整个 include graph 或保存组装后的基线。`tools/extract_sections.py:195`、`tools/length_gate.py:282`、`tools/condense_map.py:380`  
   residue 的 `--git-ref` 同样只读旧版 root，而 after 已组装，diff 比较范围不同。`tools/deai_residue.py:394`、`tools/deai_residue.py:399`

6. **major · [tools/deai_reference.py:210](D:/Projects/sci-paper/tools/deai_reference.py:210) · float 修复仍被“先分段、后投影”绕过。**  
   触发：`M + "\\begin{figure}\n\n\\caption{alpha beta gamma delta epsilon.}\n\n\\end{figure}"`。caption 成为独立 prose unit；令这五词 common、四个 pair 未见且 reference 有 spread，即产生 strong collocation finding。语料侧先投影整个 section，会删除该 float。建议：在 section/paragraph/sentence 切分前识别并处理完整环境，保留 source offsets。`tools/deai_collocation.py:260`、`tools/extract_sections.py:197`、`tools/extract_style.py:393`

7. **major · [tools/deai_residue.py:310](D:/Projects/sci-paper/tools/deai_residue.py:310) · 可见编辑标记被 vocabulary projection 吞掉。**  
   触发：`\section{Results TODO}\nClean prose.`，或 `\begin{figure}\n\caption{TODO}\n\end{figure}` 放在 Results 下，均没有 residue finding；正文独立 `TODO` 则 strong。建议：residue 的 edit-meta 扫描保留可见 headings、captions、table text；不要复用排除这些内容的词汇投影。另将跨行 `in the revised\nversion` 按规范化空白扫描，当前逐行 regex 漏报。`tools/deai_register.py:344`、`tools/deai_residue.py:204`

8. **major · [tools/deai_residue.py:288](D:/Projects/sci-paper/tools/deai_residue.py:288) · diff rule 检查的是任一消失的词干，不是完整对象。**  
   触发：before 为 `M + "The correction is applied."`；after 为 `M + "The measurement is applied.\n\\caption{Without the saddle correction}"`。得到 strong，虽然 `saddle correction` 从未在 before 出现。另把旧 caption 的 `Blue points` 改成 `Red points`，也会将原有 negation 当成新增。建议：比较 canonical negated object；确认完整对象 before 存在、after 缺失；对象新旧不能由整段 caption 字符串决定。`tools/deai_residue.py:280`、`tools/deai_residue.py:285`

9. **major · [tools/deai_reference.py:162](D:/Projects/sci-paper/tools/deai_reference.py:162) · 无 section 的文档静默漏检。**  
   触发：纯文本 `We no longer use this method.`，或前加 `\section {Methods}` / `\section[Short]{Methods}`，self-history 均无 finding；condense 的句子扫描同样为空。原因是 section regex 不接受这些合法形式，随后 `(document)` 被丢弃。建议：共享 section parser；无 heading 时保留 document unit，不能套用 bucket baseline 的轴明确标为 unavailable。`tools/deai_metrics.py:25`、`tools/deai_metrics.py:120`、`tools/condense_map.py:119`

10. **major · [tools/deai_collocation.py:145](D:/Projects/sci-paper/tools/deai_collocation.py:145) · `p_absent_by_chance` 计算了错误事件。**  
    触发：100 passages 全为 `alpha and omega`，两词 df 均为 100，adjacent pair 从未出现。代码给 `alpha omega` 的 λ=100、absence≈`3.7e-44`，实际上估计的是 passage 内共同出现，未建模有序相邻。建议：采用保留句长和 token boundaries 的 adjacency null；否则将该字段明确降为 co-presence heuristic，不能称为 pair absence probability。`tools/deai_collocation.py:112`、`tools/deai_collocation.py:203`

11. **minor · [tools/deai_register.py:419](D:/Projects/sci-paper/tools/deai_register.py:419) · 定义句给整句所有词自动豁免。**  
    触发：`M + "We define flux using quuxification."` 把 `quuxification` 标为 `defined-here`，即使定义对象只有 `flux`。建议：提取被定义的 noun phrase；无法确定对象时保留 strong 并请求 disposition。`tools/deai_register.py:447`

12. **minor · [tools/deai_reference.py:176](D:/Projects/sci-paper/tools/deai_reference.py:176) · 行号并未保持。**  
    触发：`M + "\\paragraph{A\nB}\n\nWe no longer use this method."` 实际第 5 行被报为第 4 行；替换 heading 时换行也变成了空格。另 `M + "\n\\newcommand{\\q}{word}\nWe no longer use this method."` 中 register 将第 4 行报成第 2 行；`\s*` 吃掉了前面的空行。建议：任何 blanking 保留换行，并统一保存字符到原文件行号的映射。`tools/deai_register.py:355`  
    其他定位问题：abstract 使用环境起始行；condense acronym 固定报第 1 行；多句段落的每句共用段落范围。`tools/deai_reference.py:152`、`tools/condense_map.py:241`、`tools/condense_map.py:123`

13. **minor · [tools/extract_sections.py:375](D:/Projects/sci-paper/tools/extract_sections.py:375) · include assembly 有损，新工具继承该问题。**  
    触发：root 为 `Before \input{body} After\n`，child 为 `Child`，组装结果只有 `Child`；连续两次 `\input{body}` 只保留一次。建议：按匹配区间替换，保留前后文字；用 recursion stack 检测环，不能把全部已访问文件当成环；同时返回 child 的 source map。`tools/extract_sections.py:366`、`tools/extract_sections.py:382`

14. **minor · [tools/deai_collocation.py:104](D:/Projects/sci-paper/tools/deai_collocation.py:104) · 非相邻 token 被连成 pair。**  
    触发：`content_pairs("alpha/beta gamma delta epsilon")` 和 `content_pairs("alpha 500 beta gamma delta epsilon")` 均包含 `("alpha","beta")`；`.` 无空白时也如此。建议：先产生带类型和跨度的 tokens；只连接相邻且中间没有 punctuation、number、placeholder 的 word tokens。`tools/deai_collocation.py:111`

15. **minor · [tools/eval_findings.py:295](D:/Projects/sci-paper/tools/eval_findings.py:295) · AUC 的样本量门槛在删除 NaN 前执行。**  
    触发：两组各 20 rows，其中各 19 个 `collocation_novel_fraction=NaN`，余下一组 0、一组 1，仍输出 AUC=1.0。空文档在存在 bank 时也被标为 collocation `measured`。建议：按轴统计有效 documents/eligible sentences，过滤后再应用 floor；零可测内容不能报告 measured。`tools/eval_findings.py:171`、`tools/deai_collocation.py:179`、`tools/deai_collocation.py:192`

16. **minor · [tools/label_findings.py:262](D:/Projects/sci-paper/tools/label_findings.py:262) · flagged passage 会进入 unflagged controls。**  
    触发：正常 finding 被放入 `evidence`，其中没有顶层 `text`；排除集合于是得到 `""`，同一段不会被排除。建议：用 `source + span/unit_id` 排除全部已命中 unit，而不是读取不存在的字段；控制样本不能仅排除已抽中的部分 findings。`tools/label_findings.py:229`、`tools/label_findings.py:240`、`tools/label_findings.py:268`

## 3. 投影不对称候选清单

“语料侧”包含入库后的再次 `latex_to_plain`，不能只比较第一次清洗。`tools/extract_style.py:393`、`tools/deai_register.py:599`、`tools/deai_collocation.py:296`

| 构造 | 手稿侧当前行为 | 语料侧当前行为 / 判断 |
|---|---|---|
| 多行 `\citep{\nNeverSurname2020}` | register 收到 `neversurname`，因为逐行清洗。`tools/deai_register.py:370` | 整段 citation 替换为 `[CITE]`。**确认不对称**。`tools/extract_sections.py:121` |
| 多行 `\ref` | `mass\ref{\nOddLabel}map` 产生 `mass`、`oddlabelmap`。`tools/deai_register.py:375` | 整段变成 `massmap`。**不对称且两侧都有 fusion 问题**。`tools/extract_sections.py:123`、`tools/extract_sections.py:201` |
| `\section {Methods}` | metrics 不识别，blanking 也不删除标题。`tools/deai_metrics.py:25`、`tools/extract_sections.py:158` | corpus section splitter 接受空格并排除标题。**确认不对称**。`tools/extract_sections.py:155` |
| `\section[Short]{Methods}` | heading 可被 blank，但不能正确分 bucket。`tools/extract_sections.py:158`、`tools/deai_metrics.py:25` | section splitter 不接受 optional title；在已有 section 下，标题会进入 prose。`tools/extract_sections.py:155` |
| `\paragraph` / `\subsubsection` | register/reference 删除。`tools/deai_register.py:344`、`tools/deai_reference.py:176` | corpus splitter 不将其视为 section，generic cleaning 留下标题文字。**确认不对称**。`tools/extract_sections.py:155`、`tools/extract_sections.py:207` |
| 深层 nested heading braces | 超过一层 nesting 时 blanking 失败。`tools/extract_sections.py:159` | section regex 同样只支持一层，可能无法切 section。**共同限制，后续过滤结果可不同**。`tools/extract_sections.py:155` |
| topic subsection / appendix child | manuscript 不继承 parent bucket；`Acknowledgments → Special` 的正文可进入 register。`tools/deai_metrics.py:125`、`tools/deai_register.py:323` | corpus 继承 parent，尤其继承 `skip`。**确认不对称**。`tools/extract_sections.py:500` |
| 无 sections / preamble-only | register 保留 title、documentclass 等词；reference 丢弃整个 `(document)`。`tools/deai_register.py:323`、`tools/deai_reference.py:162` | corpus 返回 unknown，随后不入 exemplar bank。`tools/extract_sections.py:481`、`tools/extract_style.py:391` |
| `\footnote`、`\thanks` | 简单参数保留，紧贴正文时会融合，例如 `mass\footnote{Rareword}`。`tools/extract_sections.py:207` | 简单形式相同，**并非已排除的 body 外内容**；参数内 bare macro 经第二次清洗后又可不同。`tools/deai_register.py:599` |
| float 外 `\tablenotetext{a}{Tied…}` | register 删除；nested 第二参数可能只删除第一参数，余下 prose 泄漏。`tools/deai_register.py:113` | generic cleaning 留下 `aTied…`。**确认不对称**。`tools/extract_sections.py:207` |
| 非星号 `deluxetable` | **已覆盖**，与 star 形式一起整块 blank。`tools/deai_register.py:344` | 同一 regex 同样覆盖，不能列为当前漏项。`tools/extract_sections.py:104` |
| float 内空行 | register 全文 blank；collocation/reference 先切段，caption 可泄漏。`tools/deai_reference.py:210` | corpus 先清洗整个 section，再分 paragraph。**确认不对称**。`tools/extract_style.py:393` |
| `minipage` 内 `\caption` | 不属于 float regex，caption 及尺寸参数留下；如 `3cm` 可融合成 `cmOddcaptionword`。`tools/extract_sections.py:104`、`tools/extract_sections.py:205` | 同样保留。**共同污染**，不是当前已解决的 caption 情况。`tools/extract_sections.py:207` |
| `\marginpar`、`\todo` | 参数保留，可能与前文融合。`tools/extract_sections.py:207` | 简单形式相同。**共同污染**；`\todo{...}` 也不等同于 case-sensitive `TODO` literal。`tools/deai_residue.py:88` |
| `verbatim`、`lstlisting` | 环境名删除，内容留下。`tools/extract_sections.py:128` | 相同。**共同污染**；若内容含 TeX commands，还会被错误解释。`tools/extract_sections.py:207` |
| `\verb`、`\texttt`、`\url`、`\path`、`\href` | register 删除 code/URL；href 只留下 display text。`tools/deai_register.py:117` | generic cleaning 留下 code、URL 或 verb delimiters 内内容。**确认不对称**。`tools/extract_sections.py:207` |
| `\[...\]`、`subequations` | register 明确 blank。`tools/deai_register.py:97` |普通 projection 没有这两种完整规则；内容可能留下。**确认不对称**。`tools/extract_sections.py:99` |
| `sub-\nhalo`、`\-` | TeX 词汇扫描得到 `sub`、`halo`。`tools/deai_register.py:76`、`tools/deai_register.py:370` | TeX 路径相同；PDF 路径将 `sub-\nhalo` 拼成 `subhalo`。**跨格式不对称**。`tools/extract_sections.py:622` |
| `--` ranges | manuscript 排除少于三字母的 `a--c`；collocation 会在 `--` 断开。`tools/deai_register.py:364`、`tools/deai_collocation.py:104` | register calibration 只检查字符串长度，仍可索引 `a--c`。`tools/deai_register.py:601` |
| unit macros：`\si{\kilo\metre}` | 一次 cleaning 后留下 `kilo`、`metre`。`tools/deai_register.py:375` | 第一遍留下 nested macro，入库后第二遍将其删除。**确认不对称**。`tools/extract_sections.py:207`、`tools/deai_register.py:599` |
| 自定义 word macro | `\newcommand{\foo}{\mathrm{quuxword}}` 的 `\foo` 被 register 还原为 `quuxword`。`tools/deai_register.py:280`、`tools/deai_register.py:371` | corpus 普通 prose cleaning 不作同等展开，bare `\foo` 被删除。`tools/extract_sections.py:207` |
| `thebibliography` 无 References heading | manuscript 整块排除；同一行旁边的正常 prose 也被一起删除。`tools/deai_register.py:326` | corpus 没有对应 whole-environment 删除规则，可能把条目留在前一 section。`tools/extract_sections.py:195`、`tools/extract_sections.py:205` |
| Unicode / 两字母词 | `café → caf`、`Müller → ller`，`AI` 不记录；“every body word”不成立。`tools/deai_register.py:76`、`tools/deai_register.py:364` | ASCII tokenizer 共同限制；仅 PDF 路径额外展开 typographic ligatures。`tools/deai_register.py:599`、`tools/extract_sections.py:627` |

另有**抽样范围差异**：语料不收 unknown、以 placeholder 开头或不在长度范围内的 paragraphs；manuscript zero audit 没有同样的 passage eligibility。故 df=0 还包含 bank selection 的影响。`tools/extract_style.py:391`、`tools/extract_style.py:401`、`tools/extract_style.py:404`

## 4. 统计方法评估

- **λ 的 N：单位一致，但事件不一致。**  
  df 是 passage presence，所以 `df_a·df_b/N` 的 N 应是 passage 数，不能直接换成 sentence 数或 paper 数。不过它估计的是独立词的 passage co-presence，未估计有序 adjacency；自配对 `a=a` 更不满足两个独立事件。即便只研究 co-presence，独立 passages 下的零出现概率也是 `(1-p_a p_b)^N`，`e^-λ` 还需 rare-event approximation。当前 bank 记录的是 distinct words/pairs per passage。`tools/deai_collocation.py:145`、`tools/deai_collocation.py:294`  
  此概率目前影响 pair evidence 的排序，**不决定 finding gate**；gate 使用 sentence novel fraction percentile。`tools/deai_collocation.py:204`、`tools/deai_collocation.py:270`

- **LOO：pair count 的 passage-level 排除成立，完整 held-out calibration 不成立。**  
  `own_passage=True` 将 pair_df=1 视为未见，正确排除了该 passage 对 pair presence 的一次贡献。但 unigram df、common-word membership、N 未重算；同一 paper 的其他 passages 仍在 bank，source 信息甚至在 `_passages` 被丢弃。应称为“固定词表下的 passage LOO”，不能等同于 document-held-out reference。`tools/deai_collocation.py:136`、`tools/deai_collocation.py:139`、`tools/deai_collocation.py:281`、`tools/deai_collocation.py:320`

- **`MIN_JUDGED=4` 与 distinct-pair：有明确 selection 和离散性影响。**  
  四个 judged types 只能得到 0、¼、½、¾、1；重复同一 pair 不增加有效样本量，长的重复句也可能 abstain。另一方面，document score 又计算所有 pair occurrences，包含不足四对的句子。因此 gate 和 AUC 使用不同统计量；这是代码明确实现的选择，应同时报告 eligible sentence coverage。`tools/deai_collocation.py:135`、`tools/deai_collocation.py:151`、`tools/deai_collocation.py:161`

- **p90/p95 不是固定 10%/5% operating rate。**  
  代码取 `P(X≤x)` 的 plateau 顶端，再与 .90/.95 比较。构造 `[0]*80 + [.5]*19 + [1]` 时，`.5` 被读为 p98，**20%** 样本都 strong；spread guard 仍通过。`tools/deai_reference.py:90`、`tools/deai_reference.py:124`、`tools/deai_collocation.py:214`  
  对现有 bank 只读重算 LOO：method advisory **13.70%**、data **14.68%**、discussion **12.30%**；对应 strong **5.44% / 4.42% / 4.54%**。应保存 empirical tail counts，选择 strict quantile exceedance 或明确 tie policy。计算路径：`tools/deai_collocation.py:318`、`tools/deai_reference.py:77`

- **AUC 与 rates：主表可复现，分母名称有误。**  
  复现 held-out zero **2.212/1k、100% documents、AUC .246**；collocation **2.031/1k、99.0%、AUC .691**。但 `/1k` 是 `1000·Σfindings/Σraw_words`，不是 per-document median，也不是 body-token rate；zero 的逐文档 rate 中位数实算为 **1.611/1k**。`tools/eval_findings.py:133`、`tools/eval_findings.py:149`  
  register AUC 按逐文档 finding density 排序；collocation AUC 按 document **token-pair fraction** 排序。这两种口径代码有明确区分，不能把 .691 解释成 sentence gate 的 AUC。`tools/eval_findings.py:85`、`tools/eval_findings.py:166`

- **.855 与 .691 的差别不是同一实验算错。**  
  §23 明确将 .855 标为 first-1,500-word prototype，当前值是全篇 document fraction。比较还应控制长度、年代和 generation regime，并按 paper/source 做 bootstrap；现有输出只有点估计。`docs/architecture/evaluation/vocabulary-and-residue.md:80`、`tools/eval_findings.py:295`

- **document fraction 不能代替 sentence gate transfer。**  
  一篇论文有很多 eligible sentences，至少一次 finding 的概率自然累积；99% document flag rate 不能直接解释为 sentence false-positive rate。当前 evaluator 没有保存 collocation eligible sentence denominator。`tools/deai_collocation.py:254`、`tools/eval_findings.py:128`

- **residue 的 203 篇是调参集。**  
  strengths 在这批 papers 上反复修改，不能再把同批 rate 当独立验证；它也没有 edit-history ground truth 来估计 recall。文档承认后一点。`docs/architecture/evaluation/vocabulary-and-residue.md:174`、`docs/architecture/evaluation/vocabulary-and-residue.md:225`  
  §23.4 的 `24 in 20 papers` 对应 **9.85% papers**，不是随后写的 12%。按当前产品入口去注释后，实算 self-history strong **24/20 papers**、edit-meta strong **16/12 papers**，合计 **31/203 papers**；旧调参表应标明版本，不能作为 v0.36.1 当前 rate。`docs/architecture/evaluation/vocabulary-and-residue.md:181`、`docs/architecture/evaluation/vocabulary-and-residue.md:190`、`tools/ai_ism_lint.py:359`、`tools/deai_residue.py:304`

- **labeller 当前不能给出有效 population recall。**  
  除 control 污染外，`caught` 累加各轴 finding，`missed` 计算 control paragraphs；同一 passage 多轴命中会重复计 TP，抽样 quotas 也没有 inclusion-probability correction。须统一到去重的 passage/unit，并采用概率抽样或完整子集标注。`tools/label_findings.py:217`、`tools/label_findings.py:341`、`tools/label_findings.py:352`

## 5. 缺失测试

| 可直接实现的用例 | 必要断言；当前覆盖不足的位置 |
|---|---|
| `test_budget_unions_overlapping_spans` | §2.1 三个重复句：目标不能超过实际唯一可删除字数。现有测试反而断言两规则直接相加。`tests/test_condense_map.py:113` |
| `test_restatement_preserves_negation_and_numbers` | 相同词汇、不同 negation/数值/单位的句子不能进入确定删除目标。`tests/test_condense_map.py:65` |
| `test_zero_gain_keeps_unique_result_and_carveout` | Conclusion 的 `In summary, we measure…` 不预算整句；仅 opener 可缩短。现有 carve-out 只测 restatement。`tests/test_condense_map.py:124` |
| `test_shrink_units_rounding_and_empty_map` | 5 words 的 10% 要求至少 1 word；`100%/200%` 按已声明范围拒绝，不能解释为 1/2 words；`inf`、`1e309`、`30%%` 返回配置错误；零词目标可完成 dry sweep。`tests/test_length_gate.py:148` |
| `test_math_placeholder_has_zero_budget` | 增删任意数量 inline/display math 均不改变 prose count；tolerance 必须设 0。现有 math test 的 tolerance=2 会掩盖 placeholder 增长。`tests/test_length_gate.py:59` |
| `test_gate_assembles_both_versions` | root 不变、child 缩短时识别 shrink；`--before` 和 `--git-ref` 使用一致的完整版本树。当前读取入口不同。`tools/length_gate.py:282`、`tools/deai_residue.py:394` |
| `test_projection_parity_matrix` | 对 §3 每个构造比较实际 corpus pipeline 与 manuscript tokens；覆盖 multi-line cite/ref、unit macro、外置 tablenote、非星号 deluxetable、minipage、深层 braces。现有 float test 主要覆盖 star 环境和 manuscript 一侧。`tests/test_deai_register.py:316` |
| `test_float_with_blank_lines_stays_excluded` | figure/table 内空行和 comment-only 行不能让 caption/cells 进入 collocation units。`tools/deai_reference.py:210` |
| `test_edit_meta_in_visible_labels` | heading、caption、table cell 中的 `TODO` 和跨行 revision phrase 必须被正确扫描。当前 literal 测试没有这些上下文。`tests/test_deai_residue.py:72` |
| `test_diff_matches_objects_not_shared_stems` | `correction → without saddle correction` 不得声称删除了 saddle object；旧 negation 仅改 caption 颜色不算新增 negation。`tests/test_deai_residue.py:128` |
| `test_no_sections_and_empty_measurement` | sectionless history 能扫描；没有 eligible sentences 的 calibrated axis 不得返回无说明的 measured；LF/CRLF 结果一致。`tools/deai_reference.py:162`、`tools/deai_collocation.py:192` |
| `test_offsets_survive_multiline_markup` | §2.12 分别断言 L5、L4；abstract 正文和 acronym 返回真实行；include finding 返回 child path/line。现有 line test 未覆盖这些场景。`tests/test_deai_register.py:271` |
| `test_definition_only_exempts_defined_term` | `We define flux using quuxification` 不能给后者 defined-here；Unicode 名称不切成伪词。`tests/test_deai_register.py:185`、`tools/deai_register.py:76` |
| `test_structure_heading_gap_is_irrelevant` | ≥30-word wh-cleft 在 heading 后一个换行与两个换行结果相同。当前 `structure_findings` 未 blank heading；已复现前者漏报、后者命中。`tools/deai_structure.py:264`、`tests/test_deai_structure.py:86` |
| `test_collocation_boundaries_and_minimum` | `/`、数字、无空白句点不制造 pair；3/4 judged types 边界；重复 pair 不改变 distinct verdict。`tests/test_deai_collocation.py:71` |
| `test_loo_matches_explicit_removal` | 与显式移除 passage 后重建 bank 比较，包括 common df 正好在 floor 的词；现有 LOO test 仅断言最大 novelty 大于 0。`tests/test_deai_collocation.py:91` |
| `test_tied_gate_and_valid_auc_floor` | 使用 80/19/1 plateau；AUC 有效样本过滤后不足 20 应 unmeasured。`tests/test_eval_findings.py:174`、`tests/test_deai_collocation.py:140` |
| `test_controls_exclude_all_flagged_units` | 同 source/span 不能同时 flagged/control；多个轴命中同段只计一个 recall TP。`tests/test_label_findings.py:193` |
| `test_dead_artifact_edge_cases` | 无 label 的 float、deluxetable/longtable、合法 `\ref {x}`、两个未使用的 macro definitions。当前仅 figure/table regex、要求 labels，macro uses 还计入其他 definitions。`tools/condense_map.py:85`、`tools/condense_map.py:200`、`tools/condense_map.py:226` |

## 6. 文档与代码漂移

| 文档原话 | 当前实现 |
|---|---|
| “The only mechanical exemption … formation of an attested stem”。`docs/architecture/evaluation/vocabulary-and-residue.md:19`；standard 同样只列 stem。`docs/SCIPAPER_STANDARD.md:160` | 还自动返回 `"defined-here"`、`"name"`。这符合本次用户给出的意图，应该修文档，同时收紧定义对象识别。`tools/deai_register.py:447` |
| “This paper presents” 属于 paper-as-agent。`CHANGELOG.md:85`、`docs/SCIPAPER_STANDARD.md:181` | regex 没有 `presents`；测试明确名为 `test_paper_that_merely_presents_is_not_an_agent`。`tools/deai_structure.py:59`、`tests/test_deai_structure.py:79` |
| “three-plus tokens **before a head noun**”。`docs/SCIPAPER_STANDARD.md:183` | `MODIFIER_STACK_RUN=3` 检查的是含 head 的 phrase 长度；`non-compensated 500-configuration subfamily` 仅两个 pre-modifiers 已足够。`tools/deai_structure.py:80`、`tools/deai_structure.py:113` |
| restatement：“≥80% … another section (**or** ≥60% … one sentence)”。`skills/condense/SKILL.md:84` | 实际为 `union >= .80 and best >= .60`，且没有要求另一 section。`tools/condense_map.py:137`、`tools/condense_map.py:144` |
| “outside the abstract/conclusion carve-out”。`docs/SCIPAPER_STANDARD.md:575` | zero-gain finding 不带 `genre_carve_out`，budget 将缺失值视为未豁免。`tools/condense_map.py:183`、`tools/condense_map.py:342` |
| “Comments and mathematics do not count … rendered prose”。`docs/SCIPAPER_STANDARD.md:584` | `latex_to_plain(...).split()` 将 `[math]`、`[MATH]`、`[FIGURE-OR-TABLE]` 计为词。`tools/length_gate.py:45`、`tools/extract_sections.py:195` |
| “The unit is the sentence”。`docs/architecture/evaluation/vocabulary-and-residue.md:92` | finding 写 `scope="paragraph", calibration_unit="paragraph"`，但 `reference.unit="sentence"`。应修 schema metadata 和 sentence spans。`tools/deai_collocation.py:218`、`tools/deai_collocation.py:224` |
| “Rates per 1,000 body words”。`docs/architecture/evaluation/vocabulary-and-residue.md:24` | `n_words = len(text.split())`，包括 raw source 中的非正文内容。`tools/eval_findings.py:133` |
| “A pair the field would write by chance has been seen”。`docs/SCIPAPER_STANDARD.md:194` | 代码允许高 `p_absent_by_chance`，且 finding 不按此概率过滤。文档不能把未见直接解释成 coinage/figure of speech。`tools/deai_collocation.py:203`、`tools/deai_collocation.py:271` |

mirror check 确实比较了两处 **22 个词的集合**；它不验证 strong/ordinary 分组，也不验证 self-reference/citation 的语义条件。该检查不能证明更广的文档行为一致。`tools/deai_residue.py:337`、`tools/deai_residue.py:353`

## 7. 值得做的显著改进

1. **建立保留 source map 的统一 TeX 分解层。**  
   输出 prose、heading、caption、math、code、bibliography 等 typed spans；各轴明确选择需要的 spans，再切 sentence/paragraph。这样能同时解决 whole-span 投影、重复 cleaning、bucket inheritance 和行号问题；residue 仍可保留 visible caption 的编辑标记。当前分裂点：`tools/deai_register.py:344`、`tools/deai_reference.py:210`、`tools/extract_sections.py:193`

2. **把评估结果固化为可复算 artifact。**  
   保存 commit、corpus/profile/projection hashes、raw/body word counts、eligible sentence counts、tie policy、source grouping 与有效 AUC 样本量；文档从 artifact 提取。当前 §23 新表没有进入 published-figure 检查清单，现有 AUC 输出也没有这些有效样本元数据。`tests/test_published_figures.py:315`、`tests/test_published_figures.py:335`、`tools/eval_findings.py:297`

3. **执行 line budget，并按职责拆分临界文件。**

   | 文件 | 当前行数 / 余量 | 建议 |
   |---|---:|---|
   | `tools/extract_sections.py:750` | 750 / 0 | 分出 TeX projection、source assembly；section/PDF 解析保留独立职责。现有职责入口：`tools/extract_sections.py:193`、`tools/extract_sections.py:344`、`tools/extract_sections.py:452` |
   | `tools/fetch_arxiv_abstracts.py:750` | 750 / 0 | 分离 arXiv client/cache 与采集选择、CLI；避免继续压缩控制流来凑行数。 |
   | `README.md:750` | 750 / 0 | 将详细 benchmark/evaluation 表移到 evidence docs，README 保留入口和当前状态。`README.md:715` |
   | `docs/SCIPAPER_STANDARD.md:749` | 749 / 1 | 保留规范条款；将实证缘由、历史比较和长解释移入 EVALUATION，以链接引用，维持单一规范权威。`docs/SCIPAPER_STANDARD.md:269`、`docs/SCIPAPER_STANDARD.md:632` |

   为受版本控制的文本增加只读 line-count check；当前 validator 的十项 checks 没有该硬限制。`tools/validate_plugin.py:712`