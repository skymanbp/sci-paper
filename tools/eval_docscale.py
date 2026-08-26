"""Reproduce the document-scale discrimination table from the shipped baseline.

EVALUATION §9 quotes a human false-flag rate and a per-tier 5%-tail power for
the keystone manifold axis. Those numbers came from throwaway scripts, so a
rebuild could move them with nothing to re-run and no way for a reader to check
them. This scores the human corpus and every `docval` tier through
`manifold_operating_point` -- the entry point findings themselves use -- and
prints the table.

The human row is measured over the whole corpus, including the documents that
trained and calibrated the manifold, so it is in-sample and labelled as one. It
exists to compare configurations evaluated identically; the distribution-free
guarantee is the split-conformal alpha, not this rate.

Run:  python tools/eval_docscale.py --field wgl [--format json]
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_docshape as ds  # noqa: E402 -- because of that same sys.path insert
import extract_sections as es  # noqa: E402 -- because of that same sys.path insert
from retrieve_exemplars import resolve_field  # noqa: E402 -- same reason

TIERS = ("ai", "ai_natural", "ai_deai", "ai_adversarial", "ai_skeleton", "ai_long")


def dispersion_row(shape: dict) -> dict[str, float]:
    """The manifold's input vector for one measured document."""
    return {name: float(shape["dispersion"][name][ds.DISPERSION_STAT])
            for name in ds.DISPERSION_FEATURE_NAMES
            if shape.get("dispersion", {}).get(name, {}).get(ds.DISPERSION_STAT)
            is not None}


def score_document(baseline: dict, text: str) -> dict | None:
    """Distance, conformal p, and length for one complete document, or None."""
    shape = ds.document_shape(text)
    if shape["status"] != "measured":
        return None
    point = ds.manifold_operating_point(
        baseline, dispersion_row(shape), shape["n_paragraphs"])
    if point is None:
        return None
    point["n_paragraphs"] = shape["n_paragraphs"]
    return point


def rank_auc(human: list[float], other: list[float]) -> float | None:
    """P(a random AI document outranks a random human one), midrank ties."""
    if not human or not other:
        return None
    merged = sorted([(value, 0) for value in human]
                    + [(value, 1) for value in other])
    rank_sum, index = 0.0, 0
    while index < len(merged):
        stop = index
        while stop + 1 < len(merged) and merged[stop + 1][0] == merged[index][0]:
            stop += 1
        shared = (index + stop) / 2.0 + 1.0
        rank_sum += shared * sum(1 for position in range(index, stop + 1)
                                 if merged[position][1] == 1)
        index = stop + 1
    n_ai, n_human = len(other), len(human)
    return (rank_sum - n_ai * (n_ai + 1) / 2.0) / (n_ai * n_human)


def collect(baseline: dict, field: str, profile_root: Path,
            corpus_root: Path) -> dict[str, list[dict]]:
    """Score the human corpus and every docval tier present."""
    scored: dict[str, list[dict]] = {"human": []}
    for _name, text in es.corpus_documents(corpus_root / field):
        point = score_document(baseline, text)
        if point:
            scored["human"].append(point)
    for tier in TIERS:
        directory = profile_root / field / "docval" / tier
        if not directory.is_dir():
            continue
        points = []
        for path in sorted(directory.glob("*.tex")):
            point = score_document(
                baseline, path.read_text(encoding="utf-8", errors="replace"))
            if point:
                points.append(point)
        if points:
            scored[tier] = points
    return scored


def summarize(scored: dict[str, list[dict]], alpha: float) -> dict:
    human = [point["distance"] for point in scored.get("human", [])]
    rows = {}
    for label, points in scored.items():
        distances = [point["distance"] for point in points]
        flagged = sum(1 for point in points
                      if point.get("p_value") is not None
                      and point["p_value"] <= alpha)
        auc = None if label == "human" else rank_auc(human, distances)
        rows[label] = {
            "n": len(points),
            "median_distance": round(statistics.median(distances), 4),
            "median_paragraphs": statistics.median(
                [point["n_paragraphs"] for point in points]),
            "flag_rate": round(flagged / len(points), 4),
            "auc_vs_human": None if auc is None else round(auc, 3),
        }
    return rows


def render(report: dict) -> str:
    rows = report["rows"]
    width = max(len(key) for key in rows)
    out = [f"[eval_docscale] field={report['field']!r} alpha={report['alpha']} "
           f"baseline={report['baseline_documents']} documents",
           f"{'tier'.ljust(width)}  {'n':>4}  {'med d':>7}  {'med par':>7}"
           f"  {'flag':>6}  {'AUC':>5}"]
    for label, row in rows.items():
        auc = ("  -  " if row["auc_vs_human"] is None
               else f"{row['auc_vs_human']:.3f}")
        out.append(
            f"{label.ljust(width)}  {row['n']:>4}  {row['median_distance']:>7.3f}"
            f"  {row['median_paragraphs']:>7.1f}  {row['flag_rate']:>6.4f}  {auc:>5}")
    out += ["", "The human row is in-sample: it includes the manifold's own "
                "train and calibration documents."]
    return "\n".join(out)


def build_report(field: str, profile_root: Path, corpus_root: Path) -> dict:
    baseline_path = profile_root / field / "docstructure_baseline.json"
    if not baseline_path.exists():
        raise SystemExit(
            f"[eval_docscale] {baseline_path} not found. Run "
            f"`python tools/deai_docstructure.py --calibrate --field {field} "
            f"--corpus-dir style-corpus/{field}` first.")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    alpha = float((baseline.get("conformal") or {}).get("alpha", 0.05))
    scored = collect(baseline, field, profile_root, corpus_root)
    return {
        "schema": "sci-paper.docscale-eval.v1",
        "field": field,
        "alpha": alpha,
        "baseline_documents": baseline.get("n_documents"),
        "human_rate_is_in_sample": True,
        "rows": summarize(scored, alpha),
    }


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__, corpus=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    report = build_report(resolve_field(args.field, args.profile_root),
                          args.profile_root, args.corpus_root)
    text = (json.dumps(report, indent=2) if args.format == "json"
            else render(report))
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"[eval_docscale] -> {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
