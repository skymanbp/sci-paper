---
name: final-review
description: 投稿前最终审阅编排器。每轮加载 paper 与 SCIPAPER_STANDARD 作为框架，并在独立 worktree 中运行 paper-review、figure-review、mainline、paper-attack-tree 和 parent-level modern-physics-review。合并 sci-paper.feedback.v1 typed findings：科学完整性 blocker 必须解决，L0 target 必须清零，strong advisory 必须 disposition，ordinary advisory 与 unavailable axes 保留报告。连续多轮验证该状态稳定，不把所有 editorial feedback 强行清零，也不输出通用 paper PASS/FAIL。Use for final-review、投稿前总审、submission-readiness evidence gathering 和所有审查 skill 的隔离编排。
disable-model-invocation: false
argument-hint: "<file_path> [--max-rounds N] [--skip <skill>[,<skill>...]] [--field <name>] [--out <dir>] [--require-consecutive N]"
---

# final-review — isolated typed-review orchestrator

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> This skill verifies a stable, disposition-complete review state. It does not certify
> journal acceptance, authorship, aesthetic perfection or a universal paper PASS.

The required review components are:

1. `/sci-paper:paper` as the writing and L0 framework;
2. `/sci-paper:paper-review` for A–R source-traced scientific review;
3. `/sci-paper:figure-review` for compiled-page figure evidence;
4. `/sci-paper:mainline` for contribution-graph and cold-read narrative feedback;
5. `/sci-paper:paper-attack-tree` for open-ended adversarial critique;
6. host-level modern-physics-review, launched by the parent orchestrator to avoid nested agents.

## 0. Hard orchestration rules

1. **Run, do not remember.** Every round launches fresh isolated reviewers for all non-skipped
   components. Prior reports are comparison artifacts, not substitutes for current review.
2. **Isolation is mandatory.** paper-review, figure-review, mainline, attack-tree and MPR run
   in separate `isolation: worktree` agents. The parent loads `paper` and the standard, merges
   reports and applies authorized fixes.
3. **No nested agents.** paper-review receives `--no-isolated-mpr`; the parent launches MPR at
   the same level as the other reviewers. Any child attempt to spawn an agent is a prompt error.
4. **Preserve evidence, not verdict authority.** The parent may not discard a child finding,
   but must verify/deduplicate it and type its consequence. CONFIRMED critique is not
   automatically an integrity blocker.
5. **Merge by structured contract.** Each child returns or is normalized to
   `sci-paper.feedback.v1`; text and JSON derive from the same findings.
6. **Scientific blockers are non-waivable.** Incorrect math/physics/statistics, source or
   citation mismatch, leakage, contradiction, broken required build and missing required
   artifacts must be resolved or verified false positives.
7. **L0 target is zero.** Tier A, em-dash and Tier B excess must be removed.
8. **Advisories use dispositions.** Strong advisories must be acted, accepted, rejected as
   false positives, or pending with a stated reason. Ordinary advisories remain visible and
   do not have to disappear.
9. **Measurement states remain explicit.** A skipped, failed or unavailable axis is
   `unmeasured`/`degraded`, not clean.
10. **Minimum effective fixes only.** Every edit maps to a finding ID; no opportunistic
    rewriting or unrelated refactor.
11. **Stable rounds verify state, not zero suggestions.** `--require-consecutive` rounds must
    reproduce a disposition-complete state with no new blockers/L0 and no unexplained change
    in strong advisories.
12. **Do not expand budget silently.** `--max-rounds` exhaustion returns
    `BREAK_WITH_USER_DECISION` with the exact unresolved state.

## 1. Invocation and states

```text
/sci-paper:final-review <file_path> [flags]
```

Defaults:

- `--max-rounds 10`
- `--require-consecutive 2`
- no skipped reviewers
- output under `final-review-out/<date>__<slug>/`

Valid skips: `paper-review`, `figure-review`, `mainline`, `paper-attack-tree`, `mpr`.
A skip must be user-explicit, remains visible as `unmeasured`, and cannot be described as
reviewed. A figure-less document normally yields `not_applicable`, not PASS.

Workflow states:

- `IN_PROGRESS`
- `DISPOSITION_COMPLETE`
- `BREAK_WITH_USER_DECISION`
- `SUBAGENT_FAILURE`
- `PROMPT_VIOLATION`
- `USER_INTERRUPTED`

## 2. Preparation

1. Read the current target manuscript completely.
2. Read `docs/SCIPAPER_STANDARD.md` and the current SKILL.md files for paper, paper-review,
   figure-review, mainline and paper-attack-tree.
3. Resolve field evidence; missing assets remain explicit.
4. Create the output root and round directory.
5. Initialize a finding registry keyed by stable finding ID plus semantic deduplication key
   `(rule, location, evidence)`.
6. Record target path, current revision/hash, build system and selected field.

## 3. Each review round

### 3.1 Load the framework

In the parent context, invoke `/sci-paper:paper` and read the normative standard. Record their
current versions/paths in `paper-baseline.md`. This provides policy, not a child verdict.

### 3.2 Isolated paper-review

Launch a worktree agent with a self-contained prompt:

- cold-read the current target and all sources;
- invoke `/sci-paper:paper-review <target> --no-isolated-mpr --field <field>`;
- do not spawn any child agent;
- return the complete typed report, including A–R coverage, measurement states, blockers,
  L0 targets, strong/ordinary advisories, dispositions, M-pass state and build evidence;
- set isolated MPR state to `SKIPPED_FOR_ORCHESTRATOR`.

If it attempts nesting, return `NESTED_AGENT_REJECTED`; the round becomes
`PROMPT_VIOLATION` and must be reissued with the corrected prompt.

### 3.3 Isolated figure-review

Launch a separate worktree agent to invoke `/sci-paper:figure-review` on the current compiled
paper. It must return:

- render/build measurement state;
- figure inventory and source provenance;
- typed blockers and advisories;
- explicit `not_applicable` if no figures exist.

It must not return literal PASS/WARN as the merge interface.

### 3.4 Isolated mainline

Launch a separate worktree agent to invoke
`/sci-paper:mainline <target> --orchestrator-isolated`. The flag records that this child is
already the fresh isolated cold reader and prevents a nested readability agent. It must return:

- root question and contribution graph;
- relations among multiple contributions;
- cold-reader confusion evidence;
- typed narrative findings and dispositions;
- unavailable measurement states.

Do not require the reader to reduce a valid multi-contribution paper to one thread.

### 3.5 Isolated paper-attack-tree

Launch a separate worktree agent to invoke `/sci-paper:paper-attack-tree` with
`--no-subagents`, passing the current paper-review report as seed when available. The child is
already isolated and must complete all framing passes itself rather than spawning nested agents.
The attack-tree process may terminate as `CONVERGED` or an explicit cap state; that status
describes search completion only.

For every leaf return:

- evidentiary verdict: CONFIRMED / MARGINAL / REFUTED;
- independent consequence kind;
- measurement status;
- proposed action and disposition;
- source trace.

All verified critiques enter the merge registry. Only their consequence determines whether
they are blockers, L0 targets or advisories.

### 3.6 Parent-level isolated modern-physics-review

Launch a sibling worktree agent, never from inside paper-review. The prompt must instruct it to:

- cold-read all current sources;
- load and execute the host-level modern-physics-review protocol;
- avoid spawning sub-agents;
- return each scientific issue with evidence and a proposed consequence class;
- report disagreements with other reviewers without assuming the other reviewers are wrong;
- state unavailable checks explicitly.

Normalize its output to the shared finding schema. A disagreement is a finding candidate, not
an automatic blocker; verify the evidence and assign consequence.

### 3.7 Merge and verify

Combine all child reports into one registry:

```text
registry = merge_by_stable_id_and_semantic_key(
    paper_review,
    figure_review,
    mainline,
    attack_tree,
    mpr,
)
```

For overlaps:

- retain every source trace and detector;
- keep the most severe consequence only when evidence supports it;
- record reviewer disagreement rather than silently choosing one;
- do not parse JSON from human-readable prose;
- totals come from the merged structured findings.

The parent verifies any finding before editing its target. A child’s REFUTED result remains a
positive evidence record; a CONFIRMED editorial critique remains an advisory.

### 3.8 Apply fixes and dispositions

Order work by the unified priority key:

1. integrity blockers;
2. L0 targets;
3. strong advisories;
4. ordinary advisories only when authorized or clearly part of a blocker/L0 repair.

For each action:

- map it to finding IDs;
- read the target and source evidence;
- apply the minimum effective edit;
- re-read affected context;
- rerun the relevant build, scientific check, figure render, linter or claim-fidelity check;
- record `acted`, `accepted`, `rejected_as_false_positive` or `pending`.

Subjective strong advisories that require author preference may remain pending with a precise
question. Do not erase them merely to make counts zero.

## 4. Stable-round criterion

A round is **disposition-complete** when:

- pending integrity blockers = 0;
- pending L0 targets = 0;
- critical derivations under scrutiny = 0;
- required build/artifacts are valid;
- every strong advisory has a disposition or stated pending reason;
- ordinary advisories and unmeasured/degraded axes are reported;
- skipped reviewers are labeled unmeasured;
- no child report or merge failed.

A stable round additionally requires:

- no new blocker or L0 target relative to the previous complete round;
- no previously resolved blocker/L0 reappears;
- strong-advisory set and dispositions are unchanged or the change is explained by new evidence;
- scientific anchors and build outputs remain current.

Increment `consecutive_stable_rounds` only for stable disposition-complete rounds. Reset it when
new blockers/L0 targets appear, a required measurement fails, or a disposition changes without
new evidence. When it reaches `--require-consecutive`, return `DISPOSITION_COMPLETE`.

Attack-tree may continue to generate ordinary advisories; those do not reset stability unless
they expose a new blocker/L0 or a new strong advisory requiring disposition.

## 5. Failure and budget handling

- Child failure/timeout: retry only after diagnosing the cause; repeated failure returns
  `SUBAGENT_FAILURE` with that axis unmeasured.
- Nested-agent attempt or wrong MPR ownership: `PROMPT_VIOLATION`.
- User skip: record `unmeasured` and continue under explicit limitation.
- `--max-rounds` exhausted: `BREAK_WITH_USER_DECISION`; list pending blockers, L0 targets,
  strong advisories, failed/unmeasured axes and options. Do not increase the budget or claim
  completion.
- User interruption: preserve all current reports and registry.

## 6. Final report contract

```markdown
# Final Review — Disposition-Complete Report
Target: <file> | Revision: <hash> | Field: <field or none>
Workflow state: DISPOSITION_COMPLETE | BREAK_WITH_USER_DECISION | SUBAGENT_FAILURE
Rounds: K | Consecutive stable rounds: N

## Measurement coverage
| reviewer/axis | status | provenance / limitation |

## Merged summary
- integrity blockers: resolved / pending
- L0 targets: resolved / pending
- strong advisories: acted / accepted / false-positive / pending
- ordinary advisories: total / reported
- M derivations: verified / under scrutiny
- build and figure render status

## Ranked merged findings
| id | source reviewers | kind | layer | rule | location | evidence | action | disposition |

## Scientific anchors
| claim/quantity | manuscript | source | verification |

## Reviewer disagreements
<evidence from each side and final consequence/disposition>

## Residual feedback
- pending strong advisories and author questions
- ordinary advisories
- degraded/unmeasured/not_applicable axes
- explicit skips

## Fix trace by round
<finding IDs, before/after, verification>

## Per-reviewer reports
<links or verbatim reports; preserve structured JSON beside them>
```

Do not show a per-skill PASS table. “No findings under measured axes” is not proof about
unmeasured axes.

## 7. Completion meaning

`DISPOSITION_COMPLETE` means the mandated review workflow reached a stable state in which:

- scientific blockers were resolved or disproved;
- L0 targets are zero;
- strong advisories have explicit author/process dispositions;
- ordinary residuals and limitations are visible;
- independent reviewers reproduced that state for the required consecutive rounds.

It does not mean the paper is guaranteed correct, accepted, human-authored, aesthetically
unique or free of every possible reviewer objection.

## 8. Anti-patterns

- Reusing last round’s report without rerunning isolated reviewers.
- Allowing paper-review to spawn nested MPR.
- Treating every child CONFIRMED critique as a blocker.
- Treating every advisory or reviewer disagreement as mandatory prose change.
- Requiring figure-review to return PASS.
- Requiring mainline to find exactly one contribution thread.
- Calling missing calibration a clean result.
- Resetting or dropping inconvenient findings during deduplication.
- Declaring completion because all numeric issue counts are zero while axes were skipped.
- Forcing subjective advisories to disappear instead of recording author disposition.
- Increasing iteration budget silently.
