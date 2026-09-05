"""Deterministic redundancy map of a manuscript: what a condense pass can remove, and how much.

The `condense` skill used to ask the model to build its own redundancy map, and
a model that finds three things stops at three. This tool builds the map by
machine so the model only rules on it. Every finding carries
`observed.removable_words`, the `condense_budget` block totals them, and
`length_gate --require-shrink` turns the total into a gate the pass has to
meet.

Six scans, all deterministic, all on the document alone (no corpus):

  condense-restatement  a sentence (>= 8 content words) whose content words are
                        >= 80% already used in earlier sentences, with one
                        earlier sentence covering >= 60% on its own: that
                        sentence is the canonical home and is reported
  condense-zero-gain    roadmap, assurance and meta-summary prose: the
                        sentence adds no claim, evidence, or qualification
  condense-dead:<kind>  a label nothing references; a figure or table whose
                        labels nothing references; a macro defined and unused;
                        an acronym defined "(ABC)" and never used again
  condense-verbose      a construction with a fixed shorter equivalent, and
                        stacked hedges (`may possibly`)
  condense-regloss      the same symbol glossed twice ("where $x$ is ...")
  condense-duplicate    two paragraphs in different sections sharing >= 60% of
                        their content words (Jaccard)

The abstract and the conclusion restate the paper by convention (the genre
carve-out of the condense skill). Their restatements are still reported, with
`observed.genre_carve_out` true, and are left out of `default_target`.

Exit status: 0 measured, 2 invalid input. The map does not judge; the skill
does, entry by entry.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

MAP_DIR = Path(__file__).resolve().parent
if str(MAP_DIR) not in sys.path:
    sys.path.insert(0, str(MAP_DIR))
import deai_collocation as collocation  # noqa: E402 because sys.path gains MAP_DIR two lines up
import deai_feedback as feedback  # noqa: E402 because sys.path gains MAP_DIR two lines up
import deai_reference as reference  # noqa: E402 because sys.path gains MAP_DIR two lines up
import deai_register as register  # noqa: E402 because sys.path gains MAP_DIR two lines up
import extract_style as es  # noqa: E402 because sys.path gains MAP_DIR two lines up

MIN_CONTENT_WORDS = 8
UNION_COVERAGE = 0.80
SINGLE_COVERAGE = 0.60
DUPLICATE_JACCARD = 0.60
DUPLICATE_MIN_WORDS = 30
CARVE_OUT_BUCKETS = frozenset({"abstract", "conclusion"})

RE_ZERO_GAIN_SENTENCE = re.compile(
    r"^(?:in this (?:section|paper|work|letter|subsection)\b|we now turn\b|"
    r"the (?:remainder|rest) of (?:this|the) (?:paper|section|letter)\b|"
    r"in what follows\b|this (?:section|paper) (?:describes|presents|is organi[sz]ed|"
    r"outlines|discusses|introduces)\b|the paper is organi[sz]ed\b|in summary\b|"
    r"to summari[sz]e\b|in other words\b|"
    r"as (?:discussed|mentioned|noted|described|shown|explained|stated) "
    r"(?:above|earlier|previously|before|in section)\b)", re.I)
RE_ZERO_GAIN_PHRASE = re.compile(
    r"\b(?:it is worth noting that|it should be noted that|it is important to "
    r"note that|note that|recall that|we (?:emphasi[sz]e|stress) that|it is "
    r"(?:clear|obvious|evident) that|needless to say|of course|obviously|clearly)\b",
    re.I)
VERBOSE = {
    "in order to": "to", "due to the fact that": "because", "owing to the fact that":
    "because", "a large number of": "many", "a small number of": "few",
    "the majority of": "most", "prior to": "before", "subsequent to": "after",
    "make use of": "use", "has the ability to": "can", "is able to": "can",
    "in the absence of": "without", "in the presence of": "with",
    "it is possible that": "may", "in the case of": "for", "in the event that": "if",
    "with respect to": "for", "by means of": "by", "for the purpose of": "to",
    "at the present time": "now", "in close proximity to": "near",
    "a significant fraction of": "much of", "on the order of": "about",
}
RE_VERBOSE = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in VERBOSE) + r")\b", re.I)
RE_HEDGE_STACK = re.compile(r"\b(?:may|might|could)\s+(?:possibly|potentially|perhaps)\b", re.I)
RE_TEX_LABEL = re.compile(r"\\label\{([^}]*)\}")
RE_TEX_REF = re.compile(
    r"\\(?:ref|eqref|cref|Cref|autoref|pageref|labelcref|nameref)\*?\{([^}]*)\}"
    r"|\\hyperref\[([^\]]*)\]")
RE_TEX_FLOAT = re.compile(r"\\begin\{(figure|table)\*?\}(.*?)\\end\{\1\*?\}", re.DOTALL)
RE_TEX_CAPTION = re.compile(r"\\caption(?:\[[^\]]*\])?\{((?:[^{}]|\{[^{}]*\})*)\}")
RE_TEX_MACRO_DEF = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand|def)\s*\{?\\([A-Za-z]+)\}?")
RE_ACRONYM = re.compile(r"\(([A-Z][A-Za-z0-9]{1,9})\)")
RE_REGLOSS = re.compile(
    r"\bwhere\s+\$([^$]+)\$\s+(?:is|denotes|represents|stands for)\b[^.;]*", re.I)


def content_words(sentence: str) -> set[str]:
    return {register.normalize(w) for w in register.RE_WORD.findall(sentence)
            if len(w) >= 3 and register.normalize(w) not in collocation.STOPWORDS}


# What a bag of content words cannot see and a restatement must not change: a
# negation, a number (digits or the number words the stopword list drops), a
# comparison. `is significant` and `is not significant` share every content
# word; before this the second was a restatement of the first.
RE_INVARIANT = re.compile(
    r"\b(?:not|no|never|without|neither|nor|cannot|only|fewer|less|more|larger|"
    r"smaller|higher|lower|greater|above|below|increases?d?|decreases?d?|"
    r"one|two|three|four|five|six|seven|eight|nine|ten)\b|\d+(?:[.,]\d+)*", re.I)
# A roadmap sentence is removable WHOLE when it says at most this many content
# words the document has not said before it; past that it carries a claim of
# its own and only the cue is budgeted.
ZERO_GAIN_OWN_WORDS = 3


def invariants(sentence: str) -> frozenset[str]:
    return frozenset(m.group(0).lower() for m in RE_INVARIANT.finditer(sentence))


def _finding(*, rule: str, path: str | Path | None, line: int, end_line: int | None,
             section: str | None, scope: str, removable: int, observed: dict[str, Any],
             message: str, action: str, confidence: float = 1.0,
             unit: str | None = None, whole: bool = False) -> dict[str, Any]:
    # `unit` names the sentence (`line:index`) or paragraph (`line:*`) the
    # words come from and `whole_unit` whether the finding removes all of it;
    # the budget sums a unit once, whatever number of scans name it.
    observed = {**observed, "removable_words": int(removable), "unit": unit,
                "whole_unit": bool(whole)}
    return feedback.make_finding(
        kind="advisory", layer="QD", rule=rule, scope=scope, path=path, line=line,
        end_line=end_line, section=section, detector="condense_map",
        strength="ordinary", observed=observed, message=message, action=action,
        reference={"provenance": "SCIPAPER_STANDARD section 5.3",
                   "policy": "one canonical home per fact"},
        normalized_distance=None,
        confidence={"value": confidence, "basis": "deterministic scan of the document"},
        measurement_status="measured", evidence=[rule, removable])


def _sentence_records(text: str) -> list[dict[str, Any]]:
    records = []
    for start, end, bucket, block in reference.units(text):
        for index, sentence in enumerate(es.sentences(es.latex_to_plain(block))):
            clean = " ".join(sentence.split())
            if clean:
                records.append({"line": start, "end": end, "bucket": bucket,
                                "unit": f"{start}:{index}",
                                "text": clean, "words": content_words(clean),
                                "invariants": invariants(clean),
                                "n_words": len(clean.split())})
    return records


def restatement_findings(records: list[dict[str, Any]], path=None) -> list[dict[str, Any]]:
    findings = []
    seen: set[str] = set()
    for index, record in enumerate(records):
        words = record["words"]
        if len(words) >= MIN_CONTENT_WORDS:
            union = len(words & seen) / len(words)
            best_index, best = -1, 0.0
            for earlier_index in range(index):
                earlier = records[earlier_index]["words"]
                if not earlier:
                    continue
                coverage = len(words & earlier) / len(words)
                if coverage > best:
                    best_index, best = earlier_index, coverage
            home = records[best_index] if best_index >= 0 else None
            # A sentence that adds a negation, a number or a comparison its
            # home does not carry restates nothing; it is a different claim.
            if (union >= UNION_COVERAGE and best >= SINGLE_COVERAGE
                    and record["invariants"] <= home["invariants"]):
                carve = record["bucket"] in CARVE_OUT_BUCKETS
                findings.append(_finding(
                    rule="condense-restatement", path=path, line=record["line"],
                    end_line=record["end"], section=record["bucket"], scope="sentence",
                    removable=record["n_words"], confidence=round(best, 2),
                    unit=record["unit"], whole=True,
                    observed={"excerpt": record["text"][:160],
                              "canonical_line": home["line"],
                              "canonical_excerpt": home["text"][:160],
                              "single_coverage": round(best, 3),
                              "union_coverage": round(union, 3),
                              "genre_carve_out": carve},
                    message=(f"{record['bucket']} sentence restates line {home['line']} "
                             f"({best:.0%} of its content words; {union:.0%} already "
                             "used earlier)" + (" -- abstract/conclusion carve-out"
                                                if carve else "") + "."),
                    action=("Delete the restatement, or replace it with a "
                            "cross-reference if a distant reader needs the pointer. "
                            "Keep the canonical home. Never delete a fact's only "
                            "support.")))
        seen |= words
    return findings


def zero_gain_findings(records: list[dict[str, Any]], path=None) -> list[dict[str, Any]]:
    """A roadmap cue budgets the cue; the whole sentence only when nothing of
    its own is left once the cue is gone (`In this section we describe the
    filter`), never a claim that happens to open with one (`In this paper we
    measure a mass of five units`). The abstract/conclusion carve-out applies
    to a whole sentence exactly as it does to a restatement."""
    findings = []
    seen: set[str] = set()
    for record in records:
        text = record["text"]
        opener = RE_ZERO_GAIN_SENTENCE.match(text)
        phrase = None if opener else RE_ZERO_GAIN_PHRASE.search(text)
        if opener or phrase:
            hit = (opener or phrase).group(0)
            own = content_words(text[opener.end():]) - seen if opener else set()
            whole = bool(opener) and len(own) <= ZERO_GAIN_OWN_WORDS
            carve = whole and record["bucket"] in CARVE_OUT_BUCKETS
            findings.append(_finding(
                rule="condense-zero-gain", path=path, line=record["line"],
                end_line=record["end"], section=record["bucket"], scope="sentence",
                removable=record["n_words"] if whole else len(hit.split()),
                unit=record["unit"], whole=whole,
                observed={"excerpt": text[:160], "cue": hit.lower(),
                          "whole_sentence": whole, "genre_carve_out": carve},
                message=(f"{'Sentence' if whole else 'Phrase'} carries no claim, "
                         f"evidence or qualification: {hit.lower()!r}."
                         + (" -- abstract/conclusion carve-out" if carve else "")),
                action=("Delete it. If one clause is load-bearing, fold that clause "
                        "into the neighbouring sentence; the structure already "
                        "carries the roadmap.")))
        seen |= record["words"]
    return findings


def dead_artifact_findings(text: str, path=None) -> list[dict[str, Any]]:
    findings = []
    referenced = {name.strip() for match in RE_TEX_REF.finditer(text)
                  for name in (match.group(1) or match.group(2) or "").split(",")}
    float_spans = []
    for match in RE_TEX_FLOAT.finditer(text):
        labels = RE_TEX_LABEL.findall(match.group(2))
        if labels and not any(label.strip() in referenced for label in labels):
            caption = RE_TEX_CAPTION.search(match.group(2))
            words = len(es.prose_words(caption.group(1))) if caption else 0
            line = text[: match.start()].count("\n") + 1
            findings.append(_finding(
                rule=f"condense-dead:{match.group(1)}", path=path, line=line,
                end_line=text[: match.end()].count("\n") + 1, section=None,
                scope="section", removable=words,
                observed={"excerpt": labels[0], "labels": labels},
                message=(f"{match.group(1)} labelled {labels[0]!r} is never "
                         "referenced from the text."),
                action=("Cite it where its evidence is used, or delete the float "
                        "and its caption; a figure nobody points at is not read.")))
        float_spans.append((match.start(), match.end()))
    for match in RE_TEX_LABEL.finditer(text):
        name = match.group(1).strip()
        if name in referenced or any(a <= match.start() < b for a, b in float_spans):
            continue
        findings.append(_finding(
            rule="condense-dead:label", path=path,
            line=text[: match.start()].count("\n") + 1, end_line=None, section=None,
            scope="sentence", removable=0, observed={"excerpt": name},
            message=f"\\label{{{name}}} is never referenced.",
            action="Delete the label, or reference the thing it names."))
    for match in RE_TEX_MACRO_DEF.finditer(text):
        name = match.group(1)
        uses = len(re.findall(r"\\" + re.escape(name) + r"(?![A-Za-z])", text)) - 1
        if uses <= 0:
            findings.append(_finding(
                rule="condense-dead:macro", path=path,
                line=text[: match.start()].count("\n") + 1, end_line=None,
                section=None, scope="sentence", removable=0,
                observed={"excerpt": "\\" + name},
                message=f"Macro \\{name} is defined and never used.",
                action="Delete the definition."))
    plain = es.latex_to_plain(text)
    for match in RE_ACRONYM.finditer(plain):
        acronym = match.group(1)
        later = len(re.findall(r"\b" + re.escape(acronym) + r"s?\b", plain)) - 1
        if later <= 0:
            findings.append(_finding(
                rule="condense-dead:acronym", path=path, line=1, end_line=None,
                section=None, scope="sentence", removable=1,
                observed={"excerpt": acronym},
                message=f"Acronym ({acronym}) is defined and never used again.",
                action="Delete the parenthetical; keep the spelled-out name."))
    return findings


def verbose_findings(records: list[dict[str, Any]], path=None) -> list[dict[str, Any]]:
    findings = []
    for record in records:
        for match in RE_VERBOSE.finditer(record["text"]):
            phrase = match.group(0).lower()
            shorter = VERBOSE[phrase]
            findings.append(_finding(
                rule="condense-verbose", path=path, line=record["line"],
                end_line=record["end"], section=record["bucket"], scope="sentence",
                removable=len(phrase.split()) - len(shorter.split()), unit=record["unit"],
                observed={"excerpt": record["text"][:160], "phrase": phrase,
                          "replacement": shorter},
                message=f"{phrase!r} has the shorter equivalent {shorter!r}.",
                action=f"Write {shorter!r}."))
        for match in RE_HEDGE_STACK.finditer(record["text"]):
            findings.append(_finding(
                rule="condense-verbose", path=path, line=record["line"],
                end_line=record["end"], section=record["bucket"], scope="sentence",
                removable=1, unit=record["unit"],
                observed={"excerpt": record["text"][:160],
                          "phrase": match.group(0).lower(), "replacement": "one hedge"},
                message=f"Stacked hedge {match.group(0).lower()!r}: one modal is a hedge already.",
                action="Keep the modal, drop the adverb."))
    return findings


def regloss_findings(text: str, path=None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    first: dict[str, int] = {}
    for match in RE_REGLOSS.finditer(text):
        symbol = re.sub(r"\s+", "", match.group(1))
        line = text[: match.start()].count("\n") + 1
        if symbol not in first:
            first[symbol] = line
            continue
        findings.append(_finding(
            rule="condense-regloss", path=path, line=line, end_line=None, section=None,
            scope="sentence", removable=len(match.group(0).split()),
            observed={"excerpt": " ".join(match.group(0).split())[:160],
                      "symbol": symbol, "first_gloss_line": first[symbol]},
            message=f"${symbol}$ is glossed again; its first gloss is at line {first[symbol]}.",
            action="Delete the repeated gloss; a symbol is defined once."))
    return findings


def duplicate_findings(text: str, path=None) -> list[dict[str, Any]]:
    paragraphs = []
    for start, end, bucket, block in reference.units(text):
        plain = es.latex_to_plain(block)
        if len(plain.split()) >= DUPLICATE_MIN_WORDS:
            paragraphs.append((start, end, bucket, plain, content_words(plain)))
    findings = []
    for j, (start, end, bucket, plain, words) in enumerate(paragraphs):
        for i in range(j):
            e_start, _e_end, e_bucket, e_plain, e_words = paragraphs[i]
            if e_bucket == bucket or not words or not e_words:
                continue
            jaccard = len(words & e_words) / len(words | e_words)
            if jaccard < DUPLICATE_JACCARD:
                continue
            carve = bucket in CARVE_OUT_BUCKETS or e_bucket in CARVE_OUT_BUCKETS
            findings.append(_finding(
                rule="condense-duplicate", path=path, line=start, end_line=end,
                section=bucket, scope="paragraph", removable=len(plain.split()),
                confidence=round(jaccard, 2), unit=f"{start}:*", whole=True,
                observed={"excerpt": plain[:160], "canonical_line": e_start,
                          "canonical_section": e_bucket, "jaccard": round(jaccard, 3),
                          "genre_carve_out": carve},
                message=(f"{bucket} paragraph duplicates the {e_bucket} paragraph at "
                         f"line {e_start} (Jaccard {jaccard:.2f})"
                         + (" -- abstract/conclusion carve-out" if carve else "") + "."),
                action=("Keep one home for the content; replace the copy with a "
                        "cross-reference or delete it.")))
            break
    return findings


def condense_map(text: str, path: str | Path | None = None) -> list[dict[str, Any]]:
    records = _sentence_records(text)
    return (restatement_findings(records, path) + zero_gain_findings(records, path)
            + dead_artifact_findings(text, path) + verbose_findings(records, path)
            + regloss_findings(text, path) + duplicate_findings(text, path))


def removable_words(findings: list[dict[str, Any]]) -> int:
    """Words the findings free, each sentence or paragraph counted ONCE.

    Three scans naming one sentence free one sentence, not three: a whole-unit
    finding takes the unit's words, phrase findings inside a unit add up only
    where nothing removes the unit whole, and a sentence inside a paragraph a
    duplicate scan removes is not counted again. Summing every finding gave a
    46-word document a 75-word target.
    """
    whole: dict[str, int] = {}
    phrases: dict[str, int] = {}
    loose = 0
    for finding in findings:
        observed = finding["observed"]
        unit, words = observed.get("unit"), int(observed["removable_words"])
        if unit is None:
            loose += words
        elif observed.get("whole_unit"):
            whole[unit] = max(whole.get(unit, 0), words)
        else:
            phrases[unit] = phrases.get(unit, 0) + words
    removed_paragraphs = {unit.split(":")[0] for unit in whole if unit.endswith(":*")}
    total = loose
    for unit in set(whole) | set(phrases):
        if not unit.endswith(":*") and unit.split(":")[0] in removed_paragraphs:
            continue
        total += max(whole.get(unit, 0), phrases.get(unit, 0))
    return total


def condense_budget(text: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """`removable_by_rule` is candidate mass per scan (overlaps included, so a
    reader sees what each scan found); `removable_total` and the default
    target count each unit once."""
    prose_words = len(es.prose_words(text))
    by_rule: dict[str, int] = {}
    for finding in findings:
        family = finding["rule"].split(":")[0]
        by_rule[family] = by_rule.get(family, 0) + int(finding["observed"]["removable_words"])
    total = removable_words(findings)
    target = removable_words([
        finding for finding in findings
        if finding["rule"].split(":")[0] in ("condense-restatement", "condense-zero-gain")
        and not finding["observed"].get("genre_carve_out")])
    return {"prose_words": prose_words, "removable_by_rule": dict(sorted(by_rule.items())),
            "removable_total": total,
            "removable_fraction": round(total / prose_words, 4) if prose_words else None,
            "default_target_words": target,
            "default_target_fraction": (round(target / prose_words, 4)
                                        if prose_words else None),
            "n_entries": len(findings)}


def render(report: dict[str, Any]) -> str:
    budget = report["condense_budget"]
    lines = [f"condense_map: {report['target']}",
             f"prose words {budget['prose_words']}; removable {budget['removable_total']} "
             f"({budget['removable_fraction'] or 0:.1%}); default shrink target "
             f"{budget['default_target_words']} words "
             f"({budget['default_target_fraction'] or 0:.1%}, restatement + zero-gain "
             "outside the abstract/conclusion carve-out)"]
    for family, words in budget["removable_by_rule"].items():
        lines.append(f"  {family:24s} {words:>6d} words")
    return "\n".join(lines) + "\n" + feedback.render_text(report) + "\n"


def main(argv: list[str] | None = None) -> int:
    import ai_ism_lint
    import cli_common
    cli_common.utf8_stdout()
    parser = cli_common.base_parser(__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.file.exists():
        print(f"[condense_map] file not found: {args.file}", file=sys.stderr)
        return 2
    try:
        text = ai_ism_lint.document_source(args.file)
        findings = condense_map(text, args.file)
    except (OSError, ValueError, UnicodeDecodeError) as error:
        print(f"[condense_map] execution failed: {error}", file=sys.stderr)
        return 2
    axes = [feedback.axis_status("QD.condense_map", "measured", detector="condense_map")]
    report = feedback.build_report(path=args.file, findings=findings, axes=axes)
    report["condense_budget"] = condense_budget(text, findings)
    rendered = feedback.dump_report(report) if args.format == "json" else render(report)
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
