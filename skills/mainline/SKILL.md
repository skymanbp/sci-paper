---
name: mainline
description: 叙事主线核查（测量原件，只产 finding，不改稿）：建 paper-level purpose record 与 contribution graph，再按 cold reader 回答七问，定位读者需要回溯、补隐藏上下文或在竞争解读间抉择的地方。findings 走 sci-paper.feedback.v1；不假设三幕模板，多贡献论文可有多个明确相关的分支。可单独运行，也是 /sci-paper:paper-review 维度 E 的唯一来源。Use for: 叙事主线, 主线检查, contribution graph, 冷读七问, narrative spine, 文章结构是否讲得通, 读者会不会卡住。
disable-model-invocation: false
argument-hint: "<file_path> [--field <name>]"
---

# mainline — 叙事主线核查（测量原件）

> **Normative authority:** `docs/SCIPAPER_STANDARD.md` §5.4（thesis spine）。
> findings 一律用 `sci-paper.feedback.v1` 的后果类别与 measurement state。
> `/sci-paper:paper` 定义主线该长成什么样；本 skill 是它的**审查端**。

**这是测量原件：只产 finding，不改稿。** 结构修复的动作由组合 skill 路由到
`/sci-paper:de-ai` Pass 3（改写）或 `/sci-paper:condense`（删减合并）。

## 0. 取证纪律

1. **必须冷读。** 从头到尾 Read 全文；不得继承任何"这段我懂了"的既有结论。
   本 skill 的全部价值来自模拟一个第一次读这篇论文的人。
2. **每个节点带 `file:line`。** purpose record 与 contribution graph 的每个条目
   都必须指回当轮读到的具体位置，不能是概括。
3. **困惑必须可复现。** 写下"读者会卡住"时，要能指出卡在哪一句、缺的是哪个前提。
   说不出来的困惑不是 finding。
4. **拿不到就标 unmeasured。** 无法访问 companion paper、数据或图时显式说明，
   不能因为读不到就当作没问题。

## 1. 第一步：purpose record

建 paper-level purpose record，全部带 `file:line`：

- **root question** —— 这篇论文到底在问什么？
- **contributions[]** —— 有哪几项贡献？
- 每项贡献的 **method_or_argument** —— 靠什么方法或论证成立？
- 每项贡献的 **key_evidence[]** —— 关键证据是什么？
- **take-home + scope** —— 读者应该带走什么，以及这个结论覆盖到哪为止？

## 2. 第二步：contribution graph

- **nodes** = claims / definitions / methods / evidence / conclusions
- **有向边** = prerequisite / supports / qualifies / contrasts / derives-from

判读规则：

- **不预设三幕。** motivation → method → validation 是常见默认，不是所有论文
  必须套用的模板。
- **多贡献合法。** 多贡献论文可以有多个明确相关的分支；问题是**关系有没有讲
  清楚**，而不是图是否恰好只有一个连通分量。
- **disconnected node 是待查证据，不是自动 fatal。**
- **禁手**：用连接词桥接逻辑断链（拿 Furthermore / Moreover 顶替缺失的前提）。

## 3. 第三步：cold reader 七问

按第一次读的读者依次回答：

1. root question 是什么？
2. 贡献有哪些？
3. 贡献之间是什么关系？
4. 各自的方法 / 论证是什么？
5. 各自的关键证据是什么？
6. take-home 与 scope 是什么？
7. 读者在哪里需要**回溯**、**补隐藏上下文**，或在**竞争解读**之间抉择？

前六问答不上来，就是主线本身的缺陷，而不是读者的问题。第七问的每个落点都是
一条候选 finding。

## 4. 后果分类

| 情形 | 类别 |
|---|---|
| 矛盾，或关键 claim 缺必要支撑论证 | `integrity_blocker` |
| 高曝光、可复现的困惑 + 能给出具体修复 | strong `advisory` |
| 局部措辞、可读性偏好 | `advisory` |

- 缺失支撑关键 claim 的必要论证可升为 `integrity_blocker`。
- 其余 narrative finding 按证据强度分 strong 或 ordinary advisory。
- **不得要求所有结构 advisory 归零。** strong advisory 要 disposition，
  普通 residual 报告即可。

## 5. 边界 —— 本 skill 不做什么

- **不做冗余判定。** 重复 claim、无信息增量段、死定义归 `/sci-paper:condense`
  的检测端与 `/sci-paper:paper-review` 维度 I，不在此复述。
- **不做逻辑/统计审查。** claim graph 里的循环论证、偷换条件、统计前提归
  `/sci-paper:logic`。本 skill 只问"读者能不能跟上"，不问"论证是否成立"。
- **不做语言/语域审查。** 归 `/sci-paper:de-ai`。
- **不做跨章节一致性核对。** 同一符号/常数/样本量跨章节是否一致归
  `/sci-paper:paper-review` 维度 L。
- **不改稿。** 见顶部。

## 6. 报告

```markdown
# Mainline — Narrative Spine Findings

**Target**: <file> | **Field**: <field or none>

## Purpose record
| field | value | file:line |

## Contribution graph
| node | type | file:line | edges (type → target) |

## Cold-read seven questions
| # | question | answer or gap | file:line |

## Findings
| id | kind | location | reader confusion | proposed fix | disposition |
```

不打印 PASS/FAIL 行。终止态是七问都有明确答案或明确记录的缺口。

## 7. 反模式

- ❌ "整体看结构还行" —— 没有 purpose record 和七问逐条答案的总评无效。
- ❌ 拿摘要或 intro 概括代替全文冷读。
- ❌ 因为图不是单连通就判 fatal。
- ❌ 要求每篇论文都是 motivation → method → validation。
- ❌ 把"我读着有点乱"写成 finding，却指不出卡在哪一句。
- ❌ 复述 `/sci-paper:logic` 或 `/sci-paper:condense` 已经拥有的检查项。
