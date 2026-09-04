from __future__ import annotations

import sys
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_structure as structure


ANTITHESIS_HEAVY = (
    "The error budget is measured rather than assumed, and every threshold "
    "derives from injections rather than from a tuned cutoff. The detector "
    "reports negatives instead of burying them, so the reader sees the "
    "boundary the grid quantifies. Each claim is stated with its reason "
    "attached, and the pipeline was frozen before the labeled sample was "
    "consumed at scoring time."
)

REVERSAL_BEAT = (
    "One might expect that raising the minimum configuration support would "
    "cheaply remove the residual noise detections from the shortlist. "
    "It would not. The support distribution of injected structure overlaps "
    "the noise support distribution across the calibrated range, so any cut "
    "strong enough to matter removes real detections at the same rate and "
    "leaves the purity of the final catalog unchanged."
)

PLAIN_PROSE = (
    "The aperture-mass map is evaluated on a regular grid in catalog "
    "coordinates. Each configuration pairs a filter scale with a truncation "
    "radius, and the resulting family covers the range of subhalo sizes the "
    "injection grid samples. Peaks are aggregated across configurations "
    "before any ranking statistic is computed, which keeps the candidate "
    "list independent of any single filter choice."
)


class AuxiliaryFamilyTests(unittest.TestCase):
    def test_antithesis_cluster_detected(self):
        values = structure.paragraph_structure(ANTITHESIS_HEAVY)
        self.assertGreaterEqual(values["antithesis_count"],
                                structure.ANTITHESIS_CLUSTER)
        self.assertIn("antithesis-cluster", values["auxiliary_templates"])

    def test_short_reversal_detected(self):
        values = structure.paragraph_structure(REVERSAL_BEAT)
        self.assertTrue(values["reversal_beat"])
        self.assertIn("short-reversal", values["auxiliary_templates"])

    def test_plain_prose_clean(self):
        values = structure.paragraph_structure(PLAIN_PROSE)
        self.assertEqual(values["auxiliary_templates"], [])
        self.assertEqual(values["antithesis_count"], 0)
        self.assertFalse(values["reversal_beat"])

    def test_single_antithesis_below_cluster_threshold(self):
        one = ("The positions are anchored to measured mass peaks rather "
               "than to any geometric property of the map, and the frame "
               "is carried through every later stage of the pipeline so "
               "that the reported coordinates match the catalog exactly.")
        values = structure.paragraph_structure(one)
        self.assertEqual(values["antithesis_count"], 1)
        self.assertNotIn("antithesis-cluster", values["auxiliary_templates"])

    def test_template_score_excludes_auxiliary(self):
        values = structure.paragraph_structure(ANTITHESIS_HEAVY)
        self.assertEqual(values["template_score"], len(values["templates"]))
        self.assertNotIn("antithesis-cluster", values["templates"])

    def test_paper_as_agent_detected(self):
        text = ("This Letter asks whether the filter response can separate the "
                "two populations at the depth of the survey.")
        values = structure.paragraph_structure(text)
        self.assertEqual(values["paper_agent_count"], 1)
        self.assertIn("paper-agent", values["auxiliary_templates"])

    def test_paper_that_merely_presents_is_not_an_agent(self):
        # "This paper presents" is the field's own convention, not a mind.
        text = ("This paper presents the filter response measured on the "
                "shear catalog around each cluster in the survey.")
        values = structure.paragraph_structure(text)
        self.assertEqual(values["paper_agent_count"], 0)

    def test_wh_cleft_detected(self):
        text = ("What it can conclude is limited by the noise of the map. "
                "The remaining sentences describe the aperture mass filter.")
        values = structure.paragraph_structure(text)
        self.assertEqual(values["wh_cleft_count"], 1)
        self.assertIn("wh-cleft", values["auxiliary_templates"])

    def test_a_plain_wh_question_word_is_not_a_cleft(self):
        text = ("How the filter responds depends on the truncation radius, so "
                "the radius is fixed before any peak is counted.")
        values = structure.paragraph_structure(text)
        self.assertEqual(values["wh_cleft_count"], 0)

    def test_modifier_stack_detected(self):
        stacks = structure.modifier_stacks(
            "We adopt a per-map empirical B-mode null for every configuration.")
        self.assertEqual(stacks, ["per-map empirical B-mode null"])
        stacks = structure.modifier_stacks(
            "The non-compensated 500-configuration subfamily fails the test.")
        self.assertEqual(stacks, ["non-compensated 500-configuration subfamily"])

    def test_ordinary_compound_noun_phrases_are_not_stacks(self):
        self.assertEqual(structure.modifier_stacks(
            "The weak-lensing mass map is smoothed, and the [math] peak is kept."), [])
        self.assertEqual(structure.modifier_stacks(
            "We use 500 configurations of the aperture-mass filter."), [])

    def test_advisor_families_stay_out_of_template_score(self):
        text = ("This Letter asks whether a per-map empirical B-mode null holds. "
                "What it can conclude is limited by the noise of the map.")
        values = structure.paragraph_structure(text)
        self.assertEqual(values["template_score"], 0)
        for family in ("paper-agent", "wh-cleft", "modifier-stack"):
            self.assertIn(family, values["auxiliary_templates"])

    def test_findings_emit_auxiliary_rule(self):
        text = "\\section{Methods}\n\n" + ANTITHESIS_HEAVY + "\n"
        findings = structure.structure_findings(text, None)
        rules = {finding["rule"] for finding in findings}
        self.assertIn("structure-auxiliary:method", rules)
        for finding in findings:
            if finding["rule"].startswith("structure-auxiliary"):
                self.assertEqual(finding["kind"], "advisory")
                self.assertFalse(finding.get("strong_advisory"))


if __name__ == "__main__":
    unittest.main()
