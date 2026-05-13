---
name: paper-attack-tree
description: 用 brainstorm 的辐射状探索方法对论文做 critique tree 审查。每个 node = 一个 critique；用 12 条 framing pass（first-principles / 反演 / 跨学科 reviewer / 对手红队 / 约束变换 / 尺度外推 / 替换 / office-hours / contrarian / 失效驱动 / high-risk 致命攻击 / 元层）从多角度攻击每条 claim；每个 critique 必须完整推进至 CONFIRMED（有 file:line 证据 + 具体修复方案）/ REFUTED（有 file:line 证据证明论文已处理）/ MARGINAL（依赖解读，列入作者判断）。**严禁** "defer / NEEDS-MORE-INFO 滞留 / 因成本 / 因时间 / future work / 可能存在该问题待确认" 等推脱式不完整 verdict；递归发散直至无新颖增益；强制 cc-enslaver 七规则全程证据可追溯。与 paper-review 互补（paper-review 是预设 checklist 静态审查；本 skill 是开放式 adversarial radial 探索）。Use when 用户说 "attack tree" / "adversarial review" / "对抗审查" / "找 reviewer 会挑什么刺" / "audit this claim" / 用 paper-review 跑完仍想 open-ended 攻击关键 claim / rebuttal 准备阶段。
disable-model-invocation: false
argument-hint: "<file_path> [--width N|∞] [--depth N|∞] [--rounds N|conv] [--focus <section|claim|equation>] [--field <name>] [--from-paper-review <report>] [--out <dir>] [--no-online] [--max-branches N|∞] — 指定论文 (.tex/.md)，可选树宽/深度/轮次上限 / 聚焦某节或某 claim / 显式 field / 与已跑过的 paper-review 报告联合 / 输出目录 / 离线模式 / 每节点分支上限"
---

# paper-attack-tree — 辐射状论文 critique 探索（全自动 / 完整推进 / 收敛终止）

> **本 skill 不是 lint，不是 checklist 审查。** 它是一台**递归式的 critique 生成—溯源—验证—剪枝—再发散**机器，等价于一棵从论文向外扩张的"攻击树（attack tree）"。
> 每个 critique 必须经过完整溯源（file:line + 论文实际内容）才有资格存活；
> 每个存活 critique 必须重新做一次发散（用 12 framing pass 攻击该 critique 本身）直到无新颖增益。
> **每一个最深叶 critique 都必须完整裁决到 CONFIRMED / REFUTED / MARGINAL——禁止 NEEDS-MORE-INFO 滞留、禁止 defer、禁止"可能有问题待确认"。**

---

## 0. 数据模型（visual metaphor — width × depth × node，承自 brainstorm）

把整棵审查想象成以论文为圆心向外扩张的径向树（与 brainstorm 同结构）：

- **root（圆心）** = 待审论文整体（或在 `--focus <X>` 时为某一节 / 某一 claim / 某一 equation）。
- **depth（同心环）** = critique 的发散层数。
  - **第 1 层**：对 root 直接使用 12 framing pass 产生的 critique 节点；
  - **第 2 层**：对每个第 1 层 critique 再用 12 framing pass 攻击**该 critique 本身**——这条 critique 是否站得住？是否被论文别处反驳？能否再深一层挖出 sub-critique？
  - **第 k 层**：以此类推无限叠加。**深度无上限**（除非用户用 `--depth N` 显式封顶）。
- **node（节点）** = 每一条具体 critique。任何位置、任何层数的 critique 都是一个 node。
- **width（最外弧）** = 最终交付的 critique 数，即树达到收敛/终止时**叶节点（不再扩展的终态 critique）**的总数。**宽度无上限**（除非用户用 `--width N` 显式封顶）。
- **生长准则**：一个 critique 若能再开出"不同子攻击角度 / 不同 sub-critique"，则**必须**伸出新子节点（depth + 1）；只有当一个 critique 已经被 §4 的 12 字段全部填满、§5 评分定论、且§3 的 12 framing pass 在该节点上跑过仍**无新颖增益**时，它才允许作为最终叶。
- **完整推进准则（硬性，§0.8 强制）**：进入 width 计数的每一片最终叶 critique 都**必须裁决到 CONFIRMED / REFUTED / MARGINAL 之一**——含 file:line 证据、具体修复方案（CONFIRMED）或论文应答位置（REFUTED）。任何含 "defer / 待确认 / 算力限制 / 时间限制 / future work / TODO / 可能存在 / 大概率 / 应该 / NEEDS-MORE-INFO 滞留" 字样的节点**不算最终叶**，必须继续推进或被显式标记为 `INCOMPLETE_FORBIDDEN` 并触发再循环。

---

## 0. 顶层禁令（违反即整轮无效）

1. **禁止凭记忆/印象引用论文内容、文献、定理、数值、API、库特性。**
   每条断言必须当轮 Read 论文 / WebFetch / Grep+Read 上下文验证；无法验证 → 标 `[NEEDS VERIFICATION]` 并降级该 critique 评分；**不得**作为下游 critique 的前提。

2. **禁止"伪 critique"**——同一个攻击角度换几个词重写、不同 framing 包装但内核相同。
   每个新 critique 必须能给出**至少一个**与父 critique 和兄弟 critique 都不同的：(a) 具体被攻击位置（file:line + 引用片段），或 (b) 不同的 falsification 路径，或 (c) 不同的修复方案。否则合并到最相近的兄弟节点并标 `MERGED_INTO`。

3. **禁止跳过溯源**——任何 critique 的"看起来有问题"都不算 CONFIRMED。
   **CONFIRMED 必要条件**：(a) `paper_position` 字段含真实存在的 file:line + Read 验证过的引用片段；(b) `proposed_fix` 给出具体改动建议（不是"重新考虑此处"这种空话）；(c) `severity` ≥ 2（cosmetic 不上 CONFIRMED）。三条缺一即 → MARGINAL 或 REFUTED。

4. **禁止避险**——不允许只生成"安全、保守、显然"的 critique。
   每个 framing pass 必须至少产出 **1 个 high-severity** critique（如"central claim 站不住"、"数据 leakage"、"推导有循环"等致命级）并完整探索；否则该 pass 无效。

5. **禁止伪收敛**——"没什么新 critique 了"不是收敛证据。
   收敛必须满足§6 的全部硬判据，**且**最近 2 轮分支生成中"CONFIRMED 占比 < `--min-confirmed-ratio`（默认 0.15）"，**且**至少触发过§3 全部 framing pass 各 1 次。

6. **禁止用户中断决策**——本 skill 是全自动的。
   遇到歧义优先选**信息量最大**的 critique 继续；只有当 (a) 触及不可逆操作、(b) 触及 §0.7 资源参数显式 cap、(c) 论文文件无法解析时才停下。

7. **资源参数（默认全部不限；caps 仅在用户显式提供数值时生效）**：
   - `--width N` 默认 ∞ — 最终 critique 叶节点总数上限
   - `--depth N` 默认 ∞ — 树深度上限
   - `--rounds N|conv` 默认 `conv` — 发散轮次，由§6 收敛判据终止
   - `--max-branches N` 默认 ∞ — 每节点单轮新增分支上限（§3 强制 12 条 framing pass 各产 ≥1 分支，下限实际为 12）
   - **caps 触顶时**：已展开的 critique 必须先全部完整推进到§4 12 字段填满、§5 verdict 定论后才允许停止；不允许"刚到上限立即停留下半成品"。报告以 `WIDTH_CAP_REACHED` / `DEPTH_CAP_REACHED` / `ROUNDS_EXHAUSTED` 标记，**但所有可见叶节点必须完整**。
   - **不允许 skill 内部自行扩大或缩小默认 ∞**。

8. **完整推进禁令（hard ban on deferred / incomplete critique leaves）** —— 见§0 数据模型最后一条：
   - 任何叶节点的任何字段含以下字样均视为**违规半成品**，节点状态强制改为 `INCOMPLETE_FORBIDDEN`，必须继续推进至完整：
     - "defer" / "deferred" / "待定" / "留后" / "待确认"
     - "因成本限制" / "因算力限制" / "因时间限制" / "时间不够" / "算力不够"
     - "future work" / "留作 future work" / "TODO" / "FIXME"
     - "暂不展开" / "略" / "details omitted" / "省略" / "暂略"
     - "应该 / 大概 / 我相信 / 通常 / 可能 / 也许 / 或许"（触发 cc-enslaver rule 01）
     - "NEEDS-MORE-INFO 永久挂起" / "无法判定" / "看作者意思" / "得问作者"（→ 必须继续溯源 / WebFetch / 跑脚本到能判定为止）
   - 若验证**真的**需要外部资源（运行作者脚本、查 companion paper 全文、查未发表数据），必须当轮通过 Bash / WebFetch / Read 获取；获取失败 → 改用§3.X / §3.E（约束变换）派生**替代验证路径**并完整裁决。**禁止**留半成品节点声称"算最终叶"。
   - 这条禁令在**每一个 critique 节点**处都强制执行。

---

## 1. 调用语义与 flag

```
/sci-paper:paper-attack-tree <file_path> [flags]
```

**file_path 解析**：
- 显式传入的 .tex / .md 文件 → 直接采用，作为 root 节点的源文档
- 若同时传 `--focus <section|claim|equation>`：root 缩窄到该单元（用 grep + Read 定位）
- 缺省 file_path → 报错退出（不允许猜测）

**flags**（全部可选）：

| flag | 默认 | 含义 |
|---|---|---|
| `--width N` | **∞** | 最终 critique 叶节点总数上限 |
| `--depth N` | **∞** | 树深度上限（从 root 起最大层数） |
| `--rounds N` | `conv` | 发散轮次上限；`conv` = 不限，由§6 终止 |
| `--max-branches N` | **∞** | 每节点单轮新增分支上限（下限 = 12 framing） |
| `--focus <id>` | 无 | 把 root 缩窄到某 section / claim / equation；其余视为外部上下文 |
| `--field <name>` | 见§1.1 | 与 paper-style 同名 field，用于文献先验加权 |
| `--from-paper-review <path>` | 无 | 与已跑过的 paper-review 报告联合：已 CONFIRMED 的问题不重复，但每条要作为 critique 树的种子拓展 sub-critique |
| `--out <dir>` | `attack-tree-out/<UTCdate>__<filename-slug>/` | 树输出目录 |
| `--no-online` | 关 | 关闭 WebSearch / WebFetch；只用本地 + 已读引用做文献核对 |
| `--min-frameworks N` | 12 | 每节点至少跑过的 framing pass 数（下限 = §3.A–§3.L 全 12 条） |
| `--min-confirmed-ratio R` | 0.15 | 收敛要求的"近 2 轮 CONFIRMED 占比"下限（详§6） |

**§1.1 field 选择**：与 `paper-style` 行为一致 —
解析 `style-profile/` 下子目录：1 个 → 自动选；多个 → 要求 `--field`；0 个 → 跳过 corpus 加权（不阻塞，仅警告）。

---

## 2. 第一阶段：基线建立（必做）

**目的**：让 root critique 候选不是空中楼阁，而是与论文的真实内容、约束、声明对齐。

执行步骤（顺序、每步必做）：

1. **从头到尾 Read 论文全文**（不抽样、不跳读）。超过 2000 行用 offset/limit 分块读完，**全部读过为止**。critique 是全局结构 + 局部细节的双层属性，跳读必然漏判。
2. **若传 `--focus <id>` → Grep + Read 定位**，把目标缩窄到该 section / claim / equation；同时保留 ±20 行上下文以判定 critique 是否被论文其它位置反驳。
3. **Read 项目根 `CLAUDE.md` / `README.md`**（若存在）—— 拿到论文领域 / project 背景，用于 §3.C 跨学科 + §3.I contrarian 的 field-aware 加权。
4. **Read `style-profile/<field>/style_dossier.md`（若存在）** —— 拿到 field 知识基线 + 该 field 的常见 reviewer 关注点。
5. **Read 论文的 `references.bib`** —— 拿到论文自己引用的文献集，用于 §3.D 检查"引用是否真支持论点"，以及 §3.C 跨学科批判前先确认论文是否已引用相关外部文献。
6. **若传 `--from-paper-review <path>` → Read 该 report**：把其中标记的 🔴/🟡 issue 提取为 root 的"已知 critique"种子集；本 skill 在此基础上**继续发散**而非重审。已知 critique 作为深度 1 的 "已 CONFIRMED" 节点直接入树，并对每条用 12 framing pass 攻击其 sub-critique（深度 2+）。
7. **生成 root 节点描述**（必填，缺项不允许进入§3）：
   - **论文核心 claim**（一句话 + file:line 证据；从 abstract / introduction / conclusion 三处对位提取）
   - **论文方法骨架**（一句话 + file:line 证据；method 节首段或图）
   - **论文关键证据**（核心 figure / table / equation 编号 + file:line）
   - **论文显式假设**（列出 ≥ 3 条，每条带 file:line；用§3.A first-principles framing 强制提取）
   - **论文隐含假设**（必列，至少 5 条；与§3.E 约束变换协同；这些是后续 critique 的最肥沃土壤）
8. **保存 root 节点到** `<out>/tree.md` 与 `<out>/tree.json`。

如果 step 7 任一项空白：**停止**，向用户报"无法从论文推断 root（论文太短 / 格式异常 / claim 不清）"，不进入§3。

---

## 3. 第二阶段：12 framing-pass critique 发散（每节点必跑全部）

> **核心创新点**：每个节点走完 §3.A–§3.L 全部 12 条 framing pass，每条至少产出 1 个 critique 分支；
> 之后由§4 完整溯源每个 critique，§5 评估并决定是否进一步展开。
> "全部"是硬性要求 —— `--min-frameworks` 仅控制下限，下限 = 12，不允许低于。

### §3.A — First-principles（剥离假设攻击）
- 把当前节点（root 或某 critique）依赖的所有"约定俗成"假设列出来；逐条问"如果这条假设不成立，论文结论还能成立吗？"
- 输出至少 1 个 critique：**指向论文中某条具体假设（file:line），论证"剥离后论文剩什么、还成立吗"**

### §3.B — 反演（Inversion / Negation attack）
- 当前论文 claim 是 X → 探索 "¬X" 或 "X 的对偶/补集" 是否更符合数据
- 当前论文用方法 M 解 P → 探索 "P 在 M 下的失效边界"是否被论文回避
- 输出至少 1 个 critique：把论文的结论倒过来问"为什么不是这个？"，给出论文未排除的反例 / 反方向

### §3.C — 跨学科 reviewer（Cross-disciplinary critique）
- 当前论文领域是 X → 列出至少 3 个外部学科（生物/经济/CS/数学/化学/语言学/...）中**形式同构**的问题，那些领域的 reviewer 会怎么读这篇论文？
- 输出至少 1 个 critique：把外部学科的标准（如 ML reviewer 看 leakage / 经济 reviewer 看 endogeneity / 数学 reviewer 看严格性 / 统计 reviewer 看 multiple testing）应用到本论文，找出本领域 reviewer 习惯性忽视的盲点

### §3.D — 对手红队（Adversarial / Red team）
- 假设你是一个**想发文反驳本论文**的 reviewer：列出**最致命的 3 条反驳**
- 反驳必须具体（指向 file:line / equation 编号 / figure 编号 / 假设条款）；不接受"general 怀疑"
- 输出至少 1 个 critique：将每条反驳转为 sub-critique 入树

### §3.E — 约束变换（Constraint relaxation/tightening attack）
- 列出论文中**所有显式与隐式约束**（数据可得性、计算预算、对称性假设、噪声模型、参数范围、...）
- 输出至少 2 个 critique：(1) 放宽某个约束后论文结论是否还成立？(2) 加紧某个约束后论文是否暴露 hidden 失效？

### §3.F — 尺度外推（Scale extrapolation attack）
- 论文实验/数据/参数在尺度 S → 外推到 1000× S, 0.001× S, 边界尺度（普朗克/宇宙学/单粒子）
- 输出至少 1 个 critique：找出在极端尺度下论文方法/结论**会失效**的具体场景，论证论文是否声明了适用范围

### §3.G — 替换（Substitution attack）
- 把论文的关键组件（数据集 / 观测量 / 算法 / 理论模型 / 目标函数 / baseline）逐一替换
- 输出至少 1 个 critique：每替换一个组件，提出"如果换成 X，论文的结论 / 数字 / 效应大小 还成立吗？"——论文是否做了 ablation？做得够吗？

### §3.H — Office-hours 强迫问题（need-question attack）
- 6 问连击（必须当成真实 reviewer 的发难）：
  1. **需求现实性**：世界上有几个人/机构会真的因为本论文的结果而改变行为？
  2. **现状分析**：他们当前是怎么应付这个问题的？本论文真的更好吗？
  3. **极致具体化**：本论文的贡献能不能收窄到一个"必须、立刻、为这个"的最小切片？如果不能 → 贡献被稀释
  4. **最窄楔子**：本论文的 minimum claim 是什么？删掉所有非核心后还剩什么？
  5. **直接观察**：本领域是否已有相同/相似工作（论文有引但隐去对比）？
  6. **未来契合度**：5 年后这个结果还重要吗？还是只对当前 fad 有意义？
- 输出至少 1 个 critique：用以上 6 问找出"看起来重要、其实贡献单薄"或"未与最相近 prior work 正面对比"的伪贡献

### §3.I — Contrarian（共识可错攻击）
- 列出本论文 implicitly 依赖的 3 条 field 主流共识
- 对每条问"如果这条共识在某个 regime 下是错的，论文在那个 regime 还成立吗？"
- 输出至少 1 个 critique：选一条最有可能在某 regime 错的共识，论证"论文有没有验证自己在那个 regime 仍正确"

### §3.J — 失效驱动（Failure-driven attack）
- 列出论文方法/结论**失败或不完美**的 3 个具体表现（不是泛泛"还能更好"；是 file:line 可定位的具体不足，如 "Fig 5 中 SNR < 3 时方法 break" / "Table 2 中 z > 1 时偏差超出 1σ"）
- 对每个失效问"论文是否声明了这是限制？是否解释了原因？是否提出了缓解？"
- 输出至少 1 个 critique：把论文未正面承认 / 未解释的失效转为 critique

### §3.K — 高风险致命攻击（Asymmetric payoffs / Fatal critique）
- 强制：列出至少 3 个"明知可能是 false positive 但若成立就是论文 fatal flaw"的攻击角度（如"central claim 数据 leakage"、"关键推导循环论证"、"主要 figure 数字与生成脚本输出不符"、"引用的 prior work 实际反驳本论文却被作者描述为支持"）
- 每个必须完整溯源（不接受 false-positive 直觉作为唯一证据）
- 输出至少 1 个 critique（不允许 skip；参见§0.4）

### §3.L — 元层（Meta / 跳出 LLM-reviewer 思维定势）
- 自问 7 问（必须当成自我审讯，不能走过场）：
  1. 我的所有 critique 是不是都来自训练分布里高频的 reviewer 套路（如 "n=X is small"、"insufficient comparison"）？哪些 critique 是该 field 不常见的？
  2. 我有没有把"我能写得出的"误当成"科学上严重的"？
  3. 有哪些 critique **人类 senior reviewer 会觉得显然但 LLM 训练数据稀疏**所以我容易跳过？
  4. 我目前的每条 critique 是不是太"温和"？真实 reviewer 的 lethal critique 通常尖锐、具体、定位精确。
  5. 我有没有避开需要长推导 / 真正算数学的 critique？把它们补上。
  6. 我有没有避开需要重跑代码 / 重对位数据的 critique？把它们补上。
  7. 现在树里"最 weird" 的 critique 真的足够 weird 吗？如果不够，强制再生成一个。
- 输出至少 1 个 critique，必须是元层自审中暴露出的盲区

> **§3 完成判据**：上述 12 条全部跑完 + `--min-frameworks` 下限满足 + 每条至少有 1 条 critique 带完整溯源。

### §3.X — 在线/项目内交叉验证（每节点至少 1 次，除非 `--no-online` 或纯文档审查）

为当前节点的 critique，按以下顺序核对：
1. **Grep + Read 项目内代码 / CSV / 脚本**：critique 涉及数字 / 公式实现 / 数据处理时，必须当轮重跑相关脚本并 byte-for-byte 对位（与 paper-review §2.G 等价）
2. **WebFetch 论文引用的 prior work**：critique 涉及"论文与 prior work 关系"时，必须 WebFetch arXiv abs / DOI 页确认作者+年份+标题+实际声明，不可仅凭 WebSearch 摘要
3. **WebSearch 相邻 field 的同类批评**：用 critique 关键词 + `arxiv comment` / `erratum` / `failure mode`，看是否已有 published 批评

`--no-online` 时跳过§3.X 在线部分，仅做项目内代码 + 论文文本核对；标记节点 `external_check_partial=true`。

---

## 4. 第三阶段：每 critique 完整溯源（硬性深度要求）

每个 §3 产出的 critique 节点必须填充以下 12 个字段后才能进入§5 评估：

| 字段 | 要求 | 容错 |
|---|---|---|
| `critique_statement` | ≤ 3 句，单一明确的对论文的攻击声明（如 "Equation (12) 量纲在化简中漏因子 c²"） | 必填 |
| `parent_framing` | 来自§3.A–§3.L 的哪一节 | 必填 |
| `paper_position` | 被攻击位置的 **file:line + Read 出来的引用片段**（不接受仅 file:line 没引用） | 必填 |
| `evidence` | 支持该 critique 的**完整论证链 + 第三方可验证证据**——含 (a) 论文中的具体引用，(b) 必要时项目内代码 / CSV 对位结果，(c) 必要时外部文献 file:line + DOI | 必填 |
| `assumptions` | 显式列出本 critique 依赖的全部前提（如 "我假设论文的 Σ_crit 定义遵循 §2 的 SI 单位制"），≥ 2 条 | 必填 |
| `predictions` | 若 critique 成立，论文应在哪里**自相矛盾 / 复现失败 / 与 prior work 不一致**？给可观察的具体表征 | 必填 |
| `paper_defense` | 论文有没有在别处预先回应这条 critique？逐段 Grep + Read 全文找应答；找到则贴 file:line + 引用片段；没找到则写 "no defense found in <sections checked>" | 必填 — 不允许只查相邻段就下"no defense" |
| `alternative_interpretations` | 这条 critique 是不是误读？至少列 2 种"可能是我看错了"的解读路径；逐条用论文文本检验 | 必填 |
| `proposed_fix` | 若 CONFIRMED，给具体修复建议（改某行 / 改某公式 / 跑某 ablation / 加某假设说明）；不接受"作者应重新考虑此处"的空话 | 必填（CONFIRMED 时硬性） |
| `external_check` | §3.X 找到的代码对位 / 文献核实结果；带具体路径 / URL；标注是否实际验证过 | `--no-online` 时部分可空 |
| `sub_critique_potential` | 这条 critique 若成立，能再发散出哪些 sub-critique？给 ≥ 2 条 hint | 必填（用于决定是否进一步递归） |
| `verdict_provisional` | `CONFIRMED` / `MARGINAL` / `REFUTED` / `INCOMPLETE_FORBIDDEN` | 必填，由§5 决定是否升级为 final |

**深度执行约束**：
- `evidence` 中含数值时**当轮**用 Bash + python（sympy / numpy）跑一次自检脚本；输出贴入字段；无法跑则在字段最后写 `[unverified — needs symbolic check]` 并强制 §5 verdict 不能为 CONFIRMED（最多 MARGINAL）
- `paper_position` 必须真实存在；用 Read 一次确认引用片段；任何 file:line 写错 → critique 整条作废重做
- `paper_defense` 必须用 Grep + Read 至少查论文 5 个主要 section（abstract / intro / method / result / discussion / appendix / supplementary），不允许只查相邻段
- 任何字段写出 "应该 / 大概 / 我相信 / 通常 / 应当 / 可能 / 也许 / 或许" → 该字段无效，必须重写
- **§0.8 完整推进禁令在此强制生效**：任何字段含 "defer / 待确认 / 因成本 / 因时间 / future work / TODO / 略 / NEEDS-MORE-INFO 滞留" 字样 → 节点状态强制改为 `INCOMPLETE_FORBIDDEN`，必须继续推进至该字段完整。**不允许把半成品节点提交进 verdict**。

---

## 5. 第四阶段：评估、剪枝、决定是否继续递归

每完成一节点的§4，进入评估：

### 5.1 评分（每项 0–3，整数）

- **Severity** S：若 critique 成立，对论文的伤害量级（0=cosmetic；3=fatal — central claim 站不住）
- **Specificity** P：critique 定位精度（0=泛泛"the paper is unclear"；3=指向具体 file:line + 具体替换建议）
- **Reproducibility** R：另一独立 reviewer 能否独立到达同一 critique（0=纯主观；3=机械可复现，如 grep + 算术验证）
- **Fixability** F：若 CONFIRMED，修复难度反向评分（0=需重写整篇；3=改一行 / 加一句即可）
- **Sub-critique fan-out** B：这条 critique 若成立，能再开多少 sub-critique（0=孤立；3=系统性问题，会牵动论文整章重写）

`score = S + P + R + F + B`（满分 15）

### 5.2 verdict 转最终（与 brainstorm 对偶但语义不同）

- 论文中**找到反驳证据**（`paper_defense` 不为空且充分） → **REFUTED**，无论 score 多高
- `score ≥ 11` **且** `paper_defense` 为空 → **CONFIRMED**
- `8 ≤ score ≤ 10` 且 `paper_defense` 部分回应但不充分 → **MARGINAL**（保留但不再深 expand；列入"作者判断清单"）
- `score ≤ 7` → 不算 critique，等同 DEAD-END，**剪枝**（标灰；推导仍保留供后续参考避免重复）
- 任一字段为 `[NEEDS VERIFICATION]` / `unverified` 占主导 → **INCOMPLETE_FORBIDDEN**（强制回到§4 补全；不允许永久 NEEDS-MORE-INFO 滞留 — 与 brainstorm 不同的硬约束）

### 5.3 是否进入下一轮发散

- 仅 `CONFIRMED` 与 `MARGINAL` critique 进入下一轮（即在该 critique 上重新跑§3 全部 framing pass，挖 sub-critique）
- `REFUTED` 保留在树上但不再 expand（仍有价值：证明论文确已处理某攻击角度）
- `DEAD-END` 标灰；不再 expand
- `INCOMPLETE_FORBIDDEN` 强制回 §4 补全，**不允许直接进入下一轮也不允许结案**

### 5.4 兄弟 critique 合并

- 同父节点下任意两兄弟若 `critique_statement` + `paper_position` 语义相似 ≥ 0.85（人工判断也可），合并为单节点，保留 score 高的一方，另一方记 `MERGED_INTO=<id>`

---

## 6. 收敛判据（终止条件 — 必须**全部**满足）

> "看起来差不多了"不是收敛证据。下面 6 条同时为真才允许声明 CONVERGED。

1. **所有节点完整**：树里**没有任何** `verdict_provisional=INCOMPLETE_FORBIDDEN` 的节点。§0.8 完整推进禁令在此强制生效。
2. **CONFIRMED 占比下降**：最近 2 轮 expand 中，新增 critique 里 `verdict=CONFIRMED` 的占比 < `--min-confirmed-ratio`（默认 0.15）。
3. **每条 framing pass 都被触发过 ≥ 1 次**（§3.A–§3.L 全部）。
4. **所有 CONFIRMED critique 至少经过一次再发散尝试**（即每个 CONFIRMED 都被当作过 root 跑过§3 全 pass；得到的 sub-critique 或为合并、或为 REFUTED、或为 MARGINAL，不再产生新的 CONFIRMED）。
5. **§3.K 至少产生过 1 个完整探索过的 high-severity critique**（即使最终 REFUTED），且不是被§0.4 强制塞进来后立即剪枝的占位。
6. **用户显式 cap 未触顶**：若用户显式设置了 `--width N` / `--depth N` / `--rounds N` 并触顶 → 不算 CONVERGED，按下表报状态；但**所有已展开节点必须完整**（§0.7 后半段 + §0.8）。

**终止状态决策表**（执行优先级从上到下）：

| 触发条件 | 报告状态 | 必要前置 |
|---|---|---|
| §6 六条全过 | `CONVERGED` | — |
| `--width N` 触顶且全部叶完整 | `WIDTH_CAP_REACHED` | 所有叶 §4 12 字段填满 + §5 verdict 定论 |
| `--depth N` 触顶且全部叶完整 | `DEPTH_CAP_REACHED` | 同上 |
| `--rounds N` 用完且全部叶完整 | `ROUNDS_EXHAUSTED` | 同上 |
| 任一 cap 触顶但**仍有半成品节点** | **不允许停止** | 必须先把所有 `INCOMPLETE_FORBIDDEN` 推进到完整，再报上面任一 cap 状态 |
| 论文文件完全无法解析 | `EARLY_STOP=paper_unparseable` | 仅在§2 基线阶段；进入§3 后此项不再适用 |

CONVERGED / WIDTH_CAP_REACHED / DEPTH_CAP_REACHED / ROUNDS_EXHAUSTED 时输出**最终报告**（§7）。
**"探索成本太高"不构成停止理由**——这是本 skill 与"快速 lint"的关键区别。

---

## 7. 第五阶段：输出格式

### 7.1 实时增量写入

每完成一个 critique 节点的§4 都立即追加进 `<out>/tree.md` 与 `<out>/tree.json`。
不允许"探索完再统一写"——**断电恢复**要求树状态随时可读。

### 7.2 树文件结构

```
<out>/
├── tree.md             # 人类可读，markdown 大纲格式
├── tree.json           # 机器可读，含完整字段
├── confirmed.md        # 终态；按 score 排序的 CONFIRMED critique 列表 (主交付物)
├── marginal.md         # MARGINAL critique 列表（作者判断清单）
├── refuted.md          # REFUTED critique 列表（论文已成功处理的角度；正面记录）
└── nodes/
    └── <id>.md         # 字段过长的节点单独成文件（evidence > 100 行时强制）
```

### 7.3 tree.md 节点格式

```markdown
### <id>  <critique_statement[:80]>
- **parent**: <parent_id> | **framing**: §3.X | **score**: S=_ P=_ R=_ F=_ B=_ → total=_
- **verdict**: CONFIRMED / MARGINAL / REFUTED / DEAD-END
- **paper_position**: <file:line> — `<引用片段>`
- **evidence**: …（或 `→ nodes/<id>.md`）
- **assumptions**: …
- **predictions**: …
- **paper_defense**: <file:line + 引用片段 / "no defense found in §X, §Y, §Z">
- **alternative_interpretations**: …
- **proposed_fix**: …（CONFIRMED 时必填具体）
- **external_check**: …
- **sub_critique_potential**: …
- **children**: [id1, id2, ...]
```

### 7.4 终态报告（CONVERGED 或 cap 触顶时）

```
## paper-attack-tree 终态报告 — <file_path>

### 状态
- 状态：CONVERGED / WIDTH_CAP_REACHED / DEPTH_CAP_REACHED / ROUNDS_EXHAUSTED
- 模式：whole-paper / focused (--focus=<id>) / from-paper-review join
- 树形：max_depth_reached=D, leaf_count=W (= 最终 width), 总节点数=N
- 节点分布：CONFIRMED=c, MARGINAL=m, REFUTED=r, DEAD-END=d, INCOMPLETE_FORBIDDEN=0
  （若 INCOMPLETE_FORBIDDEN > 0 → 报告非法，必须回到§4 补全再发本节）
- 总轮次：R
- 触发收敛/停止的判据：…
- 用户 cap：width=<N|∞>, depth=<N|∞>, rounds=<N|conv>；触顶情况：…

### 主交付 — CONFIRMED critiques（按 severity 降序）
1. [id] <critique_statement> — score=14, S=3, paper_position=<file:line>
   - evidence: …
   - proposed_fix: …
2. ...

### MARGINAL critiques（作者判断清单 — 不能直接修，需作者裁决）
1. [id] <critique_statement> — score=9; 论文部分回应见 <file:line>；建议作者澄清 …
2. ...

### REFUTED critiques（论文已正面应答 — 正面记录，对作者答辩 reviewer 有用）
1. [id] <critique_statement> — 论文在 <file:line> 处已应答："<引用片段>"
2. ...

### 元层自检结果（§3.L 第 7 题汇总）
- 最 weird critique：…
- 高风险 fatal critique 收成：…
- 元层未能跳出的盲区（坦诚承认）：…

### 完整推进自审（§0.8）
- 所有 leaf critique 100% 完整推进，无任何 defer / NEEDS-MORE-INFO 滞留 / future-work 字样：是 / 否
- 若"否" → 报告非法，必须回到§4 / §5 修复

### 推荐下一步
- 给作者：CONFIRMED 全列表 + 修复优先级
- 给 reviewer / referee：MARGINAL 清单可作为 reviewer report 的具体提问
- 与 paper-review 联合：建议把 CONFIRMED 注入 paper-review 的 🔴 队列重跑收敛
```

---

## 8. 工具使用规范（cc-enslaver 投影）

| 任务 | 必用工具 | 禁止 |
|---|---|---|
| 论文 root 内容提取 | Read（全文）| 凭印象 / grep-only |
| critique paper_position 验证 | Read 引用片段 ±20 行 | 仅 grep 命中行号下判 |
| paper_defense 查找 | Grep 全文 + Read 每个命中段 | 只查相邻段 |
| 数学/数值 critique 自检 | Bash + python(sympy/numpy) | "易证 / 显然" |
| 文献引用核对 | WebFetch arXiv abs / DOI | WebSearch 摘要做结论 |
| 平行 critique 探索 | Agent(Explore / general-purpose) 子代理；多分支可并行 | 串行偷懒 |
| 代码 / CSV 对位 | Read / Bash 重跑脚本 | 凭"我记得脚本输出 X" |

**子代理使用建议**：
- 当树宽度 ≥ 5 时，把每个 framing pass 派给一个 Explore subagent 并行；汇总后由主 agent 做§5 评估
- 子代理 prompt 必须自包含（论文片段 + 当前 critique + 该 pass 的硬要求）
- 子代理返回的引用，主 agent 必须再 verify（cc-enslaver rule 04）

---

## 9. 反模式（绝对避免）

- ❌ "我列了 10 条 critique，每条一句话" — §4 的 12 字段没填即无效。
- ❌ "我相信这个 critique 论文没回应 / 已经回应" — 必须 Grep 全文 + Read 段落实证；不接受印象。
- ❌ "数学推导太长，evidence 字段留 'see comment'" — 整段 dump 进 `nodes/<id>.md`。
- ❌ "差不多了，CONFIRMED 也够多了，应该收敛了" — §6 的 6 条不全过即未收敛。
- ❌ "high-severity critique 太刺耳，跳过 §3.K" — 违反 §0.4 与 §3.K，整轮 framing pass 无效。
- ❌ "为了节省 context，只展开高分 critique" — 树是增量写盘的，不占 context。
- ❌ "WebSearch 找了，没找到 prior 批评，就是新的 critique" — 至少要换 3 种关键词组合 + 检查相邻 field。
- ❌ "用户没说要并行，我就串行 framing pass 跑" — `--rounds conv` 模式下并行是性能必需。
- ❌ "critique 树太大用户看不动，我手动剪一下" — 用户要的是穷尽，不是好看。
- ❌ "跑完 framing A–D 觉得够了" — §3.A–§3.L 全部必跑，下限 12，不可放宽。
- ❌ **"这条 critique 留作 NEEDS-MORE-INFO 待作者答复"** / **"因时间限制只展开了一部分 framing"** / **"暂不展开 §3.K，等下次重审"** — 全部违反 §0.8 完整推进禁令；NEEDS-MORE-INFO 不是合法终态。
- ❌ "探索成本太高，提前停止" — §0.7 默认 ∞ 上限；只有§6 收敛或用户**显式** cap 触顶才能停，且停时所有叶必须完整。
- ❌ "用户只要点评，不必给 proposed_fix" — CONFIRMED 必填 proposed_fix；没有 fix 的 CONFIRMED 自动降级为 MARGINAL。
- ❌ "REFUTED 不重要，删掉省事" — REFUTED 是正面记录；保留对作者答辩 reviewer 有用，删除等于丢失"论文已处理某攻击角度"的证据。
- ❌ "把 paper-review 已 CONFIRMED 的问题再列一遍" — 用 `--from-paper-review` 时已知 critique 直接入树作种子，重点是发散 sub-critique，不是重审。

---

## 10. 与其他 sci-paper skill 的接口

- **与 `/sci-paper:paper-review`**：互补关系——
  - `paper-review` = **预设 checklist** 静态审查（A–O 维度逐项 PASS/FAIL）；适合"修到零问题"流程
  - `paper-attack-tree` = **开放式 adversarial radial** 探索；适合"作者准备 rebuttal 前自检最坏批评"或"找 checklist 不覆盖的 weird 攻击角度"
  - **建议次序**：先 `paper-review` 把 checklist 项收敛到零；再 `paper-attack-tree --from-paper-review <report>` 在已干净的 baseline 上找 reviewer 仍可能挑出的非 checklist 问题
  - 反之亦可：先 `paper-attack-tree` 发现一批 critique，再用 `paper-review` 在每条 critique 涉及的具体维度上做静态验证

- **与 `/sci-paper:brainstorm`**：本 skill **就是** brainstorm 的方法学在论文 critique 上的应用；二者在 width/depth/node/12-framing/完整推进禁令上**结构同构**。若同时跑两个 skill：brainstorm 用于"该写什么新论文"（前向探索），paper-attack-tree 用于"已写的论文哪些会被批"（后向探索）。

- **与 `/sci-paper:mainline`**：mainline 处理结构 spine；本 skill 在 §3.A / §3.H / §3.L 等 framing 会自然命中 spine 类 critique。建议次序：先 mainline 锐化 spine，再 paper-attack-tree（spine 不清楚时大量 critique 会卡在"我看不出论文要说什么"层级）。

- **与 `/sci-paper:paper-style`**：若 `style-profile/<field>/style_dossier.md` 存在，§3.C 跨学科 reviewer 视角加入 field-aware 加权（该 field 的常见 reviewer 关注点优先）。

- **与 `/sci-paper:paper`**：本 skill 不写作；它产出的 `proposed_fix` 是写作 task 的输入，可交给 `/sci-paper:paper` 配合标准做实际编辑。
