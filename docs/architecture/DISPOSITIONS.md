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
| `L1.distribution` operating point | **Decided degraded — refuted, not merely absent** | `deai_policy.json` is withdrawn as an adoption candidate. Measured on 500 human papers against 173 AI documents, one observation per document: burstiness reverses sign on adversarial prose (AUC 0.181) and long-form sits inside the human band (0.441) while flagging 7.2% of humans; signposting runs below chance at AUC 0.247 and flags 0 of 173 AI documents. Same criterion that rejected the inference-connective rate. No threshold may be built on either statistic (EVALUATION §16). |
| `L1.uid` operating point | **Decided degraded** | No field-policy-calibrated compatibility operating point; the surprisal path is measured not to add document-level power. |
| Enriched surprisal features (roadmap rank 5) | **Done, not shipped** | Better than the three scalars but inert for the model-free detector, so recorded not shipped (EVALUATION §9.8). |
| Length normalization of manifold distance | **Rejected** | A length-confound exploit, not a noise correction (guardrail 9, EVALUATION §9.8). The replacement — a length-aware manifold that widens the human band by estimator noise — has its mechanism measured (r = −0.414 inside the short stratum) and its cheap substitute refuted: finer Mondrian stratification buys no power (EVALUATION §9.4b). |
| Baseline unification into one `(feature, unit)` object (rank 2) | **Deferred (elegance debt)** | Explicitly a staged consolidation, never a rewrite; the current architecture is correct and green. |
| Jargon-conditional per-paragraph operating point (rank 3) | **Won't pursue as scoped** | The jargon confound is handled at document scale by per-stratum + conformal; a per-paragraph operating point is inconsistent with the L3-degraded decision. |
| `corpus_cos` ablation (rank 4) | **Deferred (audit-only)** | Documented as a field-register confound feature in the degraded, audit-only classifier; marginal value while L3 has no shipped operating point. |
| Topic-orthogonal axes: cohesion, hedging, citation placement (rank 6) | **Deferred, blocked** | Citation placement is blocked on the `extract_style` `\cite`-flattening root-cause fix; each is a future calibrated axis, not a gap in this spec. |
| Long-form generation (`ai_long`) | **Standing falsification target** | A recorded measured limit (EVALUATION §9.7); future detector work is benchmarked against it. |
