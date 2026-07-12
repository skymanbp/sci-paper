from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import rewrite_reward


class RewriteFidelityTests(unittest.TestCase):
    def test_preserves_scientific_invariants(self):
        reference = (
            r"the manuscript increases AUC to 0.91 at $z=0.5$ for 43 clusters "
            r"\citep{Smith2024}; the uncertainty is not below 2 km/s."
        )
        candidate = (
            r"For the 43 clusters, the manuscript increases AUC to 0.91 at $z=0.5$ "
            r"\citep{Smith2024}. The uncertainty is not below 2 km/s."
        )
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"], result["missing"])

    def test_dropped_number_is_ineligible(self):
        reference = "The sample contains 43 clusters and reaches AUC 0.91."
        candidate = "The sample reaches AUC 0.91."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("43", result["missing"]["numbers"])

    def test_reversed_comparison_is_ineligible(self):
        reference = "The calibrated score is higher than the null score."
        candidate = "The calibrated score is lower than the null score."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("higher", result["missing"]["comparison_direction"])

    def test_dropped_citation_is_ineligible(self):
        reference = r"The estimator follows the published definition \cite{Doe2025}."
        candidate = "The estimator follows the published definition."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("Doe2025", result["missing"]["citations"])

    def test_added_negation_is_ineligible(self):
        reference = "The effect is significant."
        candidate = "The effect is not significant."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("not", result["invented"]["negation"])

    def test_added_causal_marker_is_ineligible(self):
        reference = "The bias shrinks. The sample grows."
        candidate = "The bias shrinks because the sample grows."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("because", result["invented"]["causal_direction"])

    def test_added_number_is_ineligible_invention(self):
        reference = "The catalog covers the survey clusters."
        candidate = "The catalog covers the 512 survey clusters."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("512", result["invented"]["numbers"])

    def test_dropped_semantic_macro_is_ineligible(self):
        reference = r"an aperture-mass family of \Nconfig{} configurations"
        candidate = "an aperture-mass family of configurations"
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("Nconfig", result["missing"]["latex_macros"])

    def test_formatting_macros_are_not_protected(self):
        reference = r"The estimator \emph{clearly} improves with 43 clusters."
        candidate = "The estimator improves with 43 clusters."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))


if __name__ == "__main__":
    unittest.main()
