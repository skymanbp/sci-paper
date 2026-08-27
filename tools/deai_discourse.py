"""Model-free discourse-texture feedback for scientific prose (L2).

Two properties a reader feels before they can name them, each judged against the
field's own per-section distribution and each flagged on the LOW tail:

**Cohesion** -- given/new linkage, measured per PARAGRAPH. A paragraph whose
consecutive sentences share no content vocabulary reads as a list of assertions
rather than an argument. The value is the mean fraction of each sentence's
content words that already appeared in the sentence before it.

**Hedging** -- epistemic markers per 1,000 words, measured per SECTION. A
passage with no hedge anywhere has stopped distinguishing what the data show
from what the authors infer.

The two units are not a convenience. Hedging has no paragraph-scale lower tail
at all: on the 27,917-paragraph `wgl` bank the tenth percentile is exactly 0.00
in every one of the seven section buckets, because a 40-word paragraph that
hedges nowhere is entirely ordinary. Calibrating there would have produced a
gate no passage can fall below, and the axis would have reported a confident
zero findings forever. Regrouped so one section is one unit, six of the seven
buckets separate (p10 from 1.05 in `data` to 3.35 in `discussion`); `abstract`
stays flat at 0.00 and abstains, since an abstract IS one passage. Each artifact
records its own `unit` so the two can never be read against each other.

Both axes fire BELOW the tenth percentile -- the opposite direction from
`deai_salience`, because here the defect is absence rather than excess.
`deai_reference.resolves_gate` guards both tails from one implementation, so the
axes cannot drift apart on what "unresolvable" means.

Neither is an authorship claim, and the separation evidence is narrower than it
first looks. Against 203 held-out refereed papers and six independent machine
generation regimes, exactly one bucket separates for every regime: `intro`, at
rank AUC 0.676-0.830 for cohesion (human/human null 0.515) and 0.613-0.816 for
hedging (null 0.460). Everywhere else at least one regime collapses --
cohesion 0.461 in `discussion`, hedging 0.473 in `results` and 0.376 in
`conclusion`, all at or below chance -- and `method`'s apparent hedging
separation (0.603-0.796) sits against a 0.574 human/human null, so most of it is
not separation at all. EVALUATION section 19 carries the full table.

That is why these are advisories against the field's own distribution and not a
detector. The reference says what this field's prose does; a passage below its
tenth percentile is unusual for the field, which is worth telling an author. It
is not evidence about who wrote the passage, and no threshold here may be read
that way.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_feedback as feedback  # noqa: E402 -- sibling import, valid only after that insert
import deai_reference as reference  # noqa: E402 -- sibling import, valid only after that insert
import extract_style as es  # noqa: E402 -- sibling import, valid only after that insert

MIN_REFERENCE_N = reference.MIN_REFERENCE_N
ADVISORY_PERCENTILE = 0.10
STRONG_PERCENTILE = 0.05
# A paragraph shorter than this cannot exhibit or refute given/new linkage.
# Three sentences yields only two overlap measurements, which is thin -- but the
# floor was measured rather than chosen: at four sentences the 20-document `ai`
# tier offers 15 measurable intro paragraphs in total, and at three it offers
# 62, while the human-over-machine separation is unchanged (worst-of-six 0.676
# at three sentences against 0.674 at four). A floor that quadruples what the
# axis can look at for no loss of separation is the right floor.
COHESION_MIN_SENTENCES = 3
COHESION_MIN_WORDS = 40
# A hedge RATE per 1,000 words computed over less than this turns on the
# presence of one or two words. Measured against the bank: at a 120-word floor
# the `data` bucket's tenth percentile is 0.58 markers per 1,000 words and at
# 150 it is 1.05, while raising the floor to 250 buys nothing further and costs
# the `abstract` bucket 86% of its sections.
HEDGING_MIN_WORDS = 150

RE_WORD = re.compile(r"[A-Za-z][A-Za-z-]+")
# Function words carry no given/new information, so counting them as overlap
# would make any two English sentences look linked.
STOPWORDS = frozenset("""the a an and or but of in on at to for with by from as is
are was were be been being that this these those it its we our they their he she
his her which who whom whose what when where why how not no nor so than then
there here can could may might will would shall should must have has had do does
did if because while during between within into over under above below after
before more most less least very much many few both each other same such only
also""".split())
# A fixed epistemic-marker list whose RATE is judged against the field's own
# distribution. The list decides nothing by itself: the register axis refuses a
# curated cross-discipline word list as a verdict, and so does this one.
HEDGES = frozenset("""may might could would seem seems seemed appear appears appeared
suggest suggests suggested indicate indicates indicated likely unlikely possibly
possible probable probably perhaps presumably apparently arguably relatively
somewhat slightly largely broadly generally typically usually often sometimes
tend tends tended assume assumes assumed suppose supposed potentially plausibly
approximately roughly nearly essentially virtually partially partly
moderately""".split())


def _content(sentence: str) -> set[str]:
    return {word.lower() for word in RE_WORD.findall(sentence)
            if word.lower() not in STOPWORDS}


def cohesion_features(block: str) -> dict[str, Any] | None:
    """Given/new linkage for one paragraph, or None if it is too short to have any."""
    plain = es.latex_to_plain(block)
    sentences = [s for s in es.sentences(plain) if len(es.words(s)) >= 4]
    words = RE_WORD.findall(plain)
    if len(sentences) < COHESION_MIN_SENTENCES or len(words) < COHESION_MIN_WORDS:
        return None
    overlaps: list[float] = []
    previous = _content(sentences[0])
    for sentence in sentences[1:]:
        current = _content(sentence)
        if current:
            overlaps.append(len(current & previous) / len(current))
        previous = current
    if not overlaps:
        return None
    return {"cohesion": sum(overlaps) / len(overlaps),
            "n_sentences": len(sentences), "n_words": len(words)}


def hedging_features(block: str) -> dict[str, Any] | None:
    """Epistemic-marker rate for one section, or None if it is too short to have one."""
    words = RE_WORD.findall(es.latex_to_plain(block))
    if len(words) < HEDGING_MIN_WORDS:
        return None
    hedges = sum(1 for word in words if word.lower() in HEDGES)
    return {"hedging": hedges / len(words) * 1000.0,
            "hedge_count": hedges, "n_words": len(words)}


# Everything that differs between the two axes, in one place. The unit is the
# load-bearing entry: it selects both the calibration grouping and the detection
# sweep, so the two can never be set independently and fall out of step.
#
# `buckets` is the second: None means every bucket whose reference resolves, and
# a tuple restricts the axis to the section genres where its operating point was
# shown to hold. Hedging is restricted, and two independent measurements over
# 203 held-out refereed papers put the restriction in the same place:
#
#            held-out rate at a 10% gate     worst-of-six regime AUC (null)
#   intro                  7.89%                     0.613  (0.460)
#   conclusion            15.48%                     0.376  (0.469)
#   discussion            16.34%                     0.526  (0.475)
#   results               24.17%                     0.473  (0.520)
#   data                  22.98%                     0.459  (0.508)
#   method                26.77%                     0.603  (0.574)
#
# Outside `intro` the gate fires at two to three times its nominal rate on prose
# a referee accepted, and at least one generation regime lands at or below
# chance. `method` looks respectable until its human-vs-human null is read: 0.574
# of that 0.603 is not separation. Cohesion needs no such restriction -- it runs
# 6.58%-14.63% across all seven buckets against the same 10% gate.
#
# This was measured on one field. A new field inherits the restriction, and
# widening it means re-running that measurement, not editing this tuple.
AXES: dict[str, dict[str, Any]] = {
    "cohesion": {
        "baseline": "cohesion_baseline.json",
        "unit": "paragraph",
        "spans": reference.units,
        "extract": cohesion_features,
        "buckets": None,
        "message": ("{bucket} passage does not link its sentences: {value:.3f} "
                    "of each sentence's content words already appeared in the "
                    "one before it (p{pct}), against an n={n} human {bucket} "
                    "reference."),
        "action": ("Carry a term forward. Open each sentence with something the "
                   "previous one established, then add the new element -- given "
                   "before new. Do not add connectives to fake the link; repeat "
                   "the actual noun."),
    },
    "hedging": {
        "baseline": "hedging_baseline.json",
        "unit": "section",
        "spans": reference.sections,
        "extract": hedging_features,
        "buckets": ("intro",),
        "message": ("{bucket} section states everything flatly: {value:.2f} "
                    "epistemic markers per 1,000 words (p{pct}), against an "
                    "n={n} human {bucket} reference."),
        "action": ("Separate what the data show from what they suggest. Mark the "
                   "inference steps the evidence does not fully close, and leave "
                   "the measurements themselves unhedged -- the goal is "
                   "calibrated claims, not softer ones."),
    },
}

LOADERS = {feature: reference.baseline_loader(axis["baseline"])
           for feature, axis in AXES.items()}


def resolves_below_gate(ref: dict[str, Any], feature: str) -> bool:
    """Whether the reference separates an unusually low unit from a typical one."""
    return reference.resolves_gate(ref, feature, ADVISORY_PERCENTILE, high=False)


def live_buckets(feature: str, field_profile_dir: Path | None) -> list[str]:
    """The buckets this axis may speak about here, or [] if it may not speak.

    Three conditions, all necessary: the bucket is one the axis is calibrated
    for, its reference clears the sample floor, and that reference has spread
    below the gate. Detection and status read this same function, so an axis
    cannot report `measured` for a bucket it then declines to judge.
    """
    baseline = LOADERS[feature](field_profile_dir)
    if baseline is None:
        return []
    allowed = AXES[feature]["buckets"]
    return [bucket for bucket in reference.usable_buckets(
                baseline, feature, ADVISORY_PERCENTILE, high=False)
            if allowed is None or bucket in allowed]


def axis_name(feature: str) -> str:
    """The axis id one feature reports under.

    `discourse_findings` returns BOTH features' findings in one list, so any
    caller that has to split them by axis -- the status block below, the
    labelling sampler -- needs this spelling. One owner, because a second copy
    is how the sampler would come to file cohesion findings under an axis name
    the report never uses.
    """
    return f"L2.{feature}"


def discourse_axis_status(field_profile_dir: Path | None) -> list[dict[str, Any]]:
    """One status per feature: the two travel together but fail separately.

    They calibrate from the same corpus at different granularities, so a field
    can support one and not the other -- and does: `abstract` resolves for
    cohesion and never for hedging. A single joint status would hide which of
    the two a reader is allowed to act on.
    """
    statuses = []
    for feature, axis in AXES.items():
        name = axis_name(feature)
        if LOADERS[feature](field_profile_dir) is None:
            statuses.append(feedback.axis_status(
                name, "unmeasured",
                reason=f"{axis['baseline']} is unavailable",
                detector="deai_discourse"))
            continue
        live = live_buckets(feature, field_profile_dir)
        if not live:
            statuses.append(feedback.axis_status(
                name, "degraded",
                reason=(f"no calibrated {axis['unit']} bucket both reaches the "
                        f"{MIN_REFERENCE_N}-unit floor and has spread below the "
                        "advisory gate"),
                detector="deai_discourse"))
        else:
            statuses.append(feedback.axis_status(
                name, "measured",
                reason=f"{axis['unit']} unit; buckets: {', '.join(sorted(live))}",
                detector="deai_discourse"))
    return statuses


def _advisory(feature: str, value: float, values: dict[str, Any], found: float, *,
              bucket: str, start: int, end: int, path: str | Path | None,
              ref: dict[str, Any], reference_n: int, measured: bool,
              field_profile_dir: Path | None) -> dict[str, Any]:
    """The finding for one unit on one feature."""
    axis = AXES[feature]
    return feedback.make_finding(
        kind="advisory", layer="L2",
        rule=f"discourse-{feature}:{bucket}", scope=axis["unit"],
        calibration_unit=axis["unit"],
        line=start, end_line=end, section=bucket, path=path,
        detector="deai_discourse",
        measurement_status="measured" if measured else "degraded",
        strength=("strong" if measured and found < STRONG_PERCENTILE
                  else "ordinary"),
        observed=dict(values, feature=feature, value=round(value, 4),
                      percentile=round(found, 4)),
        reference=feedback.reference_block(
            field_profile_dir, bucket=bucket, n=reference_n,
            unit=axis["unit"],
            advisory_percentile=ADVISORY_PERCENTILE,
            strong_percentile=STRONG_PERCENTILE,
            gate_value=reference.grid_value(ref, feature, ADVISORY_PERCENTILE),
            provenance=axis["baseline"]),
        normalized_distance=ADVISORY_PERCENTILE - found,
        confidence={"value": min(1.0, values["n_words"] / 400.0),
                    "basis": (f"{values['n_words']} words against an "
                              f"n={reference_n} {bucket} reference")},
        message=axis["message"].format(bucket=bucket, value=value,
                                       pct=f"{found * 100:.0f}", n=reference_n),
        action=axis["action"],
        evidence=[feature, round(found, 6), round(value, 6)],
    )


def discourse_findings(text: str, field_profile_dir: Path | None,
                       path: str | Path | None = None) -> list[dict[str, Any]]:
    """One finding per unit per feature that falls below the field's gate.

    Unlike salience, the features earn separate findings rather than one led by
    the more extreme: they are measured over different spans of the document and
    name different defects, so collapsing them would leave the author with
    nothing to act on.
    """
    findings: list[dict[str, Any]] = []
    for feature, axis in AXES.items():
        live = set(live_buckets(feature, field_profile_dir))
        if not live:
            continue
        baseline = LOADERS[feature](field_profile_dir)
        for start, end, bucket, block in axis["spans"](text):
            ref = baseline.get(bucket)
            if bucket not in live or not isinstance(ref, dict):
                continue
            values = axis["extract"](block)
            if values is None:
                continue
            value = float(values.pop(feature))
            found = reference.percentile_of(ref, feature, value)
            if found is None or found >= ADVISORY_PERCENTILE:
                continue
            reference_n = int(ref.get("n", 0))
            findings.append(_advisory(
                feature, value, values, found, bucket=bucket, start=start,
                end=end, path=path, ref=ref, reference_n=reference_n,
                measured=reference_n >= MIN_REFERENCE_N,
                field_profile_dir=field_profile_dir))
    return findings


def calibrate(field_profile_dir: Path) -> dict[str, Any]:
    """Build both references, each at its own granularity."""
    banks = reference.passage_banks(field_profile_dir)
    return {feature: reference.calibrate(
                field_profile_dir, axis["baseline"], (feature,),
                axis["extract"], banks, unit=axis["unit"])
            for feature, axis in AXES.items()}


def _written(result: dict[str, Any], field_profile_dir: Path) -> str:
    """What `--calibrate` reports: each axis, its unit, and its bucket sizes.

    The per-bucket n is the line worth printing. A bucket under the reference
    floor is the difference between a measured axis and a degraded one, and
    there is nowhere else an operator would see it.
    """
    return " | ".join(
        f"{AXES[feature]['baseline']} ({AXES[feature]['unit']}: "
        + ", ".join(f"{bucket}={ref['n']}" for bucket, ref in sorted(buckets.items()))
        + ")" for feature, buckets in result.items())


def main(argv: list[str] | None = None) -> int:
    return cli_common.axis_main(
        __doc__, argv, tool="deai_discourse", calibrate=calibrate,
        summary=_written,
        report=lambda text, field_dir, path: feedback.build_report(
            path=path, findings=discourse_findings(text, field_dir, path),
            axes=discourse_axis_status(field_dir)),
        render=feedback.render_text)


if __name__ == "__main__":
    raise SystemExit(main())
