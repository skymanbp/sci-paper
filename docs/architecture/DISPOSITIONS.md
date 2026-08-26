# De-AI subsystem status and open-item dispositions

The disposition register for `sci-paper`. Split out of
[`SCIPAPER_STANDARD.md`](../SCIPAPER_STANDARD.md) §11 on 2026-08-25, when that
file passed the repository's 750-line budget and could no longer be edited.

This is a **record of decisions**, not independent policy. The standard remains
the single normative contract and nothing here can redefine a consequence class,
a measurement state, or a stopping rule; the evidence behind each row lives in
[`EVALUATION.md`](EVALUATION.md). Adoption of any item still requires passing
the §9 confound audit and keeping the suite and validator green, and updates
this register and `EVALUATION.md` together.

---

The ranked de-AI frontier is complete ([`DEAI_FRONTIER.md`](../design-notes/DEAI_FRONTIER.md)).
Every remaining engineering item has a decided disposition, so the standard rests
on no undecided obstacle. Adoption of any item requires passing the §9 confound
audit and keeping the suite and validator green, and updates this table and
`EVALUATION.md` together.

| Item | Disposition | Reason |
|---|---|---|
| Document-scale detection core (dispersion manifold, role coupling, split-conformal, per-stratum) | **Shipped, `measured`** | Calibrated on the complete human corpus; falsification and length-fair AUCs in EVALUATION §9.2–9.5. |
| Salience hierarchy (`L2.salience_hierarchy`) | **Shipped, `measured`** | Per-bucket passage reference from the field's own banks; abstains where the reference cannot resolve above the gate (EVALUATION §14). |
| Domain register (`L0.register`) | **Shipped, `measured`** | Corpus document frequency with compound-by-rarest-part and macro-subscript handling; precision verified against native-term controls (EVALUATION §14). |
| Hypotaxis ratio as the formalisation of "flat prose" | **Rejected** | Refuted on the human abstract reference: the flagged manuscript sits above the human median in subordination, so flatness is not a subordination deficit (EVALUATION §14). |
| Thesis spine (§5.4) as a measured axis | **Shipped as a writing rule, deliberately unmeasured** | Three surface formalisations refuted (EVALUATION §9.6, §14.5, §15.1), and the replacement statistic then refuted on its own pre-registered condition: an adversarial refutation pass overturned 45% of the unbound verdicts and took the domain-matched AUC from 0.756 to exactly 0.500 (§15.2b). No threshold, exit code, or advisory count may be built on it without new evidence. |
| Spine fraction as a discriminator | **Rejected** | Pre-registered failure at an overturn rate above 30%; the measured rate was 0.450, after which no domain-matched generated passage contained an unbound clause and the whole residual separation was the cross-domain genre confound (EVALUATION §15.2b). |
| Inert-clause runs and inference-connective rate | **Rejected** | Inert runs do not separate once genre is matched, and the connective rate reverses sign between two AI banks, so a connective is not evidence of an inference (EVALUATION §15.1). |
| Subfield reference for the salience axis | **Rejected as unnecessary** | A 254-abstract weak-lensing top-tier bank reproduces the broad bank's p90 gates and the same manuscript percentile; genre separates at the discipline level, not between astro-ph subfields (EVALUATION §15.4). |
| Subfield reference for the register axis | **Rejected as harmful** | 254 documents cannot express a rate below 1/254, 39.4× coarser than the 1e-4 threshold, so core field terms flip to foreign on zero counts (EVALUATION §15.5). |
| Cooperative layer (`deai_partition`, `deai_anchoring`, `deai_provenance`, `deai_personal`) | **Shipped** | Partition/anchoring `measured`; provenance/personal `unmeasured` by design until the author supplies own history/papers. |
| `L3.voice` operating point | **Decided degraded** | Offline audit instrument; per-paragraph unit near-unjudgeable and document-level surprisal refuted (§2 L3, EVALUATION §7, §9.8). |
| Field-topic-robust L3 operating point | **Not obtainable from this feature set** | Three retrains across a 2.6× bank range (17,299 / 41,641 / 44,576 records), each with its own 20-split grouped audit: field-topic false positives 0.318 → 0.285 → 0.280, every step inside one retrain's own split range, while headline AUC moved the other way 0.9320 → 0.9518. The confound is in the features, not the sample. Reopening requires a different feature set, not a larger bank (EVALUATION §7.0a). |
| Human-labelled validation for salience and register | **Half closed by provenance, half still open** | The provenance half is measured (EVALUATION §17) on 200 held-out refereed papers. What still needs a labeller is whether an individual advisory is good *advice*, and recall — neither is obtainable from provenance. The harness stands (`tools/label_findings.py`): finding-level labels, one labeller plus a blind re-label subset, drafts and published papers stratified, `unmeasured` below 20 per stratum. |
| `L1.distribution` operating point | **Decided degraded — refuted, not merely absent** | `deai_policy.json` is withdrawn as an adoption candidate. Measured on 500 human papers against 173 AI documents, one observation per document: burstiness reverses sign on adversarial prose (AUC 0.181) and long-form sits inside the human band (0.441) while flagging 7.2% of humans; signposting runs below chance at AUC 0.247 and flags 0 of 173 AI documents. Same criterion that rejected the inference-connective rate. No threshold may be built on either statistic (EVALUATION §16). |
| `L1.uid` operating point | **Decided degraded** | No field-policy-calibrated compatibility operating point; the surprisal path is measured not to add document-level power. |
| Enriched surprisal features (roadmap rank 5) | **Done, not shipped** | Better than the three scalars but inert for the model-free detector, so recorded not shipped (EVALUATION §9.8). |
| Length normalization of manifold distance | **Rejected** | A length-confound exploit, not a noise correction (guardrail 9, EVALUATION §9.8). |
| Length-aware manifold (estimator-noise covariance) | **Rejected — built and refuted** | Its exact form was implemented: subtract the fit set's mean `1/(2(n-1))` from the covariance diagonal, add each scored document's own back. Over 12 paired seeds the human out-of-fit rate is unchanged (0.030 → 0.030) and two AI tiers move the wrong way. The correction is length-*symmetric*, and the short AI documents share the confound with the short human papers they are compared against, so it cannot separate them (EVALUATION §9.4c). |
| Enlarging the conformal calibration split | **Rejected** | Tested because the achievable p-grid at n_cal = 78 makes α = 0.05 a ~96.2nd-percentile cut. Moving documents from training to calibration (0.6 → 0.3) leaves tail power flat and raises the human false-flag rate monotonically 0.030 → 0.038 (EVALUATION §9.4c). |
| Baseline unification into one `(feature, unit)` object (rank 2) | **Deferred (elegance debt)** | Explicitly a staged consolidation, never a rewrite; the current architecture is correct and green. |
| Jargon-conditional per-paragraph operating point (rank 3) | **Won't pursue as scoped** | The jargon confound is handled at document scale by per-stratum + conformal; a per-paragraph operating point is inconsistent with the L3-degraded decision. |
| `corpus_cos` ablation (rank 4) | **Deferred (audit-only)** | Documented as a field-register confound feature in the degraded, audit-only classifier; marginal value while L3 has no shipped operating point. |
| Topic-orthogonal axes: cohesion, hedging, citation placement (rank 6) | **Deferred, blocked** | Citation placement is blocked on the `extract_style` `\cite`-flattening root-cause fix; each is a future calibrated axis, not a gap in this spec. |
| Long-form generation (`ai_long`) | **Standing falsification target — robustly measured** | A recorded measured limit (EVALUATION §9.7). No longer a single-configuration result: tail power holds at 0.000 across two metrics, four calibration splits and 12 seeds, while rank AUC is 0.729 — the signal is present and the operating point cannot reach it (EVALUATION §9.4c). |
| Single-seed tail-power figures as estimates | **Rejected as a reporting practice** | Per-seed spread on the manifold tiers is 0.04–0.18, wider than several differences the record previously read as improvements. §9 figures now carry the spread, and `tools/eval_docscale.py` reproduces the table rather than it being quoted (EVALUATION §9.4c). |
| Hand labels as the only route to register/salience precision | **Superseded — half of it never needed a labeller** | A refereed ApJ/ApJL/A&A paper's provenance is already a label for "does this axis fire on accepted prose". 200 held-out papers, verified disjoint from all three calibration banks, now measure both axes (EVALUATION §17). `label_findings.py` keeps the remaining half: whether an individual advisory is good advice. |
| Comparing held-out against in-sample papers to estimate leakage | **Rejected — confounded** | The two populations are era-disjoint (2020–2021 vs 2012–2018), so the contrast charges six years of vocabulary drift to calibration leakage. Replaced by a paired test on one population where bank membership is the only thing that differs: 72.7% of 2,287 held-out register flags would be suppressed by the paper's own membership (EVALUATION §17.3). |
| `L0.register` operating point | **Standing falsification target — now measured** | On refereed papers it never saw, it fires at 0.991 per 1,000 words on 93.6% of documents, and its rank AUC against machine text is 0.080 — it fires *more* on human prose. Recorded, not retuned: a replacement operating point must be derived against a held-out target rate and validated the same way (EVALUATION §17.4). |
