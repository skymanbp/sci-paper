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


if __name__ == "__main__":
    unittest.main()
