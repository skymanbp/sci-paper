---
name: mainline
description: 主线增强 / 叙事脊柱锐化器。完整阅读全文（禁止 grep-only / 记忆 / 猜测），从 7 个正向维度（主线锐化 / 语言精简 / 叙事结构 / 隔离可读性 / 推导完整 / 逻辑合理 / 主线串联）和 8 个反向维度（定义模糊 / 主线分散 / 多而不精 / 章节无关联 / 结构不清 / 缺学术叙事 / 上下文不统一 / 低信息量形容语句）双向审查并自动修复；专门处理 brainstorm 发散后的观点收敛与叙事整合；强制隔离上下文 cold-read 可读性二审；零问题收敛硬闭环。与 paper-review 互补（paper-review 管 per-claim 正确性，本 skill 管结构层 spine）。Use when 用户说 "主线不清" / "叙事乱" / "结构层审查" / "mainline" / "整合 brainstorm 输出" / "章节衔接有问题" / "story 不顺" / 想做 spine-level 审查（per-claim 已经 paper-review 过）。
disable-model-invocation: false
argument-hint: "<file_path> [--max-iter N] [--no-fix] [--skip-isolated-readability] [--from-brainstorm <shortlist>] [--field <name>] — 指定论文 (.tex/.md)，可选迭代上限 / 只审不改 / 跳过隔离可读性二审 / 显式引用 brainstorm shortlist / 显式 field"
---

> **v1 — 与 paper-review v3 / brainstorm v0.5 互补的结构层主线增强器。**
> 调用：`/sci-paper:mainline <file>`。
> 写作标准（含 anti-AI-isms 硬规则）由 sibling skill `/sci-paper:paper` 提供，
> per-claim 正确性 / 引用溯源 / 数据漂移由 `/sci-paper:paper-review` 处理，
> 本 skill 专攻**结构 + 叙事 + spine 一致性**层级。

## 主线增强 — 执行规范（v1）

本 skill 不是 lint，是**审查 + 主线增强迭代器 + 隔离上下文可读性终验器**：
- 进程内执行 §2 双向审查（7 正 + 8 负 + brainstorm 收敛）
- 进程末用**隔离 cold-read 子代理**做可读性二审（§3）
- 二审任何 spine 不可推断点 → 回灌 §4 重启

用户原话："**完整阅读全文，禁止关键词检索、记忆依赖、猜测，增强论文的主线叙事。**" 这是本 skill 的根本约束，落实为 §0 顶层禁令的硬条款。

---

## 0. 顶层禁令（违反即审查无效）

1. **禁止使用记忆 / 缓存 / 历史对话作为事实依据。**
   每个 spine 判定、每个 claim 抽取、每个推导评估都必须**当轮重新打开源文件读取**。
   "我印象中""上次说过""我相信"都不算证据。

2. **禁止 grep / 关键词检索作为主要证据。**
   主线 / 叙事 / 章节关联 / spine 这类**高维结构属性**不可能 grep 出来；
   必须 Read 上下文（章节级别，必要时全文）。
   grep 仅用于辅助定位反模式 token（如 §2.B8 低信息量形容词清单），定位后**必须 Read 句段确认语义**才能下判。

3. **禁止猜测 / 推断 / 外推。**
   不知道 spine 是什么 → 写 `the manuscriptE NOT INFERRED`；
   章节关联不明 → 写 `CHAIN BROKEN at §X→§Y`；
   不写"应该是 X / 大致是 Y"。

4. **完整阅读强制（与用户原话一致）。**
   论文 > 2000 行用 offset/limit 分块读完，**全部读过为止**。
   spine 是**全局属性**，任何抽样 / 跳读 / "看 abstract 即可"都必然漏判。

5. **修复时禁止"加过渡词软化"。**
   两段之间有 logical jump → **不允许**用 `furthermore / moreover / additionally / importantly / in addition / on top of that` 之类的 AI-tell 过渡词缝合；
   必须**重组结构** / **补缺失前提** / **删除其中一段**。
   过渡词缝合是**反 spine**——它把结构问题伪装成衔接问题。

6. **隔离上下文 cold-read 二审是 spine 验证唯一可信源。**
   主代理在 §2 已读全文，其"spine 清楚"判定**带框架偏见**（"我懂作者意思" ≠ "spine 客观清楚"）。
   §3 子代理必须**冷读**完成；其 cold-read 结果优先于主代理自我评估。

7. **零问题收敛硬约束。**
   合法终止 = §4.3 进程内 0 issue + §3 子代理 cold-read 7-Q 全过。
   "基本清晰 / 主线大致出来了 / 大部分章节关联 / 剩下都是 minor"**一律视为未收敛**。

---

## 1. 第一阶段：准备（完整阅读 + spine 候选提取）

1. **读 sibling skill `paper/SKILL.md`** — 内化写作标准（特别是 Anti-AI-isms 节，会影响 §0.5 修复反模式）。
2. **解析 field 并读 `style-profile/<field>/style_dossier.md`（若存在）** — 单 field 自动选；多 field 要求 `--field`；0 个 → 跳过 corpus-style 加权，仅警告。
3. **从头到尾 Read 论文全文**（不抽样、不跳读）。超过 2000 行用 offset/limit 分块读完，**全部读过为止**。
4. **若传入 `--from-brainstorm <shortlist.md>` → Read shortlist** 拿到原始发散方向集合（用于 §2.C）。若未传：跳过该输入，但 §2.C 仍强制执行（即使没有 brainstorm 来源也要查发散）。
5. **生成 spine 五元组：**
   - `root_question` — 本文要回答什么问题（一句话）
   - `central_claim` — 主张是什么（一句话）
   - `method_promise` — 用什么方法 / 工具 / 数据（一句话）
   - `key_evidence` — 核心证据是什么（一句话 + file:line 指向 figure/table/equation）
   - `take_home` — 读者读完应记住什么（一句话）

   每元素必须能 `file:line` 定位到论文具体句子；定位不到 → 标 `MISSING`。
   任一 `MISSING` = 🔴 spine 缺失，且后续 §2 全部其它检查在该项被修复前都受其污染（spine 残缺时其它结构判定意义减半）。

6. **生成 outline 三层结构：**
   - L0 — 章节标题 + 一句话主旨
   - L1 — 每段的 topic sentence
   - L2 — 段内 claim → evidence / derivation pointer

7. **生成 claim chain 图：**
   - 节点 = 论文中每个 claim（标号 C1, C2, ...）
   - 边 = "C_i 是 C_j 的前提"（含 equation 引用、data 引用、prior literature 引用）
   - 输出 = (a) 总节点数 N，(b) 总边数 E，(c) 连通子图数 K
   - **K > 1 = 🔴 spine break**（说明论文实际在论证多条不相交的 claim）

---

## 2. 第二阶段：双向审查

> §2 必须**先做正向 §2.A**（建立 spine 标准），**再做反向 §2.B**（按标准找反模式），**最后 §2.C**（brainstorm 发散收敛）。次序不可颠倒。

### §2.A 正向 7 维度（每项必跑且必给修复建议）

#### A1. 主线锐化（spine sharpness）

- [ ] 五元组（§1 step 5）齐全？任一 MISSING = 🔴。
- [ ] 五元组每元素是否在 abstract / intro / conclusion **至少两处**用一致 phrasing 出现（不要求字字相同，要求语义一致）？
- [ ] 论文若浓缩为 200-字 abstract，五元组能否完整呈现而不挤压？挤压 = 论文实际 spine 弱，需在 §4.2 重写 abstract。
- [ ] **Drop-test**：删除任一非 spine 段落后，spine 是否仍完整？若仍完整 → 该段是 padding，标 🟡。

#### A2. 语言精简（compression）

- [ ] 每段是否能再缩短 20% 而不丢信息？是 → 🟡，给出缩写版本建议。
- [ ] 同一句中 ≥ 2 个形容词 / 副词堆叠（如 "comprehensive and robust analysis" / "very significantly improved"）→ 删除堆叠，仅留信息量最高的一个，或量化替代。
- [ ] 名词化（nominalization）滥用：`"perform an analysis of"` → `"analyze"`；`"conduct a comparison between"` → `"compare"`。动词驱动 > 名词驱动。
- [ ] 重复名词链（如 `"the method that we propose, namely our proposed approach, which is called X,"` ）→ 收敛为单一名称。

#### A3. 叙事结构（narrative architecture）

- [ ] 论文整体是否遵循经典学术叙事弧 `problem → gap → approach → result → implication`？任一缺失 = 🔴（与 §2.B6 联合）。
- [ ] 每个 results 子节是否结构 = `设问 → 实验 / 推导 → 数据 → 解读 → 联系下游`？
- [ ] 章节顺序是否符合 dependency（先定义后使用、先方法后结果、先结果后讨论）？
- [ ] introduction 是否漏斗结构（宏观背景 → 具体 gap → 本文贡献）？

#### A4. 隔离上下文可读性（isolated readability — 占位）

- 本项实际执行在 §3 由隔离 cold-read 子代理完成。
- 主代理在 §2 仅做"自检 dry-run"：假装从未读过这篇文章，仅凭 §1 step 6 outline 推断 spine。
- 若推断显著困难（任一五元组无法从 outline 推断）→ 标 🟡 提示 §3 重点关注；但**不允许**用 dry-run 结果替代 §3 子代理报告。

#### A5. 推导完整性（derivation completeness）

- [ ] 每个 displayed equation 的前提（涉及的物理量、假设）是否在前文已定义 / 已陈述？
- [ ] 每个推导链 `step k → step k+1` 的理由（algebraic / physical / approximation）是否给出？
- [ ] 推导跳越（`"易得 / 显然 / 直接得到 / by inspection / it follows that"`）= 🟡，必须补步骤或显式标注"省略代数化简，详 Appendix X"。
- [ ] 关键推导的输入数据 / 假设是否在前文章节中已明确铺垫？
- [ ] 与 `/sci-paper:paper-review` §2.M 的 3-pass 协同：本项只查"完整性"（步骤是否齐全 + 前提是否给出），不重复 §2.M 的"对错性"。

#### A6. 逻辑合理性（logical soundness）

- [ ] 每个 conclusion 的前提是否充分？前提-结论之间是否存在 hidden assumption？
- [ ] 因果声明（`"A leads to B" / "A drives B" / "due to A" / "because of A"`）：是否有机制说明？仅相关性 = 🟡，必须改为相关性陈述或补机制。
- [ ] 推广是否 valid（样本到总体 / 一种 regime 到另一种 regime / 一个 system 到所有 system）？过度推广 = 🔴。
- [ ] 是否存在循环论证（claim P 用 Q 支持，Q 又用 P 支持）？
- [ ] `"if / iff / only if" / "necessary / sufficient"` 使用是否正确？

#### A7. 主线串联（chaining）

- [ ] 每个 section 末尾是否有"下文将…"或自然过渡？过渡必须**承接具体内容**（不是泛泛 `"Building on the above, we now…"`）。
- [ ] 每个 section 开头是否引用上文的**具体名词或符号**（不是 `"As discussed before, …"` 这种空白指代）？
- [ ] claim chain 图（§1 step 7）的连通子图数 K = 1？若 K > 1 → 必有 spine break，转 §2.B2 处理。
- [ ] 全文是否有且仅有一条主 spine？多条并列 = 主线分散（转 §2.B2 + §2.C）。

### §2.B 反向 8 维度（反模式扫描 + 必删 / 必改）

每条反模式给出**识别规则** + **修复动作**；命中即标 🔴 / 🟡，不允许"语境合适保留"。

#### B1. 定义模糊不清

- **识别**：术语首次出现无定义；定义用更模糊的词解释（`"X is a kind of approach to handle Y"`）；定义内部循环（`"X is defined as Y where Y is X with property Z"`）；用"some kind of / a type of / something like"代替严格定义。
- **修复**：补一行 operational definition — 变量符号 + 数学表达 + 单位 + 可测量。若是抽象概念，至少给一句话 + 一个具体例子。

#### B2. 主线分散

- **识别**：§2.A7 claim chain 图出现 ≥ 2 个不相交连通子图；或 abstract 列出 ≥ 2 个独立的 "main contributions"（contributions 互不依赖）；或论文同时论证 ≥ 2 个无 dependency 的核心 claim。
- **修复**：选一条作主 spine，其它降级（详 §2.C2）。**严禁**保留多 spine 用"three contributions"类标签蒙混过关。

#### B3. 内容多而不精

- **识别**：单段 > 8 句且每句信息量低；或方法节列出 ≥ 5 个 method variants 但 results 节只用其一；或 related work 罗列 ≥ 20 papers 无 thematic clustering；或多个章节论证同一点。
- **修复**：删除非主 spine 的 variants（与 paper-review §2.O 过程残影协同）；related work 改为 `thematic groups + 一句关键差异`；同点重复 → 保留首次最完整版本，其它删。

#### B4. 章节之间没有关联

- **识别**：section k+1 第一段不引用 section k 的任何具体内容（具体内容 = 具体名词 / 公式编号 / 表/图编号 / claim 标号）；method 节描述的步骤在 results 节没有对应输出（与 paper-review §2.L5 联合）。
- **修复**：补显式 cross-reference（`"Using the kernel from §3.2, we now …"`），不接受空白指代（`"As described, we now …"`）；若实际无关联 → **重新组织章节顺序** 或 **合并相邻章节**。

#### B5. 结构不够清晰

- **识别**：subsection 嵌套 > 3 层；并列 subsections 数量 > 5 且无 thematic 分组；单一章节兼具 method + results + discussion 三重职责；section 标题模糊（`"Discussion" / "Other Results"`）。
- **修复**：扁平化层级 + thematic re-grouping + split 单一章节 + section 标题改为内容描述（`"Discussion"` → `"Why the kernel saturates at small scales"`）。

#### B6. 缺少学术叙事

- **识别**：通篇 `"We did X. Then we did Y. We got Z."` 流水账（无 motivation / 无 implication）；或仅有结果罗列无 interpretive synthesis；或 results 后没有 "what this means" 段。
- **修复**：每个 result 旁配一句 `"This implies / suggests / indicates X."`；section 开头加 motivation 句（`"To answer Q1, we …"`）；conclusion 段补全 implication（`"Our result extends / refines / refutes the prior framework of [cite]."`）。

#### B7. 上下文不统一（与 paper-review §2.L 联合）

- **识别**：同一概念在不同章节用不同术语 / 符号 / 数值；同一假设在不同节强度不一致；abstract 用一套词，body 用另一套。
- **修复**：建立**单一 glossary**（每个术语只用一个名字 + 一个符号），全文 search-replace 统一；若必须区分两种相近概念 → 显式命名 + 显式定义二者差异。

#### B8. 低信息量形容语句（**强制 grep + Read 复核**）

强制 grep 清单（命中后**必须 Read 上下文**判定，禁止只看 grep 命中数下判）：

```bash
# 程度副词堆叠
grep -nE -i '\b(very|quite|rather|fairly|extremely|highly|substantially|significantly|considerably|notably|particularly|especially|remarkably|surprisingly|importantly|crucially|markedly|profoundly|deeply)\s+\w+' <file>

# AI-tell 形容词（与 /paper Anti-AI-isms 重叠；本节着重检查"低信息量"维度）
grep -nE -i '\b(comprehensive|extensive|thorough|systematic|robust|seamless|holistic|sophisticated|elegant|powerful|effective|efficient|advanced|cutting-edge|state-of-the-art|novel|innovative|groundbreaking|paradigm-shifting)\b' <file>

# 模糊量化
grep -nE -i '\b(various|several|a number of|many|some|certain|different|diverse|multiple|numerous|a wide range of|a variety of)\b' <file>

# 低信息名词
grep -nE -i '\b(insights?|implications?|aspects?|dimensions?|considerations?|nuances?|complexities)\b' <file>
```

**判定规则**（每个 grep 命中必走）：
1. 形容词后跟具体数字 / 受测量化（`"significantly higher (p<0.01)"`） → **保留**
2. 形容词后跟另一抽象名词（`"significantly improved performance"`） → **删除程度副词，量化具体数字**（`"30% lower MSE on dataset X"`）
3. 程度副词无具体量纲（`"very robust"`） → 删除程度副词；若想保留 → 加数值
4. `"various / several / a number of"` → **改为具体数字**（`"3 datasets" / "5 surveys"`）
5. `"insights / aspects / dimensions"` 等空名词 → 替换为具体名词（`"the role of the kernel" / "the saturation behavior at low SNR"`）

**B8 命中必须全部 Read 复核后判定**；不允许仅凭 grep 命中数下判（避免 false positive）；但**判定为低信息后必须全部修复**（不允许只修一部分）。

### §2.C brainstorm 发散收敛（**强制 — 即使未传 `--from-brainstorm`**）

> 用户原话："**由于 brainstorm 技能会发散性思考，你也可以检查是否有过于分散的观点，并尝试让这些方向集中起来，让叙事更加完整。**"
> brainstorm 默认产出多条 PROMISING 方向；论文 draft 阶段，作者容易把多条方向都写进同一篇文章，导致主线分散。本节专门处理这种"发散 → 收敛失败"。

#### C1. 发散观点检测

- [ ] 论文是否同时论证 ≥ 2 个**独立**的核心 claim（非"同一 claim 的多角度论证"）？独立 = 删除其中一个不影响另一个的证据 chain。
- [ ] 是否有未在 results / discussion 节兑现的 ad-hoc 方向陈述（`"we also explore X" / "another direction is Y" / "an additional avenue is Z"`）？这是 brainstorm 残影。
- [ ] 若 `--from-brainstorm <shortlist>` 提供：shortlist 中 verdict=PROMISING ≥ 2 条，且 paper 试图同时论证 ≥ 2 条 → 🟡 分散警告。
- [ ] discussion 是否列了"我们还可以做 X / Y / Z"等多个 future direction，且无优先级？这暗示作者本人也没收敛。

#### C2. 收敛策略（优先级从上到下）

1. **选定单一主 spine**：从所有候选 claim 中选**信息量最高、证据最完整**的一条作 main thread。给用户列 priority list 决定，若用户未介入则默认选 evidence 最多者。
2. **降级其它**：
   - 与主 spine **直接相关** → **并入** main thread 作支持论据
   - **仅是有趣旁支** → 移至 discussion 末段简短陈述为 `"open question"`（**不是** `"future work"`；避免与 brainstorm §0.8 / paper-review §2.O 的过程残影禁令冲突；不要写成"我们曾考虑过 X"）
   - 与主 spine **不相关** → **完全删除**，建议拆为独立 paper
3. **重写 abstract / intro / conclusion**：让五元组（A1）回到**单一 spine**。重写后必须重跑 §2.A1。

#### C3. 收敛后完整性自检

- [ ] 收敛后的 spine 是否仍能撑起一篇完整论文（不会被砍得只剩骨架）？若骨架过细 → 提示用户可能选错了主 spine，重回 §2.C2。
- [ ] 被降级 / 删除的方向是否在 supplementary（如有）或附属 paper（如有）中有处置说明（一句话即可）？
- [ ] abstract / intro / conclusion 三处对 main thread 表述一致？

---

## 3. 第三阶段：隔离上下文 cold-read 可读性二审（**强制，除非 `--skip-isolated-readability`**）

> 用户明确要求"**隔离上下文检查可读性**"。
> 主代理在 §2 已读全文，其"spine 清晰"判定**带框架偏见**（"我懂作者意思" ≠ "spine 客观清楚"）。
> 必须用**独立 cold-read 子代理**做第三方可读性验证。

### 3.1 触发条件

- §2.A + §2.B + §2.C 已完成且进程内 §4.3 第一轮收敛
- 用户未传 `--skip-isolated-readability`

### 3.2 子代理调用规范

主代理通过 **Agent tool** 启动子代理，参数：

- `subagent_type`: `general-purpose`
- `isolation`: `worktree`（隔离 git worktree，避免污染主工作树；若子代理无改动，worktree 自动清理）
- `description`: `"Isolated cold-read readability check for paper spine"`
- `prompt`：**自包含**，必须含以下内容（不允许省略）：
  1. **路径**：`Target file: <absolute path>`
  2. **冷读约束**：
     > `You are reading this paper cold. You have NEVER seen this paper or any prior conversation about it. Do NOT rely on prior context, summaries, or "I think I remember" — Read the file from line 1 to the end as if for the first time. cc-enslaver rules apply (no memory, no guessing, no grep-only).`
  3. **必答 7 题**（cold-read questionnaire — 子代理必须逐题独立作答，每答必带 file:line 证据）：
     - **Q1**：一句话写出本文的 root question（你是从论文哪里得到这个判断的？file:line）
     - **Q2**：一句话写出本文的 central claim（同上要求证据）
     - **Q3**：一句话写出本文的 method promise
     - **Q4**：一句话写出本文的 key evidence（核心 figure / table / equation 编号）
     - **Q5**：一句话写出本文的 take-home message
     - **Q6**：论文是否有任何地方让你"读不懂、读不下去、回头找上下文"？**列出每一处** file:line + 困惑原因
     - **Q7**：论文的主线是 single thread 还是 multiple threads？若 multiple → 列出每条 + 推测的主导线
  4. **报告格式**：必须用结构化 markdown 返回 Q1-Q7 的具体答案；每答必带 file:line / 引用片段；**不接受**`"看起来还行" / "整体清晰" / "spine 基本能看出来"`等无证据总评。

### 3.3 子代理报告处理

| 子代理状态 | 主代理动作 |
|---|---|
| Q1-Q5 全 1 句话答出 + 与主进程五元组一致 + Q6 = 0 confusion + Q7 = single thread | spine 验证通过，进入 §4.5 最终报告 |
| Q1-Q5 任一答不出 / 答错 / 与主进程不一致 | 🔴 spine 不可推断；注入主队列回 §4.3 重启 |
| Q6 列出 ≥ 1 confusion | 每条 confusion 转 🟡 注入主队列回 §4.3 |
| Q7 = multiple threads | 🔴 主线分散；转 §2.B2 + §2.C 处理，回 §4.3 |
| 子代理调用失败 / 超时 | 报 `READABILITY_AGENT_FAILED`；不允许伪装通过；要求用户介入决定是否手工 cold-read 或允许跳过 |

### 3.4 重启上限

- 每次回 §4.3 后再次到达进程内收敛 → 再次跑 §3
- "§4.3 ↔ §3" 往返上限 = `--max-iter` 的 2 倍（默认 10）
- 仍不收敛 → 报 `NOT CONVERGED (process+isolated-readability)`；列全部未解项；**不允许声称完成**

---

## 4. 第四阶段：报告 + 修复迭代 + 收敛

### 4.1 单轮报告格式

```
## 主线增强报告: <filename> — Iter <N>

### Spine 五元组
- root_question: <一句话> (file:line)
- central_claim: <一句话> (file:line)
- method_promise: <一句话> (file:line)
- key_evidence: <一句话> (file:line)
- take_home: <一句话> (file:line)
[任一 MISSING → 🔴]

### Claim chain 图
- 节点数: N
- 边数: E
- 连通子图数: K  (K > 1 = 🔴 spine break)
- 孤立节点: [C_i, C_j, ...] (若有)

### §2.A 正向 7 维度
A1 主线锐化 / A2 语言精简 / A3 叙事结构 / A4 隔离可读性 (dry-run) /
A5 推导完整 / A6 逻辑合理 / A7 主线串联
[逐项 PASS / FAIL + file:line + 证据]

### §2.B 反向 8 维度
B1 定义模糊 / B2 主线分散 / B3 多而不精 / B4 章节无关联 /
B5 结构不清 / B6 缺学术叙事 / B7 上下文不统一 / B8 低信息量形容
[逐项命中数 + 修复优先级]

### §2.C brainstorm 发散收敛
- C1 独立 core claim 数: M (= 1 才算合规)
- C2 应用的降级策略 (若 M > 1)
- C3 收敛后 spine 完整性自检结果

### 修改清单（按优先级）
1. 🔴 必改 (spine 缺失 / 分散 / 章节断链 / 推导跳越): [file:line + 当前 + 建议]
2. 🟡 建议改 (语言精简 / 形容词低信息 / padding): [同上]
3. 🟢 可选: [...]
```

### 4.2 修复阶段（默认开启，除非 `--no-fix`）

1. **修复优先级**（同级内）：
   - spine 缺失 (A1) > 主线分散 (B2) > 章节断链 (B4 / A7) > 推导跳越 (A5) > 定义模糊 (B1) > 缺学术叙事 (B6) > 上下文不统一 (B7) > 结构不清 (B5) > 多而不精 (B3) > 低信息量形容 (B8 / A2)
2. 每条修复后 Re-Read 改动区域 + 重跑该维度该项检查；spine 类修复后必须重跑 claim chain 图。
3. **严禁的修复反模式**（与 §0.5 一致）：
   - ❌ 用 transitional phrase (`furthermore / moreover / additionally / importantly / crucially / in addition`) 缝合 logical jump
   - ❌ 加 `comprehensive / robust / sophisticated / elegant` 类形容词 puff 来掩盖结构松散
   - ❌ 把分散观点写成 `"We investigate three aspects: ..."` 三平行结构掩盖主线缺失
   - ❌ 给空洞段落加 topic sentence 掩盖该段无信息
   - ❌ 把 brainstorm 残留方向写成 `"future work"` 当掩护（与 paper-review §2.O 联合禁止）
   命中任一 → 修复无效，回 §4.2 重选。

### 4.3 零问题收敛硬循环

```
ITER_BUDGET = --max-iter N (默认 5)
for iter in 1..∞:
    report_k = full_review(file)            # §1 + §2.A + §2.B + §2.C
    if all hard_criteria(report_k) met:
        run_isolated_readability(§3)        # 首次进入 §3
        if §3 passes: break (CONVERGED)
        else: inject §3 findings into queue; continue
    apply_fixes(report_k.🔴 ∪ report_k.🟡)  # §4.2
    if iter >= ITER_BUDGET:
        BREAK_WITH_USER_DECISION()           # 不允许偷偷宣布完成
```

**进程内（§2）收敛硬判据**（必须**全部**满足；任一不满足即未收敛）：

| 判据 | 阈值 |
|---|---|
| Spine 五元组 MISSING 数 | = 0 |
| Claim chain 连通子图数 K | = 1 |
| 孤立 claim 节点数 | = 0 |
| 🔴 issue 数 (§2.A + §2.B 合计) | = 0 |
| 🟡 issue 数 | = 0 |
| §2.B8 grep 命中 Read 复核后真低信息的数量 | = 0 |
| §2.C1 独立 core claim 数 | = 1 |
| LaTeX 编译错误（若是 .tex） | = 0 |

**绝对禁止的"软收敛"出口**：
- ❌ `"spine 基本清晰，剩下的是表达问题"`
- ❌ `"两条 thread 都有价值，保留作为 multi-contribution paper"`
- ❌ `"用户没时间做 §3 cold-read，跳过宣布完成"`

### 4.4 §3 二审通过 = 终态

进程内 §4.3 收敛 **AND** §3 子代理 Q1-Q5 全对 + Q6 = 0 + Q7 = single thread → CONVERGED，进入 §4.5。

### 4.5 最终终态报告

```markdown
# Mainline Enhancement — Final Convergence Report

**Target**: <file_path> (N pages)
**Process-internal iters**: K
**Isolated cold-read re-verifications**: J
**Final state**: ✅ spine 五元组齐全 / claim chain K=1 / 0 🔴 / 0 🟡 / cold-read 7-Q 全过

## Final spine 五元组（与 §3 子代理 Q1-Q5 对齐）
[逐元素一行 + file:line]

## §2.A–§2.B–§2.C summary
[每维度一行 PASS + 关键证据]

## §3 子代理 cold-read 报告（贴入原文，不允许摘要）
[Q1-Q7 完整回答]

## 修复痕迹（按 iter 分组）
### Iter 1
- 🔴 [file:line] description → fix
- ...

## Convergence verification (cc-enslaver rule 06 + rule 07 自答)
1. 是不是真的解决了问题？✓ (证据: 五元组齐全 + K=1 + cold-read Q1-Q5 全对)
2. 有没有更好的解决方法？✓ (chosen min-effective-change at each fix; 未用过渡词缝合)
3. 改动是否经过验证？✓ (per-fix re-Read + claim chain 重跑 + §3 cold-read)
4. 验证是否合理？✓ (覆盖正/反双向 + 隔离 cold-read 验证)
5. (rule 07 覆盖性) 用户原始 7 正 + 8 负 + brainstorm 收敛全部落实？✓
6. (rule 07 标准性) "完整阅读 / 禁止关键词检索 / 禁止记忆 / 禁止猜测 / 隔离上下文检查" 全部硬动作？✓
7. (rule 07 忠实性) 无静默降级、无 TODO、无 future-work、无 transitional-phrase 缝合？✓
```

---

## 5. 与其他 sci-paper skill 的接口

- **与 `/sci-paper:paper`**：本 skill 假设作者已遵守 `/paper` 的写作标准（特别是 Anti-AI-isms）。本 skill 修复时**不允许**违反 `/paper` 的 Tier A 禁词清单。
- **与 `/sci-paper:paper-review`**：互补关系——
  - `paper-review` 管 per-claim 正确性（数字 / 引用 / 推导 / 数据漂移 / 过程残影）
  - `mainline` 管结构层 spine（叙事 / 章节关联 / 主线收敛）
  - **建议次序**：先 `paper-review` 把内容正确性收敛到零，再 `mainline` 锐化结构 spine。反之亦可，但 spine 大改后通常需 re-run `paper-review` 验证 per-claim 仍正确。
- **与 `/sci-paper:brainstorm`**：若论文 draft 起源于 `brainstorm` 的 shortlist，调用本 skill 时建议传 `--from-brainstorm <out>/shortlist.md`，让 §2.C 拿到原始发散方向集合做精准收敛检测。
- **与 `/sci-paper:paper-style`**：若 `style-profile/<field>/style_dossier.md` 存在，§2.A2 / §2.B8 的形容词清单按 corpus 实测频率加权，优先于本 skill 内置默认清单。

---

## 6. 反模式（绝对避免）

- ❌ `"spine 大致清楚就行，不必锱铢必较。"` — 违反 §0.7；spine 是 0/1 属性。
- ❌ `"用 furthermore / moreover 缝合两段。"` — 违反 §0.5；过渡词是 AI-tell，不是 spine。
- ❌ `"形容词 'comprehensive' 在这里是必要描述，保留。"` — 违反 §2.B8；几乎所有 `comprehensive / robust / sophisticated` 都可删或量化。
- ❌ `"claim chain 图分两块是因为文章本来就讨论两个方面。"` — 违反 §2.B2 / §2.A7；要么选一个作主 spine，要么拆为两篇 paper；不允许"two-contribution paper"自我蒙混。
- ❌ `"隔离 cold-read 子代理读不懂是因为这是技术性强的论文，正常。"` — 违反 §0.6 / §3；冷读子代理读不懂 = 真的 spine 不清楚；技术性论文也必须 spine 可推断。
- ❌ `"推导中 'by inspection' 是行业惯例，保留。"` — 违反 §2.A5；至少加 Appendix 或一行 reasoning。
- ❌ `"Q6 confusion 是子代理理解能力问题，丢弃。"` — 违反 §3.3；冷读 confusion 必须当 🟡 处理。
- ❌ `"把不相关方向移到 future work 当掩护。"` — 违反 §2.C2；`future work` 不能成为"藏垃圾的地方"；用 `open question` 短句或完全删除。
- ❌ `"B8 grep 命中太多，挑几个修。"` — 必须**全部 Read 复核**后判定，且真低信息的**全删**；不允许抽样修。
- ❌ `"iter 5 没收敛，宣布完成附残留清单。"` — 违反 §4.3 末尾；ITER_BUDGET 用满 = `BREAK_WITH_USER_DECISION`，不允许偷偷宣布完成。
- ❌ `"§3 cold-read 太慢，跳过宣布完成。"` — 违反 §0.7 / §3；除非用户显式传 `--skip-isolated-readability`，否则必须跑。
- ❌ `"分散的两条 thread 都是 brainstorm shortlist 上的 PROMISING，都保留。"` — 违反 §2.C2；brainstorm shortlist 是**候选池**，论文只挑一条。
- ❌ `"先用 grep 找 spine 关键词位置。"` — 违反 §0.2；spine 不是关键词，必须 Read 全文判定。
