from __future__ import annotations

import json
import tempfile
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
