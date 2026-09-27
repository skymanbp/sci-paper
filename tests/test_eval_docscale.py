from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401 -- because importing it is what puts tools/ on sys.path

import eval_docscale as ed


def _points(n: int, *, distance: float = 1.0, p_value: float = 0.5,
            alpha: float | None = 0.05,
            operating_point: str = "split-conformal", **extra) -> list[dict]:
    """`n` scored documents as `manifold_operating_point` returns them."""
    return [{"distance": distance, "p_value": p_value, "alpha": alpha,
             "operating_point": operating_point, "n_paragraphs": 30, **extra}
            for _ in range(n)]


class RowFloorTests(unittest.TestCase):
    """A row resting on too few documents must say so, not print a number.

    One document once printed a flag rate and an AUC of its own, and an
    empty human list reached `statistics.median` as a StatisticsError.
    """

    def test_an_empty_row_is_unmeasured_not_a_statistics_error(self) -> None:
        rows = ed.summarize({"human": [], "ai": []})
        self.assertEqual(rows["human"]["status"], "unmeasured")
        self.assertEqual(rows["ai"]["why"], "no document scored")
        self.assertNotIn("flag_rate", rows["ai"])

    def test_below_the_floor_is_unmeasured(self) -> None:
        rows = ed.summarize({"human": _points(ed.MIN_DOCUMENTS),
                             "ai": _points(ed.MIN_DOCUMENTS - 1)})
        self.assertEqual(rows["ai"]["status"], "unmeasured")
        self.assertIn(f"< {ed.MIN_DOCUMENTS}", rows["ai"]["why"])
        self.assertEqual(rows["human"]["status"], "measured")
        self.assertIn("unmeasured (n=19", ed.render(self._report(rows)))

    def test_a_thin_human_row_gives_no_auc(self) -> None:
        rows = ed.summarize({"human": _points(3),
                             "ai": _points(ed.MIN_DOCUMENTS, distance=2.0)})
        self.assertEqual(rows["ai"]["status"], "measured")
        self.assertIsNone(rows["ai"]["auc_vs_human"])

    def test_the_floor_is_shared_with_eval_findings(self) -> None:
        import eval_findings
        self.assertEqual(ed.MIN_DOCUMENTS, eval_findings.MIN_DOCUMENTS)

    @staticmethod
    def _report(rows: dict, alpha: float | None = 0.05) -> dict:
        return {"field": "wgl", "alpha": alpha, "min_documents": ed.MIN_DOCUMENTS,
                "baseline_documents": 3, "rows": rows}


class OperatingPointTests(unittest.TestCase):
    """A flag is decided by the operating point that scored the document.

    Reading a legacy in-sample percentile against the baseline's conformal
    alpha compared a within-sample percentile with a level it was never
    calibrated to.
    """

    def test_a_conformal_point_is_flagged_at_its_own_alpha(self) -> None:
        self.assertTrue(ed.flagged({"p_value": 0.04, "alpha": 0.05}))
        self.assertFalse(ed.flagged({"p_value": 0.06, "alpha": 0.05}))
        self.assertTrue(ed.flagged({"p_value": 0.10, "alpha": 0.10}))

    def test_a_legacy_percentile_point_keeps_its_own_decision(self) -> None:
        self.assertFalse(ed.flagged({"p_value": 0.03, "alpha": None, "flagged": False}))
        self.assertTrue(ed.flagged({"p_value": 0.50, "alpha": None, "flagged": True}))

    def test_each_row_names_its_operating_point(self) -> None:
        rows = ed.summarize({
            "human": _points(ed.MIN_DOCUMENTS),
            "ai": _points(ed.MIN_DOCUMENTS, distance=2.0, p_value=0.01,
                          operating_point="split-conformal, stratum manifold")})
        self.assertEqual(rows["ai"]["operating_point"], "split-conformal, stratum manifold")
        self.assertEqual(rows["ai"]["flag_rate"], 1.0)
        self.assertEqual(rows["human"]["flag_rate"], 0.0)
        self.assertEqual(rows["ai"]["auc_vs_human"], 1.0)
        rendered = ed.render(RowFloorTests._report(rows))
        self.assertIn("split-conformal, stratum manifold", rendered)
        self.assertIn("alpha=0.05", rendered)

    def test_a_legacy_baseline_reports_no_alpha(self) -> None:
        rows = ed.summarize({"human": _points(
            ed.MIN_DOCUMENTS, alpha=None, operating_point="in-sample percentile",
            flagged=False)})
        self.assertEqual(rows["human"]["operating_point"], "in-sample percentile")
        self.assertIn("alpha=-", ed.render(RowFloorTests._report(rows, alpha=None)))


class ResolutionTests(unittest.TestCase):
    def test_no_human_document_is_a_named_exit_not_a_statistics_error(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "profile" / "wgl").mkdir(parents=True)
            (root / "profile" / "wgl" / "docstructure_baseline.json").write_text(
                json.dumps({"n_documents": 3}), encoding="utf-8")
            (root / "corpus" / "wgl").mkdir(parents=True)
            with self.assertRaises(SystemExit) as caught:
                ed.build_report("wgl", root / "profile", root / "corpus")
        message = str(caught.exception)
        self.assertIn("no human document", message)
        self.assertIn("fetch_arxiv_abstracts", message)
        self.assertIn("--calibrate", message)

    def test_the_field_is_resolved_under_this_tools_own_name(self) -> None:
        # The wrapper borrowed from retrieve_exemplars signed the error with
        # that tool's name.
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(SystemExit) as caught:
                ed.main(["--field", "nope", "--profile-root", raw])
        self.assertIn("[eval_docscale]", str(caught.exception))
        self.assertNotIn("retrieve_exemplars", str(caught.exception))

    def test_tiers_are_discovered_from_docval_not_a_fixed_list(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for tier in ("ai", "ai_new_tier"):
                (root / "profile" / "wgl" / "docval" / tier).mkdir(parents=True)
                (root / "profile" / "wgl" / "docval" / tier / "x.tex").write_text(
                    "word " * 60, encoding="utf-8")
            (root / "corpus" / "wgl").mkdir(parents=True)
            # A baseline with no manifold scores nothing, so every tier is
            # present and empty rather than absent.
            scored = ed.collect({"n_documents": 3}, "wgl", root / "profile",
                                root / "corpus")
        self.assertEqual(sorted(scored), ["ai", "ai_new_tier", "human"])
        self.assertEqual(scored["ai_new_tier"], [])


if __name__ == "__main__":
    unittest.main()
