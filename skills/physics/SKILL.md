---
name: physics
description: 物理第一原则核查（测量原件，只产 finding，不改稿）：量纲一致性、渐近极限、对称性/宇称/守恒律、信息论与统计不等式的前提、代数再推导、数值溯源、基础引用真实性、编译与交叉引用完整性。findings 走 sci-paper.feedback.v1 的后果类别与 measurement state；拿不到证据报 unmeasured 或 not_applicable，绝不记成零 finding。可单独运行，也是 /sci-paper:paper-review 维度 K 的唯一来源。Use for: 物理正确性核查, 量纲检查, 守恒律与宇称, 渐近极限, 数值溯源, physics check, 物理第一原则审查。
disable-model-invocation: false
argument-hint: "<file_path> [--field <name>]"
---

# physics — 物理第一原则核查（测量原件）

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`。findings 一律用
> `sci-paper.feedback.v1` 的后果类别与 measurement state。本 skill 不定义自己的
> 评级表，不产生 paper 级 PASS/FAIL，也不要求 advisory 归零。

**这是测量原件：只产 finding，不改稿。** 修复动作由调用它的组合 skill
（`/sci-paper:paper-review`）按标准 §6 路由；单独运行时把 finding 交还作者。

## 0. 取证纪律

1. **禁止用记忆 / 缓存 / 历史对话作为事实依据。** 每个数字、公式、引用都必须
   **当轮重新打开源文件读取**。"我记得 / 上次说过" 不是证据。
2. **禁止把关键词 grep 当作唯一证据。** grep 只定位行号；定位后必须 Read 上下文
   （前后 20 行起步）确认语义。
3. **禁止猜测 / 外推。** 不知道 → `unmeasured` + `NEEDS SOURCE`；数字对不上 →
   `INCONSISTENT (paper says X, source says Y)`；不写"应该是 X"。
4. **数据溯源强制链。** 每个数字必须回溯到 (a) 一个具体 CSV/npz/脚本输出，或
   (b) 一个具体 DOI/arXiv ID 的具体 Table/Figure/公式编号，或 (c) 同论文内一个
   已编号公式经一行算术得出。缺来源是 `integrity_blocker`。
5. **不可得永远不等于零 finding。** 缺工具、缺数据、缺访问权限一律显式标
   `unmeasured` / `degraded`，不适用的检查标 `not_applicable`。

## 1. 准备

1. 从头到尾 Read 论文全文（不抽样、不关键词跳读）；超长文件分块读完为止。
2. 建**公式清单**：每个 displayed equation 的左右端量纲 + 涉及物理量的定义。
3. 建**数字溯源清单**：abstract / table / figure caption / 正文的所有数值，
   每条记值、位置、声称来源、核验状态。
4. 执行论文的权威 build（LaTeX 项目为 `pdflatex × 2 + bibtex + pdflatex × 2`）；
   记录 errors、undefined refs、multiply-defined labels、overfull、missing-number。

## 2. 检查项 P1–P8

### P1. 量纲一致性

- 每个 displayed equation 左右两端量纲一致？
- 出现的常数（`σ_T`、`m_e c²`、`k_B`、`G`、`Σ_crit` 等）因子正确？
- Fisher 矩阵 `𝓕_θθ` 量纲为 `[θ]⁻²`；其逆 `𝓕⁻¹` 为 `[θ]²`。
- 给出但不可直接使用的 "schematic" 公式必须显式标 `(schematic, illustrative)`；
  未标注而量纲不闭合的按 `integrity_blocker` 处理。

### P2. 渐近行为

- 关键量在 `d→0`、`M→∞`、`ρ→1`、`N→∞`、`κ→0`、`ν→∞` 等极限下行为合理？
- 各极限是否对应已知解析结果（NFW、isothermal、Gaussian noise、CDM …）？
- 有 "saturation" 声明时是否给出趋近方向（从上 / 从下）？

### P3. 对称性 / 宇称 / 守恒律

- 显式对称性（rotation、parity、translation、gauge）被尊重？
- 任何 "parity argument" 真有数学根据，而不是措辞？
- Fisher additivity / DPI / `KL≥0` / `P_e≥0` 等不等式成立？
- sign 约定（`b/a=-1` vs `|b/a|=1`）跨全文一致？

### P4. 统计与信息论前提

**边界（canonical home — 本条）**：本维度只管**估计量本身的物理/信息论前提**；
样本划分、CV/grouping、泄漏防护、多重比较、prior 可复现性等**经验方法学**归
`/sci-paper:logic`，不在此复述。

- iid / Gaussian / 有限矩 等假设在 theorem 中显式声明？
- CLT 与 LDP regime 正确区分？`1/√N` 还是 `1/N` scaling？
- Pinsker / Fano / Cramér-Rao / DPI 的应用满足各自前提？

### P5. 代数再推导

- 多步推导逐步可重现；必要时手算并用独立脚本验证。
- 关键代数（如 Pinsker `TV²≤KL/2` 配 Gaussian `KL = ½Δθᵀ𝓕Δθ` →
  `TV ≤ ½√(𝓕Δθ²)`）逐步检查，不接受"显然"。
- 化简结果能从原始表达式重得？量纲在化简全程保持？

### P6. 数值溯源

- 每个数字 → 一个具体脚本输出、一个 DOI 的 Table/Figure，或本文已编号公式加一行算术。
- **重新跑脚本**确认数字仍能复现——脚本演变后会漂移。
- abstract / 正文 / 图表 caption 三方一致到所有有效数字。
- 被 cite 的 companion paper 数字与该 companion 当前版本同步？

### P7. 基础引用真实性

**边界**：本条只查**支撑物理论证的基础文献**（框架、定理、不等式、模型的原始出处）
是否真实且真支持所述物理主张。全量 bibliography 核验归 `/sci-paper:paper-review`
维度 F，不在此复述。

- 每个物理框架/定理/不等式的原始出处可查（DOI / arXiv ID / ADS）？
- 关键文献无遗漏？没有 fabricated 引用？

### P8. 编译与交叉引用完整性

- 权威 build → 0 errors？
- 0 undefined references / 0 multiply-defined labels / 0 overfull hboxes /
  0 missing-number warnings？
- 编译失败或 label 冲突为 `integrity_blocker`。

## 3. 边界 —— 本 skill 不做什么

- **不做语域 / AI-ism 判定。** em-dash 与 L0 词表是 `tools/ai_ism_lint.py` 的
  `l0_target`（`kind="l0_target"`，退出码 1）；论文倚重而语料不携带的术语由
  `tools/deai_register.py` 按 corpus document frequency 判定。本 skill **不自带
  关键词表** —— 一个问题两个互相矛盾的裁决比没有裁决更糟。
- **不做结构 tell 审计。** 归 `/sci-paper:de-ai --audit-only` 的 Pass 2。
- **不做经验方法学审查。** 归 `/sci-paper:logic`（见 P4 边界）。
- **不做叙事结构审查。** 归 `/sci-paper:mainline`。
- **不改稿。** 见顶部。

## 4. 后果分类

| 类别 | 本 skill 的来源 |
|---|---|
| `integrity_blocker` | 量纲错、物理错、推导错、数值不一致、编译失败、未声明的必要假设、伪造引用 |
| strong `advisory` | 命名/单位混用、精度不一、bracketing 超出物理域、schematic 公式无标注 |
| `advisory` | 纯表述偏好 |

每条 finding 带 measurement state。不适用的检查标 `not_applicable` 并说明为什么
不适用；拿不到证据标 `unmeasured` 并说明缺什么。

## 5. 报告

```markdown
# Physics — First-Principles Findings

**Target**: <file> | **Field**: <field or none>

## Coverage
| check | status | method / why not applicable |
|---|---|---|
| P1 … P8 | measured / unmeasured / not_applicable | … |

## Numerical anchors
| quantity | paper claim | source | verification |

## Findings
| id | kind | location | evidence | source trace | recommended action |

## Build state
- errors / undef refs / multiply-defined / overfull: … / … / … / …
```

不打印 PASS/FAIL 行。终止态是"每条检查都有明确状态"，不是"零 finding"。

## 6. 反模式

- ❌ "grep 了没找到，所以没问题" —— grep 是定位工具不是验证工具。
- ❌ "上次对话里这个数是 Y" —— 上次对话不算证据。
- ❌ 把 `unmeasured` 写成通过。
- ❌ "量纲不严格但读者会理解" —— 量纲错就是错。
- ❌ "schematic 不需要量纲一致" —— 必须显式标注，否则按 `integrity_blocker`。
- ❌ 在本 skill 内新增关键词词表。
- ❌ 复述 `/sci-paper:logic` / `/sci-paper:mainline` / `/sci-paper:figure-review`
  已经拥有的检查项。
