"""Source-text projection and section splitting for the sci-paper corpus.

Everything that turns a raw corpus document -- LaTeX source or a PDF text layer
-- into normalized prose and labelled section buckets: the section vocabulary
and its classifier, the two named LaTeX projections, and the PDF heading
heuristic.

Split out of `extract_style.py` on 2026-08-25, which had grown past the point
where it could be edited at all. `extract_style` re-exports every public name
below, so `es.classify_section`, `es.latex_to_plain` and
`es.latex_to_numeral_text` keep resolving for existing callers and tests.

Section buckets key every per-section reference distribution in a profile, so a
change here changes what those distributions mean and needs a profile rebuild.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

# Ordered (compiled-regex, bucket) pairs; first match wins.
# Buckets: abstract / intro / data / method / results / discussion /
# conclusion / skip, plus `unknown` for a heading none of them name.
# "skip" excludes the section from analysis entirely.
# Order matters: discussion BEFORE conclusion so "Discussion and Conclusions"
# and "Summary and discussion" both bucket as discussion (richer content).
# Every noun carries its plural. The singular-only forms these patterns used
# until 2026-08-16 made `\bresult\b` miss "Results", `\bconclusion\b` miss
# "Conclusions" and `\bsystematic\b` miss "Systematics" -- the standard
# ApJ/MNRAS/PRD headings -- so those sections fell through to the default.
#
# `method` then had no pattern of its own until 2026-08-25: it WAS the default,
# so it silently absorbed every heading nothing else matched. The wgl bank held
# 1,671 "method" passages against 10 "results" because "method" was not a
# section, it was the residue. Three things fed it -- `.tex` corpus files with
# no `\section` markup at all (a 100-page review split into chunks contributed
# 101 and 88 paragraphs, 100% "method"), PDF table cells accepted as headings
# by the ALL-CAPS heuristic below, and data/observation sections with no bucket
# of their own. All three are now addressed, and an unrecognised heading is
# `unknown` rather than a guess.
SECTION_PATTERNS: list[tuple["re.Pattern[str]", str]] = [
    # `acknowledg` and `bibliograph` are stems, so they carry `\w*` instead of a
    # closing `\b`: written as `\b(acknowledg|bibliograph)\b` they could only
    # ever match those exact strings, and the real headings "Acknowledgements"
    # and "Bibliography" fell through to DEFAULT_SECTION_BUCKET as prose.
    (re.compile(r"(?i)\b(?:acknowledg\w*|bibliograph\w*|appendi(?:x|ces)|references?|literature\s+cited|disclosures?)\b"), "skip"),
    (re.compile(r"(?i)\babstract\b"), "abstract"),
    (re.compile(r"(?i)\b(discussions?|caveats?|limitations?|systematics?|implications?|comparisons?)\b"), "discussion"),
    (re.compile(r"(?i)\b(conclusions?|outlooks?|summar(?:y|ies))\b"), "conclusion"),
    (re.compile(r"(?i)\b(introductions?|motivations?)\b"), "intro"),
    (re.compile(r"(?i)\b(results?|detected|shear-selected|catalogs?\s+of)\b"), "results"),
    # Data/observations are their own section in ApJ/MNRAS/PRD and were being
    # counted as method. Ordered after `results` so "catalogs of ..." keeps its
    # documented results reading.
    (re.compile(r"(?i)\b(data|datasets?|observations?|imaging|photometry|spectroscopy|surveys?|samples?)\b"), "data"),
    # Explicit method vocabulary, deliberately conservative: a heading this does
    # not name (e.g. "Cosmological constraints", "Measurements") becomes
    # `unknown` rather than being guessed into a reference distribution.
    (re.compile(r"(?i)\b(methods?|methodology|formalism|approach(?:es)?|algorithms?|pipelines?|techniques?|models?|modell?ing|theory|simulations?|analys(?:is|es))\b"), "method"),
]
# Never "method". An unrecognised heading is an unknown section, and a reference
# distribution built from unknowns is not a per-section reference at all.
DEFAULT_SECTION_BUCKET = "unknown"


def classify_section(name: str) -> str:
    """Map a raw \\section{…} title string to a normalized bucket.
    Returns 'skip' for sections that should be excluded from analysis."""
    for pattern, bucket in SECTION_PATTERNS:
        if pattern.search(name):
            return bucket
    return DEFAULT_SECTION_BUCKET

# Light LaTeX cleaning. Not a full TeX parser; meant to remove enough
# command/environment noise so word/sentence stats reflect the prose.
RE_TEX_COMMENT = re.compile(r"(?<!\\)%.*?$", re.MULTILINE)
RE_TEX_DISPLAY_MATH = re.compile(
    r"\\begin\{(equation|align|gather|eqnarray|displaymath|multline)\*?\}.*?\\end\{\1\*?\}",
    re.DOTALL,
)
RE_TEX_INLINE_MATH = re.compile(r"\$[^$]+\$|\\\(.+?\\\)", re.DOTALL)
RE_TEX_ENV_FIGURE_TABLE = re.compile(
    r"\\begin\{(figure|table|figure\*|table\*)\}.*?\\end\{\1\}", re.DOTALL
)
RE_TEX_CITE = re.compile(r"\\(?:cite|citep|citet|citealt)\*?\{[^}]*\}")
RE_TEX_LABEL_REF = re.compile(r"\\(?:label|ref|eqref|cref|Cref)\{[^}]*\}")
RE_TEX_INCLUDEGRAPHICS = re.compile(r"\\includegraphics(\[[^\]]*\])?\{[^}]*\}")
# \begin{X} and \end{X} markers — drop entirely so the env name
# (document, enumerate, abstract, ...) doesn't leak into prose stats.
# Must come BEFORE RE_TEX_SIMPLE_CMD or that regex captures group(3) = "X".
RE_TEX_BEGIN_END = re.compile(r"\\(?:begin|end)\{[^}]*\}")
RE_TEX_SIMPLE_CMD = re.compile(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{([^{}]*)\})?")
RE_TEX_BRACES = re.compile(r"[{}]")
RE_TEX_TILDE = re.compile(r"(?<![\\])~")
# Used only by latex_to_numeral_text below: strip a command name without
# consuming its argument, so the digits inside survive.
RE_TEX_MATH_CMD = re.compile(r"\\[a-zA-Z]+\*?")
# LaTeX writes a thousands separator as 14{,}850; collapsing it first keeps
# that one quantity one numeral instead of three.
RE_TEX_THIN_COMMA = re.compile(r"\{\s*,\s*\}")


def _math_numerals(match: "re.Match[str]") -> str:
    """Reduce one math span to its bare numerals and operators."""
    body = RE_TEX_THIN_COMMA.sub(",", match.group(0))
    body = RE_TEX_MATH_CMD.sub(" ", body)
    for token in ("{", "}", "$"):
        body = body.replace(token, " ")
    return " " + body + " "

RE_SECTION = re.compile(
    r"\\(section|subsection|chapter)\*?\{([^}]+)\}", re.IGNORECASE
)

# Many papers put their abstract in an env, NOT in `\section{Abstract}`. We
# need to capture it explicitly because the env typically lives in the
# preamble (before the first \section{}) and would otherwise be dropped.
# AASTeX also accepts `\begin{abstract}` and ApJ's older `\abstract{...}` form.
RE_ABSTRACT_ENV = re.compile(
    r"\\begin\{abstract\}(.*?)\\end\{abstract\}", re.DOTALL | re.IGNORECASE
)


def latex_to_plain(text: str) -> str:
    text = RE_TEX_COMMENT.sub("", text)
    text = RE_TEX_DISPLAY_MATH.sub(" [MATH] ", text)
    text = RE_TEX_INLINE_MATH.sub(" [math] ", text)
    text = RE_TEX_ENV_FIGURE_TABLE.sub(" [FIGURE-OR-TABLE] ", text)
    text = RE_TEX_CITE.sub(" [CITE] ", text)
    text = RE_TEX_LABEL_REF.sub("", text)
    text = RE_TEX_INCLUDEGRAPHICS.sub("", text)
    # Drop \begin{X} / \end{X} markers BEFORE the generic command stripper,
    # so we don't end up substituting in the env name as bare text.
    text = RE_TEX_BEGIN_END.sub("", text)
    # Replace simple commands of form \cmd{arg} with their arg
    text = RE_TEX_SIMPLE_CMD.sub(lambda m: m.group(3) or "", text)
    text = RE_TEX_BRACES.sub("", text)
    text = RE_TEX_TILDE.sub(" ", text)
    return text


def latex_to_numeral_text(text: str) -> str:
    """Reduce LaTeX to prose while PRESERVING the numerals inside math.

    :func:`latex_to_plain` replaces every math span with the token ``[math]``,
    which is correct for lexical and sentence-shape statistics: a formula is
    not prose, and its symbols would pollute word counts. That reduction also
    destroys every numeral in a LaTeX manuscript, so any signal about *how a
    passage distributes its measured quantities* is identically zero on real
    `.tex` input. This second projection exists for those signals only
    (`deai_salience`); it keeps the digits and drops the markup around them.

    Both projections share one set of patterns above, so the two views of a
    document can never drift apart in how they treat comments, citations,
    labels, or commands. They differ in exactly one decision: what happens to
    the contents of an *inline* math span.

    A displayed equation is dropped by both. Its digits are the constants of a
    definition, not quantities the prose is reporting; counting the 3 in a
    volume formula as a reported result would make every derivation look like a
    recital of measurements.
    """
    text = RE_TEX_COMMENT.sub("", text)
    text = RE_TEX_DISPLAY_MATH.sub(" ", text)
    text = RE_TEX_INLINE_MATH.sub(_math_numerals, text)
    text = RE_TEX_ENV_FIGURE_TABLE.sub(" ", text)
    text = RE_TEX_CITE.sub(" ", text)
    text = RE_TEX_LABEL_REF.sub("", text)
    text = RE_TEX_INCLUDEGRAPHICS.sub("", text)
    text = RE_TEX_BEGIN_END.sub("", text)
    text = RE_TEX_SIMPLE_CMD.sub(lambda m: m.group(3) or "", text)
    text = RE_TEX_BRACES.sub("", text)
    text = RE_TEX_TILDE.sub(" ", text)
    return re.sub(r"[ \t]+", " ", text)


def split_into_sections(raw_tex: str) -> dict[str, str]:
    """Best-effort split by \\section / \\subsection / \\chapter headers.

    Returns {bucket: text} keyed by the normalized buckets in SECTION_PATTERNS
    (abstract / intro / method / results / discussion / conclusion).
    Sections classified as 'skip' (acknowledgments, bibliography, appendix,
    references, disclosures) are excluded entirely. The text BEFORE the first
    section header (LaTeX preamble: \\title, \\author, macro definitions,
    optionally \\begin{abstract}) is also dropped — it's not body prose.

    If no section markers are found at all, returns {"unknown": raw_tex} so
    the caller can decide what to do (typically: treat as a single bucket).
    """
    sections: dict[str, list[str]] = defaultdict(list)

    # Capture \begin{abstract}…\end{abstract} env content explicitly. These
    # almost always live in the preamble (before the first \section{}), so
    # the regular sweep below would miss them entirely. Multiple abstract
    # envs (rare; book-style chapter abstracts) are concatenated.
    for m in RE_ABSTRACT_ENV.finditer(raw_tex):
        sections["abstract"].append(m.group(1))

    matches = list(RE_SECTION.finditer(raw_tex))
    if not matches:
        # No section headers anywhere. Two cases:
        #   - the file IS just an abstract / standalone TeX → already captured
        #   - the file is some macro/style include with no prose → "unknown"
        if "abstract" in sections:
            return {k: "\n\n".join(v) for k, v in sections.items()}
        return {"unknown": raw_tex}

    for i, m in enumerate(matches):
        name = m.group(2).strip()
        bucket = classify_section(name)
        if bucket == "skip":
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_tex)
        sections[bucket].append(raw_tex[start:end])

    return {k: "\n\n".join(v) for k, v in sections.items()}


# Heading lines look like one of:
#   "Introduction" / "INTRODUCTION"
#   "1. Introduction" / "1 Introduction" / "1.2 Methods"
#   numbered + word, possibly with trailing punctuation
# Match anchored to whole-line because PDF text extraction tends to put
# headings on their own line.
RE_PDF_LINE_HEADER = re.compile(
    r"^\s*"
    r"(?:\d+(?:\.\d+)*\.?\s+)?"  # optional "1.", "1.2", "1.2.3 "
    r"("
    r"introduction|background|motivation|"
    r"observations?|data|sample|methods?|methodology|analysis|theory|"
    r"results?|"
    r"discussion|limitations?|caveats?|implications?|comparison|"
    r"conclusions?|summary|outlook|"
    r"abstract|"
    r"references?|bibliography|acknowledg(?:e?ments?|ements?)|appendix"
    r")"
    r"\s*[:.]?\s*$",
    re.IGNORECASE,
)


# A block ends a paragraph only if it ends a sentence. Closing quotes/brackets
# may follow the stop.
RE_SENTENCE_TERMINAL = re.compile(r"[.!?][)\]\"'’”]*\s*$")


def _rejoin_pdf_paragraphs(blocks: list[str]) -> list[str]:
    """Rebuild paragraphs from a PDF text layer's blocks.

    `get_text("blocks")` is documented as visually-distinct blocks, and the
    original code took that to mean paragraphs. On real journal PDFs it does
    not: measured over two corpus PDFs, blocks run to a median of 5 and 16
    words and only 21-23% of them end a sentence, i.e. roughly four in five are
    line fragments mid-paragraph. Downstream that was fatal, because the
    exemplar bank drops paragraphs under 30 words and `document_shape` needs
    sections carrying at least two substantial paragraphs: one 90-PDF corpus
    yielded exemplars from 3 files, and a complete paper could reduce to a
    single measurable section.

    A block therefore continues the previous paragraph unless the previous one
    ended a sentence. Headings are never absorbed and never absorb, so the
    section splitter still sees them on their own line.
    """
    out: list[str] = []
    prev_was_heading = False
    for raw in blocks:
        block = raw.strip()
        if not block:
            continue
        is_heading = _classify_pdf_heading(block.splitlines()[0].strip()) is not None
        if (out and not is_heading and not prev_was_heading
                and not RE_SENTENCE_TERMINAL.search(out[-1])):
            out[-1] = f"{out[-1]} {block}"
        else:
            out.append(block)
        prev_was_heading = is_heading
    return out


def extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF using pymupdf, with paragraph-level segmentation.

    Uses pymupdf's `get_text("blocks")` mode so each visually-distinct block
    (≈ paragraph, caption, header) is preserved as a unit separated by
    double newlines. This is necessary downstream — the exemplar bank
    splits paragraphs on `\\n\\s*\\n`; with default `get_text()` (which
    yields soft single-line breaks) every section collapses into one mega-
    paragraph and gets filtered out by the max-words cap.

    Raises ImportError if pymupdf is not installed. Caller is expected
    to handle the exception (skip the file with a warning).
    """
    try:
        import pymupdf  # type: ignore[import-not-found]
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore[import-not-found,no-redef]
        except ImportError:
            raise ImportError(
                "pymupdf not installed; install with `pip install pymupdf` "
                "to ingest .pdf corpus files"
            )

    doc = pymupdf.open(path)
    paragraphs: list[str] = []
    try:
        for page in doc:
            for block in page.get_text("blocks"):
                # block tuple: (x0, y0, x1, y1, text, block_no, block_type)
                # block_type == 0 means text; non-zero is an image block.
                if len(block) > 6 and block[6] != 0:
                    continue
                if len(block) < 5:
                    continue
                t = block[4].strip()
                if t:
                    paragraphs.append(t)
    finally:
        doc.close()

    # Join blocks with blank-line separators so downstream paragraph
    # splitters see real boundaries.
    text = "\n\n".join(_rejoin_pdf_paragraphs(paragraphs))
    # Within a single block, soft-hyphenated wrap is still possible
    # ("method-\nology"). De-hyphenate.
    text = re.sub(r"-\n(\w)", r"\1", text)
    # PDF text layers emit typographic ligatures as single codepoints, so the
    # tokenizer splits "significant" into "signi" + "cant" and the fragments
    # enter the lexicon and the exemplar bank as if they were words. Expanding
    # them here keeps the fix at the one place ligatures can enter the corpus.
    text = text.translate(LIGATURE_TABLE)
    return text


# Typographic ligatures a PDF text layer emits as one codepoint. Left in place
# they fragment the words they appear in -- "ﬁ" alone accounts for `signi`/`cant`
# style fragments across the corpus.
LIGATURE_TABLE = str.maketrans({
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
})


# Minimum shape of an ALL-CAPS line before it may be read as a heading. Each
# threshold rejects a specific class of table cell that was being accepted as a
# section heading; see _classify_pdf_heading for the measured counts.
PDF_HEADING_MIN_WORDS = 2           # "S", "RA", "NFW", "A85", "BCG" are cells
PDF_HEADING_MIN_LETTERS = 4         # "RA (J2000)", "(10^14 M)" carry too few
PDF_HEADING_MIN_LETTER_FRAC = 0.75  # rejects "S/N", "B =", "RS|"


def _classify_pdf_heading(stripped: str) -> str | None:
    """If `stripped` looks like a PDF section header, return its classified
    bucket; otherwise return None.

    Two-stage detection (precision-first):
      1. Keyword-based via RE_PDF_LINE_HEADER (matches "Introduction" /
         "1.2 Methods" / etc.). Near-zero false positives.
      2. ALL-CAPS heuristic for thematic headings the keyword list does not
         name ("2 OPTIMAL FILTER FOR GALAXY"), constrained by the
         PDF_HEADING_MIN_* thresholds below.

    Until 2026-08-25 stage 2 required only "short, ≥ 60% uppercase, no body
    punctuation", which a journal PDF's table cells satisfy constantly. Of 325
    headings it detected across the 90 corpus PDFs, 305 were cells like "S",
    "X", "RA", "S/N", "NFW", "A85" and "(10^14 M)". Each one switched the
    current bucket, so prose following a table was filed under whatever the
    last cell classified as — and since nothing matched, that was the "method"
    catchall. A single-word line can now only be a heading via the keyword
    branch, which knows what section names look like.
    """
    if not stripped or len(stripped.split()) > 12:
        return None

    m = RE_PDF_LINE_HEADER.match(stripped)
    if m:
        return classify_section(m.group(1))

    # Reject obvious body-text shapes
    if "," in stripped or "?" in stripped or ";" in stripped:
        return None
    # Trailing period would still be ambiguous (numbered prefixes "1." vs body
    # sentences) — accept either way; ALL-CAPS body sentences are unusual.

    # Strip optional numbered prefix (e.g., "2 ", "10.", "3.1.4 ")
    numbered = re.match(r"^\d+(?:\.\d+)*\.?\s+", stripped) is not None
    body = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", stripped)
    # A numbered prefix on a short, non-sentence line is itself a heading
    # signal, independent of case. Journals set section titles in title case
    # ("2.1. Marine Ice Sheet Instability", "3. Controversial Ideas to MICI"),
    # which neither the keyword list nor the ALL-CAPS test below can see; the
    # titles were absorbed into the following paragraph and their documents
    # collapsed to a single section. Bounded to short lines with no sentence
    # punctuation so a numbered list item inside prose is not caught.
    # The letter floor is what separates "3. Controversial Ideas" from a
    # numeric table row like "3 4 5", which otherwise reads as a numbered
    # heading with an unknown title.
    if (numbered and body
            and PDF_HEADING_MIN_WORDS <= len(body.split()) <= 10
            and sum(1 for c in body if c.isalpha()) >= PDF_HEADING_MIN_LETTERS
            and not RE_SENTENCE_TERMINAL.search(body)):
        return classify_section(body)
    if len(body.split()) < PDF_HEADING_MIN_WORDS:
        return None
    letters = [c for c in body if c.isalpha()]
    if len(letters) < PDF_HEADING_MIN_LETTERS:
        return None
    non_space = [c for c in body if not c.isspace()]
    if len(letters) / len(non_space) < PDF_HEADING_MIN_LETTER_FRAC:
        return None
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio < 0.6:
        return None
    return classify_section(body)


def split_pdf_into_sections(text: str) -> dict[str, str]:
    """Heuristic section splitter for PDF-extracted text.

    Walks lines; when a line looks like a section header, switches the
    current bucket via _classify_pdf_heading(). Lines before any detected
    header go to "unknown" (typically title + author block); 'skip'
    sections (acknowledgments / appendix / bibliography) drop their content.

    Multi-line ALL-CAPS headers (e.g. "2 OPTIMAL FILTER FOR GALAXY" on one
    line, "OVERDENSITIES" on the next) are handled naturally: the second
    line is detected as another header and re-classifies to the same bucket
    (since both classify to 'method' in the absence of keyword match), so
    no body content gets misattributed.
    """
    sections: dict[str, list[str]] = defaultdict(list)
    current = "unknown"
    for line in text.splitlines():
        stripped = line.strip()
        bucket = _classify_pdf_heading(stripped)
        if bucket is not None:
            # A heading whose own title names no section type is a SUBSECTION
            # of whatever we are already in ("2.1 Map making" under "2 Method"),
            # so it drops its line but inherits the parent bucket. Resetting to
            # `unknown` here emptied the parent section: once numbered
            # subsection titles became detectable, `results` fell from 26 to 7
            # because each subsection re-bucketed away from its own parent.
            if bucket != DEFAULT_SECTION_BUCKET:
                current = bucket
            continue  # drop the header line itself
        if current == "skip":
            continue
        sections[current].append(line)
    # Drop empty buckets
    out = {}
    for k, lines in sections.items():
        joined = "\n".join(lines).strip()
        if joined:
            out[k] = joined
    return out

