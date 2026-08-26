from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import deai_features as features
import deai_voice as voice
import train_voice_model as training


class ModuleSplitContractTests(unittest.TestCase):
    """`train_voice_model` must re-export everything the split modules define.

    The dataset and audit layers were split out on 2026-08-26 (1,174 lines
    against a 750-line budget). The re-export list is hand-written, so it can
    silently fall behind the modules it mirrors -- the drift the equivalent
    `extract_style` and `deai_docstructure` tests have caught four times
    between them. Every test above reaches these names as `training.<name>`.
    """

    def _public_names(self, module, module_name):
        # Imported module aliases (`vd`, `df`) are not part of the surface a
        # caller reaches through `training.<name>`; modules carry no
        # `__module__`, so they would otherwise pass the default below.
        import types

        return {
            name for name, value in vars(module).items()
            if not name.startswith("__")
            and not isinstance(value, types.ModuleType)
            and getattr(value, "__module__", module_name) == module_name
        }

    def test_dataset_names_are_re_exported(self):
        import voice_dataset

        missing = sorted(n for n in self._public_names(voice_dataset, "voice_dataset")
                         if not hasattr(training, n))
        self.assertEqual(missing, [],
                         f"train_voice_model does not re-export: {missing}")

    def test_audit_names_are_re_exported(self):
        import voice_audit

        missing = sorted(n for n in self._public_names(voice_audit, "voice_audit")
                         if not hasattr(training, n))
        self.assertEqual(missing, [],
                         f"train_voice_model does not re-export: {missing}")

    def test_the_split_modules_stay_within_the_line_budget(self):
        # The split exists to get under the budget; a test keeps it there.
        for name in ("train_voice_model.py", "voice_dataset.py", "voice_audit.py"):
            lines = len((TOOLS / name).read_text(encoding="utf-8").splitlines())
            self.assertLessEqual(lines, 750, f"{name} is {lines} lines")

    def test_the_dependency_direction_is_one_way(self):
        # audit -> dataset -> nothing. A back-edge would make the split circular
        # and reintroduce the coupling it removed.
        source = (TOOLS / "voice_dataset.py").read_text(encoding="utf-8")
        self.assertNotIn("voice_audit", source)

    def test_no_module_level_name_is_unbound(self):
        """Every name a tool module loads must be defined or imported in it.

        Splitting a module moves function bodies but re-writes the import block
        by hand, so a moved function can reference a name that stayed behind.
        That is not a hypothetical: the 2026-08-26 split left `time`,
        `CHECKPOINT_EVERY`, `df` and the two HARDSET category sets unbound, and
        the suite went green anyway because no test reached those lines --
        `build_features` failed only when a real retrain ran. This walks the AST
        instead of waiting for a call site.
        """
        import ast
        import builtins

        for name in sorted(p.name for p in TOOLS.glob("*.py")):
            tree = ast.parse((TOOLS / name).read_text(encoding="utf-8"))
            bound = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        bound.add((alias.asname or alias.name).split(".")[0])
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                       ast.ClassDef)):
                    bound.add(node.name)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    bound.add(node.id)
                elif isinstance(node, ast.arg):
                    bound.add(node.arg)
                elif isinstance(node, ast.ExceptHandler) and node.name:
                    bound.add(node.name)
            used = {n.id for n in ast.walk(tree)
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            self.assertEqual(sorted(used - bound), [], f"{name} has unbound names")


class VoiceAuditHelperTests(unittest.TestCase):
    def records(self) -> list[dict]:
        records = []
        for index in range(3):
            records.append({
                "text": (
                    "Weak lensing convergence shear aperture mass calibration "
                    f"field measurement source {index}."
                ),
                "label": 1,
                "source": f"style-corpus/paper-{index}.pdf",
                "section": "method",
            })
        for index in range(3):
            records.append({
                "text": (
                    "Stellar spectra abundance temperature atmosphere observation "
                    f"public reference {index}."
                ),
                "label": 1,
                "source": f"raid-human:record-{index}",
                "section": "abstract",
            })
        return records

    def test_cache_fingerprint_covers_all_record_and_model_inputs(self):
        records = self.records()
        with tempfile.TemporaryDirectory() as temporary:
            field_dir = Path(temporary)
            baseline = training.feature_cache_fingerprint(
                field_dir, records, "gpt2-large")
            for key, replacement in (
                ("text", "Changed scientific prose."),
                ("label", 0),
                ("source", "style-corpus/changed.pdf"),
                ("section", "discussion"),
            ):
                changed = copy.deepcopy(records)
                changed[0][key] = replacement
                self.assertNotEqual(
                    baseline,
                    training.feature_cache_fingerprint(
                        field_dir, changed, "gpt2-large"),
                    key,
                )
            self.assertNotEqual(
                baseline,
                training.feature_cache_fingerprint(field_dir, records, "gpt2"),
            )

    def test_cache_fingerprint_covers_centroid_bytes(self):
        records = self.records()
        with tempfile.TemporaryDirectory() as temporary:
            field_dir = Path(temporary)
            before = training.feature_cache_fingerprint(
                field_dir, records, "gpt2-large")
            centroid = field_dir / f"exemplar_embeddings_{features.EMBED_MODEL}.npy"
            centroid.write_bytes(b"first-centroid")
            first = training.feature_cache_fingerprint(
                field_dir, records, "gpt2-large")
            centroid.write_bytes(b"second-centroid")
            second = training.feature_cache_fingerprint(
                field_dir, records, "gpt2-large")
            self.assertNotEqual(before, first)
            self.assertNotEqual(first, second)

    def test_field_lexicon_uses_training_reference_sources_only(self):
        records = self.records()
        terms, metadata = training.build_field_lexicon(
            records, range(len(records)))
        self.assertIn("lensing", terms)
        self.assertNotIn("temperature", terms)
        self.assertEqual(metadata["n_field_sources"], 3)
        self.assertEqual(metadata["n_background_sources"], 3)

    def test_audit_covariates_do_not_modify_feature_schema(self):
        names = list(features.FEATURE_NAMES)
        self.assertGreater(features.math_marker_density(
            "The estimator is $x+y$ and the result is [MATH]."), 0.0)
        self.assertEqual(features.math_marker_density("signal [MATH]"), 100.0)
        self.assertEqual(features.math_marker_density(
            "The estimator follows from the measured covariance."), 0.0)
        self.assertGreater(features.lexicon_density(
            "Lensing shear constrains the lensing field.", {"lensing", "shear"}),
            0.0,
        )
        self.assertEqual(features.FEATURE_NAMES, names)
        self.assertNotIn("math_marker_density", features.FEATURE_NAMES)
        self.assertNotIn("field_term_density", features.FEATURE_NAMES)

    def test_binary_metrics_handle_ties_and_single_class_controls(self):
        metrics = training.binary_metrics([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
        self.assertEqual(metrics["auc"], 1.0)
        self.assertEqual(metrics["balanced_accuracy"], 1.0)
        # Tied scores must use midrank averaging, not first-seen order.
        self.assertEqual(
            training.binary_metrics([0, 1], [0.5, 0.5])["auc"], 0.5)
        self.assertEqual(
            training.binary_metrics([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.9])["auc"],
            0.75)
        controls = training.binary_metrics([0, 0], [0.1, 0.9])
        self.assertIsNone(controls["auc"])
        self.assertEqual(controls["negative_false_positive_rate"], 0.5)
        # No positive examples => F1 is UNDEFINED (None), never a real zero;
        # aggregation must skip it exactly like recall/bacc/auc.
        self.assertIsNone(controls["f1_positive"])
        self.assertIsNone(controls["positive_recall"])
        measured_zero = training.binary_metrics([1, 1], [0.1, 0.2])
        self.assertEqual(measured_zero["f1_positive"], 0.0)

    def test_hardset_provenance_categories_partition_ai_and_human(self):
        ai = training.HARDSET_AI_CATEGORIES
        human = training.HARDSET_HUMAN_CATEGORIES
        self.assertFalse(ai & human)
        self.assertIn("clear-AI-claude", ai)
        self.assertIn("clear-AI-raid", ai)
        self.assertIn("your-draft", human)
        self.assertIn("human-paper", human)

    def test_bootstrap_auc_ci_reproducible_and_brackets_point(self):
        try:
            import numpy  # noqa: F401  _bootstrap_auc_ci lazy-imports it
        except ImportError:  # CI runs without optional dependencies
            self.skipTest("numpy is unavailable")
        y = [0, 0, 0, 1, 1, 1]
        scores = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
        first = training._bootstrap_auc_ci(y, scores, n_boot=500, seed=7)
        second = training._bootstrap_auc_ci(y, scores, n_boot=500, seed=7)
        self.assertEqual(first, second)                       # seeded => reproducible
        self.assertEqual(first["auc"], 1.0)                   # perfect separation
        self.assertLessEqual(first["ci95_low"], first["auc"])
        self.assertLessEqual(first["auc"], first["ci95_high"] + 1e-9)
        self.assertIsNone(training._bootstrap_auc_ci([1, 1], [0.2, 0.9]))  # single class

    def test_undefined_f1_is_excluded_from_aggregation(self):
        report_with_positives = {"overall": training.binary_metrics(
            [0, 1], [0.2, 0.9])}
        report_without_positives = {"overall": training.binary_metrics(
            [0, 0], [0.2, 0.9])}
        aggregated = training.aggregate_audits(
            [report_with_positives, report_without_positives])
        self.assertEqual(aggregated["overall"]["f1_positive"]["n_splits"], 1)
        self.assertEqual(aggregated["overall"]["f1_positive"]["mean"], 1.0)

    def test_voice_axis_requires_measured_operating_point(self):
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            key = str(profile)
            try:
                voice._MODEL_CACHE[key] = {
                    "operating_point": 0.4,
                    "measurement_status": "degraded",
                }
                self.assertEqual(
                    voice.voice_axis_status(profile)["status"], "degraded")
                self.assertFalse(
                    voice.bundle_measured(voice._MODEL_CACHE[key]))
                voice._MODEL_CACHE[key] = {
                    "operating_point": 0.4,
                    "measurement_status": "measured",
                }
                self.assertEqual(
                    voice.voice_axis_status(profile)["status"], "measured")
                self.assertTrue(
                    voice.bundle_measured(voice._MODEL_CACHE[key]))
            finally:
                voice._MODEL_CACHE.pop(key, None)

    def test_voice_model_load_rejects_feature_provenance_drift(self):
        try:
            import joblib
        except ImportError:  # CI runs without optional dependencies
            self.skipTest("joblib is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            joblib.dump(
                {"feature_names": ["only_one_feature"],
                 "feature_schema": "sci-paper.voice-features.v0"},
                profile / "voice_model.joblib")
            try:
                self.assertIsNone(voice.load_voice_model(profile))
            finally:
                voice._MODEL_CACHE.pop(str(profile), None)

    def test_voice_model_load_degrades_on_corrupt_bundle(self):
        try:
            import joblib  # noqa: F401  presence gates the load path under test
        except ImportError:  # CI runs without optional dependencies
            self.skipTest("joblib is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary)
            (profile / "voice_model.joblib").write_bytes(b"truncated-bundle")
            try:
                self.assertIsNone(voice.load_voice_model(profile))
            finally:
                voice._MODEL_CACHE.pop(str(profile), None)

    def test_source_family_does_not_use_authorship_labels(self):
        self.assertEqual(
            training.source_family("style-corpus/paper.pdf"),
            "curated-field-paper",
        )
        self.assertEqual(
            training.source_family("raid-human:42"),
            "public-reference",
        )
        self.assertEqual(
            training.source_family("gen2:42"),
            "generated-field",
        )
        self.assertEqual(
            training.source_family("raid-ai:42"),
            "generated-public",
        )


if __name__ == "__main__":
    unittest.main()
