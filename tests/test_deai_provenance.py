from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import deai_provenance as prov

ANCESTOR = (
    "The weak lensing convergence field encodes the projected mass distribution "
    "along the line of sight to every source galaxy in the survey.\n\n"
    "We estimate the aperture mass statistic by convolving the tangential shear "
    "with a compensated filter of a fixed angular scale.\n\n"
    "The signal to noise map is thresholded at five sigma to identify candidate "
    "mass concentrations across the whole survey footprint."
)


class ProvenanceTests(unittest.TestCase):
    def test_classify_buckets(self):
        self.assertEqual(prov._classify(1.0), "ai_untouched")
        self.assertEqual(prov._classify(0.96), "ai_untouched")
        self.assertEqual(prov._classify(0.80), "lightly_edited")
        self.assertEqual(prov._classify(0.45), "rewritten")
        self.assertEqual(prov._classify(0.10), "author_original")

    def test_identical_is_ai_untouched(self):
        result = prov.document_provenance(ANCESTOR, ANCESTOR)
        self.assertEqual(result["status"], "measured")
        self.assertTrue(all(e["label"] == "ai_untouched" for e in result["ledger"]))
        self.assertEqual(result["summary"]["mean_authorship_depth"], 0.0)
        self.assertEqual(result["summary"]["ai_untouched_fraction"], 1.0)

    def test_disjoint_text_is_author_original(self):
        current = (
            "Galaxy rotation curves flatten at large radii, which motivated the "
            "original dark matter hypothesis in spiral systems decades ago.\n\n"
            "Baryon acoustic oscillations imprint a preferred comoving scale on "
            "the galaxy two point correlation function at low redshift."
        )
        result = prov.document_provenance(current, ANCESTOR)
        self.assertEqual(result["status"], "measured")
        self.assertTrue(all(e["label"] == "author_original" for e in result["ledger"]))
        self.assertEqual(result["summary"]["mean_authorship_depth"], 1.0)

    def test_empty_ancestor_is_unmeasured(self):
        result = prov.document_provenance(ANCESTOR, "")
        self.assertEqual(result["status"], "unmeasured")
        self.assertEqual(result["ledger"], [])

    def test_findings_unmeasured_without_ancestor(self):
        findings, axes = prov.document_findings(ANCESTOR, "draft.tex", None)
        self.assertEqual(findings, [])
        self.assertEqual(axes[0]["status"], "unmeasured")

    def test_findings_flag_ai_untouched_spans(self):
        findings, axes = prov.document_findings(ANCESTOR, "draft.tex", ANCESTOR)
        self.assertEqual(axes[0]["status"], "measured")
        self.assertTrue(findings)
        self.assertTrue(all(f["rule"] == "provenance:ai-untouched" for f in findings))
        # provenance is deterministic, so its confidence is NOT paragraph-capped
        self.assertGreater(findings[0]["confidence"]["value"], 0.5)
        self.assertEqual(findings[0]["layer"], "L4")

    def test_git_missing_ref_returns_none(self):
        # a ref that cannot exist -> honest None, never a guess
        self.assertIsNone(prov.git_file_at(Path(__file__), "no-such-ref-zzz999"))

    def test_findings_report_real_source_lines(self):
        # a paragraph offset from line 1 must report its real source line,
        # not an ordinal (regression: line was the paragraph index + 1).
        doc = ("\\documentclass{article}\n\n"
               "This is a real substantive paragraph with more than twelve prose "
               "words so it qualifies here.")
        findings, _axes = prov.document_findings(doc, "draft.tex", doc)
        self.assertTrue(findings)
        self.assertEqual(findings[0]["location"]["start_line"], 3)
        self.assertIsNotNone(findings[0]["location"]["end_line"])

    def test_git_unreadable_reason_is_distinguished(self):
        # supplied-but-unreadable ref must not be reported as "none supplied".
        reason = "git ref abc123 unreadable or untracked for this file"
        _f, axes = prov.document_findings(ANCESTOR, "draft.tex", None,
                                          no_ancestor_reason=reason)
        self.assertEqual(axes[0]["status"], "unmeasured")
        self.assertEqual(axes[0]["reason"], reason)
        # default (genuinely none supplied) keeps the generic reason and differs
        _f2, axes2 = prov.document_findings(ANCESTOR, "draft.tex", None)
        self.assertIn("no ai-draft ancestor", axes2[0]["reason"].lower())
        self.assertNotEqual(axes2[0]["reason"], reason)


if __name__ == "__main__":
    unittest.main()
