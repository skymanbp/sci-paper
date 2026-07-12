"""train_voice_model.py — Layer D: learn the human scientific VOICE.

Trains a classifier on the FUNDAMENTAL features (deai_features.py) to
distinguish real hand-written corpus paragraphs (positives, label=human) from
LLM-drafted paragraphs (negatives). Its P(human) score is the *reward* the
Layer C rewriter and the self-distillation loop optimize toward.

Why this replaces `ai_ism_classifier.joblib`: that model used word-1/2-gram
TF-IDF features, which only re-learn the keyword tells. This learns VOICE —
sentence-length burstiness, per-token surprisal / UID, punctuation/equivocal
rates, corpus-embedding distance — which survives synonym swaps.

Data:
  positives = style-profile/<field>/exemplar_paragraphs.jsonl (real papers)
  negatives = style-profile/<field>/ai_ism_negatives_generated.jsonl
              + ai_ism_negatives_handcrafted.txt
Anti-leakage: positives are split by SOURCE PAPER (held-out papers), so the
validation score is not inflated by same-paper paragraphs.

Run:  python tools/train_voice_model.py --field wgl [--model gpt2-large] [--refeature]
Out:  style-profile/<field>/voice_model.joblib  (+ metrics to stdout)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
    """[{text, label, source, section}] — label 1 = human, 0 = LLM.

    Positives: the curated corpus (real papers) + clean pre-2022 arXiv
    abstracts (fetch_arxiv_abstracts.py). Negatives: generated LLM paragraphs
    (v1 + the scaled/varied v2) + the hand-crafted seeds. `source` is the paper
    id / arxiv id so the group split holds out whole papers (no leakage)."""
    recs: list[dict] = []
    # positives (human): curated corpus + Ian/authoritative & broad pre-2022
    # arXiv abstracts + RAID-vetted human abstracts.
    recs += _load_jsonl(field_dir / "exemplar_paragraphs.jsonl", 1, "corpus")
    recs += _load_jsonl(field_dir / "human_abstracts_extra.jsonl", 1, "arxiv")
    recs += _load_jsonl(field_dir / "human_public_extra.jsonl", 1, "hpub")
    # negatives (LLM): generated (Claude, 6 registers) + multi-model public AI
    # text (RAID: GPT/Llama/...).
    # NOTE: ai_ism_negatives_ourdrafts.jsonl (262 paragraphs from our own paper
    # drafts) is deliberately NOT loaded. A controlled source ablation
    # (2026-07-11, tools log bm40ooo8e) showed that labeling them AI degraded
    # the model on EVERY axis — held-out AUC 0.953->0.920, and OOD fixtures
    # llm_style 0.071->0.263, ai_ish 0.487->0.722 (crossing to the wrong side).
    # Reason: after de-AI review our drafts read partly human (high burstiness /
    # UID), so tagging them AI blurs the feature->label boundary. They are
    # neither clean-AI nor clean-human. The file is retained for a user decision
    # (relabel as human positive vs discard); it must not re-enter as a negative.
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


def build_features(field_dir: Path, recs: list[dict], model_name: str,
                   refeature: bool):
    import numpy as np
    cache = field_dir / "voice_features_cache.npz"
    if cache.exists() and not refeature:
        d = np.load(cache, allow_pickle=True)
        if d["X"].shape[0] == len(recs) and list(d["names"]) == df.FEATURE_NAMES:
            print(f"[train] using cached features {d['X'].shape}", file=sys.stderr)
            return d["X"], d["y"], d["src"]
    centroid = df.corpus_centroid(field_dir)
    X, y, src = [], [], []
    t0 = time.time()
    for i, r in enumerate(recs):
        X.append(df.features_vector(r["text"], field_profile_dir=field_dir,
                                    model_name=model_name, centroid=centroid))
        y.append(r["label"]); src.append(r["source"])
        if (i + 1) % 200 == 0:
            print(f"[train] featurized {i+1}/{len(recs)} "
                  f"({(time.time()-t0):.0f}s)", file=sys.stderr)
    X = np.asarray(X, float); y = np.asarray(y, int); src = np.asarray(src, object)
    np.savez(cache, X=X, y=y, src=src, names=np.asarray(df.FEATURE_NAMES, object))
    print(f"[train] featurized {len(recs)} in {(time.time()-t0):.0f}s -> {cache.name}",
          file=sys.stderr)
    return X, y, src


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
                        "AUC (default: ship the monotonic logreg, which is more "
                        "robust out-of-distribution for a reward model).")
    p.add_argument("--val-frac", type=float, default=0.2)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.metrics import (roc_auc_score, f1_score, balanced_accuracy_score,
                                 confusion_matrix)
    import joblib

    field_dir = args.profile_root / args.field
    recs = load_records(field_dir)
    n_pos = sum(r["label"] for r in recs); n_neg = len(recs) - n_pos
    print(f"[train] {len(recs)} paragraphs: {n_pos} human / {n_neg} LLM")
    X, y, src = build_features(field_dir, recs, args.model, args.refeature)

    # Group-aware split: held-out papers for positives; negatives split with them.
    gss = GroupShuffleSplit(n_splits=1, test_size=args.val_frac, random_state=args.seed)
    tr_idx, va_idx = next(gss.split(X, y, groups=src))
    Xtr, Xva, ytr, yva = X[tr_idx], X[va_idx], y[tr_idx], y[va_idx]

    scaler = StandardScaler().fit(Xtr)
    Xtr_s, Xva_s = scaler.transform(Xtr), scaler.transform(Xva)

    def _make(name):
        if name == "logreg":
            return LogisticRegression(class_weight="balanced", max_iter=2000, C=1.0)
        return HistGradientBoostingClassifier(
            max_iter=400, learning_rate=0.05, max_depth=3,
            l2_regularization=1.0, class_weight="balanced",
            random_state=args.seed)

    # Train both; ship the one with the better held-out AUC. LR is
    # interpretable, HGB captures non-linear interactions once data is large.
    print(f"\n[val] n={len(yva)} ({int(yva.sum())} human / {int((1-yva).sum())} LLM)")
    results: dict[str, dict] = {}
    for name in ("logreg", "hgb"):
        m = _make(name).fit(Xtr_s, ytr)
        col = list(m.classes_).index(1)
        pv = m.predict_proba(Xva_s)[:, col]
        pred = (pv >= 0.5).astype(int)
        results[name] = {"auc": float(roc_auc_score(yva, pv)),
                         "f1": float(f1_score(yva, pred)),
                         "bacc": float(balanced_accuracy_score(yva, pred)),
                         "cm": confusion_matrix(yva, pred).tolist()}
        r = results[name]
        print(f"[val:{name:6s}] AUC={r['auc']:.3f}  F1(human)={r['f1']:.3f}  "
              f"balanced_acc={r['bacc']:.3f}  confusion={r['cm']}")

    # Interpretability: LR weights on standardized features (always shown).
    lr = _make("logreg").fit(Xtr_s, ytr)
    order = np.argsort(-np.abs(lr.coef_[0]))
    print("\n[val] logreg feature weights (standardized; + => more human):")
    for i in order:
        print(f"   {df.FEATURE_NAMES[i]:16s} {lr.coef_[0][i]:+.2f}")

    # Ship LOGREG by default even when HGB's in-distribution held-out AUC is
    # higher. This is a REWARD model that scores arbitrary, often
    # out-of-distribution rewrites; the monotonic linear model stays correct
    # everywhere ("more surprisal-variance / burstiness -> more human, always"),
    # whereas tree models extrapolate erratically into sparse regions.
    # Verified 2026-07-11: on a hand-crafted LLM paragraph, HGB scored
    # P(human)=0.99 (wrong) while LR gave 0.003. --prefer-hgb overrides.
    best = "hgb" if (args.prefer_hgb and
                     results["hgb"]["auc"] >= results["logreg"]["auc"]) else "logreg"
    print(f"\n[train] shipping classifier = {best} (val AUC "
          f"{results[best]['auc']:.3f}; hgb in-dist AUC "
          f"{results['hgb']['auc']:.3f} but weaker OOD — see comment)")

    # Refit the best on ALL data. Always fit+ship a StandardScaler so
    # deai_voice can apply it uniformly regardless of classifier type.
    scaler_full = StandardScaler().fit(X)
    clf_full = _make(best).fit(scaler_full.transform(X), y)
    out = field_dir / "voice_model.joblib"
    joblib.dump({"clf": clf_full, "scaler": scaler_full,
                 "feature_names": df.FEATURE_NAMES, "model": args.model,
                 "classifier": best, "n_pos": n_pos, "n_neg": n_neg,
                 "val": {k: results[best][k] for k in ("auc", "f1", "bacc")}}, out)
    print(f"[train] shipped voice model ({best}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
