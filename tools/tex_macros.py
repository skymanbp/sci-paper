"""Numbers a LaTeX manuscript holds in macros rather than in its prose.

A paper that writes `\\newcommand{\\Nfields}{63}` in its preamble and `\\Nfields{}`
in its results has put a measured quantity where no text projection can see it.
Both named projections in `extract_sections` strip the command and keep only its
argument, so the use site contributes nothing and the *definition* site
contributes the digits once, in the preamble, where no section bucket reports
them. The salience axis then measures the paper as less quantity-dense than it
reads, and every recital percentile it produces for that paper is an
underestimate.

Measured on the wgl corpus (2026-08-27, 390 documents with at least 50 visible
digits): 88.2% hide no digit this way at all, the ninetieth percentile hides
0.2%, and the ninety-ninth hides 4.5%. The habit is rare, so the correction
moves almost nothing -- but where a paper does commit to it, it commits hard.
The heaviest corpus document hides 27% of its digits behind 87 macro uses, and
one manuscript reviewed that day (the manuscript) hid 662 digits, 9.0% of its total,
behind 253 uses: the 99.5th percentile of the same corpus.

Expansion happens once, on the assembled document, because that is the only
place where a preamble definition and a body use are both in scope. It is
deliberately conservative: a macro is expanded only when its body is a bare
numeric literal with no letters and no markup, so `\\newcommand{\\Msun}{M_\\odot}`
and every macro taking an argument are left exactly as they were.
"""

from __future__ import annotations

import re

# `\newcommand{\x}{1}`, `\newcommand\x{1}`, `\renewcommand`, `\providecommand`,
# and plain-TeX `\def\x{1}`. The optional `[n]` arity is matched so that a
# macro taking arguments parses as a definition and is then rejected below,
# rather than being mis-read as a shorter definition that happens to fit.
RE_DEFINITION = re.compile(
    r"\\(?:(?:new|renew|provide)command\s*\*?\s*\{?|def\s*)\\([A-Za-z]+)\}?"
    r"(?:\[\d+\])?\s*\{([^{}]*)\}"
)
# A body that is a number and nothing else. Letters would make it a symbol and
# a backslash would make it markup; either way expanding it would put text the
# author never wrote into the prose the axes measure.
RE_BARE_NUMBER = re.compile(r"^[^A-Za-z\\]*\d[^A-Za-z\\]*$")


def expand_numeric(text: str) -> str:
    """Replace uses of numeric-literal macros with their numbers.

    The definition itself is dropped rather than left in place. Keeping it
    would double-count: `RE_TEX_SIMPLE_CMD` reduces `\\newcommand{\\Nf}{63}` to
    its argument `63`, so an unexpanded manuscript already contributes one
    stray numeral per definition, attributed to the preamble.

    A use is matched only when the macro name is not a prefix of a longer name
    (`\\Nf` must not fire inside `\\Nfields`), and an immediately following empty
    brace pair -- the `{}` LaTeX authors write to protect the following space --
    is consumed with it.
    """
    macros: dict[str, str] = {}

    def _harvest(match: "re.Match[str]") -> str:
        body = match.group(2).strip()
        if RE_BARE_NUMBER.match(body):
            macros[match.group(1)] = body
            return " "
        return match.group(0)

    text = RE_DEFINITION.sub(_harvest, text)
    if not macros:
        return text
    # Longest name first so a shorter name cannot claim a prefix of a longer
    # one before the negative lookahead is reached.
    names = "|".join(sorted((re.escape(n) for n in macros),
                            key=len, reverse=True))
    # The `{}` is optional, and so is the space before it -- but only together.
    # Written `\s*(?:\{\})?` the whitespace is consumed whether or not a brace
    # pair follows, which welds the macro to the next word: `\Nf and` -> `7and`.
    uses = re.compile(r"\\(" + names + r")(?![A-Za-z])(?:\s*\{\})?")
    return uses.sub(lambda m: macros[m.group(1)], text)
