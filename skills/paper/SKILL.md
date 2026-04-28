---
name: paper
description: Load paper writing standards, formula derivation conventions, citation rules, and key references for ApJ/MNRAS/PRD-level astrophysics papers. Use when writing or reviewing paper content.
disable-model-invocation: false
---

> **v0 — ported verbatim from `weak-gravitational-lensing/.claude/skills/paper/SKILL.md`.**
> Project-specific anchors (NFW, ACSDM, escnn, LoVoCCS) are marked `[WGL]` for
> later generalization. Keep them as-is for now since the primary user is
> still writing in this domain.

## Paper Writing Standards / 论文写作标准

Target: **Top-tier astrophysics journals** (ApJ, MNRAS, A&A level).

### General Principles

- **Accuracy over elegance.** Never sacrifice precision for readability. Every claim must be verifiable.
- **Quantitative over qualitative.** Replace vague descriptions with numbers. Not "significantly improved" but "AUC increased from 0.834 to 0.927 (+11.1%)".
- **Reproducibility.** The Methods section must contain enough detail for an independent researcher to reproduce all results. All hyperparameters, data splits, and evaluation protocols must be specified.

### Structure and Narrative

The paper should follow a clear three-act structure:

1. **Motivation** (Introduction): Why is the problem important? What are the limitations of existing methods? What gap does this work fill?
2. **Method** (Sections 2–4): How does each component work, and why was it designed this way? Physics motivation first, then mathematical formulation, then implementation.
3. **Validation** (Sections 5–6): What do the results show? How do they compare to existing work? What are the limitations?

### Formula Derivation Standards / 公式推导规范

- **Multi-line derivations**: Use `align`/`gather` environments for complete mathematical derivations, not single-line equations. Show the logical chain: a = b (1), then a = c (2), therefore b = c (3).
- **Definition completeness**: Every variable, compound term, or logical construct appearing in a formula MUST be either (a) previously defined in the text, or (b) defined/derived immediately near the formula. Never introduce undefined symbols.
- **No inline formulas for complex expressions**: Any formula longer than ~30 characters must be a displayed equation, not inline text. Short expressions (e.g., `$\kappa \ll 1$`) can remain inline.
- **Logical flow over format**: Don't force a rigid template. Derivations should flow naturally — define when needed, derive when needed, summarize at the end. The priority is that reasoning is clear and logically connected.
- **No "shooting arrow then drawing target" / 禁止射箭画靶**: Never write "we wanted X result so we changed to Y approach" or reference historical/deprecated formulas. Present: method → result → conclusion. Do not discuss the iterative path that led to the current approach.
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

LLM 生成的学术写作有一组明显的 tell；学术 reviewer 一眼可识，必须清除或限频。
本节规则按 **corpus 实证频率分级**——参见 `style-profile/<field>/style_dossier.md` §4
的 lexicon 表与 §3 的段落首词清单。第一级（Tier A）顶刊 corpus 中 0 出现，
绝对禁止；第二级（Tier B）顶刊偶用，但 LLM 滥用，需限频。
**dossier 是数据真值；本节是 dossier 的 prose 解释 + 阻塞 grep 实现**。

**最强 tell：em-dash (`—` / `\textemdash` / `---`)**
- 学术写作的破折号传统上用 `--` (en-dash, 范围) 或 `,` / `;` / `:` / `(...)` (插入语)。
- 顶刊 corpus 实测：0.098 / 1000 词（dossier §2，N=16 wgl corpus 实测
  20 em-dashes 跨 203 251 词）；LLM 默认 5–15 / 1000 词，差 50–150 倍。
- **0 残留**：写作时禁用 em-dash；review 时必须 grep `—` / `---` / `\textemdash` 清零。如必须做插入，用逗号或括号；如做范围（页码、年份），用 `--` (en-dash)。

**Tier A — 真零容忍（顶刊 corpus 0 出现 → 100% LLM tell）**

正文中 grep 命中 = 🔴 必改。这类词在顶刊 wgl corpus 里**完全不存在**，
LLM 默认会用，是最强 lexical tell。

| 类别 | 词 |
|---|---|
| 动词类 | `delve / delves / delving / delved`, `leverages / leveraging / leveraged`, `pave / paves / paving`, `shed / sheds / shedding`（含 "shed light on" 短语）, `showcase / showcases / showcasing`, `utilizing / utilizes` |
| 形容词/副词 | `seamless / seamlessly`, `holistic / holistically`, `comprehensively`, `crucially` |
| 段首套话（dossier §3 0 出现）| `Recent advances in...`, `Despite significant progress...`, `With the advent of...`, `In recent years,...`, `It is worth noting`, 段首 `Crucially,`, 段首 `Importantly,`, 段首 `Notably,`, 段首 `Interestingly,` |

替换原则：
- `delve / dive into` → `examine` / `analyze` / `study`
- `leverages X to Y` → `uses X to Y` 或 `Y by means of X`
- `pave the way for` → `enable` / 删
- `shed light on` → `clarify` / `show`
- `showcase` → `demonstrate` / `present`
- `seamless / seamlessly` → 删（或具体描述）
- `holistic` → `complete` / 删
- `comprehensively` → 替换为可量化形容词 + 范围（"covering X, Y, Z"）

**Tier B — 顶刊偶用，每节限频**

这类词在 corpus 中**有出现**（频率 ≤ 0.15 / 1000 tokens，参见 dossier §4），
不构成必删依据，但 LLM 远超此频率使用。规则：**用，但每节 ≤ 1–2 次**，
review 时 grep 出超频段落标 🟡。

下表频率基于 N=16 篇 wgl corpus（203 251 tokens）。**最新数据见
`style-profile/wgl/style_dossier.md` §4**——corpus 扩充后此表会过时，
但 Tier 划分（哪些词在 Tier B vs Tier A）从 12 篇到 16 篇完全稳定。

| 词 | corpus 频率（N=16） | LLM 默认行为 | 规则 |
|---|---|---|---|
| `Furthermore,` | 29 / 203k = 0.143 / 1k tokens | 每段开头都用 | 段落首词每节 ≤ 1 次（dossier §3：corpus 中段首仅出现个位数次） |
| `Moreover,` | 25 / 203k = 0.123 / 1k | 同上 | 同上 |
| `Additionally,` | 13 / 203k = 0.064 / 1k | 同上 | 同上 |
| `robust / robustly` | 13+4 = 17 / 203k = 0.084 / 1k | 形容方法/结果几乎必出现 | 每段 ≤ 1 处；首选具体描述（"survives a 5σ cut"，"recovered within 10%"） |
| `comprehensive` | 6 / 203k = 0.030 / 1k | 形容综述/数据集 | 每节 ≤ 1 处；优先量化（"covering 50 clusters from z=0.1 to 0.5"） |
| `utilize / utilized` | 4 / 203k = 0.020 / 1k | 替代 `use` | 默认改 `use`；保留 utilize 仅当确有形式语调需要 |
| `leverage`（单数）| 1 / 203k = 0.005 / 1k | 替代 `use` | 默认改 `use`；leverage 极少在 corpus 中出现 |
| `Importantly,` | 6 / 203k = 0.030 / 1k | 句首强调 | 段落开头 0 次（dossier §3 zero）；正文中每节 ≤ 1 次 |
| `Interestingly,` | 4 / 203k = 0.020 / 1k | 同上 | 同上 |
| `Notably,` | 2 / 203k = 0.010 / 1k | 同上 | 同上 |

**模糊量化 / 修饰词**
- 替换为具体数字或删除：`a wide range of`, `a variety of`, `a number of`, `several`, `numerous`, `many`。
  注：corpus 段首 `Several` 出现 10 次，**不是绝对禁忌**——但优先具体数字。
- 删除（除非有量化定义）：`cutting-edge`, `state-of-the-art`, `novel`, `powerful`。

**自指与套话**
- `This paper presents...` / `In this work, we...` 类 boilerplate 每段最多 1 处。
- 删除：`In summary,`, `To summarize,`, `In conclusion,`（除 conclusion 节外）。

**LLM 高频动词替换（dossier 未实证但语法层面是 tell）**
- `facilitate` → `enable`
- `In order to` → `To`
- `aim to` → `we [verb]`（直接动词）

**结构 tell**
- 三平行结构 (`not only X, but also Y, and furthermore Z`)：每节 ≤ 1 处。
- 过度规整的列表（每项都 X-word + 冒号 + 完整句）—— 学术写作的 list 应混用整句与短语。
- "X — that is, Y" 重述模式：em-dash + 重述双重 tell，必须重写。

**punctuation / 排版**
- 数字与单位之间用 `\,`（thin space），不要 LLM 习惯的普通空格。
- 千分位用 `\,`（thin space）或 `,`，不要无分隔。
- 不要在文中写 `etc.`（学术写作可接受但 LLM 滥用），改为完整列举或具体范围。

**review 阶段的强制 grep**

```bash
# em-dash：必须 0
grep -n -E '—|---|\\textemdash' main.tex

# Tier A（必删；正文中不允许出现，包括变体）
grep -n -E -i '(delve|leveraged|leverages|leveraging|paved?|paves|paving|shed[s]?|shedding|showcase[sd]?|showcasing|seamless(ly)?|holistic(ally)?|comprehensively|crucially|utilizes|utilizing|recent advances|despite significant|with the advent|in recent years|it is worth)' main.tex

# Tier B（限频，必须人工核对每段命中数）
grep -n -E -i '^|^\s*(Furthermore|Moreover|Additionally|Importantly|Interestingly|Notably),' main.tex   # 段首位置
grep -n -E -i '\b(robust|robustly|comprehensive|utilize[sd]?|leverage|leverages|leveraging|leveraged)\b' main.tex   # 全文频率

# 顽固替换组（不分级）
grep -n -E -i '\b(in order to|aim to|facilitate)\b' main.tex
```

**Tier A 残留** = 🔴 必改，不接受"语境合适保留"。
**Tier B 超频** = 🟡 标记每段命中次数，超 1 次 / 节即重写。

> **Companion check from `paper-style`:** the corpus dossier at
> `style-profile/<field>/style_dossier.md` is the **data source** for this
> tiered list. When the corpus changes, re-run `python tools/extract_style.py`
> and re-derive Tier A / Tier B from §4 of the new dossier. This file
> (`paper/SKILL.md`) should be re-aligned manually, but the linter
> (`tools/ai_ism_lint.py`) auto-loads the corpus blacklist from
> `style-profile/<field>/lexicon.json` so it always reflects the latest data.

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
