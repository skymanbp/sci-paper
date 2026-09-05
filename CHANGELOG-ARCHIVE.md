# Changelog archive — v0.22.0 through v0.27.0

Entries moved out of [CHANGELOG.md](CHANGELOG.md) on 2026-08-25 so the live
changelog stays readable, and split in two on 2026-08-26 when this file passed
the repository's 750-line budget. Nothing here is edited; the history is
verbatim.

- Current releases: [CHANGELOG.md](CHANGELOG.md)
- **v0.27.1 through v0.32.0**: [CHANGELOG-ARCHIVE-RECENT.md](CHANGELOG-ARCHIVE-RECENT.md)
- **v0.21.0 and earlier**: [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md)

---

## v0.27.0 — 2026-08-16

A repository audit, the defects it confirmed, and the structure that stops them
recurring. An adversarially verified multi-agent sweep (7 dimensions, every
finding re-derived by an independent refuter) produced 59 candidates; 12 were
refuted and the rest are fixed here. No consequence class, exit code, or
normative policy in `SCIPAPER_STANDARD` §§0-6 changed.

### The section-bucket defect, and what it invalidates

`extract_style.classify_section` matched section titles **in the singular
only**. `\bresult\b` does not match "Results", `\bconclusion\b` does not match
"Conclusions", and `\bsystematic\b` does not match "Systematics" — the standard
ApJ/MNRAS/PRD headings. All of them fell through to `DEFAULT_SECTION_BUCKET` and
were measured against the **methods** reference. The symptom was visible in the
shipped bank all along and had not been read as one: 31 weak-lensing papers
produced 1770 `method` paragraphs and **zero** `results`.

The same defect had a second form. `\b(acknowledg|bibliograph)\b` was written as
if those were stems, but the closing `\b` means each can only ever match that
exact string, so "Acknowledgements" and "Bibliography" were never skipped and
were ingested as prose.

- Every noun in `SECTION_PATTERNS` now carries its plural, and the two stems
  carry `\w*` in place of a closing word boundary.
- **Every per-section asset built before this release carries the
  mis-bucketing, and the impact is measured rather than estimated.** Rebuilding
  the same 31-paper `wgl` corpus with the fixed classifier, into a scratch
  profile root so the shipped assets were untouched:

  | bucket | pre-fix | post-fix | change |
  |---|---:|---:|---:|
  | abstract | 15 | 15 | 0 |
  | intro | 99 | 99 | 0 |
  | method | 1770 | 1671 | −99 |
  | discussion | 43 | 97 | **+126%** |
  | conclusion | 30 | 50 | **+67%** |
  | results | 0 | 10 | **0 → 10** |
  | **total** | **1957** | **1942** | −15 (back matter now skipped) |

  `discussion` and `conclusion` change materially; `results` exists for the
  first time but at n = 10, below the documented 30-passage floor, so that
  bucket stays honestly omitted until the corpus grows. `EVALUATION.md` §2
  carries this table as a standing notice, and `style-profile/README.md` says
  to treat every section-keyed axis as `degraded` until the profile is rebuilt
  and each `--calibrate` re-run. The repository ships no baseline, so a fresh
  clone is `unmeasured` and unaffected.
- `tests/test_extract_style.py` is new. `extract_style` is imported by eight
  sibling tools and owns both LaTeX projections, yet had no test file — which is
  how a singular-only vocabulary survived. The back-matter form above was found
  *by that new test*, not by the audit.

### Fidelity gate: two regexes that rejected faithful rewrites

`rewrite_reward` reported honest rewrites as unfaithful — in the over-strict
direction (`combined = -inf`) — for reasons with nothing to do with science.

- **Numbers absorbed the following comma.** `\d[\d,]*` tokenized "1200, 2400,
  and 4800" as `{"1200,", "2400,", "4800"}`, so dropping an Oxford comma was
  reported as simultaneously *missing* `2400,` and *inventing* `2400`. A numeral
  token must now end in a digit; thousands separators still parse.
- **Units absorbed the following word.** The `\s*` separator let any word after
  a numeral become a "unit": "in 2020 we found" yielded unit `we`. A unit must
  now bind to its number the way the corpus writes it — adjacent, or separated
  only by LaTeX spacing (`\,` `\;` `\!` `\ ` `~`). This deliberately narrows the
  category: a plain-ASCII-space "5 km" no longer registers a unit, though its
  number stays protected.
- Changed numbers and changed units remain ineligible, now under test.

### Display math was invisible to the fidelity gate

Both named LaTeX projections drop `\begin{equation}`/`align`/`gather` bodies by
design, and every protected category was computed from them — so a value
silently changed *inside* a displayed equation passed as fully faithful. That is
the one defect in this release that let an unfaithful candidate through rather
than rejecting a faithful one.

- `rewrite_reward` now reads displayed bodies from the raw text, adding their
  numerals to the number category and the whole body to the math category.
  Whitespace normalizes before comparison, so re-indenting an equation is not a
  change while altering a coefficient or an exponent is.
- **Exit 1, not 2, when no candidate is eligible.** Every candidate failing
  eligibility is a measured outcome the caller acts on (preserve the original,
  regenerate tighter), so reporting it as an execution failure made a correct
  run indistinguishable from a crash. `SCIPAPER_STANDARD` §0.1 now registers
  `rewrite_reward` alongside `length_gate` as carrying a narrow actionable
  contract in which `1` means a measured outcome.

### Reference rates are computed over the set they are compared against

The signposting finding printed a "reference corpus rate" derived from
`blacklist_present_in_corpus`, which `extract_style` keys to its own 12-entry
`PARAGRAPH_INITIAL_LLM_OPENERS` — several of them multi-word phrases that can
never match a single paragraph-initial word. The draft, meanwhile, is measured
against `deai_metrics.CONNECTIVE_OPENERS`, 22 single words. The two numbers were
printed side by side and were never comparable; the reference read roughly seven
times too low.

- `extract_style` now stores the complete `paragraph_initial_counts` counter as
  evidence, and `deai_metrics` computes its reference rate over its own opener
  set. The extractor supplies observations; the detector owns its policy.
- A profile predating that key cannot yield a comparable rate, so the finding
  omits the reference clause and says why, instead of quoting a wrong number.

### Grouped cross-validation, and a cache that notices its own dependency

- `train_ai_ism_classifier` splits with `StratifiedGroupKFold` grouped by source
  paper. Paragraphs from one paper are not independent, and the ungrouped split
  reported F1 0.876 where the grouped split gives 0.823. `cv_grouped` travels
  with the metrics and the CLI prints which split ran, so the two can never be
  read for each other.
- `train_voice_model`'s feature-cache fingerprint includes embedder
  availability. Rows computed without `sentence-transformers` carry
  `corpus_cos = 0.0`; a fingerprint blind to that kept serving them unchanged
  after the dependency was installed, so a degraded value persisted while
  looking measured.

### Other confirmed findings closed

- `deai_oracle` declares `calibration_unit="paragraph"`. It was the one
  paragraph-scope detector that never did, so its findings shipped at confidence
  1.0 and outranked their capped siblings.
- `fetch_arxiv_abstracts` no longer lets a transient page error masquerade as an
  exhausted query. A failed page and an empty page both arrived as `page = []`,
  which silently ended that query's pagination while the run still exited 0.
  Affected queries are now named in an `INCOMPLETE` report and the run exits 2.
- `extract_style` expands typographic ligatures on the PDF path. A PDF text
  layer emits `ﬁ`/`ﬂ`/`ﬀ` as single codepoints, so the tokenizer split
  "significant" into fragments that entered the lexicon and the exemplar bank as
  words.
- `extract_style` and `validate_plugin` gained the stdout re-encoding guard the
  other CLIs already had; both print non-ASCII and both die on a redirected
  stdout under a non-UTF-8 locale. `deai_feedback` was checked and needs none —
  it has no `main()` and no non-ASCII.
- `aggregate_sentence_stats` and `train_and_save` docstrings now describe what
  the code does: tier weights are carried but not applied, the analyzer is
  word-level rather than character-level, and the returned keys are the ones
  actually returned.
- `gather_corpus_files`'s docstring describes the implemented **depth** rule
  rather than a co-location rule it never had.
- `TestShippedReference` is renamed `TestLocalReference`. The plugin ships no
  baseline — every `style-profile/**` artifact is gitignored on purpose — so its
  claim to test "the reference the plugin actually ships" read as CI coverage
  that does not exist.
- The `fetch` tests capture the CLI's progress log, which was the suite's only
  stdout noise and printed an absolute temp path.

### Linter contract

- **Exit 1 no longer reports a crash.** `lint()` caught only
  `(OSError, ValueError, JSONDecodeError)`, so any other exception — a
  `lexicon.json` holding a JSON list raises `AttributeError` — escaped and the
  interpreter exited 1, the status the contract reserves for "an L0 target is
  present". Every execution failure now returns 2.
- **A paragraph-initial connector counts once.** `Crucially` sits in both
  `TIER_A_PATTERN` and the connector list and produced two L0 targets for one
  word, while `Notably`/`Importantly`/`Interestingly` produced one. The Tier A
  scan now applies the same span guard the Tier B scan already used.

### Optional dependencies degrade instead of crashing

- `deai_oracle` probes `transformers`/`torch` before use. Their absence now
  reports `L1.uid` as `unmeasured` with the reason instead of raising
  `ModuleNotFoundError` mid-run; an explicit `--calibrate` that cannot run exits
  2 rather than dying part-way through the corpus.
- `deai_voice` imports `joblib` inside its existing guard, so a present bundle
  with the optional dependency uninstalled degrades the L3 axis instead of
  raising through the caller.
- `deai_provenance` passes `encoding="utf-8"` to its git subprocesses. With
  `text=True` alone they decoded with the locale codepage, so on a non-UTF-8
  Windows locale a tracked file containing an em-dash made the ancestor read as
  "unreadable or untracked" — an axis unmeasured for a decoding reason.
- `retrieve_exemplars` rejects `--k < 1` (exit 2). `--k 0` returned an empty
  list that surfaced as "No paragraphs in section=…", a false claim about the
  bank; a small negative `k` silently returned all-but-the-last exemplar.

### Documentation is categorized, indexed, and mechanically checked

`docs/` now separates what decides from what describes from what is frozen:

```
docs/README.md                          index + authority order
docs/SCIPAPER_STANDARD.md               normative
docs/architecture/DEAI_SUBSYSTEM.md     implementation
docs/architecture/EVALUATION.md         evidence
docs/design-notes/                      frozen, dated reasoning records
```

`validate_plugin.py` gained a ninth check and three new invariants, so this
class of drift fails CI instead of accumulating:

- **recorded suite sizes are validated against real test discovery.**
  `EVALUATION.md` had quoted two different sizes for the same release — 147/13
  in §3 and 172/14 in §12 — because nothing compared either with the repository;
- every document under `docs/` must be linked from the index (no orphans);
- each `design-notes/` file must declare itself a design note in its header;
- no document may reappear at a location it was moved away from.

Corrected in the same pass: the `EVALUATION` §5 baseline total (1,952 → 1,957,
the value the same file already used in §6 and §14.4); the roadmap's disposition
parenthetical, which listed ranks 3 and 6 in the opposite order from
`SCIPAPER_STANDARD` §11, the file it names as the single status home; the
frontier note's "ranks 2-8", which contradicted its own header; the README's
stale tool count; the hard-set filename case in `style-profile/README.md`; and
seven `EVALUATION` links that pointed at deliberately gitignored artifacts and
so resolved on no clone. `style-profile/README.md` now documents
`salience_baseline.json` and `register_lexicon.json` with the `--calibrate`
commands that build them.

### README and discoverability

- `README.md` is rebuilt around what the plugin does, how the loop works, and
  what it refuses to do, with skills grouped by job (write / revise / review /
  explore) and tools grouped by measurement layer. `README.zh-CN.md` is the
  full Chinese counterpart.
- Manifest keywords expanded from 8 to 23 and marketplace tags from 4 to 8;
  five skill descriptions are English-first with their Chinese trigger phrases
  retained, so trigger behaviour is unchanged while the plugin is findable in
  English.

### Skills

- `condense`'s `rewrite_reward.py` example was missing the tool's required
  `--field`, so the documented command exited 2 without doing any work.
- `brainstorm` resolved three internal contradictions: a `--min-frameworks`
  floor of 5 that contradicted the flag table, the §3 completion criterion and
  the anti-pattern list (all 12); two headings both numbered `## 0.`; and a
  §0.6 stopping list that omitted the glossary grill's own hard stop.

### The independent review of this release, and what it caught

Before tagging, the diff itself went through an adversarially verified review
(5 dimensions, every finding re-derived by an independent refuter): 29
candidates, 18 refuted, 11 confirmed — **most of them regressions introduced by
this release**, which is the reason the round happened at all.

- **`rewrite_reward` exit 1 had no execution-failure guard.** Promoting 1 to a
  measured outcome without one meant an uncaught exception also exited 1, so a
  crash was indistinguishable from "no candidate was eligible" — the very bug
  this release fixed in `ai_ism_lint`, reintroduced one file over. `main()` now
  wraps its body and returns 2, matching `length_gate` and `ai_ism_lint`.
- **Reading raw text without the projections' reductions.** Scanning displayed
  equations from the raw source skipped the comment stripping both projections
  do first, so a commented-out dead equation became a hard invariant and
  deleting it scored `-inf`. The fix is one shared `_uncommented()` applied to
  **all five** raw-text categories — citations, inline math, display math,
  macros, units — not to the one site the review happened to name. Display
  bodies additionally drop the `\begin{}`/`\end{}` wrapper and `\label{}`, so
  renaming `eq:mass` or starring an environment is no longer a violation and a
  label's digits (`eq:m200`) no longer enter the number set as `00`.
- **The unit narrowing went too far.** Requiring adjacency or LaTeX spacing
  removed the false positives but also stopped catching `1.5 Mpc` → `1.5 kpc`,
  a factor-1000 physics error, in the gate whose whole job is to catch it. A
  space-separated token is protected again when it is in a closed unit
  vocabulary — keeping `in 2020 we found` unprotected and `1.5 Mpc` protected.
- **The math category is now case-sensitive.** `_normalized` lowercases, so a
  `\Delta\Sigma` → `\delta\Sigma` substitution — a different physical
  quantity — passed as fully faithful.
- **The headline evidence table did not reproduce.** The bucket counts were
  measured before the ligature fix landed in this same release, so three of
  seven numbers were stale. Re-measured against the tagged code: `method` 1770 →
  1671, `discussion` 43 → 97, `conclusion` 30 → 50, `results` 0 → 10, total
  1957 → 1942.
- Documentation overstatements corrected: §12's release gate was half-updated
  (v0.27.0's suite size beside v0.26.2's check count), and the rewritten README
  generalised a true statement about *findings* into a false one about *tools*
  (10 of the 24 entries emit none).

### Verification

`validate_plugin.py` 9/9 checks pass; the suite is **208 tests in 15 files**
(was 172 in 14), all green, with every new test written to fail against the
pre-fix code — including one regression test per confirmed review finding.

Older entries: [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md) (v0.22.0-v0.27.0)
and [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md) (v0.1.0-v0.21.0).

---

## v0.26.2 — 2026-08-16

Evidence only. The validation v0.26.1 said was designed but not executed was
executed, and it **refuted** the statistic v0.26.1 recorded as a lead. No
skill, tool, threshold, or exit code changed.

- **Spine fraction is refuted as a discriminator, on its own pre-registered
  condition** (`EVALUATION` §15.2b). Every clause the first annotator called
  unbound went to a second annotator, blind to the class and to every other
  file in the study, whose task was to *find* an antecedent. The protocol
  pre-registered failure above a 30% overturn rate. **The measured rate was
  45%** (9 of 20). The domain-matched AUC fell from 0.756 to **exactly
  0.500** (p = 1.000): after correction all five Claude-generated astronomy
  passages score 1.000, identical to all nine human arXiv passages. Every
  unbound verdict that survived refutation lies in the cross-domain bank, so
  the residual class-level separation (0.750) is the genre confound alone.
- **The overturns diagnose the contamination they were built to measure.** Six
  of nine fell on the generated astronomy passages, and the refuter's
  antecedents were exact: clauses were marked unbound because they *read* as
  machine prose while their demonstratives pointed at named earlier
  propositions. Authorship instinct produced those verdicts, not the binding
  rule.
- **This vindicates the v0.26.1 shipping decision rather than undermining it.**
  §5.4 shipped as a writing rule that forbids building a threshold on this
  signal; the evidence now says that restraint was correct. The §11
  disposition table records `Spine fraction as a discriminator` as
  **Rejected**.
- What survives is a **writing** distinction, not a detection one: a
  demonstrative pointing at a single earlier proposition is a real antecedent;
  a generic self-reference predicated on an unfalsifiable relevance claim is
  not. That is already how §5.4 and the de-ai binding ledger are written.
- Limits recorded with the result: 20 passages and one annotator pair, and a
  second annotator from the same model family, so the overturn rate bounds
  contamination from below rather than from above.

## v0.26.1 — 2026-08-16

One new normative section and the evidence for why it ships without a
detector, plus the corpus tooling that produced that evidence. No axis,
threshold, or exit code changed.

### The thesis spine (`SCIPAPER_STANDARD` §5.4)

Reader complaint: a draft lists everything its authors did and everything
they measured, and never says which result is *the* result. §5.3 cannot
reach this, because condense removes what is **repeated** and an inventory
repeats nothing — what it lacks is rank.

- **`SCIPAPER_STANDARD` §5.4** states one rule at three nested scales. The
  **document** has exactly one central result, statable in one sentence,
  and every section earns its place by serving it; the reader must finish
  able to say what was done, what the result is, and what it changes. A
  **paragraph** carries one claim, and every other sentence answers "on
  what grounds" or "therefore what". A **clause** either introduces a
  checkable new fact or binds two propositions already in play; one that
  does neither is evaluation, purpose attribution, or restatement. The
  diagnostic is a pointer to the antecedent, not a search for a
  connective.
- **The qualifier class is what this section most endangers**, so the
  protection is stated inside it: a clause that narrows a claim — a
  condition, range, uncertainty, scope limit, negation, or conceded
  limitation — is load-bearing by definition and is never padding. §6
  eligibility outranks the whole section.
- **`skills/paper`** gains the operational form: write the thesis line
  before drafting or revising, then fill the **inventory test** table
  (section → the one sentence it contributes → where it is carried). A
  section with no such sentence is inventory; two sections with the same
  sentence are one section.
- **`skills/de-ai`** Pass 3 gains step 1b and §4.3, the **binding
  ledger**: every clause of a rewritten paragraph is labelled `fact`,
  `link`, or `none` with its antecedent named, and no candidate may carry
  a clause the ledger marked `none`. A paragraph that is all `none` rows
  is handed to `condense` rather than rewritten.
- **It is deliberately not a measured axis**, and §5.4 forbids building a
  threshold on it without new evidence.

### Why there is no detector (`EVALUATION` §15)

- **Two more surface features refuted.** Inert-clause runs do not separate
  human from AI once genre is matched (human span 0.500–0.778, AI span
  0.667–0.889, overlapping, with one AI bank *below* one human bank), and
  the inference-connective rate reverses sign between two AI banks
  (Claude generations median 0.200 against human abstracts' 0.000; RAID
  generations 0.000 with p90 0.125 against the human p90 of 0.222). A
  connective is therefore not evidence of an inference. With claim
  anchoring (§9.6) and the hypotaxis ratio (§14.5), that is three
  independent surface statistics and one outcome.
- **The replacement statistic is a lead, not a result.** A blinded pilot
  (20 passages, 152 clauses, key read only after annotation, blind-file
  SHA-256 matched across a replay) put the domain-matched AUC at 0.756
  with an exact permutation p of 0.032 — but the Hanley–McNeil interval
  at n = 9 vs 5 is [0.441, 1.071], which covers chance. Ten of twenty
  passages scored 1.000, two of them AI, so it cannot be a detector;
  every passage below 0.833 was AI and no human fell below it, so the
  usable form is a one-sided low-tail band. Annotator contamination is
  unquantified and the AUC is an upper bound.
- **Null: a subfield reference does not move the salience gate.** A
  254-abstract weak-lensing top-tier bank reproduces the broad bank's p90
  gates (0.500/0.500, 0.667/0.667, 2.000/2.200) and the case document
  reads p = 0.91 against either. `salience_baseline.json` needs no
  rebuild. Genre separates at the discipline level, not between astro-ph
  subfields.
- **The same bank must not become the register reference.** 254 documents
  cannot express a rate below 1/254 = 3.9e-3, 39.4× coarser than the 1e-4
  threshold, so `saddle`, `classifier`, `recall`, and `ablation` flip to
  foreign on zero counts. A register reference needs of order 10,000
  documents. The bank is stored and wired to nothing.

### Corpus tooling

The measurements above needed a weak-lensing top-tier reference to exist,
and building one exposed three gaps in the fetcher and one in the existing
banks. The human bank is astro-ph at large rather than the weak-lensing
subfield. The two
`ai_ism_negatives_generated*` banks carry no per-record generator, date, or
prompt, only the asset-level description in this file's v0.13 entry. And
the pre-2022 date filter turns out to bound less than it appears to.

- **The "pre-LLM human reference" guarantee was weaker than stated.**
  `--date-hi` filters `submittedDate`, which dates arXiv v1; the API's
  `summary` is always the *latest* version's abstract. 6,552 of the
  13,642 records in `human_abstracts_extra` (48.0%) are non-v1, and a live
  probe of twelve 2021 weak-lensing submissions found eleven with
  `updated > published`, two of them revised after 2022-11 — after the
  text could have been touched by a public LLM. `fetch_page` now records
  `published` and `updated`, and `--updated-before YYYY-MM-DD` drops every
  record whose latest version is dated on or after the cutoff. A record
  with no `updated` is dropped rather than assumed clean. The existing
  bank predates this field and is unaffected; re-deriving its text vintage
  needs a refetch.

- **`fetch_arxiv_abstracts.py` captures `journal_ref` and `doi`**, and
  gains `--journals apj,apjl,aa` to keep only those refereed venues.
  Selection is client-side against the literal `journal_ref` shapes seen
  live, because the API's own `jr:` prefix is a loose token match: a
  `jr:"Astronomy and Astrophysics"` probe returned *Research in Astronomy
  and Astrophysics*, a different journal. The Letters pattern is ordered
  before the main-journal pattern it is a substring of, and ApJS, A&A
  Review, and RAA are pinned as explicit negatives.
- **`--query-set wl`** adds a weak-lensing-only sweep, for a reference
  matched to the subfield rather than to astro-ph at large. The `broad`
  default is byte-identical to the previous query list.
- **Fixed: a rate-limited sweep was indistinguishable from a complete
  one.** The abstract path had no 429 handling at all — it caught the
  error, emptied the page, hit `if not page: break`, and abandoned that
  query, then walked into the same wall on every remaining query. A live
  run lost 11 of 16 queries this way, wrote 195 records, and exited 0.
  The full-text path *did* have a 60 s backoff, so this was one root
  cause at two sites: both now share `urlopen_backoff`, which escalates
  through a backoff schedule and then raises `Throttled`. A throttled
  abstract sweep stops, prints a TRUNCATED report naming the query it
  stopped at, and **exits 2**.
- **`--resume`** seeds from the existing output file, so a run cut short
  by throttling is extended rather than replaced. Without it the writer
  truncates its target, which is also why a journal or subfield run now
  must pass `--out-name`: reusing the default would have destroyed the
  broad corpus the calibration baselines are built from.
- **Measured, and it is a null: the subfield reference does not move the
  salience gate.** A 254-abstract weak-lensing top-tier bank (ApJ 75,
  ApJL 8, A&A 171; submitted 2010-01 to 2021-12, every latest version
  dated before 2022-11) reproduces the broad bank's p90 gates —
  `max_recital_run_frac` 0.500 vs 0.500, `recital_frac` 0.667 vs 0.667,
  `numerals_per_sentence` 2.000 vs 2.200 — and the same manuscript reads
  p=0.91 against either. `salience_baseline.json` therefore needs no
  rebuild, and an earlier p91 finding is not an artefact of the reference
  population. This does not contradict the discipline-level genre effect
  seen against cross-domain banks: genre separates at the discipline
  level, not between astro-ph subfields.
- **The same bank must NOT become the register reference.** `deai_register`
  calls a term foreign below a document-frequency rate of 1e-4, but 254
  documents cannot express a non-zero rate below 1/254 = 3.9e-3, 39x
  coarser than the threshold. Under that reference `saddle` — the central
  concept of one of this suite's manuscripts — flips from native to
  foreign purely on zero counts, as do `classifier`, `recall`, and
  `ablation`. A register reference needs of order 10,000 documents for a
  single occurrence to land at the threshold, so the broad bank stays.
  The new bank is stored but wired to nothing.
- **`tests/test_fetch_arxiv_abstracts.py`** (new, 25 tests): journal
  classification including the four near-miss venues, `fetch_page` over a
  canned feed (namespace-scoped `journal_ref`, whitespace-wrapped values,
  `published` vs `updated`), the backoff schedule under mocked 429s, the
  text-vintage filter, and the resume/truncate contract.

## v0.26.0 — 2026-08-16

Two new corpus-referenced axes, and the reduction fix that made the first
of them measurable at all. Both answer one reader complaint from
different directions: a draft can pass every existing axis and still read
as a machine inventory written for a neighbouring discipline.

- **Fixed: every numeral in a LaTeX manuscript was invisible to the
  subsystem.** `extract_style.latex_to_plain` replaces each math span
  with the token `[math]`, which is right for lexical and sentence-shape
  statistics and destroys the digits. Any signal about how a passage
  distributes its measured quantities therefore read identically zero on
  real `.tex` input — a recital-dense abstract measured 0.0 numeric
  density. The new `latex_to_numeral_text` is a second named projection
  sharing the same pattern set and differing in one decision: it keeps
  the numerals inside *inline* math. Displayed equations are dropped by
  both, because their digits are the constants of a definition rather
  than quantities the prose reports. `latex_to_plain` is unchanged, so
  every existing calibration asset stays valid.

- **New axis `L2.salience_hierarchy` (`deai_salience.py`).** Measures
  whether a passage ranks what it reports or recites it. The
  discriminating quantity is not numeric density — a quantitative
  abstract is supposed to carry numbers — but how far the numerals run
  without an interpreting sentence between them. Calibrated per section
  bucket on the field's own passage banks (13,438 abstracts for the
  `wgl` abstract reference) and read as P(X ≤ x) against a 0.01 quantile
  grid, because two of the three features are ratios of small integers
  and a coarse grid swallows a passage that lands on a tie plateau. One
  finding per over-recital passage, led by its most extreme feature;
  emitting one per feature tripled the count of a single defect.

- **New axis `L0.register` (`deai_register.py`).** Flags terms the
  manuscript leans on that the field's own corpus does not carry — the
  tell of a paper written in a neighbouring discipline's register. The
  judgement is corpus document frequency, never a curated "foreign word"
  list, and the corpus says why: in the 15,599-passage astronomy
  reference `AUC` appears in 1 passage while `epoch` appears in 402 and
  `accuracy` in 774, so any hand-written cross-discipline blacklist
  flags all three. Three constructions that defeat a naive frequency
  test are handled rather than thresholded away: hyphenated compounds
  are judged by their rarest part (`aperture-mass` is native via
  `aperture`), subscript decorations in macro bodies are not terms
  (`\Kraw` renders `K_raw`, not the word "raw"), and possessives fold
  onto the bare term. Advisories only — field register is the author's
  judgement, and a corpus-rare term may be the concept the paper
  introduces.

- **Guard: a reference with no spread above the advisory gate abstains.**
  When every reference passage above p90 shares one value, P(X ≤ x)
  reaches 1.0 there and an ordinary passage reads as the 100th
  percentile. The affected feature declines to rank rather than
  inventing a finding.

- **Recorded negative result.** A subordination-versus-coordination
  ratio was prototyped as the formalisation of "flat prose" and refuted
  against the same human reference: the manuscript under review sits at
  the 77th percentile of hypotaxis, above the human median, so flatness
  is not a deficit of subordinate structure. Not shipped; recorded in
  `docs/EVALUATION.md` §14 so it is not re-proposed.

- Both axes are wired into `ai_ism_lint` (`--register` / `--salience`,
  default on) and emit advisories only, so the 0/1/2 exit contract is
  unchanged. 32 new tests (147 total); standard updated to v3.5.

## v0.25.1 — 2026-08-06

CI-repair patch; no behavior change to any tool or skill.

- **CI green for the first time since v0.20.0.** The numpy-backed
  bootstrap-AUC test lacked the optional-dependency guard the two
  joblib-gated tests already had, so every hosted run since 2026-07-17
  failed with `ModuleNotFoundError` (the workflow installs no optional
  dependencies by design). Guard added in `67a6b55`, verified both ways
  locally (115 discover tests with numpy; skip-not-error with numpy
  import-blocked); first green runs are 31133202443 (push) and
  31133215203 (manual dispatch).
- **`workflow_dispatch` trigger added** (`6886679`) so CI can be
  retried without an empty commit — during the 2026-08-06 GitHub
  Actions outage, pushes produced no runs and there was no manual
  lever.
- Release gate: validator 8/8, 115 unit/CLI tests, and a green hosted
  CI run on the release tree (the CI-green condition is recorded in
  EVALUATION §12 as part of the standing gate).

## v0.25.0 — 2026-08-06

Hardening patch on the v0.24.0 consistency release.

- **Validator: versioned doc headers are now gated.** `check_manifests`
  additionally requires the header lines of `docs/DEAI_SUBSYSTEM.md` and
  `docs/EVALUATION.md` to carry the current release version — the one
  surface the v0.24.0 sweep missed (two stale `v0.23.0` headers shipped
  and were fixed post-tag in `475f632`). The class of miss is now a
  release blocker instead of a review catch.
- **Full-repo debug round (all green, recorded here as the release
  gate):** validator 8/8; 115 unit/CLI tests; 33/33 tracked `.py`
  compile; 22/22 tool `--help` entry points exit 0; zero TODO/FIXME and
  zero bare `except:`; all tracked JSON parses; 20 markdown files with
  zero broken relative links; linter exit semantics re-verified on true
  process exit codes (Tier A fixture exits 1 with the `tier-a:delve`
  target present).

## v0.24.0 — 2026-08-06

Documentation-consistency release: two audit rounds (2026-08-06) drove
every finding to closed; no behavior change to the L0 linter or the
measurement axes.

- **Docs single-sourcing.** The validator check list is now authoritative
  in `validate_plugin.py` with descriptive mirrors marked as such
  (`README.md`, `docs/DEAI_SUBSYSTEM.md`); the de-ai/condense boundary
  block has one canonical home (`de-ai` SKILL.md §0); the product-tool
  registry ownership is stated (`README.md` machine-checked,
  `tools/README.md` adds calibration/failure detail).
- **Contradictions closed.** `brainstorm` is now explicitly the one
  non-normative skill in both `SCIPAPER_STANDARD.md` §7 and
  `docs/DEAI_SUBSYSTEM.md` §7 (matching `NORMATIVE_SKILLS`);
  `extract_style.py` no longer invites hand-editing generated evidence;
  stale v0.14.0 anchors in `DEAI_SUBSYSTEM.md` §11 and `EVALUATION.md`
  §12 are dated or superseded by the current release-gate record;
  perceptual AUC unified at 0.444 (EVALUATION §7).
- **Command fixes.** The whole-document calibration command in
  `tools/README.md` now matches the real CLI (`--field` + `--calibrate`
  `--corpus-dir`); the dead cross-repo link in `EVALUATION.md` §11 is a
  commit-pinned citation.
- **Registry completeness.** `style-profile/README.md` layout now lists
  `voice_model_evaluation.json`, `anchoring_baseline.json`, negative/extra
  banks, and `docval/`, and documents the second populated field
  (`wgl-letter`, 11-paper Letter-register corpus, built 2026-07); the
  `figure-review` frontmatter carries `disable-model-invocation` and an
  `argument-hint` like every other skill.
- **Tool hygiene.** The validator's exit-2 fixture no longer leaks a
  spurious stderr line above the first `[ok]`; `deai_metrics._bucket_for`
  narrows its exception guard with a stated reason.

## v0.23.0 — 2026-07-18

Skill consolidation: 11 skills become 8 mutually orthogonal directions.
The three de-AI surfaces merge into one `de-ai` skill, the two review
augmenters fold into paper-review dimensions, and a new `condense` skill
becomes the §5.3 action surface.

- **New skill `de-ai`.** Merges `academic-humanizer` (the Layer 1--5
  structural-tell catalog with patterns 2.12--2.16 and the Pass-2
  self-interrogation, both MIT upstreams credited), `rewrite-in-voice`
  (the claim-first rewrite engine with hard fidelity eligibility and the
  §5.3 length gate), and `paper-style` (field-corpus calibration, dossier
  freshness, exemplar retrieval) into one three-pass pipeline:
  measure (L0--L4) -> humanizer audit -> claim-first rewrite.
  `--audit-only` runs passes 1--2 for review integration; `--no-apply`
  proposes without writing.
- **New skill `condense` (精简).** Whole-document elimination of all
  unnecessary and cross-document duplicated content, executing the
  standard's §5.3 policy: delete > condense-in-place > same-length
  rewrite, growth only with recorded justification;
  one-canonical-home-per-fact deduplication with a genre carve-out for
  abstract/conclusion restatement; loop-until-dry convergence; the length
  gate closes every pass. Redundancy detection stays in paper-review
  dimension I; condense executes the fixes.
- **paper-review absorbs `mainline` and `paper-attack-tree`.** Dimension E
  gains the narrative-spine protocol (purpose record, contribution graph,
  cold-read questionnaire, multi-contribution legitimacy); dimension M is
  sub-structured into M.1 (the existing three-pass derivation
  verification) and M.2 (the 12-framing radial escalation with S/P/R/F/B
  scoring and CONFIRMED/REFUTED/MARGINAL verdicts, no deferred leaves,
  in-process by design); dimension D's structural-tell audit now invokes
  `de-ai --audit-only`. A--R lettering unchanged.
- **final-review re-orchestrates to four isolated reviewers.**
  paper-review, figure-review, the `de-ai --audit-only` audit, and the
  parent-level modern-physics review. `condense` is positioned as an
  action skill on dimension-I findings, not a fifth review lane.
- **figure-review gains pixel-measured canvas balance (§2.4.1).**
  Opposing outer margins must agree within max(2 px at 150 DPI, 1% of the
  canvas width); fixes go to the generator (right pad = measured left
  axis-title + tick column), never to an absolute nudge.
- **SCIPAPER_STANDARD v3.4.** Records the consolidation and rebuilds the
  §7 responsibility table as a complete 8-row registry; no policy in
  §§0--6 or §§8--11 changes. Docs, tool strings, and directory READMEs
  re-point to the surviving skills; both MIT attributions survive in the
  README Acknowledgments and the `de-ai` provenance block.

## v0.22.0 — 2026-07-18

`academic-humanizer` absorbs the academically-relevant structural tells
from blader/humanizer (MIT), a second upstream after the AIScientists-Dev
port in v0.21.0.

- **Five new Layer-2 structural patterns (2.12--2.16).** False ranges
  (categorical "from X to Y"), aphorism formulas ("X is the Y of Z"
  epigrams), persuasive-authority tropes ("at its core", "fundamentally"
  as empty emphasis), manufactured staccato drama (runs of terse fragments),
  and hyphenated-pair predicate overuse ("the result is model-dependent").
  Each is framed as structural, not lexical, and carries a corpus caveat so
  genuine quantitative ranges, formal definitions, real physical
  distinctions, single emphatic sentences, and attributive compound
  modifiers are never flagged.
- **Pass-2 self-interrogation step (Process §3.5).** After the first
  rewrite of a span, ask "what still reads as machine-written here?",
  answer in 2--4 concrete bullets, and apply one further targeted rewrite
  that re-clears the fidelity and length gates. Neutral-and-precise stays
  the target; the pass strips tells, it does not manufacture voice.
- **False-positive guards added to Layer 3.** Formal vocabulary alone, a
  single mixed register, isolated curly quotes, a lone emphatic short
  sentence, and text inside quotations / caption labels / worked examples
  are explicitly not tells.
- **What was NOT adopted.** blader/humanizer's blog/chat-specific patterns
  (emoji, title-case headings, chatbot artifacts, curly-quote flags) and
  its `landscape`-flagging word list are deliberately excluded; they
  conflict with the plugin's corpus evidence (`landscape` is a measured
  legitimate astro term). Attribution added to the SKILL provenance header
  and README Acknowledgments.
