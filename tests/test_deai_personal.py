from __future__ import annotations

import sys
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_personal as pers

P_SHORT = ("The result holds firmly. It is clear enough. We confirm it now. The data agree "
           "well. The model fits fine. No tension remains here. The fit is good. We report "
           "success. All checks pass cleanly. The bound stays tight.")
P_LONG = ("The convergence field which encodes the projected total mass distribution along the "
          "entire line of sight to each faint background source galaxy in the deep wide survey "
          "footprint is estimated here using a single compensated aperture filter of one fixed "
          "angular scale.")
P_MED = ("We estimate the aperture mass statistic here. It is convolved with a compensated "
         "filter. The angular scale is fixed throughout. We then threshold the resulting signal "
         "to noise map at five sigma to find candidate peaks across the survey footprint.")


def paper(section_rows: list[list[str]]) -> str:
    parts = []
    for i, paras in enumerate(section_rows):
        parts.append(rf"\section{{Section {i}}}")
        parts.append("\n\n".join(paras))
    return "\n\n".join(parts)


VARIED = paper([[P_SHORT, P_LONG], [P_MED, P_SHORT], [P_LONG, P_MED]])
UNIFORM = paper([[P_MED, P_MED + " Indeed."], [P_MED + " Again.", P_MED + " Still."],
                 [P_MED + " More.", P_MED + " Yet."]])


class PersonalBaselineTests(unittest.TestCase):
    def test_low_tail_fraction(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(pers._low_tail_fraction(0.0, vals), 0.0)
        self.assertEqual(pers._low_tail_fraction(1.0, vals), 0.2)
        self.assertEqual(pers._low_tail_fraction(5.0, vals), 1.0)

    def test_reference_unmeasured_below_minimum(self):
        ref = pers.personal_reference([VARIED, VARIED])   # only 2 papers
        self.assertEqual(ref["status"], "unmeasured")
        self.assertLess(ref["n_papers"], pers.MIN_PERSONAL_PAPERS)

    def test_reference_measured_with_enough_papers(self):
        ref = pers.personal_reference([VARIED, VARIED, VARIED])
        self.assertEqual(ref["status"], "measured")
        self.assertEqual(ref["n_papers"], 3)
        self.assertGreater(len(ref["by_feature"]), 0)

    def test_uniform_draft_is_under_varied(self):
        ref = pers.personal_reference([VARIED, VARIED, VARIED])
        result = pers.compare(UNIFORM, ref)
        self.assertEqual(result["status"], "measured")
        self.assertGreaterEqual(result["summary"]["under_varied_fraction"],
                                pers.FLAG_FEATURE_FRACTION)

    def test_varied_draft_is_not_flagged(self):
        ref = pers.personal_reference([VARIED, VARIED, VARIED])
        result = pers.compare(VARIED, ref)
        self.assertLess(result["summary"]["under_varied_fraction"],
                        pers.FLAG_FEATURE_FRACTION)

    def test_findings_flag_uniform_draft(self):
        findings, axes = pers.document_findings(UNIFORM, "draft.tex",
                                                [VARIED, VARIED, VARIED])
        self.assertEqual(axes[0]["status"], "measured")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "personal-baseline:under-varied")
        self.assertEqual(findings[0]["calibration_unit"], "document")

    def test_findings_unmeasured_without_history(self):
        findings, axes = pers.document_findings(UNIFORM, "draft.tex", [VARIED])
        self.assertEqual(findings, [])
        self.assertEqual(axes[0]["status"], "unmeasured")


if __name__ == "__main__":
    unittest.main()
