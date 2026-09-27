"""`deai_metrics`: the section sweep every per-bucket axis reads, the
distribution findings, and the axis status contract.

No test imported this module before the 2026-09-27 audit (B30), although
`section_units` decides the bucket of every finding in the suite and
`distribution_findings` is one of the linter's default axes.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_metrics as metrics

EVEN = " ".join(["The shear estimator recovers the input signal within the "
                 "quoted error budget."] * 6)
ROADMAP = (
    "However, the estimator recovers the signal within the error budget.\n\n"
    "Moreover, the covariance keeps the noise dependence under rotation.\n\n"
    "Therefore, the likelihood carries both quantities without a change of units.\n"
)


def write_profile(root: Path, *, buckets: dict, policy: dict | None = None,
                  counts: dict | None = None) -> None:
    (root / "sentence_stats.json").write_text(json.dumps(buckets), encoding="utf-8")
    if counts is not None:
        (root / "transition_inventory.json").write_text(json.dumps(
            {"n_paragraphs": sum(counts.values()), "paragraph_initial_counts": counts}),
            encoding="utf-8")
    if policy is not None:
        (root / "deai_policy.json").write_text(json.dumps({"distribution": policy}),
                                               encoding="utf-8")


class SectionSweepTests(unittest.TestCase):
    def test_section_units_inherit_buckets_as_the_corpus_does(self):
        text = ("\\title{T}\n\\begin{document}\n"
                "\\section{Introduction}\nintro prose\n"
                "\\subsection{Prior work}\nstill intro\n"
                "\\section{Methods}\n\\subsection{Survey data}\ndata prose\n"
                "\\section{Acknowledgments}\nthanks\n"
                "\\subsection{Funding}\nmore thanks\n")
        units = metrics.section_units(text)
        self.assertEqual(units[0], (1, 2, metrics.PREAMBLE_LABEL, metrics.PREAMBLE_BUCKET))
        self.assertEqual([(label, bucket) for _s, _e, label, bucket in units[1:]], [
            ("Introduction", "intro"),
            ("Prior work", "intro"),          # a topic subsection inherits
            ("Methods", "method"),
            ("Survey data", "data"),          # a role of its own overrides
            ("Acknowledgments", "skip"),
            ("Funding", "skip"),              # a skip parent stays skipped
        ])
        self.assertEqual([(s, e) for s, e, _l, _b in units],
                         [(1, 2), (3, 4), (5, 6), (7, 7), (8, 9), (10, 11), (12, 13)])
        self.assertEqual(metrics.section_line_ranges(text)[1], (3, 4, "Introduction"))

    def test_a_document_without_headings_is_one_unknown_unit(self):
        self.assertEqual(metrics.section_units("one\ntwo\n"),
                         [(1, 2, metrics.DOCUMENT_LABEL, "unknown")])
        self.assertEqual(metrics.section_units(""), [])

    def test_paragraph_line_ranges_are_one_based_and_offset(self):
        text = "a\nb\n\n\n c\n\nd"
        self.assertEqual(metrics.paragraph_line_ranges(text),
                         [(1, 2, "a\nb"), (5, 5, " c"), (7, 7, "d")])
        self.assertEqual(metrics.paragraph_line_ranges(text, 10),
                         [(10, 11, "a\nb"), (14, 14, " c"), (16, 16, "d")])
        self.assertEqual(metrics.paragraph_line_ranges("\n\n"), [])


class DistributionFindingTests(unittest.TestCase):
    POLICY = {"burstiness_ratio": 0.6, "signpost_fraction": 0.2}

    def test_uniform_lengths_and_roadmap_openers_flag_measured_with_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, buckets={"intro": {"mean": 20.0, "stdev": 10.0}},
                          policy=self.POLICY, counts={"However": 5, "The": 95})
            text = "\\section{Introduction}\n\n" + EVEN + "\n\n" + ROADMAP
            findings = metrics.distribution_findings(text, root, "draft.tex")
            rules = {f["rule"]: f for f in findings}
            self.assertEqual(set(rules), {"burstiness-low:intro", "opener-signposting:intro"})
            burst = rules["burstiness-low:intro"]
            self.assertEqual((burst["measurement_status"], burst["strength"]),
                             ("measured", "strong"))
            # six identical sentences plus the three roadmap ones: a CV far
            # below the reference 0.5, so the ratio sits under the 0.6 gate
            self.assertLess(burst["observed"]["sentence_length_cv"], 0.2)
            self.assertLess(burst["observed"]["ratio"], 0.6)
            self.assertAlmostEqual(burst["reference"]["sentence_length_cv"], 0.5)
            opener = rules["opener-signposting:intro"]
            self.assertEqual(opener["observed"]["connective_openers"], 3)
            self.assertAlmostEqual(opener["reference"]["corpus_fraction"], 0.05)
            self.assertIn("reference corpus rate is 5.0%", opener["message"])
            self.assertEqual(opener["location"]["path"], "draft.tex")

    def test_without_policy_findings_are_degraded_and_ordinary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, buckets={"intro": {"mean": 20.0, "stdev": 10.0}})
            text = "\\section{Introduction}\n\n" + EVEN + "\n"
            findings = metrics.distribution_findings(text, root)
            self.assertEqual([f["rule"] for f in findings], ["burstiness-low:intro"])
            self.assertEqual((findings[0]["measurement_status"], findings[0]["strength"]),
                             ("degraded", "ordinary"))
            self.assertEqual(metrics.distribution_findings(text, None), [])

    def test_skip_and_preamble_units_are_not_measured(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, buckets={"intro": {"mean": 20.0, "stdev": 10.0}},
                          policy=self.POLICY)
            text = ("\\title{T}\n\n" + EVEN + "\n\n\\section{Acknowledgments}\n\n"
                    + EVEN + "\n")
            self.assertEqual(metrics.distribution_findings(text, root), [])


class AxisStatusTests(unittest.TestCase):
    def test_reference_without_a_classified_bucket_is_degraded(self):
        # only an `unknown` bucket: pooled CV is 0, the burstiness rule can
        # never fire, and the axis used to say `measured` (audit B7)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, buckets={"unknown": {"mean": 20.0, "stdev": 10.0}},
                          policy={"burstiness_ratio": 0.6})
            reference = metrics.load_reference(root)
            self.assertEqual((reference["cv"], reference["pooled_cv"]), ({}, 0.0))
            status = metrics.distribution_axis_status(root)
            self.assertEqual(status["status"], "degraded")
            self.assertIn("no classified section bucket", status["reason"])
            write_profile(root, buckets={"intro": {"mean": 20.0, "stdev": 10.0}},
                          policy={"burstiness_ratio": 0.6})
            self.assertEqual(metrics.distribution_axis_status(root)["status"], "measured")

    def test_missing_reference_or_policy(self):
        self.assertEqual(metrics.distribution_axis_status(None)["status"], "unmeasured")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, buckets={"intro": {"mean": 20.0, "stdev": 10.0}})
            self.assertEqual(metrics.distribution_axis_status(root)["status"], "degraded")
            self.assertEqual(metrics.load_policy(root), None)
            (root / "deai_policy.json").write_text(
                json.dumps({"distribution": {"a": 1}, "structure": {"b": 2}}),
                encoding="utf-8")
            self.assertEqual(metrics.load_policy(root), {"a": 1})
            self.assertEqual(metrics.load_policy(root, section="structure"), {"b": 2})


class CliContractTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = metrics.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_field_resolution_on_the_read_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            draft.write_text("\\section{Introduction}\n\n" + EVEN + "\n", encoding="utf-8")
            profiles = root / "profiles"
            profiles.mkdir()
            code, out, _err = self.run_main([str(draft), "--profile-root", str(profiles)])
            self.assertEqual((code, "unmeasured" in out), (0, True))
            # one field auto-resolves
            only = profiles / "only"
            only.mkdir()
            write_profile(only, buckets={"intro": {"mean": 20.0, "stdev": 10.0}},
                          policy={"burstiness_ratio": 0.6})
            code, out, _err = self.run_main([str(draft), "--profile-root", str(profiles)])
            self.assertEqual((code, "burstiness-low:intro" in out), (0, True))
            # several fields: a stderr note, no profile, exit 0
            (profiles / "other").mkdir()
            code, out, err = self.run_main([str(draft), "--profile-root", str(profiles)])
            self.assertEqual((code, "unmeasured" in out, "several field profiles" in err),
                             (0, True, True))
            code, _out, err = self.run_main([str(root / "missing.tex")])
            self.assertEqual((code, "file not found" in err), (2, True))


if __name__ == "__main__":
    unittest.main()
