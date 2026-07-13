"""Document-level paragraph and section shape feedback (L2).

This tool measures repeated rhetorical geometry, not repeated subject matter.
Calibration treats each complete source document as one observation to avoid
paragraph-level pseudoreplication.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
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

# Joint dispersion manifold (Mahalanobis band distance). Marginal band flags
# can be gamed feature-by-feature: an adversary that widens each dispersion
# independently lands the right marginals with the WRONG joint, because human
# papers co-move their dispersion features. The manifold statistic measures
# the joint distance from the human center in log-ratio space; one calibrated
# aggregate replaces the correlated per-feature "strong" flag spray. Held-out
# validation of the aggregate two-sided distance recovered the shape adversary
# from chance to AUC 0.80 (EVALUATION.md section 9.1); the covariance form is
# its refinement. Requires enough reference documents to estimate an 11x11
# covariance; below the minimum the baseline honestly omits the manifold.
MANIFOLD_EPS = 1e-9        # floor before log; zero dispersion is common
MANIFOLD_CLIP = 6.0        # clip |log ratio| so zero-variance features cannot dominate
MANIFOLD_RIDGE = 0.05      # relative diagonal ridge for a stable inverse
MANIFOLD_PERCENTILE = 0.95
MIN_MANIFOLD_DOCUMENTS = 3 * len(DISPERSION_FEATURE_NAMES)

# Role-coupled dispersion (frontier idea 1): shape variance explained by
# rhetorical role, permutation-normalized per document (deai_features.
# role_coupling_z). Three cheap model-free role factors are measured; the
# detection score averages only the two that survived split-half selection
# (chosen on one human half + AI tiers, confirmed on the held-out half:
# natural 0.846 / de-AI'd 0.833 / adversarial 0.850 / skeleton 0.715 AUC —
# EVALUATION.md section 9.4). "position" (first/middle/last in section) is at
# chance and would dilute the composite; it stays reported as context only.
# Humans couple shape to role; both AI failure modes (uniform and
# forced-ragged) decouple it, so detection is LOW-tail.
ROLE_FACTORS = ("section", "position", "content")
ROLE_SCORING_FACTORS = ("section", "content")
ROLE_LOW_PERCENTILE = 0.05
# Negative lookbehinds: an escaped dollar (\$, a literal currency sign) and a
# LaTeX row break with optional spacing (\\[5pt]) are not math delimiters.
_MATH_MARKER_RE = re.compile(
    r"(?<!\\)\$|(?<!\\)\\\(|(?<!\\)\\\["
    r"|\\begin\{(equation|align|gather|eqnarray|math|multline)")


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
                # cheap content-role markers for role-coupled dispersion
                "has_cite": "\\cite" in block,
                "has_math": bool(_MATH_MARKER_RE.search(block)),
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


def document_role_coupling(shape: dict[str, Any]) -> dict[str, Any]:
    """Permutation-normalized role coupling of paragraph shape (frontier 1).

    Computed from a ``document_shape`` result. Three one-way factors, each an
    integer label per paragraph: ``section`` (which section), ``position``
    (first/middle/last within its section), ``content`` (has-math x has-cite).
    Factors degenerate to one group on some documents (e.g. every paragraph
    cites); those are honestly skipped and the score averages the defined
    factors. Score is None when no factor is defined.
    """
    if shape.get("status") != "measured":
        return {"status": "unmeasured", "score": None, "factors": {}}
    vectors: list[list[float]] = []
    section_labels: list[int] = []
    position_labels: list[int] = []
    content_labels: list[int] = []
    for section_index, section in enumerate(shape["sections"]):
        paragraphs = section["paragraphs"]
        last = len(paragraphs) - 1
        for para_index, paragraph in enumerate(paragraphs):
            vectors.append(paragraph["modelfree"])
            section_labels.append(section_index)
            position_labels.append(
                0 if para_index == 0 else (2 if para_index == last else 1))
            content_labels.append(
                2 * int(paragraph["has_math"]) + int(paragraph["has_cite"]))
    labels = {"section": section_labels, "position": position_labels,
              "content": content_labels}
    factors: dict[str, float | None] = {}
    for name in ROLE_FACTORS:
        result = features.role_coupling_z(vectors, labels[name])
        factors[name] = result["mean_z"]
    scoring = [factors[name] for name in ROLE_SCORING_FACTORS
               if factors[name] is not None]
    return {
        "status": "measured" if scoring else "unmeasured",
        "score": statistics.mean(scoring) if scoring else None,
        "scoring_factors": list(ROLE_SCORING_FACTORS),
        "factors": factors,
        "n_paragraphs": len(vectors),
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
                           iterations: int = 500,
                           seed: int = 20260713) -> list[float] | None:
    """Seeded with-replacement bootstrap CI for a corpus quantile.

    The previous "deterministic balanced" scheme indexed with
    ``(iteration*17 + index*31) % n``, which is a full permutation whenever
    gcd(31, n) == 1 — every resample was the whole corpus, so the CI was
    always zero-width and overstated certainty. A genuine with-replacement
    bootstrap (seeded, still reproducible) replaces it.
    """
    if len(values) < 3:
        return None
    rng = random.Random(seed)
    n = len(values)
    estimates = []
    for _ in range(iterations):
        sample = [values[rng.randrange(n)] for _ in range(n)]
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


# ------------------------------------------------ dispersion manifold (joint) --

def _log_ratio_vector(row: dict[str, float], medians: dict[str, float],
                      features: list[str]) -> list[float]:
    out = []
    for name in features:
        ratio = max(float(row[name]), MANIFOLD_EPS) / max(medians[name], MANIFOLD_EPS)
        out.append(max(-MANIFOLD_CLIP, min(MANIFOLD_CLIP, math.log(ratio))))
    return out


def _mat_inv(matrix: list[list[float]]) -> list[list[float]]:
    """Gauss-Jordan inverse for the small (<=11x11) ridged covariance."""
    n = len(matrix)
    augmented = [list(row) + [1.0 if i == j else 0.0 for j in range(n)]
                 for i, row in enumerate(matrix)]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(augmented[r][col]))
        if abs(augmented[pivot_row][col]) < 1e-12:
            raise ValueError("singular covariance despite ridge")
        augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]
        pivot = augmented[col][col]
        augmented[col] = [value / pivot for value in augmented[col]]
        for row in range(n):
            if row != col and augmented[row][col] != 0.0:
                factor = augmented[row][col]
                augmented[row] = [a - factor * b
                                  for a, b in zip(augmented[row], augmented[col])]
    return [row[n:] for row in augmented]


def _mahalanobis(vector: list[float], center: list[float],
                 cov_inv: list[list[float]]) -> float:
    delta = [v - c for v, c in zip(vector, center)]
    total = 0.0
    for i, di in enumerate(delta):
        total += di * sum(cov_inv[i][j] * delta[j] for j in range(len(delta)))
    return math.sqrt(max(0.0, total))


def _fit_center_cov(vectors: list[list[float]]
                    ) -> tuple[list[float], list[list[float]]]:
    n, dim = len(vectors), len(vectors[0])
    center = [statistics.mean(col) for col in zip(*vectors)]
    cov = [[0.0] * dim for _ in range(dim)]
    for vec in vectors:
        delta = [v - c for v, c in zip(vec, center)]
        for i in range(dim):
            for j in range(dim):
                cov[i][j] += delta[i] * delta[j]
    for i in range(dim):
        for j in range(dim):
            cov[i][j] /= max(1, n - 1)
    ridge = MANIFOLD_RIDGE * (sum(cov[i][i] for i in range(dim)) / dim or MANIFOLD_EPS)
    for i in range(dim):
        cov[i][i] += ridge
    return center, cov


def fit_dispersion_manifold(rows: list[dict[str, float]],
                            features: list[str] | None = None) -> dict | None:
    """Fit the joint human dispersion manifold from per-document rows.

    ``rows`` map feature name -> dispersion std for one document each. Returns
    None below MIN_MANIFOLD_DOCUMENTS (an 11-dim covariance needs data; the
    baseline then honestly omits the manifold rather than shipping noise).
    """
    features = list(features if features is not None else DISPERSION_FEATURE_NAMES)
    usable = [row for row in rows if all(name in row for name in features)]
    if len(usable) < MIN_MANIFOLD_DOCUMENTS:
        return None
    medians = {name: statistics.median([float(row[name]) for row in usable])
               for name in features}
    vectors = [_log_ratio_vector(row, medians, features) for row in usable]
    center, cov = _fit_center_cov(vectors)
    cov_inv = _mat_inv(cov)
    null_distances = sorted(_mahalanobis(vec, center, cov_inv) for vec in vectors)
    threshold = _quantile(null_distances, MANIFOLD_PERCENTILE)
    # LOO: refit without each document; flag if its distance exceeds the
    # refit threshold. Keeps the quoted false-flag rate honest.
    flags = 0
    for index in range(len(usable)):
        others = vectors[:index] + vectors[index + 1:]
        center_i, cov_i = _fit_center_cov(others)
        cov_inv_i = _mat_inv(cov_i)
        null_i = sorted(_mahalanobis(vec, center_i, cov_inv_i) for vec in others)
        if _mahalanobis(vectors[index], center_i, cov_inv_i) > _quantile(
                null_i, MANIFOLD_PERCENTILE):
            flags += 1
    return {
        "features": features,
        "eps": MANIFOLD_EPS,
        "clip": MANIFOLD_CLIP,
        "ridge_relative": MANIFOLD_RIDGE,
        "n_documents": len(usable),
        "medians": medians,
        "center": center,
        "cov_inv": cov_inv,
        "null_distances": null_distances,
        "percentile": MANIFOLD_PERCENTILE,
        "threshold": threshold,
        "leave_one_document_out_flag_rate": flags / len(usable),
    }


def manifold_distance(manifold: dict, row: dict[str, float]) -> float | None:
    """Mahalanobis band distance of one document; None if features missing."""
    features = manifold["features"]
    if not all(name in row for name in features):
        return None
    vector = _log_ratio_vector(row, manifold["medians"], features)
    return _mahalanobis(vector, manifold["center"], manifold["cov_inv"])


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
                        "dispersion": result.get("dispersion", {}),
                        "role_coupling": document_role_coupling(result)["score"]})
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
    manifold_rows = [
        {name: float(record["dispersion"][name][DISPERSION_STAT])
         for name in DISPERSION_FEATURE_NAMES
         if record.get("dispersion", {}).get(name, {}).get(DISPERSION_STAT)
         is not None}
        for record in records
    ]
    baseline["dispersion_manifold"] = fit_dispersion_manifold(manifold_rows)
    # Role-coupled dispersion reference (frontier idea 1): both AI failure
    # modes decouple paragraph shape from rhetorical role, so detection is a
    # LOW tail on the permutation-normalized coupling z.
    role_values = [float(record["role_coupling"]) for record in records
                   if record.get("role_coupling") is not None]
    if len(role_values) >= 3:
        baseline["role_coupling"] = {
            "scoring_factors": list(ROLE_SCORING_FACTORS),
            "values": role_values,
            "low_percentile": ROLE_LOW_PERCENTILE,
            "low_threshold": _quantile(role_values, ROLE_LOW_PERCENTILE),
            "bootstrap_95_ci": _bootstrap_quantile_ci(
                role_values, ROLE_LOW_PERCENTILE),
            "leave_one_document_out_flag_rate":
                _leave_one_document_out_low_flag_rate(
                    role_values, ROLE_LOW_PERCENTILE),
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
    # Joint manifold statistic first: ONE calibrated aggregate. When it is
    # available, the correlated per-feature band flags demote to ordinary
    # context so one uniform document is not reported as ~8 strong findings.
    manifold = baseline.get("dispersion_manifold")
    flat_row = {name: dispersion[name][DISPERSION_STAT]
                for name in dispersion
                if dispersion.get(name, {}).get(DISPERSION_STAT) is not None}
    per_feature_strength = "ordinary"
    if not manifold:
        per_feature_strength = "strong"
    else:
        distance = manifold_distance(manifold, flat_row)
        if distance is not None and distance > float(manifold["threshold"]):
            null = manifold["null_distances"]
            p_value = 1.0 - (sum(d <= distance for d in null) / (len(null) + 1))
            findings.append(feedback.make_finding(
                kind="advisory", layer="L2", rule="document-dispersion-manifold",
                scope="document", line=1, section=section_label, path=path,
                detector="deai_docstructure",
                detector_version="sci-paper.docstructure-baseline.v2",
                calibration_asset=BASELINE_NAME,
                measurement_status="measured", strength="strong",
                observed={"mahalanobis_distance": distance,
                          "empirical_p_value": p_value,
                          "n_sections": shape["n_sections"],
                          "n_paragraphs": shape["n_paragraphs"]},
                reference={"n_documents": manifold["n_documents"],
                           "threshold": manifold["threshold"],
                           "percentile": manifold["percentile"],
                           "leave_one_document_out_flag_rate": manifold[
                               "leave_one_document_out_flag_rate"],
                           "provenance": BASELINE_NAME},
                normalized_distance=distance - float(manifold["threshold"]),
                confidence={"value": min(1.0, manifold["n_documents"] / 100.0),
                            "basis": (f"{manifold['n_documents']} complete "
                                      "reference documents; joint band "
                                      "distance in log dispersion-ratio space")},
                message=(f"The document's joint cross-paragraph dispersion sits "
                         f"{distance:.2f} Mahalanobis units from the human "
                         f"center (reference {manifold['percentile']:.0%} "
                         f"threshold {float(manifold['threshold']):.2f}): its "
                         "paragraph-shape variation pattern departs from the "
                         "human band as a whole. Per-feature detail follows as "
                         "ordinary context; this is a measured deviation, not "
                         "an AI verdict."),
                action=("Read the per-feature context findings to see which "
                        "shape dimensions depart, then adjust only where the "
                        "argument permits."),
                evidence=["manifold", round(distance, 6)],
            ))
    # Role-coupled dispersion (orthogonal to the manifold): humans vary
    # paragraph shape where the argument demands it, so shape variance is
    # partly explained by rhetorical role. Both AI failure modes — uniform
    # AND forced-ragged — decouple shape from role; the shape adversary that
    # narrows the manifold's margin scores at 0.850 held-out AUC here
    # (EVALUATION.md section 9.4), because random variety cannot fake
    # role-coupling. Detection is the LOW tail of the permutation z.
    role_reference = baseline.get("role_coupling")
    # Drift guard: a baseline calibrated with different scoring factors would
    # compare a current-code score against thresholds fit on another quantity;
    # skip the axis instead (same pattern as the voice-model schema guard).
    if role_reference and (role_reference.get("scoring_factors")
                           != list(ROLE_SCORING_FACTORS)):
        role_reference = None
    if role_reference:
        role = document_role_coupling(shape)
        role_values = role_reference.get("values", [])
        low_threshold = role_reference.get("low_threshold")
        if (role["score"] is not None and low_threshold is not None
                and role_values and role["score"] < float(low_threshold)):
            percentile = _percentile(role_values, float(role["score"]))
            findings.append(feedback.make_finding(
                kind="advisory", layer="L2", rule="document-role-decoupling",
                scope="document", line=1, section=section_label, path=path,
                detector="deai_docstructure",
                detector_version="sci-paper.docstructure-baseline.v2",
                calibration_asset=BASELINE_NAME,
                measurement_status="measured", strength="strong",
                observed={"role_coupling_z": role["score"],
                          "factors": role["factors"],
                          "empirical_percentile": percentile,
                          "n_sections": shape["n_sections"],
                          "n_paragraphs": shape["n_paragraphs"]},
                reference={"n_documents": len(role_values),
                           "low_percentile": role_reference.get("low_percentile"),
                           "low_threshold": low_threshold,
                           "bootstrap_95_ci": role_reference.get("bootstrap_95_ci"),
                           "leave_one_document_out_flag_rate": role_reference.get(
                               "leave_one_document_out_flag_rate"),
                           "scoring_factors": role_reference.get("scoring_factors"),
                           "provenance": BASELINE_NAME},
                normalized_distance=float(low_threshold) - float(role["score"]),
                confidence={"value": min(1.0, len(role_values) / 100.0),
                            "basis": (f"{len(role_values)} complete reference "
                                      "documents; permutation-normalized within "
                                      "each document, validated held-out against "
                                      "natural, de-AI'd, and shape-adversarial "
                                      "AI document sets")},
                message=(f"Paragraph-shape variation is decoupled from rhetorical "
                         f"role: coupling z is {role['score']:.2f}, below the "
                         f"human 5th-percentile threshold "
                         f"{float(low_threshold):.2f}. Human papers vary "
                         "paragraph shape where the argument demands it (across "
                         "sections and between citing/derivation/prose "
                         "paragraphs); here the variation is unrelated to role. "
                         "This is a measured deviation, not an AI verdict."),
                action=("Where the argument changes register (setup vs "
                        "derivation vs results), let the paragraph shape follow "
                        "it; do not add variety at random, tie it to content."),
                evidence=["role_coupling", round(float(role["score"]), 6)],
            ))
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
            measurement_status="measured", strength=per_feature_strength,
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
