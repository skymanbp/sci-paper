# Documentation index

Four kinds of document live here, and the difference between them is load-bearing:
only the first is normative.

| | Document | Kind | Read it when |
|---|---|---|---|
| **Normative** | [SCIPAPER_STANDARD.md](SCIPAPER_STANDARD.md) | The single writing/review contract. If a skill, tool, profile, or workflow disagrees with it, **it wins**. | Always first. Everything else implements or measures this. |
| **Architecture** | [architecture/DEAI_SUBSYSTEM.md](architecture/DEAI_SUBSYSTEM.md) | How the de-AI subsystem is built: layers, detectors, isolation, calibration artifacts. | You are changing a tool or tracing why a finding was emitted. |
| **Evidence** | [architecture/EVALUATION.md](architecture/EVALUATION.md) | What is currently measured, what is degraded or unmeasured, and every known confound. | You want to know whether an axis can be trusted, and on what sample. |
| **Frozen design notes** | [design-notes/DEAI_ARCHITECTURE_ROADMAP.md](design-notes/DEAI_ARCHITECTURE_ROADMAP.md)<br>[design-notes/DEAI_FRONTIER.md](design-notes/DEAI_FRONTIER.md) | Dated reasoning records, **not status documents**. Their present tense is the present tense of the day they were written. | You want to know *why* a design decision was taken. |

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
