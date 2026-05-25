# style-profile/

Generated style artifacts consumed by `/sci-paper:paper-style` and the
linting tools. **Contents are NOT committed** (see `.gitignore`) — they
are regenerable from the corpus and may contain corpus-derived text.

## Layout

```
style-profile/
└── <field>/                              # mirrors style-corpus/<field>/
    ├── lexicon.json                      # word frequencies, tier-weighted
    ├── sentence_stats.json               # per-section sentence-length distributions
    ├── transition_inventory.json         # paragraph-initial transitions, with counts
    ├── exemplar_paragraphs.jsonl         # one paragraph per line, with section + topic
    ├── style_dossier.md                  # ~2k-token compact style guide (loaded into Claude's context)
    ├── exemplar_embeddings_<model>.npy   # sentence-transformers cache (rebuilt when JSONL is newer)
    └── ai_ism_classifier.joblib          # logistic-regression AI-ism classifier (sklearn)
```

The directory itself (and per-field subdirs) is tracked via `.gitkeep`
placeholders so the layout is documented in git, but every generated file
matches a pattern in the root `.gitignore`.

## Rebuilding

```bash
# Full rebuild (extract → train → warm embedding cache):
python tools/build_profile.py

# Or step by step:
python tools/extract_style.py --field <name>          # writes JSON / dossier / JSONL
python tools/train_ai_ism_classifier.py --field <name> # writes ai_ism_classifier.joblib
python tools/retrieve_exemplars.py \
    --section method --topic "warmup" --field <name>   # warms exemplar_embeddings_<model>.npy
```

When only one field exists under `style-corpus/`, all tools auto-detect
it; with multiple, `--field <name>` is required.

## Privacy / copyright note

`exemplar_paragraphs.jsonl` and `style_dossier.md` quote sentences /
paragraphs from corpus PDFs. Because the corpus itself is gitignored as
copyright-sensitive, **these generated artifacts are also gitignored**;
do not commit them or paste them into public issues. Regenerate locally
on each machine.
