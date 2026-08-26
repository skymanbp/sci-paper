"""Score the register and salience axes against labels that already exist.

Both axes are corpus-referenced advisories, and their precision has stood at
`unmeasured` because nothing in the repository says whether a human agrees with
a given advisory. `label_findings.py` is the harness for producing those
judgements by hand. This tool answers the part that needs no hand: a refereed
paper in ApJ, ApJL or A&A is text human authors wrote and human referees
accepted, so its provenance IS a label.

Three populations, and the contrast between them is the measurement:

- **published-heldout** -- refereed ApJ/ApJL/A&A papers fetched with
  `--exclude-known`, so no part of them fed `register_lexicon.json` or
  `salience_baseline.json`. On this set a register finding is a false positive
  by construction: the field's own accepted vocabulary cannot be foreign to the
  field.
- **published-insample** -- the `fulltext-arxiv/` breadth pull: same genre,
  same journals, but these papers DID feed the banks. The gap between the two
  rates is the in-sample optimism, otherwise invisible. It is not decoration:
  `deai_register.RARE_DF_RATE` is 1e-4, so on 41,593 passages the foreign-term
  threshold sits at four passages and one paper's own paragraphs suffice to
  suppress its own flags.
- **machine** -- the `docval/` AI tiers, machine-drafted, where a finding is a
  detection rather than a false positive.

The two axes must be read differently, because they are gated differently:

- **register** is an absolute rarity test, so its held-out rate is a
  false-positive rate and low is correct.
- **salience** is a percentile gate (`ADVISORY_PERCENTILE` = 0.90), so about a
  tenth of calibration passages exceed it BY DESIGN. Its held-out rate is a
  calibration-transfer check: near the design rate is correct behaviour, far
  above it means the percentile did not transfer to unseen papers. It is not a
  bug count, and reporting it as one would manufacture a defect out of the
  gate's own definition.

What this does NOT measure: "this paper was published" does not mean every
sentence in it is beyond improvement, so the held-out register rate is an UPPER
bound on the false-positive rate for advice purposes, not the rate itself.
Precision against human judgement of individual advisories, and recall, stay
`unmeasured` -- `label_findings.py` is the path to those. The rate on machine
text is a detection rate, a different quantity, and is labelled as one.

Run:  python tools/eval_findings.py --field wgl [--format json]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_register  # noqa: E402 -- because of that same sys.path insert
import deai_salience  # noqa: E402 -- because of that same sys.path insert
import extract_sections as es  # noqa: E402 -- because of that same sys.path insert
from eval_docscale import rank_auc  # noqa: E402 -- one AUC implementation, same reason

SCHEMA = "sci-paper.findings-eval.v1"
HELDOUT_DIR = "fulltext-heldout"
INSAMPLE_DIR = "fulltext-arxiv"
MIN_DOCUMENTS = 20   # below this a rate is reported `unmeasured`, never as 0/0
AXES = ("L0.register", "L2.salience_hierarchy")


def _bundle_documents(root: Path) -> list[tuple[str, str]]:
    """(name, text) per paper under a directory of arXiv source bundles.

    One bundle is one paper even when it ships a dozen `.tex` fragments, so the
    roots are selected and their includes spliced back in, rather than each file
    counting as its own document.
    """
    out: list[tuple[str, str]] = []
    for bundle in sorted(p for p in root.iterdir() if p.is_dir()):
        tex = sorted(bundle.rglob("*.tex"))
        if not tex:
            continue
        for chosen in es.select_document_roots(tex, bundle):
            text = es.read_tex_document(chosen)
            if text.strip():
                out.append((f"{bundle.name}/{chosen.name}", text))
    return out


def _flat_documents(root: Path) -> list[tuple[str, str]]:
    """(name, text) for a directory of single-file documents."""
    return [(p.name, p.read_text(encoding="utf-8", errors="replace"))
            for p in sorted(root.glob("*.tex"))]


def score_document(text: str, field_dir: Path, path: str) -> dict[str, float]:
    """Per-axis finding counts, length, and the salience denominator.

    `n_salience_units` is the count of passages the salience gate could have
    fired on. Without it the axis can only be reported per 1,000 words, and its
    gate is defined per passage — so there would be no way to check the measured
    rate against the rate the percentile is supposed to produce.
    """
    register = deai_register.register_findings(text, field_dir, path)
    salience = deai_salience.salience_findings(text, field_dir, path)
    strong = sum(1 for f in salience
                 if f.get("strength") == "strong" or f.get("strong_advisory"))
    units = sum(1 for unit in deai_salience._units(text)
                if deai_salience.salience_features(unit[3]) is not None)
    return {
        "n_words": float(len(text.split())),
        "n_salience_units": float(units),
        "L0.register": float(len(register)),
        "L2.salience_hierarchy": float(len(salience)),
        "salience_strong": float(strong),
    }


def summarize(rows: list[dict[str, float]], axis: str) -> dict:
    """Document flag rate and length-normalized density for one axis."""
    if len(rows) < MIN_DOCUMENTS:
        return {"status": "unmeasured", "n": len(rows),
                "why": f"n < {MIN_DOCUMENTS}"}
    flagged = sum(1 for r in rows if r[axis] > 0)
    words = sum(r["n_words"] for r in rows)
    findings = sum(r[axis] for r in rows)
    return {
        "status": "measured",
        "n": len(rows),
        "flag_rate": round(flagged / len(rows), 4),
        "per_1k_words": round(1000.0 * findings / words, 4) if words else None,
        "total_findings": int(findings),
    }


def _density(rows: list[dict[str, float]], axis: str) -> list[float]:
    return [1000.0 * r[axis] / r["n_words"] for r in rows if r["n_words"]]


def leakage_paired(text: str, field_dir: Path, path: str) -> tuple[int, int]:
    """(flagged, still flagged had this paper been in the bank) for one document.

    Comparing the held-out population against the in-sample one estimates
    leakage only if the two are otherwise alike, and they are not: the shipped
    breadth pull is 2020-2021 while a held-out sweep reaches deeper into the
    result order and lands on older papers, so that contrast confounds leakage
    with years of vocabulary drift.

    This is the same comparison without the confound, because it is paired on
    one document. `deai_register` calls a term foreign below a document
    frequency *rate*, so adding the paper to the bank moves both sides of that
    ratio by a computable amount -- its own passages containing the term, and
    its own passage count. No rebuild is needed and no second population is
    involved, so nothing but membership differs.
    """
    lexicon = deai_register.load_lexicon(field_dir)
    if lexicon is None:
        return (0, 0)
    n_passages = int(lexicon.get("n_passages", 0))
    table = lexicon["document_frequency"]
    own = [block for block in text.split("\n\n") if len(block.split()) >= 5]
    flagged = survives = 0
    for finding in deai_register.register_findings(text, field_dir, path):
        term = str(finding["rule"]).split("register-foreign:", 1)[-1]
        df, _ = deai_register.corpus_document_frequency(term, table)
        own_df = sum(1 for block in own if term.lower() in block.lower())
        flagged += 1
        if ((df + own_df) / (n_passages + len(own))
                < deai_register.RARE_DF_RATE):
            survives += 1
    return (flagged, survives)


def collect(field: str, corpus_root: Path, profile_root: Path, heldout_dir: str
            ) -> tuple[dict[str, list[dict[str, float]]], tuple[int, int]]:
    """Score every available population, and run the paired leakage test.

    Returns the populations and the held-out set's (flagged, would-still-fire)
    tally, which is the leakage estimate the cross-population contrast cannot
    give without confounding itself with publication era.
    """
    field_dir = profile_root / field
    corpus = corpus_root / field
    sources: list[tuple[str, Path, bool]] = [
        ("published-heldout", corpus / heldout_dir, True),
        ("published-insample", corpus / INSAMPLE_DIR, True),
    ]
    docval = field_dir / "docval"
    if docval.is_dir():
        for tier in sorted(p for p in docval.iterdir() if p.is_dir()):
            sources.append((f"machine:{tier.name}", tier, False))

    populations: dict[str, list[dict[str, float]]] = {}
    flagged = survives = 0
    for label, root, is_bundle in sources:
        if not root.is_dir():
            continue
        documents = _bundle_documents(root) if is_bundle else _flat_documents(root)
        rows = []
        for name, text in documents:
            if len(text.split()) < deai_salience.MIN_WORDS:
                continue
            rows.append(score_document(text, field_dir, name))
            if label == "published-heldout":
                one, two = leakage_paired(text, field_dir, name)
                flagged += one
                survives += two
        if rows:
            populations[label] = rows
    return populations, (flagged, survives)


def salience_gate_transfer(rows: list[dict[str, float]]) -> dict:
    """Measured per-passage flag rate against the rate the gate should produce.

    `salience_findings` emits one finding per over-recital passage, led by its
    most extreme feature, so under independent gates the per-passage rate is
    1 - p**k for k features at percentile p. Comparing the measured rate with
    that expectation is the calibration-transfer test; a per-1,000-words density
    cannot make it, because the gate is not defined per word.
    """
    units = sum(r.get("n_salience_units", 0.0) for r in rows)
    findings = sum(r["L2.salience_hierarchy"] for r in rows)
    if len(rows) < MIN_DOCUMENTS or not units:
        return {"status": "unmeasured",
                "why": f"n={len(rows)} documents, {int(units)} passages"}
    expected = 1 - deai_salience.ADVISORY_PERCENTILE ** len(deai_salience.FEATURES)
    return {
        "status": "measured",
        "n_passages": int(units),
        "n_findings": int(findings),
        "measured_per_passage": round(findings / units, 4),
        "independent_gate_expectation": round(expected, 4),
        "n_features": len(deai_salience.FEATURES),
    }


def build_report(field: str, populations: dict[str, list[dict[str, float]]],
                 leakage: tuple[int, int] = (0, 0)) -> dict:
    """The finished evidence record: per-population rows plus the AUCs."""
    heldout = populations.get("published-heldout", [])
    machine = [row for label, rows in populations.items()
               if label.startswith("machine:") for row in rows]
    if machine:
        populations = {**populations, "machine:ALL": machine}

    rows_out = {
        label: {
            "n_documents": len(rows),
            "median_words": sorted(r["n_words"] for r in rows)[len(rows) // 2],
            **{axis: summarize(rows, axis) for axis in AXES},
        }
        for label, rows in populations.items()
    }
    if len(heldout) >= MIN_DOCUMENTS and len(machine) >= MIN_DOCUMENTS:
        discrimination = {
            axis: {"auc_machine_over_heldout":
                   rank_auc(_density(heldout, axis), _density(machine, axis))}
            for axis in AXES}
    else:
        discrimination = {
            "status": "unmeasured",
            "why": f"heldout n={len(heldout)}, machine n={len(machine)}; "
                   f"both need >= {MIN_DOCUMENTS}"}
    flagged, survives = leakage
    return {
        "schema": SCHEMA,
        "field": field,
        "advisory_percentile": deai_salience.ADVISORY_PERCENTILE,
        "rare_df_rate": deai_register.RARE_DF_RATE,
        "salience_gate_transfer": salience_gate_transfer(heldout),
        "populations": rows_out,
        "discrimination": discrimination,
        "register_leakage_paired": (
            {"status": "unmeasured", "why": "no held-out register findings"}
            if not flagged else
            {"status": "measured", "flagged": flagged, "survives": survives,
             "suppressed_by_own_membership": round(1 - survives / flagged, 4)}),
        "populations_are_era_comparable": False,
    }


def _cell(entry: dict) -> str:
    if entry.get("status") != "measured":
        return f"{'unmeasured':>10s} {'-':>9s}"
    return f"{entry['flag_rate']:>10.3f} {entry['per_1k_words']:>9.3f}"


def render(report: dict) -> str:
    """The human-readable table, with each axis's reading spelled out."""
    gate = report["advisory_percentile"]
    lines = [f"[eval_findings] field={report['field']!r}  "
             f"salience gate={gate}  register rare-df={report['rare_df_rate']}",
             f"{'population':22s} {'n':>4s} {'med w':>7s} "
             f"{'reg flag':>10s} {'reg/1kw':>9s} "
             f"{'sal flag':>10s} {'sal/1kw':>9s}"]
    for label, entry in report["populations"].items():
        lines.append(f"{label:22s} {entry['n_documents']:>4d} "
                     f"{entry['median_words']:>7.0f} "
                     f"{_cell(entry['L0.register'])} "
                     f"{_cell(entry['L2.salience_hierarchy'])}")
    lines.append("")
    discrimination = report["discrimination"]
    if discrimination.get("status"):
        lines.append(f"discrimination: unmeasured ({discrimination['why']})")
    else:
        for axis, entry in discrimination.items():
            auc = entry["auc_machine_over_heldout"]
            shown = f"{auc:.3f}" if auc is not None else "unmeasured"
            lines.append(f"AUC machine over held-out published  {axis:24s} {shown}")
    gate = report["salience_gate_transfer"]
    if gate.get("status") == "measured":
        lines.append(
            f"salience gate transfer (held-out, per passage): "
            f"{gate['measured_per_passage']:.4f} measured over "
            f"{gate['n_passages']} passages against "
            f"{gate['independent_gate_expectation']:.4f} expected from "
            f"{gate['n_features']} independent gates")
    leak = report["register_leakage_paired"]
    if leak.get("status") == "measured":
        lines.append(
            f"register in-sample optimism (paired, same papers): "
            f"{leak['suppressed_by_own_membership']:.3f} of "
            f"{leak['flagged']} held-out flags would be suppressed by the "
            f"paper's own bank membership")
    lines += [
        "",
        "register on published-heldout is a false-positive rate: the field's",
        "own accepted vocabulary cannot be foreign to the field. salience is",
        f"NOT -- its gate is the {gate} percentile, so that fraction of passages",
        "exceeds it by design and the number tests whether the percentile",
        "transferred, not whether the papers are defective.",
        "",
        "Do NOT read the two published rows as a leakage estimate: they are not",
        "era-comparable (the shipped breadth pull is 2020-2021; a held-out sweep",
        "reaches deeper in the result order and lands earlier), so that contrast",
        "confounds leakage with vocabulary drift. The paired line above is the",
        "leakage measurement -- one population, one era, membership the only",
        "thing that differs.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.report_options(
        cli_common.field_parser(__doc__, corpus=True))
    parser.add_argument("--heldout-dir", default=HELDOUT_DIR,
                        help="directory under style-corpus/<field>/ holding the "
                             f"held-out refereed papers (default {HELDOUT_DIR!r})")
    args = parser.parse_args(argv)

    field = cli_common.resolve_field(args.field, args.profile_root,
                                     tool="eval_findings")
    populations, leakage = collect(field, args.corpus_root, args.profile_root,
                                   args.heldout_dir)
    if not populations:
        raise SystemExit(
            f"[eval_findings] no documents found for field {field!r}. Build a "
            f"held-out set first:\n"
            f"  python tools/fetch_arxiv_abstracts.py --field {field} "
            f"--fulltext --exclude-known \\\n"
            f"      --fulltext-dir {args.heldout_dir} --journals apj,apjl,aa")
    report = build_report(field, populations, leakage)
    return cli_common.emit_report(report, args, render=render,
                                  tool="eval_findings")


if __name__ == "__main__":
    raise SystemExit(main())
