# De-AI frontier — ranked ideation beyond the roadmap

Status: design note, 2026-07-13. Produced by a six-lens divergent ideation
(scale-unlocks, arms-race, writing-time product, cross-field transfer,
evaluation science, contrarian) after the keystone validation and its measured
adversarial limit. Complements [`DEAI_ARCHITECTURE_ROADMAP.md`](DEAI_ARCHITECTURE_ROADMAP.md)
(ranks 2–8 there remain valid engineering work); nothing here is implemented.

## The unifying theme

Stop measuring the **magnitude** of surface variation — a marginal, gameable
quantity the shape adversary already pushes to AUC 0.85/0.64 — and start
measuring the **structure** that genuine scientific authorship necessarily
produces: variation *coupled to content and role*, the *joint covariance
geometry* of dispersion, *claim-to-evidence anchoring*, the author's *own
historical fingerprint*, and the honest *editing-process record* — each on a
statistically guaranteed, falsification-tested footing. This hardens the
detector against the arms race and simultaneously converts the tool from an
adversarial verdict machine into a cooperative writing partner.

## Ranked frontier

**1. Shape must be *explained* by content role (η² conditional dispersion).**
The adversarial result proves raw dispersion measures the wrong thing: forced
variety is *random* variety, decoupled from content. Humans vary paragraph
shape *where the argument demands it*; both AI failure modes (uniform AND
forced-ragged) sit in the low η² tail of "shape variance explained by
rhetorical role." Mechanism: per-paragraph shape vector (existing
`_paragraph_modelfree`) × cheap role vector (section label, position-in-section,
has-number/[CITE]/[MATH]/\ref); compute between-role over total variance
(an F-ratio); calibrate one-observation-per-paper. Only measurable at corpus
scale (impossible at n=14). Model-free, no GPU. *The adversary cannot fake
role-coupling without actually reasoning about the content.*

**2. Promote claim-anchoring to a primary axis.** Unfalsifiable hedged
generality ("demonstrates strong performance" with no number, citation,
reference, or comparison) is AI's durable tell — and fixing it *is* a real
scientific improvement, so there is no evasion incentive to fight. Sentence-level
anchor detection (number/[CITE]/\ref/[MATH]/comparison), with section-conditional
human bands fitted on the full-text corpus (intros legitimately anchor less than
results). Escalates toward `integrity_blocker` only for entirely unanchored
Results/Methods claims.

**3. Fidelity-free structural rewrite operators (merge/split/reorder the
paragraph *partition*).** §9.1 proved word-level rewriting cannot move the
cross-paragraph signal; the only lever is the partition itself — and merge/split
touch zero tokens, so the protected invariant sets are byte-identical and the
`-inf` fidelity gate can never fire. Fidelity-safe by construction; search short
operator sequences toward the human dispersion band under a cohesion floor and
claim-dependency-order admissibility.

**4. Editing-provenance ledger (`deai_provenance.py`).** Inverts the problem:
the real researcher question is not "is this AI?" but "have MY edits made it
mine?" A process record over the author's own draft snapshots (git history)
computes per-span authorship depth (token edit ratio + semantic edit distance
from the nearest AI-draft ancestor) and maps AI-untouched / lightly-edited /
rewritten / author-original spans. Never enters the arms race, never violates
the no-authorship-detection constraint (reads only the author's own history);
honest `unmeasured` when no history exists.

**5. Joint dispersion-covariance manifold (one Mahalanobis residual).** The
marginal adversary widens each feature independently — landing correct marginals
with the *wrong joint*: real papers co-move sentence-length, comma, and
parenthetical spread. Fit human mean + shrinkage covariance (or PCA basis) on
the scaled corpus; one calibrated document p-value replaces the per-feature flag
spray (which currently over-reports one uniform document as ~8 correlated
"strong" findings — also an honesty fix).

**6. The author's own prior papers as the live dispersion reference.** For a
researcher writing paper N, papers 1..N−1 are the confound-free reference: same
author, same field, same jargon — the only difference is AI-uniformity. Sidesteps
the field-register confound behind the 32–41% FPR entirely. "Your last three
papers vary paragraph length twice as much as this draft" is both honest and
persuasive. Small-n handled by the existing `unmeasured` semantics.

**7. Matched-generation falsification test (run first — it gates 1 and 5).**
§9.2 already concedes the 0.99 AUC may partly be "diverse real library vs
uniform synthetic batch." The honest test: for each human paper, extract its
skeleton (section count, per-section paragraph counts, sentence targets,
float/equation counts), generate an AI paper to that *exact* skeleton, and
re-run the dispersion (and η²) AUC on matched pairs. If the signal survives
skeleton matching, it is within-document uniformity; if not, we learn that
honestly before building on it.

**8. Mondrian split-conformal calibration.** Separates what the detector fuses:
the *human false-flag rate* is a type-I error guaranteeable from human data
alone (finite-sample, distribution-free) — AI detection power is a separate,
wide-CI question. Conformal p-values against a held-out human calibration split,
stratified (Mondrian) by jargon-density decile, replace the 5th-percentile
heuristic and the ungrounded confidence constant. This is the statistical
backbone every other idea's operating point stands on.

## Sequencing logic

7 → (1, 5, 8) → 2, 3, 6, 4. The falsification test (7) is the honesty
prerequisite; η² (1), the covariance manifold (5), and conformal calibration
(8) are the detection core the scaled corpus newly enables; claim-anchoring
(2), partition operators (3), the personal baseline (6), and the provenance
ledger (4) are the cooperative-tool layer.

## Notable discards (with reasons)

Shape-budget generation specs (steers authors to manufacture the engineered
raggedness the detector exists to catch — guardrail-5 hazard); standing
red-team harness (tension with the no-evasion-service constraint); cross-field
transfer matrices (publication interest, secondary to the user's own-field
tool); narrative-arc grammars (unmeasurable free parameters at current n);
citation-graph and numeric-texture axes (blocked until `extract_style` stops
flattening `\cite` — roadmap rank 6 fixes that first).
