from __future__ import annotations

import contextlib
import io
import json
import random
import tempfile
import types
import unittest
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
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
        buckets = {bucket for bucket, _text, _start, _end in found}
        self.assertIn("method", buckets)
        # An appendix is `skip`; it must not supply a control passage.
        self.assertNotIn("skip", buckets)
        self.assertTrue(all(len(text.split()) >= 40 for _, text, _s, _e in found))
        # A control carries the line range a finding reports, so the two can be
        # compared by position rather than by a text prefix findings lack.
        self.assertEqual([(start, end) for _b, _t, start, end in found], [(3, 3)])

    def test_a_flagged_passage_is_excluded_from_controls_by_position(self):
        document = ("\\section{Methods}\n\n" + " ".join(["calibration"] * 60) + "\n\n"
                    + " ".join(["shear"] * 60) + "\n")
        passages = labels._passages(document)
        self.assertEqual([(s, e) for _b, _t, s, e in passages], [(3, 3), (5, 5)])
        # A finding carries its location; the control set drops the passage it
        # sits in, whether or not the sampling quota kept that finding.
        entries = [{"axis": "L0.register",
                    "finding": {"location": {"start_line": 3, "end_line": 3}}},
                   {"axis": "L2.collocation", "error": "unreadable"}]
        spans = labels.flagged_spans(entries)
        self.assertEqual(spans, [(3, 3)])
        kept = labels.unflagged_passages(passages, spans)
        self.assertEqual([(s, e) for _b, _t, s, e in kept], [(5, 5)])


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


class AxisCoverageTests(unittest.TestCase):
    """Every axis that emits findings must be sampleable, under the name the
    report uses for it.

    The discourse entry is why this is not a plain list: it returns BOTH of its
    axes from one call, because cohesion and hedging are measured over different
    spans of the document. A sampler that filed them under one name would make
    one of the two unlabelled forever.
    """

    def test_all_five_finding_emitting_axes_are_sampled(self) -> None:
        self.assertEqual(sorted(labels.AXES),
                         ["L0.register", "L2.cohesion", "L2.collocation",
                          "L2.hedging", "L2.salience_hierarchy"])

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
            # 40 true positives on 40 rows that carry no location, so each is
            # its own passage; 10 labelled misses -> 40/50, pooled.
            self.assertIn("0.800", out)
            self.assertIn("pooled", out)

    def test_a_passage_several_axes_flag_is_one_true_positive(self) -> None:
        # The control side counts passages a labeller says were missed, so the
        # numerator counts passages too: two axes right about the same twenty
        # passages are twenty hits, not forty, and recall is 20/30, not 40/50.
        rows = []
        for axis in ("L0.register", "L2.salience_hierarchy"):
            for i in range(labels.MIN_PER_CELL):
                rows.append({"id": f"{axis}-{i}", "population": "p", "axis": axis,
                             "source": "x.tex", "flagged": True, "label": True,
                             "evidence": {"location": {"start_line": 3 + 2 * i,
                                                       "end_line": 3 + 2 * i}}})
        for i in range(labels.MIN_PER_CELL):
            rows.append({"id": f"ctl-{i}", "population": "p", "axis": "control",
                         "flagged": False, "label": i < 10, "evidence": {}})
        with tempfile.TemporaryDirectory() as name:
            sheet = Path(name) / "s.jsonl"
            sheet.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                             encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                labels.cmd_score(types.SimpleNamespace(sheet=sheet, recheck=None))
        out = buffer.getvalue()
        self.assertIn("0.667", out)
        self.assertNotIn("0.800", out)
        self.assertIn("true positives counted once per passage: 40 rows on 20 passages", out)
        self.assertIn("from 1 documents", out)

    def test_a_missing_recheck_sheet_is_named_not_read_as_unsupplied(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            sheet = Path(name) / "s.jsonl"
            self._sheet(sheet)
            with self.assertRaises(SystemExit) as caught:
                labels.cmd_score(types.SimpleNamespace(
                    sheet=sheet, recheck=Path(name) / "missing.jsonl"))
        self.assertIn("missing.jsonl", str(caught.exception))


class ParserTests(unittest.TestCase):
    """The field options belong to the subcommands, and only to them.

    On the root parser as well, argparse let each subparser's defaults
    overwrite what the root had parsed: `--field wgl --corpus-root X sample`
    ran with field=None and the default corpus root, and nothing said so.
    """

    def test_field_after_the_subcommand_reaches_the_command(self) -> None:
        seen: dict = {}
        original = labels.cmd_sample
        labels.cmd_sample = lambda args: seen.update(vars(args)) or 0
        try:
            labels.main(["sample", "--field", "wgl", "--corpus-root", "corpus",
                         "--profile-root", "profile"])
        finally:
            labels.cmd_sample = original
        self.assertEqual(seen["field"], "wgl")
        self.assertEqual(seen["corpus_root"], Path("corpus"))
        self.assertEqual(seen["profile_root"], Path("profile"))

    def test_field_before_the_subcommand_is_an_error_not_a_silent_default(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            labels.main(["--field", "wgl", "--corpus-root", "corpus", "sample"])
        self.assertEqual(caught.exception.code, 2)

    def test_n_is_documented_as_the_per_cell_quota(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer), self.assertRaises(SystemExit) as caught:
            labels.main(["sample", "--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("per (population, axis) cell", buffer.getvalue())
        self.assertIn(f"default {labels.MIN_PER_CELL}", buffer.getvalue())


class SamplingTests(unittest.TestCase):
    """A cell is a random draw spread over documents, not one paper's worth.

    Taking each document's findings in emission order until the quota filled
    meant a 20-row cell usually came from one or two long papers, so the
    precision it supported was per paper, not per finding; and an emitter that
    failed on a document was read as "the corpus holds no more".
    """

    @staticmethod
    def _document(n_paragraphs: int, word: str) -> str:
        # Paragraph k sits alone on line 3 + 2k, so a finding can point at it.
        return ("\\section{Methods}\n\n"
                + "\n\n".join(" ".join([f"{word}{k}"] * 60)
                              for k in range(n_paragraphs))
                + "\n")

    @contextlib.contextmanager
    def _harness(self, findings_per_document: dict[str, int], failing=()):
        """A population of loose papers, a one-field profile, one fake emitter."""
        calls: list[str] = []

        def emit(text, field_dir, path):
            calls.append(path.name)
            if path.name in failing:
                raise RuntimeError("boom")
            return [{"rule": "fake", "location": {"start_line": 3 + 2 * k,
                                                  "end_line": 3 + 2 * k}}
                    for k in range(findings_per_document[path.name])]

        original = labels.EMITTERS, labels.AXES
        labels.EMITTERS = ((emit, ("L0.register",), None),)
        labels.AXES = ("L0.register",)
        try:
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                (root / "profile" / "wgl").mkdir(parents=True)
                (root / "corpus").mkdir()
                (root / "papers").mkdir()
                for name, count in findings_per_document.items():
                    # One paragraph more than the findings: a control candidate.
                    (root / "papers" / name).write_text(
                        self._document(count + 1, name[:3]), encoding="utf-8")
                yield root, calls
        finally:
            labels.EMITTERS, labels.AXES = original

    @staticmethod
    def _args(root: Path, n: int = labels.MIN_PER_CELL) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            field="wgl", profile_root=root / "profile", corpus_root=root / "corpus",
            population=[f"papers={root / 'papers'}"], drafts=None,
            heldout_dir="fulltext-heldout", n=n, seed=1, out=root / "labels.jsonl")

    @staticmethod
    def _rows(root: Path) -> list[dict]:
        return [json.loads(line) for line in
                (root / "labels.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]

    def test_a_cell_is_spread_over_documents_not_filled_from_one(self) -> None:
        # d00 alone could fill the cell; the draw caps any one document at a
        # fifth of the quota and reaches the rest.
        counts = {"d00.tex": 30, **{f"d{i:02d}.tex": 3 for i in range(1, 10)}}
        with self._harness(counts) as (root, calls):
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                labels.cmd_sample(self._args(root))
            rows = self._rows(root)
        flagged = [r for r in rows if r["flagged"]]
        self.assertEqual(len(flagged), labels.MIN_PER_CELL)
        per_document = Counter(r["source"] for r in flagged)
        self.assertLessEqual(max(per_document.values()), 4)
        self.assertGreaterEqual(len(per_document), labels.MIN_SOURCES_PER_CELL)
        # Ten documents hold one unflagged paragraph each: ten controls, spread.
        controls = [r for r in rows if not r["flagged"]]
        self.assertEqual(len(controls), 10)
        self.assertEqual(len({r["source"] for r in controls}), 10)
        self.assertRegex(out.getvalue(), r"L0\.register\s+20 rows from \d+ documents")
        self.assertRegex(out.getvalue(), r"control\s+10 rows from 10 documents")
        # The emitters ran once per document, for the flags and the controls alike.
        self.assertEqual(sorted(calls), sorted(counts))

    def test_an_emitter_failure_is_reported_as_one_not_as_an_exhausted_corpus(self):
        counts = {f"d{i:02d}.tex": 2 for i in range(4)}
        with self._harness(counts, failing={"d02.tex", "d03.tex"}) as (root, _calls):
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                labels.cmd_sample(self._args(root))
        self.assertIn("4 of 20 needed (2 of 4 documents hold no more; "
                      "the emitter failed on the other 2)", err.getvalue())
        self.assertIn("emitter error -- papers x L0.register: emitter failed on "
                      "2 of 4 documents; first: d02.tex: boom", err.getvalue())

    def test_n_is_the_per_cell_quota_and_a_value_under_the_floor_warns(self):
        counts = {f"d{i:02d}.tex": 6 for i in range(6)}
        with self._harness(counts) as (root, _calls):
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                labels.cmd_sample(self._args(root, n=25))
            self.assertEqual(sum(1 for r in self._rows(root) if r["flagged"]), 25)
            self.assertNotIn("below the", err.getvalue())
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                labels.cmd_sample(self._args(root, n=5))
            self.assertEqual(sum(1 for r in self._rows(root) if r["flagged"]), 5)
        self.assertIn(f"below the {labels.MIN_PER_CELL}-label floor", err.getvalue())

    def test_the_spread_fills_the_quota_when_the_cap_alone_cannot(self) -> None:
        rng = random.Random(0)
        items = [("a", i) for i in range(10)] + [("b", i) for i in range(10)]
        capped = labels._spread_sample(rng, items, 4, 2)
        self.assertEqual(Counter(name for name, _ in capped), {"a": 2, "b": 2})
        # Two documents at two each is four; the quota of eight is still met,
        # from what remains, and nothing is drawn twice.
        filled = labels._spread_sample(rng, items, 8, 2)
        self.assertEqual(len(filled), 8)
        self.assertEqual(len(set(filled)), 8)


if __name__ == "__main__":
    unittest.main()
