# sci-paper

[![CI](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.27.1-informational.svg)](CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A5CF6.svg)](https://docs.claude.com/en/docs/claude-code/plugins)
[![Python](https://img.shields.io/badge/python-%E2%89%A5%203.11-3776AB.svg)](requirements.txt)
[![Tests](https://img.shields.io/badge/tests-213%20passing-success.svg)](tests/)

**一个 Claude Code 插件：在同一套 typed 标准下完成科研论文的写作、审查、去 AI 化与精简。
每条结论都可溯源，每个测不出来的轴都如实标为测不出来。**

面向 ApJ / MNRAS / PRD / JCAP 级别的论文，以及 NSF / NIH 基金申请书。
**8 个 skill · 25 个工具 · 213 个测试 · 一份规范 · 零作者身份判决。**

[English](README.md) — [它做什么](#它做什么) · [怎么做到的](#怎么做到的) ·
[实际效果](#实际效果) · [Benchmark 面板](#benchmark-面板) · [安装](#安装) ·
[Skills](#skills8-个) · [Tools](#tools25-个) ·
[已知限制](#现状已知限制与路线图) ·
[规范正文](docs/SCIPAPER_STANDARD.md) · [文档索引](docs/README.md)

---

## 这是什么

sci-paper 把一个 Claude Code 会话变成一张论文工作台，由唯一一份成文契约
[`docs/SCIPAPER_STANDARD.md`](docs/SCIPAPER_STANDARD.md) 统治。

你把一份 `.tex` 草稿交给它。它拿**你自己领域的语料**（而不是一个通用模型先验）
去测量这份草稿，返回 **typed、排序过、可溯源的 finding**：哪里有问题、有多严重、
凭什么这么判、该怎么改，以及哪些轴它根本测不了。然后它才改写 —— 每次改写都要
先过科学保真硬门，风格分数连投票资格都没有。

它永远不会告诉你"这篇论文 87% 由 AI 生成"。这个数字在整个系统里根本不存在，
这是设计。

---

## 它做什么

### 针对的问题

技术论文有三种毁掉稿子的失败模式，没有一种是"词汇问题"：

1. **换完词以后，文字读起来还是像机器写的。** 把 "delve" 换成 "examine"，更深的规律
   一点没动：句长变化被抹平、句式模板化、全文修辞形状过度规整、claim 背后没有证据。
   *本仓库直接测了这一点：一份**零个违禁词**的合成文档，照样在全文尺度被抓住
   （[demo 3](#3-一份零违禁词的文档照样被抓住)）。*
2. **一个 AI 检测分数没法告诉编辑要改什么** —— 而且它被领域、来源、章节体裁、长度、
   术语密度、数学密度全面混淆。它回答的是"这是谁写的"，而作者并不需要这个答案。
3. **审查会悄悄把"没测到"变成"好消息"。** 一个没标定的轴报告零个 finding，
   而零个 finding 读起来就是干净。

### 八项功能

| # | 功能 | Skill | 你得到什么 |
|---|---|---|---|
| **一** | **按规范写** | [`paper`](skills/paper/SKILL.md) | 把写作框架载入上下文：准确性规则、公式与引用规范、正向叙述、带 canonical 例子的 L0 词汇政策、正向 voice 指引、measurement state、停止语义。 |
| **二** | **去 AI 化** | [`de-ai`](skills/de-ai/SKILL.md) | 三过串联 —— 子系统测量（L0–L4）、结构 tell 审计，然后 **claim-first 改写**：从受保护的 claim graph 重建文字，而不是原地润色。`--audit-only` 只跑到测量为止。 |
| **三** | **精简而不丢科学** | [`condense`](skills/condense/SKILL.md) | 全文去冗余，遵循"每个事实只有一个 canonical 位置"、loop-until-dry 收敛，并以**机械长度门**作为"确实变短了"的收尾证明。 |
| **四** | **审稿子** | [`paper-review`](skills/paper-review/SKILL.md) | 溯源式 **A–R 审查**：数学、物理、逻辑与统计、语言、结构与叙事主线、引用、数据与图表、接口、冗余、可复现性、现代物理核查、跨章节一致性、对抗式验证（三 pass + 12-framing 升级）、staleness、过程残影、引用精确度、术语对齐。 |
| **五** | **审图** | [`figure-review`](skills/figure-review/SKILL.md) | 审的是 **150 DPI 的编译页**，不是源码。追溯 figure/caption/数据的 provenance，在像素级测量画布平衡，并把科学与构建矛盾同可读性建议分开。 |
| **六** | **跑完整审查团** | [`final-review`](skills/final-review/SKILL.md) | 父级编排器：在**独立 worktree agent** 里跑 paper-review、figure-review、de-ai `--audit-only` 与 modern-physics-review，合并 typed finding，并验证 disposition-complete 状态在连续多轮里稳定。 |
| **七** | **打磨基金申请书** | [`proposal-polish`](skills/proposal-polish/SKILL.md) | NSF Project Summary/Description、NIH Specific Aims、fellowship。保留论文会删掉的"愿景+可行性"语域，强制 claim 与可行性匹配，最狠地打磨决定评分的前几页。 |
| **八** | **探索研究方向** | [`brainstorm`](skills/brainstorm/SKILL.md) | 辐射状研究方向探索器：每节点 12 条 framing pass、术语锚定到 glossary、每分支完整推导、递归发散直到收敛。严禁 defer / future-work / 半成品叶节点。 |

八项功能跑在同一层证据之上 —— 25 个工具输出同一套 schema
`sci-paper.feedback.v1` —— 所以 linter、审查 skill 和编排器给出的 finding
是同一个对象、同一个 ID。

### 工作边界 —— 它刻意不做什么

| 它不会 | 因为 |
|---|---|
| 给出作者身份判决或 "AI 百分比" | 学习型轴只是**领域相似度分诊**，在段落尺度封顶 0.5 置信度。它在领域主题 AI 文本上的假阳率是 32–42%（[为什么](#为什么没有单一分数l3-的混淆)）。 |
| 给出论文级 PASS/FAIL | 终止态是 *disposition-complete*，不是"零条 advisory"。 |
| 把缺失的基线当成零个 finding | 测不了的轴报 `unmeasured` / `degraded`，并写明原因。 |
| 为了绕过检测器而优化文字 | 改写排序优化的是忠实的科学文字。保真是硬门，不是权重。 |
| 编造 preliminary data、合作方、经费历史或推荐信 | 申请书模式是编辑，不是捏造者。 |
| 公开你的语料 | 语料文件只读、受版权保护、gitignore。 |

---

## 怎么做到的

```
             ┌──────────────────────────────────────────────┐
   你的领域   │  style-corpus/<field>/tier-{1,2,3}-*/         │  你自己提供的论文
   语料   ──▶│  → extract_style.py → style-profile/<field>/  │  （只读、gitignore）
             └──────────────────────────────────────────────┘
                          │ 描述性统计、范例段落、标定过的参照分布
                          ▼
  draft.tex ──▶ 测量 ──▶ typed findings ──▶ 排序 ──▶ 编辑 ──▶ 重测 ──▶ disposition
                  │                                              │
                  │ L0  词汇 + 标点 + 领域 register              │ 每条 strong
                  │ L1  信息分布、surprisal / UID                │ advisory 最终
                  │ L2  句式模板、salience、全文形状             │ 落到 acted /
                  │ L3  学习型领域相似度（封顶、degraded）       │ accepted /
                  │ L4  正向 voice + 协作式修复                  │ false-positive
                  └──────────────────────────────────────────────┘
```

这个循环就是产品本身：**measure → type → rank → edit → re-measure → disposition。**

### 六块硬骨头

违禁词表谁都会做。下面这些是真正花了证据的部分。

**一 · 保真是硬门，不是分数。** `rewrite_reward.py` **先过**确定性科学保真资格，
再对候选排序。这个检查是**双向的**：丢掉*或凭空加上*一个数字、单位、引用、行内公式、
大写缩写、语义 LaTeX 宏、比较方向、否定、因果方向标记 → `-inf`，风格分数再高也没用。
分词边界本身有回归测试，因为朴素实现会误杀忠实改写 —— 贪婪的数字模式让"少了一个
牛津逗号"被读成同时*丢失* `2400,` 又*凭空加上* `2400`
（[`rewrite_reward.py:33`](tools/rewrite_reward.py#L33)）；过宽的单位模式让
`"in 2020 we found"` 产出单位 `we`
（[`rewrite_reward.py:41`](tools/rewrite_reward.py#L41)）。
见 [demo 2](#2-保真门枪毙了风格分最高的候选)。

**二 · 全文尺度检测，因为段落尺度的去 AI 根本没用。** 本仓库最关键的一次测量：
把段落级去 AI 改写当作攻击施加到 AI 文档上，**改动了 22% 的文本、删掉了全部 14 个
em-dash**，而全文级 dispersion 几乎没动 —— 0.47 → 0.49，人类是 1.08
（[§9.1](docs/architecture/evaluation/document-scale.md)）。把每一段都朝"更像人"改，段落**彼此之间**
依然一样齐整。所以主检测器是一个**联合流形统计量**：把每份文档的 log dispersion 比值
向量，对人类中心与协方差做 Mahalanobis 距离 —— 纯标准库的 11 维实现，带 ridge 稳定化。
联合几何能抓住独立边缘分布抓不住的东西：形状对抗者可以凑出合理的逐特征离散度，
却凑不出正确的协方差。另一条正交轴测 **role coupling** —— 人类是在**论证需要的地方**
改变段落形状。在 507 篇的人类语料上，两条轴的 5% 尾部**完全不相交**
（0 篇被两条同时标记；若独立应约 1.3 篇）。

**三 · 操作点是 split-conformal 且按长度分层的。** 用同一批论文既拟合又定阈值，
那是 in-sample。发布的操作点在留出的人类论文上标定 nonconformity 分数，
`p = (1 + #{标定集 ≥ 分数}) / (n_cal + 1)`，在 `p ≤ α = 0.05` 处标记 ——
对可交换的人类论文给出**有限样本、分布无关的 `P(误标) ≤ α`**。标定按**文档长度三分位
做 Mondrian 分层**，因为长度是被测出来的混淆：短的人类论文系统性地拿到更高的流形距离
（第 0 层 95 分位 5.23，另两层是 4.16 / 4.36），而所有 AI 验证文档都是短的。
不分层的阈值等于拿短 AI 文档去比一个以长论文为主的人类参照，先前报告的标记率
（0.607/0.600/0.447/0.292）**高估了尾部功效**。诚实的数字替换了它们，
就在[面板里](#全文尺度长度公平的判别力)。

**四 · register 来自你的语料，不是一张词表。** `deai_register.py` 标记稿子反复依赖
（≥ 5 次）、但在**你自己领域语料**里 document frequency 低于 1e-4 的术语。
没有任何手工整理的跨学科黑名单。正是这一点让 `AUC`（df 1）能和 `epoch`（df 402）、
`accuracy`（df 774）分开，而不需要任何人去维护一张天文例外表。复合词按其最罕见的
部分判定；`_` 或 `^` 后面的 `\mathrm{}` 是下标不是术语；所有格折叠。

**五 · 沉默永远不等于干净。** 每个轴报告 `measured` / `degraded` / `unmeasured` /
`not_applicable` 之一，最终报告四种状态全列 —— 下面每个 demo 里都能看到：
`L1.distribution` 始终是 `degraded`，因为 `deai_policy.json` 不存在，
而不是报告零个 finding。缺依赖就让那个轴保持 `unmeasured`。
这是预期行为，不是一个"装个包就好了"的降级模式。

**六 · 被证伪的信号留在记录里。** "文章主旨（thesis spine）"信号的三种表层形式化
全部被构建、测量并**证伪**；该规则以*不带检测器的写作规则*形式发布，规范明文禁止
在它上面建阈值。claim-anchoring 这条 tell 对强模型生成同样被证伪，所以
`deai_anchoring.py` 明确标为**写作质量轴，不是 AI 判别轴**。Hypotaxis ratio：否决。
惰性从句串与推理连接词率：否决。一个坏重采样器产生的零宽置信区间：发现、修复、
基线重建。全部记录在 [EVALUATION.md](docs/architecture/EVALUATION.md) 里，
连同杀死它们的那些数字。**一个被证伪的检测器也是证据，它留在记录里。**

---

## 实际效果

下面每一条命令和数字都是 **2026-08-25** 在本工作树（v0.27.1）、`wgl` 参照 profile 上
真跑出来的。没有一处是示意。

> demo 文档是为这份 README 专门写的合成文字，不是语料内容。全新 clone **不带**任何
> profile（[为什么](#按-field-组织的证据)），所以 `measured` 的轴需要你先用自己的
> 论文建一份 profile。

### 1. 一份草稿的 before / after

一份 200 词、两个 section 的草稿，带着典型 tell：Tier A 词汇、一个 em-dash、
一处 announced enumeration，以及连续六句在念参数。

```console
$ python tools/ai_ism_lint.py before.tex --field wgl \
    --structure --distribution --register --salience --document-structure

findings: blockers=0 L0=10 advisories=11 (strong=0)
axis L0.lexical: measured
axis L0.register: measured
axis L2.salience_hierarchy: measured
axis L1.distribution: degraded: using documented compatibility heuristics; deai_policy.json is unavailable
axis L2.sentence_structure: degraded: template evidence measured, but no calibrated strong-feedback operating point is available
axis L2.document_structure: unmeasured: need at least 3 sections with at least 2 substantial paragraphs each

  L  3 [l0_target L0 tier-a:pivotal] Tier A lexical target 'pivotal' is present.
  L  9 [l0_target L0 em-dash] Em-dash punctuation is an L0 rewrite target.
  ...
  L 14 [advisory L2 salience-recital:method] method passage recites its quantities:
       max_recital_run_frac 0.60 (p95), recital_frac 0.60 (p91), numerals_per_sentence 0.70 (p85).
       The longest uninterrupted run of numeral-bearing sentences is 6 of 10, against an
       n=1303 human method reference.
$ echo $?
1
```

注意 salience 那条 finding 实际说的是什么：不是"数字太多"，而是
*你十句里有六句在报数值、中间没有一句解释，而人类 method 参照把这个放在第 95 百分位。*

claim-first 改写之后：

```console
$ python tools/ai_ism_lint.py after.tex --field wgl \
    --structure --distribution --register --salience --document-structure
findings: blockers=0 L0=0 advisories=3 (strong=2)          # exit 0

$ python tools/length_gate.py after.tex --before before.tex
section                       before   after   delta  status
Introduction                      79      46     -33  ok
Method                           119     117      -2  ok
TOTAL                            198     163     -35
net unjustified growth: -35 words (tolerance 0)
findings: blockers=0 L0=0 advisories=0 (strong=0)          # exit 0
```

| 指标 | 改前 | 改后 |
|---|---:|---:|
| L0 target | 10 | **0** |
| integrity blocker | 0 | 0 |
| advisory（其中 strong） | 11（0） | **3（2）** |
| linter 退出码 | `1` | **`0`** |
| 全文长度 | 198 词 | **163 词**（−35） |
| 长度门 advisory | — | **0** |
| 受保护数字保留 | — | **7 / 7** |

**它没有收敛到零，而这是对的。** 剩下两条 strong 是 method 段落上的 salience
advisory —— 那两段在规定参数网格。规范给出的答案是 `accepted` disposition，
而不是把阈值调松：参数规格**本来就该**带数字，参照只是说这一段比 90% 的人类
method 段落更密。

**长度门抓了作者两次。** 第一版改写把 Method 撑大了 60 词，门直接标出来
（`+60 GROWTH`）。第二版修好了长度，却在精简时悄悄丢了两个数字 —— 被 demo 2 抓住。

### 2. 保真门枪毙了风格分最高的候选

同一个 method 段落的三个改写候选，对照原文排序：

```console
$ python tools/rewrite_reward.py --field wgl --reference ref.txt --original ref.txt \
    --candidates cand_lossy.txt cand_faithful.txt cand_tight.txt

rank cand  combined   voice  fidelity   Δadv eligible  L0(r/c)  words(o/c)
   1    2     0.327   0.990     0.861   0.00     True  0/0  72/58  cand_tight.txt
   2    1      -inf   0.873     0.843   0.00    False  0/0  72/78  cand_faithful.txt
     over length budget: +6 words (SCIPAPER_STANDARD section 5.3; use --allow-growth
     REASON only with an author-approved justification)
   3    0      -inf   0.936     0.818   0.00    False  0/0  72/66  cand_lossy.txt
     missing: {'numbers': ['1.2', '12']}

[best] candidate 2: cand_tight.txt                          # exit 0
```

把 `voice` 一列和 `eligible` 一列对着读。`cand_lossy` 的学习型领域相似度是 **0.936**，
比忠实的 `cand_faithful`（0.873）还高 —— 然后它输给了"什么都不改"，因为它丢了
`12` 个径向 bin 和 `1.2` 百万源。风格分数根本没有投票权。`cand_faithful` 每个数字
都保住了，**依然**不合格，因为它超了 §5.3 长度预算 6 个词。如果三个全不合格，
工具退出 `1` —— 这是一个**被测量出来的结论**：保留原文，重新生成更紧的版本，
而不是崩溃。

### 3. 一份零违禁词的文档，照样被抓住

一份 5,225 词、10 个 section、由句式模板生成的稿子。没有 Tier A 词汇、没有 em-dash、
没有 register 离群词 —— **`L0=0`**：

```console
$ python tools/ai_ism_lint.py big.tex --field wgl --document-structure

findings: blockers=0 L0=0 advisories=27 (strong=4)
axis L2.document_structure: measured

  L 1 [advisory L2 document-dispersion-manifold strong] The document's joint cross-paragraph
      dispersion sits 13.99 Mahalanobis units from the human center (conformal p = 0.0169
      <= alpha 0.05 against 58 held-out human papers (stratum 1 manifold)): its paragraph-shape
      variation pattern departs from the human band as a whole. This is a measured deviation,
      not an AI verdict.

  L 1 [advisory L2 document-role-decoupling strong] Paragraph-shape variation is decoupled from
      rhetorical role: coupling z is -0.15 (conformal p = 0.0307 <= alpha 0.05 against 162 human
      papers (stratum 1)). Human papers vary paragraph shape where the argument demands it;
      here the variation is unrelated to role.

  L 1 [advisory L2 document-shape:cross_section_similarity strong] Document-level cross section
      similarity is 0.991, at empirical percentile 1.000 of the complete-document reference.
```

这就是第一种失败模式，按需复现。一个"清词"工具会报告这份文档干净。
全文尺度的轴把它放在 `p = 0.0169` 与 `p = 0.0307`（对照留出的人类论文）——
并且**依然拒绝**说它是 AI 写的，因为诚实的陈述是
*这份文档的段落形状变化偏离了人类带*，而 finding 说的正是这句话。

---

## Benchmark 面板

两类数字，不能互换：**判别力与标定**，读自评估记录；**延迟**，为这份 README
第一手实测。

### 全文尺度、长度公平的判别力

对照 169 篇同长度层、留出的人类论文的 AUC —— 这是长度混淆被发现并修正之后的
诚实协议。来源：[§9.5](docs/architecture/evaluation/document-scale.md)，2026-08-25 重测。

| 对比 | 流形 AUC | role-coupling AUC |
|---|---:|---:|
| 人类 vs **自然** AI | **0.928** | 0.702 |
| 人类 vs **去 AI 化后**的 AI（把段落级去 AI 当作攻击） | **0.939** | 0.751 |
| 人类 vs **形状对抗**的 AI（刻意制造参差） | 0.919 | **0.818** |
| 人类 vs **骨架匹配**的结构克隆 | 0.916 | 0.515 |

两条轴天生互补：流形对包括结构克隆在内的每一档都保持稳健判别，
而 role 轴的真实功效恰好集中在把流形逼到最窄的那一档上。

### α = 0.05 下的假阳控制

Split-conformal，按长度三分位做 Mondrian 分层。保证：对可交换的人类论文，
**有限样本、分布无关的 `P(误标) ≤ α`**。
来源：[§9.5](docs/architecture/evaluation/document-scale.md)。

| 量 | 流形 | role | 目标 |
|---|---:|---:|---:|
| 人类误标率（校准集上留一法） | **0.040** | **0.049** | ≤ 0.05 |
| 逐特征带的 leave-one-out 标记率 | 0.051 | 0.051 | 0.05 |

同一操作点下的尾部功效 —— 弱的地方也照实报：

| 标记 | 自然 | 去 AI 化 | 对抗 | 骨架 |
|---|---:|---:|---:|---:|
| 流形 | 0.214 | 0.400 | 0.158 | 0.292 |
| role-decoupling | 0.107 | 0.333 | 0.316 | 0.042 |
| **并集** | 0.321 | 0.667 | 0.421 | 0.333 |

短文档在流形轴上的尾部功效仍是最弱的一档，因为短人类论文的距离分布是重尾的。
"长度感知流形"排在前沿队列里，而不是就地临时发明一个。

### 为什么没有单一分数：L3 的混淆

学习型段落尺度模型效果不错 —— 而它**依然**以 `degraded` 发布，理由是测出来的。
来源：[§7.1–7.3](docs/architecture/evaluation/learned-model.md)。

| 指标 | 值 | 95% 区间 |
|---|---:|---|
| 分组切分 AUC（20 次切分，整篇论文留出） | 0.9320 | 0.9218 – 0.9416 |
| 匹配层 AUC（section × 长度 × 数学 × 领域词） | 0.9236 | 0.9044 – 0.9414 |
| 平衡准确率 | 0.8509 | 0.8382 – 0.8642 |
| 作者 hard-set、**真实 provenance** | 0.937 | — |
| 假阳率 —— 通用公开 AI 文本 | 0.086 | — |
| 假阳率 —— **领域主题 AI 文本** | **0.318** | — |
| 假阳率 —— **领域术语密集 AI 文本** | **0.417** | — |

0.93 的 AUC 头条数字，和 32–42% 的领域主题假阳率，是同一个模型。
学习型分数有一部分测的是*领域 register*，所以它恰恰在"去 AI 必须抓住的那个分布"
（领域主题 AI 文字）上不可靠。这就是 L3 只做分诊、在段落尺度封顶 0.5 置信度、
永远不是作者身份判决的原因。文档级 surprisal 路径也测了（0.757），
比 model-free 流形（0.881）更弱，且对它毫无增益 —— 所以那条路也救不了 L3。

### 延迟

2026-08-25 实测，Windows 11、Python 3.13.3，每行 7 次子进程运行取中位数，
含解释器启动。

| 通道 | 文档 | 中位墙钟 | 依赖 |
|---|---|---:|---|
| Python 解释器地板 | — | 59 ms | — |
| L0 词汇 + register | 5,225 词 | **328 ms** | 标准库 |
| **全部 model-free 轴**（L0 + L1 + L2，含全文结构） | 5,225 词 | **329 ms** | 标准库 |
| 全部 model-free 轴 | 200 词 | 193 ms | 标准库 |
| `length_gate.py` | 5,225 词 | 341 ms | 标准库 |
| `+ --oracle`（GPT-2-large token surprisal） | 5,225 词 | 25.3 s | `transformers` + `torch` |
| `+ --voice`（学习型 L3 分诊） | 5,225 词 | 47.2 s | `scikit-learn` + `sentence-transformers` |
| `validate_plugin.py`（9 项契约检查） | 仓库 | 2.0 s | 标准库 |
| 完整测试套件（213 个测试） | 仓库 | 82.9 s | 标准库 |

一句话：**一份 5,225 词的稿子跑完全部 model-free 通道，在解释器地板之上只花约
270 ms**，而且不需要装任何可选依赖。两条模型驱动的轴贵 75–140 倍，并且是显式
opt-in 的 flag —— 这正是预期形状：lint 一篇论文不该需要一块 GPU。

### 仓库健康度

| 检查 | 结果 |
|---|---|
| 契约 validator | **9/9 通过** |
| 单元 / CLI 测试 | **213 通过**（15 个文件） |
| CI | 每次 push 与 PR 跑 validator + 套件，Python 3.11，Ubuntu |

---

## 安装

```bash
git clone https://github.com/skymanbp/sci-paper.git
claude --plugin-dir /path/to/sci-paper          # 开发模式
```

之后 skill 的命名空间是 `/sci-paper:<name>`。

**Python ≥ 3.11。** 共享 schema、确定性 L0 linter、model-free 的 L1/L2 轴、
全文结构分析和 validator **只用标准库**。可选能力才需要额外依赖：

```bash
pip install -r requirements.txt      # 全部可选依赖
```

| 包 | 启用什么 |
|---|---|
| `pymupdf` | PDF 语料抽取、编译页检查 |
| `sentence-transformers` | 语义范例检索、embedding 特征 |
| `scikit-learn` + `joblib` | 旧版与学习型领域相似度模型 |
| `transformers` + `torch` | token surprisal / UID 测量 |
| `numpy` | 学习型特征、缓存、改写打分工具 |

> 不要为了把一个"测不出来的轴"变成一个名义分数而去装可选依赖。
> 缺包就让那个轴保持 `unmeasured`，这是设计。

## 快速上手

```bash
# 1. 验证 checkout。
python tools/validate_plugin.py
python -m unittest discover -s tests -v

# 2. 把你领域的论文放进 style-corpus/<field>/tier-*/，然后建 profile。
python tools/build_profile.py --field wgl

# 3. 产出一份统一的、机器可读的反馈报告。
python tools/ai_ism_lint.py draft.tex --field wgl \
  --structure --distribution --document-structure --register --salience \
  --oracle --voice --format json --output feedback.json
```

然后在 Claude Code 里驱动它：

```text
/sci-paper:paper                                  # 载入写作规范
/sci-paper:de-ai         draft.tex --field wgl    # 测量 → 审计 → 保真改写
/sci-paper:condense      draft.tex                # 去冗余，并用长度门证明确实变短了
/sci-paper:paper-review  draft.tex --field wgl    # A–R 溯源式审查
/sci-paper:figure-review draft.pdf                # 基于编译页的图表证据
/sci-paper:final-review  draft.tex --field wgl    # 隔离式多审查者编排
/sci-paper:brainstorm    "topic"                  # 辐射状研究探索
/sci-paper:proposal-polish grant.tex --agency nsf # 基金申请书 register
```

---

## Skills（8 个）

四件事；每个 skill 具体做什么见[八项功能](#八项功能)。

- **写** —— [`paper`](skills/paper/SKILL.md) · [`proposal-polish`](skills/proposal-polish/SKILL.md)
- **改** —— [`de-ai`](skills/de-ai/SKILL.md) · [`condense`](skills/condense/SKILL.md)
- **审** —— [`paper-review`](skills/paper-review/SKILL.md) · [`figure-review`](skills/figure-review/SKILL.md) · [`final-review`](skills/final-review/SKILL.md)
- **探索** —— [`brainstorm`](skills/brainstorm/SKILL.md)

## Tools（25 个）

这些工具产出的每一条 finding 都遵循同一套 `sci-paper.feedback.v1` 契约；
下面的语料、训练与数据资产类条目产出的是制品而非 finding。
逐工具的标定状态与失败行为见 [tools/README.md](tools/README.md)。

#### 契约、门与 CLI

| 工具 | 用途 |
|---|---|
| `tools/deai_feedback.py` | 实现 `sci-paper.feedback.v1`：稳定 ID、后果类别、measurement state、disposition、排序、汇总、渲染。纯标准库。 |
| `tools/ai_ism_lint.py` | 统一 CLI。把 L0 与全部 advisory 轴聚合成一份排序过的 text/JSON 报告。退出码 `0` = 无 L0 target，`1` = 有 L0 target，`2` = 输入非法或执行失败。 |
| `tools/length_gate.py` | 按 section 的散文长度预算增量门（规范 §5.3）。两个版本之间存在无理由净增长则 exit 1；`--allow` 记录理由。 |
| `tools/rewrite_reward.py` | **先过**科学保真硬门再对改写候选排序。丢掉*或凭空加上*受保护不变量 → `-inf`。 |

#### L0 —— 词汇与领域 register

| 工具 | 用途 |
|---|---|
| `tools/deai_register.py` | 领域 register：稿子反复依赖、但本领域语料里不存在的术语。判据是语料的 document frequency，而不是一张手工整理的"外来词表"。复合词按其最罕见的部分判定。只产 advisory。 |
| `tools/ai_ism_negatives_handcrafted.txt` | 旧版分类器的种子负样本（数据资产）。 |

#### L1 —— 信息分布

| 工具 | 用途 |
|---|---|
| `tools/deai_metrics.py` | model-free 的信息分布 finding —— 句长变化、连接词开头 —— 带显式标定状态。 |
| `tools/deai_oracle.py` | 可选的 token surprisal 与 UID 证据。资产不可用与兼容性阈值保持显式。 |

#### L2 —— 句子与全文结构

| 工具 | 用途 |
|---|---|
| `tools/deai_structure.py` | 句子与段落构造：announced enumeration、重复框架、并列串、对称结构等模板家族。 |
| `tools/deai_salience.py` | Salience hierarchy：一段文字里的数值能连续跑多远而中间没有一句解释性句子，对照按 section 分桶的人类参照。唯一消费"保留数字"那条 LaTeX 投影的工具。 |
| `tools/deai_docstructure.py` | 全文修辞形状与完整文档标定：dispersion band、按长度分层的联合流形、role coupling、split-conformal 操作点。 |
| `tools/deai_anchoring.py` | 按 section 类别条件化的 claim-anchoring 带 —— 一条**写作质量**轴，明确**不是** AI 判别轴。 |

#### L3 —— 学习型领域相似度

| 工具 | 用途 |
|---|---|
| `tools/deai_features.py` | 可复用的分布、UID、标点、embedding 与结构特征。 |
| `tools/deai_voice.py` | 可选的学习型领域相似度分诊。没有操作点的 bundle 一律 degraded，永远不是作者身份判决。 |
| `tools/train_voice_model.py` | 训练可选的领域相似度模型，按源论文分组。混淆审计是强制的。 |

#### L4 —— 协作式修复

| 工具 | 用途 |
|---|---|
| `tools/deai_partition.py` | 不动一个 token 的合并/拆分建议，把文档推向人类 dispersion band。只建议，由作者手动应用。 |
| `tools/deai_provenance.py` | 基于作者**自己**草稿历史的编辑 provenance 账本；按 token 编辑比把每段标为 AI-untouched → author-original。不是检测器；没有 AI 草稿祖先时为 `unmeasured`。 |
| `tools/deai_personal.py` | 个人 dispersion 基线，对照作者自己以前的论文 —— 一个无混淆的同作者参照。少于三篇时为 `unmeasured`。 |

#### 语料与 profile 构建

| 工具 | 用途 |
|---|---|
| `tools/build_profile.py` | 构建基础 field profile：抽取、可选的旧版分类器、范例缓存预热。 |
| `tools/extract_style.py` | 抽取词表、句子统计、转折词、描述性 dossier 和按 section 分类的范例库。 |
| `tools/extract_sections.py` | 源文本投影与分节层：section 词表与分类器、两条命名 LaTeX 投影、PDF 标题启发式。section 桶是 profile 里每一条按 section 参照分布的键，所以改这里就要重建 profile。 |
| `tools/retrieve_exemplars.py` | 按 section 与主题检索范例段落，走 embedding 或显式 fallback。 |
| `tools/fetch_arxiv_abstracts.py` | 抓取带日期的摘要语料用于受控评估与训练，可限定子领域 query set 与指定的 refereed 期刊。触发限流时**停止抓取并 exit 2**，而不是把被截断的语料当作完整的写下去。 |

#### 旧版与训练数据

| 工具 | 用途 |
|---|---|
| `tools/train_ai_ism_classifier.py` | 训练旧版 word-ngram 分类器，仅作为 degraded 的 advisory 证据使用。 |
| `tools/extract_md_negatives.py` | 为受控评估与训练收集候选生成段落。 |

> `tools/validate_plugin.py` 是开发/发布工具，不是产品工具，不计入上面的数量。

---

## 反馈契约

每条 finding 恰好带一个**后果类别**：

| 类别 | 含义 | 强制后果 |
|---|---|---|
| `integrity_blocker` | 科学记录可能是错的、无支撑的、自相矛盾的、不可复现的或不可用的 | **必须**从源头解决。不能以"风格偏好"豁免。 |
| `l0_target` | 一个 Tier A 词、一个 em-dash，或同一 section 内第二次及以后出现的 Tier B 词 | 改写到零。这不等于说论文在科学上无效。 |
| `advisory` | 结构、分布、学习型、修辞、清晰度或审美证据 | 排序，处理最强的几条，其余记录 disposition。 |

每个轴报告一个 **measurement state** —— `measured`、`degraded`、`unmeasured`
或 `not_applicable` —— 最终报告四种状态全列。**沉默永远不等于干净。**

每条 strong advisory 最终落到一个 **disposition**：`acted`、`accepted`、
`rejected_as_false_positive`，或带明确理由的 `pending`。普通 advisory 保持可见，
不要求消失 —— 这正是 [demo 1](#1-一份草稿的-before--after) 停在三条 advisory
而不是零条的原因。

## 按 field 组织的证据

一个 *field* 是 `style-corpus/` 下的一个子目录，加上 `style-profile/` 下同名的目录。
只有一个 field 时工具自动识别；有多个时必须显式传 `--field <name>`。
**代码里不假设任何特定 field 存在** —— 包括这份 README 通篇用到的 `wgl`。

```
style-corpus/<field>/tier-1-top/        顶刊范例
                     tier-2-mentor/     导师或目标作者范例
                     tier-3-reference/  其他相关领域论文
        |  python tools/extract_style.py --field <field>
        v
style-profile/<field>/                  生成的证据（gitignore）
```

给个量级参考 —— 本页每一个 `measured` 数字背后的参照 profile（直接读自制品）：

| 制品 | 规模 |
|---|---|
| `exemplar_paragraphs.jsonl` | 1,942 个按 section 分类的段落 |
| `register_lexicon.json` | 15,584 个 passage · 41,714 个词条 |
| `docstructure_baseline.json` | 493 篇完整文档 · conformal α 0.05 · 长度分层 [46, 76] |
| `anchoring_baseline.json` | 500 篇文档 |
| `salience_baseline.json` | abstract 13,438 · method 1,303 · intro 88 · discussion 78 · conclusion 41 · results 10（低于 30 passage 下限，仅排序） |

语料内容是**只读、受版权保护的输入**，永不入库。生成的 dossier 和范例可能引用源文字，
除非权利允许否则不得公开。语料 dossier 是描述性证据 —— 不是规范，也不是作者身份的
证明。全文级标定要求把**完整论文**作为独立观测；段落范例不能被重新贴标签当作独立文档。

## 设计哲学与技术栈

1. **唯一一份规范契约。** [`docs/SCIPAPER_STANDARD.md`](docs/SCIPAPER_STANDARD.md)
   说了算。skill、工具、profile、模型都只是实现或测量它；谁都不能另起一套后果词汇、
   不能造一个通用文字 PASS/FAIL、不能提出作者身份主张。
2. **证据不能自我提拔成政策。** 语料统计、阈值、学习型模型、评估结果都只影响 finding，
   永远不重新定义规范。
3. **诚实的 measurement state 优先于方便的默认值。** 缺标定、缺依赖、样本量不足，
   就保持 `unmeasured` 或 `degraded`。把"测不到"转换成"零个 finding"，
   正是这个项目要消灭的那个失败。
4. **保真无条件压倒风格。** 不是一个很大的权重 —— 是一道门。一句话的科学内容
   不能拿去和"读起来怎么样"做交易。
5. **负面结果照样发布**，连同杀死它们的那些数字。

| 层 | 选择 | 为什么 |
|---|---|---|
| 核心分析 | **Python ≥ 3.11 标准库** | linter、schema、model-free 的 L1/L2 轴、11 维 Mahalanobis 全文流形（不用 numpy）、validator 都能在裸解释器上跑。采用这个工具不该先编译一个 wheel。 |
| 标定 | **Split-conformal + Mondrian 分层** | 不假设分数分布，就能给出有限样本、分布无关的误标控制。 |
| 语料参照 | **用户提供、分 tier、gitignore** | 风格是相对领域而言的。通用先验正是被替换掉的那个东西。 |
| 可选模型 | `transformers`+`torch`、`scikit-learn`、`sentence-transformers` | 严格 opt-in flag。缺失只降级一条轴，从不让整次运行失败。 |
| 分发 | **Claude Code 插件**（`.claude-plugin/plugin.json`） | skill 放在 `skills/<name>/SKILL.md`，命名空间 `/sci-paper:<name>`。 |
| 契约执行 | `tools/validate_plugin.py` + GitHub Actions | 9 项检查覆盖 manifest、注册表、文档权威、记录数字、import、CLI 入口、退出语义、测试、CI 接线。漂移让 CI 挂掉，而不是慢慢堆积。 |

---

## 仓库结构

```text
sci-paper/
├── .claude-plugin/          plugin.json · marketplace.json
├── .github/workflows/       ci.yml —— 每次 push 与 PR 跑 validator + 测试
├── docs/                    ← 索引与权威顺序在 docs/README.md
│   ├── SCIPAPER_STANDARD.md      唯一规范契约（v3.6）
│   ├── architecture/             DEAI_SUBSYSTEM.md · EVALUATION.md（hub）+ evaluation/
│   └── design-notes/             冻结的、带日期的设计记录（不是现状文档）
├── skills/<name>/SKILL.md   8 个 skill
├── tools/                   25 个产品工具 + 仓库 validator
├── tests/                   15 个测试文件、213 个测试
├── style-corpus/<field>/    用户提供的只读语料（gitignore）
├── style-profile/<field>/   生成与标定的证据（gitignore）
├── ACKNOWLEDGMENTS.md       改编来源的致谢与采纳边界
├── CHANGELOG.md             逐版本历史
└── CLAUDE.md                本仓库的工作规则
```

## 开发与发布

`python tools/validate_plugin.py` 跑 9 项契约检查，
`python -m unittest discover -s tests -v` 跑 213 个测试；发布前两者都必须通过。
Validator 覆盖发布元数据、skill frontmatter、规范引用、文档权威边界与索引完整性、
记录的测试规模与真实发现的一致性、过期契约标记、产品注册表、Python 语法、
运行时 import、CLI 入口、schema 字段、linter 退出语义、Tier B 行为、测试与 CI 接线 ——
权威清单以 `tools/validate_plugin.py` 本身为准。发布还额外要求独立代码审查、
干净 checkout 验证，以及发布 commit 上的绿色 CI。

---

## 现状、已知限制与路线图

当前版本：**v0.27.1**。完整逐版本历史见 [CHANGELOG.md](CHANGELOG.md)。

**规范核心：** `docs/SCIPAPER_STANDARD.md` v3.6 —— 完整的去 AI 标准全在这一个文件里
（分层模型、全文尺度检测核心、协作层、`calibration_unit` 置信度封顶、§5.2 去 AI 化
步骤、§5.3 改写删减而非堆叠及其机械执行、以及刻意**不带检测器**发布的 §5.4 文章主旨）。
不存在单独的去 AI 标准文档。

### 已知限制，直说

| 限制 | 当前状态 |
|---|---|
| **没有学习型模型的操作点** | L3 以 `degraded` 发布。文档级 surprisal 路径已被*测量证明*给不出操作点（0.757 vs model-free 流形的 0.881）。 |
| **领域主题假阳** | 在领域主题与术语密集 AI 文字上 32–42%。这就是没有单一分数的原因。 |
| **短文档尾部功效** | 流形在短文档上对自然 AI 的 5% 尾部功效是 0.214 —— 2026-08-17 重建把它翻了三倍，但仍远低于 0.928 的长度公平排序所暗示的上限。 |
| **`results` salience 桶** | n=10，低于 30 passage 下限 —— 语料变大之前仅用于排序。 |
| **协作层工具** | `deai_provenance` 与 `deai_personal` 在作者提供自己的草稿历史或 ≥ 3 篇既往论文之前，诚实地保持 `unmeasured`。 |
| **`L1.distribution` / `L2.sentence_structure`** | 按设计是 `degraded` —— 不存在 `deai_policy.json` 操作点。上面每个 demo 里都看得到。 |
| **没有人工判断验证集** | salience 与 register 的操作点是语料参照的，不是人工标注的。 |
| **全新 clone 什么都测不出来** | 全部 profile 制品都 gitignore。在你用自己的论文建出 profile 之前，每条语料参照的轴都是 `unmeasured`。 |

### 路线图

- **长度感知流形** —— 按段落数归一化 dispersion 估计噪声，在不抬高人类误标率的前提下
  恢复短文档的 5% 尾部功效。
- **`deai_policy.json`** —— 为 L1 信息分布与句式结构强度提供成文操作点
  （语料单位、不确定度、适用性、验证行为）。这是把两条轴移出 `degraded` 的关键。
- **人工标注验证集**，用于 salience 与 register 的精确率/召回率。
- **对领域主题稳健的 L3 操作点**，带 provenance 与不确定度 —— 或者记录一个
  "以这套特征拿不到操作点"的结论。
- **补厚薄桶语料**（`results`，以及低于下限的各 section 层）。

**领域特定指引：** 弱引力透镜的科学锚点在适用处标 `[WGL]`。
共享的写作与审查政策与领域无关。

## 致谢与许可

sci-paper 改编了两个 MIT 项目的材料 ——
[academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer) 与
[blader/humanizer](https://github.com/blader/humanizer) —— 采纳了什么、
刻意没采纳什么，都记录在 [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)。

[MIT](LICENSE) 覆盖本仓库中撰写的代码、skill、文档与工具。
用户提供的语料内容与生成的摘录保留其原有权利，**不**在本仓库许可范围内。

---

<sub>**关键词：** Claude Code 插件 · Claude Code skills · agent skills · 科研写作 ·
学术写作 · 论文审查 · 同行评审 · 稿件准备 · AI 文本检测 · AI 生成文本检测器 ·
humanizer · 去 AI 化 · 降 AI 味 · 论文降重 · LaTeX · arXiv · 天体物理 · 弱引力透镜 ·
宇宙学 · ApJ · MNRAS · PRD · JCAP · NSF 申请书 · NIH Specific Aims · 科研写作助手 ·
语料驱动风格 · conformal prediction · 保形预测 · 均匀信息密度 · 可复现性 ·
科学诚信 · LLM 工具链 · 科研自动化。</sub>
