"""ai_ism_lint.py — extended anti-AI-ism linter (v0.1).

Tiered output (matches `/sci-paper:paper` Anti-AI-isms section):

- `[em-dash]`       — em-dash residue. Convergence: 0.
- `[tier-a:<word>]` — zero-tolerance words (delve, leverages, pave, shed,
                      seamless, holistic, ...). Corpus 0 occurrences.
- `[tier-a:opener]` — paragraph-start boilerplate (Recent advances in,
                      Despite significant progress, In recent years, ...).
- `[tier-a:paragraph-start:<W>]` — paragraph-initial LLM connectors
                      (Furthermore, Moreover, Additionally, Importantly,
                      Interestingly, Notably, Crucially) at line start.
- `[tier-b:<word>]` — frequency-capped (furthermore, moreover, robust,
                      comprehensive, utilize, leverage). Corpus uses
                      sparingly; >1 hit per section needs review.
- `[stubborn:<word>]` — purely-stylistic substitutions (in order to →
                      to, aim to → direct verb, facilitate → enable).
- `[three-parallel]` — "not only X, but also Y, and furthermore Z".
- `[corpus-blacklist:<word>]` — words with ZERO occurrences in
                      `style-profile/<field>/lexicon.json` (auto-derived).
- `[ai-ish:<score>]` — opt-in via --ai-classifier. Paragraph-level
                      P(LLM-style) ≥ --ai-threshold (default 0.7) per the
                      logistic-regression model at
                      `style-profile/<field>/ai_ism_classifier.joblib`.
                      Soft signal that supplements regex hits.
- `[burstiness-low:<bucket>]` / `[opener-signposting:<bucket>]` — Layer A
                      distributional diagnostics (default on; --no-distribution
                      to disable) from `deai_metrics.py`: a section's
                      sentence-length variance is below, or its paragraph-opener
                      connective rate above, the corpus reference for that
                      genre. ADVISORY — reported but never affects the exit
                      code (a fundamental-signal diagnostic, not a keyword gate).

Output: line-numbered keyword hits to stdout, exit code 0 if zero KEYWORD
hits, 1 otherwise. Distributional diagnostics are advisory and do not change
the exit code.

Optional `--summary` adds an aggregate breakdown after the per-line list:
counts by rule, Tier B density per `\\section{}`, and a verdict line. The
verdict counts excess-Tier-B hits (>1 per section per word) as 🟡.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

# Layer A distributional scorer lives in the same tools/ dir. The sys.path
# insert lets `import deai_metrics` resolve whether ai_ism_lint is run as a
# script or imported; the import is deliberately after it (E402 expected).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_metrics  # noqa: E402  because deai_metrics resolves only after the sys.path insert above


def list_fields(profile_root: Path) -> list[str]:
    if not profile_root.exists():
        return []
    return sorted(
        p.name for p in profile_root.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def resolve_field(arg_field: str | None, profile_root: Path) -> str | None:
    """Same auto-detect rules as extract_style.py, but returns None instead
    of erroring when no field exists (lint can run without a corpus profile —
    it just falls back to hand-written rules)."""
    fields = list_fields(profile_root)
    if arg_field:
        if arg_field not in fields:
            print(
                f"[ai_ism_lint] --field={arg_field!r} not found under "
                f"{profile_root}/. Available: {fields or '(none)'}. "
                "Falling back to hand-written rules only.",
                file=sys.stderr,
            )
            return None
        return arg_field
    if not fields:
        return None
    if len(fields) > 1:
        print(
            f"[ai_ism_lint] Multiple fields present ({fields}); pass "
            f"--field=<name> to use corpus-derived rules. Falling back to "
            "hand-written rules only.",
            file=sys.stderr,
        )
        return None
    return fields[0]

# Hand-written rules — kept aligned with /sci-paper:paper Anti-AI-isms.
# Tiers are based on corpus dossier evidence (style_dossier.md §3, §4).

EM_DASH_PATTERN = re.compile(r"—|---|\\textemdash")

# Tier A: words with ZERO occurrences in the WGL corpus.
# Singular `leverage` and `utilize` / `utilized` are NOT here (corpus has
# 1 / 3 / 1 occurrences respectively); they live in Tier B.
TIER_A_PATTERN = re.compile(
    r"(?i)\b(?:"
    r"delves?|delving|delved|"
    r"leverages|leveraging|leveraged|"
    r"paves?|paving|"
    r"sheds?|shedding|"  # also covers "shed light on" / "sheds light on"
    r"showcases?|showcasing|"
    r"utiliz(?:ing|es)|"
    r"seamless(?:ly)?|"
    r"holistic(?:ally)?|"
    r"comprehensively|"
    r"crucially"
    r")\b"
)

# Tier A paragraph-start boilerplate (corpus dossier §3 → 0 paragraph-initial).
TIER_A_OPENER_PATTERN = re.compile(
    r"(?i)^\s*(?:"
    r"recent advances in|"
    r"despite significant progress|"
    r"with the advent of|"
    r"in recent years|"
    r"it is worth noting"
    r")"
)

# Tier A paragraph-initial LLM connectors. Same words mid-sentence are
# Tier B (capped frequency). At line start, treat as Tier A — corpus uses
# them this way at most 1-3 times across the whole corpus (dossier §3).
TIER_A_PARAGRAPH_CONNECTOR_PATTERN = re.compile(
    r"(?i)^\s*(Furthermore|Moreover|Additionally|Importantly|"
    r"Interestingly|Notably|Crucially),"
)

# Tier B: corpus-attested but capped frequency. Each hit needs human
# audit for per-section density (>1 per section → 🟡 per /paper rules).
TIER_B_PATTERN = re.compile(
    r"(?i)\b(?:"
    r"furthermore|moreover|additionally|"
    r"robust(?:ly)?|comprehensive|"
    r"utilize|utilized|leverage|"
    r"importantly|interestingly|notably"
    r")\b"
)

# Stubborn purely-stylistic replacements (always wrong; not tier-graded).
STUBBORN_REPLACE_PATTERN = re.compile(
    r"(?i)\b(?:in order to|aim to|facilitate)\b"
)

# Sentence-level structural tells.
THREE_PARALLEL_PATTERN = re.compile(
    r"(?i)not only.+but also.+(?:and|furthermore|moreover)"
)

# For --summary section-density: same shape as extract_style.RE_SECTION.
# Inlined (not imported) to keep ai_ism_lint a self-contained linter.
RE_SECTION_HEADER = re.compile(
    r"\\(section|subsection|chapter)\*?\{([^}]+)\}", re.IGNORECASE
)


def load_corpus_blacklist(field_profile_dir: Path) -> set[str]:
    """Words from the corpus lexicon with ZERO occurrences = corpus-forbidden."""
    lex = field_profile_dir / "lexicon.json"
    if not lex.exists():
        return set()
    try:
        data = json.loads(lex.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return set(data.get("llm_words_absent_from_corpus", []))


def load_ai_classifier(field_profile_dir: Path | None):
    """Load the pickled AI-ism classifier from
    `style-profile/<field>/ai_ism_classifier.joblib`. Returns None if no
    field profile / no model file. Raises ImportError if joblib is missing.
    """
    if field_profile_dir is None:
        return None
    model_path = field_profile_dir / "ai_ism_classifier.joblib"
    if not model_path.exists():
        return None
    import joblib
    return joblib.load(model_path)


def paragraph_ranges(text: str) -> list[tuple[int, int, str]]:
    """Split file into paragraphs (blank-line separated). Returns
    [(start_line, end_line, text), ...] where lines are 1-based."""
    out: list[tuple[int, int, str]] = []
    lines = text.splitlines()
    cur: list[str] = []
    cur_start = 1
    for i, line in enumerate(lines, start=1):
        if line.strip():
            if not cur:
                cur_start = i
            cur.append(line)
        else:
            if cur:
                out.append((cur_start, i - 1, "\n".join(cur)))
                cur = []
    if cur:
        out.append((cur_start, len(lines), "\n".join(cur)))
    return out


def score_paragraphs(clf, paragraphs: list[tuple[int, int, str]]) -> list[float]:
    """Return P(AI-ish) ∈ [0,1] for each paragraph. Class 1 = AI-ish per
    train_ai_ism_classifier.py's label encoding."""
    if not paragraphs:
        return []
    texts = [p[2] for p in paragraphs]
    proba = clf.predict_proba(texts)
    # proba columns are ordered by clf.classes_; class 1 = AI-ish.
    classes = list(clf.classes_)
    if 1 in classes:
        col = classes.index(1)
    else:
        col = -1  # fallback: last column
    return [float(row[col]) for row in proba]


def section_ranges(text: str) -> list[tuple[int, int, str]]:
    """Return [(start_line, end_line, section_label), ...] covering all lines.

    Splits the file at every \\section / \\subsection / \\chapter header.
    If the file has no such headers, returns a single (1, n_lines, label) range
    so the caller still gets a meaningful bucket.
    """
    lines = text.splitlines()
    if not lines:
        return [(1, 1, "(empty)")]
    headers: list[tuple[int, str]] = []
    for i, line in enumerate(lines, start=1):
        m = RE_SECTION_HEADER.search(line)
        if m:
            label = m.group(2).strip()
            if len(label) > 40:
                label = label[:37] + "..."
            headers.append((i, label))
    if not headers:
        return [(1, len(lines), "(no \\section{} headers)")]
    out: list[tuple[int, int, str]] = []
    # Pre-section preamble (if any) gets its own bucket.
    if headers[0][0] > 1:
        out.append((1, headers[0][0] - 1, "(preamble)"))
    for idx, (start, name) in enumerate(headers):
        end = headers[idx + 1][0] - 1 if idx + 1 < len(headers) else len(lines)
        out.append((start, end, name))
    return out


def section_for_line(line_no: int, ranges: list[tuple[int, int, str]]) -> str:
    """Map a 1-based line number to its containing section label."""
    for s, e, name in ranges:
        if s <= line_no <= e:
            return name
    return "(unknown)"


def summarize(
    hits: list[tuple[int, str, str]],
    text: str,
) -> int:
    """Print aggregate breakdown. Returns count of Tier B excess hits
    (occurrences over the per-section, per-word cap of 1)."""
    from collections import Counter, defaultdict

    by_rule: Counter[str] = Counter(rule for _, rule, _ in hits)

    # Group by tier prefix
    bucket_counts: dict[str, int] = defaultdict(int)
    for rule, n in by_rule.items():
        if rule == "em-dash":
            bucket_counts["em-dash"] += n
        elif rule.startswith("tier-a:paragraph-start:"):
            bucket_counts["tier-a:paragraph-start"] += n
        elif rule.startswith("tier-a:"):
            bucket_counts["tier-a"] += n
        elif rule.startswith("tier-b:"):
            bucket_counts["tier-b"] += n
        elif rule.startswith("stubborn:"):
            bucket_counts["stubborn"] += n
        elif rule == "three-parallel":
            bucket_counts["three-parallel"] += n
        elif rule.startswith("corpus-blacklist:"):
            bucket_counts["corpus-blacklist"] += n
        elif rule.startswith("ai-ish:"):
            bucket_counts["ai-ish"] += n
        else:
            bucket_counts["other"] += n

    print("=== summary ===")
    print("By tier:")
    severity_order = [
        ("em-dash", "🔴"),
        ("tier-a", "🔴"),
        ("tier-a:paragraph-start", "🔴"),
        ("tier-b", "🟡 (audit per-section density)"),
        ("stubborn", "🟡"),
        ("three-parallel", "🟡"),
        ("corpus-blacklist", "🔴 (corpus-derived; overlaps tier-a)"),
        ("ai-ish", "🟡 (classifier; soft signal — see [ai-ish:<score>] hits)"),
    ]
    for bucket, label in severity_order:
        n = bucket_counts.get(bucket, 0)
        if n > 0:
            print(f"  {bucket:30s} {n:>3d}  {label}")

    # Per-section Tier B density (cap = 1 per section per word).
    ranges = section_ranges(text)
    tier_b_density: dict[tuple[str, str], int] = defaultdict(int)
    for line_no, rule, _ in hits:
        if rule.startswith("tier-b:"):
            word = rule.split(":", 1)[1]
            sec = section_for_line(line_no, ranges)
            tier_b_density[(sec, word)] += 1

    excess = 0
    if tier_b_density:
        print("\nTier B density per section (cap = 1 occurrence/section/word):")
        # Sort: over-cap first, then by section name
        sorted_keys = sorted(
            tier_b_density.keys(),
            key=lambda k: (tier_b_density[k] <= 1, k[0], k[1]),
        )
        for (sec, word) in sorted_keys:
            n = tier_b_density[(sec, word)]
            flag = "  🟡 OVER CAP" if n > 1 else ""
            print(f"  [{sec}] {word}: {n}{flag}")
            if n > 1:
                excess += n - 1

    print()
    if excess:
        print(f"🟡  {excess} Tier B excess occurrence(s) over per-section cap.")
    if bucket_counts.get("em-dash", 0) or bucket_counts.get("tier-a", 0) \
       or bucket_counts.get("tier-a:paragraph-start", 0):
        print("🔴  Tier A / em-dash hits present — must reach 0 before convergence.")
    return excess


def lint(
    path: Path,
    field_profile_dir: Path | None,
    summary: bool = False,
    ai_classifier: bool = False,
    ai_threshold: float = 0.7,
    distribution: bool = True,
    oracle: bool = False,
    voice: bool = False,
) -> int:
    if not path.exists():
        print(f"[ai_ism_lint] file not found: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    hits: list[tuple[int, str, str]] = []  # (line_no, rule_name, line_excerpt)

    for i, line in enumerate(lines, start=1):
        if EM_DASH_PATTERN.search(line):
            hits.append((i, "em-dash", line.strip()))
        for m in TIER_A_PATTERN.finditer(line):
            hits.append((i, f"tier-a:{m.group(0).lower()}", line.strip()))
        if TIER_A_OPENER_PATTERN.match(line):
            hits.append((i, "tier-a:opener", line.strip()))
        m_pc = TIER_A_PARAGRAPH_CONNECTOR_PATTERN.match(line)
        if m_pc:
            hits.append((i, f"tier-a:paragraph-start:{m_pc.group(1)}", line.strip()))
        for m in TIER_B_PATTERN.finditer(line):
            # Avoid double-counting: if this Tier B hit is the same word the
            # paragraph-start Tier A check just flagged, skip — the Tier A
            # entry already carries the higher-severity signal.
            if m_pc and m.start() < m_pc.end():
                continue
            hits.append((i, f"tier-b:{m.group(0).lower()}", line.strip()))
        for m in STUBBORN_REPLACE_PATTERN.finditer(line):
            hits.append((i, f"stubborn:{m.group(0).lower()}", line.strip()))
        if THREE_PARALLEL_PATTERN.search(line):
            hits.append((i, "three-parallel", line.strip()))

    # Corpus-derived: any token in the corpus blacklist appearing in the file
    corpus_blacklist: set[str] = set()
    if field_profile_dir is not None:
        corpus_blacklist = load_corpus_blacklist(field_profile_dir)
    if corpus_blacklist:
        word_re = re.compile(r"\b(" + "|".join(re.escape(w) for w in corpus_blacklist) + r")\b", re.IGNORECASE)
        for i, line in enumerate(lines, start=1):
            for m in word_re.finditer(line):
                hits.append((i, f"corpus-blacklist:{m.group(1).lower()}", line.strip()))

    # ML classifier (paragraph-level, opt-in via --ai-classifier).
    if ai_classifier:
        try:
            clf = load_ai_classifier(field_profile_dir)
        except ImportError as e:
            print(
                f"[ai_ism_lint] --ai-classifier requires joblib + sklearn: {e}",
                file=sys.stderr,
            )
            clf = None
        if clf is None:
            print(
                "[ai_ism_lint] --ai-classifier requested but no classifier "
                "found. Train one with: "
                "`python tools/train_ai_ism_classifier.py`",
                file=sys.stderr,
            )
        else:
            paras = paragraph_ranges(text)
            scores = score_paragraphs(clf, paras)
            for (p_start, _p_end, p_text), score in zip(paras, scores):
                if score >= ai_threshold:
                    excerpt = p_text.replace("\n", " ").strip()
                    hits.append((
                        p_start,
                        f"ai-ish:{score:.2f}",
                        excerpt,
                    ))

    # Layer A: distributional diagnostics (burstiness / opener over-signposting
    # vs the corpus reference). ADVISORY — deliberately kept OUT of `hits` so
    # the keyword convergence exit code is unchanged (docs/DEAI_SUBSYSTEM.md
    # guardrail 2: the fundamental signal flags what to rewrite, it is never a
    # 0-gate; formal science prose false-positives on absolute thresholds).
    advisory: list[tuple[int, str, str]] = []
    if distribution:
        advisory += deai_metrics.distribution_hits(text, field_profile_dir)
    if oracle:
        try:
            import deai_oracle
            advisory += deai_oracle.paragraph_hits(text, field_profile_dir)
        except Exception as e:  # surface, don't crash the linter on a model/oracle error
            print(f"[ai_ism_lint] --oracle unavailable ({e}); skipping UID "
                  f"pass. Calibrate with `python tools/deai_oracle.py "
                  f"--calibrate --field <f>`.", file=sys.stderr)
    if voice:
        try:
            import deai_voice
            advisory += deai_voice.paragraph_hits(text, field_profile_dir)
        except Exception as e:  # surface, don't crash the linter on a model error
            print(f"[ai_ism_lint] --voice unavailable ({e}); skipping voice-model "
                  f"pass. Train with `python tools/train_voice_model.py "
                  f"--field <f>`.", file=sys.stderr)
    advisory.sort(key=lambda h: h[0])

    def _print_advisory() -> None:
        if not (distribution or oracle):
            return
        print()
        if advisory:
            print(f"[ai_ism_lint] fundamental-signal diagnostics "
                  f"(advisory — not a gate): {len(advisory)}")
            for a_line, a_rule, a_msg in advisory:
                print(f"  L{a_line:>5}  [{a_rule}]  {a_msg}")
        else:
            print("[ai_ism_lint] fundamental-signal diagnostics: 0 (advisory).")

    if not hits:
        scope = field_profile_dir.parent.name + "/" + field_profile_dir.name if field_profile_dir else "hand-rules-only"
        print(f"[ai_ism_lint] {path}: 0 keyword hits ({scope}). Clean.")
        _print_advisory()
        if summary:
            print()
            print("=== summary ===\nNothing to summarise. 0 keyword hits.")
        return 0

    print(f"[ai_ism_lint] {path}: {len(hits)} keyword hits\n")
    for line_no, rule, excerpt in hits:
        # truncate excerpt for readability
        e = (excerpt[:120] + "...") if len(excerpt) > 120 else excerpt
        print(f"  L{line_no:>5}  [{rule}]  {e}")
    print()
    print(f"[ai_ism_lint] convergence criterion = 0 keyword hits. Currently {len(hits)}.")
    _print_distribution()
    if summary:
        print()
        summarize(hits, text)
    return 1


def main(argv: list[str] | None = None) -> int:
    # Reconfigure stdout to UTF-8 so the verdict's 🔴/🟡 markers render on
    # Windows terminals defaulting to cp936/gbk. Guarded by feature-detect
    # (reconfigure is Python 3.7+); errors='replace' so broken bytes downgrade
    # to '?' rather than crash.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", type=Path)
    p.add_argument("--field", default=None,
                   help="Field whose corpus blacklist to apply. "
                        "Auto-detected when only one field exists; falls "
                        "back to hand-rules-only when no field profile is "
                        "available.")
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--summary", action="store_true",
                   help="Append aggregate breakdown after the per-line list: "
                        "counts by tier, Tier B density per \\section{} "
                        "(cap = 1 occurrence/section/word), and a verdict.")
    p.add_argument("--ai-classifier", action="store_true",
                   help="Score each paragraph with the ML classifier at "
                        "`style-profile/<field>/ai_ism_classifier.joblib` "
                        "(train via tools/train_ai_ism_classifier.py). "
                        "Paragraphs with P(AI-ish) ≥ --ai-threshold are "
                        "tagged `[ai-ish:<score>]` (soft signal — supplements "
                        "regex hits, doesn't replace them).")
    p.add_argument("--ai-threshold", type=float, default=0.7,
                   help="Threshold for [ai-ish:*] tagging. Default 0.7 "
                        "(P(AI-ish) ≥ 0.7 flagged).")
    p.add_argument("--distribution", action=argparse.BooleanOptionalAction,
                   default=True,
                   help="Layer A distributional diagnostics (sentence-length "
                        "burstiness + opener over-signposting vs the corpus "
                        "reference). ADVISORY: reported but never affects the "
                        "exit code. Default on; --no-distribution to disable.")
    p.add_argument("--oracle", action="store_true",
                   help="Layer B surprisal/UID oracle (deai_oracle.py): flags "
                        "paragraphs whose per-token surprisal variance is below "
                        "the human corpus reference. Needs a local LM + the "
                        "uid_baseline.json (run deai_oracle.py --calibrate). "
                        "ADVISORY, off by default (heavy: loads a model).")
    p.add_argument("--voice", action="store_true",
                   help="Layer D learned voice model (deai_voice.py): flags "
                        "paragraphs whose P(human) from the trained voice model "
                        "is below threshold. Needs voice_model.joblib (train via "
                        "tools/train_voice_model.py). ADVISORY, off by default "
                        "(heavy: loads an LM + embedder + the model).")
    args = p.parse_args(argv)

    field = resolve_field(args.field, args.profile_root)
    field_profile_dir = (args.profile_root / field) if field else None
    return lint(
        args.file,
        field_profile_dir,
        summary=args.summary,
        ai_classifier=args.ai_classifier,
        ai_threshold=args.ai_threshold,
        distribution=args.distribution,
        oracle=args.oracle,
        voice=args.voice,
    )


if __name__ == "__main__":
    raise SystemExit(main())
