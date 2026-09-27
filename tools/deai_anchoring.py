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
Below the per-class minimum the class is honestly omitted. A conformal p is
never smaller than 1/(n+1), so a class whose n cannot reach its share
alpha/k can never flag: such a class is skipped and the axis reported
`degraded`, never `measured` with nothing to say.

Usage:
  python tools/deai_anchoring.py --field wgl --calibrate --corpus-dir style-corpus/wgl
  python tools/deai_anchoring.py <file.tex> --field wgl
"""

from __future__ import annotations

import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_docstructure as ds  # noqa: E402  because sibling imports resolve only after the sys.path insert above
import deai_feedback as feedback  # noqa: E402  same sys.path reason
import deai_reference as reference  # noqa: E402 because sibling tools are importable only after the sys.path insert above
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
# The reference list, blanked before the sentence scan (see `document_anchoring`).
# `deai_reference` blanks headings and floats and holds no bibliography
# pattern; this one is local so that module stays untouched.
_BIBLIOGRAPHY_RE = re.compile(
    r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}"
    r"|\\bibliography(?:style)?\s*\{[^}]*\}", re.DOTALL)

# The shared bucket (`extract_sections.classify_section`, inherited by a
# subsection as the corpus inherits it) folded onto this axis's coarser
# classes; any other bucket is "other". Until 2026-09-27 the module matched
# titles against a third keyword table, which disagreed with the curated one
# where the curation is deliberate: `Shear measurement`, which that table
# leaves `unknown` because the word names no role here, read as results;
# `Comparison with simulations` read as methods; and a topic-titled subsection
# under Methods read as other.
CLASS_OF_BUCKET = {"intro": "intro", "method": "methods", "data": "methods",
                   "results": "results", "discussion": "discussion",
                   "conclusion": "conclusions"}
STRONG_CLASSES = {"methods", "results"}  # unanchored claims here matter most


def section_class(bucket: str) -> str:
    return CLASS_OF_BUCKET.get(bucket, "other")


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
    """Per-class anchor rates for one document (one value per class).

    The sweep is the one every per-bucket axis reads
    (`deai_metrics.section_units`): the preamble and every `skip` unit
    (acknowledgements, appendices, the reference list) are dropped, and in
    each remaining unit the headings and floats are blanked by
    `deai_reference.without_headings` and the bibliography by the local
    pattern above, line count preserved. Until 2026-09-27 the sentence scan
    ran on the raw LaTeX of `section_line_ranges`: a heading fused with the
    first sentence below it, and a `thebibliography` block under the last
    section glued to its final sentence and anchored it with every year in
    the reference list (a Conclusions rate of 0.0 read as 0.2). An anchoring
    baseline built before the change must be rebuilt: its rates were measured
    on the raw text. The class is the unit's shared bucket (`section_class`).
    """
    lines = text.splitlines()
    per_class: dict[str, list[float]] = {}
    section_rows = []
    for start, end, label, bucket in metrics.section_units(text):
        if bucket in (metrics.PREAMBLE_BUCKET, "skip"):
            continue
        segment = es.blank_preserving(
            reference.without_headings("\n".join(lines[start - 1:end])),
            _BIBLIOGRAPHY_RE)
        measured = section_anchor_rate(segment)
        if measured is None:
            continue
        rate, n_sentences = measured
        cls = section_class(bucket)
        per_class.setdefault(cls, []).append(rate)
        section_rows.append({"label": label, "class": cls, "line": start,
                             "rate": rate, "n_sentences": n_sentences})
    if not section_rows:
        return {"status": "unmeasured", "classes": {}, "sections": []}
    return {"status": "measured",
            "classes": {cls: statistics.mean(rates)
                        for cls, rates in per_class.items()},
            "sections": section_rows}


def min_class_documents_for_share(alpha: float, n_classes: int) -> int:
    """The smallest class n whose conformal floor 1/(n+1) fits alpha/k."""
    return max(0, math.ceil(n_classes / alpha - 1))


def calibrate(documents: Iterable[tuple[str, str] | Path],
              field_profile_dir: Path) -> dict[str, Any]:
    """Fit the section-class conditional human anchoring reference.

    `underpowered_classes` lists every retained class whose n is below the
    floor for the Bonferroni share when a document measures ALL retained
    classes (the worst case, k = the number of classes in this baseline):
    such a class can never produce a finding, and detection reports the axis
    `degraded` whenever a document measures one. The CLI prints the list as a
    warning; MIN_CLASS_DOCUMENTS alone (30) supports only k = 1 at alpha 0.05.
    """
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
    floor = min_class_documents_for_share(ANCHORING_ALPHA, len(baseline["classes"]))
    baseline["min_class_documents_for_share"] = floor
    baseline["underpowered_classes"] = {
        cls: entry["n"] for cls, entry in baseline["classes"].items()
        if entry["n"] < floor}
    output = field_profile_dir / BASELINE_NAME
    output.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline


load_baseline = reference.baseline_loader(BASELINE_NAME)


def class_tests(baseline: dict[str, Any], result: dict[str, Any]
                ) -> dict[str, Any]:
    """Which of a document's classes the baseline can test, and at what alpha.

    `measured` are the document's classes that have a reference; the
    Bonferroni share is alpha over their count. A class whose reference is
    too small for that share -- its conformal floor 1/(n+1) exceeds alpha/k,
    so no observed rate could ever flag it -- goes to `underpowered` and is
    not tested. The share is NOT re-spread over the remaining classes: testing
    fewer classes at the same per-class alpha keeps the document-level rate
    at or below alpha, and re-spreading would make which classes are tested
    depend on the order they were dropped in. With n = 30 per class (the
    retention minimum) and two classes measured, 1/31 = 0.032 > 0.025: every
    finding was impossible and the axis still said `measured`.
    """
    alpha = float(baseline.get("alpha", ANCHORING_ALPHA))
    references = baseline.get("classes", {})
    measured = [cls for cls in result["classes"] if references.get(cls)]
    class_alpha = alpha / len(measured) if measured else alpha
    underpowered = [cls for cls in measured
                    if 1.0 / (int(references[cls]["n"]) + 1) > class_alpha]
    return {"alpha": alpha, "class_alpha": class_alpha, "measured": measured,
            "underpowered": underpowered,
            "testable": [cls for cls in measured if cls not in underpowered]}


def anchoring_axis_status(text: str, field_profile_dir: Path | None
                          ) -> dict[str, Any]:
    result = document_anchoring(text)
    if result["status"] != "measured":
        return feedback.axis_status("L2.claim_anchoring", "unmeasured",
                                    reason="no section long enough to measure",
                                    detector="deai_anchoring")
    baseline = load_baseline(field_profile_dir)
    if baseline is None:
        return feedback.axis_status("L2.claim_anchoring", "unmeasured",
                                    reason=f"{BASELINE_NAME} is unavailable",
                                    detector="deai_anchoring")
    tests = class_tests(baseline, result)
    if not tests["measured"]:
        return feedback.axis_status(
            "L2.claim_anchoring", "unmeasured",
            reason="no measured section class has a calibrated reference",
            detector="deai_anchoring")
    if tests["underpowered"]:
        n_classes = len(tests["measured"])
        return feedback.axis_status(
            "L2.claim_anchoring", "degraded",
            reason=(f"class(es) {', '.join(tests['underpowered'])} hold too few "
                    f"calibration papers for the Bonferroni share alpha/"
                    f"{n_classes} = {tests['class_alpha']:.4f} (the conformal p "
                    "cannot go below 1/(n+1)); they were skipped, not tested"),
            detector="deai_anchoring")
    return feedback.axis_status("L2.claim_anchoring", "measured",
                                detector="deai_anchoring")


def anchoring_findings(text: str, field_profile_dir: Path | None,
                       path: str | Path | None = None) -> list[dict[str, Any]]:
    baseline = load_baseline(field_profile_dir)
    result = document_anchoring(text)
    if baseline is None or result["status"] != "measured":
        return []
    # Bonferroni share: a document measures up to k classes; testing each at
    # alpha would give a document-level union false-flag rate near k*alpha
    # (measured 0.170 at alpha=0.05 before this correction), so each class
    # tests at alpha/k and the document-level rate stays <= alpha.
    tests = class_tests(baseline, result)
    alpha, class_alpha = tests["alpha"], tests["class_alpha"]
    findings = []
    for cls in tests["testable"]:
        observed = result["classes"][cls]
        class_reference = baseline["classes"][cls]
        values = class_reference["values"]
        # low-tail conformal p: rank of the observed rate among human rates
        p_value = (1 + sum(v <= observed for v in values)) / (len(values) + 1)
        if p_value > class_alpha:
            continue
        sections = [row for row in result["sections"] if row["class"] == cls]
        worst = min(sections, key=lambda row: row["rate"])
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2",
            rule=f"claim-anchoring:{cls}",
            scope="section", calibration_unit="section",
            line=worst["line"], section=worst["label"],
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
                       "n_classes_tested": len(tests["measured"]),
                       "n_calibration": class_reference["n"],
                       "human_median": class_reference["median"],
                       "provenance": BASELINE_NAME},
            normalized_distance=class_alpha - p_value,
            confidence={"value": min(1.0, class_reference["n"] / 100.0),
                        "basis": (f"conformal p against {class_reference['n']} "
                                  f"human papers' {cls}-class anchor rates; "
                                  f"P(false flag) <= {alpha:g} finite-sample")},
            message=(f"Only {observed:.0%} of {cls} sentences carry a "
                     f"checkable anchor (a number, citation, internal "
                     f"reference, equation, or comparison); the human median "
                     f"for {cls} sections is {class_reference['median']:.0%} and "
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
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__)
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--corpus-dir", type=Path)
    args = parser.parse_args(argv)
    if args.calibrate:
        if args.corpus_dir is None or not args.corpus_dir.exists():
            print("[deai_anchoring] --calibrate requires --corpus-dir",
                  file=sys.stderr)
            return 2
        # The baseline is written INTO the profile, so calibration needs a
        # field that exists; the read path below runs without one.
        try:
            field = cli_common.resolve_field(
                args.field, args.profile_root, tool="deai_anchoring",
                empty_hint="--calibrate needs an existing style-profile/<field>/ directory.")
        except SystemExit as error:
            print(error, file=sys.stderr)
            return 2
        try:
            baseline = calibrate(_paper_documents(args.corpus_dir),
                                 args.profile_root / field)
        except ValueError as error:
            print(f"[deai_anchoring] {error}", file=sys.stderr)
            return 2
        classes = {cls: ref["n"] for cls, ref in baseline["classes"].items()}
        print(f"[deai_anchoring] baseline written from "
              f"{baseline['n_documents']} documents; classes {classes}")
        if baseline["underpowered_classes"]:
            print(f"[deai_anchoring] warning: classes "
                  f"{baseline['underpowered_classes']} hold fewer than "
                  f"{baseline['min_class_documents_for_share']} documents, the "
                  f"floor for the Bonferroni share alpha/{len(classes)} at alpha "
                  f"{baseline['alpha']:g}; a document measuring them will report "
                  "the axis degraded and those classes cannot flag",
                  file=sys.stderr)
        return 0
    if args.file is None or not args.file.exists():
        print(f"[deai_anchoring] file not found: {args.file}", file=sys.stderr)
        return 2
    field_dir = cli_common.optional_field_dir(args, tool="deai_anchoring")
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
