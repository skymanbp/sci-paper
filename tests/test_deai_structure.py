from __future__ import annotations

import json
import tempfile
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

    def test_the_gap_below_a_heading_does_not_decide_a_family(self):
        # One newline or two between the heading and the paragraph: the same
        # paragraph. Left in place the heading fused with the opener (`Methods
        # What it can conclude is`) and the family went unreported.
        paragraph = ("What it can conclude is limited by the noise of the map, "
                     "which the aperture mass filter carries into every peak count "
                     "and every configuration of the calibrated grid we adopt here.")
        counts = []
        for gap in ("\n", "\n\n"):
            findings = structure.structure_findings("\\section{Methods}" + gap + paragraph, None)
            counts.append(sum(f["observed"]["wh_cleft_count"] for f in findings
                              if f["rule"].startswith("structure-auxiliary")))
        self.assertEqual(counts, [1, 1])

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


TEMPLATED = (
    "The estimator must preserve the measured signal under rotation. "
    "The covariance must retain the corresponding noise dependence under rotation. "
    "The likelihood must represent these two quantities without changing their units. "
    "These three requirements define the calculation used for every sample in this analysis."
)


def write_profile(root: Path, *, baseline: dict | None, policy: dict | None) -> None:
    if baseline is not None:
        (root / "structure_baseline.json").write_text(json.dumps(baseline),
                                                      encoding="utf-8")
    if policy is not None:
        (root / "deai_policy.json").write_text(json.dumps({"structure": policy}),
                                               encoding="utf-8")


class TricolonWrapTests(unittest.TestCase):
    """The wrap-up beat opens a sentence with "These N <nouns>" and closes it
    with a summing verb (audit 2026-09-27, B15)."""

    def test_wrap_up_sentence_matches(self):
        for sentence in ("These three requirements define the calculation.",
                         "These two simple facts together fix the scale.",
                         "These four steps constitute the pipeline."):
            self.assertTrue(structure.RE_TRICOLON_WRAP.match(sentence), sentence)

    def test_an_object_noun_phrase_is_not_a_wrap_up(self):
        for sentence in ("The likelihood must represent these two quantities "
                         "without changing their units.",
                         "these three samples were observed at dawn.",
                         "We compare these two estimators below."):
            self.assertIsNone(structure.RE_TRICOLON_WRAP.match(sentence), sentence)
        values = structure.paragraph_structure(
            "We represent these two quantities here. Nothing else follows in "
            "this paragraph of ordinary prose about the shear estimator.")
        self.assertFalse(values["tricolon_wrap"])
        self.assertTrue(structure.paragraph_structure(TEMPLATED)["tricolon_wrap"])


class StrongStatusTests(unittest.TestCase):
    """A template finding is `measured` only against a reference for its own
    bucket plus a policy; `degraded` with a baseline that lacks the bucket;
    `unmeasured` without a baseline (audit 2026-09-27, B6)."""

    BASELINE = {"method": {"n": 25, "templated_frac": 0.02, "auxiliary_frac": 0.4}}
    POLICY = {"rare_template_fraction": 0.05}

    def template_finding(self, text: str, profile: Path | None) -> dict:
        findings = [f for f in structure.structure_findings(text, profile)
                    if f["rule"].startswith("structure-template:")]
        self.assertEqual(len(findings), 1)
        return findings[0]

    def test_measured_and_strong_only_with_bucket_reference_and_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, baseline=self.BASELINE, policy=self.POLICY)
            finding = self.template_finding("\\section{Methods}\n\n" + TEMPLATED, root)
            self.assertEqual((finding["measurement_status"], finding["strength"]),
                             ("measured", "strong"))
            self.assertIn("reference method fraction 2.0%", finding["message"])
            # a bucket the baseline does not hold: degraded, never strong, and
            # the message quotes no fraction
            unknown = self.template_finding(
                "\\section{Weak gravitational lensing}\n\n" + TEMPLATED, root)
            self.assertEqual((unknown["measurement_status"], unknown["strength"]),
                             ("degraded", "ordinary"))
            self.assertEqual(unknown["reference"]["templated_fraction"], None)
            self.assertNotIn("fraction", unknown["message"])

    def test_baseline_without_policy_is_degraded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, baseline=self.BASELINE, policy=None)
            finding = self.template_finding("\\section{Methods}\n\n" + TEMPLATED, root)
            self.assertEqual((finding["measurement_status"], finding["strength"]),
                             ("degraded", "ordinary"))

    def test_no_profile_is_unmeasured(self):
        finding = self.template_finding("\\section{Methods}\n\n" + TEMPLATED, None)
        self.assertEqual((finding["measurement_status"], finding["strength"]),
                         ("unmeasured", "ordinary"))

    def test_load_policy_reads_the_structure_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, baseline=None, policy=self.POLICY)
            self.assertEqual(structure.load_policy(root), self.POLICY)
            self.assertIsNone(structure.load_policy(None))


class AuxiliaryWordingTests(unittest.TestCase):
    """The auxiliary message states the reference fraction and calls a figure
    rare only below the policy gate (audit 2026-09-27, B14)."""

    def auxiliary_message(self, profile: Path | None) -> str:
        findings = [f for f in structure.structure_findings(
            "\\section{Methods}\n\n" + ANTITHESIS_HEAVY, profile)
            if f["rule"].startswith("structure-auxiliary:")]
        self.assertEqual(len(findings), 1)
        return findings[0]["message"]

    def test_common_figure_is_not_called_rare(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, baseline={"method": {"n": 120, "auxiliary_frac": 0.4}},
                          policy={"rare_template_fraction": 0.05})
            message = self.auxiliary_message(root)
            self.assertNotIn("rare", message)
            self.assertIn("reference method fraction 40.0% (n=120)", message)

    def test_rare_figure_is_called_rare_with_the_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_profile(root, baseline={"method": {"n": 120, "auxiliary_frac": 0.01}},
                          policy={"rare_template_fraction": 0.05})
            message = self.auxiliary_message(root)
            self.assertIn("rare in the field reference (method fraction 1.0% <= 5.0%, n=120)",
                          message)

    def test_no_reference_quotes_no_fraction(self):
        message = self.auxiliary_message(None)
        self.assertNotIn("rare", message)
        self.assertNotIn("fraction", message)


if __name__ == "__main__":
    unittest.main()
