"""One (feature, unit) percentile reference, shared by every per-bucket axis.

Roadmap rank 2 called this "baseline unification into one `(feature, unit)`
object" and recorded it as elegance debt. It stopped being elegance debt when a
second per-bucket axis arrived: `deai_salience` and `deai_discourse` would
otherwise have carried two copies of the quantile grid, the plateau-top
percentile reader, the passage sweep and the calibration loop, and a percentile
would have meant two different things depending on which tool computed it. The
artifact reader had five copies across the suite before this module existed.

The invariant it holds: **calibration and detection share one unit and one
grid.** A reference built from paragraphs and read with a whole-section
measurement compares a value against a distribution that could not have
produced it, and nothing in the output would say so.

It holds no policy. Gate quantiles, feature names, and what a finding means all
belong to the axis; this module only guarantees that two axes asking "what
percentile is this" get the same answer for the same number.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_metrics as metrics  # noqa: E402 -- because the sys.path insert above must run first
import extract_style as es  # noqa: E402 because sibling tools are importable only after the sys.path insert above

# Stored on a 0.01 grid. Several features are ratios of small integers, so their
# reference distributions have wide ties: at a 0.05 grid the whole plateau
# around 0.5 collapses onto one stored point and a passage landing on it reads
# as exactly p90 when its true P(X <= x) is 0.91.
QUANTILE_GRID = tuple(round(0.01 * step, 2) for step in range(101))
# Sample floor for calling a bucket's reference usable. Below it a percentile is
# rank-only: the percentile of a 12-passage reference is not an operating point.
MIN_REFERENCE_N = 30


def quantiles(values: list[float]) -> dict[str, float]:
    """The stored grid for one feature's reference values."""
    ordered = sorted(values)
    if not ordered:
        return {}
    out: dict[str, float] = {}
    for q in QUANTILE_GRID:
        index = min(len(ordered) - 1, int(q * len(ordered)))
        out[str(q)] = round(float(ordered[index]), 6)
    return out


def baseline_loader(filename: str) -> Callable[[Path | None], Any]:
    """A `load_baseline(field_profile_dir)` bound to one artifact name.

    Returns None when the directory is unset, the file is missing, or the JSON
    is unreadable. None is not an error and not an empty result: the caller
    reports the axis `unmeasured`, because a missing calibration is not zero
    findings. Five tools each kept their own copy of exactly this before it had
    one owner, so how an unreadable artifact behaved had five answers and no
    test that they agreed.
    """
    def load(field_profile_dir: Path | None) -> Any:
        if field_profile_dir is None:
            return None
        path = field_profile_dir / filename
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return load


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


def resolves_gate(reference: dict[str, Any], feature: str, gate: float, *,
                  high: bool) -> bool:
    """Whether the reference has spread on the side the axis flags.

    If every reference passage past the gate shares one value, P(X <= x)
    saturates there and a perfectly ordinary passage reads as the most extreme
    one. `high=True` guards an upper-tail axis (salience), `high=False` a
    lower-tail one (cohesion, hedging); the failure is symmetric and so is the
    check, which is why one function serves both rather than two that drift.
    """
    at_gate = grid_value(reference, feature, gate)
    at_edge = grid_value(reference, feature, 1.0 if high else 0.0)
    if at_gate is None or at_edge is None:
        return False
    return at_edge > at_gate if high else at_gate > at_edge


def usable_buckets(baseline: dict[str, Any] | None, feature: str, gate: float, *,
                   high: bool) -> list[str]:
    """Buckets that clear the sample floor AND resolve on the flagged side."""
    if not baseline:
        return []
    return [bucket for bucket, reference in baseline.items()
            if isinstance(reference, dict)
            and int(reference.get("n", 0)) >= MIN_REFERENCE_N
            and resolves_gate(reference, feature, gate, high=high)]


def _abstracts(text: str) -> list[tuple[int, int, str, str]]:
    """The abstract environments, which the section sweep cannot see.

    In AASTeX the abstract sits in the preamble ahead of the first \\section, so
    a section-driven sweep would either miss it or measure it together with the
    title block. Both granularities need it, and both need it excluded from
    whatever the section sweep then reports, so it has one owner.
    """
    found = []
    for match in es.RE_ABSTRACT_ENV.finditer(text):
        start = text[:match.start()].count("\n") + 1
        found.append((start, start + match.group(0).count("\n"), "abstract",
                      match.group(1)))
    return found


def _labelled_sections(text: str):
    """(start, end, bucket) for each section a reference may be keyed on."""
    for start, end, raw_label in metrics.section_line_ranges(text):
        bucket = metrics._bucket_for(raw_label)
        if bucket in {"skip", "unknown"} and raw_label.startswith("("):
            continue
        yield start, end, bucket


def without_headings(block: str) -> str:
    """The block with every heading command blanked, line count preserved.

    The banks hold the prose UNDER a heading and never its words, so a heading
    left in a manuscript unit is measured on one side of every percentile only,
    and with no terminator of its own it fuses with the first sentence below it
    (`Validation Rescored catalogs ...`). Blanking rather than deleting keeps
    every reported line number pointing where it did.
    """
    return es.RE_HEADING_COMMAND.sub(lambda m: " " * len(m.group(0)), block)


def sections(text: str) -> list[tuple[int, int, str, str]]:
    """(start_line, end_line, bucket, block) for every SECTION-sized unit.

    The coarser sibling of :func:`units`. A feature whose paragraph-scale
    distribution has no lower tail can still have one here -- more than a tenth
    of real human paragraphs contain no hedge at all, while a whole method
    section that hedges nowhere is genuinely unusual. Which granularity an axis
    calibrates and detects at is the axis's choice; mixing the two is the one
    thing this module exists to prevent.
    """
    found = _abstracts(text)
    consumed = {line for start, end, _, _ in found
                for line in range(start, end + 1)}
    lines = text.splitlines()
    for start, end, bucket in _labelled_sections(text):
        body = without_headings("\n".join(
            line for number, line in enumerate(lines[start - 1:end], start)
            if number not in consumed))
        if body.strip():
            found.append((start, end, bucket, body))
    return found


def units(text: str) -> list[tuple[int, int, str, str]]:
    """(start_line, end_line, bucket, block) for every PARAGRAPH-sized unit."""
    found = _abstracts(text)
    consumed = {line for start, end, _, _ in found
                for line in range(start, end + 1)}

    lines = text.splitlines()
    for section_start, section_end, bucket in _labelled_sections(text):
        segment = without_headings("\n".join(lines[section_start - 1:section_end]))
        for start, end, block in metrics.paragraph_line_ranges(segment, section_start):
            if start in consumed or not block.strip():
                continue
            found.append((start, end, bucket, block))
    return found


def passage_banks(field_profile_dir: Path) -> list[tuple[str, Path, str | None]]:
    """(label, path, forced_bucket) for every bank of human passages in a field.

    Where the field's human prose lives is a property of the profile layout, not
    of any one axis, so both per-bucket axes read the same list: an axis that
    quietly calibrated against a smaller set of papers than its neighbour would
    make two percentiles incomparable for no stated reason. The abstract bank
    carries whole abstracts and has no meaningful `section` key of its own,
    which is what the forced bucket is for.
    """
    return [
        ("exemplar_paragraphs", field_profile_dir / "exemplar_paragraphs.jsonl", None),
        ("human_abstracts_extra", field_profile_dir / "human_abstracts_extra.jsonl",
         "abstract"),
    ]


def _bank_records(sources: Iterable[tuple[str, Path, str | None]]):
    """(label, bucket, text) for every readable record in every bank present.

    `sources` is (label, path, forced_bucket): a bank whose records all belong
    to one bucket names it, because an abstract-only bank has no `section` key
    to read.
    """
    for label, bank, forced_bucket in sources:
        if not bank.exists():
            continue
        with bank.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield (label, forced_bucket or record.get("section") or "unknown",
                       record.get("text", ""), record.get("source"))


def _section_records(sources: Iterable[tuple[str, Path, str | None]]):
    """The same records regrouped so one whole section is one unit.

    The banks store paragraphs, so a section-unit reference has to be assembled
    from them: every paragraph sharing a source document and a bucket is one
    section. A record with no `source` cannot be attributed to a document and is
    dropped rather than pooled into a fictitious one -- pooling would join
    paragraphs from unrelated papers into a section no author ever wrote.
    """
    grouped: dict[tuple[str, str], list[str]] = {}
    labels: dict[tuple[str, str], str] = {}
    for label, bucket, text, source in _bank_records(sources):
        if not source:
            continue
        key = (source, bucket)
        grouped.setdefault(key, []).append(text)
        labels[key] = label
    for (_source, bucket), blocks in grouped.items():
        yield labels[(_source, bucket)], bucket, "\n\n".join(blocks), _source


def calibrate(field_profile_dir: Path, filename: str, features: Iterable[str],
              extract: Callable[[str], dict[str, Any] | None],
              sources: Iterable[tuple[str, Path, str | None]], *,
              unit: str = "paragraph") -> dict[str, Any]:
    """Build a per-bucket reference at one granularity from the field's banks.

    `unit` is written into every bucket of the artifact, because it is the fact
    a later reader most needs and the one nothing else records: two references
    built from the same corpus at different granularities are both valid and
    are not comparable, and a detector reading the wrong one would compare a
    value against a distribution that could not have produced it.

    A record `extract` cannot measure is skipped rather than contributing a
    zero, which would pull every quantile toward a value no passage ever had.
    """
    names = tuple(features)
    stream = (_section_records(sources) if unit == "section"
              else _bank_records(sources))
    collected: dict[str, dict[str, list[float]]] = {}
    contributing: dict[str, list[str]] = {}
    for label, bucket, text, _source in stream:
        values = extract(text)
        if values is None:
            continue
        slot = collected.setdefault(bucket, {name: [] for name in names})
        for name in names:
            slot[name].append(float(values[name]))
        if label not in contributing.setdefault(bucket, []):
            contributing[bucket].append(label)

    output: dict[str, Any] = {}
    for bucket, gathered in collected.items():
        output[bucket] = {
            "n": len(gathered[names[0]]),
            "unit": unit,
            "sources": contributing.get(bucket, []),
            "percentiles": {name: quantiles(values)
                            for name, values in gathered.items()},
        }
    (field_profile_dir / filename).write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    return output
