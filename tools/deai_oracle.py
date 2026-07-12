"""Layer B surprisal and uniform-information-density (UID) evidence.

A local causal language model measures each token's surprisal. The resulting
mean, dispersion, and token-to-token variation describe information flow in a
paragraph. The tool compares those measurements with a curated reference corpus
for the same section type. It does not infer authorship, and a low-variation
paragraph is not independently a rewrite instruction.

Features per paragraph:
  mean_surprisal  -- mean -log p(token), a perplexity-related summary
  global_uid      -- standard deviation of per-token surprisal
  local_uid       -- mean absolute change between adjacent surprisals

Usage:
  # 1. build the curated reference (once per corpus; optional model runtime):
  python tools/deai_oracle.py --calibrate --field wgl [--model gpt2-large]
  # 2. score a draft (advisory):
  python tools/deai_oracle.py draft.tex --field wgl

DIAGNOSTIC only: findings remain advisories and the compatibility operating
point remains degraded until field-policy calibration is documented.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_feedback as feedback  # noqa: E402  shared finding contract
import deai_metrics as dm  # noqa: E402  resolves only after the sys.path insert above
import extract_style as es  # noqa: E402  same reason

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
BASELINE_NAME = "uid_baseline.json"

# Retained for compatibility with the recorded UID baseline and learned bundle.
# The model is configurable; model choice is part of measurement provenance.
DEFAULT_MODEL = "gpt2-large"
MIN_TOKENS = 25          # UID is unstable on very short spans
FLAG_Z = 1.3             # degraded compatibility heuristic, not calibrated policy

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
    """Cache per-section UID summaries for the curated reference corpus."""
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


def uid_axis_status(field_profile_dir: Path | None) -> dict:
    if load_baseline(field_profile_dir) is None:
        return feedback.axis_status(
            "L1.uid", "unmeasured", reason="uid_baseline.json is unavailable",
            detector="deai_oracle")
    return feedback.axis_status(
        "L1.uid", "degraded",
        reason="the compatibility z operating point has not yet been field-policy calibrated",
        detector="deai_oracle")


def uid_findings(
    text: str, field_profile_dir: Path | None, model_name: str | None = None,
    path: str | Path | None = None,
) -> list[dict]:
    """Structured UID findings with observed/reference values and provenance."""
    baseline = load_baseline(field_profile_dir)
    if baseline is None:
        return []
    model_name = model_name or baseline.get("model", DEFAULT_MODEL)
    findings: list[dict] = []
    lines = text.splitlines()
    for start, end, raw_label in dm.section_line_ranges(text):
        bucket = dm._bucket_for(raw_label)
        segment = "\n".join(lines[start - 1:end])
        for paragraph_start, paragraph_end, block in dm.paragraph_line_ranges(
                segment, start):
            plain = es.latex_to_plain(block)
            values = uid_features(token_surprisals(plain, model_name))
            if values is None:
                continue
            for key, label in (("global_uid", "surprisal variance"),
                               ("local_uid", "token-to-token jumps")):
                reference = _ref_for(baseline, bucket, key)
                mean, stdev = reference["mean"], reference["stdev"]
                if stdev <= 0:
                    continue
                z_score = (values[key] - mean) / stdev
                if z_score >= -FLAG_Z:
                    continue
                findings.append(feedback.make_finding(
                    kind="advisory", layer="L1", rule=f"uid-low:{bucket}",
                    scope="paragraph", line=paragraph_start, end_line=paragraph_end,
                    section=raw_label, path=path, detector="deai_oracle",
                    detector_version=model_name,
                    calibration_asset=BASELINE_NAME,
                    measurement_status="degraded", strength="ordinary",
                    observed={key: values[key], "z_score": z_score,
                              "token_count_minimum": MIN_TOKENS},
                    reference={"mean": mean, "stdev": stdev,
                               "section_bucket": bucket, "model": model_name,
                               "operating_point_z": -FLAG_Z,
                               "provenance": BASELINE_NAME},
                    normalized_distance=(-FLAG_Z) - z_score,
                    confidence={"value": min(1.0, reference.get("n", 0) / 30.0),
                                "basis": f"reference n={reference.get('n', 0)}"},
                    message=(f"Paragraph {label} is {values[key]:.2f} versus "
                             f"reference {mean:.2f}±{stdev:.2f} (z={z_score:+.1f})."),
                    action="Add source-backed specificity or vary phrasing only where the scientific argument permits.",
                    evidence=[key, round(values[key], 8), round(z_score, 8)],
                ))
                break
    return findings


def paragraph_hits(
    text: str, field_profile_dir: Path | None, model_name: str | None = None
) -> list[tuple[int, str, str]]:
    return feedback.tuple_hits(uid_findings(text, field_profile_dir, model_name))


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
                   help="Build the curated-reference UID summary and cache it "
                        "to style-profile/<field>/uid_baseline.json.")
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
    report = feedback.build_report(
        path=args.file,
        findings=uid_findings(text, field_dir, args.model, args.file),
        axes=[uid_axis_status(field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
