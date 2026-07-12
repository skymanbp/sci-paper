"""Document-level paragraph and section shape feedback (L2).

This tool measures repeated rhetorical geometry, not repeated subject matter.
Calibration treats each complete source document as one observation to avoid
paragraph-level pseudoreplication.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as features  # noqa: E402  sibling import after path setup
import deai_feedback as feedback  # noqa: E402  shared finding contract
import deai_metrics as metrics  # noqa: E402  canonical section/paragraph ranges
import deai_structure as structure  # noqa: E402  sentence template features
import extract_style as es  # noqa: E402  canonical LaTeX cleanup/tokenizer

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
BASELINE_NAME = "docstructure_baseline.json"
MIN_WORDS = 30
MIN_SECTIONS = 3
MIN_PARAGRAPHS_PER_SECTION = 2
METRIC_NAMES = (
    "within_section_similarity",
    "cross_section_similarity",
    "section_arc_similarity",
)


def _shape_vector(text: str) -> list[float]:
    plain = es.latex_to_plain(text)
    dist = features.distributional_features(plain)
    syntactic = structure.paragraph_structure(text)
    return [
        dist["n_sentences"] / 8.0,
        dist["mean_sent_len"] / 40.0,
        dist["sent_len_cv"],
        dist["opens_connective"],
        dist["equivocal_rate"] / 5.0,
        dist["paren_rate"] / 5.0,
        dist["semicolon_rate"] / 3.0,
        dist["comma_rate"] / 10.0,
        syntactic["template_score"] / 3.0,
    ]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _mean_vector(vectors: list[list[float]]) -> list[float]:
    return [statistics.mean(values) for values in zip(*vectors)]


def _pairwise_similarity(vectors: list[list[float]]) -> float | None:
    values = [
        _cosine(vectors[left], vectors[right])
        for left in range(len(vectors))
        for right in range(left + 1, len(vectors))
    ]
    return statistics.mean(values) if values else None


def document_shape(text: str) -> dict[str, Any]:
    """Measure document shape or return an explicit insufficient-evidence state."""
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    for start, end, label in metrics.section_line_ranges(text):
        if label == "(preamble)":
            continue
        segment = "\n".join(lines[start - 1:end])
        paragraphs = []
        for p_start, p_end, block in metrics.paragraph_line_ranges(segment, start):
            if len(es.words(es.latex_to_plain(block))) < MIN_WORDS:
                continue
            paragraphs.append({
                "start_line": p_start,
                "end_line": p_end,
                "vector": _shape_vector(block),
            })
        if len(paragraphs) >= MIN_PARAGRAPHS_PER_SECTION:
            sections.append({"label": label, "start_line": start,
                             "end_line": end, "paragraphs": paragraphs})
    if len(sections) < MIN_SECTIONS:
        return {
            "status": "insufficient_evidence",
            "reason": (f"need at least {MIN_SECTIONS} sections with at least "
                       f"{MIN_PARAGRAPHS_PER_SECTION} substantial paragraphs each"),
            "n_sections": len(sections),
            "metrics": {},
        }

    within = [
        _pairwise_similarity([paragraph["vector"] for paragraph in section["paragraphs"]])
        for section in sections
    ]
    within = [value for value in within if value is not None]
    centroids = [
        _mean_vector([paragraph["vector"] for paragraph in section["paragraphs"]])
        for section in sections
    ]
    arcs = []
    for section in sections:
        first = section["paragraphs"][0]["vector"]
        last = section["paragraphs"][-1]["vector"]
        arcs.append([end - begin for begin, end in zip(first, last)])
    return {
        "status": "measured",
        "reason": None,
        "n_sections": len(sections),
        "n_paragraphs": sum(len(section["paragraphs"]) for section in sections),
        "metrics": {
            "within_section_similarity": statistics.mean(within),
            "cross_section_similarity": _pairwise_similarity(centroids),
            "section_arc_similarity": _pairwise_similarity(arcs),
        },
        "sections": sections,
    }


def _percentile(values: list[float], observed: float) -> float:
    """One-sided empirical percentile with add-one smoothing."""
    return (1 + sum(value <= observed for value in values)) / (len(values) + 1)


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile needs at least one value")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def _bootstrap_quantile_ci(values: list[float], probability: float,
                           iterations: int = 500) -> list[float] | None:
    """Deterministic balanced resampling CI for a corpus quantile."""
    if len(values) < 3:
        return None
    estimates = []
    n = len(values)
    for iteration in range(iterations):
        sample = [values[(iteration * 17 + index * 31) % n] for index in range(n)]
        estimates.append(_quantile(sample, probability))
    return [_quantile(estimates, 0.025), _quantile(estimates, 0.975)]


def _leave_one_out_flag_rate(values: list[float], probability: float) -> float | None:
    if len(values) < 3:
        return None
    flags = 0
    for index, value in enumerate(values):
        others = values[:index] + values[index + 1:]
        flags += value > _quantile(others, probability)
    return flags / len(values)


def calibrate(documents: Iterable[Path], field_profile_dir: Path,
              strong_percentile: float = 0.95) -> dict[str, Any]:
    records = []
    for path in documents:
        text = path.read_text(encoding="utf-8", errors="replace")
        result = document_shape(text)
        if result["status"] != "measured":
            continue
        records.append({"source": path.name, "metrics": result["metrics"]})
    if len(records) < 3:
        raise ValueError("document-structure calibration needs at least 3 measurable complete documents")
    baseline: dict[str, Any] = {
        "schema": "sci-paper.docstructure-baseline.v1",
        "n_documents": len(records),
        "strong_percentile": strong_percentile,
        "documents": [record["source"] for record in records],
        "metrics": {},
    }
    for name in METRIC_NAMES:
        values = [float(record["metrics"][name]) for record in records
                  if record["metrics"].get(name) is not None]
        baseline["metrics"][name] = {
            "values": values,
            "strong_threshold": _quantile(values, strong_percentile),
            "bootstrap_95_ci": _bootstrap_quantile_ci(values, strong_percentile),
            "leave_one_document_out_flag_rate": _leave_one_out_flag_rate(
                values, strong_percentile),
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


def docstructure_axis_status(text: str, field_profile_dir: Path | None
                            ) -> dict[str, Any]:
    shape = document_shape(text)
    if shape["status"] != "measured":
        return feedback.axis_status("L2.document_structure", "unmeasured",
                                    reason=shape["reason"],
                                    detector="deai_docstructure")
    if load_baseline(field_profile_dir) is None:
        return feedback.axis_status(
            "L2.document_structure", "unmeasured",
            reason="docstructure_baseline.json is unavailable",
            detector="deai_docstructure",
        )
    return feedback.axis_status("L2.document_structure", "measured",
                                detector="deai_docstructure")


def document_findings(text: str, field_profile_dir: Path | None,
                      path: str | Path | None = None) -> list[dict[str, Any]]:
    shape = document_shape(text)
    baseline = load_baseline(field_profile_dir)
    if shape["status"] != "measured" or baseline is None:
        return []
    findings = []
    section_label = "(document)"
    for metric_name in METRIC_NAMES:
        observed = shape["metrics"].get(metric_name)
        reference = baseline.get("metrics", {}).get(metric_name, {})
        values = reference.get("values", [])
        if observed is None or not values:
            continue
        percentile = _percentile(values, float(observed))
        operating_point = float(baseline.get("strong_percentile", 0.95))
        if percentile < operating_point:
            continue
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2", rule=f"document-shape:{metric_name}",
            scope="document", line=1, section=section_label, path=path,
            detector="deai_docstructure", measurement_status="measured",
            strength="strong", strong_advisory=True,
            observed={"value": observed, "empirical_percentile": percentile,
                      "n_sections": shape["n_sections"],
                      "n_paragraphs": shape["n_paragraphs"]},
            reference={"n_documents": baseline["n_documents"],
                       "strong_percentile": operating_point,
                       "strong_threshold": reference.get("strong_threshold"),
                       "bootstrap_95_ci": reference.get("bootstrap_95_ci"),
                       "leave_one_document_out_flag_rate": reference.get(
                           "leave_one_document_out_flag_rate"),
                       "provenance": BASELINE_NAME},
            normalized_distance=percentile - operating_point,
            confidence={"value": min(1.0, baseline["n_documents"] / 30.0),
                        "basis": f"{baseline['n_documents']} complete reference documents"},
            message=(f"Document-level {metric_name.replace('_', ' ')} is "
                     f"{observed:.3f}, at empirical percentile {percentile:.3f} "
                     "of the complete-document reference."),
            action=("Inspect repeated paragraph and section shapes; vary only "
                    "needless rhetorical symmetry while preserving logical organization."),
            evidence=[metric_name, round(float(observed), 8)],
        ))
    return findings


def _documents(corpus_dir: Path) -> list[Path]:
    return sorted(path for path in corpus_dir.rglob("*")
                  if path.is_file() and path.suffix.lower() in {".tex", ".md"})


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--field", required=True)
    parser.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--corpus-dir", type=Path,
                        help="directory of complete human .tex/.md source documents")
    parser.add_argument("--strong-percentile", type=float, default=0.95)
    args = parser.parse_args(argv)
    field_dir = args.profile_root / args.field
    if args.calibrate:
        if args.corpus_dir is None or not args.corpus_dir.exists():
            print("[deai_docstructure] --calibrate requires --corpus-dir", file=sys.stderr)
            return 2
        try:
            baseline = calibrate(_documents(args.corpus_dir), field_dir,
                                 args.strong_percentile)
        except ValueError as error:
            print(f"[deai_docstructure] {error}", file=sys.stderr)
            return 2
        print(f"[deai_docstructure] baseline written from {baseline['n_documents']} complete documents")
        return 0
    if args.file is None or not args.file.exists():
        print(f"[deai_docstructure] file not found: {args.file}", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    report = feedback.build_report(
        path=args.file,
        findings=document_findings(text, field_dir, args.file),
        axes=[docstructure_axis_status(text, field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
