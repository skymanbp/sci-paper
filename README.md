# sci-paper

A Claude Code plugin for scientific writing, rewriting, source-traced review,
figure review, narrative analysis, adversarial critique, and research ideation.

The single normative authority is
[`docs/SCIPAPER_STANDARD.md`](docs/SCIPAPER_STANDARD.md) (v3). It defines scientific
integrity blockers, narrow L0 rewrite targets, ranked advisories, explicit measurement
states, author dispositions, and scientific-fidelity requirements. It also **is** the
de-AI standard: the layered signal model (L0–L4), the document-scale detection core,
the cooperative repair layer, the `calibration_unit` confidence cap, the ordered
de-AI-ization procedure (§5.2), and a disposition for every open item all live in that
one file — there is no separate de-AI standard. Corpus profiles and learned models
provide evidence; they do not define a separate paper verdict.

## What it ships

### Skills (10)

| Skill | Purpose |
|---|---|
| `paper` | Normative scientific-writing framework: accuracy, formula and citation rules, forward narrative, L0 policy, positive voice guidance, measurement states, and stopping semantics. |
| `paper-review` | Source-traced A–R review across mathematics, physics, logic, language, structure, citations, data, interfaces, reproducibility, consistency, adversarial three-pass verification, staleness, process artifacts, draft language, citation precision, and glossary alignment. |
| `figure-review` | Reviews compiled pages at 150 DPI, traces figure/caption/data provenance, and separates scientific/build blockers from readability and aesthetic advisories. |
| `paper-style` | Loads a field corpus dossier and section-typed exemplars as descriptive evidence and positive anchors. Corpus distance never proves authorship or redefines consequence policy. |
| `brainstorm` | Radial research-direction explorer with twelve framing passes, source checks, glossary anchoring, recursive branching, and bounded search convergence. |
| `mainline` | Complete cold-read contribution-graph review. Supports several explicitly related contributions and reports scientific, narrative, and editorial consequences separately. |
| `paper-attack-tree` | Open-ended adversarial critique tree. Each critique is resolved to CONFIRMED, REFUTED, or MARGINAL on evidence, then independently assigned a consequence and disposition. |
| `final-review` | Parent orchestrator for isolated paper-review, figure-review, mainline, attack-tree, and modern-physics-review runs. Verifies a stable disposition-complete state rather than zero advisories. |
| `rewrite-in-voice` | Claim-first reconstruction. Only candidates preserving protected scientific invariants are eligible; structural, distributional, exemplar, and learned evidence rank eligible prose. |
| `proposal-polish` | Funding-proposal editing mode (NSF/NIH). Keeps the vision-and-feasibility register a paper would trim, enforces claim-feasibility matching, edits the score-forming first pages hardest, and applies the shared L0 policy. Never invents preliminary data, partners, or letters. |

See [CHANGELOG.md](CHANGELOG.md) for per-version history.

### Tools (22)

| Tool | Purpose |
|---|---|
| `tools/build_profile.py` | Builds the basic field profile: extraction, optional legacy classifier, and exemplar-cache warm-up. |
| `tools/extract_style.py` | Extracts lexicon, sentence statistics, transitions, a descriptive dossier, and a section-typed exemplar bank. |
| `tools/retrieve_exemplars.py` | Retrieves section- and topic-matched exemplar paragraphs with embedding or explicit fallback retrieval. |
| `tools/ai_ism_lint.py` | Unified L0 and advisory CLI with ranked text/JSON output and exit statuses 0/1/2. |
| `tools/length_gate.py` | Per-section prose length-budget delta gate (standard §5.3): exit 1 when NET unjustified growth between two document versions exceeds tolerance; growing sections get strong advisories; records `--allow` justifications. |
| `tools/train_ai_ism_classifier.py` | Trains the legacy word-ngram classifier used only as degraded advisory evidence. |
| `tools/extract_md_negatives.py` | Harvests candidate generated paragraphs for controlled evaluation/training. |
| `tools/ai_ism_negatives_handcrafted.txt` | Seed negative examples for the legacy classifier. |
| `tools/deai_feedback.py` | Implements `sci-paper.feedback.v1`: stable IDs, consequence classes, measurement states, dispositions, ranking, summaries, and rendering. |
| `tools/deai_metrics.py` | L1 model-free information-distribution findings with explicit calibration state. |
| `tools/deai_structure.py` | L2 sentence/paragraph construction analysis for enumeration, repeated frames, parallel runs, symmetry, and related templates. |
| `tools/deai_docstructure.py` | Whole-document rhetorical-shape analysis and complete-document calibration: dispersion band, joint (per-length-stratum) manifold, role coupling, split-conformal operating points. |
| `tools/deai_partition.py` | Fidelity-free merge/split suggestions that move a document toward the human dispersion band; suggest-only, zero-token operations. |
| `tools/deai_anchoring.py` | Section-class conditional claim-anchoring band; a writing-quality axis, explicitly not an AI-discrimination axis. |
| `tools/deai_provenance.py` | Editing-provenance ledger over the author's own draft history; labels each span AI-untouched → author-original by token edit ratio. Not an AI detector; `unmeasured` without an AI-draft ancestor. |
| `tools/deai_personal.py` | Personal dispersion baseline: compares a draft to the author's own prior papers, a confound-free same-author reference; `unmeasured` below three papers. |
| `tools/deai_oracle.py` | Optional surprisal/UID evidence; unavailable assets and compatibility thresholds remain explicit. |
| `tools/deai_features.py` | Reusable distributional, UID, punctuation, embedding, and structural features. |
| `tools/deai_voice.py` | Optional learned field-similarity triage; a bundle without an operating point is degraded and never an authorship verdict. |
| `tools/train_voice_model.py` | Trains the optional field-similarity model with source-paper grouping. Confound audits remain mandatory. |
| `tools/rewrite_reward.py` | Applies hard scientific-fidelity eligibility before ranking rewrite candidates. |
| `tools/fetch_arxiv_abstracts.py` | Fetches dated abstract corpora for controlled model evaluation/training. |

The repository validator, `tools/validate_plugin.py`, is a development/release tool and
is not counted as a shipped product tool. See [tools/README.md](tools/README.md) for the
complete registry and failure behavior.

## Core feedback model

Every finding uses `sci-paper.feedback.v1` and one consequence class:

- `integrity_blocker`: scientific/source/build contradiction that must be repaired or
  verified false;
- `l0_target`: Tier A, em-dash, or Tier B usage above one occurrence per section and
  word;
- `advisory`: structural, distributional, learned, rhetorical, clarity, or aesthetic
  evidence.

Each analysis axis reports `measured`, `degraded`, `unmeasured`, or
`not_applicable`. Strong advisories require a disposition. Ordinary advisories remain
visible and do not have to disappear.

The linter exit contract is intentionally narrow:

- `0`: no L0 target; advisories may remain;
- `1`: at least one L0 target;
- `2`: invalid input, configuration failure, or execution failure.

## Quick start

```bash
# Install optional full-pipeline dependencies.
pip install -r requirements.txt

# Validate the repository contract and run tests.
python tools/validate_plugin.py
python -m unittest discover -s tests -v

# Put field papers under style-corpus/<field>/tier-*/ and build the basic profile.
python tools/build_profile.py --field wgl

# Register the plugin for development.
claude --plugin-dir <path-to-this-repo>

# Produce unified feedback.
python tools/ai_ism_lint.py draft.tex --field wgl \
  --structure --distribution --document-structure --oracle --voice \
  --format json --output feedback.json
```

Example skill invocations:

```text
/sci-paper:paper
/sci-paper:paper-style discussion --field wgl
/sci-paper:rewrite-in-voice draft.tex --field wgl
/sci-paper:paper-review draft.tex --field wgl
/sci-paper:final-review draft.tex --field wgl
```

## Why explicit profiles and typed feedback

A single learned score cannot tell an editor what to change and is vulnerable to field,
source, section, length, jargon, and mathematical-density confounds. sci-paper instead
combines:

1. deterministic scientific and L0 rules;
2. corpus-derived descriptive statistics and exemplars;
3. sentence and whole-document structural evidence;
4. optional UID and learned field-similarity evidence;
5. claim-first rewriting with hard protected-invariant eligibility;
6. source-traced review and explicit author dispositions.

This design keeps measurements inspectable and replaceable. Missing calibration remains
visible instead of becoming a nominal score. Current performance and gaps are recorded in
[EVALUATION.md](EVALUATION.md); implementation details are in
[docs/DEAI_SUBSYSTEM.md](docs/DEAI_SUBSYSTEM.md).

## Field-aware evidence

A field is one subdirectory under `style-corpus/` with a corresponding directory under
`style-profile/`. With one field, most tools can auto-detect it; with several fields,
pass `--field <name>` explicitly.

Corpus contents are read-only, copyright-sensitive inputs. Generated dossiers and
exemplars may quote source prose and must not be published unless their rights permit it.
A corpus dossier is descriptive evidence, not a normative standard and not proof of
human or machine authorship.

Whole-document calibration requires complete papers as independent observations.
Paragraph exemplars cannot be relabelled as independent documents.

## Project structure

```text
.
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── docs/
│   ├── SCIPAPER_STANDARD.md       # sole normative writing/review contract
│   └── DEAI_SUBSYSTEM.md          # implementation architecture
├── skills/
│   ├── paper/SKILL.md
│   ├── paper-review/SKILL.md
│   ├── figure-review/SKILL.md
│   ├── paper-style/SKILL.md
│   ├── brainstorm/SKILL.md
│   ├── mainline/SKILL.md
│   ├── paper-attack-tree/SKILL.md
│   ├── final-review/SKILL.md
│   ├── rewrite-in-voice/SKILL.md
│   └── proposal-polish/SKILL.md
├── style-corpus/
│   └── <field>/tier-{1,2,3}-*/    # user-supplied read-only corpus
├── style-profile/
│   └── <field>/                   # generated/calibrated evidence
├── tests/                         # schema, linter, structure, and fidelity tests
├── tools/                         # product tools plus repository validator
├── EVALUATION.md                  # current metrics, gaps, and confounds
└── CHANGELOG.md
```

## Build and calibration boundaries

`build_profile.py` builds the basic descriptive profile and legacy assets. Optional UID,
learned field-similarity, sentence-structure, and whole-document calibration have
separate tools and evidence requirements. Do not claim a measured axis merely because a
model file exists.

A field policy asset should document:

- the independent sample unit;
- corpus selection and provenance;
- sample size;
- uncertainty method;
- operating point and applicability;
- leave-source/document-out human flag behavior;
- known confounds.

Without that record, the corresponding axis remains degraded or unmeasured.

## Development and release verification

```bash
python tools/validate_plugin.py
python -m unittest discover -s tests -v
```

The validator checks release metadata, skill frontmatter, standard references, stale
contract markers, product registries, Python syntax, runtime imports, CLI entry points,
schema fields, linter exits, Tier B behavior, tests, and CI wiring.

A release additionally requires independent code review and clean-checkout verification.

## Status

Current: **v0.20.1**. Full per-version history is in
[CHANGELOG.md](CHANGELOG.md).

- **Normative core:** `docs/SCIPAPER_STANDARD.md` v3.3 — the complete de-AI
  standard (layered model, document-scale core, cooperative layer,
  `calibration_unit` cap, the §5.2 de-AI-ization procedure, the §5.3
  condense-not-accumulate rule with mechanical enforcement, auxiliary L2
  template families with the blind perceptual panel as an L2 validation
  instrument, and a disposition for every open item). There is no separate
  de-AI standard.
- **Skills (10):** `paper`, `paper-review`, `figure-review`, `paper-style`,
  `brainstorm`, `mainline`, `paper-attack-tree`, `final-review`,
  `rewrite-in-voice`, `proposal-polish`.
- **Tools (22):** exact product registry above.
- **Current calibrated gaps:** no learned-model operating point (the L3
  document-level surprisal path is now measured not to provide one, EVALUATION.md
  §9.8), no completed author hard-set labels, and the cooperative-layer tools
  (`deai_provenance`, `deai_personal`) are honestly `unmeasured` until the author
  supplies their own draft history / prior papers. These remain explicit in
  [EVALUATION.md](EVALUATION.md).
- **Field-specific guidance:** WGL-specific scientific anchors remain marked where
  applicable. Shared writing/review policy is field-agnostic.

## Acknowledgments

- **[AIScientists-Dev/academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer)**
  (MIT). The 2026-07-16 lexicon extensions (`underscore*`, `pivotal`,
  `tapestry`, `testament`, `realm*`, `intricate`, `foster*`), the `serves as`,
  `ing-tail`, and `colon-elaboration` linter rules, the Claim–Evidence
  Discipline and Preserve List sections in `skills/paper/SKILL.md`, and the
  `proposal-polish` skill adapt its material. Every lexical adoption was
  re-verified against the curated field corpora before tier assignment;
  venue-specific rules that conflict with astro usage (`landscape`, blanket
  `demonstrate`/`significantly` bans) were deliberately not adopted.
  academic-humanizer itself builds on blader/humanizer (MIT).

## License

[MIT](LICENSE) covers code, skills, documentation, and tooling authored in this
repository. User-supplied corpus contents and generated excerpts retain their source
rights and are not covered by this repository license.
