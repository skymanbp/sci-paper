"""retrieve_exemplars.py — fetch top-K corpus paragraphs by section + topic.

Reads `style-profile/<field>/exemplar_paragraphs.jsonl` (built by
`extract_style.py`) and returns the K paragraphs in the requested section
that are most similar to the user's topic, as positive style anchors for
`/sci-paper:de-ai`.

Default retrieval: sentence-transformers cosine on `all-MiniLM-L6-v2`
embeddings, with a per-corpus `.npy` cache (rebuilt automatically when
the JSONL mtime is newer than the cache).

Fallback (`--allow-fallback`): if sentence-transformers is unavailable,
fall back to naive topic-keyword overlap. This works without ML deps but
gives substantially worse retrieval — use only as a last resort.

Output format: human-readable exemplars separated by `=== Exemplar i/K
(cosine=…, section=…, tier=…, source=…) ===` headers, intended to be
streamed straight into `/sci-paper:de-ai` context.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
DEFAULT_MODEL = "all-MiniLM-L6-v2"

VALID_SECTIONS = {"abstract", "intro", "method", "results", "discussion", "conclusion"}


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
                f"[retrieve_exemplars] --field={arg_field!r} not found under "
                f"{profile_root}/. Available: {fields or '(none)'}"
            )
        return arg_field
    if not fields:
        raise SystemExit(
            f"[retrieve_exemplars] No field profiles found under {profile_root}/. "
            "Run `python tools/extract_style.py --field <name>` first."
        )
    if len(fields) > 1:
        raise SystemExit(
            f"[retrieve_exemplars] Multiple fields present ({fields}); "
            f"pass --field=<name>."
        )
    return fields[0]


def _emb_cache_path(profile_dir: Path, model_name: str) -> Path:
    safe = model_name.replace("/", "_").replace("\\", "_")
    return profile_dir / f"exemplar_embeddings_{safe}.npy"


def _load_records(jsonl_path: Path) -> list[dict]:
    records = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _build_or_load_embeddings(
    records: list[dict],
    jsonl_path: Path,
    profile_dir: Path,
    model_name: str,
):
    """Returns (embeddings ndarray L2-normalized, model). Builds cache on first
    call or when JSONL is newer than cache.

    Raises ImportError if sentence-transformers is not installed.
    """
    import numpy as np  # numpy is a dep of sentence-transformers anyway
    from sentence_transformers import SentenceTransformer

    cache = _emb_cache_path(profile_dir, model_name)
    needs_rebuild = (
        not cache.exists()
        or cache.stat().st_mtime < jsonl_path.stat().st_mtime
    )

    model = SentenceTransformer(model_name)

    if needs_rebuild:
        print(
            f"[retrieve_exemplars] Building embedding cache "
            f"({len(records)} paragraphs, model={model_name}) — "
            f"first run downloads the model (~80 MB).",
            file=sys.stderr,
        )
        texts = [r["text"] for r in records]
        embs = model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=True,
            normalize_embeddings=True,
        ).astype("float32")
        np.save(cache, embs)
        print(f"[retrieve_exemplars] Cached → {cache}", file=sys.stderr)
    else:
        embs = np.load(cache)
        if embs.shape[0] != len(records):
            print(
                f"[retrieve_exemplars] Cache size mismatch "
                f"(cache N={embs.shape[0]} vs jsonl N={len(records)}); "
                f"rebuilding.",
                file=sys.stderr,
            )
            cache.unlink(missing_ok=True)
            return _build_or_load_embeddings(records, jsonl_path, profile_dir, model_name)

    return embs, model


def _retrieve_st(records, jsonl_path, profile_dir, model_name, section, topic, k):
    """Sentence-transformers retrieval. Returns top-K (score, record) for the
    section, ranked by cosine similarity to topic."""
    import numpy as np
    embs, model = _build_or_load_embeddings(
        records, jsonl_path, profile_dir, model_name
    )
    q = model.encode(
        [topic or section],
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")[0]

    # Cosine = dot product since both sides are L2-normalized
    sims = embs @ q

    # Filter to target section, then take top-K by similarity
    candidates = [
        (float(sims[i]), records[i])
        for i in range(len(records))
        if records[i].get("section") == section
    ]
    candidates.sort(key=lambda x: -x[0])
    return candidates[:k]


def _retrieve_fallback(records, section, topic, k):
    """Keyword-overlap fallback when sentence-transformers is unavailable.
    Strictly worse than ST retrieval; use only as a last resort."""
    topic_kws = {w.lower() for w in topic.split() if len(w) > 3}
    scored = []
    for rec in records:
        if rec.get("section") != section:
            continue
        text_lc = rec.get("text", "").lower()
        score = sum(1 for kw in topic_kws if kw in text_lc)
        scored.append((float(score), rec))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def _format_exemplar(idx: int, total: int, score: float, rec: dict, mode: str) -> str:
    header = (
        f"=== Exemplar {idx}/{total}  ({mode}={score:.3f}, "
        f"section={rec['section']}, tier={rec['tier']}, "
        f"source={rec['source']}) ==="
    )
    return f"{header}\n{rec['text']}\n"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--section", required=True, choices=sorted(VALID_SECTIONS))
    p.add_argument("--topic", default="",
                   help="One-sentence topic summary. Empty → rank by section "
                        "name alone, which still surfaces representative "
                        "paragraphs.")
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--field", default=None,
                   help="Field name; auto-detected when only one exists.")
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--model", default=DEFAULT_MODEL,
                   help=f"sentence-transformers model name "
                        f"(default: {DEFAULT_MODEL}).")
    p.add_argument(
        "--allow-fallback",
        action="store_true",
        help="If sentence-transformers is not installed, fall back to "
             "naive topic-keyword overlap instead of erroring. "
             "Strictly worse retrieval.",
    )
    args = p.parse_args(argv)

    # Guarded because the retrieval helpers slice `candidates[:k]`, where k <= 0
    # is a silent wrong answer rather than an error: --k 0 returned an empty
    # list that surfaced as "No paragraphs in section=..." (a false claim about
    # the bank), and a small negative k returned all-but-the-last exemplar with
    # no diagnostic at all.
    if args.k < 1:
        print(f"[retrieve_exemplars] --k must be >= 1 (got {args.k}).",
              file=sys.stderr)
        return 2

    field = resolve_field(args.field, args.profile_root)
    field_profile_dir = args.profile_root / field
    bank = field_profile_dir / "exemplar_paragraphs.jsonl"

    if not bank.exists():
        print(
            f"[retrieve_exemplars] {bank} not found.\n"
            f"Run `python tools/extract_style.py --field {field}` first.",
            file=sys.stderr,
        )
        return 2

    records = _load_records(bank)
    if not records:
        print(f"[retrieve_exemplars] {bank} is empty.", file=sys.stderr)
        return 1

    # Try ST path first
    try:
        results = _retrieve_st(
            records, bank, field_profile_dir, args.model,
            args.section, args.topic, args.k,
        )
        mode = "cosine"
    except ImportError as e:
        if not args.allow_fallback:
            print(
                f"[retrieve_exemplars] sentence-transformers not installed "
                f"({e.name}). Install with:\n"
                f"    pip install sentence-transformers\n"
                f"or pass --allow-fallback to use naive keyword overlap "
                f"(strictly worse).",
                file=sys.stderr,
            )
            return 3
        print(
            f"[retrieve_exemplars] sentence-transformers unavailable; "
            f"falling back to keyword overlap.",
            file=sys.stderr,
        )
        results = _retrieve_fallback(records, args.section, args.topic, args.k)
        mode = "kw-overlap"

    if not results:
        print(
            f"[retrieve_exemplars] No paragraphs in section={args.section!r}. "
            f"Available sections: "
            f"{sorted({r['section'] for r in records})}",
            file=sys.stderr,
        )
        return 1

    for i, (score, rec) in enumerate(results, start=1):
        print(_format_exemplar(i, len(results), score, rec, mode))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
