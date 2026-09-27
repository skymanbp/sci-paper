from __future__ import annotations

import contextlib
import io
import itertools
import json
import pathlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

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
            # Four documents resolve no 5% tail: context, not a strong finding.
            self.assertEqual({(f["strength"], f["measurement_status"])
                              for f in uniformity_hits}, {("ordinary", "degraded")})
            varied = docstructure.document_findings(document([
                REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH,
            ]), root)
            self.assertFalse(
                [f for f in varied if f["rule"].startswith("document-uniformity:")],
                "a document matching the human reference shape should not flag")


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
        # A module object has no `__module__`, so the getattr default used to
        # count `json`, `re`, `statistics` and the sibling aliases as names
        # `deai_docshape` defines -- which made their dead imports in
        # `deai_docstructure` "required" (audit 2026-09-27, B20).
        expected = {
            n for n, v in vars(shape).items()
            if not n.startswith("__")
            and not isinstance(v, types.ModuleType)
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


class SweepAndOperatingPointTests(unittest.TestCase):
    """The 2026-09-27 audit's B12 (skip buckets) and B9 (one threshold rule)."""

    SKIP_TAIL = (
        "\n\n\\section{Acknowledgments}\n\n" + LONG_PARAGRAPH + "\n\n" + SHORT_PARAGRAPH
        + "\n\n\\section{Appendix A}\n\n" + REPEATED_PARAGRAPH + "\n\n" + LONG_PARAGRAPH
        + "\n\n\\begin{thebibliography}{9}\n\\bibitem{a} A. Author 2020, ApJ 1, 1.\n"
        "\\end{thebibliography}\n")

    def test_skip_units_do_not_enter_the_shape(self):
        # Acknowledgments, an appendix and the reference list are `skip`
        # buckets on the corpus side; they used to enter dispersion, role
        # coupling and section arc as body prose because the sweep read
        # `section_line_ranges`, which carries no bucket.
        body = document([REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
                         SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH])
        plain = docstructure.document_shape(body)
        with_tail = docstructure.document_shape(body.rstrip("\n") + self.SKIP_TAIL)
        self.assertEqual(with_tail["status"], "measured")
        self.assertEqual(with_tail["n_sections"], plain["n_sections"])
        self.assertEqual(with_tail["n_paragraphs"], plain["n_paragraphs"])
        self.assertEqual(with_tail["metrics"], plain["metrics"])
        self.assertEqual([u["label"] for u in docstructure.shape_units(body + self.SKIP_TAIL)],
                         ["Introduction", "Methods", "Results"])
        # the preamble (title block before the first heading) is dropped too
        self.assertEqual(docstructure.shape_units("\\title{T}\n\n" + body)[0]["label"],
                         "Introduction")

    def test_measurable_sections_is_the_document_shape_filter(self):
        units = docstructure.shape_units(document([REPEATED_PARAGRAPH, "Too short."]))
        kept = docstructure.measurable_sections(units)
        # each section holds one substantial and one short paragraph, so none
        # reaches MIN_PARAGRAPHS_PER_SECTION and the document is insufficient
        self.assertEqual(kept, [])
        self.assertEqual(docstructure.document_shape(
            document([REPEATED_PARAGRAPH, "Too short."]))["status"], "insufficient_evidence")

    def _baseline(self, root: Path, values: list[float], percentile: float) -> None:
        threshold = docstructure._quantile(values, percentile)
        (root / docstructure.BASELINE_NAME).write_text(json.dumps({
            "schema": "sci-paper.docstructure-baseline.v2",
            "n_documents": len(values), "strong_percentile": percentile,
            "metrics": {"within_section_similarity": {
                "values": values, "strong_threshold": threshold}},
            "dispersion": {}}), encoding="utf-8")

    def _shape(self, observed: float) -> dict:
        return {"status": "measured", "reason": None, "n_sections": 3,
                "n_paragraphs": 6, "dispersion": {}, "sections": [],
                "metrics": {"within_section_similarity": observed,
                            "cross_section_similarity": None,
                            "section_arc_similarity": None}}

    def test_strong_flag_uses_the_quoted_threshold_rule(self):
        # values [0.1, 0.2, 0.3, 0.4] at p = 0.8: the interpolated quantile the
        # baseline quotes is 0.34, while the add-one rank percentile of 0.32 is
        # (1 + 3) / 5 = 0.8, so the old rank rule flagged a document strong
        # while quoting a threshold its value was below.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._baseline(root, [0.1, 0.2, 0.3, 0.4], 0.8)
            with mock.patch.object(docstructure, "document_shape",
                                   return_value=self._shape(0.32)):
                below = docstructure.document_findings("x", root)
            self.assertEqual([f["rule"] for f in below], [])
            with mock.patch.object(docstructure, "document_shape",
                                   return_value=self._shape(0.35)):
                above = docstructure.document_findings("x", root)
            self.assertEqual([f["rule"] for f in above],
                             ["document-shape:within_section_similarity"])
            finding = above[0]
            self.assertAlmostEqual(finding["reference"]["strong_threshold"], 0.34)
            self.assertGreater(finding["observed"]["value"],
                               finding["reference"]["strong_threshold"])
            self.assertAlmostEqual(finding["normalized_distance"], 0.35 - 0.34)
            self.assertIn("threshold 0.340", finding["message"])

    def test_a_tail_the_reference_cannot_resolve_is_not_strong(self):
        # Four documents place no value beyond a 0.8 quantile (floor 5); a
        # 5% band tail needs 20 (audit B18).
        self.assertEqual([docstructure.tail_floor(p) for p in (0.95, 0.05, 0.9, 0.8)],
                         [20, 20, 10, 5])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for values, expected in (([0.1, 0.2, 0.3, 0.4], ("ordinary", "degraded")),
                                     ([0.01 * i for i in range(20)], ("strong", "measured"))):
                self._baseline(root, values, 0.8)
                with mock.patch.object(docstructure, "document_shape",
                                       return_value=self._shape(0.35)):
                    finding, = docstructure.document_findings("x", root)
                    status = docstructure.docstructure_axis_status("x", root)
                self.assertEqual((finding["strength"], finding["measurement_status"]), expected)
                self.assertEqual(status["status"], expected[1])
            self._baseline(root, [0.1, 0.2, 0.3, 0.4], 0.8)
            with mock.patch.object(docstructure, "document_shape",
                                   return_value=self._shape(0.35)):
                self.assertIn("needs 20", docstructure.docstructure_axis_status("x", root)["reason"])

    def test_a_manifold_without_a_conformal_block_is_degraded_not_scored(self):
        # The in-sample fallback that scored such a baseline went with audit
        # B24, since no calibrate writes one. Hand-built, it reads degraded with
        # a rebuild instruction: no crash, and no finding passed off as scored.
        names = docstructure.DISPERSION_FEATURE_NAMES
        rows = [{name: 1.0 + 0.1 * ((index * (k + 2)) % 7) for k, name in enumerate(names)}
                for index in range(docstructure.MIN_MANIFOLD_DOCUMENTS)]
        baseline = {"schema": "sci-paper.docstructure-baseline.v2", "n_documents": 40,
                    "strong_percentile": 0.95, "metrics": {}, "dispersion": {},
                    "dispersion_manifold": docstructure.fit_dispersion_manifold(rows)}
        self.assertIsNone(docstructure.manifold_operating_point(baseline, rows[0], 6))
        text = document([REPEATED_PARAGRAPH])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / docstructure.BASELINE_NAME).write_text(json.dumps(baseline),
                                                           encoding="utf-8")
            self.assertEqual(docstructure.document_findings(text, root), [])
            status = docstructure.docstructure_axis_status(text, root)
        self.assertEqual(status["status"], "degraded")
        self.assertIn("deai_docstructure --calibrate", status["reason"])


class BlankedSweepTests(unittest.TestCase):
    """Headings and floats are blanked before the paragraph split, as the
    anchoring sweep blanks them, and the CLI measures once (audit B22)."""

    VARIED = [REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH,
              SHORT_PARAGRAPH, LONG_PARAGRAPH, REPEATED_PARAGRAPH]

    def assert_same_shape(self, first: str, second: str) -> None:
        one, two = docstructure.document_shape(first), docstructure.document_shape(second)
        for key in ("n_paragraphs", "metrics", "dispersion"):
            self.assertEqual(one[key], two[key], key)

    def test_a_heading_does_not_fuse_into_the_first_block(self):
        spaced = document(self.VARIED)
        fused = spaced.replace("}\n\n", "}\n")  # no blank line under any heading
        start, _end, block = docstructure.shape_units(fused)[0]["blocks"][0]
        self.assertEqual(start, 2)
        self.assertNotIn("Introduction", block)
        self.assert_same_shape(fused, spaced)

    def test_a_float_does_not_split_a_paragraph(self):
        head, tail = LONG_PARAGRAPH.split("; ", 1)
        figure = ("\\begin{figure}\n\\includegraphics{map}\n\n"
                  "\\caption{The smoothed map behind every count in this section.}\n"
                  "\\end{figure}\n")
        plain = document([REPEATED_PARAGRAPH, head + ";\n" + tail] + self.VARIED[2:])
        with_float = plain.replace(head + ";\n", head + ";\n" + figure)
        blocks = docstructure.shape_units(with_float)[0]["blocks"]
        self.assertEqual(len(blocks), 2)
        start, end, block = blocks[1]
        self.assertEqual(end - start, 1 + figure.count("\n"))
        self.assertNotIn("caption", block)
        self.assert_same_shape(with_float, plain)

    def test_the_cli_measures_the_shape_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            draft.write_text(document(self.VARIED), encoding="utf-8")
            (root / "profiles").mkdir()
            with mock.patch.object(docstructure, "document_shape",
                                   wraps=docstructure.document_shape) as measure, \
                    contextlib.redirect_stdout(io.StringIO()):
                code = docstructure.main([str(draft), "--profile-root", str(root / "profiles")])
        self.assertEqual((code, measure.call_count), (0, 1))


class ConformalEndToEndTests(unittest.TestCase):
    """Calibrate -> findings through the split-conformal and Mondrian paths
    on generated documents (audit B30). The manifold is fit on int(0.6 n)
    documents and needs MIN_MANIFOLD_DOCUMENTS (33) of them, so 55 is the
    smallest corpus that writes a `conformal` block; a length stratum gets a
    manifold of its own only with 33 training and 30 calibration documents in
    it, which 75 documents of one length give."""

    def test_calibrate_then_score_on_the_stratum_and_the_pooled_manifold(self):
        fraction = docstructure.CONFORMAL_TRAIN_FRACTION
        self.assertEqual([int(n * fraction) >= docstructure.MIN_MANIFOLD_DOCUMENTS
                          for n in (54, 55)], [False, True])
        pairs = itertools.permutations((REPEATED_PARAGRAPH, SHORT_PARAGRAPH, LONG_PARAGRAPH), 2)
        combos = itertools.islice(itertools.product(list(pairs), repeat=3), 75)
        corpus = [(f"generated-{index}", document([p for pair in combo for p in pair]))
                  for index, combo in enumerate(combos)]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            conformal = docstructure.calibrate(corpus, root)["conformal"]
            manifold = conformal["manifold"]
            # six paragraphs each: one length, so every document is stratum 0
            self.assertEqual(conformal["strata_edges"], [6.0, 6.0])
            self.assertEqual((manifold["n_train"], len(manifold["calibration"])), (45, 30))
            self.assertEqual(sorted(manifold["stratum"]), ["0"])
            # a uniform document of the calibrated length is scored on the
            # stratum's own manifold; a longer one falls to the pooled one
            for per_section, operating_point, basis in (
                    (2, "split-conformal, stratum manifold", "stratum 0 manifold"),
                    (3, "split-conformal", "pooled")):
                text = "\n\n".join(
                    f"\\section{{{name}}}\n\n" + "\n\n".join([REPEATED_PARAGRAPH] * per_section)
                    for name in ("Introduction", "Methods", "Results")) + "\n"
                found = [f for f in docstructure.document_findings(text, root)
                         if f["rule"] == "document-dispersion-manifold"]
                self.assertEqual(len(found), 1, per_section)
                reference = found[0]["reference"]
                self.assertEqual((reference["operating_point"], reference["calibration_basis"],
                                  reference["n_calibration"]), (operating_point, basis, 30))
                # beyond all 30 calibration papers: the smallest p they allow
                self.assertAlmostEqual(found[0]["observed"]["p_value"], 1 / 31)
                self.assertEqual(docstructure.docstructure_axis_status(text, root)["status"],
                                 "measured")


class FeatureRuntimeTests(unittest.TestCase):
    """`deai_features` without its optional dependencies: unmeasured markers
    and a message, never a ModuleNotFoundError (audit 2026-09-27, B4)."""

    MISSING = (False, "the optional surprisal runtime is not installed (torch)")

    def test_missing_surprisal_runtime_is_an_unmeasured_marker(self):
        with mock.patch.object(deai_features.do, "model_runtime_available",
                               return_value=self.MISSING):
            feats = deai_features.paragraph_features(LONG_PARAGRAPH)
            self.assertEqual(feats["uid_status"], "unmeasured")
            self.assertIn("torch", feats["uid_reason"])
            for name in ("mean_surprisal", "global_uid", "local_uid"):
                self.assertIsNone(feats[name])
            self.assertGreater(feats["word_count"], 0)
            # the model vector cannot be built without those entries
            with self.assertRaises(RuntimeError) as raised:
                deai_features.features_vector(LONG_PARAGRAPH)
            self.assertIn("torch", str(raised.exception))
            with tempfile.TemporaryDirectory() as temporary:
                draft = Path(temporary) / "draft.tex"
                draft.write_text(LONG_PARAGRAPH + "\n", encoding="utf-8")
                out, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = deai_features.main([str(draft), "--profile-root", temporary])
                self.assertEqual(code, 2)
                self.assertIn("surprisal runtime", err.getvalue())
                self.assertEqual(out.getvalue(), "")

    def test_corpus_centroid_without_a_cache_needs_no_numpy(self):
        with tempfile.TemporaryDirectory() as temporary:
            # `numpy: None` makes `import numpy` fail even where it is installed
            with mock.patch.dict(sys.modules, {"numpy": None}):
                self.assertIsNone(deai_features.corpus_centroid(Path(temporary)))


class CliContractTests(unittest.TestCase):
    """`--field` is optional on the read path, required (and existing) for
    `--calibrate`; `--strong-percentile` is a probability (audit B1, B8)."""

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = docstructure.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_read_path_without_a_field_reports_unmeasured(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            draft.write_text(document([REPEATED_PARAGRAPH, SHORT_PARAGRAPH]),
                             encoding="utf-8")
            empty = root / "profiles"
            empty.mkdir()
            code, out, _err = self.run_main([str(draft), "--profile-root", str(empty)])
            self.assertEqual(code, 0)
            self.assertIn("unmeasured", out)
            # two fields: one stderr note, still exit 0 and unmeasured
            (empty / "a").mkdir()
            (empty / "b").mkdir()
            code, out, err = self.run_main([str(draft), "--profile-root", str(empty)])
            self.assertEqual((code, "unmeasured" in out), (0, True))
            self.assertIn("several field profiles", err)

    def test_calibrate_needs_an_existing_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "corpus"
            corpus.mkdir()
            empty = root / "profiles"
            empty.mkdir()
            code, _out, err = self.run_main(
                ["--calibrate", "--corpus-dir", str(corpus), "--profile-root", str(empty)])
            self.assertEqual(code, 2)
            self.assertIn("No field profiles", err)
            code, _out, err = self.run_main(
                ["--calibrate", "--corpus-dir", str(corpus), "--profile-root",
                 str(empty), "--field", "nope"])
            self.assertEqual(code, 2)
            self.assertIn("not found", err)

    def test_strong_percentile_must_be_a_probability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            draft = root / "draft.tex"
            draft.write_text("x\n", encoding="utf-8")
            for value in ("1.5", "1", "0", "-0.1"):
                code, _out, err = self.run_main(
                    [str(draft), "--profile-root", str(root), "--strong-percentile", value])
                self.assertEqual(code, 2, value)
                self.assertIn("--strong-percentile", err)


if __name__ == "__main__":
    unittest.main()
