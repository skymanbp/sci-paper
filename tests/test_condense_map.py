from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import condense_map as cm

CLAIM = ("The aperture mass filter recovers the injected cluster signal at the "
         "fiducial threshold for every configuration in the calibrated grid.")
RESTATED = ("At the fiducial threshold the aperture mass filter recovers the "
            "injected cluster signal for every calibrated grid configuration.")
PARAGRAPH = ("The shear catalog is cut at a signal-to-noise ratio of ten, the "
             "tangential shear is convolved with a compensated filter of fixed "
             "scale, and the aperture mass map is evaluated on a regular grid "
             "in catalog coordinates so that every peak has a position and a "
             "height that the injection grid can reproduce exactly.")
DOCUMENT = f"""\\newcommand{{\\unused}}{{x}}
\\newcommand{{\\used}}{{y}}
\\section{{Introduction}}
{PARAGRAPH}

\\section{{Methods}}
In this section we describe the filter. {CLAIM} Note that the filter uses
\\used{{}} in order to keep the scale fixed, where $\\sigma$ is the width.
The peak may possibly move, where $\\sigma$ denotes the width again.
\\label{{eq:dead}} The Dark Energy Survey (DES) provides the catalog.

\\begin{{figure}}
\\caption{{An orphaned figure carrying a caption of exactly ten words.}}
\\label{{fig:orphan}}
\\end{{figure}}

\\section{{Results}}
{RESTATED} See Figure~\\ref{{fig:kept}}.

\\begin{{figure}}
\\caption{{Kept.}}
\\label{{fig:kept}}
\\end{{figure}}

\\section{{Discussion}}
{PARAGRAPH}
"""


def by_rule(findings):
    grouped: dict[str, list] = {}
    for finding in findings:
        grouped.setdefault(finding["rule"], []).append(finding)
    return grouped


class MapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.findings = cm.condense_map(DOCUMENT)
        cls.by_rule = by_rule(cls.findings)

    def test_a_restatement_names_its_canonical_home(self):
        # The repeated discussion paragraph restates too; the results sentence
        # is the one whose home is the methods claim.
        (finding,) = [f for f in self.by_rule["condense-restatement"]
                      if f["location"]["section"] == "results"]
        self.assertIn("aperture mass filter recovers",
                      finding["observed"]["canonical_excerpt"])
        self.assertGreater(finding["observed"]["removable_words"], 10)
        self.assertFalse(finding["observed"]["genre_carve_out"])

    def test_roadmap_sentence_and_note_that_are_zero_gain(self):
        cues = sorted(f["observed"]["cue"] for f in self.by_rule["condense-zero-gain"])
        self.assertEqual(cues, ["in this section", "note that"])
        whole = [f for f in self.by_rule["condense-zero-gain"]
                 if f["observed"]["whole_sentence"]]
        self.assertEqual(len(whole), 1)
        # "In this section we describe the filter." is seven words, all removable.
        self.assertEqual(whole[0]["observed"]["removable_words"], 7)

    def test_dead_artifacts_of_every_kind(self):
        excerpts = {rule: [f["observed"]["excerpt"] for f in found]
                    for rule, found in self.by_rule.items() if rule.startswith("condense-dead:")}
        self.assertEqual(excerpts["condense-dead:macro"], ["\\unused"])
        self.assertEqual(excerpts["condense-dead:label"], ["eq:dead"])
        self.assertEqual(excerpts["condense-dead:acronym"], ["DES"])
        (orphan,) = self.by_rule["condense-dead:figure"]
        self.assertEqual(orphan["observed"]["labels"], ["fig:orphan"])
        self.assertEqual(orphan["observed"]["removable_words"], 10)
        self.assertNotIn("condense-dead:table", excerpts)

    def test_verbose_constructions_carry_their_replacement(self):
        phrases = {f["observed"]["phrase"]: f["observed"]["removable_words"]
                   for f in self.by_rule["condense-verbose"]}
        self.assertEqual(phrases["in order to"], 2)
        self.assertEqual(phrases["may possibly"], 1)

    def test_the_second_gloss_of_a_symbol_is_reported(self):
        (finding,) = self.by_rule["condense-regloss"]
        self.assertEqual(finding["observed"]["symbol"], "\\sigma")
        self.assertLess(finding["observed"]["first_gloss_line"],
                        finding["location"]["start_line"])

    def test_a_paragraph_repeated_across_sections_is_a_duplicate(self):
        (finding,) = self.by_rule["condense-duplicate"]
        self.assertEqual(finding["location"]["section"], "discussion")
        self.assertEqual(finding["observed"]["canonical_section"], "intro")
        self.assertGreaterEqual(finding["observed"]["jaccard"], cm.DUPLICATE_JACCARD)

    def test_the_budget_counts_each_unit_once(self):
        budget = cm.condense_budget(DOCUMENT, self.findings)
        totals = budget["removable_by_rule"]
        # Per-rule totals are candidate mass; the deduplicated total is smaller
        # by exactly the discussion sentence, which the restatement scan names
        # and the duplicate scan removes with its whole paragraph.
        (inside,) = [f for f in self.by_rule["condense-restatement"]
                     if f["location"]["section"] == "discussion"]
        self.assertEqual(budget["removable_total"],
                         sum(totals.values()) - inside["observed"]["removable_words"])
        self.assertEqual(budget["default_target_words"],
                         totals["condense-restatement"] + totals["condense-zero-gain"])
        self.assertGreater(budget["removable_fraction"], 0.0)
        self.assertEqual(budget["n_entries"], len(self.findings))


class BudgetUnionTests(unittest.TestCase):
    ROADMAP = ("In this section we describe precise galaxy cluster signal maps "
               "calibrated against independent external measurements.")

    def test_overlapping_scans_cannot_exceed_the_document(self):
        # Three copies of one roadmap sentence: the restatement and zero-gain
        # scans both name copies two and three, and the sum of both (75 words)
        # exceeded the 46-word document. A sentence is removed once.
        text = "\\section{Methods}\n" + "\n\n".join([self.ROADMAP] * 3)
        findings = cm.condense_map(text)
        budget = cm.condense_budget(text, findings)
        self.assertLessEqual(budget["default_target_words"], budget["prose_words"])
        self.assertEqual(budget["removable_total"], budget["default_target_words"])
        self.assertGreater(sum(budget["removable_by_rule"].values()),
                           budget["removable_total"])

    def test_a_negated_or_renumbered_sentence_is_not_a_restatement(self):
        claim = ("The calibrated galaxy cluster mass signal measurement across "
                 "independent radial apertures is significant.")
        for variant in (claim.replace("is significant", "is not significant"),
                        claim.replace("independent", "five independent")):
            findings = cm.condense_map(f"\\section{{Methods}}\n{claim}\n\n{variant}\n")
            self.assertEqual([f for f in findings if f["rule"] == "condense-restatement"],
                             [], variant)
        # The same sentence restated verbatim still is one.
        findings = cm.condense_map(f"\\section{{Methods}}\n{claim}\n\n{claim}\n")
        self.assertEqual(len([f for f in findings if f["rule"] == "condense-restatement"]), 1)

    def test_a_claim_opening_with_a_cue_budgets_only_the_cue(self):
        findings = cm.condense_map(
            "\\section{Methods}\nIn this paper we measure a galaxy mass of five units.\n")
        (finding,) = findings
        self.assertFalse(finding["observed"]["whole_sentence"])
        self.assertEqual(finding["observed"]["removable_words"], 3)

    def test_a_whole_roadmap_sentence_in_the_conclusion_is_carved_out(self):
        text = ("\\section{Results}\nWe describe the filter.\n"
                "\\section{Conclusion}\nIn this section we describe the filter.\n")
        findings = cm.condense_map(text)
        (finding,) = [f for f in findings if f["rule"] == "condense-zero-gain"]
        self.assertTrue(finding["observed"]["whole_sentence"])
        self.assertTrue(finding["observed"]["genre_carve_out"])
        self.assertEqual(cm.condense_budget(text, findings)["default_target_words"], 0)

    def test_a_document_without_sections_is_still_mapped(self):
        findings = cm.condense_map("Note that the filter is fixed. In this section we "
                                   "describe the filter.\n")
        self.assertEqual(sorted(f["observed"]["cue"] for f in findings),
                         ["in this section", "note that"])


class CarveOutTests(unittest.TestCase):
    def test_a_conclusion_restatement_is_reported_but_not_targeted(self):
        text = f"\\section{{Results}}\n{CLAIM}\n\\section{{Conclusion}}\n{RESTATED}\n"
        findings = cm.condense_map(text)
        (finding,) = [f for f in findings if f["rule"] == "condense-restatement"]
        self.assertTrue(finding["observed"]["genre_carve_out"])
        self.assertEqual(cm.condense_budget(text, findings)["default_target_words"], 0)

    def test_a_heading_does_not_fuse_with_the_first_sentence(self):
        # Left in the block, `Methods` would open the sentence and the roadmap
        # cue would no longer sit at the start of it.
        text = "\\section{Methods}\nIn this section we describe the filter.\n"
        cues = [f["observed"]["cue"] for f in cm.condense_map(text)]
        self.assertEqual(cues, ["in this section"])


class CliTests(unittest.TestCase):
    def test_json_report_carries_the_budget(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "draft.tex"
            target.write_text(DOCUMENT, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(TOOLS / "condense_map.py"), str(target),
                 "--format", "json"], text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "sci-paper.feedback.v1")
        self.assertIn("default_target_words", report["condense_budget"])

    def test_the_sample_manuscript_has_a_nonzero_budget(self):
        sample = TOOLS.parent / "examples" / "sample-manuscript.tex"
        result = subprocess.run(
            [sys.executable, str(TOOLS / "condense_map.py"), str(sample)],
            text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("condense_map:", result.stdout)
        self.assertNotIn("removable 0 (", result.stdout)


if __name__ == "__main__":
    unittest.main()
