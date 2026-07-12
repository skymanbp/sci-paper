# EVALUATION — de-AI subsystem (v0.13.0, field `wgl`)

Measured performance of the four-layer de-AI subsystem on the `wgl` field, as of
2026-07-11. Every number here traces to a training run or fixture scored in the
same session; re-derive with the commands shown. This is a *diagnostic* record,
not a benchmark claim — the scorers are advisory (guardrail 2), and absolute
scores are calibrated to the `wgl` human corpus (guardrail 1), so they do not
transfer unchanged to other fields.

## 1. Layer D — learned voice / reward model

**Data (8214 paragraphs, group-split by source paper):**

| role | source | n |
|---|---|---|
| human + | curated corpus (`exemplar_paragraphs.jsonl`) | 1952 |
| human + | pre-2022 arXiv abstracts — broad astro + weak-lensing + authoritative authors incl. advisor (DLS / LoVoCCS) | 3197 |
| human + | RAID human arXiv abstracts | 800 |
| LLM − | Claude-generated, 6 registers | 210 + 555 |
| LLM − | multi-model RAID (GPT / Llama / …) abstracts | 1500 |
| LLM − | hand-crafted seeds | 20 |

**Held-out (group-split, 20%):** LogisticRegression **AUC 0.953**, F1(human)
0.929, balanced-acc 0.880. HistGradientBoosting scored higher in-distribution
(AUC 0.993) but **fails out-of-distribution**, so the monotonic LR ships (see §4).

**Out-of-distribution fixtures** (`deai_voice.py <fixture> --field wgl --scores`):

| fixture | P(human) | target | ✓ |
|---|---|---|---|
| `llm_style` (fluent LLM prose) | 0.071 | LOW | ✓ |
| `ai_ish` (hand-crafted borderline) | 0.487 | LOW | ✓ (thin margin) |
| `human_ish` (hand-written) | 1.000 | HIGH | ✓ |
| `corpus_para` (real corpus paragraph) | 0.959 | HIGH | ✓ |

**Learned weights (standardized; + ⇒ more human).** The model keys on genuine
voice, not topic — `corpus_cos` (topic-similarity) gets a near-zero +0.23 while
surprisal-variance and burstiness dominate:

```
global_uid +3.86   sent_len_stdev -2.11   sent_len_cv +1.61   paren_rate +1.44
mean_surprisal -0.90   local_uid -0.83   ...   corpus_cos +0.23
```

## 2. Data-source ablation (why our own drafts were excluded)

Controlled ablation (fixed features, per-subset LR refit) attributing OOD
robustness to each source:

| variant | n | AUC | llm_style | ai_ish | human_ish | corpus_para |
|---|---|---|---|---|---|---|
| FULL (incl. our drafts) | 8476 | 0.920 | 0.263 | **0.722** ✗ | 0.999 | 0.912 |
| **− our drafts (shipped)** | 8214 | **0.953** | 0.071 | 0.487 ✓ | 1.000 | 0.959 |
| − RAID-human | 7676 | 0.823 | 0.348 | 0.823 | 1.000 | 0.951 |
| corpus + Claude-neg only | 2717 | 0.993* | 0.013 | 0.383 | 1.000 | 1.000 |

Our own de-AI-reviewed drafts, labeled AI, read partly human and blur the
boundary — dropping them lifts AUC and pulls `ai_ish` back to the correct side.
RAID-human is load-bearing (AUC collapses without it). *The tiny corpus-only
variant's 0.993 is in-distribution to a small clean set; it discards the
diversity the reward needs to generalize to arbitrary rewrites.

## 3. Layer C — best-of-N reward

`rewrite_reward.py` ranks candidate rewrites of one claim. Validation (one
faithful + two adversarial candidates, reference = distilled claim):

| candidate | combined | voice | fidelity | specificity | faithful |
|---|---|---|---|---|---|
| faithful + specific + voiced | **0.347** | 0.347 | 0.552 | 1.00 | True |
| meaning-drifted (high voice) | 0.015 | 0.978 | 0.303 | 0.00 | False |
| number-dropped | 0.014 | 0.941 | 0.279 | 0.00 | False |

The faithful candidate wins by ~20×. A meaning-drifted candidate that reads very
human (voice 0.978) **cannot win** — the relative claim-fidelity gate demotes it.
This is the guardrail-3 protection: the reward is genuine-voice × preserved
meaning, so best-of-N never selects detector-evasion.

Fidelity must anchor to the **distilled claim**, not the padded original: against
the padded original a faithful de-padded rewrite scored 0.30 (drift 0.26 —
indistinguishable); against the claim, 0.55 vs 0.30 (cleanly separated).

## 4. Design decisions & limitations

- **LR over gradient-boosting.** The reward scores arbitrary, often
  out-of-distribution rewrites; a monotonic linear model stays correct
  everywhere ("more surprisal-variance ⇒ more human, always"), whereas the tree
  extrapolates erratically — it scored a hand-crafted LLM paragraph P(human)=0.99
  while LR gave 0.003. Held-out AUC alone is misleading for a reward model.
- **`ai_ish` margin is thin (0.487).** Correct side, but a hand-crafted
  borderline case sits near 0.5. Acceptable for an advisory ranking signal;
  not a hard gate.
- **Field-specific.** Numbers above are `wgl`. Other fields rebuild via
  `extract_style.py` → `train_voice_model.py`; artifacts are gitignored.
- **Self-improvement rungs not yet exercised.** Best-of-N ships now.
  Self-distillation (accepted rewrites → positives → retrain) and DPO/RL need
  real usage-derived preference data, which does not exist until the rewriter is
  used; the hooks are built, the loops are not yet run.

## Reproduce

```bash
python tools/train_voice_model.py --field wgl --refeature   # -> voice_model.joblib + metrics
python tools/deai_voice.py <fixture> --field wgl --scores    # OOD fixture P(human)
python tools/rewrite_reward.py --field wgl --reference claim.txt --candidates c*.txt
```
