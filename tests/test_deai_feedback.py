from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

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


if __name__ == "__main__":
    unittest.main()
