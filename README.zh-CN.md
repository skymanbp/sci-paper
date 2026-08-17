# sci-paper

[![CI](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.27.1-informational.svg)](CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A5CF6.svg)](https://docs.claude.com/en/docs/claude-code/plugins)

**一个 Claude Code 插件：在同一套 typed 标准下完成科研论文的写作、审查、去 AI 化与精简。
每条结论都可溯源，每个测不出来的轴都如实标为测不出来。**

面向 ApJ / MNRAS / PRD / JCAP 级别的论文，以及 NSF / NIH 基金申请书。
8 个 skill、24 个工具、208 个测试、一份规范。

[English →](README.md) · [文档索引 →](docs/README.md) · [规范正文 →](docs/SCIPAPER_STANDARD.md)

---

## 目录

- [它解决什么问题](#它解决什么问题) · [牛逼在哪里](#牛逼在哪里)
- [怎么做的](#怎么做的) · [安装](#安装) · [快速上手](#快速上手)
- [Skills（8 个）](#skills8-个) · [Tools（24 个）](#tools24-个)
- [反馈契约](#反馈契约) · [按 field 组织的证据](#按-field-组织的证据)
- [仓库结构](#仓库结构) · [开发与发布](#开发与发布) · [现状](#现状)

---

## 它解决什么问题

技术论文有三种毁掉稿子的失败模式，没有一种是"词汇问题"：

1. **换完词以后，文字读起来还是像机器写的。** 把 "delve" 换成 "examine"，更深的规律
   一点没动：句长变化被抹平、句式模板化、全文修辞形状过度规整、claim 背后没有证据。
2. **一个 AI 检测分数没法告诉编辑要改什么** —— 而且它被领域、来源、章节体裁、长度、
   术语密度、数学密度全面混淆。它回答的是"这是谁写的"，而作者并不需要这个答案。
3. **审查会悄悄把"没测到"变成"好消息"。** 一个没标定的轴报告零个 finding，
   而零个 finding 读起来就是干净。

sci-paper 三条全部拒绝：它输出 **typed、排序过、可溯源的 finding** 而不是分数；
它从不宣称能识别作者；测不出来的轴会明说测不出来。

## 牛逼在哪里

| | 多数写作工具 | sci-paper |
|---|---|---|
| **输出** | 一个不透明的分数，或者直接给你改完的文本 | 带稳定 ID 的 typed finding，按后果排序，每条都有 source trace 和推荐动作 |
| **缺标定时** | 当作干净，静默通过 | 显式标 `unmeasured` / `degraded`，写明原因和补齐它需要什么 |
| **改写** | 优化一个风格分数 | **先过科学保真硬门**：丢掉*或者凭空加上*一个数字、单位、引用、公式、缩写、比较方向、否定、因果方向 → 该候选得分 `-inf`，永远不可能胜出 |
| **长度** | 每"修一次"就更长 | 机械长度预算：每次编辑的默认方向是*更短*；增长必须有记录在案的理由 |
| **作者身份** | "87% 由 AI 生成" | 绝不。学习型分数只是*领域相似度分诊*，在段落尺度被结构性地封顶在 0.5 置信度 |
| **风格参照** | 一个通用模型先验 | **你自己领域的语料** —— 从你提供的论文里抽取的描述性统计与范例 |
| **负面结果** | 悄悄丢掉 | 记录在案。"文章主旨（thesis spine）"信号的三种表层形式化全部被构建、测量并**证伪**；该规则**不带检测器**发布，规范明文禁止在它上面建阈值 |

最后一行就是整个设计哲学的缩影：**一个被证伪的检测器也是证据，它留在记录里。**
见 [docs/architecture/EVALUATION.md](docs/architecture/EVALUATION.md)。

## 怎么做的

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
它终止于一个 *disposition-complete* 状态 —— 不是"零条 advisory"，
更不是论文级别的 PASS。

## 安装

```bash
git clone https://github.com/skymanbp/sci-paper.git
```

注册到 Claude Code：

```bash
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

四件事：**写**、**改**、**审**、**探索**。

#### 写

| Skill | 做什么 |
|---|---|
| [`paper`](skills/paper/SKILL.md) | 写作框架：准确性规则、公式与引用规范、正向叙述、带 canonical 例子的 L0 词汇政策、正向 voice 指引、measurement state、停止语义。 |
| [`proposal-polish`](skills/proposal-polish/SKILL.md) | 基金申请书 register（NSF Project Summary/Description、NIH Specific Aims、fellowship）。保留论文会删掉的"愿景+可行性"语域，强制 claim 与可行性匹配，最狠地打磨决定评分的前几页。绝不编造 preliminary data、合作方或推荐信。 |

#### 改

| Skill | 做什么 |
|---|---|
| [`de-ai`](skills/de-ai/SKILL.md) | 三过串联：子系统测量（L0–L4）、vendored humanizer 结构 tell 审计、然后 **claim-first** 改写 —— 从受保护的 claim graph 重建文字，而不是原地润色。`--audit-only` 只跑前两过供审查集成。 |
| [`condense`](skills/condense/SKILL.md) | 全文去冗余，遵循"每个事实只有一个 canonical 位置"，loop-until-dry 收敛，以机械长度门作为收尾证明。 |

#### 审

| Skill | 做什么 |
|---|---|
| [`paper-review`](skills/paper-review/SKILL.md) | 溯源式 **A–R** 审查：数学、物理、逻辑与统计、语言与去 AI、结构与叙事主线、引用、数据与图表、接口、冗余、可复现性、现代物理核查、跨章节一致性、对抗式验证（三 pass + 12-framing 升级）、staleness、过程残影、内部草稿语言、引用精确度、术语对齐。 |
| [`figure-review`](skills/figure-review/SKILL.md) | 审的是 **150 DPI 的编译页**，不是源码。追溯 figure/caption/数据的 provenance，在像素级测量画布平衡，并把科学与构建矛盾同可读性、审美建议分开。 |
| [`final-review`](skills/final-review/SKILL.md) | 父级编排器。在**独立 worktree agent** 里跑 paper-review、figure-review、de-ai `--audit-only` 和 modern-physics-review，合并 typed finding，并验证 disposition-complete 状态在连续多轮里稳定。 |

#### 探索

| Skill | 做什么 |
|---|---|
| [`brainstorm`](skills/brainstorm/SKILL.md) | 辐射状研究方向探索器：每节点 12 条 framing pass、术语锚定到 glossary、每分支完整推导、递归发散直到收敛。**严禁** defer / future-work / 半成品叶节点。 |

## Tools（24 个）

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
| `tools/extract_style.py` | 抽取词表、句子统计、转折词、描述性 dossier 和按 section 分类的范例库。拥有两条命名 LaTeX 投影与 section 分桶词汇表。 |
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
`rejected_as_false_positive`，或带明确理由的 `pending`。
普通 advisory 保持可见，不要求消失。

## 按 field 组织的证据

一个 *field* 是 `style-corpus/` 下的一个子目录，加上 `style-profile/` 下同名的目录。
只有一个 field 时工具自动识别；有多个时必须显式传 `--field <name>`。
代码里不假设任何特定 field 存在。

```
style-corpus/<field>/tier-1-top/        顶刊范例
                     tier-2-mentor/     导师或目标作者范例
                     tier-3-reference/  其他相关领域论文
        |  python tools/extract_style.py --field <field>
        v
style-profile/<field>/                  生成的证据（gitignore）
```

语料内容是**只读、受版权保护的输入**，永不入库。生成的 dossier 和范例可能引用
源文字，除非权利允许否则不得公开。语料 dossier 是描述性证据 —— 不是规范，
也不是人类或机器作者身份的证明。

全文级标定要求把**完整论文**作为独立观测。段落范例不能被重新贴标签当作独立文档。

## 仓库结构

```text
sci-paper/
├── .claude-plugin/          plugin.json · marketplace.json
├── .github/workflows/       ci.yml —— 每次 push 与 PR 跑 validator + 测试
├── docs/                    ← 文档索引在 docs/README.md
│   ├── SCIPAPER_STANDARD.md      唯一规范契约（v3.6）
│   ├── architecture/
│   │   ├── DEAI_SUBSYSTEM.md     实现架构
│   │   └── EVALUATION.md         当前指标、缺口、混淆因素、被证伪的信号
│   └── design-notes/             冻结的、带日期的设计记录（不是现状文档）
├── skills/<name>/SKILL.md   8 个 skill
├── tools/                   24 个产品工具 + 仓库 validator
├── tests/                   15 个测试文件、208 个测试
├── style-corpus/<field>/    用户提供的只读语料（gitignore）
├── style-profile/<field>/   生成与标定的证据（gitignore）
├── CHANGELOG.md             逐版本历史
└── CLAUDE.md                本仓库的工作规则
```

## 文档

| 读这个 | 是为了 |
|---|---|
| [docs/README.md](docs/README.md) | 文档索引与权威顺序 |
| [docs/SCIPAPER_STANDARD.md](docs/SCIPAPER_STANDARD.md) | **规范契约。** 任何东西与它冲突，以它为准。 |
| [docs/architecture/DEAI_SUBSYSTEM.md](docs/architecture/DEAI_SUBSYSTEM.md) | 子系统是怎么实现的 |
| [docs/architecture/EVALUATION.md](docs/architecture/EVALUATION.md) | 什么测了、什么没测、以及全部已知混淆 |
| [tools/README.md](tools/README.md) | 逐工具的注册表、标定与失败行为 |
| [style-corpus/README.md](style-corpus/README.md) | 怎么提供领域语料 |
| [style-profile/README.md](style-profile/README.md) | 生成资产与构建边界 |

## 开发与发布

```bash
python tools/validate_plugin.py                  # 9 项契约检查
python -m unittest discover -s tests -v          # 208 个测试
```

Validator 检查发布元数据、skill frontmatter、规范引用、文档权威边界与索引完整性、
记录的测试规模与真实发现的一致性、过期契约标记、产品注册表、Python 语法、
运行时 import、CLI 入口、schema 字段、linter 退出语义、Tier B 行为、测试与 CI 接线。
权威清单以 `tools/validate_plugin.py` 本身为准。

发布还额外要求独立代码审查、干净 checkout 验证，以及发布 commit 上的绿色 CI。

## 现状

当前版本：**v0.27.1**。完整逐版本历史见 [CHANGELOG.md](CHANGELOG.md)。

- **规范核心：** `docs/SCIPAPER_STANDARD.md` v3.6 —— 完整的去 AI 标准全在这一个文件里
  （分层模型、全文尺度检测核心、协作层、`calibration_unit` 置信度封顶、§5.2 去 AI 化步骤、
  §5.3 改写删减而非堆叠及其机械执行、以及刻意**不带检测器**发布的 §5.4 文章主旨）。
  不存在单独的去 AI 标准文档。
- **Skills（8）：** `paper`、`de-ai`、`condense`、`paper-review`、`figure-review`、
  `brainstorm`、`final-review`、`proposal-polish`。
- **Tools（24）：** 上面的注册表是精确的。
- **已标定的缺口，直说：** 没有学习型模型的操作点（L3 文档级 surprisal 路径已被
  *测量证明*给不出操作点）；作者 hard-set 标注未完成；协作层工具
  （`deai_provenance`、`deai_personal`）在作者提供自己的草稿历史或既往论文之前
  诚实地保持 `unmeasured`。
- **领域特定指引：** 弱引力透镜的科学锚点在适用处标 `[WGL]`。
  共享的写作与审查政策与领域无关。

## 致谢

- **[AIScientists-Dev/academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer)**
  （MIT）—— 2026-07-16 的词表扩充（`underscore*`、`pivotal`、`tapestry`、`testament`、
  `realm*`、`intricate`、`foster*`）、`serves as` / `ing-tail` / `colon-elaboration`
  linter 规则、`skills/paper/SKILL.md` 的 Claim–Evidence Discipline 与 Preserve List
  章节、`proposal-polish` skill，以及 `de-ai` 的 Layer 1–5 审计目录，均改编自该仓库。
  每一条词汇采纳都在分 tier 之前对照过策展的领域语料重新验证；与天文用法冲突的
  venue-specific 规则（`landscape`、一刀切禁用 `demonstrate`/`significantly`）
  **刻意未采纳**。academic-humanizer 自身构建于 blader/humanizer（MIT）之上。
- **[blader/humanizer](https://github.com/blader/humanizer)**（MIT）—— `de-ai` 的
  结构模式 2.12–2.16（假区间、格言公式、诉诸权威的修辞套路、人造断句戏剧感、
  连字符复合谓语）、其 Pass-2 自审步骤与 false-positive 护栏改编自该 skill。
  只吸收了其中与学术写作相关的结构 tell；其博客/聊天特有的模式（emoji、
  标题式大小写、chatbot 残留、弯引号标记）与其 `landscape` 词表刻意未采纳，
  因为这里以语料证据为准。

## 许可

[MIT](LICENSE) 覆盖本仓库中撰写的代码、skill、文档与工具。
用户提供的语料内容与生成的摘录保留其原有权利，**不**在本仓库许可范围内。

---

<sub>**关键词：** Claude Code 插件 · agent skills · 科研写作 · 学术写作 · 论文审查 ·
同行评审 · 稿件准备 · AI 文本检测 · AI 生成文本 · humanizer · 去 AI 化 · 降 AI 味 ·
LaTeX · arXiv · 天体物理 · 弱引力透镜 · 宇宙学 · ApJ · MNRAS · PRD · JCAP ·
NSF 申请书 · NIH Specific Aims · 科研写作助手 · 语料驱动风格 · 可复现性 ·
科学诚信 · LLM 工具链。</sub>
