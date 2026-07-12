---
name: rewrite-in-voice
description: 根本性去 AI 改写器 (Layer C)。不"洗"AI 文本——AI 味活在句子结构里，无法靠替换词语去除——而是从论点重建：抽取 claim-graph（论点/证据/因果，丢弃 prose）→ 生成 fill-in 骨架逼出人类造句 → 用作者自己的语料 exemplar 作 few-shot 锚点 + 约束（认领论点/每段 ≥1 具体数字/禁元评论/命中句长方差目标）逐槽在作者嗓音里重写 → 对每段生成 N 个候选，用 rewrite_reward.py 的多项奖励（learned voice P(human) × 保数字 specificity，claim 保真度 relative-band 门控）best-of-N 选最佳 → 迭代最差段直至 fundamental 诊断收敛。奖励是"贴近人类嗓音分布 + 保义/保数字/保立场"，绝不奖励"骗过检测器"（guardrail 3 / AuthorMist→Pangram DAMAGE 教训）。人在环：默认展示 before/after + 奖励分解待作者认领。可选自蒸馏：作者认可的改写→追加为新正样本→周期性重训 voice 模型。与 ai_ism_lint 关键词 lint 互补（那个管 lexical tell，本 skill 管 structural AI 味）。Use when 用户说 "太 AI 了" / "去 AI 感" / "像人写的" / "rewrite in voice" / "重写得像我" / "机器味太重" / 手上有 AI 生成或 AI 味重的草稿要根本性去味。
disable-model-invocation: false
argument-hint: "<file_path> [--section <name>] [--n N] [--max-iter N] [--no-apply] [--distill] [--field <name>] — 指定草稿 (.tex/.md)；可选每段候选数 N (默认 5) / 迭代上限 / 只出改写不落盘 / 认可后自蒸馏 / 显式 field"
---

> **v1 — Layer C of the de-AI subsystem (docs/DEAI_SUBSYSTEM.md).**
> 调用：`/sci-paper:rewrite-in-voice <file>`.
> 写作标准（含 anti-AI-isms 硬规则）由 sibling skill `/sci-paper:paper` 提供；
> 关键词层 lint 由 `tools/ai_ism_lint.py` 处理；本 skill 专攻**结构层 AI 味**——
> 靠"从论点重建 + 作者嗓音再生 + 多项奖励 best-of-N"根本性去除，而非替换词语。

---

## 0. 顶层禁令（违反即改写无效）

> 这些直接落实 `docs/DEAI_SUBSYSTEM.md` 的四条 guardrail。

1. **禁止"洗"prose，必须从论点重建。** 不允许在原句上同义替换 / 删 em-dash / 换连接词冒充去 AI。AI 味活在句子结构（UID 平滑、句长同质、signposting）里，逐词替换去不掉。合法路径唯一：抽 claim → 骨架 → 在作者嗓音里重新造句。

2. **禁止奖励"骗检测器"，只奖励真实嗓音 + 保义 + 保数字（guardrail 3）。** 目标是"贴近人类嗓音分布并保留意义/具体性/立场"，**不是**"让 voice 模型输出高分"。`rewrite_reward.py` 是多项奖励（voice × specificity，claim 保真度门控）正是为此：一个洗了关键词但丢了数字或改了意思的候选**不可能**赢。教训：AuthorMist→Pangram DAMAGE，纯检测器奖励产出读起来更差且输掉军备竞赛。

3. **禁止编造数字 / 论点 / 引用来抬高 specificity（R2 硬约束）。** 改写只能**保留**源里已有的数字与论点，绝不新增未溯源的量。specificity 奖励衡量"保住了 claim 的数字"，不是"多写了数字"。任何改写引入源中不存在的数值 = 🔴 立即弃用。

4. **禁止绝对阈值，按作者语料相对校准（guardrail 1）。** 是否"AI 味重"以**本 field 的人类 corpus 基线**为准（burstiness / UID z-score，已由 deai_metrics / deai_oracle / voice 模型内建）；best-of-N 保真度门是**批内相对**的（FIDELITY_BAND），不写死 cosine 阈值。

5. **诊断驱动、人在环，非静默覆写（guardrail 2）。** voice 分只用来**选段 + 排候选**，不是论文 pass/fail 门。默认展示 before/after + 奖励分解交作者认领；`--no-apply` 只出不落盘。作者的判断 = 最终嗓音。

6. **cc-enslaver 全程适用。** 每个数字回读源（R2）；改写前 Read 整段上下文（不 grep-only）；不 defer / 不半成品；每段改写必给"root cause（何种 AI tell）+ solution（如何重建）+ evidence（奖励分解）"。

---

## 1. 第一阶段：准备

1. **Read 草稿全文**（`<file>`），建立段落 inventory：每个 blank-line 段落的行号 + 所在 `\section{}`（用 `deai_metrics.section_line_ranges` 的分节逻辑）。
2. **解析 field**：`style-profile/` 下单 field 自动选；多 field 要求 `--field`；0 个则报错（本 skill 依赖 voice 模型 + exemplar bank）。确认 `style-profile/<field>/voice_model.joblib` 与 `exemplar_paragraphs.jsonl` 存在；缺则提示先 `train_voice_model.py` / `extract_style.py`。
3. **跑 fundamental 诊断定位待改段**：
   ```bash
   python tools/ai_ism_lint.py <file> --field <field> --distribution --oracle --voice
   ```
   收集 advisory 段：`[voice-low:*]`（P(human) < 0.5）、`[burstiness-low:*]`、`[uid-low:*]`、`[opener-signposting:*]`。这些是**结构层**命中，正是关键词 lint 抓不到的 AI 味。同时跑 `deai_voice.py <file> --field <field> --scores` 拿每段 P(human) 排序，**最低分段优先**。
4. **读 `/sci-paper:paper` 的 Anti-AI-isms 节**作为写作基线（Tier A 零容忍词、em-dash 禁令、句长方差目标）。
5. 若传 `--section`，只处理该节；否则按 P(human) 升序处理所有低于 0.5 的段（`--max-iter` 段数上限，默认全部）。

---

## 2. 第二阶段：逐段"论点重建 + 嗓音再生"（每段一个循环）

对每个待改段 `P`（行号 `L`，所在节 `S`）：

### 2.1 抽取 claim（丢弃 prose）
从 `P` 抽出**核心论点 + 全部具体数字/实体**，写成一句去 padding 的 claim（这是保真度锚点，**不是**原段）。例：原段 "Furthermore, our comprehensive analysis leverages a robust framework to shed light on substructure; the method achieves 4.9σ and 22 of 43 clusters were confirmed, showcasing effectiveness." → claim = "Detection significance is 4.9σ; 22 of 43 clusters are confirmed." 把 claim 写入临时文件 `<scratch>/claim.txt`。**claim 里每个数字必须回读源确认（R2）。**

### 2.2 取作者嗓音锚点
```bash
python tools/retrieve_exemplars.py --section <S> --topic "<claim 一句话>" --k 5 --field <field>
```
（`S` 映射到 VALID_SECTIONS: abstract/intro/method/results/discussion/conclusion）。返回的 5 段是**作者本人**在该节的真实写法——few-shot 嗓音锚点。

### 2.3 生成 N 个候选（在作者嗓音里重造句）
以 claim 为内容、exemplars 为嗓音模板，写 `N`（默认 5，`--n`）个候选改写。每个候选**硬约束**：
- **认领论点**：陈述句，不 hedge 成 "may suggest"；
- **≥1 具体数字/细节**：保住 claim 的数字（不新增未溯源量）；
- **禁元评论 / 禁 signposting 开头**：不以 Furthermore/Moreover/Additionally/It is worth noting 开段；
- **命中句长方差**：长短句混排（对标 exemplars 的 burstiness，非等长句列）；
- **Tier A 零容忍词全避**（delve/leverage/robust 滥用/showcase/…，见 paper 标准）；
- **em-dash 0**。
每个候选写入 `<scratch>/cand_<k>.txt`。

### 2.4 best-of-N 选最佳
```bash
python tools/rewrite_reward.py --field <field> --reference <scratch>/claim.txt \
    --candidates <scratch>/cand_0.txt <scratch>/cand_1.txt ... 
```
读 rank 表：`combined` 最高者为选中段。奖励语义（见 `rewrite_reward.py` docstring）：
- `voice` = learned voice P(human)（已含 burstiness + UID）；
- `fidelity` = 对 claim 的 cosine，**批内相对 band** 门控（保义；漂移者 faithful=False 被降级）；
- `specificity` = 保住 claim 数字的比例；
- `combined` = faithful 段取 `voice*(0.5+0.5*spec)`，漂移段降到 `0.05*fidelity`。
**若 rank1 的 `faithful=False`**（全部候选都漂移了 claim）→ 不采用，回 2.3 重生成（收紧约束，强调保义）。

### 2.5 验证选中段确实更像人
对选中段单独跑：
```bash
python tools/deai_voice.py <scratch>/cand_best.txt --field <field> --scores
python tools/ai_ism_lint.py <scratch>/cand_best.txt --field <field> --distribution --oracle --voice
```
要求：P(human) 显著高于原段，且 `[voice-low]`/`[burstiness-low]`/`[uid-low]` 命中数下降。**若未改善** → 回 2.3 再生成（`--max-iter` 内）；连续 N 轮不改善 → surface 该段"未能收敛"，留原段 + 标注，交作者手改（不硬塞劣质改写）。

### 2.6 落盘（人在环）
展示 **before / after + 奖励分解 + 诊断前后对比**。默认用 Edit 把 `P` 替换为选中段（保持 LaTeX 环境/label 完整）；`--no-apply` 则只展示不改。每段落盘后 re-Read 改动区域确认无破坏。

---

## 3. 第三阶段：收敛 + 自蒸馏

### 3.1 收敛判据
所有待改段处理完后，重跑 §1.3 诊断。合法收敛 = 目标段 P(human) 全部 ≥ 0.5 **或**已 surface 为"未收敛交作者"。**禁止**"大部分改好了就算完"。整篇 `[voice-low]` 命中应显著下降并在报告里量化（前 X 段 → 后 Y 段）。

### 3.2 自蒸馏（`--distill`，可选，作者认可后）
作者**认可**的改写是新的真人嗓音正样本——这是"越用越好"的闭环（Layer D rung 2）：
1. 把认可段以 `{id, section, tier:"accepted", source:"<paper>", n_words, text}` 追加到 `style-profile/<field>/exemplar_paragraphs.jsonl`。**只追加作者显式认可的**（未认可/自动生成的不进，防 mode collapse + 防把 AI 味喂回正样本）。
2. 周期性（或 `--distill` 触发）重训：`python tools/train_voice_model.py --field <field> --refeature`，并**必验 OOD**（llm 低 / human 高，见 DEAI_SUBSYSTEM §Layer D）——重训后若 OOD 回归则回滚（同 ourdrafts 消融教训）。
3. DPO/RL rung（GPU，ceiling）不在本 skill；见 DEAI_SUBSYSTEM §Layer D rung 3，须在 validated reward 上做。

### 3.3 终态报告
```
# rewrite-in-voice — Report
Target: <file>  |  Field: <field>  |  Candidates/para: N
Paragraphs flagged: K  |  rewritten: R  |  surfaced-unconverged: U
Voice P(human): before [min..median..max] -> after [...]
Structural hits ([voice-low]+[burstiness-low]+[uid-low]): before B -> after A
Per-paragraph: L<line> [S] tell=<...> reward(voice/fid/spec) before->after
Distilled: <n accepted appended> (or: not run)
```

---

## 4. 反模式（绝对避免）

- ❌ 在原句上同义替换 / 删连接词冒充去 AI。→ 违反 §0.1；必须从 claim 重建。
- ❌ 为抬 specificity 编造数字 / 加"具体"实体。→ 违反 §0.3 + R2；只能保留源中数字。
- ❌ 用 padded 原段（而非 distilled claim）作保真度锚点。→ 保真度会把"去 padding"误判成"改义"（实测 padded 原段 cosine 0.30 vs claim 0.55）；必须传 claim。
- ❌ 采纳 `faithful=False`（漂移）候选因为它 voice 高。→ 违反 §0.2；漂移候选已被降级，不得手动提上来。
- ❌ 静默覆写全文。→ 违反 §0.5；人在环，展示 before/after 待认领。
- ❌ 把自动生成（未认可）的改写喂回 exemplar 正样本。→ 违反 §3.2；会把 AI 味蒸馏进"人类嗓音"，反向污染（同 ourdrafts 教训）。
- ❌ "大部分段改好即完成"。→ 违反 §3.1；未收敛段必须 surface 交作者，不硬塞劣质改写。
- ❌ 把 voice 分当论文 pass/fail 门。→ 违反 guardrail 2；它是选段 + 排候选的 advisory 信号。

---

## 5. 与其他 sci-paper skill 的接口

- **上游**：`ai_ism_lint.py`（关键词层 lint）标 Tier A/B 词；本 skill 处理**结构层**（lint 抓不到的 AI 味）。二者互补，都跑。
- **写作标准**：`/sci-paper:paper`（anti-AI-isms tier / 句长方差 / 引用规则）。
- **审查**：改写后走 `/sci-paper:paper-review`（per-claim 正确性 + 数字溯源）+ `/sci-paper:mainline`（结构 spine）确认改写没引入科学错误 / 没破坏叙事。
- **奖励/诊断工具**：`rewrite_reward.py`（best-of-N）、`deai_voice.py`（P(human)）、`deai_metrics.py`/`deai_oracle.py`（Layer A/B）、`retrieve_exemplars.py`（嗓音锚点）、`train_voice_model.py`（自蒸馏重训）。
- **设计依据**：`docs/DEAI_SUBSYSTEM.md` §Layer C + §Layer D。
