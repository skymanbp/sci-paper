---
name: condense
description: Whole-document condensation. Removes every passage that is unnecessary or already stated elsewhere: claims and numbers repeated across sections, zero-information paragraphs, dead definitions and uncited figures, verbose constructions. Executes SCIPAPER_STANDARD §5.3 (condense, do not accumulate): the default direction of every edit is shorter — delete > compress in place > same-length rewrite, with growth last and only under a recorded justification. Each fact keeps exactly one canonical home; the copies are deleted or replaced by a cross-reference. The removal map is machine-built (condense_map.py), every entry is dispositioned, and the length gate proves the shrink against the map's target. Fidelity invariants (§6) are protected throughout. Use when: "condense" / "trim" / "too long" / "repetitive" / "cut the padding" / 精简 / 太长了 / 重复 / 废话太多 / 去冗余, or when a paper-review dimension-I redundancy finding needs to be executed.
disable-model-invocation: false
argument-hint: "<file_path> [--section <name>] [--max-iter N] [--report-only] [--field <name>] [--target <words|N%>]"
---

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`. §5.3 (condense, do not
> accumulate) is the policy this skill executes; the policy text lives ONLY in
> the standard — this skill implements it and never restates a competing
> version. §6 rewrite eligibility defines the fidelity invariants every
> deletion and compression must preserve.

# condense — 精简：one canonical home per fact

## 0. What this skill does

A whole-document sweep that removes **all** content which is unnecessary or
already stated elsewhere in the document, then proves the result with the
mechanical length gate. It is the plugin's redundancy/length action surface:
`paper-review` dimension I *detects* redundancy as findings; condense
*executes* the removal. `--report-only` stops after §1: the removal map is
returned with no deletion applied.

The map is not built by reading. `tools/condense_map.py` enumerates every
removable entry with the words it would free, and the pass is judged against
that count: a pass that dispositions every entry and meets the map's target
has condensed; a pass that reads the paper and trims a phrase here and there
has not. That failure mode — a sweep that removes a few percent by hand while
the map lists ten — is the reason the tool exists.

**Boundary with `/sci-paper:de-ai` (canonical home: de-ai SKILL.md §0;
mirrored here verbatim):**
de-ai removes the *authorship fingerprint* (L0-L4 signals, structural tells,
voice; its Pass-3 length cap only guards its own rewrites against growth).
condense removes *redundancy and length* (cross-document deduplication under
one-canonical-home-per-fact). At the overlap (verbose AI-isms such as
rule-of-three padding or connective stacking), de-ai DETECTS the tell; when
the right fix is deletion rather than rewrite, the deletion EXECUTES under
condense's ranked sweep.

## 0.1 Non-negotiable rules

1. **Preference order: delete > condense-in-place > same-length rewrite.**
   Growth is forbidden; the only exceptions are §5.3's own (author-requested
   new content, or a source-verified scientific necessity), each with a
   recorded justification.
2. **Fidelity invariants (§6).** Every surviving passage preserves claims,
   numbers, units, uncertainties, citations, named entities, comparison
   direction, negation, causal direction, scope, stance, qualifiers, and
   logical dependencies. **Never delete a fact's sole support**: dedup keeps
   exactly one canonical home; the copies are deleted or replaced by a
   cross-reference — the fact itself never vanishes.
3. **One canonical home per fact.** A number, definition, or claim stated in
   two places is a defect with one exception (rule 4). The canonical home is
   where the reader needs it — normally the most detailed, first-consumed
   occurrence.
4. **Genre carve-out.** The abstract's summary of key results and the
   conclusion's restatement of the take-home message are scholarly
   convention, NOT duplication. The map reports these entries with
   `genre_carve_out: true` and leaves them out of the default target.
5. **Forward narrative.** Removal never leaves a scar ("as discussed above,
   we omit..."); the text reads as if written short from the start.
6. **Every map entry is dispositioned.** Deleted, merged, or kept — and
   `kept` carries a reason a reader could check (the survivor is the sole
   support; the repeat is the carve-out; the "dead" label is consumed by an
   include the map cannot see). An entry without a disposition is an entry
   the pass skipped.
7. **Deletions are evidence-backed.** A "dead" symbol, figure, table, or
   definition is deleted only after a whole-document grep proves nothing
   consumes it; the map's `condense-dead:*` entries carry that grep, and any
   deletion outside the map records its own.

## 1. Measure — build the removal map

1. Read the target file completely. Resolve `--field` as in
   `/sci-paper:de-ai` §1 (shared style-profile convention).
2. **Snapshot the length baseline** before any edit:
   `cp <file> <scratch>/length-baseline.tex` (or record the clean git ref).
   Without an honest baseline the closing gate is meaningless.
3. Build the map:
   `python tools/condense_map.py <file> --format json --output <scratch>/condense-map.json`.
   Six scans, each entry with `removable_words`:
   - `condense-restatement` — a sentence whose content words are ≥ 80 %
     covered by an earlier sentence in another section (or ≥ 60 % by one
     sentence): canonical home named, copy listed.
   - `condense-zero-gain` — roadmap sentences ("In this section we..."),
     assurance refrains, `Note that` / `It is worth noting` openers.
   - `condense-dead:{figure,table,label,macro,acronym}` — defined or placed,
     never consumed; the grep is the finding.
   - `condense-verbose` — `in order to`, `due to the fact that`, hedge stacks
     (`may possibly`), each with the words its replacement saves.
   - `condense-regloss` — the same symbol glossed twice.
   - `condense-duplicate` — a paragraph repeated across sections (Jaccard
     ≥ 0.60 over ≥ 30 content words).
   `condense_budget` totals them: `removable_total`, `removable_by_rule`, and
   `default_target_words` = restatement + zero-gain outside the carve-out.
   The map is exhaustive for what it scans and blind to what it does not
   (a claim restated in three sentences, a paragraph that only repeats a
   figure caption); add those by reading, with the same fields.
4. Rank the map by removable mass (largest first). The default shrink
   target is `default_target_words`; `--target` overrides it and is recorded.

## 2. Act — ranked removal, one disposition per entry

For each map entry, in rank order, record `deleted` / `merged` / `kept:<reason>`:

1. **Restatements and duplicates:** choose the canonical location; delete the
   copies, or where the distant reader genuinely needs the pointer, replace
   with a cross-reference (`Section~\ref{...}`); re-read both sites in context.
2. **Zero-gain text:** delete. If a fragment carries one load-bearing clause,
   fold that clause into the neighbouring sentence — do not keep the paragraph
   for one clause.
3. **Dead artifacts:** delete the artifact and every orphaned mention; re-run
   the map afterward to confirm nothing dangles.
4. **Verbose spans and repeated glosses:** rewrite shorter. Gate every
   shortened rewrite with `python tools/rewrite_reward.py --field <field>
   --reference <claim-record> --original <span> --candidates ...` — a
   candidate that drops a protected invariant is ineligible regardless of its
   brevity; among eligible candidates the shorter wins. `--field` is required
   by the tool (it exits 2 without one); resolve it as in §1 step 1.

Apply each change with a minimal Edit and re-read the affected region plus
every cross-reference into it.

## 3. Verify — prove the shrink

1. **Length gate against the target:**
   `python tools/length_gate.py <file> --before <scratch>/length-baseline.tex
   --require-shrink <default_target_words>` (a percentage such as `8%` or a
   fraction is also accepted). Exit 0 requires both no unjustified growth and
   a net cut of at least the target; a cut short of it is a strong
   `length-shrink-short` finding with exit 1, and the pass may not close on
   it — either remove more, or record which kept entries account for the gap.
2. **Residue:** `python tools/deai_residue.py <file> --before
   <scratch>/length-baseline.tex`. A condensation must not leave a heading or
   caption promising what the body no longer says; exit 1 blocks closing.
3. **No orphans:** rebuild/compile the document if it is LaTeX (0 errors,
   0 undefined references, no newly-missing labels); re-run the map and grep
   every deleted label and symbol to confirm zero remaining consumers.
4. **Fidelity:** re-check the §6 invariants over every edited span against
   the snapshot; every number, citation, and claim in the final text traces
   to the same source as before.

## 4. Loop until dry

Repeat §1-§3 over the whole document until **two consecutive maps list no
entry outside the carve-out with a disposition other than `kept`**. A single
clean sweep is not convergence; the first removal round exposes restatements
the map could not see while the copies stood.

## 5. Report

```markdown
# condense — Report
Target: <file> | Baseline: <snapshot/ref> | Sweeps: K (last 2 dry)
Map: <n entries>, removable <words> (<by rule>); target <words> (<default|--target>)
Net length delta: <words, per section and total>; length_gate --require-shrink: exit <0|1>

## Dispositions (every map entry)
- <rule> L<line>: <excerpt> — deleted | merged into <loc> | kept: <reason>

## Removed outside the map
- <content> : canonical home <loc>; copies removed <locs>; evidence <grep>

## Compressed spans
- <loc>: <before-words> -> <after-words>; eligibility PASS

## Gate findings
- <length-growth / length-shrink-short / residue findings and their recorded justifications>
No number, citation, claim, or sole-support fact was deleted.
```

## 6. Anti-patterns

- Appending an explanation instead of deleting the redundancy (the §5.3
  explanatory patch — the exact disease this skill exists to cure).
- Removing less than half of the map's restatement mass without a per-entry
  `kept:` reason — the scraping pass that trims phrases and leaves the
  repeated claims standing.
- Deleting a fact's only occurrence because it "felt repeated" — dedup
  requires proving the survivor exists.
- Gutting the abstract or conclusion under the dedup rule (genre carve-out).
- Trimming hedges, uncertainties, or qualifiers to save words — those are
  protected invariants, not padding.
- Declaring convergence after one clean sweep, or closing on a
  `length-shrink-short` finding without naming the entries that account for
  the shortfall.
- Leaving removal scars or drafting-history narration in the text.
- Doing de-ai's job: structural-tell rewriting (voice, templates, L0 words)
  belongs to `/sci-paper:de-ai`; condense only deletes and compresses.

## 7. Interfaces

- `docs/SCIPAPER_STANDARD.md` — §5.3 (the policy this skill executes), §6
  (fidelity invariants), §0 (consequence classes and dispositions).
- `tools/condense_map.py` — the removal map and its budget (exit 0/2).
- `tools/length_gate.py` — the mechanical closing gate; `--require-shrink`
  turns the map's target into an exit code.
- `tools/deai_residue.py` — the residue gate over the before/after pair.
- `tools/rewrite_reward.py` — eligibility + condensation ranking for
  shortened rewrites.
- `/sci-paper:paper-review` — dimension I findings are this skill's input
  queue.
- `/sci-paper:de-ai` — the authorship-fingerprint surface (boundary in §0).
