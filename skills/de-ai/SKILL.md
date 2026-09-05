---
name: de-ai
description: The single de-AI skill. Chains three passes over one target file: (1) in-house de-AI subsystem measurement (L0 lexicon plus L1-L4 structural and learned signals), (2) a vendored humanizer structural-tell audit (AIScientists-Dev/academic-humanizer Layers 1-5 plus blader/humanizer patterns 2.12-2.16 and the Pass-2 self-interrogation), and (3) claim-first faithful rewriting under hard fidelity eligibility and the §5.3 length budget. Every number, formula and citation is preserved; it strips machine tells rather than adding personality. Use when: "de-AI" / "too AI" / "make it read like a human wrote it" / "rewrite in voice" / 太 AI 了 / 去 AI 感 / 像人写的 / 机器味太重, or when paper-review / final-review invokes it as the structural-tell audit step (--audit-only).
disable-model-invocation: false
argument-hint: "<file_path> [--section <name>] [--n N] [--max-iter N] [--audit-only] [--no-apply] [--distill] [--field <name>]"
---

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`. Where this file and the
> standard disagree, the standard wins. `docs/architecture/DEAI_SUBSYSTEM.md` explains the
> design; `docs/architecture/EVALUATION.md` records the empirical evidence. Style profiles
> and learned models supply evidence and positive anchors, never competing
> policy.
>
> **Provenance (MIT, attribution retained):** this skill chains three de-AI
> sources into one pipeline — the in-house de-AI subsystem (the L0-L4 tools and
> the standard's feedback contract) and two vendored humanizers:
> [AIScientists-Dev/academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer)
> v0.3.3 (MIT; the Layer 1-5 catalog) and
> [blader/humanizer](https://github.com/blader/humanizer) (MIT; the structural
> families 2.12-2.16, the Pass-2 self-interrogation, and the false-positive
> guards). The upstream word lists are **not** normative here — corpus evidence
> is (§7 Corpus overrides).

# de-ai — one skill, three passes

## 0. What this skill does

Three sequential passes over one target, all inside the standard's
`measure -> type -> rank -> edit -> re-measure -> disposition` loop:

1. **Pass 1 — measure (de-AI subsystem).** The unified linter and the
   document-scale detectors produce a machine-readable `sci-paper.feedback.v1`
   report: L0 lexical/punctuation, L1 distribution, L2 sentence + document
   structure, L3 learned similarity, L4 positive voice.
2. **Pass 2 — humanizer audit (two vendored repos).** The structural-tell
   catalog (Layers 1-5 plus families 2.12-2.16) runs in audit form; its
   findings merge into Pass 1's ranked list.
3. **Pass 3 — claim-first rewrite.** Each selected paragraph is rebuilt from
   its protected claim graph; only fidelity-eligible candidates within the
   §5.3 length budget survive; re-measure, then apply with author-visible
   before/after.

`--audit-only` stops after Pass 2 (findings only; this is the mode
`paper-review` dimension D and `final-review` invoke). `--no-apply` runs
Pass 3 to proposals only. For technical prose, **neutral and precise IS the
human voice** — this skill strips machine tells; it never adds personality,
humor, or first-person flavor.

**Boundary with `/sci-paper:condense` (canonical home — this statement;
mirrored verbatim in condense SKILL.md §0):**
de-ai removes the *authorship fingerprint* (L0-L4 signals, structural tells,
voice; its Pass-3 length cap only guards its own rewrites against growth).
condense removes *redundancy and length* (cross-document deduplication under
one-canonical-home-per-fact). At the overlap (verbose AI-isms such as
rule-of-three padding or connective stacking), de-ai DETECTS the tell; when
the right fix is deletion rather than rewrite, the deletion EXECUTES under
condense's ranked sweep.

## 0.1 Non-negotiable rules

1. **Scientific fidelity is eligibility, not a score.** A candidate that drops
   or alters a number, unit, citation, mathematical expression, acronym,
   comparison direction, negation, causal direction, named entity, scope,
   stance, or qualifier is ineligible regardless of its style score.
2. **Never add specificity from imagination.** Every number, entity, citation,
   and quantitative qualifier must already exist in a source read in the same
   turn. Specificity means retaining supported detail, not inventing it.
3. **Rebuild from claims, not surface swaps.** Synonym substitution, connector
   deletion, and punctuation cleanup are not a structural rewrite. Extract the
   claim graph and compose new sentences.
4. **Imitate style, never content.** Exemplars guide rhythm, register,
   information distribution, and transition practice; claims, citations, data,
   and distinctive wording are never copied from them.
5. **Learned scores are advisory field-similarity signals.** They do not
   establish authorship and are not paper gates. Missing calibration is
   `degraded` or `unmeasured`, never a clean result. No universal style
   verdict exists.
6. **L0 is the only axis rewritten to zero.** Tier A, em-dash, and Tier B
   above the section cap are `l0_target`. L1-L4 findings are ranked
   advisories with dispositions, never forced to zero at the cost of clarity.
7. **Condense, do not accumulate (§5.3).** The default direction of every
   rewrite is shorter; the explanatory patch — answering a finding by
   appending a clause instead of rewriting the flagged text — is the canonical
   violation. Forward narrative: never narrate the drafting history.
8. **Minimum effective edit + explicit human control.** Rewrite only the
   paragraphs whose findings or the author's instruction justify it; show
   before/after, fidelity evidence, and residual dispositions.

## 1. Field resolution and calibration

1. Resolve `--field`: one available field under `style-profile/` selects
   automatically; multiple require `--field`; zero means corpus guidance is
   unavailable — model-free axes still run and the gap is reported.
2. Read `docs/SCIPAPER_STANDARD.md` and the `/sci-paper:paper` writing
   guidance (Anti-AI-isms tiers, forward narrative, formula and citation
   standards, canonical L0 examples).
3. Read `style-profile/<field>/style_dossier.md` in full when it exists, and
   check freshness: if the corpus under `style-corpus/<field>/` is newer than
   the dossier, stop and regenerate with `python tools/extract_style.py`. A
   stale profile is `unmeasured`, never treated as conformity.
4. Retrieve section-typed positive anchors only when the bank exists:
   `python tools/retrieve_exemplars.py --field <field> --section <type>
   --topic "<verified one-sentence topic>" --k 5`. Read every returned
   exemplar; record provenance; use for rhythm and register only.

## 2. Pass 1 — measure (de-AI subsystem)

```bash
python tools/ai_ism_lint.py <file> --field <field> \
  --structure --distribution --document-structure --register --salience \
  --oracle --voice --summary --format json --output <scratch>/feedback-before.json
```

Read the output as `sci-paper.feedback.v1`; record every axis state
(`measured` / `degraded` / `unmeasured` / `not_applicable`) — silence is
never clean. Exit semantics: 0 = no L0 targets (advisories may remain),
1 = L0 targets present, 2 = input/config/execution failure. Never re-parse
JSON from printed prose.

Axes and tools:

- **L0 lexical + punctuation** (`ai_ism_lint` Tier A/B + em-dash) — the only
  to-zero axis. The Tier A/B word lists are the `TIER_A_PATTERN` and
  `TIER_B_PATTERN` regexes in `tools/ai_ism_lint.py`, mirrored for human reading
  in `skills/paper/SKILL.md`; do not re-derive them by hand.
  `style-profile/<field>/lexicon.json` is separate calibration data: only its
  `llm_words_absent_from_corpus` key is read, and only for the advisory
  `corpus-zero:` rule.
- **L0 register** (`deai_register`) — terms the manuscript leans on that the
  field's own corpus does not carry: the tell of a paper written in a
  neighbouring discipline's vocabulary. Evidence is corpus document frequency,
  never a curated list of another field's words, because a list cannot separate
  `AUC` (1 astronomy passage in 15,599) from `epoch` (402) and `accuracy` (774).
  Advisories only; a corpus-rare term may be a borrowed method's accepted name
  or the concept the paper introduces. The same tool's **zero-hit audit**
  (`register-zero:<term>`) is exhaustive rather than thresholded: every body
  word the manuscript uses that no corpus passage carries is listed, strong
  unless the word is a mechanical formation of an attested stem (`clamped` from
  `clamp`). A strong hit is answered by one of the §4.2 dispositions, never by
  silence.
- **L2 collocation** (`deai_collocation`) — sentences that join common words
  the field never joins (`physical cells`, `controlled grid`): the fraction of a
  sentence's adjacent content-word pairs that no corpus passage attests, against
  a per-section leave-one-out reference. A pair the field writes by chance would
  have been seen; a pair it never wrote is a coinage or a figure of speech, and
  the action names the relation it compresses. Advisory; a term this paper
  defines keeps its pair.
- **L2 salience hierarchy** (`deai_salience`) — whether a passage ranks the
  quantities it reports or recites them. Not numeric density (a quantitative
  abstract is supposed to carry numbers) but how far the numerals run without an
  interpreting sentence between them, against a per-section human reference.
  This is the only axis that reads the numeral-preserving LaTeX projection; the
  others read `latex_to_plain`, which replaces math with `[math]` and therefore
  measures zero numerals on any `.tex` file.
- **L1 distribution** (`deai_metrics`, `deai_oracle`) — burstiness,
  connective openers, surprisal/UID. Degraded without a field operating
  point; rank-only.
- **L2 sentence structure** (`deai_structure`) — template families
  (announced enumeration, ordinal runs, setup-list-wrap, repeated
  modal/anaphoric frames, symmetric closers) plus the auxiliary families
  (antithesis clusters, short reversal beats, paper-as-agent subjects, wh-cleft
  openers, modifier stacks of three-plus tokens with two hyphenated compounds).
  Auxiliary families never enter the template score; they name the sentence.
- **L4 residue** (`deai_residue`) — the trace an edit leaves: self-referential
  drafting history (`we initially`, `no longer`), edit-meta text (`TODO`, `see
  previous version`), a sentence that defines the paper's own object by what
  it never does or has (`residue-absence`: `never` strong, `carries no`
  ordinary, exempt with a citation in the sentence), and a heading or caption
  that promises what the body never delivers (`negative-label`). With
  `--before` or `--git-ref` the diff
  rule reports a label the edit added and the body does not earn, and exit 1
  gates the pass; a residue finding is fixed by rewriting the sentence to the
  current state of the science, never by adding an explanation.
- **L2 document structure** (`deai_docstructure`) — the de-AI centre of
  gravity: per-stratum cross-paragraph dispersion manifold, role coupling,
  split-conformal operating points. Word-level rewriting cannot move this
  signal; the only sanctioned lever is `deai_partition` (§4).
- **L2 claim anchoring** (`deai_anchoring`) — a writing-quality band, not an
  AI-discrimination axis.
- **L3 learned voice** (`deai_voice`) — a decided-`degraded` offline audit
  instrument; per-paragraph findings are confidence-capped at 0.5. A low
  score never proves machine authorship.
- **L4 cooperative repair** (`deai_partition`, `deai_provenance`,
  `deai_personal`) — provenance/personal are honestly `unmeasured` until the
  author supplies their own draft history or prior papers.

## 3. Pass 2 — humanizer structural-tell audit (vendored)

Audit against the catalog below, then merge every hit into the Pass-1 ranked
list (Layer 1-2 structural hits are style-class advisories, density excess
upgrades to strong; Layer-4 claim-evidence failures are integrity-class).
Skip LaTeX comments and scaffolding macros. This pass never edits.

### Layer 1 — general AI tells

Inflated significance; superficial "-ing" tails that fake depth; promotional
or figurative language; vague attribution without a citation; copula
avoidance ("serves as" -> "is"); negative parallelism ("not just X, but Y");
rule-of-three padding; elegant variation (one referent keeps one name for the
whole paper); filler ("it is worth noting that", "in order to"); overlong
clause-stacked sentences (2.11); em-dashes (remove entirely; recast with
commas, colons per the colon rule, parentheses, or separate sentences).
Lexical tells are enforced mechanically by the linter — run it, do not
re-derive the lists here.

### Layer 2 — academic AI tells

- **2.1 Over-claiming verbs.** prove / establish / confirm / guarantee /
  demonstrate, checked against the evidence (§7 corpus overrides).
- **2.2 Significance hype.** paves the way for, a crucial/pivotal step
  toward, opens new avenues, sheds light on, bridges the gap -> the specific
  failure mode or result addressed.
- **2.3 Empty intensifiers.** extensive/comprehensive/thorough experiments, a
  wide range of, numerous, various -> enumerate or quantify.
- **2.4 Novelty padding.** "novel" more than once per section; "to the best
  of our knowledge"; "for the first time" -> state the specific gap.
- **2.5 Formulaic openers.** "In recent years...", "With the rapid
  development of...", "Despite recent advances,..." -> open with the
  structural fact or the problem.
- **2.6 Connective overuse.** No consecutive sentences opening with
  Moreover/Furthermore/Additionally/In particular; let logic carry.
- **2.7 Contribution-list cliches.** Each contribution names a specific
  result with its number, not a restatement of the abstract.
- **2.8 Citation dumping.** Evidence-conditional, never a length rule: flag a
  bracketed list only when entries do not support the sentence or duplicate a
  role. Never delete a relevant source merely to shorten a list.
- **2.9 Hedging-by-vagueness.** somewhat, relatively, fairly, to some extent,
  quite -> quantify or cut (distinct from calibrated hedging — Layer 3).
- **2.10 Boilerplate emphasis.** "It is worth noting that", sentence-initial
  "Notably,"/"Importantly," -> if it matters, the sentence shows it.
- **2.11 Overlong clause-stacked sentences.** Past ~30 words, 3+ subordinate
  clauses chained by which/that/while/with, or double-nested parentheticals.
  Split: one idea per sentence. The highest-yield structural check — the
  mechanical linter does not measure it.

The next five (2.12-2.16, from blader/humanizer) are structural, not
lexical — flag the construction, honour each corpus caveat, never the bare
word.

- **2.12 False ranges.** "from X to Y" with categorical endpoints ("from
  theory to observation"). *Caveat:* a genuine quantitative range (redshift
  0.1 to 0.5) is correct and required; flag only the rhetorical range whose
  endpoints share no scale.
- **2.13 Aphorism formulas.** "X is the Y of Z" / "X becomes a Y" epigrams
  for resonance -> state the literal fact. *Caveat:* a formal definition of
  the same shape ("the aperture mass is the convolution of the shear with the
  filter") is a definition; keep it.
- **2.14 Persuasive authority tropes.** "at its core", "fundamentally", "the
  real question is", "it is important to realize" -> cut, or give the
  specific reason. *Caveat:* "fundamentally different" naming a real physical
  distinction (regime, symmetry, scaling) is substantive; keep it.
- **2.15 Manufactured staccato drama.** A run of terse fragments strung for
  impact -> measured sentences; academic emphasis comes from content. A
  single emphatic short sentence is fine (Layer 3); only a *run* is a tell.
- **2.16 Hyphenated-pair predicate overuse.** Compound modifiers piled in the
  predicate ("the result is model-dependent") -> prefer the plain relation
  ("the result depends on the model") where it reads naturally. Fine as an
  attributive modifier; flag density, not any single use.

### Pass-2 self-interrogation (blader/humanizer two-pass audit)

After the first draft of any Pass-3 rewrite, ask of it: "what still reads as
machine-written here?" Answer in 2-4 concrete bullets (a specific phrase, a
rhythm, a residual tell), then apply one further targeted rewrite that clears
them and re-checks the fidelity and length gates. Do not manufacture voice to
pass this step.

### Layer 3 — preserve these (do NOT over-correct)

Evidence-tied hedging ("suggests", "is consistent with", "we hypothesize",
"may indicate", "appears to") is correct and required when the claim is
genuinely uncertain; strengthening a calibrated verb is a claim-evidence
defect. Passive voice is fine when the actor is irrelevant; first-person
plural "we" is standard; semicolons and an occasional triple are fine; formal
definitions, named methods, symbols, and equations stay verbatim.
**False-positive guards:** do not flag formal vocabulary on its own; a single
mixed register; straight-vs-curly quotes in isolation; a lone emphatic short
sentence; text inside quotations, a caption's verbatim labels, or a worked
example; or field-common knowledge. Specific hard-to-fabricate detail, a
genuine mid-sentence self-correction, and calibrated hedging are human
signals, not tells.

### Layer 4 — claim-evidence discipline

For every empirical claim: (a) is it backed by a number, figure, table, or
citation in the text, and (b) does the verb match that evidence's strength?
Unbacked -> add the pointer or soften. Verb too strong -> downgrade to what
the data show. Vague magnitude -> a number or an attributed range; lead
comparisons with the strongest baseline. Layer-4 failures are
integrity-class, not style-class.

### Layer 5 — voice and venue

If the author supplies prior papers, sample them first and match sentence
rhythm, connective habits, hedging placement, and section openers. Otherwise
default to clean, precise, venue-appropriate prose; the corpus dossier (§1)
is the measured voice baseline. Funding proposals route to
`/sci-paper:proposal-polish`, never here.

## 4. Pass 3 — claim-first rewrite

Select work in ranked order: L0 targets in the requested span first, then
strong L1/L2/L3 advisories with concrete actions, then document-shape
findings. For each selected paragraph:

1. **Protect.** Write the protected claim record (`<scratch>/claim.txt`):
   every claim and its evidence relation, all numbers/units, citations, named
   entities, inline math and acronyms, comparison/negation/causal direction,
   scope, stance, qualifiers. Re-read every numeric and citation source in
   the same turn. Snapshot the original verbatim (`<scratch>/original.txt`)
   as the §5.3 length baseline.
1b. **Bind.** Fill the binding ledger (§4.3) for the paragraph. It is not
   optional and no detector emits it; every `none` row is a clause the rewrite
   must drop rather than carry forward.
2. **Generate.** Produce N candidates (default 5) *from the claim record*,
   not by editing sentence-by-sentence. Each preserves every protected item,
   states the claim at the same strength and scope, adds no new fact, avoids
   Tier A and em-dashes, keeps Tier B within cap, breaks the specific L2
   pattern that motivated the rewrite, keeps technically necessary lists, is
   no longer than the original unless a protected invariant forces it, and
   carries no clause that the ledger marked `none`.
3. **Gate + rank.**
   ```bash
   python tools/rewrite_reward.py --field <field> \
     --reference <scratch>/claim.txt --original <scratch>/original.txt \
     --candidates <scratch>/cand_0.txt <scratch>/cand_1.txt ...
   ```
   `eligible=False` (fidelity failure, or longer than the original → `-inf`)
   cannot be selected; the tool exits 1 when NO candidate is eligible (a
   measured outcome, not a failure — regenerate tighter) and 2 only on invalid
   input or a missing profile; `--allow-growth "<reason>"` only with an
   author-approved justification, printed into the run record. Among
   eligible candidates rank by L0 reduction, semantic fidelity, voice score,
   and condensation. If none is eligible, preserve the original and
   regenerate tighter — never pick the least-bad ineligible candidate. Then
   verify entities, scope, stance, and logical dependencies against the
   source by hand: the deterministic checker is necessary, not sufficient.
4. **Re-measure.** Re-run the Pass-1 linter on the candidate in enough
   section context for section caps. A good rewrite introduces no new
   integrity blocker or L0 target, stays eligible, acts on the selected
   advisory, worsens no higher-priority finding, does not grow the passage
   without a stated reason (report the length delta), and reports residual
   advisories.
5. **Apply.** Show before/after, protected invariants, eligibility, affected
   findings, and dispositions; apply with a minimal Edit and re-read the
   changed region in context. Run the Pass-2 self-interrogation on the
   applied text.

### 4.1 Ranking a recital passage (`salience-recital`)

A recital finding is not an instruction to delete numbers. It says the passage
has not told the reader which of its quantities matter, and the repair is
hierarchy, not subtraction. Work in this order, inside the same claim-record
protocol as any other rewrite:

1. **Name the passage's one claim.** Write it as a sentence with no number in
   it. If the passage supports two claims it is two passages, and the partition
   suggestions of §4 apply instead.
2. **Ask each quantity what it establishes.** A number that is the evidence for
   the claim stays, and the sentence carrying it says what it establishes. A
   number that is merely something the work produced belongs to the section that
   argues from it. Moving a value is a fidelity-neutral operation only if it
   lands somewhere; dropping it is not, and a number that is the sole support of
   a claim never leaves.
3. **Break the run.** The measured defect is consecutive numeral-bearing
   sentences. One interpreting sentence between two reported quantities removes
   the finding *and* is the sentence a reader wanted; adding a filler clause to
   the same sentence is the §5.3 explanatory patch and is not the fix.
4. **For an abstract, check three sentences exist.** What was not known, what
   this work establishes, and what follows for someone else's analysis. A
   quantity list can satisfy none of these while every number in it is correct.
   State the contrast the result creates against what was assumed before, when
   the manuscript already supports that contrast; never manufacture novelty
   language to supply it.

An `accepted` disposition is the right outcome wherever the density is what the
genre requires: a methods paragraph specifying a parameter grid is an
enumeration by nature, and the finding only reports that it is denser than most
human method passages.

### 4.2 Register dispositions (`register-foreign`, `register-zero`)

Three dispositions, in preference order, each recorded. A strong `register-zero`
hit must take one of them explicitly: it is a word no passage of the field has
ever written, and the only reasons to keep it are that this paper defines it
(disposition 3, with the definition at first use) or that it names a method the
field has not used before (disposition 2, with the citation that introduces it).

1. **Name the field's own quantity.** Prefer the term the audience reads in,
   when one exists and means the same thing. A weak-lensing reader asks about
   completeness and purity at a given false-alarm rate; a discrimination summary
   borrowed from another field may be exactly the same number under a name they
   do not use. Only make this swap when the replacement is the same quantity —
   renaming a statistic to something it is not is an integrity defect, not a
   register fix.
2. **Keep the term and define it.** Where the borrowed name is the accepted one,
   define it at first use and say what it measures in field terms.
3. **Confirm the definition, for a term this paper introduces.** A corpus
   frequency of zero is equally consistent with a foreign term and a new one;
   the detector cannot tell them apart and does not try.

Never swap a term whose replacement would change the claim, and never introduce
a field term the manuscript has not earned.

**Document-shape findings** (dispersion manifold, role coupling) cannot be
moved by word-level rewriting. Run `python tools/deai_partition.py <file>
--field <field>` and surface its fidelity-free merge/split suggestions to the
author verbatim; they change zero tokens and are applied by hand, never
automatically.

### 4.3 The binding ledger (SCIPAPER_STANDARD §5.4)

**No detector produces this finding.** §4.1 and §4.2 act on measured advisories;
this one is a mandatory unmeasured pass, run on every paragraph selected for
rewrite. The reason it has no tool is recorded: three surface statistics were
built for it and all three were refuted (EVALUATION §9.6, §14.5, §15.1). The
defect is not a property of a clause but of the relation between a clause and
the propositions around it, so the ledger is filled by judgement and made
checkable by its output shape, not by a threshold.

**Fill it before generating candidates**, on the original paragraph:

| clause | kind | antecedent |
|---|---|---|
| … | `fact` / `link` / **`none`** | a number, an equation, a citation, or the id of an earlier clause |

- **`fact`** — introduces something checkable that was not in play: a number, a
  measurement, a named object, a concrete procedure.
- **`link`** — binds two propositions already in play. Name both.
- **`none`** — no antecedent can be named. This is a claim about the text, so
  write it only after trying to find one.

A causal, purposive, or evaluative frame with a `none` antecedent is the
padding case: the sentence has the shape of an argument and none of the
substance. Delete it in the rewrite; do not repair it by inventing the
antecedent, which manufactures a claim the sources do not support.

Two traps make this pass fail in opposite directions:

- **A connective is not an inference.** Machine prose supplies "therefore",
  "thereby", "through", and "which in turn" and leaves the antecedent unbound;
  one AI bank carries inference markers two to three times more often than
  human abstracts (EVALUATION §15.1). Judge the antecedent, never the marker.
- **A hedge is not padding.** A clause that narrows a claim — a condition, a
  range, an uncertainty, a scope limit, a negation, a conceded limitation — is
  load-bearing by definition and is `fact`, not `none`, however evaluative it
  reads. §6 eligibility already protects the qualifier class and outranks this
  pass entirely.

Where a whole paragraph resolves to `none` rows, the repair is deletion and
belongs to `/sci-paper:condense`, not to a rewrite; hand it over rather than
rewriting inert text into better inert text. Where the paragraph's `fact` rows
are unranked instead of unbound, that is the recital case — use §4.1.

### Optional self-distillation (`--distill`)

Only paragraphs explicitly accepted by the author may enter
`style-profile/<field>/exemplar_paragraphs.jsonl` as positive voice anchors,
with provenance and section type recorded. Never feed automatically generated
or merely detector-favored text back as human positive data. Retraining on
the grown bank requires held-out and confound-aware evaluation; a multi-minute
heavy run executes on the authorized compute environment, not locally.

## 5. Stopping rule and report

Stop only when: all integrity blockers are resolved or verified false
positives; applicable L0 targets are zero; every strong advisory is `acted`,
`accepted`, `rejected_as_false_positive`, or `pending` with a stated reason;
ordinary advisories and unavailable axes are reported; and every changed
paragraph passes scientific-fidelity verification. This is a
disposition-complete feedback state, not a universal prose verdict. If the
iteration budget is exhausted, leave the original text for unresolved cases
and return the pending findings.

```markdown
# de-ai — Feedback Report
Target: <file> | Field: <field> | Candidates/paragraph: N
Measurement: <axis=status list, all four states shown>
Passes run: measure / humanizer-audit / rewrite (or audit-only)
Paragraphs considered: K | rewritten: R | unchanged: U
L0 targets: before B -> after A   (Tier A, em-dash, Tier B excess)
Strong advisories: acted X | accepted Y | false-positive Z | pending P
Length delta (rendered prose): <per-paragraph words, §5.3>

## Paragraph changes
- <line/section>: <finding ids and rules>
  - eligibility, missing invariants, before/after, disposition

## Residual feedback
<ranked ordinary advisories, document-shape suggestions, unavailable axes>
No number, equation, or citation changed.
```

## 6. Anti-patterns

- Treating synonym swaps or connector deletion as a structural rewrite.
- Quoting a manuscript number or citation from the dossier or memory.
- Forcing every advisory to zero, or every sentence-length outlier to the
  mean.
- Manufacturing raggedness, voice, or personality to lower a detector score.
- Calling a compatibility threshold calibrated, or a stale profile fresh.
- Declaring a paper human- or machine-authored from a learned score.
- Answering a finding by appending an explanatory clause (the §5.3 patch).
- Deleting a relevant citation merely to shorten a list.
- Copying or lightly paraphrasing an exemplar.
- Doing condense's job: bulk redundancy deletion belongs to
  `/sci-paper:condense`; de-ai only rewrites what a tell finding selects.

## 7. Corpus overrides and interfaces

**Corpus overrides (measured evidence beats the upstream word lists):**
`landscape` is a legitimate astrophysics term — never flag it lexically;
`demonstrate*` and `significantly` are normal astro usage — flag only on a
Layer-4 failure, never as bare words. The enforced Tier A/B lists live in
`tools/ai_ism_lint.py`; this skill defers to them. The corpus-derived
`style-profile/<field>/lexicon.json` feeds the advisory `corpus-zero:` rule only.
When the corpus changes, re-run `tools/extract_style.py` and
`tools/build_profile.py`.

**Interfaces:**
- `docs/SCIPAPER_STANDARD.md` — consequence classes, ranking, disposition,
  stopping, §5.2 de-AI-ization order, §5.3 length budget, §6 rewrite
  eligibility.
- `/sci-paper:paper` — writing guidance and canonical L0 prose examples.
- `/sci-paper:condense` — the redundancy/length action surface (boundary
  statement in §0).
- `/sci-paper:paper-review` — invokes this skill `--audit-only` as its
  dimension-D structural-tell step.
- `/sci-paper:final-review` — runs this skill `--audit-only` as an isolated
  reviewer.
- Tools: `ai_ism_lint` (L0 hub + aggregation), `deai_metrics`,
  `deai_oracle`, `deai_structure`, `deai_salience`, `deai_register`,
  `deai_collocation`, `deai_residue`, `deai_docstructure`, `deai_anchoring`,
  `deai_voice`, `deai_partition`, `deai_provenance`, `deai_personal`,
  `rewrite_reward` (fidelity + length gate), `retrieve_exemplars`,
  `extract_style`, `build_profile`, `deai_feedback` (schema + ranking).
