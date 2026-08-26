"""Model-free information-distribution feedback for scientific prose (L1).

The structured API is :func:`distribution_findings`. The legacy
:func:`distribution_hits` adapter remains for callers that consume
``(line, rule, message)`` tuples. Findings are advisory; the standalone CLI
returns success when measurement completes even when feedback is present.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_feedback as feedback  # noqa: E402  sibling tool import after path setup
import extract_style as es  # noqa: E402  canonical tokenizer import after path setup

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
RE_SECTION_HEADER = re.compile(
    r"\\(section|subsection|chapter)\*?\{([^}]+)\}", re.IGNORECASE
)

CONNECTIVE_OPENERS = frozenset({
    "furthermore", "moreover", "additionally", "however", "therefore",
    "thus", "hence", "consequently", "nevertheless", "nonetheless",
    "notably", "importantly", "interestingly", "crucially", "indeed",
    "similarly", "likewise", "conversely", "meanwhile", "subsequently",
    "accordingly", "besides",
})

# Compatibility defaults used only when a profile has no explicit
# deai_policy.json. Such findings are marked degraded and never strong.
DEFAULT_BURSTINESS_RATIO = 0.60
DEFAULT_SIGNPOST_FRAC = 0.20
MIN_SENTENCES = 5
MIN_PARAGRAPHS = 3


def load_reference(field_profile_dir: Path | None) -> dict[str, Any] | None:
    if field_profile_dir is None:
        return None
    stats_path = field_profile_dir / "sentence_stats.json"
    if not stats_path.exists():
        return None
    try:
        sent = json.loads(stats_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    transition_path = field_profile_dir / "transition_inventory.json"
    trans: dict[str, Any] = {}
    if transition_path.exists():
        try:
            trans = json.loads(transition_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            trans = {}
    cv: dict[str, float] = {}
    for bucket, values in sent.items():
        if bucket == "unknown":
            continue
        mean = values.get("mean", 0)
        stdev = values.get("stdev", 0)
        if mean > 0:
            cv[bucket] = stdev / mean
    pooled_cv = statistics.median(cv.values()) if cv else 0.0
    # The reference rate must be computed over the SAME opener set the draft is
    # measured against (CONNECTIVE_OPENERS). The profile's own
    # `blacklist_present_in_corpus` is keyed to extract_style's curated
    # PARAGRAPH_INITIAL_LLM_OPENERS -- a different, smaller set whose multi-word
    # entries can never match a single paragraph-initial word -- so using it
    # printed a reference rate roughly seven times below the one the observed
    # fraction is comparable with. A profile predating
    # `paragraph_initial_counts` cannot supply a comparable rate at all, so the
    # reference is reported as None rather than as an incomparable number.
    n_paragraphs = trans.get("n_paragraphs", 0)
    counts = trans.get("paragraph_initial_counts")
    if counts and n_paragraphs:
        connective_paragraphs = sum(
            count for word, count in counts.items()
            if word.lower() in CONNECTIVE_OPENERS)
        corpus_signpost = connective_paragraphs / n_paragraphs
    else:
        corpus_signpost = None
    return {
        "cv": cv,
        "pooled_cv": pooled_cv,
        "corpus_signpost": corpus_signpost,
        "assets": [str(stats_path), str(transition_path)],
    }


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
    return data.get("distribution", data)


def section_line_ranges(text: str) -> list[tuple[int, int, str]]:
    """Return section ranges with one-based inclusive line numbers."""
    lines = text.splitlines()
    if not lines:
        return []
    headers: list[tuple[int, str]] = []
    for line_no, line in enumerate(lines, start=1):
        match = RE_SECTION_HEADER.search(line)
        if match:
            headers.append((line_no, match.group(2).strip()))
    if not headers:
        return [(1, len(lines), "(document)")]
    ranges: list[tuple[int, int, str]] = []
    if headers[0][0] > 1:
        ranges.append((1, headers[0][0] - 1, "(preamble)"))
    for index, (start, name) in enumerate(headers):
        end = headers[index + 1][0] - 1 if index + 1 < len(headers) else len(lines)
        ranges.append((start, end, name))
    return ranges


def paragraph_line_ranges(text: str, start_line: int = 1
                          ) -> list[tuple[int, int, str]]:
    """Return blank-line paragraph ranges with one-based inclusive lines."""
    lines = text.splitlines()
    ranges: list[tuple[int, int, str]] = []
    buffer: list[str] = []
    paragraph_start = start_line
    for offset, line in enumerate(lines):
        line_no = start_line + offset
        if line.strip():
            if not buffer:
                paragraph_start = line_no
            buffer.append(line)
        elif buffer:
            ranges.append((paragraph_start, line_no - 1, "\n".join(buffer)))
            buffer = []
    if buffer:
        ranges.append((paragraph_start, start_line + len(lines) - 1,
                       "\n".join(buffer)))
    return ranges


def _bucket_for(raw_label: str) -> str:
    # classify_section itself never raises on a str; the guard covers a
    # non-string label from a malformed \section capture upstream.
    try:
        return es.classify_section(raw_label)
    except (AttributeError, TypeError):
        return "unknown"


def _sentence_lengths(plain: str) -> list[int]:
    return [len(es.words(sentence)) for sentence in es.sentences(plain)
            if es.words(sentence)]


def distribution_axis_status(field_profile_dir: Path | None) -> dict[str, Any]:
    reference = load_reference(field_profile_dir)
    if reference is None:
        return feedback.axis_status(
            "L1.distribution", "unmeasured",
            reason="sentence_stats.json reference is unavailable",
            detector="deai_metrics",
        )
    if load_policy(field_profile_dir) is None:
        return feedback.axis_status(
            "L1.distribution", "degraded",
            reason="using documented compatibility heuristics; deai_policy.json is unavailable",
            detector="deai_metrics",
        )
    return feedback.axis_status("L1.distribution", "measured",
                                detector="deai_metrics")


def distribution_findings(text: str, field_profile_dir: Path | None,
                          path: str | Path | None = None
                          ) -> list[dict[str, Any]]:
    reference = load_reference(field_profile_dir)
    if reference is None:
        return []
    policy = load_policy(field_profile_dir)
    measured = policy is not None
    burstiness_ratio = float((policy or {}).get(
        "burstiness_ratio", DEFAULT_BURSTINESS_RATIO))
    signpost_frac = float((policy or {}).get(
        "signpost_fraction", DEFAULT_SIGNPOST_FRAC))
    status = "measured" if measured else "degraded"
    findings: list[dict[str, Any]] = []
    lines = text.splitlines()

    for start, end, raw_label in section_line_ranges(text):
        segment = "\n".join(lines[start - 1:end])
        plain = es.latex_to_plain(segment)
        bucket = _bucket_for(raw_label)
        ref_cv = reference["cv"].get(bucket, reference["pooled_cv"])

        lengths = _sentence_lengths(plain)
        if len(lengths) >= MIN_SENTENCES and ref_cv > 0:
            mean = statistics.mean(lengths)
            draft_cv = statistics.pstdev(lengths) / mean if mean else 0.0
            ratio = draft_cv / ref_cv
            if ratio < burstiness_ratio:
                findings.append(feedback.make_finding(
                    kind="advisory", layer="L1", rule=f"burstiness-low:{bucket}",
                    scope="section", calibration_unit="section",
                    line=start, end_line=end, section=raw_label,
                    path=path, detector="deai_metrics", measurement_status=status,
                    strength="strong" if measured else "ordinary",
                    strong_advisory=measured,
                    observed={"sentence_length_cv": draft_cv,
                              "sentence_count": len(lengths), "ratio": ratio},
                    reference={"field_profile": str(field_profile_dir),
                               "section_bucket": bucket,
                               "sentence_length_cv": ref_cv,
                               "operating_point_ratio": burstiness_ratio,
                               "provenance": reference["assets"]},
                    normalized_distance=burstiness_ratio - ratio,
                    confidence={"value": min(1.0, len(lengths) / 20.0),
                                "basis": f"{len(lengths)} sentences"},
                    message=(f"Section {raw_label!r} has sentence-length CV "
                             f"{draft_cv:.2f} versus reference {ref_cv:.2f} "
                             f"(ratio {ratio:.2f})."),
                    action="Vary sentence length where the argument permits; do not add arbitrary irregularity.",
                    evidence=[round(draft_cv, 6), round(ref_cv, 6), len(lengths)],
                ))

        openers = es.paragraph_initial_words(plain)
        if len(openers) >= MIN_PARAGRAPHS:
            n_connective = sum(
                1 for word in openers if word.lower() in CONNECTIVE_OPENERS)
            fraction = n_connective / len(openers)
            if fraction > signpost_frac:
                findings.append(feedback.make_finding(
                    kind="advisory", layer="L1",
                    rule=f"opener-signposting:{bucket}", scope="section",
                    calibration_unit="section",
                    line=start, end_line=end, section=raw_label, path=path,
                    detector="deai_metrics", measurement_status=status,
                    strength="strong" if measured else "ordinary",
                    strong_advisory=measured,
                    observed={"connective_openers": n_connective,
                              "paragraphs": len(openers), "fraction": fraction},
                    reference={"field_profile": str(field_profile_dir),
                               "section_bucket": bucket,
                               "corpus_fraction": reference["corpus_signpost"],
                               "operating_point_fraction": signpost_frac,
                               "provenance": reference["assets"]},
                    normalized_distance=fraction - signpost_frac,
                    confidence={"value": min(1.0, len(openers) / 10.0),
                                "basis": f"{len(openers)} paragraphs"},
                    message=(f"Section {raw_label!r} opens {n_connective}/"
                             f"{len(openers)} paragraphs with connectives "
                             f"({fraction:.0%}); "
                             + (f"reference corpus rate is "
                                f"{reference['corpus_signpost']:.1%}."
                                if reference["corpus_signpost"] is not None else
                                "the profile predates the comparable "
                                "paragraph-initial counter, so no reference "
                                "rate is quoted (rebuild it with "
                                "tools/extract_style.py).")),
                    action="Remove roadmap openers that restate the logical connection already carried by the argument.",
                    evidence=[n_connective, len(openers), round(fraction, 6)],
                ))
    return findings


def distribution_hits(text: str, field_profile_dir: Path | None
                      ) -> list[tuple[int, str, str]]:
    return feedback.tuple_hits(distribution_findings(text, field_profile_dir))


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    if not args.file.exists():
        print(f"[deai_metrics] file not found: {args.file}", file=sys.stderr)
        return 2
    field_dir = args.profile_root / args.field if args.field else None
    if field_dir is None and args.profile_root.exists():
        fields = [path for path in args.profile_root.iterdir()
                  if path.is_dir() and not path.name.startswith(".")]
        if len(fields) == 1:
            field_dir = fields[0]
    text = args.file.read_text(encoding="utf-8", errors="replace")
    findings = distribution_findings(text, field_dir, args.file)
    report = feedback.build_report(
        path=args.file, findings=findings,
        axes=[distribution_axis_status(field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
