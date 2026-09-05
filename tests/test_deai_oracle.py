"""deai_oracle.uid_findings runs its paragraph sweep and scores against the
baseline without a model on the machine.

The sweep is `deai_reference.paragraphs`, imported under the name
`reference`; from v0.36.2 to v0.36.3 a local of the same name inside
`uid_findings` made the module unbound before the loop began, and every
lint reported the L1.uid axis as unmeasured with the UnboundLocalError as
its reason. This test would have failed on that tree.
"""

from __future__ import annotations

import unittest

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_oracle as oracle

# One paragraph per section; the parentheses keep `* 6` from repeating the
# heading (adjacent literals concatenate before the multiplication binds).
TEXT = (
    "\\section{Introduction}\n"
    + ("The estimator uses five filters. " * 6) + "\n\n"
    + "\\section{Results}\n"
    + ("The slope is negative for all clusters. " * 6) + "\n"
)
BASELINE = {"model": "stub", "pooled": {
    "global_uid": {"mean": 3.0, "stdev": 0.4, "n": 40},
    "local_uid": {"mean": 3.4, "stdev": 0.45, "n": 40}}}


class UidFindingsTests(unittest.TestCase):
    def setUp(self):
        self.saved = (oracle.load_baseline, oracle.model_runtime_available,
                      oracle.token_surprisals)
        oracle.load_baseline = lambda field_dir: BASELINE
        oracle.model_runtime_available = lambda: (True, "stub")

    def tearDown(self):
        (oracle.load_baseline, oracle.model_runtime_available,
         oracle.token_surprisals) = self.saved

    def test_sweep_runs_and_a_flat_paragraph_is_flagged(self):
        # 30 identical surprisals: global_uid 0, z = -7.5, well below -FLAG_Z.
        oracle.token_surprisals = lambda text, model_name: [3.0] * 30
        findings = oracle.uid_findings(TEXT, None, path="draft.tex")
        self.assertEqual([f["rule"] for f in findings], ["uid-low:intro", "uid-low:results"])
        first = findings[0]
        self.assertEqual(first["reference"]["mean"], 3.0)
        # feedback caps paragraph-unit confidence at 0.5 and says so after the n.
        self.assertTrue(first["confidence"]["basis"].startswith("reference n=40"))
        self.assertEqual(first["confidence"]["value"], 0.5)
        self.assertEqual(first["calibration_unit"], "paragraph")

    def test_reference_like_paragraph_yields_no_finding(self):
        # global_uid is the surprisal pstdev: +-3.0 alternation gives 3.0 = the
        # reference mean (z = 0), and jumps of 6.0 sit above the local reference.
        surprisals = [3.0 + 3.0 * (-1) ** i for i in range(30)]
        oracle.token_surprisals = lambda text, model_name: surprisals
        self.assertEqual(oracle.uid_findings(TEXT, None), [])

    def test_short_paragraphs_are_skipped_not_scored(self):
        oracle.token_surprisals = lambda text, model_name: [3.0] * (oracle.MIN_TOKENS - 1)
        self.assertEqual(oracle.uid_findings(TEXT, None), [])


if __name__ == "__main__":
    unittest.main()
