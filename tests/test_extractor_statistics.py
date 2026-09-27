"""Extractor statistics and projection forms pinned by the 2026-09-27 audit.

Split from test_extract_style.py, which sits at the 750-line budget.
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import extract_style as es


class DisplayMathFormsTests(unittest.TestCase):
    """Every way LaTeX writes display mathematics is display mathematics."""

    def test_bracket_display_math_is_not_prose(self):
        self.assertEqual(es.prose_words(r"We have \[ E = m c^2 \] here."),
                         ["We", "have", "here."])

    def test_dollar_dollar_display_math_does_not_swallow_prose(self):
        # Matched from its second dollar by the INLINE pattern, `$$x=1$$` paired
        # with the next inline `$` and the prose between vanished from the
        # plain view alone, so the two projections no longer agreed.
        plain = es.latex_to_plain("First $$x=1$$ prose words survive here $y$ end.")
        self.assertIn("prose words survive here", plain)
        numeral = es.latex_to_numeral_text("First $$x=1$$ prose words survive here $y$ end.")
        self.assertIn("prose words survive here", numeral)

    def test_subequations_are_a_display_environment(self):
        plain = es.latex_to_plain(
            "A \\begin{subequations}\\begin{align}x=1\\end{align}\\end{subequations} B")
        self.assertEqual(plain.split(), ["A", "[MATH]", "B"])


class ExtractorStatisticsTests(unittest.TestCase):
    """The 2026-09-27 audit's extractor findings, each pinned."""

    def test_multi_word_openers_can_be_observed(self):
        # `paragraph_initial_words` records one word per paragraph, so the five
        # phrases were always reported absent from every corpus.
        text = "In recent years the field grew.\n\nRecent advances helped.\n"
        self.assertEqual(es.paragraph_initial_phrases(text),
                         ["In recent years", "Recent advances"])
        paper = {"by_section": {"intro": {
            "paragraph_initial_words": es.paragraph_initial_words(text),
            "paragraph_initial_phrases": es.paragraph_initial_phrases(text)}}}
        transitions = es.aggregate_transitions([(1.0, paper)])
        self.assertIn(("In recent years", 1), transitions["blacklist_present_in_corpus"])
        self.assertNotIn("In recent years", transitions["blacklist_absent_from_corpus"])
        self.assertEqual(transitions["n_paragraphs"], 2)

    def test_an_empty_corpus_reports_zero_paragraphs(self):
        self.assertEqual(es.aggregate_transitions([])["n_paragraphs"], 0)

    def test_placeholders_are_not_words_and_do_not_drop_a_paragraph(self):
        self.assertEqual(es.words(es.without_placeholders("[CITE] [math] x")), ["x"])
        # A citation-led paragraph is prose; a placeholder-only one is not.
        text = "[CITE] showed the effect.\n\n[MATH]\n\n[FIGURE-OR-TABLE] and more."
        self.assertEqual(es.paragraph_initial_words(text), ["showed", "and"])

    def test_words_are_unicode_letters(self):
        self.assertEqual(es.words("naïve Poincaré"), ["naïve", "Poincaré"])

    def test_bank_rows_count_prose_words_and_carry_unique_ids(self):
        prose = " ".join(f"word{i}" for i in range(EXEMPLAR_MIN))
        plain = f"[CITE] {prose}\n\n{prose}"
        paper = {"tier": "tier-1-top", "source_path": "p.tex",
                 "by_section": {"intro": {"plain_text": plain},
                                "results": {"plain_text": plain}}}
        with tempfile.TemporaryDirectory() as tmp:
            n = es.write_exemplar_bank([(1.0, paper)], pathlib.Path(tmp))
            rows = [json.loads(line) for line in
                    (pathlib.Path(tmp) / "exemplar_paragraphs.jsonl").read_text().splitlines()]
        self.assertEqual(n, 4)
        self.assertEqual(len({row["id"] for row in rows}), 4)
        self.assertTrue(all(row["n_words"] == EXEMPLAR_MIN for row in rows))

    def test_the_profile_directory_is_not_created_for_an_empty_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            corpus = pathlib.Path(tmp) / "corpus"
            for tier in ("tier-1-top", "tier-2-mentor", "tier-3-reference"):
                (corpus / "g" / tier).mkdir(parents=True)
            profile = pathlib.Path(tmp) / "profile"
            code = es.main(["--field", "g", "--corpus-root", str(corpus),
                            "--profile-root", str(profile)])
        self.assertEqual(code, 1)
        self.assertFalse((profile / "g").exists())


EXEMPLAR_MIN = 30


class FallbackRetrievalTests(unittest.TestCase):
    def test_an_empty_topic_ranks_by_section_name_in_the_fallback(self):
        import retrieve_exemplars as rx
        records = [{"section": "results", "tier": "tier-1-top", "text": "unrelated prose"},
                   {"section": "results", "tier": "tier-1-top",
                    "text": "the results section states the results"}]
        ranked = rx._retrieve_fallback(records, "results", "", 2, {"tier-1-top"})
        self.assertGreater(ranked[0][0], 0.0)
        self.assertIn("results section", ranked[0][1]["text"])



if __name__ == "__main__":
    unittest.main()
