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


def foreign_document(term: str = "logit") -> str:
    """A document carrying one foreign term often enough to clear the floor.

    Derived from `MIN_MANUSCRIPT_USES` rather than written out, so moving the
    operating point cannot silently turn these fixtures into no-ops.
    """
    return ("\\section{Validation}\n"
            + f"The {term} values. " * register.MIN_MANUSCRIPT_USES + "\n")


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
        # \Kraw renders K_raw: "raw" is a subscript label, not vocabulary.
        # Reading it as a term is what produced fake foreign words out of the
        # subscript labels of seven such macros.
        self.assertEqual(register.macro_terms("\\newcommand{\\Kraw}{K_\\mathrm{raw}}"),
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

    def test_a_compound_with_one_short_part_is_judged_on_its_long_part(self):
        # `no-dip`: "no" is too short to carry meaning, "dip" is the word.
        self.assertEqual(register.corpus_document_frequency("no-mass", self.TABLE),
                         (900, "mass"))


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
        # The repetition count is derived, not written out: three fixtures once
        # hard-coded 5 or 6 uses and went silently green-to-red the moment the
        # operating point moved to 15 (EVALUATION section 18.4).
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            document = (
                "\\newcommand{\\AUC}{\\mathrm{AUC}}\n"
                "\\section{Validation}\n"
                "The epoch and accuracy of the aperture mass are quoted. "
                "We report " + "\\AUC, " * register.MIN_MANUSCRIPT_USES + "here.\n"
            )
            rules = {finding["rule"]
                     for finding in register.register_findings(document, profile)}
            self.assertIn("register-zero:auc", rules)
            for native in ("epoch", "accuracy", "aperture", "mass"):
                self.assertNotIn(f"register-zero:{native}", rules)
                self.assertNotIn(f"register-foreign:{native}", rules)

    def test_a_single_mention_of_an_unattested_word_is_flagged(self):
        # Owner rule 2026-09-04: every word is looked up, and one in zero
        # corpus passages is a strong marker unless the text supplies a reason.
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            document = "\\section{Validation}\nWe report the auc once.\n"
            findings = {f["rule"]: f
                        for f in register.register_findings(document, profile)}
            finding = findings["register-zero:auc"]
            self.assertEqual(finding["strength"], "strong")
            self.assertEqual(finding["reference"]["use_floor"], 1)
            self.assertIn("coins", finding["recommended_action"])
            # The section title is not body prose on either side of the ratio.
            self.assertNotIn("register-zero:validation", findings)

    def test_a_single_mention_of_a_rare_attested_word_is_not_enough(self):
        # Rarity below the gate still needs the manuscript to LEAN on the term;
        # absence is the only fact that speaks at floor 1.
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(
                Path(raw), [NATIVE_PASSAGE] * 12000 + ["The logit values."])
            document = "\\section{Validation}\nWe report the logit once.\n"
            rules = {f["rule"] for f in
                     register.register_findings(document, profile)}
            self.assertFalse({r for r in rules if r.endswith(":logit")})
            rules = {f["rule"] for f in
                     register.register_findings(foreign_document(), profile)}
            self.assertIn("register-foreign:logit", rules)
            self.assertNotIn("register-zero:logit", rules)

    def test_findings_are_advisories_never_l0_targets(self):
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            document = foreign_document()
            findings = register.register_findings(document, profile)
            self.assertTrue(findings)
            for finding in findings:
                self.assertEqual(finding["kind"], "advisory")
                self.assertEqual(finding["layer"], "L0")


class ZeroHitJustificationTest(unittest.TestCase):
    """The reasons the owner allows for an unattested word, read from the text.

    A zero-hit word is strong unless the manuscript itself says why it is
    there: it defines the word, the word is a name, or the field writes its
    stem. Each downgrades to ordinary and names its reason; none is silent.
    """

    def _findings(self, body: str):
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            return register.register_findings(
                "\\section{Validation}\n" + body + "\n", profile)

    def _one(self, body: str, term: str):
        found = [f for f in self._findings(body) if f["rule"] == f"register-zero:{term}"]
        self.assertEqual(len(found), 1, body)
        return found[0]

    def test_an_acronym_expanded_in_text_is_defined_here(self):
        finding = self._one("The normalised aperture flux (NAF) is measured. "
                            "The NAF is quoted.", "naf")
        self.assertEqual(finding["strength"], "ordinary")
        self.assertEqual(finding["observed"]["justification"], "defined-here")

    def test_a_defining_sentence_marks_a_coined_term(self):
        finding = self._one("We call this quantity the saddleness. "
                            "The saddleness is measured.", "saddleness")
        self.assertEqual(finding["observed"]["justification"], "defined-here")
        self.assertIn("definition precedes every use", finding["message"])

    def test_a_word_capitalised_at_every_use_is_a_name(self):
        finding = self._one("The catalog from Euclid is used. "
                            "We match to Euclid positions.", "euclid")
        self.assertEqual(finding["observed"]["justification"], "name")
        self.assertEqual(finding["strength"], "ordinary")

    def test_a_derived_form_of_a_native_word_names_its_stem(self):
        finding = self._one("The shearing of the catalog is measured.", "shearing")
        self.assertEqual(finding["observed"]["justification"], "derived-form")
        self.assertEqual(finding["observed"]["native_stem"], "shear")
        self.assertIn("'shear'", finding["message"])

    def test_an_unexplained_word_is_strong_and_says_so(self):
        finding = self._one("The catalog is rescored after the cut.", "rescored")
        self.assertEqual(finding["strength"], "strong")
        self.assertIsNone(finding["observed"]["justification"])
        self.assertIn("Nothing in the manuscript", finding["message"])

    def test_a_sentence_initial_capital_is_not_name_evidence(self):
        finding = self._one("Rescored catalogs are used. The cut is applied.",
                            "rescored")
        self.assertEqual(finding["strength"], "strong")

    def test_the_stemmer_does_not_reach_below_three_letters(self):
        self.assertIsNone(register.native_stem("ins", {"in": 5}))
        self.assertIsNone(register.native_stem("rescored", {"score": 5}))
        self.assertEqual(register.native_stem("epochs", {"epoch": 5}), "epoch")
        self.assertEqual(register.native_stem("planes", {"plane": 5}), "plane")
        self.assertEqual(register.native_stem("fitted", {"fit": 5}), "fit")


class BodyProjectionTest(unittest.TestCase):
    """Detection must read the projection the corpus was built from.

    The corpus df comes from `exemplar_paragraphs.jsonl`, which drops the
    preamble and every `skip` bucket; detection read the whole raw file. An
    author's affiliation or a `\\bibitem` surname therefore had df 0 on one
    side and count >= 5 on the other, and the finding was manufactured by the
    asymmetry. Measured on 203 held-out refereed papers, 58.7% of register
    findings came from outside body prose.
    """

    def test_affiliation_front_matter_is_not_manuscript_vocabulary(self) -> None:
        document = ("\\title{A Study}\n"
                    "\\affiliation{Dipartimento di Fisica, Roma, Italia}\n"
                    "\\affiliation{Dipartimento di Fisica, Roma, Italia}\n"
                    "\\section{Methods}\n"
                    "The shear catalog is measured on the aperture mass.\n")
        self.assertNotIn("dipartimento", register.manuscript_terms(document))
        self.assertIn("shear", register.manuscript_terms(document))

    def test_bibliography_entries_are_not_manuscript_vocabulary(self) -> None:
        entries = "".join(
            f"\\bibitem[Blain et al.({y})]{{blain{y}}} Blain, A.~W.\n"
            for y in range(2001, 2010))
        document = ("\\section{Methods}\n"
                    "The shear catalog is measured.\n"
                    "\\begin{thebibliography}{}\n" + entries +
                    "\\end{thebibliography}\n")
        self.assertNotIn("blain", register.manuscript_terms(document))

    def test_a_skip_section_contributes_no_vocabulary(self) -> None:
        document = ("\\section{Methods}\n"
                    "The shear catalog is measured.\n"
                    "\\section{Acknowledgments}\n"
                    + "We thank Helsinki. " * 6 + "\n")
        self.assertNotIn("helsinki", register.manuscript_terms(document))

    def test_the_abstract_survives_the_preamble_drop(self) -> None:
        # AASTeX puts the abstract before the first \section, inside the very
        # block being dropped, and the corpus does carry abstracts.
        document = ("\\title{A Study}\n"
                    "\\begin{abstract}\n"
                    "We measure the convergence of the shear field.\n"
                    "\\end{abstract}\n"
                    "\\section{Methods}\n"
                    "The catalog is used.\n")
        terms = register.manuscript_terms(document)
        self.assertIn("convergence", terms)

    def test_line_numbers_still_index_the_original_document(self) -> None:
        # Blanking rather than deleting is what keeps section attribution
        # working; a deleted preamble would shift every body line.
        document = ("\\affiliation{Roma}\n"
                    "\\section{Methods}\n"
                    "The convergence is measured here.\n")
        self.assertEqual(register.manuscript_terms(document)["convergence"]["line"], 3)

    def test_macros_defined_in_the_preamble_still_resolve(self) -> None:
        # The definition is dropped with the preamble; its uses are body prose.
        document = ("\\newcommand{\\AUC}{\\mathrm{AUC}}\n"
                    "\\section{Validation}\n"
                    "We report \\AUC, \\AUC, \\AUC, \\AUC and \\AUC here.\n")
        self.assertIn("auc", register.manuscript_terms(document))

    # Third instance of the asymmetry: the corpus side blanks every math span,
    # detection blanked only what fit on one line. On the advisor-round Letter
    # the macro names inside a multi-line equation (`\dsep`, `\rmain`), a float
    # option (`htb`), a bibliography style and a `\texttt` identifier all
    # surfaced as zero-hit "words".
    def test_a_macro_inside_multi_line_math_is_not_a_word(self) -> None:
        document = ("\\section{Methods}\n"
                    "The convergence is\n"
                    "\\begin{equation}\n"
                    "\\kappa = \\frac{\\kappa_\\rmain(\\dsep)}{2}\n"
                    "\\end{equation}\n"
                    "and $\\dsep\n"
                    "/ r$ spans lines.\n")
        terms = register.manuscript_terms(document)
        self.assertNotIn("rmain", terms)
        self.assertNotIn("dsep", terms)
        self.assertIn("convergence", terms)
        self.assertIn("spans", terms)

    def test_float_options_bibliography_commands_and_code_are_not_words(self) -> None:
        document = ("\\section{Methods}\n"
                    "\\begin{figure*}[!htb]\n\\end{figure*}\n"
                    "The \\texttt{cw\\_mscale} mode is used.\n"
                    "\\bibliographystyle{aasjournalv7}\n")
        terms = register.manuscript_terms(document)
        for leaked in ("htb", "mscale", "aasjournalv", "aasjournalv7"):
            self.assertNotIn(leaked, terms)
        self.assertIn("mode", terms)
        self.assertEqual(terms["mode"]["line"], 4)


class BankResolutionTest(unittest.TestCase):
    """A bank too coarse for the gate must say so, not report `measured`.

    `MIN_CORPUS_PASSAGES` is a count and `RARE_DF_RATE` is a rate. A bank of n
    passages cannot express a non-zero rate below 1/n, so below ~10,000
    passages the rule silently becomes "df == 0" while the axis still claimed
    `measured` with no reason. The shipped `wgl-letter` profile (706 passages,
    14.2x coarser than the gate) was running that different rule in production.
    """

    def test_the_threshold_is_the_reciprocal_of_the_gate(self) -> None:
        boundary = int(1 / register.RARE_DF_RATE)
        self.assertFalse(register.resolves_rare_rate(boundary))
        self.assertTrue(register.resolves_rare_rate(boundary + 1))

    def test_an_empty_bank_does_not_divide_by_zero(self) -> None:
        self.assertFalse(register.resolves_rare_rate(0))

    def test_a_coarse_bank_is_degraded_and_says_why(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            status = register.register_axis_status(profile)
            self.assertEqual(status["status"], "degraded")
            self.assertIn("coarser", status["reason"])
            self.assertIn("df == 0", status["reason"])

    def test_a_coarse_bank_still_emits_findings_marked_degraded(self) -> None:
        # Silencing them would convert a degraded measurement into zero
        # findings, which is the one thing this repository must never do.
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 600)
            findings = register.register_findings(foreign_document(), profile)
            self.assertTrue(findings)
            for finding in findings:
                self.assertEqual(finding["measurement_status"], "degraded")
                self.assertFalse(finding["reference"]["resolves_rare_rate"])

    def test_the_two_guards_keep_distinct_jobs(self) -> None:
        # Too small to speak at all, versus able to speak but running a coarser
        # rule than the documented one. Both are degraded; only one is silent.
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            profile = build_profile(Path(raw), [NATIVE_PASSAGE] * 10)
            self.assertEqual(
                register.register_findings(foreign_document(), profile), [])
            self.assertEqual(
                register.register_axis_status(profile)["status"], "degraded")


class SameFieldFallbackTest(unittest.TestCase):
    """A format variant borrows its field's bank, and says so.

    `wgl-letter` is a format, not a domain. Its 706-passage bank cannot express
    the 1e-4 gate, so "rare" collapsed to "df == 0" and core cosmology terms
    read as foreign: on 36 letter-format documents the letter bank produced 262
    findings the field bank did not -- `sne`, `bao`, `pantheon`, `posteriors`,
    and the word `letter` itself -- against 2 the other way.
    """

    def _pair(self, root: Path) -> Path:
        build_profile(root / "fld", [NATIVE_PASSAGE] * 12000)
        return build_profile(root / "fld-letter", [NATIVE_PASSAGE] * 600)

    def test_a_coarse_variant_borrows_the_field_bank(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            root = Path(raw)
            (root / "fld").mkdir()
            (root / "fld-letter").mkdir()
            variant = self._pair(root)
            _, source = register.resolving_lexicon(variant)
            self.assertEqual(source.name, "fld")

    def test_the_borrowed_bank_is_named_not_applied_silently(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            root = Path(raw)
            (root / "fld").mkdir()
            (root / "fld-letter").mkdir()
            status = register.register_axis_status(self._pair(root))
            self.assertEqual(status["status"], "measured")
            self.assertIn("fld", status["reason"])
            finding = register.register_findings(foreign_document(),
                                                 root / "fld-letter")[0]
            self.assertEqual(finding["reference"]["borrowed_from"], "fld")

    def test_a_field_with_no_variant_suffix_never_borrows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            root = Path(raw) / "solo"
            root.mkdir()
            build_profile(root, [NATIVE_PASSAGE] * 600)
            _, source = register.resolving_lexicon(root)
            self.assertEqual(source, root)

    def test_a_variant_whose_field_is_also_coarse_stays_degraded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            root = Path(raw)
            (root / "fld").mkdir()
            (root / "fld-letter").mkdir()
            build_profile(root / "fld", [NATIVE_PASSAGE] * 600)
            variant = build_profile(root / "fld-letter", [NATIVE_PASSAGE] * 600)
            self.assertEqual(register.resolving_lexicon(variant)[1], variant)
            self.assertEqual(
                register.register_axis_status(variant)["status"], "degraded")

    def test_a_bank_that_resolves_keeps_its_own(self) -> None:
        with tempfile.TemporaryDirectory(prefix="register-") as raw:
            root = Path(raw)
            (root / "fld").mkdir()
            (root / "fld-letter").mkdir()
            build_profile(root / "fld", [NATIVE_PASSAGE] * 12000)
            variant = build_profile(root / "fld-letter",
                                    [NATIVE_PASSAGE] * 12000)
            self.assertEqual(register.resolving_lexicon(variant)[1], variant)


if __name__ == "__main__":
    unittest.main()
