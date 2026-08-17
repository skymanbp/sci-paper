from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINTER = ROOT / "tools" / "ai_ism_lint.py"


class LinterCliTests(unittest.TestCase):
    def run_lint(self, text: str, *arguments: str, profile_root: Path | None = None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            draft.write_text(text, encoding="utf-8")
            command = [sys.executable, str(LINTER), str(draft)]
            if profile_root is not None:
                command.extend(["--profile-root", str(profile_root)])
            command.extend(arguments)
            return subprocess.run(command, text=True, capture_output=True,
                                  encoding="utf-8")

    @property
    def isolated(self):
        return ("--no-distribution", "--no-structure",
                "--no-document-structure")

    def test_advisory_only_returns_zero(self):
        result = self.run_lint(
            "\\section{Methods}\nIn order to estimate the value, we fit the model.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("advisories=1", result.stdout)

    def test_tier_a_and_em_dash_return_one_without_nameerror(self):
        result = self.run_lint(
            "\\section{Introduction}\nWe delve into the result — carefully.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("NameError", result.stderr)
        self.assertIn("L0=2", result.stdout)

    def test_one_tier_b_occurrence_is_within_cap(self):
        result = self.run_lint(
            "\\section{Results}\nThe estimator is robust under this test.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("L0=0", result.stdout)

    def test_paragraph_initial_furthermore_is_tier_b_within_cap(self):
        result = self.run_lint(
            "\\section{Results}\nFurthermore, the estimate is reproducible.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("L0=0", result.stdout)

    def test_paragraph_initial_importantly_is_tier_a(self):
        result = self.run_lint(
            "\\section{Results}\nImportantly, the estimate is reproducible.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("tier-a:paragraph-start:importantly", result.stdout)

    def test_tier_b_excess_returns_one(self):
        result = self.run_lint(
            "\\section{Results}\nThe estimator is robust under this test.\n"
            "The covariance is robust under the same test.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("tier-b-excess:robust", result.stdout)

    def test_explicit_unavailable_field_is_configuration_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile_root = Path(temporary)
            result = self.run_lint(
                "\\section{Introduction}\nPlain scientific prose.\n",
                "--field", "no-such-field", *self.isolated,
                profile_root=profile_root)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("unavailable", result.stderr)

    def test_missing_calibration_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile_root = Path(temporary)
            (profile_root / "testfield").mkdir()
            result = self.run_lint(
                "\\section{Introduction}\nA short paragraph.\n",
                "--field", "testfield", "--format", "json",
                profile_root=profile_root)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        statuses = {axis["axis"]: axis["status"] for axis in report["axes"]}
        self.assertEqual(statuses["L1.distribution"], "unmeasured")
        self.assertEqual(statuses["L2.sentence_structure"], "unmeasured")
        self.assertEqual(statuses["L2.document_structure"], "unmeasured")

    def test_top_limits_details_not_summary(self):
        result = self.run_lint(
            "\\section{Methods}\nIn order to fit the model, we aim to estimate it.\n",
            *self.isolated, "--format", "json", "--top", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["emitted_findings"], 1)
        self.assertEqual(report["total_findings"], 2)
        self.assertEqual(report["summary"]["total_findings"], 2)

    def test_new_tier_a_word_pivotal_returns_one(self):
        result = self.run_lint(
            "\\section{Introduction}\nThis plays a pivotal role in the fit.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("tier-a:pivotal", result.stdout)

    def test_ing_tail_is_advisory(self):
        result = self.run_lint(
            "\\section{Results}\nThe slope is negative, highlighting the trend.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ing-tail:highlighting", result.stdout)

    def test_colon_elaboration_is_advisory_and_refs_are_exempt(self):
        result = self.run_lint(
            "\\section{Methods}\nSee \\ref{fig:map} for the selection"
            " function: the rule that maps halos onto peaks.\n",
            *self.isolated, "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        rules = [finding["rule"] for finding in report["findings"]]
        self.assertEqual(rules.count("colon-elaboration"), 1)

    def test_serves_as_is_style_substitution_advisory(self):
        result = self.run_lint(
            "\\section{Methods}\nThe peak serves as a reference point.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("style-substitution:serves as", result.stdout)

    def test_latex_comments_are_exempt_from_prose_pattern_rules(self):
        result = self.run_lint(
            "% Framing: aperture mass is the observable, highlighting scope.\n"
            "\\section{Methods}\nPlain prose. % Label: description, reflecting a note.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("colon-elaboration", result.stdout)
        self.assertNotIn("ing-tail", result.stdout)

    def test_new_tier_b_word_intricate_is_within_cap_once(self):
        result = self.run_lint(
            "\\section{Results}\nThe intricate geometry is resolved.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("L0=0", result.stdout)

    def test_output_file_does_not_duplicate_json_to_stdout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            output = root / "feedback.json"
            draft.write_text("\\section{Methods}\nPlain scientific prose.\n",
                             encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(LINTER), str(draft), *self.isolated,
                "--format", "json", "--output", str(output),
            ], text=True, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "sci-paper.feedback.v1")

    def test_paragraph_initial_connector_counts_once(self):
        # `Crucially` is in both TIER_A_PATTERN and the paragraph-connector
        # list, so without the span guard the same word produced two L0
        # targets, while `Notably`/`Importantly` (Tier B) produced one.
        result = self.run_lint(
            "\\section{Results}\nCrucially, the estimate is reproducible.\n",
            *self.isolated, "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        targets = [finding["rule"] for finding in report["findings"]
                   if finding["kind"] == "l0_target"]
        self.assertEqual(targets, ["tier-a:paragraph-start:crucially"])

    def test_tier_a_word_still_flagged_mid_sentence(self):
        # The guard must suppress only the connector's own span.
        result = self.run_lint(
            "\\section{Results}\nThe estimate is crucially dependent on it.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("tier-a:crucially", result.stdout)

    def test_malformed_profile_asset_is_execution_failure_not_l0(self):
        # Exit 1 means "an L0 target is present". A crash reported as 1 would
        # present an execution failure as a prose verdict, so any unexpected
        # exception must surface as 2.
        with tempfile.TemporaryDirectory() as temporary:
            profile_root = Path(temporary)
            field = profile_root / "testfield"
            field.mkdir()
            # Valid JSON, wrong shape: a list where an object is required.
            (field / "lexicon.json").write_text('["not", "an", "object"]',
                                                encoding="utf-8")
            result = self.run_lint(
                "\\section{Introduction}\nPlain scientific prose.\n",
                "--field", "testfield", *self.isolated,
                profile_root=profile_root)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("execution failed", result.stderr)


if __name__ == "__main__":
    unittest.main()
