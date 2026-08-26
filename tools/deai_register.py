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

The rule fires on the CONJUNCTION of two facts: the manuscript leans on the
term (repeated use, not a single mention) and the field's corpus does not
carry it. Either alone is uninformative -- every paper has rare words, and
every corpus has gaps.

Three constructions defeat a naive frequency test, and each is handled rather
than thresholded away:

* **Compounds.** Hyphenation is an open construction, so almost every compound
  is corpus-rare -- `aperture-mass`, the core observable of this field, appears
  in 8 passages of 15,599. A compound is judged by its RAREST part instead: it
  is native when every part it is built from is native.
* **Subscripts.** `\\newcommand{\\Kraw}{S_\\mathrm{sad}}` renders a subscript,
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

import argparse
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

# A term must carry weight in the manuscript before its rarity means anything.
# Five uses is the point at which a term is load-bearing vocabulary rather than
# an incidental word; below it the corpus comparison is dominated by the
# corpus's own sampling gaps.
MIN_MANUSCRIPT_USES = 5
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


def register_axis_status(field_profile_dir: Path | None) -> dict[str, Any]:
    lexicon = load_lexicon(field_profile_dir)
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
    original document and section attribution keeps working.
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
    return "\n".join("" if n in drop else line
                     for n, line in enumerate(lines, start=1))


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
    if len(parts) > 1:
        rarest = min(parts, key=lambda part: int(table.get(part, 0)))
        return int(table.get(rarest, 0)), rarest
    return int(table.get(term, 0)), term


def register_findings(text: str, field_profile_dir: Path | None,
                      path: str | Path | None = None) -> list[dict[str, Any]]:
    lexicon = load_lexicon(field_profile_dir)
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

    findings: list[dict[str, Any]] = []
    for term, usage in sorted(manuscript_terms(text).items()):
        if usage["count"] < MIN_MANUSCRIPT_USES:
            continue
        df, basis = corpus_document_frequency(term, table)
        rate = df / n_passages
        if rate >= RARE_DF_RATE:
            continue
        section = next((label for start, end, label in section_ranges
                        if start <= usage["line"] <= end), "(unknown)")
        via = "" if basis == term else f" (judged on its rarest part {basis!r})"
        findings.append(feedback.make_finding(
            kind="advisory", layer="L0",
            rule=f"register-foreign:{term}", scope="document",
            calibration_unit="document",
            line=usage["line"], section=section, path=path,
            detector="deai_register",
            measurement_status="measured" if resolved else "degraded",
            strength="strong" if df == 0 else "ordinary",
            observed={"term": usage["surface"], "manuscript_uses": usage["count"],
                      "corpus_document_frequency": df,
                      "frequency_basis": basis,
                      "corpus_df_rate": round(rate, 8)},
            reference={"field_profile": str(field_profile_dir)
                       if field_profile_dir else None,
                       "n_passages": n_passages,
                       "rare_df_rate": RARE_DF_RATE,
                       "min_manuscript_uses": MIN_MANUSCRIPT_USES,
                       "resolves_rare_rate": resolved,
                       "provenance": LEXICON_FILENAME},
            normalized_distance=RARE_DF_RATE - rate,
            confidence={"value": min(1.0, usage["count"] / 10.0),
                        "basis": (f"{usage['count']} manuscript uses against "
                                  f"{df}/{n_passages} corpus passages")},
            message=(
                f"{usage['surface']!r} is used {usage['count']} times here but "
                f"appears in {df} of {n_passages} field-corpus passages "
                f"({rate:.1e}){via}. The term is outside the register the "
                "audience reads in."),
            action=(
                "Three dispositions, in order of preference: name the quantity "
                "this field already has a word for; keep the borrowed term but "
                "define it at first use and say what it measures in field "
                "terms; or, if the paper is introducing the concept, confirm "
                "its first occurrence carries the definition a reader needs. "
                "Do not swap a term whose replacement would change the claim."),
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
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__)
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--calibrate", action="store_true")
    args = parser.parse_args(argv)
    field_dir = args.profile_root / args.field if args.field else None
    if args.calibrate:
        if field_dir is None:
            print("[deai_register] --calibrate needs --field", file=sys.stderr)
            return 2
        result = calibrate(field_dir)
        print(f"[deai_register] lexicon written: "
              f"{field_dir / LEXICON_FILENAME} "
              f"({result['n_passages']} passages, {result['n_terms']} terms)")
        return 0
    if not args.file or not args.file.exists():
        print(f"[deai_register] file not found: {args.file}", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    report = feedback.build_report(
        path=args.file,
        findings=register_findings(text, field_dir, args.file),
        axes=[register_axis_status(field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
