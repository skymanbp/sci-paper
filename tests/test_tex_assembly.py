r"""Include assembly contracts for tex_assembly (moved from test_extract_style on 2026-09-04).

A LaTeX document is assembled from files; only its root is named. These tests
pin the reader that splices `\input` / `\include` children back into their
root, from the file system and from a git ref, so every consumer measures the
same document.
"""

from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import extract_style as es
import tex_assembly as assembly


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

    def test_included_chapters_are_spliced_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "main.tex": r"\documentclass{article}" "\n"
                            r"\begin{document}" "\n"
                            r"\include{chap_1}" "\n"
                            r"\input{chap_2}" "\n"
                            r"\end{document}" "\n",
                "chap_1.tex": "first chapter body\n",
                "chap_2.tex": "second chapter body\n",
            })
            text = assembly.read_tex_document(d / "main.tex")
        self.assertIn("first chapter body", text)
        self.assertIn("second chapter body", text)

    def test_commented_out_includes_are_not_spliced(self):
        # arXiv sources routinely park an alternative build in comments
        # (`% \includeonly{WeakLens_7}`); resolving those duplicates a chapter.
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "main.tex": r"\documentclass{article}" "\n"
                            r"% \input{alt}" "\n" "kept\n",
                "alt.tex": "ALTERNATE\n",
            })
            text = assembly.read_tex_document(d / "main.tex")
        self.assertIn("kept", text)
        self.assertNotIn("ALTERNATE", text)

    def test_flattened_subdirectory_targets_resolve_to_siblings(self):
        # arXiv flattens submissions: `\input{sections/introduction}` names a
        # file that now sits beside the root. `select_document_roots` matches
        # includes by stem, so without the same fallback here the chapter is
        # dropped as a fragment and never spliced back -- 2101.09097v3 kept
        # 2 of its 9,743 words that way.
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "article.tex": r"\documentclass{article}" "\n"
                               r"\input{sections/introduction}" "\n"
                               r"\input{sections/forecast.tex}" "\n",
                "introduction.tex": "intro body\n",
                "forecast.tex": "forecast body\n",
            })
            text = assembly.read_tex_document(d / "article.tex")
        self.assertIn("intro body", text)
        self.assertIn("forecast body", text)

    def test_the_selector_and_the_reader_agree_on_targets(self):
        # The bug was an asymmetry, not a missing feature: whatever
        # select_document_roots treats as included must be spliceable.
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "article.tex": r"\documentclass{article}" "\n"
                               r"\input{sections/introduction}" "\n",
                "introduction.tex": "intro body\n",
            })
            roots = es.select_document_roots(sorted(d.glob("*.tex")))
            self.assertEqual([p.name for p in roots], ["article.tex"])
            self.assertIn("intro body", assembly.read_tex_document(roots[0]))

    def test_missing_include_target_leaves_the_call_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "main.tex": r"\documentclass{article}" "\n"
                            r"\input{aa.cls}" "\n" "body\n",
            })
            text = assembly.read_tex_document(d / "main.tex")
        self.assertIn("body", text)

    def test_include_cycles_terminate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "a.tex": r"\documentclass{article}" "\n" r"\input{b}" "\n",
                "b.tex": r"\input{a}" "\n" "cycle body\n",
            })
            text = assembly.read_tex_document(d / "a.tex")
        self.assertIn("cycle body", text)

    def test_an_include_is_spliced_in_place_and_may_repeat(self):
        # `Before \input{body} After` lost both `Before` and `After` when the
        # whole line was replaced by the child, and a second `\input{body}`
        # returned nothing because "seen anywhere" was mistaken for a cycle.
        with tempfile.TemporaryDirectory() as tmp:
            d = self._bundle(tmp, {
                "main.tex": "Before \\input{body} After\n\\input{body} % \\input{alt}\n",
                "body.tex": "CHILD",
                "alt.tex": "ALT",
            })
            text = assembly.read_tex_document(d / "main.tex")
        self.assertEqual(text, "Before CHILD After\nCHILD % \\input{alt}\n")


class GitBaselineTests(unittest.TestCase):
    """A `--git-ref` baseline is the assembled document AT THE REF, children too."""

    def test_the_git_baseline_carries_the_children_of_the_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = pathlib.Path(tmp)

            def git(*args: str) -> None:
                subprocess.run(["git", "-C", str(d), *args], check=True,
                               capture_output=True, text=True)

            git("init", "-q")
            git("config", "user.email", "t@example.com")
            git("config", "user.name", "t")
            (d / "main.tex").write_text("\\input{body}\n", encoding="utf-8")
            (d / "body.tex").write_text("old child prose\n", encoding="utf-8")
            git("add", ".")
            git("commit", "-q", "-m", "baseline")
            (d / "body.tex").write_text("new\n", encoding="utf-8")
            # The child's own newline plus the root's: a faithful splice.
            baseline = assembly.read_git_document(d / "main.tex", "HEAD")
            self.assertEqual(baseline, "old child prose\n\n")
            self.assertEqual(assembly.read_tex_document(d / "main.tex"), "new\n\n")
            with self.assertRaises(ValueError):
                assembly.read_git_document(d / "missing.tex", "HEAD")


if __name__ == "__main__":
    unittest.main()
