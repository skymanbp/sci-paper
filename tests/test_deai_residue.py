from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_residue as residue

RESIDUE_CLI = TOOLS / "deai_residue.py"


def long_body(extra: str = "") -> str:
    """A methods section past the negative-label word floor, plus `extra`."""
    filler = ("The aperture mass is measured on the shear catalog around each "
              "cluster, and the tangential shear is convolved with a compensated "
              "filter of fixed scale before any peak is counted. ")
    return "\\section{Methods}\n" + filler * 30 + extra + "\n"


def run_residue(after: str, *arguments: str, before: str | None = None):
    """Run the CLI on `after` (and optionally a `before` snapshot) in a temp dir."""
    with tempfile.TemporaryDirectory() as raw:
        files = {"after.tex": after}
        if before is not None:
            files["before.tex"] = before
        for name, body in files.items():
            (Path(raw) / name).write_text(body, encoding="utf-8")
        argv = [sys.executable, str(RESIDUE_CLI), str(Path(raw) / "after.tex")]
        if before is not None:
            argv += ["--before", str(Path(raw) / "before.tex")]
        return subprocess.run(argv + list(arguments), text=True,
                              capture_output=True, encoding="utf-8")


class SelfHistoryTests(unittest.TestCase):
    def rules(self, text):
        return {f["rule"]: f for f in residue.self_history_findings(text)}

    def test_high_precision_family_is_strong(self):
        found = self.rules("\\section{Methods}\nWe no longer use a wider filter.\n")
        self.assertIn("residue-self-history:no longer", found)
        self.assertEqual(found["residue-self-history:no longer"]["strength"], "strong")

    def test_ordinary_family_is_ordinary(self):
        found = self.rules("\\section{Methods}\nWe now fix the filter scale.\n")
        self.assertEqual(found["residue-self-history:now"]["strength"], "ordinary")

    def test_a_citation_in_the_sentence_exempts_it(self):
        found = self.rules("\\section{Methods}\nWe initially followed \\citet{x}.\n")
        self.assertEqual(found, {})

    def test_history_about_the_literature_is_not_self_history(self):
        found = self.rules("\\section{Intro}\nThe method was initially proposed "
                           "for galaxy clusters.\n")
        self.assertEqual(found, {})

    def test_the_action_never_says_delete_the_negation(self):
        for action in (residue.HISTORY_ACTION, residue.NEGATIVE_LABEL_ACTION,
                       residue.EDIT_META_ACTION):
            low = action.lower()
            self.assertNotIn("delete the negation", low)
            self.assertNotIn("remove the negation", low)
            self.assertNotIn("drop the negation", low)


class AbsenceTests(unittest.TestCase):
    def found(self, text):
        return residue.absence_findings(text)

    def test_never_is_strong(self):
        found = self.found("\\section{Methods}\nThe characterization head never "
                           "participates in the detection decision.\n")
        self.assertEqual([(f["rule"], f["strength"], f["observed"]["phrase"]) for f in found],
                         [("residue-absence", "strong", "never")])

    def test_the_template_form_is_strong(self):
        found = self.found("\\section{Methods}\nNo minimum configuration support is "
                           "applied at any layer.\n")
        self.assertEqual([f["strength"] for f in found], ["strong"])
        self.assertEqual(found[0]["observed"]["phrase"],
                         "no minimum configuration support is applied")

    def test_carries_no_is_ordinary(self):
        found = self.found("\\section{Data}\nThe reference stratum carries no quoted "
                           "number.\n")
        self.assertEqual([(f["strength"], f["observed"]["phrase"]) for f in found],
                         [("ordinary", "carries no")])

    def test_a_hyphenated_compound_is_a_name(self):
        self.assertEqual(self.found("\\section{Data}\nThe never-touched controls are "
                                    "scored last.\n"), [])

    def test_a_citation_makes_it_a_baseline_contrast(self):
        self.assertEqual(self.found("\\section{Intro}\nUnlike \\citet{x}, the null is "
                                    "never an assumed noise field.\n"), [])

    def test_the_action_keeps_load_bearing_qualifiers(self):
        low = residue.ABSENCE_ACTION.lower()
        self.assertIn("scope limit", low)
        self.assertNotIn("delete the negation", low)

    def test_the_families_are_read_between_their_own_markers(self):
        start, end = residue.ABSENCE_MARKERS
        text = f"{start}\n- `never`, `carries no`\n{end}\n`is not used`"
        self.assertEqual(residue.family_listed_in(text, residue.ABSENCE_MARKERS),
                         {"never", "carries no"})


class EditMetaTests(unittest.TestCase):
    def test_literal_marks_are_strong(self):
        text = "\\section{Results}\nThe slope (removed) is negative. TODO check.\n"
        found = residue.edit_meta_findings(text)
        self.assertEqual([f["observed"]["mark"] for f in found], ["(removed)", "TODO"])
        self.assertTrue(all(f["strength"] == "strong" for f in found))

    def test_lower_case_todo_in_prose_is_not_a_mark(self):
        found = residue.edit_meta_findings("\\section{Results}\nMuch remains to do.\n")
        self.assertEqual(found, [])

    def test_a_mark_inside_a_comment_is_not_reported_by_the_cli(self):
        result = run_residue("\\section{Results}\nThe slope is negative. % (removed) old\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("residue-edit-meta", result.stdout)

    def test_a_mark_in_a_heading_or_caption_is_visible(self):
        # The vocabulary projection blanks headings and floats; a `TODO` a
        # reader sees in a caption was invisible to the scan that shared it.
        text = ("\\section{Results TODO}\nClean prose.\n\n"
                "\\begin{figure}\n\\caption{TODO redo panel b}\n\\end{figure}\n")
        found = residue.residue_findings(text)
        marks = [(f["observed"]["mark"], f["location"]["start_line"]) for f in found
                 if f["rule"] == "residue-edit-meta"]
        self.assertEqual(marks, [("TODO", 1), ("TODO", 5)])
        # The preamble stays out: a macro definition is not prose an edit left.
        found = residue.residue_findings("\\newcommand{\\TODO}{x}\n\\section{Results}\nClean.\n")
        self.assertEqual([f for f in found if f["rule"] == "residue-edit-meta"], [])

    def test_a_phrase_mark_wrapped_at_a_line_break_is_one_mark(self):
        text = "\\section{Results}\nAs noted in the revised\nversion, the slope is negative.\n"
        found = residue.edit_meta_findings(text)
        self.assertEqual([(f["observed"]["mark"], f["location"]["start_line"]) for f in found],
                         [("in the revised version", 2)])

    def test_a_procedure_we_have_added_is_not_an_editing_mark(self):
        # Twelve of twelve `we have added/removed/revised` in the held-out
        # refereed papers were procedure, and the Planck revised version was
        # another paper's; only a document object makes the phrase a mark.
        marks = lambda text: [f["observed"]["mark"] for f in residue.edit_meta_findings(text)]
        self.assertEqual(marks("\\section{Data}\nWe have added uniform Gaussian noise.\n"), [])
        self.assertEqual(marks("\\section{Data}\nWe have removed the emission from the core.\n"), [])
        self.assertEqual(marks("\\section{Data}\nAs reported in the revised version of "
                               "\\citet{planck}, the bias is small.\n"), [])
        self.assertEqual(marks("\\section{Data}\nWe have added a paragraph on the bias.\n"),
                         ["We have added a paragraph"])
        self.assertEqual(marks("\\section{Data}\nWe have revised the text of Section 2.\n"),
                         ["We have revised the text"])


class NegativeLabelTests(unittest.TestCase):
    def test_a_caption_negating_something_the_body_never_names_is_ordinary(self):
        text = long_body("\\begin{figure}\\caption{Peak counts without the saddle "
                         "correction.}\\end{figure}")
        found = residue.negative_label_findings(text)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["rule"], "residue-negative-label")
        self.assertEqual(found[0]["strength"], "ordinary")
        self.assertIn("saddle", found[0]["observed"]["absent_from_body"])

    def test_a_negation_whose_object_the_body_names_is_fine(self):
        text = long_body("The saddle correction is applied to every map. "
                         "\\begin{figure}\\caption{Peak counts without the saddle "
                         "correction.}\\end{figure}")
        self.assertEqual(residue.negative_label_findings(text), [])

    def test_a_short_document_is_not_judged(self):
        text = ("\\section{Methods}\nShort.\n\\begin{figure}\\caption{Peak counts "
                "without the saddle correction.}\\end{figure}\n")
        self.assertEqual(residue.negative_label_findings(text), [])
        self.assertIn("not applied", residue.residue_axis_status(text)["reason"])

    def test_the_negated_object_stops_at_the_sentence_end(self):
        # A caption is several sentences; the object must not run into the next.
        caption = ("The volume renders the catalog, not a mass reconstruction. "
                   "The solid spheres mark each structure.")
        self.assertEqual([obj for obj, _ in residue.negated_objects(caption)],
                         ["a mass reconstruction"])
        text = long_body("A mass reconstruction is never made. "
                         "\\begin{figure}\\caption{" + caption + "}\\end{figure}")
        self.assertEqual(residue.negative_label_findings(text), [])

    def test_a_heading_negation_is_also_a_label(self):
        text = long_body("\\subsection{Results with no compensating kernel}")
        found = residue.negative_label_findings(text)
        self.assertEqual([f["observed"]["negated_object"] for f in found],
                         ["compensating kernel"])


class NegativeLabelAddedTests(unittest.TestCase):
    def test_a_patched_absence_is_strong(self):
        before = long_body("The saddle correction is applied to every map.")
        after = long_body("\\begin{figure}\\caption{Peak counts without the saddle "
                          "correction.}\\end{figure}")
        found = residue.negative_label_added_findings(before, after)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["rule"], "residue-negative-label-added")
        self.assertIn("saddle", found[0]["observed"]["removed_from_body"])

    def test_a_label_already_present_before_is_not_new(self):
        text = long_body("\\begin{figure}\\caption{Peak counts without the saddle "
                         "correction.}\\end{figure}")
        self.assertEqual(residue.negative_label_added_findings(text, text), [])

    def test_an_object_the_body_never_had_is_not_a_patched_absence(self):
        # `correction` alone was in the body; `saddle correction` never was, so
        # the new caption negates nothing the edit removed.
        before = long_body("The correction is applied.")
        after = long_body("The measurement is applied. \\begin{figure}\\caption{"
                          "Without the saddle correction}\\end{figure}")
        self.assertEqual(residue.negative_label_added_findings(before, after), [])

    def test_a_negation_the_old_caption_carried_is_not_new_when_the_caption_changes(self):
        before = long_body("The saddle correction is applied. \\begin{figure}"
                           "\\caption{Blue points, without the saddle correction.}"
                           "\\end{figure}")
        after = long_body("\\begin{figure}\\caption{Red points, without the saddle "
                          "correction.}\\end{figure}")
        self.assertEqual(residue.negative_label_added_findings(before, after), [])


class CliTests(unittest.TestCase):
    def test_strong_residue_exits_one_with_a_self_describing_report(self):
        result = run_residue("\\section{Methods}\nWe no longer use a wider filter.\n",
                             "--format", "json")
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "sci-paper.feedback.v1")
        self.assertEqual(report["residue_gate"]["gate_exit"], 1)
        self.assertFalse(report["residue_gate"]["diff_rule_ran"])

    def test_clean_document_exits_zero(self):
        result = run_residue("\\section{Methods}\nThe filter scale is fixed.\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("axis L4.residue: measured", result.stdout)

    def test_the_diff_rule_runs_with_a_baseline(self):
        before = long_body("The saddle correction is applied to every map.")
        after = long_body("\\begin{figure}\\caption{Peak counts without the saddle "
                          "correction.}\\end{figure}")
        result = run_residue(after, "--format", "json", before=before)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["residue_gate"]["diff_rule_ran"])
        self.assertIn("residue-negative-label-added",
                      [f["rule"] for f in report["findings"]])

    def test_missing_file_is_configuration_failure(self):
        result = subprocess.run(
            [sys.executable, str(RESIDUE_CLI), "no-such-file.tex"],
            text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2)


class ValidatorHookTests(unittest.TestCase):
    def test_the_word_family_is_read_between_the_markers(self):
        start, end = residue.FAMILY_MARKERS
        text = f"prose\n{start}\n- `initially`, `now`\n{end}\n`later`"
        self.assertEqual(residue.family_listed_in(text), {"initially", "now"})

    def test_the_repository_passes_its_own_check(self):
        messages = []

        def require(condition, message):
            if not condition:
                messages.append(message)

        summary = residue.validator_check(TOOLS.parent, require)
        self.assertEqual(messages, [])
        self.assertIn("in sync", summary)


if __name__ == "__main__":
    unittest.main()
