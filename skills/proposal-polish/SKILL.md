---
name: proposal-polish
description: Funding-proposal editing mode (NSF Project Summary/Description, NIH Specific Aims, fellowship proposals). Keeps the vision-and-feasibility register a paper would trim, enforces claim-feasibility matching, edits the score-forming first pages hardest, and applies the shared L0 lexical policy. Never invents preliminary data, partners, funding history, or letters, and is not for evading AI-use disclosure.
disable-model-invocation: false
argument-hint: "<file_path> [--agency nsf|nih] [--voice-sample <prior_proposal>]"
---

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`. The L0 lexical policy
> (Tier A, Tier B caps, em-dash zero) and the rewrite-eligibility invariants
> (§6: numbers, citations, stance, qualifiers) apply to proposals exactly as to
> papers. What changes is the **register**: a proposal is sold on vision plus
> feasibility, so ambition language that `/sci-paper:paper` would trim is
> appropriate here when a credible plan backs it.
>
> **Provenance:** adapted from academic-humanizer Layer 6 and its examples
> (github.com/AIScientists-Dev/academic-humanizer, MIT License, Copyright (c)
> 2026 AIScientists-Dev; that skill's paper-mode content now lives in
> `/sci-paper:de-ai`). Restructured to the sci-paper feedback contract.

# proposal-polish — funding-proposal editing mode

## When to use

Editing or reviewing funding proposals: NSF Project Summary / Project
Description (including CAREER), NIH Specific Aims / Significance / Innovation /
Approach, fellowship and foundation proposals. **Not** for journal manuscripts
(use `/sci-paper:paper` + `/sci-paper:paper-review`), and **never** to
fabricate results, partners, funding history, or support letters. Using this
skill does not remove the obligation to follow the funder's AI-use disclosure
policy.

## Core register shift (vs. paper mode)

A paper reports finished results; a proposal is scored on **vision plus
feasibility**. Consequences:

- **Keep and deploy ambition** ("long-term goal", "transformative",
  "establish a foundation") *when* preliminary data, prior results, a classical
  foundation, or a collaborator credibly backs it. Do not flatten vision the
  way paper mode trims significance hype.
- **The discipline is claim ↔ feasibility, not claim ↔ finished evidence.**
  For every aim and promised outcome: is the ambition matched by a credible
  means (preliminary data, a prior method or publication, a classical result
  built upon, a collaborator or letter, staged de-risking)? If yes, keep the
  ambitious verb. If no, attach the missing evidence or scale the claim to
  what the plan supports. If the support does not exist, flag the gap for the
  author; never paper over it and never invent it.
- **L0 still applies.** Tier A words, em-dashes, and Tier B excess are tells in
  proposals too; an AI-flavored proposal reads generic exactly where reviewers
  decide the score.

## Structure: the score lives in the first pages

Reviewers form a score from the opening and skim the rest to confirm it. Spend
most editing effort there.

- **NSF.** A one-page **Project Summary** with the review criteria spelled out
  (**Overview**, **Intellectual Merit**, **Broader Impacts**, each
  self-contained). The Project Description opens with long-term vision, this
  proposal's goal, the gap, the specific thrusts or aims, and the payoff,
  ideally within the first one to two pages, with one overview figure. Broader
  Impacts must be substantive and integrated, never an afterthought.
- **NIH (R01-class).** The **Specific Aims page is the whole proposal in one
  page** and is the most-read, most-decisive page. Standard arc: (1) the
  problem, what is known, the gap and critical need; (2) the long-term goal and
  the central hypothesis with its rationale; (3) "The objective of this
  application is ..." plus how the hypothesis was formed; (4) two to three
  Aims, each a one-line goal, a phrase on approach, and the expected outcome;
  (5) a payoff paragraph stating what changes if it succeeds. Significance,
  Innovation, and Approach are then separately scored sections.
- **First-pages completeness check.** By the end of page 1 (NIH Aims) or pages
  2-3 (NSF), the reader must already hold the **hook** (why it matters,
  concretely), the **gap** (what is missing and its cost), the **central idea**
  (the approach in one sentence), the **aims** (crisp and parallel), and the
  **payoff**. If any is missing or buried, fix that before touching later
  sections. A reviewer unconvinced by page 3 does not recover on page 10.

## Proposal-specific weak moves (fix these)

- **Vague importance.** "This is an important/timely problem", "X has many
  applications". Replace with the specific gap and the cost of the gap.
  Example fix: *"Without bounds on how measurement noise propagates to
  diagnosis, clinical models are tuned by trial and error, the inefficiency
  this proposal removes."*
- **Method-as-aim.** An aim naming a technique instead of a question or
  outcome. *"Aim 2: Apply transfer learning to the dataset"* becomes *"Aim 2:
  Determine whether fusing wearable and lab signals improves early detection,
  and for which patient subgroups it helps or hurts."*
- **Dominoed aims.** Aim 2/3 collapse if Aim 1 fails; reviewers flag this as
  fragile. Phrase aims as parallel and independently valuable; where one
  genuinely depends on another, state the fallback.
- **Ambition without feasibility.** Every bold claim gets a footing beside it:
  a preliminary figure, a prior publication, a classical theorem built upon, a
  named collaborator or letter. Use only the PI's own real, supplied record.
- **Boilerplate Broader Impacts / training plan.** "We will mentor students
  and disseminate via talks" is filler. Make it concrete, enumerated, and tied
  to the research: named programs, named courses or tools, measurable outreach.
- **Hedged central hypothesis.** The Aims-page hypothesis is a falsifiable
  commitment, not "we will explore whether possibly ...". Calibrated hedging
  belongs in the Approach's interpretation, not in the central claim.

## Preserve and deploy (funded-proposal craft)

These read as strength; keep or add them rather than editing them out.

- **Vision framing**: a bold long-term goal up front, with this proposal as one
  principled step toward it.
- **Run-in lead-ins for scannability**: bold or italic **Goal:**,
  **Motivation:**, **Innovation:**, *Aim N (one-line mission)*. Reviewers skim;
  visible structure earns reading time. (The manuscript colon-elaboration rule
  does not apply to these labeled run-ins.)
- **A concrete running example** that stays consistent across aims and makes an
  abstract method vivid.
- **Sharp aim statements posed as questions**: a crisp open question reads as a
  well-posed problem; a boxed or set-off question per aim works well.
- **Classical anchors**: grounding new work in a named inequality, capacity
  notion, or established test signals rigor and lineage.
- **Team standing as feasibility evidence, placed early**: prior funded work,
  preliminary results, publications, collaborators, and demonstration partners
  belong where they de-risk the aims. A real track record is evidence, not
  boasting. *(Only the PI's own real, supplied record; never invent funding,
  results, partners, or letters.)*

## Process

1. **Read** the proposal and any supplied prior funded proposal or writing
   sample; note the agency and mechanism (NSF core/CAREER, NIH R01/R21,
   fellowship) and its structural expectations above.
2. **Audit, do not edit yet.** List (a) first-pages completeness (hook / gap /
   central idea / aims / payoff, each present or missing with location), (b)
   every weak move found, with location and proposed fix, (c) every
   aim-or-promise's feasibility footing (present, weak, or absent), (d) L0
   findings from the shared linter:
   `python tools/ai_ism_lint.py <file> --field <field>` (skip the field flag
   when no profile applies; structural axes calibrated on journal corpora are
   `degraded` for proposals and advisory-only).
3. **Rewrite.** Same aims, same evidence, same citations. Fix weak moves,
   attach feasibility footings beside ambitious claims, keep the vision, clear
   L0 targets, and edit the score-forming pages hardest. Rewrite-eligibility
   invariants (SCIPAPER_STANDARD §6) hold: no number, citation, stance, or
   qualifier changes without the author's source.
4. **Report.** Cleaned text plus a change log: weak moves fixed by type,
   feasibility gaps flagged for the author (with what evidence would close
   them), L0 before/after counts, and any structural expectations the draft
   still misses. Confirm no number, result, or citation was altered and no
   support was invented.

## Anti-patterns

- Flattening the long-term vision because paper mode would trim it.
- "Improving" a proposal by inventing preliminary results, partners, letters,
  or funding history: that is fabrication, not editing.
- Leaving a hedged central hypothesis because hedging is legitimate in papers.
- Spending effort on later sections while the Aims/Summary page is weak.
- Treating funder page limits, formatting, and deadline rules from memory as
  current: consult the funder's live policy documents (NSF PAPPG, NIH
  application guide) for binding requirements.
