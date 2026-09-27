from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_anchoring as anchoring

ANCHORED = (
    "The shear bias is 3.2 per cent at scales below 10 arcmin. "
    "This matches the calibration of \\cite{Smith2020} within errors. "
    "Equation $\\gamma_t = \\Delta\\Sigma / \\Sigma_c$ defines the estimator. "
    "Compared to the fiducial model, the residuals shrink by half. "
    "Figure~\\ref{fig:bias} shows the full scale dependence."
)

UNANCHORED = (
    "The method demonstrates strong performance across the sample. "
    "Results are broadly consistent with expectations from theory. "
    "This approach provides valuable insights into the underlying physics. "
    "The framework is flexible and applies to many related problems. "
    "Overall the analysis supports the general picture described above."
)


def document(section_bodies: dict[str, str]) -> str:
    parts = [f"\\section{{{title}}}\n\n{body}"
             for title, body in section_bodies.items()]
    return "\n\n".join(parts) + "\n"


def write_baseline(root: Path, classes: dict[str, tuple[list[float], int]]) -> None:
    """A hand-written baseline: {class: (values, n)}."""
    (root / anchoring.BASELINE_NAME).write_text(json.dumps({
        "schema": "sci-paper.anchoring-baseline.v1", "alpha": 0.05,
        "n_documents": max(n for _v, n in classes.values()),
        "classes": {cls: {"values": values, "n": n, "median": values[len(values) // 2]}
                    for cls, (values, n) in classes.items()}}), encoding="utf-8")


class AnchoringTests(unittest.TestCase):
    def test_sentence_anchor_detection(self):
        self.assertTrue(anchoring.sentence_is_anchored(
            "The bias is 3.2 per cent."))
        self.assertTrue(anchoring.sentence_is_anchored(
            "This was shown by \\citep{Smith2020}."))
        self.assertTrue(anchoring.sentence_is_anchored(
            "See Figure~\\ref{fig:bias} for details."))
        self.assertTrue(anchoring.sentence_is_anchored(
            "The estimator $\\gamma_t$ is unbiased."))
        self.assertTrue(anchoring.sentence_is_anchored(
            "Errors are smaller than the fiducial case."))
        self.assertFalse(anchoring.sentence_is_anchored(
            "The method demonstrates strong performance."))
        # digits inside a citation key must not count as a number anchor
        self.assertFalse(anchoring.sentence_is_anchored(
            "This was argued by \\cite{Smith2020} convincingly."
            .replace("\\cite{Smith2020}", "")))

    def test_the_class_is_the_shared_bucket(self):
        # One heading table: `Lensing formalism` names a method, a topic
        # subsection inherits Methods, and `Comparison with simulations` is
        # discussion -- the module's own table said other, other, methods.
        result = anchoring.document_anchoring(
            "\\section{Lensing formalism}\n" + ANCHORED + "\n"
            "\\section{Methods}\n\\subsection{Weak lensing}\n" + ANCHORED + "\n"
            "\\section{Comparison with simulations}\n" + ANCHORED + "\n"
            "\\section{Summary and outlook}\n" + ANCHORED + "\n")
        self.assertEqual([row["class"] for row in result["sections"]],
                         ["methods", "methods", "discussion", "conclusions"])
        self.assertEqual(anchoring.section_class("data"), "methods")
        self.assertEqual(anchoring.section_class("unknown"), "other")

    def test_unanchored_results_flag_and_anchored_do_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # human reference: well-anchored papers. 100 references so the
            # conformal resolution 1/(n+1) stays below the Bonferroni share
            # alpha/3 (with only 30, min p = 0.032 > 0.05/3 and nothing can
            # ever flag - the production corpus has 315-512 per class).
            sources = []
            for index in range(100):
                path = root / f"human-{index}.tex"
                path.write_text(document({
                    "Introduction": ANCHORED, "Methods": ANCHORED,
                    "Results": ANCHORED}), encoding="utf-8")
                sources.append(path)
            baseline = anchoring.calibrate(sources, root)
            self.assertIn("results", baseline["classes"])
            self.assertEqual(baseline["underpowered_classes"], {})
            flagged = anchoring.anchoring_findings(document({
                "Introduction": ANCHORED, "Methods": ANCHORED,
                "Results": UNANCHORED}), root)
            self.assertTrue(
                [f for f in flagged if f["rule"] == "claim-anchoring:results"],
                "a fully unanchored Results section must flag")
            clean = anchoring.anchoring_findings(document({
                "Introduction": ANCHORED, "Methods": ANCHORED,
                "Results": ANCHORED}), root)
            self.assertFalse(clean,
                             "an anchored document must not flag any class")
            self.assertEqual(anchoring.anchoring_axis_status(
                document({"Results": UNANCHORED}), root)["status"], "measured")

    def test_axis_degrades_honestly(self):
        status = anchoring.anchoring_axis_status("too short", None)
        self.assertEqual(status["status"], "unmeasured")


class PowerFloorTests(unittest.TestCase):
    """A conformal p is never below 1/(n+1); a class whose n cannot reach its
    Bonferroni share alpha/k cannot flag and must not pass as `measured`
    (audit 2026-09-27, B5)."""

    def test_min_documents_for_share(self):
        # n + 1 >= k / alpha: k=1 -> 19, k=2 -> 39, k=3 -> 59
        self.assertEqual(anchoring.min_class_documents_for_share(0.05, 1), 19)
        self.assertEqual(anchoring.min_class_documents_for_share(0.05, 2), 39)
        self.assertEqual(anchoring.min_class_documents_for_share(0.05, 3), 59)

    def test_underpowered_class_is_skipped_and_axis_degraded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # results: n = 100 (1/101 < 0.025); intro: n = 30 (1/31 = 0.032 > 0.025)
            write_baseline(root, {"results": ([0.8] * 100, 100),
                                  "intro": ([0.5] * 30, 30)})
            text = document({"Introduction": UNANCHORED, "Results": UNANCHORED})
            tests = anchoring.class_tests(anchoring.load_baseline(root),
                                          anchoring.document_anchoring(text))
            self.assertEqual(tests["underpowered"], ["intro"])
            self.assertEqual(tests["testable"], ["results"])
            self.assertAlmostEqual(tests["class_alpha"], 0.025)
            findings = anchoring.anchoring_findings(text, root)
            self.assertEqual([f["rule"] for f in findings],
                             ["claim-anchoring:results"])
            # the share is not re-spread: still alpha / 2
            self.assertAlmostEqual(findings[0]["reference"]["alpha_class"], 0.025)
            status = anchoring.anchoring_axis_status(text, root)
            self.assertEqual(status["status"], "degraded")
            self.assertIn("intro", status["reason"])
            self.assertIn("1/(n+1)", status["reason"])
            # the same intro class alone in a document (k = 1, share 0.05) is
            # testable: 1/31 = 0.032 <= 0.05
            alone = document({"Introduction": UNANCHORED})
            self.assertEqual(anchoring.anchoring_axis_status(alone, root)["status"],
                             "measured")
            self.assertEqual([f["rule"] for f in anchoring.anchoring_findings(alone, root)],
                             ["claim-anchoring:intro"])

    def test_no_calibrated_class_is_unmeasured(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_baseline(root, {"results": ([0.8] * 100, 100)})
            status = anchoring.anchoring_axis_status(
                document({"Introduction": UNANCHORED}), root)
            self.assertEqual(status["status"], "unmeasured")
            self.assertIn("no measured section class", status["reason"])

    def test_calibration_records_underpowered_classes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            for index in range(anchoring.MIN_CLASS_DOCUMENTS):
                path = root / f"human-{index}.tex"
                path.write_text(document({
                    "Introduction": ANCHORED, "Methods": ANCHORED,
                    "Results": ANCHORED}), encoding="utf-8")
                sources.append(path)
            baseline = anchoring.calibrate(sources, root)
            # three classes of 30: the share alpha/3 needs 59 per class
            self.assertEqual(baseline["min_class_documents_for_share"], 59)
            self.assertEqual(baseline["underpowered_classes"],
                             {"intro": 30, "methods": 30, "results": 30})
            text = document({"Introduction": ANCHORED, "Methods": ANCHORED,
                             "Results": UNANCHORED})
            self.assertEqual(anchoring.anchoring_axis_status(text, root)["status"],
                             "degraded")
            self.assertEqual(anchoring.anchoring_findings(text, root), [])


class SweepTests(unittest.TestCase):
    """The sentence scan runs on section bodies with headings, floats and the
    bibliography blanked, and `skip` units dropped (audit 2026-09-27, B13)."""

    def test_heading_does_not_anchor_the_first_sentence(self):
        # No blank line after the heading: the raw scan fused "Results at 3
        # arcmin" with the first sentence, and the digit anchored it.
        result = anchoring.document_anchoring(
            "\\section{Results at 3 arcmin}\n" + UNANCHORED + "\n")
        self.assertEqual(result["classes"], {"results": 0.0})

    def test_bibliography_and_floats_do_not_anchor_the_last_sentence(self):
        text = ("\\section{Conclusions}\n\n" + UNANCHORED + "\n"
                "\\begin{figure}\n\\caption{Bias at 3 arcmin, see 2020 data}\n"
                "\\end{figure}\n"
                "\\begin{thebibliography}{99}\n"
                "\\bibitem{a} Smith, J. 2020, ApJ, 900, 1\n"
                "\\bibitem{b} Jones, K. 2021, MNRAS, 500, 2\n"
                "\\end{thebibliography}\n\\bibliography{refs}\n")
        result = anchoring.document_anchoring(text)
        self.assertEqual(result["classes"], {"conclusions": 0.0})
        self.assertEqual(result["sections"][0]["n_sentences"], 5)

    def test_skip_units_and_preamble_are_not_measured(self):
        text = ("\\title{A 2020 paper}\n\n" + UNANCHORED + "\n\n"
                + document({"Results": UNANCHORED, "Acknowledgments": ANCHORED,
                            "Appendix A": ANCHORED}))
        result = anchoring.document_anchoring(text)
        self.assertEqual([row["label"] for row in result["sections"]], ["Results"])
        self.assertEqual(result["classes"], {"results": 0.0})


class CliContractTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = anchoring.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_read_path_without_a_field_is_unmeasured_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            draft.write_text(document({"Results": UNANCHORED}), encoding="utf-8")
            empty = root / "profiles"
            empty.mkdir()
            code, out, _err = self.run_main([str(draft), "--profile-root", str(empty)])
            self.assertEqual(code, 0)
            self.assertIn("unmeasured", out)
            code, _out, err = self.run_main([str(root / "missing.tex"),
                                             "--profile-root", str(empty)])
            self.assertEqual((code, "file not found" in err), (2, True))

    def test_calibrate_needs_an_existing_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "corpus"
            corpus.mkdir()
            empty = root / "profiles"
            empty.mkdir()
            code, _out, err = self.run_main(
                ["--calibrate", "--corpus-dir", str(corpus), "--profile-root", str(empty)])
            self.assertEqual(code, 2)
            self.assertIn("No field profiles", err)


if __name__ == "__main__":
    unittest.main()
