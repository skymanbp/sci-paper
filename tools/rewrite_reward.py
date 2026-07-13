"""Best-of-N reward with hard scientific-fidelity eligibility (L3-L4).

Candidates first pass deterministic preservation checks for numbers, units,
citations, mathematical expressions, named acronyms, semantic LaTeX macros,
comparison direction, negation, and causal direction. The check is
bidirectional: dropping a protected invariant AND inventing one the reference
does not carry both make a candidate ineligible, because specificity never
licenses invention and an added negation/causal/comparison marker can invert
meaning while every original token survives. Only eligible candidates are
ranked; ranking is led by deterministic L0 advisory reduction and semantic
fidelity, and the learned field-similarity score contributes materially only
when its bundle carries a measured operating point. A style score can never
rescue an ineligible candidate.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as df  # noqa: E402  sibling import after path setup
import deai_voice as dv  # noqa: E402  sibling import after path setup

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
_NUM_RE = re.compile(r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?(?:\s*[×x]\s*10\^?[-+]?\d+)?")
_CITE_RE = re.compile(r"\\cite\w*\{([^}]+)\}")
_MATH_RE = re.compile(r"\$([^$]+)\$")
_ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9-]{1,}\b")
_UNIT_RE = re.compile(
    r"(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?\s*(?:\\,)?\s*"
    r"(\\mathrm\{[^}]+\}|\\text\{[^}]+\}|[%°]|[A-Za-z]+(?:\s*[/-]\s*[A-Za-z]+)*)"
)
_DIRECTION_RE = re.compile(
    r"\b(increase[sd]?|decrease[sd]?|higher|lower|greater|less|above|below|"
    r"positive|negative|improve[sd]?|worsen(?:ed|s)?|exceed[sd]?|underperform(?:s|ed)?)\b",
    re.I,
)
_NEGATION_RE = re.compile(r"\b(not|no|without|cannot|can't|neither|nor)\b", re.I)
_CAUSAL_RE = re.compile(r"\b(because|therefore|thus|hence|causes?|leads? to|results? in|due to)\b", re.I)
_MACRO_RE = re.compile(r"\\([a-zA-Z]+)\*?")
# Pure-formatting commands whose loss cannot drop scientific content; every
# other macro may carry a quantity (\Nconfig -> 750) or a semantic object, so it
# is protected. Citation commands are covered separately by _CITE_RE.
_FORMATTING_MACROS = frozenset({
    "emph", "textbf", "textit", "texttt", "textsc", "textrm", "textup",
    "underline", "mbox", "hbox", "vspace", "hspace", "noindent", "centering",
    "raggedright", "small", "footnotesize", "scriptsize", "large",
    "item", "begin", "end", "label", "documentclass", "usepackage",
    "newcommand", "renewcommand", "left", "right", "par", "linebreak",
    "newline", "cite", "citep", "citet", "citealt", "citealp",
    "citeauthor", "citeyear",
})
# Meaning can flip when one of these categories GAINS a marker (adding "not",
# "therefore", or "lower" inverts or invents a claim), so additions there are
# just as disqualifying as drops.
_REVERSIBLE_CATEGORIES = (
    "negation", "comparison_direction", "causal_direction",
)

# The ranking term that used to be `specificity` (fraction of reference numbers
# preserved) is identically 1.0 for every eligible candidate, because
# fidelity_eligibility already rejects any candidate missing a reference number.
# A constant does no ranking work, so it is replaced by a real signal: the
# reduction in deterministic L0 rewrite targets (the writing improvement a
# rewrite exists to make), gated by a semantic-fidelity floor so a candidate
# cannot earn improvement credit by mangling meaning.
ADVISORY_REDUCTION_WEIGHT = 0.6   # inherits the retired `specificity` weight
FIDELITY_FLOOR = 0.5              # below this cosine, no positive reduction credit


def _l0_target_count(text: str, field_profile_dir: Path) -> int:
    """Deterministic L0 rewrite-target count (em-dash + Tier A + over-cap Tier B).

    Reused from ai_ism_lint, imported lazily so rewrite_reward stays importable
    without the linter and no module-load cycle is introduced. Location is a
    placeholder path; only the finding kinds are counted.
    """
    import ai_ism_lint as lint  # noqa: E402  lazy: avoid import cycle + optional dep
    findings, _axes = lint.lexical_findings(text, Path("<candidate>"),
                                            field_profile_dir)
    return sum(1 for finding in findings if finding.get("kind") == "l0_target")


def _advisory_reduction(ref_l0: int, cand_l0: int, fidelity: float) -> float:
    """Signed reduction in L0 targets, in [-1, 1], with a fidelity floor.

    Positive when a candidate removes reference L0 targets, negative when it
    adds them, zero when it neither helps nor hurts (so a clean reference gives
    no candidate spurious credit). Below ``FIDELITY_FLOOR`` a candidate cannot
    keep positive credit: it may not buy L0 improvement with mangled meaning.
    """
    denom = max(1, ref_l0, cand_l0)
    value = (ref_l0 - cand_l0) / denom
    if fidelity < FIDELITY_FLOOR:
        value = min(value, 0.0)
    return value


def _normalized(items) -> set[str]:
    return {re.sub(r"\s+", "", item).lower() for item in items}


def _numbers(text: str) -> set[str]:
    return _normalized(_NUM_RE.findall(df.es.latex_to_plain(text)))


def _citations(text: str) -> set[str]:
    keys = []
    for group in _CITE_RE.findall(text):
        keys.extend(key.strip() for key in group.split(",") if key.strip())
    return set(keys)


def _math(text: str) -> set[str]:
    return _normalized(_MATH_RE.findall(text))


def _acronyms(text: str) -> set[str]:
    return set(_ACRONYM_RE.findall(df.es.latex_to_plain(text)))


def _units(text: str) -> set[str]:
    return _normalized(_UNIT_RE.findall(text))


def _macros(text: str) -> set[str]:
    """Semantic macro names in the RAW text (latex_to_plain would erase them)."""
    return {name.lower() for name in _MACRO_RE.findall(text)
            if name.lower() not in _FORMATTING_MACROS}


def _markers(pattern: re.Pattern, text: str) -> set[str]:
    return {match.lower() for match in pattern.findall(df.es.latex_to_plain(text))}


def _cosine(left: str, right: str) -> float:
    import numpy as np
    embeddings = df._embedder().encode(
        [df.es.latex_to_plain(left), df.es.latex_to_plain(right)],
        normalize_embeddings=True,
    )
    return float(np.dot(embeddings[0], embeddings[1]))


def protected_invariants(text: str) -> dict[str, set[str]]:
    return {
        "numbers": _numbers(text),
        "units": _units(text),
        "citations": _citations(text),
        "math": _math(text),
        "acronyms": _acronyms(text),
        "latex_macros": _macros(text),
        "comparison_direction": _markers(_DIRECTION_RE, text),
        "negation": _markers(_NEGATION_RE, text),
        "causal_direction": _markers(_CAUSAL_RE, text),
    }


def fidelity_eligibility(candidate: str, reference: str) -> dict[str, Any]:
    """Bidirectional invariant check.

    ``missing``  = reference invariants the candidate dropped (all categories).
    ``invented`` = candidate invariants the reference does not carry. These are
    disqualifying in every category: added numbers/units/citations/macros are
    unsourced invention, and added negation/causal/comparison markers can invert
    the claim. A human may re-approve an "invented" candidate only after manual
    source-tracing outside this deterministic gate.
    """
    required = protected_invariants(reference)
    present = protected_invariants(candidate)
    missing = {
        category: sorted(values - present[category])
        for category, values in required.items()
        if values - present[category]
    }
    invented = {
        category: sorted(present[category] - required[category])
        for category in required
        if present[category] - required[category]
    }
    return {
        "eligible": not missing and not invented,
        "missing": missing,
        "invented": invented,
        "required": {key: sorted(values) for key, values in required.items()},
        "present": {key: sorted(values) for key, values in present.items()},
    }


def reward(candidate: str, reference: str, field_profile_dir: Path,
           centroid=None, ref_l0: int | None = None) -> dict[str, Any]:
    if centroid is None:
        centroid = df.corpus_centroid(field_profile_dir)
    voice = dv.voice_score(candidate, field_profile_dir, centroid=centroid)
    voice = 0.0 if voice is None else voice
    voice_calibrated = dv.bundle_measured(dv.load_voice_model(field_profile_dir))
    fidelity = _cosine(candidate, reference)
    required_numbers = _numbers(reference)
    candidate_numbers = _numbers(candidate)
    # Reported for transparency (confirms eligibility), but NOT a ranking term:
    # it is identically 1.0 for every eligible candidate. See ADVISORY_REDUCTION.
    specificity = (len(required_numbers & candidate_numbers) / len(required_numbers)
                   if required_numbers else 1.0)
    if ref_l0 is None:
        ref_l0 = _l0_target_count(reference, field_profile_dir)
    cand_l0 = _l0_target_count(candidate, field_profile_dir)
    advisory_reduction = _advisory_reduction(ref_l0, cand_l0, fidelity)
    eligibility = fidelity_eligibility(candidate, reference)
    return {
        "voice": voice,
        "voice_calibrated": voice_calibrated,
        "fidelity": fidelity,
        "specificity": specificity,
        "advisory_reduction": advisory_reduction,
        "n_l0_ref": ref_l0,
        "n_l0_cand": cand_l0,
        "n_num_ref": len(required_numbers),
        "n_num_cand": len(candidate_numbers),
        "faithful": eligibility["eligible"],
        "missing_invariants": eligibility["missing"],
        "invented_invariants": eligibility["invented"],
    }


def rank(candidates: list[str], reference: str, field_profile_dir: Path
         ) -> list[tuple[int, dict[str, Any]]]:
    """Rank eligible candidates first; ineligible candidates can never win.

    L0 advisory reduction and semantic fidelity lead the ranking. The learned
    L3 score is a low-weight tie-break unless its bundle is measured/calibrated,
    so an uncalibrated field-similarity model can never be the deciding term
    (SCIPAPER_STANDARD section 9.5: lower detector visibility is not
    independently valuable).
    """
    centroid = df.corpus_centroid(field_profile_dir)
    ref_l0 = _l0_target_count(reference, field_profile_dir)   # constant across candidates
    scored = []
    for index, candidate in enumerate(candidates):
        result = reward(candidate, reference, field_profile_dir, centroid, ref_l0=ref_l0)
        if result["faithful"]:
            voice_weight = 0.4 if result["voice_calibrated"] else 0.05
            result["combined"] = (
                ADVISORY_REDUCTION_WEIGHT * result["advisory_reduction"]
                + 0.3 * result["fidelity"]
                + voice_weight * result["voice"]
            )
        else:
            result["combined"] = float("-inf")
        scored.append((index, result))
    scored.sort(key=lambda item: (
        item[1]["faithful"], item[1]["combined"], item[1]["fidelity"]),
        reverse=True)
    return scored


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--field", required=True)
    parser.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    parser.add_argument("--reference", type=Path, required=True,
                        help="distilled claim and protected scientific content")
    parser.add_argument("--candidates", type=Path, nargs="+", required=True)
    args = parser.parse_args(argv)
    field_dir = args.profile_root / args.field
    if dv.load_voice_model(field_dir) is None:
        print(f"[rewrite_reward] no voice_model.joblib in {field_dir}", file=sys.stderr)
        return 2
    reference = args.reference.read_text(encoding="utf-8", errors="replace")
    candidates = [path.read_text(encoding="utf-8", errors="replace")
                  for path in args.candidates]
    ranked = rank(candidates, reference, field_dir)
    print(f"{'rank':>4} {'cand':>4} {'combined':>9} {'voice':>7} "
          f"{'fidelity':>9} {'Δadv':>6} {'eligible':>8}  L0(r/c)")
    for position, (index, result) in enumerate(ranked, 1):
        combined = result["combined"]
        combined_text = "-inf" if combined == float("-inf") else f"{combined:.3f}"
        print(f"{position:>4} {index:>4} {combined_text:>9} "
              f"{result['voice']:>7.3f} {result['fidelity']:>9.3f} "
              f"{result['advisory_reduction']:>6.2f} {str(result['faithful']):>8}  "
              f"{result['n_l0_ref']}/{result['n_l0_cand']}  "
              f"{args.candidates[index].name}")
        if result["missing_invariants"]:
            print(f"     missing: {result['missing_invariants']}")
        if result["invented_invariants"]:
            print(f"     invented: {result['invented_invariants']}")
    eligible = [item for item in ranked if item[1]["faithful"]]
    if not eligible:
        print("\n[rewrite_reward] no candidate preserved all protected invariants",
              file=sys.stderr)
        return 2
    best_index = eligible[0][0]
    print(f"\n[best] candidate {best_index}: {args.candidates[best_index].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
