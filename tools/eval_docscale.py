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

A row under `MIN_DOCUMENTS` scored documents reports `unmeasured`, never a
rate: one document once printed a flag rate and an AUC of its own. Each row
names the operating point its flags were decided by (a stratum or the pooled
manifold); every point is split-conformal and flags at p <= its own alpha,
because a baseline without that calibration scores no document (audit B24).

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

# Below this many scored documents a row is `unmeasured`, never a rate.
# `eval_findings` imports this same floor, so the two evaluators cannot
# disagree on how many documents a document-level rate needs.
MIN_DOCUMENTS = 20


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
    """Score the human corpus and every docval tier present.

    The tiers are whatever `docval/` holds, discovered the way `eval_findings`
    discovers them: a fixed tuple of tier names left a tier added later out of
    the table with nothing to say so. A tier directory that scores nothing
    stays in the result as an empty list, so the table prints it as
    `unmeasured` rather than omitting it.
    """
    scored: dict[str, list[dict]] = {"human": []}
    for _name, text in es.corpus_documents(corpus_root / field):
        point = score_document(baseline, text)
        if point:
            scored["human"].append(point)
    docval = profile_root / field / "docval"
    tiers = (sorted(p for p in docval.iterdir() if p.is_dir())
             if docval.is_dir() else [])
    for directory in tiers:
        points = []
        for path in sorted(directory.glob("*.tex")):
            point = score_document(
                baseline, path.read_text(encoding="utf-8", errors="replace"))
            if point:
                points.append(point)
        scored[directory.name] = points
    return scored


def flagged(point: dict) -> bool:
    """Whether the operating point that scored a document flags it.

    Every point is split-conformal and carries its own `alpha`; the flag is
    `p_value <= alpha`. The branch for a legacy in-sample percentile point
    (no alpha, its threshold's own decision) went with that point in B24.
    """
    return point["p_value"] <= point["alpha"]


def operating_point(points: list[dict]) -> str:
    """The rule(s) a row's flags were decided by, as the points record them."""
    return ", ".join(sorted({str(point.get("operating_point")) for point in points}))


def summarize(scored: dict[str, list[dict]]) -> dict:
    """One row per population: the numbers at the floor, `unmeasured` below it.

    The AUC against the human row needs both sides at the floor, so a thin
    human row leaves every AUC `None` rather than ranking against a handful.
    """
    human = [point["distance"] for point in scored.get("human", [])]
    rows = {}
    for label, points in scored.items():
        if len(points) < MIN_DOCUMENTS:
            rows[label] = {"status": "unmeasured", "n": len(points),
                           "why": (f"n={len(points)} < {MIN_DOCUMENTS}" if points
                                   else "no document scored")}
            continue
        distances = [point["distance"] for point in points]
        auc = (rank_auc(human, distances)
               if label != "human" and len(human) >= MIN_DOCUMENTS else None)
        rows[label] = {
            "status": "measured",
            "n": len(points),
            "operating_point": operating_point(points),
            "median_distance": round(statistics.median(distances), 4),
            "median_paragraphs": statistics.median(
                [point["n_paragraphs"] for point in points]),
            "flag_rate": round(
                sum(1 for point in points if flagged(point)) / len(points), 4),
            "auc_vs_human": None if auc is None else round(auc, 3),
        }
    return rows


def render(report: dict) -> str:
    rows = report["rows"]
    width = max(len(key) for key in rows)
    alpha = "-" if report["alpha"] is None else report["alpha"]
    out = [f"[eval_docscale] field={report['field']!r} alpha={alpha} "
           f"baseline={report['baseline_documents']} documents "
           f"(floor {report['min_documents']} documents per row)",
           f"{'tier'.ljust(width)}  {'n':>4}  {'med d':>7}  {'med par':>7}"
           f"  {'flag':>6}  {'AUC':>5}  operating point"]
    for label, row in rows.items():
        if row["status"] != "measured":
            out.append(f"{label.ljust(width)}  {row['n']:>4}  "
                       f"unmeasured ({row['why']})")
            continue
        auc = ("  -  " if row["auc_vs_human"] is None
               else f"{row['auc_vs_human']:.3f}")
        out.append(
            f"{label.ljust(width)}  {row['n']:>4}  {row['median_distance']:>7.3f}"
            f"  {row['median_paragraphs']:>7.1f}  {row['flag_rate']:>6.4f}  {auc:>5}"
            f"  {row['operating_point']}")
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
    scored = collect(baseline, field, profile_root, corpus_root)
    if not scored["human"]:
        # `statistics.median([])` raised a StatisticsError here, naming
        # neither the empty corpus nor the manifold that scored nothing.
        raise SystemExit(
            f"[eval_docscale] no human document under {corpus_root / field} "
            f"scored, so there is no row to compare the tiers against. Either "
            f"the corpus holds no complete documents -- fetch some with `python "
            f"tools/fetch_arxiv_abstracts.py --field {field} --fulltext` -- or "
            f"the baseline scores none of them: rebuild it with `python "
            f"tools/deai_docstructure.py --calibrate --field {field} "
            f"--corpus-dir style-corpus/{field}`.")
    # The level every flag in this run was decided at: the points carry it.
    alphas = {point["alpha"] for points in scored.values() for point in points}
    return {
        "schema": "sci-paper.docscale-eval.v1",
        "field": field,
        "alpha": alphas.pop() if len(alphas) == 1 else None,
        "min_documents": MIN_DOCUMENTS,
        "baseline_documents": baseline.get("n_documents"),
        "human_rate_is_in_sample": True,
        "rows": summarize(scored),
    }


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.report_options(
        cli_common.field_parser(__doc__, corpus=True))
    args = parser.parse_args(argv)

    # Resolved under this tool's own name: the wrapper borrowed from
    # `retrieve_exemplars` signed its errors `[retrieve_exemplars]`.
    field = cli_common.resolve_field(args.field, args.profile_root,
                                     tool="eval_docscale")
    report = build_report(field, args.profile_root, args.corpus_root)
    return cli_common.emit_report(report, args, render=render,
                                  tool="eval_docscale")


if __name__ == "__main__":
    raise SystemExit(main())
