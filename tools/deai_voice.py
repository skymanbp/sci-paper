"""deai_voice.py — score paragraphs with the learned voice model (Layer D).

Loads style-profile/<field>/voice_model.joblib (trained by
train_voice_model.py on the FUNDAMENTAL features) and returns P(human) per
paragraph. This score is the *reward* the Layer C rewriter and the
self-distillation loop optimize toward: higher = reads more like a real
hand-written scientific paragraph.

  voice_score(text, field_dir) -> float in [0,1]   (P a human wrote it)
  paragraph_hits(text, field_dir) -> [(line, rule, msg)]  advisory flags for
      paragraphs whose P(human) is below --voice-threshold (default 0.5)

DIAGNOSTIC only (docs/DEAI_SUBSYSTEM.md guardrail 2). It flags paragraphs to
rewrite; it is never a pass/fail gate, and it is NEVER used to reward
detector-evasion — only to reward genuine human-voice + specificity.

CLI:  python tools/deai_voice.py draft.tex --field wgl
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as df   # noqa: E402  resolves only after the sys.path insert
import deai_metrics as dm    # noqa: E402  same reason
import extract_style as es   # noqa: E402  same reason

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
VOICE_THRESHOLD = 0.5
_MODEL_CACHE: dict = {}


def load_voice_model(field_profile_dir: Path | None):
    if field_profile_dir is None:
        return None
    key = str(field_profile_dir)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    path = field_profile_dir / "voice_model.joblib"
    if not path.exists():
        _MODEL_CACHE[key] = None
        return None
    import joblib
    bundle = joblib.load(path)
    _MODEL_CACHE[key] = bundle
    return bundle


def _p_human(bundle, feats_vec) -> float:
    import numpy as np
    clf, scaler = bundle["clf"], bundle["scaler"]
    x = scaler.transform(np.asarray([feats_vec], float))
    col = list(clf.classes_).index(1)  # class 1 = human
    return float(clf.predict_proba(x)[0, col])


def voice_score(text: str, field_profile_dir: Path | None,
                model_name: str | None = None, centroid=None) -> float | None:
    """P(human) for a paragraph, or None if no voice model / text too short."""
    bundle = load_voice_model(field_profile_dir)
    if bundle is None:
        return None
    model_name = model_name or bundle.get("model", df.do.DEFAULT_MODEL)
    if centroid is None and field_profile_dir is not None:
        centroid = df.corpus_centroid(field_profile_dir)
    vec = df.features_vector(text, field_profile_dir=field_profile_dir,
                             model_name=model_name, centroid=centroid)
    return _p_human(bundle, vec)


def paragraph_hits(text: str, field_profile_dir: Path | None,
                   threshold: float = VOICE_THRESHOLD) -> list[tuple[int, str, str]]:
    bundle = load_voice_model(field_profile_dir)
    if bundle is None:
        return []
    model_name = bundle.get("model", df.do.DEFAULT_MODEL)
    centroid = df.corpus_centroid(field_profile_dir)
    hits: list[tuple[int, str, str]] = []
    lines = text.splitlines()
    for start, end, raw_label in dm.section_line_ranges(text):
        bucket = dm._bucket_for(raw_label)
        seg = "\n".join(lines[start - 1:end])
        # blank-line paragraphs, tracking start line
        buf: list[str] = []; buf_start = start
        blocks: list[tuple[int, str]] = []
        for off, ln in enumerate(seg.splitlines()):
            if ln.strip():
                if not buf:
                    buf_start = start + off
                buf.append(ln)
            elif buf:
                blocks.append((buf_start, "\n".join(buf))); buf = []
        if buf:
            blocks.append((buf_start, "\n".join(buf)))
        for p_line, block in blocks:
            if len(es.words(es.latex_to_plain(block))) < 30:
                continue
            s = voice_score(block, field_profile_dir, model_name, centroid)
            if s is not None and s < threshold:
                hits.append((
                    p_line, f"voice-low:{bucket}",
                    f"paragraph ({bucket}): learned voice score P(human)={s:.2f} "
                    f"< {threshold:.2f} — reads machine-authored; rebuild in your "
                    f"own voice (specifics, varied rhythm, a defended claim).",
                ))
    return hits


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", type=Path)
    p.add_argument("--field", required=True)
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--voice-threshold", type=float, default=VOICE_THRESHOLD)
    p.add_argument("--scores", action="store_true",
                   help="print P(human) for every paragraph, not just flags")
    args = p.parse_args(argv)
    field_dir = args.profile_root / args.field
    if load_voice_model(field_dir) is None:
        print(f"[deai_voice] no voice_model.joblib in {field_dir}; train with "
              f"`python tools/train_voice_model.py --field {args.field}`.",
              file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    if args.scores:
        centroid = df.corpus_centroid(field_dir)
        for i, b in enumerate(x for x in re.split(r"\n\s*\n", text) if x.strip()):
            s = voice_score(b, field_dir, None, centroid)
            if s is not None:
                print(f"  para[{i}] P(human)={s:.3f}")
        return 0
    hits = paragraph_hits(text, field_dir, args.voice_threshold)
    if not hits:
        print(f"[deai_voice] {args.file}: 0 voice flags.")
        return 0
    print(f"[deai_voice] {args.file}: {len(hits)} voice flag(s)\n")
    for line_no, rule, msg in hits:
        print(f"  L{line_no:>5}  [{rule}]  {msg}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
