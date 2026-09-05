from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import _profilefixture as fixture
import deai_salience as salience
import extract_style as es


# Eight sentences; the middle four each carry a measured quantity, so the
# longest uninterrupted recital run is 4 of 8.
RECITAL_HEAVY = (
    "The detection step selects on the depth of the inter-peak dip. "
    "We ran the grid over $500$ detector configurations. "
    "The strict label holds for $34.6\\%$ of resolvable rows. "
    "Configurations with no dip detect at $0.98\\%$. "
    "The held-out split reaches $0.813$ to $0.843$. "
    "The criterion transfers to unseen mass ratios. "
    "Its factors follow from the linearity of the estimator. "
    "The catalog is therefore saddle-limited rather than mass-selected."
)

# Same eight sentences' worth of numbers, but interleaved with the statements
# that give them consequence, so no run exceeds one.
RANKED = (
    "The detection step selects on the depth of the inter-peak dip. "
    "Configurations whose map keeps no dip detect at $0.98\\%$. "
    "That floor is set by the protocol alone, not by halo mass. "
    "Resolvable configurations detect at $34.6\\%$ instead. "
    "The gap is what makes the catalog saddle-limited. "
    "A fit on half the cells transfers to the remainder. "
    "Its factors follow from the linearity of the estimator. "
    "The criterion is therefore computable before detection is run."
)

NO_NUMBERS = (
    "The aperture-mass map is a filter-weighted mean of tangential "
    "ellipticity. Peaks are detected on the processed signal-to-noise map "
    "after an empirical null. The convergence itself is never observed. "
    "This Letter asks what physical quantity the detection step selects on."
)


class TestNumeralPreservingReduction(unittest.TestCase):
    def test_inline_math_numerals_survive(self):
        reduced = es.latex_to_numeral_text("We used $500$ configurations.")
        self.assertIn("500", reduced)

    def test_latex_to_plain_still_destroys_them(self):
        # The contrast is the reason this axis needs its own reduction; if
        # latex_to_plain ever kept numerals, the two projections would merge.
        self.assertNotIn("500", es.latex_to_plain("We used $500$ configurations."))

    def test_thousands_separator_is_one_numeral(self):
        reduced = es.latex_to_numeral_text("The sample has $14{,}850{,}000$ rows.")
        self.assertEqual(len(salience.RE_NUMERAL.findall(reduced)), 1)

    def test_displayed_equations_are_dropped(self):
        text = ("Prose here.\n"
                "\\begin{equation}\nx = 3 \\pi / 200\n\\end{equation}\n"
                "More prose.")
        reduced = es.latex_to_numeral_text(text)
        self.assertNotIn("200", reduced)


class TestSalienceFeatures(unittest.TestCase):
    def test_recital_run_counts_consecutive_numeral_sentences(self):
        values = salience.salience_features(RECITAL_HEAVY)
        self.assertEqual(values["max_recital_run"], 4)
        self.assertEqual(values["n_sentences"], 8)

    def test_interleaving_breaks_the_run_at_equal_number_count(self):
        heavy = salience.salience_features(RECITAL_HEAVY)
        ranked = salience.salience_features(RANKED)
        self.assertLess(ranked["max_recital_run"], heavy["max_recital_run"])

    def test_prose_without_numerals_measures_zero_recital(self):
        values = salience.salience_features(NO_NUMBERS)
        self.assertEqual(values["recital_frac"], 0.0)
        self.assertEqual(values["max_recital_run"], 0)

    def test_short_passage_is_unmeasurable_rather_than_clean(self):
        self.assertIsNone(salience.salience_features("One sentence only here."))


class TestPercentileReading(unittest.TestCase):
    REFERENCE = {"percentiles": {"max_recital_run_frac": {
        "0.0": 0.0, "0.5": 0.2, "0.85": 0.4, "0.9": 0.5, "0.94": 0.5,
        "0.95": 0.6, "1.0": 1.0}}}

    def test_value_on_a_tie_plateau_reads_the_top_of_the_tie(self):
        # 0.5 is shared by the 0.90-0.94 band. Reading the plateau's lower edge
        # would report a passage as exactly typical whenever it lands on a
        # common value, which is what suppressed the Letter's abstract.
        found = salience.percentile_of(self.REFERENCE, "max_recital_run_frac", 0.5)
        self.assertEqual(found, 0.94)

    def test_value_above_the_grid_is_the_top_percentile(self):
        self.assertEqual(
            salience.percentile_of(self.REFERENCE, "max_recital_run_frac", 2.0), 1.0)

    def test_missing_feature_is_none_not_zero(self):
        self.assertIsNone(salience.percentile_of(self.REFERENCE, "absent", 0.5))


def synthetic_passage(run_length: int, total: int = 8) -> str:
    """A passage whose leading `run_length` sentences each carry a numeral."""
    numeric = "The recovered rate is $12.3\\%$ on this split. "
    plain = "The behaviour follows from the linearity of the estimator. "
    return numeric * run_length + plain * (total - run_length)


def graded_bank(directory: Path, section: str = "abstract") -> Path:
    """A reference with spread in its upper tail, as a real corpus has.

    Ten passages each at run lengths 0-2, nine at 3, and one saturated: enough
    that the p90 gate and the maximum differ, which is the condition a
    reference must meet before it can rank anything.
    """
    bank = directory / "exemplar_paragraphs.jsonl"
    lengths = [0] * 10 + [1] * 10 + [2] * 10 + [3] * 9 + [8]
    with bank.open("w", encoding="utf-8") as handle:
        for run in lengths:
            handle.write(json.dumps({"section": section,
                                     "text": synthetic_passage(run)}) + "\n")
    return bank


class TestFindingsAndCalibration(unittest.TestCase):
    def test_no_baseline_yields_no_findings_and_an_unmeasured_axis(self):
        self.assertEqual(salience.salience_findings(RECITAL_HEAVY, None), [])
        axis = salience.salience_axis_status(None)
        self.assertEqual(axis["status"], "unmeasured")

    def test_calibrate_then_detect_round_trip(self):
        with tempfile.TemporaryDirectory(prefix="salience-") as raw:
            profile = Path(raw)
            graded_bank(profile)
            result = salience.calibrate(profile)
            self.assertEqual(result["abstract"]["n"], 40)
            self.assertEqual(salience.salience_axis_status(profile)["status"],
                             "measured")

            document = ("\\begin{abstract}\n" + RECITAL_HEAVY +
                        "\n\\end{abstract}\n")
            findings = salience.salience_findings(document, profile)
            self.assertEqual(len(findings), 1,
                             "one over-recital passage must yield exactly one "
                             "finding, not one per feature")
            finding = findings[0]
            self.assertEqual(finding["rule"], "salience-recital:abstract")
            self.assertEqual(finding["kind"], "advisory")
            self.assertEqual(finding["layer"], "L2")
            self.assertLessEqual(finding["confidence"]["value"],
                                 salience.feedback.PARAGRAPH_CONFIDENCE_CAP)

    def test_calibration_reads_the_numeral_projection_of_the_bank(self):
        # A bank row stores the passage twice. Read on `text`, every reference
        # passage below carries zero numerals and the p90 of the run fraction
        # is 0; read on `numeral_text` the reference has the spread the
        # manuscript side will be compared against.
        lengths = [0] * 10 + [1] * 10 + [2] * 10 + [3] * 9 + [8]
        rows = [{"section": "abstract",
                 "text": es.latex_to_plain(synthetic_passage(run)),
                 "numeral_text": synthetic_passage(run)} for run in lengths]
        with fixture.temp_profile(rows) as profile:
            p90 = salience.calibrate(profile)["abstract"]["percentiles"][
                "max_recital_run_frac"]["0.9"]
        self.assertGreater(p90, 0.0)
        with fixture.temp_profile([{k: v for k, v in row.items()
                                    if k != "numeral_text"} for row in rows]) as profile:
            fallback = salience.calibrate(profile)["abstract"]["percentiles"][
                "max_recital_run_frac"]["0.9"]
        self.assertEqual(fallback, 0.0)

    def test_a_typical_passage_is_not_flagged(self):
        with tempfile.TemporaryDirectory(prefix="salience-") as raw:
            profile = Path(raw)
            graded_bank(profile)
            salience.calibrate(profile)
            document = ("\\begin{abstract}\n" + synthetic_passage(1) +
                        "\n\\end{abstract}\n")
            self.assertEqual(salience.salience_findings(document, profile), [])

    def test_a_reference_with_no_upper_tail_spread_abstains(self):
        # Forty identical passages give P(X <= x) = 1.0 for the value they all
        # share, so an unguarded reading would flag a perfectly typical
        # passage as the 100th percentile.
        with fixture.temp_profile(fixture.uniform(RANKED, 40)) as profile:
            salience.calibrate(profile)
            baseline = salience.load_baseline(profile)
            self.assertFalse(salience.resolves_above_gate(
                baseline["abstract"], "max_recital_run_frac"))
            document = "\\begin{abstract}\n" + RANKED + "\n\\end{abstract}\n"
            self.assertEqual(salience.salience_findings(document, profile), [])

    def test_small_reference_is_degraded_not_measured(self):
        with fixture.temp_profile(fixture.uniform(RANKED, 5)) as profile:
            salience.calibrate(profile)
            self.assertEqual(salience.salience_axis_status(profile)["status"],
                             "degraded")


class TestLocalReference(unittest.TestCase):
    """The axis on a real locally-built reference, when one is present.

    The plugin ships NO baseline -- every `style-profile/**` artifact is
    gitignored on purpose, so these assertions never run on a clean clone or in
    CI, and that is by design rather than an accident to be fixed. The previous
    name and docstring claimed the opposite ("the reference the plugin actually
    ships"), which read as CI coverage that does not exist. Deterministic
    behaviour is covered by the fixture-built baselines in the classes above;
    this class only adds a smoke check on the author's own corpus.
    """

    PROFILE = Path(__file__).resolve().parents[1] / "style-profile" / "wgl"

    def setUp(self):
        if salience.load_baseline(self.PROFILE) is None:
            self.skipTest(
                "no locally-built wgl salience baseline (expected on a clean "
                "clone: style-profile artifacts are gitignored)")

    def test_axis_is_measured(self):
        self.assertEqual(salience.salience_axis_status(self.PROFILE)["status"],
                         "measured")

    def test_recital_heavy_abstract_is_flagged(self):
        # Six numeral sentences of eight. The four-of-eight passage the
        # fixture tests use sits at P(X <= x) = 0.90 of real abstracts once
        # the reference counts the numerals inside their math (v0.36.3), which
        # is the gate itself, not above it; a smoke check must not ride the
        # edge of the distribution it is checking.
        heavier = RECITAL_HEAVY.replace(
            "The criterion transfers to unseen mass ratios. ",
            "The criterion transfers to $3$ of $4$ unseen mass ratios. ").replace(
            "The detection step selects on the depth of the inter-peak dip. ",
            "The detection step selects on the depth of the inter-peak dip at $2$ pixels. ")
        document = "\\begin{abstract}\n" + heavier + "\n\\end{abstract}\n"
        rules = {f["rule"] for f in salience.salience_findings(document, self.PROFILE)}
        self.assertIn("salience-recital:abstract", rules)

    def test_prose_without_numerals_is_not_flagged(self):
        document = ("\\begin{abstract}\n" + NO_NUMBERS + " " + NO_NUMBERS +
                    "\n\\end{abstract}\n")
        self.assertEqual(salience.salience_findings(document, self.PROFILE), [])


if __name__ == "__main__":
    unittest.main()
