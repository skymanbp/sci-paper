from __future__ import annotations

import io
import re
import tempfile
import unittest
from collections import Counter
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import rewrite_reward


class RewriteFidelityTests(unittest.TestCase):
    def test_preserves_scientific_invariants(self):
        reference = (
            r"The estimator increases AUC to 0.91 at $z=0.5$ for 43 clusters "
            r"\citep{Smith2024}; the uncertainty is not below 2 km/s."
        )
        candidate = (
            r"For the 43 clusters, the estimator increases AUC to 0.91 at $z=0.5$ "
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
        reference = r"a filter family of \Nconfig{} configurations"
        candidate = "a filter family of configurations"
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("nconfig", result["missing"]["latex_macros"])

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
            set(rewrite_reward._numbers("We analyze 1200, 2400, and 4800 sources.")),
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


class AdjacentSuffixTests(unittest.TestCase):
    """An English suffix glued onto the digits is not a unit (`3rd`, `1990s`, `5x`)."""

    def test_suffixes_glued_to_digits_are_not_units(self):
        for text in ("the 3rd run", "the 1990s", "a 5x gain", "the 21st", "the 2nd", "the 4th"):
            with self.subTest(text=text):
                self.assertEqual(rewrite_reward._units(text), set())

    def test_typeset_seconds_stay_a_unit(self):
        self.assertEqual(rewrite_reward._units(r"5\,s"), {"s"})
        self.assertEqual(rewrite_reward._units("5 s"), {"s"})

    def test_rephrasing_around_a_decade_stays_eligible(self):
        result = rewrite_reward.fidelity_eligibility("during the 1990s", "in the 1990s")
        self.assertTrue(result["eligible"], (result["missing"], result["invented"]))


class AcronymTests(unittest.TestCase):
    """A hyphen is part of an acronym only where an acronym continues after it."""

    def test_trailing_hyphen_is_not_part_of_an_acronym(self):
        self.assertEqual(rewrite_reward._acronyms("a CDM-like model"), {"CDM"})
        self.assertEqual(rewrite_reward._acronyms("X-RAY data, paper II, HST-ACS and HST"),
                         {"X-RAY", "II", "HST-ACS", "HST"})

    def test_hyphenating_the_acronym_stays_eligible(self):
        result = rewrite_reward.fidelity_eligibility("a CDM model", "a CDM-like model")
        self.assertTrue(result["eligible"], (result["missing"], result["invented"]))

    def test_projection_placeholders_are_not_acronyms(self):
        text = r"\citep{Smith2024} \begin{equation}y=x\end{equation} \begin{figure}z\end{figure}"
        self.assertEqual(rewrite_reward._acronyms(text), set())

    def test_removing_an_empty_float_is_not_an_acronym_loss(self):
        reference = "We show the fit.\n\\begin{figure}\n\\centering\n\\end{figure}\nIt converges."
        candidate = "We show the fit. It converges."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"], (result["missing"], result["invented"]))


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

    def test_inline_math_numerals_are_collected_too(self):
        # Inline and display forms are read symmetrically; see _numbers.
        self.assertIn("0.5", rewrite_reward._numbers("at $z=0.5$"))

    def test_moving_an_equation_between_display_and_inline_is_not_a_change(self):
        inline = (self.REFERENCE.replace("\n\\begin{equation}\n", " $")
                  .replace("\n\\end{equation}\n", "$ "))
        for candidate, reference in ((inline, self.REFERENCE), (self.REFERENCE, inline)):
            with self.subTest(candidate=candidate[:24]):
                result = rewrite_reward.fidelity_eligibility(candidate, reference)
                self.assertTrue(result["eligible"], (result["missing"], result["invented"]))

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
        self.assertEqual(set(rewrite_reward._numbers(reference)), {"43"})
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


class FormattingMacroAndRmUnitTests(unittest.TestCase):
    """`\\ldots`/`\\dots` and the natbib variants are formatting; `{\\rm Mpc}` is a unit."""

    def test_dots_and_natbib_variants_are_not_semantic_macros(self):
        self.assertEqual(
            rewrite_reward._macros(r"a \ldots b \dots \citeyearpar{k} \citetext{see} \Nconfig"),
            {"nconfig"})
        result = rewrite_reward.fidelity_eligibility("with 43 sources ...",
                                                     r"with 43 sources \ldots")
        self.assertTrue(result["eligible"], (result["missing"], result["invented"]))

    def test_rm_unit_is_protected_in_both_forms(self):
        for text in (r"5\,{\rm Mpc}", r"5 {\rm Mpc}", r"5{\rm\,Mpc}"):
            with self.subTest(text=text):
                self.assertEqual(rewrite_reward._units(text), {r"\mathrm{mpc}"})
        # Only a vocabulary unit: `{\rm ...}` wraps far more than units.
        self.assertEqual(rewrite_reward._units(r"5 {\rm foo}"), set())

    def test_modernising_rm_is_not_a_unit_change_but_kpc_is(self):
        reference = r"The scale is 5\,{\rm Mpc}."
        modern = rewrite_reward.fidelity_eligibility(r"The scale is 5\,\mathrm{Mpc}.", reference)
        self.assertTrue(modern["eligible"], (modern["missing"], modern["invented"]))
        result = rewrite_reward.fidelity_eligibility(r"The scale is 5\,{\rm kpc}.", reference)
        self.assertFalse(result["eligible"])
        self.assertIn(r"\mathrm{mpc}", result["missing"]["units"])


class MultiplicityTests(unittest.TestCase):
    """Numbers and markers are bags: a dropped second occurrence is a loss,
    and a token still present with the wrong count is reported as such."""

    REFERENCE = "The bias is not significant and the trend is not real."

    def test_dropped_second_negation_is_ineligible(self):
        result = rewrite_reward.fidelity_eligibility(
            "The bias is not significant and the trend is real.", self.REFERENCE)
        self.assertFalse(result["eligible"])
        self.assertEqual(result["missing"]["negation"], ["not"])
        self.assertEqual(result["count_mismatches"], {"negation": {"not": (2, 1)}})

    def test_both_negations_dropped_lists_each_occurrence(self):
        result = rewrite_reward.fidelity_eligibility(
            "The bias is significant and the trend is real.", self.REFERENCE)
        self.assertEqual(result["missing"]["negation"], ["not", "not"])
        self.assertEqual(result["count_mismatches"], {})

    def test_repeated_number_replaced_by_another_is_ineligible(self):
        # Sets saw {43, 512} on both sides and passed this.
        result = rewrite_reward.fidelity_eligibility(
            "We find 43 here and 512 there among 512.",
            "We find 43 here and 43 there among 512.")
        self.assertFalse(result["eligible"])
        self.assertEqual(result["missing"]["numbers"], ["43"])
        self.assertEqual(result["invented"]["numbers"], ["512"])

    def test_added_second_causal_marker_is_invention(self):
        reference = "The bias shrinks because the sample grows; the scatter falls."
        candidate = reference[:-1] + " because of it."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertEqual(result["invented"]["causal_direction"], ["because"])

    def test_repeated_citations_and_units_stay_sets(self):
        reference = r"At 5 Mpc \citep{Doe2025} and again at 5 Mpc \citep{Doe2025}."
        candidate = r"At 5 Mpc \citep{Doe2025}, and again at 5 Mpc."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertTrue(result["eligible"], (result["missing"], result["invented"]))


class MainExitContractTests(unittest.TestCase):
    """Exit 0/1 by eligibility, 2 for invalid input and crashes; a missing
    optional model, profile or embedder is none of these (unmeasured, weight 0)."""

    REFERENCE = "The sample of 43 clusters has a bias of 0.5--1.2 dex.\n"
    FAITHFUL = "For 43 clusters the bias spans 0.5 to 1.2 dex.\n"
    UNFAITHFUL = "The bias spans 0.5 to 1.2 dex.\n"

    def run_cli(self, candidate=FAITHFUL, *, fields=(), field=None, bundle=None,
                reference=REFERENCE, embedder=True, cosine=None, rank=None):
        out, err = io.StringIO(), io.StringIO()
        with ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            profiles = root / "profiles"
            profiles.mkdir()
            for name in fields:
                (profiles / name).mkdir()
                if bundle is not None:
                    (profiles / name / "voice_model.joblib").write_bytes(bundle)
            if reference is not None:
                (root / "ref.txt").write_text(reference, encoding="utf-8")
            (root / "cand.txt").write_text(candidate, encoding="utf-8")
            argv = ["--profile-root", str(profiles), "--reference", str(root / "ref.txt"),
                    "--candidates", str(root / "cand.txt")]
            if field:
                argv += ["--field", field]
            stack.enter_context(mock.patch.object(rewrite_reward.df, "embedder_available",
                                                  return_value=embedder))
            stack.enter_context(mock.patch.object(rewrite_reward, "_cosine",
                                                  **(cosine or {"return_value": 0.9})))
            if rank is not None:
                stack.enter_context(mock.patch.object(rewrite_reward, "rank", **rank))
            stack.enter_context(redirect_stdout(out))
            stack.enter_context(redirect_stderr(err))
            status = rewrite_reward.main(argv)
        return status, out.getvalue(), err.getvalue()

    def test_crash_inside_rank_is_execution_failure(self):
        status, _out, err = self.run_cli(rank={"side_effect": RuntimeError("boom")})
        self.assertEqual(status, 2)
        self.assertIn("execution failed: RuntimeError: boom", err)

    def test_unreadable_input_is_execution_failure(self):
        status, _out, err = self.run_cli(reference=None)
        self.assertEqual(status, 2)
        self.assertIn("execution failed: FileNotFoundError", err)

    def test_no_eligible_candidate_is_exit_1_even_without_a_profile(self):
        status, out, err = self.run_cli(self.UNFAITHFUL)
        self.assertEqual(status, 1)
        self.assertIn("missing: {'numbers': ['43']}", out)
        self.assertIn("no field profile", err)
        self.assertIn("regenerate tighter", err)

    def test_eligible_candidate_is_exit_0(self):
        status, out, _err = self.run_cli()
        self.assertEqual(status, 0)
        self.assertIn("[best] candidate 0", out)

    def test_missing_voice_model_is_unmeasured_not_exit_2(self):
        status, out, err = self.run_cli(fields=("wgl",), field="wgl")
        self.assertEqual(status, 0)
        self.assertRegex(err, r"no voice_model\.joblib in \S*wgl: learned field-similarity "
                              r"score unmeasured, weight 0")
        # voice column `-`, fidelity 0.900, combined = 0.3 * 0.9 with no voice term.
        self.assertRegex(out, re.compile(r"^ +1 +0 +0\.270 +- +0\.900 ", re.M))

    def test_single_field_is_auto_detected(self):
        status, _out, err = self.run_cli(fields=("wgl",))
        self.assertEqual(status, 0)
        self.assertRegex(err, r"no voice_model\.joblib in \S*wgl")

    def test_several_fields_run_without_a_profile(self):
        status, _out, err = self.run_cli(fields=("a", "b"))
        self.assertEqual(status, 0)
        self.assertIn("several field profiles present", err)
        self.assertIn("no field profile", err)

    def test_unusable_bundle_is_named_as_present(self):
        status, _out, err = self.run_cli(fields=("wgl",), bundle=b"not a joblib bundle")
        self.assertEqual(status, 0)
        self.assertIn("voice_model.joblib is present but unusable", err)
        self.assertNotIn("no voice_model.joblib", err)

    def test_missing_embedder_is_unmeasured_not_a_crash(self):
        status, out, err = self.run_cli(embedder=False,
                                        cosine={"side_effect": AssertionError("embedder used")})
        self.assertEqual(status, 0)
        self.assertIn("semantic fidelity unmeasured, weight 0", err)
        self.assertRegex(out, re.compile(r"^ +1 +0 +0\.000 +- +- ", re.M))

    def test_count_mismatch_is_reported_with_both_counts(self):
        _status, out, _err = self.run_cli(
            "The bias is not significant and the trend is real.",
            reference="The bias is not significant and the trend is not real.")
        self.assertIn("count mismatch: negation 'not': 2 in reference, 1 in candidate", out)


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
    Heavy dependencies (embedder, voice model) are mocked out."""

    ORIGINAL = "The estimator is stable across the five smoothing scales."
    REFERENCE = "claim: estimator stable across five smoothing scales"

    def rank_with_mocks(self, candidates, fidelity, **kwargs):
        with mock.patch.object(rewrite_reward.dv, "load_voice_model",
                               return_value=None), \
             mock.patch.object(rewrite_reward.df, "embedder_available",
                               return_value=True), \
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


class UnmeasuredTermTests(unittest.TestCase):
    """A term that cannot be measured is None at weight 0, never a nominal 0.0."""

    def test_floor_is_not_applied_to_an_unmeasured_fidelity(self):
        self.assertEqual(rewrite_reward._advisory_reduction(2, 0, None), 1.0)
        self.assertEqual(rewrite_reward._advisory_reduction(2, 0, 0.1), 0.0)

    def test_rank_without_bundle_or_embedder_keeps_the_gate(self):
        with mock.patch.object(rewrite_reward.df, "embedder_available", return_value=False), \
             mock.patch.object(rewrite_reward, "_cosine", side_effect=AssertionError):
            ranked = rewrite_reward.rank(["We find 43 sources.", "We find sources."],
                                         "We find 43 sources.", None)
        (best, result), (_worst, rejected) = ranked
        self.assertEqual(best, 0)
        self.assertIsNone(result["fidelity"])
        self.assertIsNone(result["voice"])
        self.assertEqual(result["combined"], 0.0)
        self.assertEqual(rejected["combined"], float("-inf"))


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
    into the token -- after the Oxford comma and the spaced unit. The LaTeX
    en-dash `--` was the fourth: its second hyphen follows a hyphen, not a
    digit, so the digit/dot rule alone still read it as a sign.
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

    def test_latex_dashes_are_separators_too(self):
        self.assertEqual(self.numbers("seeing 0.5--1.2 arcsec"), {"0.5", "1.2"})
        self.assertEqual(self.numbers("5---10 per field"), {"5", "10"})

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
        for dash in ("-", "--"):
            reference = f"The grid spans 12 seeing values from 0.5{dash}1.2 arcsec."
            candidate = "The grid samples 12 seeing values between 0.5 and 1.2 arcsec."
            with self.subTest(dash=dash):
                result = rewrite_reward.fidelity_eligibility(candidate, reference)
                self.assertTrue(result["eligible"], result["missing"])

    def test_a_range_endpoint_actually_dropped_is_still_caught(self):
        reference = "The grid spans 12 seeing values from 0.5-1.2 arcsec."
        candidate = "The grid spans 12 seeing values starting at 0.5 arcsec."
        result = rewrite_reward.fidelity_eligibility(candidate, reference)
        self.assertFalse(result["eligible"])
        self.assertIn("1.2", result["missing"]["numbers"])


class SignedAndIdentifierNumeralTests(unittest.TestCase):
    """Corrections (2), (3), (5) and (6) of the numeral record."""

    def test_unicode_minus_is_a_sign_and_folds_to_ascii(self):
        self.assertEqual(rewrite_reward._numbers("a bias of \u22120.06 dex"),
                         Counter({"-0.06": 1}))
        reference = "a bias of \u22120.06 dex"
        self.assertFalse(rewrite_reward.fidelity_eligibility("a bias of 0.06 dex",
                                                             reference)["eligible"])
        self.assertTrue(rewrite_reward.fidelity_eligibility("a bias of -0.06 dex",
                                                            reference)["eligible"])

    def test_exponent_belongs_to_the_number(self):
        self.assertEqual(set(rewrite_reward._numbers("a rate of 1.5e-3 per year")), {"1.5e-3"})
        self.assertFalse(rewrite_reward.fidelity_eligibility("1.5e+3", "1.5e-3")["eligible"])

    def test_a_token_does_not_start_inside_an_identifier(self):
        self.assertEqual(rewrite_reward._numbers("M200 and z0.5"), Counter())
        self.assertEqual(rewrite_reward._units("M200c"), set())

    def test_leading_dot_decimal_is_one_number(self):
        self.assertEqual(set(rewrite_reward._numbers("a bias of .06 dex")), {".06"})


if __name__ == "__main__":
    unittest.main()
