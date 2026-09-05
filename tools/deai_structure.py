"""Model-free sentence-construction feedback for scientific prose (L2).

The detector reports concrete template families without making authorship
claims. :func:`structure_findings` is the structured API;
:func:`structure_hits` is the compatibility tuple adapter.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_feedback as feedback  # noqa: E402  sibling import after path setup
import deai_reference as reference  # noqa: E402  the shared paragraph sweep
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
# Auxiliary families (v0.18.0, panel-derived; EVALUATION §13). Kept OUT of
# `templates`/`template_score` so the calibrated document-dispersion manifold
# (deai_docstructure consumes template_score) is unchanged by their addition.
RE_ANTITHESIS = re.compile(
    r"\b(rather than|instead of)\b|\bnot\s+(?:\w+\s+){0,3}?but\b", re.I)
RE_REVERSAL = re.compile(
    r"^(it|they|this|that)\b[^.!?]{0,25}\b(not|never|opposite)\b", re.I)
# Advisor-round families (v0.36.0; advisor-round taxonomy, 2026-09-01). Three
# constructions an advisor marked as reading like a prompt or a machine, each
# abstracted to its form; no sentence from that round is quoted anywhere in
# this repository. Auxiliary like the two above: never in `template_score`.
#   paper-agent    the paper as a thinking agent ("this Letter asks whether")
#   wh-cleft       a wh-clause as subject with the point in the predicate
#                  ("what it can conclude is limited by")
#   modifier-stack a noun buried under a run of pre-modifiers, at least two of
#                  them hyphenated or numeric ("per-map empirical B-mode null")
RE_PAPER_AGENT = re.compile(
    r"\b(?:this|the present|our)\s+(?:paper|letter|work|study|article|analysis|"
    r"note|manuscript)\s+(?:asks?|answers?|argues?|wonders?|explores?|seeks?|"
    r"hopes?|believes?|claims?|contends?|concludes?|finds?|suggests?|reveals?|"
    r"cannot|can|does not|will not)\b", re.I)
RE_WH_CLEFT = re.compile(
    r"^(?:what|how|whether|why)\b[^.!?;:]{2,60}?\b(?:is|are|was|were|remains|"
    r"becomes)\s+(?:that|the|a|an|to|whether|how|not|limited|set|governed|"
    r"determined|simply|this|its|our)\b", re.I)
_MODIFIER_TOKEN = r"[A-Za-z0-9][A-Za-z0-9\-']*"
_MODIFIER_FUNCTION = frozenset("""a an the of in on at to for from by with and or
but as is are was were be been that this these those it its we our which than
then there where when while if so such not no also both each any all some more
most less very can may will do does has have had into over under between among
through per via""".split())
MIN_WORDS = 30
ANAPHORA_RUN = 3
ORDINAL_RUN = 2
MODAL_RUN = 3
ANTITHESIS_CLUSTER = 2
REVERSAL_MAX_WORDS = 5
MODIFIER_STACK_RUN = 3
MODIFIER_STACK_COMPOUNDS = 2


def modifier_stacks(sentence: str) -> list[str]:
    """Noun phrases of >= MODIFIER_STACK_RUN consecutive non-function tokens in
    which >= MODIFIER_STACK_COMPOUNDS are hyphenated compounds.

    A run of content tokens is cut at the head noun, the token after the last
    compound, because without a parser that is the only place a phrase can be
    seen to end: `non-compensated 500-configuration subfamily fails` reports
    the phrase, not the verb. `[math]`/`[CITE]` placeholders and every
    punctuation mark break a run, so a list of quantities is not a phrase.
    """
    stacks: list[str] = []
    for clause in re.split(r"[,;:()\[\]\"“”]|--|—|–", sentence):
        run: list[str] = []
        for token in clause.split():
            word = token.strip(".!?'\"")
            if (not re.fullmatch(_MODIFIER_TOKEN, word)
                    or word.lower() in _MODIFIER_FUNCTION):
                run = _flush_stack(run, stacks)
                continue
            run.append(word)
            if token != word:                       # trailing sentence punctuation
                run = _flush_stack(run, stacks)
        _flush_stack(run, stacks)
    return stacks


def _flush_stack(run: list[str], stacks: list[str]) -> list[str]:
    compounds = [index for index, word in enumerate(run) if "-" in word.strip("-")]
    if compounds and len(compounds) >= MODIFIER_STACK_COMPOUNDS:
        phrase = run[: compounds[-1] + 2]           # through the head noun
        if len(phrase) >= MODIFIER_STACK_RUN:
            stacks.append(" ".join(phrase))
    return []


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
    antithesis_count = len(RE_ANTITHESIS.findall(plain))
    reversal_beat = any(
        len(es.words(sentence)) <= REVERSAL_MAX_WORDS
        and RE_REVERSAL.match(sentence.strip())
        for sentence in sentences)
    paper_agent = sum(1 for sentence in sentences if RE_PAPER_AGENT.search(sentence))
    wh_cleft = sum(1 for sentence in sentences if RE_WH_CLEFT.match(sentence.strip()))
    stacks = [stack for sentence in sentences for stack in modifier_stacks(sentence)]
    auxiliary: list[str] = []
    if antithesis_count >= ANTITHESIS_CLUSTER:
        auxiliary.append("antithesis-cluster")
    if reversal_beat:
        auxiliary.append("short-reversal")
    if paper_agent:
        auxiliary.append("paper-agent")
    if wh_cleft:
        auxiliary.append("wh-cleft")
    if stacks:
        auxiliary.append("modifier-stack")
    return {
        "paper_agent_count": paper_agent,
        "wh_cleft_count": wh_cleft,
        "modifier_stacks": stacks,
        "n_sent": len(sentences),
        "announced": announced,
        "ordinal_run": ordinal_run,
        "anaphora_run": anaphora_run,
        "modal_run": modal_run,
        "tricolon_wrap": tricolon_wrap,
        "balanced": balanced,
        "antithesis_count": antithesis_count,
        "reversal_beat": reversal_beat,
        "templates": templates,
        "auxiliary_templates": auxiliary,
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
    # The shared paragraph sweep blanks headings before splitting: left in
    # place, a heading one newline above a wh-cleft opener fused with it
    # (`Methods What it can conclude is`) and the family was missed while the
    # same paragraph two newlines below the heading was reported.
    for paragraph_start, paragraph_end, raw_label, bucket, block in reference.paragraphs(text):
        if len(es.words(es.latex_to_plain(block))) < MIN_WORDS:
            continue
        values = paragraph_structure(block)
        if not values["templates"] and not values["auxiliary_templates"]:
            continue
        bucket_reference = baseline.get(bucket, {}) if baseline else {}
        human_fraction = bucket_reference.get("templated_frac")
        reference_n = int(bucket_reference.get("n", 0))
        rare_fraction = (policy or {}).get("rare_template_fraction")
        if values["templates"]:
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
                reference=feedback.reference_block(
                    field_profile_dir, bucket=bucket, n=reference_n,
                    templated_fraction=human_fraction,
                    operating_point=rare_fraction,
                    provenance="structure_baseline.json" if baseline else None),
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
        if values["auxiliary_templates"]:
            aux_fraction = bucket_reference.get("auxiliary_frac")
            aux_context = (f"; reference {bucket} fraction {aux_fraction:.1%} "
                           f"(n={reference_n})") if aux_fraction is not None else ""
            findings.append(feedback.make_finding(
                kind="advisory", layer="L2",
                rule=f"structure-auxiliary:{bucket}", scope="paragraph",
                calibration_unit="paragraph",
                line=paragraph_start, end_line=paragraph_end,
                section=raw_label, path=path, detector="deai_structure",
                measurement_status="measured" if aux_fraction is not None else (
                    "degraded" if baseline else "unmeasured"),
                strength="ordinary", strong_advisory=False,
                observed={"auxiliary_templates": values["auxiliary_templates"],
                          "antithesis_count": values["antithesis_count"],
                          "reversal_beat": values["reversal_beat"],
                          "paper_agent_count": values["paper_agent_count"],
                          "wh_cleft_count": values["wh_cleft_count"],
                          "modifier_stacks": values["modifier_stacks"],
                          "sentence_count": values["n_sent"]},
                reference=feedback.reference_block(
                    field_profile_dir, bucket=bucket, n=reference_n,
                    auxiliary_fraction=aux_fraction,
                    provenance="structure_baseline.json" if baseline else None),
                normalized_distance=(1.0 - float(aux_fraction))
                if aux_fraction is not None else None,
                confidence={"value": min(1.0, values["n_sent"] / 6.0),
                            "basis": f"{values['n_sent']} sentences; deterministic rhetorical-figure evidence"},
                message=("Paragraph leans on rhetorical figure(s) rare in the "
                         "field reference: "
                         f"{', '.join(values['auxiliary_templates'])}{aux_context}."),
                action=("Keep an antithesis only where the contrast is load-bearing "
                        "technical content; state posture contrasts as plain positive "
                        "claims; flatten short reversal beats into connected prose. "
                        "Give a paper-as-agent sentence a human or physical subject "
                        "(we ask / the data show); turn a wh-cleft into a plain "
                        "subject-verb claim; unpack a modifier stack into a head "
                        "noun and one relative clause or prepositional phrase."),
                evidence=values["auxiliary_templates"],
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
        "auxiliary": 0, "antithesis_cluster": 0, "reversal": 0,
        "paper_agent": 0, "wh_cleft": 0, "modifier_stack": 0,
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
        item["auxiliary"] += bool(values["auxiliary_templates"])
        item["antithesis_cluster"] += values["antithesis_count"] >= ANTITHESIS_CLUSTER
        item["reversal"] += values["reversal_beat"]
        item["paper_agent"] += values["paper_agent_count"] > 0
        item["wh_cleft"] += values["wh_cleft_count"] > 0
        item["modifier_stack"] += bool(values["modifier_stacks"])
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
            "auxiliary_frac": item["auxiliary"] / n,
            "antithesis_cluster_frac": item["antithesis_cluster"] / n,
            "reversal_frac": item["reversal"] / n,
            "paper_agent_frac": item["paper_agent"] / n,
            "wh_cleft_frac": item["wh_cleft"] / n,
            "modifier_stack_frac": item["modifier_stack"] / n,
        }
    (field_profile_dir / "structure_baseline.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    return cli_common.axis_main(
        __doc__, argv, tool="deai_structure", calibrate=calibrate,
        summary=lambda _result, field_dir:
            f"baseline written: {field_dir / 'structure_baseline.json'}",
        report=lambda text, field_dir, path: feedback.build_report(
            path=path, findings=structure_findings(text, field_dir, path),
            axes=[structure_axis_status(field_dir)]),
        render=feedback.render_text)


if __name__ == "__main__":
    raise SystemExit(main())
