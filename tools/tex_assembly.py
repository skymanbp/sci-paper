"""Assemble a LaTeX document from its root and the files it \\input / \\includes.

A LaTeX document is assembled from files; only its root is named. Reading the
root alone is as wrong as counting each piece separately -- Bartelmann &
Schneider (2001) has 72 words in `WeakLens.tex` and its whole ~40,000-word body
in the eleven chapter files that root includes.

Every reader of a document goes through one assembler, so the manuscript the
axes measure, the baseline a gate compares against, and the corpus passages the
banks are built from are the same projection of the same include graph:

- `read_tex_document(path)` reads from the file system;
- `read_git_document(path, ref)` reads the same graph at a git ref, so a
  `--git-ref` baseline whose root only says `\\input{body}` still carries the
  body (it did not: the gate read the root alone and a shortened child never
  changed the count);
- `assemble(text, root, read)` is the one algorithm behind both.

The splice is in place: `Before \\input{body} After` keeps `Before` and `After`
(the earlier assembler replaced the whole line with the child, losing both),
and the same file included twice is spliced twice, because a cycle is a file
on the current include STACK, not a file seen anywhere before.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable

import tex_macros

# One owner for the comment pattern: `extract_sections` re-exports it.
RE_TEX_COMMENT = re.compile(r"(?<!\\)%.*?$", re.MULTILINE)
RE_TEX_UNESCAPED_PERCENT = re.compile(r"(?<!\\)%")
# A LaTeX *document* root, as opposed to a piece of one. \documentstyle is
# LaTeX 2.09 and still appears throughout pre-1995 arXiv sources.
RE_TEX_DOC_MARKER = re.compile(r"\\document(?:class|style)\b|\\begin\{document\}")
# The whole call, so it can be replaced in place; group 1 is the target.
RE_TEX_INCLUDE = re.compile(r"\\(?:include|input)\s*\{?\s*([^}\s\\]+)\s*\}?")


def include_targets(text: str) -> list[str]:
    """\\include / \\input targets on lines where the call is not commented out.

    Comment-stripping matters: arXiv sources routinely park an alternative
    build in comments (`% \\includeonly{WeakLens_7}`), and resolving those
    would splice a chapter into the document twice.
    """
    names: list[str] = []
    for line in text.splitlines():
        names.extend(RE_TEX_INCLUDE.findall(RE_TEX_COMMENT.sub("", line)))
    return names


def resolve_include(root: Path, name: str) -> Path | None:
    """The file an \\include/\\input target names, or None. Literal path first,
    then a same-stem sibling (arXiv flattens submission directories)."""
    literal = root.parent / name
    if literal.suffix.lower() != ".tex":
        literal = literal.with_suffix(".tex")
    if literal.is_file():
        return literal
    sibling = root.parent / f"{Path(name).stem}.tex"
    return sibling if sibling.is_file() else None


def assemble(text: str, root: Path, read: Callable[[Path], str | None],
             _stack: tuple[Path, ...] = ()) -> str:
    """`text` (the content of `root`) with every live include spliced in place.

    `read(path)` returns a child's content or None when it cannot be read; an
    unresolvable target (`\\input{aa.cls}`) is left in place rather than
    failing. Includes inside a comment are not calls.
    """
    stack = _stack + (root.resolve(),)
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        comment = RE_TEX_UNESCAPED_PERCENT.search(line)
        code, tail = (line[:comment.start()], line[comment.start():]) if comment else (line, "")
        if not RE_TEX_INCLUDE.search(code):
            out.append(line)
            continue

        def splice(match: "re.Match[str]") -> str:
            child = resolve_include(root, match.group(1))
            if child is None:
                return match.group(0)
            if child.resolve() in stack:
                return ""
            body = read(child)
            return match.group(0) if body is None else assemble(body, child, read, stack)

        out.append(RE_TEX_INCLUDE.sub(splice, code) + tail)
    return "".join(out)


def _read_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def read_tex_document(path: Path) -> str:
    """Read a `.tex` root with its \\include / \\input children spliced in.

    A target is resolved against the root's directory first and, failing that,
    against a sibling with the same stem: arXiv flattens submissions, so
    `\\input{sections/introduction}` routinely names a file that now sits
    beside the root, and `select_document_roots` matches includes by stem --
    four wgl bundles lost most of their prose (one 9,741 of 9,743 words)
    before the reader used the same rule. Numeric macros are expanded once, on
    the assembled document (`tex_macros`): only the root holds definition and use.
    """
    text = _read_file(path)
    if text is None:
        return ""
    return tex_macros.expand_numeric(assemble(text, path, _read_file))


def read_git_document(path: Path, ref: str) -> str:
    """The same assembled document at git `ref`, every child read from the ref too.

    Decoding uses `errors="replace"`: a baseline with stray non-UTF-8 bytes
    must degrade to lossy words, not escape as an uncaught traceback. Raises
    ValueError when the path is outside a repository or absent at the ref.
    """
    directory = path.resolve().parent
    top = _git(directory, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise ValueError(f"not inside a git repository: {top.stderr.strip()}")
    repo = Path(top.stdout.strip())

    def read(target: Path) -> str | None:
        try:
            relative = target.resolve().relative_to(repo).as_posix()
        except ValueError:
            return None
        shown = _git(directory, "show", f"{ref}:{relative}")
        return shown.stdout if shown.returncode == 0 else None

    root_text = read(path)
    if root_text is None:
        raise ValueError(f"git show {ref}:{path.name} failed: not present at {ref!r}")
    return tex_macros.expand_numeric(assemble(root_text, path, read))


def _git(directory: Path, *arguments: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(["git", "-C", str(directory), *arguments], text=True,
                          capture_output=True, encoding="utf-8", errors="replace")
