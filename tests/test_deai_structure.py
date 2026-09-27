from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_structure as structure


ANTITHESIS_HEAVY = (
    "The error budget is measured rather than assumed, and every correction "
    "is taken from simulations rather than from a tuned cutoff. The catalog "
    "reports failed fits instead of dropping them, so the reader sees how "
    "often the shape measurement breaks. Each claim is stated with its "
    "reason attached, and the selection was fixed before the shear was "
    "measured."
)

REVERSAL_BEAT = (
    "One might expect that doubling the exposure time would double the "
    "number of usable source galaxies behind each cluster. "
    "It would not. The added galaxies are faint and small, so most of them "
    "fail the size cut applied before the shapes are measured, and the "
    "source density rises by far less than the exposure time does."
)

PLAIN_PROSE = (
    "The aperture-mass map is evaluated on a regular grid across each "
    "field. Each smoothing scale is matched to the angular size of a typical "
    "cluster at the median lens redshift, and the resulting maps are combined "
    "after their noise levels are equalised. Peaks are counted on the "
    "combined map before any cosmological model is compared with the counts, "
    "which keeps the measurement independent of the model."
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
        text = ("This study asks whether the filter response can separate the "
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
        text = ("What matters here is the noise of the map. "
                "The remaining sentences describe the aperture mass filter.")
        values = structure.paragraph_structure(text)
        self.assertEqual(values["wh_cleft_count"], 1)
        self.assertIn("wh-cleft", values["auxiliary_templates"])

    def test_a_plain_wh_question_word_is_not_a_cleft(self):
        text = ("How the filter responds depends on the smoothing scale, so "
                "the scale is fixed before any peak is counted.")
        values = structure.paragraph_structure(text)
        self.assertEqual(values["wh_cleft_count"], 0)

    def test_the_gap_below_a_heading_does_not_decide_a_family(self):
        # One newline or two between the heading and the paragraph: the same
        # paragraph. Left in place the heading fused with the opener (`Methods
        # What matters here is`) and the family went unreported.
        paragraph = ("What matters here is the noise of the map, which the aperture "
                     "mass filter carries into every peak count and into every "
                     "scale of the smoothing family that we adopt in this section.")
        counts = []
        for gap in ("\n", "\n\n"):
            findings = structure.structure_findings("\\section{Methods}" + gap + paragraph, None)
            counts.append(sum(f["observed"]["wh_cleft_count"] for f in findings
                              if f["rule"].startswith("structure-auxiliary")))
        self.assertEqual(counts, [1, 1])

    def test_modifier_stack_detected(self):
        stacks = structure.modifier_stacks(
            "We adopt a per-band smoothed star-galaxy classifier for every exposure.")
        self.assertEqual(stacks, ["per-band smoothed star-galaxy classifier"])
        stacks = structure.modifier_stacks(
            "The non-weighted 200-image stack fails the test.")
        self.assertEqual(stacks, ["non-weighted 200-image stack"])

    def test_ordinary_compound_noun_phrases_are_not_stacks(self):
        self.assertEqual(structure.modifier_stacks(
            "The weak-lensing mass map is smoothed, and the [math] peak is kept."), [])
        self.assertEqual(structure.modifier_stacks(
            "We use 200 maps of the aperture-mass filter."), [])

    def test_advisor_families_stay_out_of_template_score(self):
        text = ("This study asks whether a per-band smoothed star-galaxy classifier "
                "suffices. What matters here is the noise of the map.")
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


class CalibrateTests(unittest.TestCase):
    """`calibrate` turns the exemplar bank into per-bucket fractions (audit B30)."""

    def test_a_tiny_bank_yields_per_bucket_fractions(self):
        rows = [{"section": "method", "text": TEMPLATED},
                {"section": "method", "text": PLAIN_PROSE},
                {"section": "results", "text": ANTITHESIS_HEAVY},
                {"section": "results", "text": "Too short to be a reference paragraph."}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "exemplar_paragraphs.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            baseline = structure.calibrate(root)
            written = json.loads((root / "structure_baseline.json").read_text(encoding="utf-8"))
            # the detector reads the written reference back for its bucket
            finding, = [f for f in structure.structure_findings(
                "\\section{Methods}\n\n" + TEMPLATED, root)
                if f["rule"] == "structure-template:method"]
        self.assertEqual(written, baseline)
        # the paragraph under MIN_WORDS is not a reference observation
        self.assertEqual({bucket: entry["n"] for bucket, entry in baseline.items()},
                         {"method": 2, "results": 1})
        method, results = baseline["method"], baseline["results"]
        self.assertEqual((method["templated_frac"], method["tricolon_frac"],
                          method["modal_frac"], method["auxiliary_frac"]), (0.5, 0.5, 0.5, 0.0))
        self.assertEqual((results["templated_frac"], results["auxiliary_frac"],
                          results["antithesis_cluster_frac"]), (0.0, 1.0, 1.0))
        self.assertEqual((finding["reference"]["templated_fraction"], finding["reference"]["n"],
                          finding["measurement_status"]), (0.5, 2, "degraded"))
        with tempfile.TemporaryDirectory() as temporary, self.assertRaises(SystemExit):
            structure.calibrate(Path(temporary))  # no bank: a stated failure


if __name__ == "__main__":
    unittest.main()
