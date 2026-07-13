"""Editing-provenance ledger (cooperative layer, frontier idea 4).

Inverts the detection question. Instead of "is this AI?" it asks the question a
researcher actually owns: "have my edits made this text mine?" Given the
author's own draft history -- a designated AI-draft ancestor (a git ref or an
earlier file) and the current draft -- it matches each current paragraph to its
nearest ancestor paragraph and measures how much the author has since changed
it, then labels every span:

  ai_untouched    -- still essentially the AI draft (edit it or own the claim)
  lightly_edited  -- surface edits only
  rewritten       -- substantially the author's words, same idea
  author_original -- no close ancestor; written by the author

This never enters the arms race and never asserts authorship of anyone else's
text: it reads only the author's own supplied history. With no ancestor it is
honestly ``unmeasured`` -- a document with no recorded AI draft has no provenance
to report, which is not the same as being clean. The measure is a deterministic
token edit ratio (difflib), so it needs no model and no GPU.

CLI:
  python tools/deai_provenance.py draft.tex --ai-ancestor draft.ai.tex
  python tools/deai_provenance.py draft.tex --git-ai-ref <commit>   # ancestor from git
Lib:
  from deai_provenance import document_provenance, document_findings
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_style as es       # noqa: E402  resolves only after the sys.path insert
import deai_feedback as feedback  # noqa: E402  shared finding contract

MIN_WORDS = 12                 # ignore trivial fragments (titles, stray lines)
# Similarity (difflib token ratio, in [0, 1]) buckets. Higher similarity to the
# AI ancestor means the author changed less, i.e. lower authorship depth.
UNTOUCHED_SIM = 0.95           # >= this: essentially the AI draft, unedited
LIGHT_SIM = 0.65               # >= this: surface edits only
MATCH_SIM = 0.30               # below this: no meaningful ancestor -> author-original
# Authorship depth per label: 0 = still AI, 1 = fully the author's.
DEPTH = {"ai_untouched": 0.0, "lightly_edited": 0.4,
         "rewritten": 0.8, "author_original": 1.0}


def _paragraphs(text: str) -> list[tuple[int, int, str]]:
    """(start_line, end_line, block) per blank-line paragraph with enough prose
    words to carry a claim; line numbers are 1-based source lines so a finding's
    location points at the real paragraph, matching the sibling detectors."""
    lines = text.splitlines()
    out: list[tuple[int, int, str]] = []
    index = 0
    while index < len(lines):
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines):
            break
        start = index + 1                       # 1-based first line of the block
        block_lines = []
        while index < len(lines) and lines[index].strip():
            block_lines.append(lines[index])
            index += 1
        end = index                             # 1-based last non-blank line
        block = "\n".join(block_lines).strip()
        if block and len(es.words(es.latex_to_plain(block))) >= MIN_WORDS:
            out.append((start, end, block))
    return out


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in es.words(es.latex_to_plain(text))]


def _similarity(new_tokens: list[str], old_tokens: list[str]) -> float:
    """difflib token ratio in [0, 1]; 1.0 = identical token sequences."""
    if not new_tokens and not old_tokens:
        return 1.0
    if not new_tokens or not old_tokens:
        return 0.0
    return difflib.SequenceMatcher(None, old_tokens, new_tokens).ratio()


def _classify(similarity: float) -> str:
    if similarity >= UNTOUCHED_SIM:
        return "ai_untouched"
    if similarity >= LIGHT_SIM:
        return "lightly_edited"
    if similarity >= MATCH_SIM:
        return "rewritten"
    return "author_original"


def _best_ancestor(new_tokens: list[str],
                   ancestor_tokens: list[list[str]]) -> tuple[int, float]:
    """Index and similarity of the closest ancestor paragraph (-1 if none)."""
    best_index, best_sim = -1, 0.0
    for index, old in enumerate(ancestor_tokens):
        sim = _similarity(new_tokens, old)
        if sim > best_sim:
            best_index, best_sim = index, sim
    return best_index, best_sim


def document_provenance(current_text: str, ancestor_text: str) -> dict[str, Any]:
    """Per-paragraph authorship-depth ledger of ``current_text`` vs an ancestor.

    Returns ``status`` (``measured`` when both sides have paragraphs, otherwise
    ``unmeasured``), the per-paragraph ``ledger``, and a ``summary`` with the
    label mix and a word-weighted mean authorship depth in [0, 1].
    """
    current = _paragraphs(current_text)
    ancestor = _paragraphs(ancestor_text)
    if not current or not ancestor:
        return {"status": "unmeasured",
                "reason": "current or ancestor draft has no substantial paragraphs",
                "ledger": [], "summary": {}}
    ancestor_tokens = [_tokens(block) for _start, _end, block in ancestor]
    ledger = []
    for index, (start_line, end_line, para) in enumerate(current):
        new_tokens = _tokens(para)
        anc_index, sim = _best_ancestor(new_tokens, ancestor_tokens)
        label = _classify(sim)
        ledger.append({
            "paragraph": index,
            "start_line": start_line,
            "end_line": end_line,
            "n_words": len(new_tokens),
            "ancestor_paragraph": anc_index if sim >= MATCH_SIM else None,
            "similarity_to_ancestor": round(sim, 4),
            "label": label,
            "authorship_depth": DEPTH[label],
        })
    total_words = sum(entry["n_words"] for entry in ledger) or 1
    weighted_depth = sum(entry["authorship_depth"] * entry["n_words"]
                         for entry in ledger) / total_words
    counts = {label: 0 for label in DEPTH}
    for entry in ledger:
        counts[entry["label"]] += 1
    return {
        "status": "measured",
        "reason": None,
        "ledger": ledger,
        "summary": {
            "n_paragraphs": len(ledger),
            "label_counts": counts,
            "ai_untouched_fraction": counts["ai_untouched"] / len(ledger),
            "mean_authorship_depth": weighted_depth,
        },
    }


def git_file_at(path: Path, ref: str) -> str | None:
    """Contents of ``path`` at git ``ref`` from the author's own history, or None.

    Runs ``git show <ref>:<relpath>`` in the file's repository. Returns None when
    git is absent, the path is untracked, or the ref does not exist -- every
    failure keeps provenance honestly ``unmeasured`` rather than guessing.
    """
    path = path.resolve()
    try:
        top = subprocess.run(
            ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=15)
        if top.returncode != 0:
            return None
        repo = Path(top.stdout.strip())
        rel = path.relative_to(repo).as_posix()
        show = subprocess.run(
            ["git", "-C", str(repo), "show", f"{ref}:{rel}"],
            capture_output=True, text=True, timeout=15)
        if show.returncode != 0:
            return None
        return show.stdout
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def document_findings(current_text: str, path: str | Path | None,
                      ancestor_text: str | None,
                      no_ancestor_reason: str | None = None
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Findings + axis status for the provenance ledger.

    Emits one advisory per ``ai_untouched`` span: the cooperative signal that a
    paragraph is still the AI draft and needs the author's edit or explicit
    ownership. Confidence is the deterministic similarity, not an AI-ness guess,
    so paragraph-unit findings here are not capped. With no ancestor the axis is
    ``unmeasured`` and no finding is emitted; ``no_ancestor_reason`` lets the
    caller distinguish "none supplied" from "supplied but unreadable at that ref".
    """
    axis_name = "L4.editing_provenance"
    if ancestor_text is None:
        return [], [feedback.axis_status(
            axis_name, "unmeasured",
            reason=(no_ancestor_reason
                    or "no AI-draft ancestor supplied (--ai-ancestor / --git-ai-ref)"),
            detector="deai_provenance")]
    result = document_provenance(current_text, ancestor_text)
    if result["status"] != "measured":
        return [], [feedback.axis_status(axis_name, "unmeasured",
                                         reason=result["reason"],
                                         detector="deai_provenance")]
    findings = []
    for entry in result["ledger"]:
        if entry["label"] != "ai_untouched":
            continue
        findings.append(feedback.make_finding(
            kind="advisory", layer="L4", rule="provenance:ai-untouched",
            scope="paragraph", line=entry["start_line"],
            end_line=entry["end_line"], path=path,
            detector="deai_provenance",
            detector_version="sci-paper.provenance.v1",
            measurement_status="measured", strength="ordinary",
            observed={"similarity_to_ancestor": entry["similarity_to_ancestor"],
                      "authorship_depth": entry["authorship_depth"]},
            reference={"ancestor_paragraph": entry["ancestor_paragraph"]},
            normalized_distance=1.0 - entry["authorship_depth"],
            confidence={"value": entry["similarity_to_ancestor"],
                        "basis": "deterministic token edit ratio vs AI ancestor"},
            message=("This paragraph is essentially unchanged from the AI draft "
                     f"(similarity {entry['similarity_to_ancestor']:.2f})."),
            action=("Rewrite it in your own words or confirm you own the claim; "
                    "provenance is advisory, never an eligibility gate.")))
    axes = [feedback.axis_status(
        axis_name, "measured",
        reason=(f"mean authorship depth "
                f"{result['summary']['mean_authorship_depth']:.2f}; "
                f"{result['summary']['label_counts']['ai_untouched']} AI-untouched "
                f"of {result['summary']['n_paragraphs']} paragraphs"),
        detector="deai_provenance")]
    return findings, axes


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--ai-ancestor", type=Path,
                        help="an earlier AI-draft file to compare against")
    parser.add_argument("--git-ai-ref",
                        help="git ref whose version of FILE is the AI draft")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if not args.file.exists():
        print(f"[deai_provenance] file not found: {args.file}", file=sys.stderr)
        return 2
    current = args.file.read_text(encoding="utf-8", errors="replace")
    ancestor = None
    no_ancestor_reason = None
    if args.ai_ancestor is not None:
        if not args.ai_ancestor.exists():
            print(f"[deai_provenance] ancestor not found: {args.ai_ancestor}",
                  file=sys.stderr)
            return 2
        ancestor = args.ai_ancestor.read_text(encoding="utf-8", errors="replace")
    elif args.git_ai_ref is not None:
        ancestor = git_file_at(args.file, args.git_ai_ref)
        if ancestor is None:
            no_ancestor_reason = (f"git ref {args.git_ai_ref} unreadable or "
                                  f"untracked for this file")
            print(f"[deai_provenance] could not read {args.file} at git ref "
                  f"{args.git_ai_ref}; provenance is unmeasured", file=sys.stderr)
    findings, axes = document_findings(current, args.file, ancestor,
                                       no_ancestor_reason=no_ancestor_reason)
    if args.format == "json":
        report = feedback.build_report(path=args.file, findings=findings, axes=axes)
        print(feedback.dump_report(report), end="")
        return 0
    for axis in axes:
        detail = f": {axis['reason']}" if axis.get("reason") else ""
        print(f"axis {axis['axis']}: {axis['status']}{detail}")
    if ancestor is not None:
        result = document_provenance(current, ancestor)
        if result["status"] == "measured":
            for label, count in result["summary"]["label_counts"].items():
                print(f"  {label}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
