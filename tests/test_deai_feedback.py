from __future__ import annotations

import sys
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_feedback as feedback


class FeedbackContractTests(unittest.TestCase):
    def finding(self, *, layer: str, section: str, line: int,
                distance: float = 0.2, strong: bool = True):
        return feedback.make_finding(
            kind="advisory", layer=layer, rule=f"test-{layer}-{line}",
            scope="paragraph", message="measured feedback",
            action="revise without changing the claim", detector="test",
            path="paper.tex", line=line, section=section,
            observed={"value": 1.0},
            reference={"value": 0.5, "provenance": "fixture"},
            normalized_distance=distance,
            confidence={"value": 0.9, "basis": "fixture"},
            strength="strong" if strong else "ordinary",
            strong_advisory=strong,
        )

    def test_structure_ranks_above_distribution(self):
        method_l1 = self.finding(layer="L1", section="Methods", line=20,
                                 distance=2.0)
        intro_l2 = self.finding(layer="L2", section="Introduction", line=5,
                                distance=0.1)
        ranked = feedback.rank_findings([method_l1, intro_l2])
        self.assertEqual(ranked[0]["layer"], "L2")
        self.assertEqual(ranked[0]["location"]["section"], "Introduction")

    def test_top_does_not_change_summary(self):
        findings = [self.finding(layer="L2", section="Introduction", line=i)
                    for i in range(1, 4)]
        report = feedback.build_report(
            path="paper.tex", findings=findings,
            axes=[feedback.axis_status("L2", "measured")], top=1)
        self.assertEqual(report["emitted_findings"], 1)
        self.assertEqual(report["total_findings"], 3)
        self.assertEqual(report["summary"]["total_findings"], 3)
        self.assertTrue(report["truncated"])

    def test_schema_contains_operational_fields(self):
        finding = self.finding(layer="L2", section="Introduction", line=7)
        required = {
            "finding_id", "kind", "layer", "scope", "location", "observed",
            "reference", "normalized_distance", "confidence", "priority",
            "recommended_action", "detector", "measurement_status",
            "disposition", "before_after",
        }
        self.assertTrue(required.issubset(finding))
        self.assertEqual(finding["disposition"], "pending")
        self.assertEqual(feedback.SCHEMA_VERSION, "sci-paper.feedback.v1")

    def test_tuple_adapter_projects_structured_finding(self):
        finding = self.finding(layer="L1", section="Results", line=11)
        self.assertEqual(
            feedback.tuple_hits([finding]),
            [(11, finding["rule"], finding["message"])],
        )


class CalibrationUnitTests(unittest.TestCase):
    """Rank 8: paragraph-unit findings are structurally capped in confidence."""

    def make(self, *, calibration_unit=None, value=0.9):
        return feedback.make_finding(
            kind="advisory", layer="L1", rule="cu-test", scope="paragraph",
            message="m", action="a", detector="test", path="p.tex", line=3,
            confidence={"value": value, "basis": "fixture"},
            calibration_unit=calibration_unit)

    def test_default_none_preserves_confidence(self):
        f = self.make()
        self.assertIsNone(f["calibration_unit"])
        self.assertEqual(f["confidence"]["value"], 0.9)

    def test_paragraph_unit_caps_high_confidence(self):
        f = self.make(calibration_unit="paragraph", value=0.9)
        self.assertEqual(f["calibration_unit"], "paragraph")
        self.assertEqual(f["confidence"]["value"], feedback.PARAGRAPH_CONFIDENCE_CAP)
        self.assertIn("capped", f["confidence"]["basis"])

    def test_paragraph_unit_leaves_low_confidence(self):
        f = self.make(calibration_unit="paragraph", value=0.3)
        self.assertEqual(f["confidence"]["value"], 0.3)
        self.assertNotIn("capped", f["confidence"]["basis"])

    def test_document_unit_does_not_cap(self):
        f = self.make(calibration_unit="document", value=0.9)
        self.assertEqual(f["confidence"]["value"], 0.9)

    def test_sentence_unit_caps_like_paragraph(self):
        # The collocation axis calibrates per sentence: a unit smaller than a
        # paragraph, so the same structural cap applies.
        f = self.make(calibration_unit="sentence", value=0.9)
        self.assertEqual(f["confidence"]["value"], feedback.PARAGRAPH_CONFIDENCE_CAP)

    def test_unknown_unit_raises(self):
        with self.assertRaises(ValueError):
            self.make(calibration_unit="clause")


if __name__ == "__main__":
    unittest.main()
