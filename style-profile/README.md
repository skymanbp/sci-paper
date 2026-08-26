# style-profile/

Field-scoped evidence consumed by `/sci-paper:de-ai`, the unified feedback
CLI, and the rewrite tools. Normative policy lives in
`docs/SCIPAPER_STANDARD.md`; profile artifacts describe a corpus or record a
calibration and cannot create an authorship verdict or redefine consequence
classes.

Generated and user-labelled profile contents are local and gitignored because
they may contain corpus-derived or unpublished text.

## Layout

```text
style-profile/
└── <field>/
    ├── lexicon.json                       # descriptive word counts
    ├── sentence_stats.json                # section-level sentence statistics
    ├── transition_inventory.json          # paragraph-initial transitions
    ├── exemplar_paragraphs.jsonl          # section/topic-tagged exemplars
    ├── style_dossier.md                   # compact generated evidence summary
    ├── exemplar_embeddings_<model>.npy    # retrieval cache
    ├── ai_ism_classifier.joblib           # legacy word-ngram style classifier
    ├── structure_baseline.json             # sentence-template reference data
    ├── uid_baseline.json                   # optional surprisal/UID reference data
    ├── docstructure_baseline.json          # optional complete-document baseline
    ├── salience_baseline.json              # per-section salience reference (deai_salience.py --calibrate)
    ├── register_lexicon.json               # corpus document frequency (deai_register.py --calibrate)
    ├── deai_policy.json                    # optional calibrated operating points
    ├── voice_model.joblib                  # optional learned field-similarity model
    ├── voice_features_cache.npz            # learned-model feature cache
    ├── voice_model_evaluation.json         # learned-model audit record (train_voice_model.py)
    ├── anchoring_baseline.json             # claim-anchoring band (deai_anchoring.py --calibrate)
    ├── ai_ism_negatives_*.jsonl            # harvested negative paragraph banks
    ├── human_*_extra.jsonl                 # supplementary human-positive banks
    ├── human_wl_toptier.jsonl              # subfield-restricted human bank (stored, not wired)
    ├── docval/                             # document-level validation working set
    └── hardset/
        ├── deai_hardset_key.csv             # local item key/provenance
        └── deai_hardset_LABEL_ME.csv        # user-authored difficult-case labels
```

Two fields are populated locally as of 2026-08-25: `wgl` (the full asset set
above, built from 19 curated papers plus the 500-paper `fulltext-arxiv/` breadth
corpus) and `wgl-letter` (descriptive subset —
lexicon, sentence stats, transitions, exemplars, dossier — built from the
11-paper Letter-register corpus for `--field wgl-letter`).

An absent artifact remains absent evidence. The corresponding axis must report
`unmeasured` or `degraded`; tools must not convert absence into zero findings.
In particular, a `voice_model.joblib` bundle without a documented operating
point is degraded, and paragraph exemplars cannot calibrate whole-document
shape.

## Build boundaries

`build_profile.py` is deliberately a **basic descriptive-profile builder**. It
runs style extraction, optionally trains the legacy word-ngram classifier, and
optionally warms the exemplar embedding cache:

```bash
python tools/build_profile.py --field <name>
```

It does **not** create calibrated L1/L2/L3 policy. Build those assets explicitly
and preserve their provenance:

```bash
# Sentence-template reference fractions from the field exemplar bank
python tools/deai_structure.py --field <name> --calibrate

# Optional token-surprisal/UID baseline; requires transformers + torch/model assets
python tools/deai_oracle.py --field <name> --calibrate

# Whole-document calibration; the corpus directory must contain independent,
# complete .tex/.md papers rather than paragraphs sampled from one paper
python tools/deai_docstructure.py --field <name> --calibrate \
  --corpus-dir <private-complete-document-directory>

# Per-section salience reference (L2.salience_hierarchy) from the passage banks
python tools/deai_salience.py --field <name> --calibrate

# Corpus document frequency for the domain-register axis (L0.register)
python tools/deai_register.py --field <name> --calibrate

# Optional learned field-similarity model; still degraded until the recorded
# confound audit and operating point justify stronger use
python tools/train_voice_model.py --field <name>
```

> **Recalibrate after v0.28.0.** Two rounds of corpus-layer defects were fixed
> on 2026-08-25. Section labelling: `classify_section` matched titles in the
> singular only, `method` was itself the default bucket and absorbed every
> unnamed heading, and PDF "paragraphs" were line fragments. Then what counts as
> a paper: `\include` fragments were counted as separate papers, selecting the
> root instead lost the body it includes, the root-selector and the reader
> resolved `\input` targets differently, and a `\subsection` did not inherit
> its `\section` — which sent 54.8% of all section words to `unknown`. The
> 500-paper `fulltext-arxiv/` breadth corpus was also invisible to every
> paragraph-level baseline.
>
> Rebuilding against all of it takes the exemplar bank from 593 to **25,005**
> paragraphs and `results` from 26 to **3,118**, so every bucket clears the
> 30-passage floor and none is rank-only.
>
> **Until you rebuild, treat every section-keyed axis as `degraded`** whatever
> its recorded status says: rerun `build_profile.py` and then each `--calibrate`
> above. `docs/architecture/EVALUATION.md` §2 carries the same notice.

Snapshot before any rebuild — a recalibration overwrites artifacts that can take
hours of GPU time to regenerate:

```bash
cp -r style-profile ".backups/style-profile-$(date +%Y%m%d-%H%M%S)"
```

`.backups/` is gitignored and lives **inside the repository**. A snapshot placed
beside it instead reads as a project of its own in the parent directory, and it
holds copies of the same corpus-derived, copyright-sensitive artifacts these
rules exclude, so it must not drift outside the repository's ignore rules.

`deai_policy.json` is not synthesized by the basic builder. Add it only when the
sample unit, corpus selection, uncertainty, applicability, operating point, and
validation behavior are documented in the asset and `EVALUATION.md`. For the
`wgl` field this asset is **not** obtainable: EVALUATION §16 measures both
statistics it would threshold and finds burstiness reverses sign on adversarial
prose while signposting runs below chance, so `L1.distribution` and
`L2.sentence_structure` stay `degraded` by measurement.

## Regeneration discipline

Do not hand-edit generated JSON, JSONL, dossier, model, or cache artifacts. If an
extraction is wrong, correct the corpus source or extractor and regenerate so
the evidence remains reproducible. The hard-set label file is the exception: it
is explicit local user input and must retain its item keys and provenance.

With one field, tools may auto-detect it; with multiple fields, pass
`--field <name>` explicitly.

## Privacy and copyright

`exemplar_paragraphs.jsonl`, `style_dossier.md`, hard-set files, feature caches,
and model bundles can expose corpus or unpublished project content. Root
`.gitignore` excludes them. Do not commit them or paste them into public issues;
regenerate locally from authorized sources.
