"""Shared command-line preamble and field resolution for the tool suite.

Every tool opened `main()` the same way: reconfigure stdout to UTF-8 so Windows
consoles do not mangle a dossier, build an ArgumentParser whose description is
the module's own first docstring line, and register `--field` /
`--profile-root`. Five tools additionally carried byte-equivalent `list_fields`
and `resolve_field` copies that differed only in the tool name inside their
error strings.

This module is deliberately small and holds no policy: it decides no default
beyond the two roots, reads no profile, and emits no findings. 21 of the 30
tools were retrofitted onto it on 2026-08-26; the rest are library modules with
no CLI, plus the two divergences below.

Two divergences are kept on purpose rather than folded in:

- `ai_ism_lint.resolve_field` **warns and returns None** instead of raising,
  because the linter must still run its L0 pass with no profile present. That is
  a behavioural difference, not duplication, so it keeps its own copy.
- `extract_style` resolves against the *corpus* root, where a `tier-*`
  subdirectory is not a field. That is expressed here as `exclude_prefixes`
  rather than as a second implementation.
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


def base_parser(doc: str | None, **kwargs) -> argparse.ArgumentParser:
    """An ArgumentParser whose description is the caller's first docstring line.

    `validate_plugin`'s entry-point check reads that description, so a tool that
    loses it fails the contract rather than merely looking bare in `--help`.
    """
    return argparse.ArgumentParser(
        description=(doc or "").splitlines()[0] if doc else None, **kwargs)


def field_options(*, corpus: bool = False) -> argparse.ArgumentParser:
    """The field options alone, as an `add_help=False` parent parser.

    A tool with subcommands needs these on each subparser, not only on the root:
    argparse hands everything after the subcommand name to the subparser, so a
    root-only `--field` forces `tool --field wgl sample` while every other tool
    in the suite accepts `--field` last. Pass this in `parents=`.
    """
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--field", default=None,
                        help="Field name; auto-detected when only one exists.")
    parent.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    if corpus:
        parent.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    return parent


def field_parser(doc: str | None, *, corpus: bool = False
                 ) -> argparse.ArgumentParser:
    """`base_parser` plus the options every field-aware tool takes."""
    return base_parser(doc, parents=[field_options(corpus=corpus)])


def list_fields(root: Path, *, exclude_prefixes: tuple[str, ...] = ()) -> list[str]:
    """Non-hidden subdirectories of `root`, minus any excluded prefix."""
    if not root.exists():
        return []
    return sorted(
        path.name for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
        and not path.name.startswith(exclude_prefixes or ("\0",))
    )


def resolve_field(arg_field: str | None, root: Path, *, tool: str,
                  exclude_prefixes: tuple[str, ...] = (),
                  empty_hint: str = "Run `python tools/extract_style.py "
                                    "--field <name>` first.") -> str:
    """Pick the one field to operate on, or exit with a usable message.

    Named `--field` must exist; otherwise a single field auto-resolves and zero
    or several are an error. Raising here rather than guessing is the point: a
    tool that silently picked a field would write one profile's evidence into
    another's directory.
    """
    fields = list_fields(root, exclude_prefixes=exclude_prefixes)
    if arg_field:
        if arg_field not in fields:
            raise SystemExit(
                f"[{tool}] --field={arg_field!r} not found under {root}/. "
                f"Available: {fields or '(none)'}")
        return arg_field
    if not fields:
        raise SystemExit(f"[{tool}] No field profiles found under {root}/. "
                         f"{empty_hint}")
    if len(fields) > 1:
        raise SystemExit(
            f"[{tool}] Multiple fields present ({fields}); pass --field=<name> "
            "to select one.")
    return fields[0]
