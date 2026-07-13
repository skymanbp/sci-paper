from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import deai_docstructure as docstructure


REPEATED_PARAGRAPH = (
    "The estimator must preserve the measured signal under rotation. "
    "The covariance must retain the corresponding noise dependence under rotation. "
    "The likelihood must represent these two quantities without changing their units. "
    "These three requirements define the calculation used for every sample in this analysis."
)

SHORT_PARAGRAPH = (
    "A direct calculation fixes the scale. The result follows from the measured "
    "covariance and does not require a separate roadmap sentence. The remaining "
    "uncertainty comes from the finite sample rather than the estimator itself."
)

LONG_PARAGRAPH = (
    "Because the selection function couples angular position, source density, and "
    "measurement noise, we evaluate its contribution before fitting the population "
    "model; this ordering preserves the conditional structure of the likelihood, "
    "keeps the normalization explicit, and makes the later comparison with the null "
    "sample depend on a quantity that has already been defined."
)


def document(paragraphs: list[str]) -> str:
    sections = []
    for index, name in enumerate(("Introduction", "Methods", "Results")):
        first = paragraphs[(2 * index) % len(paragraphs)]
        second = paragraphs[(2 * index + 1) % len(paragraphs)]
        sections.append(f"\\section{{{name}}}\n\n{first}\n\n{second}")
    return "\n\n".join(sections) + "\n"


class DocumentStructureTests(unittest.TestCase):
    def test_repeated_shape_is_more_uniform_than_ragged_shape(self):
        repeated = docstructure.document_shape(document([REPEATED_PARAGRAPH]))
        ragged = docstructure.document_shape(document([
            REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
            SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
        ]))
        self.assertEqual(repeated["status"], "measured")
        self.assertEqual(ragged["status"], "measured")
        self.assertGreater(
            repeated["metrics"]["within_section_similarity"],
            ragged["metrics"]["within_section_similarity"],
        )

    def test_short_document_reports_insufficient_evidence(self):
        result = docstructure.document_shape(
            "\\section{Introduction}\n\n" + REPEATED_PARAGRAPH)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIn("at least 3 sections", result["reason"])

    def test_calibration_uses_complete_documents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            variants = [
                [REPEATED_PARAGRAPH, SHORT_PARAGRAPH],
                [SHORT_PARAGRAPH, LONG_PARAGRAPH],
                [LONG_PARAGRAPH, REPEATED_PARAGRAPH],
            ]
            for index, paragraphs in enumerate(variants):
                path = root / f"human-{index}.tex"
                path.write_text(document(paragraphs), encoding="utf-8")
                sources.append(path)
            baseline = docstructure.calibrate(sources, root, strong_percentile=0.8)
            self.assertEqual(baseline["n_documents"], 3)
            self.assertEqual(len(baseline["documents"]), 3)
            self.assertTrue((root / docstructure.BASELINE_NAME).exists())
            for metric in docstructure.METRIC_NAMES:
                self.assertEqual(len(baseline["metrics"][metric]["values"]), 3)

    def test_document_shape_reports_cross_paragraph_dispersion(self):
        shape = docstructure.document_shape(document([
            REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
            SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
        ]))
        self.assertEqual(shape["status"], "measured")
        self.assertIn("dispersion", shape)
        # every model-free feature has a std dispersion entry
        for name in docstructure.DISPERSION_FEATURE_NAMES:
            self.assertIn(name, shape["dispersion"])
            self.assertIn(docstructure.DISPERSION_STAT, shape["dispersion"][name])

    def test_over_dispersed_document_flags_high_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Reference: consistently UNIFORM human stand-ins (narrow band).
            sources = []
            for index in range(4):
                path = root / f"human-{index}.tex"
                path.write_text(document([REPEATED_PARAGRAPH]), encoding="utf-8")
                sources.append(path)
            docstructure.calibrate(sources, root, strong_percentile=0.9)
            # A wildly varied document departs the band on the HIGH side.
            ragged = docstructure.document_findings(document([
                REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
            ]), root)
            self.assertTrue(
                [f for f in ragged
                 if f["rule"].startswith("document-overdispersion:")],
                "an over-dispersed document should flag the high tail")

    def test_over_uniform_document_is_flagged_but_varied_is_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Human reference: ragged documents that mix paragraph shapes.
            sources = []
            for index in range(4):
                path = root / f"human-{index}.tex"
                path.write_text(document([
                    REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                    SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
                ]), encoding="utf-8")
                sources.append(path)
            docstructure.calibrate(sources, root, strong_percentile=0.9)
            # An over-uniform document (every paragraph identical) must draw at
            # least one over-uniformity finding; the varied reference shape must not.
            uniform = docstructure.document_findings(
                document([REPEATED_PARAGRAPH]), root)
            uniformity_hits = [f for f in uniform
                               if f["rule"].startswith("document-uniformity:")]
            self.assertTrue(uniformity_hits, "over-uniform document should flag")
            varied = docstructure.document_findings(document([
                REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
            ]), root)
            self.assertFalse(
                [f for f in varied if f["rule"].startswith("document-uniformity:")],
                "a document matching the human reference shape should not flag")


if __name__ == "__main__":
    unittest.main()
