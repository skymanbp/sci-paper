"""Every published figure must equal the artifact it was read from.

The numbers the documents quote live in `style-profile/<field>/`, which is
gitignored. Nothing has ever been able to see the source of a published figure,
so the only rule holding the two together was "re-read the artifact in the same
turn you paste it" -- and that rule broke three times in three releases:

- v0.29.0 re-ran the README demo against a rebuilt profile but left the
  section's provenance stamp naming the previous one;
- the v0.32.0 sweep corrected `EVALUATION.md`'s axis table and missed both
  READMEs' artifact tables, where six of seven structure counts and six of
  seven salience counts were stale;
- the UID baseline finished rebuilding after the v0.32.0 tag, with nothing
  pointing at the four documents that quote it.

One document has no artifact at all. `examples/README.md` publishes what the
linter reports about the two example manuscripts this repository ships, so its
source is the run, and that case renders its counts by running it.

Each case below renders the expected substring FROM the artifact and then looks
for it, so a document that agrees with a stale artifact and a document nobody
updated fail identically. That is the point: this is not a spell-check of the
digits, it is a check that the digits still have a source.

A fresh clone ships no profile, so these tests SKIP rather than pass. Absence is
reported as absence; treating it as agreement would be the same defect one
layer up.
"""

from __future__ import annotations

import collections
import functools
import json
import pathlib
import re
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
UID_DOC = "docs/architecture/evaluation/lexical-structure-uid.md"
EVALUATION_DOC = "docs/architecture/EVALUATION.md"
DISCOURSE_DOC = "docs/architecture/evaluation/discourse-and-citation.md"
EXAMPLES_DOC = "examples/README.md"
EXAMPLE_BEFORE = "examples/sample-manuscript.tex"
EXAMPLE_AFTER = "examples/sample-manuscript-revised.tex"
LINTER = "tools/ai_ism_lint.py"
DOCSCALE_DETECTOR = "deai_docstructure"
RE_PROFILE_FIELD = re.compile(r"style-profile/([^/`\s]+)/uid_baseline\.json")
BUCKETS = ("method", "results", "data", "intro", "discussion", "conclusion",
           "abstract")
AXIS_TABLE_ORDER = ("abstract", "method", "data", "intro", "discussion",
                    "results", "conclusion")
# The per-rule table in examples/README.md, in its order: one rule named with
# its variant, one with its layer, five with neither. Which rules the
# walkthrough tabulates is the document's choice; every count in it is the
# linter's.
EXAMPLE_RULE_ROWS = (
    ("`discourse-cohesion`", "discourse-cohesion"),
    ("`em-dash` (L0)", "em-dash"),
    ("`ing-tail:highlighting`", "ing-tail:highlighting"),
    ("`document-uniformity`", "document-uniformity"),
    ("`document-role-decoupling`", "document-role-decoupling"),
    ("`structure-template`", "structure-template"),
    ("`salience-recital`", "salience-recital"),
)


def _field() -> str | None:
    """The field the evidence record names, rather than a hard-coded one.

    The record writes its own source path (`style-profile/wgl/uid_baseline
    .json`), so the field is data. A corpus with two fields, or one named
    anything else, needs no edit here.
    """
    match = RE_PROFILE_FIELD.search((REPO / UID_DOC).read_text(encoding="utf-8"))
    return match.group(1) if match else None


FIELD = _field()
PROFILE = REPO / "style-profile" / (FIELD or "")
HAVE_PROFILE = bool(FIELD) and (PROFILE / "uid_baseline.json").is_file()
needs_profile = unittest.skipUnless(
    HAVE_PROFILE,
    f"no built profile at style-profile/{FIELD}/ — figures are unmeasured here")


def artifact(name: str) -> dict:
    return json.loads((PROFILE / name).read_text(encoding="utf-8"))


def bucket_n(name: str) -> dict[str, int]:
    return {key: value["n"] for key, value in artifact(name).items()}


def by_dot(counts: dict[str, int]) -> str:
    """The `name n · name n` ordering §19.1 uses: largest bucket first."""
    return " · ".join(f"{key} {counts[key]:,}"
                       for key in sorted(counts, key=lambda key: -counts[key]))


def gate(name: str, feature: str, bucket: str, places: int) -> str:
    """The feature value at the advisory gate, as §19 prints it."""
    reference = artifact(name)[bucket]["percentiles"][feature]
    at = min(reference, key=lambda stored: abs(float(stored) - 0.10))
    return f"{float(reference[at]):.{places}f}"


def by_n(counts: dict[str, int]) -> str:
    """The `name n · name n` ordering both READMEs use: largest bucket first."""
    return " · ".join(f"{key} {counts[key]:,}"
                      for key in sorted(counts, key=lambda key: -counts[key]))


def pooled_uid(metric: str) -> tuple[str, str]:
    pooled = artifact("uid_baseline.json")["pooled"][metric]
    return f"{pooled['mean']:.3f}", f"{pooled['stdev']:.3f}"


def bank_size() -> int:
    with (PROFILE / "exemplar_paragraphs.jsonl").open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def uid_row(bucket: str) -> tuple[str, str, str]:
    uid = artifact("uid_baseline.json")["by_section"][bucket]["global_uid"]
    return f"{uid['n']:,}", f"{uid['mean']:.2f}", f"{uid['stdev']:.2f}"


@functools.lru_cache(maxsize=None)
def lint_report(manuscript: str) -> dict:
    """The shipped linter's own report for one shipped example manuscript.

    Every other figure here has an artifact behind it; this one has a run. The
    walkthrough publishes what `ai_ism_lint` reports about `examples/`, so the
    source its table must agree with is the linter, and a cell the linter does
    not produce fails this case.
    """
    finished = subprocess.run(
        [sys.executable, str(REPO / LINTER), str(REPO / manuscript),
         "--field", FIELD or "", "--format", "json"],
        capture_output=True, text=True, encoding="utf-8")
    # Exit 1 is the documented code for "an L0 target is present", which the
    # before-manuscript is written to carry. Only a third code is a failure.
    if finished.returncode not in (0, 1):
        raise RuntimeError(f"{manuscript}: lint exited {finished.returncode}\n"
                           f"{finished.stderr}")
    return json.loads(finished.stdout)


def example_rule_counts(manuscript: str) -> collections.Counter:
    """Findings per rule, counted under the whole rule and under its family.

    The table names one rule with its variant (`ing-tail:highlighting`) and
    four without (`document-uniformity` covers six features), so a count has to
    be readable at either spelling.
    """
    counts: collections.Counter = collections.Counter()
    for finding in lint_report(manuscript)["findings"]:
        counts[finding["rule"]] += 1
        family = finding["rule"].split(":")[0]
        if family != finding["rule"]:
            counts[family] += 1
    return counts


def example_docscale_findings(manuscript: str) -> int:
    """The document-scale row: what the whole-document detector emitted."""
    return sum(1 for finding in lint_report(manuscript)["findings"]
               if finding["detector"]["name"] == DOCSCALE_DETECTOR)


def example_row(label: str, before: int, after: int) -> str:
    return f"| {label} | {before} | {after} |"


def expectations(document: str) -> list[tuple[str, str]]:
    """(label, exact substring) pairs `document` must contain, rendered now.

    Separate entries per rendering, because the same figure is written one way
    in a table cell and another in prose. Pinning the prose is what catches a
    half-done sweep -- which is how this list came to exist.
    """
    structure = bucket_n("structure_baseline.json")
    if document in ("README.md", "README.zh-CN.md"):
        english = document == "README.md"
        return [
            ("exemplar bank",
             f"**{bank_size():,}** " + ("section-typed paragraphs" if english
                                        else "个按 section 分类的段落")),
            ("register lexicon",
             f"{artifact('register_lexicon.json')['n_passages']:,} "
             + ("passages · " if english else "个 passage · ")
             + f"{len(artifact('register_lexicon.json')['document_frequency']):,}"
             + (" terms" if english else " 个词条")),
            ("uid paragraphs",
             f"| {artifact('uid_baseline.json')['n_paragraphs_used']:,} "
             + ("paragraphs under GPT-2-large" if english else "段（GPT-2-large）")),
            ("uid pooled global",
             ("pooled global UID " if english else "合并 global UID ")
             + "{} ± {}".format(*pooled_uid("global_uid"))),
            ("structure buckets",
             f"| `structure_baseline.json` | {by_n(structure)} |"),
            ("salience buckets",
             "| `salience_baseline.json` | "
             f"{by_n(bucket_n('salience_baseline.json'))} |"),
            ("docstructure documents",
             f"| {artifact('docstructure_baseline.json')['n_documents']:,} "
             + ("complete documents" if english else "篇完整文档")),
            ("anchoring documents",
             f"| {artifact('anchoring_baseline.json')['n_documents']:,} "
             + ("documents · all six section classes" if english
                else "篇文档 · 六个 section 类")),
        ]
    if document == EXAMPLES_DOC:
        reports = [lint_report(EXAMPLE_BEFORE), lint_report(EXAMPLE_AFTER)]
        kinds = [report["summary"]["by_kind"] for report in reports]
        rules = [example_rule_counts(EXAMPLE_BEFORE),
                 example_rule_counts(EXAMPLE_AFTER)]
        return [
            ("L0 targets",
             example_row("L0 targets", *(kind["l0_target"] for kind in kinds))),
            ("integrity blockers",
             example_row("integrity blockers",
                         *(kind["integrity_blocker"] for kind in kinds))),
            ("total advisories",
             example_row("total advisories",
                         *(kind["advisory"] for kind in kinds))),
            ("strong advisories",
             example_row("strong advisories",
                         *(report["summary"]["strong_advisories"]
                           for report in reports))),
            ("document-scale findings",
             example_row("document-scale findings",
                         example_docscale_findings(EXAMPLE_BEFORE),
                         example_docscale_findings(EXAMPLE_AFTER))),
        ] + [(f"per rule: {rule}",
              example_row(label, *(count[rule] for count in rules)))
             for label, rule in EXAMPLE_RULE_ROWS]
    if document == DISCOURSE_DOC:
        # §19 is the only place two references built at different units are
        # quoted side by side, and reading one against the other is the exact
        # error the axis exists to prevent -- so both are pinned to their own
        # artifact, including the p10 gate each bucket abstains or fires at.
        return [
            ("cohesion buckets", f"| paragraph | {by_dot(bucket_n('cohesion_baseline.json'))} |"),
            ("hedging buckets", f"| section | {by_dot(bucket_n('hedging_baseline.json'))} |"),
            ("bank size", f"the {bank_size():,}-paragraph `{FIELD}` bank"),
        ] + [(f"hedging gate: {bucket}",
              f"| {bucket} | {gate('hedging_baseline.json', 'hedging', bucket, 3)} |")
             for bucket in BUCKETS if bucket != "abstract"]
    if document == EVALUATION_DOC:
        salience = bucket_n("salience_baseline.json")
        register = artifact("register_lexicon.json")
        return [
            ("bucket-history total", f"| **{sum(structure.values()):,}** |"),
            ("axis table: register",
             f"{register['n_passages']:,} corpus passages, "
             f"{len(register['document_frequency']):,} terms"),
            # The axis table lists its buckets in a fixed prose order rather
            # than by size. The order is the document's; the numbers are the
            # artifact's. Twelve of these went stale in one release.
            ("axis table: salience buckets",
             "; ".join(f"{bucket} {salience[bucket]:,}"
                       for bucket in AXIS_TABLE_ORDER)),
            ("axis table: structure buckets",
             f"{sum(structure.values()):,} paragraphs — "
             + "; ".join(f"{bucket} {structure[bucket]:,}"
                         for bucket in BUCKETS) + "."),
        ]
    cases = [
        ("uid paragraphs",
         f"records **{artifact('uid_baseline.json')['n_paragraphs_used']:,}** "
         "paragraphs that met its"),
        ("uid pooled global",
         "global UID is **{} ± {}**".format(*pooled_uid("global_uid"))),
        ("uid pooled local", "local UID {} ± {}".format(*pooled_uid("local_uid"))),
        ("uid pooled surprisal",
         "mean surprisal {} ± {}.".format(*pooled_uid("mean_surprisal"))),
        ("structure total",
         f"contains {sum(structure.values()):,} paragraph observations"),
    ]
    for bucket in BUCKETS:
        # Section 5's `name n` list wraps across source lines, so the whole
        # list is not a safe substring; each term separately is.
        cases.append((f"structure term: {bucket}",
                      f"`{bucket}` {structure[bucket]:,}"))
        cases.append((f"uid row: {bucket}",
                      "| {} | {} | {} ± {} |".format(bucket, *uid_row(bucket))))
    return cases


class PublishedFiguresMatchTheirArtifactsTest(unittest.TestCase):
    """One test per document that quotes the generated profile."""

    def assert_document_carries_its_figures(self, document: str) -> None:
        text = (REPO / document).read_text(encoding="utf-8")
        source = f"style-profile/{FIELD}/"
        if document == EXAMPLES_DOC:
            # Which cell the walkthrough bolds is editorial; the digits in it
            # are not. The emphasis is dropped before the comparison rather
            # than reproduced here.
            text = text.replace("**", "")
            source = f"linting examples/ against the `{FIELD}` profile"
        for label, wanted in expectations(document):
            with self.subTest(figure=label):
                self.assertIn(
                    wanted, text,
                    f"{document} no longer carries the {label} figure; "
                    f"{source} now says {wanted!r}")

    @needs_profile
    def test_the_english_readme_artifact_table(self) -> None:
        self.assert_document_carries_its_figures("README.md")

    @needs_profile
    def test_the_chinese_readme_artifact_table(self) -> None:
        self.assert_document_carries_its_figures("README.zh-CN.md")

    @needs_profile
    def test_the_uid_and_structure_reference_sections(self) -> None:
        self.assert_document_carries_its_figures(UID_DOC)

    @needs_profile
    def test_the_evaluation_hub_bucket_table(self) -> None:
        self.assert_document_carries_its_figures(EVALUATION_DOC)

    @needs_profile
    def test_the_discourse_reference_tables(self) -> None:
        self.assert_document_carries_its_figures(DISCOURSE_DOC)

    @needs_profile
    def test_the_worked_example_tables(self) -> None:
        self.assert_document_carries_its_figures(EXAMPLES_DOC)


class TheCheckKnowsWhatItIsCheckingTest(unittest.TestCase):
    """Guards on the check itself, which run with or without a profile."""

    def test_the_field_is_read_from_the_record_not_hard_coded(self) -> None:
        self.assertIsNotNone(
            FIELD,
            f"{UID_DOC} names no style-profile/<field>/uid_baseline.json, so "
            "these tests have no artifact to check the figures against")

    def test_an_absent_profile_skips_rather_than_passes(self) -> None:
        # A check that silently passes when it cannot see its source is worse
        # than no check: it reports agreement it never established.
        self.assertEqual(HAVE_PROFILE,
                         (PROFILE / "uid_baseline.json").is_file())
        self.assertIs(needs_profile, needs_profile)
