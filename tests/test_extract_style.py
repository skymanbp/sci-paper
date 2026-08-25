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
import pathlib
import tempfile
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

    def test_thematic_headings_fall_back_to_the_default_bucket(self):
        for heading in ["Aperture mass", "Cosmological background",
                        "Object Detection"]:
            with self.subTest(heading=heading):
                self.assertEqual(es.classify_section(heading),
                                 es.DEFAULT_SECTION_BUCKET)

    def test_default_bucket_is_unknown_rather_than_method(self):
        # `method` was the default until 2026-08-25, so it silently absorbed
        # every unmatched heading: the wgl bank held 1,671 "method" passages
        # against 10 "results". A residue bucket is not a section, and a
        # per-section reference built from one does not describe that section.
        self.assertEqual(es.DEFAULT_SECTION_BUCKET, "unknown")
        self.assertNotEqual(es.DEFAULT_SECTION_BUCKET, "method")

    def test_method_is_reached_by_its_own_vocabulary(self):
        # Because the default moved away from `method`, the bucket only exists
        # if real method headings still land in it.
        for heading in ["Methods", "Methodology", "Weak-lensing analysis",
                        "Simulations", "The model", "Formalism", "Pipeline"]:
            with self.subTest(heading=heading):
                self.assertEqual(es.classify_section(heading), "method")

    def test_data_sections_are_not_counted_as_method(self):
        for heading in ["Data", "Observations", "The data set",
                        "Photometry", "Survey and sample"]:
            with self.subTest(heading=heading):
                self.assertEqual(es.classify_section(heading), "data")


class PdfHeadingTests(unittest.TestCase):
    """A PDF text layer interleaves table cells with prose.

    Every string below was taken from the 90-PDF wgl corpus, where the
    pre-2026-08-25 ALL-CAPS heuristic accepted 305 of 325 "headings" that were
    really table cells. Each accepted cell switched the current section bucket,
    so the prose after a table was filed under whatever the cell classified as.
    """

    TABLE_CELLS = ["S", "X", "N", "RA", "O", "XS", "RS|", "S/N", "SO", "Z",
                   "gNFW", "NFW", "XSO", "P", "RA (J2000)", "E", "R", "ID",
                   "BCG", "A85", "A1606", "(1014 M)", "B =", "XL", "L", "D"]

    def test_table_cells_are_not_headings(self):
        for cell in self.TABLE_CELLS:
            with self.subTest(cell=cell):
                self.assertIsNone(es._classify_pdf_heading(cell))

    def test_real_headings_survive_the_tightened_thresholds(self):
        expected = {"1. Introduction": "intro", "INTRODUCTION": "intro",
                    "3 RESULTS": "results", "Conclusions": "conclusion",
                    "2 Data": "data"}
        for heading, bucket in expected.items():
            with self.subTest(heading=heading):
                self.assertEqual(es._classify_pdf_heading(heading), bucket)


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


class CorpusGatheringTests(unittest.TestCase):
    """`gather_corpus_files` must return its dict.

    The 2026-08-25 split of extract_style.py cut this function's `return out`
    off its end: the line moved into the new module, where it parsed as dead
    code after another function's return, so imports succeeded and the whole
    suite stayed green while extraction died with 'NoneType has no attribute
    values' on the first real run. Nothing asserted the return value.
    """

    def test_returns_a_tier_keyed_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            field = pathlib.Path(tmp)
            for tier in ("tier-1-top", "tier-2-mentor", "tier-3-reference"):
                (field / tier).mkdir(parents=True)
            (field / "tier-1-top" / "paper.tex").write_text(
                "\section{Results}\ntext\n", encoding="utf-8")
            out = es.gather_corpus_files(field)
        self.assertIsInstance(out, dict)
        self.assertEqual(set(out), {"tier-1-top", "tier-2-mentor", "tier-3-reference"})
        self.assertEqual([p.name for p in out["tier-1-top"]], ["paper.tex"])
        self.assertEqual(out["tier-2-mentor"], [])


class PdfParagraphRejoinTests(unittest.TestCase):
    """A PDF text layer emits line fragments, not paragraphs.

    Measured over two corpus PDFs before the 2026-08-25 fix: blocks ran to a
    median of 5 and 16 words and only 21-23% ended a sentence. Downstream the
    exemplar bank drops paragraphs under 30 words and `document_shape` needs
    sections with two substantial paragraphs each, so a 90-PDF corpus produced
    exemplars from 3 files and complete papers reduced to one section.
    """

    def test_line_fragments_rejoin_into_one_paragraph(self):
        out = es._rejoin_pdf_paragraphs(
            ["A Broad Examination on Bacterial Responses to a",
             "Wide Range of Biocide Chemicals and Exploration",
             "of Potential Biosensor Strategy."])
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].endswith("Strategy."))

    def test_sentence_terminal_blocks_stay_separate(self):
        out = es._rejoin_pdf_paragraphs(["First paragraph ends here.",
                                         "Second paragraph starts here."])
        self.assertEqual(len(out), 2)

    def test_headings_are_never_absorbed_or_absorbing(self):
        # A heading must survive on its own line or split_pdf_into_sections
        # cannot see it, and the bucket never switches.
        out = es._rejoin_pdf_paragraphs(
            ["a fragment with no full stop", "1. Introduction",
             "body text after the heading"])
        self.assertIn("1. Introduction", out)
        self.assertEqual(out[out.index("1. Introduction") + 1],
                         "body text after the heading")

    def test_closing_punctuation_after_the_stop_still_terminates(self):
        out = es._rejoin_pdf_paragraphs(['He called it "settled."',
                                         "A new paragraph."])
        self.assertEqual(len(out), 2)


class ReExportContractTests(unittest.TestCase):
    """`extract_style` must re-export everything `extract_sections` defines.

    Eight sibling tools and this file reach these names as `es.<name>`. The
    re-export list is hand-written, so it can silently fall behind the module
    it mirrors -- which it did the moment `_rejoin_pdf_paragraphs` was added.
    """

    def test_every_public_name_is_re_exported(self):
        import extract_sections as sections
        expected = {n for n in vars(sections)
                    if not n.startswith("__")
                    and getattr(vars(sections)[n], "__module__", "extract_sections")
                    in ("extract_sections", "re", None)
                    and n not in {"annotations", "re", "defaultdict", "Path"}}
        missing = sorted(n for n in expected if not hasattr(es, n))
        self.assertEqual(missing, [], f"extract_style does not re-export: {missing}")


class NumberedHeadingTests(unittest.TestCase):
    """Journals set section titles in title case behind a number.

    "2.1. Marine Ice Sheet Instability" matches neither the keyword list nor
    the ALL-CAPS branch, so before 2026-08-25 such titles were absorbed into
    the following paragraph and their documents collapsed to one section.
    """

    def test_numbered_title_case_headings_are_detected(self):
        for heading in ["2.1.  Marine Ice Sheet Instability",
                        "3.  Controversial Ideas to MICI",
                        "4 Detector Response Model"]:
            with self.subTest(heading=heading):
                self.assertIsNotNone(es._classify_pdf_heading(heading))

    def test_numbered_prose_sentences_are_not_headings(self):
        # A numbered list item inside prose ends a sentence or runs long.
        for line in ["1. We first calibrate the detector against a known source.",
                     "2. " + " ".join(["word"] * 20)]:
            with self.subTest(line=line[:40]):
                self.assertIsNone(es._classify_pdf_heading(line))

    def test_numeric_table_cells_are_still_rejected(self):
        for cell in ["1. 2", "2. x", "3 4 5"]:
            with self.subTest(cell=cell):
                self.assertIsNone(es._classify_pdf_heading(cell))
