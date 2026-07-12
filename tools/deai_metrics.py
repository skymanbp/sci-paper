"""deai_metrics.py — model-free distributional de-AI scorer (Layer A).

The fundamental AI-vs-human signal is the DISTRIBUTION of information across
the text, not any word list. This scorer compares a draft's per-section
distributions to the human corpus reference
(`style-profile/<field>/{sentence_stats,transition_inventory}.json`) and
emits calibrated, DIAGNOSTIC flags. It is NOT a hard gate — see
`docs/DEAI_SUBSYSTEM.md` guardrail 2 (formal science prose false-positives
on absolute thresholds, and detector-evasion is an arms race).

It reuses `extract_style.py`'s tokenizers (`sentences`, `words`,
`paragraph_initial_words`, `latex_to_plain`, `classify_section`) so a draft's
distributions are byte-for-byte comparable to how the corpus reference was
built. No re-implementation of the canonical tokenizers.

Signals (all calibrated to the human reference for the section's genre):

  [burstiness-low:<bucket>]   — the section's sentence-length coefficient of
                                variation (stdev/mean) is well below the human
                                corpus's for that genre. AI prose is smoothed
                                to uniform sentence length; humans are bursty.
  [opener-signposting:<bucket>] — too large a fraction of the section's
                                paragraphs open with a connective
                                (Furthermore / Moreover / However / ...). The
                                human corpus opens paragraphs this way ~0.2 %
                                of the time; over-signposting is a structural
                                AI tell.

Both are 🟡 diagnostics: they tell the writer WHICH sections to vary, they
do not fail a convergence gate.

Standalone:  python tools/deai_metrics.py draft.tex [--field wgl]
Library:     from deai_metrics import distribution_hits
             hits = distribution_hits(text, field_profile_dir)   # [(line,rule,msg)]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

# Reuse the canonical tokenizers so a draft's distributions match the corpus
# builder exactly. The sys.path insert must precede the import because
# extract_style is a sibling module in tools/, not an installed package, so
# the import below is intentionally after it (E402 is expected here).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_style as es  # noqa: E402  because extract_style resolves only after the sys.path insert above

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

# Section header scan (line-numbered) — same shape as extract_style.RE_SECTION
# but kept local so this module has no circular import with ai_ism_lint.
RE_SECTION_HEADER = re.compile(
    r"\\(section|subsection|chapter)\*?\{([^}]+)\}", re.IGNORECASE
)

# Connectives that read as over-signposting when they OPEN a paragraph.
# Structural openers a human uses freely (Finally, First, Another, Overall as
# a genuine summary lead) are deliberately excluded; these are the AI ones.
CONNECTIVE_OPENERS = frozenset({
    "furthermore", "moreover", "additionally", "however", "therefore",
    "thus", "hence", "consequently", "nevertheless", "nonetheless",
    "notably", "importantly", "interestingly", "crucially", "indeed",
    "similarly", "likewise", "conversely", "meanwhile", "subsequently",
    "accordingly", "besides",
})

# Calibration constants (soft, diagnostic). Documented, not magic:
BURSTINESS_RATIO = 0.60   # flag if draft CV < 0.60 x human CV for the genre
MIN_SENTENCES = 5         # need enough sentences for a stable CV
SIGNPOST_FRAC = 0.20      # flag if >20% of paragraph openers are connectives
MIN_PARAGRAPHS = 3        # ... and the section has at least a few paragraphs


def load_reference(field_profile_dir: Path | None) -> dict | None:
    """Load {cv, pooled_cv, corpus_signpost} from the profile, or None."""
    if field_profile_dir is None:
        return None
    ss = field_profile_dir / "sentence_stats.json"
    if not ss.exists():
        return None
    try:
        sent = json.loads(ss.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    ti_path = field_profile_dir / "transition_inventory.json"
    trans = {}
    if ti_path.exists():
        try:
            trans = json.loads(ti_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            trans = {}
    # Per-genre human CV, excluding the noisy "unknown" bucket.
    cv = {}
    for bucket, s in sent.items():
        if bucket == "unknown":
            continue
        m, sd = s.get("mean", 0), s.get("stdev", 0)
        if m > 0:
            cv[bucket] = sd / m
    pooled_cv = statistics.median(cv.values()) if cv else 0.55
    # Corpus paragraph-opener connective rate (context for the message).
    n_par = trans.get("n_paragraphs", 0)
    present = trans.get("blacklist_present_in_corpus", [])
    conn_par = sum(c for _, c in present) if present else 0
    corpus_signpost = (conn_par / n_par) if n_par else 0.0
    return {"cv": cv, "pooled_cv": pooled_cv, "corpus_signpost": corpus_signpost}


def section_line_ranges(text: str) -> list[tuple[int, int, str]]:
    """[(start_line, end_line, raw_label)] over \\section headers. Whole doc
    as one range if there are none."""
    lines = text.splitlines()
    if not lines:
        return []
    heads: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        m = RE_SECTION_HEADER.search(line)
        if m:
            heads.append((i, m.group(2).strip()))
    if not heads:
        return [(1, len(lines), "(document)")]
    out: list[tuple[int, int, str]] = []
    if heads[0][0] > 1:
        out.append((1, heads[0][0] - 1, "(preamble)"))
    for idx, (start, name) in enumerate(heads):
        end = heads[idx + 1][0] - 1 if idx + 1 < len(heads) else len(lines)
        out.append((start, end, name))
    return out


def _bucket_for(raw_label: str) -> str:
    try:
        return es.classify_section(raw_label)
    except Exception:
        return "unknown"


def _sentence_lengths(plain: str) -> list[int]:
    return [len(es.words(s)) for s in es.sentences(plain) if es.words(s)]


def distribution_hits(
    text: str, field_profile_dir: Path | None
) -> list[tuple[int, str, str]]:
    """Return [(line_no, rule, message)] diagnostic hits. Empty if no
    reference profile is available (graceful, like the corpus blacklist)."""
    ref = load_reference(field_profile_dir)
    if ref is None:
        return []
    hits: list[tuple[int, str, str]] = []
    lines = text.splitlines()
    for start, end, raw_label in section_line_ranges(text):
        seg = "\n".join(lines[start - 1:end])
        plain = es.latex_to_plain(seg)
        bucket = _bucket_for(raw_label)
        ref_cv = ref["cv"].get(bucket, ref["pooled_cv"])

        # --- burstiness (sentence-length CV) ---
        lens = _sentence_lengths(plain)
        if len(lens) >= MIN_SENTENCES:
            m = statistics.mean(lens)
            sd = statistics.pstdev(lens)
            draft_cv = sd / m if m else 0.0
            if ref_cv > 0 and draft_cv < BURSTINESS_RATIO * ref_cv:
                hits.append((
                    start,
                    f"burstiness-low:{bucket}",
                    f"section {raw_label!r} ({bucket}): sentence-length CV "
                    f"{draft_cv:.2f} vs human {ref_cv:.2f} "
                    f"(ratio {draft_cv / ref_cv:.2f}, n={len(lens)}) — "
                    f"vary sentence lengths (mix short punchy + long).",
                ))

        # --- opener over-signposting ---
        openers = es.paragraph_initial_words(plain)
        if len(openers) >= MIN_PARAGRAPHS:
            n_conn = sum(1 for w in openers if w.lower() in CONNECTIVE_OPENERS)
            frac = n_conn / len(openers)
            if frac > SIGNPOST_FRAC:
                hits.append((
                    start,
                    f"opener-signposting:{bucket}",
                    f"section {raw_label!r} ({bucket}): {n_conn}/{len(openers)} "
                    f"paragraphs ({frac:.0%}) open with a connective vs "
                    f"~{ref['corpus_signpost']:.1%} in the human corpus — "
                    f"let logical flow carry the reader; cut roadmap openers.",
                ))
    return hits


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", type=Path)
    p.add_argument("--field", default=None)
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    args = p.parse_args(argv)

    if not args.file.exists():
        print(f"[deai_metrics] file not found: {args.file}", file=sys.stderr)
        return 2
    # Field auto-detect: single field dir, else require --field.
    field_dir = None
    if args.field:
        field_dir = args.profile_root / args.field
    else:
        fields = [d for d in args.profile_root.iterdir()
                  if d.is_dir() and not d.name.startswith(".")] \
            if args.profile_root.exists() else []
        if len(fields) == 1:
            field_dir = fields[0]
    text = args.file.read_text(encoding="utf-8", errors="replace")
    hits = distribution_hits(text, field_dir)
    if not hits:
        print(f"[deai_metrics] {args.file}: 0 distributional flags.")
        return 0
    print(f"[deai_metrics] {args.file}: {len(hits)} distributional flag(s)\n")
    for line_no, rule, msg in hits:
        print(f"  L{line_no:>5}  [{rule}]  {msg}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
