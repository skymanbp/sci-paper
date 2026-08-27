from __future__ import annotations

import json
import tempfile
import types
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401 -- because importing it is what puts tools/ on sys.path

import label_findings as labels


class ThinStratumTests(unittest.TestCase):
    """A rate resting on too few labels must say so, not print a number.

    This is why the tool exists at all: the axes it scores are honest about
    missing calibration, so the instrument that judges them cannot be the place
    where a 2-of-3 sample turns into "precision 0.667".
    """

    def test_a_thin_cell_is_unmeasured_not_a_rate(self):
        self.assertIn("unmeasured", labels._rate(2, 3))
        self.assertIn(f"< {labels.MIN_PER_CELL}", labels._rate(2, 3))

    def test_zero_of_zero_never_reads_as_a_rate(self):
        # The failure being excluded: 0/0 rendering as 0.000, which reads as
        # "the axis got everything right" rather than "nothing was measured".
        self.assertIn("unmeasured", labels._rate(0, 0))

    def test_a_sufficient_cell_reports_the_rate(self):
        rendered = labels._rate(15, labels.MIN_PER_CELL)
        self.assertNotIn("unmeasured", rendered)
        self.assertIn(f"n={labels.MIN_PER_CELL}", rendered)


class PassageSelectionTests(unittest.TestCase):
    def test_only_substantial_classified_passages_become_controls(self):
        document = (
            "\\section{Methods}\n\n"
            + " ".join(["calibration"] * 60) + "\n\n"
            + "too short\n\n"
            "\\section{Appendix A}\n\n"
            + " ".join(["appendix"] * 60) + "\n"
        )
        found = labels._passages(document)
        buckets = {bucket for bucket, _ in found}
        self.assertIn("method", buckets)
        # An appendix is `skip`; it must not supply a control passage.
        self.assertNotIn("skip", buckets)
        self.assertTrue(all(len(text.split()) >= 40 for _, text in found))


class RelabelContractTests(unittest.TestCase):
    """The blind subset must actually be blind, or the agreement number lies."""

    def _sheet(self, directory: Path) -> Path:
        rows = [{"schema": labels.SCHEMA, "id": f"published-{index:04d}",
                 "population": "published", "axis": "L0.register",
                 "source": "x.tex", "flagged": True,
                 "evidence": {"text": f"passage {index}"},
                 "label": bool(index % 2), "note": "first pass"}
                for index in range(30)]
        path = directory / "labels.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n",
                        encoding="utf-8")
        return path

    def test_relabel_strips_the_prior_answer_and_keeps_the_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = type("Args", (), {})()
            args.sheet = self._sheet(directory)
            args.out = directory / "recheck.jsonl"
            args.frac, args.seed = 0.4, 1
            labels.cmd_relabel(args)

            served = [json.loads(line) for line in
                      args.out.read_text(encoding="utf-8").splitlines()
                      if line.strip()]
            self.assertEqual(len(served), 12)
            for row in served:
                self.assertIsNone(row["label"], "prior answer leaked into recheck")
                self.assertEqual(row["note"], "")
                self.assertIn("_relabel_of", row)
            self.assertEqual(len({row["_relabel_of"] for row in served}),
                             len(served))


if __name__ == "__main__":
    unittest.main()


class AxisCoverageTests(unittest.TestCase):
    """Every axis that emits findings must be sampleable, under the name the
    report uses for it.

    The discourse entry is why this is not a plain list: it returns BOTH of its
    axes from one call, because cohesion and hedging are measured over different
    spans of the document. A sampler that filed them under one name would make
    one of the two unlabelled forever.
    """

    def test_all_four_finding_emitting_axes_are_sampled(self) -> None:
        self.assertEqual(sorted(labels.AXES),
                         ["L0.register", "L2.cohesion", "L2.hedging",
                          "L2.salience_hierarchy"])

    def test_the_multi_axis_emitter_tags_each_feature_separately(self) -> None:
        _, axes, axis_of = next(e for e in labels.EMITTERS if len(e[1]) > 1)
        self.assertEqual(sorted(axes), ["L2.cohesion", "L2.hedging"])
        self.assertEqual(axis_of({"observed": {"feature": "cohesion"}}),
                         "L2.cohesion")
        self.assertEqual(axis_of({"observed": {"feature": "hedging"}}),
                         "L2.hedging")

    def test_the_tags_match_the_names_the_detector_reports(self) -> None:
        # The join that matters: if the axis name is ever renamed in one place,
        # the sheet would file findings under a name no report ever prints.
        import deai_discourse
        reported = {s["axis"] for s in deai_discourse.discourse_axis_status(None)}
        self.assertTrue(reported <= set(labels.AXES),
                        f"detector reports {reported - set(labels.AXES)}")

    def test_single_axis_emitters_need_no_discriminator(self) -> None:
        for _, axes, axis_of in labels.EMITTERS:
            if len(axes) == 1:
                self.assertIsNone(axis_of)


class PopulationTests(unittest.TestCase):
    """Which prose to label is a research decision, so it is named on the
    command line rather than fixed in the file."""

    def test_a_population_without_a_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            (tmp / "wgl").mkdir()      # the field is resolved before the parse
            with self.assertRaises(SystemExit) as caught:
                labels.main(["sample", "--field", "wgl",
                             "--profile-root", str(tmp), "--corpus-root", str(tmp),
                             "--population", "mentor"])
            self.assertIn("NAME=DIR", str(caught.exception))

    def test_a_missing_population_directory_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(SystemExit) as caught:
                labels._load_population(Path(name) / "absent")
            self.assertIn("no such population directory", str(caught.exception))

    def test_loose_files_count_one_paper_each(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / "a.tex").write_text("alpha", encoding="utf-8")
            (root / "b.tex").write_text("beta", encoding="utf-8")
            self.assertEqual(len(labels._load_population(root)), 2)

    def test_a_directory_of_bundles_counts_one_paper_each(self) -> None:
        # The shape every style-corpus/<field>/fulltext-* pull has: a manuscript
        # whose main.tex \input's its sections is one paper, not fifteen.
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for paper in ("p1", "p2"):
                (root / paper).mkdir()
                (root / paper / "main.tex").write_text(
                    r"\documentclass{article}\begin{document}x\end{document}",
                    encoding="utf-8")
                (root / paper / "macros.tex").write_text(r"\def\x{1}",
                                                         encoding="utf-8")
            self.assertEqual(len(labels._load_population(root)), 2)


class PooledRecallTests(unittest.TestCase):
    """A control row records that a passage was missed, but not by WHICH axis.

    Dividing every axis by the same miss count -- what this did while it carried
    two axes -- charges each axis with every other axis's misses, and understates
    all of them by more the more axes there are.
    """

    def _sheet(self, path: Path) -> None:
        rows = []
        for axis in ("L0.register", "L2.salience_hierarchy"):
            for i in range(labels.MIN_PER_CELL):
                rows.append({"id": f"{axis}-{i}", "population": "p", "axis": axis,
                             "flagged": True, "label": True, "evidence": {}})
        for i in range(labels.MIN_PER_CELL):
            rows.append({"id": f"ctl-{i}", "population": "p", "axis": "control",
                         "flagged": False, "label": i < 10, "evidence": {}})
        path.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                        encoding="utf-8")

    def test_recall_is_reported_once_per_population_not_once_per_axis(self) -> None:
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as name:
            sheet = Path(name) / "s.jsonl"
            self._sheet(sheet)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                labels.cmd_score(types.SimpleNamespace(sheet=sheet, recheck=None))
            out = buffer.getvalue()
            self.assertEqual(out.count("recall"), 1, out)
            # 40 true positives, 10 labelled misses -> 40/50, pooled.
            self.assertIn("0.800", out)
            self.assertIn("pooled", out)
