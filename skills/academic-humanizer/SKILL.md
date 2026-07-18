---
name: academic-humanizer
description: Standalone audit-then-rewrite pass for AI-assisted academic prose, ported whole from AIScientists-Dev/academic-humanizer (MIT). Detects the structural tells the mechanical linter cannot measure (clause-stacked sentences, negative parallelisms, elegant variation, rule-of-three padding, inflated significance) and enforces claim-evidence verb matching. Audit findings feed paper-review section D; rewrites must pass the sci-paper fidelity and length gates. Not for evading AI-use disclosure.
disable-model-invocation: false
argument-hint: "<file_path> [--field <name>] [--audit-only]"
---

> **Provenance:** ported from
> [AIScientists-Dev/academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer)
> v0.3.3 (MIT license; attribution retained in README Acknowledgments).
> Layer-2 patterns 2.12--2.16 and the Pass-2 self-interrogation step are
> adapted from [blader/humanizer](https://github.com/blader/humanizer)
> (MIT); only its academically-relevant structural tells were absorbed,
> its blog/chat-specific patterns (emoji, title-case headings, chatbot
> artifacts, curly-quote flags) and its `landscape`-flagging word list
> were deliberately not adopted (they conflict with the corpus evidence
> below).
> **Normative authority:** `docs/SCIPAPER_STANDARD.md`. Where this file and the
> standard disagree, the standard wins. The upstream word lists are **not**
> normative here — corpus evidence is (see "Corpus overrides" below).
> **Layer 6 (funding proposals)** of the upstream skill is NOT duplicated
> here; it lives as the sibling skill `/sci-paper:proposal-polish`. Route
> proposal texts there.

# academic-humanizer — structural-tell audit + evidence-bound rewrite

Improve the clarity and voice of AI-assisted academic prose while keeping the
precise, evidence-bound register scholarship requires. Preserve every number,
result, and citation. Never inject opinion, humor, or first-person
"personality": for technical writing, neutral and precise *is* the human voice.

## When to use

- Invoked standalone on a manuscript file (`/sci-paper:academic-humanizer <file>`).
- Invoked by `/sci-paper:paper-review` as the structural-tell audit step of its
  section D (audit-only mode: findings are returned as review issues, fixes
  applied by the review loop under its own gates).
- NOT for blogs, marketing, or personal essays; NOT for proposals (use
  `/sci-paper:proposal-polish`).

## Process (upstream steps, gate-wired)

1. **Read** the manuscript in full, plus the field's style dossier
   (`style-profile/<field>/style_dossier.md`) if present. Skip LaTeX comments
   and any scaffolding macros (e.g. `\SLOT{...}` skeleton bodies).
2. **Audit** (never edit in this step): list every detected pattern with
   file:line, pattern class, exact quote, and a proposed fix that preserves
   all numbers, citations, and claim direction.
3. **Rewrite** (skip under `--audit-only`): same content and coverage, tells
   removed, over-claims matched to evidence, legitimate hedging kept. Every
   rewritten span MUST satisfy the sci-paper gates:
   - fidelity eligibility (`tools/rewrite_reward.py` invariants: numbers,
     citations, comparison directions, negations, semantic macros);
   - the §5.3 length budget (`tools/length_gate.py` against the pre-edit
     snapshot): rewrite, condense, never stack.
3.5. **Pass-2 self-interrogation** (adapted from blader/humanizer's two-pass
   audit; skip under `--audit-only`). After the first rewrite of a span,
   ask of it: "what still reads as machine-written here?" Answer in 2--4
   concrete bullets (a specific phrase, a rhythm, a residual tell), then
   apply one further targeted rewrite that clears them and re-checks the
   fidelity and length gates. Do NOT manufacture voice or personality to
   pass this pass: for technical prose neutral-and-precise IS the target;
   the audit strips tells, it does not add flavor.
4. **Report**: change log by pattern class, claims softened or given evidence
   pointers, and confirmation that no number, equation, or citation changed.

## Layer 1: General AI-tell catalog

Inflated significance ("marking a pivotal moment"); superficial "-ing" tails
that fake depth ("..., highlighting..."); promotional or figurative language
("rich", "vibrant", "groundbreaking"); vague attributions ("experts argue"
with no cite); copula avoidance ("serves as" -> "is"); negative parallelisms
("not just X, but Y"); rule-of-three padding; elegant variation (cycling
synonyms for one referent — one concept keeps one name for the whole paper);
filler ("it is worth noting that", "in order to"); overlong clause-stacked
sentences (see 2.11); em-dashes (L0: remove entirely; recast with commas,
colons per the colon rule, parentheses, or separate sentences).

Lexical tells (delve, underscore, tapestry, testament, pivotal, showcase,
foster, realm, seamless, intricate, leverage-as-filler) are already enforced
mechanically by `tools/ai_ism_lint.py` Tier A/B — do not re-derive them here;
run the linter.

## Layer 2: Academic AI tells

- **2.1 Over-claiming verbs.** Empirical work *shows* and *provides evidence*;
  it does not *prove* universal truths. Verbs to check against evidence:
  prove, establish, confirm, guarantee, demonstrate. See "Corpus overrides".
- **2.2 Significance hype.** paves the way for, a crucial/pivotal step toward,
  potential to revolutionize, opens new avenues, sheds light on, of paramount
  importance, bridges the gap -> replace with the specific failure mode or
  result addressed.
- **2.3 Empty intensifiers.** extensive/comprehensive/thorough experiments,
  a wide range of, numerous, various -> enumerate or quantify.
- **2.4 Novelty padding.** "novel" more than once per section; "to the best of
  our knowledge"; "for the first time" -> state the specific gap instead.
- **2.5 Formulaic openers.** "In recent years, X has attracted increasing
  attention"; "With the rapid development of..."; "Despite recent
  advances,..." -> open with the structural fact or the problem.
- **2.6 Connective overuse.** No consecutive sentences opening with
  Moreover/Furthermore/Additionally/In particular; let logic carry.
- **2.7 Contribution-list cliches.** Each contribution names a specific
  result with its number, not a restatement of the abstract.
- **2.8 Citation dumping.** Evidence-conditional, never a length rule: flag a
  bracketed citation list only when individual entries do not support the
  sentence they are attached to or duplicate another entry's role. Never
  delete a relevant source merely to shorten the list (Layer 3 preserves
  every citation; distinct provenance legitimately needs several).
- **2.9 Hedging-by-vagueness.** somewhat, relatively, fairly, to some extent,
  quite -> quantify or cut. (Distinct from calibrated hedging — see Layer 3.)
- **2.10 Boilerplate emphasis.** "It is worth noting that", "It should be
  emphasized that", sentence-initial "Notably,"/"Importantly," -> if it
  matters, the sentence shows it.
- **2.11 Overlong, clause-stacked sentences.** Watch sentences past ~30 words
  or with 3+ subordinate clauses chained by "which/that/while/with", and
  double-nested parentheticals. Split: one idea per sentence; cut subordinate
  clauses that carry no weight. This is the highest-yield structural check —
  the mechanical linter does not measure it.

The next five (2.12--2.16, adapted from blader/humanizer) are structural,
not lexical — flag the construction, never the bare word, and honor the
corpus caveat in each.

- **2.12 False ranges.** "from X to Y" where the endpoints are categorical
  rather than a measured span ("from theory to observation", "from the
  smallest scales to the deepest questions"). *Corpus caveat:* a genuine
  quantitative range is correct and required (redshift 0.1 to 0.5, mass
  $10^{13}$ to $10^{15}\,M_\odot$); flag only the rhetorical range whose
  endpoints share no scale.
- **2.13 Aphorism formulas.** "X is the Y of Z" / "X becomes a Y" epigrams
  inserted for resonance ("the error budget is the heartbeat of the
  pipeline") -> state the literal fact. *Corpus caveat:* a formal
  definition of the same shape ("the aperture mass is the convolution of
  the tangential shear with the filter") is a definition, not an aphorism;
  keep it.
- **2.14 Persuasive authority tropes.** "at its core", "fundamentally",
  "the real question is", "it is important to realize" asserting an
  importance the sentence has not earned -> cut, or replace with the
  specific reason. *Corpus caveat:* "fundamentally different" naming a real
  physical distinction (a different regime, symmetry, or scaling) is
  substantive; keep it.
- **2.15 Manufactured staccato drama.** A run of terse fragments strung for
  rhetorical impact ("The signal is weak. The noise is not. Detection
  fails.") -> recast as measured sentences; academic emphasis comes from
  content. Distinct from 2.11: this is too-short-for-drama, 2.11 is
  too-long. A single emphatic short sentence is fine (Layer 3); only a
  *run* is a tell.
- **2.16 Hyphenated-pair predicate overuse.** Compound modifiers piled in
  the predicate ("the result is model-dependent", "the map is
  noise-dominated") build an AI texture -> in the predicate prefer the
  plain relation ("the result depends on the model") where it reads
  naturally. Fine as an attributive modifier ("a model-dependent result");
  flag only density, not any single use.

## Layer 3: Preserve these (do NOT over-correct)

- **Evidence-tied hedging is correct and required.** Keep "suggests",
  "is consistent with", "we hypothesize", "may indicate", "appears to" when
  the claim is genuinely uncertain. Strengthening a calibrated verb is a
  claim-evidence defect, not an improvement.
- **Passive voice** is fine when the actor is irrelevant.
- **First-person plural "we"** is standard; do not rewrite it away.
- **Semicolons and an occasional triple** are fine in moderation.
- **Formal definitions, named methods, technical terms, equations, symbols**
  stay verbatim.
- **Never invent, drop, or alter a number, equation, or citation.**
- **False-positive guards** (blader/humanizer, corpus-aligned): do NOT flag
  formal vocabulary on its own ("ostensibly", "constituent"); a single mixed
  casual/formal register; straight-vs-curly quotes in isolation; a lone
  emphatic short sentence (only a *run* is 2.15); text inside quotations,
  a figure caption's verbatim labels, or a worked example; or a claim that
  is field-common knowledge (that goes to Layer 4 only if it is a
  load-bearing empirical claim). Specific hard-to-fabricate detail, a
  genuine mid-sentence self-correction, and calibrated hedging are human
  signals, not tells.

## Layer 4: Claim-evidence discipline

For every empirical claim: (a) is it backed by a number, figure, table, or
citation in the text, and (b) does the verb match the strength of that
evidence?

- Unbacked claim -> add the evidence pointer or soften.
- Verb stronger than evidence -> downgrade to what the data show.
- Vague magnitude -> a number or attributed range; prefer ranges over single
  averaged values unless the averaging is stated; lead comparisons with the
  strongest baseline, not the trivial one.

In paper-review integration, Layer-4 failures are 🔴 (integrity class);
Layers 1-2 structural hits are 🟡 (style class).

## Layer 5: Voice and venue matching

If the author supplies prior papers, read a sample first and note sentence
rhythm, connective habits, hedging placement, section openers, notation, and
recurring phrasings, then match them. Match the venue register. Absent a
sample, default to clean, precise, venue-appropriate prose. In this plugin the
corpus dossier (`style-profile/<field>/style_dossier.md`) is the measured
voice baseline — use it before improvising.

## Corpus overrides (this plugin's evidence beats the upstream word list)

- **`landscape`** is a legitimate domain term in astrophysics corpora
  (192 hits / 7.49M words measured 2026-07-16) — never flag it lexically.
- **`demonstrate*`** (0.147/1k) and **`significantly`** (0.274/1k) are normal
  astro usage — flag them only when Layer 4 fails (no test or number backs
  the claim), never as bare words.
- Tier A/B word lists live in `style-profile/<field>/lexicon.json` and
  `tools/ai_ism_lint.py`; this skill defers to them.

## Output

The cleaned text (or, in audit-only mode, the finding list) plus a short
change report: patterns removed by class, claims softened or given evidence
pointers, voice notes, and the gate evidence (fidelity eligibility + length
budget) for every rewritten span.
