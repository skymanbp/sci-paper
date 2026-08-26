"""Model-free salience-hierarchy feedback for scientific prose (L2).

The axis answers one question a reader asks of a results passage: does the
prose rank what it reports, or recite it? A human abstract interleaves its
measured quantities with the statements that give them consequence; a machine
draft strings the quantities together, because every result it holds looks
equally important to it.

The measured quantity is therefore not "how many numbers" -- a quantitative
abstract is supposed to carry numbers -- but how far the numerals run without
interruption. On the 13,438-passage human abstract reference the longest
uninterrupted run of numeral-bearing sentences covers a fifth of the passage
at the median; a draft whose run covers half its sentences is in the top
decile of recital.

This detector is the only consumer of :func:`extract_style.latex_to_numeral_text`.
Every other axis reads ``latex_to_plain``, which replaces each math span with
``[math]`` and so measures zero numerals on any real `.tex` file. That is the
right reduction for lexical and sentence-shape statistics and the wrong one
here, which is why the two projections are separate named functions rather
than one function with a flag.

Nothing in this axis is an authorship claim. A high recital run is a writing
finding: the passage has not told the reader which of its numbers matter.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_feedback as feedback  # noqa: E402 because sibling tools are importable only after the sys.path insert above
import deai_reference as reference  # noqa: E402 because sibling tools are importable only after the sys.path insert above
import extract_style as es  # noqa: E402 because sibling tools are importable only after the sys.path insert above

# A numeral is a digit run that is not part of an identifier. Version-like and
# decimal forms count once; a leading sign is part of the value.
RE_NUMERAL = re.compile(r"(?<![A-Za-z0-9_.])[-+]?\d[\d,]*(?:\.\d+)?")
RE_ABSTRACT_ENV = es.RE_ABSTRACT_ENV

MIN_WORDS = 30
MIN_SENTENCES = 3
# Sample floor for calling a bucket's reference usable. Below it the axis is
# degraded: the percentile of a 12-passage reference is not an operating point.
MIN_REFERENCE_N = reference.MIN_REFERENCE_N
BASELINE_FILENAME = "salience_baseline.json"
FEATURES = ("max_recital_run_frac", "recital_frac", "numerals_per_sentence")
ADVISORY_PERCENTILE = 0.90
STRONG_PERCENTILE = 0.95


def salience_features(block: str) -> dict[str, Any] | None:
    """Return the recital-structure features of one passage, or None.

    None means the passage is too short to measure: a two-sentence paragraph
    cannot exhibit or refute a recital run.
    """
    plain = es.latex_to_numeral_text(block)
    sentences = [s for s in es.sentences(plain) if len(es.words(s)) >= 4]
    if len(sentences) < MIN_SENTENCES:
        return None
    if len(es.words(plain)) < MIN_WORDS:
        return None
    counts = [len(RE_NUMERAL.findall(sentence)) for sentence in sentences]
    longest = current = 0
    for count in counts:
        current = current + 1 if count else 0
        longest = max(longest, current)
    n = len(sentences)
    return {
        "n_sentences": n,
        "recital_frac": sum(1 for c in counts if c) / n,
        "numerals_per_sentence": sum(counts) / n,
        "max_recital_run": longest,
        "max_recital_run_frac": longest / n,
    }


load_baseline = reference.baseline_loader(BASELINE_FILENAME)
percentile_of = reference.percentile_of
grid_value = reference.grid_value
_units = reference.units
_quantiles = reference.quantiles
QUANTILE_GRID = reference.QUANTILE_GRID


def resolves_above_gate(ref: dict[str, Any], feature: str) -> bool:
    """Whether the reference can tell an extreme passage from a typical one."""
    return reference.resolves_gate(ref, feature, ADVISORY_PERCENTILE, high=True)


def salience_axis_status(field_profile_dir: Path | None) -> dict[str, Any]:
    baseline = load_baseline(field_profile_dir)
    if baseline is None:
        return feedback.axis_status(
            "L2.salience_hierarchy", "unmeasured",
            reason=f"{BASELINE_FILENAME} is unavailable",
            detector="deai_salience",
        )
    usable = [bucket for bucket, ref in baseline.items()
              if isinstance(ref, dict) and int(ref.get("n", 0)) >= MIN_REFERENCE_N]
    if not usable:
        return feedback.axis_status(
            "L2.salience_hierarchy", "degraded",
            reason=(f"no section bucket reaches the {MIN_REFERENCE_N}-passage "
                    "reference floor; percentiles are rank-only"),
            detector="deai_salience",
        )
    return feedback.axis_status("L2.salience_hierarchy", "measured",
                                detector="deai_salience")


def salience_findings(text: str, field_profile_dir: Path | None,
                      path: str | Path | None = None) -> list[dict[str, Any]]:
    """One finding per over-recital passage, led by its most extreme feature.

    A passage that recites its numbers is one writing problem, so it earns one
    finding. Emitting a separate item per feature would triple the count of a
    single defect and push genuinely distinct passages down the ranking.
    """
    baseline = load_baseline(field_profile_dir)
    if baseline is None:
        return []
    findings: list[dict[str, Any]] = []
    for start, end, bucket, block in _units(text):
        values = salience_features(block)
        if values is None:
            continue
        reference = baseline.get(bucket)
        if not isinstance(reference, dict):
            continue
        reference_n = int(reference.get("n", 0))
        measured = reference_n >= MIN_REFERENCE_N

        percentiles: dict[str, float] = {}
        for feature in FEATURES:
            if not resolves_above_gate(reference, feature):
                continue
            found = percentile_of(reference, feature, float(values[feature]))
            if found is not None:
                percentiles[feature] = found
        if not percentiles:
            continue
        lead = max(percentiles, key=lambda feature: percentiles[feature])
        lead_percentile = percentiles[lead]
        if lead_percentile <= ADVISORY_PERCENTILE:
            continue
        strong = bool(measured and lead_percentile > STRONG_PERCENTILE)
        detail = ", ".join(
            f"{feature} {values[feature]:.2f} (p{percentiles[feature] * 100:.0f})"
            for feature in FEATURES if feature in percentiles)
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2",
            rule=f"salience-recital:{bucket}", scope="paragraph",
            calibration_unit="paragraph",
            line=start, end_line=end, section=bucket, path=path,
            detector="deai_salience",
            measurement_status="measured" if measured else "degraded",
            strength="strong" if strong else "ordinary",
            observed={"lead_feature": lead,
                      "lead_percentile": round(lead_percentile, 4),
                      "features": {feature: round(float(values[feature]), 4)
                                   for feature in FEATURES},
                      "percentiles": {feature: round(value, 4)
                                      for feature, value in percentiles.items()},
                      "max_recital_run": values["max_recital_run"],
                      "sentence_count": values["n_sentences"]},
            reference=feedback.reference_block(
                field_profile_dir, bucket=bucket, n=reference_n,
                advisory_percentile=ADVISORY_PERCENTILE,
                strong_percentile=STRONG_PERCENTILE,
                provenance=BASELINE_FILENAME),
            normalized_distance=lead_percentile - ADVISORY_PERCENTILE,
            confidence={"value": min(1.0, values["n_sentences"] / 8.0),
                        "basis": (f"{values['n_sentences']} sentences against an "
                                  f"n={reference_n} {bucket} reference")},
            message=(
                f"{bucket} passage recites its quantities: {detail}. The longest "
                f"uninterrupted run of numeral-bearing sentences is "
                f"{values['max_recital_run']} of {values['n_sentences']}, against "
                f"an n={reference_n} human {bucket} reference."),
            action=(
                "Rank the quantities instead of reciting them. Keep the numbers "
                "the passage's claim rests on, say what they establish, and let "
                "the section that argues from them carry the rest. Never delete "
                "a number that is the sole support of a claim."),
            evidence=[lead, round(lead_percentile, 6), values["max_recital_run"]],
        ))
    return findings


def calibrate(field_profile_dir: Path) -> dict[str, Any]:
    """Build the per-bucket human reference from the field's own passage banks.

    Calibration and detection share one unit (a passage), so a percentile means
    the same thing on both sides. Mixing a paragraph reference with a
    whole-section measurement would compare a run length against a distribution
    that could not produce it.
    """
    return reference.calibrate(
        field_profile_dir, BASELINE_FILENAME, FEATURES, salience_features,
        reference.passage_banks(field_profile_dir))


def _written(result: dict[str, Any], field_profile_dir: Path) -> str:
    """What `--calibrate` reports: the artifact and each bucket's sample size.

    The per-bucket n is the line worth printing, because a bucket under the
    30-passage floor is the difference between a measured axis and a degraded
    one and there is nowhere else the operator would see it.
    """
    counts = ", ".join(f"{bucket}={ref['n']}" for bucket, ref in sorted(result.items()))
    return f"baseline written: {field_profile_dir / BASELINE_FILENAME} ({counts})"


def main(argv: list[str] | None = None) -> int:
    return cli_common.axis_main(
        __doc__, argv, tool="deai_salience", calibrate=calibrate,
        summary=_written,
        report=lambda text, field_dir, path: feedback.build_report(
            path=path, findings=salience_findings(text, field_dir, path),
            axes=[salience_axis_status(field_dir)]),
        render=feedback.render_text)


if __name__ == "__main__":
    raise SystemExit(main())
