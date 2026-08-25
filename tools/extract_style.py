"""Extract descriptive, field-scoped writing evidence from a paper corpus.

The extractor reads standalone ``.tex``, ``.txt``, and ``.pdf`` sources under
``style-corpus/<field>/tier-*`` and writes descriptive artifacts under
``style-profile/<field>/``: sentence statistics, paragraph-initial transitions,
lexical counts, an exemplar JSONL bank, and a compact dossier. PDF ingestion is
best-effort and requires pymupdf.

This module does not define consequence classes, authorship, or calibrated
operating points. Its section detection and PDF block segmentation are
heuristic; unmatched LaTeX sections default to ``method`` and non-LaTeX input to
``unknown``. Fix extraction errors in the source or this extractor and
regenerate rather than hand-editing generated evidence. Normative policy lives
in ``docs/SCIPAPER_STANDARD.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Section vocabulary, LaTeX projections and PDF heading detection moved to
# extract_sections.py on 2026-08-25 (this file could no longer be edited at
# its size). Re-exported here because sibling tools and tests reach them as
# es.<name>; the names below are unused in this module by design, which is
# what the F401 waiver records.
from extract_sections import (  # noqa: F401
    DEFAULT_SECTION_BUCKET, LIGATURE_TABLE, RE_ABSTRACT_ENV,
    RE_PDF_LINE_HEADER, RE_SECTION, RE_TEX_BEGIN_END, RE_TEX_BRACES,
    RE_TEX_CITE, RE_TEX_COMMENT, RE_TEX_DISPLAY_MATH,
    RE_TEX_ENV_FIGURE_TABLE, RE_TEX_INCLUDEGRAPHICS, RE_TEX_INLINE_MATH,
    RE_TEX_LABEL_REF, RE_TEX_MATH_CMD, RE_TEX_SIMPLE_CMD, RE_TEX_THIN_COMMA,
    RE_TEX_TILDE, SECTION_PATTERNS, _classify_pdf_heading, _math_numerals,
    classify_section, extract_pdf_text, latex_to_numeral_text,
    latex_to_plain, split_into_sections, split_pdf_into_sections,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS_ROOT = REPO_ROOT / "style-corpus"
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

TIER_WEIGHTS = {"tier-1-top": 0.5, "tier-2-mentor": 0.3, "tier-3-reference": 0.2}


def list_fields(corpus_root: Path) -> list[str]:
    """Return sorted list of field subdirs (any non-hidden dir whose name does
    NOT start with `tier-` is treated as a field)."""
    if not corpus_root.exists():
        return []
    return sorted(
        p.name for p in corpus_root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and not p.name.startswith("tier-")
    )


def resolve_field(arg_field: str | None, corpus_root: Path) -> str:
    """Pick the field. If --field passed, validate it exists. Otherwise:
    - 0 fields → error
    - 1 field → auto-pick it
    - >1 fields → error asking for explicit --field"""
    fields = list_fields(corpus_root)
    if arg_field:
        if arg_field not in fields:
            raise SystemExit(
                f"[extract_style] --field={arg_field!r} not found under "
                f"{corpus_root}/. Available: {fields or '(none)'}"
            )
        return arg_field
    if not fields:
        raise SystemExit(
            f"[extract_style] No field subdirectories found under {corpus_root}/. "
            "Create style-corpus/<field>/{tier-1-top,tier-2-mentor,tier-3-reference}/ "
            "and add papers."
        )
    if len(fields) > 1:
        raise SystemExit(
            f"[extract_style] Multiple fields present ({fields}); pass "
            f"--field=<name> to select one."
        )
    return fields[0]



# Placeholder strings emitted by latex_to_plain; paragraphs starting with
# these are NOT real prose paragraphs and should be excluded from
# paragraph-initial-word stats.
PLACEHOLDER_PARAGRAPH_PREFIXES = (
    "[MATH]", "[math]", "[CITE]", "[FIGURE-OR-TABLE]",
)
PLACEHOLDER_INITIAL_WORDS = {"FIGURE", "MATH", "CITE", "OR"}

# Candidate generated-style terms summarized against the current corpus.
# This compatibility list is descriptive; normative Tier A/Tier B policy lives
# in docs/SCIPAPER_STANDARD.md and is not inferred from corpus absence alone.
LLM_TYPICAL_WORDS = {
    "leverage", "leverages", "leveraging", "leveraged",
    "utilize", "utilizes", "utilizing", "utilized",
    "delve", "delves", "delving", "delved",
    "showcase", "showcases", "showcasing",
    "shed", "sheds", "shedding",  # "shed light"
    "pave", "paves", "paving",
    "seamless", "seamlessly",
    "comprehensive", "comprehensively",
    "robust", "robustly",
    "holistic", "holistically",
    "moreover", "furthermore", "additionally",
    "notably", "importantly", "crucially", "interestingly",
    # Candidates adopted 2026-07-16 from the academic-humanizer catalog
    # (github.com/AIScientists-Dev/academic-humanizer, MIT); "landscape" is
    # deliberately excluded because it is a legitimate domain term in the
    # astro corpus (e.g. detection landscape, energy landscape).
    "underscore", "underscores", "underscored", "underscoring",
    "intricate", "tapestry", "testament",
    "pivotal", "foster", "fosters", "fostering", "fostered",
    "realm", "realms",
}

PARAGRAPH_INITIAL_LLM_OPENERS = {
    "Furthermore", "Moreover", "Additionally", "Notably", "Importantly",
    "Crucially", "Interestingly", "It is worth", "Recent advances",
    "Despite significant", "With the advent", "In recent years",
}


RE_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\(])")


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [s for s in RE_SENTENCE_END.split(text) if s.strip()]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'\-]*", text)


def paragraph_initial_words(text: str) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        # Skip paragraphs that are nothing but our own placeholders
        # (figures, tables, equations, citations).
        if p.startswith(PLACEHOLDER_PARAGRAPH_PREFIXES):
            continue
        first_match = re.search(r"[A-Za-z]+", p)
        if first_match:
            word = first_match.group(0)
            # Skip the bare placeholder words themselves if they survived
            # (e.g., paragraph starts with " [FIGURE-OR-TABLE] ..." after
            # whitespace stripping leaves "[FIGURE-OR-TABLE]" as content).
            if word in PLACEHOLDER_INITIAL_WORDS:
                continue
            out.append(word)
    return out


def count_em_dashes(text: str) -> int:
    return len(re.findall(r"—|---|\\textemdash", text))


def gather_corpus_files(field_corpus_dir: Path) -> dict[str, list[Path]]:
    """field_corpus_dir is the field-specific dir, e.g. style-corpus/wgl/.

    Picks up `.tex`, `.txt`, and standalone `.pdf` sources. **A `.pdf` is
    accepted only directly under the tier directory (depth 1); anything nested
    deeper is skipped** as a figure or supplemental file inside an arXiv-source
    bundle, which ships 5-50 of them alongside the `.tex`. The rule is depth,
    not co-location with a `.tex`: a figure PDF placed directly in the tier
    directory is still ingested as if it were a paper. PDF parsing is best-effort
    via pymupdf; if pymupdf is unavailable the standalone PDF rows are
    still listed and `analyse_paper` will skip them with a warning.
    """
    out: dict[str, list[Path]] = {}
    for tier in TIER_WEIGHTS:
        tier_dir = field_corpus_dir / tier
        if not tier_dir.exists():
            continue
        # PDFs are accepted ONLY when placed directly under the tier
        # directory (depth = 1). Anything nested deeper is treated as a
        # figure / supplemental file inside an arXiv-source bundle (those
        # bundles often ship 5-50 figure PDFs alongside the .tex), and
        # would otherwise dominate the corpus with near-empty parses.
        files = []
        for p in tier_dir.rglob("*"):
            if not p.is_file():
                continue
            suf = p.suffix.lower()
            if suf in {".tex", ".txt"}:
                files.append(p)
            elif suf == ".pdf" and p.parent == tier_dir:
                files.append(p)
        out[tier] = files

def analyse_paper(path: Path) -> dict | None:
    """Parse one paper into per-section stats.

    Returns None if the file cannot be parsed (currently: PDF + pymupdf
    missing). Otherwise returns the standard analysis dict; callers use
    None to skip without error.
    """
    suffix = path.suffix.lower()
    is_tex = suffix == ".tex"
    is_pdf = suffix == ".pdf"

    if is_pdf:
        try:
            raw = extract_pdf_text(path)
        except ImportError as e:
            print(
                f"[extract_style] WARNING: skipping {path.name}: {e}",
                file=sys.stderr,
            )
            return None
        sections = split_pdf_into_sections(raw)
    elif is_tex:
        raw = path.read_text(encoding="utf-8", errors="replace")
        sections = split_into_sections(raw)
    else:
        raw = path.read_text(encoding="utf-8", errors="replace")
        sections = {"unknown": raw}

    by_section = {}
    for sec, sec_raw in sections.items():
        # PDFs are already plain text; only .tex needs latex_to_plain.
        sec_plain = latex_to_plain(sec_raw) if is_tex else sec_raw
        sents = sentences(sec_plain)
        sent_lens = [len(words(s)) for s in sents if len(words(s)) > 0]
        by_section[sec] = {
            "n_sentences": len(sents),
            "sentence_lengths": sent_lens,
            "n_words": sum(sent_lens),
            "em_dash_count": count_em_dashes(sec_plain),
            "paragraph_initial_words": paragraph_initial_words(sec_plain),
            "word_counter": Counter(w.lower() for w in words(sec_plain)),
            # Plain prose text retained for exemplar-bank construction.
            # Numbers/citations stripped to placeholders; safe to chunk by
            # paragraph and ship as style anchors.
            "plain_text": sec_plain,
        }

    return {
        "path": str(path.relative_to(Path.cwd())) if Path.cwd() in path.parents else str(path),
        "by_section": by_section,
        "total_words": sum(s["n_words"] for s in by_section.values()),
        "total_em_dashes": sum(s["em_dash_count"] for s in by_section.values()),
    }


def aggregate_sentence_stats(per_paper: list[tuple[float, dict]]) -> dict:
    """Per-section sentence-length stats, pooled across papers.

    Tier weights are carried through the bucket but NOT applied: the stats
    below flatten to the bare lengths, so a tier-1 and a tier-3 paper
    contribute equally. Applying them needs weighted percentiles (numpy),
    and this module is standard-library only.
    """
    bucket: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for weight, paper in per_paper:
        for sec, st in paper["by_section"].items():
            for L in st["sentence_lengths"]:
                bucket[sec].append((weight, L))

    out = {}
    for sec, weighted in bucket.items():
        if not weighted:
            continue
        # Expand by integer weight approximation for simple stats.
        # (Proper weighted percentiles would need numpy; stdlib approximation OK for v0.1.)
        flat = [L for _w, L in weighted]
        out[sec] = {
            "n": len(flat),
            "mean": statistics.mean(flat),
            "median": statistics.median(flat),
            "stdev": statistics.pstdev(flat) if len(flat) > 1 else 0.0,
            "p25": _percentile(flat, 25),
            "p75": _percentile(flat, 75),
            "p95": _percentile(flat, 95),
        }
    return out


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def aggregate_em_dashes(per_paper: list[tuple[float, dict]]) -> dict:
    total_words = sum(p["total_words"] for _w, p in per_paper)
    total_em = sum(p["total_em_dashes"] for _w, p in per_paper)
    return {
        "total_em_dashes": total_em,
        "total_words": total_words,
        "em_dashes_per_1000_words": (total_em / total_words * 1000) if total_words else 0.0,
        "n_papers": len(per_paper),
    }


def aggregate_transitions(per_paper: list[tuple[float, dict]]) -> dict:
    counter: Counter[str] = Counter()
    for _w, paper in per_paper:
        for sec, st in paper["by_section"].items():
            for w in st["paragraph_initial_words"]:
                counter[w] += 1

    total = sum(counter.values()) or 1
    used = [(w, c, c / total) for w, c in counter.most_common()]
    used_set = {w for w, _, _ in used}

    forbidden_present = [
        (w, counter.get(w, 0))
        for w in PARAGRAPH_INITIAL_LLM_OPENERS
        if counter.get(w, 0) > 0
    ]
    forbidden_absent = [
        w for w in PARAGRAPH_INITIAL_LLM_OPENERS if counter.get(w, 0) == 0
    ]

    return {
        "n_paragraphs": total,
        "whitelist_observed": [
            {"word": w, "count": c, "freq": f}
            for w, c, f in used[:30]
        ],
        "blacklist_present_in_corpus": forbidden_present,
        "blacklist_absent_from_corpus": forbidden_absent,
        # The complete paragraph-initial counter, so a consumer can compute a
        # reference rate over ITS OWN opener set. The two curated lists above
        # are this extractor's descriptive view; a detector that measures a
        # draft against a different set (deai_metrics.CONNECTIVE_OPENERS) must
        # not be handed a rate computed over this one, which is how the
        # reported "reference corpus rate" came to be incomparable with the
        # fraction it was printed beside.
        "paragraph_initial_counts": dict(counter),
    }


# Exemplar paragraph filters. Paragraphs outside this band are skipped:
# below the floor they're noise (lone "where ..." lines, captions, fragments);
# above the ceiling they're often bibliography blobs or merged sections.
EXEMPLAR_MIN_WORDS = 30
EXEMPLAR_MAX_WORDS = 400


def write_exemplar_bank(per_paper: list[tuple[float, dict]],
                        profile_dir: Path) -> int:
    """Emit one JSONL row per qualifying paragraph in `exemplar_paragraphs.jsonl`.

    Each row: {id, section, tier, source, n_words, text}.
    Section is the normalized bucket from classify_section();
    rows in the 'unknown' bucket and rows whose paragraphs are pure
    placeholders are excluded. Returns the number of rows written.
    """
    out_path = profile_dir / "exemplar_paragraphs.jsonl"
    n_written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for _weight, paper in per_paper:
            tier = paper.get("tier", "?")
            source = paper.get("source_path", paper.get("path", "?"))
            for sec, st in paper["by_section"].items():
                if sec == "unknown":
                    continue
                plain = st.get("plain_text", "")
                if not plain:
                    continue
                paragraphs = re.split(r"\n\s*\n", plain)
                for idx, para in enumerate(paragraphs):
                    para = para.strip()
                    if not para:
                        continue
                    if para.startswith(PLACEHOLDER_PARAGRAPH_PREFIXES):
                        continue
                    n_w = len(words(para))
                    if n_w < EXEMPLAR_MIN_WORDS or n_w > EXEMPLAR_MAX_WORDS:
                        continue
                    rec = {
                        "id": f"{source}:p{idx}",
                        "section": sec,
                        "tier": tier,
                        "source": source,
                        "n_words": n_w,
                        "text": para,
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_written += 1
    return n_written


def aggregate_lexicon(per_paper: list[tuple[float, dict]]) -> dict:
    overall: Counter[str] = Counter()
    for _w, paper in per_paper:
        for st in paper["by_section"].values():
            overall.update(st["word_counter"])

    total = sum(overall.values()) or 1
    llm_in_corpus = {
        w: {"count": overall.get(w, 0), "freq_per_1k": overall.get(w, 0) / total * 1000}
        for w in LLM_TYPICAL_WORDS
    }
    llm_absent = sorted(w for w, d in llm_in_corpus.items() if d["count"] == 0)
    return {
        "total_tokens": total,
        "llm_typical_word_counts": llm_in_corpus,
        "llm_words_absent_from_corpus": llm_absent,
        "top_50_corpus_words": overall.most_common(50),
    }


def write_dossier(
    profile_dir: Path,
    sentence_stats: dict,
    em_dash_stats: dict,
    transitions: dict,
    lexicon: dict,
    n_papers: int,
    field: str,
) -> None:
    lines = []
    lines.append(f"# Style Dossier — field: `{field}` (auto-generated)\n")
    lines.append(f"Built from {n_papers} corpus papers under "
                 f"`style-corpus/{field}/`. Re-run "
                 f"`python tools/extract_style.py --field {field}` after "
                 "corpus changes.\n")
    lines.append("> Descriptive evidence only. Normative policy lives in "
                 "`docs/SCIPAPER_STANDARD.md`. Do not hand-edit this file: "
                 "the extractor overwrites it. Fix the source or extractor "
                 "and regenerate.\n")

    lines.append("\n## 1. Sentence length per section\n")
    if not sentence_stats:
        lines.append("_No sections detected. Are you using `.tex` source with "
                     "`\\section{}` markers?_\n")
    else:
        lines.append("| Section | n | mean | median | stdev | p25 | p75 | p95 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for sec, st in sorted(sentence_stats.items()):
            lines.append(
                f"| {sec} | {st['n']} | {st['mean']:.1f} | {st['median']:.1f} "
                f"| {st['stdev']:.1f} | {st['p25']:.0f} | {st['p75']:.0f} "
                f"| {st['p95']:.0f} |"
            )
        lines.append("\n**Interpretation:** compare a draft with the relevant "
                     "section distribution, but do not turn a distance alone "
                     "into a blocker or strong advisory. Strength requires an "
                     "applicable calibrated operating point.\n")

    lines.append("\n## 2. Em-dash usage\n")
    lines.append(f"- Corpus em-dashes per 1000 words: "
                 f"**{em_dash_stats['em_dashes_per_1000_words']:.3f}** "
                 f"(total: {em_dash_stats['total_em_dashes']} across "
                 f"{em_dash_stats['total_words']} words).")
    lines.append("- The normative standard treats prose em-dashes as an L0 "
                 "rewrite target; this corpus count is supporting evidence, "
                 "not the source of that rule.\n")

    lines.append("\n## 3. Paragraph-initial transitions\n")
    if transitions["n_paragraphs"] == 0:
        lines.append("_No paragraphs detected._\n")
    else:
        lines.append("**Observed in corpus (top 30, paragraph-initial):**")
        lines.append("")
        for entry in transitions["whitelist_observed"]:
            lines.append(f"- `{entry['word']}` — {entry['count']} "
                         f"({entry['freq']*100:.1f}%)")
        lines.append("")
        if transitions["blacklist_absent_from_corpus"]:
            lines.append("**Candidate generated-style openers absent from this "
                         "corpus:**")
            lines.append("")
            for word in transitions["blacklist_absent_from_corpus"]:
                lines.append(f"- `{word}`")
            lines.append("")
            lines.append("Absence is evidence for review, not by itself a new "
                         "L0 prohibition.\n")
        if transitions["blacklist_present_in_corpus"]:
            lines.append("**Candidate generated-style openers observed in this "
                         "corpus:**")
            lines.append("")
            for word, count in transitions["blacklist_present_in_corpus"]:
                lines.append(f"- `{word}` — {count}× in corpus")

    lines.append("\n## 4. Candidate generated-style lexicon in this corpus\n")
    lines.append(f"Corpus total tokens: {lexicon['total_tokens']}.\n")
    lines.append("| Word | Count | Per 1k tokens |")
    lines.append("|---|---|---|")
    for word, data in sorted(lexicon["llm_typical_word_counts"].items()):
        lines.append(
            f"| `{word}` | {data['count']} | {data['freq_per_1k']:.3f} |")
    if lexicon["llm_words_absent_from_corpus"]:
        lines.append("")
        lines.append("**Candidate terms with zero occurrence in this corpus:**")
        lines.append(", ".join(
            f"`{word}`" for word in lexicon["llm_words_absent_from_corpus"]))
        lines.append("\nZero occurrence does not independently create a "
                     "normative rule; apply the standard's Tier A/Tier B "
                     "contract.\n")

    lines.append("\n## 5. Top 50 corpus content words\n")
    lines.append("(Extraction sense-check only; not a writing constraint.)\n")
    lines.append(", ".join(
        f"`{word}`({count})" for word, count in lexicon["top_50_corpus_words"]))

    lines.append("\n## 6. How `/sci-paper:de-ai` uses this file\n")
    lines.append(
        "1. The skill loads this dossier as descriptive field evidence.\n"
        "2. It retrieves section- and topic-matched paragraphs from "
        "`exemplar_paragraphs.jsonl`.\n"
        "3. It applies `docs/SCIPAPER_STANDARD.md` for consequence classes, "
        "measurement states, ranking, and dispositions.\n"
        "4. Distributional or lexical distance from this dossier remains an "
        "advisory unless the normative L0 list or an integrity rule applies.\n"
        "5. Missing calibration remains `degraded` or `unmeasured`; it is not "
        "reported as zero findings.\n"
        "6. Final feedback is emitted through `python tools/ai_ism_lint.py "
        "<file> --field <field> --format json`.\n"
    )

    (profile_dir / "style_dossier.md").write_text(
        "\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    # This module prints non-ASCII (arrows, en dashes). With stdout redirected
    # to a pipe or a file under a non-UTF-8 locale -- exactly what
    # build_profile.py does when it captures this tool's output -- the default
    # encoder raises UnicodeEncodeError and the run dies after the work is done.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--field", default=None,
                   help="Field name (subdir under style-corpus/). "
                        "Auto-detected when only one field exists.")
    p.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT,
                   help="Root corpus dir (default: style-corpus/).")
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT,
                   help="Root profile dir (default: style-profile/).")
    args = p.parse_args(argv)

    field = resolve_field(args.field, args.corpus_root)
    field_corpus = args.corpus_root / field
    field_profile = args.profile_root / field
    field_profile.mkdir(parents=True, exist_ok=True)

    print(f"[extract_style] field={field!r}")
    print(f"  corpus: {field_corpus}")
    print(f"  profile: {field_profile}")

    files_by_tier = gather_corpus_files(field_corpus)
    n_files = sum(len(v) for v in files_by_tier.values())
    if n_files == 0:
        print(f"[extract_style] No .tex/.txt files found under {field_corpus}/.")
        print(f"Add papers to style-corpus/{field}/tier-{{1,2,3}}-* and re-run.")
        return 1
    if n_files < 5:
        print(f"[extract_style] WARNING: only {n_files} corpus files. "
              "Statistics will be noisy; recommended ≥ 8.")

    per_paper: list[tuple[float, dict]] = []
    for tier, files in files_by_tier.items():
        weight = TIER_WEIGHTS[tier]
        for f in files:
            try:
                analysis = analyse_paper(f)
            except Exception as e:
                print(f"[extract_style] FAILED to parse {f}: {e}", file=sys.stderr)
                continue
            if analysis is None:
                # analyse_paper returns None for files it knows it cannot
                # handle (e.g., PDF + pymupdf missing); already logged.
                continue
            # Tag tier + a stable, repo-relative source path so the exemplar
            # writer can include both fields per row without rebuilding state.
            analysis["tier"] = tier
            try:
                analysis["source_path"] = str(
                    f.relative_to(args.corpus_root.parent)
                ).replace("\\", "/")
            except ValueError:
                analysis["source_path"] = str(f).replace("\\", "/")
            per_paper.append((weight, analysis))
            print(f"  parsed {tier}/{f.name}: {analysis['total_words']} words, "
                  f"{analysis['total_em_dashes']} em-dashes")

    if not per_paper:
        print("[extract_style] All files failed to parse.")
        return 1

    sentence_stats = aggregate_sentence_stats(per_paper)
    em_dash_stats = aggregate_em_dashes(per_paper)
    transitions = aggregate_transitions(per_paper)
    lexicon = aggregate_lexicon(per_paper)

    (field_profile / "sentence_stats.json").write_text(
        json.dumps(sentence_stats, indent=2, sort_keys=True), encoding="utf-8"
    )
    (field_profile / "transition_inventory.json").write_text(
        json.dumps(transitions, indent=2, sort_keys=True, default=list),
        encoding="utf-8",
    )
    (field_profile / "lexicon.json").write_text(
        json.dumps(lexicon, indent=2, sort_keys=True), encoding="utf-8"
    )

    write_dossier(
        field_profile,
        sentence_stats,
        em_dash_stats,
        transitions,
        lexicon,
        n_papers=len(per_paper),
        field=field,
    )

    n_exemplars = write_exemplar_bank(per_paper, field_profile)

    print(f"\n[extract_style] OK. {len(per_paper)} papers processed for field {field!r}.")
    print(f"  → {field_profile}/style_dossier.md")
    print(f"  → {field_profile}/{{sentence_stats,transition_inventory,lexicon}}.json")
    print(f"  → {field_profile}/exemplar_paragraphs.jsonl  ({n_exemplars} paragraphs)")
    print("\nNext: inspect style_dossier.md; if anything looks off, fix the "
          "corpus or extractor and re-run (generated evidence is never "
          "hand-edited).")
    print("To enable retrieval: `python tools/retrieve_exemplars.py --section <s> --topic <t>`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
