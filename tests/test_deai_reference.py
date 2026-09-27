"""deai_reference.paragraphs yields prose units only.

Headings and floats are blanked in place so every unit keeps its line
number, and blanking a `\\section{...}\\label{...}` line leaves the label
and a run of spaces behind; a comment-only block never had prose at all.
Until v0.36.3 both reached every per-paragraph axis as units of their own:
GPT-2 tokenises forty-eight spaces into more than the UID minimum, so four
heading lines of a manuscript under review were reported as paragraphs of
near-zero surprisal variance (z = -7), and a `% SCOPE:` comment block
counted as a unit of the removal map.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import _profilefixture as fixture
import deai_reference as reference

PROSE = "The estimator uses five filters and reports the peak height. " * 3
DISPLAY = "\\begin{equation}\nS = a + b\n\\end{equation}"

TEXT = "\n".join([
    "\\section{Introduction}\\label{sec:intro}",      # 1: heading + trailing label
    "",
    PROSE,                                           # 3
    "",
    "% SCOPE: what this section covers",              # 5: comment-only block
    "% and a second comment line",
    "",
    PROSE,                                           # 8
    "",
    "\\section{Results}",                            # 10
    "\\label{sec:results}",                          # 11: label on its own line
    "",
    DISPLAY,                                         # 13-15: math-only paragraph
    "",
    PROSE,                                           # 17
    "",
    "\\section{Appendix}\\label{sec:app}",           # 19: a section holding no prose
    "",
])


class ParagraphSweepTests(unittest.TestCase):
    def test_units_are_prose_or_math_never_labels_or_comments(self):
        units = [(start, end, bucket) for start, end, _raw, bucket, _block
                 in reference.paragraphs(TEXT)]
        self.assertEqual(units, [(3, 3, "intro"), (8, 8, "intro"),
                                 (13, 15, "results"), (17, 17, "results")])

    def test_math_only_paragraph_keeps_its_block(self):
        blocks = {start: block for start, _end, _raw, _bucket, block
                  in reference.paragraphs(TEXT)}
        self.assertIn("\\begin{equation}", blocks[13])

    def test_section_of_labels_alone_is_not_a_section_unit(self):
        buckets = [bucket for _start, _end, bucket, _block in reference.sections(TEXT)]
        self.assertEqual(buckets, ["intro", "results"])

    def test_a_bucket_split_over_subsections_is_one_section_unit(self):
        # The reference side pools a paper's paragraphs per bucket (that is how
        # the corpus splitter cuts a paper); read per heading span, a 150-word
        # subsection was compared with references pooled over whole papers.
        text = "\n".join(["\\section{Methods}", "\\subsection{Filter}", PROSE,
                          "\\subsection{Noise}", PROSE, "\\section{Results}", PROSE])
        found = reference.sections(text)
        self.assertEqual([(start, end, bucket) for start, end, bucket, _ in found],
                         [(1, 5, "method"), (6, 7, "results")])
        self.assertEqual(found[0][3].count(PROSE.strip()), 2)


class QuantileGridTests(unittest.TestCase):
    """The stored p_q point is the first order statistic with P(X <= x) >= q.

    The grid read floor(q * n) until 2026-09-27 -- one order statistic high:
    p90 of 100 values was the 91st smallest, and at the 30-unit floor p10 and
    p90 sat at P = 0.133 and 0.933. Every rate recorded against an artifact
    calibrated before that date was read at those shifted points.
    """

    def test_nearest_rank_on_a_hundred_values(self):
        grid = reference.quantiles([float(v) for v in range(100)])
        self.assertEqual((grid["0.0"], grid["0.1"], grid["0.5"], grid["0.9"], grid["1.0"]),
                         (0.0, 9.0, 49.0, 89.0, 99.0))

    def test_every_grid_point_is_the_smallest_rank_at_or_past_q(self):
        n = 100
        grid = reference.quantiles([float(v) for v in range(n)])
        for q, value in grid.items():
            rank = int(value) + 1  # values are 0..99, so value + 1 is its rank
            self.assertGreaterEqual(rank / n, float(q), q)
            if float(q) > 0:
                self.assertLess((rank - 1) / n, float(q), q)

    def test_the_floor_bucket_reads_its_tails_at_the_nominal_rate(self):
        grid = reference.quantiles([float(v) for v in range(30)])
        self.assertEqual((grid["0.1"], grid["0.9"]), (2.0, 26.0))  # 3rd and 27th smallest

    def test_a_single_value_fills_the_grid(self):
        self.assertEqual(set(reference.quantiles([5.0]).values()), {5.0})


class ArtifactUnitTests(unittest.TestCase):
    """The unit an artifact records is read back, not merely written."""

    BASELINE = {"intro": {"n": 40, "unit": "section", "percentiles": {
                    "hedging": {"0.0": 0.0, "0.1": 1.0, "1.0": 5.0}}},
                "method": {"n": 40, "unit": "paragraph", "percentiles": {
                    "hedging": {"0.0": 0.0, "0.1": 1.0, "1.0": 5.0}}},
                "data": {"n": 40, "percentiles": {
                    "hedging": {"0.0": 0.0, "0.1": 1.0, "1.0": 5.0}}}}

    def test_a_bucket_built_at_another_unit_is_not_usable(self):
        self.assertEqual(reference.usable_buckets(self.BASELINE, "hedging", 0.1,
                                                  high=False, unit="section"),
                         ["intro"])

    def test_the_foreign_units_are_named_with_what_they_record(self):
        self.assertEqual(reference.foreign_units(self.BASELINE, "section"),
                         {"method": "paragraph", "data": "unrecorded"})
        reason = reference.unit_reason(self.BASELINE, "section")
        self.assertIn("method (paragraph)", reason)
        self.assertIn("recalibrate", reason)
        self.assertIsNone(reference.unit_reason({"intro": self.BASELINE["intro"]}, "section"))

    def test_only_the_buckets_the_axis_would_read_count(self):
        intro = [(1, 3, "intro", "prose")]
        self.assertIsNone(reference.unit_reason(self.BASELINE, "section", intro))
        reason = reference.unit_reason(self.BASELINE, "section",
                                       intro + [(4, 6, "method", "prose")])
        self.assertIn("method (paragraph)", reason)
        self.assertNotIn("data", reason)
        self.assertIsNone(reference.unit_reason(self.BASELINE, "section", allowed=("intro",)))


class UnbucketedUnitsTests(unittest.TestCase):
    def test_untitled_prose_is_counted_as_unmeasured(self):
        text = PROSE + "\n\n" + PROSE
        reason = reference.unbucketed_reason(reference.units(text), "paragraph")
        self.assertTrue(reason.startswith("2 of 2 paragraph units carry no calibrated bucket"))

    def test_a_topic_heading_is_unmeasured_and_a_role_heading_is_not(self):
        self.assertIsNone(reference.unbucketed_reason(
            reference.units("\\section{Methods}\n" + PROSE), "paragraph"))
        self.assertIsNotNone(reference.unbucketed_reason(
            reference.units("\\section{Weak lensing}\n" + PROSE), "paragraph"))


class SentenceLineTests(unittest.TestCase):
    BLOCK = "The shear is measured \\citep{x}\nhere. The \\emph{map}\nis drawn now."

    def test_the_second_sentence_starts_on_its_own_line(self):
        self.assertEqual(reference.sentence_lines(self.BLOCK, 10, "The map is drawn now."),
                         (11, 12))

    def test_a_citation_between_two_words_does_not_hide_the_sentence(self):
        self.assertEqual(reference.sentence_lines(
            self.BLOCK, 10, "The shear is measured [CITE] here."), (10, 11))

    def test_an_unlocatable_sentence_keeps_the_unit_range(self):
        self.assertEqual(reference.sentence_lines(self.BLOCK, 10, "Absent words here."),
                         (10, 12))


class CalibrationRecordTests(unittest.TestCase):
    def test_no_reference_record_means_none_and_nothing_written(self):
        with tempfile.TemporaryDirectory(prefix="reference-") as raw:
            profile = Path(raw)
            written = reference.calibrate(
                profile, "x_baseline.json", ("f",), lambda text: {"f": 1.0},
                reference.passage_banks(profile))
            self.assertIsNone(written)
            self.assertFalse((profile / "x_baseline.json").exists())

    def test_rows_read_on_the_fallback_projection_are_counted_per_bucket(self):
        rows = fixture.uniform("The rate is $3$ here.", 4, section="method")
        rows[0]["numeral_text"] = "The rate is 3 here."
        with fixture.temp_profile(rows) as profile:
            with (profile / "human_abstracts_extra.jsonl").open("w", encoding="utf-8") as handle:
                handle.write(json.dumps({"text": "An abstract in LaTeX."}) + "\n")
            tally: Counter[str] = Counter()
            records = list(reference._bank_records(
                reference.passage_banks(profile), text_key="numeral_text", fallbacks=tally))
        # Three exemplar rows fell back; the abstract bank never has the key
        # by design (it stores source) and is not a fallback.
        self.assertEqual(tally, Counter({"method": 3}))
        self.assertEqual(len(records), 5)
        self.assertEqual(records[0][2], "The rate is 3 here.")


if __name__ == "__main__":
    unittest.main()
