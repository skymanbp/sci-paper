"""train_ai_ism_classifier.py — train a paragraph-level AI-ism classifier.

Trains a binary classifier (logistic regression on word 1–2 gram TF-IDF)
that scores a paragraph's probability of being LLM-style academic prose.

Positives: corpus paragraphs from `style-profile/<field>/exemplar_paragraphs.jsonl`.
Negatives: hand-written AI-style paragraphs in
`tools/ai_ism_negatives_handcrafted.txt`. Free-form AI-voiced WGL prose
covering distributional patterns regex alone misses (heavy connective
stacking, generic intensifier sequences, "shed light on" / "paving the way"
phrasings).

Why hand-written only (no synthetic mutations): mutations of corpus
paragraphs (swap `use` → `leverage`, prepend `Furthermore,`) sit ~95%
identical to positives at the n-gram level — the classifier overfits to
noise, generalizes worse than majority-class predictor (empirically: train
acc 0.70, CV acc 0.51 vs baseline 0.56). Handcrafted-only with word 1–2
grams gives CV F1 ≈ 0.88 with 20 negatives + 1957 positives.

To improve quality further: append more paragraphs to
`ai_ism_negatives_handcrafted.txt` and re-train. Diminishing returns past
~100 handcrafted samples; class_weight="balanced" handles imbalance.

Model saves to `style-profile/<field>/ai_ism_classifier.joblib` (field-
aware). Run: `python tools/train_ai_ism_classifier.py [--field <name>]`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
HANDCRAFTED_NEGATIVES = REPO_ROOT / "tools" / "ai_ism_negatives_handcrafted.txt"

# Mutation infrastructure removed — empirically (see docstring) mutated
# negatives sit ~95% identical to positives in n-gram space and harm
# generalization. Handcrafted negatives only.


def list_fields(profile_root: Path) -> list[str]:
    if not profile_root.exists():
        return []
    return sorted(
        p.name for p in profile_root.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def resolve_field(arg_field: str | None, profile_root: Path) -> str:
    fields = list_fields(profile_root)
    if arg_field:
        if arg_field not in fields:
            raise SystemExit(
                f"[train_ai_ism_classifier] --field={arg_field!r} not found "
                f"under {profile_root}/. Available: {fields or '(none)'}"
            )
        return arg_field
    if not fields:
        raise SystemExit(
            f"[train_ai_ism_classifier] No field profiles under {profile_root}/. "
            "Run `python tools/extract_style.py` first."
        )
    if len(fields) > 1:
        raise SystemExit(
            f"[train_ai_ism_classifier] Multiple fields present ({fields}); "
            f"pass --field=<name>."
        )
    return fields[0]


def load_positives(jsonl_path: Path, min_words: int = 30) -> list[str]:
    pos = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = rec.get("text", "").strip()
            if text and rec.get("n_words", 0) >= min_words:
                pos.append(text)
    return pos


def load_handcrafted_negatives(path: Path) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    paras = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        if line.strip():
            current.append(line)
        elif current:
            paras.append(" ".join(current).strip())
            current = []
    if current:
        paras.append(" ".join(current).strip())
    return [p for p in paras if p]


def train_and_save(
    positives: list[str],
    negatives: list[str],
    output_path: Path,
    seed: int = 0,
) -> dict:
    """Train logistic regression on char-3-5 n-gram TF-IDF; save to joblib.
    Returns {n_pos, n_neg, cv_accuracy, cv_f1}."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score
    import joblib

    X = positives + negatives
    y = [0] * len(positives) + [1] * len(negatives)  # 1 = AI-ish

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            # Word 1-2 grams capture phrase-level AI-isms
            # ("shed light", "paving the way", "comprehensive suite") —
            # char n-grams over-fitted on the mutation experiment.
            analyzer="word",
            ngram_range=(1, 2),
            max_features=4000,
            min_df=2,
            sublinear_tf=True,
        )),
        ("lr", LogisticRegression(
            max_iter=2000,
            C=1.0,
            class_weight="balanced",
            random_state=seed,
        )),
    ])

    # Stratified 5-fold so each fold has both classes (handcrafted is rare).
    from sklearn.model_selection import StratifiedKFold
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    acc_scores = cross_val_score(pipeline, X, y, cv=skf, scoring="accuracy")
    f1_scores = cross_val_score(pipeline, X, y, cv=skf, scoring="f1")

    pipeline.fit(X, y)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_path)

    return {
        "n_pos": len(positives),
        "n_neg": len(negatives),
        "cv_accuracy_mean": float(acc_scores.mean()),
        "cv_accuracy_std": float(acc_scores.std()),
        "cv_f1_mean": float(f1_scores.mean()),
        "cv_f1_std": float(f1_scores.std()),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--field", default=None,
                   help="Field name; auto-detected when only one exists.")
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    field = resolve_field(args.field, args.profile_root)
    field_profile_dir = args.profile_root / field
    pos_jsonl = field_profile_dir / "exemplar_paragraphs.jsonl"
    if not pos_jsonl.exists():
        raise SystemExit(
            f"[train_ai_ism_classifier] {pos_jsonl} not found. "
            f"Run `python tools/extract_style.py --field {field}` first."
        )

    print(f"[train_ai_ism_classifier] field={field!r}")
    positives = load_positives(pos_jsonl)
    print(f"  positives (corpus): {len(positives)}")

    handcrafted = load_handcrafted_negatives(HANDCRAFTED_NEGATIVES)
    print(f"  handcrafted negatives: {len(handcrafted)} "
          f"(from {HANDCRAFTED_NEGATIVES.name})")

    # Optional auto-extracted negatives from user's local project files
    # (built by tools/extract_md_negatives.py). Field-specific, gitignored.
    extracted_path = field_profile_dir / "ai_ism_negatives_extracted.txt"
    extracted = load_handcrafted_negatives(extracted_path) if extracted_path.exists() else []
    if extracted:
        print(f"  extracted negatives: {len(extracted)} "
              f"(from style-profile/{field}/{extracted_path.name})")

    negatives = handcrafted + extracted

    if len(negatives) < 10:
        print(
            f"[train_ai_ism_classifier] WARNING: only {len(negatives)} "
            "negatives total. Add more to "
            f"{HANDCRAFTED_NEGATIVES.name}, or run "
            "`tools/extract_md_negatives.py --source-dir <doc-dir>` to harvest more.",
            file=sys.stderr,
        )

    output = field_profile_dir / "ai_ism_classifier.joblib"
    print(f"\n[train_ai_ism_classifier] training (this takes ~10-30 s)...")
    metrics = train_and_save(positives, negatives, output, seed=args.seed)

    print(f"\n[train_ai_ism_classifier] OK.")
    print(f"  n_pos = {metrics['n_pos']}, n_neg = {metrics['n_neg']}")
    print(f"  5-fold CV accuracy: "
          f"{metrics['cv_accuracy_mean']:.3f} ± {metrics['cv_accuracy_std']:.3f}")
    print(f"  5-fold CV F1 (AI-ish): "
          f"{metrics['cv_f1_mean']:.3f} ± {metrics['cv_f1_std']:.3f}")
    print(f"  → {output}")
    print()
    print("To use the classifier:")
    print(f"  python tools/ai_ism_lint.py <draft.tex> --ai-classifier --summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
