"""deai_oracle.uid_findings runs its paragraph sweep and scores against the
baseline without a model on the machine.

The sweep is `deai_reference.paragraphs`, imported under the name
`reference`; from v0.36.2 to v0.36.3 a local of the same name inside
`uid_findings` made the module unbound before the loop began, and every
lint reported the L1.uid axis as unmeasured with the UnboundLocalError as
its reason. This test would have failed on that tree.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_calibrate_skips_a_blank_or_undecodable_bank_line(self):
        # `json.loads` on a blank line aborted an hour-long calibration.
        oracle.token_surprisals = lambda text, model_name: [3.0 + (i % 2) for i in range(30)]
        with tempfile.TemporaryDirectory(prefix="oracle-") as raw:
            bank = Path(raw) / "exemplar_paragraphs.jsonl"
            bank.write_text("\n".join([json.dumps({"section": "intro", "text": "one"}),
                                       "", "not json {", "   ",
                                       json.dumps({"section": "intro", "text": "two"})]) + "\n",
                            encoding="utf-8")
            baseline = oracle.calibrate(Path(raw), "stub")
        self.assertEqual(baseline["n_paragraphs_used"], 2)


class FailureMessageTests(unittest.TestCase):
    def test_an_exception_with_no_message_has_a_first_line(self):
        # The CUDA fallback handler read `str(exc).splitlines()[0]` and died
        # on the way to the fallback when the message was empty.
        self.assertEqual(oracle._first_line(Exception("")), "?")
        self.assertEqual(oracle._first_line(Exception("first\nsecond")), "first")


class FieldResolutionTests(unittest.TestCase):
    """`--field` resolves through `cli_common.optional_field_dir`: none is
    exit 2 with the message the tool always printed, one resolves on its own,
    and `profile_root / None` is no longer a TypeError. `deai_voice`, the
    other tool that cannot run without a profile, has the same case in
    `test_deai_voice.py`."""

    def test_oracle_needs_a_profile_and_finds_a_single_one(self):
        with tempfile.TemporaryDirectory(prefix="oracle-") as raw:
            draft = Path(raw) / "draft.tex"
            draft.write_text(TEXT, encoding="utf-8")
            profiles = Path(raw) / "profiles"
            profiles.mkdir()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(oracle.main([str(draft), "--profile-root", str(profiles)]), 2)
            self.assertIn("need --field", stderr.getvalue())
            (profiles / "fld").mkdir()
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(oracle.main([str(draft), "--profile-root", str(profiles)]), 0)
            self.assertIn("axis L1.uid: unmeasured", stdout.getvalue())

    def test_calibrating_a_field_without_a_bank_is_exit_two(self):
        # With the runtime present, `calibrate` raised FileNotFoundError out
        # of `main` (a traceback, exit 1) for a --field that has no bank.
        with tempfile.TemporaryDirectory(prefix="oracle-") as raw:
            (Path(raw) / "fld").mkdir()
            stderr = io.StringIO()
            with mock.patch.object(oracle, "model_runtime_available",
                                   return_value=(True, "")), \
                    contextlib.redirect_stderr(stderr):
                code = oracle.main(["--calibrate", "--field", "fld", "--profile-root", raw])
            self.assertEqual(code, 2)
            self.assertIn("no exemplar_paragraphs.jsonl", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
