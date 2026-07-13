"""Feature extraction for the optional learned compatibility model.

The model contrasts curated reference prose with generated negative examples.
These features measure distribution, UID, punctuation, and corpus similarity;
they do not identify an author. Audit-only covariates expose mathematical-marker
and field-term density so evaluation can test known confounds without silently
adding them to the shipped classifier.

Feature groups (all reuse the existing tooling so they match the corpus):
  distributional (model-free, from extract_style tokenizers):
    n_sentences, mean_sent_len, sent_len_cv, sent_len_stdev, word_count,
    opens_connective, equivocal_rate, paren_rate, semicolon_rate, comma_rate
  surprisal / UID (Layer B, local LM):
    mean_surprisal, global_uid, local_uid
  semantic (all-MiniLM-L6-v2, cached corpus centroid):
    corpus_cos  (cosine similarity of the paragraph embedding to the curated
                 reference-corpus centroid)

The learned model determines how these measurements separate its curated-reference
and generated-negative classes. This module does not assign authorship semantics to
any feature or score.

CLI:  python tools/deai_features.py draft.tex --field wgl   # dump per-paragraph
Lib:  from deai_features import paragraph_features, FEATURE_NAMES, features_vector
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_style as es      # noqa: E402  resolves only after the sys.path insert
import deai_oracle as do        # noqa: E402  same reason
from deai_metrics import CONNECTIVE_OPENERS  # noqa: E402  same reason

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
EMBED_MODEL = "all-MiniLM-L6-v2"
FEATURE_SCHEMA_VERSION = "sci-paper.voice-features.v1"

_MATH_MARKER_RE = re.compile(
    r"\[MATH\]|\[math\]|\$[^$]+\$|\\\(.+?\\\)|"
    r"\\begin\{(?:equation|align|gather|eqnarray|displaymath|multline)\*?\}",
    re.DOTALL,
)
_PLACEHOLDER_RE = re.compile(r"\[(?:MATH|math|CITE|FIGURE-OR-TABLE)\]")

EQUIVOCAL = frozenset({
    "but", "however", "although", "though", "whereas", "yet",
    "nonetheless", "nevertheless", "despite", "conversely", "while",
})

FEATURE_NAMES = [
    "n_sentences", "mean_sent_len", "sent_len_cv", "sent_len_stdev",
    "word_count", "opens_connective", "equivocal_rate", "paren_rate",
    "semicolon_rate", "comma_rate",
    "mean_surprisal", "global_uid", "local_uid",
    "corpus_cos",
]

_EMB_CACHE: dict = {}
_CENTROID_CACHE: dict = {}


def _embedder():
    if "m" not in _EMB_CACHE:
        from sentence_transformers import SentenceTransformer
        _EMB_CACHE["m"] = SentenceTransformer(EMBED_MODEL)
    return _EMB_CACHE["m"]


def corpus_centroid(field_profile_dir: Path) -> "object | None":
    """Unit-normalized mean of the cached corpus paragraph embeddings, or None."""
    key = str(field_profile_dir)
    if key in _CENTROID_CACHE:
        return _CENTROID_CACHE[key]
    import numpy as np
    npy = field_profile_dir / f"exemplar_embeddings_{EMBED_MODEL}.npy"
    if not npy.exists():
        _CENTROID_CACHE[key] = None
        return None
    emb = np.load(npy)
    c = emb.mean(axis=0)
    n = np.linalg.norm(c)
    c = c / n if n > 0 else c
    _CENTROID_CACHE[key] = c
    return c


def distributional_features(plain: str) -> dict:
    """Public model-free paragraph-shape features for reuse by L2 tools."""
    sents = [s for s in es.sentences(plain) if es.words(s)]
    lens = [len(es.words(s)) for s in sents]
    wc = sum(lens)
    mean_len = statistics.mean(lens) if lens else 0.0
    stdev = statistics.pstdev(lens) if len(lens) >= 2 else 0.0
    cv = (stdev / mean_len) if mean_len else 0.0
    openers = es.paragraph_initial_words(plain)
    opens_conn = 1.0 if (openers and openers[0].lower() in CONNECTIVE_OPENERS) else 0.0
    low = plain.lower()
    equiv = sum(len(re.findall(rf"\b{re.escape(w)}\b", low)) for w in EQUIVOCAL)
    per100 = (100.0 / wc) if wc else 0.0
    return {
        "n_sentences": float(len(lens)),
        "mean_sent_len": mean_len,
        "sent_len_cv": cv,
        "sent_len_stdev": stdev,
        "word_count": float(wc),
        "opens_connective": opens_conn,
        "equivocal_rate": equiv * per100,
        "paren_rate": plain.count("(") * per100,
        "semicolon_rate": plain.count(";") * per100,
        "comma_rate": plain.count(",") * per100,
    }


def _prose_words(text: str) -> list[str]:
    plain = _PLACEHOLDER_RE.sub(" ", es.latex_to_plain(text))
    return [word.lower() for word in es.words(plain)]


def math_marker_density(text: str) -> float:
    """Return LaTeX/placeholder math markers per 100 prose words.

    This is an audit covariate, not a classifier feature. Counting both raw
    LaTeX delimiters and extractor placeholders makes the value comparable
    across corpus, arXiv, and generated JSONL records. Placeholder tokens are
    excluded from the prose-word denominator.
    """
    n_words = len(_prose_words(text))
    if n_words == 0:
        return 0.0
    return 100.0 * len(_MATH_MARKER_RE.findall(text)) / n_words


def lexicon_density(text: str, lexicon: set[str] | frozenset[str]) -> float:
    """Return supplied field-lexicon occurrences per 100 prose words."""
    tokens = _prose_words(text)
    if not tokens:
        return 0.0
    return 100.0 * sum(token in lexicon for token in tokens) / len(tokens)


def paragraph_features(
    text: str,
    field_profile_dir: Path | None = None,
    model_name: str = do.DEFAULT_MODEL,
    centroid=None,
) -> dict:
    """Full fundamental-feature dict for one paragraph. `text` may contain LaTeX."""
    plain = es.latex_to_plain(text)
    feats = distributional_features(plain)
    # surprisal / UID (Layer B)
    uid = do.uid_features(do.token_surprisals(plain, model_name))
    if uid is None:  # too short for a stable UID estimate
        feats.update({"mean_surprisal": 0.0, "global_uid": 0.0, "local_uid": 0.0})
    else:
        feats.update({k: uid[k] for k in ("mean_surprisal", "global_uid", "local_uid")})
    # semantic distance to corpus centroid
    cos = 0.0
    if centroid is None and field_profile_dir is not None:
        centroid = corpus_centroid(field_profile_dir)
    if centroid is not None:
        import numpy as np
        e = _embedder().encode([plain], normalize_embeddings=True)[0]
        cos = float(np.dot(e, centroid))
    feats["corpus_cos"] = cos
    return feats


def features_vector(text: str, **kw) -> list[float]:
    f = paragraph_features(text, **kw)
    return [f[name] for name in FEATURE_NAMES]


# Cross-paragraph dispersion: the document-scale, confound-orthogonal signal.
# Field register shifts the LEVEL (mean) of per-paragraph features; AI-uniformity
# compresses their SPREAD across a document. A per-paragraph score sees only
# levels, so it is fooled by on-topic AI prose (the 32-41% field-topic FPR). The
# spread of the same features across a whole document is orthogonal to topic and
# is where a human paper's list/argument/result paragraphs differ from an evenly
# drafted AI section. See docs/DEAI_ARCHITECTURE_ROADMAP.md.
DISPERSION_STATS = ("std", "cv", "iqr", "lag1_autocorr", "min_gap")


def _lag1_autocorr(series: list[float]) -> float | None:
    """Lag-1 autocorrelation along document order, or None if undefined."""
    n = len(series)
    if n < 3:
        return None
    mean = statistics.mean(series)
    denom = sum((value - mean) ** 2 for value in series)
    if denom == 0:  # a perfectly constant feature has no defined autocorrelation
        return None
    numer = sum((series[i] - mean) * (series[i + 1] - mean) for i in range(n - 1))
    return numer / denom


def feature_dispersion(values: list[float]) -> dict[str, float | None]:
    """Dispersion statistics of one feature across a document's paragraphs.

    Lower dispersion means a more uniform (AI-drafted) document. ``cv`` is the
    scale-free spread; ``min_gap`` is the smallest adjacent absolute change and
    is an over-uniformity indicator; ``lag1_autocorr`` captures smooth drift.
    """
    n = len(values)
    if n < 2:
        return {stat: None for stat in DISPERSION_STATS}
    std = statistics.pstdev(values)
    mean = statistics.mean(values)
    ordered = sorted(values)
    q1 = _quantile_sorted(ordered, 0.25)
    q3 = _quantile_sorted(ordered, 0.75)
    gaps = [abs(values[i + 1] - values[i]) for i in range(n - 1)]
    return {
        "std": std,
        "cv": (std / abs(mean)) if mean != 0 else None,
        "iqr": q3 - q1,
        "lag1_autocorr": _lag1_autocorr(values),
        "min_gap": min(gaps) if gaps else None,
    }


def _quantile_sorted(ordered: list[float], probability: float) -> float:
    position = probability * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def cross_paragraph_dispersion(
    paragraph_vectors: list[list[float]],
    feature_names: list[str] | None = None,
) -> dict[str, dict[str, float | None]]:
    """Per-feature cross-paragraph dispersion for one complete document.

    ``paragraph_vectors`` are per-paragraph feature vectors in document order.
    Returns ``{feature_name: {std, cv, iqr, lag1_autocorr, min_gap}}``. Any
    feature set may be passed; the model-free subset needs no GPU, so the
    document detector can calibrate locally and add surprisal/embedding
    dispersion when those are available.
    """
    names = feature_names if feature_names is not None else FEATURE_NAMES
    if not paragraph_vectors:
        return {name: {stat: None for stat in DISPERSION_STATS} for name in names}
    columns = list(zip(*paragraph_vectors))
    return {
        name: feature_dispersion([float(value) for value in columns[index]])
        for index, name in enumerate(names)
        if index < len(columns)
    }


# Role-coupled dispersion (frontier idea 1): humans vary paragraph shape WHERE
# THE ARGUMENT DEMANDS IT, so shape variance is partly explained by rhetorical
# role; both AI failure modes (uniform and forced-ragged) vary shape at random
# with respect to role. Raw eta-squared inflates with group count and shrinks
# with paragraph count, so the observed value is normalized against a seeded
# within-document permutation null (shuffling role labels), giving a z that is
# comparable across documents of different lengths and section structures.
ROLE_COUPLING_PERMUTATIONS = 200
ROLE_COUPLING_SEED = 20260713


def _eta_squared_columns(columns: list[list[float]],
                         labels: list[int]) -> list[float | None]:
    """One-way eta-squared of each feature column grouped by ``labels``.

    Returns None for a column with zero total variance (eta-squared undefined)
    or when fewer than two groups are present.
    """
    n = len(labels)
    groups = sorted(set(labels))
    if n < 3 or len(groups) < 2:
        return [None] * len(columns)
    out: list[float | None] = []
    for column in columns:
        total = sum(column)
        ss_total = sum(v * v for v in column) - total * total / n
        if ss_total <= 0:
            out.append(None)
            continue
        group_sum: dict[int, float] = {}
        group_n: dict[int, int] = {}
        for value, label in zip(column, labels):
            group_sum[label] = group_sum.get(label, 0.0) + value
            group_n[label] = group_n.get(label, 0) + 1
        ss_between = sum(s * s / group_n[g] for g, s in group_sum.items())
        ss_between -= total * total / n
        out.append(max(0.0, min(1.0, ss_between / ss_total)))
    return out


def role_coupling_z(
    paragraph_vectors: list[list[float]],
    role_labels: list[int],
    n_permutations: int = ROLE_COUPLING_PERMUTATIONS,
    seed: int = ROLE_COUPLING_SEED,
) -> dict[str, float | None]:
    """Permutation-normalized role coupling of paragraph shape for one factor.

    ``role_labels`` assigns each paragraph an integer role group (e.g. section
    index). Returns ``{"mean_z": ..., "n_features_defined": ...}`` where
    ``mean_z`` averages, over feature columns with defined eta-squared, the z
    of the observed value against the label-permutation null. Positive z =
    shape coupled to role beyond chance; near-zero or negative = decoupled.
    ``mean_z`` is None when no feature has a defined, permutation-stable z.
    """
    if len(paragraph_vectors) != len(role_labels):
        raise ValueError("one role label per paragraph vector is required")
    columns = [list(map(float, column)) for column in zip(*paragraph_vectors)]
    observed = _eta_squared_columns(columns, role_labels)
    if all(value is None for value in observed):
        return {"mean_z": None, "n_features_defined": 0}
    rng = random.Random(seed)
    null_values: list[list[float]] = [[] for _ in columns]
    shuffled = list(role_labels)
    for _ in range(n_permutations):
        rng.shuffle(shuffled)
        for index, value in enumerate(_eta_squared_columns(columns, shuffled)):
            if value is not None:
                null_values[index].append(value)
    z_scores = []
    for index, obs in enumerate(observed):
        null = null_values[index]
        if obs is None or len(null) < max(10, n_permutations // 2):
            continue
        spread = statistics.pstdev(null)
        if spread == 0:
            continue
        z_scores.append((obs - statistics.mean(null)) / spread)
    if not z_scores:
        return {"mean_z": None, "n_features_defined": 0}
    return {"mean_z": statistics.mean(z_scores),
            "n_features_defined": len(z_scores)}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", type=Path)
    p.add_argument("--field", default=None)
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--model", default=do.DEFAULT_MODEL)
    args = p.parse_args(argv)
    field_dir = None
    if args.field:
        field_dir = args.profile_root / args.field
    text = args.file.read_text(encoding="utf-8", errors="replace")
    centroid = corpus_centroid(field_dir) if field_dir else None
    # split into blank-line paragraphs and dump features
    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    print("feature order:", ", ".join(FEATURE_NAMES))
    for i, b in enumerate(blocks):
        v = features_vector(b, field_profile_dir=field_dir, model_name=args.model,
                            centroid=centroid)
        print(f"para[{i}] " + " ".join(f"{x:.2f}" for x in v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
