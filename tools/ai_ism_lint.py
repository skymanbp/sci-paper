"""Unified lexical and structural feedback CLI for sci-paper.

Exit status is intentionally narrow: 0 means no L0 rewrite targets, 1 means at
least one L0 target, and 2 means invalid input or execution failure. L1-L3
findings are advisory and never change the L0 exit status.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import deai_docstructure  # noqa: E402  sibling tool import after path setup
import deai_feedback as feedback  # noqa: E402  shared finding contract
import deai_metrics  # noqa: E402  distribution and canonical ranges
import deai_discourse  # noqa: E402  cohesion and hedging detector
import deai_register  # noqa: E402  domain-register detector
import deai_salience  # noqa: E402  salience-hierarchy detector
import deai_structure  # noqa: E402  sentence-construction detector

REPO_ROOT = TOOLS_DIR.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
EM_DASH_PATTERN = re.compile(r"—|---|\\textemdash")
TIER_A_PATTERN = re.compile(
    r"(?i)\b(?:delves?|delving|delved|leverages|leveraging|leveraged|"
    r"paves?|paving|sheds?|shedding|showcases?|showcasing|utiliz(?:ing|es)|"
    r"seamless(?:ly)?|holistic(?:ally)?|comprehensively|crucially|"
    r"underscor(?:e|es|ed|ing)|tapestry|testament|pivotal|realms?)\b"
)
TIER_A_OPENER_PATTERN = re.compile(
    r"(?i)^\s*(?:recent advances in|despite significant progress|"
    r"with the advent of|in recent years|it is worth noting)"
)
TIER_A_PARAGRAPH_CONNECTOR_PATTERN = re.compile(
    r"(?i)^\s*(Importantly|Interestingly|Notably|Crucially),"
)
TIER_B_PATTERN = re.compile(
    r"(?i)\b(?:furthermore|moreover|additionally|robust(?:ly)?|comprehensive|"
    r"utilize|utilized|leverage|importantly|interestingly|notably|"
    r"intricate|foster(?:s|ing|ed)?)\b"
)
STUBBORN_REPLACE_PATTERN = re.compile(
    r"(?i)\b(?:in order to|aim to|facilitate|serves as)\b")
THREE_PARALLEL_PATTERN = re.compile(r"(?i)not only.+but also.+(?:and|furthermore|moreover)")
# Participial tail that fakes analytic depth ("..., highlighting X").
# Curated verb set adopted 2026-07-16 from the academic-humanizer catalog
# (MIT); kept narrow to avoid flagging legitimate participial clauses.
ING_TAIL_PATTERN = re.compile(
    r"(?i),\s+(?:highlighting|underscoring|showcasing|emphasizing|"
    r"emphasising|illustrating|demonstrating|signaling|signalling|"
    r"revealing|reflecting)\b"
)
# Appositive-elaboration colon in prose ("X: the rule that ...").
# User style rule 2026-07-16; caption tags ("Left: ...") and list
# specifications are legitimate, so this stays an advisory.
COLON_ELABORATION_PATTERN = re.compile(r"(?:[A-Za-z0-9]|\})(?:: )[a-z$\\]")
# The two 2026-07-16 rules above/below match rendered prose only: unescaped
# LaTeX comments (full-line or trailing) are stripped before matching.
# Comments conventionally carry "Label: description" tags and note-style
# participial phrases that are not rendered. Older rules keep their
# long-standing raw-line behavior.
TRAILING_COMMENT_PATTERN = re.compile(r"(?<!\\)%.*$")
TIER_B_CAP = 1


def list_fields(profile_root: Path) -> list[str]:
    if not profile_root.exists():
        return []
    return sorted(path.name for path in profile_root.iterdir()
                  if path.is_dir() and not path.name.startswith("."))


def resolve_field(arg_field: str | None, profile_root: Path) -> str | None:
    fields = list_fields(profile_root)
    if arg_field:
        if arg_field not in fields:
            print(f"[ai_ism_lint] field {arg_field!r} is unavailable under {profile_root}",
                  file=sys.stderr)
            return None
        return arg_field
    return fields[0] if len(fields) == 1 else None


def load_corpus_blacklist(field_profile_dir: Path | None) -> set[str]:
    if field_profile_dir is None:
        return set()
    path = field_profile_dir / "lexicon.json"
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return set(data.get("llm_words_absent_from_corpus", []))


def load_ai_classifier(field_profile_dir: Path | None):
    if field_profile_dir is None:
        return None
    path = field_profile_dir / "ai_ism_classifier.joblib"
    if not path.exists():
        return None
    import joblib
    return joblib.load(path)


def paragraph_ranges(text: str) -> list[tuple[int, int, str]]:
    return deai_metrics.paragraph_line_ranges(text)


def score_paragraphs(classifier, paragraphs: list[tuple[int, int, str]]) -> list[float]:
    if not paragraphs:
        return []
    probabilities = classifier.predict_proba([paragraph[2] for paragraph in paragraphs])
    classes = list(classifier.classes_)
    column = classes.index(1) if 1 in classes else -1
    return [float(row[column]) for row in probabilities]


def section_ranges(text: str) -> list[tuple[int, int, str]]:
    return deai_metrics.section_line_ranges(text)


def section_for_line(line_no: int, ranges: list[tuple[int, int, str]]) -> str:
    for start, end, label in ranges:
        if start <= line_no <= end:
            return label
    return "(unknown)"


def _finding(*, path: Path, kind: str, layer: str, rule: str, line: int,
             section: str, excerpt: str, message: str, action: str,
             detector: str = "ai_ism_lint", strength: str = "ordinary",
             strong_advisory: bool = False,
             observed: dict[str, Any] | None = None,
             reference: dict[str, Any] | None = None,
             normalized_distance: float | None = None,
             measurement_status: str = "measured") -> dict[str, Any]:
    return feedback.make_finding(
        kind=kind, layer=layer, rule=rule, scope="sentence", path=path,
        line=line, section=section, detector=detector, strength=strength,
        strong_advisory=strong_advisory, observed=observed or {"excerpt": excerpt},
        reference=reference, normalized_distance=normalized_distance,
        confidence={"value": 1.0, "basis": "deterministic lexical match"},
        measurement_status=measurement_status, message=message, action=action,
        evidence=[rule, excerpt],
    )


def lexical_findings(text: str, path: Path,
                     field_profile_dir: Path | None,
                     ai_classifier: bool = False,
                     ai_threshold: float = 0.7
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return lexical findings and axis statuses.

    Tier B is measured everywhere but only occurrences beyond the per-section,
    per-word cap become L0 targets.
    """
    lines = text.splitlines()
    ranges = section_ranges(text)
    findings: list[dict[str, Any]] = []
    tier_b: dict[tuple[str, str], list[tuple[int, str]]] = defaultdict(list)

    for line_no, line in enumerate(lines, start=1):
        section = section_for_line(line_no, ranges)
        excerpt = line.strip()
        # Resolved before the Tier A/B scans because one paragraph-initial
        # connector must produce exactly one L0 target. `Crucially` sits in both
        # TIER_A_PATTERN and this connector list, so without the same span guard
        # the Tier B loop already applies it would be counted twice, while
        # `Notably`/`Importantly`/`Interestingly` (Tier B) are counted once.
        connector = TIER_A_PARAGRAPH_CONNECTOR_PATTERN.match(line)
        if EM_DASH_PATTERN.search(line):
            findings.append(_finding(
                path=path, kind="l0_target", layer="L0", rule="em-dash",
                line=line_no, section=section, excerpt=excerpt,
                strength="target", message="Em-dash punctuation is an L0 rewrite target.",
                action="Replace with punctuation that matches the sentence relation.",
            ))
        for match in TIER_A_PATTERN.finditer(line):
            if connector and match.start() < connector.end():
                continue
            word = match.group(0).lower()
            findings.append(_finding(
                path=path, kind="l0_target", layer="L0", rule=f"tier-a:{word}",
                line=line_no, section=section, excerpt=excerpt, strength="target",
                message=f"Tier A lexical target {word!r} is present.",
                action="Rewrite the sentence with a direct field-appropriate expression.",
            ))
        if TIER_A_OPENER_PATTERN.match(line):
            findings.append(_finding(
                path=path, kind="l0_target", layer="L0", rule="tier-a:opener",
                line=line_no, section=section, excerpt=excerpt, strength="target",
                message="A zero-reference boilerplate opener is present.",
                action="Open with the specific scientific problem or evidence.",
            ))
        if connector:
            word = connector.group(1).lower()
            findings.append(_finding(
                path=path, kind="l0_target", layer="L0",
                rule=f"tier-a:paragraph-start:{word}", line=line_no,
                section=section, excerpt=excerpt, strength="target",
                message=f"Paragraph-initial connector {word!r} is an L0 target.",
                action="Remove the roadmap connector and let the argument carry the transition.",
            ))
        for match in TIER_B_PATTERN.finditer(line):
            if connector and match.start() < connector.end():
                continue
            word = match.group(0).lower()
            tier_b[(section, word)].append((line_no, excerpt))
        for match in STUBBORN_REPLACE_PATTERN.finditer(line):
            word = match.group(0).lower()
            findings.append(_finding(
                path=path, kind="advisory", layer="L0",
                rule=f"style-substitution:{word}", line=line_no,
                section=section, excerpt=excerpt,
                message=f"The phrase {word!r} is an indirect stylistic construction.",
                action="Prefer a direct verb when doing so preserves meaning.",
            ))
        if THREE_PARALLEL_PATTERN.search(line):
            findings.append(_finding(
                path=path, kind="advisory", layer="L2", rule="three-parallel",
                line=line_no, section=section, excerpt=excerpt,
                message="The sentence uses a conspicuous three-part parallel frame.",
                action="Keep the parallelism only if it carries a real logical distinction; otherwise simplify it.",
            ))
        prose_part = TRAILING_COMMENT_PATTERN.sub("", line)
        for match in ING_TAIL_PATTERN.finditer(prose_part):
            word = match.group(0).lstrip(", ").lower()
            findings.append(_finding(
                path=path, kind="advisory", layer="L2", rule=f"ing-tail:{word}",
                line=line_no, section=section, excerpt=excerpt,
                message=(f"A participial tail {word!r} appends interpretation "
                         "instead of stating it as a claim."),
                action="Promote the tail to its own sentence with a subject and evidence, or delete it.",
            ))
        if COLON_ELABORATION_PATTERN.search(prose_part):
            findings.append(_finding(
                path=path, kind="advisory", layer="L2", rule="colon-elaboration",
                line=line_no, section=section, excerpt=excerpt,
                message="A prose colon introduces an appositive elaboration.",
                action=("Rewrite as a relative clause, two sentences, or ', so ...'; "
                        "keep the colon only for caption tags or genuine list specifications."),
            ))

    for (section, word), occurrences in tier_b.items():
        for index, (line_no, excerpt) in enumerate(occurrences):
            if index < TIER_B_CAP:
                continue
            findings.append(_finding(
                path=path, kind="l0_target", layer="L0",
                rule=f"tier-b-excess:{word}", line=line_no, section=section,
                excerpt=excerpt, strength="target",
                observed={"word": word, "occurrence_in_section": index + 1,
                          "section_count": len(occurrences)},
                reference={"cap_per_section_per_word": TIER_B_CAP,
                           "provenance": "skills/paper/SKILL.md"},
                normalized_distance=float(index + 1 - TIER_B_CAP),
                message=(f"Tier B word {word!r} exceeds the per-section cap "
                         f"of {TIER_B_CAP}; this is occurrence {index + 1}."),
                action="Replace or remove the excess occurrence with a specific description.",
            ))

    blacklist = load_corpus_blacklist(field_profile_dir)
    if blacklist:
        pattern = re.compile(r"\b(" + "|".join(re.escape(word) for word in blacklist)
                             + r")\b", re.IGNORECASE)
        for line_no, line in enumerate(lines, start=1):
            for match in pattern.finditer(line):
                word = match.group(1).lower()
                findings.append(_finding(
                    path=path, kind="advisory", layer="L0",
                    rule=f"corpus-zero:{word}", line=line_no,
                    section=section_for_line(line_no, ranges), excerpt=line.strip(),
                    message=f"The field lexicon records zero occurrences of {word!r}.",
                    action="Inspect the corpus evidence and rewrite only if the term is not scientifically necessary.",
                    reference={"provenance": str(field_profile_dir / 'lexicon.json')},
                ))

    axes = [feedback.axis_status("L0.lexical", "measured", detector="ai_ism_lint")]
    if ai_classifier:
        try:
            classifier = load_ai_classifier(field_profile_dir)
        except (ImportError, OSError, ValueError) as error:
            classifier = None
            axes.append(feedback.axis_status(
                "L3.legacy_classifier", "unmeasured", reason=str(error),
                detector="ai_ism_lint"))
        else:
            if classifier is None:
                axes.append(feedback.axis_status(
                    "L3.legacy_classifier", "unmeasured",
                    reason="ai_ism_classifier.joblib is unavailable",
                    detector="ai_ism_lint"))
            else:
                axes.append(feedback.axis_status(
                    "L3.legacy_classifier", "degraded",
                    reason="legacy classifier threshold is user-supplied and not an authorship verdict",
                    detector="ai_ism_lint"))
                paragraphs = paragraph_ranges(text)
                for (start, end, paragraph), score in zip(
                        paragraphs, score_paragraphs(classifier, paragraphs)):
                    if score < ai_threshold:
                        continue
                    section = section_for_line(start, ranges)
                    findings.append(feedback.make_finding(
                        kind="advisory", layer="L3", rule="legacy-classifier-high",
                        scope="paragraph", path=path, line=start, end_line=end,
                        section=section, detector="ai_ism_lint",
                        measurement_status="degraded", strength="ordinary",
                        observed={"legacy_similarity_score": score},
                        reference={"user_threshold": ai_threshold,
                                   "provenance": "ai_ism_classifier.joblib"},
                        normalized_distance=score - ai_threshold,
                        confidence={"value": 0.5,
                                    "basis": "legacy classifier; calibration limitations apply"},
                        message=(f"Legacy classifier score {score:.2f} is above the "
                                 f"requested review point {ai_threshold:.2f}."),
                        action="Use this only as triage; inspect specific L1/L2 evidence before rewriting.",
                        evidence=round(score, 8),
                    ))
    return findings, axes


def collect_feedback(path: Path, field_profile_dir: Path | None, *,
                     ai_classifier: bool = False, ai_threshold: float = 0.7,
                     distribution: bool = True, structure: bool = True,
                     document_structure: bool = True, oracle: bool = False,
                     voice: bool = False, register: bool = True,
                     salience: bool = True, discourse: bool = True
                     ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings, axes = lexical_findings(
        text, path, field_profile_dir, ai_classifier, ai_threshold)
    if register:
        findings.extend(deai_register.register_findings(text, field_profile_dir, path))
        axes.append(deai_register.register_axis_status(field_profile_dir))
    if salience:
        findings.extend(deai_salience.salience_findings(text, field_profile_dir, path))
        axes.append(deai_salience.salience_axis_status(field_profile_dir))
    if discourse:
        findings.extend(deai_discourse.discourse_findings(text, field_profile_dir, path))
        # extend, not append: this detector reports one status PER FEATURE,
        # because cohesion and hedging calibrate at different units and a
        # field can support one and not the other.
        axes.extend(deai_discourse.discourse_axis_status(field_profile_dir))
    if distribution:
        findings.extend(deai_metrics.distribution_findings(text, field_profile_dir, path))
        axes.append(deai_metrics.distribution_axis_status(field_profile_dir))
    if structure:
        findings.extend(deai_structure.structure_findings(text, field_profile_dir, path))
        axes.append(deai_structure.structure_axis_status(field_profile_dir))
    if document_structure:
        findings.extend(deai_docstructure.document_findings(text, field_profile_dir, path))
        axes.append(deai_docstructure.docstructure_axis_status(text, field_profile_dir))
    if oracle:
        try:
            import deai_oracle
            findings.extend(deai_oracle.uid_findings(
                text, field_profile_dir, path=path))
            axes.append(deai_oracle.uid_axis_status(field_profile_dir))
        except Exception as error:
            axes.append(feedback.axis_status("L1.uid", "unmeasured",
                                             reason=str(error), detector="deai_oracle"))
    if voice:
        try:
            import deai_voice
            findings.extend(deai_voice.voice_findings(
                text, field_profile_dir, path=path))
            axes.append(deai_voice.voice_axis_status(field_profile_dir))
        except Exception as error:
            axes.append(feedback.axis_status("L3.voice", "unmeasured",
                                             reason=str(error), detector="deai_voice"))
    return findings, axes


def lint(path: Path, field_profile_dir: Path | None, summary: bool = False,
         ai_classifier: bool = False, ai_threshold: float = 0.7,
         distribution: bool = True, structure: bool = True,
         oracle: bool = False, voice: bool = False,
         document_structure: bool = True, output_format: str = "text",
         output: Path | None = None, top: int | None = None,
         register: bool = True, salience: bool = True,
         discourse: bool = True) -> int:
    del summary  # retained as a compatibility option; reports always include totals
    if not path.exists():
        print(f"[ai_ism_lint] file not found: {path}", file=sys.stderr)
        return 2
    try:
        findings, axes = collect_feedback(
            path, field_profile_dir, ai_classifier=ai_classifier,
            ai_threshold=ai_threshold, distribution=distribution,
            structure=structure, document_structure=document_structure,
            oracle=oracle, voice=voice, register=register, salience=salience,
            discourse=discourse)
        report = feedback.build_report(path=path, findings=findings, axes=axes, top=top)
        rendered = (feedback.dump_report(report)
                    if output_format == "json" else feedback.render_text(report) + "\n")
        if output is not None:
            output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except Exception as error:
        # Deliberately broad: exit 1 is reserved for "an L0 target is present",
        # so ANY execution failure must surface as 2. A narrow tuple let a
        # malformed profile asset (a lexicon.json holding a JSON list rather
        # than an object -> AttributeError) escape and exit 1, reporting a
        # crash as a clean prose verdict. KeyboardInterrupt/SystemExit are
        # BaseException and still propagate.
        print(f"[ai_ism_lint] execution failed: {type(error).__name__}: {error}",
              file=sys.stderr)
        return 2
    return 1 if report["summary"]["by_kind"]["l0_target"] else 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--field", default=None)
    parser.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    parser.add_argument("--summary", action="store_true",
                        help="compatibility flag; totals are always included")
    parser.add_argument("--ai-classifier", action="store_true")
    parser.add_argument("--ai-threshold", type=float, default=0.7)
    parser.add_argument("--distribution", action=argparse.BooleanOptionalAction,
                        default=True)
    parser.add_argument("--structure", action=argparse.BooleanOptionalAction,
                        default=True)
    parser.add_argument("--document-structure", action=argparse.BooleanOptionalAction,
                        default=True)
    parser.add_argument("--register", action=argparse.BooleanOptionalAction,
                        default=True)
    parser.add_argument("--salience", action=argparse.BooleanOptionalAction,
                        default=True)
    parser.add_argument("--discourse", action=argparse.BooleanOptionalAction,
                        default=True)
    parser.add_argument("--oracle", action="store_true")
    parser.add_argument("--voice", action="store_true")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top", type=int)
    args = parser.parse_args(argv)
    field = resolve_field(args.field, args.profile_root)
    if args.field and field is None:
        # An explicitly requested field that cannot be loaded is a
        # configuration failure (exit 2), never a clean exit-0 run.
        return 2
    field_dir = args.profile_root / field if field else None
    return lint(
        args.file, field_dir, summary=args.summary,
        ai_classifier=args.ai_classifier, ai_threshold=args.ai_threshold,
        distribution=args.distribution, structure=args.structure,
        document_structure=args.document_structure, oracle=args.oracle,
        voice=args.voice, output_format=args.format, output=args.output,
        top=args.top, register=args.register, salience=args.salience,
        discourse=args.discourse,
    )


if __name__ == "__main__":
    raise SystemExit(main())
