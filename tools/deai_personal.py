"""Personal dispersion baseline (cooperative layer, frontier idea 6).

For a researcher writing paper N, their own papers 1..N-1 are the confound-free
reference: same author, same field, same jargon, so the only thing that can move
cross-paragraph shape dispersion is AI-uniformity, not field register. This
sidesteps the field-topic confound behind the shipped classifier's 32-41% false
positive rate entirely -- the comparison is you-versus-you.

It reuses the shipped document dispersion (deai_docstructure.document_shape) and
asks, per shape feature, where the draft's within-document dispersion falls in
the distribution of the author's own prior papers. A draft that varies paragraph
shape far less than the author usually does lands in the low tail: "your last N
papers vary paragraph length more than this draft." Honest and persuasive,
model-free, no GPU.

With fewer than MIN_PERSONAL_PAPERS measured prior papers the axis is honestly
``unmeasured`` -- a personal baseline needs the author's own history to exist.

CLI:
  python tools/deai_personal.py draft.tex --prior-papers-dir my_papers/
Lib:
  from deai_personal import personal_reference, compare, document_findings
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_docstructure as ds    # noqa: E402  resolves only after the sys.path insert
import deai_feedback as feedback  # noqa: E402  shared finding contract

MIN_PERSONAL_PAPERS = 3        # a personal baseline below this is not a distribution
BAND_PERCENTILE = 0.10         # draft dispersion in the author's low tail -> under-varied
FLAG_FEATURE_FRACTION = 0.40   # this fraction of features under-varied -> document flag
DISPERSION_STAT = ds.DISPERSION_STAT            # "std"
FEATURE_NAMES = list(ds.DISPERSION_FEATURE_NAMES)


def paper_dispersion(text: str) -> dict[str, float] | None:
    """Per-feature within-document dispersion (std) for one paper, or None.

    None when the paper does not meet the document_shape section/paragraph gates,
    so a fragment can never pollute the personal reference.
    """
    shape = ds.document_shape(text)
    if shape.get("status") != "measured":
        return None
    dispersion = shape.get("dispersion", {})
    row = {}
    for name in FEATURE_NAMES:
        stat = dispersion.get(name, {})
        value = stat.get(DISPERSION_STAT)
        if value is not None:
            row[name] = float(value)
    return row or None


def personal_reference(paper_texts: list[str]) -> dict[str, Any]:
    """Distribution of each dispersion feature across the author's own papers."""
    rows = [row for row in (paper_dispersion(t) for t in paper_texts) if row]
    if len(rows) < MIN_PERSONAL_PAPERS:
        return {"status": "unmeasured",
                "reason": (f"need >= {MIN_PERSONAL_PAPERS} measured prior papers, "
                           f"have {len(rows)}"),
                "n_papers": len(rows), "by_feature": {}}
    by_feature = {}
    for name in FEATURE_NAMES:
        values = sorted(row[name] for row in rows if name in row)
        if len(values) >= MIN_PERSONAL_PAPERS:
            by_feature[name] = values
    return {"status": "measured", "reason": None,
            "n_papers": len(rows), "by_feature": by_feature}


def _low_tail_fraction(draft_value: float, author_values: list[float]) -> float:
    """Fraction of the author's own papers with dispersion at or below the draft.

    Near 0 = the draft varies this feature less than almost all of the author's
    own papers (the AI-uniformity tell); near 1 = the draft is as varied as usual.
    """
    at_or_below = sum(1 for v in author_values if v <= draft_value)
    return at_or_below / len(author_values)


def compare(draft_text: str, reference: dict[str, Any]) -> dict[str, Any]:
    """Compare a draft's dispersion to the author's own baseline distribution."""
    if reference.get("status") != "measured":
        return {"status": "unmeasured", "reason": reference.get("reason"),
                "features": [], "summary": {}}
    draft = paper_dispersion(draft_text)
    if draft is None:
        return {"status": "unmeasured",
                "reason": "draft does not meet the document_shape gates",
                "features": [], "summary": {}}
    features = []
    for name, author_values in reference["by_feature"].items():
        if name not in draft:
            continue
        percentile = _low_tail_fraction(draft[name], author_values)
        features.append({
            "feature": name,
            "draft_dispersion": draft[name],
            "author_median": statistics.median(author_values),
            "personal_percentile": percentile,
            "under_varied": percentile <= BAND_PERCENTILE,
        })
    if not features:
        return {"status": "unmeasured",
                "reason": "no feature is measured on both draft and baseline",
                "features": [], "summary": {}}
    n_under = sum(1 for f in features if f["under_varied"])
    return {
        "status": "measured", "reason": None, "features": features,
        "summary": {
            "n_papers": reference["n_papers"],
            "n_features": len(features),
            "n_under_varied": n_under,
            "under_varied_fraction": n_under / len(features),
            "mean_personal_percentile": statistics.mean(
                f["personal_percentile"] for f in features),
        },
    }


def document_findings(draft_text: str, path: str | Path | None,
                      paper_texts: list[str]
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Findings + axis status for the personal-baseline comparison.

    Emits a single document-scale advisory when the draft is under-varied on at
    least FLAG_FEATURE_FRACTION of features relative to the author's own papers.
    The reference is confound-free (same author), so this is not subject to the
    field-topic false-positive rate; it is still an advisory, never a gate.
    """
    axis_name = "L4.personal_baseline"
    reference = personal_reference(paper_texts)
    result = compare(draft_text, reference)
    if result["status"] != "measured":
        return [], [feedback.axis_status(axis_name, "unmeasured",
                                         reason=result.get("reason"),
                                         detector="deai_personal")]
    summary = result["summary"]
    axes = [feedback.axis_status(
        axis_name, "measured",
        reason=(f"draft under-varied on {summary['n_under_varied']} of "
                f"{summary['n_features']} features vs {summary['n_papers']} own "
                f"papers (mean personal percentile "
                f"{summary['mean_personal_percentile']:.2f})"),
        detector="deai_personal")]
    if summary["under_varied_fraction"] < FLAG_FEATURE_FRACTION:
        return [], axes
    under = [f["feature"] for f in result["features"] if f["under_varied"]]
    findings = [feedback.make_finding(
        kind="advisory", layer="L4", rule="personal-baseline:under-varied",
        scope="document", calibration_unit="document", line=1, path=path,
        detector="deai_personal", detector_version="sci-paper.personal.v1",
        measurement_status="measured",
        strength="strong" if summary["under_varied_fraction"] >= 0.6 else "ordinary",
        observed={"under_varied_features": under,
                  "mean_personal_percentile": summary["mean_personal_percentile"]},
        reference={"n_own_papers": summary["n_papers"]},
        normalized_distance=1.0 - summary["mean_personal_percentile"],
        confidence={"value": min(1.0, summary["n_papers"] / 6.0),
                    "basis": "confound-free same-author dispersion baseline"},
        message=(f"This draft varies paragraph shape less than your own "
                 f"{summary['n_papers']} papers on {summary['n_under_varied']} of "
                 f"{summary['n_features']} features."),
        action=("Let paragraphs differ where the argument demands it, as your own "
                "prior papers do; personal-baseline evidence is advisory."))]
    return findings, axes


def _load_papers(directory: Path) -> list[str]:
    """Concatenate each paper directory (multi-file papers = one document)."""
    return [text for _name, text in ds._paper_documents(directory)]


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.base_parser(__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--prior-papers-dir", type=Path, required=True,
                        help="directory of the author's own prior papers")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if not args.file.exists():
        print(f"[deai_personal] file not found: {args.file}", file=sys.stderr)
        return 2
    draft = args.file.read_text(encoding="utf-8", errors="replace")
    papers = _load_papers(args.prior_papers_dir) if args.prior_papers_dir.exists() else []
    findings, axes = document_findings(draft, args.file, papers)
    if args.format == "json":
        report = feedback.build_report(path=args.file, findings=findings, axes=axes)
        print(feedback.dump_report(report), end="")
        return 0
    for axis in axes:
        detail = f": {axis['reason']}" if axis.get("reason") else ""
        print(f"axis {axis['axis']}: {axis['status']}{detail}")
    for finding in findings:
        print(f"  [{finding['rule']}] {finding['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
