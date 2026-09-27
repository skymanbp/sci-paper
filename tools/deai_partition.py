"""Fidelity-free partition operators for the document dispersion band (L2).

EVALUATION.md section 9.1 shows word-level rewriting cannot move the
cross-paragraph dispersion signal; the only lever is the paragraph partition
itself. Merge (delete one blank line) and split (insert one blank line at a
sentence boundary) touch zero tokens, so every protected invariant (numbers,
citations, macros) is byte-identical and the rewrite fidelity gate cannot
fire, by construction.

This tool only SUGGESTS operations, ranked by how far they move the document
into the calibrated human dispersion band: states are compared by their
split-conformal p against the human reference (higher = deeper inside the
band; two-sided, so over-uniform documents get variety-creating ops and
over-dispersed ones get smoothing ops), with the raw Mahalanobis distance as
a tie-break only between states scored on one calibration basis. The author
applies them by hand where the argument allows. Cohesion is self-normalized
against the document itself: a merge must join paragraphs at least as
lexically related as the document's median adjacent pair, and a split must
cut at a boundary no more related than that same median - no tuned constants.

Reordering paragraphs is deliberately NOT offered: it changes reading order,
and admissibility would need a real claim-dependency analysis; guessing one
would violate the correctness-first contract.

Usage:
  python tools/deai_partition.py <file.tex> --field wgl [--max-ops 5]
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_docstructure as ds  # noqa: E402  because sibling imports resolve only after the sys.path insert above
import deai_features as features  # noqa: E402  same sys.path reason
import extract_sections  # noqa: E402  same sys.path reason; RE_HEADING_COMMAND
import extract_style as es  # noqa: E402  same sys.path reason

MIN_SPLIT_SENTENCES = 4      # both halves must keep >= 2 sentences
MAX_OPS_DEFAULT = 5


def _content_words(text: str) -> set[str]:
    """Content-word proxy: lowercase plain-text words of length >= 4."""
    return {w.lower() for w in es.words(es.latex_to_plain(text)) if len(w) >= 4}


def _overlap(a: str, b: str) -> float:
    """Jaccard overlap of content-word sets (0 when either side is empty)."""
    wa, wb = _content_words(a), _content_words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _parse(text: str) -> list[dict]:
    """Sections as ordered paragraph blocks with original line spans.

    The prose blocks are `deai_docshape.shape_units`' own, headings and floats
    blanked, so the preamble and every `skip` unit are absent here exactly as
    they are absent from the measurement a plan is scored on. What the
    blanking took out between them -- a heading on its own line, a float
    standing between paragraphs -- stays as a `landmark` block of raw text:
    fixed and never scored, so no merge is offered across it ("delete the
    blank line" would not describe one). A prose block whose raw text still
    starts with a heading command (a heading sharing its line with a `\\label`)
    is fixed too: merging or splitting into a heading would be a nonsense
    suggestion. Any heading command counts (`\\subsection`, `\\chapter`, ...);
    until 2026-09-27 only `\\section` did, and a subsection heading was
    offered as a merge partner.
    """
    lines = text.splitlines()
    sections = []
    for unit in ds.shape_units(text):
        blocks, cursor = [], unit["start_line"]
        for p_start, p_end, block in unit["blocks"]:
            blocks += _landmark(lines, cursor, p_start - 1)
            raw = "\n".join(lines[p_start - 1:p_end])
            blocks.append({"lines": (p_start, p_end), "text": block,
                           "fixed": bool(extract_sections.RE_HEADING_COMMAND.match(
                               raw.lstrip()))})
            cursor = p_end + 1
        blocks += _landmark(lines, cursor, unit["end_line"])
        if blocks:
            sections.append({"label": unit["label"], "blocks": blocks})
    return sections


def _landmark(lines: list[str], first: int, last: int) -> list[dict]:
    """The raw text between lines `first` and `last` that no prose block holds,
    as one fixed, unscored block (none when those lines are blank)."""
    filled = [number for number in range(first, last + 1) if lines[number - 1].strip()]
    if not filled:
        return []
    return [{"lines": (filled[0], filled[-1]), "fixed": True, "landmark": True,
             "text": "\n".join(lines[filled[0] - 1:filled[-1]])}]


def _state_statistics(sections: list[dict], baseline: dict) -> dict | None:
    """Manifold distance and split-conformal p of a partition state.

    The blocks scored -- every block but the landmarks -- are exactly the ones
    `document_shape` scores, through the shared `measurable_sections` filter
    (word floor, paragraphs per section, sections per document), so the
    starting distance printed here is the one `deai_docstructure` reports for
    the same file. `calibration_basis` names the manifold and calibration set
    the numbers came from; a state below the document-shape floor, or one the
    axis cannot score, is None.
    """
    units = [{"blocks": [(b["lines"][0], b["lines"][1], b["text"])
                         for b in section["blocks"] if not b.get("landmark")]}
             for section in sections]
    kept = ds.measurable_sections(units)
    if len(kept) < ds.MIN_SECTIONS:
        return None
    vectors = [ds._paragraph_modelfree(block)
               for unit in kept for _start, _end, block in unit["blocks"]]
    dispersion = features.cross_paragraph_dispersion(
        vectors, list(ds.DISPERSION_FEATURE_NAMES))
    row = {name: dispersion[name][ds.DISPERSION_STAT]
           for name in dispersion
           if dispersion[name][ds.DISPERSION_STAT] is not None}
    operating = ds.manifold_operating_point(baseline, row, len(vectors))
    if operating is None:
        return None
    return {"distance": operating["distance"], "n_paragraphs": len(vectors),
            "calibration_basis": operating["calibration_basis"],
            "conformal_p": operating["p_value"], "alpha": operating["alpha"]}


def _split_at(block_text: str, cut: int) -> tuple[str, str]:
    """The block cut after its `cut`-th sentence, at that boundary's own offset.

    The boundary is located in the ORIGINAL block text with the pattern
    `es.sentences` splits on, so the k-th boundary here is the k-th sentence
    end there, and both halves keep their line breaks. Re-joining the
    sentence list with spaces turned every newline into a space, so a
    `% note` at the end of a line commented out the rest of the paragraph:
    the ranking and the quoted `distance_after` were computed on a half that
    had lost its prose. The suggestion was always zero-token; the state being
    scored was not the state the author would get.
    """
    boundary = list(es.RE_SENTENCE_END.finditer(block_text))[cut - 1]
    return block_text[:boundary.start()], block_text[boundary.end():]


def _merge_candidates(sections: list[dict], floor: float) -> list[dict]:
    ops = []
    for s_index, section in enumerate(sections):
        for b_index in range(len(section["blocks"]) - 1):
            first = section["blocks"][b_index]
            second = section["blocks"][b_index + 1]
            if first.get("fixed") or second.get("fixed"):
                continue
            overlap = _overlap(first["text"], second["text"])
            if overlap >= floor:
                ops.append({"kind": "merge", "section": s_index,
                            "block": b_index, "overlap": overlap})
    return ops


def _split_candidates(sections: list[dict], floor: float) -> list[dict]:
    ops = []
    for s_index, section in enumerate(sections):
        for b_index, block in enumerate(section["blocks"]):
            if block.get("fixed"):
                continue
            parts = es.sentences(block["text"])
            if len(parts) < MIN_SPLIT_SENTENCES:
                continue
            best = None
            for cut in range(2, len(parts) - 1):
                left, right = _split_at(block["text"], cut)
                overlap = _overlap(left, right)
                if best is None or overlap < best[1]:
                    best = (cut, overlap)
            if best is not None and best[1] <= floor:
                ops.append({"kind": "split", "section": s_index,
                            "block": b_index, "cut": best[0],
                            "overlap": best[1]})
    return ops


def _apply(sections: list[dict], op: dict) -> list[dict]:
    """Return a new state with the operation applied (originals untouched)."""
    new_sections = [{"label": s["label"], "blocks": list(s["blocks"])}
                    for s in sections]
    blocks = new_sections[op["section"]]["blocks"]
    if op["kind"] == "merge":
        first, second = blocks[op["block"]], blocks[op["block"] + 1]
        merged = {"lines": (first["lines"][0], second["lines"][1]),
                  "text": first["text"] + "\n" + second["text"]}
        blocks[op["block"]:op["block"] + 2] = [merged]
    else:
        block = blocks[op["block"]]
        left, right = _split_at(block["text"], op["cut"])
        start, end = block["lines"]
        blocks[op["block"]:op["block"] + 1] = [
            {"lines": (start, start + left.count("\n")), "text": left,
             "derived": "split-left"},
            {"lines": (end - right.count("\n"), end), "text": right,
             "derived": "split-right"},
        ]
    return new_sections


def _describe(op: dict, sections: list[dict]) -> str:
    section = sections[op["section"]]
    if op["kind"] == "merge":
        first = section["blocks"][op["block"]]
        second = section["blocks"][op["block"] + 1]
        return (f"MERGE in [{section['label']}]: join paragraphs at lines "
                f"{first['lines'][0]}-{first['lines'][1]} and "
                f"{second['lines'][0]}-{second['lines'][1]} "
                f"(delete the blank line; lexical overlap {op['overlap']:.2f})")
    block = section["blocks"][op["block"]]
    left, _right = _split_at(block["text"], op["cut"])
    tail = " ".join(es.words(es.latex_to_plain(left))[-6:])
    return (f"SPLIT in [{section['label']}]: paragraph at lines "
            f"{block['lines'][0]}-{block['lines'][1]}, insert a blank line "
            f"after sentence {op['cut']} (ending '...{tail}'; boundary "
            f"overlap {op['overlap']:.2f})")


def _improves(trial: dict, over: dict) -> bool:
    """Whether `trial` sits deeper inside the human band than `over`.

    States are compared by conformal p, which stays meaningful when a plan
    step changes the paragraph count and so crosses a length-stratum edge.
    Raw manifold distance is only a tie-break, and only between states scored
    on one calibration basis: a distance from the stratum-1 manifold and one
    from the stratum-2 manifold are different quantities
    (`deai_docshape.manifold_operating_point`). Until 2026-09-27 the greedy
    step compared raw distances across that switch, and stopped on p while
    advancing on distance.
    """
    if trial["conformal_p"] != over["conformal_p"]:
        return trial["conformal_p"] > over["conformal_p"]
    return (trial["calibration_basis"] == over["calibration_basis"]
            and trial["distance"] < over["distance"])


def suggest(text: str, baseline: dict, max_ops: int) -> dict:
    """Greedy band-seeking plan of admissible merge/split operations."""
    uncalibrated = ds.uncalibrated_manifold_reason(baseline)
    if uncalibrated:  # no state is scored against such a baseline, whatever the document
        return {"status": "unmeasured", "reason": uncalibrated, "plan": []}
    sections = _parse(text)
    start = _state_statistics(sections, baseline)
    if start is None:
        return {"status": "unmeasured",
                "reason": "document or manifold not measurable", "plan": []}
    # self-normalized cohesion reference: median adjacent-pair overlap
    adjacent = [_overlap(s["blocks"][i]["text"], s["blocks"][i + 1]["text"])
                for s in sections for i in range(len(s["blocks"]) - 1)]
    if not adjacent:
        return {"status": "unmeasured",
                "reason": "no adjacent paragraph pairs", "plan": []}
    floor = statistics.median(adjacent)
    state, current = sections, start
    plan = []
    for _ in range(max_ops):
        if current["conformal_p"] > current["alpha"]:
            break  # inside the human band: nothing left to fix
        candidates = (_merge_candidates(state, floor)
                      + _split_candidates(state, floor))
        best = None
        for op in candidates:
            trial = _state_statistics(_apply(state, op), baseline)
            if trial is None or not _improves(trial, current):
                continue
            if best is None or _improves(trial, best[1]):
                best = (op, trial)
        if best is None:
            break
        op, trial = best
        # Every step records the basis on both sides, so a manifold switch
        # between two consecutive distances is visible in the plan itself.
        plan.append({"description": _describe(op, state),
                     "kind": op["kind"],
                     "distance_before": current["distance"],
                     "distance_after": trial["distance"],
                     "conformal_p_before": current.get("conformal_p"),
                     "conformal_p_after": trial.get("conformal_p"),
                     "calibration_basis_before": current["calibration_basis"],
                     "calibration_basis_after": trial["calibration_basis"]})
        state, current = _apply(state, op), trial
    return {"status": "measured", "start": start, "end": current,
            "cohesion_floor": floor, "plan": plan}


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--max-ops", type=int, default=MAX_OPS_DEFAULT)
    parser.add_argument("--json", type=Path, default=None,
                        help="also write the plan as JSON")
    args = parser.parse_args(argv)
    if not args.file.exists():
        print(f"[deai_partition] file not found: {args.file}", file=sys.stderr)
        return 2
    field_dir = cli_common.optional_field_dir(args, tool="deai_partition")
    baseline = ds.load_baseline(field_dir)
    if baseline is None or not baseline.get("dispersion_manifold"):
        where = f"under {field_dir}" if field_dir else "(no field profile resolved)"
        print(f"[deai_partition] no calibrated dispersion manifold {where}; "
              "run deai_docstructure --calibrate --field <name> first",
              file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    result = suggest(text, baseline, args.max_ops)
    if args.json:
        args.json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if result["status"] != "measured":
        print(f"[deai_partition] {result['reason']}")
        return 0
    start, end = result["start"], result["end"]
    print(f"[deai_partition] {args.file}")
    print(f"  manifold distance {start['distance']:.3f} ({start['calibration_basis']}), "
          f"conformal p {start['conformal_p']:.4f} (alpha {start['alpha']:g})")
    if not result["plan"]:
        if start["conformal_p"] > start["alpha"]:
            print("  already inside the human band; nothing to fix")
        else:
            print("  no admissible partition operation moves the document "
                  "deeper into the band")
        return 0
    for index, step in enumerate(result["plan"], 1):
        print(f"  {index}. {step['description']}")
        extra = (f", p {step['conformal_p_before']:.4f} -> "
                 f"{step['conformal_p_after']:.4f}")
        if step["calibration_basis_before"] != step["calibration_basis_after"]:
            extra += (f" [calibration basis {step['calibration_basis_before']} -> "
                      f"{step['calibration_basis_after']}: the two distances "
                      "are not on one scale]")
        print(f"     distance {step['distance_before']:.3f} -> "
              f"{step['distance_after']:.3f}{extra}")
    verdict = (" (inside the human band)" if end["conformal_p"] > end["alpha"]
               else " (still outside the band; apply and re-measure)")
    print(f"  projected: conformal p {start['conformal_p']:.4f} -> "
          f"{end['conformal_p']:.4f}{verdict}")
    print("  suggestions only - apply by hand where the argument allows; "
          "merge/split change zero tokens, so fidelity is preserved by "
          "construction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
