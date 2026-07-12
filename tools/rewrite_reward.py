"""rewrite_reward.py — best-of-N reward for the /rewrite-in-voice rewriter (Layer C).

Given N candidate rewrites of a paragraph and the CLAIM that paragraph must
preserve, ranks the candidates so the `/sci-paper:rewrite-in-voice` selector can
pick the best. The reward is DELIBERATELY multi-term so the optimizer targets
genuine human voice AND meaning / specificity preservation — never
detector-evasion (docs/DEAI_SUBSYSTEM.md guardrail 3; the AuthorMist->Pangram
DAMAGE lesson: optimizing bare detector-score yields text that reads worse and
loses the arms race).

Terms (all reuse existing tooling so they match the corpus):
  voice        deai_voice P(human) from the learned voice model (Layer D). This
               single term already folds in Layer A burstiness (sent_len_cv) and
               Layer B surprisal/UID, since those are its input features.
  fidelity     cosine(embed(cand), embed(reference)) — meaning preserved.
  specificity  fraction of the reference's concrete numbers the candidate keeps.

The `reference` MUST be the distilled CLAIM (from the claim-graph, Step 1 of the
skill), NOT the padded original paragraph. Whole-paragraph cosine to a padded AI
original conflates de-padding with meaning-drift: measured 2026-07-11, a faithful
de-padded rewrite scored only 0.30 against the padded original (drift 0.26, i.e.
indistinguishable) but 0.55 against the claim (drift 0.30, cleanly separated).

Ranking (relative, calibration-free — guardrail 1 forbids absolute thresholds):
  1. fidelity gate is RELATIVE to the batch: a candidate is "faithful" iff its
     fidelity is within FIDELITY_BAND cosine of the most-faithful candidate. So
     genuinely faithful candidates (clustered high) all pass; a drifted one
     (much lower) is demoted — without ever hardcoding an absolute cosine floor,
     which is brittle across genres/embedders.
  2. faithful candidates score `voice * (0.5 + 0.5 * specificity)`; a candidate
     that washed out the numbers is halved, so it cannot beat a specific one.
  3. demoted (drifted) candidates get a tiny `0.05 * fidelity` — ranked below
     every faithful candidate, so meaning-drift can never win on voice alone.

CLI:  python tools/rewrite_reward.py --field wgl --reference claim.txt \
          --candidates c1.txt c2.txt c3.txt          # ranks + prints best
Lib:  from rewrite_reward import reward, rank
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as df   # noqa: E402  because resolves only after the sys.path insert
import deai_voice as dv      # noqa: E402  because resolves only after the sys.path insert

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

# Relative fidelity band (cosine units): a candidate within this much of the
# most-faithful candidate in the batch counts as faithful. RELATIVE, not an
# absolute floor — MiniLM paragraph cosines are low and genre-dependent, so an
# absolute threshold is brittle (guardrail 1). 0.15 separates the measured
# faithful/drift gap (claim-anchored: 0.55 vs 0.30) with margin to spare.
FIDELITY_BAND = 0.15
_NUM_RE = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    """Concrete numeric tokens (counts, values, percentages), sans equation guts.
    Reused for specificity: a rewrite must keep the claim's hard numbers."""
    plain = df.es.latex_to_plain(text)
    return set(_NUM_RE.findall(plain))


def _cosine(a_text: str, b_text: str) -> float:
    import numpy as np
    emb = df._embedder().encode(
        [df.es.latex_to_plain(a_text), df.es.latex_to_plain(b_text)],
        normalize_embeddings=True)
    return float(np.dot(emb[0], emb[1]))


def reward(candidate: str, reference: str, field_profile_dir: Path,
           centroid=None) -> dict:
    """Raw reward terms for one candidate vs the CLAIM it must preserve.

    Returns voice, fidelity, specificity, n_num_ref, n_num_cand. `combined` is
    NOT set here — it needs the batch (relative fidelity gate); use rank()."""
    if centroid is None:
        centroid = df.corpus_centroid(field_profile_dir)
    voice = dv.voice_score(candidate, field_profile_dir, centroid=centroid)
    voice = 0.0 if voice is None else voice
    fidelity = _cosine(candidate, reference)
    nums_r, nums_c = _numbers(reference), _numbers(candidate)
    specificity = (len(nums_r & nums_c) / len(nums_r)) if nums_r else 1.0
    return {"voice": voice, "fidelity": fidelity, "specificity": specificity,
            "n_num_ref": len(nums_r), "n_num_cand": len(nums_c)}


def rank(candidates: list[str], reference: str, field_profile_dir: Path
         ) -> list[tuple[int, dict]]:
    """(index, reward-dict incl. 'combined') for every candidate, best first.

    The fidelity gate is relative to the batch (see FIDELITY_BAND): faithful
    candidates score voice*(0.5+0.5*specificity); drifted ones are demoted."""
    centroid = df.corpus_centroid(field_profile_dir)
    rs = [reward(c, reference, field_profile_dir, centroid) for c in candidates]
    max_fid = max((r["fidelity"] for r in rs), default=0.0)
    scored = []
    for i, r in enumerate(rs):
        faithful = r["fidelity"] >= max_fid - FIDELITY_BAND
        r["faithful"] = faithful
        r["combined"] = (r["voice"] * (0.5 + 0.5 * r["specificity"])
                         if faithful else 0.05 * r["fidelity"])
        scored.append((i, r))
    scored.sort(key=lambda t: t[1]["combined"], reverse=True)
    return scored


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--field", required=True)
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--reference", type=Path, required=True,
                   help="file with the CLAIM the paragraph must preserve "
                        "(from the claim-graph; NOT the padded original)")
    p.add_argument("--candidates", type=Path, nargs="+", required=True,
                   help="one file per candidate rewrite")
    args = p.parse_args(argv)
    field_dir = args.profile_root / args.field
    if dv.load_voice_model(field_dir) is None:
        print(f"[rewrite_reward] no voice_model.joblib in {field_dir}; train "
              f"with `python tools/train_voice_model.py --field {args.field}`.",
              file=sys.stderr)
        return 2
    reference = args.reference.read_text(encoding="utf-8", errors="replace")
    cands = [c.read_text(encoding="utf-8", errors="replace") for c in args.candidates]
    ranked = rank(cands, reference, field_dir)
    print(f"{'rank':>4} {'cand':>4} {'combined':>9} {'voice':>7} "
          f"{'fidelity':>9} {'spec':>6} {'faith':>6}  nums(r/c)")
    for pos, (idx, r) in enumerate(ranked, 1):
        print(f"{pos:>4} {idx:>4} {r['combined']:>9.3f} {r['voice']:>7.3f} "
              f"{r['fidelity']:>9.3f} {r['specificity']:>6.2f} "
              f"{str(r['faithful']):>6}  {r['n_num_ref']}/{r['n_num_cand']}  "
              f"{args.candidates[idx].name}")
    best_idx = ranked[0][0]
    print(f"\n[best] candidate {best_idx}: {args.candidates[best_idx].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
