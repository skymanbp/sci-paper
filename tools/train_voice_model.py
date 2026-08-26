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
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_features as df  # noqa: E402  resolves only after the sys.path insert

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

# Re-exported so `train_voice_model.<name>` keeps resolving for existing
# callers and tests after the 2026-08-26 split. A contract test asserts this
# list still covers every public name in both modules.
from voice_dataset import (  # noqa: E402,F401 -- re-export, unused here by design
    CHECKPOINT_EVERY,
    build_features, build_field_lexicon, feature_cache_fingerprint,
    load_records, source_family,
    _atomic_savez, _load_jsonl, _record_embeddings, _tokens,
)
from voice_audit import (  # noqa: E402,F401 -- re-export, unused here by design
    HARDSET_AI_CATEGORIES, HARDSET_HUMAN_CATEGORIES,
    aggregate_audits, binary_metrics, confound_audit, first_valid_group_split,
    hardset_evaluation, repeated_group_audit, section_normalize_uid,
    split_corpus_cos,
    _auc, _bootstrap_auc_ci, _breakdown, _math_bin, _metric_maps, _quantile,
    _series_summary, _three_way_bin,
)


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    p = cli_common.field_parser(__doc__)
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
