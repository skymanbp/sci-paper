from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_features as features
import deai_voice as voice
import train_voice_model as training


def _unbound_names(source: str, filename: str = "<module>") -> list[str]:
    """`scope:name` for every name read where no binding reaches it.

    Scope-aware, on CPython's own symbol tables rather than a flat walk of the
    AST. The flat walk pooled every binding in the module, so a function-local
    `import numpy as np` in one function let a bare `np` in every other
    function pass, and the `time` it was written to catch went uncaught the
    moment any other scope bound the name. Here a function-local import binds
    the name only inside that function; a name a function reads without
    binding it must be bound at module level (including through a `global`
    declaration elsewhere), be a builtin, or be a closure variable of an
    enclosing function. Annotation and type-parameter blocks (3.12+) are
    skipped: every tool imports `annotations` from `__future__`, so those
    names are never evaluated.
    """
    import builtins
    import symtable

    module = symtable.symtable(source, filename, "exec")
    known = set(dir(builtins)) | {
        "__file__", "__name__", "__doc__", "__package__", "__spec__",
        "__loader__", "__builtins__", "__module__", "__qualname__"}

    def tables(table):
        yield table
        for child in table.get_children():
            try:
                kind = child.get_type()
            except AssertionError:  # a 3.12 annotation or type-parameter block
                continue
            if kind in ("function", "class"):
                yield from tables(child)

    scopes = list(tables(module))
    for table in scopes:
        for symbol in table.get_symbols():
            bound_here = (symbol.is_assigned() or symbol.is_imported()
                          or symbol.is_namespace())
            if bound_here and (table is module or symbol.is_declared_global()):
                known.add(symbol.get_name())
    return sorted(
        f"{table.get_name()}:{symbol.get_name()}"
        for table in scopes for symbol in table.get_symbols()
        if symbol.is_referenced()
        and not (symbol.is_local() or symbol.is_free() or symbol.is_parameter())
        and symbol.get_name() not in known)


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

    def test_no_name_is_read_where_nothing_binds_it(self):
        """Every name a tool reads must be bound in a scope that reaches it.

        Splitting a module moves function bodies but re-writes the import block
        by hand, so a moved function can reference a name that stayed behind.
        That is not a hypothetical: the 2026-08-26 split left `time`,
        `CHECKPOINT_EVERY`, `df` and the two HARDSET category sets unbound, and
        the suite went green anyway because no test reached those lines --
        `build_features` failed only when a real retrain ran. This reads the
        symbol tables instead of waiting for a call site.
        """
        for name in sorted(p.name for p in TOOLS.glob("*.py")):
            unbound = _unbound_names((TOOLS / name).read_text(encoding="utf-8"), name)
            self.assertEqual(unbound, [], f"{name} reads names nothing binds")

    def test_the_unbound_name_check_is_scope_aware(self):
        # The case the 2026-09-27 audit reproduced against the flat walk: a
        # local import in one function does not bind the name in another.
        leaked = ("def a():\n    import numpy as np\n    return np\n\n"
                  "def b():\n    return np.zeros(1)\n")
        self.assertEqual(_unbound_names(leaked), ["b:np"])
        # The case the check was written for, in the shape it had.
        split = ("def build_features():\n    t0 = time.time()\n"
                 "    return CHECKPOINT_EVERY - t0\n")
        self.assertEqual(_unbound_names(split),
                         ["build_features:CHECKPOINT_EVERY", "build_features:time"])
        # The same names bound where they are read pass, as do a closure, a
        # `global` binding made in another function, and a method's `super()`.
        bound = ("import time\nCHECKPOINT_EVERY = 500\n\n"
                 "def build_features():\n    import numpy as np\n"
                 "    return np, time.time(), CHECKPOINT_EVERY\n\n"
                 "def outer():\n    x = 1\n    def inner():\n        return x\n"
                 "    return inner\n\n"
                 "def init():\n    global _CACHE\n    _CACHE = {}\n\n"
                 "def use():\n    return _CACHE\n\n"
                 "class K(dict):\n    def m(self):\n        return super().m()\n")
        self.assertEqual(_unbound_names(bound), [])
        # A class attribute is not visible from its methods: a real NameError.
        self.assertEqual(
            _unbound_names("class K:\n    attr = 1\n    def m(self):\n        return attr\n"),
            ["m:attr"])

    def test_the_split_modules_carry_no_unused_import(self):
        """The mirror of the unbound-name check: a name imported and never read.

        The 2026-08-26 split re-wrote three import blocks by hand and left
        hashlib, math, re, statistics, json, Counter and defaultdict behind in
        one file or another (audit 2026-09-27, E22), plus `DEFAULT_PROFILE_ROOT`
        copies that `cli_common` owns. Declared re-exports (`noqa: F401`) are
        read by nothing here by design and are skipped.
        """
        import ast

        for name in ("train_voice_model.py", "voice_dataset.py", "voice_audit.py",
                     "train_ai_ism_classifier.py"):
            source = (TOOLS / name).read_text(encoding="utf-8")
            lines = source.splitlines()
            tree = ast.parse(source)
            imported = set()
            for node in tree.body:
                if not isinstance(node, (ast.Import, ast.ImportFrom)):
                    continue
                if "F401" in " ".join(lines[node.lineno - 1:node.end_lineno]):
                    continue
                for alias in node.names:
                    bound = (alias.asname or alias.name).split(".")[0]
                    if bound != "annotations":
                        imported.add(bound)
            read = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            unused = sorted(imported - read)
            self.assertEqual(unused, [], f"{name} imports but never reads {unused}")
        import train_ai_ism_classifier
        import voice_dataset
        for module in (training, voice_dataset, train_ai_ism_classifier):
            self.assertFalse(hasattr(module, "DEFAULT_PROFILE_ROOT"), module.__name__)
        self.assertFalse(hasattr(train_ai_ism_classifier, "list_fields"))


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
        # The status under test is the bundle's, so every input the feature
        # vector needs is pinned as present -- the surprisal runtime, the
        # embedder and the exemplar centroid: without one the axis is
        # `unmeasured` whatever the bundle says (tests/test_deai_voice.py).
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(voice.do, "model_runtime_available",
                                  return_value=(True, "")), \
                mock.patch.object(voice.df, "embedder_available", return_value=True), \
                mock.patch.object(voice.df, "corpus_centroid", return_value=object()):
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

    def test_a_blank_line_in_a_bank_is_skipped_not_parsed(self):
        # `train_ai_ism_classifier.load_positives` reads the same files and
        # always tolerated a blank line; `json.loads("")` raised here.
        with tempfile.TemporaryDirectory() as raw:
            bank = Path(raw) / "exemplar_paragraphs.jsonl"
            record = json.dumps({"text": "word " * 30, "source": "s"})
            bank.write_text(record + "\n\n" + record + "\n   \n", encoding="utf-8")
            loaded = training._load_jsonl(bank, 1, "corpus")
        self.assertEqual(len(loaded), 2)
        self.assertEqual({record["label"] for record in loaded}, {1})

    def test_repeated_audit_seeds_start_past_the_primary_split(self):
        # The first "repeat" was the primary split again, so twenty repeats
        # were nineteen plus the one already reported.
        self.assertEqual(training.audit_split_seed(7, 0), 8)
        self.assertNotIn(7, [training.audit_split_seed(7, attempt)
                             for attempt in range(400)])
        self.assertEqual([training.audit_split_seed(0, a) for a in range(3)], [1, 2, 3])
        # ...counted from the seed the primary actually used, which the
        # trainer passes on rather than the one requested.
        source = (TOOLS / "train_voice_model.py").read_text(encoding="utf-8")
        self.assertIn("seed=primary_split_seed", source)


class _Array:
    """Just enough of an ndarray for `build_features`' bookkeeping."""

    def __init__(self, shape, value=None):
        self.shape = tuple(shape)
        self.value = value

    def __setitem__(self, key, value):
        pass

    def __getitem__(self, key):
        return self

    def __iter__(self):
        return iter(self.value or [])

    def item(self):
        return self.value

    def copy(self):
        return self


class _Npz:
    def __init__(self, stored):
        self._stored = stored
        self.files = list(stored)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __getitem__(self, key):
        shape, value = self._stored[key]
        return _Array(shape, value)


class _Numpy(types.ModuleType):
    """A stand-in for the optional numpy: an array is its shape plus, for the
    small ones, its values, and `savez`/`load` round-trip them through JSON."""

    float32 = "float32"

    def __init__(self):
        super().__init__("numpy")

    def zeros(self, shape, dtype=None):
        return _Array(shape)

    def asarray(self, values, dtype=None):
        if isinstance(values, _Array):
            return values
        if isinstance(values, (int, float, str)):
            return _Array((), values)
        rows = list(values)
        if rows and isinstance(rows[0], (list, tuple)):
            return _Array((len(rows), len(rows[0])), [list(row) for row in rows])
        return _Array((len(rows),), rows)

    def array_equal(self, first, second):
        return first.value == second.value

    def savez(self, handle, **arrays):
        handle.write(json.dumps({key: [list(array.shape), array.value]
                                 for key, array in arrays.items()}).encode("utf-8"))

    def load(self, path, allow_pickle=False):
        return _Npz(json.loads(Path(path).read_bytes()))


class EmbeddingFailureTests(unittest.TestCase):
    """A run whose encoder fails must not become the feature cache.

    `embedder_available()` probes the import, and that is what the cache
    fingerprint records. The encode itself can still fail -- offline, a
    device fault -- and the rows then carry corpus_cos = 0.0; cached under the
    healthy fingerprint they were served as measured to every later run.
    """

    RECORDS = [{"text": "word " * 40 + str(i), "label": i % 2, "source": f"s{i}",
                "section": "method"} for i in range(4)]

    def test_width_zero_is_a_failure_only_when_the_embedder_imports(self):
        original = features.embedder_available
        try:
            features.embedder_available = lambda: True
            self.assertTrue(training.embeddings_failed_at_run_time(0))
            self.assertFalse(training.embeddings_failed_at_run_time(384))
            features.embedder_available = lambda: False
            self.assertFalse(training.embeddings_failed_at_run_time(0))
        finally:
            features.embedder_available = original

    @contextlib.contextmanager
    def _fakes(self, encoder):
        """The numpy stand-in, an importable embedder whose encode is
        `encoder`, and a free per-record feature pass that records its calls."""
        saved = sys.modules.get("numpy")
        originals = (features.embedder_available, features._embedder,
                     features.features_vector)
        featurized: list[str] = []
        sys.modules["numpy"] = _Numpy()
        features.embedder_available = lambda: True
        features._embedder = lambda: types.SimpleNamespace(encode=encoder)
        features.features_vector = (
            lambda text, **kw: featurized.append(text) or [0.0] * len(features.FEATURE_NAMES))
        try:
            yield featurized
        finally:
            (features.embedder_available, features._embedder,
             features.features_vector) = originals
            if saved is None:
                sys.modules.pop("numpy", None)
            else:
                sys.modules["numpy"] = saved

    @staticmethod
    def _failing(*args, **kwargs):
        raise RuntimeError("offline")

    @staticmethod
    def _working(plains, **kwargs):
        return [[0.1, 0.2, 0.3] for _ in plains]

    def test_a_failed_encode_withholds_the_cache_and_keeps_the_rows(self):
        with tempfile.TemporaryDirectory() as raw:
            field_dir = Path(raw)
            cache = field_dir / "voice_features_cache.npz"
            partial = field_dir / "voice_features_cache.partial.npz"
            with self._fakes(self._failing) as featurized, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                _X, _y, _src, emb = training.build_features(
                    field_dir, self.RECORDS, "gpt2", False)
            self.assertEqual(emb.shape, (4, 0))
            self.assertEqual(len(featurized), 4)
            self.assertFalse(cache.exists())
            self.assertTrue(partial.exists())
            self.assertEqual(json.loads(partial.read_bytes())["n_done"][1], 4)
            self.assertIn("withheld", err.getvalue())
            # The next run resumes past the language-model pass, retries the
            # embedder, and only then writes the cache.
            with self._fakes(self._working) as featurized, \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                _X, _y, _src, emb = training.build_features(
                    field_dir, self.RECORDS, "gpt2", False)
            self.assertEqual(emb.shape, (4, 3))
            self.assertEqual(featurized, [])
            self.assertIn("resuming featurization from checkpoint row 4/4", err.getvalue())
            self.assertTrue(cache.exists())
            self.assertFalse(partial.exists())

    def test_a_cache_of_empty_embeddings_under_a_healthy_fingerprint_is_recomputed(self):
        # A cache an earlier run wrote from a failed encode.
        with tempfile.TemporaryDirectory() as raw, self._fakes(self._working) as featurized:
            field_dir = Path(raw)
            fingerprint = training.feature_cache_fingerprint(field_dir, self.RECORDS, "gpt2")
            names = list(features.FEATURE_NAMES)
            stale = {"X": [[4, len(names)], None],
                     "y": [[4], [r["label"] for r in self.RECORDS]],
                     "src": [[4], [r["source"] for r in self.RECORDS]],
                     "emb": [[4, 0], None],
                     "names": [[len(names)], names],
                     "fingerprint": [[], fingerprint]}
            (field_dir / "voice_features_cache.npz").write_bytes(
                json.dumps(stale).encode("utf-8"))
            with contextlib.redirect_stderr(io.StringIO()) as err:
                _X, _y, _src, emb = training.build_features(
                    field_dir, self.RECORDS, "gpt2", False)
        self.assertIn("empty embeddings", err.getvalue())
        self.assertEqual(len(featurized), 4)
        self.assertEqual(emb.shape, (4, 3))


class TrainingEntryTests(unittest.TestCase):
    def test_a_missing_learning_dependency_is_one_line_and_exit_2(self):
        saved = sys.modules.get("numpy")
        sys.modules["numpy"] = None      # `import numpy` raises, installed or not
        try:
            with tempfile.TemporaryDirectory() as raw:
                (Path(raw) / "wgl").mkdir()
                err = io.StringIO()
                with contextlib.redirect_stderr(err), \
                        contextlib.redirect_stdout(io.StringIO()):
                    code = training.main(["--field", "wgl", "--profile-root", raw])
        finally:
            if saved is None:
                sys.modules.pop("numpy", None)
            else:
                sys.modules["numpy"] = saved
        self.assertEqual(code, 2)
        self.assertEqual(err.getvalue().count("\n"), 1, err.getvalue())
        self.assertIn("[train_voice_model] cannot train without numpy", err.getvalue())

    def test_the_field_is_resolved_under_the_tools_own_name(self):
        # `args.profile_root / None` was a TypeError traceback without --field.
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaises(SystemExit) as caught:
                training.main(["--field", "nope", "--profile-root", raw])
        self.assertIn("[train_voice_model]", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
