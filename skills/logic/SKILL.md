---
name: logic
description: 逻辑与统计核查（测量原件，只产 finding，不改稿）：claim graph 的循环论证、断链、偷换条件、充分/必要条件错误、未声明假设；样本与 split、CV/grouping、泄漏防护、metric、uncertainty、多重比较、prior 的可复现性；以及声明-证据纪律的审查端——动词强度不得超过证据强度。findings 走 sci-paper.feedback.v1。可单独运行，也是 /sci-paper:paper-review 维度 C 的唯一来源。Use for: 逻辑检查, 论证是否成立, 统计方法学, 数据泄漏, 多重比较, 声明证据纪律, claim-evidence, over-claim 检查。
disable-model-invocation: false
argument-hint: "<file_path> [--field <name>]"
---

# logic — 逻辑与统计核查（测量原件）

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`。findings 一律用
> `sci-paper.feedback.v1` 的后果类别与 measurement state。
> `/sci-paper:paper` 定义"声明-证据纪律"；本 skill 是它的**审查端**。

**这是测量原件：只产 finding，不改稿。** 措辞层面的弱化改写由组合 skill 路由到
`/sci-paper:de-ai` Pass 3，并受该 skill 的 Preserve List 约束——**不得为了降低
风险把证据绑定的 hedging 改强，也不得为避词改动数字、引用或 stance**。

## 0. 取证纪律

1. **每条声明当轮定位到证据。** 声明的支撑必须在本轮从正文数字、图、表或引用
   重新读到，记忆和旧报告只能帮助定位。
2. **grep 只定位。** 命中与未命中都要 Read 上下文确认语义。
3. **不能验证就标 unmeasured。** 无法访问数据、脚本或 companion 时显式说明缺口，
   不能因为查不到就当作支撑成立。
4. **不可得不等于零 finding。**

## 1. claim graph

从全文抽出经验声明与推理链，检查：

- **循环论证** —— 结论被用来支撑自己的前提。
- **断链** —— 中间步骤缺失，结论推不出来。
- **偷换条件** —— 前提在推理过程中被悄悄放宽或收紧。
- **充分/必要条件错误** —— 把"必要"当"充分"用，或反之。
- **未声明假设** —— 论证依赖但从未写出来的前提。

无效推理、错误外推或 unsupported conclusion 为 `integrity_blocker`。
合法但表达不清的逻辑连接通常是 `advisory`。

## 2. 统计方法学

逐项检查可复现性：

- 样本定义、split 方式、CV / grouping 策略；
- **泄漏防护** —— train/test 之间、特征构造与标签之间、同源样本跨 split；
- metric 定义与其适用前提；
- uncertainty 的定义、来源与样本量；
- 多重比较是否校正；
- prior（log-uniform / flat / informative）是否声明。

无效统计、数据泄漏为 `integrity_blocker`。

**边界（canonical home — 本条）**：本维度管**经验方法学**。估计量本身的
物理/信息论前提（iid / Gaussian / 有限矩的显式声明、CLT vs LDP regime、
Pinsker / Fano / Cramér-Rao / DPI 的适用条件）归 `/sci-paper:physics` P4，
不在此复述。

## 3. 声明-证据纪律

`/sci-paper:paper` "声明-证据纪律"的审查端：

- 每个经验声明有**正文内**数字 / 图 / 表 / 引用支撑；
- **动词强度不超过证据强度** —— `demonstrates` / `establishes` / `proves` 各自
  需要什么级别的证据，由标准定义；
- 模糊量级写成**有归属的数字或区间**，而不是 "substantially" / "much larger"；
- `significantly` 出现时必须伴随检验或数字，否则是 claim 缺陷。

分类：

| 情形 | 类别 |
|---|---|
| 无支撑，或动词强度超过证据强度 | claim-evidence defect → `integrity_blocker` |
| 措辞层面可以更准的弱化建议 | `advisory` |

**这不是词表判定。** `significantly` 之所以被点名，是因为它宣称了一个统计结论；
`landscape` / `demonstrate` 这类词的语域问题走 `tools/deai_register.py` 的
corpus document frequency，不在此按词表标记。

## 4. 边界 —— 本 skill 不做什么

- **不做物理第一原则核查。** 量纲、守恒、宇称、渐近、代数再推导归
  `/sci-paper:physics`（见 §2 边界）。
- **不做叙事结构审查。** "读者能不能跟上"归 `/sci-paper:mainline`；本 skill 只问
  "论证是否成立"。
- **不做语域 / AI-ism 判定。** 归 `tools/ai_ism_lint.py` 与 `/sci-paper:de-ai`。
- **不做引用真实性核验。** 引用是否存在、是否被伪造归 `/sci-paper:paper-review`
  维度 F；本 skill 只问被引内容**是否支撑该句的推理**。
- **不改稿。** 见顶部。

## 5. 报告

```markdown
# Logic — Reasoning and Statistics Findings

**Target**: <file> | **Field**: <field or none>

## Coverage
| area | status | method / why not applicable |
|---|---|---|
| claim graph / 统计方法学 / 声明-证据 | measured / unmeasured / not_applicable | … |

## Claim–evidence ledger
| claim | file:line | verb strength | evidence | verdict |

## Findings
| id | kind | location | evidence | recommended action | disposition |
```

不打印 PASS/FAIL 行。终止态是每条声明都有明确判定或明确记录的缺口。

## 6. 反模式

- ❌ "统计看着标准，跳过" —— 泄漏几乎总是藏在被跳过的那一步。
- ❌ 把 `significantly` 当词表命中标记，而不是去查有没有伴随的检验。
- ❌ 为了消掉 over-claim 把证据绑定的 hedging 改强——那本身是新的 claim 缺陷。
- ❌ 把"论证不成立"和"读者跟不上"混为一谈（后者归 `mainline`）。
- ❌ 把 `unmeasured` 写成通过。
- ❌ 复述 `/sci-paper:physics` 或 `/sci-paper:paper-review` 维度 F 已拥有的检查项。
