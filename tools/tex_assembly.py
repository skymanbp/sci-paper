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
  changed the count), and its children are looked up AT THE REF too: resolved
  against the working tree, a child deleted since the ref vanished from the
  baseline, which understated exactly the cut a condense pass makes when it
  drops a whole section file;
- `assemble(text, root, read, resolve=...)` is the one algorithm behind both.

The root of a document must be readable: an unreadable root raises, because a
gate that read a missing baseline as an empty document reported every section
as growth, and a linter that read a directory named `x.tex` as an empty
document reported it clean. Only a CHILD may fail to resolve and stay in
place as the literal call.

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

# One owner for the comment pattern (`tex_macros`); `extract_sections` re-exports it.
RE_TEX_COMMENT = tex_macros.RE_TEX_COMMENT
RE_TEX_UNESCAPED_PERCENT = re.compile(r"(?<!\\)%")
# A LaTeX *document* root, as opposed to a piece of one. \documentstyle is
# LaTeX 2.09 and still appears throughout pre-1995 arXiv sources.
RE_TEX_DOC_MARKER = re.compile(r"\\document(?:class|style)\b|\\begin\{document\}")
# The whole call, so it can be replaced in place; group 1 is the target. The
# name boundary keeps `\includegraphics`, `\includeonly` and `\inputminted`
# from reading as include calls with a mangled target.
RE_TEX_INCLUDE = re.compile(r"\\(?:include|input)(?![A-Za-z])\s*\{?\s*([^}\s\\]+)\s*\}?")


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


def include_candidates(base: Path, current: Path, name: str) -> list[Path]:
    """The files an \\include/\\input target may name, in resolution order.

    LaTeX resolves a target against the directory it was started in -- the
    document root's, whatever file the call sits in -- so that comes first,
    then the including file's own directory. A name with a suffix is tried
    as written (`\\input{fig.tikz}` does not mean `fig.tex`); one without gets
    `.tex`. Last, a same-stem sibling of each, because arXiv flattens
    submission directories and `\\input{sections/introduction}` routinely
    names a file that now sits beside the root.
    """
    target = Path(name)
    literal = target if target.suffix else target.with_suffix(".tex")
    ordered: list[Path] = []
    for directory in (base, current.parent):
        for candidate in (directory / literal, directory / f"{target.stem}.tex"):
            if candidate not in ordered:
                ordered.append(candidate)
    return ordered


def resolve_include(root: Path, name: str, base: Path | None = None) -> Path | None:
    """The file an \\include/\\input target names on disk, or None."""
    for candidate in include_candidates(base or root.parent, root, name):
        if candidate.is_file():
            return candidate
    return None


def assemble(text: str, root: Path, read: Callable[[Path], str | None],
             _stack: tuple[Path, ...] = (), *,
             resolve: Callable[[Path, str, Path], Path | None] | None = None,
             base: Path | None = None) -> str:
    """`text` (the content of `root`) with every live include spliced in place.

    `read(path)` returns a child's content or None when it cannot be read;
    `resolve(current, name, base)` names the child a call refers to (the disk
    rule by default; a git reader passes one that looks at the ref). An
    unresolvable target (`\\input{aa.cls}`) is left in place rather than
    failing. Includes inside a comment are not calls. `base` is the document
    root's directory and is threaded through the recursion so a nested
    `\\input` resolves the way LaTeX resolves it.
    """
    stack = _stack + (root.resolve(),)
    base_dir = base if base is not None else root.parent
    find = resolve or resolve_include
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        comment = RE_TEX_UNESCAPED_PERCENT.search(line)
        code, tail = (line[:comment.start()], line[comment.start():]) if comment else (line, "")
        if not RE_TEX_INCLUDE.search(code):
            out.append(line)
            continue

        def splice(match: "re.Match[str]") -> str:
            child = find(root, match.group(1), base_dir)
            if child is None:
                return match.group(0)
            if child.resolve() in stack:
                return ""
            body = read(child)
            if body is None:
                return match.group(0)
            return assemble(body, child, read, stack, resolve=find, base=base_dir)

        out.append(RE_TEX_INCLUDE.sub(splice, code) + tail)
    return "".join(out)


def _read_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def read_tex_document(path: Path) -> str:
    """Read a `.tex` root with its \\include / \\input children spliced in.

    The root is read with `read_text` and its OSError propagates (a missing
    file, a directory, a permission failure): the caller decides what an
    unreadable root means, and no caller may read it as an empty document.
    Children go through `_read_file` and degrade to "left in place". Numeric
    macros are expanded once, on the assembled document (`tex_macros`): only
    the root holds definition and use.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return tex_macros.expand_numeric(assemble(text, path, _read_file))


def read_git_document(path: Path, ref: str) -> str:
    """The same assembled document at git `ref`, every child read from the ref too.

    Children are RESOLVED at the ref as well (`git cat-file -e`), with the
    same candidate order as the disk reader, so a child that the working tree
    no longer holds is still part of the baseline. Decoding uses
    `errors="replace"`: a baseline with stray non-UTF-8 bytes must degrade to
    lossy words, not escape as an uncaught traceback. Raises ValueError when
    the path is outside a repository or absent at the ref.
    """
    directory = path.resolve().parent
    top = _git(directory, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        raise ValueError(f"not inside a git repository: {top.stderr.strip()}")
    repo = Path(top.stdout.strip())

    def relative(target: Path) -> str | None:
        try:
            return target.resolve().relative_to(repo).as_posix()
        except ValueError:
            return None

    def read(target: Path) -> str | None:
        name = relative(target)
        if name is None:
            return None
        shown = _git(directory, "show", f"{ref}:{name}")
        return shown.stdout if shown.returncode == 0 else None

    def resolve(current: Path, name: str, base: Path) -> Path | None:
        for candidate in include_candidates(base, current, name):
            inside = relative(candidate)
            if inside is None:
                continue
            if _git(directory, "cat-file", "-e", f"{ref}:{inside}").returncode == 0:
                return candidate
        return None

    root_text = read(path)
    if root_text is None:
        raise ValueError(f"git show {ref}:{path.name} failed: not present at {ref!r}")
    return tex_macros.expand_numeric(assemble(root_text, path, read, resolve=resolve))


def _git(directory: Path, *arguments: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(["git", "-C", str(directory), *arguments], text=True,
                          capture_output=True, encoding="utf-8", errors="replace")
