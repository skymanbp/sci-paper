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
import re
import sys
from collections import Counter
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
    """The stored grid for one feature's reference values.

    Nearest rank: the point stored at q is the ceil(q * n)-th smallest value,
    the first order statistic with P(X <= x) >= q; q = 0 stores the minimum
    and q = 1 the maximum. The rank is computed in integers (a grid point is
    a whole hundredth) because 0.9 * 100 is 90.00000000000001 in floating
    point, and a ceiling taken there reads one rank high again.

    Until 2026-09-27 the index was floor(q * n), one order statistic further
    up: the stored p90 of 100 values was the 91st smallest (P(X <= x) = 0.91),
    and at the 30-unit floor the stored p10 and p90 sat at P = 0.133 and
    0.933. Every artifact calibrated before that date, and every held-out
    rate measured against one, was read one order statistic high -- widest
    at the smallest buckets, which is where the floor matters. Recalibrate
    to move the grid; the artifacts do not move on their own.
    """
    ordered = sorted(values)
    n = len(ordered)
    if not n:
        return {}
    out: dict[str, float] = {}
    for step, q in enumerate(QUANTILE_GRID):
        index = min(n - 1, max(0, (step * n + 99) // 100 - 1))
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


def unit_matches(reference: dict[str, Any], unit: str) -> bool:
    """Whether one bucket's artifact was built at the unit the caller measures."""
    return reference.get("unit") == unit


def foreign_units(baseline: dict[str, Any] | None, unit: str,
                  buckets: Iterable[str] | None = None) -> dict[str, str]:
    """bucket -> the unit its artifact records, for every bucket NOT built at `unit`.

    `calibrate` has written `unit` into every bucket since the module existed
    and nothing read it back: a mislabelled or stale artifact -- a hedging
    reference rebuilt at paragraph unit, say -- was read against section
    measurements without a word in the output. The invariant this module is
    for was a declaration until the reader checked it. An artifact with no
    `unit` key predates the key and is reported as `unrecorded`. `buckets`,
    when given, limits the answer to those buckets.
    """
    scope = None if buckets is None else set(buckets)
    return {bucket: str(reference.get("unit") or "unrecorded")
            for bucket, reference in (baseline or {}).items()
            if isinstance(reference, dict) and not unit_matches(reference, unit)
            and (scope is None or bucket in scope)}


def unit_reason(baseline: dict[str, Any] | None, unit: str,
                spans: Iterable[tuple[int, int, str, Any]] | None = None,
                allowed: Iterable[str] | None = None) -> str | None:
    """The status text for buckets an axis refuses because of their unit, or None.

    Only buckets the axis would read count: those in `allowed` (None: every
    bucket) and, given the document's `spans` (as `unbucketed_reason` takes
    them), those the document reaches. Counted over the whole profile, one
    stale `method` bucket marked an abstract-only document `degraded` and sent
    its reader to recalibrate, though the axis had read every unit it held.
    """
    scope = set(baseline or {}) if allowed is None else set(allowed)
    if spans is not None:
        scope &= {bucket for _start, _end, bucket, _block in spans}
    foreign = foreign_units(baseline, unit, scope)
    if not foreign:
        return None
    listed = ", ".join(f"{bucket} ({recorded})" for bucket, recorded in sorted(foreign.items()))
    return (f"bucket(s) recorded at another unit are not read: {listed}; this axis "
            f"measures {unit} units, so recalibrate")


def usable_buckets(baseline: dict[str, Any] | None, feature: str, gate: float, *,
                   high: bool, unit: str) -> list[str]:
    """Buckets built at `unit` that clear the sample floor AND resolve on the flagged side."""
    if not baseline:
        return []
    return [bucket for bucket, reference in baseline.items()
            if isinstance(reference, dict)
            and unit_matches(reference, unit)
            and int(reference.get("n", 0)) >= MIN_REFERENCE_N
            and resolves_gate(reference, feature, gate, high=high)]


def unbucketed_reason(spans: Iterable[tuple[int, int, str, Any]], unit: str) -> str | None:
    """Why part of a document went unmeasured: its units in the `unknown` bucket.

    A document with no heading, or with headings that name a topic rather than
    a role (`\\section{Weak lensing}`), lands in `unknown`, and no bank holds
    that bucket, so every per-bucket axis skips such a unit. Until 2026-09-27
    an axis status was computed from the profile alone and reported `measured`
    with zero findings on a document it had not read (CLAUDE.md rule 3). Each
    status function now takes the text and reports this count, so "nothing
    found" and "nothing measured" stay two different sentences.
    """
    spans = list(spans)
    unknown = sum(1 for _start, _end, bucket, _block in spans
                  if bucket == es.DEFAULT_SECTION_BUCKET)
    if not unknown:
        return None
    return (f"{unknown} of {len(spans)} {unit} units carry no calibrated bucket "
            "(no section heading, or one naming a topic rather than a role) "
            "and were not measured")


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
    """(start, end, raw_label, bucket) for each section a reference may be keyed on.

    The preamble is title-block markup, never prose; everything else is a unit,
    including a document with no heading at all (`(document)`, bucket
    `unknown`), which an earlier reading dropped so that a sectionless file
    produced no residue or removal-map findings and no message saying so.
    """
    for start, end, raw_label, bucket in metrics.section_units(text):
        if bucket == metrics.PREAMBLE_BUCKET:
            continue
        yield start, end, raw_label, bucket


def without_headings(block: str) -> str:
    """The block with every heading and float blanked, line count preserved.

    The banks hold the prose UNDER a heading and never its words, so a heading
    left in a manuscript unit is measured on one side of every percentile only,
    and with no terminator of its own it fuses with the first sentence below it
    (`Validation Rescored catalogs ...`). A float is blanked whole for the same
    reason, BEFORE the paragraph split: the corpus side projects a passage in
    one pass, and a `\\caption` separated from its `\\begin{figure}` by a blank
    line was becoming a paragraph of its own here. Blanking rather than
    deleting keeps every reported line number pointing where it did.
    """
    return es.blank_preserving(block, es.RE_HEADING_COMMAND, es.RE_TEX_ENV_FIGURE_TABLE)


def sections(text: str) -> list[tuple[int, int, str, str]]:
    """(start_line, end_line, bucket, block): one SECTION-sized unit per bucket.

    The coarser sibling of :func:`units`. A feature whose paragraph-scale
    distribution has no lower tail can still have one here -- more than a tenth
    of real human paragraphs contain no hedge at all, while a whole method
    section that hedges nowhere is genuinely unusual. Which granularity an axis
    calibrates and detects at is the axis's choice; mixing the two is the one
    thing this module exists to prevent.

    One unit per BUCKET, not per heading. The reference side pools every
    paragraph a paper holds in a bucket into one section (`_section_records`),
    because that is how the corpus splitter cuts a paper -- it keys a paper's
    text by bucket -- so a manuscript's four Methods subsections are one unit
    here as well. Read per heading span until 2026-09-27, a 150-word
    subsection was compared with references pooled over whole papers: the
    mixing of granularities this module exists to prevent, on the side where
    nothing recorded it. The span runs from the bucket's first line to its
    last, and the block joins its spans in document order.
    """
    lines = text.splitlines()
    spans: dict[str, list[tuple[int, int, str]]] = {}
    consumed: set[int] = set()
    for start, end, bucket, body in _abstracts(text):
        spans.setdefault(bucket, []).append((start, end, body))
        consumed.update(range(start, end + 1))
    for start, end, _label, bucket in _labelled_sections(text):
        body = without_headings("\n".join(
            line for number, line in enumerate(lines[start - 1:end], start)
            if number not in consumed))
        spans.setdefault(bucket, []).append((start, end, body))
    found = []
    for bucket, parts in spans.items():
        block = "\n\n".join(body for _start, _end, body in parts)
        if has_prose(block):
            found.append((parts[0][0], parts[-1][1], bucket, block))
    return sorted(found)


def has_prose(block: str) -> bool:
    """Whether a block projects to anything at all: prose, or a placeholder
    standing for math, a float or a citation.

    Blanking keeps a heading's line, and the `\\label{}` that shared it stays
    behind with a run of spaces; a `% SCOPE:` comment block never had prose.
    The corpus side drops both before it splits paragraphs, so a unit made of
    them here was measured against a reference that holds none: GPT-2 read
    forty-eight spaces as more tokens than the UID minimum and scored four of
    a manuscript's heading lines as paragraphs of near-zero surprisal variance.
    A display-equation-only paragraph projects to `[MATH]` and stays a unit
    here, although the corpus side writes no row for it (the bank writer drops
    a placeholder-only paragraph and anything under 30 words): the axes with
    no reference -- residue, the removal map -- still see it and every later
    unit keeps its line number, while each calibrated axis's extractor returns
    None on it (too few sentences or words) and measures nothing.
    """
    return bool(es.latex_to_plain(block).strip())


def paragraphs(text: str) -> list[tuple[int, int, str, str, str]]:
    """(start_line, end_line, raw_label, bucket, block) for every PARAGRAPH unit.

    The one paragraph sweep of the manuscript side: abstracts first, then every
    section's blank-line paragraphs with headings and floats blanked. Every
    per-paragraph axis reads this rather than cutting the document itself, so a
    paragraph boundary, a bucket and a line number mean the same thing in every
    report. `units` is the same list without the raw section title.
    """
    found = [(start, end, "abstract", bucket, block)
             for start, end, bucket, block in _abstracts(text)]
    consumed = {line for start, end, _, _, _ in found
                for line in range(start, end + 1)}
    lines = text.splitlines()
    for section_start, section_end, raw_label, bucket in _labelled_sections(text):
        segment = without_headings("\n".join(lines[section_start - 1:section_end]))
        for start, end, block in metrics.paragraph_line_ranges(segment, section_start):
            if start in consumed or not has_prose(block):
                continue
            found.append((start, end, raw_label, bucket, block))
    return found


def units(text: str) -> list[tuple[int, int, str, str]]:
    """(start_line, end_line, bucket, block) for every PARAGRAPH-sized unit."""
    return [(start, end, bucket, block)
            for start, end, _label, bucket, block in paragraphs(text)]


RE_PLACEHOLDER_TOKEN = re.compile(es.PLACEHOLDER_SHAPE)  # the projection's own token shape
# What may sit between two consecutive words of one projected sentence in the
# raw block: anything but a letter (space, line break, punctuation, digit), a
# command with its bracketed and braced arguments (a citation, a reference),
# a bare command name, or an inline math span. Never prose: a gap that could
# cross words matched `The map` from an earlier sentence's `The`.
_GAP = (r"(?:[^A-Za-z]|\\[A-Za-z]+\*?(?:\[[^\]\n]*\])?\{[^{}]*\}"
        r"|\\[A-Za-z]+\*?|\$[^$\n]*\$){0,60}?")


def _word_run(words: list[str]) -> str:
    """A pattern matching `words` in order with only markup between them."""
    return _GAP.join(rf"\b{re.escape(word)}\b" for word in words)


def sentence_lines(block: str, start: int, sentence: str) -> tuple[int, int]:
    """(first, last) source line of one projected sentence inside its unit.

    A sentence-scope finding pointed at its PARAGRAPH's line range, so a reader
    following `L 41` to a sentence on line 44 met the wrong one. The projected
    sentence is looked up in the raw block by its first two words, then its
    last three from that point (a command, a citation, a math span or a line
    break may sit between any two, but no prose), and the lines are counted
    from the unit's first line. A sentence whose head cannot be found keeps
    the unit's whole range, and one whose tail cannot be found keeps the
    unit's last line, so a finding is never anchored on a guess.
    """
    words = es.words(RE_PLACEHOLDER_TOKEN.sub(" ", sentence))
    end = start + block.count("\n")
    if not words:
        return start, end
    head = re.search(_word_run(words[:2]), block, re.IGNORECASE)
    if head is None:
        return start, end
    first = start + block[:head.start()].count("\n")
    tail = re.search(_word_run(words[-3:]), block[head.start():], re.IGNORECASE)
    if tail is None:
        return first, end
    return first, first + block[head.start():head.start() + tail.end()].count("\n")


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


# Banks whose `text` is already the `[math]` projection. A record there
# without the projection an axis asks for can only be read on `text`, which
# is a different projection of the same paragraph; the abstract bank stores
# LaTeX source instead, which every key projects the same way.
PROJECTED_BANKS = frozenset({"exemplar_paragraphs"})


def _bank_records(sources: Iterable[tuple[str, Path, str | None]], *,
                  text_key: str = "text", fallbacks: Counter[str] | None = None):
    """(label, bucket, text, source) for every readable record in every bank present.

    `sources` is (label, path, forced_bucket): a bank whose records all belong
    to one bucket names it, because an abstract-only bank has no `section` key
    to read. `source` is the record's own document id, or None.

    `text_key` names the projection the axis measures. The exemplar bank
    stores each paragraph twice, as `text` (math spans reduced to `[math]`)
    and as `numeral_text` (math numerals kept); an axis that counts numerals
    on the manuscript must calibrate on the second, or its reference holds
    fewer numerals than any manuscript it reads. A record without the key
    falls back to `text`: the abstract bank stores its LaTeX source, which
    the axis projects itself. In a bank of `PROJECTED_BANKS` that fallback
    mixes projections, and `fallbacks`, when given, counts such records per
    bucket so the artifact records the mix and the axis can warn about it
    instead of calibrating on it silently.
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
                bucket = forced_bucket or record.get("section") or "unknown"
                if (fallbacks is not None and label in PROJECTED_BANKS
                        and text_key != "text" and not record.get(text_key)):
                    fallbacks[bucket] += 1
                yield (label, bucket, record.get(text_key) or record.get("text", ""),
                       record.get("source"))


def _section_records(sources: Iterable[tuple[str, Path, str | None]], *,
                     text_key: str = "text", fallbacks: Counter[str] | None = None):
    """(label, bucket, text, source): the same records regrouped, one section each.

    The banks store paragraphs, so a section-unit reference has to be assembled
    from them: every paragraph sharing a source document and a bucket is one
    section, its paragraphs joined by blank lines. A record with no `source`
    cannot be attributed to a document and is dropped rather than pooled into
    a fictitious one -- pooling would join paragraphs from unrelated papers
    into a section no author ever wrote.
    """
    grouped: dict[tuple[str, str], list[str]] = {}
    labels: dict[tuple[str, str], str] = {}
    for label, bucket, text, source in _bank_records(sources, text_key=text_key,
                                                     fallbacks=fallbacks):
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
              unit: str = "paragraph", text_key: str = "text") -> dict[str, Any] | None:
    """Build a per-bucket reference at one granularity from the field's banks.

    `unit` is written into every bucket of the artifact, because it is the fact
    a later reader most needs: two references built from the same corpus at
    different granularities are both valid and are not comparable, and a
    detector reading the wrong one would compare a value against a
    distribution that could not have produced it. `usable_buckets` reads it
    back and refuses a bucket built at any other unit.

    `text_key` is the same invariant on the other axis: the reference must be
    built from the projection the detector measures (see `_bank_records`).
    Each bucket records the key it was read on and `text_fallback_rows`, the
    records of a projected bank that lacked it and were read on `text`.

    A record `extract` cannot measure is skipped rather than contributing a
    zero, which would pull every quantile toward a value no passage ever had.
    None when no record contributed at all: nothing is written, because an
    empty artifact reported as calibrated is a missing calibration wearing a
    file name, and `cli_common.axis_main` turns None into exit 2.
    """
    names = tuple(features)
    fallbacks: Counter[str] = Counter()
    stream = (_section_records(sources, text_key=text_key, fallbacks=fallbacks)
              if unit == "section"
              else _bank_records(sources, text_key=text_key, fallbacks=fallbacks))
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

    if not collected:
        return None
    output: dict[str, Any] = {}
    for bucket, gathered in collected.items():
        output[bucket] = {
            "n": len(gathered[names[0]]),
            "unit": unit,
            "text_key": text_key,
            "text_fallback_rows": fallbacks.get(bucket, 0),
            "sources": contributing.get(bucket, []),
            "percentiles": {name: quantiles(values)
                            for name, values in gathered.items()},
        }
    (field_profile_dir / filename).write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    return output
