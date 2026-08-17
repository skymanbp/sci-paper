---
name: paper
description: Load the unified SCIPAPER_STANDARD writing guidance, formula derivation conventions, scientific-integrity rules, canonical L0 examples, and field-specific reference anchors for ApJ/MNRAS/PRD-level papers. Use when writing or reviewing scientific content.
disable-model-invocation: false
---

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> This skill supplies concrete scientific-writing guidance and canonical L0
> examples. It does not define an independent paper verdict. If this file, a
> style profile, or a workflow conflicts with the unified standard, the unified
> standard wins. Project-specific anchors remain marked `[WGL]`.

## Paper Writing Standards / 论文写作标准

Target: **Top-tier astrophysics journals** (ApJ, MNRAS, A&A level).

### General Principles

- **Accuracy over elegance.** Never sacrifice precision for readability. Every claim must be verifiable.
- **Quantitative over qualitative.** Replace vague descriptions with numbers. Not "significantly improved" but "AUC increased from 0.834 to 0.927 (+11.1%)".
- **Reproducibility.** The Methods section must contain enough detail for an independent researcher to reproduce all results. All hyperparameters, data splits, and evaluation protocols must be specified.

### Structure and Narrative

A motivation → method → validation arc is a useful default for many empirical
papers, not a universal document template. Theory papers, methods papers, data
releases, and multi-contribution papers may require a different shape. In every
case, make the contribution graph explicit: explain how the claims relate, place
definitions before use, and ensure that each conclusion is supported by the
presented argument or evidence.

When the three-part arc fits:

1. **Motivation**: identify the scientific problem, prior limitations, and the
   specific gap addressed.
2. **Method**: present physical motivation, mathematical formulation, and
   implementation in dependency order.
3. **Validation**: state what the results establish, compare like with like, and
   delimit the evidence and limitations.

#### 文章主旨 / Thesis spine — one result, everything subordinate to it

> **Normative authority: `docs/SCIPAPER_STANDARD.md` §5.4.** That section is
> the policy; this is how to write to it. It is a writing rule, not a measured
> axis — no linter reports it and none may be built on it without new evidence
> (EVALUATION §15.1).

The arc above says what *order* to write in. It does not say what to leave out,
and that is where drafts fail: an arc filled with everything the authors did is
still an inventory. Choose the one result first, then let the arc carry it.

**Before drafting or revising any section, write the thesis line.** One
sentence, the paper's single central result. Not the topic, not the method, not
a list — the finding. Everything in the paper then exists to 铺垫 / 介绍 /
解释 / 推理 / 论证 that sentence. A second result is either subordinate to it
or belongs in a second paper.

The reader must finish able to answer three questions **in this order**:

1. 我们做了什么 — what was done;
2. 成果是什么 — what the result is;
3. 牛逼在哪里 — what it changes that was not true before.

A draft that answers only (1) is an inventory however well written. A draft
that answers (1) and (2) but not (3) has reported a measurement and not made a
claim. Question (3) is the one that must be argued, not asserted: name what was
previously believed, or previously impossible, and what this result replaces it
with.

**The inventory test.** Build this table before editing, and again after:

| section | the one sentence it contributes to the thesis | where it is carried |
|---|---|---|

A section with no such sentence is inventory: cut it, or fold its load-bearing
clause into a section that has one. Two sections whose sentences say the same
thing are one section. Any row a reader can falsify in seconds is doing its
job; a row you cannot fill is the finding.

**Do not confuse this with condensing.** `/sci-paper:condense` removes what is
**repeated**; this removes what is **unranked**. A section can be perfectly
non-redundant, fully sourced, and still be an inventory entry.

**Rank, do not delete, the supporting results.** A result that does not carry
the thesis is not thereby worthless: state it where it does work, in one
sentence, subordinate to the claim it supports. A number that is the sole
support of a claim never leaves the paper (§6 eligibility).

**Never cut to sharpen.** Conditions, ranges, uncertainties, scope limits,
negations, and conceded limitations are load-bearing by definition and are
never inventory, however secondary they sound. A paper made punchier by
deleting its hedges has been damaged.

### Structural Updates · Forward Narrative / 结构式更新 · 正向叙述

> **每一次写作、修订、纠错都必须把文章重写到"当前真值的最终态"——禁止把"旧态 → 新态"的迁移痕迹留在正文里。**
> 本节是 `paper-review` §O ("Process-artifact removal") 的**写作端对偶**：
> 审查端默认 *删除* 过程残影；写作端默认 *一开始就不写进去*。

**正向叙述（forward narrative）—— 唯一合法形式**

正文只描述当前科学声明的最终态。读者应看到：

- ✅ "We use method B; the result is X."
- ✅ "Equation (3) gives Y, which we then evaluate at $z = 0.5$."
- ✅ "We adopt $H_0 = 67.4\,\mathrm{km\,s^{-1}\,Mpc^{-1}}$."

读者**绝对不该**看到（无论初稿还是修订稿）：

- ❌ "我们一开始尝试了 A，发现 A 不对，所以改用 B"
- ❌ "We did A, found it gave incorrect results, and therefore switched to B"
- ❌ "Method A would have suggested X, but in fact ..."（除非这是本文有意做的 baseline 对照，见下"唯一例外"）
- ❌ "An earlier version of Eq. (5) had a factor-of-2 error; the corrected form is ..."
- ❌ "Note: the previous draft used $H_0 = 70$; the present analysis uses $H_0 = 67.4$."
- ❌ "After several iterations we converged on the following architecture."

**Patch（禁）vs Structural（要）—— 修订时的硬区分**

发现错误 / 公式不对 / 数字漂移 / reviewer 指出问题时：

- ❌ **Patch 式修改**：在错误旁注释"原方法 A 错在 …，因此现采用 B"；保留旧公式 + 加 footnote 解释"现已修正"；保留旧数字 + 加括号给"修正后值"；段尾追加"this supersedes our earlier claim that ..."。
- ✅ **Structural 式修改**：**删掉 A 的所有痕迹**，从段首重写到段尾，让正文呈现为"从一开始就一直是 B"。读者无法从论文本身推断出 A 曾经存在过。

| Patch（禁） | Structural（要） |
|---|---|
| "We initially used $H_0 = 70$; later we adopted $H_0 = 67.4$." | "We adopt $H_0 = 67.4$." |
| "An earlier version of Eq. (5) had a factor-of-2 error; the corrected form is ..." | 只保留 Eq. (5) 的正确形式；下游推导全部 propagate 重写。不提"earlier version"。 |
| "Method $M_1$ failed due to overfitting; we therefore use $M_2$." | "We use $M_2$." |
| "After several iterations we converged on the following architecture." | 只描述最终 architecture。 |
| "上一版图 3 的曲线已更新；新的拟合参数为 ..." | 只展示新图 3 + 新参数。 |

**唯一例外 —— 真正的 baseline 对照**

仅当**全部三条**满足时，可以在正文中保留"方法对照"：

1. 被对照的方法是 **领域内已发表的外部 baseline / prior published method**——**不是作者自己的早期迭代**；
2. 本文对该对照做了**正式 head-to-head 实验**并给出**数值**；
3. 呈现方式是 *"contrast with baseline X (Smith+2020) on protocol P → numerical comparison"*，**不是** *"we initially tried X"* 这种第一人称自传式。

判定时若任一条不满足 → 默认按 "Patch（禁）" 处理，重写到只剩当前方法。

**写作时强制自检（每段 / 每次修订执行）**

1. 这段是不是**只**描述了当前最终态？（如果包含过去态，删掉过去态。）
2. 一个从未参与本研究的读者，看了这段会觉得有别的方案 / 旧版本存在过吗？如果会 → **重写**。
3. 修订时新增的内容是"重写过的最终态"还是"在旧态上贴的补丁"？是补丁 → **撕掉补丁、重写整段**，不要"补丁 + 解释为什么打补丁"。
4. 是否出现 *initially / originally / previously / at first / earlier / now / currently / corrected / revised / updated / supersedes* 等过程时间词指向**本文自身研究进程**？任一命中 → **重写**。（指外部科学时间维度的不算，例如 "recent supernova observations" / "previously published catalogs"。）

**与 "Formula Derivation Standards" 中"射箭画靶"的关系**

下节的"No shooting arrow then drawing target / 禁止射箭画靶"是本规则在**公式推导场景的窄特例**（"我想得到 X 结果，所以改了推导步骤"）。本节是更广的写作准则——覆盖正文叙述、方法描述、结果呈现、讨论、结论：**整篇论文的任一段落都适用**。

### 改写不堆叠 / Condense, Do Not Accumulate

> 规范条文：`docs/SCIPAPER_STANDARD.md` §5.3。用户规则 2026-07-16：
> "改写、删减、精简，而不是堆叠！"

- 每次修改的默认方向是**更短**。优先级：删除 > 原位精简 > 等长改写 > 增长。
- 增长只有两种合法理由：用户要求的新内容，或来源可验证的科学必需
  （缺失的假设/定义/单位/caveat 属 integrity 缺陷）。
- 典型违规是**解释性补丁**：对被标记的句子追加从句、句子或脚注去"解释"，
  而不是重写句子本身。上节 forward narrative 禁止堆叠**状态**；本节禁止
  堆叠**字数**。
- 每处修改报告字数差；靠加字消除 detector 信号是缺陷，不是修复。
- **机械执行**（标准 §5.3 v3.3）：改写候选经 `rewrite_reward.py --original`
  硬门（超长即 `-inf`）；编辑循环收尾经 `length_gate.py` delta 门
  （无理由净增长 = exit 1，循环不得收尾）。增长的唯一合法路径是
  `--allow`/`--allow-growth` 记录的作者批准理由。

### Formula Derivation Standards / 公式推导规范

- **Multi-line derivations**: Use `align`/`gather` environments for complete mathematical derivations, not single-line equations. Show the logical chain: a = b (1), then a = c (2), therefore b = c (3).
- **Definition completeness**: Every variable, compound term, or logical construct appearing in a formula MUST be either (a) previously defined in the text, or (b) defined/derived immediately near the formula. Never introduce undefined symbols.
- **No inline formulas for complex expressions**: Any formula longer than ~30 characters must be a displayed equation, not inline text. Short expressions (e.g., `$\kappa \ll 1$`) can remain inline.
- **Logical flow over format**: Don't force a rigid template. Derivations should flow naturally — define when needed, derive when needed, summarize at the end. The priority is that reasoning is clear and logically connected.
- **No "shooting arrow then drawing target" / 禁止射箭画靶**: Never write "we wanted X result so we changed to Y approach" or reference historical/deprecated formulas. Present: method → result → conclusion. Do not discuss the iterative path that led to the current approach. *（公式推导场景的窄特例；广义写作准则见上节 "Structural Updates · Forward Narrative"。）*
- **No outdated content**: Only present current formulas and label definitions. Do not reference deprecated versions in the paper body — at most a brief footnote if essential for context.
- **Summary block**: After a derivation chain, include a brief summary: "We therefore obtain [final formula], where [key quantities] are [definitions]. This shows [physical conclusion]."

### Physics Descriptions [WGL]

- Describe weak lensing physics using standard notation (Bartelmann & Schneider 2001 conventions).
- Clearly distinguish between: convergence (kappa), shear (gamma), reduced shear (g), aperture mass (M_ap), and S/N maps.
- When describing the detection pipeline, maintain the distinction between signal (E-mode) and noise (B-mode).
- All filter functions must be written with explicit mathematical definitions, not just names.

### Method Descriptions

- For each ML model, specify: architecture, input representation, loss function, training procedure, and evaluation metric.
- For ensembles, explain the aggregation strategy and why it is appropriate given any class imbalance.
- Clearly state any transfer learning protocol: what was pretrained, on what data, and how fine-tuning differs.
- For grouped/leave-one-out CV: explain why grouping is necessary and how group IDs prevent leakage.

### Results Presentation

- All performance metrics must include: (a) the metric name and definition, (b) the evaluation protocol, (c) uncertainty estimates where possible.
- Tables should be self-contained — a reader should understand the table without reading the text.
- Figures should have: descriptive captions, labeled axes with units, legends, and consistent color schemes.
- When comparing methods, use the same evaluation protocol for all. Never compare training metrics of one model to validation metrics of another.

### Discussion and Limitations

- **Honestly discuss limitations.** Acknowledge sample-size and selection-effect limits.
- Distinguish between: limitations of the method vs. limitations of the data.
- For detection-boundary analyses: discuss where sim-to-real transfer breaks down and why.
- Avoid overclaiming. Detection frameworks are not definitive physical measurement tools.

### Anti-AI-isms / 去 AI 表达规范

LLM 生成的学术写作有一组明显的 tell；本节保留既有 L0 词汇与标点
目标，同时把结构、信息分布和 learned field-similarity 信号纳入统一反馈协议。
`style-profile/<field>/style_dossier.md`、lexicon 和 baseline 是可更新的经验
证据，不是独立政策，也不能把论文判为 AI 或非 AI。后续动作由
`docs/SCIPAPER_STANDARD.md` 的 consequence class、measurement state、ranking
和 disposition 规则决定。

**根本层（fundamental）—— 结构性 AI 味，关键词 lint 抓不到。** 本节后面
列出的 Tier A/B 是**词汇层**（lexical），必要但不充分：一篇文章可以 0 关键词命中、
甚至逐段读着都像人，却仍通篇 AI 味。真正的 tell 活在结构里，分两个尺度：

1. **信息分布层**（token / 句长）：过度均匀的信息密度、句长同质、重复的
   signposting 和缺少局部节奏变化。由 distribution 与 UID axes 度量。
2. **句式与文档形状层**：句子或段落的构造被重复模板化。需要重点检查：
   - **报数式枚举**：`rests on five elements. First, ... Fifth, ...` /
     `there are three reasons`。
   - **先设数目 → 列举 → 收尾**：`inherits three obligations. [A][B][C].
     These three requirements ...`。
   - **排比 / 首语重复**：≥3 句同一开头或同一模态（`must ... must ... must`）。
   - **对称收尾**：`A is one limit of it, and B another`。
   - **段落或章节同形**：多个段落重复相同的主题句、展开和收束几何。

这些模式不是单次出现即错误。它们在适用 baseline 下构成测量证据；阈值、样本量、
置信度和效应量属于 `EVALUATION.md` 或 profile calibration，不写死在规范里。

这一层由 de-AI 子系统统一度量（`docs/architecture/DEAI_SUBSYSTEM.md`）：

```bash
python tools/ai_ism_lint.py <file> --field <field> \
  --structure --distribution --document-structure --oracle --voice \
  --format json --output <scratch>/writing-feedback.json
```

- Tier A、em-dash 和超过每节每词 cap 的 Tier B 是 `l0_target`。
- 句式模板、burstiness、UID、document shape 与 learned field-similarity 是
  advisory；必须保留 `measured` / `degraded` / `unmeasured` / `not_applicable`
  区别，不能把缺失测量当作零命中。
- 命中的段可用 `/sci-paper:de-ai`（Pass 3）从 claim graph 重建，而不是做
  同义词替换。任何候选先通过 scientific-fidelity eligibility，再比较风格证据。
- 强 advisory 必须行动或显式 disposition；普通 advisory 可以保留并报告。

因此，Tier A / em-dash 清零与 Tier B cap 是 L0 地板；结构和信息分布信号用于
排序后续动作，不构成必须全部归零的通用 prose gate。

**最强 L0 标点目标：em-dash (`—` / `\textemdash` / `---`)**

- 正文目标为 0。插入语改用逗号、括号、分号或独立句；范围使用 `--`。
- 该规则是项目锁定的 L0 policy。当前 corpus 频率及比较值只在 profile 和
  `EVALUATION.md` 中维护，避免把会漂移的测量写进规范。

**Tier A — L0 target**

正文命中必须重写。canonical set：

| 类别 | 词 |
|---|---|
| 动词类 | `delve / delves / delving / delved`, `leverages / leveraging / leveraged`, `pave / paves / paving`, `shed / sheds / shedding`（含 "shed light on"）, `showcase / showcases / showcasing`, `utilizing / utilizes`, `underscore / underscores / underscored / underscoring` |
| 形容词/副词 | `seamless / seamlessly`, `holistic / holistically`, `comprehensively`, `crucially`, `pivotal` |
| 名词类 | `tapestry`, `testament`, `realm / realms` |
| 段首套话 | `Recent advances in...`, `Despite significant progress...`, `With the advent of...`, `In recent years,...`, `It is worth noting`, 段首 `Crucially,`, `Importantly,`, `Notably,`, `Interestingly,` |

2026-07-16 扩充（`underscore*`, `pivotal`, `tapestry`, `testament`, `realm*`）
采自 academic-humanizer 词表（MIT，见文末 Provenance），并经两域 curated
corpus 复核为 0 出现后才入 Tier A；`landscape` 虽在其词表中，但它是本领域
正当术语（detection landscape 等，corpus 高频），**不入表**。

替换原则：使用直接、具体、可核验的动词或范围，不做机械同义词交换。例如
`leverages X to Y` → `uses X to Y`，`pave the way for` → `enable`，
`comprehensively` → 明确列出覆盖范围。

**Tier B — per-section/per-word cap**

Tier B 可以使用，但同一个 Tier B 词在同一 section 最多出现 1 次。第 2 次及
以后是 `l0_target`；cap 内的出现不是 finding。当前词表由 linter 与 profile
共同维护，常见项包括 `Furthermore`, `Moreover`, `Additionally`,
`robust/robustly`, `comprehensive`, `utilize/utilized`, `leverage`,
`Importantly`, `Interestingly`, `Notably`, `intricate`,
`foster/fosters/fostering/fostered`（后两组 2026-07-16 加入；curated corpus
各有 1 次出现，非零故不入 Tier A）。经验频率只从当前 profile 读取，不在
本文件复制。优先用直接陈述或可验证数字，但不要为了避词而损害准确性。

**模糊量化 / 修饰词**
- `a wide range of`, `a variety of`, `a number of`, `several`, `numerous`,
  `many`：有可核验数量时写数量；没有时检查该模糊程度是否科学必要。
- `cutting-edge`, `state-of-the-art`, `novel`, `powerful`：需要明确比较对象和证据，
  否则删除。它们是 claim-quality advisories，不因单词本身自动成为 L0 target。

**自指与套话**
- `This paper presents...` / `In this work, we...` 类 boilerplate 每段最多 1 处。
- 删除：`In summary,`, `To summarize,`, `In conclusion,`（除 conclusion 节外）。

**LLM 高频动词替换（dossier 未实证但语法层面是 tell）**
- `facilitate` → `enable`
- `In order to` → `To`
- `aim to` → `we [verb]`（直接动词）
- `serves as` → `is`（copula 回避；linter `style-substitution` advisory）

**结构 tell（L2 advisory）**
- repeated parallel frames，例如连续三句相同首语或 modal；
- announced enumeration 与 setup/list/wrap-up symmetry；
- 多段重复相同开场、展开和收束几何；
- `X — that is, Y` 同时触发 em-dash L0 target 与可能的冗余 advisory；
- **分词尾巴（-ing tail）**：`..., highlighting/underscoring/demonstrating X`
  把解读挂在句尾冒充分析深度。改写为带主语和证据的独立句，或删除
  （linter `ing-tail` advisory）；
- **阐释式冒号（colon-appositive）**：`X: the rule that ...` 这类
  "名词: 展开" 结构是 `X — that is, Y` 的冒号变体。改写为限定从句、
  两个句子或 ", so ..."；caption 标签（`Left: ...`）与真正的列表规格
  说明可保留（linter `colon-elaboration` advisory；用户规则 2026-07-16）。

结构模式必须结合 section、样本量、calibration 和科学功能判断。技术列表若编码真实
分类，不应为了制造参差而破坏可读性。

**punctuation / 排版**
- 数字与单位之间用 `\,`（thin space），不要 LLM 习惯的普通空格。
- 千分位用 `\,`（thin space）或 `,`，不要无分隔。
- 不要在文中写 `etc.`（学术写作可接受但 LLM 滥用），改为完整列举或具体范围。

**review 阶段的强制 grep**

```bash
# em-dash：必须 0
grep -n -E '—|---|\\textemdash' main.tex

# Tier A（必删；正文中不允许出现，包括变体）
grep -n -E -i '(delve|leveraged|leverages|leveraging|paved?|paves|paving|shed[s]?|shedding|showcase[sd]?|showcasing|seamless(ly)?|holistic(ally)?|comprehensively|crucially|utilizes|utilizing|underscor(e|es|ed|ing)|tapestry|testament|pivotal|realms?|recent advances|despite significant|with the advent|in recent years|it is worth)' main.tex

# Tier B（定位；是否超过每节每词 cap 由 linter 按 section 计算）
grep -n -E -i '^\s*(Furthermore|Moreover|Additionally|Importantly|Interestingly|Notably),' main.tex
grep -n -E -i '\b(robust|robustly|comprehensive|utilize|utilized|leverage|intricate|foster(s|ing|ed)?)\b' main.tex

# 顽固替换组（不分级）
grep -n -E -i '\b(in order to|aim to|facilitate|serves as)\b' main.tex

# 结构 advisory 定位（-ing 尾巴 / 阐释式冒号）
grep -n -E -i ',\s+(highlighting|underscoring|showcasing|emphasi[sz]ing|illustrating|demonstrating|signal[l]?ing|revealing|reflecting)\b' main.tex
grep -n -E '([A-Za-z0-9]|\}): [a-z$\\]' main.tex
```

**Tier A / em-dash 残留** = `l0_target`。
**Tier B 超频** = 同词在同 section 的第 2 次及以后为 `l0_target`。

> **Companion evidence from `/sci-paper:de-ai` calibration:** corpus assets supply
> descriptive frequencies and calibration. Re-run `python tools/extract_style.py`
> when the corpus changes. They may suggest future policy changes, but do not
> silently redefine the current consequence classes or cap.

### Claim–Evidence Discipline / 声明-证据纪律

> QD 类规则（claim-evidence defects 在 SCIPAPER_STANDARD §2 QD 下是
> `integrity_blocker`）。本节给出操作化检查；条目改编自 academic-humanizer
> Layer 4（MIT，见文末 Provenance），并按天体物理语料重校准。

对每个经验性声明检查两件事：(a) 它是否有正文内的数字、图、表或引用支撑；
(b) 动词强度是否不超过证据强度。

- **无支撑声明 → 补证据指针或降级。**
  ❌ *Our method is more robust.*
  ✅ *Our method's accuracy drops by 2 points under distribution shift,
  versus 11 points for the baseline (Figure 3).*
- **动词强于证据 → 降级。**
  ❌ *This demonstrates that our method is universally superior.*
  ✅ *On these three datasets, our method matches or exceeds the strongest
  baseline (Table 2).*
- **模糊量级 → 有归属的数字或区间。**
  ❌ *a large improvement.*  ✅ *a 2--6\% improvement in balanced accuracy
  over the strongest baseline.*
  区间优于单一均值（除非均值方法已声明）；每个数字注明方法、指标、基线。
  做比较时先打最强对手，不打平凡基线。
- **`significantly` 必须有伴随检验或数字**；孤立的 "significantly better"
  是声明缺陷。注意这是**证据条件规则，不是词法禁令**：astro curated corpus
  中 `demonstrate*`（0.147/1k）与 `significantly`（0.274/1k，合并语料实测
  2026-07-16）都是正常用词，禁词式移植（ML 会议口味）会误伤本领域写作——
  只有"动词/副词超出证据"才构成 finding。

### 防过度纠正 / Preserve List（rewrite 护栏）

> 改编自 academic-humanizer Layer 3（MIT）。De-AI 重写循环的反向风险是
> "把校准的 hedging 改强"——这会**制造** over-claiming，比留下 AI 词更糟。
> 与 SCIPAPER_STANDARD §6 rewrite eligibility（stance/modality/qualifier
> 不可变）同源；此处是写作端明细。

- **证据绑定的 hedging 是正确且必需的。** `suggests`, `is consistent
  with`, `we hypothesize that`, `may indicate`, `appears to` 在声明真有
  不确定性时**保留**。把 *"the results suggest X"* 改成 *"the results
  prove X"* 是制造 over-claim，属 rewrite eligibility 违规。
- **被动语态**在施动者无关时合法：*"Samples were normalized to total
  protein."* 不要为主动而主动。
- **第一人称复数 "we"** 是学术标准，不改写回避。
- **分号与偶发三联**适度可用；em-dash 是唯一零容忍标点。
- **正式定义、命名方法/指标、术语、公式、符号**逐字保留。
- **数字、公式、引用永不发明、丢弃或改动**；cite key 全保留。

### Citation Standards

- Only cite papers that genuinely support the claim being made.
- For established results, cite the original paper, not a review (unless the review adds value).
- For software: cite the primary paper for each library.
- **Never fabricate or hallucinate citations.** If unsure, flag with `[CITATION NEEDED]`.

### Key References / 关键参考文献 [WGL]

- **Weak lensing formalism**: Bartelmann & Schneider (2001), Schneider et al. (1998)
- **Aperture mass / Schirmer filter**: Schirmer et al. (2007), Schneider (1996)
- **NFW profile**: Navarro, Frenk & White (1996, 1997)
- **E(2)-equivariant CNNs**: Weiler & Cesa (2019), `escnn` library
- **Swin Transformer**: Liu et al. (2021)
- **SBI / Neural Posterior Estimation**: Cranmer, Brehmer & Louppe (2020)
- **Persistent homology / TDA**: Edelsbrunner & Harer (2010)
- **LoVoCCS survey**: Fu et al. (2022)

### Provenance / 借鉴出处

The 2026-07-16 additions (Tier A/B word extensions, `serves as`, the
-ing-tail and colon-elaboration structure tells, the Claim–Evidence
Discipline section, and the Preserve List) adapt material from
[academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer)
(MIT License, Copyright (c) 2026 AIScientists-Dev, itself building on
blader/humanizer, MIT). Every lexical adoption was re-verified against the
curated field corpora before tier assignment; venue-specific rules that
conflict with astro usage (`landscape`, blanket `demonstrate`/
`significantly` bans) were deliberately not adopted.
