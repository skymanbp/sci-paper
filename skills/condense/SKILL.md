---
name: condense
description: 精简技能。对整篇文档剔除**所有**不必要的、以及上下文/全文其他地方已有重复的内容：跨节重复的 claim/数字、零信息增量段落、死定义/死图表、冗长表达。执行 SCIPAPER_STANDARD §5.3（改写、删减、精简，而不是堆叠）：默认方向永远是更短，删除 > 原地压缩 > 等长改写，增长最后且必须有记录理由。每个事实只保留一个 canonical 位置，副本删除或改为交叉引用。保真不变量（§6）全程保护。Use when 用户说 "精简" / "太长了" / "重复" / "废话太多" / "condense" / "trim" / "去冗余"，或 paper-review 维度 I 的冗余 finding 需要执行修复时。
disable-model-invocation: false
argument-hint: "<file_path> [--section <name>] [--max-iter N] [--report-only] [--field <name>]"
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
*executes* the removal. `--report-only` stops after §1: the ranked redundancy
map is returned with no deletion applied.

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
   convention, NOT duplication. Everything else that has a home elsewhere
   goes.
5. **Forward narrative.** Removal never leaves a scar ("as discussed above,
   we omit..."); the text reads as if written short from the start.
6. **Deletions are evidence-backed.** A "dead" symbol, figure, table, or
   definition is deleted only after a whole-document grep proves nothing
   consumes it; the grep evidence goes in the report.

## 1. Measure — build the redundancy map

1. Read the target file completely. Resolve `--field` as in
   `/sci-paper:de-ai` §1 (shared style-profile convention).
2. **Snapshot the length baseline** before any edit:
   `cp <file> <scratch>/length-baseline.tex` (or record the clean git ref).
   Without an honest baseline the closing gate is meaningless.
3. Build the redundancy map, four sweeps:
   - **(a) Cross-section duplicates.** Grep every number/macro and scan each
     section pair for the same claim, definition, or figure description
     stated twice. Record: content, all locations, proposed canonical home.
   - **(b) Zero-information-gain text.** Paragraphs or sentences that add no
     claim, definition, evidence, qualification, or necessary link —
     assurance refrains, restated setup, roadmap prose the structure already
     carries.
   - **(c) Dead artifacts.** Defined-but-unused symbols, `\label`s never
     `\ref`'d, figures/tables never cited, definitions never consumed — each
     with the grep output that proves deadness.
   - **(d) Verbose constructions.** Multi-sentence spans whose content
     survives in fewer words (nominalization chains, redundant qualifiers,
     repeated glosses of the same symbol).
4. Rank the map by removable mass (largest duplication first).

## 2. Act — ranked removal

For each map entry, in rank order:

1. **Duplicates (a):** choose the canonical location; delete the copies, or
   where the distant reader genuinely needs the pointer, replace with a
   cross-reference (`Section~\ref{...}`); re-read both sites in context.
2. **Zero-gain text (b):** delete. If a fragment carries one load-bearing
   clause, fold that clause into the neighboring sentence — do not keep the
   paragraph for one clause.
3. **Dead artifacts (c):** delete the artifact and every orphaned mention;
   re-run the deadness grep afterward to confirm nothing dangles.
4. **Verbose spans (d):** rewrite shorter. Gate every shortened rewrite with
   `python tools/rewrite_reward.py --reference <claim-record> --original
   <span> --candidates ...` — a candidate that drops a protected invariant is
   ineligible regardless of its brevity; among eligible candidates the
   shorter wins.

Apply each change with a minimal Edit and re-read the affected region plus
every cross-reference into it.

## 3. Verify — prove the shrink

1. **Length gate:** `python tools/length_gate.py <file> --before
   <scratch>/length-baseline.tex`. Required outcome: exit 0 with a
   zero-or-negative net delta for a pure condensation pass. Any
   `length-growth:<section>` finding must be dispositioned (condense back, or
   record the §5.3 justification) before the pass may close.
2. **No orphans:** rebuild/compile the document if it is LaTeX (0 errors,
   0 undefined references, no newly-missing labels); grep every deleted label
   and symbol to confirm zero remaining consumers.
3. **Fidelity:** re-check the §6 invariants over every edited span against
   the snapshot; every number, citation, and claim in the final text traces
   to the same source as before.

## 4. Loop until dry

Repeat §1-§3 over the whole document until **two consecutive full sweeps
find nothing removable**. A single clean sweep is not convergence; simple
counters miss the tail that the first removal round exposes.

## 5. Report

```markdown
# condense — Report
Target: <file> | Baseline: <snapshot/ref> | Sweeps: K (last 2 dry)
Net length delta: <words, per section and total — zero or negative>

## Removed duplicates
- <content> : canonical home <loc>; copies removed <locs>

## Deleted (zero-gain / dead artifacts)
- <item> : deadness evidence <grep summary>

## Compressed spans
- <loc>: <before-words> -> <after-words>; eligibility PASS

## Dispositions
- <any length-growth findings and their recorded justifications>
No number, citation, claim, or sole-support fact was deleted.
```

## 6. Anti-patterns

- Appending an explanation instead of deleting the redundancy (the §5.3
  explanatory patch — the exact disease this skill exists to cure).
- Deleting a fact's only occurrence because it "felt repeated" — dedup
  requires proving the survivor exists.
- Gutting the abstract or conclusion under the dedup rule (genre carve-out).
- Trimming hedges, uncertainties, or qualifiers to save words — those are
  protected invariants, not padding.
- Declaring convergence after one clean sweep.
- Leaving removal scars or drafting-history narration in the text.
- Doing de-ai's job: structural-tell rewriting (voice, templates, L0 words)
  belongs to `/sci-paper:de-ai`; condense only deletes and compresses.

## 7. Interfaces

- `docs/SCIPAPER_STANDARD.md` — §5.3 (the policy this skill executes), §6
  (fidelity invariants), §0 (consequence classes and dispositions).
- `tools/length_gate.py` — the mechanical closing gate (exit 0/1/2).
- `tools/rewrite_reward.py` — eligibility + condensation ranking for
  shortened rewrites.
- `/sci-paper:paper-review` — dimension I findings are this skill's input
  queue.
- `/sci-paper:de-ai` — the authorship-fingerprint surface (boundary in §0).
