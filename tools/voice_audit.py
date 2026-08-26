"""Held-out metrics, confound audits, and the author hard set for the voice model.

Everything that judges a trained bundle rather than building one: AUC with
bootstrap intervals, thresholded binary metrics, the section-normalized UID
alternative, the corpus-similarity split, the hard-set evaluation, and the
repeated grouped audits that expose source, section, length, field-term and
mathematical-density confounding.

Split out of `train_voice_model.py` on 2026-08-26, which had reached 1,174
lines against the repository's 750-line budget and could no longer be edited.
Nothing here fits a model; a bundle stays degraded until an operating point and
a confound audit are recorded, and these functions produce that evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as df  # noqa: E402  resolves only after the sys.path insert
import voice_dataset as vd  # noqa: E402  resolves only after the sys.path insert

# Hard-set provenance categories. They live here rather than in the CLI because
# `hardset_evaluation` below is their only consumer; `train_voice_model`
# re-exports both names, and a test asserts the two sets stay disjoint.
HARDSET_AI_CATEGORIES = frozenset({"clear-AI-raid", "clear-AI-claude"})
HARDSET_HUMAN_CATEGORIES = frozenset({"your-draft", "human-paper"})


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = probability * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    fraction = position - low
    return float(ordered[low] * (1.0 - fraction) + ordered[high] * fraction)


def _three_way_bin(value: float, lower: float, upper: float) -> str:
    if value <= lower:
        return "low"
    if value <= upper:
        return "mid"
    return "high"


def _math_bin(value: float, nonzero_median: float) -> str:
    if value <= 0:
        return "zero"
    if value <= nonzero_median:
        return "present-low"
    return "present-high"


def _auc(y_values: list[int], scores: list[float]) -> float | None:
    n_pos = sum(y_values)
    n_neg = len(y_values) - n_pos
    if not n_pos or not n_neg:
        return None
    ordered = sorted(zip(scores, y_values), key=lambda pair: pair[0])
    rank_sum = 0.0
    position = 1
    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        while end < len(ordered) and ordered[end][0] == ordered[cursor][0]:
            end += 1
        average_rank = (position + position + (end - cursor) - 1) / 2.0
        rank_sum += average_rank * sum(label for _, label in ordered[cursor:end])
        position += end - cursor
        cursor = end
    return (rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def binary_metrics(y_values, scores, threshold: float = 0.5) -> dict:
    labels = [int(value) for value in y_values]
    probabilities = [float(value) for value in scores]
    tp = fp = tn = fn = 0
    for label, score in zip(labels, probabilities):
        predicted = int(score >= threshold)
        if label and predicted:
            tp += 1
        elif label:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1
    tpr = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    tnr = tn / (tn + fp) if tn + fp else None
    precision = tp / (tp + fp) if tp + fp else None
    # A stratum with no positive examples has an UNDEFINED F1 (None, skipped by
    # aggregation) — never a real zero; 0.0 is reserved for measured failure.
    if tpr is None:
        f1 = None
    elif precision is None or precision + tpr == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * tpr / (precision + tpr)
    bacc = ((tpr + tnr) / 2.0) if tpr is not None and tnr is not None else None
    return {
        "n": len(labels),
        "n_positive": sum(labels),
        "n_negative": len(labels) - sum(labels),
        "score_mean": statistics.mean(probabilities) if probabilities else None,
        "score_median": statistics.median(probabilities) if probabilities else None,
        "auc": _auc(labels, probabilities),
        "positive_recall": tpr,
        "negative_false_positive_rate": fpr,
        "f1_positive": f1,
        "balanced_accuracy": bacc,
        "confusion": [[tn, fp], [fn, tp]],
        "threshold": threshold,
    }


def _breakdown(labels: list[str], y_values, scores,
               threshold: float = 0.5) -> dict[str, dict]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, label in enumerate(labels):
        grouped[label].append(index)
    return {
        label: binary_metrics([y_values[i] for i in indices],
                              [scores[i] for i in indices], threshold)
        for label, indices in sorted(grouped.items())
    }


def section_normalize_uid(X, recs: list[dict], train_indices):
    """Residualize UID features against positive training prose by section."""
    import numpy as np
    uid_names = ("mean_surprisal", "global_uid", "local_uid")
    uid_indices = [df.FEATURE_NAMES.index(name) for name in uid_names]
    positive_train = [int(i) for i in train_indices if recs[int(i)]["label"] == 1]
    pooled: dict[int, tuple[float, float]] = {}
    by_section: dict[str, dict[int, tuple[float, float]]] = defaultdict(dict)
    for feature_index in uid_indices:
        values = [float(X[i, feature_index]) for i in positive_train]
        mean = statistics.mean(values)
        stdev = statistics.pstdev(values) or 1.0
        pooled[feature_index] = (mean, stdev)
    sections = sorted({str(recs[i]["section"]) for i in positive_train})
    for section in sections:
        rows = [i for i in positive_train if str(recs[i]["section"]) == section]
        if len(rows) < 5:
            continue
        for feature_index in uid_indices:
            values = [float(X[i, feature_index]) for i in rows]
            by_section[section][feature_index] = (
                statistics.mean(values), statistics.pstdev(values) or 1.0)

    normalized = np.asarray(X, float).copy()
    for row_index, record in enumerate(recs):
        section_stats = by_section.get(str(record["section"]), {})
        for feature_index in uid_indices:
            mean, stdev = section_stats.get(feature_index, pooled[feature_index])
            normalized[row_index, feature_index] = (
                normalized[row_index, feature_index] - mean) / stdev
    return normalized, {
        "method": "positive-training section z-score with pooled fallback",
        "minimum_section_n": 5,
        "section_reference_count": len(by_section),
        "features": list(uid_names),
    }


def split_corpus_cos(X, emb, recs: list[dict], train_indices):
    """Recompute corpus_cos against a training-only curated centroid.

    The deployed centroid averages every curated exemplar, so a validation
    paper held out by the group split still contributed to it and its
    corpus_cos is self-inflated. Audits must instead use a centroid built
    only from curated training rows, or the grouped-split AUC is optimistic.
    """
    import numpy as np
    cos_index = df.FEATURE_NAMES.index("corpus_cos")
    X_leakfree = np.asarray(X, float).copy()
    if emb is None or emb.size == 0 or emb.shape[1] == 0:
        return X_leakfree, {"status": "unavailable",
                            "reason": "record embeddings were not computed"}
    rows = [int(i) for i in train_indices
            if recs[int(i)]["label"] == 1
            and vd.source_family(str(recs[int(i)]["source"])) == "curated-field-paper"]
    basis = "curated-field-paper training rows"
    if len(rows) < 5:
        rows = [int(i) for i in train_indices if recs[int(i)]["label"] == 1]
        basis = "all positive training rows (curated fallback)"
    centroid = emb[rows].mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm
    X_leakfree[:, cos_index] = emb @ centroid
    return X_leakfree, {"status": "recomputed", "basis": basis,
                        "n_centroid_rows": len(rows)}


def _bootstrap_auc_ci(y_values: list[int], scores: list[float], *,
                      n_boot: int = 2000, seed: int = 12345) -> dict | None:
    """Seeded percentile bootstrap CI for an AUC (reproducible, no live RNG).

    Small author-labelled strata have wide sampling error; a point AUC without
    an interval invites the exact over-reading this hard set previously caused.
    """
    point = _auc(y_values, scores)
    if point is None:
        return None
    import numpy as np
    rng = np.random.default_rng(seed)
    n = len(y_values)
    draws: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        value = _auc([y_values[i] for i in idx], [scores[i] for i in idx])
        if value is not None:
            draws.append(value)
    draws.sort()
    return {
        "auc": point,
        "ci95_low": _quantile(draws, 0.025) if draws else None,
        "ci95_high": _quantile(draws, 0.975) if draws else None,
        "n_bootstrap": len(draws),
    }


def hardset_evaluation(field_dir: Path, bundle: dict, model_name: str) -> dict:
    """Score the difficult hard set against the shipped model.

    The primary yardstick is the recorded TRUE provenance of each paragraph
    (deai_hardset_key.csv: generated vs human), not the author's perceptual
    ai_feel rating. A controlled analysis on this set showed that single
    decontextualized paragraphs carry too little signal for reliable human
    AI-judgement, so the perceptual rating is reported only as a task-difficulty
    baseline, never as the model's yardstick. Every AUC carries a bootstrap CI
    because the AI-labelled subset is small.
    """
    import csv
    import numpy as np
    label_path = field_dir / "hardset" / "deai_hardset_LABEL_ME.csv"
    key_path = field_dir / "hardset" / "deai_hardset_key.csv"
    if not label_path.exists():
        return {"status": "absent", "path": str(label_path.name)}
    with label_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    provenance: dict[str, str] = {}
    if key_path.exists():
        with key_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                provenance[row["id"]] = row.get("category", "")

    centroid = df.corpus_centroid(field_dir)
    clf, scaler = bundle["clf"], bundle["scaler"]
    column = list(clf.classes_).index(1)
    ids, feel, scores, is_ai = [], [], [], []
    for row in rows:
        vec = df.features_vector(row["paragraph"], field_profile_dir=field_dir,
                                 model_name=model_name, centroid=centroid)
        x = scaler.transform(np.asarray([vec], float))
        ids.append(row["id"])
        raw_feel = str(row.get("ai_feel_1to5", "")).strip()
        feel.append(int(float(raw_feel)) if raw_feel else None)
        scores.append(float(clf.predict_proba(x)[0, column]))
        category = provenance.get(row["id"], "")
        if category in HARDSET_AI_CATEGORIES:
            is_ai.append(1)
        elif category in HARDSET_HUMAN_CATEGORIES:
            is_ai.append(0)
        else:
            is_ai.append(None)

    # Primary: model score against TRUE provenance. Low compatibility should
    # mean generated, so invert the sign of the curated-reference probability.
    prov_idx = [i for i, value in enumerate(is_ai) if value is not None]
    provenance_result: dict = {"status": "absent"}
    perception_baseline: dict = {"status": "absent"}
    if prov_idx:
        y_prov = [is_ai[i] for i in prov_idx]
        neg_scores = [-scores[i] for i in prov_idx]
        n_ai = sum(y_prov)
        provenance_result = {
            "status": "measured",
            "n_ai_generated": n_ai,
            "n_human": len(y_prov) - n_ai,
            "model_auc_low_compat_predicts_generated": _bootstrap_auc_ci(
                y_prov, neg_scores),
            "score_by_provenance": {
                cat: {
                    "n": sum(1 for i in prov_idx if provenance.get(ids[i]) == cat),
                    "score_mean": (statistics.mean(
                        [scores[i] for i in prov_idx if provenance.get(ids[i]) == cat])
                        if any(provenance.get(ids[i]) == cat for i in prov_idx) else None),
                }
                for cat in sorted(HARDSET_AI_CATEGORIES | HARDSET_HUMAN_CATEGORIES)
            },
        }
        # Task-difficulty baseline: can the author's perception separate the
        # same true provenance? A low value means the single-paragraph task is
        # near-impossible for a human, which bounds what any detector's
        # agreement-with-perception could ever have meant.
        feel_prov = [(i, feel[i]) for i in prov_idx if feel[i] is not None]
        if feel_prov:
            perception_baseline = {
                "status": "measured",
                "human_ai_feel_auc_vs_provenance": _bootstrap_auc_ci(
                    [is_ai[i] for i, _ in feel_prov],
                    [float(value) for _, value in feel_prov]),
                "note": ("AUC of the author's ai_feel rating predicting true "
                         "provenance; a value near 0.5 means single-paragraph "
                         "human AI-judgement is near chance."),
            }

    labelled_feel = [(i, feel[i]) for i in range(len(ids)) if feel[i] is not None]
    perception_secondary: dict = {"status": "unlabelled"}
    if labelled_feel:
        strong = [int(value >= 4) for _, value in labelled_feel]
        perception_secondary = {
            "status": "labelled",
            "label_definition": "author ai_feel_1to5; 4-5 treated as strong AI feel",
            "n_strong": sum(strong),
            "caveat": ("perception-based and low-power (few strong labels); NOT a "
                       "model yardstick. See perception_baseline for why."),
            "auc_low_compat_predicts_strong_feel": _bootstrap_auc_ci(
                strong, [-scores[i] for i, _ in labelled_feel]),
            "score_by_feel": {
                str(level): {
                    "n": sum(1 for _, value in labelled_feel if value == level),
                    "score_mean": (statistics.mean(
                        [scores[i] for i, value in labelled_feel if value == level])
                        if any(value == level for _, value in labelled_feel) else None),
                }
                for level in sorted({value for _, value in labelled_feel})
            },
        }

    return {
        "status": "measured",
        "n_paragraphs": len(rows),
        "primary_provenance": provenance_result,
        "perception_baseline": perception_baseline,
        "perception_secondary": perception_secondary,
        "release_consequence": (
            "The provenance AUC measures true generated-vs-human separation; the "
            "perception metrics measure a near-chance single-paragraph human task "
            "and must not gate L3 alone. L3 stays degraded on the well-powered "
            "field-topic negative-control false-positive rates and the absence of "
            "document-level calibration."
        ),
        "per_paragraph": [
            {"id": ids[i], "provenance": provenance.get(ids[i], ""),
             "ai_feel_1to5": feel[i], "compatibility_score": round(scores[i], 6)}
            for i in range(len(ids))
        ],
    }


def confound_audit(recs: list[dict], X, train_indices, validation_indices,
                   y_validation, scores, threshold: float = 0.5) -> dict:
    """Build one split's confound report without creating an operating point."""
    train_indices = [int(i) for i in train_indices]
    validation_indices = [int(i) for i in validation_indices]
    lexicon, lexicon_meta = vd.build_field_lexicon(recs, train_indices)
    word_index = df.FEATURE_NAMES.index("word_count")
    word_counts = [float(X[i, word_index]) for i in range(len(recs))]
    math_density = [df.math_marker_density(record["text"]) for record in recs]
    jargon_density = [df.lexicon_density(record["text"], lexicon) for record in recs]

    train_lengths = [word_counts[i] for i in train_indices]
    length_edges = [_quantile(train_lengths, 1 / 3), _quantile(train_lengths, 2 / 3)]
    nonzero_math = [math_density[i] for i in train_indices if math_density[i] > 0]
    math_cut = _quantile(nonzero_math, 0.5)
    train_jargon = [jargon_density[i] for i in train_indices]
    jargon_edges = [_quantile(train_jargon, 1 / 3), _quantile(train_jargon, 2 / 3)]

    families = [vd.source_family(str(recs[i]["source"])) for i in validation_indices]
    sections = [str(recs[i]["section"]) for i in validation_indices]
    length_bins = [_three_way_bin(word_counts[i], *length_edges)
                   for i in validation_indices]
    math_bins = [_math_bin(math_density[i], math_cut) for i in validation_indices]
    jargon_bins = [_three_way_bin(jargon_density[i], *jargon_edges)
                   for i in validation_indices]

    source_groups = _breakdown(
        [str(recs[i]["source"]) for i in validation_indices], y_validation, scores,
        threshold)
    multi_record_sources = {
        source: metrics for source, metrics in source_groups.items()
        if metrics["n"] >= 5
    }

    joint_labels = [
        "|".join(values)
        for values in zip(sections, length_bins, math_bins, jargon_bins)
    ]
    joint = _breakdown(joint_labels, y_validation, scores, threshold)
    qualifying_joint = {
        label for label, metrics in joint.items()
        if metrics["n_positive"] >= 5 and metrics["n_negative"] >= 5
    }
    matched_indices = [i for i, label in enumerate(joint_labels)
                       if label in qualifying_joint]

    negative_indices = [i for i, label in enumerate(y_validation) if int(label) == 0]
    controls: dict[str, dict] = {}
    control_rules = {
        "math-present-generated": [i for i in negative_indices
                                    if math_density[validation_indices[i]] > 0],
        "math-dense-generated": [i for i in negative_indices
                                  if math_bins[i] == "present-high"],
        "field-jargon-dense-generated": [i for i in negative_indices
                                          if jargon_bins[i] == "high"],
        "field-topic-generated": [i for i in negative_indices
                                    if families[i] == "generated-field"],
        "public-generated": [i for i in negative_indices
                              if families[i] == "generated-public"],
    }
    for name, indices in control_rules.items():
        controls[name] = binary_metrics([y_validation[i] for i in indices],
                                        [scores[i] for i in indices], threshold)

    matched_metrics = binary_metrics(
        [y_validation[i] for i in matched_indices],
        [scores[i] for i in matched_indices], threshold)
    matched_metrics.update({
        "qualifying_strata": len(qualifying_joint),
        "total_strata": len(joint),
        "rule": "section × length-tertile × math-bin × field-term-tertile; "
                "retain cells with at least five records per class",
    })
    return {
        "overall": binary_metrics(y_validation, scores, threshold),
        "source_family": _breakdown(families, y_validation, scores, threshold),
        "source_paper": {
            "multi_record_groups": multi_record_sources,
            "n_groups_total": len(source_groups),
            "n_single_record_groups": sum(metrics["n"] == 1
                                          for metrics in source_groups.values()),
            "minimum_reported_group_n": 5,
        },
        "section": _breakdown(sections, y_validation, scores, threshold),
        "paragraph_length": {
            "training_tertile_edges_words": length_edges,
            "bins": _breakdown(length_bins, y_validation, scores, threshold),
        },
        "mathematical_marker_density": {
            "nonzero_training_median_per_100_words": math_cut,
            "bins": _breakdown(math_bins, y_validation, scores, threshold),
        },
        "field_term_density": {
            "training_tertile_edges_per_100_words": jargon_edges,
            "lexicon": lexicon_meta,
            "bins": _breakdown(jargon_bins, y_validation, scores, threshold),
        },
        "joint_matched_support": matched_metrics,
        "negative_controls": controls,
    }


def _metric_maps(report: dict, prefix: tuple[str, ...] = ()):
    """Yield report paths that carry binary-metric dictionaries."""
    if {"n", "score_mean", "balanced_accuracy"} <= report.keys():
        yield prefix, report
        return
    for key, value in report.items():
        if isinstance(value, dict):
            yield from _metric_maps(value, prefix + (str(key),))


def _series_summary(values: list[float]) -> dict:
    return {
        "n_splits": len(values),
        "mean": statistics.mean(values),
        "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "p2_5": _quantile(values, 0.025),
        "median": _quantile(values, 0.5),
        "p97_5": _quantile(values, 0.975),
        "minimum": min(values),
        "maximum": max(values),
    }


def aggregate_audits(reports: list[dict]) -> dict[str, dict]:
    """Summarize repeated-split variation for every available audit stratum."""
    collected: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for report in reports:
        for path, metrics in _metric_maps(report):
            path_key = "/".join(path)
            for metric in (
                "n", "n_positive", "n_negative", "score_mean", "score_median",
                "auc", "positive_recall", "negative_false_positive_rate",
                "f1_positive", "balanced_accuracy",
            ):
                value = metrics.get(metric)
                if value is not None:
                    collected[path_key][metric].append(float(value))
    return {
        path: {metric: _series_summary(values)
               for metric, values in sorted(metric_values.items())}
        for path, metric_values in sorted(collected.items())
    }


def first_valid_group_split(X, y, groups, *, val_frac: float, seed: int,
                            maximum_attempts: int = 100):
    """Return the first grouped split containing both classes on both sides."""
    from sklearn.model_selection import GroupShuffleSplit

    for offset in range(maximum_attempts):
        split_seed = seed + offset
        splitter = GroupShuffleSplit(
            n_splits=1, test_size=val_frac, random_state=split_seed)
        train_indices, validation_indices = next(
            splitter.split(X, y, groups=groups))
        if len(set(int(value) for value in y[train_indices])) < 2:
            continue
        if len(set(int(value) for value in y[validation_indices])) < 2:
            continue
        return train_indices, validation_indices, split_seed
    raise RuntimeError(
        f"no grouped split with both classes after {maximum_attempts} attempts")


def repeated_group_audit(recs: list[dict], X, y, groups, *, n_splits: int,
                         val_frac: float, seed: int, emb=None) -> dict:
    """Compare raw and section-normalized UID under repeated grouped splits.

    When record embeddings are supplied, every split recomputes corpus_cos
    against a training-only centroid (split_corpus_cos), so held-out papers
    cannot inflate their own similarity feature.
    """
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.preprocessing import StandardScaler

    raw_reports: list[dict] = []
    normalized_reports: list[dict] = []
    paired_deltas: dict[str, list[float]] = defaultdict(list)
    split_records: list[dict] = []
    attempts = 0
    maximum_attempts = max(20, n_splits * 20)
    while len(raw_reports) < n_splits and attempts < maximum_attempts:
        split_seed = seed + attempts
        splitter = GroupShuffleSplit(
            n_splits=1, test_size=val_frac, random_state=split_seed)
        train_indices, validation_indices = next(splitter.split(X, y, groups=groups))
        attempts += 1
        y_train = y[train_indices]
        y_validation = y[validation_indices]
        if len(set(int(value) for value in y_train)) < 2:
            continue
        if len(set(int(value) for value in y_validation)) < 2:
            continue

        X_split, centroid_meta = split_corpus_cos(X, emb, recs, train_indices)

        raw_scaler = StandardScaler().fit(X_split[train_indices])
        raw_model = LogisticRegression(
            class_weight="balanced", max_iter=2000, C=1.0,
            random_state=split_seed,
        ).fit(raw_scaler.transform(X_split[train_indices]), y_train)
        positive_column = list(raw_model.classes_).index(1)
        raw_scores = raw_model.predict_proba(
            raw_scaler.transform(X_split[validation_indices]))[:, positive_column]
        raw_report = confound_audit(
            recs, X_split, train_indices, validation_indices, y_validation,
            raw_scores)

        normalized_X, normalization = section_normalize_uid(
            X_split, recs, train_indices)
        normalized_scaler = StandardScaler().fit(normalized_X[train_indices])
        normalized_model = LogisticRegression(
            class_weight="balanced", max_iter=2000, C=1.0,
            random_state=split_seed,
        ).fit(normalized_scaler.transform(normalized_X[train_indices]), y_train)
        positive_column = list(normalized_model.classes_).index(1)
        normalized_scores = normalized_model.predict_proba(
            normalized_scaler.transform(normalized_X[validation_indices]))[:, positive_column]
        normalized_report = confound_audit(
            recs, X_split, train_indices, validation_indices,
            y_validation, normalized_scores)

        raw_reports.append(raw_report)
        normalized_reports.append(normalized_report)
        for path in (
            ("overall", "auc"),
            ("overall", "balanced_accuracy"),
            ("joint_matched_support", "auc"),
            ("joint_matched_support", "balanced_accuracy"),
        ):
            raw_value = raw_report[path[0]].get(path[1])
            normalized_value = normalized_report[path[0]].get(path[1])
            if raw_value is not None and normalized_value is not None:
                paired_deltas["/".join(path)].append(
                    float(normalized_value) - float(raw_value))
        for control in raw_report["negative_controls"]:
            raw_value = raw_report["negative_controls"][control].get(
                "negative_false_positive_rate")
            normalized_value = normalized_report["negative_controls"][control].get(
                "negative_false_positive_rate")
            if raw_value is not None and normalized_value is not None:
                paired_deltas[f"negative_controls/{control}/false_positive_rate"].append(
                    float(normalized_value) - float(raw_value))
        split_records.append({
            "seed": split_seed,
            "n_train": int(len(train_indices)),
            "n_validation": int(len(validation_indices)),
            "n_validation_positive": int(np.sum(y_validation)),
            "n_validation_negative": int(len(y_validation) - np.sum(y_validation)),
            "normalization": normalization,
            "corpus_cos_centroid": centroid_meta,
        })

    if len(raw_reports) < n_splits:
        raise RuntimeError(
            f"obtained {len(raw_reports)} valid grouped splits after {attempts} attempts; "
            f"requested {n_splits}")
    return {
        "classifier": "logistic regression",
        "split_method": "GroupShuffleSplit by source identifier",
        "requested_splits": n_splits,
        "completed_splits": len(raw_reports),
        "attempts": attempts,
        "validation_fraction": val_frac,
        "split_records": split_records,
        "raw_uid": aggregate_audits(raw_reports),
        "section_normalized_uid": aggregate_audits(normalized_reports),
        "normalized_minus_raw": {
            path: _series_summary(values)
            for path, values in sorted(paired_deltas.items())
        },
        "interpretation": (
            "Intervals summarize variation across repeated grouped splits; they are "
            "not independent-sample confidence intervals. No operating point is "
            "created by this audit."
        ),
    }
