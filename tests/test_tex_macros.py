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
        text = r"\newcommand{\Nsamples}{12}" "\n" r"We drew \Nsamples{} samples."
        self.assertIn("12 samples", tex_macros.expand_numeric(text))

    def test_the_definition_stops_contributing_its_digits(self):
        """The second half of the bug: an unexpanded definition leaked once."""
        out = tex_macros.expand_numeric(r"\newcommand{\Ns}{12}" "\nNo uses here.")
        self.assertNotIn("12", out)

    def test_a_symbolic_macro_is_left_alone(self):
        text = r"\newcommand{\Msun}{M_\odot}" "\n" r"a mass of \Msun today"
        self.assertEqual(tex_macros.expand_numeric(text), text)

    def test_a_macro_taking_an_argument_is_left_alone(self):
        text = r"\newcommand{\hl}[1]{\textbf{#1}}" "\n" r"\hl{42} rows"
        self.assertEqual(tex_macros.expand_numeric(text), text)
        # A numeric body does not make an argument-taking macro a constant:
        # `\foo{x}` became `42{x}` because the arity was matched and ignored.
        text = r"\newcommand{\foo}[1]{42}" "\n" r"Use \foo{x} here."
        self.assertEqual(tex_macros.expand_numeric(text), text)

    def test_a_commented_out_definition_is_not_a_definition(self):
        text = (r"% \newcommand{\Ns}{12}" "\n" r"\newcommand{\Ns}{7}" "\n"
                r"We use \Ns{} samples.")
        self.assertIn("We use 7 samples.", tex_macros.expand_numeric(text))
        alone = r"% \newcommand{\Ns}{12}" "\n" r"We use \Ns{} samples."
        self.assertEqual(tex_macros.expand_numeric(alone), alone)

    def test_a_use_inside_a_comment_is_left_as_written(self):
        text = r"\newcommand{\Ns}{7}" "\n" r"We use \Ns{} samples. % was \Ns before the cut"
        self.assertEqual(tex_macros.expand_numeric(text).splitlines()[1],
                         r"We use 7 samples. % was \Ns before the cut")

    def test_a_definition_across_lines_moves_no_later_line(self):
        text = "\\newcommand{\\Ns}{%\n  12}\nWe use \\Ns{} samples.\n"
        out = tex_macros.expand_numeric(text)
        self.assertEqual(out.count("\n"), text.count("\n"))
        self.assertEqual(out.splitlines()[2], "We use 12 samples.")

    def test_a_shorter_name_does_not_fire_inside_a_longer_one(self):
        text = (r"\newcommand{\Ns}{7}" "\n" r"\newcommand{\Nsamples}{12}" "\n"
                r"\Ns and \Nsamples")
        self.assertIn("7 and 12", tex_macros.expand_numeric(text))

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
            r"\newcommand{\Nsamples}{12}" "\n" r"\begin{document}"
            "\n" r"\input{child}" "\n" r"\end{document}",
            r"We drew \Nsamples{} samples in total.")
        self.assertIn("12 samples", sec.read_tex_document(root))

    def test_the_numeral_projection_now_sees_that_number(self):
        """The end the fix exists for: `latex_to_numeral_text` counts it."""
        root = self._document(
            r"\newcommand{\Nsamples}{12}" "\n" r"\begin{document}"
            "\n" r"\input{child}" "\n" r"\end{document}",
            r"We drew \Nsamples{} samples in total.")
        projected = sec.latex_to_numeral_text(sec.read_tex_document(root))
        self.assertIn("12", projected)


if __name__ == "__main__":
    unittest.main()
