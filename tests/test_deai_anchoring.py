from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

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

    def test_section_classification(self):
        self.assertEqual(anchoring.classify_section("Introduction"), "intro")
        self.assertEqual(anchoring.classify_section("Data and Methods"),
                         "methods")
        self.assertEqual(anchoring.classify_section("Results"), "results")
        self.assertEqual(anchoring.classify_section("Summary and outlook"),
                         "conclusions")
        self.assertEqual(anchoring.classify_section("Lensing formalism"),
                         "other")

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

    def test_axis_degrades_honestly(self):
        status = anchoring.anchoring_axis_status("too short", None)
        self.assertEqual(status["status"], "unmeasured")


if __name__ == "__main__":
    unittest.main()
