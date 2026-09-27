# Acknowledgments

Material adapted into `sci-paper` from other MIT-licensed projects, with the
adoption boundary recorded in each case. Corpus evidence governs here, so
adoption was never wholesale: rules that conflict with measured field usage were
deliberately declined, and each declined rule is named below rather than left
implicit.

## AIScientists-Dev/academic-humanizer

<https://github.com/AIScientists-Dev/academic-humanizer> (MIT License,
Copyright (c) 2026 AIScientists-Dev)

**Adopted.** The 2026-07-16 lexicon extensions (`underscore*`, `pivotal`,
`tapestry`, `testament`, `realm*`, `intricate`, `foster*`); the `serves as`,
`ing-tail`, and `colon-elaboration` linter rules; the Claim–Evidence Discipline
(its Layer 4, recalibrated on the astronomy corpus) and Preserve List (its
Layer 3) sections of [`skills/paper/SKILL.md`](skills/paper/SKILL.md);
the [`proposal-polish`](skills/proposal-polish/SKILL.md) skill; and the
[`de-ai`](skills/de-ai/SKILL.md) skill's Layer 1–5 audit catalog adapt its
material. The first five words entered Tier A only after both curated field
corpora showed zero occurrences of them; `intricate` and `foster*` occur once
each there, so they entered Tier B.

**Declined.** Venue-specific rules that conflict with astronomy usage —
`landscape`, a legitimate field term (`detection landscape`) frequent in the
corpus, and the blanket `demonstrate` / `significantly` bans: in the combined
curated astronomy corpus `demonstrate*` runs at 0.147/1k and `significantly` at
0.274/1k (measured 2026-07-16). Every lexical adoption was re-verified against
the curated field corpora before tier assignment.

academic-humanizer itself builds on blader/humanizer (MIT).

## blader/humanizer

<https://github.com/blader/humanizer> (MIT)

**Adopted.** The [`de-ai`](skills/de-ai/SKILL.md) skill's structural patterns
2.12–2.16 (false ranges, aphorism formulas, persuasive-authority tropes,
manufactured staccato drama, hyphenated-pair predicates), its Pass-2
self-interrogation step, and its false-positive guards.

**Declined.** Its blog- and chat-specific patterns (emoji, title-case headings,
chatbot artifacts, curly-quote flags) and its `landscape`-flagging word list.
Only the academically relevant structural tells were absorbed.

## Project-owner rules

Two rules in [`skills/paper/SKILL.md`](skills/paper/SKILL.md) were set by the
project owner on 2026-07-16: condense, do not accumulate (改写、删减、精简，而不是堆叠;
now standard §5.3), and the `colon-elaboration` rule.

---

Licensing: [MIT](LICENSE) covers code, skills, documentation, and tooling
authored in this repository. User-supplied corpus contents and generated
excerpts retain their source rights and are **not** covered by this repository
license.
