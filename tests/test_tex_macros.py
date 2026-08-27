"""A number written as a macro must reach the axis that counts numbers.

The salience axis measures how densely a passage recites measured quantities.
A manuscript that keeps those quantities in `\\newcommand` bodies -- the habit
that makes every number in the text traceable to one definition -- was invisible
to it twice over: the use site contributed nothing, and the definition site
contributed the digits once, in the preamble, where no section reports them.

Both directions are covered here, because they cancel: on the manuscript that
prompted this (2026-08-27) expanding uses added 650 digits while dropping
definitions removed 493, so a test that checked only the net would have passed
against a fix that did neither.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import extract_sections as sec
import tex_macros


class ExpandNumericTests(unittest.TestCase):
    def test_a_use_of_a_numeric_macro_becomes_its_number(self):
        text = r"\newcommand{\Nfields}{63}" "\n" r"We scored \Nfields{} fields."
        self.assertIn("63 fields", tex_macros.expand_numeric(text))

    def test_the_definition_stops_contributing_its_digits(self):
        """The second half of the bug: an unexpanded definition leaked once."""
        out = tex_macros.expand_numeric(r"\newcommand{\Nf}{63}" "\nNo uses here.")
        self.assertNotIn("63", out)

    def test_a_symbolic_macro_is_left_alone(self):
        text = r"\newcommand{\Msun}{M_\odot}" "\n" r"a mass of \Msun today"
        self.assertEqual(tex_macros.expand_numeric(text), text)

    def test_a_macro_taking_an_argument_is_left_alone(self):
        text = r"\newcommand{\hl}[1]{\textbf{#1}}" "\n" r"\hl{42} rows"
        self.assertEqual(tex_macros.expand_numeric(text), text)

    def test_a_shorter_name_does_not_fire_inside_a_longer_one(self):
        text = (r"\newcommand{\Nf}{7}" "\n" r"\newcommand{\Nfields}{63}" "\n"
                r"\Nf and \Nfields")
        self.assertIn("7 and 63", tex_macros.expand_numeric(text))

    def test_plain_tex_def_and_renewcommand_are_recognised(self):
        self.assertIn("5", tex_macros.expand_numeric(r"\def\Na{5}" "\n" r"\Na"))
        self.assertIn("9", tex_macros.expand_numeric(
            r"\renewcommand{\Nb}{9}" "\n" r"\Nb"))


class AssembledDocumentTests(unittest.TestCase):
    """Expansion has to happen on the whole document, not on a file.

    A definition sits in the preamble and its uses sit in the section files the
    root \\input's, so a per-file expansion resolves nothing at all.
    """

    def _document(self, root_body: str, child_body: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        (directory / "child.tex").write_text(child_body, encoding="utf-8")
        root = directory / "main.tex"
        root.write_text(root_body, encoding="utf-8")
        return root

    def test_a_definition_in_the_root_reaches_a_use_in_an_included_file(self):
        root = self._document(
            r"\newcommand{\Nfields}{63}" "\n" r"\begin{document}"
            "\n" r"\input{child}" "\n" r"\end{document}",
            r"We scored \Nfields{} fields in total.")
        self.assertIn("63 fields", sec.read_tex_document(root))

    def test_the_numeral_projection_now_sees_that_number(self):
        """The end the fix exists for: `latex_to_numeral_text` counts it."""
        root = self._document(
            r"\newcommand{\Nfields}{63}" "\n" r"\begin{document}"
            "\n" r"\input{child}" "\n" r"\end{document}",
            r"We scored \Nfields{} fields in total.")
        projected = sec.latex_to_numeral_text(sec.read_tex_document(root))
        self.assertIn("63", projected)


if __name__ == "__main__":
    unittest.main()
