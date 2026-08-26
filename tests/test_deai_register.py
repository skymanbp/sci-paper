from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_register as register


def build_profile(directory: Path, passages: list[str]) -> Path:
    bank = directory / "exemplar_paragraphs.jsonl"
    with bank.open("w", encoding="utf-8") as handle:
        for text in passages:
            handle.write(json.dumps({"section": "method", "text": text}) + "\n")
    register.calibrate(directory)
    return directory


NATIVE_PASSAGE = (
    "The aperture mass is measured on the shear catalog at each epoch, and "
    "the accuracy of the recovered convergence is quoted against the "
    "injection grid. The sub-halo population is drawn from the same plane, "
    "and the classifier used for the shortlist is held out from training."
)


class TestTermNormalisation(unittest.TestCase):
    def test_possessive_folds_onto_the_bare_term(self):
        self.assertEqual(register.normalize("sub-halo's"), "sub-halo")

    def test_case_folds(self):
        self.assertEqual(register.normalize("AUC"), "auc")


class TestMacroTerms(unittest.TestCase):
    def test_word_rendering_macro_is_a_term(self):
        macros = register.macro_terms("\\newcommand{\\AUC}{\\mathrm{AUC}}")
        self.assertEqual(macros, {"AUC": "AUC"})

    def test_subscript_decoration_is_not_a_term(self):
        # \Kraw renders S_sad: "sad" is a subscript label, not vocabulary.
        # Reading it as a term is what produced 'sad', 'det', 'nat' and 'crit'
        # as fake foreign words.
        self.assertEqual(register.macro_terms("\\newcommand{\\Kraw}{S_\\mathrm{sad}}"),
                         {})

    def test_superscript_decoration_is_not_a_term(self):
        self.assertEqual(
            register.macro_terms("\\newcommand{\\Kref}{K^\\mathrm{ref}}"), {})


class TestCompoundFrequency(unittest.TestCase):
    TABLE = {"aperture": 312, "mass": 900, "held": 24, "out": 800,
             "cross": 300, "validation": 2, "auc": 1}

    def test_compound_is_judged_by_its_rarest_part(self):
        df, basis = register.corpus_document_frequency("aperture-mass", self.TABLE)
        self.assertEqual((df, basis), (312, "aperture"))

    def test_a_compound_with_one_foreign_part_stays_foreign(self):
        df, basis = register.corpus_document_frequency("cross-validation", self.TABLE)
        self.assertEqual((df, basis), (2, "validation"))

    def test_single_word_uses_its_own_count(self):
        self.assertEqual(register.corpus_document_frequency("auc", self.TABLE),
                         (1, "auc"))


class TestFindings(unittest.TestCase):
    def test_no_lexicon_yields_no_findings_and_an_unmeasured_axis(self):
        self.assertEqual(register.register_findings("AUC AUC AUC", None), [])
        self.assertEqual(register.register_axis_status(None)["status"], "unmeasured")

    def test_small_corpus_is_degraded_not_measured(self):
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 10)
            self.assertEqual(register.register_axis_status(profile)["status"],
                             "degraded")
            self.assertEqual(register.register_findings("AUC " * 10, profile), [])

    def test_foreign_macro_term_is_flagged_and_native_terms_are_not(self):
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            document = (
                "\\newcommand{\\AUC}{\\mathrm{AUC}}\n"
                "\\section{Validation}\n"
                "The epoch and accuracy of the aperture mass are quoted. "
                "We report \\AUC, \\AUC, \\AUC, \\AUC, \\AUC and \\AUC here.\n"
            )
            rules = {finding["rule"]
                     for finding in register.register_findings(document, profile)}
            self.assertIn("register-foreign:auc", rules)
            for native in ("epoch", "accuracy", "aperture", "mass"):
                self.assertNotIn(f"register-foreign:{native}", rules)

    def test_a_single_mention_is_not_enough(self):
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            document = "\\section{Validation}\nWe report the AUC once.\n"
            self.assertEqual(register.register_findings(document, profile), [])

    def test_findings_are_advisories_never_l0_targets(self):
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            document = ("\\section{Validation}\n"
                        "The logit, logit, logit, logit and logit values.\n")
            findings = register.register_findings(document, profile)
            self.assertTrue(findings)
            for finding in findings:
                self.assertEqual(finding["kind"], "advisory")
                self.assertEqual(finding["layer"], "L0")


if __name__ == "__main__":
    unittest.main()
