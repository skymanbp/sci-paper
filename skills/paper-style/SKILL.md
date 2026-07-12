---
name: paper-style
description: Apply a corpus-distilled field and genre style profile when drafting or rewriting scientific prose. Loads a descriptive dossier and section-typed exemplars, then uses the unified SCIPAPER_STANDARD feedback contract. The corpus supplies evidence and positive anchors; it never defines blocker or paper-verdict policy. Invoke before drafting, rewriting, or a final style pass.
disable-model-invocation: false
argument-hint: "<section_type> [--field <name>] [target_file] — section_type ∈ {abstract, intro, method, results, discussion, conclusion}"
---

# paper-style — descriptive corpus evidence for scientific writing

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> `style_dossier.md`, baselines, lexicons, and exemplars are empirical evidence.
> They do not redefine `integrity_blocker`, `l0_target`, `advisory`, ranking,
> disposition, measurement-state, or stopping semantics.

## 0. Hard rules

1. **Imitate style, never content.** Exemplars may guide rhythm, register,
   information distribution, and transition practice. Do not copy wording, claims,
   citations, data, or distinctive argument structure.
2. **Re-read scientific sources.** Every number, date, coefficient, citation, and
   scientific claim inserted into the user's draft must be verified from its source
   in the same turn. A style profile cannot supply manuscript facts.
3. **Report profile freshness and coverage.** If the corpus is newer than its derived
   profile, stop and regenerate with `tools/extract_style.py`. Missing or weak
   calibration is `unmeasured` or `degraded`, not evidence of conformity.
4. **Apply the unified consequence model.** Tier A, em-dash, and Tier B occurrences
   above the standard's cap are L0 targets. Corpus distances and positive-style
   mismatches are advisories unless scientific integrity is affected.
5. **Resolve field explicitly.** One available field may be selected automatically;
   multiple fields require `--field`; zero fields means corpus guidance is unavailable,
   but the core writing standard can still be used with that limitation reported.
6. **No universal style verdict.** A document may differ from the corpus for a valid
   genre, authorial, or scientific reason. Measure the difference and recommend an
   action; do not infer authorship or reject the paper from style distance.

## 1. Preconditions

Verify in order:

- the target section type and file;
- `style-profile/<field>/style_dossier.md` exists and is not older than the newest
  relevant source under `style-corpus/<field>/`;
- `exemplar_paragraphs.jsonl` exists before attempting retrieval;
- the profile's declared field and provenance match the selected field;
- any required baseline or `deai_policy.json` exists before calling a result
  calibrated or strong;
- `docs/SCIPAPER_STANDARD.md` and `/sci-paper:paper` are loaded alongside the profile.

If an optional asset is absent, continue with available axes and report the missing
axis. Do not silently replace a missing field baseline with a fixed threshold.

## 2. Load evidence

1. Read `docs/SCIPAPER_STANDARD.md` for policy.
2. Read the `/sci-paper:paper` writing guidance, especially scientific accuracy,
   forward narrative, formula standards, citations, and canonical L0 examples.
3. Read `style-profile/<field>/style_dossier.md` in full.
4. Read `lexicon.json`, `sentence_stats.json`, `transition_inventory.json`, or other
   baseline files only when needed for the current finding.
5. Retrieve section-typed exemplars when the bank is available:

   ```bash
   python tools/retrieve_exemplars.py --field <field> \
     --section <abstract|intro|method|results|discussion|conclusion> \
     --topic "<verified one-sentence topic>" --k 5
   ```

Read every returned exemplar. Record provenance. Treat a complete paper as one
calibration observation for document-level shape; never treat its paragraphs as
independent papers.

## 3. Draft or rewrite

Use the source-verified scientific content as the immutable input. Apply corpus
evidence to:

- sentence-length variation and local information distribution;
- paragraph openings and transitions;
- field register and accepted terminology;
- section-appropriate density of definitions, citations, equations, and results;
- document-level variation in paragraph and section arcs;
- positive author/field voice anchors.

Do not mechanically force every sentence into a reference interval. Preserve a
scientifically motivated short definition, long derivation, list, or parallel frame
when it carries real structure. Record a residual advisory if it remains distant from
the baseline.

After any rewrite, protect numbers, units, citations, mathematics, acronyms,
comparison and causal direction, negation, named entities, scope, and stance. Use
`tools/rewrite_reward.py` for deterministic eligibility when generating alternatives,
then verify the remaining semantic invariants manually.

## 4. Mandatory measurement

Run the shared report after drafting or rewriting:

```bash
python tools/ai_ism_lint.py <target_file> --field <field> \
  --structure --distribution --document-structure --oracle --voice \
  --format json --output <scratch>/style-feedback.json
```

Interpretation:

- exit 0: no L0 targets; advisories may remain;
- exit 1: at least one L0 target;
- exit 2: input, configuration, or execution failure;
- `measured`, `degraded`, `unmeasured`, and `not_applicable` must remain distinct;
- details may be truncated with `--top`, but summary totals must not change.

Use the ranked report to act:

1. resolve all integrity blockers outside this style skill;
2. remove applicable L0 targets;
3. act on or explicitly disposition strong advisories;
4. report ordinary advisories and unavailable axes.

Do not reconstruct JSON by parsing printed messages. Do not treat zero L0 targets as
proof that the prose is natural, scientifically correct, or ready for submission.

## 5. Output

For each changed section, return:

- selected field and profile provenance;
- measurement-state table;
- source-verified scientific anchors;
- retrieved exemplar IDs, never copied text unless needed for immediate comparison;
- before/after prose;
- ranked findings affected by the edit;
- author dispositions for residual strong advisories;
- ordinary residual advisories and unmeasured axes.

A style pass is complete when the unified standard's stopping rule is met, not when a
binary style PASS line is reached.

## 6. Anti-patterns

- Copying or lightly paraphrasing an exemplar.
- Quoting a manuscript number or citation from the dossier or memory.
- Calling a compatibility threshold calibrated.
- Treating every corpus-zero word as an automatic L0 target.
- Treating every sentence-length outlier as an error.
- Requiring every advisory to disappear.
- Declaring a paper human-authored or AI-authored from a learned score.
- Using a stale profile or silently selecting among multiple fields.
- Loading corpus evidence without the unified standard, or policy without current
  empirical evidence when making a corpus-specific claim.

## 7. References

- `docs/SCIPAPER_STANDARD.md` — normative policy.
- `EVALUATION.md` — empirical results and limitations.
- `docs/DEAI_SUBSYSTEM.md` — subsystem design.
- `/sci-paper:paper` — writing guidance.
- `/sci-paper:rewrite-in-voice` — claim-first structural rewrite.
- `tools/extract_style.py` — corpus-to-profile pipeline.
- `tools/retrieve_exemplars.py` — section-typed retrieval.
- `tools/ai_ism_lint.py` — shared structured report.
