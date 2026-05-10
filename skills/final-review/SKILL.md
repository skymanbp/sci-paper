---
name: final-review
description: 最终审阅编排器。完整使用 5 个 skill 作为框架——paper（写作标准基线）/ paper-review（A–Q 全维度 checklist 审查）/ figure-review（图表 150-DPI 关）/ mainline（结构 spine）/ paper-attack-tree（adversarial radial critique）。**每个 skill 都在隔离上下文（Agent isolation=worktree）中独立运行**，cold-read 论文消除框架偏见。每轮 merge 所有 issue 后修复，循环直至**连续 2 轮所有 5 个 skill 均 0 issue**（稳态收敛）。**严禁** "基本干净 / 大致收敛 / 剩下都是 minor / 用户没时间提前结束"——这是投稿前的最终关，要求"完全收敛"。ITER_BUDGET 默认 10 轮，触顶 BREAK_WITH_USER_DECISION（不允许偷偷宣布完成）。
disable-model-invocation: false
argument-hint: "<file_path> [--max-rounds N] [--skip <skill>[,<skill>...]] [--field <name>] [--out <dir>] [--require-consecutive N] — 指定论文 (.tex/.md)，可选最大轮次（默认 10）/ 跳过某子 skill（如 --skip figure-review）/ 显式 field / 输出目录 / 稳态连续 N 轮（默认 2）"
---

> **v1 — 5-skill orchestrator with per-skill isolated context + iterate-to-perfect-convergence.**
> 用户原话："**加一个"最终审阅"功能，完整使用：1.paper 技能作为框架。2.paper review 技能。3.figure-review 技能。4.mainline 技能。5.paper attack tree 技能。并且循环多次使用，每次都隔离上下文，修改至完美，直至完全收敛。**"
> 本 skill 是上述需求的**逐字落地**：5 个 skill 全用、每次隔离上下文、循环至完全收敛。

# final-review — 投稿前最终审阅编排器

本 skill 不审任何内容**本身**——它**编排**已有的 5 个审查 skill 在隔离上下文中循环运行直至全部收敛。
适用场景：论文已经过 paper-review / mainline / paper-attack-tree 单独打磨多轮后，准备投稿前的**最终关**。

---

## 0. 顶层禁令（违反即审阅无效）

1. **禁止用记忆 / 缓存 / 历史对话替代任何子 skill 的实际调用。**
   每轮必须**真的调用** Agent tool 启动 5 个隔离子代理（除非 `--skip <skill>` 显式跳过）；不允许"我记得上轮 paper-review 已经收敛了，跳过本轮"。

2. **禁止在主代理本进程内直接跑 5 个 skill。**
   每个子 skill 必须通过 Agent tool `isolation: worktree` 启动隔离子代理；主代理本进程**只做编排 + 合并 issue + 应用修复**，不亲自审。这是用户"每次都隔离上下文"的硬性要求。

3. **禁止主代理覆盖子代理判断。**
   子代理报 🔴/🟡/CONFIRMED critique → 必须注入修复队列；不允许主代理判"这条不重要丢弃"。子代理之间 disagreement 视为更多 issue（合集，不是交集）。

4. **完全收敛硬约束。**
   合法终止 = **连续 `--require-consecutive` 轮（默认 2）**所有 5 个 skill（未 skip 的）都返回 0 issue。
   "1 轮干净就完成" / "4 个 skill 干净 + 1 个还有 1 个 🟡" 一律**未收敛**。

5. **不允许偷偷扩 ITER_BUDGET。**
   `--max-rounds` 触顶 → `BREAK_WITH_USER_DECISION`，向用户报未收敛清单；不允许内部自行从 10 改 20 继续跑。

6. **修改必须最小有效化（minimum effective change）。**
   主代理应用修复时禁止顺手重构、禁止"我看不顺眼也改"；每条修改必须可追溯到某子代理报的某条 issue。

7. **每轮独立。**
   round k+1 不允许带 round k 的"印象"。子代理用 isolation=worktree 已经隔离；主代理在 round 间也要清空缓存——每轮重读论文当前版本，重新启动 5 个子代理。

---

## 1. 调用语义与 flag

```
/sci-paper:final-review <file_path> [flags]
```

**file_path**：要审的论文（.tex / .md），必须为绝对路径或项目内相对路径。缺省 → 报错退出。

**flags**：

| flag | 默认 | 含义 |
|---|---|---|
| `--max-rounds N` | 10 | 最大循环轮次；触顶 = BREAK_WITH_USER_DECISION |
| `--require-consecutive N` | 2 | 连续 N 轮全 skill 0 issue 才算 CONVERGED；提高 N 增强稳态保证 |
| `--skip <skill>[,<skill>...]` | 无 | 跳过某子 skill（如 `--skip figure-review` 适合纯 .md 草稿；`--skip paper-attack-tree` 适合保守审）；**默认不允许 skip**——只在用户显式传入时才跳过 |
| `--field <name>` | 自动 | 与其它 sci-paper skill 一致的 field；会透传给子代理 |
| `--out <dir>` | `final-review-out/<UTCdate>__<filename-slug>/` | 输出目录 |

---

## 2. 第一阶段：准备（每次 final-review 启动一次）

1. **Read 论文当前版本全文** —— 让主代理对论文有 baseline 概念（用于 §4 修复时定位 + 决定优先级）。
2. **解析 field 并 Read `style-profile/<field>/style_dossier.md`（若存在）** —— 同其它 sci-paper skill 单 field 自动选；多 field 要求 `--field`。
3. **Read 当前 paper / paper-review / figure-review / mainline / paper-attack-tree 5 个 sibling SKILL.md** —— 主代理需要知道每个子 skill 的输出格式（PASS/FAIL / 🔴/🟡 / CONFIRMED/REFUTED/MARGINAL），才能合并 issue。
4. **建立 round counter `r=1` 和 `consecutive_clean_rounds=0`。**
5. **创建 `<out>/round-001/` 子目录** —— 每轮的所有子代理报告与 merged issue 列表都进这里。

---

## 3. 第二阶段：每轮执行（5 步串行 + 子代理调用全部 isolated）

### 3.0 Round 进入前

清空主代理对论文的"假设记忆"——主动 Re-Read 当前版本（处理上轮可能已修改的版本），刷新所有引用位置。

### 3.1 Step 1 — `/sci-paper:paper` 加载写作标准（主代理本进程；非 isolated）

> 用户原话："**paper 技能作为框架。**"
> paper 不是审查器，是**标准基线**。每轮开始**主代理本进程 invoke 一次 `/sci-paper:paper`** 加载写作标准（含 Anti-AI-isms tier 表 / 公式约定 / 引用规则 / 关键参考）。
> 这一步**不**进 Agent isolation——它是给主代理本进程的"评估基线"。

**操作**：主代理执行 `Skill paper`（无 args），把标准加载到 working context；记录此基线版本 ID（`<out>/round-<NNN>/paper-baseline.md`）。

### 3.2 Step 2 — `/sci-paper:paper-review` 隔离子代理（Agent worktree）

**主代理调用 Agent tool**：

- `subagent_type`: `general-purpose`
- `isolation`: `worktree`
- `description`: `"Round <r> isolated paper-review"`
- `prompt`（自包含）：
  > Target file: `<absolute path>`
  >
  > **Cold-read context**: You are running in an isolated worktree. You have NEVER seen this paper before. Do NOT rely on prior context, summaries, or "I think I remember". Re-Read every file, re-run every script, re-grep every pattern. cc-enslaver rules apply.
  >
  > **Task**: Invoke the sibling skill `/sci-paper:paper-review` on the target file with `--max-iter 5` and default flags (do NOT pass `--no-fix`; allow the skill's own auto-fix loop). Run the skill's full A–Q dimension protocol + zero-issue convergence hard loop + isolated MPR §4.4 final verification. cc-enslaver rules from `/sci-paper:paper-review` SKILL.md apply.
  >
  > **Report format**: Return the skill's §4.5 final convergence report verbatim, plus a one-line summary: `STATUS=CONVERGED|NOT_CONVERGED; RED=<n>; YELLOW=<n>; UNDER_SCRUTINY=<n>; ISOLATED_MPR=<PASS|FAIL>`. Do NOT abbreviate the report. Each unresolved issue must include file:line + current text + suggested fix.

**回传处理**：把子代理报告保存到 `<out>/round-<NNN>/paper-review.md`；提取 `STATUS` + issue 计数。

### 3.3 Step 3 — `/sci-paper:figure-review` 隔离子代理

同 §3.2 模板，prompt 改为调用 `/sci-paper:figure-review`。

**特例处理**：若 `<file>` 是 .md 草稿无 figure 文件 → 子代理自然返回 "no figures present, PASS"。若用户传 `--skip figure-review` → 跳过本 step 但**仍在 round counter 里记录"skipped"**（不当作"通过"，但不阻塞收敛判据）。

### 3.4 Step 4 — `/sci-paper:mainline` 隔离子代理

同 §3.2 模板，prompt 调用 `/sci-paper:mainline`，传 `--max-iter 5`。子代理会自己跑 mainline 的 §3 cold-read 7-Q questionnaire（mainline 内部已是 isolated cold-read pattern；这里是**双重隔离**，可接受）。

### 3.5 Step 5 — `/sci-paper:paper-attack-tree` 隔离子代理

同 §3.2 模板，prompt 调用 `/sci-paper:paper-attack-tree`，建议传：
- `--from-paper-review <out>/round-<NNN>/paper-review.md` — 让 attack-tree 在 paper-review 已找出的 CONFIRMED 基础上继续发散 sub-critique
- `--width 30 --depth 3 --rounds conv` — 第一轮探索性放宽；后续轮次可缩窄
- 让子代理跑到 attack-tree 自身收敛（CONVERGED / WIDTH_CAP_REACHED 等）

**回传期望**：CONFIRMED critique 数 + 节点分布 + 完整 critique 树。CONFIRMED 全部注入主修复队列。

### 3.6 Step 6 — Merge & Fix

主代理合并 4 个子代理（review / figure / mainline / attack）的 issue：

```
all_issues = []
all_issues += parse_issues(round-NNN/paper-review.md)       # 🔴/🟡
all_issues += parse_issues(round-NNN/figure-review.md)      # FAIL items
all_issues += parse_issues(round-NNN/mainline.md)           # 🔴/🟡 + Q6 confusion
all_issues += parse_issues(round-NNN/paper-attack-tree.md)  # CONFIRMED

deduplicate_overlapping_issues(all_issues)  # 同一 file:line 不同 skill 报的算一条
```

**应用修复**：按优先级（CONFIRMED > 🔴 > 🟡）逐条 Edit；每条修改后 re-Read 改动区域；不允许"批量修改不验证"。

**修复完成后保存** `<out>/round-<NNN>/fixes-applied.md`：每条 fix 标 `applied | skipped (with reason) | needs-author`（用户裁决项）。

### 3.7 Step 7 — 判定收敛

```
n_issues_this_round = sum of all_issues counts
if n_issues_this_round == 0 AND all skill STATUSes == CONVERGED:
    consecutive_clean_rounds += 1
    if consecutive_clean_rounds >= --require-consecutive (默认 2):
        return CONVERGED  # 最终终态
else:
    consecutive_clean_rounds = 0  # 重置；不允许"基本干净就算稳态"

r += 1
if r > --max-rounds:
    return BREAK_WITH_USER_DECISION  # 不允许偷偷宣布完成
```

---

## 4. 第三阶段：收敛终止条件与状态报告

### 4.1 终止状态决策表

| 触发条件 | 状态 |
|---|---|
| 连续 `--require-consecutive` 轮 4 个 skill 全部 0 issue + 全部 CONVERGED | `CONVERGED` |
| 4 个 skill 单轮 0 issue 但稳态轮数未达 N → 继续下一轮 | `IN_PROGRESS` |
| `--max-rounds` 触顶 | `BREAK_WITH_USER_DECISION` — 列残留 issue 给用户裁决 |
| 任一子代理调用失败 / 超时（连续 2 轮失败同一 skill） | `SUBAGENT_FAILURE`，要求用户手工诊断 |
| 用户中断 | `USER_INTERRUPTED`，保留中间状态 |

### 4.2 最终终态报告（仅 CONVERGED 时）

```markdown
# Final Review — Convergence Report

**Target**: <file_path>
**Total rounds**: K
**Consecutive clean rounds**: <--require-consecutive 默认 2>
**Final state**: ✅ CONVERGED

## Per-skill final status (last round)
| Skill | Status | 🔴 | 🟡 | CONFIRMED | Compile |
|---|---|---|---|---|---|
| paper-review | CONVERGED | 0 | 0 | — | 0 errors |
| figure-review | PASS | — | — | — | — |
| mainline | CONVERGED | 0 | 0 | — | — |
| paper-attack-tree | CONVERGED | — | — | 0 | — |

## All fixes applied across K rounds
### Round 1
[逐条 file:line + 来自哪个 skill + 修改前/后 diff 摘要]

### Round 2 ...

## Per-skill final convergence reports (verbatim, 不允许摘要)
### paper-review §4.5 report
[完整贴入]

### mainline §4.5 report
[完整贴入]

### paper-attack-tree §7.4 report
[完整贴入]

### figure-review report
[完整贴入]

## Convergence verification (cc-enslaver rule 06 + rule 07 自答)
1. 是不是真的解决了问题？✓ (5 个 skill 全部 0 issue 连续 2 轮 + 各自隔离 cold-read)
2. 有没有更好的方法？✓ (chosen orchestration + per-skill isolation; min-effective-change at each fix)
3. 改动是否经过验证？✓ (每轮重 Read + 子代理 cold-read + 稳态 N 轮)
4. 验证是否合理？✓ (覆盖 per-claim correctness / 结构 spine / adversarial critique / figure / writing standards)
5. (rule 07 覆盖性) 用户原始 5 skill + 隔离上下文 + 循环至完全收敛 全部落实？✓
6. (rule 07 标准性) "完整使用 / 每次都隔离 / 修改至完美 / 直至完全收敛" 全部硬动作？✓
7. (rule 07 忠实性) 无静默 skip / 无 ITER_BUDGET 偷偷扩容 / 无"基本干净宣布完成"？✓
```

### 4.3 BREAK_WITH_USER_DECISION 状态（max-rounds 触顶仍未收敛）

输出：当前残留 issue 全列表 + 每条建议（继续追加预算 / 接受残留 / 修改 --skip 跳过特定 skill），让用户决定。**不允许**主代理单方面宣布"已完成"。

---

## 5. 反模式（绝对避免）

- ❌ "5 个 skill 跑一遍就好，不必循环。" — 违反 §0.4；用户原话"循环多次使用 / 直至完全收敛"。
- ❌ "在主代理本进程内直接跑 paper-review 节省时间。" — 违反 §0.2；用户原话"每次都隔离上下文"——必须 Agent worktree。
- ❌ "round 1 干净了直接宣布完成。" — 违反 §0.4 + §3.7；必须连续 N 轮稳态（默认 2）。
- ❌ "figure-review 暂时跑不通，先 skip 报告完成。" — 违反 §0.1；除非用户显式 `--skip`，否则必须报 SUBAGENT_FAILURE 给用户。
- ❌ "paper-attack-tree 输出太多 CONFIRMED，主代理过滤一下。" — 违反 §0.3；子代理 CONFIRMED 必须全部注入修复队列；主代理无权过滤。
- ❌ "max-rounds 用满 10 轮还有 2 个 🟡，宣布完成。" — 违反 §0.5 + §4.3；ITER_BUDGET 用满 = BREAK_WITH_USER_DECISION。
- ❌ "round 2 还有 issue，本轮不跑 attack-tree 节省时间。" — 违反 §0.1；每轮必须完整跑所有未 skip 的 skill。
- ❌ "子代理报告太长，我提炼一下要点贴报告。" — 违反 §4.2 末尾要求"verbatim, 不允许摘要"。
- ❌ "上轮 paper-review CONVERGED，本轮不必再跑。" — 违反 §0.1 + §0.7；每轮独立，每轮重跑。修复可能引入新问题。
- ❌ "5 个 skill 中 4 个 CONVERGED + 1 个 NOT_CONVERGED 但只剩 1 个 🟡，作为投稿临界算通过。" — 违反 §0.4；"完全收敛" = 全 5 个 skill 全 0 issue。

---

## 6. 与其他 sci-paper skill 的接口

- **本 skill 是 5 个审查 skill 的编排器**，本身不审。所有审查决策来自子代理。
- **使用次序建议**：
  - 普通流程：先各自单独跑 `paper-review` / `mainline` / `paper-attack-tree` 把大问题清掉
  - 投稿前最后关：跑 `final-review` 做交叉 + 稳态确认
- **不要在 final-review 跑到一半时手工编辑论文**：会破坏隔离上下文的 cold-read 前提；如必须手工改 → 中断本次 final-review，改完后重启（round 计数从 1 开始）
- **不要把 final-review 当作"全自动一键投稿"**：BREAK_WITH_USER_DECISION 路径是设计意图，不是失败——它把用户裁决权保留在最终决策点上
