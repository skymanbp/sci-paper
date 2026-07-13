"""Model-free sentence-construction feedback for scientific prose (L2).

The detector reports concrete template families without making authorship
claims. :func:`structure_findings` is the structured API;
:func:`structure_hits` is the compatibility tuple adapter.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_feedback as feedback  # noqa: E402  sibling import after path setup
import deai_metrics as metrics  # noqa: E402  canonical section/paragraph ranges
import extract_style as es  # noqa: E402  canonical tokenizer

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
_COUNT = r"two|three|four|five|six|seven|eight|2|3|4|5|6|7|8"
_ENUM_NOUN = (r"elements|components|parts|ingredients|obligations|requirements|"
              r"properties|features|reasons|ways|steps|aspects|criteria|"
              r"principles|pillars|considerations|facts|assumptions|conditions|"
              r"constraints|observations|points|contributions|goals|questions|"
              r"claims|axes|desiderata|stages|pieces|threads|strands")
_ORDINALS = {"first", "second", "third", "fourth", "fifth", "sixth", "seventh"}
_TRIVIAL_OPENERS = {"the", "a", "an", "this", "that", "these", "those", "it",
                    "we", "our", "in", "for", "as", "to", "at", "on", "by"}
_MODAL_PATTERN = re.compile(r"\b(must|should|shall|will|can|cannot|need to|needs to|has to|have to)\b", re.I)
RE_ENUM_NOUN = re.compile(rf"\b({_COUNT})\s+({_ENUM_NOUN})\b", re.I)
RE_ENUM_VERB = re.compile(
    rf"\b(rests?|relies|rely|hinges?|based|consists?|comprises?|comprise|"
    rf"depends?|builds?|require|requires|involve|involves|follow|follows|"
    rf"proceeds?|breaks? down)\b[^.\n]{{0,30}}\b(on|of|into|from|in)\b"
    rf"[^.\n]{{0,20}}\b({_COUNT})\b", re.I)
RE_TRICOLON_WRAP = re.compile(rf"\bthese\s+({_COUNT})\s+\w+", re.I)
RE_BALANCED = re.compile(r"\bone\b[^.\n]{0,60}\band\b[^.\n]{0,45}\banother\b", re.I)
MIN_WORDS = 30
ANAPHORA_RUN = 3
ORDINAL_RUN = 2
MODAL_RUN = 3


def _first_word(sentence: str) -> str:
    words = es.words(sentence)
    return words[0].lower() if words else ""


def _max_run(sequence, predicate) -> int:
    best = current = 0
    for value in sequence:
        current = current + 1 if predicate(value) else 0
        best = max(best, current)
    return best


def _max_run_equal(sequence, exclude=frozenset()) -> int:
    best = current = 1 if sequence else 0
    for index in range(1, len(sequence)):
        if (sequence[index] and sequence[index] == sequence[index - 1]
                and sequence[index] not in exclude):
            current += 1
        else:
            current = 1
        best = max(best, current)
    return best if sequence else 0


def _modal(sentence: str) -> str:
    match = _MODAL_PATTERN.search(sentence)
    return match.group(1).lower() if match else ""


def paragraph_structure(text: str) -> dict[str, Any]:
    plain = es.latex_to_plain(text)
    sentences = [sentence for sentence in es.sentences(plain) if es.words(sentence)]
    first_words = [_first_word(sentence) for sentence in sentences]
    modals = [_modal(sentence) for sentence in sentences]
    announced = bool(RE_ENUM_NOUN.search(plain) or RE_ENUM_VERB.search(plain))
    ordinal_run = _max_run(first_words, lambda word: word in _ORDINALS)
    anaphora_run = _max_run_equal(first_words, exclude=_TRIVIAL_OPENERS)
    modal_run = _max_run_equal(modals, exclude={""})
    tricolon_wrap = bool(RE_TRICOLON_WRAP.search(plain))
    balanced = bool(RE_BALANCED.search(plain))
    templates: list[str] = []
    if announced and ordinal_run >= ORDINAL_RUN:
        templates.append("announced-enumeration")
    elif announced:
        templates.append("announced-count")
    elif ordinal_run >= ORDINAL_RUN:
        templates.append("ordinal-run")
    if tricolon_wrap:
        templates.append("tricolon-wrapup")
    if anaphora_run >= ANAPHORA_RUN:
        templates.append("parallel-anaphora")
    if modal_run >= MODAL_RUN:
        templates.append("parallel-modal")
    if balanced:
        templates.append("balanced-closer")
    return {
        "n_sent": len(sentences),
        "announced": announced,
        "ordinal_run": ordinal_run,
        "anaphora_run": anaphora_run,
        "modal_run": modal_run,
        "tricolon_wrap": tricolon_wrap,
        "balanced": balanced,
        "templates": templates,
        "template_score": len(templates),
    }


def load_baseline(field_profile_dir: Path | None) -> dict[str, Any] | None:
    if field_profile_dir is None:
        return None
    path = field_profile_dir / "structure_baseline.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_policy(field_profile_dir: Path | None) -> dict[str, Any] | None:
    if field_profile_dir is None:
        return None
    path = field_profile_dir / "deai_policy.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data.get("structure", data)


def structure_axis_status(field_profile_dir: Path | None) -> dict[str, Any]:
    if load_baseline(field_profile_dir) is None:
        return feedback.axis_status(
            "L2.sentence_structure", "unmeasured",
            reason="structure_baseline.json is unavailable",
            detector="deai_structure",
        )
    if load_policy(field_profile_dir) is None:
        return feedback.axis_status(
            "L2.sentence_structure", "degraded",
            reason="template evidence measured, but no calibrated strong-feedback operating point is available",
            detector="deai_structure",
        )
    return feedback.axis_status("L2.sentence_structure", "measured",
                                detector="deai_structure")


def structure_findings(text: str, field_profile_dir: Path | None,
                       path: str | Path | None = None
                       ) -> list[dict[str, Any]]:
    baseline = load_baseline(field_profile_dir)
    policy = load_policy(field_profile_dir)
    findings: list[dict[str, Any]] = []
    lines = text.splitlines()
    for start, end, raw_label in metrics.section_line_ranges(text):
        bucket = metrics._bucket_for(raw_label)
        segment = "\n".join(lines[start - 1:end])
        for paragraph_start, paragraph_end, block in metrics.paragraph_line_ranges(
                segment, start):
            if len(es.words(es.latex_to_plain(block))) < MIN_WORDS:
                continue
            values = paragraph_structure(block)
            if not values["templates"]:
                continue
            bucket_reference = baseline.get(bucket, {}) if baseline else {}
            human_fraction = bucket_reference.get("templated_frac")
            reference_n = int(bucket_reference.get("n", 0))
            rare_fraction = (policy or {}).get("rare_template_fraction")
            strong = bool(
                baseline and policy and human_fraction is not None
                and rare_fraction is not None and reference_n >= 20
                and human_fraction <= float(rare_fraction)
            )
            status = "measured" if baseline and policy else (
                "degraded" if baseline else "unmeasured")
            context = (f"; reference {bucket} fraction {human_fraction:.1%} "
                       f"(n={reference_n})") if human_fraction is not None else ""
            findings.append(feedback.make_finding(
                kind="advisory", layer="L2",
                rule=f"structure-template:{bucket}", scope="paragraph",
                calibration_unit="paragraph",
                line=paragraph_start, end_line=paragraph_end,
                section=raw_label, path=path, detector="deai_structure",
                measurement_status=status,
                strength="strong" if strong else "ordinary",
                strong_advisory=strong,
                observed={"templates": values["templates"],
                          "template_score": values["template_score"],
                          "sentence_count": values["n_sent"]},
                reference={"field_profile": str(field_profile_dir) if field_profile_dir else None,
                           "section_bucket": bucket,
                           "templated_fraction": human_fraction,
                           "n": reference_n,
                           "operating_point": rare_fraction,
                           "provenance": "structure_baseline.json" if baseline else None},
                normalized_distance=(1.0 - float(human_fraction))
                if human_fraction is not None else None,
                confidence={"value": min(1.0, values["n_sent"] / 6.0),
                            "basis": f"{values['n_sent']} sentences; deterministic template evidence"},
                message=("Paragraph contains repeated sentence-construction "
                         f"template(s): {', '.join(values['templates'])}{context}."),
                action=("Dissolve unnecessary enumeration or symmetry while preserving "
                        "the claim, evidence, and logical dependencies."),
                evidence=values["templates"],
            ))
    return findings


def structure_hits(text: str, field_profile_dir: Path | None
                   ) -> list[tuple[int, str, str]]:
    return feedback.tuple_hits(structure_findings(text, field_profile_dir))


def calibrate(field_profile_dir: Path) -> dict[str, Any]:
    bank = field_profile_dir / "exemplar_paragraphs.jsonl"
    if not bank.exists():
        raise SystemExit(f"[deai_structure] no exemplar bank at {bank}")
    aggregate = defaultdict(lambda: {
        "n": 0, "templated": 0, "announced": 0, "ordinal": 0,
        "tricolon": 0, "anaphora": 0, "modal": 0, "balanced": 0,
    })
    for line in bank.open(encoding="utf-8"):
        record = json.loads(line)
        text = record.get("text", "")
        if len(es.words(es.latex_to_plain(text))) < MIN_WORDS:
            continue
        bucket = record.get("section", "unknown")
        values = paragraph_structure(text)
        item = aggregate[bucket]
        item["n"] += 1
        item["templated"] += bool(values["templates"])
        item["announced"] += values["announced"]
        item["ordinal"] += values["ordinal_run"] >= ORDINAL_RUN
        item["tricolon"] += values["tricolon_wrap"]
        item["anaphora"] += values["anaphora_run"] >= ANAPHORA_RUN
        item["modal"] += values["modal_run"] >= MODAL_RUN
        item["balanced"] += values["balanced"]
    output: dict[str, Any] = {}
    for bucket, item in aggregate.items():
        n = max(1, item["n"])
        output[bucket] = {
            "n": item["n"],
            "templated_frac": item["templated"] / n,
            "announced_frac": item["announced"] / n,
            "ordinal_frac": item["ordinal"] / n,
            "tricolon_frac": item["tricolon"] / n,
            "anaphora_frac": item["anaphora"] / n,
            "modal_frac": item["modal"] / n,
            "balanced_frac": item["balanced"] / n,
        }
    (field_profile_dir / "structure_baseline.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--field", default=None)
    parser.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    parser.add_argument("--calibrate", action="store_true")
    args = parser.parse_args(argv)
    field_dir = args.profile_root / args.field if args.field else None
    if args.calibrate:
        if field_dir is None:
            print("[deai_structure] --calibrate needs --field", file=sys.stderr)
            return 2
        calibrate(field_dir)
        print(f"[deai_structure] baseline written: {field_dir / 'structure_baseline.json'}")
        return 0
    if not args.file or not args.file.exists():
        print(f"[deai_structure] file not found: {args.file}", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    report = feedback.build_report(
        path=args.file,
        findings=structure_findings(text, field_dir, args.file),
        axes=[structure_axis_status(field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
