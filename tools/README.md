# tools/

Helpers for the `/sci-paper:paper-style` pipeline.

| Script | Purpose | Status |
|---|---|---|
| `extract_style.py` | Ingest `style-corpus/<field>/**/*.{tex,pdf}` → emit lexicon / sentence-stats / transition-inventory JSON + `style_dossier.md` + `exemplar_paragraphs.jsonl`. | v0.3 — `.tex` + `.pdf` (via pymupdf blocks-mode for paragraph segmentation; ALL-CAPS heuristic for thematic section detection) + plain text. Computes em-dash counts, per-section sentence-length stats, transition word frequencies, dossier markdown, and segment-by-paragraph exemplar bank. **Field-aware**: `--field <name>`, auto-detected when only one field exists. **PDF-aware**: standalone PDFs at the immediate tier-dir level are parsed; PDFs nested inside arXiv-source bundles are treated as figures and skipped. |
| `retrieve_exemplars.py` | Query the exemplar bank by section type + topic + field, return top-K paragraphs as `=== Exemplar i/K ===` blocks for direct context injection. | v0.2 — sentence-transformers cosine retrieval with per-corpus `.npy` cache (rebuilt automatically when JSONL is newer). Falls back to keyword overlap (`--allow-fallback`) if `sentence-transformers` is not installed. Default model: `all-MiniLM-L6-v2`. **Field-aware**. |
| `train_ai_ism_classifier.py` | Train a paragraph-level AI-ism classifier (logistic regression on word 1–2 gram TF-IDF) using corpus paragraphs as positives and `ai_ism_negatives_handcrafted.txt` as negatives. Save model to `style-profile/<field>/ai_ism_classifier.joblib`. | v0.3 — handcrafted-only negatives (≈20 default; user can extend). 5-fold stratified CV F1 ≈ 0.88 on the wgl corpus. **Field-aware**. |
| `ai_ism_lint.py` | Tier-graded anti-AI-ism linter (em-dash, Tier A zero-tolerance, Tier B frequency-capped, stubborn replacements, three-parallel, corpus-derived blacklist, **opt-in classifier `[ai-ish:<score>]`**) with `--summary` aggregate (per-tier counts + Tier B per-section density). | v0.3 — Tier A/B split synced with `/paper` SKILL; corpus blacklist auto-derived from `lexicon.json`; opt-in `--ai-classifier` runs the trained model on each paragraph and tags those above `--ai-threshold` (default 0.7). **Field-aware**: falls back to hand-rules-only when no field profile is available. |

## Dependencies

Stdlib + numpy (already present on most scientific Python installs) is enough
for the regex side of `ai_ism_lint.py` and for `extract_style.py` when the
corpus is `.tex`/`.txt`-only. For PDF corpus papers, semantic retrieval, and
the ML classifier:

```
pymupdf                # PDF text extraction
sentence-transformers  # default embedding (~80 MB model on first run)
scikit-learn + joblib  # AI-ism classifier (already pulled by sentence-transformers)
```

Install when ready:
```bash
pip install pymupdf sentence-transformers
```

Graceful degradation:
- `retrieve_exemplars.py` falls back to keyword overlap (`--allow-fallback`)
  if sentence-transformers is missing.
- `extract_style.py` skips `.pdf` corpus rows with a warning if pymupdf is
  missing.
- `ai_ism_lint.py` only loads the classifier when `--ai-classifier` is passed;
  if the model file is missing it prints a clear "train one with…" hint.

Planned (no concrete deadline):
```
regex   # Unicode-aware sentence segmentation (v0.4 — minor improvement)
```

## Conventions

- All scripts read from `<repo>/style-corpus/<field>/` and write to
  `<repo>/style-profile/<field>/`.
- All scripts accept `--field <name>` (auto-detected when only one field
  exists) plus `--corpus-root` / `--profile-root` overrides.
- Emit JSON with `indent=2` and stable key ordering for diff-ability.
- Never print absolute paths from outside the plugin tree (privacy hygiene
  if the user shares a snippet).

## Roadmap

- [x] v0.2: Embedding-based exemplar retrieval (sentence-transformers + `.npy` cache).
- [x] v0.2: Tier-graded `ai_ism_lint.py` with `--summary` per-section density.
- [x] v0.3: PDF parsing via `pymupdf` blocks-mode; ALL-CAPS heuristic for
      thematic section detection on top of keyword-based detector.
- [x] v0.3: Paragraph-level AI-ism classifier (logistic regression on word
      1–2 gram TF-IDF). Positives = corpus paragraphs; negatives = handcrafted
      AI-style WGL paragraphs in `ai_ism_negatives_handcrafted.txt` (extend
      to improve quality). CV F1 ≈ 0.88 with 20 negatives. Opt-in via
      `ai_ism_lint.py --ai-classifier`.
- [x] v0.2: Multi-field profiles under `style-profile/<field>/` with
      auto-detection from corpus content (single-field case).
- [ ] v0.4: Improve negatives by adding LLM-drafted samples from real
      Claude/GPT outputs (rather than handcrafted by Claude itself).
