"""Corpus-referenced domain-register feedback for scientific prose (L0).

A draft can be free of every AI-ism and still read as though it were written
for a different discipline. The tell is a term the author's own field does not
use: a weak-lensing paper that reports `AUC` is speaking machine learning to
an audience that says completeness and purity.

The judgement cannot come from a hand-written list of "ML words", and the
corpus says why. In the 15,599-passage astronomy reference, `AUC` appears in 1
passage, but `epoch` appears in 415 and `accuracy` in 835 -- because an epoch
is an observation time and accuracy is ordinary English. Any curated
cross-discipline blacklist flags all three. Document frequency in the field's
own corpus separates them, needs no maintenance, and re-derives itself for any
new field (guardrail 7 of the standard).

Two rules share the one lexicon:

* `register-zero` (owner rule, 2026-09-04): EVERY word of the body prose is
  looked up, and a word in zero corpus passages is a strong advisory unless
  the manuscript itself supplies the reason the owner allows -- the word is
  defined here (an acronym expansion or a defining sentence), it is a proper
  name, or the field writes its stem and only the derived form is unattested.
  Those three are read mechanically and downgrade the finding to ordinary;
  "first use of this method in the field" is a disposition the author records.
  This is a vocabulary AUDIT, not a detector, and the record says so: on 40
  held-out refereed papers the median is 2.57 zero-hit words per 1,000 against
  1.25 on machine documents, rank AUC 0.242 (EVALUATION §23) -- human papers
  carry MORE unattested words. What it finds is register leakage a referee
  would stop on: software vocabulary in an astronomy manuscript, or a coined
  term with no definition.
* `register-foreign`: a term the manuscript leans on (`MIN_MANUSCRIPT_USES`
  uses or more) whose document-frequency RATE is below the gate but not zero.
  Every paper has rare words, so a single mention of one is uninformative.

Three constructions defeat a naive frequency test, and each is handled rather
than thresholded away:

* **Compounds.** Hyphenation is an open construction, so almost every compound
  is corpus-rare -- `aperture-mass`, the core observable of this field, appears
  in 8 passages of 15,599. A compound is judged by its RAREST part instead: it
  is native when every part it is built from is native.
* **Subscripts.** `\\newcommand{\\Kraw}{S_\\mathrm{raw}}` renders a subscript,
  not a word. Reading macro bodies without checking for a preceding `_` or `^`
  turns every symbol decoration into a fake foreign term.
* **Possessives.** `sub-halo's` and `sub-halo` are one term.

Macro definitions are read as well as prose, because a term bound to a macro is
by construction one the author uses repeatedly, and the reduction that feeds
every other axis erases it: `\\newcommand{\\AUC}{\\mathrm{AUC}}` followed by 12
uses of `\\AUC` leaves no occurrence of the string "AUC" in reduced prose.

This axis emits advisories, never `l0_target`s. Field register is a judgement
the author owns: a term may be deliberate, may be the accepted name of a
borrowed method, or may be the very thing the paper introduces.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_feedback as feedback  # noqa: E402 because sibling tools are importable only after the sys.path insert above
import deai_metrics as metrics  # noqa: E402 because sibling tools are importable only after the sys.path insert above
import extract_style as es  # noqa: E402 because sibling tools are importable only after the sys.path insert above

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
LEXICON_FILENAME = "register_lexicon.json"

RE_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
RE_NEWCOMMAND = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand)\s*\{?\\([A-Za-z]+)\}?"
    r"\s*(?:\[\d+\])?\s*\{(.*)")
# A word-rendering macro body, with the character before it captured so a
# subscript or superscript decoration can be told from a term.
RE_MACRO_TEXT = re.compile(
    r"(.?)\\(?:mathrm|mathit|text|textrm|mathsf|operatorname)\s*\{([^{}]+)\}")
RE_POSSESSIVE = re.compile(r"'s$")
# A bibliography is an environment, not a section, so the section-level `skip`
# bucket never sees it: it sits inside the span of whatever section precedes it.
RE_BIB_ENV = re.compile(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}",
                        re.DOTALL)
RE_BIBITEM = re.compile(r"^\s*\\bibitem\b", re.MULTILINE)
# Mathematics never contributes vocabulary on the corpus side: the passage
# projection replaces every math span with `[math]` before counting words.
# Detection ran `latex_to_plain` one LINE at a time, so a `$...$` or an
# `equation` environment that crossed a line boundary was invisible to it and
# the macro names inside surfaced as words with df 0 (`\dsep`, `\rmain`). The
# third instance of the calibration/detection projection asymmetry, after the
# preamble (§17.4) and citation commands (§18.1); this time the seam is the line.
RE_MATH_SPAN = re.compile(
    r"\\begin\{(equation|align|gather|eqnarray|displaymath|multline|subequations)"
    r"\*?\}.*?\\end\{\1\*?\}"
    r"|\\\[.*?\\\]|\$\$.*?\$\$|\$[^$]+\$|\\\(.*?\\\)", re.DOTALL)
# Float placement options, bibliography commands and code spans render no
# prose either; each leaked one token as a term (`htb`, `aasjournalv7`,
# `cw_mscale`). The float pattern keeps its `\begin{...}` so the environment
# stripper downstream still sees it.
RE_FLOAT_OPTION = re.compile(r"(\\begin\{[A-Za-z*]+\})\[[^\]\n]*\]")
RE_BIB_COMMAND = re.compile(r"\\bibliography(?:style)?\s*\{[^}]*\}")
RE_CODE_SPAN = re.compile(
    r"\\(?:texttt|lstinline|url|path)\s*\{[^{}]*\}|\\href\s*\{[^{}]*\}"
    r"|\\verb\*?(?P<delim>[^A-Za-z\s]).*?(?P=delim)")
# What the manuscript says about its own vocabulary. An acronym is defined by
# the expansion-then-parenthesis convention; a coined term by a defining
# sentence. Both are the owner's "the word is our own definition" reason, read
# from the text rather than asked for.
RE_ACRONYM_DEF = re.compile(r"\(([A-Z][A-Za-z0-9]{1,9})s?\)")
RE_HEADING = es.RE_HEADING_COMMAND
RE_DEFINING = re.compile(
    r"\b(?:we (?:define|call|term|name|introduce|refer to)|hereafter|henceforth"
    r"|(?:is|are) defined as|defined as|denoted?|which we call|referred to as)\b",
    re.I)
# A derived form of a native word is reported against its stem rather than as
# foreign: the field writes `resolvable`, the manuscript `resolvability`.
# Suffix stripping, longest first, with the -e / -y / doubled-consonant
# restorations; deliberately small, because a stemmer that reaches too far
# turns a genuinely foreign word into a false native.
STEM_SUFFIXES = ("ations", "ation", "ities", "ity", "ness", "ments", "ment",
                 "ingly", "ing", "edly", "ed", "ies", "ally", "al", "ly",
                 "ers", "er", "es", "s")

# A term must carry weight in the manuscript before its RARITY means anything;
# absence is judged at floor 1 by `register-zero` above. This floor governs
# only `register-foreign`.
# Five uses was an estimate; 15 is where the curve was cut once 203 held-out
# refereed papers made the false-positive rate measurable (EVALUATION §18.4).
# Sweeping this knob against those papers and 173 machine documents:
#
#   uses   human docs flagged   rank AUC (machine over human)
#      5               85.2%    0.154
#     10               60.1%    0.235
#     15               44.8%    0.285
#     50               12.3%    0.438
#
# The AUC column is why the operating point is not a detector threshold: it is
# below 0.5 everywhere, so the axis fires MORE on refereed prose than on
# machine prose at every setting, and tightening silences the machine side
# faster than the human one. What the knob buys is advisory volume, and a
# paper already good enough to referee should not draw an advisory more often
# than not. 15 is the first setting on the curve below one document in two.
MIN_MANUSCRIPT_USES = 15
# Document-frequency rate below which the field corpus is judged not to use a
# term. On the 15,599-passage reference this is single-digit passages: `AUC`
# (6.4e-5) qualifies, while `logistic` (3.8e-4), `epoch` (2.7e-2) and
# `accuracy` (5.4e-2) do not.
RARE_DF_RATE = 1e-4
# Below this the corpus itself is too small to call anything absent from it.
MIN_CORPUS_PASSAGES = 500


def resolves_rare_rate(n_passages: int) -> bool:
    """Can this bank express a non-zero document frequency below the gate?

    `MIN_CORPUS_PASSAGES` is a *count* and `RARE_DF_RATE` is a *rate*, and the
    two are unrelated: a bank of n passages cannot express any non-zero rate
    below 1/n, so wherever 1/n >= RARE_DF_RATE the firing rule collapses from
    "df rate below the gate" to "df == 0" and a single occurrence anywhere
    clears the flag.

    EVALUATION §15.5 derived exactly this for a 254-document subfield bank and
    used it to reject that bank, but the conclusion was never turned into a
    guard. It applies to every bank: at n = 706 (the shipped `wgl-letter`
    profile) the resolution is 14.2x coarser than the gate, and the axis
    reported `measured` with `reason: null` while running a different rule
    from the documented one.
    """
    return n_passages > 0 and (1.0 / n_passages) < RARE_DF_RATE


def load_lexicon(field_profile_dir: Path | None) -> dict[str, Any] | None:
    if field_profile_dir is None:
        return None
    path = field_profile_dir / LEXICON_FILENAME
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "document_frequency" not in data:
        return None
    return data


def resolving_lexicon(
        field_profile_dir: Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    """The lexicon to judge against, and the profile it came from.

    A register axis measures *domain* vocabulary, and a variant profile like
    `wgl-letter` is a **format**, not a domain: a letter and a full paper in
    one field share their words and differ in length and structure, which
    other axes measure. Its 706-passage bank cannot express the 1e-4 gate, so
    the rule collapses to "df == 0" and any field term the small bank happens
    to lack reads as foreign. Measured on 36 letter-format documents, the
    letter bank produced 262 findings the field bank did not -- `sne`, `bao`,
    `pantheon`, `quasars`, `posteriors`, and the word `letter` itself -- to
    2 in the other direction (EVALUATION §18.5).

    So a `<field>-<variant>` profile whose own bank is too coarse falls back
    to `<field>`, and the borrowed source is named in the axis status and in
    every finding rather than being applied silently.
    """
    own = load_lexicon(field_profile_dir)
    if own is None or field_profile_dir is None:
        return own, field_profile_dir
    if resolves_rare_rate(int(own.get("n_passages", 0))):
        return own, field_profile_dir
    base, sep, _ = field_profile_dir.name.partition("-")
    if not sep or not base:
        return own, field_profile_dir
    sibling_dir = field_profile_dir.parent / base
    sibling = load_lexicon(sibling_dir)
    if sibling is None or not resolves_rare_rate(int(sibling.get("n_passages", 0))):
        return own, field_profile_dir
    return sibling, sibling_dir


def register_axis_status(field_profile_dir: Path | None) -> dict[str, Any]:
    lexicon, source = resolving_lexicon(field_profile_dir)
    borrowed = source is not None and source != field_profile_dir
    if lexicon is None:
        return feedback.axis_status(
            "L0.register", "unmeasured",
            reason=f"{LEXICON_FILENAME} is unavailable",
            detector="deai_register",
        )
    n_passages = int(lexicon.get("n_passages", 0))
    if n_passages < MIN_CORPUS_PASSAGES:
        return feedback.axis_status(
            "L0.register", "degraded",
            reason=(f"corpus has {n_passages} passages, below the "
                    f"{MIN_CORPUS_PASSAGES} floor for calling a term absent"),
            detector="deai_register",
        )
    if not resolves_rare_rate(n_passages):
        return feedback.axis_status(
            "L0.register", "degraded",
            reason=(f"corpus has {n_passages} passages, so the finest non-zero "
                    f"document-frequency rate it can express is "
                    f"{1.0 / n_passages:.2e} — "
                    f"{(1.0 / n_passages) / RARE_DF_RATE:.1f}x coarser than the "
                    f"{RARE_DF_RATE:.0e} gate. The rule in force is 'df == 0', "
                    f"not 'df rate below the gate'; a bank needs more than "
                    f"{int(1 / RARE_DF_RATE):,} passages to run the documented one"),
            detector="deai_register",
        )
    if borrowed:
        return feedback.axis_status(
            "L0.register", "measured",
            reason=(f"own bank too coarse for the {RARE_DF_RATE:.0e} gate; "
                    f"judged against the same field's {source.name} bank "
                    f"({n_passages:,} passages), because a format variant "
                    f"shares its domain vocabulary"),
            detector="deai_register",
        )
    return feedback.axis_status("L0.register", "measured", detector="deai_register")


def normalize(term: str) -> str:
    return RE_POSSESSIVE.sub("", term.lower()).strip("-'")


def macro_terms(text: str) -> dict[str, str]:
    """Map macro name -> the word it renders, skipping symbol decorations."""
    out: dict[str, str] = {}
    for match in RE_NEWCOMMAND.finditer(text):
        name, body = match.group(1), match.group(2)
        for lead, chunk in RE_MACRO_TEXT.findall(body):
            if lead in {"_", "^"}:
                continue
            words = RE_WORD.findall(chunk)
            if words:
                out.setdefault(name, words[0])
                break
    return out


def body_only(text: str) -> str:
    """Blank the regions the corpus side never saw, keeping line numbers.

    The corpus document frequency is built from `exemplar_paragraphs.jsonl`,
    which `extract_style` produces by section-splitting and dropping the
    preamble and every `skip` bucket. Detection read the whole raw file, so the
    two sides of one ratio ran on different projections: `dipartimento`,
    `cedex` and an author's surname have df 0 on the corpus side because front
    matter and the bibliography were stripped there, and count >= 5 on the
    manuscript side because they were not stripped here. The finding was
    manufactured by the asymmetry, not by anything about the vocabulary.

    Measured on the 203 held-out refereed papers of EVALUATION §17, **58.7%**
    of register findings came from outside body prose: 27.5% preamble, 26.3%
    bibliography, 4.1% TeX control words (which live in preamble macro
    definitions), 0.9% `skip` sections.

    `deai_salience` needs none of this — on the same papers 0 of its 1,077
    findings fall in a bibliography — so this stays here rather than becoming
    shared machinery for a single consumer.

    Lines are blanked rather than deleted so `usage["line"]` still indexes the
    original document and section attribution keeps working. Spans that cross
    lines -- mathematics, code, float options, bibliography commands -- are
    blanked character by character for the same reason (`RE_MATH_SPAN`).
    """
    lines = text.splitlines()
    drop: set[int] = set()
    for start, end, label in metrics.section_line_ranges(text):
        if label == "(preamble)" or es.classify_section(label) == "skip":
            drop.update(range(start, end + 1))
    for pattern in (RE_BIB_ENV, RE_BIBITEM):
        for match in pattern.finditer(text):
            first = text[:match.start()].count("\n") + 1
            drop.update(range(first, first + match.group(0).count("\n") + 1))
    # The abstract is body prose the corpus does carry, and in AASTeX it sits
    # inside the preamble that was just dropped.
    for match in es.RE_ABSTRACT_ENV.finditer(text):
        first = text[:match.start()].count("\n") + 1
        drop.difference_update(
            range(first, first + match.group(0).count("\n") + 1))
    body = "\n".join("" if n in drop else line
                     for n, line in enumerate(lines, start=1))

    def blank(match: "re.Match[str]") -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    # Headings too: the corpus passages are the prose UNDER a heading, never
    # its words, so a section title counted here and nowhere else.
    for pattern in (RE_MATH_SPAN, RE_BIB_COMMAND, RE_CODE_SPAN, RE_HEADING):
        body = pattern.sub(blank, body)
    return RE_FLOAT_OPTION.sub(
        lambda match: match.group(1) + " " * (len(match.group(0)) - len(match.group(1))),
        body)


def manuscript_terms(text: str) -> dict[str, dict[str, Any]]:
    """Count each candidate term, from prose and from word-rendering macros."""
    macros = macro_terms(text)
    body = re.sub(r"^\s*\\(?:new|renew|provide)command.*$", "", body_only(text),
                  flags=re.MULTILINE)
    counts: Counter[str] = Counter()
    lines: dict[str, int] = {}
    surface: dict[str, str] = {}

    def record(raw: str, line_no: int, times: int = 1) -> None:
        key = normalize(raw)
        if len(key) < 3:
            return
        counts[key] += times
        lines.setdefault(key, line_no)
        surface.setdefault(key, raw)

    for line_no, line in enumerate(body.splitlines(), start=1):
        for name, word in macros.items():
            uses = len(re.findall(rf"\\{re.escape(name)}(?![A-Za-z])", line))
            if uses:
                record(word, line_no, uses)
        for word in RE_WORD.findall(es.latex_to_plain(line)):
            record(word, line_no)

    return {term: {"count": count, "line": lines[term], "surface": surface[term]}
            for term, count in counts.items()}


def corpus_document_frequency(term: str, table: dict[str, Any]) -> tuple[int, str]:
    """Document frequency of a term, and which part of it that count came from.

    A hyphenated compound is native to the field when every part is native, so
    its frequency is the frequency of its RAREST part. Judging the compound
    string itself would call `aperture-mass` foreign to weak lensing.
    """
    parts = [part for part in term.split("-") if len(part) >= 3]
    # `no-dip` has one part long enough to carry meaning; judging the whole
    # string instead called every `no-X` / `in-X` compound absent at floor 1.
    if parts and "-" in term:
        rarest = min(parts, key=lambda part: int(table.get(part, 0)))
        return int(table.get(rarest, 0)), rarest
    return int(table.get(term, 0)), term


def zero_hit_context(text: str) -> dict[str, set[str]]:
    """What the manuscript says about its own words, read once per document.

    `acronym`: terms introduced by the expansion-then-parenthesis convention.
    `defined`: every term in a sentence that defines something. `name`: terms
    capitalised at every mid-sentence occurrence and never written lower-case
    (a survey, an instrument, a person). Sentence-initial occurrences carry no
    capitalisation evidence and are skipped.
    """
    # `body_only` has blanked the headings, so the first sentence under one
    # opens the text rather than fusing with the title: left in place,
    # `Validation\nRescored catalogs` read `Rescored` as a mid-sentence
    # capital and therefore as a name.
    plain = es.latex_to_plain(body_only(text))
    acronyms = {normalize(found) for found in RE_ACRONYM_DEF.findall(plain)}
    defined: set[str] = set()
    capitalised: Counter[str] = Counter()
    lower: Counter[str] = Counter()
    for sentence in es.sentences(plain):
        words = RE_WORD.findall(sentence)
        if RE_DEFINING.search(sentence):
            defined.update(normalize(word) for word in words)
        for word in words[1:]:
            (capitalised if word[0].isupper() else lower)[normalize(word)] += 1
    names = {term for term in capitalised if lower[term] == 0}
    return {"acronym": acronyms, "defined": defined, "name": names}


def native_stem(term: str, table: dict[str, Any]) -> str | None:
    """The corpus-attested stem a derived form reduces to, or None."""
    for suffix in STEM_SUFFIXES:
        if not term.endswith(suffix) or len(term) - len(suffix) < 3:
            continue
        root = term[:-len(suffix)]
        candidates = [root, root + "e", root + "y"]
        if len(root) > 1 and root[-1] == root[-2]:
            candidates.append(root[:-1])
        for candidate in candidates:
            if int(table.get(candidate, 0)) > 0:
                return candidate
    return None


def zero_hit_class(term: str, context: dict[str, set[str]],
                   table: dict[str, Any]) -> tuple[str | None, str | None]:
    """(justification, native stem) the manuscript supplies for a zero-hit term.

    None means the text gives no reason for the word, so the finding is strong.
    """
    if term in context["acronym"] or term in context["defined"]:
        return "defined-here", None
    if term in context["name"]:
        return "name", None
    stem = native_stem(term, table)
    if stem is not None:
        return "derived-form", stem
    return None, None


ZERO_HIT_ACTION = (
    "Four dispositions, in order of preference: name the quantity this field "
    "already has a word for; keep the term but define it at first use and say "
    "what it measures in field terms; if this paper coins it, make sure the "
    "definition precedes every use; if the method itself is new to the field, "
    "record that as the accepted reason. Do not swap a term whose replacement "
    "would change the claim.")


def _zero_hit_message(surface: str, uses: int, n_passages: int,
                      justification: str | None, stem: str | None) -> str:
    head = (f"{surface!r} is used {uses} time{'s' if uses != 1 else ''} here "
            f"and appears in 0 of {n_passages} field-corpus passages.")
    if justification == "defined-here":
        return (f"{head} The manuscript defines it (an acronym expansion or a "
                "defining sentence), so it reads as this paper's own term; "
                "confirm the definition precedes every use.")
    if justification == "name":
        return (f"{head} It is capitalised at every use, so it reads as a proper "
                "name (a survey, an instrument, a person).")
    if justification == "derived-form":
        return (f"{head} The field writes {stem!r}; only this derived form is "
                "unattested.")
    return (f"{head} Nothing in the manuscript marks it as a coined term, a "
            "defined acronym, or a name, so a reader in this field has no "
            "way to resolve it.")


def register_findings(text: str, field_profile_dir: Path | None,
                      path: str | Path | None = None) -> list[dict[str, Any]]:
    lexicon, source = resolving_lexicon(field_profile_dir)
    if lexicon is None:
        return []
    n_passages = int(lexicon.get("n_passages", 0))
    if n_passages < MIN_CORPUS_PASSAGES:
        return []
    table = lexicon["document_frequency"]
    section_ranges = metrics.section_line_ranges(text)
    # A bank too coarse for the gate still carries real evidence -- a term in
    # zero corpus passages is absent whatever the resolution -- so the findings
    # stand and it is their status that changes. Silencing them would convert
    # a degraded measurement into zero findings.
    resolved = resolves_rare_rate(n_passages)
    reference = {"field_profile": str(source) if source else None,
                 "borrowed_from": source.name
                 if source and source != field_profile_dir else None,
                 "n_passages": n_passages,
                 "rare_df_rate": RARE_DF_RATE,
                 "min_manuscript_uses": MIN_MANUSCRIPT_USES,
                 "resolves_rare_rate": resolved,
                 "provenance": LEXICON_FILENAME}
    context: dict[str, set[str]] | None = None

    findings: list[dict[str, Any]] = []
    for term, usage in sorted(manuscript_terms(text).items()):
        df, basis = corpus_document_frequency(term, table)
        section = next((label for start, end, label in section_ranges
                        if start <= usage["line"] <= end), "(unknown)")
        if df == 0:
            if context is None:
                context = zero_hit_context(text)
            justification, stem = zero_hit_class(term, context, table)
            findings.append(feedback.make_finding(
                kind="advisory", layer="L0",
                rule=f"register-zero:{term}", scope="document",
                calibration_unit="document",
                line=usage["line"], section=section, path=path,
                detector="deai_register",
                measurement_status="measured" if resolved else "degraded",
                strength="ordinary" if justification else "strong",
                observed={"term": usage["surface"],
                          "manuscript_uses": usage["count"],
                          "corpus_document_frequency": 0,
                          "frequency_basis": basis,
                          "justification": justification,
                          "native_stem": stem},
                reference={**reference, "use_floor": 1},
                normalized_distance=RARE_DF_RATE,
                confidence={"value": 0.5 if justification else 1.0,
                            "basis": (f"absent from all {n_passages} corpus "
                                      f"passages; justification read from the "
                                      f"manuscript: {justification or 'none'}")},
                message=_zero_hit_message(usage["surface"], usage["count"],
                                          n_passages, justification, stem),
                action=ZERO_HIT_ACTION,
                evidence=[term, usage["count"], 0, justification],
            ))
            continue
        if usage["count"] < MIN_MANUSCRIPT_USES:
            continue
        rate = df / n_passages
        if rate >= RARE_DF_RATE:
            continue
        via = "" if basis == term else f" (judged on its rarest part {basis!r})"
        findings.append(feedback.make_finding(
            kind="advisory", layer="L0",
            rule=f"register-foreign:{term}", scope="document",
            calibration_unit="document",
            line=usage["line"], section=section, path=path,
            detector="deai_register",
            measurement_status="measured" if resolved else "degraded",
            strength="ordinary",
            observed={"term": usage["surface"], "manuscript_uses": usage["count"],
                      "corpus_document_frequency": df,
                      "frequency_basis": basis,
                      "corpus_df_rate": round(rate, 8)},
            reference=reference,
            normalized_distance=RARE_DF_RATE - rate,
            confidence={"value": min(1.0, usage["count"] / 10.0),
                        "basis": (f"{usage['count']} manuscript uses against "
                                  f"{df}/{n_passages} corpus passages")},
            message=(
                f"{usage['surface']!r} is used {usage['count']} times here but "
                f"appears in {df} of {n_passages} field-corpus passages "
                f"({rate:.1e}){via}. The term is outside the register the "
                "audience reads in."),
            action=ZERO_HIT_ACTION,
            evidence=[term, usage["count"], df],
        ))
    return findings


def calibrate(field_profile_dir: Path) -> dict[str, Any]:
    """Count per-term document frequency across the field's own passage banks."""
    banks = [field_profile_dir / "exemplar_paragraphs.jsonl",
             field_profile_dir / "human_abstracts_extra.jsonl"]
    document_frequency: Counter[str] = Counter()
    n_passages = 0
    for bank in banks:
        if not bank.exists():
            continue
        with bank.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                passage = record.get("text", "")
                if not passage.strip():
                    continue
                n_passages += 1
                seen: set[str] = set()
                for word in RE_WORD.findall(es.latex_to_plain(passage)):
                    key = normalize(word)
                    if len(key) < 3:
                        continue
                    seen.add(key)
                    # Index the parts too, so a compound in the manuscript can
                    # be judged by parts the corpus writes as separate words.
                    for part in key.split("-"):
                        if len(part) >= 3:
                            seen.add(part)
                document_frequency.update(seen)

    payload = {
        "n_passages": n_passages,
        "n_terms": len(document_frequency),
        "sources": [bank.name for bank in banks if bank.exists()],
        "document_frequency": dict(sorted(document_frequency.items())),
    }
    (field_profile_dir / LEXICON_FILENAME).write_text(
        json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    return cli_common.axis_main(
        __doc__, argv, tool="deai_register", calibrate=calibrate,
        summary=lambda result, field_dir: (
            f"lexicon written: {field_dir / LEXICON_FILENAME} "
            f"({result['n_passages']} passages, {result['n_terms']} terms)"),
        report=lambda text, field_dir, path: feedback.build_report(
            path=path, findings=register_findings(text, field_dir, path),
            axes=[register_axis_status(field_dir)]),
        render=feedback.render_text)


if __name__ == "__main__":
    raise SystemExit(main())
