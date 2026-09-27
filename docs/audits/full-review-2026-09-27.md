# 全库缺陷排查与合理性审计（2026-09-27）

审计对象：`main` = `claude/relaxed-galileo-lpkc74` @ `6107991`（v0.38.0）。只读审计：本次未改任何代码或文档，本文件是唯一新增产物。四项任务——缺陷排查、逻辑与合理性、冗余与累赘、冲突/冗余/过时——分别对应 §3、§4、§5、§6；§2 是主会话自己重跑的复现记录，§8 是建议动作分级。

## 0. 方法与基线

- **基线**：`python tools/validate_plugin.py` 11/11 通过；`python -m unittest discover -s tests` 529 个测试通过、16 个跳过；`python -X dev -W error::DeprecationWarning -W error::ResourceWarning` 下同样全绿。可选依赖（numpy / pymupdf / sentence-transformers / scikit-learn / joblib / torch / transformers）均未安装，`style-profile/wgl/` 只有 `.gitkeep`，所以"无 profile、无可选依赖"的路径是本次覆盖最完整的路径；需要 numpy 的分支只读代码。
- **分工**：九个只读子审计并行，各自逐行读范围内每个文件，并在临时目录里用 `python - <<PY` 调 `tools/` 复现；主会话再对高/中严重度条目重跑一遍（§2）。编号前缀即范围：**A** length_gate / condense_map / tex_assembly / tex_macros / extract_sections / cli_common；**B** deai_feedback / metrics / features / structure / docstructure / docshape / partition / anchoring；**C** register / collocation / discourse / reference / residue / salience / personal / provenance / oracle / voice；**D** extract_style / build_profile / retrieve_exemplars / fetch_arxiv_abstracts / extract_md_negatives；**E** rewrite_reward / eval_findings / eval_docscale / label_findings / train_* / voice_*；**F** ai_ism_lint / verify_references / validate_plugin / CI / manifests；**G** 两份 README、tools/README、examples、CHANGELOG、manifests；**H** 12 个 skill 对照 standard / RESPONSIBILITIES / DISPOSITIONS；**I** 架构与证据文档；**M** 主会话自己的静态扫描与 CLI 探测。
- **状态口径**：**已复现** = 主会话在本机重跑得到同样输出（§2 有命令）；**已核实** = 子审计跑代码复现且主会话读过对应代码行；**待核实** = 只由代码推断，未跑。
- **严重度**：高 = 错误结果、错误退出码或门禁失效；中 = 局部错误，或文档与代码不一致到会误导操作；低 = 卫生问题。
- **上一次审计的落地情况**（`codex-review-2026-09-04.md` A1–A16）：A1、A3、A4、A5、A6、A7、A8、A9、A12、A13、A14、A16 已在 v0.36.2 落地并经本次复核；A2（否定/数字守卫）只落地了一个方向（§3.2 A12）；A5 只落地在 gate 一侧、map 一侧未落地（§3.2 A13）；A9 未落地到 `deai_residue.RE_LABEL`（§3.6 C4）；A10/A16 以改名收口；`RE_PAPER_AGENT` 缺 `presents` 一项以改文档收口，但 DEAI_SUBSYSTEM 的例句没改（§6.2 I25）。

## 1. 结论摘要

最要紧的十二条：

1. **门禁在没有证据时给出"测量"结论**（高）。`length_gate --before <不存在的文件>` 把空基线读成 0 词，每个 section 都报 GROWTH 并 exit 1（A1）；`ai_ism_lint dir.tex` 把不可读的根文件当空文档，L0 报 `measured`、exit 0（F3）；`--git-ref` 基线里已从工作区删除的 `\input` 子文件从基线消失，删整节的缩减被低估、`--require-shrink` 误报 NOT MET（A4）。三者同源：`tex_assembly._read_file` 吞掉 OSError 返回空串，根文件与子文件被同等对待。
2. **`rewrite_reward` 的科学保真门有四类系统性误判**（高）。LaTeX en-dash 范围 `0.5--1.2` 被切成 `-1.2`，所有含范围的忠实改写被硬拒（E1）；`CDM-like` 产出缩写 `CDM-`（E2；v0.37.1 把这个现象记成 disposition 而没有修正则）；Unicode 减号被丢、`1.5e-3` 的指数符号被丢、`M200` 里的 `00` 成受保护数字（E3）；集合比较对否定词的位置与个数不敏感，`not` 从一个从句挪到另一个从句可以通过门（E12）。
3. **`rewrite_reward` 在没有可选 `voice_model.joblib` 时直接 exit 2**（高）。de-ai Pass 3 与 condense 把它当强制门，但确定性保真检查被一个 sklearn/joblib 制品挡在门外；新克隆或没训练学习模型的 profile 上整条流程不可执行（H1）。
4. **省略 `--field` 时 5 个工具以 TypeError 崩溃**（deai_anchoring / docstructure / voice / partition / fetch_arxiv_abstracts），`rewrite_reward` 报成 "execution failed: TypeError"，而它们共享的 `--help` 文本承诺 "auto-detected when only one exists"；`axis_main` 系工具既不探测也不报错，直接把轴标成 unmeasured（M、B1、C1、C2、D3、E9、H2）。
5. **静默零发现**（违反 CLAUDE.md 第 3 条）。anchoring 在 n=30、k≥2 时 p 值下界 1/31 > α/k，永远不可能出 finding 却报 `measured`（B5）；salience 在没有任何 bucket 能在 gate 之上分辨时报 `measured` 且零 finding（C10）；无 section 或题目式 section 的文档落入 `unknown` bucket，逐 bucket 轴整篇跳过仍报 `measured`（C13）；structure 对 baseline 里没有的 bucket 报 `measured`（B6）；`--journals` 在 `--fulltext` 本地捷径下被静默忽略（D1）。
6. **quantile 网格整体偏一位次序统计量**：`quantiles(range(100))["0.9"]` 是 90，即 P(X≤x)=0.91；在 30 单元下限处 "p10" 实际是 0.133、"p90" 是 0.933（C12）。逐 bucket 轴的名义操作点在样本最小的 bucket 上偏差最大。
7. **condense_map 的 carve-out 只看副本一侧**：摘要在正文之前时，正文句被列为可删 restatement、摘要被指为 canonical home，与 skill 规则相反并进入默认缩减目标（A11）；否定/数字守卫单向（A12）；map 的 `removable_words` 计入 `[math]`/`[CITE]` 占位符而 gate 不计，默认目标可能不可达（A13）。
8. **L0 词表两处失配**：`paved` / `showcased` 在 SKILL 表和 grep 里有、在 `TIER_A_PATTERN` 里没有（F9）；"段首"规则按物理行而非段落判定，一句一行的 LaTeX 里句中 `Notably,` 成 L0 目标，合并成一行则不报（F4）。
9. **verify_references**：注释里的 `% \cite{x}` 触发 integrity_blocker 并 exit 1（F1）；`http.client.HTTPException` 逃逸成 traceback（F2）；`--cache` 把一次 404 永久化（F6）。
10. **文档数字与代码/制品脱节**：validator 11 项检查在两处写成 10（F16 / I11 / G1）；tools/README 与 DISPOSITIONS 仍引用 v0.36.2 之前的 3.1% / 16.7% / AUC 0.246（现为 1.59% / 13.3% / 0.174）；EVALUATION hub 的 L3 行仍是 0.932（现 0.9487）、document-shape 493 篇（制品 507）；README 示例表 salience 4→6 与 examples/README 的 4→3 矛盾（I1–I9、G14–G18）。
11. **skill 层缺门禁**：final-review 收尾时既不快照也不跑 `length_gate` / `deai_residue --before`（标准 §5.3 要求）（H12）；de-ai 自称 diff 规则 "gates the pass" 但流程里从未运行（H13）；paper-review §O 没有 `residue-absence`（H5）；final-review 让子进程读"父进程产出的 references 报告"但父流程没有生成它的步骤（H36）。
12. **`TIER_WEIGHTS`（0.5/0.3/0.2）从未参与任何聚合**，而 style-corpus/README、tools/README、calibrate skill、EVALUATION 都说三层按权重聚合（D15）。

冗余方面：17 个工具残留无用的 `import argparse`（2026-08-26 cli_common 迁移遗留）；train_voice_model / voice_audit / docstructure 各有一批拆分残留的无用 import；4 个测试文件的 `unittest.main()` 写在文件中部；三份 40 行工具注册表已互相不一致；hedging 单位理由在 7 处重讲、salience 投影缝在 8 处重讲（§5）。

## 2. 主会话第一方复现

以下每一行都在本机重跑过；`tools/` 通过 `sys.path.insert(0, "tools")` 导入。

| 编号 | 调用 | 观察 | 结论 |
|---|---|---|---|
| A1 | `length_gate.py after.tex --before missing.tex` | 表格 `Methods 0 → 5 GROWTH`，一条 strong `length-growth`，exit 1，stderr 为空 | 缺失基线被当成 0 词的测量结论 |
| A3 | `required_shrink_words(parse_required_shrink("7%"), 100)` | 8（应为 7）；`14%` × 50 → 8 | 浮点 `ceil` 多要一个词 |
| A4 | git 仓库：HEAD 有 `main.tex`（含 `\input{body}`）和 10 词的 `body.tex`；工作区删掉两者后 `read_git_document(main.tex, "HEAD")` | 返回 `'\section{Methods}\nRoot prose here.\n\input{body}\n'`，子文件未拼入；`--git-ref HEAD --require-shrink 5` → "removed 2 words of the 5 required (4 -> 2)"，exit 1 | 子文件按工作区而非 ref 解析 |
| A5 | `es.prose_words(r"We have \[ E = m c^2 \] here.")` | 9 个 token，含 `\[`、`E`、`=`、`c^2` | `\[...\]` 不是数学区 |
| A6 | `es.latex_to_plain("First $$x=1$$ prose words survive here $y$ end.")` | `'First $ [math]  [math] y$ end.'` | `$$` 吞掉后续散文（numeral 投影不吞） |
| A7 | `lg.section_word_counts("\section{Methods}\nOne two three.\n% \section{Old draft heading}\nFour five six seven.\n")` | `{'Methods': 3, 'Old draft heading': 4}` | 注释掉的标题成了 section |
| A11 | 摘要与 Results 各含同一句 | `condense-restatement` 落在 `results`，`genre_carve_out False`，`canonical_line 1`（摘要），19 词 | carve-out 只看副本一侧 |
| A12 | 同段落先 "is not significant" 后 "is significant" | `condense-restatement` 16 词 | 丢否定词的副本仍算 restatement |
| A13 | 读 `condense_map.py:150` | `n_words = len(clean.split())`，`clean` 来自 `latex_to_plain`，含 `[math]`/`[CITE]` | map 与 gate 计词口径不同 |
| F1 | `refs.bib` + `doc.tex`（含 `% \cite{ghost}`），`fetch` 打桩为离线 | `('reference-missing-entry', 'integrity_blocker')`，exit 1 | 注释里的 cite 成 blocker |
| F3 | `mkdir dir.tex; ai_ism_lint.py dir.tex` | 各轴 unmeasured，exit 0，无错误 | 不可读根文件 = 空文档 |
| F4 | `Notably,` 独占一行 / 与前句同行 | 前者 `tier-a:paragraph-start:notably` exit 1；后者 0 finding exit 0 | 行首 ≠ 段首 |
| F7 | 一行内两个 `---` | 1 条 `em-dash` finding | 按行不按命中计数 |
| F9 | "This paved the way for the fit and showcased the model." | 0 finding，exit 0；`SKILL.md:275` 表列 `pave/paves/paving`、`:344` grep 有 `paved?`/`showcase[sd]?` | linter 漏 `paved`/`showcased` |
| E1 | `rr._numbers("0.5--1.2 arcsec")` | `{'0.5', '-1.2'}`；"between 0.5 and 1.2" vs "0.5--1.2" → `eligible False`, missing `-1.2` | en-dash 范围被硬拒 |
| E2 | `rr._acronyms("a CDM-like model")` | `{'CDM-'}`；"a CDM model…" vs "a CDM-like model…" → 不合格 | 尾连字符进缩写 |
| E3 | `rr._numbers("a bias of −0.06 dex")`；`1.5e+3` vs `1.5e-3`；`_numbers("M200")`；`_units("M200c")` | `{'0.06'}`；eligible True；`{'00'}`；`{'c'}` | 符号丢失、标识符中切词 |
| E12 | "not significant at 43 … significant at 512" vs 对调 | `eligible True`，missing/invented 皆空 | 集合比较看不见位置 |
| E7 | `parse_args(["--field","wgl","--corpus-root","/tmp/x","sample"])`（label_findings 的构造方式） | `field=None`，`corpus_root` 为默认值 | 子命令默认值覆盖根解析结果 |
| C12 | `ref.quantiles(list(range(100)))["0.9"]`；n=30 | 90（P=0.91）；`q[0.1]`=3（P=0.133）、`q[0.9]`=27（P=0.933） | 网格偏一位 |
| C3 | `\section{Appendix}\nTODO fix this later.` 经 `body_lines` 后 `edit_meta_findings` | `[]`；同文本放在 `\section{Data availability}` 下 → `['residue-edit-meta']` | `skip` 段落里的编辑标记不可见 |
| C4 | `res.RE_LABEL.findall("\section {No saddle}")` | `[]` | 上次审计 A9 未落到 residue |
| C13 | `ref.units("无标题散文")`、`ref.units("\section{Weak lensing}…")` | bucket 均为 `'unknown'` | 逐 bucket 轴无此 bucket，整篇跳过 |
| D1 | 读 `fetch_arxiv_abstracts._candidate_ids` 本地捷径条件 | `if jsonl.exists() and not exclude and not args.author:`，不看 `journals` | `--journals` 静默失效 |
| D2 | 读 `:399`/`:403` | `range(args.start_at, …)` 配 `min(args.page, args.per_query - start)` | `--start-at 2000` 请求 `max_results=-1600` |
| D6 | `est.paragraph_initial_words("In recent years the field grew.\n\nRecent advances helped.")` | `['In', 'Recent']` | 多词开头短语永远"absent" |
| D7 | `est.words("[CITE] [math] [FIGURE-OR-TABLE]")` | `['CITE', 'math', 'FIGURE-OR-TABLE']` | 占位符计入词数与词表 |
| D15 | `grep` 所有含 `weight` 的行 | 没有任何一行把权重乘进聚合 | `TIER_WEIGHTS` 是死常量 |
| H1 | `rewrite_reward.py --field wgl --reference r --candidates c` | `[rewrite_reward] no voice_model.joblib in …/style-profile/wgl`，exit 2 | 可选模型成硬前提 |
| H5/H12/H36 | `grep` paper-review §O、final-review | §O 列四条规则无 `residue-absence`；final-review 无 `length_gate`/`deai_residue`/snapshot；`verify_references` 只出现在子进程提示的一个 bullet（:116） | skill 层缺门禁 |
| M1 | 每个工具无参数运行 | deai_anchoring / docstructure / fetch_arxiv_abstracts / train_voice_model 出 traceback；给真实文件不给 `--field`：deai_voice / partition 同样 TypeError，rewrite_reward "execution failed: TypeError" exit 2，deai_features 抛 `ModuleNotFoundError: torch` | 见 §3.1 |
| M2 | AST 扫描未用 import / 未引用定义 | 17 个工具 `argparse` 未用；`length_gate` 的 `re`；`extract_sections:21` 的 `tex_macros`；docstructure 的 json/math/random/re/statistics/Iterable；train_voice_model 的 hashlib/math/re/statistics/defaultdict；voice_audit 的 hashlib/json/re/Counter；12 个测试文件的 `sys`、5 个的 `Path` | 见 §5 |
| M3 | 全部 43 个 markdown 文件的相对链接 / `tools/*.py` / `skills/*` 引用解析 | 唯一失败：`codex-review-2026-09-04.md` 有 16 个 `D:/Projects/sci-paper/...` 本机绝对路径链接 | 对其他读者是死链，且泄露本机路径 |
| M4 | `grep -rn latency.json` | 无任何 py/md/yml 引用 | 孤儿文件，且与 README 延迟行不一致（G19） |

## 3. 缺陷清单（按区域）

列内"位置"为 `文件:行`；"建议"是最小改法。状态见 §0。

### 3.1 CLI 与退出码契约（横跨多个工具）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| M1 / B1 / C1 / D3 / E9 | 中 | 已复现 | deai_anchoring.py:271, deai_docstructure.py:406, deai_voice.py:247, deai_partition.py:234, fetch_arxiv_abstracts.py:318/370/621, rewrite_reward.py:477, train_voice_model.py:85 | `args.profile_root / args.field` 在 `--field` 缺省时是 `Path / None` → TypeError traceback（exit 1）；`--help` 承诺自动探测。只有 8 个工具经 `cli_common.resolve_field` | 统一走 `resolve_field`（或新增不抛异常的 `resolve_field_dir`），缺省且无法唯一解析时 exit 2 |
| C2 | 中 | 已核实 | cli_common.py:120；影响 register / collocation / discourse / salience | `axis_main` 从不自动探测单字段：无 `--field` 时 `field_dir=None`，轴报 "baseline is unavailable" 的 unmeasured，尽管 baseline 存在 | `axis_main` 内用 `list_fields` 唯一时自动选，否则报错 |
| F12 / F34 | 低-中 | 已核实 | ai_ism_lint.py:83-91, 507-512；cli_common.py:15-19；tools/README.md:47 | 多字段且无 `--field` 时 `resolve_field` 静默返回 None，所有校准轴 unmeasured，stderr 为空；文档说它 "warns and returns None" | 多字段分支打印一行 stderr；改文档措辞 |
| C8 | 低 | 已核实 | cli_common.py:121-126；deai_register.py:641；deai_reference.py:366 | `--calibrate --field 不存在` 抛 FileNotFoundError（exit 1）；`--field` 指向空目录则写出空制品并报成功；`deai_collocation --calibrate --glossary` 静默忽略 `--glossary` | `axis_main` 检查 `field_dir.is_dir()` → 2；无记录时 `summary` 返回 2；`--glossary` 走 argparse |
| C6 | 低 | 已核实 | deai_residue.py:537-541 | `--output` 不可写抛 FileNotFoundError，exit 1（"有 strong finding"的码） | 写文件放进 try，OSError → 2 |
| B8 | 低 | 已核实 | deai_docstructure.py:404；deai_docshape.py:320-330 | `--strong-percentile 1.5` → IndexError exit 1；负值外推 | `main` 校验 0<p<1 |
| A8 | 低 | 已核实 | condense_map.py:291-293, 453 | `VERBOSE[match.group(0).lower()]` 对 `İn order to` 抛 KeyError（`re.I` 匹配到而 `.lower()` 展开成不同键），traceback exit 1 | `VERBOSE.get(...)`，缺失即 continue |
| B4 | 中 | 已复现 | deai_features.py:97-112, 179, 371-389；deai_oracle.py:84 | `corpus_centroid` 在检查 `.npy` 前 `import numpy`；`paragraph_features` 无条件 `import torch`；CLI 直接 ModuleNotFoundError。README 行说"缺依赖时降级" | 先查文件再 import；UID 块以 `model_runtime_available()` 守卫，缺失给 `unmeasured` 标记而非 0.0 |
| M5 | 低 | 已复现 | train_voice_model.py:77 | 无 numpy 时裸 ModuleNotFoundError traceback（train_ai_ism_classifier 同类情况给的是消息 + exit 1） | 捕获 ImportError，打印安装提示，exit 2 |
| M6 | 低 | 已复现 | build_profile / eval_docscale / eval_findings / extract_style / train_ai_ism_classifier | 配置缺失时 exit 1 + 消息；linter 契约用 2 表示配置无效。标准 §0.1 对 advisory 工具只说 "nonzero"，合规但不一致 | 统一为 2 或在 §0.1 写明 |
| D14 | 低 | 已核实 | extract_style.py:636, 648-651 | 发现语料为空之前已 `mkdir` profile 目录，失败后留下空字段，其他工具的 `resolve_field` 从此报 "Multiple fields" | 把 `mkdir` 移到空语料返回之后 |
| E10 | 低 | 已核实 | label_findings.py:382, 404 | `score --recheck 不存在的文件` 报 "no --recheck sheet supplied" | 给出文件不存在的 SystemExit |
| C21 | 低 | 已核实 | deai_collocation.py:465-470；cli_common.py:101-132；deai_oracle.py:286-309 | `--glossary` 由手工从 argv 里剔除，绕过 argparse；`--field` 在 axis_main / oracle / voice 三种解析方式后面只有一条 help 文本 | `axis_main` 加 `extra_arguments` 钩子；一处解析字段目录 |

### 3.2 length_gate / condense_map / tex 装配（A）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| A1 | 高 | 已复现 | tex_assembly.py:99-103, 117-119；length_gate.py:260-266, 287 | `--before` 文件不存在 → 基线全 0 → 每节 GROWTH，exit 1 而非 2 | `main` 里 `is_file()` 校验；`read_tex_document` 对根文件不可读抛 OSError（子文件才允许"留在原地"） |
| A2 | 中 | 已核实 | 同上 | `after` 是目录时被读成空 → 视为全部删除，exit 0 | 同 A1 |
| A3 | 中 | 已复现 | length_gate.py:203-204, 212-219 | `ceil(0.07*100)` = 8；7/14/17/27/28/34/54/55/56/68/81% 在 ≤1000 词基线上多要一个词 | 用 `Fraction` 精确计算，或 `ceil(round(x, 6))` |
| A4 | 高 | 已复现 | tex_assembly.py:57-66, 86-93, 123-147 | `read_git_document` 只换了读取函数，子文件仍按工作区 `is_file()` 解析；ref 里存在、工作区已删的 `\input` 子文件从基线消失 | 给 `assemble` 注入 `resolve` 回调；git 路径下用 `git cat-file -e ref:path` 解析 |
| A5 | 中 | 已复现 | extract_sections.py:97-100 | `\[...\]`（及 `subequations`）不在 `RE_TEX_DISPLAY_MATH`，其 token 计为散文；README 说"数学不计入" | 加 `\\\[.*?\\\]`、`subequations` |
| A6 | 中 | 已复现 | extract_sections.py:100 | `\$[^$]+\$` 把 `$$…$$` 的第 2、3 个 `$` 配对，吞掉后续散文直到下一个行内公式；numeral 投影不吞，两投影不再同构 | 行内匹配前先匹配 `\$\$.*?\$\$` |
| A7 | 中 | 已复现 | length_gate.py:52-58；deai_metrics.py:118-126；extract_sections.py:433 | 注释掉的 `% \section{…}` 生成幽灵 section；condense_map 走 `document_source` 会先去注释，两工具分节不同 | 分节前 `blank_preserving(text, RE_TEX_COMMENT)` |
| A9 | 低 | 已核实 | tex_macros.py:31-34, 60-65；README.md:580 | 带参数宏若 body 是纯数字仍被展开（注释说 "rejected below"，实际无人拒绝）：`\foo{x}` → `42{x}` | 捕获 `(\[\d+\])?` 组，命中即原样返回 |
| A10 | 低 | 已核实 | tex_assembly.py:60-62 | `\input{fig.tikz}` 被强制成 `fig.tex` | 先按原名找，无后缀再补 `.tex` |
| A11 | 高 | 已复现 | condense_map.py:172-193 vs :348；deai_reference.py:236-238 | carve-out 只看副本 bucket 不看 home bucket；摘要总在前，于是正文句被列为可删并计入 `default_target_words`，与 skill 规则 4 相反 | `carve = record 或 home 任一在 CARVE_OUT_BUCKETS`，或选第一个非 carve-out 的 home |
| A12 | 中 | 已复现 | condense_map.py:170-173 | 守卫是 `record["invariants"] <= home["invariants"]`：副本多出 `not`/数字被放过，副本少了则仍算 restatement | 改为相等 |
| A13 | 中-高 | 已复现 | condense_map.py:150, 179, 218, 337, 351 vs length_gate.py:45-49 | `removable_words` 计入占位符，gate 不计；skill 让人用 map 的目标喂 `--require-shrink`，完全执行后仍 NOT MET | 用 `RE_PLACEHOLDER` 过滤后再计数 |
| A14 | 低 | 已核实 | condense_map.py:406 vs length_gate.py:42-49 | map 分母含标题词，gate 不含 | `prose_words(RE_HEADING_COMMAND.sub("", text))` |
| A15 | 低 | 已核实 | condense_map.py:92（deai_register.py:124 同模式） | `\(([A-Z][A-Za-z0-9]{1,9})\)` 把 `(Gaussian)` 当缩写报 dead acronym | 要求 ≥2 个大写 |
| A16 | 低 | 已核实 | condense_map.py:85-87 | `\subref`/`\vref`/`\fref` 不算引用 → 假 dead figure | 按形状 `\\[A-Za-z]*ref\*?\{` 匹配 |
| A17 | 低 | 已核实 | condense_map.py:89 | `\caption*` 与两层嵌套 caption 得 `removable_words 0` | `\\caption\*?` + 第二层嵌套 |
| A18 | 低 | 已核实 | tex_assembly.py:86-93 | 嵌套 `\input` 相对子文件目录而非根目录解析，LaTeX 相反 | 递归时传根目录 |
| A19 | 低 | 已核实 | tex_assembly.py:41 | `RE_TEX_INCLUDE` 无名字边界：`\includegraphics`/`\inputminted` 被当 include | `\\(?:include\|input)(?![A-Za-z])` |
| A20 | 低 | 已核实 | tex_assembly.py:120, 147；tex_macros.py:67 | 注释掉的 `% \newcommand{\Nf}{63}` 仍被采集为宏定义 | 在去注释副本上采集 |
| A27 | 中 | 已核实 | skills/condense/SKILL.md:78-80 | 基线配方 `cp <file> <scratch>/length-baseline.tex` 对多文件文档失效：副本解析不到 `\input` 子文件，基线≈0 词，每节都 GROWTH | 改成 `cp -r` 整棵 include 树或用 `--git-ref` |
| A28 | 中 | 已核实 | skills/condense/SKILL.md:128-134；length_gate.py:205-206；tests/test_length_gate.py:182 | map 目标为 0 时 `--require-shrink 0` exit 2（测试还钉住了这个拒绝），skill 的收敛步骤无法门禁 | 接受 0 为"不要求缩减"，或 skill 在目标为 0 时省略该 flag |

### 3.3 ai_ism_lint（F）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| F3 | 中 | 已复现 | ai_ism_lint.py:357-360；tex_assembly.py:98-119；deai_residue.py:520-521 | 不可读的 `.tex` 根文件（目录、无权限）被当空文档：L0 `measured`，exit 0；同输入 `.md` 则 exit 2 | `document_source` 用会抛错的 `read_text` 读根文件 |
| F4 | 中 | 已复现 | ai_ism_lint.py:40-46, 183, 201, 208-216 | "段首"连接词/开头模式用 `^\s*` 按物理行判定，还带 `(?i)`；一句一行时句中 `Notably,` 成 L0，硬折行的小写 `importantly,` 也是；同时 `It is worth noting` 在行中被漏 | 只在 `paragraph_line_ranges` 每段首行上判，去掉 `(?i)`；开头短语按句首 `finditer` |
| F9 | 中 | 已复现 | ai_ism_lint.py:34-39；skills/paper/SKILL.md:274 vs :344 | `TIER_A_PATTERN` 缺 `paved`、`showcased`；SKILL 表与 grep 两种拼法 | `paves?\|paved\|paving`、`showcases?\|showcased\|showcasing`；表与 grep 对齐 |
| F7 | 低 | 已复现 | ai_ism_lint.py:184-190 | em-dash 用 `search` 每行一条；标准说"每个命中"；examples/README 钉住的计数偏少 | `finditer` |
| F14 | 低 | 已核实 | ai_ism_lint.py:191-200 | 词法规则扫原始源：`\ref{sec:realm}`、`\label{…}`、`\cite{delve-2020}` 里的键成 L0 目标 | 先把 `\label/\ref/\cite*/\url` 参数区置空 |
| F15 | 低 | 已核实 | ai_ism_lint.py:171, 221, 257-273；skills/paper/SKILL.md:291 | Tier B 上限按 heading 单元（含 subsection）计，SKILL 说按 section | 以外层 `\section` 为键，或 SKILL 改口 |
| F18 | 低 | 已核实 | ai_ism_lint.py:54 | `THREE_PARALLEL_PATTERN` 无词边界，`Bland` 里的 `and` 命中 | `\b(?:and\|furthermore\|moreover)\b` |
| F19 | 低 | 已核实 | ai_ism_lint.py:100-104 | `lexicon.json` 非法 JSON 被吞 → 零条 corpus-zero 且 `measured`；list 形状却 exit 2 | 让 JSONDecodeError 传出去（2）或给轴 unmeasured |
| F20 | 低 | 已核实 | ai_ism_lint.py:33, 72, 238, 357-358 | `.md` 输入：YAML front matter 的 `---` 成 em-dash 目标，`%` 被当注释 | 声明只支持 `.tex`，或非 `.tex` 跳过 front matter 且不用注释规则 |
| F25 | 低 | 已核实 | ai_ism_lint.py:156；deai_feedback.py:48-57 | 同一行同一规则两次命中 → 相同 `finding_id`（目前无人按 id 去重，潜伏） | evidence 加 `match.start()` |
| F26 | 低 | 待核实 | ai_ism_lint.py:47-51, 257-273 | Methods 讲 robust estimator 的段落永远无法 exit 0，SKILL:298 又说不能牺牲准确性 | 技术二元组白名单或 `% lint: allow <word>` |
| F27 | 低 | 已核实 | ai_ism_lint.py:67-72, 238 | `TRAILING_COMMENT_PATTERN` 对 `.tex` 已死（`document_source` 先去注释），注释文字过时；对非 `.tex` 反而有害（F20） | 删除 |
| F33 | 低 | 已核实 | ai_ism_lint.py:439, 478-479；skills/de-ai/SKILL.md:111；train_ai_ism_classifier.py:246 | `--summary` 是 no-op，仍被 skill 与工具提示引用 | 调用方去掉后 `help=SUPPRESS` 或删除 |

### 3.4 verify_references（F）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| F1 | 高 | 已复现 | verify_references.py:387-403, 451-453；tex_assembly.py:69-97 | `cross_check` 扫的装配文本含注释，`% \cite{ghost}` → `reference-missing-entry` integrity_blocker，exit 1 | `cite_keys(RE_TEX_COMMENT.sub("", text))` |
| F2 / F32 | 中 | 已核实 | verify_references.py:173-185, 464-478 | `http.client.IncompleteRead`/`BadStatusLine` 不是 OSError，逃逸成 traceback exit 1；except 元组里 `URLError`/`TimeoutError`/`JSONDecodeError`/`UnicodeDecodeError` 反而是多余的子类 | `fetch` 加 `HTTPException`；`main` 兜底 `except Exception → 2` |
| F5 | 中-低 | 已核实 | verify_references.py:86-104 | `#` 拼接或 `\"` 转义引号之后的字段全部丢失，DOI 丢了就报 "no identifier" | 支持 `#` 循环；引号值按深度扫描；未解析尾部抛 ValueError |
| F6 | 中 | 已核实 | verify_references.py:343-360, 438-450 | `--cache` 把 404 存成 `null` 永不重查；索引滞后的 DOI 每轮都是 blocker，且 finding 不说来自缓存 | 不缓存 None（或带时间戳 N 天后重查）；`observed` 加 `record_source` |
| F8 | 低 | 待核实 | verify_references.py:190, 194, 225, 228 | `date-parts: [[]]` 等形状 → IndexError traceback | 防御取值 + `main` 兜底 |
| F10 | 中-低 | 已核实 | verify_references.py:265-266 | 第一作者子串匹配：`li`⊂`lin`、`ma`⊂`mandelbaum`、`he`⊂`heymans` 静默通过 | 按 token 比较，或子串分支要求 ≥4 字符 |
| F11 | 中 | 已核实 | verify_references.py:60, 387-389 | `RE_CITE` 只认 `\cite*`：`\nocite`、biblatex `\parencite`/`\textcite`/`\autocite`、`\cites{a}{b}` 的第二组都看不见 → 假 `reference-uncited`、漏 missing-entry | 扩展命令名与重复 `{…}` 组；`\nocite{*}` 视为全引；或声明不支持 biblatex |
| F13 | 低 | 已核实 | verify_references.py:107-119, 283-288 | `@string` 被跳过但不展开，`journal = aap` 与记录字面比较 → 假 mismatch | 收集并替换 `@string` |
| F21 | 低 | 已核实 | verify_references.py:398 | `--tex` 的 missing-entry finding 永远 `line=1` | 按匹配偏移算行号 |
| F22 | 低 | 待核实 | verify_references.py:45, 173-185, 433 | 无重试/退避，UA 无 `mailto:`（CrossRef polite pool） | 429/5xx 重试一次；可配置 mailto |
| F23 | 低 | 已核实 | verify_references.py:139 | 作者列表只按小写 ` and ` 切分 | `re.split(r"\s+and\s+", …, re.I)` |
| F24 | 低 | 已核实 | verify_references.py:321-327 | 只在 `url` 字段里的 DOI 被忽略 → "no identifier" | 对 `url` 也跑 `RE_DOI_URL` |

### 3.5 rewrite_reward 保真门（E、H）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| E1 | 高 | 已复现 | rewrite_reward.py:48-50 | `_NUMBER_SIGN` 禁止数字后的符号，但 `--` 的第二个连字符前面是连字符，被当负号：`0.5--1.2` → `{0.5, -1.2}`；每个含 en-dash 范围的忠实改写被硬拒 | `(?:(?<![\d.\-+])[-+])?`；`HyphenatedRangeTests` 加 `--`/`---` 用例 |
| E2 | 中 | 已复现 | rewrite_reward.py:53, 258-259 | `[A-Z][A-Z0-9-]{1,}` 允许尾连字符：`CDM-like` → `CDM-`；v0.37.1 把它记为 disposition 而未修正则 | `\b[A-Z](?:[A-Z0-9]\|-(?=[A-Z0-9]))+\b` |
| E3 | 中 | 已复现 | rewrite_reward.py:37-50 | U+2212 不在符号类（`−0.06` → `0.06`，丢负号仍"忠实"）；`1.5e-3`/`1.5e+3` 都切成 `{1.5, 3}`；lookbehind 只排字母不排数字：`M200`→`00`、`z0.5`→`5`、`M200c` 的单位 `c` | 数字体加 `(?:[eE][-+]?\d+)?`；符号类 `[-+−]`；lookbehind `(?<![A-Za-z\d.])`；归一化 `−`→`-` |
| E4 | 中-低 | 已核实 | rewrite_reward.py:76-83, 53/258, 223-227 vs 249-255 | `3rd`→单位 `rd`、`1990s`→`s`；`latex_to_plain` 的 `[MATH]`/`[CITE]` 命中缩写正则；display math 里的数字被收集而行内 `$…$` 不收，同一公式从 display 改 inline 被双重拒绝 | 先剥占位符；绑定单位停用表 `{st,nd,rd,th,s,x}`；行内数字同样收集或 display 数字不进数字集 |
| E12 | 中 | 已复现 | rewrite_reward.py:283-284, 333-361 | 不变量按集合比较：否定词换从句、两处数字互换、丢掉两个否定中的一个都判"忠实" | 用 `Counter` 比多重数；可选按句配对 marker+数字；在 §8 与 de-ai skill 写明剩余限制 |
| H1 | 高 | 已复现 | rewrite_reward.py:477-480；skills/de-ai/SKILL.md:330-345；skills/condense/SKILL.md:116-121 | `load_voice_model` 为 None 即 exit 2；de-ai 与 condense 把它写成强制门并把 exit 2 解释为"输入无效/缺 profile"；calibrate 又说学习模型"never required" | 工具：无模型时 voice 权重 0、`voice_calibrated=False` 继续；skill：写明真实前提与回退 |
| E20 | 低 | 待核实 | deai_features.py:186-195；deai_voice.py:101-112 | centroid 文件缺失时 `corpus_cos=0.0` 无 degraded 标记，学习分仍进 `combined` | `voice_score` 返回 None（权重 0）或 degraded 标记 |
| E30 | 低 | 已核实 | rewrite_reward.py:119-127, 478-480 | `_FORMATTING_MACROS` 缺 `ldots/dots/citeyearpar/citetext`（`\ldots`→`...` 被硬拒）；`{\rm Mpc}` 两种单位形式都不保护；bundle 损坏时也报 "no voice_model.joblib" | 补宏名；损坏与缺失分开报 |

### 3.6 逐 bucket 轴：reference / register / collocation / discourse / salience / residue（C）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| C12 | 低-中 | 已复现 | deai_reference.py:49 | `index = min(n-1, int(q*n))` 取的是第 ⌊qn⌋+1 小的值，P(X≤x)=q+1/n；30 单元下限处 p10/p90 实际为 0.133/0.933，叠加 plateau-top 读法后名义操作率系统偏移 | 最近秩 `ceil(q*n)-1`，并重测受影响的 EVALUATION 比率；或在 tie policy 旁写明偏差 |
| C11 | 中 | 已核实 | deai_reference.py:77-139, 158-207, 302-321 | "一个单位"不变量只是声明：没人读制品的 `unit`，错标/过期制品照读不报；hedging 的手稿 "section" 是单个 heading 跨度（含 `\subsection`），参考侧则是一篇论文同 bucket 全部段落合并，两侧的 section 不是同一个东西 | `usable_buckets` 校验 `unit == expected`；`sections()` 按顶层 `\section`+bucket 合并 |
| C10 | 中 | 已核实 | deai_salience.py:106-116 vs 142-149 | 状态只看 n≥30，检测还要求 `resolves_above_gate`；平坦参考下 `measured` + 零 finding（discourse/collocation 用 `usable_buckets` 没这个问题） | 状态也走 `usable_buckets(…, high=True)`，空则 degraded |
| C13 | 低-中 | 已复现 | deai_metrics.py:162；deai_collocation.py:271-275；deai_salience.py:135-137；deai_discourse.py:315-317 | 无 section 文档或题目式 `\section{Weak lensing}` 落 `unknown`；bank 无此 bucket，逐 bucket 轴整篇跳过而状态（只由 profile 算）仍 `measured` | 状态函数接收文本，有 `unknown` 单元时报 degraded 并给出计数 |
| C3 | 中 | 已复现 | deai_residue.py:426；deai_register.py:335-341 | v0.36.2 把编辑标记扫描改到 `body_lines`，但它连 `skip` 段落一起置空，附录（bucket `skip`）里的 `TODO`/`(removed)` 不可见，strong 门 exit 0 | 标记规则单独投影：只去 preamble 与参考文献 |
| C4 | 低-中 | 已复现 | deai_residue.py:172-174 | `RE_LABEL` 无 `\s*`，`\section {X}`/`\caption {X}` 看不到标签；负标签静态与 diff 规则对这类文件失效 | 镜像 `RE_HEADING_COMMAND` 的 `\*?\s*(?:\[…\])?\s*\{` |
| C5 | 中 | 已核实 | deai_residue.py:329-339, 196-201 | (a) 标签从全文（含 `skip`）采集、正文词表却排除 `skip`，附录 caption 的对象被报"正文未提及"；(b) `stem()` 只剥第一个后缀：`truncation`→`trunc`、`truncated`→`truncat`，同词根被判不同 | (a) 查找用含 `skip`（除参考文献）的散文；(b) 归一 `ation/ated/ating` |
| C7 | 低 | 已核实 | deai_oracle.py:103-106, 134-137 | CUDA 回退处理器对空消息异常 `str(exc).splitlines()[0]` 抛 IndexError；`calibrate` 对空行 `json.loads` 崩溃 | `(… or ["?"])[0]`；跳过空/坏行 |
| C9 | 低 | 已核实 | deai_register.py:77-79 | `\newcommand*` 定义不被 `RE_NEWCOMMAND` 读取，`\AUC` 展开为空、既不计数也不审计 | `\\(?:newcommand\|renewcommand\|providecommand)\*?` |
| C14 | 低 | 已核实 | deai_collocation.py:300-303, 350-356, 456-459, 338-355 | `--glossary`：定义线索正则含裸 `\(`、`, the`（`(Fig. 1)` 也算"已定义"）；线索在句中任意位置都算；状态块用需要 baseline 的 `collocation_axis_status`，有 bank 无 baseline 时 finding 与 "unmeasured" 并列；同一句出现两次不算两次使用 | 线索限定在词对之后的窗口；glossary 专用状态只依赖 bank；按出现次数计或改口"in N sentences" |
| C15 | 低 | 已核实 | deai_collocation.py:227-229；deai_residue.py:204-211 | sentence-scope finding 报的是所在段落的行范围 | 像 `_line_of_pair` 那样定位句子首个实词 |
| C16 | 低 | 已核实 | deai_provenance.py:52-73 | `_paragraphs` 按空行切全文，`\author{…}\affiliation{…}` 块被记为 `ai_untouched` 段落 | 用 `reference.paragraphs(text)`（跳 `skip`） |
| C17 | 低 | 已核实 | deai_register.py:96-100 vs extract_sections.py:100-103；extract_style.py:461-466；deai_reference.py:297 | 手稿侧 `RE_MATH_SPAN` 置空 `\[…\]`、`subequations`，语料侧 `RE_TEX_DISPLAY_MATH` 不含（`\kappa_\mathrm{raw}` 的 `raw` 在语料侧成词）；bank 行只收 30–400 词、手稿侧无此过滤；`record.get(text_key) or record.get("text")` 逐行静默混投影且制品不记 `text_key` | 见 A5；制品记录 `text_key` 与回退行数并在校准时警告；在 EVALUATION 写明 30–400 词带的不对称 |

### 3.7 文档级轴：docshape / docstructure / partition / anchoring / structure / metrics（B）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| B5 | 高 | 已核实 | deai_anchoring.py:49, 146-159, 199-213, 173-185 | conformal p 的下界是 1/(n+1)；n=30 时 0.032 > α/k（k=2 时 0.025），任何文档都不可能出 finding，轴仍 `measured`；tests/test_deai_anchoring.py:147-150 自己写出了这个算术但代码不执行 | 检测时 `1/(n+1) > class_alpha` 的类报 degraded 并跳过；或校准下限提到 `ceil(k/α)` |
| B6 | 中 | 已核实 | deai_structure.py:271-282 vs 322-323 | template finding 的状态由 `baseline and policy` 决定而非 `bucket_reference`；baseline 没有的 bucket（如 `unknown`）报 `measured`，reference 块是 `templated_fraction: None, n: 0` | `measured` 仅当 `human_fraction is not None and policy` |
| B7 | 低 | 已核实 | deai_metrics.py:72-79, 241, 198-213 | `sentence_stats.json` 只有 `unknown` bucket 时 pooled_cv=0，任何 burstiness finding 不可能产生，轴 `measured` | `reference["cv"]` 为空时 degraded/unmeasured |
| B9 | 中 | 已核实 | deai_docstructure.py:92-94, 104-110；deai_docshape.py:288-290, 355-362, 583-592 | 触发规则用 `_percentile ≥ p`（加一秩），但 finding 引用的 `strong_threshold` 与 LOO 假报率用 `_quantile`：文档可以在自己引用的阈值之下被判 strong，LOO 率对应的是另一条规则（约 2×） | 两侧统一为一条规则 |
| B10 | 中 | 已核实 | deai_partition.py:82-102, 203-212；deai_docshape.py:496-549 | 每一步 `n_paragraphs` 变化，跨越 `strata_edges` 时换 manifold，贪心比较的是不同 manifold 上的距离（docshape 的 docstring 明言不可混比）；停止条件用 `conformal_p`、改进条件用原始距离 | 比较 `p_value`，或整个计划钉住起始 manifold 并记录 `calibration_basis` |
| B2 | 中 | 已核实 | deai_partition.py:154-161, 126-135；extract_style.py:135-139 | 模拟 split 用 `" ".join(sentences)` 重接，换行变空格，行尾 `% note` 注释掉后半段，排序与 `distance_after` 算在丢了散文的文本上；"零 token"只对建议成立，不对被评分的状态成立 | 在原始块文本的句边界偏移处切分，保留换行 |
| B3 | 中 | 已核实 | deai_partition.py:67-72；extract_sections.py:163-165 | 只有 `\section` 块被标 fixed，`\subsection`/`\chapter` 块成为 merge/split 候选 | `fixed = bool(RE_HEADING_COMMAND.match(block.lstrip()))` |
| B11 | 低 | 已核实 | deai_partition.py:84-87 vs deai_docshape.py:183-198 | partition 不套 `MIN_SECTIONS`/`MIN_PARAGRAPHS_PER_SECTION` 过滤，两工具对同一文档的起始距离不同 | 复用 `document_shape` 的过滤 |
| B12 | 中 | 已核实 | deai_docshape.py:178-180 | `document_shape` 用 `section_line_ranges` 丢掉 bucket，Acknowledgments/Appendix/References（`skip`）作为正文进入分散度、role coupling 与 section arc，校准与检测两侧皆然 | 用 `section_units` 并跳 `preamble`/`skip`；随后重建 baseline |
| B13 | 低 | 已核实 | deai_anchoring.py:95-102, 110-114 | 句子扫描跑在原始 LaTeX 上：标题与第一句粘连，`thebibliography` 整块粘到末句并被年份"锚定"（Conclusions 率 0.0→0.2） | 用 `deai_reference.sections()` 的正文并跳 `skip` |
| B14 | 低 | 已核实 | deai_structure.py:312-351 | `structure-auxiliary` 消息无条件写 "rare in the field reference"，即使参考分数是 40% | 措辞中性或按分数分级 |
| B15 | 低 | 已核实 | deai_structure.py:41 | `RE_TRICOLON_WRAP` = `\bthese\s+(COUNT)\s+\w+` 匹配任何 "these two samples"，且进 `template_score` 与 manifold | 要求句首或后接 `together/define/form…`；改后需重校准 |
| B16 | 低 | 待核实 | deai_metrics.py:238-244；extract_style.py:289-320 | 单节 CV 与跨论文合并的 bucket CV 比较，比值系统偏低，`burstiness_ratio=0.60` 吸收了未知偏差 | 按 (paper, bucket) 校准节内 CV 分布，或在常量旁写明 |
| B17 | 低 | 待核实 | deai_docshape.py:630-637 | Mondrian 分层边界用含校准集的全体文档拟合，严格可交换性要求只用训练集 | 边界只从 `train_records` 算 |
| B18 | 低 | 待核实 | deai_docstructure.py:137-138；deai_docshape.py:570-571, 600-613 | 无 manifold（<55 篇）时逐特征 uniformity/overdispersion 一律 strong，哪怕 baseline 只有 3 篇 | 低于文档数下限降为 ordinary/degraded |

### 3.8 语料、抓取与检索（D）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| D1 | 高 | 已复现 | fetch_arxiv_abstracts.py:370-391, 422-424, 464 | `--fulltext` 且本地 `human_abstracts_extra.jsonl` 存在时走本地捷径，捷径不看 `journals`；calibrate skill §2 的 "refereed" 广度语料实际不受期刊限制，无警告。docstring 说期刊信息"只在线上路径可得"已过时（记录带 `journal`） | 本地分支加 `if journals and record.get("journal") not in journals: continue`，或有 `journals` 即走线上路径 |
| D2 | 中 | 已复现 | fetch_arxiv_abstracts.py:399-404 | 页大小 `min(args.page, args.per_query - start)` 用绝对偏移，`--start-at 2000`（held-out-labels §17.1 的文档做法）每次请求 `max_results=-1600` | `min(args.page, args.start_at + args.per_query - start)` |
| D4 | 中 | 已核实 | fetch_arxiv_abstracts.py:405-409, 477-483, 513-515 | 全文路径遇 429 `Throttled` 只 `break`，打印 DONE、exit 0；摘要路径才有 TRUNCATED + exit 2；tools/README 未区分 | 把 `throttled` 标志带出 `_candidate_ids`/`fetch_fulltext`，TRUNCATED + 2 |
| D5 | 中 | 已核实 | fetch_arxiv_abstracts.py:573-581, 341-453, 435-436, 591-593 | `--updated-before`（README 称"唯一能给文本定年代的控制"）在 `--fulltext` 下无效；`--query-set/--out-name/--resume` 同样被接受但忽略 | 线上候选循环里套 `updated` 检查，设了该 flag 时拒绝本地捷径；其余三个与 `--fulltext` 互斥报错 |
| D6 | 中 | 已复现 | extract_style.py:125-129, 146-166, 354-361 | `paragraph_initial_words` 只记第一个字母串，五个多词开头短语（"In recent years" 等）永远落在 `blacklist_absent_from_corpus`，dossier §3 写它们"absent" | 对去空白段落用 `startswith(phrase)`，或从集合里删掉短语 |
| D7 | 中 | 已复现 | extract_style.py:142-143, 258-266, 462 | `words()` 把 `[math]`、`[CITE]`、`[FIGURE-OR-TABLE]` 当词：抬高句长、`n_words`（em-dash 分母）、词表 top-50，25 词 + 5 个引用的段落也够 `EXEMPLAR_MIN_WORDS` | `analyse_paper`/`write_exemplar_bank` 先剥占位符（`words()` 本身被 salience/partition 共用，别改） |
| D8 | 低 | 已核实 | extract_style.py:169-170, 264 | `count_em_dashes` 在投影后的文本里找 `\textemdash`，而 `RE_TEX_SIMPLE_CMD` 已把它删掉 | 在去注释的 `sec_raw` 上计数 |
| D9 | 低 | 已核实 | extract_style.py:350, 364, 552-553 | 空 counter 的 `n_paragraphs` 报 1，dossier 的"No paragraphs detected"分支不可达 | `sum(counter.values())`，除法处才 `or 1` |
| D10 | 低 | 已核实 | extract_style.py:142-143, 132 | `words()` 只认 ASCII：`naïve Poincaré` → `na/ve/Poincar`；句末 lookahead 同样 ASCII | Unicode 字母类 |
| D11 | 低 | 已核实 | extract_style.py:466 | bank 行 `id` 按 bucket 重置，`paper.tex:p0` 重复（今日无人读 `id`） | `f"{source}:{sec}:p{idx}"` |
| D12 | 低 | 已核实 | fetch_arxiv_abstracts.py:278-288 | `_tex_members` 要求字面 `\documentclass`（1995 年前的 `\documentstyle`、注释开头的源被丢）；同名成员 `appendix/intro.tex` 覆盖 `sections/intro.tex` | 用 `RE_TEX_DOC_MARKER`；同名成员去歧义 |
| D13 | 低 | 已核实 | fetch_arxiv_abstracts.py:205, 415-419, 470-474 | 续传/去重按带版本号的 id：论文出新版后被再下一份 `…v2` 并列 `…v1` | 目录与 `seen` 用 `_bare(id)` |
| D15 | 中 | 已复现 | extract_style.py:63, 289-296, 332-379, 484-501；style-corpus/README.md:26-29；tools/README.md:12；skills/calibrate/SKILL.md:58,65；EVALUATION.md:99 | `TIER_WEIGHTS` 只被打包进元组，从不参与任何聚合；五处文档说按 0.5/0.3/0.2 加权 | 实现加权均值与分位数，或把五处改成"记录权重，未应用" |
| D16 | 中 | 已核实 | extract_style.py:94-96, 460-461, 155-156 | 以占位符开头的段落（`\citet{X} showed…`、`$\Lambda$CDM predicts…`、公式后接散文）被整段排除出 bank 与开头统计，docstring 说只排"纯占位符段落"；intro bucket（hedging 唯一校准的 bucket）系统性缺少引用开头的段落 | 只在剥掉占位符后为空时跳过；开头词取剥占位符后的首词 |
| D17 | 低 | 已核实 | extract_style.py:246-248, 447-448 | `.txt` 与无 `\section` 的 `.tex` 全落 `unknown`，进统计但不进 bank；dossier 的 "No sections detected" 提示不可能触发 | 文档写明 `.txt` 只用于统计，或按文件警告 |
| D18 | 低 | 已核实 | extract_style.py:233-241, 672-675, 515-518 | 缺 pymupdf 跳过的 PDF 只在 stderr 留一行，dossier 的 "Built from N papers" 不含它们 | dossier 头与最终汇总打印跳过数 |
| D19 | 低 | 已核实 | retrieve_exemplars.py:168-180, 197-200 | 关键词回退在 `--topic` 为空时返回前 k 行、分数 0 | 回退按 `(topic or section)` 打分 |
| D20 | 低 | 待核实 | retrieve_exemplars.py:93-127 | `.npy` 缓存只按 mtime 顺序与行数判有效，同行数重建后可能位置错位（voice_dataset 的缓存有指纹，这个没有） | sidecar 记录 bank 大小与 sha1 |
| D24 | 中 | 已核实 | fetch_arxiv_abstracts.py:83-145, 237-245, 292-293；skills/calibrate/SKILL.md:41-42, 72-79 | 抓取器写成字段通用，实则硬编码 astro-ph/弱引力透镜查询与关键词过滤，无 `--query`；`condmat` 用户按 §2 操作会把弱透镜论文装进自己的语料 | 查询集标 `[WGL]`，加 `--query/--queries-file`，非该字段拒绝关键词捷径 |

### 3.9 评估、标注与学习模型（E）

| 编号 | 严重度 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|---|
| E7 | 中 | 已复现 | label_findings.py:408-415；cli_common.py:54-68 | 根解析器与每个子解析器都注册 `--field/--profile-root/--corpus-root`，argparse 用子解析器默认值覆盖根解析结果：`--field wgl --corpus-root X sample` 以 `field=None` 和默认语料根运行，无报错 | 根只用 `base_parser`，或子解析器副本 `default=SUPPRESS` |
| E13 | 中 | 已核实 | label_findings.py:246, 42-44；skills/calibrate/SKILL.md:176-178 | `quota = max(20, n // (2·populations·5))`，文档的 `--n 60`/`--n 240` 都落到 20，实际每 population 出 ≥100 flagged + ≥100 控制行；`--n` 在 <200×populations 时是死参数且无 help | 定义 `--n` 为每格配额，或下限覆盖时警告；改文档数字 |
| E14 | 中 | 已核实 | label_findings.py:253-274, 288-306 | 文档打乱后按发射顺序取一篇的全部 finding 直到配额满，没有每文档上限：20 行的格通常来自一两篇长论文，精度估计是按论文而非按 finding | 先收集全部再 `rng.sample`（或每文档封顶）；汇总里记每格来源数 |
| E15 | 中 | 已核实 | label_findings.py:366-379 | 合并召回把按轴计数的真阳性（一段被三个轴命中算三次）与按段落计数的漏报相加，单位不一致且被多轴命中抬高（上次审计已指出，未变） | 真阳性按 `(source, start_line, end_line)` 去重 |
| E11 | 低-中 | 已核实 | label_findings.py:192-197, 277-279 | 发射器逐篇抛异常被静默吞成 `{"axis", "error"}` 条目并跳过，汇总把它报成"语料只有这么多" | 按轴计数错误并随 shortfall 行打印 |
| E5 | 中-低 | 已核实 | eval_findings.py:152-166, 340-343 | ≥20 篇但 `n_words` 全 0 的 population 报 `measured`、`per_1k_words: None`，`render` 对 None 做 `.3f` → TypeError | 无词即 unmeasured；`_cell` 防 None |
| E6 | 中-低 | 已核实 | eval_docscale.py:97-114 | 人类语料一篇都没评上时 `statistics.median([])` 抛 StatisticsError | 空层 unmeasured；无人类文档时 SystemExit 带提示 |
| E8 | 低 | 已核实 | voice_dataset.py:35-47 | `_load_jsonl` 对空行 JSONDecodeError（`train_ai_ism_classifier.load_positives` 能容忍） | 跳过空行 |
| E16 | 中-低 | 已核实 | voice_dataset.py:107-134, 198-217, 310-315 | 指纹记录 embedder 可导入性，但 `_record_embeddings` 任何运行期失败（离线下载失败）都降成 0 宽行，缓存带着"健康"指纹写出，`corpus_cos` 永远 0 | `embedder_available()` 为真而 `emb.shape[1]==0` 时不写缓存，或把宽度写进指纹 |
| E17 | 低 | 待核实 | eval_findings.py:199-213 vs deai_register.py:621-655 | `leakage_paired` 的本篇 df 用原始空行块子串匹配（含 preamble/参考文献，`halo` 命中 `halos`）而非 bank 的 token 化，抬高 `suppressed_by_own_membership` | 本篇侧同样 `body_only` + `RE_WORD` + 词根规则 |
| E18 | 低-中 | 已核实/待核实 | eval_docscale.py:97-114, 143 | 无文档下限（1 篇也出 `flag_rate`/AUC）；`alpha` 取自 baseline 而 pooled 分支的 `p_value` 是样本内百分位（`alpha=None`），只影响旧 baseline | 共享 `MIN_DOCUMENTS`；用 `point["alpha"]` |
| E19 | 低 | 已核实 | eval_findings.py:293 | `median_words` 偶数 n 取上元素（100/200/300/400 → 300，`statistics.median` 250） | `statistics.median` |
| E21 | 低 | 已核实 | voice_audit.py:513-530 vs 552-556 | 主划分与第一个审计划分同为 `seed+0`，"20 次重复"里含已报告的那次 | 审计从 `seed+1` 起 |

## 4. 逻辑与合理性（横切主题）

1. **静默零发现是一个模式，不是孤例**。B5（anchoring 功效为零仍 measured）、C10（salience 无可分辨 bucket）、C13（`unknown` bucket 整篇跳过）、B6（structure 对无参考 bucket）、B7（metrics 无可用 bucket）、F19（坏 `lexicon.json` 被吞）、F3/A1/A2（不可读文件当空文档）、D1（`--journals` 静默失效）、F12（多字段静默 None）。共同根因：轴状态由 profile 是否存在决定，不由"这篇文档是否真的被测过"决定。建议每个状态函数都接收文本并报告"被测单元 / 总单元"。
2. **投影不对称仍有残留**（上次审计的主题）。语料侧不认 `\[…\]`/`subequations`（A5/C17）、`$$` 只在 plain 投影吞散文（A6）、docshape 与 anchoring 把 `skip` 段落与参考文献当正文而其他轴不算（B12/B13/B22）、partition 评分状态丢注释后散文（B2）、bank 行 30–400 词带在手稿侧没有对应（C17）、map 与 gate 的计词口径不同（A13/A14）。
3. **"一个单位"是声明而非契约**（C11）：制品记了 `unit`，没人读；hedging 的 section 在两侧不是同一对象。
4. **分位数与百分位数的两套读法**：网格偏一位（C12）；docstructure 触发用秩规则、阈值与 LOO 用分位规则（B9）。两者都在样本最小处偏差最大，正是 30 单元下限存在的理由。
5. **保真门的比较代数太弱**：集合比较（E12）、单向守卫（A12）、分词器对符号与标识符的处理（E1–E4）。标准 §6 说"确定性保真测试 + 语义比较"，目前确定性一半在四类常见输入上失效。
6. **贪心搜索跨 manifold 比距离**（B10）：`manifold_operating_point` 的 docstring 禁止的事，partition 每跨一次分层边界就做一次。
7. **标注抽样不是抽样**（E14/E15/E13）：每格通常来自一两篇论文，召回单位混杂，`--n` 基本无效。这三条一起决定 `label_findings` 出的精度/召回目前不可解释。
8. **anchoring 的功效算术**（B5）与 **tier 权重**（D15）都是"文档承诺、代码未做"的同类：前者测试文件里写了算式，后者五处文档写了权重。
9. **`verify_references` 是第四个 exit-1 契约**（H4/I30），标准 §0.1 只登记三个，RESPONSIBILITIES §8 没有它的行；而它 exit 1 的触发条件是 blocker，与 §0.1 "完整性审查不压进 L0 退出码" 的精神相抵。
10. **Tier B 上限按 heading 单元而非 section**（F15）；SKILL 说 "同一 section 最多 1 次"。

## 5. 冗余与累赘

### 5.1 代码

| 编号 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| M2 | 已复现 | build_profile, deai_anchoring, deai_docstructure, deai_features, deai_oracle, deai_partition, deai_personal, deai_provenance, deai_residue, deai_voice, extract_md_negatives, extract_style, length_gate, retrieve_exemplars, rewrite_reward, train_ai_ism_classifier, train_voice_model | 17 个工具 `import argparse` 未用（都改用 `cli_common`） | 删除；在 validator 或 CI 里加一步 pyflakes 类检查（现有 AST 未绑定名检查不覆盖未用名） |
| M2 / A21 | 已复现 | length_gate.py:22, 27+32, 339, 38/60-63 | `re` 未用；两次 `sys.path.insert`；except 元组里 `JSONDecodeError`/`UnicodeDecodeError` 是 `ValueError` 子类；`FRONT_MATTER`/`rest` 不可达（`section_line_ranges` 总覆盖全部行并标 `(preamble)`） | 删除 |
| M2 | 已复现 | extract_sections.py:21 | `import tex_macros` 无引用 | 删除 |
| B20 / M2 | 已复现 | deai_docstructure.py:10-18, 22, 25-26, 31-34；tests/test_deai_docstructure.py:318-329 | json/math/random/re/statistics/Iterable 与 `features`/`metrics`/`structure` 别名未用；四个常量先定义再被 docshape 的 import 覆盖；再导出契约测试因 `getattr(module, "__module__", …)` 对模块对象取默认值而把这些模块名也算进"必须再导出"的集合 | 测试过滤 `types.ModuleType`，然后删死 import/常量 |
| E22 / M2 | 已复现 | train_voice_model.py:21-29, 37；voice_audit.py:17-23；train_ai_ism_classifier.py:30, 38-39；voice_dataset.py:81 | 拆分残留：hashlib/math/re/statistics/defaultdict；hashlib/json/re/Counter；`DEFAULT_PROFILE_ROOT`；`list_fields` 定义未调用；函数内重复 `import re` | 删除 |
| B21 / C18 / D21 | 已核实 | deai_metrics.py:27-28, deai_features.py:43-44, deai_structure.py:23-24, deai_docstructure.py:29-30, deai_register.py:72-73, deai_oracle.py:38-39, deai_voice.py:33-34, build_profile.py:33, retrieve_exemplars.py:32-33, fetch_arxiv_abstracts.py:45, extract_md_negatives.py:51-52 | `REPO_ROOT`/`DEFAULT_PROFILE_ROOT` 各处重定义且未读（`cli_common` 已拥有） | 删除 |
| C18 | 已核实 | deai_reference.py:98-99；deai_discourse.py:264-277, 329；deai_register.py:598, 87-90, 111-116；deai_salience.py:87-90；deai_provenance.py:285-289；deai_voice.py:256 | 不可达分支 `if v_high == v_low`；`measured` 恒为 True 的分支；`min(1.0, count/10)` 在 `count>=15` 下恒 1（floor=5 时代遗留）；`RE_BIBITEM` 冗余；注释描述 v0.36.2 前的顺序；四个别名无人引用；provenance 文本输出重算一遍；`--scores` 用另一套分段导致索引与 finding 不对应 | 逐条删/改 |
| B19 | 已核实 | deai_metrics.py:310-312；deai_structure.py:355-357；deai_feedback.py:302-307；deai_oracle/deai_voice `paragraph_hits` | 兼容元组适配器无调用方（只有一个测试用 `tuple_hits`） | 删除并删测试，或在文档登记为公共 API |
| B22 / B23 | 已核实 | deai_docshape.py:176-194；deai_partition.py:59-75；deai_anchoring.py:107-121；deai_metrics/deai_structure `load_policy`；deai_features/deai_docshape 两个同名不同义的 `_MATH_MARKER_RE`；deai_features `_prose_words`、`re.split` 分段；anchoring 的第三个 section 分类器 | 三个轴各自重做 `deai_reference.paragraphs` 声称"每个轴都读它"的扫描，因此标题不置空、`skip` 不跳、float 不置空；`document_shape`/`document_anchoring` 每次 CLI 算两遍 | 统一消费 `reference.paragraphs/sections`；重建 docstructure/anchoring baseline |
| A22 / A23 / A24 / D21 / D23 / F28 | 已核实 | length_gate.py:67-69（`read_git_version` 一行别名，deai_residue 经它导入）；length_gate/condense_map 重复声明 `--format/--output`；extract_sections.py:286-288 死再导出；extract_style.py:624-630 重造 `field_parser`；`build_profile.list_fields` 与 `cli_common.list_fields` 字节等价；`retrieve_exemplars.VALID_SECTIONS` 手抄 `CLASSIFIED_BUCKETS`；占位符词汇三处编码；ai_ism_lint.py:76-80, 472-477, 503-504 重造 `list_fields`/`utf8_stdout`/`base_parser`/`field_options`/`report_options` | 直接调 `cli_common`/`tex_assembly`/`extract_sections` |
| E23 / E24 / E25 / E28 | 已核实 | eval_findings.py:88-110 ≡ label_findings.py:134-151（文档加载三份）；label_findings 每篇跑两遍发射器、eval_findings 两遍 register、voice_audit 每次 `confound_audit` 重算 4.4 万行的数学密度、train_ai_ism_classifier 两次 5 折；`eval_docscale.rank_auc` 与 `voice_audit._auc` 两套 midrank AUC（注释却说"一个实现"）；eval_docscale 从 retrieve_exemplars 借 `resolve_field`，错误信息署名 `[retrieve_exemplars]` | 合并 |
| F29 / F30 / F31 | 已核实 | validate_plugin.py:628-667（与 test_ai_ism_lint_cli 重复的退出码检查；`_discovered_test_count` 调两次）；tests/test_published_figures.py:98-101 = :111-114（`by_dot`≡`by_n`）；ai_ism_lint.py:337-355 docstring 被 test 逐字复制 | 留一份；memoize |
| M2 | 已复现 | tests：12 个文件 `import sys` 未用，5 个文件 `Path` 未用；两个正则体（`\\[a-zA-Z]+\*?`、`\\(?:begin\|end)\{[^}]*\}`）各在两个工具里重复编译 | 删除 / 共享 |
| A25 / E29 | 已核实 | tests/test_extract_style.py:407-465 与 tests/test_tex_assembly.py:22-29 同名同 docstring 的 `TexDocumentAssemblyTests`（测的是根选择）；`_bundle` 复制三次；train_voice_model.py:39-55 的 13 个私有名再导出只服务于自己的契约测试 | 改名；测试直接 import 拆分后的模块 |

### 5.2 文档与 skill

| 编号 | 位置 | 问题 | 建议 |
|---|---|---|---|
| G27 / G26 / G28 / G29 / G30 | README.md:543-584 ≡ README.zh-CN.md:514-555 ≡ tools/README.md:9-50；plugin.json:4 = marketplace.json:14（1,300 字符逐字相同）；validator 覆盖范围五处三种清单；可选依赖表四处；校准命令两份且互相缺项 | 40 行工具注册表三份，且已互不一致（0.246 vs 0.174、16.7%、3.1%、10 vs 11、"28 of 40" vs "21 of 30"） | tools/README 为注册表，README 只留工具+层+一句话；marketplace 用一行摘要；requirements.txt 为依赖之家；style-profile/README 为校准命令之家 |
| R1 / R2 / R3 / R4 | discourse-and-citation.md:29-59 及六处；held-out-labels.md:192-218 及七处；EVALUATION.md:55-110 + lexical-structure-uid.md:46-97 + narrative-salience-register.md:213-254；held-out-labels.md:131-160 及七处 | hedging 单位理由讲 7 遍；salience 投影缝讲 8 遍；2026-08-25 语料层两轮修复讲 3 遍（hub 56 行历史）；register 假阳性链（0.991→…→0.0371）讲 8 遍（含嵌套 "superseded" 引用块） | 各留一处之家 + 指针；估计省约 115 行 |
| R5–R10 | learned-model.md:46-50 = :126-130；document-scale.md:17-135 vs :448-455 等（同一量三四处）；docs/README + EVALUATION + §18.8 五处描述 `test_published_figures`；EVALUATION.md:170-186 与 DEAI_SUBSYSTEM.md:449-466 的 v0.14.0 发布门历史；DISPOSITIONS 的 Reason 单元格整段复述 §19/§20；DEAI_SUBSYSTEM L4 段复述 §23.4 | 状态文档里的版本历史按 docs/README 的规定应在 CHANGELOG | 估计再省约 105 行，多数落在接近 750 行上限的文件（document-scale 712、narrative-salience-register 614） |
| G31 | README.md:637-638, 718-719, 177-181, 729-734；README.zh-CN.md:704-722；style-profile/README.md:96-113 | Limitations 与 "hard parts" 逐版本复述 CHANGELOG | 表里只留当前值 + § 链接 |
| H23–H30 | skills/paper:394-428 ≡ de-ai:276-290（保留清单，logic/paper-review 再引一遍）；`landscape/demonstrate/significantly` 五处；claim-evidence 三处；de-ai §2 复述标准 §2（同一 `AUC/epoch/accuracy` 例子）；thesis-spine 三处；de-ai/condense 边界段逐字镜像；四个 primitive 各一份四条证据纪律；paper 内 ❌ 列表与表格重复例子 | skill 间约 130 行重复 | 各留一处之家（多数在 de-ai），其他改指针 |
| H45–H51 | paper:226-262（"根本层"复述标准 §1-2）、:162-176（复述 §5.3）；final-review 四处停止条件；brainstorm 四处 no-defer/上限语义 + 两份 flag 表；de-ai §0.1 与 paper-review 三处复述类与停止规则；standard §2 的 panel/L3 证据叙事（§9.8 说证据应在 EVALUATION，而 standard 正卡在 750 行上限） | 不改变 Claude 行为的叙事 | 估计省约 110 行 |
| M3 | docs/audits/codex-review-2026-09-04.md | 16 个 `D:/Projects/sci-paper/...` 绝对路径链接、33 行行尾空白、无末尾换行；I35：Part 1 承诺的逐条 disposition 从未补上（v0.36.2 修了哪些、A10 改名、A11 收窄，无处记录） | 链接改仓库相对路径；补 16 行 disposition 列 |

## 6. 冲突、过时与文档失实

### 6.1 skill 与标准 / 工具

| 编号 | 严重度 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| H12 | 高 | skills/final-review/SKILL.md:203-250；standard:585-591 | 编排者在 §3.7 应用编辑、§4 宣布 disposition-complete，全程无快照、无 `length_gate`、无 `deai_residue --before`；标准说这两个 gate 缺 disposition 时循环不得收尾 | §2 加"首轮编辑前快照"，§3.7 收尾跑两个 gate，§4 加对应条目 |
| H13 | 中 | skills/de-ai/SKILL.md:112-116, 169-182, 308-348, 472-480 | §2 说 diff 规则 "gates the pass"，但 Pass 1 只静态跑 residue，Pass 3 与 §5 都不跑 `--before`；作为改写循环也没有 §5.3 的收尾 length gate | Pass 3 第 5 步或 §5 加两个 gate |
| H36 | 中 | skills/final-review/SKILL.md:112-119 vs :105-108 | 子进程被要求读"父进程产出的 references.json"，父流程没有生成它的步骤（CHANGELOG v0.36.3 说 final-review 每轮先跑） | 加 3.1b 步骤 |
| H5 | 中 | skills/paper-review/SKILL.md:288-293 | §O 列的规则缺 v0.37.0 的 `residue-absence`，动作句仍是 v0.37.1 已替换的"改写优先"形式 | 补规则 + 指向 paper 自检项 5 |
| H3 / I26 | 中 | standard:160-162（正确）vs de-ai:136-141、paper-review:146、RESPONSIBILITIES:53、DISPOSITIONS:57、tools/README:28、DEAI_SUBSYSTEM:127-130 | zero-hit 豁免代码有三类（defined-here / name / derived-form），"cited method's name" 明确不是机械豁免；四处只说词根，DISPOSITIONS 说"词根 + 定义 + 被引方法名"，DEAI_SUBSYSTEM 把两类推给作者 | 全部对齐标准措辞 |
| H4 / I30 | 中 | standard:56-72；verify_references.py:478；DEAI_SUBSYSTEM.md:330 | §0.1 登记"三个例外"，`verify_references` 是第四个（blocker → exit 1）；RESPONSIBILITIES §8 无其行（label_findings 也无，H44） | §0.1 加第四条 + §8 加两行，或改工具 exit 0 |
| H6 | 中 | skills/de-ai/SKILL.md:97-101, 525-526；build_profile.py:11-14 | 新鲜度步骤只让重跑 `extract_style`/`build_profile`（且无 `--field`），六个 `--calibrate` 轴仍是旧参考却报 `measured` | 改为"跑 `/sci-paper:calibrate <field>` §3" |
| H1 / H2 | 高 / 中 | 见 §3.5 | 强制门依赖可选模型；`--field` "auto-detected" 承诺 | 见 §3.5 |
| H14 | 中 | standard:402-412；de-ai:195-198、paper-review:157、physics:119、mainline:72 | 标准把 strong advisory 定义为 measured + 有参考 + 超操作点；四个 skill 按人工判断升 strong | §4 加一句允许"reviewer judgement"为基础，或四处降为 ordinary + priority boost |
| H15 | 中 | skills/physics/SKILL.md:47-48 vs :119 vs :155 | 未标注 schematic 公式：P1 与反模式说 blocker，§4 表说 strong advisory | 表里限定"量纲闭合时" |
| H16 | 中（待核实） | skills/proposal-polish/SKILL.md:98-100, 137-141, 153 | 要求把 hedged 中心假设改为承诺式，同时自绑 §6 的 stance/modality 不变量 | 改为作者审批项 |
| H17 | 中（待核实） | skills/mainline/SKILL.md:10, 45-49；standard:599-601 | 引 §5.4 为权威，又允许多个贡献分支；§5.4 说"exactly one central result" | 加一句"分支必须从属于唯一 thesis line"，七问加 thesis 一问 |
| H18 | 中（待核实） | skills/paper-review/SKILL.md:153-160, 191-193, 386-388；final-review:30-32, 130-155 | `--orchestrated` 只跳 physics/mainline/logic；D 维每轮仍跑 de-ai 审计、G 维仍调 figure-review，父进程又各起一个隔离 agent，重复审计 | `--orchestrated` 也把 D/G 置 SKIPPED_FOR_ORCHESTRATOR |
| H7 / H8 / H9 | 低 | skills/paper/SKILL.md:278 vs :346-347；standard:131-135 vs de-ai:124-127 vs paper:289-299；standard:35 | grep 块把段首 `Importantly/Notably/Interestingly` 标成 Tier B（表与 linter 是 Tier A）；三处对"词表之家"说法不同且无镜像检查；标准称 Tier B 上限"calibrated"，实为常量 1 | 拆 grep；声明 linter 正则为准并加 validator 镜像；改措辞 |
| H10 / H11 / H41 / H43 | 低 | de-ai:104-107；paper-review:288-291 + condense:135-137；proposal-polish:108-111；physics:37 vs figure-review:39-42 | 检索命令缺 `--allow-fallback`（无 sentence-transformers 即报错）；负标签静态规则 400 词下限无 skill 提及；run-in 冒号会被 linter 报却说不适用；两套"权威构建"配方 | 各加一句 |
| H19 / H20 / H21 / H22 / H42 | 低 | calibrate:8 vs RESPONSIBILITIES:37-39 + validator `NORMATIVE_SKILLS`；standard:224 vs :512；paper-review:264-272 vs brainstorm:276-357；final-review:151-152 vs de-ai:183-185；paper-review:436-447 vs :353-354 | calibrate 自称"非规范 skill"而 validator 与 annex 说是；anchoring 一处 L2 一处 L4；同一 12-framing 引擎一处禁 NEEDS-MORE-INFO 一处常设；final-review 期待 `--audit-only` 返回 partition 建议而 de-ai 把它放在 Pass 3；§7 停止语义漏 residue gate | 逐条对齐 |
| H37 / H38 / H39 / H40 | 中 / 中 / 低 / 低 | paper-review:242-250 vs physics:42-79（M.1 复述 P1-P6，违反自身组合规则；K 维单独运行未定义）；paper:15, 196-215（未标 `[WGL]` 的 ML/弱透镜指引）；condense/calibrate/brainstorm/final-review 的 argument-hint 列出正文未定义的 flag；brainstorm `--min-frameworks` 是 no-op，并依赖公共插件不带的 cc-enforcer/FACTS.md/cc-tree | 对齐；标 `[WGL]`；定义或删 flag；外部引用改为可选 |
| H31 / H32 / H33 / H34 / H35 | 低 | standard:9-15（仍标 v3.8 2026-09-04，但 v0.37.0/v0.37.1/v0.38.0 改了三处）；brainstorm:56 叙述已删 flag；paper:164, 280-283, 296-298, 327, 430-440 带日期的来源说明当作现行政策；README.md:77 "35 tools"、:70 `--audit-only` "stops after measurement"（实为 Pass 2 后）；standard §7-8/§11 与两份 annex 头四处讲迁移史，DISPOSITIONS 自身"Adoption requires…"句出现两次 | 升 v3.9 并说明；删旧叙述；来源说明移 ACKNOWLEDGMENTS；改数字；迁移史各留一句 |

### 6.2 证据文档中的数字（I、G）

| 编号 | 严重度 | 位置 | 过时值 → 现值 |
|---|---|---|---|
| I1 / G22 | 高 | EVALUATION.md:123；document-scale.md:147, 194-196, 436-437；DEAI_SUBSYSTEM.md:277 vs :460；README.md:398-416 | document-shape 参考 493 篇（hub、§9 全部操作点 16/493、21/493）与 "14-paper" → 制品 507 篇（v0.36.3 重建），§9 没有重评分记录；README 同时描述 507 制品与 493 时代的判别数字 |
| I2 | 高 | EVALUATION.md:124 | L3 行 0.932 / 0.924 / 0.937 / 32–41% → 0.9487 / 0.9262 / 0.938 / 30–42%（commit 7d5e865 只改了两份 README）；FPR 区间三种写法 |
| I3 | 中 | EVALUATION.md:125-126；DISPOSITIONS.md:47；README.md:720；tools/README.md:30；discourse-and-citation.md:180-181 | cohesion/hedging bucket 计数与转移率 10.87%/7.89% 是 v0.33.0；§19.1/§19.4 现为 6,886/3,228/… 与 10.78%/7.80% |
| I4 | 中 | narrative-salience-register.md:312-325；DEAI_SUBSYSTEM.md:206；DISPOSITIONS.md:59；vocabulary-and-residue.md:5 | register 41,710 / 53,414 → 41,644 / 53,367；摘要占比 33% vs 35% 两处不一 |
| I5 / G20 | 中 | vocabulary-and-residue.md:95-121；DISPOSITIONS.md:59；README.md:480；README.zh-CN.md:438, 695 | collocation 11,286 / 530,677 与旧 bucket 表 → 11,282 / 530,504；hub 的 "7,237 findings" 无出处 |
| I6 | 低-中 | vocabulary-and-residue.md:167-175；EVALUATION.md:119 | §23.3 结构族 n 列是 v0.32.0 bank（3,840/9,512/…），制品现为 3,812/9,478/… |
| I7 / G16 | 中 | DISPOSITIONS.md:57；tools/README.md:28 | zero-hit 2.21 每千词、AUC 0.246 → 3.37、0.174 |
| I8 / G18 / A29 | 中 | DISPOSITIONS.md:62；tools/README.md:23 | condense 中位目标 3.1% → 1.59%（p90 4.11%） |
| I9 / G17 | 低-中 | tools/README.md:24 | residue strong 文档率 16.7% → 13.3% |
| I10 / G15 | 中 | README.md:716；README.zh-CN.md:690 | 稳定性 ρ 0.846 / overlap 0.654 → 0.991 / 0.889（7d5e865 漏改此行） |
| I11 / G1 / F16 | 中 | README.md:666；tools/README.md:50；DEAI_SUBSYSTEM.md:426-440 | "10 checks" → 11；validator 的形状检查正则要求 "contract checks" 字样且不扫 tools/README，所以漏网 |
| G14 | 高 | README.md:390-392 vs examples/README.md:46, 77-81, 100-105 | 示例表 salience-recital 4 → **6**（2026-08-27 读数），examples/README 已改为 4 → 3（v0.36.3）；`test_published_figures` 只钉 examples/README |
| G19 / M4 | 中 | README.md:477；README.zh-CN.md:435；latency.json | 延迟行把 529 个测试与 523 时代的墙钟配对；latency.json 是 v0.36.3 的 516 时代数据、无人引用 |
| I12–I20 | 低 | EVALUATION.md:117, 143, 94；lexical-structure-uid.md:123；narrative-salience-register.md:401-406, 210；projection-and-operating-point.md:237, 273-275, 123；document-scale.md:37-39 vs :95-97 vs :436-437, :113 vs :482, :388 vs :554；held-out-labels.md:47, 226 | 0.2775 vs 0.2776 vs 0.2705；529 个测试标日 2026-09-05（应 09-16）；"104×/85×" floor 倍数是 v0.28.0；UID 0.26–0.58 vs 表 0.26–0.51；"三次重训"已是四次；"pins 39 figures" 现为 61；同一量两套分母/两个 r 值无版本标签；held-out 200 vs 203 未解释；"sit above" 实为 below |
| G2 / G3 / G4 / G5 / G6 / G7 / G8 / G10 / G12 / G13 / G23 / G24 / G25 / G33 / G34 / G35 / G36 | 低-中 | README.md:77, 576, 554, 191-192 vs 270-271, 72；style-corpus/README.md:66-69；style-profile/README.md:14-43, 70-94, 36；style-corpus/wgl/README.md:3-5, 26-27；examples/README.md:52-54, 86-88, 24, 28-47；README.zh-CN.md:576-577, 381-384；docs/README.md:78, 57-66 | "35 tools"；cli_common "28 of 40"（实 29）；negatives 文件标层 L0；demo 复现 flag 前后不一；paper-review 行少 P 维；语料 README 说无最少论文警告（有）；profile README 缺 discourse/anchoring 校准与 negatives 文件名；wgl README 是 v0.1 措辞；examples/README 说 headline 对在 discussion 复述（在 abstract）、日期 09-04 vs v0.36.3 09-05、before 合计对不上；中文 README 说 demo 2 "停在三条 advisory"（实为 0）、估计噪声模型"未发布"（已建并证伪）；long-form AUC 0.740 vs 0.729 无协议标注；docs/README 提到仓库不带的"editing hook"、索引缺 examples/README |
| G11 | 中 | README.md vs README.zh-CN.md | 结构级差异 16 项：英文有 §6 worked example 中文无（中文从不链接 examples/）；中文有 Claude Code 驱动块、归档链接、14 行 limitations（英文 13 行且集合不同）、长版 roadmap（Codex 模型名、12.5× 引用密度）而英文无；493 vs 507；工具表行长短与数字不同 | 决定一份为准，另一份逐节对译 |

### 6.3 代码声明与过时说法

| 编号 | 位置 | 问题 |
|---|---|---|
| I21 | EVALUATION.md:121；DISPOSITIONS.md:60；RESPONSIBILITIES.md:55；DEAI_SUBSYSTEM.md:306；deai_residue.py:4 | residue 规则数四种说法："three static + one diff"（hub、DISPOSITIONS）、"Four static and one diff"（代码）、"Five rules"（DEAI_SUBSYSTEM）；规范附件 RESPONSIBILITIES 的必需行为里没有 `residue-absence`；DISPOSITIONS 无该规则的行；代码 docstring 编号 1、2、3、5、6，没有 4 |
| I25 / B26 / C20 | DEAI_SUBSYSTEM.md:158；deai_structure.py:59-63；tests/test_deai_structure.py:79-81 | paper-as-agent 例句 "This paper presents" 正是检测器刻意排除的（测试 `test_paper_that_merely_presents_is_not_an_agent`）；v0.36.2 只改了标准与 skill |
| I22 / I31 / I32 / I33 / I34 | EVALUATION.md:124, 163-168, 184-186, 128；DEAI_SUBSYSTEM.md:137-143, 290-291, 414；document-scale.md:515-516 | hub 仍"要求" L3 操作点（§7.0a 已决定不可得）；§12 保留 v0.28.0 "this release" 门与已决定的"open"作者决定；DEAI_SUBSYSTEM 把已撤回的 `deai_policy.json`/已证伪的 L1 操作点写成待定；§9.4b "stays open" 而 §9.4c 已证伪；§8 的空格单位边界"remains open"无 disposition 行，与 v0.36.3 "no loose ends" 相抵 |
| I36 | design-notes/DEAI_FRONTIER.md:6-8, 143-144；DEAI_ARCHITECTURE_ROADMAP.md:3-8, 188-211 | "冻结"设计笔记在冻结日期后被编辑成状态记录，且内容已错（rank 2 已 Done、rank 6 已 shipped、§11 已迁到 DISPOSITIONS） |
| I23 / I27 / I28 / I29 / I37 / I38 / I39 / I24 | DISPOSITIONS.md:57；DEAI_SUBSYSTEM.md:188-189, 213, 122-125, 420-422 及十余处数字；tools/README.md 九行；RESPONSIBILITIES.md:48, 52, 54；DEAI_SUBSYSTEM.md:362-385 | "Superseded/replaces the knob" 与"beside the thresholded rule"矛盾（15 用阈值仍在发射）；"sole consumer of `latex_to_numeral_text`" 自 v0.36.3 起 bank 也用；pair-break 集与权重名滞后 v0.36.2；zero-hit 投影漏 floats；DEAI_SUBSYSTEM 声明数字属于 EVALUATION 却引十余处（三处已过时）；tools/README 九行带未钉住的评估数字（四处已错）；RESPONSIBILITIES 说 linter "optional L1-L3"，实际默认跑 L2 collocation 与 L4 residue；DEAI_SUBSYSTEM §7 只列 8 个 skill |
| B24 / B25 / F35 / F17 / A26 / A30 / C19 / D25 / E26 / E27 | deai_docstructure.py:166-182 + tools/README.md:33；deai_metrics/deai_structure 的 `deai_policy.json` 分支；tools/README.md:50；validate_plugin.py:285-286, 386；tools/README（无 tex_macros 行）；tex_macros.py:22-24, 31-34, 47-51；extract_sections.py:203-207；deai_reference.py:220-221, 273, 304；deai_register.py:27, 447-451；style-corpus/README.md:14-20；style-profile/README.md:36, 96-113；extract_md_negatives.py:5, 27；fetch_arxiv_abstracts.py:46, 193, 255；voice_audit.py:11；train_ai_ism_classifier.py:55-56, 231；voice_dataset.py:109；learned-model.md:207-210, 243-249；tools/README.md:45 + README.md:573 | 无 conformal 块的"legacy baseline"路径今日任何 `--calibrate` 都不会产生、无测试；`deai_policy.json` 无写入方且键未文档化，`measured/strong` 分支实际死；"no shipped document carries an edit-meta literal" 只扫 3 份文档 + skills；两处注释指向不存在的"file-link check"；tex_macros 三处说法与行为相反；`_project` "same substitutions" 在 `$$` 下不成立；`has_prose`/`_bank_records` docstring 与实现不符；register AUC 在代码 0.242 / tools README 0.246 / 记录 0.174 三个值；`defined_terms` docstring 方向写反；style-corpus 布局缺 `fulltext-*`；profile README "Recalibrate after v0.28.0" 已两次重建过时；extract_md_negatives 带个人绝对路径且说 "appended"（实为覆盖）；fetch 的 UA `sci-paper-voice/0.13|0.14`、API 用 `http://`；voice_audit "Fits no model"（实际每次划分拟合两个逻辑回归）；classifier 文件里三个时代的语料数并存；指纹注释"覆盖每个输入"不成立；两份 README 说 `eval_findings` 评 cohesion/hedging 而代码刻意只做四轴 |

## 7. 测试

| 编号 | 状态 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| A31 / D26 / E33 / B28 | 已核实 | tests/test_extract_style.py:211；test_fetch_arxiv_abstracts.py:495；test_label_findings.py:108；test_deai_docstructure.py:304 | `if __name__ == "__main__": unittest.main()` 写在文件中部，直接运行只跑前面的类（17/58、33/45、6/16、13/16） | 移到文件末尾 |
| E31 | 已核实 | tests/test_train_voice_model.py:67-99 | AST 未绑定名检查把全模块所有绑定（含其他函数内的局部 import）并成一个集合，只要任何函数 `import numpy as np`，别的函数裸用 `np` 也过；它当初要抓的 `time` 只要在文件别处绑定就抓不到 | 按作用域解析（`symtable`/pyflakes），至少函数内 import 只算该函数 |
| F37 | 已核实 | tests/test_published_figures.py:348-353 | `assertIs(needs_profile, needs_profile)` 恒真；无 profile 时该文件 8 个测试跳 6 个，这是仅剩两个之一 | 用 dummy 测试类验证 skip，或删除 |
| E32 | 已核实 | tests/test_rewrite_reward.py:265-277 vs rewrite_reward.py:462-480 | "不可读输入 → 2" 的测试在读文件前就因 `--field no-such-field` 返回 2，崩溃兜底从未被触达，删掉兜底测试仍绿 | mock bundle + 让 `rank` 抛错 |
| C22 | 已核实 | tests/test_deai_salience.py:162-179 | 测试钉住"无 `numeral_text` 的 bank 校准得 p90 == 0.0"为正确行为，把静默投影回退固化 | 改为要求警告/degraded 记录 |
| D29 / A32 | 已核实 | test_fetch_arxiv_abstracts.py:145-147, 230-234, 286-299；test_length_gate.py:152-153；test_tex_macros.py:41-43 | 断言字面定义的测试；`issubclass(Throttled, Exception)` 恒真；再导出契约测试排除的正是 extract_sections 自己再导出的三个 tex_assembly 名；注释"九个词"实为 12；带参数宏测试用非数字 body 故抓不到 A9 | 修正 |
| B30 / C22 / D27 / D28 / E34 / F38 | 已核实 | 全库 | 无测试 import `deai_metrics`；conformal/Mondrian 端到端路径（需 ≥55 篇）从未被测；`deai_structure.calibrate`/`strong` 逻辑无测试；partition 只测 unmeasured 路径且用词多重集比较看不到 B2；PDF/连字路径从未端到端跑过（可用假 `pymupdf` 模块）；`_build_or_load_embeddings` 失效与位置对齐无测试；`cmd_sample`、`--n`、根位置 `--field`、`_tex_members`、`fetch_fulltext`、`--author` + REFERENCE_DIR 拒绝、`--glossary`、`--ai-classifier`、`.md` 输入、eval_docscale 整体（无测试文件）均无测试；§3 里每个已复现缺陷都缺回归测试 | 优先给 §8 第一档的修复各配一条两行测试 |

## 8. 建议动作分级

1. **应修（行为错误，含门禁失效）**：A1/A2/F3（根文件不可读 → 2，不是空文档）；A4（`--git-ref` 子文件按 ref 解析）；A3（精确分数）；A11/A12/A13/A14（carve-out 双侧、守卫双向、map 与 gate 同一计词口径）；A5/A6/A7（`\[…\]`、`$$`、注释标题）；E1/E2/E3/E12（保真分词器与多重数比较）；H1（无 voice 模型时降级而非 exit 2）；M1/C2/E7（`--field` 解析统一，子命令默认值不覆盖根解析）；B5/C10/C13/B6/B7（无功效或无 bucket 时报 degraded）；C12/B9（分位读法统一）；B10/B2/B3（partition 同 manifold 比较、原文切分、subsection 固定）；B12/B13/C3/C5/C4（`skip`/参考文献/标签投影）；F1/F2/F6/F9/F4/F7（linter 与 references）；D1/D2/D4/D5/D6/D7/D16（抓取与语料统计）；E5/E6/E8/E13/E14/E15（评估与标注）；C11（读并校验制品 `unit`）；A27/A28（condense 配方）。修改 B12/B13/B15/B22/C12 后需重建对应 baseline 并重取 EVALUATION 相应数字。
2. **应改文档/元数据**：§6.2 全部数字（I1–I20、G14–G25）；§6.1 中 H3/H4/H5/H6/H12/H13/H36 的 skill 补丁；I21（RESPONSIBILITIES 补 `residue-absence`）；I25；I36（设计笔记恢复冻结）；I22/I31–I34（关闭 stale open）；tools/README 去评估数字（I38）；G11 中英 README 对齐；G27 注册表只留一份；D15 二选一（实现权重或改五处措辞）；标准升 v3.9（H31）。
3. **可延后**：§5 的 import/常量清理（一次 pyflakes 扫描即可批量完成）；R1–R10 与 H23–H30/H45–H51 的去重（约 350 行，且多数文件接近上限，值得排期）；B16/B17/B18/E17/E18/E20/F22/F26/D20 等待核实项；测试补齐（§7 末行）；latency.json 重取或删除（G19）；上次审计的 disposition 列与本机路径链接（M3/I35）。

## 9. 已检查且未发现问题（摘要）

- 全部 27 个测试文件、validator 11 项、`-X dev` 警告即错误模式下均通过；无已弃用 stdlib API；无 CRLF/BOM；分支与 `main` 同一提交。
- 退出码契约在正常路径上成立：`ai_ism_lint` 0/1/2、`length_gate` 与 `deai_residue` 的 0/1/2、`rewrite_reward` 0/1/2、`verify_references` 0/1/2、抓取器摘要模式的 429 → 2；`--top` 不改变计数与汇总；JSON 键稳定。
- `parse_required_shrink` 对 `100%`/`200%`/`inf`/`nan`/`30%%` 的拒绝与 `30%`/`0.3`/`1e-1` 的接受；装配的行内 `\input`、重复 include、环、注释掉的 include；跨行 `\citep[e.g.][]{…}` 与 float 置空；`\section {X}`/`[S]`/subsection 继承（deai_metrics/extract_sections 侧）；bank 行 schema 与所有读者一致；`paired_paragraphs` 两投影同构（`$$` 除外）；REFERENCE_DIR 不加权、不进聚合、默认不进检索。
- `deai_feedback` 校验、优先级排序（与 §4 一致）、0.5 段落置信上限；`_mat_inv`/Mahalanobis/conformal `_conformal_p`/分层回退/角色 z 分数正负号一致；`fit_dispersion_manifold` 33 行下限；voice 流水线的训练集内 centroid、词表、分组划分、原子写出、schema 漂移拒绝；`rank_auc` 与 `_auc` 与暴力 tie-aware AUC 在 3000 例上一致；kappa 与独立实现一致；20 标签下限；blind relabel 剥离字段正确。
- register 的多行置空、宏项、复合词最稀部分、三类 zero-hit 豁免、`wgl-letter` 借用；collocation 的断点集、留一法、可能所有格首词；discourse 状态与检测同一 `live_buckets`、hedging 限 `intro`；salience 的 `numeral_text` 与 `latex_to_numeral_text` 占位符一致、每段一条 finding、低于下限的 bucket 给 degraded finding 而非沉默；residue 规则 6 家族、`never(?!-)`、`[CITE]` 豁免、强弱顺序；validator 镜像检查；CUDA 回退可达且不泄漏（除 C7 的空消息情形）。
- 文档：所有 43 个 markdown 的相对链接、`tools/*.py`、`skills/*` 引用均可解析（除 M3）；docs/README 的 section map 与磁盘一致；skill 里引用的 EVALUATION §号全部经 hub 解析；没有 skill 引入 PASS/FAIL 或作者身份断言，没有 skill 豁免 integrity blocker；README 引用的所有 flag 存在；文档常量（15 / 1e-4 / 500 / 2e-4 / 4 / 2 / 30 / 0.90 / 0.95 / 0.10 / 0.05 / 150 / 3 / 400 / 0.60 / 0.20 / 0.5 / 3 篇 / 0.40 / 20 / 0.05 / 3 层 / 0.6）与代码一致；v0.36.3 重测数字在已更新的位置内部一致，过时的恰是 §6.2 列出的位置。

## 10. 落地记录（v0.39.0，2026-09-27）

§8 第一梯队与其耦合的第二梯队已在 v0.39.0 落地，提交按范围列出；每个提交正文写明它覆盖的条目号。

| 范围 | 条目 | 提交 |
|---|---|---|
| 字段解析：`cli_common.optional_field_dir`、`axis_main` 的 `--calibrate` 检查与 `extra_arguments`/`check`/`report_for` 钩子 | M1/B1/C1/C2/D3/E9/H2，C8/C21 的 cli_common 侧 | `49624e5` |
| 装配、投影与宏；length_gate 与 condense_map；ai_ism_lint 与 validate_plugin；extract_style 与 retrieve_exemplars | A1–A20、A28，F3/F4/F7/F9/F12/F14/F16–F20/F25/F27/F28/F33，D6–D11/D14/D16/D19，M2/M3 | `5ce670c` |
| verify_references | F1/F2/F5/F6/F8/F10/F11/F13/F21/F23/F24/F32 | `46cf4ce` |
| 文档级轴：docshape、docstructure、metrics、structure、features、partition、anchoring | B1–B15、B19–B21、B23、B28，E20 的 features 侧 | `1c9736d`、`f211ece`、`2d2685d` |
| rewrite_reward | E1–E4、E12、E30，H1 | `116f074` |
| eval_findings、eval_docscale、label_findings、voice_dataset、voice_audit、train_voice_model、train_ai_ism_classifier | E5–E8、E10/E11、E13–E16、E18/E19、E21/E22、E28、E31、E33，M5 | `9b30c47`、`e47d250` |
| fetch_arxiv_abstracts | D1–D5、D12/D13、D24、D26 | `41a29a8` |
| 逐 bucket 轴：reference、collocation、discourse、salience、register、residue、oracle、provenance、personal、voice | C1–C19、C21、C22（C20 属 deai_structure，未动），E20 的 voice 侧 | `95c988f`、`3e13594` |
| 文档与元数据：§6.2 全部数字（I1–I20、G14–G25）、H3–H6/H12/H13/H36 的 skill 补丁、I21/I25/I36、I22/I31–I34、I38、G11、G27、D15（改为"记录权重，未应用"）、H31（标准 v3.9）及各部分的 registry 行、发布说明与记录的测试数 | | `1ad6ed7`、`de925a9`、`470290d`、`b25f4cd` 及本节所在提交 |

未落地（§8.3 及本轮范围之外）：

- §5 的去重（R1–R10、H23–H30/H45–H51）；待核实项 B16/B17/B18/E17/E32/F22/F26/D20；G19（`latency.json`）；M3/I35 的 disposition 列。A31/D26/E33/B28 的 `__main__` 位置已随各自文件修复。
- 需重建的制品：`structure_baseline` 与 `docstructure_baseline`（B12/B15）、`anchoring_baseline`（B13）；逐 bucket 轴的制品需重新校准才采用最近秩分位网格（C12）。重建前，EVALUATION 中据旧制品测得的比率沿用旧值，各处已注明测得日期。
- 抓取器的内置查询集、关键词过滤与期刊表标为 `[WGL]`，其他领域改用 `--query`（D24）；`TIER_WEIGHTS` 仍只记录不应用（D15 按第二梯队的"改措辞"落地）。
