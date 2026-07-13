"""Claim anchoring (L2): a WRITING-QUALITY band, not an AI-discrimination axis.

A sentence is ANCHORED when it carries something checkable: a number, a
citation, an internal reference (\\ref family), mathematics, or an explicit
comparison. "Demonstrates strong performance" with none of these is an
unanchored claim. Fixing an unanchored claim is a genuine scientific
improvement, so unlike surface-style axes there is no evasion incentive.

Measured honestly (EVALUATION.md section 9.6): full-paper generations from a
strong model anchor MORE than the human corpus, so the frontier hypothesis
that under-anchoring is a durable AI tell is REFUTED for that generator
class; this axis flags a quality problem (hedged generality in any draft,
human or hybrid), and its findings must not be read as AI evidence.

Human papers anchor at section-dependent rates (introductions legitimately
anchor less than results), so the reference is SECTION-CLASS conditional:
one observation per document per class (sections of the same class are
averaged, never counted twice - the same anti-pseudoreplication rule as the
document baseline). Detection is a low-tail conformal p per class with a
Bonferroni share alpha/k (k = classes measured in the document), so the
DOCUMENT-level false-flag rate stays <= alpha for exchangeable human papers.
Below the per-class minimum the class is honestly omitted.

Usage:
  python tools/deai_anchoring.py --field wgl --calibrate --corpus-dir style-corpus/wgl
  python tools/deai_anchoring.py <file.tex> --field wgl
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_docstructure as ds  # noqa: E402  because sibling imports resolve only after the sys.path insert above
import deai_feedback as feedback  # noqa: E402  same sys.path reason
import deai_metrics as metrics  # noqa: E402  same sys.path reason
import extract_style as es  # noqa: E402  same sys.path reason

BASELINE_NAME = "anchoring_baseline.json"
ANCHORING_ALPHA = 0.05
MIN_CLASS_DOCUMENTS = 30      # below this a class band is honestly omitted
MIN_SENTENCE_WORDS = 5        # fragments carry no claim to anchor
MIN_SECTION_SENTENCES = 3     # a 1-2 sentence section is not a rate estimate

_REF_RE = re.compile(r"\\(?:ref|eqref|autoref|cref|Cref|pageref)\{")
_MATH_RE = ds._MATH_MARKER_RE
_CITE_RE = es.RE_TEX_CITE
_NUMBER_RE = re.compile(r"\d")
_COMPARISON_MARKERS = (" than ", "compared to", "compared with",
                       "relative to", "in contrast", "versus ")

# section-title keyword -> class; first match wins, unmatched -> "other"
SECTION_CLASSES = (
    ("introduction", "intro"),
    ("conclusion", "conclusions"), ("summary", "conclusions"),
    ("discussion", "discussion"),
    ("result", "results"), ("measurement", "results"),
    ("constraint", "results"),
    ("data", "methods"), ("method", "methods"), ("model", "methods"),
    ("simulat", "methods"), ("analysis", "methods"), ("observ", "methods"),
    ("appendix", "other"), ("acknowledg", "other"),
)
STRONG_CLASSES = {"methods", "results"}  # unanchored claims here matter most


def classify_section(label: str) -> str:
    lowered = label.lower()
    for keyword, cls in SECTION_CLASSES:
        if keyword in lowered:
            return cls
    return "other"


def sentence_is_anchored(source_sentence: str) -> bool:
    if (_CITE_RE.search(source_sentence) or _REF_RE.search(source_sentence)
            or _MATH_RE.search(source_sentence)):
        return True
    plain = es.latex_to_plain(source_sentence)
    # digits are checked on the PLAIN text so citation keys and labels
    # (already stripped or replaced) cannot count as numbers
    if _NUMBER_RE.search(plain):
        return True
    lowered = f" {plain.lower()} "
    return any(marker in lowered for marker in _COMPARISON_MARKERS)


def section_anchor_rate(section_source: str) -> tuple[float, int] | None:
    """(anchored fraction, n sentences) of one section, or None if too short."""
    sentences = [s for s in es.sentences(section_source)
                 if len(es.words(es.latex_to_plain(s))) >= MIN_SENTENCE_WORDS]
    if len(sentences) < MIN_SECTION_SENTENCES:
        return None
    anchored = sum(sentence_is_anchored(s) for s in sentences)
    return anchored / len(sentences), len(sentences)


def document_anchoring(text: str) -> dict[str, Any]:
    """Per-class anchor rates for one document (one value per class)."""
    lines = text.splitlines()
    per_class: dict[str, list[float]] = {}
    section_rows = []
    for start, end, label in metrics.section_line_ranges(text):
        if label == "(preamble)":
            continue
        segment = "\n".join(lines[start - 1:end])
        measured = section_anchor_rate(segment)
        if measured is None:
            continue
        rate, n_sentences = measured
        cls = classify_section(label)
        per_class.setdefault(cls, []).append(rate)
        section_rows.append({"label": label, "class": cls, "line": start,
                             "rate": rate, "n_sentences": n_sentences})
    if not section_rows:
        return {"status": "unmeasured", "classes": {}, "sections": []}
    return {"status": "measured",
            "classes": {cls: statistics.mean(rates)
                        for cls, rates in per_class.items()},
            "sections": section_rows}


def calibrate(documents: Iterable[tuple[str, str] | Path],
              field_profile_dir: Path) -> dict[str, Any]:
    """Fit the section-class conditional human anchoring reference."""
    class_values: dict[str, list[float]] = {}
    n_documents = 0
    for item in documents:
        if isinstance(item, Path):
            text = item.read_text(encoding="utf-8", errors="replace")
        else:
            _, text = item
        result = document_anchoring(text)
        if result["status"] != "measured":
            continue
        n_documents += 1
        for cls, value in result["classes"].items():
            class_values.setdefault(cls, []).append(value)
    if n_documents < MIN_CLASS_DOCUMENTS:
        raise ValueError(
            f"anchoring calibration needs at least {MIN_CLASS_DOCUMENTS} "
            f"measurable documents, got {n_documents}")
    baseline: dict[str, Any] = {
        "schema": "sci-paper.anchoring-baseline.v1",
        "n_documents": n_documents,
        "alpha": ANCHORING_ALPHA,
        "min_class_documents": MIN_CLASS_DOCUMENTS,
        "classes": {},
    }
    for cls, values in class_values.items():
        if len(values) < MIN_CLASS_DOCUMENTS:
            continue  # honestly omitted; small classes give no band
        baseline["classes"][cls] = {
            "values": sorted(values),
            "n": len(values),
            "median": statistics.median(values),
        }
    output = field_profile_dir / BASELINE_NAME
    output.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline


def load_baseline(field_profile_dir: Path | None) -> dict[str, Any] | None:
    if field_profile_dir is None:
        return None
    path = field_profile_dir / BASELINE_NAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def anchoring_axis_status(text: str, field_profile_dir: Path | None
                          ) -> dict[str, Any]:
    result = document_anchoring(text)
    if result["status"] != "measured":
        return feedback.axis_status("L2.claim_anchoring", "unmeasured",
                                    reason="no section long enough to measure",
                                    detector="deai_anchoring")
    if load_baseline(field_profile_dir) is None:
        return feedback.axis_status("L2.claim_anchoring", "unmeasured",
                                    reason=f"{BASELINE_NAME} is unavailable",
                                    detector="deai_anchoring")
    return feedback.axis_status("L2.claim_anchoring", "measured",
                                detector="deai_anchoring")


def anchoring_findings(text: str, field_profile_dir: Path | None,
                       path: str | Path | None = None) -> list[dict[str, Any]]:
    baseline = load_baseline(field_profile_dir)
    result = document_anchoring(text)
    if baseline is None or result["status"] != "measured":
        return []
    alpha = float(baseline.get("alpha", ANCHORING_ALPHA))
    # Bonferroni share: a document measures up to k classes; testing each at
    # alpha would give a document-level union false-flag rate near k*alpha
    # (measured 0.170 at alpha=0.05 before this correction), so each class
    # tests at alpha/k and the document-level rate stays <= alpha.
    measured_classes = [cls for cls in result["classes"]
                        if baseline.get("classes", {}).get(cls)]
    if not measured_classes:
        return []
    class_alpha = alpha / len(measured_classes)
    findings = []
    for cls, observed in result["classes"].items():
        reference = baseline.get("classes", {}).get(cls)
        if not reference:
            continue
        values = reference["values"]
        # low-tail conformal p: rank of the observed rate among human rates
        p_value = (1 + sum(v <= observed for v in values)) / (len(values) + 1)
        if p_value > class_alpha:
            continue
        sections = [row for row in result["sections"] if row["class"] == cls]
        worst = min(sections, key=lambda row: row["rate"])
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2",
            rule=f"claim-anchoring:{cls}",
            scope="section", line=worst["line"], section=worst["label"],
            path=path, detector="deai_anchoring",
            detector_version="sci-paper.anchoring-baseline.v1",
            calibration_asset=BASELINE_NAME,
            measurement_status="measured",
            strength="strong" if cls in STRONG_CLASSES else "ordinary",
            observed={"anchored_fraction": observed,
                      "conformal_p": p_value,
                      "sections": [{"label": row["label"],
                                    "rate": row["rate"]}
                                   for row in sections]},
            reference={"operating_point": "conformal low tail, Bonferroni",
                       "alpha_document": alpha,
                       "alpha_class": class_alpha,
                       "n_classes_tested": len(measured_classes),
                       "n_calibration": reference["n"],
                       "human_median": reference["median"],
                       "provenance": BASELINE_NAME},
            normalized_distance=class_alpha - p_value,
            confidence={"value": min(1.0, reference["n"] / 100.0),
                        "basis": (f"conformal p against {reference['n']} human "
                                  f"papers' {cls}-class anchor rates; "
                                  f"P(false flag) <= {alpha:g} finite-sample")},
            message=(f"Only {observed:.0%} of {cls} sentences carry a "
                     f"checkable anchor (a number, citation, internal "
                     f"reference, equation, or comparison); the human median "
                     f"for {cls} sections is {reference['median']:.0%} and "
                     f"this document sits below the human low tail "
                     f"(conformal p = {p_value:.4f}). Unanchored claims read "
                     f"as unfalsifiable generality. This is a measured "
                     f"deviation, not an AI verdict."),
            action=("Tie each claim to something checkable: the measured "
                    "number, the figure or table that shows it, the citation "
                    "that established it, or the explicit comparison. Delete "
                    "claims that have nothing to anchor to."),
            evidence=[cls, round(observed, 6)],
        ))
    return findings


def _paper_documents(corpus_dir: Path) -> list[tuple[str, str]]:
    return ds._paper_documents(corpus_dir)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--field", required=True)
    parser.add_argument("--profile-root", type=Path,
                        default=ds.DEFAULT_PROFILE_ROOT)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--corpus-dir", type=Path)
    args = parser.parse_args(argv)
    field_dir = args.profile_root / args.field
    if args.calibrate:
        if args.corpus_dir is None or not args.corpus_dir.exists():
            print("[deai_anchoring] --calibrate requires --corpus-dir",
                  file=sys.stderr)
            return 2
        try:
            baseline = calibrate(_paper_documents(args.corpus_dir), field_dir)
        except ValueError as error:
            print(f"[deai_anchoring] {error}", file=sys.stderr)
            return 2
        classes = {cls: ref["n"] for cls, ref in baseline["classes"].items()}
        print(f"[deai_anchoring] baseline written from "
              f"{baseline['n_documents']} documents; classes {classes}")
        return 0
    if args.file is None or not args.file.exists():
        print(f"[deai_anchoring] file not found: {args.file}", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    report = feedback.build_report(
        path=args.file,
        findings=anchoring_findings(text, field_dir, args.file),
        axes=[anchoring_axis_status(text, field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
