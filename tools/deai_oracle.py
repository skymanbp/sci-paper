"""deai_oracle.py — Layer B: surprisal / Uniform-Information-Density oracle.

The single deepest AI-vs-human signal is the DISTRIBUTION of per-token
surprisal (information content). Human scientific prose is *bursty*: high
surprisal variance, large jumps between consecutive tokens, words drawn from
the model's tail. LLM prose is smoothed toward Uniform Information Density
(UID) and the model's own high-probability region. This module computes that
signal with a local causal LM and flags paragraphs whose UID sits below the
human corpus reference for their genre.

Features per paragraph (GPT-who / UID literature, arXiv 2310.06202 & 2109.11635):
  mean_surprisal  -- mean -log p(token)  (perplexity proxy)
  global_uid      -- stdev of per-token surprisal   (HUMAN high, AI low)
  local_uid       -- mean |surprisal[i] - surprisal[i-1]|  (HUMAN high, AI low)

Usage:
  # 1. build the human reference (once per corpus; GPU):
  python tools/deai_oracle.py --calibrate --field wgl [--model gpt2]
  # 2. score a draft (advisory):
  python tools/deai_oracle.py draft.tex --field wgl

Library:
  from deai_oracle import paragraph_hits
  hits = paragraph_hits(text, field_profile_dir)   # [(line, rule, msg)]

DIAGNOSTIC only (docs/DEAI_SUBSYSTEM.md guardrail 2): flags WHICH paragraphs
read as mechanically uniform; never a pass/fail gate. Off by default in
ai_ism_lint (needs a model + GPU); opt in with --oracle there.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_metrics as dm  # noqa: E402  resolves only after the sys.path insert above
import extract_style as es  # noqa: E402  same reason

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
BASELINE_NAME = "uid_baseline.json"

# gpt2-large (774M) separates human vs LLM surprisal markedly better than
# gpt2 (124M) on formal science prose — measured 2026-07-11: an LLM-style
# paragraph's global_uid was 2.73 vs human 3.4-6.2 under gpt2-large, a much
# cleaner gap than gpt2's. The detection literature uses 2.7B-7B scoring
# models; gpt2-large is the quality/speed knee for a local, always-available
# oracle. Override with --model (e.g. a 1-3B model) for still-better signal.
DEFAULT_MODEL = "gpt2-large"
MIN_TOKENS = 25          # UID is noisy on short spans
FLAG_Z = 1.3             # flag if a UID feature is >1.3 sigma below human mean

_MODEL_CACHE: dict[str, tuple] = {}


def _get_model(model_name: str):
    """Load (tokenizer, model, device); cached. Imports torch lazily so the
    rest of the plugin never pays for it."""
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device).eval()
    _MODEL_CACHE[model_name] = (tok, model, device)
    return tok, model, device


def token_surprisals(text: str, model_name: str = DEFAULT_MODEL) -> list[float]:
    """Per-token surprisal (-log p, natural log) of `text` under the LM.
    Empty list if fewer than 2 tokens."""
    import torch
    tok, model, device = _get_model(model_name)
    ids = tok(text, return_tensors="pt", truncation=True,
              max_length=model.config.max_position_embeddings)["input_ids"].to(device)
    if ids.shape[1] < 2:
        return []
    with torch.no_grad():
        logits = model(ids).logits  # [1, T, V]
    # logits[:, i] predicts token i+1 -> surprisal of token i+1.
    logp = torch.log_softmax(logits[:, :-1, :].float(), dim=-1)
    targets = ids[:, 1:]
    surp = -logp.gather(-1, targets.unsqueeze(-1)).squeeze(-1)  # [1, T-1]
    return surp.squeeze(0).cpu().tolist()


def uid_features(surp: list[float]) -> dict | None:
    """{mean_surprisal, global_uid, local_uid} or None if too short."""
    if len(surp) < MIN_TOKENS:
        return None
    mean = statistics.mean(surp)
    global_uid = statistics.pstdev(surp)
    local = [abs(surp[i] - surp[i - 1]) for i in range(1, len(surp))]
    local_uid = statistics.mean(local) if local else 0.0
    return {"mean_surprisal": mean, "global_uid": global_uid,
            "local_uid": local_uid}


# ---------------------------------------------------------------- calibrate --

def calibrate(field_profile_dir: Path, model_name: str = DEFAULT_MODEL) -> dict:
    """Run the LM over the corpus paragraphs, cache the human UID reference
    (per-section mean/stdev of global_uid & local_uid) -> uid_baseline.json."""
    exemplars = field_profile_dir / "exemplar_paragraphs.jsonl"
    if not exemplars.exists():
        raise FileNotFoundError(f"no exemplar_paragraphs.jsonl in {field_profile_dir}")
    FEATURES = ("global_uid", "local_uid", "mean_surprisal")
    by_bucket: dict[str, dict[str, list[float]]] = {}
    pooled: dict[str, list[float]] = {k: [] for k in FEATURES}
    n_used = 0
    with exemplars.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            text = rec.get("text", "")
            bucket = rec.get("section", "unknown")
            feats = uid_features(token_surprisals(text, model_name))
            if feats is None:
                continue
            n_used += 1
            b = by_bucket.setdefault(bucket, {k: [] for k in FEATURES})
            for key in FEATURES:
                b[key].append(feats[key])
                pooled[key].append(feats[key])

    def _ms(xs: list[float]) -> dict:
        if len(xs) < 2:
            return {"mean": (xs[0] if xs else 0.0), "stdev": 0.0, "n": len(xs)}
        return {"mean": statistics.mean(xs), "stdev": statistics.pstdev(xs),
                "n": len(xs)}

    baseline = {
        "model": model_name,
        "min_tokens": MIN_TOKENS,
        "n_paragraphs_used": n_used,
        "pooled": {k: _ms(v) for k, v in pooled.items()},
        "by_section": {
            bucket: {k: _ms(v) for k, v in feats.items()}
            for bucket, feats in by_bucket.items()
        },
    }
    out = field_profile_dir / BASELINE_NAME
    out.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    return baseline


def load_baseline(field_profile_dir: Path | None) -> dict | None:
    if field_profile_dir is None:
        return None
    p = field_profile_dir / BASELINE_NAME
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# ------------------------------------------------------------------- score --

def _ref_for(baseline: dict, bucket: str, key: str) -> dict:
    sec = baseline.get("by_section", {}).get(bucket)
    if sec and sec.get(key, {}).get("n", 0) >= 5:
        return sec[key]
    return baseline.get("pooled", {}).get(key, {"mean": 0.0, "stdev": 0.0})


def paragraph_hits(
    text: str, field_profile_dir: Path | None, model_name: str | None = None
) -> list[tuple[int, str, str]]:
    """Return [(line_no, rule, message)] for paragraphs whose UID is below the
    human corpus reference. Empty if no baseline (call --calibrate first)."""
    baseline = load_baseline(field_profile_dir)
    if baseline is None:
        return []
    model_name = model_name or baseline.get("model", DEFAULT_MODEL)
    hits: list[tuple[int, str, str]] = []
    lines = text.splitlines()
    for start, end, raw_label in dm.section_line_ranges(text):
        bucket = dm._bucket_for(raw_label)
        seg = "\n".join(lines[start - 1:end])
        # paragraph = blank-line separated block; keep its start line for the hit
        line_no = start
        buf: list[str] = []
        buf_start = start
        blocks: list[tuple[int, str]] = []
        for off, ln in enumerate(seg.splitlines()):
            cur = start + off
            if ln.strip():
                if not buf:
                    buf_start = cur
                buf.append(ln)
            elif buf:
                blocks.append((buf_start, "\n".join(buf)))
                buf = []
        if buf:
            blocks.append((buf_start, "\n".join(buf)))

        for p_line, block in blocks:
            plain = es.latex_to_plain(block)
            feats = uid_features(token_surprisals(plain, model_name))
            if feats is None:
                continue
            for key, human_label in (("global_uid", "surprisal variance"),
                                     ("local_uid", "token-to-token jumps")):
                ref = _ref_for(baseline, bucket, key)
                mu, sd = ref["mean"], ref["stdev"]
                if sd <= 0:
                    continue
                z = (feats[key] - mu) / sd
                if z < -FLAG_Z:
                    hits.append((
                        p_line,
                        f"uid-low:{bucket}",
                        f"paragraph ({bucket}): {human_label} "
                        f"{feats[key]:.2f} vs human {mu:.2f}±{sd:.2f} "
                        f"(z={z:+.1f}) — reads as uniform/low-surprisal; add "
                        f"specificity and vary phrasing, don't smooth it.",
                    ))
                    break  # one flag per paragraph is enough
    return hits


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", type=Path, nargs="?")
    p.add_argument("--field", default=None)
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--model", default=None,
                   help=f"HF causal LM for surprisal (default {DEFAULT_MODEL} / "
                        "the model recorded in uid_baseline.json).")
    p.add_argument("--calibrate", action="store_true",
                   help="Build the human UID reference from the corpus and "
                        "cache it to style-profile/<field>/uid_baseline.json.")
    args = p.parse_args(argv)

    # Resolve field dir.
    field_dir = None
    if args.field:
        field_dir = args.profile_root / args.field
    elif args.profile_root.exists():
        fields = [d for d in args.profile_root.iterdir()
                  if d.is_dir() and not d.name.startswith(".")]
        if len(fields) == 1:
            field_dir = fields[0]
    if field_dir is None:
        print("[deai_oracle] need --field (multiple/zero profiles).", file=sys.stderr)
        return 2

    if args.calibrate:
        model_name = args.model or DEFAULT_MODEL
        print(f"[deai_oracle] calibrating UID baseline on {field_dir.name} "
              f"with {model_name} ...", file=sys.stderr)
        b = calibrate(field_dir, model_name)
        print(f"[deai_oracle] baseline written: {b['n_paragraphs_used']} "
              f"paragraphs, {len(b['by_section'])} sections, model {b['model']}.")
        for sec, feats in sorted(b["by_section"].items()):
            g, l = feats["global_uid"], feats["local_uid"]
            print(f"  {sec:12s} global_uid {g['mean']:.2f}±{g['stdev']:.2f} "
                  f"local_uid {l['mean']:.2f}±{l['stdev']:.2f} (n={g['n']})")
        return 0

    if not args.file or not args.file.exists():
        print("[deai_oracle] pass a draft file to score, or --calibrate.",
              file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    hits = paragraph_hits(text, field_dir, args.model)
    if not hits:
        if load_baseline(field_dir) is None:
            print(f"[deai_oracle] no uid_baseline.json in {field_dir}; run "
                  f"--calibrate first.", file=sys.stderr)
            return 2
        print(f"[deai_oracle] {args.file}: 0 UID flags.")
        return 0
    print(f"[deai_oracle] {args.file}: {len(hits)} UID flag(s)\n")
    for line_no, rule, msg in hits:
        print(f"  L{line_no:>5}  [{rule}]  {msg}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
