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
