"""Sample findings for human labelling, then score the axes against the labels.

Salience and register are corpus-referenced: they compare a draft against the
field's own banks. Nothing in the repository says whether a human agrees that a
given advisory is *right*, so their precision and recall are unmeasured — the
one roadmap item that no amount of computation closes, because it needs labels.

This is the harness for producing them, to the scheme chosen on 2026-08-26:

- **finding-level** labels. You judge one emitted advisory at a time, which is
  what you actually see in a report, and a matched sample of unflagged passages
  supplies the negatives that make recall computable.
- **one labeller, with a blind re-label subset.** A single labeller cannot give
  an inter-rater bound, so `--relabel` re-serves a fraction in shuffled order
  with the prior answers stripped. The resulting intra-rater agreement is the
  noise ceiling: an axis cannot be held to a precision the task itself does not
  support.
- **stratified over both populations.** Drafts and published papers are sampled
  and reported separately, because "does it misfire on my drafts" and "does it
  misfire on published work" are different questions with different answers.

Nothing here calibrates anything. It writes a labelling sheet and, once you
fill it in, reads it back and reports precision, recall and agreement with
explicit `unmeasured` states wherever a stratum is too thin to support a rate.

Run:  python tools/label_findings.py sample --field wgl --drafts path/to/drafts \\
          --n 60 --out labels.jsonl
      python tools/label_findings.py relabel --sheet labels.jsonl --frac 0.2 \\
          --out recheck.jsonl
      python tools/label_findings.py score --sheet labels.jsonl [--recheck recheck.jsonl]
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_register  # noqa: E402 -- because of that same sys.path insert
import deai_salience  # noqa: E402 -- because of that same sys.path insert
import extract_sections as es  # noqa: E402 -- because of that same sys.path insert

SCHEMA = "sci-paper.finding-labels.v1"
AXES = ("L0.register", "L2.salience_hierarchy")
MIN_PER_CELL = 20   # below this a rate is reported `unmeasured`, never as 0/0


def _passages(text: str) -> list[tuple[str, str]]:
    """(section bucket, passage) pairs from one document."""
    out = []
    for bucket, body in es.split_into_sections(text).items():
        if bucket in ("skip", es.DEFAULT_SECTION_BUCKET):
            continue
        for block in body.split("\n\n"):
            block = block.strip()
            if len(block.split()) >= 40:
                out.append((bucket, block))
    return out


def _findings_for(path: Path, field_dir: Path) -> list[dict]:
    """Every register and salience finding one document produces."""
    text = path.read_text(encoding="utf-8", errors="replace")
    found = []
    emitters = ((deai_register.register_findings, "L0.register"),
                (deai_salience.salience_findings, "L2.salience_hierarchy"))
    for emit, axis in emitters:
        try:
            result = emit(text, field_dir, path)
        except Exception as error:  # noqa: BLE001 -- because one unreadable document must not abort a sampling run
            found.append({"axis": axis, "error": str(error)})
            continue
        for item in (result or []):
            if isinstance(item, dict):
                found.append({"axis": axis, "finding": item})
    return found


def cmd_sample(args) -> int:
    field = cli_common.resolve_field(args.field, args.profile_root,
                                     tool="label_findings")
    field_dir = args.profile_root / field
    rng = random.Random(args.seed)

    populations: dict[str, list[Path]] = {}
    if args.drafts:
        populations["draft"] = sorted(Path(args.drafts).rglob("*.tex"))
    corpus = args.corpus_root / field
    if corpus.is_dir():
        populations["published"] = [p for p, _ in
                                    [(x, None) for x in sorted(corpus.rglob("*.tex"))]]
    if not any(populations.values()):
        raise SystemExit("[label_findings] no documents found; pass --drafts and/or "
                         "build a corpus under --corpus-root.")

    rows = []
    for population, paths in populations.items():
        if not paths:
            print(f"[label_findings] population {population!r} is empty; skipped",
                  file=sys.stderr)
            continue
        rng.shuffle(paths)
        per_population = max(1, args.n // len([p for p in populations.values() if p]))
        for path in paths:
            if sum(1 for r in rows if r["population"] == population) >= per_population:
                break
            for entry in _findings_for(path, field_dir):
                if "error" in entry:
                    continue
                rows.append({
                    "id": f"{population}-{len(rows):04d}",
                    "population": population,
                    "axis": entry["axis"],
                    "source": path.name,
                    "flagged": True,
                    "evidence": entry["finding"],
                    "label": None,          # <- you fill this in: true | false
                    "note": "",
                })
    # Unflagged controls make recall computable: a sheet of flags alone can only
    # ever report precision. Target roughly as many controls as flags in each
    # population, so neither side of the ratio is the one that starves.
    for population, paths in populations.items():
        flagged_here = sum(1 for r in rows
                           if r["population"] == population and r["flagged"])
        want = max(MIN_PER_CELL, flagged_here)
        made = 0
        for path in paths:
            if made >= want:
                break
            text = path.read_text(encoding="utf-8", errors="replace")
            flagged_text = {r["evidence"].get("text", "")[:200] for r in rows
                            if r["population"] == population and r["flagged"]
                            and isinstance(r.get("evidence"), dict)}
            for bucket, passage in _passages(text):
                if made >= want:
                    break
                if passage[:200] in flagged_text:
                    continue      # a flagged passage is not a control for itself
                rows.append({
                    "id": f"{population}-ctl-{len(rows):04d}",
                    "population": population,
                    "axis": "control",
                    "source": path.name,
                    "flagged": False,
                    "evidence": {"section": bucket, "text": passage[:1200]},
                    "label": None,
                    "note": "",
                })
                made += 1

    rng.shuffle(rows)
    args.out.write_text(
        "\n".join(json.dumps({"schema": SCHEMA, **row}, ensure_ascii=False)
                  for row in rows) + "\n", encoding="utf-8")
    by_population: dict[str, int] = {}
    for row in rows:
        by_population[row["population"]] = by_population.get(row["population"], 0) + 1
    print(f"[label_findings] {len(rows)} rows -> {args.out}")
    for population, count in sorted(by_population.items()):
        flagged = sum(1 for r in rows
                      if r["population"] == population and r["flagged"])
        print(f"    {population:10s} {count:4d} rows ({flagged} flagged, "
              f"{count - flagged} controls)")
    print('    Set "label" to true (the advisory is right) or false (it is not).')
    return 0


def cmd_relabel(args) -> int:
    rows = [json.loads(line) for line in
            args.sheet.read_text(encoding="utf-8").splitlines() if line.strip()]
    done = [r for r in rows if r.get("label") is not None]
    if not done:
        raise SystemExit("[label_findings] nothing labelled yet; fill in --sheet first.")
    rng = random.Random(args.seed)
    take = max(1, round(len(done) * args.frac))
    picked = rng.sample(done, take)
    rng.shuffle(picked)
    blind = [{**r, "label": None, "note": "", "_relabel_of": r["id"]} for r in picked]
    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in blind) + "\n",
        encoding="utf-8")
    print(f"[label_findings] {take} of {len(done)} rows re-served blind -> {args.out}")
    print("    Label them again without consulting the first pass.")
    return 0


def _rate(hits: int, total: int) -> str:
    if total < MIN_PER_CELL:
        return f"unmeasured (n={total} < {MIN_PER_CELL})"
    return f"{hits / total:.3f}  (n={total})"


def cmd_score(args) -> int:
    rows = [json.loads(line) for line in
            args.sheet.read_text(encoding="utf-8").splitlines() if line.strip()]
    labelled = [r for r in rows if r.get("label") is not None]
    if not labelled:
        raise SystemExit("[label_findings] no labels present in --sheet.")
    print(f"[label_findings] {len(labelled)} of {len(rows)} rows labelled\n")

    populations = sorted({r["population"] for r in labelled})
    for population in populations:
        print(f"population: {population}")
        for axis in AXES:
            flagged = [r for r in labelled
                       if r["population"] == population and r["axis"] == axis]
            controls = [r for r in labelled
                        if r["population"] == population and not r["flagged"]]
            true_positive = sum(1 for r in flagged if r["label"] is True)
            missed = sum(1 for r in controls if r["label"] is True)
            print(f"  {axis:24s} precision {_rate(true_positive, len(flagged))}")
            denominator = true_positive + missed
            print(f"  {'':24s} recall    {_rate(true_positive, denominator)}")
        print()

    if args.recheck and args.recheck.exists():
        second = {r["_relabel_of"]: r["label"] for r in
                  (json.loads(line) for line in
                   args.recheck.read_text(encoding="utf-8").splitlines() if line.strip())
                  if r.get("label") is not None}
        first = {r["id"]: r["label"] for r in labelled}
        shared = [k for k in second if k in first]
        if len(shared) < MIN_PER_CELL:
            print(f"intra-rater agreement: unmeasured (n={len(shared)} < {MIN_PER_CELL})")
        else:
            agree = sum(1 for k in shared if first[k] == second[k])
            observed = agree / len(shared)
            positive_first = statistics.mean(1 if first[k] else 0 for k in shared)
            positive_second = statistics.mean(1 if second[k] else 0 for k in shared)
            chance = (positive_first * positive_second
                      + (1 - positive_first) * (1 - positive_second))
            kappa = ((observed - chance) / (1 - chance)) if chance < 1 else float("nan")
            print(f"intra-rater agreement: {observed:.3f} raw, kappa {kappa:.3f} "
                  f"(n={len(shared)})")
            print("  This is the ceiling: no axis can be held to a precision above "
                  "the agreement the task itself supports.")
    else:
        print("intra-rater agreement: unmeasured (no --recheck sheet supplied)")
    return 0


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__, corpus=True)
    # The field options go on every subparser too: argparse routes everything
    # after the subcommand name to the subparser, so a root-only --field would
    # force `label_findings --field wgl sample`, unlike every other tool here.
    shared = [cli_common.field_options(corpus=True)]
    sub = parser.add_subparsers(dest="command", required=True)

    s = sub.add_parser("sample", parents=shared, help="write a labelling sheet")
    s.add_argument("--drafts", type=Path, default=None,
                   help="directory of your own .tex drafts")
    s.add_argument("--n", type=int, default=60)
    s.add_argument("--seed", type=int, default=20260826)
    s.add_argument("--out", type=Path, default=Path("labels.jsonl"))
    s.set_defaults(func=cmd_sample)

    r = sub.add_parser("relabel", parents=shared, help="re-serve a blind subset")
    r.add_argument("--sheet", type=Path, required=True)
    r.add_argument("--frac", type=float, default=0.2)
    r.add_argument("--seed", type=int, default=20260826)
    r.add_argument("--out", type=Path, default=Path("recheck.jsonl"))
    r.set_defaults(func=cmd_relabel)

    c = sub.add_parser("score", parents=shared,
                   help="report precision, recall and agreement")
    c.add_argument("--sheet", type=Path, required=True)
    c.add_argument("--recheck", type=Path, default=None)
    c.set_defaults(func=cmd_score)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
