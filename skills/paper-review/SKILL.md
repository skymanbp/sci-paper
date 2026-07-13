---
name: paper-review
description: 严格、溯源式科学论文审查。按 SCIPAPER_STANDARD 的统一 feedback contract 执行 A–R 全维度检查：数学、物理、逻辑、语言与 de-AI、结构、引用、数据、接口、冗余、可复现性、现代物理、跨章节一致性、三重怀疑式推导检查、staleness、过程残影、内部草稿语言、引用精确度和术语对齐。科学完整性 blocker 必须解决，L0 target 必须清零，strong advisory 必须显式 disposition；不把普通 editorial advisory 伪装成通用 paper PASS/FAIL。Use for 投稿前 audit、完整论文审查、source tracing、数学物理复核和严格迭代修订。
disable-model-invocation: false
argument-hint: "<file_path> [--max-iter N] [--no-fix] [--skip-final-mpr] [--no-isolated-mpr] [--field <name>]"
---

# paper-review — typed, source-traced scientific review

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> `/sci-paper:paper` supplies writing guidance; field dossiers, baselines and
> learned models supply evidence. None defines an independent paper verdict.

本 skill 不是快速 lint。它完整读取论文与源材料，逐项验证科学声明，并把结果写成
`sci-paper.feedback.v1` finding。审查循环是：

measure → type → rank → edit → re-measure → disposition

终点是 **disposition-complete review state**，不是“0 个审美意见”或通用 PASS。

## 0. Non-negotiable rules

1. **当轮重新取证。** 数字、公式、引用、图表、时间和版本必须在本轮从源文件、
   DOI/arXiv、数据或脚本输出重新读取。记忆和旧报告只能帮助定位，不能证明事实。
2. **grep 只定位。** 每个命中或未命中都要通过上下文 Read、替代拼写和必要的全文
   检查确认；不能把 grep 当作语义证据。
3. **禁止猜测。** 无法验证时写明 `unmeasured`、`NEEDS SOURCE` 或
   `NEEDS PHYSICAL ACCESS`，不能制造近似答案。
4. **每个数值都有 provenance。** 合法来源是：具体数据/脚本输出、具体 DOI/arXiv
   的表/图/公式，或由本文已编号公式直接算得。缺失来源是 `integrity_blocker`。
5. **图表看实际内容。** 每个 figure 必须查看实际 PDF/PNG；每个 table 必须与上游
   数据逐 cell 对位。caption、正文和制品矛盾是 `integrity_blocker`。
6. **科学优先。** 数学、物理、统计、数据或引用错误不能靠 softening、disclaimer、
   “schematic” 标签或风格改写掩盖。修复根因。
7. **推导三重独立验证。** 每个 displayed derivation、关键物理链和数值结论都执行
   M.pass-1/2/3；任一命中后修复并重跑全部三 pass。
8. **后果类别不能混用。**
   - `integrity_blocker`: 科学、来源、引用、构建或必需制品错误；不可由风格偏好豁免。
   - `l0_target`: Tier A、em-dash、同 section 同 Tier B 词的第 2 次及以后。
   - `advisory`: editorial、narrative、结构、corpus distance、learned field-similarity。
9. **缺失测量不等于 0。** 所有 axes 显式标 `measured`、`degraded`、
   `unmeasured` 或 `not_applicable`。
10. **用户保留主观裁决权。** strong advisory 可以 `acted`、`accepted`、
    `rejected_as_false_positive` 或带理由 `pending`。普通 advisory 可以保留，但必须报告。

## 1. Preparation

每轮均重新执行：

1. Read `docs/SCIPAPER_STANDARD.md`、`/sci-paper:paper` 和当前 SKILL.md。
2. 解析 field：单 profile 可自动选；多个 profile 必须 `--field`；无 profile 时继续
   model-free 审查并标相关 axes `unmeasured`。
3. 从头到尾 Read 论文；分块也必须覆盖全文。
4. Read bibliography、项目事实源、数据/结果索引、生成脚本和相关 companion 当前版本。
5. 建立五张清单：
   - claims：claim、scope、stance、evidence relation、位置；
   - numbers：值、单位、位置、source trace、核验状态；
   - equations：定义、量纲、假设、边界、实现位置；
   - figures/tables：制品、caption claims、生成脚本、上游数据；
   - interfaces：论文符号 ↔ code variable ↔ data column。
6. 对 LaTeX 论文执行项目规定的完整 build；记录 errors、undefined refs、duplicate
   labels、missing assets 和 warnings。项目若使用其他 build system，执行其权威命令。
7. 运行共享 de-AI report：

```bash
python tools/ai_ism_lint.py <file> --field <field> \
  --structure --distribution --document-structure --oracle --voice \
  --format json --output <scratch>/paper-review-feedback.json
```

解释 exit status：0 = 无 L0 target，advisories 可存在；1 = 有 L0 target；2 = 输入、
配置或执行失败。不得从打印文本反解析 JSON。

同轮补充 claim-anchoring 质量带（写作质量轴，非 AI 判别轴——EVALUATION.md §9.6
记录了被证伪的假设；发现只作为"主张缺锚"质量问题处理）：

```bash
python tools/deai_anchoring.py <file> --field <field>
```

Cooperative-layer tools (opt-in; each is honestly `unmeasured` without the
author's own material, never an AI verdict). When the author supplies an AI-draft
ancestor, report which spans are still the AI draft; when they point at their own
prior papers, report whether this draft is under-varied against their own baseline
(a confound-free same-author reference — EVALUATION.md §9.9):

```bash
python tools/deai_provenance.py <file> --ai-ancestor <earlier-draft>   # or --git-ai-ref <commit>
python tools/deai_personal.py <file> --prior-papers-dir <author-own-papers>
```

## 2. A–R review dimensions

每个 finding 必须给出：`kind`、`layer`、`rule`、scope/location、当前证据、source
trace、measurement status、priority、recommended action、disposition。确认某条 critique
存在，不自动决定它是 blocker；后果类别单独判断。

### A. Mathematics

- 逐式检查量纲、代数、定义、符号一致性、近似条件、边界和极限。
- 手算或用独立脚本复现关键化简与数值例；脚本结果必须保留 provenance。
- 所有 `\eqref{}`、labels 和符号定义闭合。
- 数学错误、未声明的必要假设或结论无法推出均为 `integrity_blocker`。

### B. Physics

- 核心物理量、算子、滤波器、信号/噪声模式和 sign convention 与代码一致。
- 守恒律、对称性、宇称、渐近行为和适用域成立。
- 区分相关与因果；因果声明要有机制或设计支持。
- 物理错误、适用域矛盾或 claim/evidence 冲突为 `integrity_blocker`。

### C. Logic and statistics

- claim graph 无循环论证、断链、偷换条件、充分/必要条件错误或未声明假设。
- 样本、split、CV/grouping、泄漏防护、metric、uncertainty、多重比较和 prior 可复现。
- 无效统计、泄漏、错误外推或 unsupported conclusion 为 `integrity_blocker`。
- 合法但表达不清的逻辑连接通常是 advisory。

### D. Language and de-AI

- 术语、缩写、时态、句法、信息密度和段间连接支持准确阅读。
- Tier A、em-dash、Tier B cap 由共享 linter产生 `l0_target`。
- announced enumeration、parallel-modal runs、setup/list/wrap-up symmetry、重复段落/章节
  几何、burstiness、UID、document shape 和 learned field-similarity 是 advisory。
- learned signals 只表示 field-similarity/triage，不证明作者身份；没有 calibrated
  operating point 时必须 `degraded`。
- 不能要求所有结构 advisory 归零。strong advisory 要 disposition，普通 residual 要报告。

### E. Document structure

- 检查 contribution graph、依赖顺序、section function、abstract coverage、intro promise、
  results/discussion/conclusion closure 和图表首次引用位置。
- motivation → method → validation 是常见默认，不是所有论文必须套用的三幕模板。
- 多贡献论文可以有多个明确相关分支；问题是关系是否解释清楚，而非图是否恰好只有
  一个 component。
- 缺失支撑关键 claim 的必要论证可升为 `integrity_blocker`；其余 narrative findings
  按证据强度分为 strong 或 ordinary advisory。

### F. Citation existence and relevance

- 每个 bibliography item 的作者、年份、标题和唯一标识从 DOI/arXiv/出版页核验。
- 每个 citation 在当前句中确实支持所述 claim；查不到则标明访问缺口。
- fabricated、misused 或 claim-critical unverified citation 是 `integrity_blocker`。
- 边缘但可能更好的引用通常是 advisory，不自动阻塞。

### G. Data, results, figures and tables

- 每个数字定位到 source；当轮重算能重算的结果。
- abstract、正文、table、caption、figure、conclusion 同名数字与单位一致。
- table 逐 cell 对位；figure 检查曲线、点、误差、轴、单位、legend 和 caption。
- baseline 比较使用相同 protocol；uncertainty 的定义与样本量明确。
- mismatch、stale result、missing required artifact 或不可复现 claim 为
  `integrity_blocker`。

### H. Interfaces

- 论文公式 ↔ 实现函数、符号 ↔ code variable ↔ data column、pipeline 叙述 ↔ 执行顺序
  逐项映射。
- 因子、单位、cut、mask、preprocessing、randomization 和 aggregation 不得漂移。
- 接口矛盾为 `integrity_blocker`。

### I. Redundancy

- 找重复 claim、无信息增量段、死定义、死 figure/table 和重复解释。
- 若冗余造成两个互相冲突的版本，则为 `integrity_blocker`；纯压缩与可读性通常 advisory。

### J. Reproducibility

- 数据来源、selection、preprocessing、software、hardware、seed、hyperparameters、split、
  metric 和 availability 足以复现声明。
- 缺失使核心结果不可复现的必要信息是 `integrity_blocker`；非核心补充信息可为 advisory。

### K. Modern-physics checks

对适用内容执行：

1. dimensional analysis；
2. asymptotic limits；
3. symmetry/parity/conservation；
4. statistical and probability assumptions；
5. algebraic derivation；
6. numerical traceability；
7. foundational citation verification；
8. build and cross-reference integrity；
9. de-AI review 不得覆盖物理判断。

不适用项标 `not_applicable`，不能虚构检查结果。

### L. Systemic consistency

- 同一符号、定义、常数、样本规模、split、cut 和假设跨章节一致。
- introduced concepts 被使用；used concepts 已定义；forward references 兑现。
- method → result → discussion → conclusion 和 abstract → intro → conclusion 闭环。
- companion claims 从当前版本重新核验。
- 跨章节矛盾或未兑现的核心 claim 是 `integrity_blocker`。

### M. Three-pass adversarial verification

对每个关键推导块和数值结论独立执行：

- **pass-1:** 量纲、代数、近似、边界、数值复算。
- **pass-2:** 以对手 reviewer 视角提出最强的具体反驳，并用当前证据回答。
- **pass-3:** 守恒、对称、渐近、概率与统计前提。

规则：

- 三 pass 不共享“已经 OK”的结论；都从源重新开始。
- 任一命中 → 修复 → 三 pass 全部重跑。
- 只有三 pass 均无未解决 scientific issue 才标 `VERIFIED`；否则
  `UNDER_SCRUTINY`，并产生 `integrity_blocker`。
- 报告保留每个 pass 的方法和证据，不允许只写“checked”。

### N. Staleness and drift

完整检查：

- 数字、叙述、公式依赖、结论、figure、table、labels、references、markup；
- source 脚本或数据变化后，下游全部同步；
- TODO/FIXME/placeholder/commented-out deprecated blocks 为 0；
- dead artifacts 删除，必要内容更新为当前真值，不堆叠旧版。

stale scientific content、冲突副本或 required artifact drift 是 `integrity_blocker`。
纯 dead prose 的删除建议通常是 advisory，除非造成歧义。

### O. Process-artifact removal

- 删除“initially/originally/previous draft/we tried then changed”等本文内部研究旅程。
- 只保留当前科学状态。
- 外部 published baseline 的正式 head-to-head 比较可以保留，前提是有 citation、protocol
  和 numerical comparison。
- 过程叙述若使当前 method/claim 不清或引入 stale content，按 blocker；否则按 advisory。

### P. Internal and draft language

- 清理 TODO、内部路径、run/version 名、debug 名、skill/tool 名、commit-message 口吻、
  实验日志语言和未定义内部缩写。
- required placeholder、内部版本残留或暴露错误来源为 blocker；普通口语和 polish 为 advisory。

### Q. Reference completeness and precision

- 从论文 claim 和 field 重新识别应引用的 foundational/direct prior work。
- 对每个 `\cite{}` 比对原文实际支持范围，分类为 CORRECT、WEAK、MISUSED、UNVERIFIABLE。
- MISUSED、fabricated、遗漏导致 novelty/attribution 错误的关键文献为 blocker。
- WEAK 或边缘 missing reference 为 advisory；不要把“可能还能多引一篇”强制成 blocker。
- paywall 不等于已验证；记录 access limitation，必要时请求用户获取原文。

### R. Terminology and glossary alignment

- 优先读取项目权威 glossary/FACTS/notation source；不存在则以论文 definitions 做自洽检查，
  并将外部对齐标 `unmeasured`。
- 关键 noun phrase、acronym、symbol 首次出现定义明确，全文单义且与权威定义一致。
- semantic conflict 为 blocker；可理解但不一致的 alias 通常 advisory。

## 3. Cross-validation matrix

必须完成四类对位：

1. architecture in paper ↔ code/config；
2. numerical claim ↔ current data/output；
3. formula ↔ implementation, including corner cases；
4. pipeline narrative ↔ execution order。

每个结论写 source trace，不能用“看起来一致”。

## 4. Fix and re-measure loop

默认修复，`--no-fix` 仅输出报告。

每轮：

1. 按 unified priority 排序 findings；科学 blockers 先于 L0，L0 先于 advisories。
2. 对每个 blocker 修根因；对每个 L0 做最小有效修改。
3. 对 strong advisory：行动、接受、验证为 false positive，或带原因 pending。
4. ordinary advisory 不要求消失；保留并报告即可。
5. 每个 edit 后重新 Read 相关上下文。
6. 改公式/数字/物理链后重跑 M 三 pass；改 figure/table 后重新查看制品与来源；
   改 citation 后重新读原文；改 prose 后重新跑 shared linter。
7. 重跑权威 build 和所有受影响测试/脚本。

伪代码：

```text
for iter in 1..max_iter:
    report = full_A_to_R_review_from_current_sources()
    if no integrity_blocker \
       and no l0_target \
       and no UNDER_SCRUTINY derivation \
       and every strong advisory has a disposition:
        stop with DISPOSITION_COMPLETE
    if no_fix:
        stop with REVIEW_ONLY
    apply_ranked_root_cause_fixes(report)
    re_measure_affected_axes()

if budget exhausted:
    return BREAK_WITH_USER_DECISION with unresolved findings
```

不得自动增加 `--max-iter`。预算耗尽不是 paper failure verdict，而是 review workflow
尚未完成；把 pending blockers、L0 和 strong advisories交给用户决定下一步。

## 5. Isolated modern-physics verification

单独运行 paper-review 时，达到进程内 disposition-complete 状态后，默认由主代理启动
isolated worktree agent，重新读取 host-level modern-physics-review skill 并 cold-read
目标论文。它不能继承当前审查的“已经验证”结论。

- `--skip-final-mpr`: 仅用户显式选择时跳过，报告 `unmeasured`/`SKIPPED_BY_USER`。
- `--no-isolated-mpr`: 仅供 final-review 等父 orchestrator 避免 nested agent；报告
  `SKIPPED_FOR_ORCHESTRATOR`，由父级独立执行。
- isolated review 产生的 critique 先判断 evidentiary verdict，再单独赋 consequence class。
  CONFIRMED editorial critique 不自动成为 blocker。
- 新 blocker/L0/strong advisory 回注主循环；agent failure 必须显式报告，不能伪装通过。

## 6. Report contract

```markdown
# Paper Review — Typed Feedback Report
Target: <file> | Iterations: K | Field: <field or none>
Workflow state: DISPOSITION_COMPLETE | REVIEW_ONLY | BREAK_WITH_USER_DECISION | EXECUTION_FAILURE

## Measurement state
| axis | status | provenance / limitation |

## Summary
- integrity_blocker: total / resolved / pending
- l0_target: total / resolved / pending
- strong advisory: acted / accepted / false-positive / pending
- ordinary advisory: total / reported
- M derivations: VERIFIED / UNDER_SCRUTINY
- build: measured status and result
- isolated MPR: measured / unmeasured / orchestrator-owned / failed

## Ranked findings
| id | kind | layer | rule | location | evidence | source trace | action | disposition |

## A–R coverage
For every dimension: measurement status, methods used, and finding IDs.
Do not print PASS/FAIL rows.

## Numerical anchors
| quantity | paper claim | source | verification |

## M three-pass record
| derivation | pass-1 evidence | pass-2 objections/answers | pass-3 invariants | status |

## Residual feedback
- pending strong advisories with reasons
- ordinary advisories
- degraded/unmeasured axes
- author decisions required
```

The human-readable report and JSON must come from the same structured findings. Totals must not
change when detail is truncated.

## 7. Stopping semantics

Review may stop as disposition-complete only when:

- all integrity blockers are resolved or verified false positives;
- applicable L0 targets are zero;
- all critical derivations are VERIFIED;
- required build and artifacts are valid;
- every strong advisory has an explicit disposition or a stated pending reason;
- ordinary advisories and unavailable axes are reported.

This does **not** assert that the paper is universally perfect, human-authored, accepted by a journal,
or free of subjective editorial alternatives.

## 8. Anti-patterns

- Declaring “grep found nothing, therefore correct”.
- Reusing numbers or citations from memory.
- Looking only at captions instead of figures.
- Softening a wrong claim instead of correcting its source, math, data or scope.
- Calling a learned score proof of authorship.
- Treating a missing baseline as zero findings.
- Requiring every yellow/editorial suggestion to disappear.
- Converting every confirmed critique into a blocker.
- Demanding exactly one narrative thread when multiple related contributions are legitimate.
- Calling advisory-only exit 0 a scientific or submission PASS.
- Skipping M pass-2/pass-3 because pass-1 looked correct.
- Hiding unresolved items after iteration budget exhaustion.
- Starting a nested sub-agent when `--no-isolated-mpr` delegates MPR to the parent orchestrator.
