"""deai_reference.paragraphs yields prose units only.

Headings and floats are blanked in place so every unit keeps its line
number, and blanking a `\\section{...}\\label{...}` line leaves the label
and a run of spaces behind; a comment-only block never had prose at all.
Until v0.36.3 both reached every per-paragraph axis as units of their own:
GPT-2 tokenises forty-eight spaces into more than the UID minimum, so the
Letter's four heading lines were reported as paragraphs of near-zero
surprisal variance (z = -7), and a `% SCOPE:` comment block counted as a
unit of the removal map.
"""

from __future__ import annotations

import unittest

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

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


if __name__ == "__main__":
    unittest.main()
