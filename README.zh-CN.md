# sci-paper

[![CI](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.36.0-informational.svg)](CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A5CF6.svg)](https://docs.claude.com/en/docs/claude-code/plugins)
[![Python](https://img.shields.io/badge/python-%E2%89%A5%203.11-3776AB.svg)](requirements.txt)
[![Tests](https://img.shields.io/badge/tests-463%20passing-success.svg)](tests/)

**一个 Claude Code 插件：在同一套 typed 标准下完成科研论文的写作、审查、去 AI 化与精简。
每条结论都可溯源，每个测不出来的轴都如实标为测不出来。**

面向 ApJ / MNRAS / PRD / JCAP 级别的论文，以及 NSF / NIH 基金申请书。
**12 个 skill · 38 个工具 · 463 个测试 · 一份规范 · 零作者身份判决。**

[English](README.md) — [它做什么](#它做什么) · [怎么做到的](#怎么做到的) ·
[实际效果](#实际效果) · [Benchmark 面板](#benchmark-面板) · [安装](#安装) ·
[Skills](#skills12-个) · [Tools](#tools38-个) ·
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
   （[demo 4](#4-一份零违禁词的文档照样被抓住)）。*
2. **一个 AI 检测分数没法告诉编辑要改什么** —— 而且它被领域、来源、章节体裁、长度、
   术语密度、数学密度全面混淆。它回答的是"这是谁写的"，而作者并不需要这个答案。
3. **审查会悄悄把"没测到"变成"好消息"。** 一个没标定的轴报告零个 finding，
   而零个 finding 读起来就是干净。

### 十二个 skill 按层

| 层 | Skill | 你得到什么 |
|---|---|---|
| **准备** | [`calibrate`](skills/calibrate/SKILL.md) | 把一个 field 从空语料走到可测量的轴 —— 抽取、建 profile、按 section 建参考分布，再到你自己的 held-out 标注。每个 field 跑一次：下面任何轴要报 `measured` 都依赖它，样本不足的分层保持 `unmeasured`，不会悄悄算通过。 |
| **规范** | [`paper`](skills/paper/SKILL.md) | 把写作框架载入上下文：准确性规则、公式与引用规范、正向叙述、带 canonical 例子的 L0 词汇政策、正向 voice 指引、measurement state、停止语义。 |
| **测量** | [`physics`](skills/physics/SKILL.md) | 测量原件，只产 finding。第一原则 P1–P8：量纲一致性、渐近极限、对称性与宇称、守恒律、信息论与统计不等式的前提、代数再推导、数值溯源、基础引用、编译完整性。是 `paper-review` 维度 K 的唯一来源；语域与 L0 委派给共享轴，不自带词表。 |
| **测量** | [`logic`](skills/logic/SKILL.md) | 测量原件，只产 finding。claim graph（循环论证、断链、偷换条件、未声明假设）、经验统计方法学（split、泄漏、多重比较、prior），以及声明-证据纪律的审查端：动词强度不得超过证据强度。是 `paper-review` 维度 C 的唯一来源。 |
| **测量** | [`mainline`](skills/mainline/SKILL.md) | 测量原件，只产 finding。建 paper-level purpose record 与 contribution graph，再按冷读者回答七问——读者在哪里需要回溯、补隐藏上下文，或在竞争解读间抉择？不预设三幕模板。是 `paper-review` 维度 E 的唯一来源。 |
| **测量** | [`figure-review`](skills/figure-review/SKILL.md) | 审的是 **150 DPI 的编译页**，不是源码。追溯 figure/caption/数据的 provenance，在像素级测量画布平衡，并把科学与构建矛盾同可读性建议分开。 |
| **动作** | [`de-ai`](skills/de-ai/SKILL.md) | 三过串联 —— 子系统测量（L0–L4）、结构 tell 审计，然后 **claim-first 改写**：从受保护的 claim graph 重建文字，而不是原地润色。`--audit-only` 只跑到测量为止。 |
| **动作** | [`condense`](skills/condense/SKILL.md) | 全文去冗余，遵循"每个事实只有一个 canonical 位置"、loop-until-dry 收敛，并以**机械长度门**作为"确实变短了"的收尾证明。 |
| **组合** | [`paper-review`](skills/paper-review/SKILL.md) | 溯源式 **A–R 审查**：数学、物理、逻辑与统计、语言、结构与叙事主线、引用、数据与图表、接口、冗余、可复现性、现代物理核查、跨章节一致性、对抗式验证（三 pass + 12-framing 升级）、staleness、过程残影、引用精确度、术语对齐。 |
| **组合** | [`final-review`](skills/final-review/SKILL.md) | 父级编排器：在**独立 worktree agent** 里跑 paper-review、figure-review、de-ai `--audit-only` 与 physics / mainline / logic 三个原件，合并 typed finding，并验证 disposition-complete 状态在连续多轮里稳定。 |
| **体裁** | [`proposal-polish`](skills/proposal-polish/SKILL.md) | NSF Project Summary/Description、NIH Specific Aims、fellowship。保留论文会删掉的"愿景+可行性"语域，强制 claim 与可行性匹配，最狠地打磨决定评分的前几页。 |
| **探索** | [`brainstorm`](skills/brainstorm/SKILL.md) | 辐射状研究方向探索器：每节点 12 条 framing pass、术语锚定到 glossary、每分支完整推导、递归发散直到收敛。严禁 defer / future-work / 半成品叶节点。 |

凡是产出 finding 的 skill 都跑在同一层证据之上 —— 35 个工具输出同一套 schema
`sci-paper.feedback.v1` —— 所以 linter、测量原件和编排器给出的 finding 是同一个
对象、同一个 ID。**组合只调用原件，绝不复述它们的检查项。**`calibrate` 构建的
就是它们赖以测量的这层证据。

### 工作边界 —— 它刻意不做什么

| 它不会 | 因为 |
|---|---|
| 给出作者身份判决或 "AI 百分比" | 学习型轴只是**领域相似度分诊**，在段落尺度封顶 0.5 置信度。它在领域主题 AI 文本上的假阳率是 28–39%（[为什么](#为什么没有单一分数l3-的混淆)）。 |
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
（[`rewrite_reward.py:56`](tools/rewrite_reward.py#L56)）。
见 [demo 3](#3-保真门枪毙了风格分最高的候选)。

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
就在[面板里](#全文尺度的判别力与假阳控制)。

**四 · register 来自你的语料，不是一张词表。** `deai_register.py` 标记稿子反复依赖
（≥ 15 次）、但在**你自己领域语料**里 document frequency 低于 1e-4 的术语。
没有任何手工整理的跨学科黑名单。正是这一点让 `AUC`（df 1）能和 `epoch`（df 402）、
`accuracy`（df 774）分开，而不需要任何人去维护一张天文例外表。复合词按其最罕见的
部分判定；`_` 或 `^` 后面的 `\mathrm{}` 是下标不是术语；所有格折叠。同一份语料还回答
一个更钝的问题，而且是穷举的：**零命中审计**列出正文里每一个本领域从未写过的词，
`deai_collocation.py` 列出每一句把本领域从不并置的常用词并置起来的句子（`physical
cells`、`controlled grid`），每个词对都带着"按机会本该写出它的 passage 数"。两者都是
带作者 disposition 的建议——本文自己定义的术语保留它的词和词对——都不是检测器：
已发表论文里的零命中词反而比机器草稿多（[§23](docs/architecture/evaluation/vocabulary-and-residue.md)）。

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

demo 1 是 **2026-08-26** 在 v0.32.0、`wgl` 参照 profile 上重跑的；demo 2 是 v0.28.0 的
带期记录，其草稿未留存。两个 demo 都早于语篇、collocation 与 residue 轴 —— 加 `--no-discourse --no-collocation --no-residue` 才复现得出上面的计数。没有一处是示意。全新 clone **不带**任何 profile（[为什么](#按-field-组织的证据)），
所以 `measured` 的轴需要你先用自己的论文建一份 profile。

### 1. 同一个段落的三种处理

比 before/after 更有用的是：**普通"去 AI"词表改一遍，和这套流程走一遍，各自改变了什么**。
同一个段落，同一个工具测量。原文取自本仓库 20 篇 AI 验证集里得分最差的那个 Results 段。

**A —— 原始生成。** `L0=1, advisories=4`

> …by a factor of 1.4, driven primarily by the removal of selection bias **rather
> than** a reduction in shape-noise itself. The dominant remaining systematic is
> PSF model **error:** a 2 per cent fractional error … **underscoring** that PSF
> characterization **rather than** the shear estimator will set the floor…

```
[l0_target L0 tier-a:underscoring]         Tier A 词汇命中。
[advisory  L0 corpus-zero:underscoring]    本领域词库中该词出现次数为 0。
[advisory  L2 structure-auxiliary:results] antithesis-cluster；参照 results 占比 0.2%（n=3958）。
[advisory  L2 colon-elaboration]           散文冒号引出同位语式补充。
[advisory  L2 ing-tail:underscoring]       分词尾巴把解读挂在句尾。
```

**B —— 普通去 AI 处理。** 把命中的词换成同义词，删掉 em-dash。机械层就这些。
`L0=0, advisories=3`

```
[advisory  L2 structure-auxiliary:results] antithesis-cluster    <- 没变
[advisory  L2 colon-elaboration]           散文冒号              <- 没变
[advisory  L2 ing-tail:highlighting]       分词尾巴              <- 跟着替换改了名
```

看第三行。`underscoring` 变成 `highlighting`，Tier A target 和 corpus-zero 两条都清了 ——
**而 ing-tail 那条只是换了个名字**。句子依旧把解读当分词尾巴挂在句尾，变的只是那个词。
**这份文本现在能过关键词检测，读起来却和之前一模一样。**

**C —— sci-paper 流程。** 在保真不变量下做 claim-first 改写：每个数字、单位、引用
都保留，长度预算不超。`L0=0, advisories=1`

> …by a factor of 1.4. Most of that gain comes from removing the selection bias;
> the shape-noise contribution is essentially unchanged. The dominant remaining
> systematic is PSF model error. A 2 per cent fractional error propagates to
> Δm ≈ 4×10⁻³… PSF characterization will therefore set the systematic floor.

```
[advisory L2 salience-recital:results] 这个 results 段在念数字：
  max_recital_run_frac 0.20 (p71), recital_frac 0.40 (p87), numerals_per_sentence 1.20 (p95).
  连续带数字的句子最长 1/5 句，对照 n=3206 个人类 results 段。
```

剩下这条是**另一个层次的意见**：机械 tell 已经没了，工具转而给出编辑判断 ——
一个段落该带多少数字，之后论证才该接手 —— 参照的是 3,206 个人类 Results 段。

| | A：原始生成 | B：词表去 AI | C：sci-paper |
|---|---:|---:|---:|
| L0 target · advisory | 1 · 4 | **0** · 3 | **0** · **1** |
| 结构类 finding 解决数 | — | **0 / 3** | **3 / 3** |

放到**整个 20 篇集合**上，同样三种处理、同一个工具：带 L0 target 的文档
**4 → 0 → 0**；em-dash **2 → 0 → 0**；advisory **331 → 329 → 315**；
strong advisory **131 → 131 → 126**。词表处理让 strong advisory 变化了**整整 0 条** ——
它删掉的是检测器会 grep 的东西，读者会注意到的一样没动。（表里的 C 用的是仓库中
独立写成的 de-AI 集，不是 A 的改写，所以这张表读作"同题材的三个总体"；上面那个
段落才是严格同源对照。）

### 2. 一份草稿的 before / after

一份 189 词、两个 section 的草稿：六个 Tier A 词、两个 em-dash、一处序数串，
以及连续六句在念参数网格。

```console
$ python tools/ai_ism_lint.py before.tex --field wgl \
    --structure --distribution --register --salience --document-structure --no-discourse

findings: blockers=0 L0=8 advisories=10 (strong=1)
axis L0.lexical: measured   axis L0.register: measured   axis L2.salience_hierarchy: measured
axis L1.distribution: degraded: using documented compatibility heuristics; deai_policy.json is unavailable
axis L2.sentence_structure: degraded: template evidence measured, but no calibrated strong-feedback operating point is available

  L  3 [l0_target L0 tier-a:pivotal]  Tier A lexical target 'pivotal' is present.
  L  8 [l0_target L0 em-dash]         Em-dash punctuation is an L0 rewrite target.
  ...
  L 14 [advisory L2 salience-recital:method strong] method passage recites its quantities:
       max_recital_run_frac 0.60 (p98), recital_frac 0.60 (p96), numerals_per_sentence 1.80 (p98).
       Longest run of numeral-bearing sentences is 6 of 10, against an n=5957 human method reference.
  L 14 [advisory L2 structure-template:method] repeated sentence-construction template(s):
       ordinal-run; reference method fraction 5.3% (n=8144).
$ echo $?   # -> 1
```

仔细读最后一条。它说的不是"你用了列表"，而是*这种构造在你自己语料的 8,144 个人类
method 段里出现于 5.3%，你这段是其中之一* —— 参照样本量一并给出，好让你判断这 5.3%
值多少分量。

做完 claim-first 改写（24 个网格数值一个不少）后 `L0=0 advisories=0`（exit 0），
长度闸门确认它确实变短了：

```console
$ python tools/length_gate.py after.tex --before before.tex
section                       before   after   delta  status
Introduction                      84      58     -26  ok
Method                           105      88     -17  ok
TOTAL                            189     146     -43
net unjustified growth: -43 words (tolerance 0)            # exit 0
```

### 3. 保真门枪毙了风格分最高的候选

同一个 method 段的三个改写候选，对照一份写明 claim 与受保护内容的 reference 排序：

```console
$ python tools/rewrite_reward.py --field wgl --reference ref.txt --original orig.txt \
    --candidates cand1.txt cand2.txt cand3.txt

rank cand  combined   voice  fidelity   Δadv eligible  L0(r/c)  words(o/c)
   1    0     0.205   0.491     0.549   0.00     True  0/0  105/88  cand1.txt
   2    2     0.201   0.599     0.517   0.00     True  0/0  105/88  cand3.txt
   3    1      -inf   0.729     0.554   0.00    False  0/0  105/65  cand2.txt
     missing: {'numbers': ['0.01', '0.06', '12', '3', '4', '6', '8'], 'acronyms': ['PSF']}

[best] candidate 0: cand1.txt                               # exit 0
```

把 `voice` 列和 `eligible` 列对着看。`cand2` 的学习式领域相似度是 **0.729**，
**三个里最高**，而且 65 词最紧 —— 它输给了"什么都不选"，因为它在压缩时丢了七个数字
和一个缩写。风格分根本没有投票权。如果三个全不合格，工具退出 `1`：
保留原文、重新生成更紧的版本，而不是崩溃。

### 4. 一份零违禁词的文档，照样被抓住

一份 5 个 section 的稿子，没有 Tier A 词汇、没有 em-dash、没有 register 离群词
—— **`L0=0`** —— 逐句读都通顺：

```console
$ python tools/ai_ism_lint.py big.tex --field wgl --document-structure ...
findings: blockers=0 L0=0 advisories=10 (strong=1)
axis L2.document_structure: measured

  L 1 [advisory L2 document-dispersion-manifold strong] The document's joint cross-paragraph
      dispersion sits 18.43 Mahalanobis units from the human center (conformal p = 0.0122
      <= alpha 0.05 against 81 held-out human papers (stratum 0 manifold)): its paragraph-shape
      variation pattern departs from the human band as a whole. This is a measured deviation,
      not an AI verdict.

  L 1 [advisory L2 document-uniformity:word_count]     4.859 vs human low-tail 39.260
  L 1 [advisory L2 document-uniformity:n_sentences]    0.484 vs human low-tail  1.631
  L 1 [advisory L2 document-uniformity:mean_sent_len]  2.973 vs human low-tail  5.268
  L 1 [advisory L2 document-uniformity:paren_rate]     0.000 vs human low-tail  0.749
  L 1 [advisory L2 document-uniformity:equivocal_rate] 0.000 vs human low-tail  0.350
```

这就是第一种失败模式，按需复现。一个"清词"工具会报告这份文档干净。全文尺度的轴
把它放在 `p = 0.0122`（对照留出的人类论文），再点名是哪五个维度把它送到那里的：
段落长度全都一样、句子数全都一样，而且**一次括号、一次 hedge 都没有**。
它依然拒绝说这是 AI 写的 —— 诚实的陈述是*这份文档的段落形状变化偏离了人类带*，
finding 说的正是这句话。

### 5. 一次完整 review 长什么样

linter 只是其中一路输入。`/sci-paper:final-review` 会在隔离 worktree 里编排其余部分，
把六条独立通路的 typed finding 合并：

| 通路 | 覆盖内容 |
|---|---|
| `paper-review` | **A–R** 共 18 个维度：数学、物理、逻辑与统计、语言与去 AI、文档结构与叙事主线、引用存在性与相关性、数据/结果/图表、接口、冗余、可复现性、现代物理检查、系统一致性、对抗式验证、陈旧与漂移、过程残留、内部草稿语言、参考文献精度、术语表对齐 |
| `figure-review` | 从编译后的 PDF 以 150 DPI 重渲每张图 —— 图/caption/数据一致性、单位、印刷尺寸下的可读性、色彩可及性、浮动体位置、跨图一致性 |
| `de-ai --audit-only` | L0–L4 测量栈，加上引入的 humanizer 结构 tell 目录 |
| `physics` · `mainline` · `logic` | 三个测量原件，各起一个兄弟 agent：第一性原理 P1–P8；对着贡献图回答冷读者的七个问题；claim 图、经验统计与 claim–evidence 纪律 |

合并规则才是重点：**integrity blocker 必须解决、L0 target 必须清零、每条 strong
advisory 必须有明确 disposition，而普通 advisory 与不可用的轴保持可见**。轮次会一直
重复，直到这个"disposition 完备"的状态**连续两轮稳定** —— 不是直到反馈数归零，
更不会给出一个全局 PASS/FAIL。维度 **M** 会用三遍独立推导复核论文自己的数学，
分歧则通过十二种 framing 升级为 `CONFIRMED` / `REFUTED` / `MARGINAL`。

---

## Benchmark 面板

两类数字，不能互换：**判别力与标定**，读自评估记录；**延迟**，为这份 README
第一手实测。

### 全文尺度的判别力与假阳控制

AUC 是长度公平的：每份文档只跟**自己那个长度层**的人类论文比（短层 170 篇）。
标记率走 split-conformal，按长度三分位做 Mondrian 分层，对可交换的人类论文给出
**有限样本、分布无关的 `P(误标) ≤ α`**。
来源：[§9.5](docs/architecture/evaluation/document-scale.md)。

| 对比 | 流形 AUC | role AUC | 流形尾功效 | role | 并集 |
|---|---:|---:|---:|---:|---:|
| 人类 vs **自然** AI | **0.933** | 0.690 | 0.250 | 0.036 | 0.286 |
| 人类 vs **去 AI 化后**的 AI（段落级去 AI 当攻击） | **0.943** | 0.742 | 0.400 | 0.268 | **0.600** |
| 人类 vs **形状对抗**的 AI（刻意制造参差） | 0.927 | **0.810** | 0.184 | 0.316 | 0.447 |
| 人类 vs **骨架匹配**的结构克隆 | 0.914 | 0.507 | 0.292 | 0.042 | 0.333 |
| 人类 vs **长文**生成 *（长期证伪靶）* | 0.740 | 0.634 | **0.000** | 0.069 | 0.069 |
| **人类误标率**，492 篇直接打分，α = 0.05 | — | — | **0.033** | **0.043** | 0.075 |

两条轴天生互补：流形对包括结构克隆在内的每一档都保持稳健判别，而 role 轴的功效
恰好集中在把流形逼到最窄的那一档上。跨越 42 倍的语料重建，八个已发表 AUC
**全部复现在 0.012 以内** —— 这是逐值核对，不是总数对上就算数。

尾部功效照实报，包括弱的地方和为零的地方。长文生成在严格操作点上**完全抓不到**。
短文档仍是流形最弱的一档：在短层内部，人类距离与段落数仍有 **−0.414** 的相关。
更细的分层已经测过并被否掉（不涨功效，还倒赔），所以真正的修法是估计量噪声模型，
本版**没有**发布。

### 为什么没有单一分数：L3 的混淆

学习型段落尺度模型效果不错 —— 而它**依然**以 `degraded` 发布，理由是测出来的。
2026-08-26 用 44,576 条记录重训。
来源：[§7](docs/architecture/evaluation/learned-model.md)。

| 指标 | 值 | 95% 切分区间 | 上一版语料 |
|---|---:|---|---:|
| 分组切分 AUC（20 次切分，整篇论文留出） | **0.9502** | 0.9428 – 0.9588 | 0.9320 |
| 匹配层 AUC（section × 长度 × 数学 × 领域词） | **0.9303** | 0.9173 – 0.9499 | 0.9236 |
| 平衡准确率 | **0.8736** | 0.8630 – 0.8897 | 0.8509 |
| 作者 hard-set、**真实 provenance** | 0.934 | 0.838 – 0.998 | 0.937 |
| 假阳率 —— 通用公开 AI 文本 | 0.053 | 0.030 – 0.068 | 0.086 |
| 假阳率 —— **领域主题 AI 文本** | **0.285** | 0.209 – 0.344 | 0.318 |
| 假阳率 —— **领域术语密集 AI 文本** | **0.410** | 0.271 – 0.534 | 0.417 |

0.95 的 AUC 头条数字，和 28–39% 的领域主题假阳率，是同一个模型。学习型分数有一
部分测的是*领域 register*，所以它恰恰在"去 AI 必须抓住的那个分布"上不可靠。
**把语料放大 2.6 倍并没有修好它** —— 术语密集档 0.417 → 0.410，落在切分区间内 ——
两次在规模差异极大的语料上的重训，现在一致指向：这个混淆属于特征集，不属于某一份
训练语料。这就是 L3 只做分诊、在段落尺度封顶 0.5 置信度、永远不是作者身份判决的
原因。文档级 surprisal 路径也测了（0.757），比 model-free 流形（0.881）更弱，
且对它毫无增益。

重训**不保证行为等价，也不宣称等价**：同一批 1,845 个段落经两个 bundle 打分，
degraded 模式真正消费的那个**排序**保持在 Spearman **ρ = 0.846**，被推到人前复核的
三个段落平均重合 **0.654**。schema、特征、`degraded` 姿态都没变，也没有凭空引入
阈值 —— 但重跑一份旧的分诊清单，不会一字不差地复现。

### 延迟与仓库健康度

2026-09-04 实测，Windows 11、Python 3.13.3、RTX 4060 Ti，每行 7 次子进程运行取
中位数（套件取 3 次），含解释器启动。测试文档是一篇真实的 5,084 词语料论文，按其
LaTeX include 组装而成。标准库的每一行都重测了：解释器地板从 98 ms 走到 75 ms，所以
更早的表里没有一行还能直接比。两条模型驱动的行**没有**重测：整个测量期间另一个进程
把 GPU 占到 100%，在那种条件下量出来的数字描述的是争抢而不是这条轴——它们仍是
2026-08-27 的值。

| 通道 | 中位墙钟 | 依赖 |
|---|---:|---|
| Python 解释器地板 | 75 ms | — |
| L0 词汇 + register（含零命中审计） | **514 ms** | 标准库 |
| **全部 model-free 轴**（L0 + L1 + L2，含全文结构、语篇、collocation、residue） | **1.07 s** | 标准库 |
| 同上但加 `--no-collocation`（不加载词对库） | 474 ms | 标准库 |
| `length_gate.py` | 212 ms | 标准库 |
| `+ --oracle`（GPT-2-large token surprisal） | 33.8 s（2026-08-27） | `transformers` + `torch` |
| `+ --voice`（学习型 L3 分诊） | 37.2 s（2026-08-27） | `scikit-learn` + `sentence-transformers` |
| `validate_plugin.py` —— **10/10 通过** | 0.42 s | 标准库 |
| 完整测试套件 —— **463 通过**，23 个文件（3 次取中位数，落在 51.0 – 62.3 s） | 52.2 s | 标准库 |

一句话：**一份 5,084 词的稿子跑完全部 model-free 通道，在解释器地板之上约花 1.0 s**，
且不需要任何可选依赖——其中 0.6 s 是加载 541,309 个词对的 collocation 库，
`--no-collocation` 能把它降回约 0.4 s。两条模型驱动的轴比完整的 model-free 通道贵
30–35 倍，并且是显式 opt-in 的 flag —— lint 一篇论文不该需要一块 GPU。CI 每次推到
main 的 push 与每个 PR 都跑 validator + 套件，Python 3.11，Ubuntu。

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

## Skills（12 个）

每个 skill 具体做什么见[十二个 skill 按层](#十二个-skill-按层)。
调用方式 `/sci-paper:<name> draft.tex --field wgl`；`calibrate` 最先跑，每个 field 一次。

## Tools（38 个）

每条 finding 统一走 `sci-paper.feedback.v1` 契约；语料/训练类条目产出的是
artifact。`layer` 列是该工具服务的轴 —— `core` 契约与闸门，`build` 语料与
profile 构建，`eval` 可复现的证据。逐工具细节见 [tools/README.md](tools/README.md)。

| Tool | Layer | 作用 |
|---|---|---|
| `tools/deai_feedback.py` | core | 实现 `sci-paper.feedback.v1`：稳定 ID、后果类别、measurement state、disposition、排序、汇总、渲染。纯标准库。 |
| `tools/ai_ism_lint.py` | core | 统一 CLI。把 L0 与全部 advisory 轴聚合成一份排序过的 text/JSON 报告。退出码 `0` = 无 L0 target，`1` = 有 L0 target，`2` = 输入非法或执行失败。 |
| `tools/length_gate.py` | core | 按 section 的散文长度预算增量门（规范 §5.3）。两个版本之间存在无理由净增长、或净删减未达 `--require-shrink` 目标则 exit 1；`--allow` 记录理由。 |
| `tools/condense_map.py` | core | `/sci-paper:condense` 背后的可删图：复述（带 canonical home）、零信息句、死 figure/table/label/macro/缩写、冗长构式、重复符号释义、跨节重复段——每条带可释放词数，汇总成删减目标。它自己不删任何东西。 |
| `tools/deai_residue.py` | core | 编辑留下的痕迹：第一人称的研究旅程、编辑元文本、正文兑现不了的标题或 caption，以及加 `--before` 后本次编辑新增的标签。有 strong finding 则 exit 1。 |
| `tools/rewrite_reward.py` | core | **先过**科学保真硬门再对改写候选排序。丢掉*或凭空加上*受保护不变量 → `-inf`。 |
| `tools/deai_register.py` | L0 | 领域 register：稿子反复依赖、但本领域语料里不存在的术语。判据是语料的 document frequency，而不是一张手工整理的"外来词表"。复合词按其最罕见的部分判定。零命中审计列出正文里每一个 df 为 0 的词。只产 advisory。 |
| `tools/deai_collocation.py` | L2 | 把本领域从不并置的常用词并置起来的句子：相邻实词对在语料里零共现的比例，对照按 section 分桶的留一法参照；每个词对带自己的"按机会缺席"概率。只产 advisory；本文定义的术语保留它的词对。 |
| `tools/ai_ism_negatives_handcrafted.txt` | L0 | 旧版分类器的种子负样本（数据资产）。 |
| `tools/deai_metrics.py` | L1 | model-free 的信息分布 finding —— 句长变化、连接词开头 —— 带显式标定状态。 |
| `tools/deai_oracle.py` | L1 | 可选的 token surprisal 与 UID 证据。资产不可用与兼容性阈值保持显式。 |
| `tools/deai_structure.py` | L2 | 句子与段落构造：announced enumeration、重复框架、并列串、对称结构等模板家族；辅助家族（对偶、短反转句、论文当施事者、wh-cleft、修饰语堆叠）只命名句子，不进分数。 |
| `tools/deai_salience.py` | L2 | Salience hierarchy：一段文字里的数值能连续跑多远而中间没有一句解释性句子，对照按 section 分桶的人类参照。唯一消费"保留数字"那条 LaTeX 投影的工具。 |
| `tools/deai_discourse.py` | L2 | 语篇质地，两条都打**低尾**：`cohesion` 逐段的 given/new 衔接（一句话的实词有多大比例在上一句已经出现过），`hedging` 逐 **section** 的认知情态标记密度（每千词）。这里的缺陷是「缺席」而不是「过量」，所以打低尾。两条轴**单位不同、各自的产物各写各的 `unit`**：hedging 在段落尺度根本没有低尾（`wgl` 七个桶的 p10 全是 0.000），只有按 section 重组才分得开。hedging 只对 `intro` 说话 —— 那是它的操作点被验证能迁移的唯一桶（EVALUATION §19）。 |
| `tools/deai_reference.py` | L2 | 所有按桶参照的轴共用的那一份 `(feature, unit)` 百分位参照：0.01 分位网格、并列平台顶端的百分位读法、30 单位样本下限、段落与 section 两条扫描、产物读取与标定循环。不持有任何策略；它唯一的不变量是「标定与检测共用同一个单位、同一张网格」—— 正是这条检查抓出了 hedging 标定在一个没有低尾的单位上。 |
| `tools/deai_docshape.py` | L2 | 全文形状测量与完整文档标定：逐段特征向量、跨段 dispersion、联合 Mahalanobis 流形、role coupling、split-conformal 操作点，以及 baseline 构建器。2026-08-25 从 `deai_docstructure.py` 拆出，后者 re-export 这里每一个公开名字。 |
| `tools/deai_docstructure.py` | L2 | 全文修辞形状与完整文档标定：dispersion band、按长度分层的联合流形、role coupling、split-conformal 操作点。 |
| `tools/deai_anchoring.py` | L2 | 按 section 类别条件化的 claim-anchoring 带 —— 一条**写作质量**轴，明确**不是** AI 判别轴。 |
| `tools/deai_features.py` | L3 | 可复用的分布、UID、标点、embedding 与结构特征。 |
| `tools/deai_voice.py` | L3 | 可选的学习型领域相似度分诊。没有操作点的 bundle 一律 degraded，永远不是作者身份判决。 |
| `tools/train_voice_model.py` | L3 | 训练可选的领域相似度模型，按源论文分组。混淆审计是强制的。重导出 `voice_dataset.py` 与 `voice_audit.py` 的全部公共名。 |
| `tools/voice_dataset.py` | L3 | 记录装载、源族分组、仅用训练集的领域词表，以及带指纹的特征矩阵缓存。2026-08-26 从 `train_voice_model.py` 拆出。 |
| `tools/voice_audit.py` | L3 | 留出指标、bootstrap AUC 区间、作者 hard set，以及重复分组混淆审计。它不拟合任何模型，只产出让 bundle 离开 `degraded` 所需的证据。 |
| `tools/deai_partition.py` | L4 | 不动一个 token 的合并/拆分建议，把文档推向人类 dispersion band。只建议，由作者手动应用。 |
| `tools/deai_provenance.py` | L4 | 基于作者**自己**草稿历史的编辑 provenance 账本；按 token 编辑比把每段标为 AI-untouched → author-original。不是检测器；没有 AI 草稿祖先时为 `unmeasured`。 |
| `tools/deai_personal.py` | L4 | 个人 dispersion 基线，对照作者自己以前的论文 —— 一个无混淆的同作者参照。少于三篇时为 `unmeasured`。 |
| `tools/label_findings.py` | eval | 把五条会产出 finding 的轴（register、salience、cohesion、hedging、collocation）抽成人工标注表，再盲发一个子集算 intra-rater 一致性，按 `--population NAME=DIR` 命名的总体分层，逐轴报 precision、**合并**报 recall。任何不足 20 条标注的分层一律报 `unmeasured`，不给数字。 |
| `tools/eval_findings.py` | eval | 用**出处**当标签来测 register、salience、cohesion、hedging 与 collocation，而不是靠人工标注：在**留出**的 ApJ/ApJL/A&A 已发表论文、同体裁但参与过标定的论文（泄漏对照）、以及 `docval` 机器 tier 上各自的命中率，外加机器对留出人类的秩 AUC。register 那行是误报率；salience 那行不是——它的门是百分位，非零命中率是设计值，测的是标定迁移。 |
| `tools/eval_docscale.py` | eval | 复现 §9 的全文尺度表 —— 人类误标率与逐 tier 尾部功效 —— 把语料与每个 `docval` tier 都送进 finding 用的同一个操作点。 |
| `tools/build_profile.py` | build | 构建基础 field profile：抽取、可选的旧版分类器、范例缓存预热。 |
| `tools/cli_common.py` | build | 共享的命令行前置：UTF-8 stdout，以及每个 field 感知工具都要的 `--field` / `--profile-root` 选项。不持有任何策略。 |
| `tools/extract_style.py` | build | 抽取词表、句子统计、转折词、描述性 dossier 和按 section 分类的范例库。 |
| `tools/extract_sections.py` | build | 源文本投影与分节层：section 词表与分类器、两条命名 LaTeX 投影、PDF 标题启发式。section 桶是 profile 里每一条按 section 参照分布的键，所以改这里就要重建 profile。 |
| `tools/tex_macros.py` | build | 在装配好的文档根上一次性展开纯数值 `\newcommand` 宏，使作者写成宏的测量量能被计数数字的投影看见。保守策略：符号宏与带参数宏一律不动。 |
| `tools/retrieve_exemplars.py` | build | 按 section 与主题检索范例段落，走 embedding 或显式 fallback。 |
| `tools/fetch_arxiv_abstracts.py` | build | 抓取带日期的摘要语料用于受控评估与训练，可限定子领域 query set 与指定的 refereed 期刊；也可抓单个作者的完整 LaTeX 源（`--author` + `--author-is` + `--max-authors`）。触发限流时**停止抓取并 exit 2**，而不是把被截断的语料当作完整的写下去。 |
| `tools/train_ai_ism_classifier.py` | legacy | 训练旧版 word-ngram 分类器，仅作为 degraded 的 advisory 证据使用。 |
| `tools/extract_md_negatives.py` | legacy | 为受控评估与训练收集候选生成段落。 |

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
不要求消失 —— 这正是 [demo 2](#2-一份草稿的-before--after) 停在三条 advisory
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
| `exemplar_paragraphs.jsonl` | **27,917** 个按 section 分类的段落，来自 19 篇精选 + 500 篇参照论文 |
| `register_lexicon.json` | 41,710 个 passage · 53,414 个词条 |
| `uid_baseline.json` | 27,917 段（GPT-2-large）· 合并 global UID 3.303 ± 0.437 |
| `structure_baseline.json` | method 9,512 · results 3,958 · data 3,908 · intro 3,840 · discussion 3,647 · conclusion 2,609 · abstract 433 |
| `salience_baseline.json` | abstract 13,971 · method 6,959 · intro 3,264 · results 3,206 · data 3,016 · discussion 2,958 · conclusion 1,994 |
| `docstructure_baseline.json` | 507 篇完整文档 · conformal α 0.05 · 长度分层 [46, 75] |
| `anchoring_baseline.json` | 517 篇文档 · 六个 section 类全部高于 30 篇下限 |
| `voice_model.joblib` | 44,576 条记录 · 14 个特征 · **无操作点**，`degraded` |

每个桶都过了 30 passage 下限，没有一个是"仅排序" —— 这在 2026-08-25 之前并不成立：
当时 `results` 只有 26，而那被误诊为语料量不足。语料内容是**只读、受版权保护的输入**，
永不入库；生成的 dossier 可能引用源文字。dossier 是描述性证据，不是规范，也不是作者
身份的证明。全文级标定要求把**完整论文**作为独立观测 —— 段落范例不是文档，
一篇论文的 `\include` 片段同样不是。

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
├── .github/workflows/       ci.yml —— 推到 main 的 push 与 PR 跑 validator + 测试
├── docs/                    ← 索引与权威顺序在 docs/README.md
│   ├── SCIPAPER_STANDARD.md      唯一规范契约（v3.8）
│   ├── architecture/             DEAI_SUBSYSTEM.md · EVALUATION.md（hub）+ evaluation/
│   └── design-notes/             冻结的、带日期的设计记录（不是现状文档）
├── skills/<name>/SKILL.md   12 个 skill
├── tools/                   38 个产品工具 + 仓库 validator
├── tests/                   23 个测试文件、463 个测试
├── style-corpus/<field>/    用户提供的只读语料（gitignore）
├── style-profile/<field>/   生成与标定的证据（gitignore）
├── ACKNOWLEDGMENTS.md       改编来源的致谢与采纳边界
├── CHANGELOG.md             逐版本历史
└── CLAUDE.md                本仓库的工作规则
```

## 开发与发布

`python tools/validate_plugin.py` 跑 10 项契约检查，
`python -m unittest discover -s tests -v` 跑 463 个测试；发布前两者都必须通过。
Validator 覆盖发布元数据、skill frontmatter、规范引用、文档权威边界与索引完整性、
记录的测试规模与真实发现的一致性、过期契约标记、产品注册表、Python 语法、
运行时 import、CLI 入口、schema 字段、linter 退出语义、Tier B 行为、测试与 CI 接线 ——
权威清单以 `tools/validate_plugin.py` 本身为准。发布还额外要求独立代码审查、
干净 checkout 验证，以及发布 commit 上的绿色 CI。

---

## 现状、已知限制与路线图

当前版本：**v0.36.0**。完整逐版本历史见 [CHANGELOG.md](CHANGELOG.md)，更早的条目见 [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md)（v0.22.0–v0.27.0）与 [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md)（v0.1.0–v0.21.0）。

**规范核心：** `docs/SCIPAPER_STANDARD.md` v3.8 —— 完整的去 AI 标准全在这一个文件里
（分层模型、全文尺度检测核心、协作层与 residue 轴、`calibration_unit` 置信度封顶、§5.2 去 AI 化
步骤、§5.3 改写删减而非堆叠及其三处机械执行、以及刻意**不带检测器**发布的 §5.4 文章主旨）。
不存在单独的去 AI 标准文档。

### 已知限制，直说

| 限制 | 当前状态 |
|---|---|
| **没有学习型模型的操作点** | L3 以 `degraded` 发布。文档级 surprisal 路径已被*测量证明*给不出操作点（0.757 vs model-free 流形的 0.881）。 |
| **尾部功效数字是单次抽样** | 流形各 tier 的逐 seed 标准差是 0.04–0.18，比记录里几处曾被读作"提升"的差还大。`tools/eval_docscale.py` 用来重跑，而不是引用。 |
| **领域主题假阳** | 在领域主题与术语密集 AI 文字上 28–39%。**已以决定收口**：跨 2.6 倍语料区间的三次重训一致表明混淆在特征集里，因此这套特征拿不到对领域主题稳健的操作点。 |
| **短文档尾部功效** | 流形对短的自然 AI 文档，12 个 seed 平均 **0.170 ± 0.110**，而长度公平排序是 0.933。三条修法都做了、都失败：距离归一化（已否决）、更细分层、显式估计噪声协方差。 |
| **长文生成抓不到** | α = 0.05 下流形对长文 AI 的尾部功效是 **0.000** —— 在 2 种度量 × 4 种标定切分 × 12 个 seed 下都稳定。排序 AUC 是 0.729，说明信号在，操作点够不着。 |
| **协作层工具** | `deai_provenance` 与 `deai_personal` 在作者提供自己的草稿历史或 ≥ 3 篇既往论文之前，诚实地保持 `unmeasured`。 |
| **`L1.distribution` / `L2.sentence_structure`** | `degraded` —— 现在是有*测量依据*的。burstiness 在对抗文本上符号反转（AUC 0.181），signposting 低于随机（0.247），根本写不出一个操作点。 |
| **重训不保证行为等价** | 重建 profile 会重拟 L3。排序保持 ρ 0.846、分诊重合 0.654，但旧的分诊清单不会一字不差复现。 |
| **语料有四分之一从未被用上** | 匹配不到任何 section 桶的标题是被丢弃，而不是被猜进某个桶：`wgl` 里 9,178 个标题中有 **2,334 个（25.4%）**，`wgl-letter` 里 148 个中有 42 个。剩下的多是主题标题（"Matter power spectrum"）；"Measurements" 与 "Background" 因真歧义被拒绝加入。 |
| **register 在已发表文字上照样开火** | 在它从没见过的 203 篇留出 ApJ/ApJL/A&A 已发表论文上实测：v0.36.0 修掉标题投影后**每千词 0.0351 条**（之前是 0.0858），30.0% 的文档命中，对机器文本的秩 AUC **0.352** —— 它在人类论文上仍比在 AI 草稿上更爱开火。剩下 81 条 flag 里，95.1% 只要论文自己在库里就会消失。把用词门槛从 5 扫到 50，AUC **处处低于 0.5**：没有任何设置能把它变成检测器，它就是一条建议，切在「一篇够格送审的论文不会过半被点名」的第一个点上。这个结论已在第二个群体上复现 —— 按作者而非期刊取样的 22 篇导师论文（1996–2015），AUC **0.328**（[§21](docs/architecture/evaluation/held-out-labels.md)）。 |
| **建议质量仍未被标注** | 出处只能回答「它是否在已发表文字上开火」，回答不了「这条建议对不对」。salience 的门迁移得几乎精确（逐 passage 0.2775，期望 0.2710）；而在 v0.32.0 之前，它在 LaTeX 上读到的数字有 7.00% 是引用年份；建议本身的精确率与召回率仍需 `tools/label_findings.py`。 |
| **hedging 只对引言说话** | 认知情态轴发布时被收窄到只管 `intro` —— 在 203 篇留出的已审稿论文上，它的 p10 门在 `intro` 上开火率是 7.89%，而其他桶是 15–27% —— 那是审稿人已经接受的文字，且至少有一套生成流程落到随机以下。cohesion 不需要这条限制（七个桶 6.6–14.6%）。 |
| **两条词汇审计是建议，且要加载词对库** | 零命中审计列出语料从未写过的每一个词，而已发表论文里这种词反而比机器草稿多（每千词 2.66 个，203 篇留出论文篇篇都有，秩 AUC 0.221）；collocation 轴每次运行都要加载 541,309 个词对的库，model-free 那一行延迟上升的 0.6 s 就是它。两者都不是检测器；`--no-collocation` 可以跳过词对库（[§23](docs/architecture/evaluation/vocabulary-and-residue.md)）。 |
| **全新 clone 什么都测不出来** | 全部 profile 制品都 gitignore。在你用自己的论文建出 profile 之前，每条语料参照的轴都是 `unmeasured`。 |

### 路线图

空了。`label_findings.py` 已交付 —— 跑不跑标注是作者自己的事，不是仓库的事。本项目
自己的参照基准是 provenance：`eval_findings.py` 拿**已经存在的标注**（203 篇未见过的
已发表审稿论文等）给各轴打分。「这条建议对不对」需要人，上面的限制表里已写明。

**citation placement 不是「待定」，是被证伪了。** v0.32.0 留下的条件是「换一套独立生成的
机器库来验」，这次补上了：同一个模型（Codex `gpt-5.6-terra`）、同样 20 个题目，提示词只差
一行。不提引用时同一个统计量得 **0.053** —— 不是「没有区分度」，而是几乎同等强度地指向
**反方向**；提了就得 **0.734**。引用密度在这一行提示词之间摆动 12.5 倍（每千词 1.00 ↔ 12.55），
而人类中位数是 6.20，两个机器极端把人类分布夹在中间。信号是提示词，不是作者身份
（[§20](docs/architecture/evaluation/discourse-and-citation.md)）。

**以证伪收口，不是以发布收口。** 长度感知流形、扩大 conformal 标定集、长文尾部功效、
三次 L3 重训、留出对样本内的泄漏估计、register 操作点，以及这次的 citation placement ——
全部做出来、测过、然后被否决，每一条在上表里都有自己的一行。同一批工作里，cohesion 与
hedging 两条轴（roadmap rank 6，自 v0.26.1 挂着）**发布**了，其中 hedging 被收窄到只管
`intro`。`deai_policy.json` 维持撤回；细节见
[§9.4c](docs/architecture/evaluation/document-scale.md)、
[§18.4](docs/architecture/evaluation/projection-and-operating-point.md)。

**v0.28.0 已收口。** `deai_policy.json` 是**撤回**而非推迟：在 500 篇人类论文上测量，
它要设阈值的那两个统计量都不具判别力
（[§16](docs/architecture/evaluation/lexical-structure-uid.md)）；补厚薄桶语料也已完成。
**领域特定指引：** 弱引力透镜的科学锚点在适用处标 `[WGL]`，共享的写作与审查政策与领域无关。

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
