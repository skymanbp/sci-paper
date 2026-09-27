from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import ai_ism_lint as lint

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

    def test_a_robust_statistics_term_is_not_tier_b(self):
        # The method's name, wrapped or not, leaves the cap to the adjective.
        methods = ("\\section{Methods}\nWe adopt a robust estimator of the mean.\n"
                   "The robust\nestimator down-weights outliers.\n"
                   "The fit is robust to the prior.\n")
        result = self.run_lint(methods, *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("L0=0", result.stdout)
        result = self.run_lint(methods + "A robust estimate of the mass follows.\n",
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
        self.assertEqual(statuses["L2.collocation"], "unmeasured")
        # Residue needs no calibration: it is deterministic on the text.
        self.assertEqual(statuses["L4.residue"], "measured")

    def test_residue_and_collocation_can_be_switched_off(self):
        result = self.run_lint(
            "\\section{Methods}\nWe initially tried a wider filter.\n",
            *self.isolated, "--no-residue", "--no-collocation",
            "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        axes = {axis["axis"] for axis in report["axes"]}
        self.assertNotIn("L4.residue", axes)
        self.assertNotIn("L2.collocation", axes)

    def test_self_history_residue_is_advisory_not_l0(self):
        result = self.run_lint(
            "\\section{Methods}\nWe initially tried a wider filter.\n",
            *self.isolated)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("residue-self-history", result.stdout)

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


def run_lint_file(name: str, text: str, *arguments: str, profile_root: Path | None = None):
    """Lint `text` written to a file called `name` (the suffix picks the reader)."""
    with tempfile.TemporaryDirectory() as temporary:
        draft = Path(temporary) / name
        draft.write_text(text, encoding="utf-8")
        command = [sys.executable, str(LINTER), str(draft), "--no-distribution",
                   "--no-structure", "--no-document-structure"]
        if profile_root is not None:
            command.extend(["--profile-root", str(profile_root)])
        command.extend(arguments)
        return subprocess.run(command, text=True, capture_output=True, encoding="utf-8")


class LexicalRuleTests(unittest.TestCase):
    """The 2026-09-27 audit's linter findings, each pinned."""

    def test_a_paragraph_initial_connector_is_judged_per_paragraph_not_per_line(self):
        # One-sentence-per-line LaTeX: a sentence-initial `Notably,` inside a
        # paragraph is Tier B within its cap, whatever line it starts.
        inside = run_lint_file("d.tex", "\\section{Results}\nWe ran the swap test.\n"
                                        "Notably, the covariance is stable.\n")
        self.assertEqual(inside.returncode, 0, inside.stdout + inside.stderr)
        joined = run_lint_file("d.tex", "\\section{Results}\nWe ran the swap test. "
                                        "Notably, the covariance is stable.\n")
        self.assertEqual(joined.returncode, 0, joined.stdout + joined.stderr)
        # The paragraph's first prose line, after a heading, is paragraph-initial.
        first = run_lint_file("d.tex", "\\section{Results}\nNotably, the covariance "
                                       "is stable.\n\nMore prose.\n")
        self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
        self.assertIn("tier-a:paragraph-start:notably", first.stdout)

    def test_an_opener_is_judged_where_a_sentence_starts(self):
        mid_line = run_lint_file("d.tex", "\\section{Results}\nWe ran the test. It is "
                                          "worth noting that this holds.\n")
        self.assertEqual(mid_line.returncode, 1, mid_line.stdout + mid_line.stderr)
        self.assertIn("tier-a:opener", mid_line.stdout)
        wrapped = run_lint_file("d.tex", "\\section{Results}\nThe field moved on, and\n"
                                         "in recent years the estimate settled.\n")
        self.assertEqual(wrapped.returncode, 0, wrapped.stdout + wrapped.stderr)

    def test_paved_and_showcased_are_tier_a(self):
        result = run_lint_file("d.tex", "\\section{Results}\nThis paved the way for the "
                                        "fit and showcased the model.\n")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("tier-a:paved", result.stdout)
        self.assertIn("tier-a:showcased", result.stdout)

    def test_every_em_dash_on_a_line_is_a_target_with_its_own_id(self):
        result = run_lint_file("d.tex", "\\section{Results}\nThe catalog---measured "
                                        "here---is used, so we delve and delve.\n",
                               "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        findings = json.loads(result.stdout)["findings"]
        rules = [finding["rule"] for finding in findings]
        self.assertEqual(rules.count("em-dash"), 2)
        ids = [finding["finding_id"] for finding in findings]
        self.assertEqual(len(ids), len(set(ids)))

    def test_command_arguments_are_not_prose(self):
        result = run_lint_file("d.tex", "\\section{Results}\nSee \\ref{sec:realm}, "
                                        "\\cite{delve-2020} and \\url{http://x/delve}.\n"
                                        "\\label{sec:realm}\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("L0=0", result.stdout)

    def test_three_parallel_needs_whole_words(self):
        result = run_lint_file("d.tex", "\\section{Results}\nIt is not only fast but "
                                        "also stable in Bland.\n")
        self.assertNotIn("three-parallel", result.stdout)

    def test_an_unreadable_tex_root_is_an_execution_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "dir.tex"
            directory.mkdir()
            result = subprocess.run(
                [sys.executable, str(LINTER), str(directory), "--no-distribution",
                 "--no-structure", "--no-document-structure"],
                text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_several_fields_without_a_choice_say_so(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile_root = Path(temporary)
            (profile_root / "fieldA").mkdir()
            (profile_root / "fieldB").mkdir()
            result = run_lint_file("d.tex", "\\section{Results}\nPlain prose.\n",
                                   profile_root=profile_root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("several field profiles", result.stderr)

    def test_an_unparseable_lexicon_is_an_execution_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile_root = Path(temporary)
            (profile_root / "f").mkdir()
            (profile_root / "f" / "lexicon.json").write_text("{not json", encoding="utf-8")
            result = run_lint_file("d.tex", "\\section{Results}\nPlain prose.\n",
                                   "--field", "f", profile_root=profile_root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_markdown_front_matter_and_rules_are_not_em_dashes(self):
        result = run_lint_file("d.md", "---\ntitle: x\n---\n\nSome prose here.\n\n---\n"
                                       "About 50% of the sample: the rest, revealing "
                                       "the bias.\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("L0=0", result.stdout)
        self.assertIn("colon-elaboration", result.stdout)
        self.assertIn("ing-tail:revealing", result.stdout)


class DocumentAssemblyTests(unittest.TestCase):
    """The lint path measures `ai_ism_lint.document_source`; its docstring says why."""

    def lint(self, files: "dict[str, str]"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, body in files.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(LINTER), str(root / "main.tex"),
                 "--no-distribution", "--no-structure",
                 "--no-document-structure"],
                text=True, capture_output=True, encoding="utf-8")

    def test_an_em_dash_inside_a_latex_comment_is_not_a_target(self):
        result = self.lint({"main.tex":
                            "% --- calibration block: values from run 3 ---\n"
                            "\\section{Methods}\nThe shear catalog is measured.\n"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("L0=0", result.stdout)

    def test_an_em_dash_in_prose_is_still_a_target(self):
        # Blanking comments must not disarm the rule on the prose it protects.
        result = self.lint({"main.tex": "\\section{Methods}\n"
                                        "The catalog---measured here---is used.\n"})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("L0=0", result.stdout)

    def test_an_included_file_is_measured_not_skipped(self):
        result = self.lint({
            "main.tex": "\\section{Methods}\nSee below.\n\\input{sections/body}\n",
            "sections/body.tex": "The catalog---measured here---is used.\n"})
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("L0=0", result.stdout)


class LegacyClassifierTests(unittest.TestCase):
    """`--ai-classifier` (the L3 legacy axis), with a stub in place of the joblib."""

    TEXT = ("\\section{Methods}\nWe fit the model to the binned counts.\n\n"
            "The residuals stay within the quoted errors.\n")

    class Stub:
        """A fitted classifier that gives every paragraph one probability."""

        classes_ = [0, 1]

        def __init__(self, probability: float):
            self.probability = probability

        def predict_proba(self, paragraphs):
            return [[1.0 - self.probability, self.probability] for _ in paragraphs]

    def lexical(self, loaded: dict, **options):
        """(L3 findings, L3 axis status or None, the patched loader)."""
        with mock.patch.object(lint, "load_ai_classifier", **loaded) as loader:
            findings, axes = lint.lexical_findings(self.TEXT, Path("d.tex"), None, **options)
        status = {axis["axis"]: axis for axis in axes}.get("L3.legacy_classifier")
        return [f for f in findings if f["layer"] == "L3"], status, loader

    def test_a_paragraph_at_or_above_the_threshold_is_a_degraded_advisory(self):
        legacy, status, _ = self.lexical({"return_value": self.Stub(0.9)}, ai_classifier=True)
        self.assertEqual(status["status"], "degraded")
        self.assertEqual([(f["location"]["start_line"], f["location"]["end_line"])
                          for f in legacy], [(1, 2), (4, 4)])
        for finding in legacy:
            self.assertEqual((finding["kind"], finding["rule"], finding["measurement_status"]),
                             ("advisory", "legacy-classifier-high", "degraded"))
            self.assertEqual(finding["observed"], {"legacy_similarity_score": 0.9})
            self.assertEqual(finding["reference"]["user_threshold"], 0.7)
            self.assertAlmostEqual(finding["normalized_distance"], 0.2)
        # The test is `score < threshold`, so a score at the threshold is flagged.
        at_threshold, _, _ = self.lexical({"return_value": self.Stub(0.5)},
                                          ai_classifier=True, ai_threshold=0.5)
        self.assertEqual(len(at_threshold), 2)

    def test_a_score_below_the_threshold_leaves_the_axis_degraded_and_silent(self):
        legacy, status, _ = self.lexical({"return_value": self.Stub(0.5)}, ai_classifier=True)
        self.assertEqual((legacy, status["status"]), ([], "degraded"))

    def test_no_classifier_is_unmeasured(self):
        for loaded, reason in (
                ({"return_value": None}, "ai_ism_classifier.joblib is unavailable"),
                ({"side_effect": ImportError("No module named 'joblib'")}, "joblib")):
            legacy, status, _ = self.lexical(loaded, ai_classifier=True)
            self.assertEqual((legacy, status["status"]), ([], "unmeasured"))
            self.assertIn(reason, status["reason"])

    def test_with_the_option_off_no_legacy_axis_is_reported_or_loaded(self):
        legacy, status, loader = self.lexical({"return_value": self.Stub(0.9)})
        self.assertEqual((legacy, status), ([], None))
        loader.assert_not_called()


class SkillMirrorTests(unittest.TestCase):
    """skills/paper/SKILL.md mirrors the four L0 patterns and the validator
    holds it to them both ways (audit H8): `paved` and `showcased` once sat in
    the skill's table while the linter passed them."""

    SKILL = (ROOT / "skills" / "paper" / "SKILL.md").read_text(encoding="utf-8")

    def failures(self, skill_text: str | None = None) -> list[str]:
        """`validator_check`'s failure messages on a repository holding `skill_text`."""
        messages: list[str] = []

        def require(condition, message):
            if not condition:
                messages.append(message)

        with tempfile.TemporaryDirectory() as temporary:
            skill = Path(temporary) / "skills" / "paper" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(self.SKILL if skill_text is None else skill_text,
                             encoding="utf-8")
            lint.validator_check(Path(temporary), require)
        return messages

    def test_the_repository_passes_its_own_check(self):
        self.assertEqual(self.failures(), [])

    def test_a_form_the_skill_drops_is_reported(self):
        for name, listed, shorter, form in (
                ("TIER_A_PATTERN", "`pave / paves / paved / paving`",
                 "`pave / paves / paving`", "paved"),
                ("TIER_A_OPENER_PATTERN", "`It is worth noting`, ", "", "it is worth noting"),
                ("TIER_A_PARAGRAPH_CONNECTOR_PATTERN", ", `Notably,`", "", "Notably,"),
                ("TIER_B_PATTERN", "`intricate`, ", "", "intricate")):
            with self.subTest(name):
                self.assertEqual(self.SKILL.count(listed), 1)
                failures = self.failures(self.SKILL.replace(listed, shorter))
                self.assertEqual(len(failures), 1, failures)
                self.assertIn(f"mirror of {name} ", failures[0])
                self.assertIn(f"matched but not listed=[{form!r}]", failures[0])

    def test_a_form_the_linter_drops_is_reported(self):
        for name, alternative, form in (
                ("TIER_A_PATTERN", "paved|", "paved"),
                ("TIER_A_OPENER_PATTERN", "|it is worth noting", "It is worth noting"),
                ("TIER_A_PARAGRAPH_CONNECTOR_PATTERN", "|Notably", "Notably,"),
                ("TIER_B_PATTERN", "intricate|", "intricate")):
            with self.subTest(name):
                pattern = lint.MIRRORED[name]
                self.assertEqual(pattern.pattern.count(alternative), 1)
                narrower = re.compile(pattern.pattern.replace(alternative, ""), pattern.flags)
                with mock.patch.dict(lint.MIRRORED, {name: narrower}):
                    failures = self.failures()
                self.assertEqual(len(failures), 1, failures)
                self.assertIn(f"mirror of {name} ", failures[0])
                self.assertIn(f"listed but not matched=[{form!r}]", failures[0])

    def test_a_pattern_language_is_its_forms_without_their_context(self):
        self.assertEqual(lint.pattern_language(re.compile(r"(?i)\bfoster(?:s|ing|ed)?\b")),
                         {"foster", "fosters", "fostering", "fostered"})
        self.assertEqual(lint.pattern_language(lint.TIER_A_PARAGRAPH_CONNECTOR_PATTERN),
                         {"Importantly,", "Interestingly,", "Notably,", "Crucially,"})
        with self.assertRaises(ValueError):  # an unbounded pattern has no finite mirror
            lint.pattern_language(re.compile(r"\bdelv\w+"))


if __name__ == "__main__":
    unittest.main()
