"""Train the optional learned field-similarity model.

The training task separates curated field prose (positive class) from generated
negative examples using distributional, UID, punctuation, and embedding features.
Its probability is a compatibility score for triage and eligible-candidate ranking,
not an authorship probability. A shipped bundle remains degraded until an explicit
calibrated operating point and confound audit are recorded.

Records are grouped by their available source identifier. Curated corpus records
therefore hold out complete papers, while generated assets without source metadata
remain record-level groups. Repeated audits expose source, section, length, field-term,
and mathematical-density confounding and compare raw UID with a section-normalized
alternative.

Run:  python tools/train_voice_model.py --field wgl [--model gpt2-large] [--refeature]
Out:  style-profile/<field>/voice_model.joblib and voice_model_evaluation.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as df  # noqa: E402  resolves only after the sys.path insert

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"


def _load_jsonl(path: Path, label: int, prefix: str) -> list[dict]:
    out: list[dict] = []
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            r = json.loads(line)
            t = r.get("text", "")
            if t and len(t.split()) >= 30:
                out.append({"text": t, "label": label,
                            "source": r.get("source", f"{prefix}:{i}"),
                            "section": r.get("section", "unknown")})
    return out


def load_records(field_dir: Path) -> list[dict]:
    """Return records for curated-field versus generated-negative training.

    The positive class contains curated papers, dated pre-2022 arXiv abstracts,
    and the public reference side of the RAID-derived asset. The negative class
    contains generated field paragraphs, public generated records, and controlled
    hand-crafted seeds. ``source`` is preserved when an asset provides it; assets
    without source metadata receive record-level identifiers. These labels define
    a compatibility task, not human authorship.
    """
    recs: list[dict] = []
    # Positive class: curated field corpus + authoritative and broad pre-2022
    # arXiv abstracts + public records vetted as non-generated.
    recs += _load_jsonl(field_dir / "exemplar_paragraphs.jsonl", 1, "corpus")
    recs += _load_jsonl(field_dir / "human_abstracts_extra.jsonl", 1, "arxiv")
    recs += _load_jsonl(field_dir / "human_public_extra.jsonl", 1, "hpub")
    # Negative class: controlled generated prose (six registers) plus
    # multi-model public generated text.
    # NOTE: ai_ism_negatives_ourdrafts.jsonl (262 paragraphs from our own paper
    # drafts) is deliberately NOT loaded. A controlled source ablation
    # (2026-07-11, tools log bm40ooo8e) showed that assigning them to the
    # generated-negative class degraded every recorded validation axis: held-out
    # AUC 0.953->0.920, llm_style 0.071->0.263, and ai_ish 0.487->0.722. The
    # reviewed drafts occupy a mixed feature region, so forcing a binary label
    # blurs the compatibility task. Keep this source excluded unless a later
    # provenance-backed relabelling decision is evaluated explicitly.
    recs += _load_jsonl(field_dir / "ai_ism_negatives_generated.jsonl", 0, "gen1")
    recs += _load_jsonl(field_dir / "ai_ism_negatives_generated_v2.jsonl", 0, "gen2")
    recs += _load_jsonl(field_dir / "ai_ism_negatives_public.jsonl", 0, "public")
    hand = field_dir / "ai_ism_negatives_handcrafted.txt"
    if hand.exists():
        import re
        blocks = [b.strip() for b in re.split(r"\n\s*\n", hand.read_text(encoding="utf-8"))]
        for i, b in enumerate(blocks):
            if b and not b.startswith("#") and len(b.split()) >= 30:
                recs.append({"text": b, "label": 0, "source": f"hand:{i}",
                             "section": "mixed"})
    return recs


def source_family(source: str) -> str:
    """Return a stable dataset family without asserting individual authorship."""
    if source.startswith("style-corpus/") or source.startswith("corpus:"):
        return "curated-field-paper"
    if source.startswith("arxiv:"):
        return "dated-arxiv-reference"
    if source.startswith("raid-human:") or source.startswith("hpub:"):
        return "public-reference"
    if source.startswith(("gen1:", "gen2:")):
        return "generated-field"
    if source.startswith(("raid-ai:", "public:")):
        return "generated-public"
    if source.startswith("hand:"):
        return "generated-handcrafted"
    return "other"


def feature_cache_fingerprint(field_dir: Path, recs: list[dict],
                              model_name: str) -> str:
    """Fingerprint every input that can change a cached feature row."""
    digest = hashlib.sha256()
    header = {
        "feature_schema": df.FEATURE_SCHEMA_VERSION,
        "feature_names": df.FEATURE_NAMES,
        "model": model_name,
        "embedding_model": df.EMBED_MODEL,
        "records": [
            {key: record.get(key) for key in ("text", "label", "source", "section")}
            for record in recs
        ],
    }
    digest.update(json.dumps(header, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    centroid = field_dir / f"exemplar_embeddings_{df.EMBED_MODEL}.npy"
    if centroid.exists():
        with centroid.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    else:
        digest.update(b"<no-centroid>")
    return digest.hexdigest()


def _tokens(text: str) -> set[str]:
    plain = df.es.latex_to_plain(text).lower()
    return {
        token for token in re.findall(r"[a-z][a-z-]{2,}", plain)
        if token not in {"math", "cite", "figure-or-table"}
    }


def build_field_lexicon(recs: list[dict], train_indices) -> tuple[frozenset[str], dict]:
    """Derive audit-only field terms from training sources.

    Terms must recur across curated field papers and be enriched relative to the
    public reference corpus. Generated labels are not used to define the lexicon.
    """
    field_docs: dict[str, set[str]] = defaultdict(set)
    background_docs: dict[str, set[str]] = defaultdict(set)
    for raw_index in train_indices:
        record = recs[int(raw_index)]
        source = str(record["source"])
        family = source_family(source)
        if family == "curated-field-paper":
            field_docs[source].update(_tokens(record["text"]))
        elif family == "public-reference":
            background_docs[source].update(_tokens(record["text"]))

    field_df = Counter(token for words in field_docs.values() for token in words)
    background_df = Counter(token for words in background_docs.values() for token in words)
    n_field = len(field_docs)
    n_background = len(background_docs)
    ranked: list[tuple[float, int, str]] = []
    if n_field >= 3 and n_background >= 3:
        for token, count in field_df.items():
            if count < 3:
                continue
            background_count = background_df.get(token, 0)
            field_odds = (count + 0.5) / (n_field - count + 0.5)
            background_odds = ((background_count + 0.5) /
                               (n_background - background_count + 0.5))
            enrichment = math.log(field_odds) - math.log(background_odds)
            if enrichment >= 1.0:
                ranked.append((enrichment, count, token))
    ranked.sort(reverse=True)
    terms = frozenset(token for _, _, token in ranked[:256])
    return terms, {
        "method": "training-only source-document log-odds",
        "n_field_sources": n_field,
        "n_background_sources": n_background,
        "n_terms": len(terms),
        "minimum_field_sources": 3,
        "minimum_log_odds_enrichment": 1.0,
    }


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
            and source_family(str(recs[int(i)]["source"])) == "curated-field-paper"]
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


def hardset_evaluation(field_dir: Path, bundle: dict, model_name: str) -> dict:
    """Score the author-labelled hard set against the shipped model.

    This is the only stratum whose negatives can be human manuscript prose
    judged by the author, so it is the calibration path the generated-negative
    audits structurally cannot provide. Unlabelled rows are reported as
    unlabelled; they are never counted as zero findings.
    """
    import csv
    import numpy as np
    path = field_dir / "hardset" / "deai_hardset_LABEL_ME.csv"
    if not path.exists():
        return {"status": "absent", "path": str(path.name)}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labelled = [row for row in rows if str(row.get("ai_feel_1to5", "")).strip()]
    if not labelled:
        return {"status": "unlabelled", "n_paragraphs": len(rows),
                "release_consequence": (
                    "No author-labelled calibration evidence; L3 stays degraded.")}
    centroid = df.corpus_centroid(field_dir)
    clf, scaler = bundle["clf"], bundle["scaler"]
    ids, labels, scores = [], [], []
    for row in labelled:
        vec = df.features_vector(row["paragraph"], field_profile_dir=field_dir,
                                 model_name=model_name, centroid=centroid)
        x = scaler.transform(np.asarray([vec], float))
        column = list(clf.classes_).index(1)
        ids.append(row["id"])
        labels.append(int(float(row["ai_feel_1to5"])))
        scores.append(float(clf.predict_proba(x)[0, column]))
    by_label = {
        str(level): {
            "n": sum(1 for value in labels if value == level),
            "score_mean": (statistics.mean(
                [s for s, v in zip(scores, labels) if v == level])
                if any(v == level for v in labels) else None),
        }
        for level in sorted(set(labels))
    }
    strong_feel = [int(value >= 4) for value in labels]
    return {
        "status": "labelled",
        "n_labelled": len(labelled),
        "n_total": len(rows),
        "label_definition": "author ai_feel_1to5; 4-5 treated as strong AI feel",
        "score_by_label": by_label,
        # AUC of LOW compatibility predicting strong AI feel: the shipped
        # score is P(curated-reference class), so invert its sign.
        "auc_low_score_predicts_strong_ai_feel": _auc(
            strong_feel, [-value for value in scores]),
        "per_paragraph": [
            {"id": pid, "ai_feel_1to5": label, "compatibility_score": round(score, 6)}
            for pid, label, score in zip(ids, labels, scores)
        ],
    }


def confound_audit(recs: list[dict], X, train_indices, validation_indices,
                   y_validation, scores, threshold: float = 0.5) -> dict:
    """Build one split's confound report without creating an operating point."""
    train_indices = [int(i) for i in train_indices]
    validation_indices = [int(i) for i in validation_indices]
    lexicon, lexicon_meta = build_field_lexicon(recs, train_indices)
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

    families = [source_family(str(recs[i]["source"])) for i in validation_indices]
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


CHECKPOINT_EVERY = 500   # rows between resumable partial-cache writes


def _atomic_savez(path: Path, **arrays) -> None:
    import numpy as np
    temporary = path.with_name(f"{path.stem}.tmp{path.suffix}")
    with temporary.open("wb") as handle:
        np.savez(handle, **arrays)
    temporary.replace(path)


def _record_embeddings(recs: list[dict]):
    """Batch-encode every record's plain text; (n, 0) when no embedder exists.

    Embeddings feed both the shipped corpus_cos feature and the per-split
    leakage-free centroid recomputation in the audits. A missing
    sentence-transformers install degrades corpus_cos to 0.0 exactly as
    feature extraction always has, so the failure is warned, not fatal.
    """
    import numpy as np
    plains = [df.es.latex_to_plain(record["text"]) for record in recs]
    try:
        emb = df._embedder().encode(
            plains, normalize_embeddings=True, batch_size=64,
            show_progress_bar=False)
    except Exception as error:
        print(f"[train] embeddings unavailable ({error}); corpus_cos "
              "degrades to 0.0 and per-split centroids are skipped",
              file=sys.stderr)
        return np.zeros((len(recs), 0), np.float32)
    return np.asarray(emb, np.float32)


def build_features(field_dir: Path, recs: list[dict], model_name: str,
                   refeature: bool):
    """Return (X, y, src, emb) with provenance-fingerprinted caching.

    The slow per-record language-model pass checkpoints every
    ``CHECKPOINT_EVERY`` rows into a resumable partial cache so a preempted
    cloud run loses at most one chunk, never the whole extraction.
    """
    import numpy as np
    cache = field_dir / "voice_features_cache.npz"
    partial = field_dir / "voice_features_cache.partial.npz"
    fingerprint = feature_cache_fingerprint(field_dir, recs, model_name)
    n_features = len(df.FEATURE_NAMES)
    if cache.exists() and not refeature:
        try:
            with np.load(cache, allow_pickle=False) as cached:
                cached_fingerprint = (
                    str(cached["fingerprint"].item())
                    if "fingerprint" in cached.files else None
                )
                required = {"X", "y", "src", "emb", "names", "fingerprint"}
                names_match = (
                    "names" in cached.files
                    and list(cached["names"]) == df.FEATURE_NAMES
                )
                shapes_match = (
                    required <= set(cached.files)
                    and cached["X"].shape == (len(recs), n_features)
                    and cached["y"].shape == (len(recs),)
                    and cached["src"].shape == (len(recs),)
                    and cached["emb"].shape[0] == len(recs)
                )
                values_match = (
                    shapes_match
                    and np.array_equal(
                        cached["y"], np.asarray([record["label"] for record in recs], int))
                    and np.array_equal(
                        cached["src"],
                        np.asarray([str(record["source"]) for record in recs], str),
                    )
                )
                if (cached_fingerprint == fingerprint and names_match
                        and values_match):
                    print(f"[train] using provenance-verified cached features "
                          f"{cached['X'].shape}", file=sys.stderr)
                    return (cached["X"].copy(), cached["y"].copy(),
                            cached["src"].copy(), cached["emb"].copy())
        except (OSError, ValueError, KeyError) as error:
            print(f"[train] unusable legacy feature cache ({error}); recomputing",
                  file=sys.stderr)
        else:
            print("[train] feature cache provenance mismatch; recomputing",
                  file=sys.stderr)

    y = np.asarray([record["label"] for record in recs], int)
    src = np.asarray([str(record["source"]) for record in recs], str)
    emb = _record_embeddings(recs)
    centroid = df.corpus_centroid(field_dir)

    X = np.zeros((len(recs), n_features), float)
    start_row = 0
    if partial.exists():
        try:
            with np.load(partial, allow_pickle=False) as saved:
                if (str(saved["fingerprint"].item()) == fingerprint
                        and list(saved["names"]) == df.FEATURE_NAMES
                        and saved["X"].shape == X.shape):
                    start_row = int(saved["n_done"].item())
                    X[:start_row] = saved["X"][:start_row]
                    print(f"[train] resuming featurization from checkpoint "
                          f"row {start_row}/{len(recs)}", file=sys.stderr)
        except (OSError, ValueError, KeyError) as error:
            print(f"[train] unusable featurization checkpoint ({error}); "
                  "starting from row 0", file=sys.stderr)

    t0 = time.time()
    for i in range(start_row, len(recs)):
        # corpus_cos is set from the batch embeddings below, so the per-record
        # pass runs with no centroid (cos placeholder 0.0).
        X[i] = df.features_vector(recs[i]["text"], field_profile_dir=None,
                                  model_name=model_name, centroid=None)
        done = i + 1
        if done % 200 == 0:
            print(f"[train] featurized {done}/{len(recs)} "
                  f"({(time.time()-t0):.0f}s)", file=sys.stderr)
        if done % CHECKPOINT_EVERY == 0 and done < len(recs):
            _atomic_savez(partial, X=X, n_done=np.asarray(done),
                          names=np.asarray(df.FEATURE_NAMES, str),
                          fingerprint=np.asarray(fingerprint))

    cos_index = df.FEATURE_NAMES.index("corpus_cos")
    if centroid is not None and emb.shape[1]:
        X[:, cos_index] = emb @ np.asarray(centroid, np.float32)
    _atomic_savez(cache, X=X, y=y, src=src, emb=emb,
                  names=np.asarray(df.FEATURE_NAMES, str),
                  fingerprint=np.asarray(fingerprint))
    if partial.exists():
        partial.unlink()
    print(f"[train] featurized {len(recs)} in {(time.time()-t0):.0f}s -> {cache.name}",
          file=sys.stderr)
    return X, y, src, emb


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--field", required=True)
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--model", default=df.do.DEFAULT_MODEL)
    p.add_argument("--refeature", action="store_true", help="recompute features")
    p.add_argument("--prefer-hgb", action="store_true",
                   help="ship the gradient-boosting model when it wins held-out "
                        "AUC (default: ship logistic regression, following the "
                        "recorded out-of-distribution fixture audit).")
    p.add_argument("--val-frac", type=float, default=0.2)
    p.add_argument("--audit-splits", type=int, default=20,
                   help="number of valid source-grouped splits in the confound audit")
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)
    if not 0 < args.val_frac < 1:
        p.error("--val-frac must lie strictly between 0 and 1")
    if args.audit_splits < 3:
        p.error("--audit-splits must be at least 3")

    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import (roc_auc_score, f1_score, balanced_accuracy_score,
                                 confusion_matrix)
    import joblib

    field_dir = args.profile_root / args.field
    recs = load_records(field_dir)
    n_pos = sum(r["label"] for r in recs); n_neg = len(recs) - n_pos
    if not recs:
        p.error(f"no training records found in {field_dir}")
    if not n_pos or not n_neg:
        p.error("training records must contain both compatibility classes")
    print(f"[train] {len(recs)} paragraphs: {n_pos} curated-field / "
          f"{n_neg} generated-negative")
    X, y, src, emb = build_features(field_dir, recs, args.model, args.refeature)

    # Group-aware split: complete sources are held out as groups. This limits
    # same-paper leakage, but the later confound audit must still match source,
    # section, length, jargon, and mathematical density explicitly. Every
    # validation metric below uses corpus_cos recomputed against a
    # training-only centroid (split_corpus_cos), because the deployed global
    # centroid contains the held-out curated papers.
    tr_idx, va_idx, primary_split_seed = first_valid_group_split(
        X, y, src, val_frac=args.val_frac, seed=args.seed)
    X_primary, primary_centroid_meta = split_corpus_cos(X, emb, recs, tr_idx)
    Xtr, Xva, ytr, yva = (X_primary[tr_idx], X_primary[va_idx],
                          y[tr_idx], y[va_idx])

    scaler = StandardScaler().fit(Xtr)
    Xtr_s, Xva_s = scaler.transform(Xtr), scaler.transform(Xva)

    def _make(name):
        if name == "logreg":
            return LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0)
        return HistGradientBoostingClassifier(
            max_iter=400, learning_rate=0.05, max_depth=3,
            l2_regularization=1.0, class_weight="balanced",
            random_state=args.seed)

    # Train both for the recorded comparison. The shipped default is selected
    # below from the held-out and out-of-distribution evidence, not interpreted
    # as an authorship classifier.
    print(f"\n[val] n={len(yva)} ({int(yva.sum())} curated-field / "
          f"{int((1-yva).sum())} generated-negative)")
    results: dict[str, dict] = {}
    validation_scores: dict[str, object] = {}
    for name in ("logreg", "hgb"):
        m = _make(name).fit(Xtr_s, ytr)
        col = list(m.classes_).index(1)
        pv = m.predict_proba(Xva_s)[:, col]
        validation_scores[name] = pv
        pred = (pv >= 0.5).astype(int)
        results[name] = {"auc": float(roc_auc_score(yva, pv)),
                         "f1": float(f1_score(yva, pred)),
                         "bacc": float(balanced_accuracy_score(yva, pred)),
                         "cm": confusion_matrix(yva, pred).tolist()}
        r = results[name]
        print(f"[val:{name:6s}] AUC={r['auc']:.3f}  "
              f"F1(positive)={r['f1']:.3f}  balanced_acc={r['bacc']:.3f}  "
              f"confusion={r['cm']}")

    # Interpretability: logistic-regression weights on standardized features.
    # Positive coefficients indicate greater similarity to the curated-field
    # class under this training task; they do not identify a human author.
    lr = _make("logreg").fit(Xtr_s, ytr)
    order = np.argsort(-np.abs(lr.coef_[0]))
    print("\n[val] logreg feature weights "
          "(standardized; + => curated-field class):")
    for i in order:
        print(f"   {df.FEATURE_NAMES[i]:16s} {lr.coef_[0][i]:+.2f}")

    # Ship LOGREG by default even when HGB has higher held-out AUC. This model
    # ranks arbitrary rewrite candidates, so extrapolation outside the training
    # support matters. The recorded 2026-07-11 fixture audit found unstable HGB
    # behavior on one generated paragraph; EVALUATION.md records the limitation.
    # --prefer-hgb remains an explicit override.
    best = "hgb" if (args.prefer_hgb and
                     results["hgb"]["auc"] >= results["logreg"]["auc"]) else "logreg"
    print(f"\n[train] shipping classifier = {best} (val AUC "
          f"{results[best]['auc']:.3f}; hgb in-dist AUC "
          f"{results['hgb']['auc']:.3f} but weaker OOD — see comment)")

    print(f"[audit] primary confound strata for {best}", file=sys.stderr)
    primary_raw_audit = confound_audit(
        recs, X_primary, tr_idx, va_idx, yva, validation_scores[best])
    normalized_X, normalization_meta = section_normalize_uid(
        X_primary, recs, tr_idx)
    normalized_scaler = StandardScaler().fit(normalized_X[tr_idx])
    normalized_model = _make(best).fit(
        normalized_scaler.transform(normalized_X[tr_idx]), ytr)
    normalized_column = list(normalized_model.classes_).index(1)
    normalized_scores = normalized_model.predict_proba(
        normalized_scaler.transform(normalized_X[va_idx]))[:, normalized_column]
    primary_normalized_audit = confound_audit(
        recs, X_primary, tr_idx, va_idx, yva, normalized_scores)

    print(f"[audit] repeated source-grouped comparison: "
          f"{args.audit_splits} splits", file=sys.stderr)
    repeated_audit = repeated_group_audit(
        recs,
        X,
        y,
        src,
        n_splits=args.audit_splits,
        val_frac=args.val_frac,
        seed=args.seed,
        emb=emb,
    )
    cache_fingerprint = feature_cache_fingerprint(field_dir, recs, args.model)

    # Refit the best on ALL data (deployment uses the global corpus centroid;
    # validation above used training-only centroids so its estimates stay
    # leakage-free). Always fit+ship a StandardScaler so deai_voice can apply
    # it uniformly regardless of classifier type. Write via a temp file +
    # atomic replace (like the cache and evaluation outputs) so an interrupted
    # run can never leave a truncated bundle that crashes the scoring side.
    scaler_full = StandardScaler().fit(X)
    clf_full = _make(best).fit(scaler_full.transform(X), y)
    bundle = {"clf": clf_full, "scaler": scaler_full,
              "feature_names": df.FEATURE_NAMES,
              "feature_schema": df.FEATURE_SCHEMA_VERSION,
              "feature_cache_fingerprint": cache_fingerprint,
              "model": args.model,
              "classifier": best, "n_pos": n_pos, "n_neg": n_neg,
              "measurement_status": "degraded",
              "evaluation_schema": "sci-paper.voice-model-evaluation.v1",
              "val": {k: results[best][k] for k in ("auc", "f1", "bacc")}}

    print("[audit] author-labelled hard-set stratum", file=sys.stderr)
    hardset_report = hardset_evaluation(field_dir, bundle, args.model)

    evaluation = {
        "schema": "sci-paper.voice-model-evaluation.v1",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "field": args.field,
        "task": "curated-reference versus generated-negative field compatibility",
        "interpretation": (
            "This evaluation measures compatibility with the recorded training task. "
            "It does not identify an author."
        ),
        "measurement_status": "degraded",
        "operating_point": None,
        "degraded_reason": (
            "The audit measures split sensitivity and known confounds, but no "
            "accepted author-labelled operating point exists."
        ),
        "records": {
            "total": len(recs),
            "positive_class": n_pos,
            "negative_class": n_neg,
            "by_source_family": dict(sorted(Counter(
                source_family(str(record["source"])) for record in recs).items())),
            "by_section": dict(sorted(Counter(
                str(record["section"]) for record in recs).items())),
        },
        "features": {
            "schema": df.FEATURE_SCHEMA_VERSION,
            "names": df.FEATURE_NAMES,
            "language_model": args.model,
            "embedding_model": df.EMBED_MODEL,
            "cache_fingerprint_sha256": cache_fingerprint,
        },
        "corpus_cos_handling": (
            "validation and audit splits recompute corpus_cos against a "
            "training-only curated centroid; the shipped model uses the "
            "global deployment centroid"
        ),
        "primary_split": {
            "method": "GroupShuffleSplit by source identifier",
            "requested_seed": args.seed,
            "used_seed": primary_split_seed,
            "validation_fraction": args.val_frac,
            "classifier": best,
            "corpus_cos_centroid": primary_centroid_meta,
            "raw_uid": primary_raw_audit,
            "section_normalized_uid": primary_normalized_audit,
            "uid_normalization": normalization_meta,
        },
        "repeated_group_audit": repeated_audit,
        "author_labelled_hardset": hardset_report,
        "release_consequence": (
            "Keep L3 degraded and omit an operating_point until author-labelled "
            "calibration and an accepted consequence policy are available."
        ),
    }
    evaluation_path = field_dir / "voice_model_evaluation.json"
    temporary_evaluation = evaluation_path.with_name(
        f"{evaluation_path.stem}.tmp{evaluation_path.suffix}")
    temporary_evaluation.write_text(
        json.dumps(evaluation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_evaluation.replace(evaluation_path)
    print(f"[audit] wrote confound-aware evaluation -> {evaluation_path}")

    out = field_dir / "voice_model.joblib"
    temporary_model = out.with_name(f"{out.stem}.tmp{out.suffix}")
    joblib.dump(bundle, temporary_model)
    temporary_model.replace(out)
    print(f"[train] shipped voice model ({best}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
