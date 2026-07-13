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

# Model-free per-paragraph features whose cross-paragraph DISPERSION is the
# document-scale, confound-orthogonal AI signal (docs/DEAI_ARCHITECTURE_ROADMAP.md).
# Each feature is compared against its OWN human dispersion distribution during
# calibration, so no magic-constant scaling or cross-feature z-scoring is needed.
# Surprisal and embedding dispersion (GPT-2-large, all-MiniLM) are added by the
# cloud calibration path; this model-free subset calibrates locally with no GPU.
DISPERSION_FEATURE_NAMES = (
    "n_sentences", "mean_sent_len", "sent_len_cv", "sent_len_stdev",
    "word_count", "opens_connective", "equivocal_rate", "paren_rate",
    "semicolon_rate", "comma_rate", "template_score",
)
DISPERSION_STAT = "std"          # primary dispersion statistic used for detection
# Human documents occupy a BAND of cross-paragraph dispersion. Both departures
# are measured deviations: below the low tail = over-uniform (natural AI
# drafting); above the high tail = over-dispersed (measured on text written to
# force raggedness, which overshoots the human band). Held-out validation at
# n=195 human papers: one-sided low-tail scoring is at chance against a
# deliberate shape adversary, while two-sided band distance recovers AUC 0.80.
DISPERSION_LOW_PERCENTILE = 0.05
DISPERSION_HIGH_PERCENTILE = 0.95


def _paragraph_modelfree(text: str) -> list[float]:
    """Raw model-free per-paragraph feature vector (no GPU, no magic constants)."""
    plain = es.latex_to_plain(text)
    dist = features.distributional_features(plain)
    syntactic = structure.paragraph_structure(text)
    values = [dist[name] for name in DISPERSION_FEATURE_NAMES[:-1]]
    values.append(float(syntactic["template_score"]))
    return values


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
                "modelfree": _paragraph_modelfree(block),
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
    # Cross-paragraph dispersion over the whole document, in reading order: the
    # confound-orthogonal document-scale signal. Low dispersion = over-uniform
    # (AI-drafted); each feature is compared to its own human distribution later.
    ordered_vectors = [
        paragraph["modelfree"]
        for section in sections for paragraph in section["paragraphs"]
    ]
    dispersion = features.cross_paragraph_dispersion(
        ordered_vectors, list(DISPERSION_FEATURE_NAMES))
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
        "dispersion": dispersion,
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


def _leave_one_document_out_low_flag_rate(values: list[float],
                                          probability: float) -> float | None:
    """LOO false-flag rate for a LOW-tail operating point (over-uniformity).

    A held-out human document flags when its dispersion falls BELOW the low
    quantile of the others; a well-behaved reference keeps this near the
    nominal percentile, so a large value warns that the threshold is unstable.
    """
    if len(values) < 3:
        return None
    flags = 0
    for index, value in enumerate(values):
        others = values[:index] + values[index + 1:]
        flags += value < _quantile(others, probability)
    return flags / len(values)


def calibrate(documents: Iterable[tuple[str, str] | Path], field_profile_dir: Path,
              strong_percentile: float = 0.95) -> dict[str, Any]:
    """Build the document baseline. Each item is one complete document, given as
    a ``(name, text)`` pair or a ``Path`` (read as one document). Concatenate a
    multi-file paper into one item before calling this — never pass fragments."""
    records = []
    for item in documents:
        if isinstance(item, Path):
            name, text = item.name, item.read_text(encoding="utf-8", errors="replace")
        else:
            name, text = item
        result = document_shape(text)
        if result["status"] != "measured":
            continue
        records.append({"source": name, "metrics": result["metrics"],
                        "dispersion": result.get("dispersion", {})})
    if len(records) < 3:
        raise ValueError("document-structure calibration needs at least 3 measurable complete documents")
    baseline: dict[str, Any] = {
        "schema": "sci-paper.docstructure-baseline.v2",
        "n_documents": len(records),
        "strong_percentile": strong_percentile,
        "dispersion_low_percentile": DISPERSION_LOW_PERCENTILE,
        "dispersion_high_percentile": DISPERSION_HIGH_PERCENTILE,
        "dispersion_stat": DISPERSION_STAT,
        "documents": [record["source"] for record in records],
        "metrics": {},
        "dispersion": {},
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
    # Per-feature human dispersion BAND. Detection fires on either departure:
    # below the low tail (over-uniform) or above the high tail (over-dispersed).
    for name in DISPERSION_FEATURE_NAMES:
        values = [float(record["dispersion"][name][DISPERSION_STAT])
                  for record in records
                  if record.get("dispersion", {}).get(name, {}).get(DISPERSION_STAT)
                  is not None]
        if len(values) < 3:
            continue
        baseline["dispersion"][name] = {
            "values": values,
            "low_threshold": _quantile(values, DISPERSION_LOW_PERCENTILE),
            "high_threshold": _quantile(values, DISPERSION_HIGH_PERCENTILE),
            "bootstrap_95_ci": _bootstrap_quantile_ci(values, DISPERSION_LOW_PERCENTILE),
            "bootstrap_95_ci_high": _bootstrap_quantile_ci(
                values, DISPERSION_HIGH_PERCENTILE),
            "leave_one_document_out_flag_rate": _leave_one_document_out_low_flag_rate(
                values, DISPERSION_LOW_PERCENTILE),
            "leave_one_document_out_high_flag_rate": _leave_one_out_flag_rate(
                values, DISPERSION_HIGH_PERCENTILE),
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
    # Dispersion-band findings: human documents occupy a per-feature BAND of
    # cross-paragraph dispersion. Below the low tail = over-uniform (the
    # natural-AI direction); above the high tail = over-dispersed (measured on
    # text written to force raggedness, which overshoots the band). Held-out
    # validation: one-sided scoring is at chance against a shape adversary;
    # the band view recovers it (EVALUATION.md section 9).
    dispersion = shape.get("dispersion", {})
    for feature_name, reference in baseline.get("dispersion", {}).items():
        observed = dispersion.get(feature_name, {}).get(DISPERSION_STAT)
        low_threshold = reference.get("low_threshold")
        high_threshold = reference.get("high_threshold")
        values = reference.get("values", [])
        if observed is None or low_threshold is None or not values:
            continue
        value = float(observed)
        if value < float(low_threshold):
            tail, rule_name = "low", "document-uniformity"
            threshold, distance = low_threshold, float(low_threshold) - value
            direction = "below the human low-tail"
            advice = ("Check whether the paragraphs are more uniform than the "
                      "argument needs; vary this feature where the science allows "
                      "(mix a list, a long-argument, and a terse paragraph) without "
                      "manufacturing variety that harms clarity.")
        elif high_threshold is not None and value > float(high_threshold):
            tail, rule_name = "high", "document-overdispersion"
            threshold, distance = high_threshold, value - float(high_threshold)
            direction = "above the human high-tail"
            advice = ("Check whether paragraph shapes swing more than the argument "
                      "motivates; forced or erratic variation reads as noise and "
                      "also departs from the human band.")
        else:
            continue
        percentile = _percentile(values, value)
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2",
            rule=f"{rule_name}:{feature_name}",
            scope="document", line=1, section=section_label, path=path,
            detector="deai_docstructure",
            detector_version="sci-paper.docstructure-baseline.v2",
            calibration_asset=BASELINE_NAME,
            measurement_status="measured", strength="strong",
            observed={"dispersion_std": observed,
                      "empirical_percentile": percentile,
                      "band_tail": tail,
                      "n_sections": shape["n_sections"],
                      "n_paragraphs": shape["n_paragraphs"]},
            reference={"n_documents": baseline["n_documents"],
                       "low_percentile": baseline.get("dispersion_low_percentile"),
                       "high_percentile": baseline.get("dispersion_high_percentile"),
                       "low_threshold": low_threshold,
                       "high_threshold": high_threshold,
                       "bootstrap_95_ci": reference.get("bootstrap_95_ci"),
                       "leave_one_document_out_flag_rate": reference.get(
                           "leave_one_document_out_flag_rate"),
                       "provenance": BASELINE_NAME},
            normalized_distance=distance,
            confidence={"value": min(1.0, baseline["n_documents"] / 30.0),
                        "basis": (f"{baseline['n_documents']} complete reference "
                                  "documents; band semantics validated held-out "
                                  "against natural, de-AI'd, and shape-adversarial "
                                  "AI document sets")},
            message=(f"Cross-paragraph variation in {feature_name.replace('_', ' ')} "
                     f"is {value:.3f}, {direction} {float(threshold):.3f}: the "
                     "document departs from the complete-human dispersion band for "
                     "this feature. This is a measured deviation, not an AI verdict."),
            action=advice,
            evidence=[tail, feature_name, round(value, 8)],
        ))
    return findings


def _paper_documents(corpus_dir: Path) -> list[tuple[str, str]]:
    """One concatenated document per paper directory (avoids pseudoreplication).

    A paper split across several .tex files (e.g. main + per-section fragments)
    is one observation, not many. Files are grouped by their containing
    directory and concatenated in sorted order; a flat .md/.tex directly under
    the corpus root is its own document.
    """
    by_paper: dict[Path, list[Path]] = {}
    for path in sorted(corpus_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".tex", ".md"}:
            by_paper.setdefault(path.parent, []).append(path)
    documents: list[tuple[str, str]] = []
    for parent, paths in sorted(by_paper.items()):
        text = "\n\n".join(
            p.read_text(encoding="utf-8", errors="replace") for p in sorted(paths))
        name = parent.name if parent != corpus_dir else paths[0].name
        documents.append((name, text))
    return documents


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
            baseline = calibrate(_paper_documents(args.corpus_dir), field_dir,
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
