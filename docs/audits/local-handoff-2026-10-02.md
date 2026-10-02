# 本地交接：需要 `wgl` profile 才能完成的核对（2026-10-02）

2026-10-02 的文档全量复核（`df59140` 至本文件所在提交）在云端完成。云端没有
`style-corpus/wgl/` 的语料，`style-profile/wgl/` 也是空的，所以下面几项只能在有语料的
本地 session 里做。除此之外，复核发现的问题都已修完并推到 `main`。

每一项都写了：要做什么、用什么命令、结果怎么回填。数字一律从命令输出里取，不凭记忆。
完成一项就在本文件里把它划掉，并注明提交号；全部完成后，在
[`full-review-2026-09-27.md`](full-review-2026-09-27.md) §10 的落地表里加一行，指向本文件。

## 前提

```bash
# style-profile/wgl/ 应当已是 2026-09-27 的重建；若不是，按 style-profile/README.md
# 的完整命令链重建（build_profile 加上各轴的 --calibrate），或者走 /sci-paper:calibrate
python tools/validate_plugin.py
python -m unittest discover -s tests
```

云端跑出的结果是 802 tests、17 skipped，被跳过的就是 `tests/test_published_figures.py`
里依赖 profile 的那些。到了本地，**这 17 项必须实际运行并通过**：文档里引用的每个图表数字，
它都会从对应 artifact 重新算一遍，所以它通过了，就证明本轮挪动和改写的数字没有走样。
如果有失败，按失败信息修改对应的文档，不要改测试。

## ~~1. document-scale §9.4 与 §9.4b 的数值冲突（必须解决）~~ ✅ `e87748f`

`docs/architecture/evaluation/document-scale.md` 里，§9.4 的 Vintage 框写的是 shipped scorer
按长度分层后，`r(distance, paragraph count)` 从 **0.353 → −0.080**（493 篇）；§9.4b 引用的是
同一个结果，写的却是 **0.353 → −0.113**。两处都标注为重建后重测，而 2026-08-27 之前的
git 历史已被压掉，无法分辨哪个是当前值。

在当前 profile 上重测 shipped 路径（与 `eval_docscale` 同一个打分入口）：

```bash
python - <<'EOF'
import json, statistics, sys
from pathlib import Path
sys.path.insert(0, "tools")
import eval_docscale as ev
field = "wgl"
baseline = json.loads(Path(f"style-profile/{field}/docstructure_baseline.json").read_text(encoding="utf-8"))
points = ev.collect(baseline, field, Path("style-profile"), Path("style-corpus"))["human"]
distance = [p["distance"] for p in points]
paragraphs = [p["n_paragraphs"] for p in points]
print("n =", len(points), " r(distance, paragraphs) =", round(statistics.correlation(distance, paragraphs), 3))
EOF
```

回填：

- 把 §9.4 Vintage 框和 §9.4b 括号里的值都改成实测值，同时更新篇数，并写明测量日期；
- `grep -rn "0.353" docs/ README*.md` 查一遍，凡是引用这对数字的地方都要一致；
- 如果实测值和 −0.080、−0.113 都不一样，就在 §9.4 里写清"重建后重测为 X（日期）"，旧值不保留。

## ~~2. 从 `tools/README.md` 移入 EVALUATION、云端未能复核的数字~~ ✅ `e87748f`

审计项 I38 把评估数字从工具注册表移进了 EVALUATION，搬迁时一字未改。下面这一项是当前状态的
数字（不是带版本号的历史记录），需要重跑确认：

- `evaluation/learned-model.md` §7.6：legacy word-ngram 分类器在 2026-09-27 重建上的
  F1 **0.822 ± 0.116**。命令：`python tools/train_ai_ism_classifier.py --field wgl`，
  把输出的分组交叉验证 F1 与 §7.6 对照；不一致就改 §7.6 并注明日期。

§5 的标题识别计数（1,671 / 10、305 / 325，v0.28.0）和 §21.3 的抓取器 finding 数（v0.34.0）
都是带版本号的历史测量，不需要重跑。

## ~~3. examples 的 advisory 计数~~ ✅ `e87748f`

`examples/README.md` 记录的是两份示例稿件在 v0.39.0 profile 上的输出（22 → 17 条 advisory，
以及逐规则的计数）。按该文件开头的命令重跑：

```bash
python tools/ai_ism_lint.py examples/sample-manuscript.tex --field wgl
python tools/ai_ism_lint.py examples/sample-manuscript-revised.tex --field wgl
```

总数和逐规则计数都要与 `examples/README.md` 一致。逐规则各行加起来不等于总数，可能只是因为
有些规则没列出；如果是这样，就在表下注明"其余 N 条来自未列出的规则"。

## ~~4. `style-profile/README.md` 的本地状态句~~ ✅ `e87748f`

`style-profile/README.md` 写着 "Two fields are populated locally as of 2026-08-25"（`wgl` 和
`wgl-letter`）。请按本地实际情况核对这两个 field 是否都在、`wgl` 的语料构成是否仍是"19 篇精选 +
500 篇 `fulltext-arxiv/`"，然后把日期改为核对当天。

## 完成记录（2026-10-02，本地 session，提交 `e87748f`）

前提：`validate_plugin.py` 全过；`unittest` 802 tests OK、0 skipped——`test_published_figures.py`
里依赖 profile 的 17 项实际运行并通过（改文档前后各跑一次）。

1. 已解决。shipped 路径实测 `r = −0.164`，504 篇；三个长度层（边界 49、78 段）中位距离
   2.412 / 2.291 / 2.125，层内 r = −0.350（197 篇）/ −0.075 / −0.215。与 −0.080、−0.113 都不同，
   §9.4 与 §9.4b 都改成这组值并注明日期；`0.353` 的其余命中（§9.4 正文的 role-coupling
   r(score, paragraphs) 与 learned-model 的 AUC 史）不是这对数字，未动。
2. 已改。分组 F1 实测 **0.838 ± 0.149**（两次运行相同；28,444 段 vs 20 条手写负例），§7.6 已改并注明日期。
3. 一致。22 → 17、strong 8 → 6、L0 1 → 0、表里逐规则各行都对；表下补注三条未列出的规则
   （`document-overdispersion` 1 / 1、`document-dispersion-manifold` 1 / 1、`burstiness-low` 1 / 0）。
4. 已核。`wgl` 仍是 19 篇精选 + 500 篇 `fulltext-arxiv/`；`wgl-letter` 已不是「描述性子集」——
   13 个制品均为 2026-09-27 重建，语料是 11 篇精选 + 28 篇 `fulltext-arxiv/`，句子已改，日期改为 2026-10-02。
