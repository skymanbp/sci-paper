"""Record loading, grouping, and feature-matrix assembly for the voice model.

Everything that turns `style-profile/<field>/*.jsonl` into the training matrix:
the positive/negative banks, the source-family grouping that keeps whole papers
together, the train-only field lexicon, the embedding pass, and the on-disk
feature cache with its fingerprint.

Split out of `train_voice_model.py` on 2026-08-26, which had reached 1,174
lines against the repository's 750-line budget and could no longer be edited.
`train_voice_model` re-exports every public name here, so existing callers keep
resolving. Per-paragraph feature extraction itself lives in `deai_features`;
this module assembles what that produces.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as df  # noqa: E402  resolves only after the sys.path insert

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

CHECKPOINT_EVERY = 500   # rows between resumable partial-cache writes


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
        # Availability is an input to the cached rows, not an environment
        # detail: without the embedder every row carries corpus_cos = 0.0, and
        # a fingerprint blind to it kept serving those degraded rows after the
        # dependency was installed.
        "embedder_available": df.embedder_available(),
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
