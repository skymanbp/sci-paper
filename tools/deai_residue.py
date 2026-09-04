"""Edit-residue feedback for scientific prose (L4): traces an editing loop leaves behind.

A manuscript revised in many passes accumulates marks that were true of the
process and are not true of the science. Three static rules and one diff rule
find them; none is an authorship claim and none touches the L0 exit status.

- `residue-self-history` -- the text narrates its own drafting: `initially`,
  `we tried`, `no longer`, `superseded` in a sentence about *us* with no
  citation to anchor the history to the literature. Two tiers, because the
  words differ in precision: on 142,228 refereed sentences the high-precision
  family fires only where a draft really recounts itself, while `now`,
  `currently`, `previously` are ordinary scientific words that fire about
  1.7 times per 5,000-word paper on prose nobody would change. The first tier
  is strong; the second is an ordinary advisory.
- `residue-negative-label` -- a heading or caption defined by what it is NOT
  (`without the saddle correction`, `non-compensated`), where the negated
  thing appears nowhere else in the paper. A label like that was written
  against a variant the loop later deleted; the reader meets a comparison
  with one side missing.
- `residue-edit-meta` -- literal editing marks: `(removed)`, `TODO`,
  `\\textcolor{red}`, `in the revised version`. Comments are blanked before the
  scan, so a note the author keeps for themselves is not a finding.
- `residue-negative-label-added` (diff only) -- a negative label that is NEW
  in this edit and whose negated object was PRESENT before and is absent
  now: the patch that removed a thing and left its absence in a caption.

The static rules run inside `ai_ism_lint` (`--residue`, axis `L4.residue`).
The diff rule needs a baseline and runs from this file:
`deai_residue.py <after> --before <snapshot>` (or `--git-ref REF`), with the
exit contract of `length_gate`: 0 clean, 1 a strong residue finding is
present, 2 invalid input. Both are mechanical gates of SCIPAPER_STANDARD
section 5.3 (condense, do not accumulate): a patch is not a fix.

The rule-1 word families defined here are the SINGLE SOURCE. `skills/paper/
SKILL.md` lists them verbatim between `residue-family` markers and
`validate_plugin` compares the two, so the writer and the detector cannot
drift apart on which words count.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Iterable

RESIDUE_DIR = Path(__file__).resolve().parent
if str(RESIDUE_DIR) not in sys.path:
    sys.path.insert(0, str(RESIDUE_DIR))
import deai_feedback as feedback  # noqa: E402 because the tools directory joins sys.path just above
import deai_reference as reference  # noqa: E402 because the tools directory joins sys.path just above
import deai_register as register  # noqa: E402 because the tools directory joins sys.path just above
import extract_sections as sections  # noqa: E402 because the tools directory joins sys.path just above
import extract_style as es  # noqa: E402 because the tools directory joins sys.path just above
import length_gate  # noqa: E402 because the tools directory joins sys.path just above

# Rule 1. Single source of the word families (see the module docstring).
# Strength was set on 203 held-out refereed papers, not by intuition. `used to`
# is not a family word at all: 174 of its 203 first-person hits there were the
# instrumental sense ("the radii used to trace ..."). `initially`, `originally`
# and `at first` are ordinary: they open procedure steps ("we initially select
# galaxies with ...", "at first order"), which is pipeline order, not drafting
# history. What is left fires in 12% of those papers (EVALUATION §23.4).
HISTORY_STRONG = (
    "previous draft", "earlier draft", "previous version", "earlier version",
    "supersedes", "superseded", "no longer", "we tried", "we switched",
    "we abandoned", "we replaced", "we moved away from",
)
HISTORY_ORDINARY = (
    "initially", "originally", "at first", "now", "currently", "earlier",
    "previously", "corrected", "revised", "updated",
)
FAMILY_MARKERS = ("<!-- residue-family:start -->", "<!-- residue-family:end -->")
RE_HISTORY_STRONG = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in HISTORY_STRONG) + r")\b", re.I)
RE_HISTORY_ORDINARY = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in HISTORY_ORDINARY) + r")\b", re.I)
RE_SELF = re.compile(
    r"\b(?:we|our|us|this (?:paper|letter|work|study|analysis|manuscript|note))\b",
    re.I)
CITATION_TOKEN = "[CITE]"

# Rule 3. Literal editing marks. The upper-case tokens are matched
# case-sensitively at word boundaries; everything else case-insensitively.
# `XXX` is not one of them: "Planck Collaboration XXX" is a paper title this
# field cites, and a bibliography key can carry it too.
EDIT_META_CASE = ("TODO", "FIXME")
EDIT_META = (
    "(removed)", "(deleted)", "(added)", "(new)", "(updated)", "(moved)",
    "(revised)", "(old)", "(was:", "\\textcolor{red}", "\\hl{", "\\sout{",
    "\\st{", "in this revision", "in the revised version",
    "the revised manuscript", "we have revised", "we have added",
    "we have removed", "as requested by the referee",
    "as suggested by the referee", "in response to the referee",
    "per the referee", "per reviewer", "reviewer's comment",
)
# Two compiled forms, not one alternation: a scoped `(?i:...)` group next to a
# case-sensitive branch is the construction that hid a stray byte here once.
RE_EDIT_META = (
    re.compile(r"\b(?:" + "|".join(re.escape(w) for w in EDIT_META_CASE) + r")\b"),
    re.compile("|".join(re.escape(w) for w in EDIT_META), re.I),
)

# Rule 2 / 5. Labels are headings and captions; the negated object runs from
# the marker to the next punctuation or coordinating word.
RE_LABEL = re.compile(
    r"\\(?:chapter|section|subsection|subsubsection|paragraph|caption)\*?"
    r"(?:\[[^\]]*\])?\{((?:[^{}]|\{[^{}]*\})*)\}")
RE_NEGATION = re.compile(
    r"\b(?:no|non|not|without|excluding|neither|nor|absent|minus|free of|lacking)"
    r"\b[-\s]*((?:[^,;:()\[\]]|\[math\])+?)(?=[,;:()\[\]]|\s+(?:and|or|with|versus|vs)\b|$)",
    re.I)
MIN_WORDS_NEGATIVE_LABEL = 400
LABEL_HEAD_WORDS = 3
STOPWORDS = frozenset("""the a an of in on at to for from by with and or but
as is are was were be been that this these those it its any all each some
same other such only""".split())


def _content_stems(text: str) -> list[str]:
    stems = []
    for word in register.RE_WORD.findall(text):
        low = register.normalize(word)
        if len(low) >= 3 and low not in STOPWORDS:
            stems.append(stem(low))
    return stems


def stem(word: str) -> str:
    """One suffix off, when a root of three or more letters remains."""
    for suffix in register.STEM_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _sentences(text: str) -> Iterable[tuple[int, int, str, str]]:
    # Prose units only: the reference layer already drops the preamble, and a
    # `skip` bucket (references, acknowledgments) is not prose an edit left.
    for start, end, bucket, block in reference.units(text):
        if bucket == "skip":
            continue
        for sentence in es.sentences(es.latex_to_plain(block)):
            if sentence.strip():
                yield start, end, bucket, " ".join(sentence.split())


def _finding(*, rule: str, path: str | Path | None, line: int, end_line: int | None,
             section: str | None, scope: str, strength: str, observed: dict[str, Any],
             message: str, action: str, confidence: float = 1.0) -> dict[str, Any]:
    return feedback.make_finding(
        kind="advisory", layer="L4", rule=rule, scope=scope, path=path,
        line=line, end_line=end_line, section=section, detector="deai_residue",
        strength=strength, observed=observed, message=message, action=action,
        reference={"provenance": "SCIPAPER_STANDARD section 5.3",
                   "policy": "condense, do not accumulate; a patch is not a fix"},
        normalized_distance=None,
        confidence={"value": confidence, "basis": "deterministic pattern on the text"},
        measurement_status="measured", evidence=[rule, observed.get("excerpt")])


HISTORY_ACTION = (
    "State the method as it stands. Drafting history belongs in a cover "
    "letter or a footnote comparing to a cited earlier result, never in the "
    "method itself; if the sentence contrasts this work with published work, "
    "cite that work in the same sentence.")


def self_history_findings(text: str, path: str | Path | None = None) -> list[dict[str, Any]]:
    findings = []
    for start, end, bucket, sentence in _sentences(text):
        if CITATION_TOKEN in sentence or not RE_SELF.search(sentence):
            continue
        strong = RE_HISTORY_STRONG.search(sentence)
        hit = strong or RE_HISTORY_ORDINARY.search(sentence)
        if hit is None:
            continue
        word = hit.group(0).lower()
        findings.append(_finding(
            rule=f"residue-self-history:{word}", path=path, line=start,
            end_line=end, section=bucket, scope="sentence",
            strength="strong" if strong else "ordinary",
            confidence=1.0 if strong else 0.6,
            observed={"excerpt": sentence[:160], "word": word,
                      "tier": "strong" if strong else "ordinary"},
            message=(f"The sentence narrates the draft's own history ({word!r}) "
                     "about the authors, with no citation anchoring the contrast."),
            action=HISTORY_ACTION))
    return findings


EDIT_META_ACTION = (
    "Resolve the mark: finish what the note asks for, then remove the note "
    "and any colour or strike-through that marked the edit. Revision-tracking "
    "language belongs in the response letter, not the manuscript.")


def edit_meta_findings(text: str, path: str | Path | None = None) -> list[dict[str, Any]]:
    findings = []
    for number, line in enumerate(text.splitlines(), start=1):
        hits = (m for rx in RE_EDIT_META for m in rx.finditer(line))
        for match in sorted(hits, key=lambda m: m.start()):
            findings.append(_finding(
                rule="residue-edit-meta", path=path, line=number, end_line=None,
                section=None, scope="sentence", strength="strong",
                observed={"excerpt": line.strip()[:160], "mark": match.group(0)},
                message=f"An editing mark {match.group(0)!r} is in the manuscript text.",
                action=EDIT_META_ACTION))
    return findings


def _labels(text: str) -> list[tuple[int, str]]:
    """(line, plain text) of every heading and caption."""
    out = []
    for match in RE_LABEL.finditer(text):
        plain = " ".join(es.latex_to_plain(match.group(1)).split())
        if plain:
            out.append((text[: match.start()].count("\n") + 1, plain))
    return out


def _body_stems(text: str) -> set[str]:
    body = RE_LABEL.sub(" ", text)
    return set(_content_stems(es.latex_to_plain(body)))


def negated_objects(label: str) -> list[tuple[str, list[str]]]:
    """(object text, its first content-word stems) for each negation in a label."""
    out = []
    for match in RE_NEGATION.finditer(label):
        obj = match.group(1).strip(" -")
        stems = _content_stems(obj)[:LABEL_HEAD_WORDS]
        if stems:
            out.append((obj, stems))
    return out


NEGATIVE_LABEL_ACTION = (
    "Name what the figure or section shows in its own terms. If the paper "
    "still contains the thing the label negates, name it where the reader "
    "first meets it; if that variant was edited out, the label is describing "
    "a comparison the paper no longer makes and must be rewritten to what "
    "remains. The negation itself is not the defect; the missing referent is.")


def negative_label_findings(text: str, path: str | Path | None = None,
                            body_text: str | None = None) -> list[dict[str, Any]]:
    """Labels come from `text` (headings are blanked in the body projection);
    the object is looked for in body prose only. Ordinary, not strong: on 203
    refereed papers the static rule fires in 30% of documents, so it names a
    label to check, and the diff rule is the one that gates."""
    if len(es.latex_to_plain(text).split()) < MIN_WORDS_NEGATIVE_LABEL:
        return []
    body = _body_stems(register.body_only(text) if body_text is None else body_text)
    findings = []
    for line, label in _labels(text):
        for obj, stems in negated_objects(label):
            missing = [s for s in stems if s not in body]
            if not missing:
                continue
            findings.append(_finding(
                rule="residue-negative-label", path=path, line=line, end_line=None,
                section=None, scope="section", strength="ordinary",
                observed={"excerpt": label[:160], "negated_object": obj,
                          "absent_from_body": missing},
                message=(f"A heading or caption is defined by a negation "
                         f"({obj!r}) whose object appears nowhere in the body "
                         f"(absent: {', '.join(missing)})."),
                action=NEGATIVE_LABEL_ACTION))
    return findings


def negative_label_added_findings(before: str, after: str,
                                  path: str | Path | None = None) -> list[dict[str, Any]]:
    """Rule 5: negation new in this edit, its object present before and gone now."""
    old_labels = {label for _line, label in _labels(before)}
    old_body = _body_stems(register.body_only(before))
    new_body = _body_stems(register.body_only(after))
    findings = []
    for line, label in _labels(after):
        if label in old_labels:
            continue
        for obj, stems in negated_objects(label):
            removed = [s for s in stems if s in old_body and s not in new_body]
            if not removed:
                continue
            findings.append(_finding(
                rule="residue-negative-label-added", path=path, line=line,
                end_line=None, section=None, scope="section", strength="strong",
                observed={"excerpt": label[:160], "negated_object": obj,
                          "removed_from_body": removed},
                message=(f"This edit added a label negating {obj!r} and removed "
                         f"the thing it negates from the body "
                         f"({', '.join(removed)}): the absence was patched in "
                         "where the content was taken out."),
                action=NEGATIVE_LABEL_ACTION))
    return findings


def residue_findings(text: str, path: str | Path | None = None) -> list[dict[str, Any]]:
    # One projection for the literal and label rules: the preamble
    # (`\newcommand{\TODO}`) and the bibliography are not prose an edit left
    # behind. Same asymmetry class as `deai_register.body_only`, so it is that
    # function, not a copy of it; the sentence rule keeps the raw text because
    # `reference.units` needs the headings to find the sections.
    body = register.body_only(text)
    return (self_history_findings(text, path)
            + negative_label_findings(text, path, body_text=body)
            + edit_meta_findings(body, path))


def residue_axis_status(text: str) -> dict[str, Any]:
    words = len(es.latex_to_plain(text).split())
    reason = None
    if words < MIN_WORDS_NEGATIVE_LABEL:
        reason = (f"negative-label rule not applied below "
                  f"{MIN_WORDS_NEGATIVE_LABEL} prose words ({words} here)")
    return feedback.axis_status("L4.residue", "measured", reason=reason,
                                detector="deai_residue")


# --- validator hook ----------------------------------------------------------

RE_MD_CODE = re.compile(r"```.*?```|`[^`\n]*`", re.DOTALL)
DOC_SCAN = ("README.md", "README.zh-CN.md", "docs/SCIPAPER_STANDARD.md")


def family_listed_in(skill_text: str) -> set[str]:
    start, end = FAMILY_MARKERS
    if start not in skill_text or end not in skill_text:
        return set()
    block = skill_text.split(start, 1)[1].split(end, 1)[0]
    return {item.lower() for item in re.findall(r"`([^`]+)`", block)}


RE_DOC_EDIT_META = re.compile("(?i:" + "|".join(re.escape(w) for w in EDIT_META) + ")")


def validator_check(repo: Path, require) -> str:
    """The `validate_plugin` check: word family in sync, documentation residue-free.

    Only the phrase marks of rule 3 are scanned in documentation. The
    upper-case tokens are exempt because the skills name the marks they hunt
    (`TODO/FIXME ... 为 0`), and the negative-label rule is not applied to
    markdown headings at all: "Condense, Do Not Accumulate" is a policy stated
    as an imperative, not a label defined against content the page lost.
    """
    listed = family_listed_in((repo / "skills" / "paper" / "SKILL.md").read_text("utf-8"))
    expected = set(HISTORY_STRONG) | set(HISTORY_ORDINARY)
    require(listed == expected,
            "skills/paper/SKILL.md residue word family differs from deai_residue: "
            f"missing={sorted(expected - listed)}, extra={sorted(listed - expected)}")
    pages = [repo / name for name in DOC_SCAN]
    pages.extend(sorted((repo / "skills").glob("*/SKILL.md")))
    marks = []
    for page in pages:
        prose = RE_MD_CODE.sub(" ", page.read_text("utf-8"))
        for number, line in enumerate(prose.splitlines(), start=1):
            for match in RE_DOC_EDIT_META.finditer(line):
                marks.append(f"{page.relative_to(repo).as_posix()}:{number} {match.group(0)!r}")
    require(not marks, "editing residue in documentation: " + "; ".join(marks))
    return (f"residue word family in sync ({len(expected)} terms); "
            f"{len(pages)} documents free of editing marks")


# --- CLI ---------------------------------------------------------------------

def _blank_comments(text: str) -> str:
    return sections.RE_TEX_COMMENT.sub(lambda m: " " * len(m.group(0)), text)


def main(argv: list[str] | None = None) -> int:
    import cli_common
    cli_common.utf8_stdout()
    parser = cli_common.base_parser(__doc__)
    parser.add_argument("after", type=Path, help="the document to check")
    parser.add_argument("--before", type=Path, help="pre-edit snapshot (enables the diff rule)")
    parser.add_argument("--git-ref", default=None, help="read the pre-edit version from git")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if not args.after.exists():
        print(f"[deai_residue] file not found: {args.after}", file=sys.stderr)
        return 2
    if args.before is not None and args.git_ref is not None:
        print("[deai_residue] provide at most one of --before or --git-ref", file=sys.stderr)
        return 2
    try:
        import ai_ism_lint
        after = ai_ism_lint.document_source(args.after)
        findings = residue_findings(after, args.after)
        if args.before is not None:
            before = ai_ism_lint.document_source(args.before)
        elif args.git_ref is not None:
            before = _blank_comments(length_gate.read_git_version(args.after, args.git_ref))
        else:
            before = None
        if before is not None:
            findings.extend(negative_label_added_findings(before, after, args.after))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        print(f"[deai_residue] execution failed: {error}", file=sys.stderr)
        return 2
    axes = [residue_axis_status(after)]
    report = feedback.build_report(path=args.after, findings=findings, axes=axes)
    strong = sum(1 for f in findings if f["strength"] == "strong")
    report["residue_gate"] = {"strong_findings": strong, "diff_rule_ran": before is not None,
                              "gate_exit": 1 if strong else 0}
    rendered = (feedback.dump_report(report) if args.format == "json"
                else feedback.render_text(report) + "\n")
    if args.output is not None:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return report["residue_gate"]["gate_exit"]


if __name__ == "__main__":
    raise SystemExit(main())
