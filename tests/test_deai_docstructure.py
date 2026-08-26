from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import deai_docstructure as docstructure
import deai_features


REPEATED_PARAGRAPH = (
    "The estimator must preserve the measured signal under rotation. "
    "The covariance must retain the corresponding noise dependence under rotation. "
    "The likelihood must represent these two quantities without changing their units. "
    "These three requirements define the calculation used for every sample in this analysis."
)

SHORT_PARAGRAPH = (
    "A direct calculation fixes the scale. The result follows from the measured "
    "covariance and does not require a separate roadmap sentence. The remaining "
    "uncertainty comes from the finite sample rather than the estimator itself."
)

LONG_PARAGRAPH = (
    "Because the selection function couples angular position, source density, and "
    "measurement noise, we evaluate its contribution before fitting the population "
    "model; this ordering preserves the conditional structure of the likelihood, "
    "keeps the normalization explicit, and makes the later comparison with the null "
    "sample depend on a quantity that has already been defined."
)


def document(paragraphs: list[str]) -> str:
    sections = []
    for index, name in enumerate(("Introduction", "Methods", "Results")):
        first = paragraphs[(2 * index) % len(paragraphs)]
        second = paragraphs[(2 * index + 1) % len(paragraphs)]
        sections.append(f"\\section{{{name}}}\n\n{first}\n\n{second}")
    return "\n\n".join(sections) + "\n"


class DocumentStructureTests(unittest.TestCase):
    def test_repeated_shape_is_more_uniform_than_ragged_shape(self):
        repeated = docstructure.document_shape(document([REPEATED_PARAGRAPH]))
        ragged = docstructure.document_shape(document([
            REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
            SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
        ]))
        self.assertEqual(repeated["status"], "measured")
        self.assertEqual(ragged["status"], "measured")
        self.assertGreater(
            repeated["metrics"]["within_section_similarity"],
            ragged["metrics"]["within_section_similarity"],
        )

    def test_short_document_reports_insufficient_evidence(self):
        result = docstructure.document_shape(
            "\\section{Introduction}\n\n" + REPEATED_PARAGRAPH)
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIn("at least 3 sections", result["reason"])

    def test_calibration_uses_complete_documents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            variants = [
                [REPEATED_PARAGRAPH, SHORT_PARAGRAPH],
                [SHORT_PARAGRAPH, LONG_PARAGRAPH],
                [LONG_PARAGRAPH, REPEATED_PARAGRAPH],
            ]
            for index, paragraphs in enumerate(variants):
                path = root / f"human-{index}.tex"
                path.write_text(document(paragraphs), encoding="utf-8")
                sources.append(path)
            baseline = docstructure.calibrate(sources, root, strong_percentile=0.8)
            self.assertEqual(baseline["n_documents"], 3)
            self.assertEqual(len(baseline["documents"]), 3)
            self.assertTrue((root / docstructure.BASELINE_NAME).exists())
            for metric in docstructure.METRIC_NAMES:
                self.assertEqual(len(baseline["metrics"][metric]["values"]), 3)
            # role-coupling reference is stored alongside the dispersion band
            self.assertIn("role_coupling", baseline)
            self.assertEqual(baseline["role_coupling"]["scoring_factors"],
                             list(docstructure.ROLE_SCORING_FACTORS))
            self.assertEqual(len(baseline["role_coupling"]["values"]), 3)

    def test_document_shape_reports_cross_paragraph_dispersion(self):
        shape = docstructure.document_shape(document([
            REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
            SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
        ]))
        self.assertEqual(shape["status"], "measured")
        self.assertIn("dispersion", shape)
        # every model-free feature has a std dispersion entry
        for name in docstructure.DISPERSION_FEATURE_NAMES:
            self.assertIn(name, shape["dispersion"])
            self.assertIn(docstructure.DISPERSION_STAT, shape["dispersion"][name])

    def test_dispersion_manifold_math_and_outlier(self):
        inverse = docstructure._mat_inv([[1.0, 0.0], [0.0, 1.0]])
        self.assertAlmostEqual(inverse[0][0], 1.0)
        self.assertAlmostEqual(inverse[0][1], 0.0)
        self.assertAlmostEqual(
            docstructure._mahalanobis([3.0, 4.0], [0.0, 0.0],
                                      [[1.0, 0.0], [0.0, 1.0]]), 5.0)
        rows = [{"a": 1.0 + 0.01 * i, "b": 2.0 + 0.02 * (i % 7),
                 "c": 0.5 + 0.005 * (i % 11)} for i in range(40)]
        manifold = docstructure.fit_dispersion_manifold(rows, ["a", "b", "c"])
        self.assertIsNotNone(manifold)
        self.assertEqual(manifold["n_documents"], 40)
        far = docstructure.manifold_distance(
            manifold, {"a": 10.0, "b": 0.01, "c": 5.0})
        near = docstructure.manifold_distance(manifold, rows[20])
        self.assertGreater(far, manifold["threshold"])
        self.assertLess(near, far)
        # below the minimum document count the manifold is honestly absent
        self.assertIsNone(docstructure.fit_dispersion_manifold(rows[:5], ["a", "b", "c"]))

    def test_over_dispersed_document_flags_high_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Reference: consistently UNIFORM human stand-ins (narrow band).
            sources = []
            for index in range(4):
                path = root / f"human-{index}.tex"
                path.write_text(document([REPEATED_PARAGRAPH]), encoding="utf-8")
                sources.append(path)
            docstructure.calibrate(sources, root, strong_percentile=0.9)
            # A wildly varied document departs the band on the HIGH side.
            ragged = docstructure.document_findings(document([
                REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
            ]), root)
            self.assertTrue(
                [f for f in ragged
                 if f["rule"].startswith("document-overdispersion:")],
                "an over-dispersed document should flag the high tail")

    def test_role_coupling_z_separates_coupled_from_decoupled(self):
        # 30 paragraphs, one feature; two role groups with distinct means.
        coupled_vectors = [[1.0 + 0.05 * (i % 3)] if i < 15
                           else [5.0 + 0.05 * (i % 3)] for i in range(30)]
        labels = [0] * 15 + [1] * 15
        coupled = deai_features.role_coupling_z(coupled_vectors, labels)
        self.assertIsNotNone(coupled["mean_z"])
        self.assertGreater(coupled["mean_z"], 2.0)
        # Same value spread, but placed independently of the role labels.
        decoupled_vectors = [[1.0 + 0.05 * (i % 3)] if i % 2 == 0
                             else [5.0 + 0.05 * (i % 3)] for i in range(30)]
        decoupled = deai_features.role_coupling_z(decoupled_vectors, labels)
        self.assertIsNotNone(decoupled["mean_z"])
        self.assertLess(decoupled["mean_z"], coupled["mean_z"] / 2)
        # Constant feature: eta-squared undefined, honestly unmeasured.
        constant = deai_features.role_coupling_z([[2.0]] * 30, labels)
        self.assertIsNone(constant["mean_z"])

    def test_conformal_helpers(self):
        # stratum assignment against ascending edges
        self.assertEqual(docstructure._length_stratum(10, [46.0, 76.0]), 0)
        self.assertEqual(docstructure._length_stratum(46, [46.0, 76.0]), 0)
        self.assertEqual(docstructure._length_stratum(60, [46.0, 76.0]), 1)
        self.assertEqual(docstructure._length_stratum(200, [46.0, 76.0]), 2)
        # conformal p: rank with add-one smoothing; exact small case
        cal = [1.0, 2.0, 3.0, 4.0]
        self.assertAlmostEqual(docstructure._conformal_p(cal, 5.0), 1 / 5)
        self.assertAlmostEqual(docstructure._conformal_p(cal, 0.0), 5 / 5)
        self.assertAlmostEqual(docstructure._conformal_p(cal, 2.5), 3 / 5)
        # thin stratum falls back to the pooled calibration set
        axis = {"min_cal_per_stratum": 3,
                "calibration": [[0, 1.0], [0, 2.0], [0, 3.0], [1, 9.0]]}
        scores, basis = docstructure._stratum_calibration(axis, 0)
        self.assertEqual((len(scores), basis), (3, "stratum 0"))
        scores, basis = docstructure._stratum_calibration(axis, 1)
        self.assertEqual((len(scores), basis), (4, "pooled"))

    def test_role_coupling_guards(self):
        labels = [0] * 15 + [1] * 15
        # NaN column: min(1.0, NaN) is 1.0 in CPython, which used to bypass
        # the ss_total guard and report eta-squared 1.0; must be undefined.
        nan_result = deai_features.role_coupling_z(
            [[float("nan")]] * 30, labels)
        self.assertIsNone(nan_result["mean_z"])
        # unequal-length vectors must raise, not silently truncate under zip
        with self.assertRaises(ValueError):
            deai_features.role_coupling_z([[1.0, 2.0], [1.0]], [0, 1])
        # escaped dollars and row breaks are not math markers
        self.assertIsNone(
            docstructure._MATH_MARKER_RE.search("cost \\$5 total"))
        self.assertIsNone(
            docstructure._MATH_MARKER_RE.search("value \\\\[5pt] more"))
        self.assertIsNotNone(
            docstructure._MATH_MARKER_RE.search("inline $x$ math"))
        self.assertIsNotNone(
            docstructure._MATH_MARKER_RE.search("display \\[ x \\] math"))

    def test_role_baseline_factor_drift_disables_finding(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            coupled_doc = (
                f"\\section{{Introduction}}\n\n{SHORT_PARAGRAPH}\n\n{SHORT_PARAGRAPH}"
                f"\n\n\\section{{Methods}}\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}"
                f"\n\n\\section{{Results}}\n\n{REPEATED_PARAGRAPH}\n\n{REPEATED_PARAGRAPH}\n")
            sources = []
            for index in range(4):
                path = root / f"human-{index}.tex"
                path.write_text(coupled_doc, encoding="utf-8")
                sources.append(path)
            docstructure.calibrate(sources, root, strong_percentile=0.9)
            baseline_path = root / docstructure.BASELINE_NAME
            baseline = __import__("json").loads(
                baseline_path.read_text(encoding="utf-8"))
            baseline["role_coupling"]["scoring_factors"] = ["section"]
            baseline_path.write_text(__import__("json").dumps(baseline),
                                     encoding="utf-8")
            decoupled_doc = (
                f"\\section{{Introduction}}\n\n{SHORT_PARAGRAPH}\n\n{LONG_PARAGRAPH}"
                f"\n\n\\section{{Methods}}\n\n{REPEATED_PARAGRAPH}\n\n{SHORT_PARAGRAPH}"
                f"\n\n\\section{{Results}}\n\n{LONG_PARAGRAPH}\n\n{REPEATED_PARAGRAPH}\n")
            findings = docstructure.document_findings(decoupled_doc, root)
            self.assertFalse(
                [f for f in findings if f["rule"] == "document-role-decoupling"],
                "mismatched scoring_factors must disable the role axis, not "
                "compare against thresholds fit on a different quantity")

    def test_document_role_coupling_states(self):
        shape = docstructure.document_shape(document([
            REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
            SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
        ]))
        role = docstructure.document_role_coupling(shape)
        self.assertEqual(role["status"], "measured")
        self.assertIsNotNone(role["score"])
        self.assertEqual(set(role["factors"]), set(docstructure.ROLE_FACTORS))
        # an unmeasurable document degrades honestly
        short = docstructure.document_shape(
            "\\section{Introduction}\n\n" + REPEATED_PARAGRAPH)
        self.assertEqual(docstructure.document_role_coupling(short)["status"],
                         "unmeasured")

    def test_role_decoupled_document_flags_low_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Reference: paragraph shape strongly follows section identity
            # (each section repeats its own shape).
            coupled_doc = (
                f"\\section{{Introduction}}\n\n{SHORT_PARAGRAPH}\n\n{SHORT_PARAGRAPH}"
                f"\n\n\\section{{Methods}}\n\n{LONG_PARAGRAPH}\n\n{LONG_PARAGRAPH}"
                f"\n\n\\section{{Results}}\n\n{REPEATED_PARAGRAPH}\n\n{REPEATED_PARAGRAPH}\n")
            sources = []
            for index in range(4):
                path = root / f"human-{index}.tex"
                path.write_text(coupled_doc, encoding="utf-8")
                sources.append(path)
            baseline = docstructure.calibrate(sources, root, strong_percentile=0.9)
            self.assertIn("role_coupling", baseline)
            # Target: identical shape spread, shuffled against the sections.
            decoupled_doc = (
                f"\\section{{Introduction}}\n\n{SHORT_PARAGRAPH}\n\n{LONG_PARAGRAPH}"
                f"\n\n\\section{{Methods}}\n\n{REPEATED_PARAGRAPH}\n\n{SHORT_PARAGRAPH}"
                f"\n\n\\section{{Results}}\n\n{LONG_PARAGRAPH}\n\n{REPEATED_PARAGRAPH}\n")
            findings = docstructure.document_findings(decoupled_doc, root)
            self.assertTrue(
                [f for f in findings if f["rule"] == "document-role-decoupling"],
                "a role-decoupled document should flag the low tail")
            coupled_findings = docstructure.document_findings(coupled_doc, root)
            self.assertFalse(
                [f for f in coupled_findings
                 if f["rule"] == "document-role-decoupling"],
                "a role-coupled document matching the reference must not flag")

    def test_over_uniform_document_is_flagged_but_varied_is_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # Human reference: ragged documents that mix paragraph shapes.
            sources = []
            for index in range(4):
                path = root / f"human-{index}.tex"
                path.write_text(document([
                    REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                    SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
                ]), encoding="utf-8")
                sources.append(path)
            docstructure.calibrate(sources, root, strong_percentile=0.9)
            # An over-uniform document (every paragraph identical) must draw at
            # least one over-uniformity finding; the varied reference shape must not.
            uniform = docstructure.document_findings(
                document([REPEATED_PARAGRAPH]), root)
            uniformity_hits = [f for f in uniform
                               if f["rule"].startswith("document-uniformity:")]
            self.assertTrue(uniformity_hits, "over-uniform document should flag")
            varied = docstructure.document_findings(document([
                REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
            ]), root)
            self.assertFalse(
                [f for f in varied if f["rule"].startswith("document-uniformity:")],
                "a document matching the human reference shape should not flag")


if __name__ == "__main__":
    unittest.main()


class ModuleSplitContractTests(unittest.TestCase):
    """`deai_docstructure` must re-export everything `deai_docshape` defines.

    The measurement layer was split out on 2026-08-25 (1,092 lines against a
    750-line budget). Eight sibling tools and the tests reach these names as
    `dds.<name>`, and the re-export list is hand-written, so it can silently
    fall behind the module it mirrors -- exactly the drift the equivalent
    `extract_style` test has caught three times.
    """

    def test_every_public_name_is_re_exported(self):
        import deai_docshape as shape
        expected = {
            n for n, v in vars(shape).items()
            if not n.startswith("__")
            and getattr(v, "__module__", "deai_docshape") in ("deai_docshape",
                                                              "re", None)
            and n not in {"annotations", "Path", "Any", "Iterable"}
        }
        missing = sorted(n for n in expected if not hasattr(docstructure, n))
        self.assertEqual(missing, [],
                         f"deai_docstructure does not re-export: {missing}")


class CorpusDocumentOrderTests(unittest.TestCase):
    r"""A bundle is assembled in document order, not sorted filename order.

    This axis measures section arc, so concatenating `Conclusion.tex` before
    `Introduction.tex` corrupts the observation itself. 122 of 500 `wgl`
    bundles hold more than one `.tex`; 12 were provably out of order.
    """

    def test_paper_documents_follows_include_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            d = root / "2501.00001"
            d.mkdir()
            (d / "ms.tex").write_text(
                r"\documentclass{mnras}" "\n" r"\begin{document}" "\n"
                r"\input{Introduction}" "\n" r"\input{Conclusion}" "\n"
                r"\end{document}" "\n", encoding="utf-8")
            (d / "Introduction.tex").write_text("FIRST body\n", encoding="utf-8")
            (d / "Conclusion.tex").write_text("LAST body\n", encoding="utf-8")
            docs = docstructure._paper_documents(root)
        self.assertEqual(len(docs), 1)
        text = docs[0][1]
        self.assertLess(text.index("FIRST body"), text.index("LAST body"))

    def test_a_bundle_is_one_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            d = root / "2501.00002"
            d.mkdir()
            (d / "main.tex").write_text(
                r"\documentclass{article}" "\n" r"\input{chap}" "\n",
                encoding="utf-8")
            (d / "chap.tex").write_text("body\n", encoding="utf-8")
            docs = docstructure._paper_documents(root)
        self.assertEqual([n for n, _t in docs], ["2501.00002"])
