"""Numbers a LaTeX manuscript holds in macros rather than in its prose.

A paper that writes `\\newcommand{\\Nsamples}{12}` in its preamble and `\\Nsamples{}`
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
one manuscript reviewed that day hid 662 digits, 9.0% of its total,
behind 253 uses: the 99.5th percentile of the same corpus.

Expansion happens once, on the assembled document, because that is the only
place where a preamble definition and a body use are both in scope. It is
deliberately conservative: a macro is expanded only when its body is a bare
numeric literal with no letters and no markup, so `\\newcommand{\\Msun}{M_\\odot}`
and every macro taking an argument are left exactly as they were. A comment is
not source: harvested, a commented-out `% \\newcommand{\\Ns}{12}` beat the live
value that followed it, and a use inside a comment is left as written.
"""

from __future__ import annotations

import re

# One owner for the comment pattern: `tex_assembly` and `extract_sections`
# re-export it, and it lives here because this is the lowest module that needs
# it (a definition inside a comment must not be harvested).
RE_TEX_COMMENT = re.compile(r"(?<!\\)%.*?$", re.MULTILINE)
# `\newcommand{\x}{1}`, `\newcommand\x{1}`, `\renewcommand`, `\providecommand`,
# and plain-TeX `\def\x{1}`. The optional `[n]` arity is CAPTURED (group 2) so
# that a macro taking arguments parses as a definition and is then left alone,
# rather than being mis-read as a shorter definition that happens to fit: the
# arity used to be matched and discarded, so `\newcommand{\foo}[1]{42}` was
# harvested and `\foo{x}` became `42{x}`.
RE_DEFINITION = re.compile(
    r"\\(?:(?:new|renew|provide)command\s*\*?\s*\{?|def\s*)\\([A-Za-z]+)\}?"
    r"(?:\[(\d+)\])?\s*\{([^{}]*)\}"
)
# A body that is a number and nothing else. Letters would make it a symbol and
# a backslash would make it markup; either way expanding it would put text the
# author never wrote into the prose the axes measure.
RE_BARE_NUMBER = re.compile(r"^[^A-Za-z\\]*\d[^A-Za-z\\]*$")


def _blank(text: str, spans: list[tuple[int, int]]) -> str:
    """`text` with each span turned to spaces, its line breaks kept."""
    pieces: list[str] = []
    cursor = 0
    for start, end in spans:
        pieces += [text[cursor:start], re.sub(r"[^\n]", " ", text[start:end])]
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def expand_numeric(text: str) -> str:
    """Replace uses of numeric-literal macros with their numbers.

    The definition itself is blanked rather than left in place. Keeping it
    would double-count: the projections reduce `\\newcommand{\\Ns}{12}` to the
    stray token `\\Ns12`, so an unexpanded manuscript already contributes one
    stray numeral per definition, attributed to the preamble. It is blanked at
    its own length with its line breaks kept, so no later line moves: replaced
    by one space, a definition written across lines (`{%`, then the number on
    the next line) pulled every later finding up by a line.

    Definitions and uses are both read from a copy with comments blanked (same
    offsets), so a commented-out definition is neither harvested nor dropped,
    and a use inside a comment is not expanded; a definition that takes
    arguments is left exactly as written.

    A use is matched only when the macro name is not a prefix of a longer name
    (`\\Ns` must not fire inside `\\Nsamples`), and an immediately following
    empty brace pair -- the `{}` LaTeX authors write to protect the following
    space -- is consumed with it.
    """
    macros: dict[str, str] = {}
    live = RE_TEX_COMMENT.sub(lambda m: " " * len(m.group(0)), text)
    harvested: list[tuple[int, int]] = []
    for match in RE_DEFINITION.finditer(live):
        body = match.group(3).strip()
        if match.group(2) is not None or not RE_BARE_NUMBER.match(body):
            continue
        macros[match.group(1)] = body
        harvested.append(match.span())
    if not macros:
        return text
    text, live = _blank(text, harvested), _blank(live, harvested)
    # Longest name first so a shorter name cannot claim a prefix of a longer
    # one before the negative lookahead is reached.
    names = "|".join(sorted((re.escape(n) for n in macros),
                            key=len, reverse=True))
    # The `{}` is optional, and so is the space before it -- but only together.
    # Written `\s*(?:\{\})?` the whitespace is consumed whether or not a brace
    # pair follows, which welds the macro to the next word: `\Ns and` -> `7and`.
    uses = re.compile(r"\\(" + names + r")(?![A-Za-z])(?:\s*\{\})?")
    pieces: list[str] = []
    cursor = 0
    for match in uses.finditer(live):
        pieces += [text[cursor:match.start()], macros[match.group(1)]]
        cursor = match.end()
    pieces.append(text[cursor:])
    return "".join(pieces)
