from __future__ import annotations

import sys
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

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


class InvariantTokenizationTests(unittest.TestCase):
    """Punctuation and neighbouring prose are not protected invariants.

    Both regexes used to absorb the character after the quantity: `\\d[\\d,]*`
    kept the comma that separates list items, and the unit's `\\s*` separator
    let any following word become a "unit". Together they hard-rejected
    faithful rewrites (`combined = -inf`) for changing punctuation or the word
    after a numeral.
    """

    def test_list_comma_is_not_part_of_the_number(self):
        self.assertEqual(
            rewrite_reward._numbers("We analyze 1200, 2400, and 4800 sources."),
            {"1200", "2400", "4800"})

    def test_thousands_separator_stays_inside_the_number(self):
        self.assertIn("1,234", rewrite_reward._numbers("A total of 1,234 halos."))

    def test_dropping_an_oxford_comma_stays_eligible(self):
        reference = "We analyze 1200, 2400, and 4800 sources."
        candidate = "We analyze 1200, 2400 and 4800 sources."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))

    def test_word_after_a_numeral_is_not_a_unit(self):
        self.assertEqual(rewrite_reward._units("in 2020 we found"), set())
        self.assertEqual(rewrite_reward._units("in 1200, 2400 sources"), set())

    def test_rewording_after_a_numeral_stays_eligible(self):
        reference = r"In 2020 we measured 5\,\mathrm{Mpc}."
        candidate = r"In 2020 the team measured 5\,\mathrm{Mpc}."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))

    def test_bound_units_are_still_protected(self):
        for text, expected in [
            (r"a 5\,\mathrm{Mpc} scale", r"\mathrm{mpc}"),
            ("a 5~km scale", "km"),
            ("a 5km scale", "km"),
            # `10\%` is the LaTeX-correct percent; an unescaped `%` starts a
            # comment and is stripped, as it is for every other category.
            (r"a 10\% increase", r"\%"),
        ]:
            with self.subTest(text=text):
                self.assertIn(expected, rewrite_reward._units(text))

    def test_changed_unit_is_still_ineligible(self):
        reference = r"The scale is 5\,\mathrm{Mpc}."
        candidate = r"The scale is 5\,\mathrm{kpc}."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn(r"\mathrm{mpc}", result["missing"]["units"])

    def test_changed_number_is_still_ineligible(self):
        result = rewrite_reward.fidelity_eligibility("We find 4900 sources.",
                                                     "We find 4800 sources.")
        self.assertFalse(result["eligible"])
        self.assertIn("4800", result["missing"]["numbers"])


class DisplayMathFidelityTests(unittest.TestCase):
    """Numbers inside a displayed equation are protected.

    Both named LaTeX projections drop `\\begin{equation}` bodies by design, so
    every category computed from them was blind to display math: a value
    silently changed inside a displayed equation passed as fully faithful.
    """

    REFERENCE = (
        "The scaling is\n"
        "\\begin{equation}\n"
        "M = 4.2 \\times 10^{14} h^{-1} M_\\odot\n"
        "\\end{equation}\n"
        "for the stacked sample of 43 clusters."
    )

    def test_display_math_numbers_are_collected(self):
        numbers = rewrite_reward._numbers(self.REFERENCE)
        self.assertIn("4.2", numbers)
        self.assertIn("14", numbers)
        self.assertIn("43", numbers)

    def test_changed_value_inside_equation_is_ineligible(self):
        candidate = self.REFERENCE.replace("4.2", "5.7")
        result = rewrite_reward.fidelity_eligibility(candidate, self.REFERENCE)
        self.assertFalse(result["eligible"])
        self.assertIn("4.2", result["missing"]["numbers"])

    def test_changed_exponent_is_ineligible(self):
        candidate = self.REFERENCE.replace("10^{14}", "10^{15}")
        result = rewrite_reward.fidelity_eligibility(candidate, self.REFERENCE)
        self.assertFalse(result["eligible"])

    def test_reindenting_the_equation_stays_eligible(self):
        candidate = self.REFERENCE.replace("\\begin{equation}\nM", "\\begin{equation}\n    M")
        result = rewrite_reward.fidelity_eligibility(candidate, self.REFERENCE)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))

    def test_rewording_prose_around_the_equation_stays_eligible(self):
        candidate = self.REFERENCE.replace("for the stacked sample",
                                           "across the stacked sample")
        result = rewrite_reward.fidelity_eligibility(candidate, self.REFERENCE)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))

    def test_commented_out_equation_is_not_an_invariant(self):
        # Both projections strip comments first; reading the raw span without
        # doing so made a dead commented-out equation a hard invariant, so
        # deleting it scored -inf.
        reference = ("We adopt the fiducial cosmology.\n"
                     "% \\begin{equation}\n"
                     "% M = 9.9 \\times 10^{9}\n"
                     "% \\end{equation}\n"
                     "The sample has 43 clusters.")
        candidate = "We adopt the fiducial cosmology. The sample has 43 clusters."
        self.assertEqual(rewrite_reward._numbers(reference), {"43"})
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))

    LABELLED = ("\\begin{equation}\n\\label{eq:m200}\n"
                "M = 4.2 \\times 10^{14}\n\\end{equation}")

    def test_label_digits_do_not_enter_the_number_set(self):
        # `eq:m200` used to contribute the junk token "00".
        self.assertNotIn("00", rewrite_reward._numbers(self.LABELLED))

    def test_renaming_a_label_is_not_a_fidelity_change(self):
        # `label` is in _FORMATTING_MACROS precisely because it carries no
        # scientific content; the math category must agree with that.
        candidate = self.LABELLED.replace("eq:m200", "eq:mass")
        result = rewrite_reward.fidelity_eligibility(candidate, self.LABELLED)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))

    def test_starring_the_environment_is_not_a_fidelity_change(self):
        candidate = self.LABELLED.replace("{equation}", "{equation*}")
        result = rewrite_reward.fidelity_eligibility(candidate, self.LABELLED)
        self.assertTrue(result["eligible"],
                        (result["missing"], result["invented"]))

    def test_case_only_symbol_substitution_is_ineligible(self):
        # LaTeX control words are case-sensitive and the case carries the
        # physics: \Delta\Sigma and \delta\Sigma are different quantities.
        reference = r"\begin{equation}\Delta\Sigma(R) = \bar{\Sigma}(<R)\end{equation}"
        candidate = reference.replace(r"\Delta", r"\delta")
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])


class SpacedUnitTests(unittest.TestCase):
    """`1.5 Mpc` is the ordinary prose form and must stay protected.

    Requiring adjacency or LaTeX spacing removed the false positives but also
    stopped catching `1.5 Mpc` -> `1.5 kpc`, a factor-1000 physics error, in
    the gate whose whole job is to catch exactly that. A space-separated token
    is now protected when it is a known unit.
    """

    def test_spaced_unit_change_is_ineligible(self):
        for reference, candidate in [
            ("The scale is 1.5 Mpc.", "The scale is 1.5 kpc."),
            ("Speed is 300 km/s here.", "Speed is 300 m/s here."),
            ("Resolution is 0.7 arcsec.", "Resolution is 0.7 arcmin."),
        ]:
            with self.subTest(reference=reference):
                result = rewrite_reward.fidelity_eligibility(candidate, reference)
                self.assertFalse(result["eligible"], result)

    def test_ordinary_word_after_a_numeral_is_still_not_a_unit(self):
        for reference, candidate in [
            ("In 2020 we found it.", "In 2020 the team found it."),
            ("We analyze 1200, 2400 sources.", "We analyze 1200, 2400 objects."),
        ]:
            with self.subTest(reference=reference):
                result = rewrite_reward.fidelity_eligibility(candidate, reference)
                self.assertTrue(result["eligible"],
                                (result["missing"], result["invented"]))


class MainExitContractTests(unittest.TestCase):
    """Exit 1 means "no candidate eligible"; a crash must not borrow it."""

    def test_unreadable_input_is_execution_failure(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = rewrite_reward.main([
                "--field", "no-such-field",
                "--reference", "no_such_reference.tex",
                "--candidates", "no_such_candidate.tex",
            ])
        self.assertEqual(status, 2)


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

    def test_empty_original_is_within_budget_with_zero_condensation(self):
        budget = rewrite_reward.length_budget("Some candidate text.", "")
        self.assertFalse(budget["within"])
        budget = rewrite_reward.length_budget("", "")
        self.assertTrue(budget["within"])
        self.assertEqual(budget["condensation"], 0.0)


class RankLengthGateIntegrationTests(unittest.TestCase):
    """Protect the length gate's integration into rank(): -inf for over-budget
    candidates, --allow-growth lift, and the fidelity floor on the bonus.
    Heavy dependencies (embedder, voice model, centroid) are mocked out."""

    ORIGINAL = "The estimator is stable across the five smoothing scales."
    REFERENCE = "claim: estimator stable across five smoothing scales"

    def rank_with_mocks(self, candidates, fidelity, **kwargs):
        from unittest import mock
        with mock.patch.object(rewrite_reward.df, "corpus_centroid",
                               return_value=None), \
             mock.patch.object(rewrite_reward.dv, "voice_score",
                               return_value=0.0), \
             mock.patch.object(rewrite_reward.dv, "load_voice_model",
                               return_value=None), \
             mock.patch.object(rewrite_reward.dv, "bundle_measured",
                               return_value=False), \
             mock.patch.object(rewrite_reward, "_cosine",
                               return_value=fidelity), \
             mock.patch.object(rewrite_reward, "_l0_target_count",
                               return_value=0):
            return rewrite_reward.rank(candidates, self.REFERENCE, None, **kwargs)

    def test_over_budget_candidate_scores_minus_inf(self):
        longer = self.ORIGINAL + " It also stays stable when the noise doubles."
        ranked = self.rank_with_mocks([longer], 0.95, original=self.ORIGINAL)
        result = ranked[0][1]
        self.assertFalse(result["length_eligible"])
        self.assertEqual(result["combined"], float("-inf"))

    def test_allow_growth_lifts_the_gate(self):
        longer = self.ORIGINAL + " It also stays stable when the noise doubles."
        ranked = self.rank_with_mocks([longer], 0.95, original=self.ORIGINAL,
                                      allow_growth=True)
        result = ranked[0][1]
        self.assertTrue(result["length_eligible"])
        self.assertNotEqual(result["combined"], float("-inf"))

    def test_condensation_bonus_requires_fidelity_floor(self):
        shorter = "The estimator is stable."
        high = self.rank_with_mocks([shorter], 0.9, original=self.ORIGINAL)[0][1]
        low = self.rank_with_mocks([shorter], 0.2, original=self.ORIGINAL)[0][1]
        bonus_high = high["combined"] - 0.3 * 0.9
        bonus_low = low["combined"] - 0.3 * 0.2
        self.assertGreater(bonus_high, 0.0)
        self.assertEqual(bonus_low, 0.0)


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


class HyphenatedRangeTests(unittest.TestCase):
    """A hyphen between two numerals separates a range; it is not a minus sign.

    `[-+]?` accepted a sign straight after a digit, so "0.5-1.2 arcsec" gave
    {"0.5", "-1.2"} and a faithful rewrite saying "from 0.5 to 1.2" was
    reported as MISSING "-1.2" while INVENTING "1.2", then hard-rejected at
    combined = -inf. Every hyphenated range in a reference did this, which is
    most of them. Third occurrence of one root cause -- a separator absorbed
    into the token -- after the Oxford comma and the spaced unit.
    """

    def numbers(self, text):
        return set(rewrite_reward._NUM_RE.findall(text))

    def test_hyphenated_ranges_yield_two_positive_numbers(self):
        for text, want in [
            ("seeing 0.5-1.2 arcsec", {"0.5", "1.2"}),
            ("5-40 per square arcminute", {"5", "40"}),
            ("magnitudes 24.0-26.0", {"24.0", "26.0"}),
            ("amplitudes 0.01-0.06", {"0.01", "0.06"}),
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.numbers(text), want)

    def test_genuine_negatives_are_still_signed(self):
        self.assertEqual(self.numbers("a bias of -0.06 dex"), {"-0.06"})
        self.assertEqual(self.numbers("from -3 to +5"), {"-3", "+5"})

    def test_exponents_keep_their_sign(self):
        self.assertEqual(self.numbers("10^-3"), {"10", "-3"})

    def test_earlier_separator_fixes_still_hold(self):
        # The Oxford comma and thousands-separator cases this regex was
        # previously corrected for must not regress.
        self.assertEqual(self.numbers("1200, 2400, and 4800"),
                         {"1200", "2400", "4800"})
        self.assertEqual(self.numbers("1,234 sources"), {"1,234"})

    def test_a_range_rewritten_as_prose_is_eligible(self):
        reference = "The grid spans 12 seeing values from 0.5-1.2 arcsec."
        candidate = "The grid samples 12 seeing values between 0.5 and 1.2 arcsec."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"], result["missing"])

    def test_a_range_endpoint_actually_dropped_is_still_caught(self):
        reference = "The grid spans 12 seeing values from 0.5-1.2 arcsec."
        candidate = "The grid spans 12 seeing values starting at 0.5 arcsec."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("1.2", result["missing"]["numbers"])


if __name__ == "__main__":
    unittest.main()
