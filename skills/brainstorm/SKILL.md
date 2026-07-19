---
name: brainstorm
description: 全自动辐射状探索器。可用于发散式寻找研究 ideas，也可用于穷尽地寻找解决某个切实难题的途径。以"系统发生树（phylogenetic tree）"为数据模型：root = 起点（topic / 问题 / 当前研究状态）；node = 一个想法；depth = 发散层数；width = 最终结果数。每一节点用多种视角（first-principles / 反演 / 跨学科迁移 / 对抗 / 约束变换 / 尺度外推 / office-hours / contrarian / 失效驱动 / high-risk / 元层 等）穷尽 brainstorm，每个分支完整严谨推导（数学/物理/逻辑/文献核对/可行性/可证伪性），递归发散直至每一最深叶节点完整推进。启动时强制 §2.0 glossary grill 预热（与 mattpocock-skills:grill-with-docs 同源），把 root 节点术语锁到项目 FACTS.md。默认 width / depth / rounds **全部不限**，由收敛判据终止。**严禁** "defer / 因成本限制 / future work / TODO" 等推脱式不完整结果。强制 cc-enslaver 七规则全程证据可追溯。Use when 用户说 "brainstorm" / "发散思考" / "找研究方向" / "怎么解决这个难题" / "explore options" / 想穷尽某个研究问题的解法 / 论文 motivation 阶段需要 radial 探索。
disable-model-invocation: false
argument-hint: "[topic] [--width N|∞] [--depth N|∞] [--rounds N|conv] [--max-branches N|∞] [--field <name>] [--out <dir>] [--seed <text>] [--no-online] — 不传 topic 则自动从当前项目状态推断"
---

# brainstorm — 辐射状发散探索（全自动 / 完整推进 / 收敛终止）

> **本 skill 不是头脑风暴清单。** 它是一台递归式的**想法生成—推导—评估—剪枝—再发散**机器，等价于一棵向外扩张的"系统发生树（phylogenetic tree）"。
> 每个想法必须经过完整推导才有资格存活；每个存活节点必须重新做一次发散直到无新颖性增益；
> **每一个最深叶节点都必须完整推进到底——禁止 defer / 因成本 / 因时间 / future-work 等不完整结果。**

---

## 0. 数据模型（visual metaphor — width × depth × node）

把整棵探索想象成下面这张径向树（参考用户示例图）：

- **root（圆心）** = 你给定的 topic，或在不显式给定 topic 时由§2 从当前项目状态推断出的起点。
- **depth（同心环 / "深度"）** = 想法/方向的发散层数。第 1 层（红环）= 从 root 直接产生的 framing 分支；第 2 层（绿环）= 对每个第 1 层节点再各跑一遍 framing 后产生的子分支；以此类推无穷叠。**深度无上限**（除非用户用 `--depth N` 显式封顶）。
- **node（节点）** = 每一个想法本身。无论位于哪一层、哪一支，**任何一个发散/推导/结果点都是 node**。
- **width（最外弧 / "宽度"）** = 最终交付的结果数，即树达到收敛/终止时**叶节点（不再扩展的终态节点）**的总数。**宽度无上限**（除非用户用 `--width N` 显式封顶）。
- **生长准则**：一个 node 若能再开出"不同尝试 / 不同方向"，则**必须**伸出新子节点继续向外（depth + 1）；只有当一个 node 已经被 §4 的 12 字段全部填满、§5 评分定论、且§3 的 12 个 framing pass 在该节点上跑过仍**无新颖增益**时，它才允许作为最终叶（计入 width）。
- **完整推进准则（硬性，§0.8 强制）**：进入 width 计数的每一片最终叶节点都**必须完整推进**——derivation 走通、predictions 给数、falsifiability 给判据、novelty_vs_literature 给真实文献对比。任何含 "defer / 时间不够 / 算力不够 / future work / 留作 TODO" 字样的节点**不算最终叶**，必须继续推进或被显式标记为 `INCOMPLETE_FORBIDDEN` 并触发再循环。

---

## 0. 顶层禁令（违反即整轮无效）

1. **禁止凭记忆/印象引用文献、定理、数值、API、库特性。**
   每条外部断言必须当轮 WebFetch / Read / Grep 验证；无法验证 → 标 `[NEEDS VERIFICATION]` 并降级该分支评分，**不得**作为推导前提。

2. **禁止"伪发散"**——同一个想法换几个词重写、不同 framing 包装但内核相同。
   每个新分支必须能给出**至少一个**与父节点和兄弟节点都不同的可证伪预测、可观测量、或可分离的实验设计；否则合并到最相近的兄弟节点并标 `MERGED_INTO`。

3. **禁止跳过推导**——任何节点的"看起来有意思"都不算 PROMISING。
   **PROMISING 必要条件**：(a) 有完整数学/物理推导链或可行性论证，(b) 有至少一处可与现有文献区分的新颖性声明（带具体引用），(c) 有可证伪/可观测的判据。三条缺一即 → MARGINAL 或 NEEDS-MORE-INFO。

4. **禁止避险**——不允许只生成"安全、保守、增量"分支。
   每个 framing pass 必须至少产出 **1 个 high-risk-high-reward** 分支并完整探索；否则该 pass 无效。

5. **禁止伪收敛**——"没什么新想法了"不是收敛证据。
   收敛必须满足§6 的全部硬判据，**且**最近 2 轮分支生成中"新颖分支 / 总分支"比 < 0.15，**且**至少触发过§3 全部 framing pass 各 1 次。

6. **禁止用户中断决策**——本 skill 是全自动的。
   遇到歧义优先选**信息量最大**的分支继续；只有当 (a) 触及不可逆操作、(b) 触及 §0.7 资源安全阀、(c) 用户原始 topic 完全无法解析时才停下。

7. **资源参数（默认全部不限；caps 仅在用户显式提供数值时生效）**：
   - `--width N` 默认 ∞ — 最终叶节点总数上限
   - `--depth N` 默认 ∞ — 树深度上限
   - `--rounds N|conv` 默认 `conv` — 发散轮次，由§6 收敛判据终止
   - `--max-branches N` 默认 ∞ — 每节点单轮新增分支上限（注意：§3 强制 12 条 framing pass 各产 ≥1 分支，所以下限实际是 12；该 flag 仅可放大）
   - **caps 触顶的语义**：当用户**显式**设置了 `--width N` / `--depth N` / `--rounds N` 并触顶时，**已展开的节点必须先全部完整推进到§4 12 字段填满、§5 verdict 定论之后**才允许停止；不允许"刚到上限立即停留下半成品"。报告以 `WIDTH_CAP_REACHED` / `DEPTH_CAP_REACHED` / `ROUNDS_EXHAUSTED` 标记，**但所有可见叶节点必须完整**。
   - **不允许 skill 内部自行扩大 cap**；也不允许内部自行缩小默认 ∞ 为某个有限值。
   - 旧版的 `--max-nodes 200` / `--max-time-min 60` 已**移除**。"探索成本太大"不构成停止理由；这是本 skill 与普通 brainstorm 工具的关键区别。

8. **完整推进禁令（hard ban on deferred / incomplete leaves）** —— 见§0 数据模型最后一条：
   - 任何叶节点的任何字段中含以下字样均视为**违规半成品**，节点状态强制改为 `INCOMPLETE_FORBIDDEN`，必须继续推进至完整：
     - "defer" / "deferred" / "待定" / "留后"
     - "因成本限制" / "因算力限制" / "因时间限制" / "时间不够" / "算力不够"
     - "future work" / "留作 future work" / "TODO" / "FIXME"
     - "暂不展开" / "略" / "details omitted" / "省略" / "暂略"
     - "应该" / "大概" / "我相信" / "通常" / "可能"（→ 触发 cc-enslaver rule 01）
   - 若推导**真的**需要外部资源（特定数据集、特定计算、特定文献全文），必须当轮通过 WebFetch / WebSearch / Bash / Read 获取；获取失败 → 改用§3.X / §3.E（约束变换）派生**替代方案分支**并完整推导。**禁止**留半成品节点声称"算最终叶"。
   - 这条禁令在**每一个节点**处都强制执行，不分主分支次分支、不分高分低分。

---

## 1. 调用语义与 flag

```
/sci-paper:brainstorm [topic] [flags]
```

**topic 解析**：
- 显式传入 → 直接采用（原文进 `tree.md` 的 root 节点）
- 显式传入但形式为"如何解决 X / 怎样实现 Y / 我想 ..."（问题解决型）→ 同样直接采用，§2 baseline 切换到"problem-solving mode"（详§2）
- 缺省 → 按§2 自动从当前项目状态推断；推断失败 → 报错退出（不允许猜测）

**flags**（全部可选）：
| flag | 默认 | 含义 |
|---|---|---|
| `--width N` | **∞** | 最终叶节点总数上限（最外弧的结果数）；ASCII "inf"、字面 ∞ 与不传均视为不限 |
| `--depth N` | **∞** | 树深度上限（从 root 起的最大层数）；不传 = 不限 |
| `--rounds N` | `conv` | 发散轮次上限；`conv` = 不限轮次，由§6 收敛判据终止 |
| `--max-branches N` | **∞** | 每节点单轮新增分支上限。注意：§3 强制 12 条 framing pass 各产 ≥1 分支，下限实际为 12；该 flag 仅用于放大（极少需要） |
| `--field <name>` | 见§1.1 | 与 `style-profile/` 共享的 field 约定（同 `/sci-paper:de-ai`），用于文献先验加权 |
| `--out <dir>` | `brainstorm-out/<UTCdate>__<topic-slug>/` | 树输出目录 |
| `--seed <text>` | 无 | 额外种子提示，作为 root 节点的 hint |
| `--no-online` | 关 | 关闭 WebSearch / WebFetch；只用本地 + 已读引用 |
| `--min-frameworks N` | 12 | 每节点至少跑过的 framing pass 数（§3）；下限即 §3.A–§3.L 全 12 条 |
| `--min-novelty-ratio R` | 0.15 | 收敛要求的"近 2 轮新颖比"下限（详§6） |
| `--no-grill` | 关 | 跳过 §2.0 glossary grill 预热（弱收敛模式；root 节点术语标 `unverified`） |

> **关于"无上限"**：本 skill 的设计哲学是用§6 收敛判据（substantive convergence）而不是用资源 cap（resource exhaustion）来终止。当用户既不传 `--width / --depth / --rounds` 也不触§6 收敛 → 它会一直跑直到收敛，这是预期行为而非 bug。

**§1.1 field 选择**：与 `/sci-paper:de-ai` 的 field 解析一致 —
解析 `style-profile/` 下子目录：1 个 → 自动选；多个 → 要求 `--field`；0 个 → 跳过文献先验加权（不阻塞，仅警告）。

---

## 2. 第一阶段：基线建立（必做）

**目的**：让 root 节点不是空中楼阁，而是与"当前真实状态"或"用户给定问题的真实约束"对齐。

### §2.0 — Glossary grill prelude（**强制；除非传 `--no-grill`**）

> 借鉴 `mattpocock-skills:grill-with-docs` 的"挑战术语 + 锐化模糊语言"模式。
> brainstorm 的 root 节点用错术语 → 整棵树发散偏方向 → 一千个子节点解决一个不存在的问题。
> 这一步**先**于 §2.A / §2.B mode 判别——因为术语错了再判 mode 也没用。

**操作**（一次一问、每问给推荐答；用户传 `--no-grill` 才跳过）：

1. **定位 glossary 来源**（按优先级 Read 第一个存在的）：
   - `wgl-suite/FACTS.md` + `wgl-suite/KEY_NUMBERS.md`（WGL 项目 single source of truth）
   - 项目根的 `CLAUDE.md`
   - `style-profile/<field>/style_dossier.md` 中含 glossary 表的段落
   - 兜底：从最近 git log + .tex / .md draft 抽常见 noun-phrase 自建临时 glossary
   - 全部找不到 → 标 `[NEEDS_GLOSSARY]`，可继续但 §6 收敛判据加一条警告"未做 glossary grill"

2. **拆解 topic 中的关键 noun**：
   - 若 topic 是单一抽象词（"WGL 中可探索的新方向"）→ 跳本步直接进 §2.A
   - 若 topic ≥1 个具体术语（"如何提升 secondary peak detection 的 SNR_resolved"）→ 对每个具体术语做下面 step 3-4

3. **逐 term 对照 glossary**：
   - **EXACT MATCH** → 默认用 glossary 定义，无须打扰用户，记入 `<out>/glossary-anchors.md`
   - **ALIAS** → 直接用 canonical 名替换，在 `glossary-anchors.md` 注 `aka: "<别名>"`，无须打扰用户
   - **MISSING**（glossary 没收）→ 一次性问用户："你说的 X 是不是指 glossary 里的 Y？还是 Z？还是一个 glossary 没收的新概念？" → 给 ≤3 个选项 + 推荐答（按 grill-me 的"一次一问"惯例）
   - **AMBIGUOUS**（glossary 有 ≥2 条相似条目 A vs B）→ 一次性问 "X 是 A（FACTS.md §3.A）还是 B（FACTS.md §3.B）？" + 推荐答
   - **CONFLICT**（用户 topic 的用法跟 glossary 已收定义矛盾）→ **立刻停 brainstorm**，等用户裁决：改 brainstorm 用法 vs 改 glossary 收新定义。**不允许**绕过冲突静默继续。

4. **产物**：写 `<out>/glossary-anchors.md`：root 节点用的术语 + 对应 glossary 定义 + file:line 引用。后续每个 framing pass / 每个分支生成时用本文件做术语锁——若新分支引入新 noun，要追加到本文件并 grill 一次。

**跳过 grill 的弱后果**：传 `--no-grill` → root 节点术语状态全标 `unverified` → §6 收敛判据加警告 "未做 glossary grill；不允许声称强收敛"。

**模式判别**（必做，作为§2 的第 0.5 步）：
- **Mode A — 研究探索（research mode）**：topic 缺省，或显式 topic 是开放式研究方向（如"weak lensing 中可探索的新方向"）。基线 = 当前项目研究状态。走§2.A 流程。
- **Mode B — 问题解决（problem-solving mode）**：显式 topic 包含具体待解决问题（如"如何解决 X 的 Y 性能瓶颈"、"怎么实现满足约束 C 的 Z"）。基线 = 问题陈述 + 约束 + 已尝试方案 + 已知失败模式。走§2.B 流程。
- 两模式不互斥：若 topic 同时是研究方向**且**带具体卡点，**两份基线都做**，root 节点写入合成版。

### §2.A — Research mode 基线步骤（顺序、每步必做）

1. **Read 当前项目根目录的 `CLAUDE.md`、`README.md`** —— 拿到项目自我描述。
2. **Glob + Read 项目里的 `*.tex` / `*.md` 草稿** —— 识别"目前在写什么、写到哪一步"。如果存在多文件，取最新修改的 3 篇全文 Read；其余 metadata only。
3. **Read `style-profile/<field>/style_dossier.md`（若存在）** —— 拿到 field 知识基线。
4. **Read 项目 `references.bib` / `*.bib`（若存在）** —— 拿到当前文献网络的"已知集"。
5. **Read 最近 N=20 条 git log（`git log --oneline -20`）** —— 拿到最近工作焦点。
6. **从 1-5 中合成 root 节点描述**：
   - **当前研究主题**（一句话，带 file:line 证据）
   - **已完成 / 已稳定的部分**（列表，带证据）
   - **未解决 / 卡住的部分**（列表，带证据）
   - **隐含假设**（必列，至少 5 条；用§3.A first-principles framing 强制提取）

### §2.B — Problem-solving mode 基线步骤（顺序、每步必做）

1. **解析 topic 中的"想要 / 必须 / 不能 / 限制于"等程度词**，提取硬约束 / 软偏好 / 成功判据。
2. **Read / Grep 项目中与该问题最相关的文件**（用 topic 关键词 Grep；若 ≥ 1 hit → 全文 Read 命中文件）。
3. **WebSearch（除非 `--no-online`）** topic 关键词 + `solution` / `benchmark` / `prior art`，找已知方案与已知失败模式；WebFetch 至少 3 篇关键命中。
4. **从 1-3 中合成 root 节点描述**：
   - **问题陈述**（一句话，带 file:line / URL 证据）
   - **硬约束**（列出，每条带来源）
   - **软偏好 / 优化目标**（列出）
   - **已尝试方案**（含本项目内、外部 prior art；带证据）
   - **已知失败模式**（为什么之前的尝试不行；带证据；缺则标 `[NEEDS VERIFICATION]`）
   - **成功判据**（具体、可验证；不允许写"work better"这种模糊判据）

### §2 收尾

7. **保存 root 节点到** `<out>/tree.md` 与 `<out>/tree.json`。

如果 Mode A 第 6 步或 Mode B 第 4 步任一项空白：**停止**，向用户报"无法从当前状态推断 root；请显式传 topic 或补足问题陈述"，不进入§3。

---

## 3. 第二阶段：多视角发散（每节点必跑全部 framing pass）

> **核心创新点**：每个节点走完 §3.A–§3.L 全部 12 条 framing pass，每条至少产出 1 个分支；
> 之后由§4 完整推导每个分支，§5 评估并决定是否进一步展开。
> "全部"是硬性要求 —— `--min-frameworks` 仅控制下限可放宽至 5（紧急快速场景），不允许低于 5。

### §3.A — First-principles / Constructor-theoretic
- 把当前节点的所有"约定俗成"假设列出来；逐条问"如果这条不成立呢？"
- 输出至少 1 个分支：**剥离该假设后还成立的最小定理或最小目标**

### §3.B — 反演（Inversion）
- 当前目标是 X → 探索 "¬X" 或 "X 的对偶/补集" 作为目标
- 当前用方法 M 解 P → 探索 "用 P 反推 M 的失效边界"
- 输出至少 1 个分支：把当前问题倒过来问

### §3.C — 跨学科迁移（Cross-disciplinary transport）
- 当前是物理/天文 → 列出至少 3 个外部学科（生物/经济/CS/数学/化学/语言学/...）里**形式同构**的问题
- 输出至少 1 个分支：把外部学科的成熟工具迁移过来；列出迁移代价与可能 break 的不变量

### §3.D — 对抗（Adversarial / Red team）
- 假设你是一个想发文反驳当前研究的 reviewer：列出**最致命的 3 条反驳**
- 输出至少 1 个分支：将这些反驳变成可证伪实验作为新研究方向

### §3.E — 约束变换（Constraint relaxation/tightening）
- 列出当前研究中**所有显式与隐式约束**（数据可得性、计算复杂度、对称性假设、噪声模型、...）
- 输出至少 2 个分支：(1) 放宽某个约束打开新空间；(2) 加紧某个约束逼出新结构

### §3.F — 尺度外推（Scale extrapolation）
- 当前问题在尺度 S → 探索 1000× S, 0.001× S, 边界尺度（普朗克/宇宙学/单粒子）
- 输出至少 1 个分支：找出在极端尺度下涌现的新物理或新观测窗口

### §3.G — 替换（Substitution）
- 把当前研究的关键组件（数据集 / 观测量 / 算法 / 理论模型 / 目标函数）逐一替换
- 输出至少 1 个分支：每替换一个组件，提出一个非平凡的等价问题

### §3.H — Office-hours 强迫问题（embed YC office-hours framing）
- **需求现实性**：现在世界上有几个人/机构会真的为这个方向的进展付出时间？
- **现状分析**：他们当前是怎么应付这个问题的？
- **极致具体化**：能不能把方向收窄到一个"必须、立刻、为这个"的最小切片？
- **最窄楔子**：什么是最小的能验证整个想法的实验？
- **直接观察**：有没有人已经在做？做到哪？
- **未来契合度**：5 年后这个方向还重要吗？为什么？
- 输出至少 1 个分支：用上面 6 问筛掉"看起来重要、其实没需求"的伪方向

### §3.I — Contrarian（共识可错）
- 列出当前 field 的 3 条主流共识
- 对每条问"如果这条主流共识在某个 regime 下是错的，会是哪个 regime？"
- 输出至少 1 个分支：选一条最有可能在某 regime 错的共识作为靶子

### §3.J — 失效驱动（Failure-driven）
- 列出当前研究失败/不完美的 3 个具体表现（不是泛泛"还能更好"）
- 对每个失效问"这个失效本身能不能成为新研究问题？"
- 输出至少 1 个分支：把"我们做不到 X"变成"为什么做不到 X 是科学问题"

### §3.K — 高风险高回报（Asymmetric payoffs）
- 强制：列出至少 3 个"明知大概率失败但成功就是范式转变"的方向
- 输出至少 1 个分支（不允许 skip，参见§0.4）

### §3.L — 元层（Meta / 跳出 AI 思维定势）
- 自问 7 问（必须当成自我审讯，不能走过场）：
  1. 我的所有分支是不是都来自训练分布里高频的 framing？哪些 framing 是这个 field 不常见的？
  2. 我有没有把"我能写出来的"误当成"科学上重要的"？
  3. 有哪些方向**人类专家会觉得显然重要但 LLM 训练数据稀疏**所以我容易跳过？
  4. 我目前每个分支的"叙事光滑度"是不是太高？真实研究方向通常粗糙、有矛盾。
  5. 我有没有避开数学要求高、需要长推导的分支？把它们补上。
  6. 我有没有避开需要大量实验工作的分支？把它们补上。
  7. 现在树里的"最 weird" 分支真的足够 weird 吗？如果不够，强制再生成一个。
- 输出至少 1 个分支，必须是元层自审中暴露出的盲区

> **§3 完成判据**：上述 12 条全部跑完 + `--min-frameworks` 下限满足 + 每条至少有 1 条分支带完整推导。

### §3.X — 在线工具/插件检索（每节点至少 1 次，除非 `--no-online`）

为当前节点的研究方向，按以下顺序搜索：
1. **WebSearch**：方向关键词 + `arxiv` / `github` / `dataset` / `benchmark`
2. **WebSearch**：方向关键词 + `claude code plugin` / `mcp server` / `langchain tool`（找现成可调用的工具）
3. 对找到的 GitHub repo 或 plugin：WebFetch 其 README，判断是否能直接复用
4. 把结果记入节点的 `external_resources` 字段

`--no-online` 时跳过§3.X，标记节点 `external_resources_unchecked=true`。

---

## 4. 第三阶段：每分支完整探索（硬性深度要求）

每个 §3 产出的分支节点必须填充以下 12 个字段后才能进入§5 评估：

| 字段 | 要求 | 容错 |
|---|---|---|
| `idea_statement` | ≤ 3 句，单一明确假设 | 必填 |
| `parent_framing` | 来自§3.A–§3.L 的哪一节 | 必填 |
| `derivation` | **完整数学/物理推导链**或可行性论证；不接受 "details omitted"；公式必须可被独立第三方走通 | 必填 |
| `assumptions` | 显式列出推导依赖的全部假设（≥ 3 条） | 必填 |
| `predictions` | 至少 1 条**定量、可证伪**的预测；带量级 + 误差 | 必填 |
| `falsifiability` | 何种观测/计算结果会**否定**此分支？ | 必填 |
| `novelty_vs_literature` | 与至少 3 篇真实文献逐条对比；每条带 DOI/arXiv ID + 一句话差异声明 | 必填；无可比时必须 WebSearch 至少 1 轮再下结论 |
| `feasibility` | 数据/算力/时间/技能 4 项各 1 行 | 必填 |
| `risks` | 至少 3 条；每条标注是技术风险/科学风险/资源风险 | 必填 |
| `branch_potential` | 这个分支若成功，能再发散出哪些子问题？给 ≥ 2 条 hint | 必填（用于决定是否进一步递归） |
| `external_resources` | §3.X 找到的 repo/plugin/dataset；带 URL；标注是否实际可用 | `--no-online` 时可空 |
| `verdict_provisional` | `PROMISING` / `MARGINAL` / `DEAD-END` / `NEEDS-MORE-INFO` | 必填，由§5 决定是否升级为 final |

**深度执行约束**：
- `derivation` 中含数值时**当轮**用 Bash + python（sympy / numpy）跑一次自检脚本；输出贴入字段；无法跑则在字段最后写 `[unverified — needs symbolic check]`
- `novelty_vs_literature` 中每篇引用必须 WebFetch arXiv abs / DOI 页确认作者+年份+标题至少匹配；不可仅凭 WebSearch 摘要下结论
- 任何字段写出 "应该 / 大概 / 我相信 / 通常 / 应当" → 该字段无效，必须重写
- **§0.8 完整推进禁令在此强制生效**：任何字段含 "defer / 留后 / 待定 / 因成本限制 / 因时间限制 / 因算力限制 / future work / TODO / FIXME / 略 / details omitted / 暂略 / 暂不展开" 之一 → 该字段无效，节点状态强制改为 `INCOMPLETE_FORBIDDEN`，必须继续推进至该字段完整。**不允许把半成品节点提交进 verdict**。

---

## 5. 第四阶段：评估、剪枝、决定是否继续递归

每完成一节点的§4，进入评估：

### 5.1 评分（每项 0–3，整数）
- **科学价值** S：成功后对 field 的贡献量级（0=无；3=范式级）
- **新颖性** N：与现有文献的差异程度（0=完全重复；3=未见）
- **可行性** F：在当前用户资源下走通的概率（0=不可行；3=已经几乎备齐）
- **可证伪性** K：实验/计算判据是否清晰（0=纯哲学；3=有明确硬判据）
- **分支潜力** B：成功后能再开多少子方向（0=死胡同；3=树状爆炸）

`score = S + N + F + K + B`（满分 15）

### 5.2 verdict 转最终
- `score ≥ 11` → **PROMISING**
- `8 ≤ score ≤ 10` → **MARGINAL**（保留但不再深 expand）
- `score ≤ 7` → **DEAD-END**（标灰，停止 expand）
- 任一字段为 `[NEEDS VERIFICATION]` 或 `unverified` 占主导 → **NEEDS-MORE-INFO**（不下 verdict，挂"待补充"）

### 5.3 是否进入下一轮发散
- 仅 `PROMISING` 节点进入下一轮（即在该节点上重新跑§3 全部 framing pass）
- `MARGINAL` 保留在树上但不再 expand
- `DEAD-END` 标灰；其推导仍保留供后续参考
- `NEEDS-MORE-INFO` 列入"待补充清单"；下一轮起始时优先 WebFetch 补充，再决定 verdict

### 5.4 兄弟节点合并
- 同父节点下任意两兄弟若 `idea_statement` 余弦语义相似 ≥ 0.85（人工判断也可），合并为单节点，保留得分高的一方，另一方记 `MERGED_INTO=<id>`

---

## 6. 收敛判据（终止条件 — 必须**全部**满足）

> "看起来差不多了"不是收敛证据。下面 6 条同时为真才允许声明 CONVERGED。

1. **所有节点完整**：树里**没有任何**节点处于 `verdict_provisional=NEEDS-MORE-INFO` 或 `INCOMPLETE_FORBIDDEN`。§0.8 完整推进禁令在此强制生效。
2. **新颖性比例下降**：最近 2 轮 expand 中，新增节点里 `verdict=PROMISING` 的占比 < `--min-novelty-ratio`（默认 0.15）。
3. **每条 framing pass 都被触发过 ≥ 1 次**（§3.A–§3.L 全部）。
4. **所有 PROMISING 叶子至少经过一次再发散尝试**（即每个 PROMISING 都被当作过 root 跑过§3 全 pass，得到的子代或为合并、或为 DEAD-END、或为 MARGINAL；不再产生新的 PROMISING）。
5. **§3.K 至少产生过 1 个完整探索过的 high-risk 分支**（即使最终 DEAD-END），且不是被 §0.4 强制塞进来后立即剪枝的占位。
6. **用户显式 cap 未触顶**：若用户显式设置了 `--width N` / `--depth N` / `--rounds N` 并触顶 → 不算 CONVERGED，按下表报状态；但**所有已展开节点必须完整**（§0.7 后半段 + §0.8）。

**终止状态决策表**（执行优先级从上到下）：

| 触发条件 | 报告状态 | 必要前置 |
|---|---|---|
| §6 六条全过 | `CONVERGED` | — |
| `--width N` 触顶且全部叶完整 | `WIDTH_CAP_REACHED` | 所有叶 §4 12 字段填满 + §5 verdict 定论 |
| `--depth N` 触顶且全部叶完整 | `DEPTH_CAP_REACHED` | 同上 |
| `--rounds N` 用完且全部叶完整 | `ROUNDS_EXHAUSTED` | 同上 |
| 任一 cap 触顶但**仍有半成品节点** | **不允许停止** | 必须先把所有 `INCOMPLETE_FORBIDDEN` 推进到完整，再报上面任一 cap 状态 |
| Topic 完全无法解析 | `EARLY_STOP=topic_unparseable` | 必须在§2 baseline 阶段；进入§3 之后此项不再适用 |

CONVERGED / WIDTH_CAP_REACHED / DEPTH_CAP_REACHED / ROUNDS_EXHAUSTED 时输出**最终报告**（§7）。
**"资源不够"不构成停止理由**——本 skill 不接受 "exploration cost too high" 之类的隐含 early-stop（与 §0.7 / §0.8 一致）。

---

## 7. 第五阶段：输出格式

### 7.1 实时增量写入

每完成一个节点的§4 都立即追加进 `<out>/tree.md` 与 `<out>/tree.json`。
不允许"探索完再统一写"——**断电恢复**要求树状态随时可读。

### 7.2 树文件结构

```
<out>/
├── tree.md           # 人类可读，markdown 大纲格式
├── tree.json         # 机器可读，含完整字段
├── shortlist.md      # 终态；按 score 排序的 PROMISING 列表
├── pending.md        # NEEDS-MORE-INFO 待补充清单
└── nodes/
    └── <id>.md       # 字段过长的节点单独成文件（derivation > 100 行时强制）
```

### 7.3 tree.md 节点格式

```markdown
### <id>  <idea_statement[:80]>
- **parent**: <parent_id> | **framing**: §3.X | **score**: S=_ N=_ F=_ K=_ B=_ → total=_
- **verdict**: PROMISING / MARGINAL / DEAD-END / NEEDS-MORE-INFO
- **derivation**: …（或 `→ nodes/<id>.md`）
- **assumptions**: …
- **predictions**: …
- **falsifiability**: …
- **novelty_vs_literature**:
  - [arXiv:xxxx.xxxxx] <一句话差异>
  - [DOI:10.xxx/...] <一句话差异>
- **feasibility / risks / branch_potential / external_resources**: …
- **children**: [id1, id2, ...]
```

### 7.4 终态报告（CONVERGED / WIDTH_CAP_REACHED / DEPTH_CAP_REACHED / ROUNDS_EXHAUSTED）

```
## brainstorm 终态报告 — <topic>

### 状态
- 状态：CONVERGED / WIDTH_CAP_REACHED / DEPTH_CAP_REACHED / ROUNDS_EXHAUSTED / EARLY_STOP=<reason>
- 模式：research / problem-solving / hybrid
- 树形：max_depth_reached=D, leaf_count=W (= 最终 width), 总节点数=N
- 节点分布：PROMISING=p, MARGINAL=m, DEAD-END=d, NEEDS-MORE-INFO=0, INCOMPLETE_FORBIDDEN=0
  （若上面后两项不为 0 → 报告非法，必须回到§4 把它们推进到完整再发本节）
- 总轮次：R
- 触发收敛/停止的判据：…
- 用户 cap：width=<N|∞>, depth=<N|∞>, rounds=<N|conv>；触顶情况：…

### 最终 width — 所有完整推进的叶节点（按 score 降序）
（即最外弧上每一片"完整推进到底"的叶；含 PROMISING + MARGINAL + DEAD-END 的终态叶）
1. [id] <idea_statement> — verdict=…, score=…; 关键判据=…; 第一个实验=…
2. ...

### Top-K 推荐方向（按 score 降序，仅 PROMISING）
1. [id] <idea_statement> — score=14; 关键判据=…; 第一个实验=…
2. ...

### 元层自检结果（§3.L 第 7 题汇总）
- 最 weird 分支：…
- 高风险分支收成：…
- 元层未能跳出的盲区（坦诚承认）：…

### 完整推进自审（§0.8）
- 本次报告中所有叶节点已 100% 完整推进，无任何 defer / future-work / TODO 字样：是 / 否
- 若"否" → 报告非法，必须回到§4 / §5 修复

### 推荐下一步
（仅给 1–3 条具体行动，每条带 file:line 或 URL 证据）
```

---

## 8. 工具使用规范（cc-enslaver 投影）

| 任务 | 必用工具 | 禁止 |
|---|---|---|
| 项目当前状态推断 | Read / Glob / Grep / Bash(git log) | 凭印象 |
| 文献核对 | WebFetch arXiv abs / DOI 页 | WebSearch 摘要做结论 |
| 数学推导自检 | Bash + python(sympy/numpy) | "易证 / 显然" |
| 平行分支探索 | Agent(Explore) 子代理；多分支可并行 | 串行偷懒 |
| 寻找现成插件/repo | WebSearch + WebFetch README | 凭"我记得有个工具叫 X" |
| 代码搜索 | Grep / Glob | 关键词推测路径 |

**子代理使用建议**：
- 当树宽度 ≥ 5 时，把每个 framing pass 派给一个 Explore subagent 并行；汇总后由主 agent 做§5 评估
- 子代理 prompt 必须自包含（背景 + 当前节点 + 该 pass 的硬要求）
- 子代理返回的引用主 agent 必须再 verify（cc-enslaver rule 04）

---

## 9. 反模式（绝对避免）

- ❌ "我列了 10 个方向，每个一句话" — §4 的 12 字段没填即无效。
- ❌ "我相信这个方向有人做过 / 没人做过" — 必须 WebFetch 实证。
- ❌ "数学推导太长省略" — 整段 dump 进 `nodes/<id>.md`。
- ❌ "差不多了，应该收敛了" — §6 的 6 条不全过即未收敛。
- ❌ "high-risk 分支太天马行空，跳过" — 违反§0.4 与§3.K，整轮 framing pass 无效。
- ❌ "为了节省 context，只展开高分分支" — 树是增量写盘的，不占 context。
- ❌ "WebSearch 找了，没找到，就是新的" — 至少要换 3 种关键词组合 + 检查相邻 field。
- ❌ "用户没说要并行，我就串行做" — `--rounds conv` 模式下并行是性能必需。
- ❌ "树太大用户看不动，我手动剪一下" — 用户要的是穷尽，不是好看。
- ❌ "我跑完了 framing A 到 D 觉得够了" — §3.A–§3.L 全部必跑（`--min-frameworks` 下限即 12）。
- ❌ **"这条分支留作 future work"** / **"因时间限制暂不展开"** / **"因算力限制 defer 到将来"** / **"细节暂略"** / **"TODO: 进一步推导"** — 全部违反§0.8 完整推进禁令。节点必须完整推进或显式标 `INCOMPLETE_FORBIDDEN` 触发再循环。
- ❌ "探索成本太高，提前停止" — §0.7 已移除时间 / 节点数硬 cap；只有§6 收敛或用户**显式** width/depth/rounds cap 触顶才能停，且停时所有叶必须完整。
- ❌ "用户说 problem-solving，我就跳过§3 的某些 framing" — 不允许。研究 mode 与问题求解 mode 都跑全部 12 条 framing；问题求解 mode 只是 baseline 不同。

---

## 10. 与其他 sci-paper skill 的接口

- 用 `/sci-paper:brainstorm` 找出 PROMISING 方向 → 用 `/sci-paper:paper` 加载写作标准 → 起草新论文
- 起草时若已有 `style-profile/<field>/`：自动叠加其 dossier 作为风格基线（`/sci-paper:de-ai` §1 的校准资产）
- brainstorm 自身**不写论文正文**；它只产出方向 + 推导骨架，不替用户决定写哪篇
- brainstorm 输出的 `shortlist.md` 是 `/paper` skill 的合法输入（用户挑一条交给 paper）
