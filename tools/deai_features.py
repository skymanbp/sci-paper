"""deai_features.py — fundamental-feature extractor for the learned voice model.

Turns a paragraph into a compact vector of the FUNDAMENTAL (non-keyword)
features that separate human scientific prose from LLM prose. This is the
input to the Layer D voice/reward model (train_voice_model.py), replacing the
old word-ngram TF-IDF features that only re-learn the keyword tells.

Feature groups (all reuse the existing tooling so they match the corpus):
  distributional (model-free, from extract_style tokenizers):
    n_sentences, mean_sent_len, sent_len_cv, sent_len_stdev, word_count,
    opens_connective, equivocal_rate, paren_rate, semicolon_rate, comma_rate
  surprisal / UID (Layer B, local LM):
    mean_surprisal, global_uid, local_uid
  semantic (all-MiniLM-L6-v2, cached corpus centroid):
    corpus_cos  (cosine similarity of the paragraph embedding to the human
                 corpus centroid)

Human prose: high sent_len_cv, high global_uid/local_uid, higher
equivocal/paren/semicolon rates, opens_connective≈0. LLM prose: the opposite.
The learned model weights them; this module just measures.

CLI:  python tools/deai_features.py draft.tex --field wgl   # dump per-paragraph
Lib:  from deai_features import paragraph_features, FEATURE_NAMES, features_vector
"""

from __future__ import annotations

import argparse
import json
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


def _distributional(plain: str) -> dict:
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


def paragraph_features(
    text: str,
    field_profile_dir: Path | None = None,
    model_name: str = do.DEFAULT_MODEL,
    centroid=None,
) -> dict:
    """Full fundamental-feature dict for one paragraph. `text` may contain LaTeX."""
    plain = es.latex_to_plain(text)
    feats = _distributional(plain)
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
