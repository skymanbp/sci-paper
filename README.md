# sci-paper

A Claude Code plugin for scientific writing, rewriting, source-traced review,
figure review, narrative analysis, adversarial critique, and research ideation.

The single normative authority is
[`docs/SCIPAPER_STANDARD.md`](docs/SCIPAPER_STANDARD.md). It defines scientific
integrity blockers, narrow L0 rewrite targets, ranked advisories, explicit measurement
states, author dispositions, and scientific-fidelity requirements. Corpus profiles and
learned models provide evidence; they do not define a separate paper verdict.

## What it ships

### Skills (9)

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

See [CHANGELOG.md](CHANGELOG.md) for per-version history.

### Tools (17)

| Tool | Purpose |
|---|---|
| `tools/build_profile.py` | Builds the basic field profile: extraction, optional legacy classifier, and exemplar-cache warm-up. |
| `tools/extract_style.py` | Extracts lexicon, sentence statistics, transitions, a descriptive dossier, and a section-typed exemplar bank. |
| `tools/retrieve_exemplars.py` | Retrieves section- and topic-matched exemplar paragraphs with embedding or explicit fallback retrieval. |
| `tools/ai_ism_lint.py` | Unified L0 and advisory CLI with ranked text/JSON output and exit statuses 0/1/2. |
| `tools/train_ai_ism_classifier.py` | Trains the legacy word-ngram classifier used only as degraded advisory evidence. |
| `tools/extract_md_negatives.py` | Harvests candidate generated paragraphs for controlled evaluation/training. |
| `tools/ai_ism_negatives_handcrafted.txt` | Seed negative examples for the legacy classifier. |
| `tools/deai_feedback.py` | Implements `sci-paper.feedback.v1`: stable IDs, consequence classes, measurement states, dispositions, ranking, summaries, and rendering. |
| `tools/deai_metrics.py` | L1 model-free information-distribution findings with explicit calibration state. |
| `tools/deai_structure.py` | L2 sentence/paragraph construction analysis for enumeration, repeated frames, parallel runs, symmetry, and related templates. |
| `tools/deai_docstructure.py` | Whole-document rhetorical-shape analysis and complete-document calibration. |
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
│   └── rewrite-in-voice/SKILL.md
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

Current: **v0.14.0**. Full per-version history is in
[CHANGELOG.md](CHANGELOG.md).

- **Skills (9):** `paper`, `paper-review`, `figure-review`, `paper-style`,
  `brainstorm`, `mainline`, `paper-attack-tree`, `final-review`,
  `rewrite-in-voice`.
- **Tools (17):** exact product registry above.
- **Current calibrated gaps:** no `wgl` complete-document baseline, no learned-model
  operating point, no completed author hard-set labels, and unresolved learned-model
  confound audit. These remain explicit in [EVALUATION.md](EVALUATION.md).
- **Field-specific guidance:** WGL-specific scientific anchors remain marked where
  applicable. Shared writing/review policy is field-agnostic.

## License

[MIT](LICENSE) covers code, skills, documentation, and tooling authored in this
repository. User-supplied corpus contents and generated excerpts retain their source
rights and are not covered by this repository license.
