# De-AI subsystem — design & build plan (v0.13.0)

**Goal.** Make drafts read like a human scientist, not a machine — at the
*root* level (sentence architecture, argument shape, information
distribution), not by scrubbing keywords. Keyword lint stays as a backstop;
it is not the mechanism.

## 0. Thesis (the one signal)

Every AI-vs-human text signal in the literature — perplexity, burstiness,
DetectGPT curvature, Binoculars cross-perplexity, GLTR token-rank, GPT-who
UID — is a different lens on **one property: the distribution of per-token
surprisal**. Human writing is *bursty* (high surprisal variance, sharp local
spikes, tail-drawn tokens); MLE-trained LLM writing is *smoothed* toward
Uniform Information Density and its own high-probability region. Swapping
words does not change that distribution, which is why keyword de-AI is
cosmetic and AI prose is "hard to remove."

Two feature tiers, weighted differently:

- **Fundamental (hard to spoof) — the "voice":** surprisal/UID variance,
  sentence-length variance, syntactic-structure variety, probability
  curvature, cross-perplexity. Model-free syntactic projections
  (sentence-length variance, dependency/constituent variety) are the most
  *robust* because they need only a tokenizer/parser.
- **Keyword (brittle, gameable) — "tells to avoid":** the corpus-derived
  excess-vocabulary list (delve/underscore/…). Kept as a backstop only.

## 1. Four guardrails (non-negotiable; from the research caveats)

1. **Calibrate against the human reference corpus, per genre. Never
   hard-code absolute thresholds.** Direction and magnitude of nearly every
   feature drift by genre and model generation (hedging is *down* in AI
   essays but *up* in AI abstracts; lexical diversity no longer separates
   modern LLMs). All thresholds derive from `style-profile/<field>/`.
2. **Diagnostic, not gate.** Surprisal / detector scores flag *which
   paragraphs to rewrite*; they never become a pass/fail convergence
   criterion. Reasons: (a) formal science prose is formulaic and
   false-positives on likelihood detectors; (b) optimizing to beat a
   detector is a losing arms race (Pangram's DAMAGE re-detects 19
   humanizers).
3. **Optimize for genuine voice / specificity / stance** — real qualities
   that are robust because they are real — not for detector evasion.
4. **The excess-vocabulary lexicon is data to re-derive**, not a frozen
   constant. Re-estimate as models/corpus change.

## 2. Three layers

### Layer A — distributional scorer (model-free, ships first)
`tools/deai_metrics.py`. Reuses `extract_style.py` tokenizers
(`sentences`, `words`, `paragraph_initial_words`, `split_into_sections`,
`classify_section`, `latex_to_plain`) so a draft's distributions are
directly comparable to the corpus reference. Per section, scores vs
`style-profile/<field>/{sentence_stats,transition_inventory,
distribution_baselines}.json`:

- **Burstiness / sentence-length variance** (Desaire, GPTZero, Muñoz-Ortiz):
  flag sections whose sentence-length coefficient-of-variation is below the
  human reference.
- **Opener over-signposting:** fraction of paragraphs opening with a
  connective (Furthermore/Moreover/However/…). Human corpus ≈ 0.1–0.2 %;
  flag over-use.
- **Desaire science features:** paragraph length (sentences/para), equivocal
  connective density (but/however/although), punctuation richness
  (parentheses, semicolons, question marks) — all vs corpus baselines
  emitted by an extended `extract_style.py`.

Emits `(line, rule, excerpt)` hits into `ai_ism_lint.lint()`'s aggregation
(the `[ai-ish:*]` path is the template) so it auto-propagates into
`paper-style §2d` and `paper-review §2.D` loops. New `severity_order`
bucket. **Diagnostic 🟡, never a 🔴 gate.**

### Layer B — surprisal / UID + detector oracle (local, GPU)
`tools/deai_oracle.py`. torch 2.8 + CUDA present.

- **UID feature vector** (GPT-who, arXiv 2310.06202): per-token surprisal
  under a local LM → global UID (surprisal variance) + local UID
  (consecutive-token surprisal jumps). The operational core of "voice."
- **Detector score:** RADAR (IBM, Apache-2.0, single RoBERTa forward pass,
  fully local, paraphrase-robust) as the per-paragraph AI-ness flag;
  optionally Binoculars (cross-perplexity of two small models) as a second,
  orthogonal signal.
- **Embedding-manifold distance:** reuse the cached
  `exemplar_embeddings_all-MiniLM-L6-v2.npy` to measure a paragraph's
  distance from the corpus manifold.

Calibrated against the 31-paper corpus's own paragraph score distribution
(flag paragraphs *more uniform / lower-surprisal-variance than the human
corpus*), validated on RAID's ArXiv-Abstracts domain before trust.
**Diagnostic only.**

### Layer C — claim-graph → skeleton → voice regeneration (the deep fix)
New skill `/sci-paper:rewrite-in-voice` (+ orchestration). You cannot
launder AI prose — the AI-ness lives in the sentence structure, so we don't
edit it, we rebuild from the argument:

1. Extract the **claim-graph** from the draft (claims, evidence, causal
   links) — ignore the prose.
2. Emit a **fill-in skeleton** (same mechanism as the the manuscript paper skeleton)
   — forces human sentence construction; the AI skeleton cannot survive.
3. Regenerate each slot in the **author's own voice**: condition on the
   author's prior human paragraphs (`retrieve_exemplars.py`, already
   embedding-based) as few-shot anchors + constraints (commit to a claim,
   ≥1 specific number/detail per paragraph, forbid meta-commentary, hit the
   sentence-length-variance target).
4. Score with Layers A+B; iterate the worst paragraphs.

Voice-transfer machinery to borrow: StyleRemix (EMNLP24, style-axis LoRA),
STRAP (EMNLP20, style-transfer-as-paraphrase), DIPPER control codes
(NeurIPS23).

**Auto-writing systems — verified: none handle voice/AI-tell** (checked
STORM, AI-Scientist v1/v2, gpt-researcher, PaperQA2, gpt-researcher,
data-to-paper, Agent Laboratory — all optimize grounding or automated
review-score, never human-likeness). So the voice layer is a genuine gap,
and these systems are *complementary substrates* to borrow from, not
competitors:

- **PaperQA2** (Apache-2.0) RCS re-rank+contextual-summarize retrieval — the
  grounding substrate so a voice rewrite never fabricates a citation.
- **data-to-paper** (MIT) backward numeric traceability — voice-editing must
  keep every number click-traceable (our R2). 
- **STORM** (MIT) perspective-guided simulated-conversation outline — the
  antidote to flat/templated AI *structure* (itself a tell); feeds Layer C's
  claim-graph with non-generic section logic.
- **AI-Scientist v1** ensemble review-and-revise loop — reuse the
  *iterate-until-rubric-passes* shape, with the rubric = Layers A+B (this is
  the de-AI convergence engine of `/rewrite-in-voice`).
- **Agent Laboratory / Co-STORM** staged human-in-the-loop checkpoints — pause
  at section boundaries for author steering (keeps the human's voice in).

### Layer D — learned voice model + self-improvement loop
The heuristic scorers (A) and off-the-shelf oracles (B) are the floor. The
ceiling is a model that **learns real hand-written scientific voice from the
corpus and keeps improving**.

- **Learned voice model (reward model).** Train on the human corpus
  (positives: `exemplar_paragraphs.jsonl`, 31 papers) vs harvested LLM
  drafts (negatives: `extract_md_negatives.py`). Features are the
  **fundamental** ones — Layer A distributional stats + Layer B surprisal/UID
  + sentence embeddings — **not** word-ngram TF-IDF (which just re-learns the
  keyword tells and is the current classifier's ceiling). Output: a
  calibrated per-paragraph *human-voice score*. This score is the **reward**.
- **Self-improvement, three rungs (increasing cost):**
  1. **Best-of-N (no training, ships first).** The rewriter generates N
     candidates; the voice model + semantic-fidelity (embedding sim to the
     claim) + specificity (carries a number) pick the best. "Poor-man's RL,"
     high ROI, no GPU training.
  2. **Self-distillation (ongoing).** Human-accepted rewrites → new positives
     → periodically retrain the voice model and optionally SFT a small
     generator (LoRA). The plugin gets better the more it is used.
  3. **DPO / RL fine-tune (ceiling, GPU).** DPO on (accepted, rejected)
     rewrite pairs against the voice reward; StyleRemix-style style-axis LoRA.
     Sequenced last, on a *validated* reward.
- **Reward-design guardrail (critical, from the research):** the target is
  *match the human-voice distribution + preserve meaning / specificity /
  stance*, **never "evade a detector"** — detector-as-reward yields evasion
  that reads worse and loses an arms race (AuthorMist → Pangram DAMAGE
  re-detects 19 humanizers). Hold out papers and add a diversity penalty to
  avoid overfitting to the 31 authors' tics (mode collapse).

## 3. Verified external resources (2026-07-11)

| Use | Resource | Note |
|---|---|---|
| Local detector oracle | RADAR — github.com/IBM/RADAR (Apache-2.0) | single RoBERTa pass, local, paraphrase-robust |
| Zero-shot oracle (2nd) | Binoculars — github.com/ahans30/Binoculars (BSD-3) | cross-perplexity; two ~7B models, GPU |
| UID feature defs | GPT-who — arXiv 2310.06202 | 44-dim surprisal-variance vector |
| Science-prose features | Desaire — arXiv 2303.16352 | model-free, 99% on science paragraphs |
| Excess-vocab lexicon | Kobak — arXiv 2406.07016 / sciadv.adt3813 | re-derivable science avoid-word set |
| Voice transfer | StyleRemix EMNLP24 / STRAP EMNLP20 / DIPPER NeurIPS23 | style-axis / paraphrase transfer |
| Calibration test-bed | RAID ArXiv-Abstracts — arXiv 2405.07940 | the only public science-prose bench |

## 4. Integration points (verified, file:line)

- `tools/ai_ism_lint.py:335` `lint()` — add distributional + oracle passes
  emitting into the `hits` list; `:287` `severity_order` — add buckets.
- `tools/extract_style.py:514` `aggregate_sentence_stats`, `:562`
  `aggregate_transitions`, `:644` `aggregate_lexicon` — add
  `distribution_baselines` (CV, paragraph length, punctuation, equivocal,
  connective-opener rate) + OOD/excess-vocab discovery.
- `tools/train_ai_ism_classifier.py:128` — swap TF-IDF word-ngram features
  for distributional+embedding features; enlarge negatives via
  `extract_md_negatives.py`.
- Skills: `paper/SKILL.md` (new fundamental tier + fix N=16→N=31 drift),
  `paper-style §2d` / `paper-review §2.D/§O4` / `mainline §B8` /
  `final-review` (register the new diagnostic dimension).

## 5. Phased build → release

1. ✅ research (done + auto-writing re-run)
2. Layer A (scorer + extract_style baselines + ai_ism_lint integration + tests)
3. Layer B (oracle, weights download, calibration on corpus + RAID)
4. Layer C (rewrite-in-voice skill + orchestration)
5. Skills/docs update (+ dossier drift fix, EVALUATION)
6. Release **v0.13.0**: bump `plugin.json` + `marketplace.json`, CHANGELOG,
   `git tag v0.13.0`, GitHub release.

Version now: 0.12.1 → **0.13.0** (feature release).
