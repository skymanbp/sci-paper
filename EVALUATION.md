# Feasibility Evaluation: Style Distillation for `sci-paper` Plugin

Date: 2026-04-27
Author: skymanbp + Claude Opus 4.7

## Question

Can we "fine-tune" or "distill" a model on a curated corpus of top-journal +
mentor + high-reference-value papers, so that AI-assisted writing in this
plugin reproduces human-academic style and avoids AI tells?

## Short answer

**No** to literal fine-tuning. **Yes** to the underlying goal, via explicit
style extraction + retrieval-augmented exemplars (RAG-for-style).

## Path-by-path analysis

### 1. Fine-tune Claude via API — IMPOSSIBLE

Anthropic does not currently offer Claude fine-tuning. There is no public
endpoint, no Bedrock/Vertex variant of fine-tuned Claude, and no leaked
beta. Verified via Anthropic docs as of 2026-01 knowledge cutoff. This path
is closed.

### 2. LoRA an OSS model (Llama/Qwen/Mistral) on the corpus — NOT RECOMMENDED

Technically possible, but:

- **Data volume is wrong by 2-3 orders of magnitude.** Style fine-tuning
  empirically needs 10⁸–10⁹ tokens to converge. A curated paper corpus is
  10⁵–10⁶ tokens. The model will overfit to surface n-grams (you'll see
  verbatim phrases from the corpus appearing in outputs) without
  internalizing the underlying style.
- **The fine-tuned model writes *worse* than Claude raw.** Even Llama-3-70B
  trained from a strong base will lag Claude on long-form scientific
  reasoning. Replacing Claude with a LoRA-Llama as your writing
  assistant is a regression for everything except surface mimicry.
- **Integration friction.** This is a Claude Code plugin. Routing some
  prompts to a local model breaks the skill model and makes review
  inconsistent.

### 3. Style profile + exemplar retrieval (RAG-for-style) — RECOMMENDED ✅

This is what `paper-style` implements. Pipeline:

#### 3a. Quantitative feature extraction

Parse each corpus paper (`.tex` preferred, PDF acceptable) and emit:

- **Per-section sentence-length distribution** — abstract / intro / methods
  / results / discussion / conclusion separately. Top journals have
  characteristic distributions (ApJ methods sections trend toward ~22 word
  median, abstracts ~28; LLMs default to ~18–20 across all sections, which
  is itself a tell).
- **Transition-word inventory.** Which connectors does the corpus actually
  use? (Spoiler: nothing like `Furthermore,` `Moreover,` `Importantly,` —
  those are LLM signatures.) Build the *whitelist* from corpus, the
  *blacklist* from absent-but-LLM-frequent.
- **Em-dash count.** Top astro/physics papers use em-dash near zero; LLMs
  use it ~5–15× per 1000 words. This is the strongest single tell.
- **Hedge-word frequency.** `arguably`, `seemingly`, `perhaps` — corpus
  papers use these *less* than LLMs.
- **Passive-voice ratio per section.** Methods runs higher passive; results
  runs lower. LLMs flatten this.
- **Formula:text density.** Tokens per displayed equation. Field-specific.
- **Opening-pattern catalog.** First sentences of paragraphs across
  sections — what verbs, what subjects, what tense?
- **Abbreviation/notation conventions.** thinspace `\,` vs space, `Eq.`
  vs `equation`, etc.

#### 3b. Compression to a style dossier

The numerical artifacts above (~10s of KB JSON) are too verbose for a
prompt. `extract_style.py` synthesizes a `style_dossier.md` of ~2000
tokens that reads like a style guide:

> **Sentence length (Methods):** median 22 words; 75th pct 32. Avoid
> Claude's default ~18 (sounds clipped). Cap at 45 unless the sentence
> carries a derivation.
>
> **Transition inventory (paragraph-initial):** `We`, `The`, `In`, `To`,
> `Following`, `Given`, `Once`. NOT in corpus: `Furthermore`, `Moreover`,
> `Importantly`, `Notably`, `Crucially`, `Additionally`. (0 occurrences
> across N=42 papers, 31k paragraphs.)
>
> **Em-dash:** 0.4 per paper across corpus. Default to en-dash (`--`) for
> ranges; use comma/colon/parenthesis for asides. Never em-dash.
>
> ...

This file IS the prompt-time payload. Claude reads it and conditions
on it, much like a human writer reading the journal's style sheet.

#### 3c. Section-typed exemplar bank

For each section type, retain the top-K (~50) paragraphs from corpus,
indexed by section type and topic embedding. At write time, given
"I'm drafting the Discussion of a weak-lensing paper", retrieve the 5
nearest Discussion paragraphs (by topic embedding) and inject as
positive style anchors.

This is the part that gives you "writes *like* Smith et al. 2024" — the
model sees the actual rhythm and is asked to match it.

#### 3d. Data-driven anti-AI-ism extension

The current `paper` skill has a hand-written blacklist (`leverage`,
`utilize`, `delve into`, etc.). Extend it by computing:

- Words/phrases in LLM-typical writing whose corpus frequency is < 0.1×
  expected → add to blacklist with corpus-frequency evidence.
- Top-50 most-distinctive corpus n-grams not in LLM defaults → add to
  whitelist as "phrases worth using".

### 4. Sentence-level AI-ism classifier — OPTIONAL ADD-ON

Train a simple classifier (logistic regression on TF-IDF + length + char
features, or embedding distance to corpus mean) to flag candidate sentences
as "looks-like-LLM" vs "looks-like-corpus". Use as a final-pass linter.
Cheap to train, complements the rule-based grep.

## Implementation plan

| Phase | Output | Effort |
|---|---|---|
| 0 (done) | Plugin scaffold; ported skills; `paper-style/SKILL.md` spec; tool stubs. | Small. |
| 1 | Working `extract_style.py` for `.tex` source: sentence stats, em-dash count, transition inventory, lexicon, dossier generation. | ~½ day. |
| 2 | PDF parsing (`pymupdf` text extraction) for papers without LaTeX source. Section detection by heuristic (regex on `\section{…}` or PDF font-size jumps). | ~½ day. |
| 3 | Exemplar retrieval (`retrieve_exemplars.py`): paragraph chunking, embedding via `sentence-transformers`, cosine NN. | ~½ day. |
| 4 | Linter (`ai_ism_lint.py`): existing greps + corpus-frequency-driven additions. | ~2 hours. |
| 5 | Optional sentence classifier. | ~½ day. |
| 6 | De-WGL-ify the ported skills (remove ACSDM / NFW / E-mode references, keep generic structure). | ~2 hours. |

## Honest risks / limitations

1. **Corpus availability.** Mentor papers are presumably accessible; top-journal
   PDFs may have access constraints (institutional). Tracking them in
   `.gitignore` is mandatory — don't commit copyrighted PDFs.

2. **Section detection on PDFs is lossy.** Heuristic section boundaries fail
   on conference papers, two-column merged figures, and non-English macros.
   Recommend `.tex` source where possible; fall back to PDF only when needed.

3. **Style is field-specific.** A profile built from astrophysics papers will
   transfer poorly to bio or condensed-matter writing. **Implemented (v0.1):**
   per-field profiles under `style-corpus/<field>/` and `style-profile/<field>/`.
   Currently `wgl` is the only populated field; tools auto-detect when only
   one exists, or require `--field <name>` when multiple are present.

4. **Overfitting to mentor.** If tier-2-mentor is small (3–5 papers) and the
   weighting in the dossier is naïve, the style will mimic that mentor's
   idiosyncrasies including their bad ones. Solution: weight tiers
   (top-journal: 0.5, mentor: 0.3, references: 0.2) or have the dossier-
   generation prompt explicitly note "mentor-specific quirks may not
   generalize".

5. **The "no AI-ism" goal can't be fully won by rules alone.** Reviewers also
   read for *substance* tells (over-confident hedging, redundant explanation
   of well-known concepts, suspicious uniformity of paragraph length). The
   dossier should include positive guidance on these too, not only word
   blacklists.

## Decision

Ship `paper-style` as the headline new feature, delivered via the RAG-for-style
pipeline above. Do not pursue actual fine-tuning of any model.
