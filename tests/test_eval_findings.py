from __future__ import annotations

import unittest

from _toolpath import TOOLS  # noqa: F401 -- because importing it is what puts tools/ on sys.path

import eval_findings as ef
import extract_style
import deai_salience


class HeldOutIsActuallyHeldOutTest(unittest.TestCase):
    """The evaluation set must not be readable by the calibration builder.

    This is the contract the whole measurement rests on. `extract_style`
    collects from a fixed tuple of source directories; if the held-out
    directory ever joins that tuple, the next profile rebuild absorbs the
    evaluation papers and every rate this tool reports silently becomes
    in-sample -- with no error, no warning, and no visible change in the table.
    """

    def test_the_heldout_directory_is_not_a_calibration_source(self) -> None:
        calibration_sources = (*extract_style.TIER_WEIGHTS,
                               extract_style.REFERENCE_DIR)
        self.assertNotIn(ef.HELDOUT_DIR, calibration_sources)

    def test_the_insample_directory_IS_a_calibration_source(self) -> None:
        # The control population is only a leakage control if it really leaks.
        self.assertIn(ef.INSAMPLE_DIR,
                      (*extract_style.TIER_WEIGHTS, extract_style.REFERENCE_DIR))

    def test_the_two_populations_are_different_directories(self) -> None:
        self.assertNotEqual(ef.HELDOUT_DIR, ef.INSAMPLE_DIR)


class ThinPopulationTest(unittest.TestCase):
    """A rate resting on too few documents must say so, not print a number."""

    @staticmethod
    def _rows(n: int, findings: float) -> list[dict[str, float]]:
        return [{"n_words": 1000.0, "n_salience_units": 10.0,
                 "L0.register": findings,
                 "L2.salience_hierarchy": findings, "salience_strong": 0.0}
                for _ in range(n)]

    def test_below_the_floor_is_unmeasured(self) -> None:
        summary = ef.summarize(self._rows(ef.MIN_DOCUMENTS - 1, 0.0),
                               "L0.register")
        self.assertEqual(summary["status"], "unmeasured")
        self.assertNotIn("flag_rate", summary)

    def test_an_empty_population_never_reads_as_a_clean_rate(self) -> None:
        # The failure being excluded: 0 documents rendering as flag_rate 0.000,
        # which reads as "the axis never misfires" rather than "nothing ran".
        self.assertEqual(ef.summarize([], "L0.register")["status"], "unmeasured")

    def test_at_the_floor_the_rate_is_reported(self) -> None:
        summary = ef.summarize(self._rows(ef.MIN_DOCUMENTS, 2.0), "L0.register")
        self.assertEqual(summary["status"], "measured")
        self.assertEqual(summary["flag_rate"], 1.0)
        self.assertEqual(summary["per_1k_words"], 2.0)

    def test_density_is_per_thousand_words_not_per_document(self) -> None:
        rows = [{"n_words": 2000.0, "L0.register": 4.0,
                 "L2.salience_hierarchy": 0.0, "salience_strong": 0.0}]
        self.assertEqual(ef._density(rows, "L0.register"), [2.0])

    def test_zero_length_documents_do_not_divide_by_zero(self) -> None:
        rows = [{"n_words": 0.0, "L0.register": 1.0,
                 "L2.salience_hierarchy": 0.0, "salience_strong": 0.0}]
        self.assertEqual(ef._density(rows, "L0.register"), [])


class DiscriminationGuardTest(unittest.TestCase):
    def test_no_auc_without_both_populations(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        report = ef.build_report("wgl", {"published-heldout": rows})
        self.assertEqual(report["discrimination"]["status"], "unmeasured")

    def test_auc_appears_once_both_sides_reach_the_floor(self) -> None:
        heldout = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 0.0)
        machine = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 5.0)
        report = ef.build_report("wgl", {"published-heldout": heldout,
                                         "machine:ai": machine})
        auc = report["discrimination"]["L0.register"]["auc_machine_over_heldout"]
        self.assertEqual(auc, 1.0)   # machine flags more, so it outranks always

    def test_machine_tiers_are_pooled_into_one_row(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        report = ef.build_report("wgl", {"machine:ai": rows,
                                         "machine:ai_deai": rows})
        self.assertEqual(
            report["populations"]["machine:ALL"]["n_documents"],
            2 * ef.MIN_DOCUMENTS)


class ReadingOfEachAxisTest(unittest.TestCase):
    """The salience row must never be presented as a false-positive count.

    Its gate is a percentile, so the design point is a non-zero rate. A report
    that called it a false-positive rate would turn the gate's own definition
    into a defect and invite "fixing" a correctly calibrated axis.
    """

    def test_the_rendered_table_states_the_salience_gate(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        rendered = ef.render(ef.build_report("wgl", {"published-heldout": rows}))
        self.assertIn(str(deai_salience.ADVISORY_PERCENTILE), rendered)
        self.assertIn("by design", rendered)

    def test_the_rendered_table_names_the_register_row_a_false_positive_rate(self):
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        rendered = ef.render(ef.build_report("wgl", {"published-heldout": rows}))
        self.assertIn("false-positive rate", rendered)

    def test_unmeasured_cells_render_without_a_number(self) -> None:
        rendered = ef._cell({"status": "unmeasured", "n": 3})
        self.assertIn("unmeasured", rendered)
        self.assertNotIn("0.000", rendered)


class SalienceGateTransferTest(unittest.TestCase):
    """The gate is defined per passage, so the transfer test must be too.

    A per-1,000-words density cannot be compared with a percentile: the gate
    never promised a rate per word. Reporting only the density would leave the
    axis's central calibration claim untestable, and its ~0.97 document flag
    rate looking like a defect when it is the design point.
    """

    def test_the_expectation_is_the_independent_gate_union(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        gate = ef.salience_gate_transfer(rows)
        expected = 1 - deai_salience.ADVISORY_PERCENTILE ** len(deai_salience.FEATURES)
        self.assertAlmostEqual(gate["independent_gate_expectation"],
                               round(expected, 4))
        self.assertEqual(gate["n_features"], len(deai_salience.FEATURES))

    def test_the_measured_rate_is_per_passage_not_per_word(self) -> None:
        # 20 documents x 1 finding over 20 x 10 passages = 0.10 per passage,
        # which is NOT the 1.0 per 1,000 words the same rows imply.
        gate = ef.salience_gate_transfer(ThinPopulationTest._rows(20, 1.0))
        self.assertEqual(gate["measured_per_passage"], 0.1)
        self.assertEqual(gate["n_passages"], 200)

    def test_no_passages_is_unmeasured_not_a_zero_rate(self) -> None:
        rows = [{"n_words": 1000.0, "n_salience_units": 0.0, "L0.register": 0.0,
                 "L2.salience_hierarchy": 0.0, "salience_strong": 0.0}
                for _ in range(ef.MIN_DOCUMENTS)]
        self.assertEqual(ef.salience_gate_transfer(rows)["status"], "unmeasured")

    def test_the_rendered_table_carries_both_numbers(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        rendered = ef.render(ef.build_report("wgl", {"published-heldout": rows}))
        self.assertIn("gate transfer", rendered)
        self.assertIn("independent gates", rendered)

    def test_the_percentile_sentence_prints_the_percentile(self) -> None:
        # A local name collision printed the whole gate-transfer dict into the
        # sentence that is supposed to name the 0.9 percentile.
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        rendered = ef.render(ef.build_report("wgl", {"published-heldout": rows}))
        gate = deai_salience.ADVISORY_PERCENTILE
        self.assertIn(f"its gate is the {gate} percentile", rendered)
        self.assertNotIn("'status':", rendered)


class LeakageIsMeasuredPairedTest(unittest.TestCase):
    """The cross-population contrast is confounded, so it must not be offered.

    The shipped breadth pull is 2020-2021 and a held-out sweep reaches deeper in
    the newest-first result order, so it lands on earlier papers. Reading the
    gap between the two published rows as in-sample optimism would attribute
    years of vocabulary drift to calibration leakage.
    """

    def test_the_report_denies_era_comparability(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        report = ef.build_report("wgl", {"published-heldout": rows})
        self.assertFalse(report["populations_are_era_comparable"])

    def test_the_rendered_table_warns_against_the_cross_population_read(self):
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        rendered = ef.render(ef.build_report("wgl", {"published-heldout": rows}))
        self.assertIn("not", rendered)
        self.assertIn("era-comparable", rendered)

    def test_no_findings_means_unmeasured_not_zero_leakage(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        report = ef.build_report("wgl", {"published-heldout": rows}, (0, 0))
        self.assertEqual(report["register_leakage_paired"]["status"],
                         "unmeasured")

    def test_a_measured_tally_reports_the_suppressed_fraction(self) -> None:
        rows = ThinPopulationTest._rows(ef.MIN_DOCUMENTS, 1.0)
        report = ef.build_report("wgl", {"published-heldout": rows}, (100, 27))
        leak = report["register_leakage_paired"]
        self.assertEqual(leak["status"], "measured")
        self.assertEqual(leak["suppressed_by_own_membership"], 0.73)
        self.assertIn("0.730", ef.render(report))

    def test_leakage_without_a_lexicon_is_zero_not_a_crash(self) -> None:
        from pathlib import Path
        self.assertEqual(
            ef.leakage_paired("word " * 60, Path("no-such-profile-dir"), "x"),
            (0, 0))


if __name__ == "__main__":
    unittest.main()
