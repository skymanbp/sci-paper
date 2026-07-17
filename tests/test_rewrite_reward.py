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


class LengthBudgetTests(unittest.TestCase):
    """SCIPAPER_STANDARD section 5.3: candidates must not outgrow the original."""

    def test_shorter_candidate_is_within_budget(self):
        original = "The estimator remains stable across all five smoothing scales."
        candidate = "The estimator is stable across the five scales."
        budget = rewrite_reward.length_budget(candidate, original)
        self.assertTrue(budget["within"])
        self.assertGreater(budget["condensation"], 0.0)

    def test_longer_candidate_breaks_budget(self):
        original = "The estimator is stable."
        candidate = ("The estimator is stable, which means that it does not "
                     "change when the configuration changes.")
        budget = rewrite_reward.length_budget(candidate, original)
        self.assertFalse(budget["within"])
        self.assertGreater(budget["delta_words"], 0)
        self.assertLess(budget["condensation"], 0.0)

    def test_comments_do_not_count_toward_the_budget(self):
        original = "The estimator is stable across scales."
        candidate = ("The estimator is stable across scales. "
                     "% long trailing source comment with many words in it")
        budget = rewrite_reward.length_budget(candidate, original)
        self.assertTrue(budget["within"], budget)


class AdvisoryReductionTests(unittest.TestCase):
    """Rank 7: the ranking term is L0 advisory reduction, not the dead
    specificity term (identically 1.0 for every eligible candidate)."""

    def test_l0_count_detects_targets(self):
        # em-dash and a Tier A word are L0 targets without any lexicon.
        self.assertEqual(rewrite_reward._l0_target_count("A plain clause here.", None), 0)
        self.assertGreaterEqual(
            rewrite_reward._l0_target_count("The result improves — clearly.", None), 1)
        self.assertGreaterEqual(
            rewrite_reward._l0_target_count("We delve into the estimator.", None), 1)

    def test_removing_a_target_scores_positive(self):
        # ref carries 1 target, candidate removes it -> positive reduction.
        value = rewrite_reward._advisory_reduction(ref_l0=1, cand_l0=0, fidelity=0.95)
        self.assertGreater(value, 0.0)
        self.assertAlmostEqual(value, 1.0)

    def test_adding_a_target_scores_negative(self):
        value = rewrite_reward._advisory_reduction(ref_l0=0, cand_l0=1, fidelity=0.95)
        self.assertLess(value, 0.0)

    def test_no_change_is_neutral_not_full_credit(self):
        # the old specificity was 1.0 here; the reduction term is 0.0.
        self.assertEqual(rewrite_reward._advisory_reduction(0, 0, 0.95), 0.0)
        self.assertEqual(rewrite_reward._advisory_reduction(2, 2, 0.95), 0.0)

    def test_fidelity_floor_blocks_positive_credit(self):
        # a low-fidelity candidate cannot buy improvement credit with mangled meaning.
        self.assertEqual(
            rewrite_reward._advisory_reduction(ref_l0=2, cand_l0=0, fidelity=0.1), 0.0)
        # but it is still penalized for adding targets.
        self.assertLess(
            rewrite_reward._advisory_reduction(ref_l0=0, cand_l0=2, fidelity=0.1), 0.0)

    def test_reduction_is_bounded(self):
        for ref_l0, cand_l0 in [(5, 0), (0, 5), (3, 1), (1, 9)]:
            value = rewrite_reward._advisory_reduction(ref_l0, cand_l0, 0.9)
            self.assertGreaterEqual(value, -1.0)
            self.assertLessEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main()
