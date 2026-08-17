# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.27.1 — 2026-08-17

v0.27.0 fixed the section classifier and measured what it would change. This
release carries out the rebuild that fix required and writes the resulting
numbers back into the evaluation record. No code, consequence class, exit code,
or normative policy changed; every edit here is a measurement or a document.

### The rebuild, and what it moved

The full `wgl` profile was rebuilt with the fixed classifier — extraction, then
each `--calibrate` stage, then a complete `train_voice_model.py` retrain
(18,647 rows, 20/20 audit splits completed). `wgl-letter` was rebuilt alongside
it. Every figure below is read from the rebuilt artifact, not from the v0.27.0
projection.

- **Reference banks.** `structure_baseline` and `uid_baseline` now hold 1,942
  paragraph observations across six buckets rather than 1,957 across five;
  `results` gains a surprisal reference for the first time. Salience buckets
  move `method` 1,377 → 1,303, `discussion` 35 → 78, `conclusion` 26 → 41, and
  gain `results` at n=10. `conclusion` crosses the 30-passage floor, so it is
  `measured` rather than rank-only for the first time. The register reference
  goes 15,599 → 15,584 passages and 41,933 → 41,714 terms.
- **The learned model barely moved, and that is the result.** Comparing the new
  audit against the pre-rebuild record key by key, every headline figure changed
  by at most 0.002 in AUC (primary split 0.9414 → 0.9399; 20-split mean 0.9324 →
  0.9320) and the negative-control false-positive rates by at most 0.005. L3
  stays `degraded` with no operating point, for the same measured reasons.
- **What did move is the per-section audit strata, which were degenerate.** The
  `discussion` stratum held a median of 5 positive rows and some splits held
  none, so its minimum F1 and recall were both 0.000; post-rebuild the median is
  19 and those minima are 0.857 and 0.850. The `conclusion` stratum's smallest
  split rose from 3 rows to 9. Before the fix that breakdown was not measuring
  section behaviour — it was measuring an empty cell.
- **§15 was checked and left alone.** Its figures come from the abstract and
  generated banks, which are not section-bucketed; the rebuilt abstract
  percentile grids are byte-identical to the pre-rebuild ones. The v0.27.0
  notice that named §15 as affected was over-broad and is corrected.

### A stale artifact the rebuild exposed

The local `voice_model_evaluation.json` predated the hard-set restructure: it
carried only the retired `auc_low_score_predicts_strong_ai_feel` key, while
`EVALUATION.md` §7.3 already documented `primary_provenance` and
`perception_baseline`. The document was ahead of the artifact on disk, which no
gate checked because nothing compared documented figures against the file they
describe. The retrain regenerates the record in the current schema, and §7.3's
0.937 / 0.444 now reproduce from it.

### Resolved limitation

`EVALUATION.md` §7.5 recorded that the cloud bundle was built with scikit-learn
1.4.2 and emitted an unpickle-version warning under a newer local install, and
predicted a local rebuild would clear it. Verified: the retrained bundle loads
under local scikit-learn 1.8.0 with no warnings. The limitation is removed
rather than restated.

### Corrections

- `style-profile/README.md` quoted the pre-ligature-fix projection (`method`
  1672, `conclusion` 51, total 1944) where `CHANGELOG.md` and `EVALUATION.md`
  carried the re-measured 1671 / 50 / 1942. It was missed in the v0.27.0
  re-measurement sweep and now agrees with the artifact it describes.
- Profile snapshots taken before a rebuild now live in the gitignored
  `.backups/` inside the repository. A snapshot placed beside the repository
  reads as a project of its own in the parent directory and escapes the ignore
  rules that cover the same corpus-derived files.

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
  (`\Kraw` renders `S_sad`, not the word "sad"), and possessives fold
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

## v0.21.0 — 2026-07-17

The academic-humanizer becomes a standalone skill, paper-review gains a
per-round structural audit step, and the documentation tree is consolidated.

- **New skill `academic-humanizer` (11th skill).** Whole-repo port of
  AIScientists-Dev/academic-humanizer v0.3.3 (MIT; attribution retained):
  Layers 1--5 as a standalone audit-then-rewrite pass. Adaptations over
  upstream: corpus overrides are normative (landscape never flagged;
  demonstrate/significantly evidence-conditional only), rewrites must pass
  the fidelity and length gates, Layer 6 routes to the existing
  `proposal-polish` skill instead of being duplicated, and lexical tells
  defer to `ai_ism_lint.py` Tier A/B rather than re-deriving a word list.
  Field-validated before porting: a standalone audit run on a live
  manuscript found seven true positives (two colon-elaborations that the
  per-line linter regex misses at line breaks, three comma-splice
  run-ons, one Layer-1 lexical hit, one dense results sentence).
- **paper-review §D structural-tell audit step.** Every review round now
  runs the humanizer Layers 1--2 checklist (clause-stacking, negative
  parallelism, elegant variation, rule-of-three, formulaic openers,
  connective runs) in audit-only mode; structural hits are advisories,
  Layer-4 claim-evidence hits join §C as `integrity_blocker`.
- **Docs consolidated.** The canonical `EVALUATION.md` moved from the
  repository root into `docs/` (replacing the redirect stub that pointed
  the other way); all path references updated (README, standard,
  subsystem, roadmap links). `docs/` is now the single home for all five
  documentation files.

## v0.20.1 — 2026-07-16

Post-release independent audit of the v0.20.0 length gate (7 findings, all
dispositioned; the two High items were real defects in orchestration use).

- **JSON report is now self-describing.** `length_gate.py --format json`
  embeds a `length_budget` block (totals, justified growth,
  `net_unjustified_growth`, `tolerance_words`, `gate_exit`), so a downstream
  orchestrator derives the gate result from the report alone instead of
  parsing stdout or trusting the process exit.
- **Allowance accounting matches the documented net formula.** Every allowed
  positive section delta is credited to `justified_growth`, including growth
  below the per-section flagging tolerance; previously an allowed
  sub-tolerance growth was not credited and could flip a compliant edit to
  exit 1.
- **Ambiguous `--allow` keys are a configuration error (exit 2)** instead of
  silently authorizing every matching section.
- **Heading stripper covers `\\section[short]{long}` and one level of nested
  braces**, keeping renames of those forms budget-neutral.
- Registry/skill wording aligned with shipped behavior (net-exit semantics in
  the top-level README; rewrite-in-voice ranking terms name L0 advisory
  reduction, fidelity, voice, condensation, with specificity
  transparency-only).
- New tests: allowance-tolerance interaction, ambiguous key, optional-argument
  heading rename, self-describing JSON, empty-original budget, and three
  mocked `rank()` integration cases (-inf over budget, `allow_growth` lift,
  fidelity-floored condensation bonus). Suite: 115 tests green.

## v0.20.0 — 2026-07-16

§5.3 (condense, do not accumulate) gets mechanical enforcement. Standard bumped
to **v3.3**. Design: prevent at candidate time, detect at loop close, and make
recorded justification the only path for growth — three layers, all auditable.

- **New tool `length_gate.py` (tools: 21 → 22), the loop-close delta gate.**
  Compares per-section rendered-prose word counts (comments and math excluded
  via `latex_to_plain`) between the pre-edit baseline (`--before <snapshot>` or
  `--git-ref <ref>`) and the edited file. Each unjustified growing section
  emits a strong advisory `length-growth:<section>` (strong advisories already
  require an explicit disposition before a loop may close); `--allow
  "<section>=<reason>"` (case-insensitive, substring-tolerant) /
  `--allow-total <reason>` convert it to an ordinary
  `length-growth-justified` advisory that carries the recorded reason into the
  report. The exit code gates the NET budget: 0 when total growth minus
  justified growth is within `--tolerance-words`, 1 beyond it, 2 for invalid
  input (negative tolerance, empty reason, missing baseline) or execution
  failure; a pure section rename nets to zero. Registered in standard §0.1.
- **`rewrite_reward.py` length-budget hard gate (candidate time).** New
  `--original <paragraph>` input: a candidate longer than the original scores
  `-inf` regardless of style evidence (`length_eligible` joins fidelity in the
  eligibility conjunction); `--allow-growth <reason>` lifts the gate for one
  run and prints the reason; within budget a `CONDENSATION_WEIGHT` bonus
  prefers the shorter of otherwise-equal candidates. CLI prints a
  `words(o/c)` column and the over-budget diagnosis.
- **Contract wiring.** Standard §5.3 enforcement paragraph + §0.1 exit
  exception + §8 tool row; `paper-review` §1 snapshot step (6b), §4 step 8
  (gate must exit 0 before the loop closes), §6 report length-budget row, §7
  stopping condition; `rewrite-in-voice` §2.1 saves `original.txt`, §2.4
  passes `--original`; `paper` mirror notes the two mechanical gates.
- Section headings are stripped before counting, so a section rename cannot
  register as prose growth; independent review (2 accepted defects, net-exit
  redesign, substring `--allow`, UTF-8-lossy git baseline, input validation)
  is folded in.
- New tests: `tests/test_length_gate.py` (10 CLI cases: shrink, unjustified
  growth, justified growth, comment/math exclusion, shared JSON schema,
  missing-baseline / negative-tolerance / empty-reason failures, rename
  netting, substring allowance) and 3 `length_budget` unit cases. Suite: 107
  tests green.

## v0.19.0 — 2026-07-16

Academic-humanizer integration (github.com/AIScientists-Dev/academic-humanizer,
MIT; acknowledged in README) plus the condense-not-accumulate rule. Standard
bumped to **v3.2**.

- **New normative rule §5.3 — condense, do not accumulate（改写、删减、精简，
  而不是堆叠）.** The default direction of every edit is shorter: delete >
  condense in place > same-length rewrite > growth; growth is legitimate only
  for author-requested content or source-verified scientific necessity. The
  explanatory patch (appending a clarification to flagged text instead of
  rewriting it) is the canonical violation. Fix loops report a per-passage
  length delta; clearing a detector signal by inflating prose is a defect.
  Mirrored in `paper` (writing), `paper-review` §4 (fix loop), and
  `rewrite-in-voice` §2.3/§2.5 (candidate constraint + re-measure check).
- **Proposal routing note in `paper-review`:** funding proposals are reviewed
  under the `proposal-polish` register; the L0 policy and §6 invariants carry
  over, paper-mode significance trimming does not.

- **Lexicon extensions, corpus-verified.** `LLM_TYPICAL_WORDS` gains
  `underscore*`, `intricate`, `tapestry`, `testament`, `pivotal`, `foster*`,
  `realm*`; profiles regenerated for both fields. Zero-in-both-corpora words
  (`underscore*`, `tapestry`, `testament`, `pivotal`, `realm*`) enter Tier A
  (linter `TIER_A_PATTERN` + `skills/paper/SKILL.md` canonical table);
  `intricate` (1 hit per corpus) and `foster*` (1 hit in wgl) enter Tier B.
  `landscape` deliberately NOT adopted (legitimate domain term, 192 hits in the
  combined corpus); blanket `demonstrate`/`significantly` bans NOT adopted
  (0.147/1k and 0.274/1k in astro corpora — evidence-conditional rules instead).
- **New linter rules** (all advisory): `ing-tail` (curated participial-tail verb
  set, L2), `colon-elaboration` (appositive-elaboration prose colon, L2; user
  style rule 2026-07-16 — caption tags and list specifications stay legitimate),
  and `serves as` added to the `style-substitution` set (L0 advisory).
- **Claim–Evidence Discipline** section in `skills/paper/SKILL.md` (QD;
  operationalizes the existing claim-evidence `integrity_blocker` class):
  unbacked claim → evidence pointer or soften; verb strength ≤ evidence
  strength; vague magnitude → attributed number or range; compare against the
  strongest baseline; `significantly` requires an accompanying test or number.
  Mirrored as a review-side item in `paper-review` §2.C.
- **Preserve List** (anti-over-correction guard) in `skills/paper/SKILL.md`:
  evidence-tied hedging, actor-irrelevant passives, first-person plural,
  definitions/symbols/citations stay; strengthening a hedged verb is itself a
  claim-evidence defect. Mirrored in `paper-review` §2.D.
- **New skill `proposal-polish` (skills: 9 → 10).** Funding-proposal editing
  mode adapted from academic-humanizer Layer 6: NSF/NIH structural anatomy,
  first-pages primacy, proposal-specific weak moves (vague importance,
  method-as-aim, dominoed aims, ambition-without-feasibility, boilerplate
  broader impacts, hedged central hypothesis), preserve-and-deploy craft list,
  claim ↔ feasibility discipline, and hard anti-fabrication rules.
- New tests: 5 CLI cases (`tier-a:pivotal`, `ing-tail`, `colon-elaboration`
  with `\ref{fig:...}` exemption, `style-substitution:serves as`, Tier B
  `intricate` cap). Suite: 93 tests green.

## v0.18.0 — 2026-07-14

Panel-validated release: a blind A/B perceptual panel on a real 31-page ApJ
draft (three versions of the same document under a mechanical fidelity gate)
surfaced a second stratum of machine-writing tells and validated the reading
protocol for perceptual scores. Standard bumped to **v3.1**.

- **New auxiliary L2 template families in `deai_structure`** (panel-derived,
  corpus-calibrated): `antithesis-cluster` (2+ contrastive "X rather than Y" /
  "not X but Y" frames in one paragraph; human base rate 0.2% of 1,957 wgl
  paragraphs vs 5.6% in the audited drafts, a 28x separation) and
  `short-reversal` (a reversal sentence of 5 words or fewer, e.g. "It would
  not."; human base rate 0/1,957). Both emit ordinary advisories under the new
  `structure-auxiliary:<bucket>` rule and are **excluded from `template_score`**,
  so the calibrated document-dispersion manifold consumed by
  `deai_docstructure` is unchanged. `structure_baseline.json` recalibrated with
  the new per-bucket fractions (`auxiliary_frac`, `antithesis_cluster_frac`,
  `reversal_frac`).
- **Blind perceptual panel recognized as an L2 validation instrument**
  (standard §2 L2): independent cold-read judges score `ai_feel_1to5` and must
  name tells with verbatim quotes. The normative reading is **tell-inventory
  turnover, not the mean score** — judges saturate on the most visible tell
  family, so removing it exposes the next stratum at a similar score.
- **EVALUATION §13: the case study.** Three versions paneled at mean scores
  2.0 / 2.0 / 2.25 while the top tell named turned over completely (announced
  enumeration 4/4 judges → 0/4 after the de-scaffold rewrite). The upgraded
  detector cross-validates the panel: template findings 8→0→0, auxiliary
  findings 4→6→1 across pristine / Phase A / targeted-revision versions.
- **Aphoristic "perform rigor" closers** documented as a panel-advisory class
  (no reliable lexical pattern; handled by rewrite instruction, not a
  detector).
- New test module `tests/test_deai_structure.py` (6 tests: cluster detection,
  reversal detection, clean-prose negative, sub-threshold negative,
  `template_score` isolation, finding-rule emission). Suite: 88 tests green.

## v0.17.0 — 2026-07-13

Normative-standard release: `docs/SCIPAPER_STANDARD.md` is updated to **v3** and
is now the complete de-AI standard. There is no separate de-AI standard document
— the sci-paper standard includes it.

- **The de-AI subsystem is fully specified in the single authority.** v2 predated
  the v0.13–0.16 buildout; v3 adds the document-scale detection core (per-stratum
  dispersion manifold, role-coupled dispersion, split-conformal operating points),
  the L2 claim-anchoring writing-quality band, the offline-audit-instrument status
  of the L3 learned classifier, and the cooperative L4 repair layer
  (`deai_partition`, `deai_provenance`, `deai_personal`) — each with its axis,
  measurement state, and confound status.
- **`calibration_unit` is now in the finding contract (§3).** The paragraph
  confidence cap is stated normatively: a single paragraph is near-unjudgeable, so
  paragraph-unit findings are structurally capped at 0.5; `null` is uncapped.
- **New: the de-AI-ization procedure (§5.2, 去AI化步骤).** An ordered,
  layer-by-layer normative procedure for removing machine-writing regularity —
  L0 to zero, L1 distribution, L2 sentence and document structure (via
  fidelity-free partition), L4 anchoring and voice, the confound-free
  provenance/personal self-checks, then invariant-protected re-measurement — with
  the concrete move and tool named at each step. The target is faithful writing
  quality, never detector evasion.
- **Length is stratified, never normalized (guardrail 9).** Dividing a
  document-scale distance by a function of paragraph count is prohibited as a
  length-confound exploit (measured in EVALUATION.md §9.8).
- **Every open item is dispositioned (§11).** The ranked frontier is complete; the
  remaining roadmap ranks (2/3/4/6), the degraded L1 (distribution and UID) and
  L3.voice operating points, and the `ai_long` standing target each carry a decided
  disposition, so the standard rests on no undecided obstacle.

No product code changed; the tool and test registries are unchanged (21 tools, 9
skills). Validator and the 82-test suite pass.

## v0.16.0 — 2026-07-13

Closes the ranked de-AI frontier and the last recorded measurement debt. Two new
cooperative-layer tools finish the frontier queue (17 → 19 → 21 tools), two
roadmap ranks land, and the document-level L3 surprisal question is resolved on a
cloud pass. Every result is measured in EVALUATION.md §9.8–9.9; three findings
came back negative and are recorded, not deleted.

- **Editing-provenance ledger (`deai_provenance.py`, new tool — frontier idea 4).**
  Inverts the question from "is this AI?" to "have my edits made it mine?" Matches
  each current paragraph to its nearest paragraph in a designated AI-draft ancestor
  (an earlier file or a git ref from the author's own history) and labels the span
  `ai_untouched` / `lightly_edited` / `rewritten` / `author_original` by a
  deterministic token edit ratio (difflib, no model). Reads only the author's own
  history; `unmeasured` without an ancestor (EVALUATION.md §9.9).
- **Personal dispersion baseline (`deai_personal.py`, new tool — frontier idea 6).**
  Uses the author's own prior papers as the confound-free dispersion reference:
  same author, same field, same jargon, so it sidesteps the field-topic
  false-positive rate (32–41%) entirely. Flags a draft that varies paragraph shape
  far less than the author usually does; `unmeasured` below three prior papers
  (EVALUATION.md §9.9).
- **Document-level L3 surprisal — measured and refuted (the last cloud debt).** A
  gpt2-large pass over 38,319 paragraphs (507 human + 154 AI docs) shows
  document-scale surprisal dispersion (pooled AUC 0.757) is weaker than the
  model-free manifold (0.881) and adds nothing to it (0.878). The detector stays
  model-free by measurement at document scale too; L3 stays `degraded` for a
  measured reason (EVALUATION.md §9.8).
- **Rank 5 (enriched surprisal) — confirmed but inert.** Five enriched surprisal
  descriptors (skew, kurtosis, filler rate, burstiness, low-frequency spectral
  energy) beat the three shipped scalars (0.803 vs 0.757), but since surprisal is
  not in the shipped model-free detector they would be dead weight — recorded, not
  added (EVALUATION.md §9.8).
- **Length-normalization refinement — measured as a confound trap.** Dividing
  manifold distance by √(paragraph count) appears to lift AUC to 0.929, but that is
  a length confound (human papers median 60 paragraphs vs 11–15 for AI tiers); a
  human-null-calibrated normalization gives 0.752 and a length-matched band shows no
  gain. The per-stratum manifold plus length-Mondrian conformal remains the
  confound-safe length handling (EVALUATION.md §9.8).
- **Rank 7 — dead specificity term replaced (`rewrite_reward.py`).** The retired
  `specificity` term was identically 1.0 for every eligible candidate (the
  eligibility gate already forces the reference numbers in), so it did no ranking
  work. Replaced with a signed L0-advisory-reduction delta (reusing `ai_ism_lint`)
  gated by a semantic-fidelity floor, so ranking now rewards the actual writing
  improvement a rewrite makes.
- **Rank 8 — `calibration_unit` honesty cap (`deai_feedback.make_finding`).** A new
  `calibration_unit` field (paragraph|section|document) structurally caps
  paragraph-unit findings at 0.5 confidence (a single paragraph is near-unjudgeable,
  perceptual AUC 0.44). Wired through every detector at its true granularity; the
  learned per-paragraph classifier (`deai_voice`) is now capped by construction.
  Backward-compatible: `None` (every prior caller) is uncapped.

## v0.15.0 — 2026-07-13

The document-scale de-AI release: a validated detection core (dispersion band →
joint manifold → role coupling → split-conformal operating points), the first
repair path for document-scale findings, a claim-anchoring quality band, and a
corpus grown 14 → 507 human papers plus five AI validation tiers. Every claim in
this release is measured in EVALUATION.md §9; refuted hypotheses (surprisal
recovery, perceptual hard-set labels, the under-anchoring AI tell) are recorded
rather than deleted.

- **Partition operators (`deai_partition.py`, new tool).** Merge/split suggestions
  that move a document toward the human dispersion band; zero-token operations, so
  the rewrite fidelity gate holds by construction. Suggest-only with a
  self-normalized cohesion floor; reordering deliberately excluded. Efficacy: 4 of 8
  conformally flagged AI docs brought inside the band (median 1 op); 116/116
  unflagged docs untouched (EVALUATION.md §9.7). Wired into `rewrite-in-voice` as
  the sanctioned lever when document-dispersion findings persist.
- **Claim-anchoring band (`deai_anchoring.py`, new tool).** Section-class
  conditional anchored-sentence rates (number/citation/\ref/math/comparison) against
  517 corpus documents, low-tail conformal with a Bonferroni share per class
  (document-level human false-flag 0.037 ≤ α). Shipped explicitly as a
  writing-quality axis: the "under-anchoring is the AI tell" hypothesis is
  **refuted** for strong-model full-paper generations, which anchor above the human
  level (EVALUATION.md §9.6). Wired into `paper-review`.
- **Per-stratum (length-aware) manifolds.** Each length stratum with enough
  training/calibration papers gets its own manifold; `manifold_operating_point` is
  the single scoring entry for findings, partition, and evaluations. Structure
  clones caught at twice the rate (0.125 → 0.292); adversarial 0.026 → 0.053
  (EVALUATION.md §9.7).
- **The `ai_long` validation tier (29 long-form generations).** The measured
  frontier: manifold flags 0/29, role 4/29 at α = 0.05, while ranking signal
  survives (stratum-matched AUC 0.716/0.639). Long-form natural generation is
  recorded as the standing falsification target (EVALUATION.md §9.7).

### Document-scale dispersion detector + hard-set correction

**Document-scale cross-paragraph dispersion detector (architecture keystone).** A
five-lens architecture reflection ([`docs/DEAI_ARCHITECTURE_ROADMAP.md`](docs/design-notes/DEAI_ARCHITECTURE_ROADMAP.md))
identified that AI-ness in scientific writing concentrates at the document scale, which
the paragraph-level detectors structurally cannot see.

- `deai_features.cross_paragraph_dispersion` / `feature_dispersion`: per-feature spread
  (std/cv/iqr/lag1-autocorrelation/min-gap) of the per-paragraph features across a
  complete document. Stdlib, no GPU.
- `deai_docstructure` now attaches a model-free dispersion profile and calibrates a
  human dispersion **band** at two levels: a joint Mahalanobis dispersion manifold
  (`fit_dispersion_manifold` / `manifold_distance`, pure stdlib, primary finding at the
  95th-percentile distance) and per-feature two-sided band flags (5th/95th percentile
  low/high tails, demoted to ordinary context when the manifold is present). `calibrate`
  takes `(name, text)` or `Path`; multi-file papers are concatenated into one
  observation.
- **Calibrated over 507 complete human `wgl` papers** (new bulk arXiv full-text channel
  in `fetch_arxiv_abstracts.py --fulltext`: 475 papers fetched politely from local-ID
  candidates); manifold leave-one-paper-out false-flag rate 0.063, per-feature tails
  0.051 median. `L2.document_structure` is `measured`; every finding states only the
  measured deviation from the human corpus, not an AI verdict.
- **Role-coupled dispersion (`document-role-decoupling`).** Humans vary paragraph shape
  where the argument demands it; both AI failure modes (uniform and forced-ragged) vary
  it at random with respect to rhetorical role. Per-document permutation-normalized
  eta-squared over two role factors (which-section, has-math × has-cite; split-half
  selection rejected in-section position as chance). Held-out confirmation AUC: natural
  0.846, de-AI'd 0.833, adversarial 0.850, skeleton 0.715 (full-set adversarial 0.888,
  CI 0.847–0.926, with residual selection optimism) — the shape adversary that narrows
  the manifold's margin is this axis's strongest tier, because random variety cannot
  fake role-coupling. The manifold+role union flags 0.68–0.80 of AI tiers at ~0.10
  human in-sample cost, and the two 5% flag sets are exactly disjoint on the 507 humans
  (EVALUATION.md §9.4). Structure cloning evades role-coupling (0.658) but is caught by
  the manifold (§9.3): the axes cover each other. Known quantified bias: flagged human
  papers skew short (median 38 vs 60 paragraphs).
- **Split-conformal + Mondrian operating points (`baseline["conformal"]`).** The two
  strong document findings now flag on conformal p-values: the manifold is fit on a
  304-paper proper-training split and calibrated on 203 held-out human papers; the
  role z (no fit needed) calibrates on all 507. P(false flag) ≤ α = 0.05 finite-sample
  and distribution-free for exchangeable human papers, stratified by document-length
  terciles (the measured confound). Legacy baselines without the block fall back to
  the percentile thresholds. Independent three-way replication: human test rates
  0.029 (manifold) / 0.069 (role) at α = 0.05.
- **Corrected: earlier flag rates were length-confounded.** Stratification exposed
  that short human papers score systematically higher manifold distances (stratum-0
  95th percentile 5.23 vs 4.16/4.36) and all AI validation docs are short, so the
  unstratified thresholds had overstated tail power (e.g. natural 0.607 → honest
  0.071 at length-fair α = 0.05). The discrimination itself survives length matching:
  manifold length-fair AUC 0.82–0.90 across all four tiers (consistent with the
  paired skeleton test), role 0.70–0.82 with the skeleton tier at chance (its earlier
  0.658 was length artifact). Full corrected picture in EVALUATION.md §9.5.
- **Post-review hardening of the role axis** (multi-agent adversarial review; the
  verifier stage hit session limits, so every finding was manually re-verified against
  the code): NaN/inf feature columns no longer bypass the eta-squared guard via
  `min(1.0, NaN) == 1.0`; unequal-length paragraph vectors raise instead of silently
  truncating under `zip`; a baseline whose `scoring_factors` differ from the current
  code disables the role finding instead of comparing against mismatched thresholds;
  the math marker regex no longer counts escaped dollars (`\$`) or row breaks
  (`\\[5pt]`) as math. Baseline regenerated; all discrimination numbers re-measured
  (unchanged within rounding).
- **Fixed: baseline quantile CIs were zero-width.** The "deterministic balanced"
  resampler indexed `(iter*17 + idx*31) % n`, a full permutation whenever
  gcd(31, n) = 1 — every bootstrap CI in the document baseline was degenerate and
  overstated certainty. Replaced with a seeded with-replacement bootstrap; baseline
  regenerated.
- **Held-out validation** (242 reference / 242 never-touched humans): natural AI AUC
  0.917 (CI 0.874–0.951), de-AI-rewritten 0.931 (CI 0.888–0.965) — a 22%-of-text
  paragraph-level de-AI rewrite barely moves the document signal — and a deliberate
  paragraph-shape adversary 0.895 (CI 0.855–0.930). The adversarial number is the honest
  arc's endpoint: one-sided low-tail scoring collapsed to chance at realistic reference
  breadth, the adversary's overshoot motivated the two-sided band (0.801), and the joint
  covariance geometry recovered the rest (EVALUATION.md §9).
- **Skeleton-matched falsification (format artifact ruled out).** 24 AI papers generated
  to the exact structural skeleton of 24 human papers (sections, paragraph counts,
  sentence counts); on the 17 compliant pairs, with the manifold refit excluding all
  sources, the AI clone still separates from its own identically-structured human source
  at paired AUC 0.934 (CI 0.830–1.000) — 0.920 (CI 0.810–1.000) after dropping the two
  count features the skeleton pins. The signal is intra-format prose texture, not paper
  format (EVALUATION.md §9.3).
- **Full-feature cloud pass refuted the surprisal-recovery hypothesis.** Against the
  adversarial tier, surprisal-only dispersion scores AUC 0.677 (CI spans chance) and the
  GPU model features add nothing to the robust punctuation/clause-rhythm core (0.921 with
  vs 0.914 without), while including gamed features dilutes the detector (full-14 0.673).
  The shipped document detector is model-free and GPU-free by measurement (EVALUATION.md
  §9). Honest limits (small n per tier, single field and generator) are recorded.

### Hard-set evaluation correction

Corrects a statistically wrong claim in the v0.14.0 evaluation record and reframes the
author hard set around true provenance instead of perception.

- **Provenance is the hard-set yardstick, not perception.** `hardset_evaluation` now
  reads `deai_hardset_key.csv` and reports, as the primary metric, the model's AUC for
  separating true generated-vs-human paragraphs (0.937, bootstrap CI 0.860–0.990). The
  author's perceptual `ai_feel` rating is demoted to a task-difficulty baseline: it
  separates the same true provenance only at chance (AUC 0.444, CI 0.304–0.582), showing
  that single decontextualized paragraphs carry too little signal for reliable human
  AI-judgement.
- **Withdrawn claim.** v0.14.0's EVALUATION.md called an AUC of 0.354 (model vs
  `ai_feel≥4`) "decisive" proof that the model measures field register, not AI-ness. That
  metric scored the model against the near-chance perceptual axis and, with only 8
  strong-feel labels, has a bootstrap interval of 0.141–0.588 that straddles 0.5. It is
  not distinguishable from random and is retained only as a low-power secondary line.
- **Every hard-set AUC now carries a seeded bootstrap 95% interval** (`_bootstrap_auc_ci`)
  so small strata cannot be over-read again.
- L3 remains `degraded`, now on the well-powered field-topic negative-control
  false-positive rates (§7.4) and the absence of a document-level calibration set, not on
  the withdrawn perceptual metric.

## v0.14.0 — 2026-07-12

**Unified scientific-writing feedback contract.** This release supersedes the
v0.13 de-AI semantics without erasing their historical record. The sole
normative authority is `docs/SCIPAPER_STANDARD.md`; corpus profiles, structural
baselines, UID measurements, and learned models are evidence, not competing
policy or authorship detectors.

- **Typed consequences and measurement states.** New
  `sci-paper.feedback.v1` findings distinguish `integrity_blocker`, `l0_target`,
  and `advisory`, with `measured`, `degraded`, `unmeasured`, and
  `not_applicable` axis states. Missing calibration is never converted to zero
  findings.
- **Feedback, not a universal prose verdict.** The shared workflow is measure →
  type → rank → edit → re-measure → disposition. Strong advisories require an
  explicit author disposition; ordinary advisories remain visible without
  blocking the paper.
- **Narrow L0 semantics.** Tier A lexical occurrences, prose em-dashes, and only
  Tier B occurrences above one use per section and word are rewrite targets.
  `ai_ism_lint.py` exits `0` with no L0 targets, `1` with L0 targets, and `2`
  for invalid input/configuration/execution; advisories never cause exit `1`.
- **Structured analysis.** Added deterministic sentence-template analysis and
  whole-document rhetorical-shape analysis. Complete papers are the independent
  calibration unit for document structure; paragraph exemplars cannot be
  relabelled as independent documents.
- **Claim-first rewrite eligibility.** Rewrite candidates must preserve protected
  numbers, units, citations, mathematics, acronyms, comparison direction,
  negation, and causal direction before ranking. Ineligible candidates receive
  negative infinity and cannot win on style or learned score.
- **Learned evidence renamed and bounded.** The optional learned model reports
  field similarity/compatibility for triage and eligible-candidate ranking, not
  `P(human)`. A bundle without a calibrated operating point remains degraded;
  source, section, length, jargon, and mathematical-density confounds remain
  explicit evaluation requirements.
- **All writing/review skills aligned.** `paper`, `paper-style`, `paper-review`,
  `figure-review`, `mainline`, `paper-attack-tree`, `rewrite-in-voice`, and
  `final-review` implement the same consequence, ranking, disposition, and
  stopping contract. Evidentiary `CONFIRMED` does not automatically mean
  blocker, and bounded-process `CONVERGED` is not a paper-quality verdict.
- **Profile/build boundary documented.** `build_profile.py` now identifies
  itself as a basic descriptive-profile builder. Sentence structure, UID,
  whole-document shape, learned field similarity, hard-set labels, and policy
  operating points have explicit independent build/calibration paths.
- **Validation strengthened.** The repository validator checks manifests,
  registries, skill frontmatter and standard references, normative/evaluation
  document authority, Python syntax/imports, CLI help, schema fields/enums,
  linter exit semantics, Tier B cap behavior, tests, and CI wiring. It rejects
  an active duplicate `docs/EVALUATION.md`; regression tests cover the shared
  schema, linter CLI, document structure, and rewrite eligibility.
- **Real-paper evaluation added.** `EVALUATION.md` records a source-traced,
  proposal-only the manuscript introduction rewrite that removes an announced-list
  template while preserving L0=0 and all protected scientific invariants. The
  manuscript remains unchanged pending author disposition.
- **Independent-review fixes (16 verified findings).** An adversarially
  verified multi-agent review confirmed and this release fixes: undefined F1 on
  positive-free strata now reports `None` and is excluded from aggregation;
  AUC midrank tie handling is regression-tested; the confound-audit threshold
  threads through every stratum breakdown; the scoring side now refuses model
  bundles whose feature names/schema drift from the installed extractor and
  degrades cleanly on corrupt bundles; the model bundle is written atomically
  and carries fingerprint provenance surfaced in findings; an explicitly
  requested unavailable `--field` exits `2`; detector objects carry real
  version and calibration-asset provenance; `strong_advisory` is derived from
  the strength enum (single source of truth); rewrite eligibility is
  bidirectional (invented negation/causal/comparison markers, numbers, units,
  citations, or acronyms disqualify) and protects semantic LaTeX macros;
  rewrite ranking is led by specificity/fidelity with the learned score gated
  to tie-break weight unless its bundle is measured; an uncalibrated voice
  bundle emits rank-based triage (lowest-scoring paragraphs) instead of a
  forbidden universal 0.5 cutoff; grouped-split validation recomputes
  `corpus_cos` against training-only centroids so held-out papers cannot
  inflate their own similarity feature; and the trainer adds an
  author-labelled hard-set stratum plus preemption-safe featurization
  checkpoints for cloud runs. `docs/EVALUATION.md` is now a pointer stub to
  the canonical root record.

- **Confound-aware learned-model audit run (cloud, RTX PRO 6000).** The learned model
  was retrained on an expanded corpus (16,394 positive / 2,265 negative; dated arXiv
  positives grown 3,197 → 13,642) and audited with the new pipeline. Repeated
  source-grouped AUC 0.932 and matched-stratum AUC 0.924 show the separation is not a
  pure topic/length/math artifact, but 32–41% false-positive rates on field-topic and
  field-jargon-dense AI text keep L3 `degraded` with no operating point. The full result
  is in `EVALUATION.md` §7 and the machine-readable `voice_model_evaluation.json`. The
  75-paragraph author hard set is now fully labelled. **[Correction — see Unreleased
  above:** this entry originally cited an author-hard-set AUC of 0.354 as decisive proof
  the model measures field register, not AI-ness; that metric was underpowered
  (n_pos=8, CI 0.141–0.588) and scored against a near-chance perceptual axis. Against
  true provenance the model separates AI-vs-human at AUC 0.937.**]**

Published after fresh validator/tests, the 16-finding independent review and fixes, the
confound-aware learned-model status above, EVALUATION.md update, and clean-checkout
verification.

## v0.13.0 — 2026-07-11

**Fundamental (non-keyword) de-AI subsystem** — a four-layer capability that
detects and removes the *structural* AI-ness (smoothed per-token surprisal,
homogeneous sentence length, paragraph signposting) that survives keyword
cleaning. Design + guardrails: [docs/DEAI_SUBSYSTEM.md](docs/architecture/DEAI_SUBSYSTEM.md).

- **Layer A — `tools/deai_metrics.py`** (model-free): flags sentence-length
  burstiness / connective-opener signposting outside the human-corpus baseline.
- **Layer B — `tools/deai_oracle.py`** (gpt2-large): per-token surprisal / UID
  oracle; flags below-baseline surprisal variance. Calibrated per section.
- **Layer C — `skills/rewrite-in-voice/` + `tools/rewrite_reward.py`**: new
  `/sci-paper:rewrite-in-voice` skill rebuilds flagged paragraphs from their
  claim-graph (claim → fill-in skeleton → author-voice regeneration) instead of
  word-swapping. Best-of-N over a multi-term reward (learned-voice P(human) ×
  number-specificity, gated by relative claim-fidelity) so genuine voice +
  preserved meaning win, never detector-evasion (the AuthorMist→Pangram DAMAGE
  lesson). Human-in-the-loop; optional self-distillation.
- **Layer D — `tools/deai_voice.py` + `tools/train_voice_model.py`**: a learned
  voice/reward model on the *fundamental* features (distributional + surprisal/
  UID + corpus-embedding), not word-ngram TF-IDF. Held-out AUC 0.953 on `wgl`;
  ships LogisticRegression over gradient-boosting for out-of-distribution
  robustness (a reward that scores arbitrary rewrites must stay monotonic — the
  tree model scored a hand-crafted LLM paragraph P(human)=0.99, LR gave 0.003).
- **Training data** scaled + diversified to ~8.2k paragraphs: curated corpus +
  clean pre-2022 arXiv abstracts (broad astro + weak-lensing + authoritative
  authors, via new `tools/fetch_arxiv_abstracts.py`) as human positives;
  Claude-generated 6-register + multi-model RAID abstracts as LLM negatives. A
  controlled source ablation caught and excluded a poisoning source: our own
  de-AI-reviewed drafts read partly human, so mislabeling them AI dropped
  held-out AUC 0.953→0.920 and crossed an OOD fixture to the wrong side.
- **`ai_ism_lint.py`** gains `--distribution` / `--oracle` / `--voice` advisory
  passes, kept out of the exit-code gate (guardrail 2: diagnostic, not gate).
- **Skill integration**: `paper` gains a fundamental-tier note; `paper-review`
  gains dimension **D4** (structural AI-ness → rewrite-in-voice); `mainline` B8
  gains the structural complement; `final-review` inherits D4 via `paper-review`.
- **`paper/SKILL.md` drift fix**: anti-AI-ism corpus provenance re-derived from
  the current 31-paper dossier (was N=16 / 203,251 tokens → N=31 / 230,006;
  em-dash 0.098→0.213 per 1k words, Tier-B frequency table refreshed).
- **`.gitignore`**: trained model artifacts + feature caches (`*.joblib` /
  `*.npz`) ignored per-field (regenerate via `train_*.py`); the
  copyright/privacy-sensitive corpus jsonl stays local, so voice models built on
  unpublished drafts never leak.

## v0.12.1 — 2026-05-25

Structural cleanup release; **no skill behavior changes**.

- **`CHANGELOG.md`** extracted: per-version history pulled out of the
  `plugin.json` / `marketplace.json` `description` fields (which had
  bloated to ~1.4 KB of inline changelog text); both manifests now carry
  a one-line description pointing here.
- **`README.md`** drift fixes: skills table now lists all 8 skills (was 5;
  `mainline` / `paper-attack-tree` / `final-review` were only mentioned in
  prose); new Tools (7) table replaces hand-counted "Tools (6)" (was missing
  `build_profile.py` + `extract_md_negatives.py` + the negatives data file);
  hard-coded `D:/Projects/sci-paper` paths replaced with
  `<path-to-this-repo>` placeholders.
- **`CLAUDE.md`** sanitization: dropped three personal Windows absolute
  paths (`D:/Projects/weak-gravitational-lensing/`, two
  `C:/Users/skyma/...`) in favour of portable descriptions; documented
  the new `CLAUDE.local.md` convention.
- **`CLAUDE.local.md`** added to `.gitignore` (per-machine paths / virtualenvs
  go there; Claude Code reads both, only `CLAUDE.md` is shared).
- **`memory/`** added to `.gitignore`: cc-memory plugin local sqlite +
  private conversation notes. Regenerable; never commit.
- **`style-profile/README.md`** added: documents the generated-artifact
  layout, why per-field subdirs appear empty in git, how to rebuild,
  and the privacy / copyright reason exemplar JSONL is gitignored.
- **`tools/README.md`** table extended from 4 to 7 rows so it matches
  what actually lives in `tools/`; new entry for `validate_plugin.py`.
- **NEW `tools/validate_plugin.py`**: repo-shape sanity checks
  (manifests parse + versions match, every `skills/<name>/SKILL.md` has
  YAML frontmatter with matching `name`, every `tools/*.py` parses).
  stdlib-only; runs in ~50 ms.
- **NEW `.github/workflows/ci.yml`**: invokes the validator on push to
  main and on every PR so the README drift / mismatched-version class
  of bug can't silently reappear.
- **`requirements.txt`**: drop "v0.3 pipeline" anchor so the comment
  doesn't need bumping each release.

## v0.12.0 — 2026-05

- **`paper`** adds top-level writing standard
  **"Structural Updates · Forward Narrative"**: every update / correction /
  iteration must rewrite the paper to its current final state; never
  accrete "tried A, found A wrong, switched to B" patch-style residue in
  the body. Ships with:
  - Forward-narrative (final-state only) requirement.
  - Patch-vs-structural comparison table.
  - A single allowed exception (true external-baseline contrast).
  - 4-question per-paragraph self-check.
- The existing `formula derivation > no shooting-arrow-then-drawing-target`
  rule is now framed as a narrow special case with a back-reference.
- Writing-time dual of `paper-review` §2.O (update-not-accumulate).

## v0.11.0

- **`final-review` nested-sub-agent bug fix.** `paper-review` §4.4 isolated
  MPR was unrunnable when launched inside an `isolation=worktree`
  sub-agent. Resolved by promoting MPR to the `final-review` main agent as
  a dedicated 5th isolated sub-agent (§3.6); `paper-review` gains
  `--no-isolated-mpr` so orchestrators can suppress the nested call.
- **`paper-review` dimension R** — Glossary consistency (canonical-term
  alignment against project `FACTS.md` / glossary; alias / conflict /
  missing detection). Borrowed from `mattpocock-skills:grill-with-docs`.
- **`brainstorm` §2.0 glossary grill prelude** — one-question-at-a-time
  term lock against `FACTS.md` before root-node generation.
- 6 skill descriptions rewritten with explicit "Use when …" triggers per
  `mattpocock-skills:write-a-skill` convention.

## v0.10.0

- **NEW `final-review`** — 5-skill orchestrator for pre-submission final
  pass. Runs `paper` / `paper-review` / `figure-review` / `mainline` /
  `paper-attack-tree` each in its own `isolation: worktree` sub-agent
  every round; merges all issues; applies fixes; loops until consecutive
  N rounds (default 2) show 0 issues across all 5 skills. ITER_BUDGET 10
  rounds by default with `BREAK_WITH_USER_DECISION` on cap hit. No silent
  skipping or premature completion.
- **`paper-review` dimensions P and Q.**
  - **P** — internal development / research / draft language sweep:
    4-class grep for placeholders / draft colloquialisms / experiment-log
    style / internal codenames, replaced with general academic language.
  - **Q** — reference completeness + citation precision: missing-key-
    reference detection via WebSearch + per-`\cite{}` WebFetch
    verification that the cited paper actually supports the citing
    sentence (CORRECT / WEAK / MISUSED / UNVERIFIABLE).
- Convergence criteria extended: `P=0` / `Q-MISUSED=0` /
  `Q-missing-key-ref=0` / `Q-UNVERIFIABLE=0`.

## v0.9.0

- **NEW `paper-attack-tree`** — `brainstorm`'s radial phylogenetic-tree
  methodology applied to paper critique. Each node is one critique
  attacked via 12 framing passes (first-principles / inversion /
  cross-disciplinary reviewer / adversarial red-team / constraint
  variation / scale extrapolation / substitution / office-hours /
  contrarian / failure-driven / high-risk-fatal / meta). Every leaf
  resolved to **CONFIRMED** (`file:line` + proposed fix) / **REFUTED**
  (`file:line` of paper's defense) / **MARGINAL** (author judgement).
  Hard ban on `NEEDS-MORE-INFO` defer. Complements `paper-review` by
  covering open-ended adversarial angles a static checklist misses.

## v0.8.0

- **NEW `mainline`** — structural narrative-spine reinforcer. Mandatory
  full-read (no grep-only / no memory / no guessing). Audits along
  7 positive dimensions (spine sharpening / language compression /
  narrative architecture / isolated readability / derivation completeness
  / logical soundness / chaining) and 8 negative dimensions (vague
  definitions / scattered spine / volume-over-precision / disconnected
  sections / unclear structure / missing academic narrative / context
  drift / low-information adjectives). Explicit brainstorm-divergence
  consolidation pass; forbids transitional-phrase suturing of logical
  jumps; mandatory isolated-context cold-read 7-question readability
  check by an `isolation: worktree` sub-agent. Zero-issue convergence
  hard loop.

## v0.7.0

- **`paper-review` dimensions N and O.**
  - **N** — deep stale / wrong / redundant / drift sweep across 6
    content types + residual-markup grep.
  - **O** — process-artifact removal with **update-not-accumulate** hard
    constraint.

## v0.6.0

- **`paper-review` v3 dimensions K, L, M + isolated MPR.**
  - **K** — host-level `modern-physics-review` (M1–M9) merged in-process.
  - **L** — systemic inconsistency / cross-section context discontinuity.
  - **M** — mathematical / physical adversarial 3-pass.
- On zero-issue convergence, mandatory isolated-context final MPR via
  `isolation: worktree` sub-agent.

## v0.5.0

- **`brainstorm` v0.5** — radial 12-framing idea / problem tree with
  phylogenetic-tree width × depth model and no-defer enforcement.

## v0.4.0

- **NEW `brainstorm`** — fully-automated radial research-direction
  explorer (12 framings; recursive on promising leaves until
  convergence).

## v0.3.0

- **`extract_style.py`**: PDF parsing via `pymupdf` blocks-mode +
  ALL-CAPS heuristic for thematic section detection on top of the
  keyword-based detector.
- **`train_ai_ism_classifier.py`**: paragraph-level AI-ism classifier
  (logistic regression on word 1–2 gram TF-IDF). CV F1 ≈ 0.88 on the
  `wgl` corpus with 20 handcrafted negatives.
- **`ai_ism_lint.py --ai-classifier`** opt-in flag.

## v0.2.0

- **Embedding-based exemplar retrieval** in `retrieve_exemplars.py` via
  sentence-transformers + per-corpus `.npy` cache (rebuilt automatically
  when JSONL is newer). Keyword-overlap fallback via `--allow-fallback`.
- **Tier-graded `ai_ism_lint.py`** with `--summary` per-section density.
- **Multi-field profiles** under `style-profile/<field>/` with
  auto-detection in the single-field case.

## v0.1.0

- Initial plugin scaffold. Skills `paper`, `paper-review`, `figure-review`
  ported verbatim from `weak-gravitational-lensing/.claude/skills/`
  (project-specific anchors marked `[WGL]`).
- `paper-style/SKILL.md` spec + initial `tools/` stubs
  (`extract_style.py`, `retrieve_exemplars.py`, `ai_ism_lint.py`).
- Field-aware corpus / profile layout:
  `style-corpus/<field>/tier-{1-top, 2-mentor, 3-reference}/` ↔
  `style-profile/<field>/`.
