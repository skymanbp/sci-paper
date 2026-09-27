"""Extract descriptive, field-scoped writing evidence from a paper corpus.

Reads ``.tex``, ``.txt`` and ``.pdf`` sources under ``style-corpus/<field>/tier-*``
and writes descriptive artifacts under ``style-profile/<field>/``: sentence
statistics, paragraph-initial transitions, lexical counts, an exemplar JSONL
bank and a dossier. PDF ingestion needs pymupdf; ``.txt`` sources carry no
sections, so they feed the statistics under ``unknown`` and never the bank.

This module defines no consequence class, authorship or operating point; its
section detection is heuristic and an unmatched heading is ``unknown``, never a
default bucket. Fix extraction in the source or here and regenerate; never
hand-edit generated evidence. Policy lives in ``docs/SCIPAPER_STANDARD.md``.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first

# Section vocabulary, LaTeX projections, PDF heading detection, and corpus
# document assembly live in extract_sections.py (moved 2026-08-25; this file
# could no longer be edited at its size). Re-exported here because sibling
# tools and tests reach them as es.<name>; the names below are unused in this
# module by design, which is what the F401 waiver records. The re-export list
# is hand-written, so `ReExportContractTests` asserts it stays complete --
# it has caught three additions already.
from extract_sections import (  # noqa: F401 -- re-export, unused here by design
    CALIBRATION_FULLTEXT, CLASSIFIED_BUCKETS, _classified_word_count, DEFAULT_SECTION_BUCKET,
    LIGATURE_TABLE, RE_ABSTRACT_ENV, RE_HEADING_CMD, RE_HEADING_COMMAND, RE_HEADING_DROP_ARG,
    RE_HEADING_MATH, RE_HEADING_TEXORPDF, RE_PDF_LINE_HEADER, RE_PLACEHOLDER, RE_SECTION,
    RE_TEX_BEGIN_END, RE_TEX_BRACES, RE_TEX_CITE, RE_TEX_CITE_SILENT, RE_TEX_CITE_TEXT,
    RE_TEX_COMMENT, RE_TEX_DISPLAY_MATH, RE_TEX_ENV_FIGURE_TABLE, RE_TEX_INCLUDEGRAPHICS,
    RE_TEX_INLINE_MATH, RE_TEX_DOC_MARKER, RE_TEX_INCLUDE, RE_TEX_LABEL_REF, RE_TEX_MATH_CMD,
    RE_TEX_SIMPLE_CMD, RE_TEX_THIN_COMMA, RE_TEX_TILDE, RE_SENTENCE_TERMINAL, SECTION_PATTERNS,
    PDF_HEADING_MIN_LETTER_FRAC, PDF_HEADING_MIN_LETTERS, PDF_HEADING_MIN_WORDS,
    _classify_pdf_heading, _include_targets, _math_numerals, _resolve_include,
    _rejoin_pdf_paragraphs, blank_preserving, classify_section, clean_heading, corpus_documents,
    extract_pdf_text, latex_to_numeral_text, latex_to_plain, PLAIN_PLACEHOLDERS, _project,
    prose_words, read_tex_document, select_document_roots, split_into_sections,
    split_pdf_into_sections,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS_ROOT = REPO_ROOT / "style-corpus"
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

# The curated tiers. The weights are RECORDED metadata (they travel with each
# observation) and are NOT applied: every aggregate pools the tiers equally,
# as `aggregate_sentence_stats` says. The dict also names which directories
# are curated; everything else under the field is breadth.
TIER_WEIGHTS = {"tier-1-top": 0.5, "tier-2-mentor": 0.3, "tier-3-reference": 0.2}

# Breadth corpus: the bulk arXiv full-text pull (fetch_arxiv_abstracts.py
# --fulltext), gathered so the per-section reference distributions have enough
# observations, and excluded from the dossier aggregates so breadth cannot
# restyle the imitation target (with one list, `results` sat at 26 passages
# while 500 field papers sat unread). The name is owned by extract_sections,
# which must tell it apart from the held-out `fulltext-*` siblings.
REFERENCE_DIR = CALIBRATION_FULLTEXT


def list_fields(corpus_root: Path) -> list[str]:
    return cli_common.list_fields(corpus_root, exclude_prefixes=("tier-",))


def resolve_field(arg_field: str | None, corpus_root: Path) -> str:
    return cli_common.resolve_field(
        arg_field, corpus_root, tool="extract_style", exclude_prefixes=("tier-",))





# Placeholder tokens emitted by latex_to_plain. A paragraph that is NOTHING but
# placeholders is not prose; one that merely STARTS with one (`\citet{X}
# showed ...`) is, and until 2026-09-27 it was dropped whole from the bank and
# the opener statistics, so `intro` lost its citation-led paragraphs. Nor are
# the tokens words: counted, they inflated sentence lengths, the em-dash
# denominator and the lexicon, and let a 25-word paragraph into the bank.
_RE_PLAIN_PLACEHOLDER_TOKEN = re.compile(r"\[(?:MATH|math|FIGURE-OR-TABLE|CITE)\]")


def without_placeholders(text: str) -> str:  # every placeholder becomes a space
    return _RE_PLAIN_PLACEHOLDER_TOKEN.sub(" ", text)

# Candidate generated-style terms summarized against the current corpus.
# This compatibility list is descriptive; normative Tier A/Tier B policy lives
# in docs/SCIPAPER_STANDARD.md and is not inferred from corpus absence alone.
# The second block was adopted 2026-07-16 from the academic-humanizer catalog
# (github.com/AIScientists-Dev/academic-humanizer, MIT); "landscape" is left
# out because it is a domain term in the astro corpus (detection landscape).
LLM_TYPICAL_WORDS = {
    "leverage", "leverages", "leveraging", "leveraged", "utilize", "utilizes",
    "utilizing", "utilized", "delve", "delves", "delving", "delved", "showcase",
    "showcases", "showcasing", "shed", "sheds", "shedding", "pave", "paves", "paving",
    "seamless", "seamlessly", "comprehensive", "comprehensively", "robust", "robustly",
    "holistic", "holistically", "moreover", "furthermore", "additionally", "notably",
    "importantly", "crucially", "interestingly",
    "underscore", "underscores", "underscored", "underscoring", "intricate", "tapestry",
    "testament", "pivotal", "foster", "fosters", "fostering", "fostered", "realm", "realms",
}

PARAGRAPH_INITIAL_LLM_OPENERS = {
    "Furthermore", "Moreover", "Additionally", "Notably", "Importantly", "Crucially",
    "Interestingly", "It is worth", "Recent advances", "Despite significant",
    "With the advent", "In recent years",
}


RE_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\(])")


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [s for s in RE_SENTENCE_END.split(text) if s.strip()]


# A word is a run of letters in any script: the ASCII class split `naïve` into
# `na` and `ve` and `Poincaré` into `Poincar`, and the fragments entered the
# lexicon and the word counts, the same class of defect as the PDF ligatures.
RE_WORD_TOKEN = re.compile(r"[^\W\d_][^\W\d_'\-]*")


def words(text: str) -> list[str]:
    return RE_WORD_TOKEN.findall(text)


def _prose_paragraphs(text: str) -> list[str]:
    """Each paragraph of projected text with its placeholders removed; a
    paragraph that was only placeholders is dropped."""
    out = []
    for p in RE_PARAGRAPH_BREAK.split(text):
        p = without_placeholders(p).strip()
        if p:
            out.append(p)
    return out


def paragraph_initial_words(text: str) -> list[str]:
    out = []
    for p in _prose_paragraphs(text):
        first_match = RE_WORD_TOKEN.search(p)
        if first_match:
            out.append(first_match.group(0))
    return out


def paragraph_initial_phrases(text: str) -> list[str]:
    """Multi-word openers a paragraph starts with. `paragraph_initial_words`
    records one WORD per paragraph, so the phrases read as always absent."""
    phrases = [p for p in PARAGRAPH_INITIAL_LLM_OPENERS if " " in p]
    return [phrase for p in _prose_paragraphs(text)
            for phrase in phrases if p.startswith(phrase)]


def count_em_dashes(text: str) -> int:
    return len(re.findall(r"—|---|\\textemdash", text))


def gather_corpus_files(field_corpus_dir: Path) -> dict[str, list[Path]]:
    """field_corpus_dir is the field-specific dir, e.g. style-corpus/wgl/.

    Returns `{source: [paths]}` for the three curated tiers plus, when it
    exists, the breadth directory named by `REFERENCE_DIR`. Callers must not
    assume every key is in `TIER_WEIGHTS`; the breadth source is unweighted
    (see that constant).

    Picks up `.tex`, `.txt`, and standalone `.pdf` sources. `.tex` files are
    reduced to document roots by `select_document_roots`. **A `.pdf` is
    accepted only directly under the source directory (depth 1); anything
    nested deeper is skipped** as a figure or supplemental file inside an
    arXiv-source bundle, which ships 5-50 of them alongside the `.tex`. The
    rule is depth, not co-location with a `.tex`: a figure PDF placed directly
    in the source directory is still ingested as if it were a paper. PDF
    parsing is best-effort via pymupdf; if pymupdf is unavailable the
    standalone PDF rows are still listed and `analyse_paper` will skip them
    with a warning.
    """
    out: dict[str, list[Path]] = {}
    for source in (*TIER_WEIGHTS, REFERENCE_DIR):
        source_dir = field_corpus_dir / source
        if not source_dir.exists():
            continue
        # PDFs are accepted ONLY when placed directly under the source
        # directory (depth = 1). Anything nested deeper is treated as a
        # figure / supplemental file inside an arXiv-source bundle (those
        # bundles often ship 5-50 figure PDFs alongside the .tex), and
        # would otherwise dominate the corpus with near-empty parses.
        tex: list[Path] = []
        files: list[Path] = []
        for p in source_dir.rglob("*"):
            if not p.is_file():
                continue
            suf = p.suffix.lower()
            if suf == ".tex":
                tex.append(p)
            elif suf == ".txt":
                files.append(p)
            elif suf == ".pdf" and p.parent == source_dir:
                files.append(p)
        out[source] = sorted(files + select_document_roots(tex, source_dir))
    return out


def analyse_paper(path: Path) -> dict | None:
    """Parse one paper into per-section stats.

    A `.tex` path is read as a whole document via `read_tex_document`, which
    splices in the files it \\include's; `gather_corpus_files` hands over
    document roots, and a root on its own is often just a wrapper.

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
        raw = read_tex_document(path)
        sections = split_into_sections(raw)
    else:
        raw = path.read_text(encoding="utf-8", errors="replace")
        sections = {"unknown": raw}

    by_section = {}
    for sec, sec_raw in sections.items():
        # PDFs are already plain text; only .tex needs latex_to_plain, and a
        # PDF paragraph is its own numeral view.
        if is_tex:
            sec_plain, sec_numeral = paired_paragraphs(sec_raw)
        else:
            sec_plain, sec_numeral = sec_raw, RE_PARAGRAPH_BREAK.split(sec_raw)
        # Statistics read the prose without its placeholders; the bank keeps
        # `plain_text` with them, as slot markers the paired view relies on.
        prose = without_placeholders(sec_plain)
        sents = sentences(prose)
        sent_lens = [len(words(s)) for s in sents if len(words(s)) > 0]
        by_section[sec] = {
            "n_sentences": len(sents),
            "sentence_lengths": sent_lens,
            "n_words": sum(sent_lens),
            # Counted on the comment-stripped source for .tex: the projection
            # has already deleted `\textemdash`, so counting there missed it.
            "em_dash_count": count_em_dashes(RE_TEX_COMMENT.sub("", sec_raw)
                                             if is_tex else sec_plain),
            "paragraph_initial_words": paragraph_initial_words(sec_plain),
            "paragraph_initial_phrases": paragraph_initial_phrases(sec_plain),
            "word_counter": Counter(w.lower() for w in words(prose)),
            # Plain prose text retained for exemplar-bank construction.
            # Numbers/citations stripped to placeholders; safe to chunk by
            # paragraph and ship as style anchors.
            "plain_text": sec_plain,
            # Each paragraph of `plain_text` under the numeral-preserving
            # projection (None when the views could not be paired), so the
            # salience reference sees `0.81` where the manuscript does; on
            # `plain_text` it saw `[math]` (held-out-labels.md §17.5).
            "numeral_paragraphs": sec_numeral,
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
    phrases: Counter[str] = Counter()
    for _w, paper in per_paper:
        for sec, st in paper["by_section"].items():
            for w in st["paragraph_initial_words"]:
                counter[w] += 1
            for phrase in st.get("paragraph_initial_phrases", ()):
                phrases[phrase] += 1

    n_paragraphs = sum(counter.values())
    total = n_paragraphs or 1
    used = [(w, c, c / total) for w, c in counter.most_common()]

    def seen(opener: str) -> int:
        return phrases.get(opener, 0) if " " in opener else counter.get(opener, 0)

    forbidden_present = [
        (w, seen(w)) for w in PARAGRAPH_INITIAL_LLM_OPENERS if seen(w) > 0
    ]
    forbidden_absent = [
        w for w in PARAGRAPH_INITIAL_LLM_OPENERS if seen(w) == 0
    ]

    return {
        # The real count: `or 1` here made an empty corpus report one
        # paragraph, and the dossier's "No paragraphs detected" unreachable.
        "n_paragraphs": n_paragraphs,
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


# A paragraph boundary in projected text. One owner: the bank writer, the
# paired projection and the opener statistics must cut at the same places.
RE_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def _math_numerals_slotted(match: "re.Match[str]") -> str:
    """`_math_numerals`, except a span with nothing left in it keeps a slot:
    `$\\vec{\\nabla}$` alone on a line is a `[math]` paragraph in the plain
    view and would be a swallowed blank line in the numeral one."""
    reduced = _math_numerals(match)
    return reduced if reduced.strip() else " [math] "


def paired_paragraphs(text: str) -> tuple[str, list[str] | None]:
    """`latex_to_plain(text)` and, per paragraph of it, the numeral projection.

    The bank stores the plain paragraph and the salience axis calibrates on
    the numeral one, so they must be the same paragraph. Split on blank lines
    alone the views do not pair (an equation-only paragraph is `[MATH]` in one
    and swallowed whitespace in the other), so the numeral view is projected
    WITH the plain placeholders as slot markers, split on the same boundaries
    and stripped after. Both views run one `_project`, so the counts agree by
    construction; the None branch is a guard, not a live outcome.
    """
    plain = latex_to_plain(text)
    slotted = _project(text, inline=_math_numerals_slotted, **PLAIN_PLACEHOLDERS)
    plain_paragraphs = RE_PARAGRAPH_BREAK.split(plain)
    numeral_paragraphs = RE_PARAGRAPH_BREAK.split(slotted)
    if len(numeral_paragraphs) != len(plain_paragraphs):
        return plain, None
    return plain, [re.sub(r"[ \t]+", " ", _RE_PLAIN_PLACEHOLDER_TOKEN.sub(" ", p))
                   for p in numeral_paragraphs]


# Exemplar paragraph filters. Paragraphs outside this band are skipped:
# below the floor they're noise (lone "where ..." lines, captions, fragments);
# above the ceiling they're often bibliography blobs or merged sections.
EXEMPLAR_MIN_WORDS = 30
EXEMPLAR_MAX_WORDS = 400


def write_exemplar_bank(per_paper: list[tuple[float, dict]],
                        profile_dir: Path) -> int:
    """Emit one JSONL row per qualifying paragraph in `exemplar_paragraphs.jsonl`.

    Each row: {id, section, tier, source, n_words, text, numeral_text}. The
    id carries the bucket, because a per-bucket index made `paper.tex:p0`
    the id of two rows. Section is the normalized bucket from
    classify_section(); rows in the 'unknown' bucket and rows whose
    paragraphs are pure placeholders are excluded, and `n_words` counts the
    prose without its placeholders. Returns the number of rows written.

    `numeral_text` is the same paragraph under `latex_to_numeral_text`, paired
    by `paired_paragraphs`. A section it could not pair is reported and
    written without the field, which the salience calibration reads as "fall
    back to `text`" rather than as a paragraph from elsewhere in the paper.
    """
    out_path = profile_dir / "exemplar_paragraphs.jsonl"
    n_written = 0
    unaligned: list[str] = []
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
                paragraphs = RE_PARAGRAPH_BREAK.split(plain)
                numeral = st.get("numeral_paragraphs") or []
                if not numeral:
                    unaligned.append(f"{source}:{sec}")
                for idx, para in enumerate(paragraphs):
                    para = para.strip()
                    if not without_placeholders(para).strip():
                        continue
                    n_w = len(words(without_placeholders(para)))
                    if n_w < EXEMPLAR_MIN_WORDS or n_w > EXEMPLAR_MAX_WORDS:
                        continue
                    rec = {
                        "id": f"{source}:{sec}:p{idx}",
                        "section": sec,
                        "tier": tier,
                        "source": source,
                        "n_words": n_w,
                        "text": para,
                    }
                    if numeral:
                        rec["numeral_text"] = numeral[idx].strip()
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n_written += 1
    if unaligned:
        print(f"[extract_style] WARNING: {len(unaligned)} section(s) written "
              f"without numeral_text (projections disagree on paragraph "
              f"count): {', '.join(unaligned[:5])}", file=sys.stderr)
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
    cli_common.utf8_stdout()
    p = cli_common.base_parser(__doc__)
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

    print(f"[extract_style] field={field!r}")
    print(f"  corpus: {field_corpus}")
    print(f"  profile: {field_profile}")

    files_by_tier = gather_corpus_files(field_corpus)
    # The warning below counts the CURATED tiers only. Breadth papers cannot
    # stand in for them: they are excluded from every weighted aggregate, so
    # counting them here would silence the warning while leaving the dossier
    # exactly as thin as it was.
    n_curated = sum(len(v) for k, v in files_by_tier.items() if k in TIER_WEIGHTS)
    if sum(len(v) for v in files_by_tier.values()) == 0:
        print(f"[extract_style] No .tex/.txt files found under {field_corpus}/.")
        print(f"Add papers to style-corpus/{field}/tier-{{1,2,3}}-* and re-run.")
        return 1
    if n_curated < 5:
        print(f"[extract_style] WARNING: only {n_curated} curated corpus files. "
              "Statistics will be noisy; recommended ≥ 8.")
    # Created only once the corpus is known to hold something: a failed run
    # left an empty field behind, and every other tool's `resolve_field` then
    # reported "Multiple fields present".
    field_profile.mkdir(parents=True, exist_ok=True)

    # `per_paper` drives the weighted aggregates and the dossier and holds the
    # curated tiers only; `reference_papers` is the unweighted breadth corpus.
    # The exemplar bank is built from both -- it is the reference distribution
    # every L1/L2 axis measures against, and needs the observations.
    per_paper: list[tuple[float, dict]] = []
    reference_papers: list[tuple[float, dict]] = []
    skipped = 0
    for source, files in files_by_tier.items():
        weight = TIER_WEIGHTS.get(source, 0.0)
        sink = per_paper if source in TIER_WEIGHTS else reference_papers
        verbose = source in TIER_WEIGHTS
        for f in files:
            try:
                analysis = analyse_paper(f)
            except Exception as e:
                print(f"[extract_style] FAILED to parse {f}: {e}", file=sys.stderr)
                continue
            if analysis is None:
                # analyse_paper returns None for files it knows it cannot
                # handle (e.g., PDF + pymupdf missing); already logged, and
                # counted so the summary says the profile is built without them.
                skipped += 1
                continue
            # Tag tier + a stable, repo-relative source path so the exemplar
            # writer can include both fields per row without rebuilding state.
            analysis["tier"] = source
            try:
                analysis["source_path"] = str(
                    f.relative_to(args.corpus_root.parent)
                ).replace("\\", "/")
            except ValueError:
                analysis["source_path"] = str(f).replace("\\", "/")
            sink.append((weight, analysis))
            if verbose:
                # The breadth corpus runs to hundreds of papers; printing a
                # line each buries the curated tiers it is meant to complement.
                print(f"  parsed {source}/{f.name}: {analysis['total_words']} "
                      f"words, {analysis['total_em_dashes']} em-dashes")
    if reference_papers:
        print(f"  parsed {len(reference_papers)} reference papers from "
              f"{REFERENCE_DIR}/ (unweighted; exemplar bank only)")

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

    n_exemplars = write_exemplar_bank(per_paper + reference_papers, field_profile)

    print(f"\n[extract_style] OK. {len(per_paper)} curated + "
          f"{len(reference_papers)} reference papers for field {field!r}."
          + (f" {skipped} source file(s) SKIPPED (pymupdf unavailable): the "
             "profile does not describe them." if skipped else ""))
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
