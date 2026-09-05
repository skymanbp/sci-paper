# Documentation index

Six kinds of document live here, and the difference between them is load-bearing:
only the first two are normative.

| | Document | Kind | Read it when |
|---|---|---|---|
| **Normative** | [SCIPAPER_STANDARD.md](SCIPAPER_STANDARD.md) | The single writing/review contract. If a skill, tool, profile, or workflow disagrees with it, **it wins**. | Always first. Everything else implements or measures this. |
| **Normative annex** | [architecture/RESPONSIBILITIES.md](architecture/RESPONSIBILITIES.md) | §§7-8 of the standard, incorporated by reference: what each skill and each tool is required to do. No independent authority — the standard wins. | You are writing or changing a skill or tool and need its binding role. |
| **Decision register** | [architecture/DISPOSITIONS.md](architecture/DISPOSITIONS.md) | §11 of the standard: every open de-AI engineering item and its decided disposition, with the measurement behind it. A record of decisions, not policy. | You want to know whether an idea was shipped, deferred, rejected, or refuted — and on what evidence. |
| **Architecture** | [architecture/DEAI_SUBSYSTEM.md](architecture/DEAI_SUBSYSTEM.md) | How the de-AI subsystem is built: layers, detectors, isolation, calibration artifacts. | You are changing a tool or tracing why a finding was emitted. |
| **Evidence** | [architecture/EVALUATION.md](architecture/EVALUATION.md) — the hub | Evaluation contract, current per-axis status, repository verification, release evidence boundary, and the map of every section. | You want to know whether an axis can be trusted, and on what sample. **Start here**, then follow the map. |
| **Frozen design notes** | [design-notes/DEAI_ARCHITECTURE_ROADMAP.md](design-notes/DEAI_ARCHITECTURE_ROADMAP.md)<br>[design-notes/DEAI_FRONTIER.md](design-notes/DEAI_FRONTIER.md) | Dated reasoning records, **not status documents**. Their present tense is the present tense of the day they were written. | You want to know *why* a design decision was taken. |

The evidence record is one document split across nine files, because a single one
had grown past the point of being readable. Section numbers are **global**: §9.5 means
the same thing wherever it is cited from, and the hub's section map says which file it
lives in.

| Part | Sections | Evidence |
|---|---|---|
| [architecture/EVALUATION.md](architecture/EVALUATION.md) | 1–3, 12 | The hub: contract, axis status, repository verification, release boundary, section map |
| [architecture/evaluation/lexical-structure-uid.md](architecture/evaluation/lexical-structure-uid.md) | 4–6, 16 | L0 behaviour, sentence-structure reference, UID reference |
| [architecture/evaluation/learned-model.md](architecture/evaluation/learned-model.md) | 7, 8, 10 | Learned field similarity and its confound audit, rewrite eligibility, author hard set |
| [architecture/evaluation/document-scale.md](architecture/evaluation/document-scale.md) | 9 | Whole-document dispersion: the keystone axis, its adversarial tiers and conformal operating points |
| [architecture/evaluation/narrative-salience-register.md](architecture/evaluation/narrative-salience-register.md) | 11, 13–15 | Real rewrite evaluation, blind perceptual panel, salience hierarchy, domain register, narrative salience |
| [architecture/evaluation/held-out-labels.md](architecture/evaluation/held-out-labels.md) | 17, 21 | Held-out refereed papers as provenance labels: the register false-positive rate, the salience gate-transfer check, and the paired leakage test |
| [architecture/evaluation/projection-and-operating-point.md](architecture/evaluation/projection-and-operating-point.md) | 18, 22 | Citation projection symmetry, the digits the salience axis was misreading, the held-out collection guard, the register operating point derived against refereed prose, citation placement measured but not shipped (refuted in §20), and the three drift events behind the check that now pins every published figure to its artifact |
| [architecture/evaluation/discourse-and-citation.md](architecture/evaluation/discourse-and-citation.md) | 19–20 | The two discourse axes and why they measure at different units — hedging has no paragraph-scale lower tail, so it calibrates per section and speaks only for the bucket where its gate was shown to transfer — and citation placement refuted by a second, independently produced machine bank: one prompt line moves the same statistic from 0.053 to 0.734 |
| [architecture/evaluation/vocabulary-and-residue.md](architecture/evaluation/vocabulary-and-residue.md) | 23 | The zero-hit vocabulary audit (exhaustive, not a detector), the collocation axis against a leave-one-out reference, the three structure families taken from a mentor's comments, the removal map's baseline on refereed papers, and the residue rules' false-positive rate |

## The authority order

```
docs/SCIPAPER_STANDARD.md          normative policy — the only file that decides
        │
        ├── docs/architecture/RESPONSIBILITIES.md  §§7-8, incorporated by reference
        ├── docs/architecture/DISPOSITIONS.md      §11, the decision register
        │
        ├── docs/architecture/DEAI_SUBSYSTEM.md    how it is implemented
        │        └── docs/architecture/EVALUATION.md   what that implementation measures
        │
        └── docs/design-notes/                     why it was designed that way (frozen)
```

The standard was 823 lines against a 750-line budget on 2026-08-25 and could no
longer be edited at all. The two registers above and its embedded version
history (now in [../CHANGELOG.md](../CHANGELOG.md)) were moved out; §§0-10 of
the contract itself are unchanged.

Corpus profiles, learned models, thresholds, and evaluation results are **evidence**.
They cannot redefine the standard, create an authorship verdict, or produce a
universal paper PASS/FAIL.

## Where everything else is documented

| Topic | File |
|---|---|
| What the plugin ships and how to run it | [../README.md](../README.md) · [../README.zh-CN.md](../README.zh-CN.md) |
| Per-tool registry, calibration, and failure behavior | [../tools/README.md](../tools/README.md) |
| Supplying a field corpus | [../style-corpus/README.md](../style-corpus/README.md) |
| Generated profile assets and build boundaries | [../style-profile/README.md](../style-profile/README.md) |
| Per-version history | [../CHANGELOG.md](../CHANGELOG.md) · [../CHANGELOG-ARCHIVE-v0.33-v0.34.md](../CHANGELOG-ARCHIVE-v0.33-v0.34.md) (v0.33.0-v0.34.0) · [../CHANGELOG-ARCHIVE-RECENT.md](../CHANGELOG-ARCHIVE-RECENT.md) (v0.27.1-v0.32.0) · [../CHANGELOG-ARCHIVE.md](../CHANGELOG-ARCHIVE.md) (v0.22.0-v0.27.0) · [../CHANGELOG-ARCHIVE-EARLY.md](../CHANGELOG-ARCHIVE-EARLY.md) (v0.1.0-v0.21.0) |
| Working rules for this repository | [../CLAUDE.md](../CLAUDE.md) |
| Adapted-material attribution and adoption boundaries | [../ACKNOWLEDGMENTS.md](../ACKNOWLEDGMENTS.md) |
| External review records (findings, first-party verification, disposition) | [audits/codex-review-2026-09-04.md](audits/codex-review-2026-09-04.md) |

## Conventions this directory is held to

`tools/validate_plugin.py` enforces the following, so drift fails CI rather than
accumulating:

- the release version appears in the header line of `DEAI_SUBSYSTEM.md` and `EVALUATION.md`;
- every document in `docs/` is linked from this index (no orphan documents);
- each file under `design-notes/` declares itself a design note in its header;
- no document reappears at a location it was moved away from;
- every suite size recorded anywhere in the evidence record or in either README matches actual test discovery;
- no tracked source or document exceeds 750 lines, the same cap the editing hook enforces.

One convention it cannot enforce lives in the suite instead. The figures these
documents quote come from `style-profile/<field>/`, which is gitignored, so no
CI check can open the source of a published number.
`tests/test_published_figures.py` therefore renders each figure *from* the
artifact and looks for it in the document, and skips — rather than passes — when
a clean clone has no profile to read. The drift it exists to stop is recorded in
[§18.8](architecture/evaluation/projection-and-operating-point.md).

Historical `CHANGELOG.md` entries quote the documentation paths that were current
at that release; documents moved into `architecture/` and `design-notes/` in
v0.27.0.
