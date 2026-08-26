from __future__ import annotations

import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import _profilefixture as fixture
import deai_discourse as discourse
import deai_reference as reference

# Three topics, each written twice sentence for sentence. The RICH version
# carries both properties: every sentence after the first opens on a term the
# one before it established, and the claims past the measurement are marked as
# inferences. The POOR version carries neither: nothing is carried forward, and
# every claim is stated as though it were a measurement. The three topics share
# no vocabulary, so a section built from all three is not cohesive merely
# because it repeats itself.
RICH_SENTENCES = (
    ("The tangential shear is measured in annuli around each candidate centre.",
     "That shear is convolved with a compensated filter of fixed scale.",
     "The filter may define an aperture mass insensitive to the mass sheet.",
     "This aperture mass likely inherits the shape noise of the source catalogue.",
     "That shape noise probably sets the detection floor for every candidate.",
     "The detection floor may then be quoted per square degree of footprint."),
    ("Photometric redshifts are assigned to each source galaxy by template fits.",
     "Those redshifts propagate into the lensing efficiency of every bin.",
     "The efficiency appears to set the amplitude of the predicted signal.",
     "That amplitude is possibly degenerate with the intrinsic alignment term.",
     "The alignment term seems to dominate the systematic budget at low redshift.",
     "That systematic budget is arguably what the calibration effort targets."),
    ("Cluster centres are taken from the brightest member galaxy in each halo.",
     "Misplaced centres may leave the stacked profile smoothed inward.",
     "That smoothed profile likely biases the recovered concentration downward.",
     "The concentration bias could plausibly exceed the statistical error.",
     "That statistical error is roughly what the survey area was chosen to fix.",
     "The survey area is likely fixed by the observing time that was awarded."),
)

POOR_SENTENCES = (
    ("The tangential shear is measured in annuli around each candidate centre.",
     "A compensated filter of fixed scale removes the constant sheet.",
     "Aperture statistics stay insensitive to unobservable additive offsets.",
     "Intrinsic ellipticity dispersion propagates into every reconstruction.",
     "Detection floors are quoted per square degree of the survey footprint.",
     "Photometric calibration errors enter the shear estimate multiplicatively."),
    ("Photometric redshifts are assigned to each source galaxy by template fits.",
     "Lensing efficiency rises steeply behind the deflector plane.",
     "Tomographic binning splits the catalogue at fixed number density.",
     "Intrinsic alignments contribute a negative term to the observed spectrum.",
     "Systematic budgets are dominated by shear calibration at high redshift.",
     "Blending fractions rise steeply toward the faint end of the catalogue."),
    ("Cluster centres are taken from the brightest member galaxy in each halo.",
     "Stacked profiles are smoothed inward by an offset in the adopted position.",
     "Recovered concentrations fall below the value the simulations report.",
     "Statistical errors scale as the inverse square root of the survey area.",
     "The footprint was chosen to control this quantity from the outset.",
     "Observing time was awarded on the basis of a forecast covariance."),
)

LEVELS = len(RICH_SENTENCES[0])
RICH = tuple(" ".join(s) for s in RICH_SENTENCES)
POOR = tuple(" ".join(s) for s in POOR_SENTENCES)


def blend(topic: int, level: int) -> str:
    """One topic's paragraph with `level` of its sentences in the rich version.

    Level 0 is fully POOR and level LEVELS fully RICH, and both properties rise
    monotonically in between. A reference needs that gradient: a bank holding
    only the two extremes puts its tenth percentile in the middle of the lower
    clump, so the extreme itself reads as p25 and nothing is ever flagged.

    Levels 0 and 1 are the same paragraph. The two versions share their opening
    sentence -- cohesion is a property of what follows an opening, so a topic
    that started differently would be measuring the topic and not the linkage.
    """
    rich, poor = RICH_SENTENCES[topic], POOR_SENTENCES[topic]
    return " ".join(rich[:level] + poor[level:])


def levels_for(documents: int) -> list[int]:
    """One blend level per document, with the lowest level deliberately rare.

    Two constraints shape this. The levels start at 2, not 1, because level 1
    IS level 0 -- the two versions share their opening sentence -- so a bank
    holding level 1 would tie with the fully POOR document the tests submit
    instead of sitting above it. And the lowest level gets about a twentieth of
    the mass rather than an even share, because the tenth percentile of N units
    is the (N // 10)-th smallest: a bank whose minimum occupies a tenth or more
    has p10 == p0, and the reference then correctly refuses to resolve.
    """
    rare = max(1, documents // 20)
    return [2] * rare + [3 + index % (LEVELS - 2)
                         for index in range(documents - rare)]


def graded_bank(*, documents: int = 40, section: str = "intro") -> list[dict]:
    """A bank with spread in its LOWER tail, as a real corpus has.

    Each source document contributes one paragraph per topic at one blend
    level, so N documents give a paragraph reference of 3N and a section
    reference of N.
    """
    return [{"section": section, "source": f"paper-{index:03d}.tex",
             "text": blend(topic, level)}
            for index, level in enumerate(levels_for(documents))
            for topic in range(len(RICH_SENTENCES))]


def document(paragraphs, label: str = "Introduction") -> str:
    """One `\\section` holding `paragraphs`, each its own paragraph unit."""
    return f"\\section{{{label}}}\n\n" + "\n\n".join(paragraphs) + "\n"


class TestCohesionFeature(unittest.TestCase):
    def test_carried_terms_score_above_dropped_ones(self):
        self.assertGreater(discourse.cohesion_features(RICH[0])["cohesion"],
                           discourse.cohesion_features(POOR[0])["cohesion"])

    def test_function_words_do_not_count_as_linkage(self):
        # Every English sentence shares "the" and "is". If stopwords counted,
        # POOR would score as linked prose and the axis would say nothing.
        self.assertLess(discourse.cohesion_features(POOR[0])["cohesion"], 0.25)

    def test_short_passage_is_unmeasurable_rather_than_zero(self):
        self.assertIsNone(discourse.cohesion_features("One sentence only here."))

    def test_the_sentence_floor_is_a_floor_not_a_default(self):
        self.assertIsNone(discourse.cohesion_features(
            "The shear is measured here. The filter is applied after that."))


class TestHedgingFeature(unittest.TestCase):
    def test_epistemic_markers_raise_the_rate(self):
        rich = discourse.hedging_features(document(RICH))
        poor = discourse.hedging_features(document(POOR))
        self.assertGreater(rich["hedging"], poor["hedging"])

    def test_a_flat_passage_reports_zero_rather_than_nothing(self):
        values = discourse.hedging_features(document(POOR))
        self.assertEqual(values["hedge_count"], 0)
        self.assertEqual(values["hedging"], 0.0)

    def test_below_the_word_floor_is_unmeasurable(self):
        # A rate per 1,000 words over 40 words turns on one word's presence.
        self.assertIsNone(discourse.hedging_features(POOR[0]))


class TestUnitsAreNotInterchangeable(unittest.TestCase):
    """The one invariant the two-unit design exists to hold."""

    def test_each_axis_declares_the_unit_it_calibrates_at(self):
        self.assertEqual(discourse.AXES["cohesion"]["unit"], "paragraph")
        self.assertEqual(discourse.AXES["hedging"]["unit"], "section")

    def test_the_span_sweep_follows_the_declared_unit(self):
        self.assertIs(discourse.AXES["cohesion"]["spans"], reference.units)
        self.assertIs(discourse.AXES["hedging"]["spans"], reference.sections)

    def test_sections_are_coarser_than_paragraphs_on_the_same_text(self):
        text = document(RICH) + document(POOR, "Methods")
        self.assertGreater(len(reference.units(text)), len(reference.sections(text)))

    def test_the_artifact_records_the_unit_it_was_built_at(self):
        with fixture.temp_profile(graded_bank(), prefix="discourse-") as profile:
            result = discourse.calibrate(profile)
            self.assertEqual(result["cohesion"]["intro"]["unit"], "paragraph")
            self.assertEqual(result["hedging"]["intro"]["unit"], "section")

    def test_a_record_with_no_source_cannot_form_a_section(self):
        # Pooling unattributable paragraphs would join prose from unrelated
        # papers into a section no author ever wrote.
        records = [{"section": "intro", "text": text}
                   for _ in range(40) for text in POOR]
        with fixture.temp_profile(records, prefix="discourse-") as profile:
            result = discourse.calibrate(profile)
            self.assertEqual(result["hedging"], {})
            self.assertEqual(result["cohesion"]["intro"]["n"], 120)


class TestFindingsAndCalibration(unittest.TestCase):
    def test_no_baseline_yields_no_findings_and_unmeasured_axes(self):
        self.assertEqual(discourse.discourse_findings(document(POOR), None), [])
        statuses = discourse.discourse_axis_status(None)
        self.assertEqual({s["status"] for s in statuses}, {"unmeasured"})

    def test_the_two_axes_report_separately(self):
        self.assertEqual([s["axis"] for s in discourse.discourse_axis_status(None)],
                         ["L2.cohesion", "L2.hedging"])

    def test_calibrate_then_detect_round_trip(self):
        with fixture.temp_profile(graded_bank(), prefix="discourse-") as profile:
            result = discourse.calibrate(profile)
            self.assertEqual(result["cohesion"]["intro"]["n"], 120)
            self.assertEqual(result["hedging"]["intro"]["n"], 40)
            rules = {f["rule"] for f in discourse.discourse_findings(
                document(POOR), profile)}
            self.assertIn("discourse-cohesion:intro", rules)
            self.assertIn("discourse-hedging:intro", rules)

    def test_linked_and_hedged_prose_is_not_flagged(self):
        with fixture.temp_profile(graded_bank(), prefix="discourse-") as profile:
            discourse.calibrate(profile)
            self.assertEqual(discourse.discourse_findings(
                document(RICH), profile), [])

    def test_findings_are_advisories_that_name_their_own_artifact(self):
        with fixture.temp_profile(graded_bank(), prefix="discourse-") as profile:
            discourse.calibrate(profile)
            found = discourse.discourse_findings(
                document(POOR), profile)
            self.assertTrue(found)
            for finding in found:
                self.assertEqual(finding["kind"], "advisory")
                self.assertEqual(finding["layer"], "L2")
                feature = finding["observed"]["feature"]
                self.assertEqual(finding["reference"]["provenance"],
                                 discourse.AXES[feature]["baseline"])
                self.assertEqual(finding["reference"]["unit"],
                                 discourse.AXES[feature]["unit"])

    def test_a_reference_with_no_lower_tail_spread_abstains(self):
        # Forty identical passages give the same value at p0 and p10, so an
        # unguarded reading would report every passage as the lowest there is.
        with fixture.temp_profile(fixture.uniform(" ".join(POOR), 40,
                                                  section="intro"),
                                  prefix="discourse-") as profile:
            discourse.calibrate(profile)
            baseline = discourse.LOADERS["hedging"](profile)
            self.assertFalse(
                discourse.resolves_below_gate(baseline["intro"], "hedging"))
            self.assertEqual(discourse.live_buckets("hedging", profile), [])

    def test_small_reference_is_degraded_not_measured(self):
        with fixture.temp_profile(graded_bank(documents=5),
                                  prefix="discourse-") as profile:
            discourse.calibrate(profile)
            statuses = {s["axis"]: s["status"]
                        for s in discourse.discourse_axis_status(profile)}
            self.assertEqual(statuses["L2.hedging"], "degraded")


class TestBucketRestriction(unittest.TestCase):
    """Hedging is calibrated for introductions only, and has to say so."""

    def test_hedging_declares_its_restriction_and_cohesion_declares_none(self):
        self.assertEqual(discourse.AXES["hedging"]["buckets"], ("intro",))
        self.assertIsNone(discourse.AXES["cohesion"]["buckets"])

    def test_a_resolving_bucket_outside_the_restriction_stays_silent(self):
        with fixture.temp_profile(graded_bank(section="method"),
                                  prefix="discourse-") as profile:
            discourse.calibrate(profile)
            # The reference resolves; the restriction is what silences it.
            baseline = discourse.LOADERS["hedging"](profile)
            self.assertTrue(
                discourse.resolves_below_gate(baseline["method"], "hedging"))
            self.assertEqual(discourse.live_buckets("hedging", profile), [])
            self.assertEqual(discourse.live_buckets("cohesion", profile), ["method"])

    def test_status_and_detection_agree_on_which_buckets_are_live(self):
        with fixture.temp_profile(graded_bank(section="method"),
                                  prefix="discourse-") as profile:
            discourse.calibrate(profile)
            statuses = {s["axis"]: s for s in
                        discourse.discourse_axis_status(profile)}
            self.assertEqual(statuses["L2.hedging"]["status"], "degraded")
            rules = {f["rule"] for f in discourse.discourse_findings(
                document(POOR, "Methods"), profile)}
            self.assertNotIn("discourse-hedging:method", rules)
            self.assertIn("discourse-cohesion:method", rules)


class TestLocalReference(unittest.TestCase):
    """The axes on a real locally-built reference, when one is present.

    The plugin ships NO baseline -- every `style-profile/**` artifact is
    gitignored on purpose -- so these never run on a clean clone or in CI. They
    are a smoke check on the author's own corpus, not coverage.
    """

    PROFILE = Path(__file__).resolve().parents[1] / "style-profile" / "wgl"

    def setUp(self):
        if discourse.LOADERS["cohesion"](self.PROFILE) is None:
            self.skipTest(
                "no locally-built wgl discourse baseline (expected on a clean "
                "clone: style-profile artifacts are gitignored)")

    def test_both_axes_are_measured(self):
        statuses = {s["axis"]: s["status"]
                    for s in discourse.discourse_axis_status(self.PROFILE)}
        self.assertEqual(statuses["L2.cohesion"], "measured")
        self.assertEqual(statuses["L2.hedging"], "measured")

    def test_hedging_is_live_for_introductions_only(self):
        self.assertEqual(discourse.live_buckets("hedging", self.PROFILE), ["intro"])

    def test_an_unlinked_flat_introduction_is_flagged_on_both_axes(self):
        rules = {f["rule"] for f in discourse.discourse_findings(
            document(POOR), self.PROFILE)}
        self.assertIn("discourse-cohesion:intro", rules)
        self.assertIn("discourse-hedging:intro", rules)


if __name__ == "__main__":
    unittest.main()
