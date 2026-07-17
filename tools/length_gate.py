"""Per-section prose length-budget gate between two versions of a document.

Enforces SCIPAPER_STANDARD section 5.3 (condense, do not accumulate): an edit
loop's output must not carry net prose growth without a recorded
justification. Exit status mirrors the linter's narrow contract: 0 means no
unjustified NET growth, 1 means the document's total prose grew beyond the
tolerance after subtracting justified section growth, 2 means invalid input or
execution failure. Per-section growth findings are emitted either way: an
unjustified growing section is a strong advisory (disposition required before
a loop may close, SCIPAPER_STANDARD section 5.1) even when a shrink elsewhere
balances the net, and a justified one is an ordinary advisory carrying the
recorded reason, so the audit trail survives into the report. A pure section
rename appears as a paired shrink/growth that nets to zero: exit stays 0 and
the paired findings document the rename for the report.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import deai_feedback as feedback  # noqa: E402  shared finding contract
import deai_metrics  # noqa: E402  section segmentation
import extract_style as es  # noqa: E402  LaTeX-to-prose cleaning

FRONT_MATTER = "(front matter)"
# Heading commands are stripped before counting: the budget measures body
# prose, and a section RENAME must not register as prose growth.
HEADING_PATTERN = re.compile(
    r"\\(?:chapter|section|subsection|subsubsection|paragraph)\*?\{[^{}]*\}")


def prose_word_count(tex: str) -> int:
    return len(es.latex_to_plain(HEADING_PATTERN.sub("", tex)).split())


def section_word_counts(text: str) -> dict[str, int]:
    """Rendered-prose word count per section label, plus a front-matter bucket."""
    lines = text.splitlines()
    counts: Counter[str] = Counter()
    covered: set[int] = set()
    for start, end, label in deai_metrics.section_line_ranges(text):
        counts[label] += prose_word_count("\n".join(lines[start - 1:end]))
        covered.update(range(start, end + 1))
    rest = "\n".join(line for number, line in enumerate(lines, start=1)
                     if number not in covered)
    if rest.strip():
        counts[FRONT_MATTER] += prose_word_count(rest)
    return dict(counts)


def read_git_version(after: Path, ref: str) -> str:
    # errors="replace" on both calls: a baseline with stray non-UTF-8 bytes
    # must degrade to lossy words, not escape as an uncaught decode traceback.
    directory = after.resolve().parent
    top = subprocess.run(["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
                         text=True, capture_output=True, encoding="utf-8",
                         errors="replace")
    if top.returncode != 0:
        raise ValueError(f"not inside a git repository: {top.stderr.strip()}")
    relative = after.resolve().relative_to(Path(top.stdout.strip())).as_posix()
    shown = subprocess.run(["git", "-C", str(directory), "show", f"{ref}:{relative}"],
                           text=True, capture_output=True, encoding="utf-8",
                           errors="replace")
    if shown.returncode != 0:
        raise ValueError(f"git show {ref}:{relative} failed: {shown.stderr.strip()}")
    return shown.stdout


def parse_allowances(entries: list[str]) -> dict[str, str]:
    allowances: dict[str, str] = {}
    for entry in entries:
        label, separator, reason = entry.partition("=")
        if not separator or not label.strip() or not reason.strip():
            raise ValueError(f"--allow expects '<section>=<reason>', got {entry!r}")
        allowances[label.strip().lower()] = reason.strip()
    return allowances


def _finding(*, path: Path, rule: str, section: str, kind: str = "advisory",
             strength: str = "ordinary", strong_advisory: bool = False,
             observed: dict[str, Any], message: str, action: str) -> dict[str, Any]:
    return feedback.make_finding(
        kind=kind, layer="QD", rule=rule, scope="section", path=path, line=1,
        section=section, detector="length_gate", strength=strength,
        strong_advisory=strong_advisory, observed=observed,
        reference={"provenance": "SCIPAPER_STANDARD section 5.3",
                   "budget": "no net prose growth without recorded justification"},
        normalized_distance=None,
        confidence={"value": 1.0, "basis": "deterministic word-count delta"},
        measurement_status="measured", message=message, action=action,
        evidence=[rule, observed],
    )


def match_allowance(label: str, allowances: dict[str, str]) -> str | None:
    """Case-insensitive exact-or-substring match, so a human-typed --allow key
    still matches a long or macro-mangled section label."""
    low = label.lower()
    for key, reason in allowances.items():
        if key == low or key in low:
            return reason
    return None


def gate_findings(before_text: str, after_text: str, path: Path,
                  tolerance_words: int, allowances: dict[str, str],
                  allow_total: str | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    before = section_word_counts(before_text)
    after = section_word_counts(after_text)
    findings: list[dict[str, Any]] = []
    rows = []
    justified_growth = 0
    for label in sorted(set(before) | set(after)):
        words_before = before.get(label, 0)
        words_after = after.get(label, 0)
        delta = words_after - words_before
        reason = allow_total or match_allowance(label, allowances)
        grew = delta > tolerance_words
        status = "ok" if not grew else ("justified" if reason else "GROWTH")
        rows.append((label, words_before, words_after, delta, status))
        if not grew:
            continue
        if reason:
            justified_growth += delta
        observed = {"section": label, "words_before": words_before,
                    "words_after": words_after, "delta_words": delta,
                    "tolerance_words": tolerance_words}
        if reason:
            observed["justification"] = reason
            findings.append(_finding(
                path=path, rule=f"length-growth-justified:{label}", section=label,
                observed=observed,
                message=(f"Section {label!r} grew by {delta} words with a recorded "
                         f"justification: {reason}"),
                action="No action required; the justification is on record for the author.",
            ))
        else:
            findings.append(_finding(
                path=path, rule=f"length-growth:{label}", section=label,
                strength="strong", strong_advisory=True, observed=observed,
                message=(f"Section {label!r} grew by {delta} words "
                         f"({words_before} -> {words_after}) with no recorded "
                         "justification."),
                action=("Condense the section back within budget, record the "
                        "author-approved justification via --allow "
                        f"\"{label}=<reason>\", or note the section rename "
                        "that pairs this growth with a shrink elsewhere."),
            ))
    total_delta = sum(after.values()) - sum(before.values())
    summary = {
        "total_before": sum(before.values()),
        "total_after": sum(after.values()),
        "total_delta": total_delta,
        "justified_growth": justified_growth,
        "net_unjustified_growth": total_delta - justified_growth,
        "rows": rows,
    }
    return findings, summary


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("after", type=Path, help="edited version of the document")
    parser.add_argument("--before", type=Path,
                        help="pre-edit version of the document (file path)")
    parser.add_argument("--git-ref", default=None,
                        help="read the pre-edit version from this git ref instead")
    parser.add_argument("--tolerance-words", type=int, default=0)
    parser.add_argument("--allow", action="append", default=[],
                        metavar="SECTION=REASON",
                        help="record a justification for one section's growth")
    parser.add_argument("--allow-total", default=None, metavar="REASON",
                        help="record one justification covering every section")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if not args.after.exists():
        print(f"[length_gate] file not found: {args.after}", file=sys.stderr)
        return 2
    if (args.before is None) == (args.git_ref is None):
        print("[length_gate] provide exactly one of --before or --git-ref",
              file=sys.stderr)
        return 2
    if args.tolerance_words < 0:
        print("[length_gate] --tolerance-words must be >= 0", file=sys.stderr)
        return 2
    if args.allow_total is not None and not args.allow_total.strip():
        print("[length_gate] --allow-total requires a non-empty reason",
              file=sys.stderr)
        return 2
    try:
        if args.git_ref is not None:
            before_text = read_git_version(args.after, args.git_ref)
        else:
            before_text = args.before.read_text(encoding="utf-8", errors="replace")
        after_text = args.after.read_text(encoding="utf-8", errors="replace")
        allowances = parse_allowances(args.allow)
        findings, summary = gate_findings(
            before_text, after_text, args.after,
            args.tolerance_words, allowances, args.allow_total)
        axes = [feedback.axis_status("QD.length_budget", "measured",
                                     detector="length_gate")]
        report = feedback.build_report(path=args.after, findings=findings, axes=axes)
        if args.format == "json":
            rendered = feedback.dump_report(report)
        else:
            lines = [f"length_gate: {args.after}",
                     f"{'section':<28} {'before':>7} {'after':>7} {'delta':>7}  status"]
            for label, words_before, words_after, delta, status in summary["rows"]:
                lines.append(f"{label[:28]:<28} {words_before:>7} {words_after:>7} "
                             f"{delta:>+7}  {status}")
            lines.append(f"{'TOTAL':<28} {summary['total_before']:>7} "
                         f"{summary['total_after']:>7} {summary['total_delta']:>+7}")
            lines.append(f"net unjustified growth: "
                         f"{summary['net_unjustified_growth']:+d} words "
                         f"(tolerance {args.tolerance_words})")
            rendered = "\n".join(lines) + "\n" + feedback.render_text(report) + "\n"
        if args.output is not None:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"[length_gate] execution failed: {error}", file=sys.stderr)
        return 2
    return 1 if summary["net_unjustified_growth"] > args.tolerance_words else 0


if __name__ == "__main__":
    raise SystemExit(main())
