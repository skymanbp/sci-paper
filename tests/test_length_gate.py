from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "length_gate.py"

BEFORE = (
    "\\section{Methods}\nThe estimator uses five filters.\n"
    "\\section{Results}\nThe slope is negative for all clusters.\n"
)


class LengthGateCliTests(unittest.TestCase):
    def run_gate(self, before: str, after: str, *arguments: str):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before_path = root / "before.tex"
            after_path = root / "after.tex"
            before_path.write_text(before, encoding="utf-8")
            after_path.write_text(after, encoding="utf-8")
            command = [sys.executable, str(GATE), str(after_path),
                       "--before", str(before_path), *arguments]
            return subprocess.run(command, text=True, capture_output=True,
                                  encoding="utf-8")

    def test_shrinking_edit_exits_zero(self):
        after = ("\\section{Methods}\nFive filters.\n"
                 "\\section{Results}\nThe slope is negative for all clusters.\n")
        result = self.run_gate(BEFORE, after)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("GROWTH", result.stdout)

    def test_unjustified_growth_exits_one_with_strong_finding(self):
        after = BEFORE.replace(
            "The slope is negative for all clusters.",
            "The slope is negative for all clusters, and this additional "
            "sentence explains the same fact again in more words.")
        result = self.run_gate(BEFORE, after)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("length-growth:Results", result.stdout)

    def test_allowed_growth_exits_zero_and_records_reason(self):
        after = BEFORE.replace(
            "The slope is negative for all clusters.",
            "The slope is negative for all clusters, and the user asked for "
            "an added robustness paragraph here.")
        result = self.run_gate(BEFORE, after,
                               "--allow", "Results=user requested the addition")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("length-growth-justified:Results", result.stdout)
        self.assertIn("user requested the addition", result.stdout)

    def test_comment_and_math_growth_does_not_count(self):
        after = BEFORE.replace(
            "The slope is negative for all clusters.",
            "The slope is negative for all clusters. % a very long trailing "
            "comment that adds many source words but zero rendered prose\n"
            "\\begin{equation}\\label{eq:x}\ny = a x + b + c + d\n\\end{equation}"
            " with $a$ and $b$ inline")
        # Tolerance ZERO: the projection's `[MATH]` / `[math]` placeholders once
        # counted as words, and a tolerance of two was hiding exactly that.
        result = self.run_gate(BEFORE, after, "--tolerance-words", "0")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("grew by 3 words", result.stdout)   # with, and, inline

    def test_json_report_uses_shared_schema(self):
        after = BEFORE.replace("for all clusters", "for all clusters everywhere")
        result = self.run_gate(BEFORE, after, "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "sci-paper.feedback.v1")
        rules = [finding["rule"] for finding in report["findings"]]
        self.assertTrue(any(rule.startswith("length-growth:") for rule in rules))

    def test_missing_before_source_is_configuration_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            after_path = Path(temporary) / "after.tex"
            after_path.write_text(BEFORE, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(GATE), str(after_path)],
                text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("exactly one of --before or --git-ref", result.stderr)

    def test_section_rename_nets_to_zero_but_documents_the_pair(self):
        after = BEFORE.replace("\\section{Results}",
                               "\\section{Experimental Results}")
        result = self.run_gate(BEFORE, after)
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)
        self.assertIn("length-growth:Experimental Results", result.stdout)

    def test_negative_tolerance_is_configuration_failure(self):
        result = self.run_gate(BEFORE, BEFORE, "--tolerance-words", "-1")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("must be >= 0", result.stderr)

    def test_empty_allow_total_is_configuration_failure(self):
        result = self.run_gate(BEFORE, BEFORE, "--allow-total", "  ")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("non-empty reason", result.stderr)

    def test_allow_matches_section_by_substring(self):
        after = BEFORE.replace(
            "The slope is negative for all clusters.",
            "The slope is negative for all clusters, with an added sentence "
            "the author explicitly requested during review.")
        result = self.run_gate(BEFORE, after, "--allow", "Res=author request")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("length-growth-justified:Results", result.stdout)

    def test_ambiguous_allow_key_is_configuration_failure(self):
        before = (BEFORE + "\\section{Results and Limitations}\n"
                  "A closing remark sits here.\n")
        result = self.run_gate(before, before, "--allow", "Results=reason")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("ambiguous", result.stderr)

    def test_allowed_subtolerance_growth_is_credited_to_the_net(self):
        # Methods grows 3 words (allowed), Results grows 3 words (not allowed);
        # tolerance 5 flags neither section, and the documented net formula
        # (total growth minus justified growth) gives 6 - 3 = 3 <= 5 -> exit 0.
        after = BEFORE.replace(
            "The estimator uses five filters.",
            "The estimator uses five filters chosen before any unblinding.")
        after = after.replace(
            "The slope is negative for all clusters.",
            "The slope is negative for all clusters in the current sample.")
        blocked = self.run_gate(BEFORE, after, "--tolerance-words", "2")
        self.assertEqual(blocked.returncode, 1, blocked.stderr)
        credited = self.run_gate(BEFORE, after, "--tolerance-words", "5",
                                 "--allow", "Methods=author request")
        self.assertEqual(credited.returncode, 0,
                         credited.stdout + credited.stderr)

    def test_optional_argument_heading_rename_stays_neutral(self):
        before = BEFORE.replace("\\section{Results}",
                                "\\section[Res]{Results}")
        after = before.replace("\\section[Res]{Results}",
                               "\\section[Res]{Results of the Blind Analysis}")
        result = self.run_gate(before, after)
        self.assertEqual(result.returncode, 0,
                         result.stdout + result.stderr)

    def test_require_shrink_fails_a_pass_that_barely_cut(self):
        # Nine prose words before; dropping one word is an 11% cut, short of
        # the 30% required, so the gate must refuse to close green.
        after = BEFORE.replace("The estimator uses five filters.",
                               "The estimator uses filters.")
        result = self.run_gate(BEFORE, after, "--require-shrink", "0.3")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("length-shrink-short", result.stdout)
        self.assertIn("NOT MET", result.stdout)

    def test_require_shrink_passes_when_the_cut_is_deep_enough(self):
        after = ("\\section{Methods}\nFive filters.\n"
                 "\\section{Results}\nThe slope is negative.\n")
        result = self.run_gate(BEFORE, after, "--require-shrink", "30%",
                               "--format", "json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        budget = json.loads(result.stdout)["length_budget"]
        self.assertTrue(budget["shrink_met"])
        self.assertEqual(budget["required_shrink_words"], 4)

    def test_require_shrink_accepts_a_word_count(self):
        after = BEFORE.replace("The estimator uses five filters.",
                               "The estimator uses filters.")
        result = self.run_gate(BEFORE, after, "--require-shrink", "1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.run_gate(BEFORE, after, "--require-shrink", "2")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_require_shrink_rejects_nonsense(self):
        # `100%` and `200%` once parsed as one and two WORDS; `inf` and `1e309`
        # escaped as an uncaught OverflowError. A percentage is a percentage.
        for bad in ("0", "-0.2", "1.5", "lots", "100%", "200%", "0%", "inf", "1e309",
                    "nan", "30%%"):
            result = self.run_gate(BEFORE, BEFORE, "--require-shrink", bad)
            self.assertEqual(result.returncode, 2, bad + result.stderr)
            self.assertIn("--require-shrink", result.stderr)

    def test_a_fraction_of_a_short_document_rounds_up_to_one_word(self):
        # 10% of the 12-word baseline is 1.2 words: rounding to nearest gave a
        # requirement of one word, but 10% of a five-word note gave zero and
        # an unchanged file closed green. The minimum cut rounds UP.
        after = BEFORE.replace("The estimator uses five filters.",
                               "The estimator uses filters.")
        result = self.run_gate(BEFORE, after, "--require-shrink", "10%",
                               "--format", "json")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["length_budget"]
                         ["required_shrink_words"], 2)

    def test_both_versions_are_assembled_from_their_input_children(self):
        # A root that only says `\input{body}` never changed when its child
        # shrank: the gate read the root alone while the removal map it closes
        # was built on the whole paper.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("before", "after"):
                (root / name).mkdir()
                (root / name / "main.tex").write_text("\\input{body}\n", encoding="utf-8")
            (root / "before" / "body.tex").write_text(BEFORE, encoding="utf-8")
            (root / "after" / "body.tex").write_text(
                BEFORE.replace("The estimator uses five filters.", "Five filters."),
                encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(GATE), str(root / "after" / "main.tex"),
                 "--before", str(root / "before" / "main.tex"),
                 "--require-shrink", "2", "--format", "json"],
                text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        budget = json.loads(result.stdout)["length_budget"]
        self.assertEqual((budget["total_before"], budget["total_after"]), (12, 9))

    def test_json_report_is_self_describing(self):
        after = BEFORE.replace("for all clusters", "for all clusters everywhere")
        result = self.run_gate(BEFORE, after, "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        budget = report["length_budget"]
        self.assertEqual(budget["gate_exit"], 1)
        self.assertGreater(budget["net_unjustified_growth"], 0)
        self.assertEqual(budget["tolerance_words"], 0)


if __name__ == "__main__":
    unittest.main()
