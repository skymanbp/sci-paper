"""Extractor statistics and projection forms pinned by the 2026-09-27 audit.

Split from test_extract_style.py, which sits at the 750-line budget.
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

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

    def test_every_placeholder_the_projection_writes_is_dropped_by_its_readers(self):
        # One vocabulary (`PLAIN_INLINE`, `PLAIN_PLACEHOLDERS`); the three
        # patterns that read it were typed out by hand until audit D23.
        import deai_reference
        for token in (es.PLAIN_INLINE, *es.PLAIN_PLACEHOLDERS.values()):
            with self.subTest(token=token):
                self.assertRegex(token.strip(), es.RE_PLACEHOLDER)
                self.assertEqual(es.without_placeholders(token).strip(), "")
                self.assertEqual(deai_reference.RE_PLACEHOLDER_TOKEN.sub("", token).strip(), "")

    def test_words_are_unicode_letters(self):
        self.assertEqual(es.words("naïve Poincaré"), ["naïve", "Poincaré"])

    def test_a_compound_is_one_word(self):
        # The Unicode class first shipped without `-` and `'`, so every
        # compound counted twice in the bank's 30-400-word admission band.
        self.assertEqual(es.words("N-body O'Brien's two-point naïve-looking 3-D"),
                         ["N-body", "O'Brien's", "two-point", "naïve-looking", "D"])

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


class EmbeddingCacheTests(unittest.TestCase):
    """The `.npy` cache is keyed by the bank's content, not by mtime (audit D20)."""

    def test_a_same_size_rebuild_with_other_rows_is_re_encoded(self):
        try:
            import numpy as np
        except ImportError:  # CI runs without optional dependencies
            self.skipTest("numpy is unavailable")
        import os
        import sys
        import types
        from unittest import mock
        import retrieve_exemplars as rx
        calls = []

        class FakeModel:
            def __init__(self, _name):
                pass

            def encode(self, texts, **_options):
                calls.append(list(texts))
                return np.array([[float(len(text)), 1.0] for text in texts])

        fake = types.SimpleNamespace(SentenceTransformer=FakeModel)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(sys.modules, {"sentence_transformers": fake}):
            profile = pathlib.Path(tmp)
            bank = profile / "exemplar_paragraphs.jsonl"

            def write(texts):
                bank.write_text("".join(json.dumps({"text": t}) + "\n" for t in texts),
                                encoding="utf-8")
                return rx._load_records(bank)

            records = write(["aa", "bbbb"])
            rx._build_or_load_embeddings(records, bank, profile, "m")
            rx._build_or_load_embeddings(records, bank, profile, "m")
            self.assertEqual(len(calls), 1)
            records = write(["bbbb", "aa"])
            os.utime(bank, (0, 0))  # older than the cache: the mtime rule kept it
            embeddings, _model = rx._build_or_load_embeddings(records, bank, profile, "m")
            self.assertEqual(len(calls), 2)
            self.assertEqual(embeddings[:, 0].tolist(), [4.0, 2.0])


class DossierTests(unittest.TestCase):
    """What the dossier says about the corpus behind it (audit D17, D18)."""

    PROSE = ("The sample is small. The method is simple and the result is stable. "
             "We repeat the measurement twice.\n")

    def _dossier(self, files: dict[str, str]) -> str:
        """Run the extractor over one curated tier holding `files`; return the dossier."""
        with tempfile.TemporaryDirectory() as tmp:
            corpus = pathlib.Path(tmp) / "corpus"
            tier = corpus / "g" / "tier-1-top"
            tier.mkdir(parents=True)
            for name, body in files.items():
                (tier / name).write_text(body, encoding="utf-8")
            profile = pathlib.Path(tmp) / "profile"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                code = es.main(["--field", "g", "--corpus-root", str(corpus),
                                "--profile-root", str(profile)])
            self.assertEqual(code, 0)
            return (profile / "g" / "style_dossier.md").read_text(encoding="utf-8")

    def test_the_no_sections_hint_fires_when_only_unknown_was_measured(self):
        # `.txt` and sectionless `.tex` fill `unknown`, which reaches the
        # statistics, so a hint keyed on an empty dict could never fire.
        unsectioned = self._dossier({"notes.txt": self.PROSE})
        self.assertIn("No sections detected", unsectioned)
        self.assertIn("| unknown |", unsectioned)  # the hint adds; the row stays
        sectioned = self._dossier({"paper.tex": "\\section{Results}\n" + self.PROSE})
        self.assertNotIn("No sections detected", sectioned)

    def test_the_header_counts_the_files_the_run_skipped(self):
        # Without pymupdf a standalone PDF is skipped: the run's summary said
        # so, and the dossier's "Built from N corpus papers" did not.
        missing = ImportError("pymupdf not installed")
        with mock.patch.object(es, "extract_pdf_text", side_effect=missing):
            dossier = self._dossier({"notes.txt": self.PROSE, "scan.pdf": "%PDF-1.4\n"})
        header = next(line for line in dossier.splitlines() if line.startswith("Built from"))
        self.assertIn("Built from 1 corpus papers", header)
        self.assertIn("1 source file(s) SKIPPED (pymupdf unavailable)", header)


class PdfPathTests(unittest.TestCase):
    """The PDF path end to end on a stand-in `pymupdf` (audit D27): only its
    helpers had tests, never `extract_pdf_text` reading a text layer."""

    def test_ligatures_expand_and_line_fragments_rejoin_into_paragraphs(self):
        blocks = [(0, 0, 1, 1, "1. Introduction", 0, 0),
                  (0, 0, 1, 1, "The ﬁrst eﬀect is signiﬁcant, and the", 1, 0),
                  (0, 0, 1, 1, "inﬂated estimate follows from it.", 2, 0),
                  (0, 0, 1, 1, "an image block the text layer must drop", 3, 1),
                  (0, 0, 1, 1, "2. Results", 4, 0),
                  (0, 0, 1, 1, "The ﬁnal ﬁgure is stable.", 5, 0)]

        class Page:
            def get_text(self, mode):
                return blocks if mode == "blocks" else ""

        class Document:
            closed = False

            def __iter__(self):
                return iter([Page()])

            def close(self):
                Document.closed = True

        fake = types.SimpleNamespace(open=lambda path: Document())
        with mock.patch.dict(sys.modules, {"pymupdf": fake}):
            analysis = es.analyse_paper(pathlib.Path("paper.pdf"))
        sections = analysis["by_section"]
        self.assertEqual(sorted(sections), ["intro", "results"])
        self.assertEqual(sections["intro"]["plain_text"],
                         "The first effect is significant, and the inflated "
                         "estimate follows from it.")
        self.assertEqual(sections["results"]["plain_text"], "The final figure is stable.")
        self.assertIn("significant", sections["intro"]["word_counter"])
        self.assertTrue(Document.closed)


if __name__ == "__main__":
    unittest.main()
