"""Fidelity-free partition operators for the document dispersion band (L2).

EVALUATION.md section 9.1 shows word-level rewriting cannot move the
cross-paragraph dispersion signal; the only lever is the paragraph partition
itself. Merge (delete one blank line) and split (insert one blank line at a
sentence boundary) touch zero tokens, so every protected invariant (numbers,
citations, macros) is byte-identical and the rewrite fidelity gate cannot
fire, by construction.

This tool only SUGGESTS operations, ranked by how far they move the document
toward the calibrated human dispersion band (Mahalanobis manifold distance,
two-sided: over-uniform documents get variety-creating ops, over-dispersed
ones get smoothing ops). The author applies them by hand where the argument
allows. Cohesion is self-normalized against the document itself: a merge must
join paragraphs at least as lexically related as the document's median
adjacent pair, and a split must cut at a boundary no more related than that
same median - no tuned constants.

Reordering paragraphs is deliberately NOT offered: it changes reading order,
and admissibility would need a real claim-dependency analysis; guessing one
would violate the correctness-first contract.

Usage:
  python tools/deai_partition.py <file.tex> --field wgl [--max-ops 5]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_docstructure as ds  # noqa: E402  because sibling imports resolve only after the sys.path insert above
import deai_features as features  # noqa: E402  same sys.path reason
import deai_metrics as metrics  # noqa: E402  same sys.path reason
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
    """Sections as ordered raw paragraph blocks with original line spans."""
    lines = text.splitlines()
    sections = []
    for start, end, label in metrics.section_line_ranges(text):
        if label == "(preamble)":
            continue
        segment = "\n".join(lines[start - 1:end])
        # a block holding the \section command itself is a fixed landmark:
        # merging or splitting into it would be a nonsense suggestion
        blocks = [{"lines": (p_start, p_end), "text": block,
                   "fixed": block.lstrip().startswith("\\section")}
                  for p_start, p_end, block in
                  metrics.paragraph_line_ranges(segment, start)]
        if blocks:
            sections.append({"label": label, "blocks": blocks})
    return sections


def _measurable(block_text: str) -> bool:
    return len(es.words(es.latex_to_plain(block_text))) >= ds.MIN_WORDS


def _state_statistics(sections: list[dict], baseline: dict) -> dict | None:
    """Manifold distance (+ conformal p when available) of a partition state."""
    vectors = [ds._paragraph_modelfree(block["text"])
               for section in sections for block in section["blocks"]
               if _measurable(block["text"])]
    if len(vectors) < 2:
        return None
    dispersion = features.cross_paragraph_dispersion(
        vectors, list(ds.DISPERSION_FEATURE_NAMES))
    row = {name: dispersion[name][ds.DISPERSION_STAT]
           for name in dispersion
           if dispersion[name][ds.DISPERSION_STAT] is not None}
    operating = ds.manifold_operating_point(baseline, row, len(vectors))
    if operating is None:
        return None
    out = {"distance": operating["distance"], "n_paragraphs": len(vectors)}
    if operating["alpha"] is not None:
        out["conformal_p"] = operating["p_value"]
        out["calibration_basis"] = operating["calibration_basis"]
        out["alpha"] = operating["alpha"]
    return out


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
                left = " ".join(parts[:cut])
                right = " ".join(parts[cut:])
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
        parts = es.sentences(block["text"])
        left = " ".join(parts[:op["cut"]])
        right = " ".join(parts[op["cut"]:])
        blocks[op["block"]:op["block"] + 1] = [
            {"lines": block["lines"], "text": left, "derived": "split-left"},
            {"lines": block["lines"], "text": right, "derived": "split-right"},
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
    parts = es.sentences(block["text"])
    tail = " ".join(es.words(es.latex_to_plain(parts[op["cut"] - 1]))[-6:])
    return (f"SPLIT in [{section['label']}]: paragraph at lines "
            f"{block['lines'][0]}-{block['lines'][1]}, insert a blank line "
            f"after sentence {op['cut']} (ending '...{tail}'; boundary "
            f"overlap {op['overlap']:.2f})")


def suggest(text: str, baseline: dict, max_ops: int) -> dict:
    """Greedy band-seeking plan of admissible merge/split operations."""
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
        alpha = current.get("alpha")
        if alpha is not None and current.get("conformal_p", 0.0) > alpha:
            break  # inside the human band: nothing left to fix
        candidates = (_merge_candidates(state, floor)
                      + _split_candidates(state, floor))
        best = None
        for op in candidates:
            trial = _state_statistics(_apply(state, op), baseline)
            if trial is None:
                continue
            if trial["distance"] < current["distance"] and (
                    best is None or trial["distance"] < best[1]["distance"]):
                best = (op, trial)
        if best is None:
            break
        op, trial = best
        plan.append({"description": _describe(op, state),
                     "kind": op["kind"],
                     "distance_before": current["distance"],
                     "distance_after": trial["distance"],
                     "conformal_p_after": trial.get("conformal_p")})
        state, current = _apply(state, op), trial
    return {"status": "measured", "start": start, "end": current,
            "cohesion_floor": floor, "plan": plan}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--field", required=True)
    parser.add_argument("--profile-root", type=Path,
                        default=ds.DEFAULT_PROFILE_ROOT)
    parser.add_argument("--max-ops", type=int, default=MAX_OPS_DEFAULT)
    parser.add_argument("--json", type=Path, default=None,
                        help="also write the plan as JSON")
    args = parser.parse_args(argv)
    baseline = ds.load_baseline(args.profile_root / args.field)
    if baseline is None or not baseline.get("dispersion_manifold"):
        print("[deai_partition] no calibrated dispersion manifold for this "
              "field; run deai_docstructure --calibrate first", file=sys.stderr)
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
    line = f"  manifold distance {start['distance']:.3f}"
    if "conformal_p" in start:
        line += f", conformal p {start['conformal_p']:.4f} (alpha {start['alpha']:g})"
    print(line)
    if not result["plan"]:
        if ("conformal_p" in start and start.get("alpha") is not None
                and start["conformal_p"] > start["alpha"]):
            print("  already inside the human band; nothing to fix")
        else:
            print("  no admissible partition operation improves the band "
                  "distance")
        return 0
    for index, step in enumerate(result["plan"], 1):
        print(f"  {index}. {step['description']}")
        extra = (f" -> p {step['conformal_p_after']:.4f}"
                 if step.get("conformal_p_after") is not None else "")
        print(f"     distance {step['distance_before']:.3f} -> "
              f"{step['distance_after']:.3f}{extra}")
    verdict = ""
    if "conformal_p" in end and end.get("alpha") is not None:
        verdict = (" (inside the human band)"
                   if end["conformal_p"] > end["alpha"]
                   else " (still outside the band; apply and re-measure)")
    print(f"  projected: distance {start['distance']:.3f} -> "
          f"{end['distance']:.3f}{verdict}")
    print("  suggestions only - apply by hand where the argument allows; "
          "merge/split change zero tokens, so fidelity is preserved by "
          "construction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
