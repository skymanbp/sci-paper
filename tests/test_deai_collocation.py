from __future__ import annotations

import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import _profilefixture as fixture
import deai_collocation as collocation


# A bank with spread. Every passage repeats the field's shared sentences (so
# their pairs are attested many times over) and adds one sentence with one,
# two or four pairs of its own: under leave-one-out that sentence carries
# novel pairs, so the reference distribution has an upper tail to gate on.
SHARED = (
    "The aperture mass is measured on the shear catalog around each cluster. "
    "The tangential shear is convolved with a compensated filter of fixed scale. "
    "The detection threshold is set by the noise of the aperture mass map. "
    "The shape noise of the source galaxies sets the detection floor.")
MODIFIERS = ("calibrated", "controlled", "empty", "physical", "deployed",
             "clamped", "rescored", "strict")
NOUNS = ("filter", "grid", "saddle", "cell", "boundary", "catalog", "map", "floor")
# Pseudo-words that occur in exactly one passage each (letters only: the word
# regex admits no digits).
COINED = ["".join(letters) for letters in itertools.product("bcdfgh", repeat=3)]


def records(count: int = 64) -> list[dict]:
    out = []
    for index in range(count):
        pair = f"{MODIFIERS[index % 8]} {NOUNS[(index // 8) % 8]}"
        first, second = COINED[index], COINED[count + index]
        own = {
            0: f"The {pair} response of the aperture mass filter sets the "
               "detection threshold here.",
            1: f"The {pair} response of the {first} aperture mass filter sets the "
               "detection threshold here.",
            2: f"The {pair} response of the {first} aperture mass {second} filter "
               "sets the detection threshold here.",
        }[index % 3]
        out.append({"section": "method", "source": f"paper-{index:03d}.tex",
                    "text": SHARED + " " + own})
    return out


ATTESTED = ("\\section{Methods}\nThe aperture mass is measured on the shear "
            "catalog around each cluster. The tangential shear is convolved with "
            "a compensated filter of fixed scale.\n")
# Every word below is common in the bank; none of the pairs is written by it.
NOVEL = ("\\section{Methods}\nThe calibrated saddle deployed a physical floor "
         "grid catalog for the empty threshold filter response map.\n")


class ContentPairTests(unittest.TestCase):
    def test_function_words_are_not_partners(self):
        pairs = collocation.content_pairs("The map of the shear is measured.")
        self.assertNotIn(("map", "the"), pairs)
        self.assertNotIn(("the", "shear"), pairs)

    def test_adjacent_content_words_pair_in_order(self):
        pairs = collocation.content_pairs("The calibrated blur sets the floor.")
        self.assertIn(("calibrated", "blur"), pairs)
        self.assertNotIn(("blur", "calibrated"), pairs)

    def test_punctuation_and_placeholders_break_a_pair(self):
        pairs = collocation.content_pairs(
            "The filter yields, separate profiles [math] keeps (the) noise floor.")
        self.assertNotIn(("yields", "separate"), pairs)
        self.assertNotIn(("profiles", "keeps"), pairs)
        self.assertIn(("separate", "profiles"), pairs)
        self.assertIn(("noise", "floor"), pairs)


class CalibrationTests(unittest.TestCase):
    def test_calibrate_writes_the_bank_and_a_sentence_unit_reference(self):
        with fixture.temp_profile(records()) as profile:
            result = collocation.calibrate(profile)
            bank = json.loads((profile / collocation.BANK_FILENAME).read_text("utf-8"))
            self.assertEqual(bank["n_passages"], 64)
            self.assertEqual(bank["pair_df"].get("aperture mass"), 64)
            baseline = result["baseline"]["method"]
            self.assertEqual(baseline["unit"], "sentence")
            self.assertGreaterEqual(baseline["n"], collocation.MIN_REFERENCE_N)

    def test_the_reference_is_leave_one_out(self):
        # Each passage's own modifier-noun sentence must read as novel to the
        # bank, otherwise every calibration sentence scores zero and the gate
        # has nothing above it to resolve.
        with fixture.temp_profile(records()) as profile:
            collocation.calibrate(profile)
            baseline = collocation.load_baseline(profile)["method"]
            top = float(baseline["percentiles"][collocation.FEATURE]["1.0"])
            self.assertGreater(top, 0.0)

    def test_a_rare_word_is_not_a_partner(self):
        with fixture.temp_profile(records()) as profile:
            collocation.calibrate(profile)
            bank = collocation.load_bank(profile)
            verdict = collocation.judge_sentence(
                "The zzyzx filter zzyzx catalog zzyzx map zzyzx floor is set.", bank)
            self.assertIsNone(verdict)   # fewer than MIN_JUDGED judged pairs


class FindingTests(unittest.TestCase):
    def test_a_sentence_of_attested_pairs_is_not_flagged(self):
        with fixture.temp_profile(records()) as profile:
            collocation.calibrate(profile)
            self.assertEqual(collocation.collocation_findings(ATTESTED, profile), [])

    def test_a_sentence_of_novel_pairs_is_flagged_with_each_pair_weighed(self):
        with fixture.temp_profile(records()) as profile:
            collocation.calibrate(profile)
            findings = collocation.collocation_findings(NOVEL, profile)
            self.assertEqual(len(findings), 1)
            (finding,) = findings
            self.assertEqual((finding["kind"], finding["layer"], finding["rule"]),
                             ("advisory", "L2", "collocation-novel:method"))
            self.assertGreater(finding["observed"]["novel_pairs"], 0)
            pair = finding["observed"]["pairs"][0]
            # Co-presence, named as such: the bank knows which passages hold a
            # word, not where, so the weight is not an adjacency probability.
            self.assertIn("expected_copresent_passages", pair)
            self.assertLessEqual(pair["p_copresence_absent"], 1.0)
            self.assertIn("coins", finding["recommended_action"])
            # The unit is the sentence, in the schema as in the reference, and
            # a sentence-unit finding cannot claim more than the paragraph cap.
            self.assertEqual((finding["scope"], finding["calibration_unit"]),
                             ("sentence", "sentence"))
            self.assertLessEqual(finding["confidence"]["value"], 0.5)

    def test_a_slash_a_number_or_a_bare_stop_breaks_a_pair(self):
        for sentence in ("The alpha/beta filter keeps the noise floor.",
                         "The alpha 500 beta filter keeps the noise floor.",
                         "The alpha.beta filter keeps the noise floor."):
            pairs = collocation.content_pairs(sentence)
            self.assertNotIn(("alpha", "beta"), pairs, sentence)
            self.assertIn(("noise", "floor"), pairs, sentence)

    def test_no_bank_is_unmeasured_not_clean(self):
        with tempfile.TemporaryDirectory(prefix="colloc-") as raw:
            profile = Path(raw)
            self.assertEqual(collocation.collocation_findings(NOVEL, profile), [])
            status = collocation.collocation_axis_status(profile)
            self.assertEqual(status["status"], "unmeasured")
            self.assertIn(collocation.BANK_FILENAME, status["reason"])

    def test_a_flat_reference_abstains(self):
        # Every passage identical: every pair attested 40 times, no sentence
        # novel under leave-one-out, so the reference has no upper tail and
        # the axis must abstain rather than call a typical sentence p100.
        with fixture.temp_profile(fixture.uniform(SHARED, 40, section="method")) as profile:
            collocation.calibrate(profile)
            self.assertEqual(collocation.collocation_findings(NOVEL, profile), [])
            self.assertEqual(collocation.collocation_axis_status(profile)["status"],
                             "degraded")

    def test_the_document_fraction_is_evidence_in_the_axis_status(self):
        with fixture.temp_profile(records()) as profile:
            collocation.calibrate(profile)
            status = collocation.collocation_axis_status(profile, NOVEL)
            self.assertEqual(status["status"], "measured")
            self.assertIn("document novel-pair fraction", status["reason"])
            self.assertIn("not a percentile", status["reason"])


class CliTests(unittest.TestCase):
    def test_the_report_is_the_shared_schema(self):
        with fixture.temp_profile(records()) as profile:
            collocation.calibrate(profile)
            target = profile / "draft.tex"
            target.write_text(NOVEL, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(TOOLS / "deai_collocation.py"), str(target),
                 "--field", profile.name, "--profile-root", str(profile.parent)],
                text=True, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("axis L2.collocation: measured", result.stdout)
            self.assertIn("collocation-novel:method", result.stdout)


if __name__ == "__main__":
    unittest.main()
