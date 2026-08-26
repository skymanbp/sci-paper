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

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_feedback as feedback  # noqa: E402 because sibling tools are importable only after the sys.path insert above
import deai_metrics as metrics  # noqa: E402 because sibling tools are importable only after the sys.path insert above
import extract_style as es  # noqa: E402 because sibling tools are importable only after the sys.path insert above

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

# A numeral is a digit run that is not part of an identifier. Version-like and
# decimal forms count once; a leading sign is part of the value.
RE_NUMERAL = re.compile(r"(?<![A-Za-z0-9_.])[-+]?\d[\d,]*(?:\.\d+)?")
RE_ABSTRACT_ENV = es.RE_ABSTRACT_ENV

MIN_WORDS = 30
MIN_SENTENCES = 3
# Sample floor for calling a bucket's reference usable. Below it the axis is
# degraded: the percentile of a 12-passage reference is not an operating point.
MIN_REFERENCE_N = 30
BASELINE_FILENAME = "salience_baseline.json"
FEATURES = ("max_recital_run_frac", "recital_frac", "numerals_per_sentence")
# Stored on a 0.01 grid. Two of the three features are ratios of small
# integers, so their reference distributions have wide ties: at a 0.05 grid the
# whole plateau around 0.5 collapses onto one stored point and a passage
# landing on it reads as exactly p90 when its true P(X <= x) is 0.91.
QUANTILE_GRID = tuple(round(0.01 * step, 2) for step in range(101))
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


def load_baseline(field_profile_dir: Path | None) -> dict[str, Any] | None:
    if field_profile_dir is None:
        return None
    path = field_profile_dir / BASELINE_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


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


def percentile_of(reference: dict[str, Any], feature: str,
                  value: float) -> float | None:
    """Return P(X <= value) against the stored human quantile grid.

    The reference distributions are tie-heavy, so the quantile that matters is
    the TOP of the plateau a value lands on, not its first occurrence. Reading
    the plateau's lower edge would report a passage as merely typical whenever
    its value happens to be a common one.
    """
    grid = (reference.get("percentiles") or {}).get(feature)
    if not grid:
        return None
    points = sorted((float(q), float(v)) for q, v in grid.items())
    below = [(q, v) for q, v in points if v <= value]
    if not below:
        return points[0][0]
    above = [(q, v) for q, v in points if v > value]
    if not above:
        return 1.0
    q_low, v_low = below[-1]
    q_high, v_high = above[0]
    if v_high == v_low:
        return q_high
    span = (value - v_low) / (v_high - v_low)
    return q_low + span * (q_high - q_low)


def grid_value(reference: dict[str, Any], feature: str,
               quantile: float) -> float | None:
    """The stored reference value at (the grid point nearest) `quantile`."""
    grid = (reference.get("percentiles") or {}).get(feature)
    if not grid:
        return None
    key = min(grid, key=lambda stored: abs(float(stored) - quantile))
    return float(grid[key])


def resolves_above_gate(reference: dict[str, Any], feature: str) -> bool:
    """Whether the reference can tell an extreme passage from a typical one.

    If every reference passage above the advisory gate shares one value, then
    P(X <= x) reaches 1.0 at that value and a perfectly ordinary passage reads
    as the 100th percentile. A reference with no spread in its upper tail
    cannot support a finding, so the feature abstains rather than inventing
    one.
    """
    gate = grid_value(reference, feature, ADVISORY_PERCENTILE)
    top = grid_value(reference, feature, 1.0)
    return gate is not None and top is not None and top > gate


def _units(text: str) -> list[tuple[int, int, str, str]]:
    """Yield (start_line, end_line, bucket, block) for every measurable unit.

    The abstract is pulled out by environment rather than left to the section
    sweep, because in AASTeX it sits in the preamble ahead of the first
    \\section and would otherwise be measured together with the title block.
    """
    units: list[tuple[int, int, str, str]] = []
    consumed: set[int] = set()
    for match in RE_ABSTRACT_ENV.finditer(text):
        start = text[:match.start()].count("\n") + 1
        end = start + match.group(0).count("\n")
        units.append((start, end, "abstract", match.group(1)))
        consumed.update(range(start, end + 1))

    lines = text.splitlines()
    for section_start, section_end, raw_label in metrics.section_line_ranges(text):
        bucket = metrics._bucket_for(raw_label)
        if bucket in {"skip", "unknown"} and raw_label.startswith("("):
            continue
        segment = "\n".join(lines[section_start - 1:section_end])
        for start, end, block in metrics.paragraph_line_ranges(segment, section_start):
            if start in consumed:
                continue
            units.append((start, end, bucket, block))
    return units


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
            reference={"field_profile": str(field_profile_dir)
                       if field_profile_dir else None,
                       "section_bucket": bucket, "n": reference_n,
                       "advisory_percentile": ADVISORY_PERCENTILE,
                       "strong_percentile": STRONG_PERCENTILE,
                       "provenance": BASELINE_FILENAME},
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


def _quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}
    out: dict[str, float] = {}
    for q in QUANTILE_GRID:
        index = min(len(ordered) - 1, int(q * len(ordered)))
        out[str(q)] = round(float(ordered[index]), 6)
    return out


def _calibration_sources(field_profile_dir: Path) -> list[tuple[str, Path, str | None]]:
    """(label, path, forced_bucket) for every bank that can feed the baseline."""
    return [
        ("exemplar_paragraphs", field_profile_dir / "exemplar_paragraphs.jsonl", None),
        ("human_abstracts_extra", field_profile_dir / "human_abstracts_extra.jsonl",
         "abstract"),
    ]


def calibrate(field_profile_dir: Path) -> dict[str, Any]:
    """Build the per-bucket human reference from the field's own passage banks.

    Calibration and detection share one unit (a passage), so a percentile means
    the same thing on both sides. Mixing a paragraph reference with a
    whole-section measurement would compare a run length against a distribution
    that could not produce it.
    """
    collected: dict[str, dict[str, list[float]]] = {}
    sources: dict[str, list[str]] = {}
    for label, bank, forced_bucket in _calibration_sources(field_profile_dir):
        if not bank.exists():
            continue
        with bank.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                values = salience_features(record.get("text", ""))
                if values is None:
                    continue
                bucket = forced_bucket or record.get("section") or "unknown"
                slot = collected.setdefault(bucket, {feature: [] for feature in FEATURES})
                for feature in FEATURES:
                    slot[feature].append(float(values[feature]))
                if label not in sources.setdefault(bucket, []):
                    sources[bucket].append(label)

    output: dict[str, Any] = {}
    for bucket, features in collected.items():
        n = len(features[FEATURES[0]])
        output[bucket] = {
            "n": n,
            "sources": sources.get(bucket, []),
            "percentiles": {feature: _quantiles(values)
                            for feature, values in features.items()},
        }
    (field_profile_dir / BASELINE_FILENAME).write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__)
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--calibrate", action="store_true")
    args = parser.parse_args(argv)
    field_dir = args.profile_root / args.field if args.field else None
    if args.calibrate:
        if field_dir is None:
            print("[deai_salience] --calibrate needs --field", file=sys.stderr)
            return 2
        result = calibrate(field_dir)
        summary = ", ".join(f"{bucket}={ref['n']}" for bucket, ref in sorted(result.items()))
        print(f"[deai_salience] baseline written: "
              f"{field_dir / BASELINE_FILENAME} ({summary})")
        return 0
    if not args.file or not args.file.exists():
        print(f"[deai_salience] file not found: {args.file}", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    report = feedback.build_report(
        path=args.file,
        findings=salience_findings(text, field_dir, args.file),
        axes=[salience_axis_status(field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
