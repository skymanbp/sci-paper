# Skill and tool responsibilities (normative annex)

**Incorporated by reference into [`SCIPAPER_STANDARD.md`](../SCIPAPER_STANDARD.md)
§§7-8.** These tables bind every component and carry the same force as the rest
of the standard; they were moved here on 2026-08-25 when that file passed the
repository's 750-line budget. The annex has **no independent authority**: it
cannot create a consequence class, a measurement state, or a stopping rule, and
where it and the standard could be read to differ, the standard wins.

Architecture is documented in [`DEAI_SUBSYSTEM.md`](DEAI_SUBSYSTEM.md), the
per-tool operational registry in [`../../tools/README.md`](../../tools/README.md),
and empirical evidence in [`EVALUATION.md`](EVALUATION.md). None of them
overrides the standard.

---

## 7. Skill responsibilities

| Skill | Required role |
|---|---|
| `paper` | Load this standard; provide canonical L0 lists and detailed writing/QD guidance; operationalise the §5.4 thesis spine, including the thesis line and the inventory test, before drafting or revising a section. |
| `de-ai` | The single de-AI surface: Pass 1 subsystem measurement (L0–L4), Pass 2 vendored humanizer structural-tell audit, Pass 3 claim-first faithful rewrite under §6 eligibility and the §5.3 length budget; fill the §5.4 binding ledger for every rewritten paragraph, an unmeasured pass no detector emits; provide the descriptive field-calibration assets; never redefine consequence classes. |
| `condense` | The redundancy/length action surface: execute §5.3 (delete > condense-in-place > same-length; growth only with recorded justification) with one-canonical-home-per-fact deduplication, proven by the length gate; never delete a fact's sole support. |
| `paper-review` | Produce typed findings across dimensions A–R, including the narrative-spine protocol (dimension E) and adversarial escalation (dimension M); verify integrity evidence; allow multiple explicitly related contributions; treat an escalation `CONFIRMED` as a critique that survived verification, then classify its consequence separately; avoid a universal paper verdict. |
| `figure-review` | Separate objective scientific/rendering blockers from aesthetic advisories; measure canvas balance at the pixel level. |
| `brainstorm` | Radial pre-draft ideation: produce candidate directions with evidence, derivation skeletons and reader payoff; never fabricate scientific content or write manuscript prose. |
| `final-review` | Preserve independent isolated reviews (paper-review, figure-review, de-ai audit, physics, mainline, logic); merge typed findings; resolve blockers and L0 targets; record advisory dispositions and unmeasured axes. |
| `calibrate` | Walk one field from an empty corpus to calibrated axes and, where a labeller is available, to measured advice quality; report every axis's floor and leave a stratum that cannot support a rate `unmeasured`; never lower a floor, never admit a held-out document into calibration, and never turn a calibrated distribution into a detector or a verdict. |
| `physics` | Measurement primitive. First-principles verification (P1-P8): dimensions, asymptotics, symmetry/parity/conservation, the preconditions of information-theoretic bounds, algebraic re-derivation, numerical provenance, foundational citations, build integrity. Emit findings only; never carry a private word list or a zero-advisory gate. |
| `mainline` | Measurement primitive. Build the purpose record and contribution graph, then answer the cold reader's seven questions; classify each confusion by consequence. Assume no three-act template and no single-component graph. Emit findings only. |
| `logic` | Measurement primitive. Claim graph, empirical statistical methodology, and the review side of claim-evidence discipline: verb strength may not exceed evidence strength. Emit findings only; never mark register by word list. |
| `proposal-polish` | Funding-proposal register (vision plus feasibility): keep backed ambition, enforce claim-feasibility matching, apply the L0 policy and §6 rewrite invariants unchanged; never fabricate support. |

`docs/architecture/DEAI_SUBSYSTEM.md` documents architecture. `EVALUATION.md` records
empirical evidence. Neither overrides this standard.

All of the above except `brainstorm` are normative implementers and must
reference this standard (enforced by `validate_plugin.py` `NORMATIVE_SKILLS`).
`brainstorm` operates before manuscript prose exists; its role row binds its
scope, not a standard-reference obligation.

---

## 8. Tool responsibilities

| Tool | Layer | Required behavior |
|---|---|---|
| `ai_ism_lint.py` | L0 hub plus optional L1-L3 aggregation | Emit text or structured JSON from the same findings; use L0-only exit semantics. |
| `deai_metrics.py` | L1 | Emit calibrated distribution findings and explicit missing-baseline status. |
| `deai_oracle.py` | L1 | Emit surprisal/UID findings with observed and reference values; advisory-success exit 0. |
| `deai_structure.py` | L2 sentence | Emit template evidence with calibration metadata; advisory-success exit 0. |
| `deai_salience.py` | L2 salience | Measure recital structure against a per-section human passage reference at one shared unit; one finding per passage; abstain where the reference cannot resolve above the gate. Sole consumer of `extract_style.latex_to_numeral_text`, the numeral-preserving projection (`latex_to_plain` replaces math with `[math]`, which zeroes every numeral signal on `.tex` input). |
| `deai_register.py` | L0 register | Compare manuscript vocabulary against field-corpus document frequency; judge compounds by their rarest part; read macro bodies but not subscript decorations; emit advisories only, never `l0_target`s. |
| `deai_discourse.py` | L2 cohesion + L2 hedging | Measure given/new linkage and epistemic-marker rate against the field's own distribution, each at its declared unit, and flag the LOW tail. Report one status per feature, never a joint one: they calibrate from the same corpus at different granularities, so a field can support one and not the other. Speak only for buckets whose operating point was shown to transfer. |
| `deai_reference.py` | shared reference | Own the `(feature, unit)` percentile contract for every per-bucket axis -- one quantile grid, one sample floor, one plateau-top reader, one calibration loop -- and hold no policy of its own. |
| `deai_docstructure.py` | L2 document | Measure document shape (per-stratum dispersion manifold, role coupling, split-conformal) with sample-sufficiency checks; one shared `manifold_operating_point` scoring entry. |
| `deai_anchoring.py` | L2 | Emit the section-class claim-anchoring band as a writing-quality axis, never an AI-discrimination axis. |
| `deai_voice.py` | L3 | Emit calibrated similarity evidence, model metadata, and confound status without authorship claims; degraded, offline audit instrument. |
| `deai_feedback.py` | shared | Validate schema (incl. `calibration_unit` cap), attach actions, rank findings, summarize statuses, and serialize output. |
| `rewrite_reward.py` | L3-L4 | Exclude unfaithful candidates before ranking eligible rewrites; rank by L0 advisory reduction and fidelity. |
| `retrieve_exemplars.py` | L4 | Supply author-voice evidence without copying unsupported scientific content. |
| `length_gate.py` | QD (§5.3) | Compare per-section rendered-prose word counts between two document versions; strong advisory and exit 1 on unjustified growth; record `--allow` justifications in the report. |
| `deai_partition.py` | L4 | Suggest fidelity-free merge/split operations toward the human dispersion band; zero-token, suggest-only. |
| `deai_provenance.py` | L4 | Label author edit depth vs a designated AI-draft ancestor from the author's own history; `unmeasured` without one. |
| `deai_personal.py` | L4 | Compare a draft to the author's own prior papers (confound-free reference); `unmeasured` below three papers. |
| `eval_findings.py` | evidence | Score the register and salience axes on a **held-out** refereed corpus that fed no calibration bank, and report the same-genre in-sample population beside it so the leakage gap stays visible. Never present the salience rate as a false-positive rate — its gate is a percentile, so a non-zero rate is its design point — and never present either rate as precision for the advice itself. Added 2026-08-27: the axes' precision had stood at `unmeasured` pending hand labels, while a refereed paper's provenance was already a label for half of the question. |
| `eval_docscale.py` | evidence | Reproduce the EVALUATION §9 table through the same `manifold_operating_point` that findings use — never a private scoring path. Label the human rate **in-sample** wherever it includes the manifold's own train and calibration documents, and never present a single-seed tail-power figure as an estimate. Added 2026-08-26: nothing bound the evidence-producing path before, and §9 accumulated headline figures produced by a 95th-percentile cut rather than by the shipped conformal rule. |

Compatibility tuple APIs may remain temporarily, but new orchestration consumes
structured finding APIs. Adapters project from structured findings, not the
reverse.

---

