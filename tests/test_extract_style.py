"""Section bucketing and LaTeX projection contracts for extract_style.

`extract_style` is the canonical reduction layer: eight sibling tools import it
for `classify_section`, `latex_to_plain` and `latex_to_numeral_text`, and every
per-section reference distribution in the profile is keyed by the bucket this
module assigns. It had no test file until 2026-08-16, which is how the
singular-only section vocabulary survived: `\\bresult\\b` never matched the
plural "Results", so the standard ApJ/MNRAS/PRD headings fell through to
DEFAULT_SECTION_BUCKET and a 31-paper corpus produced 1770 `method` paragraphs
and zero `results` ones.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import extract_style as es


class SectionClassificationTests(unittest.TestCase):
    """Journal headings are plural far more often than singular."""

    def test_plural_headings_bucket_like_their_singular(self):
        for singular, plural in [
            ("Result", "Results"),
            ("Conclusion", "Conclusions"),
            ("Introduction", "Introductions"),
            ("Discussion", "Discussions"),
            ("Limitation", "Limitations"),
            ("Implication", "Implications"),
            ("Comparison", "Comparisons"),
            ("Caveat", "Caveats"),
            ("Motivation", "Motivations"),
        ]:
            with self.subTest(heading=plural):
                self.assertEqual(es.classify_section(plural),
                                 es.classify_section(singular))

    def test_canonical_journal_headings(self):
        expected = {
            "Abstract": "abstract",
            "Introduction": "intro",
            "Methods": "method",
            "Results": "results",
            "Conclusions": "conclusion",
            "Summary": "conclusion",
            "Summaries": "conclusion",
            "Discussion": "discussion",
            "Systematics": "discussion",
            "Systematic Errors": "discussion",
        }
        for heading, bucket in expected.items():
            with self.subTest(heading=heading):
                self.assertEqual(es.classify_section(heading), bucket)

    def test_results_is_not_silently_bucketed_as_method(self):
        # The regression itself: the plural heading must not land in the
        # default bucket, which would measure a Results section against the
        # methods reference distribution.
        self.assertNotEqual(es.classify_section("Results"),
                            es.DEFAULT_SECTION_BUCKET)
        self.assertNotEqual(es.classify_section("Conclusions"),
                            es.DEFAULT_SECTION_BUCKET)

    def test_back_matter_is_skipped_in_both_numbers(self):
        for heading in ["Appendix", "Appendices", "Appendix A",
                        "Acknowledgements", "References", "Bibliography"]:
            with self.subTest(heading=heading):
                self.assertEqual(es.classify_section(heading), "skip")

    def test_discussion_outranks_conclusion_in_combined_headings(self):
        # Documented ordering: the richer bucket wins a combined heading.
        self.assertEqual(es.classify_section("Discussion and Conclusions"),
                         "discussion")
        self.assertEqual(es.classify_section("Summary and discussion"),
                         "discussion")

    def test_thematic_headings_fall_back_to_method(self):
        for heading in ["Aperture mass", "Cosmological background",
                        "Object Detection"]:
            with self.subTest(heading=heading):
                self.assertEqual(es.classify_section(heading),
                                 es.DEFAULT_SECTION_BUCKET)


class LigatureTests(unittest.TestCase):
    """PDF text layers emit ligatures as single codepoints."""

    def test_ligatures_expand_to_their_letters(self):
        source = "The ﬁrst eﬀect is signiﬁcant and inﬂated."
        expanded = source.translate(es.LIGATURE_TABLE)
        self.assertEqual(expanded,
                         "The first effect is significant and inflated.")

    def test_expansion_keeps_words_whole_for_the_tokenizer(self):
        # Unexpanded, the tokenizer splits "significant" into fragments that
        # enter the lexicon and the exemplar bank as if they were words.
        self.assertNotIn("signi", es.words("signiﬁcant".translate(es.LIGATURE_TABLE)))
        self.assertIn("significant", es.words("signiﬁcant".translate(es.LIGATURE_TABLE)))


class LatexProjectionTests(unittest.TestCase):
    """The two named projections differ only inside inline math."""

    SOURCE = r"We measure $\sigma_8 = 0.81$ across 14 fields \citep{Smith2024}."

    def test_latex_to_plain_erases_inline_math_numerals(self):
        plain = es.latex_to_plain(self.SOURCE)
        self.assertNotIn("0.81", plain)
        self.assertIn("14", plain)

    def test_latex_to_numeral_text_preserves_inline_math_numerals(self):
        numeral = es.latex_to_numeral_text(self.SOURCE)
        self.assertIn("0.81", numeral)
        self.assertIn("14", numeral)

    def test_both_projections_drop_display_math(self):
        source = "Before.\n\\begin{equation}\nA = 42\n\\end{equation}\nAfter."
        for projection in (es.latex_to_plain, es.latex_to_numeral_text):
            with self.subTest(projection=projection.__name__):
                self.assertNotIn("42", projection(source))


if __name__ == "__main__":
    unittest.main()
