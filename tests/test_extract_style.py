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

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

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
                r"\section{Results}" "\ntext\n", encoding="utf-8")
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
        # An imported module is not a name this module defines, and naming each
        # one to exclude it (`re`, `defaultdict`, `Path`) put the test one
        # `import` behind its own subject: adding `tex_macros` failed it.
        import types
        import extract_sections as sections
        expected = {n for n in vars(sections)
                    if not n.startswith("__")
                    and not isinstance(vars(sections)[n], types.ModuleType)
                    and getattr(vars(sections)[n], "__module__", "extract_sections")
                    in ("extract_sections", "re", None)
                    and n != "annotations"}
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


class DocumentRootTests(unittest.TestCase):
    r"""A LaTeX bundle is one paper, not one paper per .tex file.

    Measured on the wgl corpus before the 2026-08-25 fix: `tier-1-top` held 20
    .tex files but only 8 papers. Bartelmann & Schneider (2001) alone shipped
    `WeakLens.tex` plus `WeakLens_1..10` and `WeakLens_D`, so that one review
    entered every downstream distribution twelve times at tier-1 weight -- the
    same pseudoreplication the project refuses elsewhere.
    """

    def _bundle(self, tmp: str, files: dict[str, str]) -> list[Path]:
        d = pathlib.Path(tmp) / "bundle"
        d.mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            (d / name).write_text(body, encoding="utf-8")
        return sorted(d.glob("*.tex"))

    def test_included_fragments_are_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tex = self._bundle(tmp, {
                "main.tex": r"\documentclass{article}" "\n"
                            r"\begin{document}" "\n"
                            r"\include{chap_1}" "\n"
                            r"\input{chap_2}" "\n"
                            r"\end{document}" "\n",
                "chap_1.tex": r"\section{Results}" "\nfirst\n",
                "chap_2.tex": r"\section{Discussion}" "\nsecond\n",
            })
            roots = es.select_document_roots(tex)
        self.assertEqual([p.name for p in roots], ["main.tex"])

    def test_unmarked_sibling_of_a_marked_root_is_dropped(self):
        # bib.tex is neither \input nor marked, but it is not a paper either.
        with tempfile.TemporaryDirectory() as tmp:
            tex = self._bundle(tmp, {
                "ms.tex": r"\documentclass{aastex}" "\n"
                          r"\begin{document}" "\nbody\n"
                          r"\end{document}" "\n",
                "bib.tex": r"\bibitem{a} A. Author, 2001" "\n",
            })
            roots = es.select_document_roots(tex)
        self.assertEqual([p.name for p in roots], ["ms.tex"])

    def test_a_lone_unmarked_file_is_still_the_paper(self):
        # Plain-TeX papers predating LaTeX2e carry no document marker at all;
        # Schneider (1996) in the wgl corpus is one, and it IS the paper.
        with tempfile.TemporaryDirectory() as tmp:
            tex = self._bundle(tmp, {
                "aperture.tex": r"\def\ave#1{\langle #1\rangle}" "\n"
                                r"\section{Introduction}" "\nbody\n",
            })
            roots = es.select_document_roots(tex)
        self.assertEqual([p.name for p in roots], ["aperture.tex"])

    def test_documentstyle_counts_as_a_document_marker(self):
        # LaTeX 2.09; still used by pre-1995 arXiv sources such as
        # Kaiser, Squires & Broadhurst (1995) and Refregier (2003).
        with tempfile.TemporaryDirectory() as tmp:
            tex = self._bundle(tmp, {
                "main.tex": r"\documentstyle[aaspp]{article}" "\nbody\n",
                "macros.tex": r"\def\x{1}" "\n",
            })
            roots = es.select_document_roots(tex)
        self.assertEqual([p.name for p in roots], ["main.tex"])

    def test_separate_bundles_do_not_shadow_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name in ("a", "b"):
                d = root / name
                d.mkdir()
                (d / "paper.tex").write_text(r"\section{Results}" "\nx\n",
                                             encoding="utf-8")
            roots = es.select_document_roots(sorted(root.rglob("*.tex")))
        self.assertEqual(len(roots), 2)


class TexDocumentAssemblyTests(unittest.TestCase):
    r"""Dropping a fragment must not drop the prose it holds.

    `WeakLens.tex` is 72 words of \include calls; the ~40,000-word review it
    names lives in the eleven chapter files. Selecting the root and reading
    it with `read_text` is as wrong as counting each chapter as its own
    paper -- it replaces a twelvefold overcount with a total loss.
    """

    def _bundle(self, tmp: str, files: dict[str, str]) -> pathlib.Path:
        d = pathlib.Path(tmp) / "bundle"
        d.mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            (d / name).write_text(body, encoding="utf-8")
        return d

    def test_a_bundle_yields_one_paper_not_the_journal_template(self):
        # 27 of the 500 wgl arXiv bundles ship the journal's class
        # documentation next to the manuscript; mnras_template.tex is a
        # complete sample paper populating all seven buckets, so only the
        # amount of real prose separates it from the submission.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            d = root / "2501.00001"
            d.mkdir()
            (d / "ms.tex").write_text(
                r"\documentclass{mnras}" "\n" r"\section{Results}" "\n"
                + "real " * 400, encoding="utf-8")
            (d / "mnras_template.tex").write_text(
                r"\documentclass{mnras}" "\n" r"\section{Results}" "\n"
                + "sample ", encoding="utf-8")
            roots = es.select_document_roots(sorted(d.glob("*.tex")), root)
        self.assertEqual([p.name for p in roots], ["ms.tex"])

    def test_loose_files_in_the_source_root_stay_independent(self):
        # Two papers dropped straight into a tier dir are two papers; only a
        # SUBDIRECTORY is an arXiv bundle.
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            for name in ("a.tex", "b.tex"):
                (root / name).write_text(
                    r"\documentclass{article}" "\n" r"\section{Results}" "\nx\n",
                    encoding="utf-8")
            roots = es.select_document_roots(sorted(root.glob("*.tex")), root)
        self.assertEqual([p.name for p in roots], ["a.tex", "b.tex"])

    def test_the_whole_bundle_is_read_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "main.tex": r"\documentclass{article}" "\n"
                            r"\include{ch}" "\n",
                "ch.tex": r"\section{Results}" "\nUNIQUE MARKER\n",
            })
            roots = es.select_document_roots(sorted(d.glob("*.tex")))
            self.assertEqual([p.name for p in roots], ["main.tex"])
            analysis = es.analyse_paper(roots[0])
        self.assertEqual(analysis["by_section"]["results"]["plain_text"].count(
            "UNIQUE MARKER"), 1)


class SubsectionInheritanceTests(unittest.TestCase):
    r"""A \subsection belongs to the \section that encloses it.

    The vocabulary names sections, not subsections. "Covariance matrix",
    "Likelihood" and "Blinding" are method prose, but classified alone they
    are `unknown` and discarded -- 54.8% of all section words in the 561-doc
    wgl corpus reached `unknown` that way. The PDF path was fixed on
    2026-08-25; the LaTeX path was not.
    """

    def test_unnamed_subsection_inherits_its_section(self):
        secs = es.split_into_sections(
            r"\section{Methods}" "\nalpha\n"
            r"\subsection{Covariance matrix}" "\nbeta\n")
        self.assertIn("beta", secs["method"])
        self.assertNotIn("unknown", secs)

    def test_a_named_subsection_keeps_its_own_bucket(self):
        secs = es.split_into_sections(
            r"\section{Methods}" "\nalpha\n"
            r"\subsection{Results of the fit}" "\nbeta\n")
        self.assertIn("beta", secs["results"])
        self.assertIn("alpha", secs["method"])

    def test_subsections_of_a_skipped_section_stay_skipped(self):
        secs = es.split_into_sections(
            r"\section{Appendix A}" "\nalpha\n"
            r"\subsection{Covariance matrix}" "\nbeta\n")
        self.assertEqual(secs, {})

    def test_an_unnamed_section_does_not_borrow_the_previous_one(self):
        # "Matter power spectrum" names a topic, not a section role, and is one
        # of the headings the 2026-08-26 sweep deliberately left `unknown`.
        # (It replaced "Cosmological constraints", which that same sweep moved
        # into `results` -- the rule under test is unchanged, the example is.)
        secs = es.split_into_sections(
            r"\section{Methods}" "\nalpha\n"
            r"\section{Matter power spectrum}" "\nbeta\n")
        self.assertIn("beta", secs["unknown"])
        self.assertNotIn("beta", secs["method"])

    def test_a_title_that_is_only_markup_keeps_the_enclosing_bucket(self):
        # `\section{\label{sec:x}}` names nothing; resetting the parent on it
        # turned every following subsection `unknown` in 12 wgl documents.
        secs = es.split_into_sections(
            r"\section{Methods}" "\nalpha\n"
            r"\section{\label{sec:x}}" "\nbeta\n"
            r"\subsection{Some topic}" "\ngamma\n")
        self.assertIn("beta", secs["method"])
        self.assertIn("gamma", secs["method"])
        self.assertNotIn("unknown", secs)


class HeadingCleaningTests(unittest.TestCase):
    """Markup inside a title must not decide the bucket.

    `RE_SECTION` captured `[^}]+`, so it stopped at the first inner brace and
    handed `classify_section` fragments like `Results\\label{sec:res`. The
    capture now spans one level of nesting and `clean_heading` strips what is
    left, so the words the author wrote are what get classified.
    """

    def test_label_inside_the_title_is_dropped(self):
        self.assertEqual(es.clean_heading(r"Results\label{sec:res}"), "Results")
        self.assertEqual(es.classify_section(r"Results\label{sec:res}"), "results")

    def test_a_cross_reference_key_cannot_decide_the_bucket(self):
        # Without stripping, `sec:data` would classify this heading as `data`.
        self.assertEqual(es.classify_section(r"Formalism\label{sec:data}"), "method")

    def test_texorpdfstring_keeps_its_typeset_argument(self):
        self.assertEqual(
            es.clean_heading(r"\texorpdfstring{$\Lambda$CDM}{LCDM} constraints"),
            "CDM constraints")

    def test_spacing_commands_are_dropped(self):
        self.assertEqual(es.clean_heading(r"\hspace*{+0.0mm}Discussion"),
                         "Discussion")

    def test_nested_braces_are_captured_whole(self):
        secs = es.split_into_sections(
            r"\section{Conclusions\label{sec:concl}}" "\nalpha\n")
        self.assertIn("alpha", secs["conclusion"])

    def test_a_markup_only_title_cleans_to_empty(self):
        self.assertEqual(es.clean_heading(r"\label{sec:intro}"), "")

    def test_ambiguous_headings_are_refused_not_guessed(self):
        # Both were frequent fall-throughs in the 2026-08-26 sweep and both
        # were deliberately NOT added: in weak lensing "Shear measurement" is
        # method while "Mass measurements" is results, and "Background" spans
        # intro, method and data. Guessing either is how `method` became the
        # residue this vocabulary exists to prevent.
        for heading in ("Measurements", "Background", "Weak gravitational lensing",
                        "Galaxy clustering"):
            self.assertEqual(es.classify_section(heading), "unknown", heading)


class ReferenceCorpusTests(unittest.TestCase):
    """The breadth corpus is gathered but must stay out of TIER_WEIGHTS.

    The curated tiers are the imitation target and carry the dossier's
    weighted statistics; `REFERENCE_DIR` exists only so the per-section
    reference distributions have observations. Conflating the two roles is
    what left `results` at 26 passages -- under its own 30-passage floor --
    while 500 field papers sat unread under fulltext-arxiv/.
    """

    def _field(self, tmp: str) -> pathlib.Path:
        field = pathlib.Path(tmp)
        for tier in es.TIER_WEIGHTS:
            (field / tier).mkdir(parents=True)
        (field / "tier-1-top" / "curated.tex").write_text(
            r"\section{Results}" "\ncurated\n", encoding="utf-8")
        ref = field / es.REFERENCE_DIR / "2501.00001"
        ref.mkdir(parents=True)
        (ref / "ms.tex").write_text(r"\section{Results}" "\nbreadth\n",
                                    encoding="utf-8")
        return field

    def test_reference_dir_is_gathered_under_its_own_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = es.gather_corpus_files(self._field(tmp))
        self.assertIn(es.REFERENCE_DIR, out)
        self.assertEqual([p.name for p in out[es.REFERENCE_DIR]], ["ms.tex"])

    def test_reference_dir_carries_no_tier_weight(self):
        self.assertNotIn(es.REFERENCE_DIR, es.TIER_WEIGHTS)

    def test_absent_reference_dir_yields_only_tier_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            field = pathlib.Path(tmp)
            for tier in es.TIER_WEIGHTS:
                (field / tier).mkdir(parents=True)
            out = es.gather_corpus_files(field)
        self.assertEqual(set(out), set(es.TIER_WEIGHTS))


class ExemplarRetrievalScopeTests(unittest.TestCase):
    """Retrieval reads the curated tiers; the breadth corpus is opt-in.

    The bank now carries both roles, so an unscoped retrieval would answer
    "show me how this field writes a Results paragraph" with an arbitrary
    arXiv preprint. Tier filtering must also happen after the embedding
    lookup: the `.npy` cache is positional against the full bank.
    """

    def _bank(self):
        return [
            {"section": "results", "tier": "tier-1-top", "text": "curated one"},
            {"section": "results", "tier": es.REFERENCE_DIR, "text": "breadth"},
            {"section": "intro", "tier": "tier-1-top", "text": "intro one"},
        ]

    def test_curated_default_excludes_the_breadth_corpus(self):
        import retrieve_exemplars as rx
        got = rx._retrieve_fallback(self._bank(), "results", "curated", 5,
                                    rx.CURATED_TIERS)
        self.assertEqual([r["text"] for _s, r in got], ["curated one"])

    def test_include_reference_widens_to_the_whole_bank(self):
        import retrieve_exemplars as rx
        got = rx._retrieve_fallback(self._bank(), "results", "", 5,
                                    rx.ALL_TIERS)
        self.assertEqual(len(got), 2)

    def test_data_is_a_retrievable_section(self):
        # `data` was split out of `method` on 2026-08-25 and reached the bank
        # (112 rows) before VALID_SECTIONS learned about it, so --section data
        # was rejected by argparse while the rows sat there.
        import retrieve_exemplars as rx
        self.assertIn("data", rx.VALID_SECTIONS)


class CitationProjectionTests(unittest.TestCase):
    r"""A bibliography key must never reach the prose as a word.

    `RE_TEX_CITE` listed four command names and required the brace to follow
    the name directly. The corpus carries 46 distinct cite-command names over
    75,566 uses, and natbib's `\citep[e.g.][]{key}` -- 8,100 uses -- matched
    none of them, so `RE_TEX_SIMPLE_CMD` substituted the argument as text.
    Measured on 203 held-out refereed papers, 64 of 887 register findings
    (7.2%) were leaked surnames: bethermin, rasia, leroy, ivison, tacconi.
    """

    LEAKY = ["citealp", "citeauthor", "citeyear", "citeyearpar", "citenum",
             "citetalias", "citepalias", "citename", "citepads", "astroncite",
             "Citet", "Citep", "Citealp", "citejap", "citeg"]

    def test_the_optional_argument_form_does_not_leak(self):
        for command in ("cite", "citep", "citet", "citealt"):
            source = r"as shown by \%s[e.g.][]{Bethermin2012} here" % command
            plain = es.latex_to_plain(source)
            self.assertNotIn("Bethermin", plain, command)
            self.assertIn("[CITE]", plain, command)

    def test_every_surveyed_command_name_reduces_to_a_placeholder(self):
        for command in self.LEAKY:
            plain = es.latex_to_plain(r"see \%s{Rasia2014} now" % command)
            self.assertNotIn("Rasia", plain, command)
            self.assertIn("[CITE]", plain, command)

    def test_a_local_macro_the_allowlist_never_saw_is_still_caught(self):
        # \citeiac, \citepf, \putcite -- one paper each. Matching by shape is
        # the only rule that covers a name nobody has written yet.
        plain = es.latex_to_plain(r"see \citewhatever{Ivison2011} now")
        self.assertNotIn("Ivison", plain)
        self.assertIn("[CITE]", plain)

    def test_declarations_leave_nothing_behind(self):
        for source in (r"\nocite{Hutsemekers2010}",
                       r"\defcitealias{Fu2022}{Paper~I}",
                       r"\citestyle{aa}",
                       r"\setcitestyle{citesep={,}}"):
            plain = es.latex_to_plain("before " + source + " after").split()
            self.assertEqual(plain, ["before", "after"], source)

    def test_citetext_keeps_its_prose_and_reduces_its_nested_citations(self):
        plain = es.latex_to_plain(
            r"surveys \citetext{DES Collaboration \citeyear{des2005}} and")
        self.assertIn("DES Collaboration", plain)
        self.assertNotIn("des2005", plain)

    def test_both_projections_treat_citations_alike(self):
        # The two views share one pattern set by design, so a key stripped from
        # one and left in the other would let them disagree about vocabulary.
        source = r"we use \citep[e.g.][]{Tacconi2018} and \citealp{Leroy2013}"
        self.assertNotIn("Tacconi", es.latex_to_numeral_text(source))
        self.assertNotIn("Leroy", es.latex_to_numeral_text(source))
