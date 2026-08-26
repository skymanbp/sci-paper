from __future__ import annotations

import sys
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_partition as partition

LENSING_A = (
    "The aperture mass statistic isolates the tangential shear signal around "
    "each candidate peak. The same aperture mass filter suppresses the "
    "large-scale shear gradient across the field. Both properties make the "
    "aperture mass estimator suitable for substructure searches."
)
LENSING_B = (
    "The aperture mass significance depends on the local source density and "
    "the shape noise of the background sample. We therefore weight the "
    "aperture mass filter by the inverse shear variance in each cell."
)
UNRELATED = (
    "Spectroscopic follow-up of the brightest cluster galaxies proceeded on "
    "a different telescope during the second observing season. Redshift "
    "completeness reached ninety per cent for the magnitude-limited sample."
)


class PartitionTests(unittest.TestCase):
    def test_overlap_orders_related_above_unrelated(self):
        related = partition._overlap(LENSING_A, LENSING_B)
        unrelated = partition._overlap(LENSING_A, UNRELATED)
        self.assertGreater(related, unrelated)

    def test_apply_merge_and_split_preserve_words(self):
        text = ("\\section{Methods}\n\n" + LENSING_A + "\n\n" + LENSING_B
                + "\n\n\\section{Results}\n\n" + UNRELATED
                + "\n\n" + LENSING_A + "\n")
        sections = partition._parse(text)
        # the \section command line is its own fixed block; the two prose
        # paragraphs follow it
        self.assertTrue(sections[0]["blocks"][0]["fixed"])
        self.assertEqual(len(sections[0]["blocks"]), 3)
        import extract_style as es
        words_before = sorted(
            w for s in sections for b in s["blocks"]
            for w in es.words(es.latex_to_plain(b["text"])))
        merged = partition._apply(sections, {
            "kind": "merge", "section": 0, "block": 1, "overlap": 1.0})
        words_after = sorted(
            w for s in merged for b in s["blocks"]
            for w in es.words(es.latex_to_plain(b["text"])))
        self.assertEqual(words_before, words_after,
                         "merge must not add or drop a single word")
        self.assertEqual(len(merged[0]["blocks"]), 2)
        split = partition._apply(sections, {
            "kind": "split", "section": 0, "block": 1, "cut": 2,
            "overlap": 0.0})
        words_split = sorted(
            w for s in split for b in s["blocks"]
            for w in es.words(es.latex_to_plain(b["text"])))
        self.assertEqual(words_before, words_split,
                         "split must not add or drop a single word")
        self.assertEqual(len(split[0]["blocks"]), 4)
        # fixed blocks are never candidates
        floor = 0.0
        candidates = (partition._merge_candidates(sections, floor)
                      + partition._split_candidates(sections, 1.0))
        self.assertTrue(all(
            not sections[op["section"]]["blocks"][op["block"]].get("fixed")
            for op in candidates))

    def test_suggest_degrades_honestly_without_manifold(self):
        result = partition.suggest("\\section{A}\n\nshort\n",
                                   {"dispersion_manifold": None}, 3)
        self.assertEqual(result["status"], "unmeasured")


if __name__ == "__main__":
    unittest.main()
