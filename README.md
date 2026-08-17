# sci-paper

[![CI](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.27.0-informational.svg)](CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A5CF6.svg)](https://docs.claude.com/en/docs/claude-code/plugins)

**A Claude Code plugin that writes, reviews, de-AIs, and condenses scientific
manuscripts for top-tier journals — under one typed standard, with every claim
traced to a source and every unavailable measurement labelled as unavailable.**

Built for ApJ / MNRAS / PRD / JCAP-class papers and NSF / NIH proposals.
8 skills, 24 tools, 208 tests, one normative contract.

[中文文档 →](README.zh-CN.md) · [Documentation index →](docs/README.md) · [The standard →](docs/SCIPAPER_STANDARD.md)

---

## Contents

- [The problem](#the-problem) · [What makes it different](#what-makes-it-different)
- [How it works](#how-it-works) · [Install](#install) · [Quick start](#quick-start)
- [Skills (8)](#skills-8) · [Tools (24)](#tools-24)
- [The feedback contract](#the-feedback-contract) · [Field-aware evidence](#field-aware-evidence)
- [Repository layout](#repository-layout) · [Development](#development) · [Status](#status)

---

## The problem

Three failure modes ruin technical manuscripts, and none of them is a vocabulary
problem:

1. **Prose still reads as machine-written after keyword cleanup.** Swapping
   "delve" for "examine" leaves the deeper regularities untouched: smoothed
   sentence-length variation, templated construction, over-regular document
   shape, and claims with no evidence behind them.
2. **A single AI-detector score cannot tell an editor what to change** — and it
   is confounded by field, source, section genre, length, jargon, and
   mathematical density. It answers a question ("who wrote this?") that an
   author does not need answered.
3. **Review silently converts missing evidence into good news.** An
   uncalibrated axis reports zero findings, and zero findings read as clean.

sci-paper refuses all three. It emits **typed, ranked, source-traced findings**
instead of a score, it never claims to identify an author, and an axis it could
not measure says so.

## What makes it different

| | Most writing tools | sci-paper |
|---|---|---|
| **Output** | One opaque score, or a rewrite | Typed findings with stable IDs, ranked by consequence, each with a source trace and a recommended action |
| **Missing calibration** | Silently reported as clean | Explicitly `unmeasured` / `degraded`, with the reason and what would restore it |
| **Rewriting** | Optimizes a style score | **Hard scientific-fidelity eligibility first**: drop *or invent* a number, unit, citation, equation, acronym, comparison direction, negation, or causal direction and the candidate scores `-inf` and cannot win |
| **Length** | Grows with every "fix" | A mechanical length budget: the default direction of every edit is *shorter*; growth needs a recorded justification |
| **Authorship** | "87% AI-generated" | Never. Learned scores are *field-similarity triage*, structurally capped at 0.5 confidence at paragraph scale |
| **Style reference** | A generic model prior | **Your field's own corpus** — descriptive statistics and exemplars extracted from papers you supply |
| **Negative results** | Quietly dropped | Recorded. Three surface formalisations of the "thesis spine" signal were built, measured, and **refuted**; the rule ships as a writing rule *with no detector*, and the standard forbids building a threshold on it |

That last row is the design philosophy in miniature: **a refuted detector is
evidence, and it stays in the record.** See
[docs/architecture/EVALUATION.md](docs/architecture/EVALUATION.md).

## How it works

```
             ┌──────────────────────────────────────────────┐
  your field │  style-corpus/<field>/tier-{1,2,3}-*/         │  papers you supply
  corpus  ──▶│  → extract_style.py → style-profile/<field>/  │  (read-only, gitignored)
             └──────────────────────────────────────────────┘
                                  │ descriptive statistics, exemplars, calibrated references
                                  ▼
  draft.tex ──▶ measure ──▶ typed findings ──▶ rank ──▶ edit ──▶ re-measure ──▶ disposition
                   │                                                    │
                   │ L0  lexicon + punctuation + domain register        │ every strong
                   │ L1  information distribution, surprisal / UID      │ advisory ends
                   │ L2  sentence templates, salience, document shape   │ as acted /
                   │ L3  learned field similarity (capped, degraded)    │ accepted /
                   │ L4  positive voice + cooperative repair            │ false-positive
                   └────────────────────────────────────────────────────┘
```

The loop is the whole product: **measure → type → rank → edit → re-measure →
disposition.** It terminates in a *disposition-complete* state — not in "zero
advisories", and never in a paper-level PASS.

## Install

```bash
git clone https://github.com/skymanbp/sci-paper.git
```

Register it with Claude Code:

```bash
claude --plugin-dir /path/to/sci-paper          # development
```

Skills are then namespaced `/sci-paper:<name>`.

**Python ≥ 3.11.** The shared schema, the deterministic L0 linter, the
model-free L1/L2 axes, the document-structure analysis, and the validator are
**standard library only**. Optional capabilities add dependencies:

```bash
pip install -r requirements.txt      # all optional extras
```

| Package | Enables |
|---|---|
| `pymupdf` | PDF corpus extraction, compiled-page inspection |
| `sentence-transformers` | semantic exemplar retrieval, embedding features |
| `scikit-learn` + `joblib` | legacy and learned field-similarity models |
| `transformers` + `torch` | token-surprisal / UID measurement |
| `numpy` | learned feature, cache, and rewrite-score utilities |

> Never install an optional dependency merely to turn an unavailable axis into a
> nominal score. A missing package keeps its axis `unmeasured`, by design.

## Quick start

```bash
# 1. Verify the checkout.
python tools/validate_plugin.py
python -m unittest discover -s tests -v

# 2. Put your field's papers under style-corpus/<field>/tier-*/ and build the profile.
python tools/build_profile.py --field wgl

# 3. Produce one unified, machine-readable feedback report.
python tools/ai_ism_lint.py draft.tex --field wgl \
  --structure --distribution --document-structure --register --salience \
  --oracle --voice --format json --output feedback.json
```

Then drive it from Claude Code:

```text
/sci-paper:paper                                  # load the writing standard
/sci-paper:de-ai         draft.tex --field wgl    # measure → audit → faithful rewrite
/sci-paper:condense      draft.tex                # remove redundancy, prove the shrink
/sci-paper:paper-review  draft.tex --field wgl    # A–R source-traced review
/sci-paper:figure-review draft.pdf                # compiled-page figure evidence
/sci-paper:final-review  draft.tex --field wgl    # isolated multi-reviewer orchestration
/sci-paper:brainstorm    "topic"                  # radial research exploration
/sci-paper:proposal-polish grant.tex --agency nsf # proposal register
```

---

## Skills (8)

Four jobs: **write**, **revise**, **review**, **explore**.

#### Write

| Skill | What it does |
|---|---|
| [`paper`](skills/paper/SKILL.md) | The writing framework: accuracy rules, formula and citation conventions, forward narrative, the L0 lexical policy with canonical examples, positive-voice guidance, measurement states, and stopping semantics. |
| [`proposal-polish`](skills/proposal-polish/SKILL.md) | Funding-proposal register (NSF Project Summary/Description, NIH Specific Aims, fellowships). Keeps the vision-and-feasibility language a paper would trim, enforces claim–feasibility matching, and edits the score-forming first pages hardest. Never invents preliminary data, partners, or letters. |

#### Revise

| Skill | What it does |
|---|---|
| [`de-ai`](skills/de-ai/SKILL.md) | Three chained passes: subsystem measurement (L0–L4), a vendored humanizer structural-tell audit, then **claim-first** rewriting — prose is rebuilt from the protected claim graph, not polished in place. `--audit-only` runs passes 1–2 for review integration. |
| [`condense`](skills/condense/SKILL.md) | Whole-document redundancy elimination under one-canonical-home-per-fact, loop-until-dry convergence, and the mechanical length gate as the closing proof. |

#### Review

| Skill | What it does |
|---|---|
| [`paper-review`](skills/paper-review/SKILL.md) | Source-traced **A–R** review: mathematics, physics, logic and statistics, language and de-AI, structure and narrative spine, citations, data and figures, interfaces, redundancy, reproducibility, modern-physics checks, consistency, adversarial verification (three passes + twelve-framing escalation), staleness, process artifacts, draft language, citation precision, glossary alignment. |
| [`figure-review`](skills/figure-review/SKILL.md) | Reviews **compiled pages at 150 DPI** — not source. Traces figure/caption/data provenance, measures canvas balance at the pixel level, and separates scientific and build contradictions from readability and aesthetic advisories. |
| [`final-review`](skills/final-review/SKILL.md) | Parent orchestrator. Runs paper-review, figure-review, de-ai `--audit-only`, and modern-physics-review as **isolated worktree agents**, merges their typed findings, and verifies a stable disposition-complete state across consecutive rounds. |

#### Explore

| Skill | What it does |
|---|---|
| [`brainstorm`](skills/brainstorm/SKILL.md) | Radial research-direction explorer: twelve framing passes per node, glossary-anchored terminology, complete derivation per branch, recursive divergence to convergence. Deferred or incomplete leaves are hard-banned. |

## Tools (24)

Every finding any of these tools emits uses the same `sci-paper.feedback.v1`
contract; the corpus, training and data-asset entries below produce artifacts
rather than findings. Full per-tool calibration and failure behavior:
[tools/README.md](tools/README.md).

#### Contract, gates, and CLI

| Tool | Purpose |
|---|---|
| `tools/deai_feedback.py` | Implements `sci-paper.feedback.v1`: stable IDs, consequence classes, measurement states, dispositions, ranking, summaries, rendering. Standard library only. |
| `tools/ai_ism_lint.py` | The unified CLI. Aggregates L0 and every advisory axis into one ranked text/JSON report. Exit `0` = no L0 target, `1` = L0 target present, `2` = invalid input or execution failure. |
| `tools/length_gate.py` | Per-section prose length-budget delta gate (standard §5.3). Exit 1 on net unjustified growth between two document versions; `--allow` records justifications. |
| `tools/rewrite_reward.py` | Ranks rewrite candidates **after** hard scientific-fidelity eligibility. Dropping *or inventing* a protected invariant scores `-inf`. |

#### L0 — lexicon and register

| Tool | Purpose |
|---|---|
| `tools/deai_register.py` | Domain register: terms the manuscript leans on that the field's own corpus does not carry, judged by corpus document frequency rather than a curated cross-discipline list. Compounds are judged by their rarest part. Advisories only. |
| `tools/ai_ism_negatives_handcrafted.txt` | Seed negative examples for the legacy classifier (data asset). |

#### L1 — information distribution

| Tool | Purpose |
|---|---|
| `tools/deai_metrics.py` | Model-free information-distribution findings — sentence-length variation, connective openers — with explicit calibration state. |
| `tools/deai_oracle.py` | Optional token-surprisal and Uniform Information Density evidence. Unavailable assets and compatibility thresholds stay explicit. |

#### L2 — sentence and document structure

| Tool | Purpose |
|---|---|
| `tools/deai_structure.py` | Sentence and paragraph construction: enumeration, repeated frames, parallel runs, symmetry, and related template families. |
| `tools/deai_salience.py` | Salience hierarchy: how far a passage's measured quantities run without an interpreting sentence between them, against a per-section human reference. Sole consumer of the numeral-preserving LaTeX projection. |
| `tools/deai_docstructure.py` | Whole-document rhetorical shape and complete-document calibration: dispersion band, per-length-stratum joint manifold, role coupling, split-conformal operating points. |
| `tools/deai_anchoring.py` | Section-class conditional claim-anchoring band — a writing-quality axis, explicitly **not** an AI-discrimination axis. |

#### L3 — learned field similarity

| Tool | Purpose |
|---|---|
| `tools/deai_features.py` | Reusable distributional, UID, punctuation, embedding, and structural features. |
| `tools/deai_voice.py` | Optional learned field-similarity triage. A bundle without an operating point is degraded and never an authorship verdict. |
| `tools/train_voice_model.py` | Trains the optional field-similarity model with source-paper grouping. Confound audits are mandatory. |

#### L4 — cooperative repair

| Tool | Purpose |
|---|---|
| `tools/deai_partition.py` | Fidelity-free merge/split suggestions that move a document toward the human dispersion band. Suggest-only, zero-token operations. |
| `tools/deai_provenance.py` | Editing-provenance ledger over the author's **own** draft history; labels each span AI-untouched → author-original by token edit ratio. Not a detector; `unmeasured` without an AI-draft ancestor. |
| `tools/deai_personal.py` | Personal dispersion baseline against the author's own prior papers — a confound-free same-author reference. `unmeasured` below three papers. |

#### Corpus and profile building

| Tool | Purpose |
|---|---|
| `tools/build_profile.py` | Builds the basic field profile: extraction, optional legacy classifier, exemplar-cache warm-up. |
| `tools/extract_style.py` | Extracts lexicon, sentence statistics, transitions, a descriptive dossier, and a section-typed exemplar bank. Owns the two named LaTeX projections and the section-bucket vocabulary. |
| `tools/retrieve_exemplars.py` | Retrieves section- and topic-matched exemplar paragraphs, with embedding or explicit fallback retrieval. |
| `tools/fetch_arxiv_abstracts.py` | Fetches dated abstract corpora for controlled evaluation and training, optionally restricted to a subfield query set and named refereed journals. Rate limiting **stops the sweep and exits 2** rather than writing a truncated corpus as if it were complete. |

#### Legacy and training data

| Tool | Purpose |
|---|---|
| `tools/train_ai_ism_classifier.py` | Trains the legacy word-ngram classifier, used only as degraded advisory evidence. |
| `tools/extract_md_negatives.py` | Harvests candidate generated paragraphs for controlled evaluation and training. |

> `tools/validate_plugin.py` is a development and release tool, not a shipped
> product tool, and is excluded from the count above.

---

## The feedback contract

Every finding carries exactly one **consequence class**:

| Class | Meaning | Required consequence |
|---|---|---|
| `integrity_blocker` | The scientific record may be wrong, unsupported, inconsistent, unreproducible, or unusable | **Must** be resolved from sources. Cannot be waived as a style preference. |
| `l0_target` | A Tier A word, an em-dash, or a Tier B word beyond one occurrence per section | Rewrite to zero. Not a claim that the paper is scientifically invalid. |
| `advisory` | Structural, distributional, learned, rhetorical, clarity, or aesthetic evidence | Rank, act on the strongest, then record a disposition for the rest. |

Every axis reports one **measurement state** — `measured`, `degraded`,
`unmeasured`, or `not_applicable` — and a final report lists all four.
**Silence is never read as clean.**

Every strong advisory ends at one **disposition**: `acted`, `accepted`,
`rejected_as_false_positive`, or `pending` with a stated reason. Ordinary
advisories stay visible and do not have to disappear.

## Field-aware evidence

A *field* is one subdirectory under `style-corpus/` with a matching directory
under `style-profile/`. With exactly one field present, tools auto-detect it;
with several, pass `--field <name>` explicitly. Nothing assumes a particular
field exists.

```
style-corpus/<field>/tier-1-top/        top-journal exemplars
                     tier-2-mentor/     mentor or target-author exemplars
                     tier-3-reference/  other relevant field papers
        |  python tools/extract_style.py --field <field>
        v
style-profile/<field>/                  generated evidence (gitignored)
```

Corpus contents are **read-only, copyright-sensitive inputs** and are never
committed. Generated dossiers and exemplars may quote source prose and must not
be published unless their rights permit it. A corpus dossier is descriptive
evidence — not a normative standard, and not proof of human or machine
authorship.

Whole-document calibration requires complete papers as independent
observations. Paragraph exemplars cannot be relabelled as independent
documents.

## Repository layout

```text
sci-paper/
├── .claude-plugin/          plugin.json · marketplace.json
├── .github/workflows/       ci.yml — validator + test suite on every push and PR
├── docs/                    ← documentation index at docs/README.md
│   ├── SCIPAPER_STANDARD.md      the single normative contract (v3.6)
│   ├── architecture/
│   │   ├── DEAI_SUBSYSTEM.md     implementation architecture
│   │   └── EVALUATION.md         current metrics, gaps, confounds, refuted signals
│   └── design-notes/             frozen, dated reasoning records (not status)
├── skills/<name>/SKILL.md   8 skills
├── tools/                   24 product tools + the repository validator
├── tests/                   15 test files, 208 tests
├── style-corpus/<field>/    user-supplied read-only corpus (gitignored)
├── style-profile/<field>/   generated and calibrated evidence (gitignored)
├── CHANGELOG.md             per-version history
└── CLAUDE.md                working rules for this repository
```

## Documentation

| Read this | For |
|---|---|
| [docs/README.md](docs/README.md) | Documentation index and authority order |
| [docs/SCIPAPER_STANDARD.md](docs/SCIPAPER_STANDARD.md) | **The normative contract.** If anything disagrees with it, it wins. |
| [docs/architecture/DEAI_SUBSYSTEM.md](docs/architecture/DEAI_SUBSYSTEM.md) | How the subsystem is built |
| [docs/architecture/EVALUATION.md](docs/architecture/EVALUATION.md) | What is measured, what is not, and every known confound |
| [tools/README.md](tools/README.md) | Per-tool registry, calibration, failure behavior |
| [style-corpus/README.md](style-corpus/README.md) | Supplying a field corpus |
| [style-profile/README.md](style-profile/README.md) | Generated assets and build boundaries |

## Development

```bash
python tools/validate_plugin.py                  # 9 contract checks
python -m unittest discover -s tests -v          # 208 tests
```

The validator checks release metadata, skill frontmatter, standard references,
documentation authority boundaries and index completeness, recorded suite sizes
against real discovery, stale contract markers, product registries, Python
syntax, runtime imports, CLI entry points, schema fields, linter exit semantics,
Tier B behavior, tests, and CI wiring. The authoritative list is
`tools/validate_plugin.py` itself.

A release additionally requires independent code review, clean-checkout
verification, and a green hosted CI run on the release commit.

## Status

Current: **v0.27.0**. Full per-version history in [CHANGELOG.md](CHANGELOG.md).

- **Normative core:** `docs/SCIPAPER_STANDARD.md` v3.6 — the complete de-AI
  standard in one file (layered model, document-scale detection core,
  cooperative layer, the `calibration_unit` confidence cap, the §5.2
  de-AI-ization procedure, the §5.3 condense-not-accumulate rule with mechanical
  enforcement, and the §5.4 thesis spine shipped deliberately **without** a
  detector). There is no separate de-AI standard.
- **Skills (8):** `paper`, `de-ai`, `condense`, `paper-review`, `figure-review`,
  `brainstorm`, `final-review`, `proposal-polish`.
- **Tools (24):** the registry above is exact.
- **Calibrated gaps, stated plainly:** no learned-model operating point (the L3
  document-level surprisal path is *measured* not to provide one); no completed
  author hard-set labels; and the cooperative-layer tools (`deai_provenance`,
  `deai_personal`) are honestly `unmeasured` until the author supplies their own
  draft history or prior papers.
- **Field-specific guidance:** weak-lensing scientific anchors stay marked
  `[WGL]` where they apply. Shared writing and review policy is field-agnostic.

## Acknowledgments

- **[AIScientists-Dev/academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer)**
  (MIT) — the 2026-07-16 lexicon extensions (`underscore*`, `pivotal`,
  `tapestry`, `testament`, `realm*`, `intricate`, `foster*`), the `serves as`,
  `ing-tail`, and `colon-elaboration` linter rules, the Claim–Evidence
  Discipline and Preserve List sections of `skills/paper/SKILL.md`, the
  `proposal-polish` skill, and the `de-ai` skill's Layer 1–5 audit catalog adapt
  its material. Every lexical adoption was re-verified against the curated field
  corpora before tier assignment; venue-specific rules that conflict with astro
  usage (`landscape`, blanket `demonstrate`/`significantly` bans) were
  deliberately **not** adopted. academic-humanizer itself builds on
  blader/humanizer (MIT).
- **[blader/humanizer](https://github.com/blader/humanizer)** (MIT) — the
  `de-ai` skill's structural patterns 2.12–2.16 (false ranges, aphorism
  formulas, persuasive-authority tropes, manufactured staccato drama,
  hyphenated-pair predicates), its Pass-2 self-interrogation step, and its
  false-positive guards adapt this skill. Only its academically relevant
  structural tells were absorbed; its blog and chat-specific patterns (emoji,
  title-case headings, chatbot artifacts, curly-quote flags) and its
  `landscape`-flagging word list were deliberately not adopted, because corpus
  evidence governs here.

## License

[MIT](LICENSE) covers code, skills, documentation, and tooling authored in this
repository. User-supplied corpus contents and generated excerpts retain their
source rights and are **not** covered by this repository license.

---

<sub>**Keywords:** Claude Code plugin · agent skills · scientific writing ·
academic writing · paper review · peer review · manuscript preparation ·
AI text detection · AI-generated text · humanizer · de-AI · LaTeX · arXiv ·
astrophysics · weak gravitational lensing · cosmology · ApJ · MNRAS · PRD ·
JCAP · NSF proposal · NIH Specific Aims · research writing assistant ·
corpus-driven style · reproducibility · scientific integrity · LLM tooling.</sub>
