"""Document-shape measurement and complete-document calibration.

Everything that turns a complete document into numbers, and everything that
fits a human reference to those numbers: the per-paragraph model-free feature
vector, cross-paragraph dispersion, the joint Mahalanobis manifold, role
coupling, the split-conformal / Mondrian operating points, and the baseline
builder.

Split out of `deai_docstructure.py` on 2026-08-25, which had grown to 1,092
lines against a 750-line budget and could no longer be edited. The seam is
measurement versus feedback: this module produces statistics, and
`deai_docstructure` turns them into `sci-paper.feedback.v1` findings and a CLI.
That module re-exports every public name here, so `dds.document_shape`,
`dds.calibrate` and `dds.manifold_operating_point` keep resolving for existing
callers and tests.

Nothing here defines a consequence class or an authorship claim. A calibrated
operating point is a statement about a human reference distribution, not about
who wrote a document.
"""

from __future__ import annotations

import json
import math
import random
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as features  # noqa: E402  resolves after the path insert
import deai_metrics as metrics  # noqa: E402  canonical section/paragraph ranges
import deai_structure as structure  # noqa: E402  sentence template features
import extract_style as es  # noqa: E402  canonical LaTeX cleanup/tokenizer

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
# document-scale, confound-orthogonal AI signal (docs/design-notes/DEAI_ARCHITECTURE_ROADMAP.md).
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

# Split-conformal operating points (frontier idea 8): the human false-flag
# rate is guaranteeable from human data alone. The manifold is fit on a
# proper-training split and its calibration scores come from held-out human
# papers, so the in-sample-quantile anti-conservatism (LOO 0.063 vs nominal
# 0.05) disappears; the role z needs no fit, so every reference paper is
# calibration. Conformal p = (1 + #{cal >= score}) / (n_cal + 1); flag when
# p <= alpha gives P(false flag) <= alpha for exchangeable human papers,
# finite-sample and distribution-free. Mondrian stratification uses document
# LENGTH terciles because that is the measured confound (EVALUATION.md 9.4:
# r(role score, paragraphs) = 0.353, flagged humans median 38 vs 60
# paragraphs); a stratum below the minimum falls back to the pooled
# calibration set, which keeps marginal validity.
CONFORMAL_ALPHA = 0.05
CONFORMAL_TRAIN_FRACTION = 0.6
CONFORMAL_SEED = 20260713
CONFORMAL_STRATA = 3
MIN_CAL_PER_STRATUM = 30
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


def _length_stratum(n_paragraphs: int, edges: list[float]) -> int:
    """Mondrian stratum index for a document length (edges ascending)."""
    for index, edge in enumerate(edges):
        if n_paragraphs <= edge:
            return index
    return len(edges)


def _conformal_p(calibration_scores: list[float], score: float) -> float:
    """Split-conformal p-value: rank of the score among calibration scores.

    Higher score = more nonconforming. With exchangeable human calibration
    scores, P(p <= alpha) <= alpha for a new human document, finite-sample.
    """
    return ((1 + sum(value >= score for value in calibration_scores))
            / (len(calibration_scores) + 1))


def _stratum_calibration(conformal_axis: dict, stratum: int) -> tuple[list[float], str]:
    """Calibration scores for a stratum, pooling when the stratum is thin."""
    scores = [score for s, score in conformal_axis["calibration"] if s == stratum]
    if len(scores) >= int(conformal_axis.get("min_cal_per_stratum",
                                             MIN_CAL_PER_STRATUM)):
        return scores, f"stratum {stratum}"
    return [score for _, score in conformal_axis["calibration"]], "pooled"


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


def manifold_operating_point(baseline: dict, row: dict[str, float],
                             n_paragraphs: int) -> dict[str, Any] | None:
    """Single scoring entry for the manifold axis (findings, partition, evals).

    Prefers the document's length-stratum manifold + calibration when the
    baseline carries one (length-aware metric); otherwise scores against the
    pooled manifold with stratum-then-pooled calibration. Distances from
    different manifolds are never mixed in one calibration comparison.
    Returns None when the axis is unmeasurable (no manifold or missing
    features).
    """
    pooled = baseline.get("dispersion_manifold")
    conformal = baseline.get("conformal")
    axis = (conformal or {}).get("manifold") if conformal else None
    if axis:
        stratum = _length_stratum(n_paragraphs, conformal["strata_edges"])
        alpha = float(conformal.get("alpha", CONFORMAL_ALPHA))
        entry = (axis.get("stratum") or {}).get(str(stratum))
        if entry:
            distance = manifold_distance(entry["manifold"], row)
            if distance is None:
                return None
            return {"distance": distance,
                    "p_value": _conformal_p(entry["calibration"], distance),
                    "alpha": alpha,
                    "operating_point": "split-conformal, stratum manifold",
                    "calibration_basis": f"stratum {stratum} manifold",
                    "n_calibration": len(entry["calibration"]),
                    "n_train": entry.get("n_train")}
        if pooled and axis.get("calibration"):
            distance = manifold_distance(pooled, row)
            if distance is None:
                return None
            cal, basis = _stratum_calibration(axis, stratum)
            return {"distance": distance,
                    "p_value": _conformal_p(cal, distance),
                    "alpha": alpha,
                    "operating_point": "split-conformal",
                    "calibration_basis": basis,
                    "n_calibration": len(cal),
                    "n_train": axis.get("n_train")}
    if pooled:
        distance = manifold_distance(pooled, row)
        if distance is None:
            return None
        null = pooled["null_distances"]
        return {"distance": distance,
                "p_value": 1.0 - (sum(d <= distance for d in null)
                                  / (len(null) + 1)),
                "alpha": None,
                "operating_point": "in-sample percentile",
                "threshold": pooled["threshold"],
                "flagged": distance > float(pooled["threshold"])}
    return None


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
                        "n_paragraphs": result["n_paragraphs"],
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
    def manifold_row(record: dict) -> dict[str, float]:
        return {name: float(record["dispersion"][name][DISPERSION_STAT])
                for name in DISPERSION_FEATURE_NAMES
                if record.get("dispersion", {}).get(name, {}).get(DISPERSION_STAT)
                is not None}

    # Split-conformal: the manifold is fit on a proper-training split so the
    # calibration scores are genuinely out-of-fit; the role z needs no fit.
    order = list(range(len(records)))
    random.Random(CONFORMAL_SEED).shuffle(order)
    n_train = int(len(records) * CONFORMAL_TRAIN_FRACTION)
    train_records = [records[i] for i in order[:n_train]]
    cal_records = [records[i] for i in order[n_train:]]
    manifold = fit_dispersion_manifold([manifold_row(r) for r in train_records])
    baseline["dispersion_manifold"] = manifold

    lengths = sorted(record["n_paragraphs"] for record in records)
    strata_edges = [
        _quantile([float(v) for v in lengths], k / CONFORMAL_STRATA)
        for k in range(1, CONFORMAL_STRATA)
    ]

    def stratum_of(record: dict) -> int:
        return _length_stratum(record["n_paragraphs"], strata_edges)

    if manifold is not None and cal_records:
        manifold_cal = []
        for record in cal_records:
            distance = manifold_distance(manifold, manifold_row(record))
            if distance is not None:
                manifold_cal.append([stratum_of(record), distance])
        # Length-aware (per-stratum) manifolds: short human papers score
        # systematically higher pooled-manifold distances (noisier dispersion
        # vectors), which cost the short strata their tail power. A stratum
        # that can support its own manifold fit AND enough calibration papers
        # gets a stratum-local metric; strata that cannot fall back to the
        # pooled manifold and pooled calibration (marginal validity intact).
        stratum_entries: dict[str, Any] = {}
        for s in range(CONFORMAL_STRATA):
            s_train = [r for r in train_records if stratum_of(r) == s]
            s_cal = [r for r in cal_records if stratum_of(r) == s]
            s_manifold = fit_dispersion_manifold(
                [manifold_row(r) for r in s_train])
            if s_manifold is None or len(s_cal) < MIN_CAL_PER_STRATUM:
                continue
            scores = [d for d in (manifold_distance(s_manifold,
                                                    manifold_row(r))
                                  for r in s_cal) if d is not None]
            if len(scores) < MIN_CAL_PER_STRATUM:
                continue
            stratum_entries[str(s)] = {"manifold": s_manifold,
                                       "calibration": scores,
                                       "n_train": len(s_train)}
        role_cal = [[stratum_of(record), -float(record["role_coupling"])]
                    for record in records
                    if record.get("role_coupling") is not None]
        baseline["conformal"] = {
            "alpha": CONFORMAL_ALPHA,
            "seed": CONFORMAL_SEED,
            "train_fraction": CONFORMAL_TRAIN_FRACTION,
            "strata_edges": strata_edges,
            "min_cal_per_stratum": MIN_CAL_PER_STRATUM,
            # nonconformity = manifold distance (high tail); role stores the
            # NEGATED coupling z so "higher = more nonconforming" holds for
            # both axes and one p-value rule serves both.
            "manifold": {"n_train": len(train_records),
                         "min_cal_per_stratum": MIN_CAL_PER_STRATUM,
                         "calibration": manifold_cal,
                         "stratum": stratum_entries},
            "role": {"scoring_factors": list(ROLE_SCORING_FACTORS),
                     "min_cal_per_stratum": MIN_CAL_PER_STRATUM,
                     "calibration": role_cal},
        }
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


