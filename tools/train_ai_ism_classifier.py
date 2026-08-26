"""Train the legacy word-ngram generated-style compatibility classifier.

The logistic-regression model contrasts corpus paragraphs with controlled
handcrafted examples of connective stacking, generic intensifiers, and lexical
AI-isms. Its score is optional advisory evidence about resemblance to that
negative set, not an authorship probability and not an L0 gate.

The legacy design deliberately avoids synthetic one-token mutations of corpus
paragraphs: those examples remain nearly identical in word 1--2-gram space and
previously degraded cross-validation below the majority baseline. The broader
v0.14 field-similarity model lives in ``train_voice_model.py``; this file remains
for backward-compatible ``--ai-classifier`` analysis.

The model is written to
``style-profile/<field>/ai_ism_classifier.joblib``. Run
``python tools/train_ai_ism_classifier.py [--field <name>]``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
HANDCRAFTED_NEGATIVES = REPO_ROOT / "tools" / "ai_ism_negatives_handcrafted.txt"

# Mutation infrastructure removed — empirically (see docstring) mutated
# negatives sit ~95% identical to positives in n-gram space and harm
# generalization. Handcrafted negatives only.


def list_fields(profile_root: Path) -> list[str]:
    return cli_common.list_fields(profile_root)


def resolve_field(arg_field: str | None, profile_root: Path) -> str:
    return cli_common.resolve_field(
        arg_field, profile_root, tool="train_ai_ism_classifier")




def load_positives(jsonl_path: Path,
                   min_words: int = 30) -> list[tuple[str, str]]:
    """(paragraph, source-paper) pairs.

    The source travels with the text because paragraphs from one paper are not
    independent: an ungrouped split puts siblings in train and test at once and
    reports an optimistic score. 28 source papers back the 1957 `wgl`
    paragraphs, so grouping is available and is used.
    """
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
                pos.append((text, str(rec.get("source") or f"unknown:{len(pos)}")))
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
    groups: list[str] | None = None,
) -> dict:
    """Train logistic regression on word 1-2 gram TF-IDF; save to joblib.

    Returns {n_pos, n_neg, cv_accuracy_mean, cv_accuracy_std, cv_f1_mean,
    cv_f1_std}. The analyzer is word-level, not character-level: char
    n-grams over-fitted on the mutation experiment (see the vectorizer
    comment below).
    """
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

    # Stratified 5-fold so each fold has both classes (handcrafted is rare),
    # and GROUPED by source paper when groups are supplied: paragraphs from one
    # paper are not independent observations, and an ungrouped split lets
    # siblings sit in train and test simultaneously. Measured on the `wgl`
    # corpus the difference is F1 0.876 ungrouped vs 0.823 grouped, so the
    # ungrouped number was optimistic by ~0.05. `cv_grouped` travels with the
    # metrics so a consumer can never read one for the other.
    from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
    n_splits = 5
    cv_grouped = bool(groups) and len(set(groups)) >= n_splits
    if cv_grouped:
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True,
                                        random_state=seed)
        split_kwargs = {"groups": groups}
    else:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True,
                                   random_state=seed)
        split_kwargs = {}
    acc_scores = cross_val_score(pipeline, X, y, cv=splitter,
                                 scoring="accuracy", **split_kwargs)
    f1_scores = cross_val_score(pipeline, X, y, cv=splitter, scoring="f1",
                                **split_kwargs)

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
        "cv_grouped": cv_grouped,
    }


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()

    p = cli_common.field_parser(__doc__)
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
    positive_pairs = load_positives(pos_jsonl)
    positives = [text for text, _source in positive_pairs]
    positive_groups = [source for _text, source in positive_pairs]
    print(f"  positives (corpus): {len(positives)} "
          f"from {len(set(positive_groups))} source papers")

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
    # Each negative is its own group: handcrafted items are independently
    # authored and extracted ones come from unrelated documents, so none of
    # them shares a source with another row.
    negative_groups = [f"negative:{index}" for index in range(len(negatives))]
    metrics = train_and_save(positives, negatives, output, seed=args.seed,
                             groups=positive_groups + negative_groups)

    print(f"\n[train_ai_ism_classifier] OK.")
    print(f"  n_pos = {metrics['n_pos']}, n_neg = {metrics['n_neg']}")
    # Accuracy alone is unreadable at this class ratio: the corpus bank grew to
    # 25k paragraphs against ~20 negatives, so always-predict-corpus already
    # scores ~0.999. Print that baseline next to it so the headline number
    # cannot be mistaken for skill; F1 on the minority class is the real signal.
    majority = metrics["n_pos"] / max(1, metrics["n_pos"] + metrics["n_neg"])
    print(f"  class ratio: {metrics['n_pos'] / max(1, metrics['n_neg']):.0f}:1 "
          f"(always-predict-corpus accuracy = {majority:.3f})")
    print(f"  5-fold CV accuracy: "
          f"{metrics['cv_accuracy_mean']:.3f} ± {metrics['cv_accuracy_std']:.3f}")
    print(f"  5-fold CV F1 (AI-ish): "
          f"{metrics['cv_f1_mean']:.3f} ± {metrics['cv_f1_std']:.3f}")
    print(f"  CV split: "
          f"{'grouped by source paper' if metrics['cv_grouped'] else 'UNGROUPED (optimistic)'}")
    print(f"  → {output}")
    print()
    print("To use the classifier:")
    print(f"  python tools/ai_ism_lint.py <draft.tex> --ai-classifier --summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
