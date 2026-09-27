from __future__ import annotations

import contextlib
import io
import json
import statistics
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_docstructure as ds
import deai_partition as partition
import extract_style as es

LENSING_A = (
    "The aperture mass statistic isolates the tangential shear signal around "
    "each candidate peak. The same aperture mass filter suppresses the "
    "large-scale shear gradient across the field. Both properties make the "
    "aperture mass estimator suitable for substructure searches."
)
LENSING_B = (
    "The aperture mass significance depends on the local source density and "
    "the shape noise of the background sample. We therefore weight the "
    "aperture mass filter by the inverse shear variance in each cell."
)
UNRELATED = (
    "Spectroscopic follow-up of the brightest cluster galaxies proceeded on "
    "a different telescope during the second observing season. Redshift "
    "completeness reached ninety per cent for the magnitude-limited sample."
)
# Four sentences of ~17 words: every half of a split stays above MIN_WORDS.
FOUR_SENTENCES = (
    "The aperture mass statistic isolates the tangential shear signal around "
    "each candidate peak in the survey footprint. The same aperture mass "
    "filter suppresses the large-scale shear gradient across the field of "
    "view considered here. Both properties make the aperture mass estimator "
    "suitable for substructure searches in the cluster outskirts we study. "
    "We therefore weight the aperture mass filter by the inverse shear "
    "variance in each cell of the map."
)


def uniform_document(paragraph: str, per_section: int = 3) -> str:
    body = "\n\n".join([paragraph] * per_section)
    return "\n\n".join(f"\\section{{{name}}}\n\n{body}"
                       for name in ("Introduction", "Methods", "Results")) + "\n"


class PartitionTests(unittest.TestCase):
    def test_overlap_orders_related_above_unrelated(self):
        related = partition._overlap(LENSING_A, LENSING_B)
        unrelated = partition._overlap(LENSING_A, UNRELATED)
        self.assertGreater(related, unrelated)

    def test_apply_merge_and_split_preserve_words(self):
        text = ("\\section{Methods}\n\n" + LENSING_A + "\n\n" + LENSING_B
                + "\n\n\\section{Results}\n\n" + UNRELATED
                + "\n\n" + LENSING_A + "\n")
        sections = partition._parse(text)
        # the \section command line is its own fixed block; the two prose
        # paragraphs follow it
        self.assertTrue(sections[0]["blocks"][0]["fixed"])
        self.assertEqual(len(sections[0]["blocks"]), 3)
        words_before = sorted(
            w for s in sections for b in s["blocks"]
            for w in es.words(es.latex_to_plain(b["text"])))
        merged = partition._apply(sections, {
            "kind": "merge", "section": 0, "block": 1, "overlap": 1.0})
        words_after = sorted(
            w for s in merged for b in s["blocks"]
            for w in es.words(es.latex_to_plain(b["text"])))
        self.assertEqual(words_before, words_after,
                         "merge must not add or drop a single word")
        self.assertEqual(len(merged[0]["blocks"]), 2)
        split = partition._apply(sections, {
            "kind": "split", "section": 0, "block": 1, "cut": 2,
            "overlap": 0.0})
        words_split = sorted(
            w for s in split for b in s["blocks"]
            for w in es.words(es.latex_to_plain(b["text"])))
        self.assertEqual(words_before, words_split,
                         "split must not add or drop a single word")
        self.assertEqual(len(split[0]["blocks"]), 4)
        # fixed blocks are never candidates
        floor = 0.0
        candidates = (partition._merge_candidates(sections, floor)
                      + partition._split_candidates(sections, 1.0))
        self.assertTrue(all(
            not sections[op["section"]]["blocks"][op["block"]].get("fixed")
            for op in candidates))

    def test_suggest_degrades_honestly_without_manifold(self):
        result = partition.suggest("\\section{A}\n\nshort\n",
                                   {"dispersion_manifold": None}, 3)
        self.assertEqual(result["status"], "unmeasured")


class SplitFidelityTests(unittest.TestCase):
    """A split is simulated on the ORIGINAL block text at the sentence
    boundary's own offset, line breaks kept (audit 2026-09-27, B2)."""

    BLOCK = ("Alpha one is measured here. Beta two follows there. % note kept\n"
             "Gamma three continues the argument. Delta four closes the block.")

    def test_split_keeps_the_prose_after_a_trailing_comment(self):
        left, right = partition._split_at(self.BLOCK, 2)
        self.assertEqual(right, "Delta four closes the block.")
        self.assertIn("\n", left, "the line break inside the left half survives")
        # re-joined with spaces the `% note kept` would comment out Gamma
        self.assertIn("Gamma", es.latex_to_plain(left))
        self.assertNotIn("Gamma", es.latex_to_plain(
            " ".join(es.sentences(self.BLOCK)[:2])))
        # the k-th boundary here is the k-th sentence end of es.sentences
        self.assertEqual(len(es.sentences(self.BLOCK)), 3)
        self.assertEqual(partition._split_at(self.BLOCK, 1)[0],
                         "Alpha one is measured here.")

    def test_apply_split_scores_and_locates_the_real_halves(self):
        sections = [{"label": "Methods", "blocks": [
            {"lines": (10, 11), "text": self.BLOCK}]}]
        split = partition._apply(sections, {"kind": "split", "section": 0,
                                            "block": 0, "cut": 2})
        left, right = split[0]["blocks"]
        self.assertEqual((left["lines"], right["lines"]), ((10, 11), (11, 11)))
        plain_words = sorted(w for b in (left, right)
                             for w in es.words(es.latex_to_plain(b["text"])))
        self.assertEqual(plain_words,
                         sorted(es.words(es.latex_to_plain(self.BLOCK))))
        description = partition._describe(
            {"kind": "split", "section": 0, "block": 0, "cut": 2, "overlap": 0.0},
            sections)
        self.assertIn("continues the argument", description)


class FixedBlockTests(unittest.TestCase):
    def test_any_heading_command_fixes_its_block(self):
        # only `\section` used to be fixed; a `\subsection` block was offered
        # as a merge partner (audit 2026-09-27, B3)
        text = ("\\section{Methods}\n\n" + LENSING_A + "\n\n"
                "\\subsection{Weighting}\n\n" + LENSING_B + "\n\n"
                "\\subsection*{Details}\n" + UNRELATED + "\n\n"
                "\\chapter{Next}\n\n" + LENSING_A + "\n")
        fixed = {block["text"].splitlines()[0]: block["fixed"]
                 for section in partition._parse(text)
                 for block in section["blocks"]}
        self.assertTrue(fixed["\\section{Methods}"])
        self.assertTrue(fixed["\\subsection{Weighting}"])
        self.assertTrue(fixed["\\subsection*{Details}"])
        self.assertTrue(fixed["\\chapter{Next}"])
        self.assertFalse(fixed[LENSING_A])
        candidates = partition._merge_candidates(partition._parse(text), 0.0)
        for op in candidates:
            section = partition._parse(text)[op["section"]]
            self.assertFalse(section["blocks"][op["block"]]["fixed"])
            self.assertFalse(section["blocks"][op["block"] + 1]["fixed"])

    def test_what_the_blanking_removes_stays_a_fixed_unscored_landmark(self):
        # The measured blocks no longer carry headings or floats (audit B22).
        # A heading sharing its line with a \label keeps its block fixed, and a
        # float between two paragraphs is a landmark: no merge across it, and
        # the scored blocks are exactly `shape_units`' own.
        text = ("\\section{Methods}\\label{sec:m}\n" + LENSING_A + "\n\n"
                "\\begin{figure}\n\\caption{A map.}\n\n\\end{figure}\n\n"
                + LENSING_B + "\n\n" + LENSING_B + "\n")
        section, = partition._parse(text)
        self.assertEqual([(b["lines"], b["fixed"], b.get("landmark", False))
                          for b in section["blocks"]],
                         [((1, 2), True, False), ((4, 7), True, True),
                          ((9, 9), False, False), ((11, 11), False, False)])
        self.assertEqual([op["block"] for op in partition._merge_candidates([section], 0.0)], [2])
        self.assertEqual([b["lines"] for b in section["blocks"] if not b.get("landmark")],
                         [(start, end) for start, end, _ in ds.shape_units(text)[0]["blocks"]])

    def test_landmarks_do_not_move_the_cohesion_floor(self):
        # The floor is the median overlap of adjacent paragraphs. Counted as
        # blocks, every heading and float added near-zero pairs that pulled it
        # down (the pre-merge review of audit B22).
        figure = "\\begin{figure}\n\\caption{A map of the field.}\n\\end{figure}\n\n"

        def document(between: str) -> str:
            return ("\\section{Introduction}\n\n" + LENSING_A + "\n\n" + LENSING_B + "\n\n"
                    "\\section{Methods}\n\n" + LENSING_A + "\n\n" + between + UNRELATED
                    + "\n\n" + LENSING_B + "\n\n"
                    "\\section{Results}\n\n" + LENSING_B + "\n\n" + LENSING_A + "\n")
        pairs = [(LENSING_A, LENSING_B), (LENSING_A, UNRELATED),
                 (UNRELATED, LENSING_B), (LENSING_B, LENSING_A)]
        expected = statistics.median(partition._overlap(a, b) for a, b in pairs)
        # six paragraphs reach the manifold (UNRELATED is under MIN_WORDS);
        # p inside the band, so the plan stops before its first step
        operating = fake_operating_point(p_by_n={6: 0.5}, distance_by_n={6: 1.0})
        with mock.patch.object(ds, "manifold_operating_point", operating):
            floors = [partition.suggest(document(between), {"dispersion_manifold": {}},
                                        1)["cohesion_floor"] for between in ("", figure)]
        self.assertEqual(floors, [expected, expected])


def fake_operating_point(p_by_n: dict, distance_by_n: dict):
    """A stand-in for `manifold_operating_point` keyed by paragraph count,
    with the length stratum switching at ten paragraphs."""
    def operating(_baseline, _row, n_paragraphs):
        return {"distance": distance_by_n[n_paragraphs],
                "p_value": p_by_n[n_paragraphs], "alpha": 0.05,
                "operating_point": "split-conformal, stratum manifold",
                "calibration_basis": f"stratum {0 if n_paragraphs < 10 else 1} manifold",
                "n_calibration": 40, "n_train": 60}
    return operating


class BandComparisonTests(unittest.TestCase):
    """Candidate states are compared by conformal p; distance only breaks a
    tie within one calibration basis (audit 2026-09-27, B10)."""

    def test_improves_orders_by_p_then_by_distance_within_one_basis(self):
        better_p = {"conformal_p": 0.3, "distance": 9.0, "calibration_basis": "stratum 1 manifold"}
        worse_p = {"conformal_p": 0.1, "distance": 1.0, "calibration_basis": "stratum 0 manifold"}
        self.assertTrue(partition._improves(better_p, worse_p))
        self.assertFalse(partition._improves(worse_p, better_p))
        same_basis_closer = {"conformal_p": 0.1, "distance": 0.5,
                             "calibration_basis": "stratum 0 manifold"}
        other_basis_closer = {"conformal_p": 0.1, "distance": 0.5,
                              "calibration_basis": "stratum 1 manifold"}
        self.assertTrue(partition._improves(same_basis_closer, worse_p))
        self.assertFalse(partition._improves(other_basis_closer, worse_p))

    def test_plan_prefers_the_higher_p_and_records_the_basis(self):
        text = uniform_document(FOUR_SENTENCES)
        # start: 9 paragraphs; a merge gives 8, a split gives 10. The merge
        # cuts the raw distance most, but the split moves the p up most and
        # crosses the stratum edge; the plan must take the split and say so.
        operating = fake_operating_point(
            p_by_n={9: 0.01, 8: 0.02, 10: 0.04},
            distance_by_n={9: 3.0, 8: 1.0, 10: 3.5})
        with mock.patch.object(ds, "manifold_operating_point", operating):
            result = partition.suggest(text, {"dispersion_manifold": {}}, 1)
        self.assertEqual(result["status"], "measured")
        self.assertEqual(result["start"]["n_paragraphs"], 9)
        self.assertEqual(result["start"]["calibration_basis"], "stratum 0 manifold")
        step = result["plan"][0]
        self.assertEqual(step["kind"], "split")
        self.assertEqual((step["conformal_p_before"], step["conformal_p_after"]),
                         (0.01, 0.04))
        self.assertEqual((step["calibration_basis_before"], step["calibration_basis_after"]),
                         ("stratum 0 manifold", "stratum 1 manifold"))
        self.assertEqual((step["distance_before"], step["distance_after"]), (3.0, 3.5))

    def test_state_uses_the_document_shape_filter(self):
        # a section below MIN_PARAGRAPHS_PER_SECTION or a document below
        # MIN_SECTIONS is not measurable here either (audit B11)
        text = uniform_document(FOUR_SENTENCES)
        operating = fake_operating_point(p_by_n={9: 0.5}, distance_by_n={9: 1.0})
        with mock.patch.object(ds, "manifold_operating_point", operating):
            start = partition._state_statistics(partition._parse(text), {})
            self.assertEqual(start["n_paragraphs"],
                             ds.document_shape(text)["n_paragraphs"])
            two_sections = "\n\n".join(text.split("\n\n\\section{Results}")[:1]) + "\n"
            self.assertIsNone(partition._state_statistics(
                partition._parse(two_sections), {}))
            thin = uniform_document(FOUR_SENTENCES, per_section=1)
            self.assertIsNone(partition._state_statistics(partition._parse(thin), {}))


class CliContractTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = partition.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_without_a_profile_the_tool_exits_2_with_a_message(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            draft.write_text(uniform_document(FOUR_SENTENCES), encoding="utf-8")
            empty = root / "profiles"
            empty.mkdir()
            code, _out, err = self.run_main([str(draft), "--profile-root", str(empty)])
            self.assertEqual(code, 2)
            self.assertIn("no calibrated dispersion manifold", err)
            code, _out, err = self.run_main([str(draft), "--profile-root", str(empty),
                                             "--field", "nope"])
            self.assertEqual(code, 2)
            self.assertIn("nope", err)
            code, _out, err = self.run_main([str(root / "missing.tex"),
                                             "--profile-root", str(empty)])
            self.assertEqual((code, "file not found" in err), (2, True))

    def test_a_manifold_without_conformal_calibration_names_the_rebuild(self):
        # It printed "document or manifold not measurable" and exited 0; the
        # document axis already said why, in words this tool now shares.
        names = ds.DISPERSION_FEATURE_NAMES
        rows = [{name: 1.0 + 0.1 * ((index * (k + 2)) % 7) for k, name in enumerate(names)}
                for index in range(ds.MIN_MANIFOLD_DOCUMENTS)]
        baseline = {"n_documents": 40, "dispersion_manifold": ds.fit_dispersion_manifold(rows)}
        text = uniform_document(FOUR_SENTENCES)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "f").mkdir()
            (root / "f" / ds.BASELINE_NAME).write_text(json.dumps(baseline), encoding="utf-8")
            draft = root / "draft.tex"
            draft.write_text(text, encoding="utf-8")
            code, out, _err = self.run_main([str(draft), "--profile-root", str(root),
                                             "--field", "f", "--json", str(root / "plan.json")])
            plan = json.loads((root / "plan.json").read_text(encoding="utf-8"))
            reason = ds.docstructure_axis_status(text, root / "f")["reason"]
        self.assertEqual(code, 0)
        self.assertIn("deai_docstructure --calibrate", reason)
        self.assertEqual(out, f"[deai_partition] {reason}\n")
        self.assertEqual((plan["status"], plan["reason"]), ("unmeasured", reason))


if __name__ == "__main__":
    unittest.main()
