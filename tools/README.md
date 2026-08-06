# tools/

Runtime helpers for the sci-paper profile, feedback, de-AI, rewrite, and validation
pipeline. Normative policy lives in `docs/SCIPAPER_STANDARD.md`; tools measure and
serialize evidence but do not define an independent paper verdict.

## Registry

| File | Purpose | Calibration / failure behavior |
|---|---|---|
| `build_profile.py` | Builds the basic descriptive profile, optionally trains the legacy classifier, and warms the exemplar cache. | Aborts on extraction failure; reports optional-stage failures and continues. It does not create calibrated L1/L2/L3 policy. |
| `extract_style.py` | Builds descriptive lexicon, sentence statistics, transition inventory, dossier, and exemplar bank from `.tex`, `.pdf`, or text corpora. | PDF extraction is unavailable without pymupdf; corpus observations do not redefine policy. |
| `retrieve_exemplars.py` | Retrieves section- and topic-matched exemplar paragraphs. | Uses sentence-transformer cosine when installed; keyword fallback requires `--allow-fallback`. |
| `train_ai_ism_classifier.py` | Trains the legacy word-ngram paragraph classifier. | Output is degraded L3 advisory evidence, not authorship evidence or an L0 gate. |
| `extract_md_negatives.py` | Harvests candidate negative paragraphs from a document tree. | Generated data are privacy-sensitive and remain profile-local/gitignored. |
| `ai_ism_negatives_handcrafted.txt` | Seed negative examples for the legacy classifier. | Data asset, not normative prose policy. |
| `deai_feedback.py` | Implements `sci-paper.feedback.v1`: stable IDs, consequence classes, measurement states, dispositions, ranking, summaries, text/JSON rendering, and tuple compatibility. | Stdlib-only shared contract. |
| `ai_ism_lint.py` | Unified L0 and advisory CLI. Emits ranked text or JSON from the same findings. | Exit 0 = no L0 target; 1 = L0 target present; 2 = invalid input/configuration/execution. Advisories never cause exit 1. |
| `length_gate.py` | Per-section rendered-prose length-budget delta gate between two document versions (standard §5.3). Growing sections emit strong advisories; `--allow` records justifications. | Exit 0 = net unjustified growth within tolerance; 1 = net unjustified growth beyond it; 2 = invalid input/execution. Comments and math are excluded; a pure section rename nets to zero. |
| `deai_metrics.py` | L1 information-distribution analysis: sentence-length variation and connective-openers. | Strong status requires applicable policy calibration; compatibility heuristics are degraded. |
| `deai_structure.py` | L2 sentence-template analysis: enumeration, ordinal/modal/parallel runs, setup-list-wrap-up patterns, and balanced closers. | Strong status requires calibrated policy and sufficient reference sample. |
| `deai_docstructure.py` | L2 whole-document rhetorical-shape analysis and complete-document calibration: shape similarity, dispersion band, joint Mahalanobis manifold (pooled and per-length-stratum), role-coupled dispersion, and split-conformal operating points. | Requires at least three measurable complete documents and sufficient sections/paragraphs; otherwise unmeasured. Legacy baselines without a conformal block fall back to percentile thresholds; factor-drifted role references disable that axis. |
| `deai_partition.py` | Fidelity-free partition suggestions (merge/split of paragraph blocks) that move a document toward the calibrated human dispersion band. Suggest-only; the author applies changes by hand. | Zero-token operations, so rewrite fidelity holds by construction; cohesion is self-normalized to the document's median adjacent-pair overlap; section-command blocks are never candidates; reordering is deliberately not offered. Without a calibrated manifold the tool exits with an explicit message. |
| `deai_anchoring.py` | L2 claim-anchoring band: section-class conditional anchored-sentence rates against the human corpus, low-tail conformal with a Bonferroni share per class. | A writing-quality axis, not an AI-discrimination axis (EVALUATION.md 9.6 records the refuted tell). Classes below the 30-document minimum are honestly omitted; unmeasurable documents degrade to unmeasured. |
| `deai_provenance.py` | Editing-provenance ledger (frontier idea 4): matches each current paragraph to a designated AI-draft ancestor (file or git ref from the author's own history) and labels the span AI-untouched / lightly-edited / rewritten / author-original by a deterministic difflib token edit ratio. | Not an AI detector; reads only the author's own history. `unmeasured` without an ancestor or when the file has no git history for the given ref (never a guess). |
| `deai_personal.py` | Personal dispersion baseline (frontier idea 6): places a draft's per-feature within-document dispersion in the distribution of the author's own prior papers, a confound-free same-author reference. | Model-free; reuses `document_shape`. `unmeasured` below three measured prior papers. Flags a draft that varies paragraph shape far less than the author's own papers on at least 40% of features. |
| `deai_oracle.py` | Optional token-surprisal and UID analysis. | Requires transformers/model assets for measurement; compatibility `FLAG_Z` is degraded until field calibration exists. Document-level surprisal is measured (EVALUATION.md 9.8) to be weaker than the model-free manifold and adds nothing to it. |
| `deai_features.py` | Reusable model-free, UID, and embedding features for document analysis and learned field-similarity models. | Optional model features degrade when dependencies/assets are unavailable. |
| `deai_voice.py` | Optional learned field-similarity triage. | Refuses bundles with drifted feature names/schema and degrades on corrupt bundles. A measured operating point gates threshold findings; an uncalibrated bundle yields rank-based triage of the lowest-scoring paragraphs, never a universal 0.5 cutoff. |
| `train_voice_model.py` | Trains the optional learned field-similarity/rewrite-ranking model and writes `voice_model_evaluation.json`. | Cache reuse requires a content/model/centroid fingerprint; featurization checkpoints every 500 rows for preemptible runs. Grouped splits recompute `corpus_cos` from training-only centroids; repeated source-group splits audit source, section, length, mathematical-marker, field-term, matched-stratum, and UID-normalization sensitivity, plus the author-labelled hard-set stratum, without creating an operating point. |
| `rewrite_reward.py` | Evaluates rewrite candidates after hard scientific-fidelity eligibility. | Bidirectional: dropping OR inventing protected numbers, units, citations, math, acronyms, semantic LaTeX macros, comparison direction, negation, or causal direction makes a candidate ineligible (`-inf`). Ranking is led by L0 advisory reduction (signed, fidelity-floored) and semantic fidelity; the learned score is tie-break weight unless its bundle is measured. |
| `fetch_arxiv_abstracts.py` | Fetches dated arXiv abstract corpora for controlled model evaluation/training. | Network failures are explicit; fetched text is evidence/training data, not policy. |
| `validate_plugin.py` | Validates manifests, version/count agreement (including the versioned doc headers of DEAI_SUBSYSTEM/EVALUATION), skill frontmatter and standard references, normative/evaluation document authority, stale review markers, Python syntax, runtime imports, CLI entry points, feedback schema, linter exits, required tests, and CI wiring. | Stdlib-only; rejects active duplicate evaluation records and exits nonzero on contract drift. |

The top-level manifest counts 22 product tools: the 21 shipped Python tools plus the
`ai_ism_negatives_handcrafted.txt` data asset. `validate_plugin.py` is a
development/release tool and is excluded from that count.

## Dependencies

The shared schema, regex linter, model-free L1/L2 analysis, document structure,
and validator use the standard library. Optional capabilities add:

```text
pymupdf                PDF corpus extraction and compiled-page rendering
sentence-transformers  semantic exemplar retrieval and embedding features
scikit-learn + joblib  legacy and learned field-similarity models
transformers + torch   token-surprisal / UID measurement
numpy                   learned feature/model utilities
```

Do not install optional dependencies merely to turn an unavailable axis into a
nominal score. Missing assets remain `unmeasured`; compatibility thresholds remain
`degraded`.

## Common commands

```bash
# Validate repository and active contract
python tools/validate_plugin.py

# Run all unit and CLI tests
python -m unittest discover -s tests -v

# Build/update one field profile
python tools/build_profile.py --field wgl

# Unified feedback report
python tools/ai_ism_lint.py draft.tex --field wgl \
  --structure --distribution --document-structure --oracle --voice \
  --format json --output feedback.json

# Calibrate whole-document shape from a directory of verified complete
# documents (independent .tex/.md papers, not paragraphs of one paper)
python tools/deai_docstructure.py --field <field> --calibrate \
  --corpus-dir <private-complete-document-directory>

# Rebuild the learned model and repeated source-group confound audit
python tools/train_voice_model.py --field <field> --refeature --audit-splits 20
```

## Conventions

- Field corpora live under `style-corpus/<field>/`; generated evidence lives under
  `style-profile/<field>/`.
- JSON is UTF-8, indented, and stable enough for reviewable diffs.
- Human-readable output and JSON are projections of the same structured findings.
- Missing measurements are never converted to zero findings.
- Sample counts, operating points, confidence intervals, effect sizes, and model
  metrics belong in `EVALUATION.md` or profile assets, not the normative standard.
- Complete documents, not paragraphs from one document, are the independent units
  for document-level calibration.
- Learned scores describe field similarity/triage and never prove authorship.
- Rewrite ranking optimizes faithful scientific prose, not detector evasion.
- Never print external absolute paths in shareable output.
