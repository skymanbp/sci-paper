"""Shared command-line preamble for the tool suite.

Every tool opens `main()` the same way: reconfigure stdout to UTF-8 so Windows
consoles do not mangle a dossier, build an ArgumentParser whose description is
the module's own first docstring line, and register `--field` / `--profile-root`.
Written out per tool that is 26 near-identical copies, and the repository's
duplicate-content guard refuses a 27th.

This module is deliberately small and holds no policy: it decides no default
beyond the profile root, reads no profile, and emits no findings. Tools that
predate it still carry their own copies; they are not retrofitted here because
their parsers differ in the options that follow, and a sweep of 26 CLIs carries
regression risk out of proportion to the duplication it removes. New tools use
this.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
DEFAULT_CORPUS_ROOT = REPO_ROOT / "style-corpus"


def utf8_stdout() -> None:
    """Make stdout UTF-8 where the runtime allows it (Windows consoles)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def field_parser(doc: str | None, *, corpus: bool = False
                 ) -> argparse.ArgumentParser:
    """An ArgumentParser carrying the options every field-aware tool takes.

    `doc` is the calling module's `__doc__`; its first line becomes the
    description, which is what `--help` shows and what `validate_plugin`'s
    entry-point check reads.
    """
    parser = argparse.ArgumentParser(
        description=(doc or "").splitlines()[0] if doc else None)
    parser.add_argument("--field", default=None,
                        help="Field name; auto-detected when only one exists.")
    parser.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    if corpus:
        parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    return parser
