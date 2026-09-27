"""Best-of-N reward with hard scientific-fidelity eligibility (L3-L4).

Candidates first pass deterministic preservation checks for numbers, units,
citations, mathematical expressions, named acronyms, semantic LaTeX macros,
comparison direction, negation, and causal direction. The check is
bidirectional: dropping a protected invariant AND inventing one the reference
does not carry both make a candidate ineligible, because specificity never
licenses invention and an added negation/causal/comparison marker can invert
meaning while every original token survives. Numbers and the three marker
categories are compared as bags (``collections.Counter``), not sets: ``not``
said twice is not preserved by ``not`` said once, nor a value stated twice by
one copy of it. A bag is blind to position, and that is the residual limit: a
negation or causal marker moved into another clause, or two distinct numbers
exchanging places, changes no count and passes this gate -- the by-hand
verification the de-ai skill requires after it covers that class, and the
report's ``count mismatch`` line says where a bag came up short rather than
empty.

Only eligible candidates are ranked; ranking is led by deterministic L0
advisory reduction and semantic fidelity, and the learned field-similarity
score contributes materially only when its bundle carries a measured operating
point. A style score can never rescue an ineligible candidate. Every learned
or embedded term is optional and degrades visibly instead of blocking the
gate: with no field profile or no ``voice_model.joblib`` the voice term is
unmeasured at weight 0, and with sentence-transformers uninstalled the
semantic-fidelity cosine is unmeasured at weight 0 and cannot apply its floor.
Each case prints one stderr line naming what is missing; the exit status stays
0/1 by eligibility, and 2 is reserved for invalid input and crashes.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_features as df  # noqa: E402  sibling import after path setup
import deai_voice as dv  # noqa: E402  sibling import after path setup

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
# The numeral tokenizer, with the record of its corrections. Every entry is
# pinned by a test in tests/test_rewrite_reward.py; extend the record, do not
# prune it. Five of the six are one root cause -- a neighbour absorbed into
# the token, or the token started inside a neighbour.
#
# (1) A numeral token must END in a digit. `\d[\d,]*` was greedy across the
# comma that separates list items, so "1200, 2400, and 4800" tokenized as
# {"1200,", "2400,", "4800"} and a candidate that merely dropped the Oxford
# comma was reported as simultaneously MISSING "2400," and INVENTING "2400"
# -- a faithful rewrite hard-rejected (combined = -inf) on punctuation. The
# thousands separator inside a number ("1,234") is still captured.
#
# (2) A leading-dot decimal (".06") is a number of its own (2026-09-27): once
# (6) stopped a token starting after a dot, the junk "06" it used to yield
# would have become nothing at all, and a changed ".06" would go unprotected.
# (3) An exponent is part of the number (2026-09-27): `1.5e-3` tokenized as
# {"1.5", "3"}, the exponent's sign lost, so `1.5e-3` -> `1.5e+3` passed.
_NUMBER_BODY = r"(?:\d(?:[\d,]*\d)?(?:\.\d+)?|\.\d+)(?:[eE][-+]?\d+)?"
# (4) ...and it must not swallow the separator in FRONT of it either, which is
# the same root cause a third time. `[-+]?` accepted a sign directly after a
# digit, so the range "0.5-1.2 arcsec" tokenized as {"0.5", "-1.2"}. A rewrite
# saying "from 0.5 to 1.2" was then reported as MISSING "-1.2" and INVENTING
# "1.2" and hard-rejected -- and every hyphenated range in a reference did the
# same, which is most of them ("5-40", "24.0-26.0", "0.01-0.06"). A sign is a
# sign only where one can occur: not straight after a digit or a decimal point,
# where `-` separates a range and `+` states a tolerance. Exponents (`10^-3`)
# and genuine negatives after a space or brace are unaffected.
#
# (5) Nor straight after another sign character (2026-09-27). The LaTeX
# en-dash range "0.5--1.2" puts a hyphen before its second hyphen, which (4)
# did not exclude, so it tokenized as {"0.5", "-1.2"} all over again and every
# faithful rewrite of an en-dash range -- the corpus's usual spelling -- was
# hard-rejected; `---` is the same case. The Unicode minus U+2212 joins the
# sign class: "−0.06" tokenized as "0.06", so dropping the sign passed.
# `_normalize` folds U+2212 to `-`, so both spellings of a negative are one token.
_NUMBER_SIGN = r"(?:(?<![\d.\-+\u2212])[-+\u2212])?"
# (6) A token may not START inside an identifier (2026-09-27). The lookbehind
# excluded letters only, so `M200` yielded "00", `z0.5` yielded "5" and
# `M200c` yielded the unit "c": junk invariants that rejected faithful
# rewrites of the identifier. Digits and dots now stop a token too. Shared
# with the unit regexes below, which tokenize the same numerals.
_NUMBER_START = r"(?<![A-Za-z\d.])"
_NUMBER_TOKEN = rf"{_NUMBER_SIGN}{_NUMBER_BODY}"
_NUM_RE = re.compile(rf"{_NUMBER_START}{_NUMBER_TOKEN}(?:\s*[×x]\s*10\^?[-+]?\d+)?")
_CITE_RE = re.compile(r"\\cite\w*\{([^}]+)\}")
_MATH_RE = re.compile(r"\$([^$]+)\$")
# An acronym continues across a hyphen only when an acronym continues after it
# (`X-RAY`, `HST-ACS`). `[A-Z][A-Z0-9-]{1,}` took a trailing hyphen as well, so
# `CDM-like` yielded the acronym `CDM-` and a candidate writing `CDM model`
# was reported as dropping it; v0.37.1 had recorded that as a disposition
# instead of correcting the pattern (2026-09-27).
_ACRONYM_RE = re.compile(r"\b[A-Z](?:[A-Z0-9]|-(?=[A-Z0-9]))+\b")
# Same root cause as _NUM_RE, and the binding one once numbers were fixed: the
# separator was `\s*(?:\\,)?\s*`, so a plain space let ANY following word become
# a "unit". "in 2020 we found" yielded unit {"we"} and "1200, 2400 sources"
# yielded {"sources"}, so a faithful rewrite that changed the word after a
# numeral was rejected as having dropped and invented a unit.
#
# A unit is recognised in two forms, and the separator decides which test the
# token has to pass:
#
#   BOUND  -- adjacent, or separated only by LaTeX spacing (`\,` `\;` `\!` `\ `
#             `~`), or written as \mathrm{}/\text{}/%/°. This is how the corpus
#             typesets units, so any token in that position is taken as one --
#             except an English suffix glued straight onto the digits, see
#             _ADJACENT_SUFFIXES, and `{\rm ...}`, see _rm_unit.
#   SPACED -- a single ASCII space, the ordinary prose form ("1.5 Mpc"). Here
#             the token must be a KNOWN unit, because an unrestricted `[A-Za-z]+`
#             turned every word after a numeral into a protected invariant
#             ("in 2020 we found" yielded unit "we") and hard-rejected faithful
#             rewrites. Dropping the spaced form entirely was the first attempt
#             and went too far the other way: it stopped catching `1.5 Mpc` ->
#             `1.5 kpc`, a factor-1000 physics error, in the gate whose whole
#             job is to catch exactly that.
_LATEX_THIN_SPACE = r"(?:\\[,;:!]|\\ |~)*"
_UNIT_TOKEN = r"[A-Za-z]+(?:\s*[/-]\s*[A-Za-z]+)*"
# `{\rm Mpc}` is the older spelling of `\mathrm{Mpc}` and just as common in
# the corpus; neither regex reached it, so a unit written that way was
# unprotected in both forms (2026-09-27).
_UNIT_RM = r"\{\\rm\b[^{}]*\}"
_UNIT_RM_INNER_RE = re.compile(rf"\{{\\rm\b\s*{_LATEX_THIN_SPACE}\s*({_UNIT_TOKEN})\s*\}}")
_UNIT_BOUND_RE = re.compile(
    rf"{_NUMBER_START}{_NUMBER_TOKEN}(?P<sep>{_LATEX_THIN_SPACE})"
    # `\%` before bare `%`: an unescaped `%` starts a LaTeX comment and is
    # stripped upstream (as it always has been for every projection-based
    # category), so `10\%` is the form that survives to be measured.
    rf"(?P<unit>\\mathrm\{{[^}}]+\}}|\\text\{{[^}}]+\}}|{_UNIT_RM}|\\%|[%°]|{_UNIT_TOKEN})"
)
_UNIT_SPACED_RE = re.compile(
    rf"{_NUMBER_START}{_NUMBER_TOKEN} (?P<unit>{_UNIT_RM}|{_UNIT_TOKEN})")
# Glued straight onto the digits with no separator at all, these are English
# suffixes, not units: `3rd`, `1990s`, `5x` yielded the units "rd", "s", "x"
# and rejected a rewrite that spelled the ordinal or decade out (2026-09-27).
# `s` is also the second: it stays a unit behind a space or LaTeX spacing
# (`5 s`, `5\,s`), where an author has typeset a quantity.
_ADJACENT_SUFFIXES = frozenset({"st", "nd", "rd", "th", "s", "x"})
# Physical units a numeral is followed by in this literature. Deliberately a
# closed vocabulary and deliberately NOT a detection policy: it decides only
# whether a space-separated token is eligible to be a protected invariant, so a
# missing entry costs protection on that one unit and never produces a finding.
# Ambiguous single letters that are ordinary English words ("a", "i") are
# excluded; the rest are unambiguous after a numeral in scientific prose.
_UNIT_VOCABULARY = frozenset({
    # length / distance
    "pc", "kpc", "mpc", "gpc", "au", "ly", "m", "km", "cm", "mm", "um", "nm",
    "angstrom", "å",
    # time
    "s", "ms", "us", "ns", "ps", "yr", "yrs", "gyr", "myr", "kyr", "hr", "h",
    "d", "day", "days", "year", "years", "min", "sec",
    # angle
    "deg", "degree", "degrees", "arcmin", "arcsec", "mas", "rad", "sr",
    # frequency / energy / power
    "hz", "khz", "mhz", "ghz", "thz", "ev", "kev", "mev", "gev", "tev",
    "erg", "ergs", "j", "w", "kw", "mw",
    # mass / flux / magnitude
    "kg", "g", "msun", "jy", "mjy", "ujy", "mag", "mags",
    # misc physical
    "k", "t", "v", "n", "c", "f", "pa", "mol", "dex", "sigma", "σ", "bit",
    "bits", "byte", "bytes", "gb", "mb", "kb", "tb", "px", "pixel", "pixels",
})
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
# is protected. Citation commands are covered separately by _CITE_RE; the
# natbib variants that were missing here (`\citeyearpar`, `\citetext`) made a
# citation rewritten between them a macro violation, and `\ldots`/`\dots`
# made `\ldots` -> `...` one (2026-09-27). `\rm`/`\mathrm` are the math-mode
# twins of `\textrm`; without them here `_rm_unit`'s equivalence was undone.
_FORMATTING_MACROS = frozenset({
    "emph", "textbf", "textit", "texttt", "textsc", "textrm", "textup",
    "rm", "mathrm",
    "underline", "mbox", "hbox", "vspace", "hspace", "noindent", "centering",
    "raggedright", "small", "footnotesize", "scriptsize", "large",
    "item", "begin", "end", "label", "documentclass", "usepackage",
    "newcommand", "renewcommand", "left", "right", "par", "linebreak",
    "newline", "ldots", "dots", "cite", "citep", "citet", "citealt", "citealp",
    "citeauthor", "citeyear", "citeyearpar", "citetext",
})
# The ranking term that used to be `specificity` (fraction of reference numbers
# preserved) is identically 1.0 for every eligible candidate, because
# fidelity_eligibility already rejects any candidate missing a reference number.
# A constant does no ranking work, so it is replaced by a real signal: the
# reduction in deterministic L0 rewrite targets (the writing improvement a
# rewrite exists to make), gated by a semantic-fidelity floor so a candidate
# cannot earn improvement credit by mangling meaning.
ADVISORY_REDUCTION_WEIGHT = 0.6   # inherits the retired `specificity` weight
FIDELITY_FLOOR = 0.5              # below this cosine, no positive reduction credit
# SCIPAPER_STANDARD section 5.3 (condense, do not accumulate): when the
# original paragraph is supplied, a candidate longer than it is HARD-ineligible
# unless growth is explicitly allowed with a recorded reason, and within budget
# a small condensation bonus prefers the shorter of otherwise-equal candidates.
CONDENSATION_WEIGHT = 0.1
# Bag (multiset) categories; the rest are sets, because a repeated citation,
# unit, acronym or math span is a restatement a condensation may fold.
_BAG_CATEGORIES = ("numbers", "comparison_direction", "negation", "causal_direction")


def _l0_target_count(text: str, field_profile_dir: Path | None) -> int:
    """Deterministic L0 rewrite-target count (em-dash + Tier A + over-cap Tier B).

    Reused from ai_ism_lint, imported lazily so rewrite_reward stays importable
    without the linter and no module-load cycle is introduced. Location is a
    placeholder path; only the finding kinds are counted, and a profile adds
    advisory lexicon findings only, never targets, so it does not change them.
    """
    import ai_ism_lint as lint  # noqa: E402  lazy: avoid import cycle + optional dep
    findings, _axes = lint.lexical_findings(text, Path("<candidate>"),
                                            field_profile_dir)
    return sum(1 for finding in findings if finding.get("kind") == "l0_target")


def _clears_floor(fidelity: float | None) -> bool:
    """Whether the fidelity floor permits credit; an unmeasured cosine cannot
    apply it, so the credit stands and `_unmeasured_terms` says so."""
    return fidelity is None or fidelity >= FIDELITY_FLOOR


def _advisory_reduction(ref_l0: int, cand_l0: int, fidelity: float | None) -> float:
    """Signed reduction in L0 targets, in [-1, 1], with a fidelity floor.

    Positive when a candidate removes reference L0 targets, negative when it
    adds them, zero when it neither helps nor hurts (so a clean reference gives
    no candidate spurious credit). Below ``FIDELITY_FLOOR`` a candidate cannot
    keep positive credit: it may not buy L0 improvement with mangled meaning.
    With the cosine unmeasured (``None``, no embedder installed) the floor has
    nothing to test and is not applied; the run reports the degradation.
    """
    denom = max(1, ref_l0, cand_l0)
    value = (ref_l0 - cand_l0) / denom
    if not _clears_floor(fidelity):
        value = min(value, 0.0)
    return value


def _normalize(token: str) -> str:
    """Whitespace-insensitive, case-folded, with the Unicode minus read as `-`:
    U+2212 and the hyphen-minus typeset the same negative number, and kept
    apart they reported `-0.06` for `−0.06` as one number dropped, one invented."""
    return re.sub(r"\s+", "", token).lower().replace("\u2212", "-")


_ENV_WRAPPER_RE = re.compile(r"\\(?:begin|end)\{[^}]*\}")
_EQUATION_NOISE_RE = re.compile(r"\\(?:nonumber|notag)\b")


def _uncommented(text: str) -> str:
    """Text with LaTeX comments removed.

    Every category that reads the RAW text — citations, inline and display
    math, semantic macros, units — must strip comments first, because both
    named projections do it as their first substitution and because commented
    LaTeX is not rendered and therefore carries no scientific content. Without
    this, a commented-out equation, citation or macro becomes a hard protected
    invariant and deleting dead markup hard-rejects the candidate at -inf.
    """
    return df.es.RE_TEX_COMMENT.sub("", text)


def _display_math_bodies(text: str) -> list[str]:
    """Reduced ``\\begin{equation}``/``align``/``gather``/… bodies.

    Both named LaTeX projections drop displayed equations deliberately, so
    anything a displayed equation alone carries is invisible to every category
    computed from them: a value silently changed inside ``\\begin{equation}``
    passed as fully faithful. These bodies are therefore read from the raw
    text — but they must first pass through the SAME reductions the projections
    apply, or the raw span smuggles in three kinds of non-content:

    * **comments.** ``RE_TEX_COMMENT`` is the first substitution in both
      projections; without it a commented-out dead equation becomes a hard
      invariant and deleting it hard-rejects the candidate.
    * **the environment wrapper.** Keeping ``\\begin{equation}`` in the token
      makes ``equation`` -> ``equation*`` a fidelity violation.
    * **labels.** ``\\label`` is in ``_FORMATTING_MACROS`` precisely because it
      carries no scientific content, so renaming ``eq:mass`` must not be a
      violation — and its digits (``eq:m200``) must not enter the number set.
    """
    reduced = _uncommented(text)
    bodies = []
    for match in df.es.RE_TEX_DISPLAY_MATH.finditer(reduced):
        body = _ENV_WRAPPER_RE.sub(" ", match.group(0))
        body = df.es.RE_TEX_LABEL_REF.sub(" ", body)
        body = _EQUATION_NOISE_RE.sub(" ", body)
        if body.strip():
            bodies.append(body)
    return bodies


def _numbers(text: str) -> Counter:
    """Numerals of the prose, of inline spans and of displayed equations, by count.

    Inline and displayed mathematics are read symmetrically (2026-09-27). The
    plain projection turns every math span into a placeholder, so numerals
    were collected from displayed bodies (v0.27.0) but never from inline
    spans, and a formula moved from display to inline, or back, was rejected
    twice over: its numerals went "missing" or came "invented" while the math
    category, which reads both forms, saw no change. Of the two symmetric
    repairs, inline numerals are collected (through the numeral projection,
    which exists to keep them) rather than display numerals dropped: the math
    category already rejects any change inside a span, so this adds no
    rejection the gate did not make, whereas dropping display numerals would
    take a changed value out of the ``numbers`` report the v0.27.0 tests pin.
    """
    tokens = _NUM_RE.findall(df.es.latex_to_numeral_text(text))
    for body in _display_math_bodies(text):
        tokens.extend(_NUM_RE.findall(body))
    return Counter(_normalize(token) for token in tokens)


def _citations(text: str) -> set[str]:
    keys = []
    for group in _CITE_RE.findall(_uncommented(text)):
        keys.extend(key.strip() for key in group.split(",") if key.strip())
    return set(keys)


def _math_normalized(items) -> set[str]:
    """Whitespace-insensitive but CASE-SENSITIVE normalization.

    Unlike prose, LaTeX control words are case-sensitive and the case carries
    the physics: ``\\Delta\\Sigma`` and ``\\delta\\Sigma`` are different
    quantities, as are ``\\Omega``/``\\omega`` and ``\\Phi``/``\\phi``. Folding
    case here would let a case-only symbol substitution pass the gate as fully
    faithful.
    """
    return {re.sub(r"\s+", "", item) for item in items}


def _math(text: str) -> set[str]:
    # Inline spans plus reduced displayed-equation bodies. Whitespace is
    # stripped, so re-wrapping or re-indenting an equation is not a change;
    # altering a symbol, a coefficient or an exponent is.
    spans = _math_normalized(_MATH_RE.findall(_uncommented(text)))
    spans |= _math_normalized(_display_math_bodies(text))
    return spans


def _acronyms(text: str) -> set[str]:
    """Uppercase acronyms of the rendered prose, projection placeholders excluded.

    The plain projection writes `[MATH]`, `[CITE]` and `[FIGURE-OR-TABLE]`
    where an equation, a citation or a float stood, each shaped like an
    acronym, so a candidate that turned a `\\citep` into prose "dropped" the
    acronym `CITE` (2026-09-27). `prose_words` owns placeholder removal.
    """
    return set(_ACRONYM_RE.findall(" ".join(df.es.prose_words(text))))


def _rm_unit(token: str) -> str | None:
    """`{\\rm Mpc}` as the `\\mathrm{Mpc}` it is the older spelling of, or None.

    Only a vocabulary unit qualifies: `{\\rm ...}` wraps far more than units
    (`M_{\\rm vir}`, `{\\rm d}x`), so unlike `\\mathrm{}` after a numeral it is
    not a unit on position alone. Both spellings render identically, so
    modernising one into the other is no unit change; `{\\rm kpc}` for `{\\rm Mpc}` is.
    """
    match = _UNIT_RM_INNER_RE.fullmatch(token)
    if match is None:
        return None
    inner = match.group(1)
    head = re.split(r"[\s/-]", inner, maxsplit=1)[0].lower()
    return rf"\mathrm{{{inner}}}" if head in _UNIT_VOCABULARY else None


def _unit_token(match: re.Match, *, spaced: bool) -> str | None:
    token = match.group("unit")
    if token.startswith("{"):
        return _rm_unit(token)
    if spaced:
        head = re.split(r"[\s/-]", token, maxsplit=1)[0].lower()
        return token if head in _UNIT_VOCABULARY else None
    if not match.group("sep") and token.lower() in _ADJACENT_SUFFIXES:
        return None
    return token


def _units(text: str) -> set[str]:
    prose = _uncommented(text)
    units = set()
    for spaced, pattern in ((False, _UNIT_BOUND_RE), (True, _UNIT_SPACED_RE)):
        for match in pattern.finditer(prose):
            token = _unit_token(match, spaced=spaced)
            if token is not None:
                units.add(_normalize(token))
    return units


def _macros(text: str) -> set[str]:
    """Semantic macro names in the raw text (latex_to_plain would erase them).

    Comments are stripped first: a macro that appears only inside a `%` comment
    is not rendered, so treating it as a protected invariant rejected the
    removal of dead markup.
    """
    return {name.lower() for name in _MACRO_RE.findall(_uncommented(text))
            if name.lower() not in _FORMATTING_MACROS}


def _markers(pattern: re.Pattern, text: str) -> Counter:
    return Counter(match.lower() for match in pattern.findall(df.es.latex_to_plain(text)))


def _cosine(left: str, right: str) -> float:
    import numpy as np
    embeddings = df._embedder().encode(
        [df.es.latex_to_plain(left), df.es.latex_to_plain(right)],
        normalize_embeddings=True,
    )
    return float(np.dot(embeddings[0], embeddings[1]))


def _prose_words(text: str) -> int:
    return len(df.es.latex_to_plain(text).split())


def length_budget(candidate: str, original: str) -> dict[str, Any]:
    """Section-5.3 length budget of one candidate against the ORIGINAL paragraph.

    The budget compares rendered-prose word counts. ``within`` is True when the
    candidate is no longer than the original; ``condensation`` is the fraction
    of the original's words removed (negative when the candidate grew).
    """
    words_original = _prose_words(original)
    words_candidate = _prose_words(candidate)
    return {
        "words_original": words_original,
        "words_candidate": words_candidate,
        "delta_words": words_candidate - words_original,
        "within": words_candidate <= words_original,
        "condensation": ((words_original - words_candidate) / words_original
                         if words_original else 0.0),
    }


def protected_invariants(text: str) -> dict[str, Any]:
    """Every protected category: a ``Counter`` for the bag categories
    (``_BAG_CATEGORIES``), a ``set`` for the rest."""
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


def _listed(values) -> list[str]:
    """A category as a sorted list, one entry per occurrence for a bag."""
    return sorted(values.elements()) if isinstance(values, Counter) else sorted(values)


def _count_mismatches(required: dict, present: dict) -> dict[str, dict[str, tuple[int, int]]]:
    """Bag tokens both sides carry with different multiplicities: "missing
    negation: not" beside a candidate that still says "not" then reads as what
    it is, the second occurrence went. A bag is blind to position, so a marker
    moved between clauses changes no count and is not detected here."""
    mismatches: dict[str, dict[str, tuple[int, int]]] = {}
    for category in _BAG_CATEGORIES:
        both = {token: (count, present[category][token])
                for token, count in required[category].items()
                if present[category][token] and present[category][token] != count}
        if both:
            mismatches[category] = both
    return mismatches


def fidelity_eligibility(candidate: str, reference: str) -> dict[str, Any]:
    """Bidirectional invariant check.

    ``missing``  = reference invariants the candidate dropped (all categories).
    ``invented`` = candidate invariants the reference does not carry. These are
    disqualifying in every category: added numbers/units/citations/macros are
    unsourced invention, and added negation/causal/comparison markers can invert
    the claim. A human may re-approve an "invented" candidate only after manual
    source-tracing outside this deterministic gate.

    The bag categories (``_BAG_CATEGORIES``) are compared by multiplicity, so
    both lists carry one entry per lost or added OCCURRENCE: ``["not", "not"]``
    when both negations went, ``["not"]`` when only the second did, a case
    ``count_mismatches`` names with both counts. A bag cannot see position: a
    marker moved into another clause, or two distinct numbers exchanging
    places, keeps every count and passes; the by-hand check covers that.
    """
    required = protected_invariants(reference)
    present = protected_invariants(candidate)
    missing = {category: _listed(values - present[category])
               for category, values in required.items()
               if values - present[category]}
    invented = {category: _listed(present[category] - required[category])
                for category in required
                if present[category] - required[category]}
    return {
        "eligible": not missing and not invented,
        "missing": missing,
        "invented": invented,
        "count_mismatches": _count_mismatches(required, present),
        "required": {key: _listed(values) for key, values in required.items()},
        "present": {key: _listed(values) for key, values in present.items()},
    }


def reward(candidate: str, reference: str, field_profile_dir: Path | None,
           centroid=None, ref_l0: int | None = None,
           original: str | None = None,
           allow_growth: bool = False) -> dict[str, Any]:
    """Every term of one candidate. ``voice`` and ``fidelity`` are ``None`` when
    unmeasured (no usable bundle; no embedder), never a nominal 0.0."""
    bundle = dv.load_voice_model(field_profile_dir)
    if bundle is None:
        voice = None
    else:
        if centroid is None:
            centroid = df.corpus_centroid(field_profile_dir)
        voice = dv.voice_score(candidate, field_profile_dir, centroid=centroid)
    voice_calibrated = dv.bundle_measured(bundle)
    fidelity = _cosine(candidate, reference) if df.embedder_available() else None
    required_numbers = _numbers(reference)
    candidate_numbers = _numbers(candidate)
    # Reported for transparency (confirms eligibility), but NOT a ranking term:
    # it is identically 1.0 for every eligible candidate. See ADVISORY_REDUCTION.
    specificity = ((required_numbers & candidate_numbers).total() / required_numbers.total()
                   if required_numbers else 1.0)
    if ref_l0 is None:
        ref_l0 = _l0_target_count(reference, field_profile_dir)
    cand_l0 = _l0_target_count(candidate, field_profile_dir)
    advisory_reduction = _advisory_reduction(ref_l0, cand_l0, fidelity)
    eligibility = fidelity_eligibility(candidate, reference)
    budget = length_budget(candidate, original) if original is not None else None
    length_eligible = True if budget is None else (budget["within"] or allow_growth)
    return {
        "voice": voice,
        "voice_calibrated": voice_calibrated,
        "fidelity": fidelity,
        "specificity": specificity,
        "advisory_reduction": advisory_reduction,
        "n_l0_ref": ref_l0,
        "n_l0_cand": cand_l0,
        "n_num_ref": required_numbers.total(),
        "n_num_cand": candidate_numbers.total(),
        "faithful": eligibility["eligible"],
        "missing_invariants": eligibility["missing"],
        "invented_invariants": eligibility["invented"],
        "count_mismatches": eligibility["count_mismatches"],
        "length_budget": budget,
        "length_eligible": length_eligible,
    }


def rank(candidates: list[str], reference: str, field_profile_dir: Path | None,
         original: str | None = None, allow_growth: bool = False
         ) -> list[tuple[int, dict[str, Any]]]:
    """Rank eligible candidates first; ineligible candidates can never win.

    L0 advisory reduction and semantic fidelity lead the ranking. The learned
    L3 score is a low-weight tie-break unless its bundle is measured/calibrated,
    so an uncalibrated field-similarity model can never be the deciding term
    (SCIPAPER_STANDARD section 9.5: lower detector visibility is not
    independently valuable). A term that is unmeasured -- no usable bundle, no
    embedder -- is left out of ``combined`` (weight 0) rather than scored 0.0,
    and the eligibility gate runs regardless. When ``original`` is supplied,
    the section-5.3 length budget is a second hard gate: a candidate longer
    than the original scores -inf unless ``allow_growth`` records an explicit
    exception, and a condensation bonus prefers the shorter of otherwise-equal
    candidates.
    """
    # The centroid feeds the learned score only; loading it needs numpy, which
    # a run without a bundle must not require.
    centroid = (df.corpus_centroid(field_profile_dir)
                if dv.load_voice_model(field_profile_dir) is not None else None)
    ref_l0 = _l0_target_count(reference, field_profile_dir)   # constant across candidates
    scored = []
    for index, candidate in enumerate(candidates):
        result = reward(candidate, reference, field_profile_dir, centroid,
                        ref_l0=ref_l0, original=original, allow_growth=allow_growth)
        if result["faithful"] and result["length_eligible"]:
            combined = ADVISORY_REDUCTION_WEIGHT * result["advisory_reduction"]
            if result["fidelity"] is not None:
                combined += 0.3 * result["fidelity"]
            if result["voice"] is not None:
                combined += (0.4 if result["voice_calibrated"] else 0.05) * result["voice"]
            # The condensation bonus sits behind the same fidelity floor as
            # advisory reduction: a degenerate ultra-short candidate may not
            # buy ranking credit with dropped meaning.
            if result["length_budget"] is not None and _clears_floor(result["fidelity"]):
                combined += (CONDENSATION_WEIGHT
                             * max(0.0, result["length_budget"]["condensation"]))
            result["combined"] = combined
        else:
            result["combined"] = float("-inf")
        scored.append((index, result))
    scored.sort(key=lambda item: (
        item[1]["faithful"] and item[1]["length_eligible"],
        item[1]["combined"],
        -1.0 if item[1]["fidelity"] is None else item[1]["fidelity"]),
        reverse=True)
    return scored


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    parser = cli_common.field_parser(__doc__)
    parser.add_argument("--reference", type=Path, required=True,
                        help="distilled claim and protected scientific content")
    parser.add_argument("--candidates", type=Path, nargs="+", required=True)
    parser.add_argument("--original", type=Path, default=None,
                        help="the paragraph being replaced; enables the "
                             "section-5.3 length-budget hard gate")
    parser.add_argument("--allow-growth", default=None, metavar="REASON",
                        help="record an author-approved reason that lifts the "
                             "length-budget gate for this run")
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except Exception as error:
        # Deliberately broad, and mandatory once exit 1 became a MEASURED
        # outcome: without this guard an uncaught exception also left the
        # interpreter at 1, so a crash was indistinguishable from — and would
        # be acted on as — "no candidate was eligible, regenerate tighter".
        # This is the same guard ai_ism_lint and length_gate already carry.
        # KeyboardInterrupt/SystemExit are BaseException and still propagate.
        print(f"[rewrite_reward] execution failed: "
              f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


def _unmeasured_terms(field_dir: Path | None) -> list[str]:
    """One stderr line per optional term this run cannot measure.

    Neither line is a refusal: the term is unmeasured at weight 0 and the gate
    and the exit status by eligibility go on. Until 2026-09-27 a missing
    ``voice_model.joblib`` was exit 2, so a fresh clone or an untrained
    profile could not run the fidelity gate at all, although the de-ai and
    condense skills use it as a mandatory gate and calibrate documents the
    learned model as never required. A bundle present but unusable
    (unreadable, joblib uninstalled, feature-schema mismatch) is named as
    such: `deai_voice` has just printed why, and "no voice_model.joblib"
    would send the reader to train a model they already have.
    """
    unmeasured = "learned field-similarity score unmeasured, weight 0"
    lines = []
    if field_dir is None:
        lines.append("no field profile (pass --field, or keep exactly one field "
                     f"under the profile root): {unmeasured}")
    elif dv.load_voice_model(field_dir) is None:
        artifact = field_dir / "voice_model.joblib"
        if artifact.exists():
            lines.append(f"{artifact} is present but unusable (see the deai_voice "
                         f"line above): {unmeasured}")
        else:
            lines.append(f"no voice_model.joblib in {field_dir}: {unmeasured}")
    if not df.embedder_available():
        lines.append("sentence-transformers is not installed: semantic fidelity "
                     "unmeasured, weight 0; its floor on the advisory-reduction credit "
                     "and the condensation bonus cannot apply; verify meaning by hand")
    return lines


def _cell(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}"


def _render_counts(mismatches: dict[str, dict[str, tuple[int, int]]]) -> str:
    return "; ".join(
        f"{category} {token!r}: {n_ref} in reference, {n_cand} in candidate"
        for category, tokens in mismatches.items()
        for token, (n_ref, n_cand) in tokens.items())


def _run(args) -> int:
    field_dir = cli_common.optional_field_dir(args, tool="rewrite_reward")
    for line in _unmeasured_terms(field_dir):
        print(f"[rewrite_reward] {line}", file=sys.stderr)
    reference = args.reference.read_text(encoding="utf-8", errors="replace")
    candidates = [path.read_text(encoding="utf-8", errors="replace")
                  for path in args.candidates]
    original = (args.original.read_text(encoding="utf-8", errors="replace")
                if args.original is not None else None)
    if args.allow_growth:
        print(f"[length-budget] growth allowed for this run: {args.allow_growth}")
    ranked = rank(candidates, reference, field_dir,
                  original=original, allow_growth=bool(args.allow_growth))
    print(f"{'rank':>4} {'cand':>4} {'combined':>9} {'voice':>7} "
          f"{'fidelity':>9} {'Δadv':>6} {'eligible':>8}  L0(r/c)  words(o/c)")
    for position, (index, result) in enumerate(ranked, 1):
        combined = result["combined"]
        combined_text = "-inf" if combined == float("-inf") else f"{combined:.3f}"
        budget = result["length_budget"]
        words_text = (f"{budget['words_original']}/{budget['words_candidate']}"
                      if budget is not None else "-")
        eligible_flag = result["faithful"] and result["length_eligible"]
        print(f"{position:>4} {index:>4} {combined_text:>9} "
              f"{_cell(result['voice']):>7} {_cell(result['fidelity']):>9} "
              f"{result['advisory_reduction']:>6.2f} {str(eligible_flag):>8}  "
              f"{result['n_l0_ref']}/{result['n_l0_cand']}  {words_text}  "
              f"{args.candidates[index].name}")
        if result["missing_invariants"]:
            print(f"     missing: {result['missing_invariants']}")
        if result["invented_invariants"]:
            print(f"     invented: {result['invented_invariants']}")
        if result["count_mismatches"]:
            print(f"     count mismatch: {_render_counts(result['count_mismatches'])} "
                  "(bags are blind to position: a marker moved between clauses "
                  "is not detected here)")
        if budget is not None and not result["length_eligible"]:
            print(f"     over length budget: +{budget['delta_words']} words "
                  "(SCIPAPER_STANDARD section 5.3; use --allow-growth REASON "
                  "only with an author-approved justification)")
    eligible = [item for item in ranked
                if item[1]["faithful"] and item[1]["length_eligible"]]
    if not eligible:
        # Exit 1, not 2. Every candidate being ineligible is a MEASURED outcome
        # the caller acts on -- de-ai §4.3 step 3 says to preserve the original
        # and regenerate tighter -- not an execution failure. Reporting it as 2
        # made a successful, correct run indistinguishable from a crash or a
        # missing profile. Registered in SCIPAPER_STANDARD §0.1 alongside
        # length_gate's narrow actionable contract.
        print("\n[rewrite_reward] no candidate passed fidelity and length-budget "
              "eligibility; preserve the original and regenerate tighter",
              file=sys.stderr)
        return 1
    best_index = eligible[0][0]
    print(f"\n[best] candidate {best_index}: {args.candidates[best_index].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
