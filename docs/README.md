# Documentation index

Four kinds of document live here, and the difference between them is load-bearing:
only the first is normative.

| | Document | Kind | Read it when |
|---|---|---|---|
| **Normative** | [SCIPAPER_STANDARD.md](SCIPAPER_STANDARD.md) | The single writing/review contract. If a skill, tool, profile, or workflow disagrees with it, **it wins**. | Always first. Everything else implements or measures this. |
| **Architecture** | [architecture/DEAI_SUBSYSTEM.md](architecture/DEAI_SUBSYSTEM.md) | How the de-AI subsystem is built: layers, detectors, isolation, calibration artifacts. | You are changing a tool or tracing why a finding was emitted. |
| **Evidence** | [architecture/EVALUATION.md](architecture/EVALUATION.md) — the hub | Evaluation contract, current per-axis status, repository verification, release evidence boundary, and the map of every section. | You want to know whether an axis can be trusted, and on what sample. **Start here**, then follow the map. |
| **Frozen design notes** | [design-notes/DEAI_ARCHITECTURE_ROADMAP.md](design-notes/DEAI_ARCHITECTURE_ROADMAP.md)<br>[design-notes/DEAI_FRONTIER.md](design-notes/DEAI_FRONTIER.md) | Dated reasoning records, **not status documents**. Their present tense is the present tense of the day they were written. | You want to know *why* a design decision was taken. |

The evidence record is one document split across five files, because a single one
had grown past the point of being readable. Section numbers are **global**: §9.5 means
the same thing wherever it is cited from, and the hub's section map says which file it
lives in.

| Part | Sections | Evidence |
|---|---|---|
| [architecture/EVALUATION.md](architecture/EVALUATION.md) | 1–3, 12 | The hub: contract, axis status, repository verification, release boundary, section map |
| [architecture/evaluation/lexical-structure-uid.md](architecture/evaluation/lexical-structure-uid.md) | 4–6 | L0 behaviour, sentence-structure reference, UID reference |
| [architecture/evaluation/learned-model.md](architecture/evaluation/learned-model.md) | 7, 8, 10 | Learned field similarity and its confound audit, rewrite eligibility, author hard set |
| [architecture/evaluation/document-scale.md](architecture/evaluation/document-scale.md) | 9 | Whole-document dispersion: the keystone axis, its adversarial tiers and conformal operating points |
| [architecture/evaluation/narrative-salience-register.md](architecture/evaluation/narrative-salience-register.md) | 11, 13–15 | Real rewrite evaluation, blind perceptual panel, salience hierarchy, domain register, narrative salience |

## The authority order

```
docs/SCIPAPER_STANDARD.md          normative policy — the only file that decides
        │
        ├── docs/architecture/DEAI_SUBSYSTEM.md    how it is implemented
        │        └── docs/architecture/EVALUATION.md   what that implementation measures
        │
        └── docs/design-notes/                     why it was designed that way (frozen)
```

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
| Per-version history | [../CHANGELOG.md](../CHANGELOG.md) |
| Working rules for this repository | [../CLAUDE.md](../CLAUDE.md) |
| Adapted-material attribution and adoption boundaries | [../ACKNOWLEDGMENTS.md](../ACKNOWLEDGMENTS.md) |

## Conventions this directory is held to

`tools/validate_plugin.py` enforces the following, so drift fails CI rather than
accumulating:

- the release version appears in the header line of both architecture documents;
- every document in `docs/` is linked from this index (no orphan documents);
- each file under `design-notes/` declares itself a design note in its header;
- no document reappears at a location it was moved away from;
- every suite size recorded in `EVALUATION.md` matches actual test discovery.

Historical `CHANGELOG.md` entries quote the documentation paths that were current
at that release; documents moved into `architecture/` and `design-notes/` in
v0.27.0.
