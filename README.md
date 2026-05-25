# sci-paper

A Claude Code plugin for writing and reviewing scientific papers at the
ApJ / MNRAS / PRD / JCAP / Nature-Physics level.

## What it ships

### Skills (8)

| Skill | Purpose |
|---|---|
| `paper` | Writing standards (formula conventions, citation rules, **anti-AI-ism hard rules**, **forward-narrative structural-update rule**, key references). Invoke before drafting. |
| `paper-review` | Forced source-traceable review across **A–R** dimensions (math / physics / logic / language / structure / citations / data / interfaces / redundancy / reproducibility / modern-physics-review / systemic inconsistency / adversarial 3-pass / drift sweep / process-artifact removal / draft language / citation precision / glossary alignment). Zero-issue convergence hard loop; isolated-context MPR final verification. |
| `figure-review` | Renders compiled PDF at 150 DPI and reviews each figure as a human reader would actually see it (axis font sizes, legend readability, float placement). |
| `paper-style` | Loads a corpus-distilled style profile (top-journal + mentor + high-value-reference papers) plus retrieves section-typed exemplar paragraphs. Constrains writing/rewriting to match observed human-academic patterns. |
| `brainstorm` | Fully-automated radial research-direction explorer (phylogenetic-tree model). 12 framings (first-principles / inversion / cross-disciplinary / adversarial / constraint-shift / scale extrapolation / substitution / office-hours / contrarian / failure-driven / high-risk-high-reward / meta-self-audit). Recurses on promising leaves until convergence. §2.0 glossary grill prelude locks root-node terms to `FACTS.md`. |
| `mainline` | Structural narrative-spine reinforcer. Full-read audit on 7 positive + 8 negative structural dimensions; mandatory isolated-context cold-read 7-question readability sub-agent. Complements `paper-review` (per-claim correctness) by covering spine-level issues. |
| `paper-attack-tree` | `brainstorm`'s radial methodology applied to critique. Each node = one critique attacked by 12 framing passes; every leaf resolved to **CONFIRMED** / **REFUTED** / **MARGINAL** with `file:line` evidence. No `NEEDS-MORE-INFO` defer. Complements `paper-review` (static checklist) with open-ended adversarial coverage. |
| `final-review` | 5-skill orchestrator for pre-submission final pass. Runs `paper-review` / `figure-review` / `mainline` / `paper-attack-tree` / `modern-physics-review` each in its own `isolation: worktree` sub-agent every round; loops until consecutive N rounds (default 2) show 0 issues across all 5. ITER_BUDGET 10 rounds. |

See [CHANGELOG.md](CHANGELOG.md) for the per-version evolution.

### Tools (7)

| Tool | Purpose |
|---|---|
| `tools/build_profile.py` | One-shot orchestrator: extract → train classifier → warm exemplar cache. |
| `tools/extract_style.py` | Corpus → lexicon / sentence-stats / transition-inventory JSON + `style_dossier.md` + section-typed exemplar bank. `.tex` and `.pdf` (pymupdf blocks). |
| `tools/retrieve_exemplars.py` | Section + topic + field → top-K exemplar paragraphs (sentence-transformers cosine, `.npy` cache, keyword-overlap fallback). |
| `tools/ai_ism_lint.py` | Tier-graded regex (em-dash, Tier A zero-tolerance, Tier B frequency-capped) + corpus-derived blacklist + opt-in ML classifier (`--ai-classifier`) + `--summary`. |
| `tools/train_ai_ism_classifier.py` | Trains a paragraph-level logistic-regression classifier on word 1–2 gram TF-IDF. Positives = corpus, negatives = `ai_ism_negatives_handcrafted.txt` (extend with `extract_md_negatives.py`). CV F1 ≈ 0.88 on `wgl`. |
| `tools/extract_md_negatives.py` | Harvests LLM-drafted prose from your project tree as extra negatives for the classifier. |
| `tools/ai_ism_negatives_handcrafted.txt` | Seed negatives shipped with the plugin (extend by hand or via `extract_md_negatives.py`). |

See [tools/README.md](tools/README.md) for per-tool roadmap and graceful-degradation behaviour.

## Quick start

```bash
# 1. Install Python deps (numpy + pymupdf + sentence-transformers + sklearn).
pip install -r requirements.txt

# 2. Drop corpus papers into the field tier dirs:
#       style-corpus/wgl/tier-1-top/        ← top-journal .tex / .pdf
#       style-corpus/wgl/tier-2-mentor/     ← mentor's papers
#       style-corpus/wgl/tier-3-reference/  ← other high-value references

# 3. Build the profile end-to-end (extract → train → warm cache).
#    First run downloads the sentence-transformers model (~80 MB; ~30 s).
python tools/build_profile.py

# 4. Register the plugin in your Claude Code session
claude --plugin-dir <path-to-this-repo>

# 5. Use it
#    - skill (Claude does the work)        :  /sci-paper:paper-style discussion
#    - manual exemplar retrieval           :  python tools/retrieve_exemplars.py --section method --topic "..."
#    - lint a draft (regex + ML classifier):  python tools/ai_ism_lint.py draft.tex --ai-classifier --summary
```

## Why `paper-style` instead of "fine-tuning a model"

Fine-tuning Claude is **not offered** by Anthropic; LoRA-ing an OSS model on a
small (~10–100 paper) corpus produces a writer strictly worse than Claude raw.
The realistic path is **explicit style extraction + retrieval-augmented
exemplars**:

1. Parse the corpus → quantitative features (section-conditional sentence-length
   distributions, transition-word inventory, em-dash vs en-dash counts, passive
   ratio per section, formula:text density, hedge-word frequency, opening
   patterns).
2. Compress to a `style_dossier.md` (~2k tokens) loaded into Claude's context
   when the skill is invoked.
3. Index representative paragraphs by section type (abstract / intro / method /
   results / discussion / conclusion); retrieve top-K at write time as positive
   anchors.
4. Extend the existing hand-written anti-AI-ism blacklist with **data-driven**
   evidence (words/phrases the corpus actually never uses).

This gives you what fine-tuning would, except: it's transparent (every rule
traces to a corpus paper), editable (drop in new papers, re-extract), and
small-data-friendly (RAG dominates fine-tuning at this corpus size).

See [EVALUATION.md](EVALUATION.md) for the full feasibility analysis.

## Project structure

The plugin is **field-aware**: a "field" is one subfolder under
`style-corpus/<field>/` and a corresponding `style-profile/<field>/`.
v0.1 ships only `wgl` (weak gravitational lensing); add fields by creating
new subdirs alongside it (e.g. `cosmology/`, `ml-methods/`). When only one
field exists, all tools and skills auto-detect it; with multiple, pass
`--field <name>` explicitly.

```
.
├── .claude-plugin/
│   ├── plugin.json               # plugin manifest
│   └── marketplace.json          # single-plugin marketplace manifest
├── skills/
│   ├── paper/SKILL.md
│   ├── paper-review/SKILL.md
│   ├── figure-review/SKILL.md
│   ├── paper-style/SKILL.md      # --field aware
│   ├── brainstorm/SKILL.md       # radial idea/problem tree with width × depth
│   ├── mainline/SKILL.md         # structural spine reinforcer + cold-read sub-agent
│   ├── paper-attack-tree/SKILL.md # brainstorm methodology applied to paper critique
│   └── final-review/SKILL.md     # 5-skill orchestrator with per-skill isolation + stable-convergence loop
├── style-corpus/                  # user-populated; gitignored content
│   ├── README.md
│   └── wgl/                       # current default field
│       ├── tier-1-top/            # top-journal exemplars
│       ├── tier-2-mentor/         # mentor's high-quality WGL papers
│       └── tier-3-reference/      # high-value WGL references
├── style-profile/                 # generated by tools/extract_style.py
│   ├── README.md
│   └── wgl/                       # populated on first build_profile.py run
└── tools/
    ├── build_profile.py           # one-shot orchestrator: extract → train → warm
    ├── extract_style.py           # corpus → dossier + JSONL exemplar bank
    ├── retrieve_exemplars.py      # cosine retrieval (sentence-transformers)
    ├── ai_ism_lint.py             # tier-graded regex + opt-in ML classifier
    ├── train_ai_ism_classifier.py # logistic regression on word 1–2 grams
    ├── extract_md_negatives.py    # harvest LLM-drafted prose for negatives
    └── ai_ism_negatives_handcrafted.txt
```

## Installation (development)

From this repo:

```bash
claude --plugin-dir <path-to-this-repo>
```

Reload after edits:

```
/reload-plugins
```

Once invoked, skills appear as `/sci-paper:paper`, `/sci-paper:paper-review`,
`/sci-paper:figure-review`, `/sci-paper:paper-style`, `/sci-paper:brainstorm`,
`/sci-paper:mainline`, `/sci-paper:paper-attack-tree`,
`/sci-paper:final-review` (Claude Code namespaces plugin skills by plugin
name to prevent conflicts).

## Build the style profile (one-time + on corpus change)

1. Drop papers into `style-corpus/wgl/tier-{1,2,3}-*/` (PDF or `.tex` source —
   `.tex` is preferred because parsing is exact, but PDF works via text
   extraction).
2. Run:
   ```bash
   python tools/extract_style.py --field wgl
   # (or just `python tools/extract_style.py` while wgl is the only field —
   # tools auto-detect single-field corpora.)
   ```
3. Inspect `style-profile/wgl/style_dossier.md` and edit by hand if any
   extracted pattern looks wrong. The dossier is the file that actually
   enters Claude's context, so it's worth a manual pass.

## Add a new field later

```bash
mkdir -p style-corpus/<new-field>/{tier-1-top,tier-2-mentor,tier-3-reference}
# drop papers
python tools/extract_style.py --field <new-field>
```

After this, all tools/skills require explicit `--field <name>` because
multiple fields are present.

## Status

Current: **v0.12.0**. Full per-version history in [CHANGELOG.md](CHANGELOG.md).

- **Skills (8):** `paper`, `paper-review`, `figure-review`, `paper-style`,
  `brainstorm`, `mainline`, `paper-attack-tree`, `final-review`.
- **Tools (7):** `build_profile.py` (orchestrator), `extract_style.py`
  (`.tex` + `.pdf`), `retrieve_exemplars.py` (sentence-transformers
  cosine + `.npy` cache + keyword fallback), `ai_ism_lint.py` (tier-graded
  regex + `--ai-classifier` + `--summary`), `train_ai_ism_classifier.py`
  (LR on word 1–2 grams; CV F1 ≈ 0.88 on `wgl`), `extract_md_negatives.py`
  (harvest negatives from your doc tree), `ai_ism_negatives_handcrafted.txt`
  (seed negatives).
- **Field-aware:** auto-detect single field, require `--field <name>` when
  multiple. v0.12 still ships only `wgl` populated.
- **WGL anchors:** four ported skills (`paper`, `paper-review`,
  `figure-review`, and parts of others) carry `[WGL]` markers for the
  weak-gravitational-lensing project's specifics; remove or replace those
  anchors when generalizing to other fields.

See [tools/README.md](tools/README.md) for the per-tool roadmap and
[EVALUATION.md](EVALUATION.md) for the design rationale.

## License

[MIT](LICENSE) — covers the code, skills, documentation, and tooling
authored in this repository. The `style-corpus/` directory is user-populated
and git-ignored (`.gitignore` blanket-denies `style-corpus/**/tier-*/**`),
so no third-party papers or copyrighted materials are bundled or
distributed with this plugin.
