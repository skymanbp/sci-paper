"""`deai_voice` is the optional L3 triage: it degrades, it never crashes.

Two things in front of it are optional: the trained bundle (joblib) and the
surprisal runtime (transformers/torch) that `deai_features.features_vector`
needs for three of the bundle's features. Without the bundle the axis was
already `unmeasured`; without the runtime `features_vector` raises, and until
2026-09-27 that RuntimeError went straight through `voice_score`, the
findings, the axis status and `--scores`. These tests pin that path to
`unmeasured` with the runtime's reason, check that a present runtime still
scores, and hold the `--field` resolution that once divided a path by None.
"""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_features as df
import deai_oracle as oracle
import deai_voice as voice

# Two paragraphs of sixty words each: over the thirty-word floor of the sweep.
TEXT = ("\\section{Introduction}\n"
        + ("The estimator uses five filters and reports the peak height. " * 6).strip()
        + "\n\n\\section{Methods}\n"
        + ("The shear catalog is measured around each cluster in the field. " * 6).strip()
        + "\n")
MISSING = "the optional surprisal runtime is not installed (torch)"


def fake_bundle() -> dict:
    """A bundle `load_voice_model` accepts: the installed feature schema and a
    measured operating point, with no classifier (the scoring is patched)."""
    return {"feature_names": list(df.FEATURE_NAMES),
            "feature_schema": df.FEATURE_SCHEMA_VERSION,
            "measurement_status": "measured", "operating_point": 0.5,
            "model": "stub"}


class RuntimeProbeTests(unittest.TestCase):
    def setUp(self):
        self.raw = tempfile.TemporaryDirectory(prefix="voice-")
        self.addCleanup(self.raw.cleanup)
        self.root = Path(self.raw.name) / "profiles"
        self.field = self.root / "fld"
        self.field.mkdir(parents=True)
        # The cache is the one way a bundle enters without joblib installed.
        voice._MODEL_CACHE[str(self.field)] = fake_bundle()
        self.addCleanup(voice._MODEL_CACHE.pop, str(self.field), None)
        self.addCleanup(df._CENTROID_CACHE.pop, str(self.field), None)

    def test_without_the_runtime_the_axis_is_unmeasured_with_the_reason(self):
        with mock.patch.object(oracle, "model_runtime_available",
                               return_value=(False, MISSING)):
            self.assertIsNone(voice.voice_score(TEXT, self.field))
            self.assertEqual(voice.voice_findings(TEXT, self.field), [])
            status = voice.voice_axis_status(self.field)
        self.assertEqual(status["status"], "unmeasured")
        self.assertIn(MISSING, status["reason"])
        self.assertIn("token surprisal", status["reason"])

    def test_scores_without_the_runtime_prints_the_reason_and_exits_zero(self):
        draft = Path(self.raw.name) / "draft.tex"
        draft.write_text(TEXT, encoding="utf-8")
        stdout = io.StringIO()
        with mock.patch.object(oracle, "model_runtime_available",
                               return_value=(False, MISSING)), \
                contextlib.redirect_stdout(stdout):
            code = voice.main([str(draft), "--field", "fld", "--profile-root",
                               str(self.root), "--scores"])
        self.assertEqual(code, 0)
        self.assertIn(f"axis L3.voice: unmeasured: {MISSING}", stdout.getvalue())

    def test_with_the_runtime_the_bundle_scores_and_flags(self):
        # The probe must not block a present runtime: the vector and the
        # classifier are stubbed, the rest of the path is real.
        with mock.patch.object(oracle, "model_runtime_available", return_value=(True, "")), \
                mock.patch.object(df, "features_vector",
                                  return_value=[0.0] * len(df.FEATURE_NAMES)), \
                mock.patch.object(voice, "_positive_class_probability", return_value=0.25):
            self.assertEqual(voice.voice_score(TEXT, self.field), 0.25)
            self.assertEqual(voice.voice_axis_status(self.field)["status"], "measured")
            findings = voice.voice_findings(TEXT, self.field)
        self.assertEqual([f["rule"] for f in findings],
                         ["voice-distance:intro", "voice-distance:method"])
        self.assertEqual({f["measurement_status"] for f in findings}, {"measured"})


class FieldResolutionTests(unittest.TestCase):
    """`--field` resolves through `cli_common.optional_field_dir`: none or
    several profiles is the exit 2 the tool always printed for a missing
    bundle, one resolves on its own, and `profile_root / None` is no longer a
    TypeError."""

    def test_without_a_field_is_exit_two_not_a_type_error(self):
        with tempfile.TemporaryDirectory(prefix="voice-") as raw:
            draft = Path(raw) / "draft.tex"
            draft.write_text(TEXT, encoding="utf-8")
            profiles = Path(raw) / "profiles"
            (profiles / "one").mkdir(parents=True)
            (profiles / "two").mkdir()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(voice.main([str(draft), "--profile-root", str(profiles)]), 2)
            self.assertIn("no voice_model.joblib", stderr.getvalue())
            (profiles / "two").rmdir()
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(voice.main([str(draft), "--profile-root", str(profiles)]), 2)
            self.assertIn(str(profiles / "one"), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
