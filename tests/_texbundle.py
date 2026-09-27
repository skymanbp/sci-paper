"""A throwaway LaTeX source bundle: named `.tex` bodies written to one directory.

The root-selection tests (`test_extract_style`) and the include-assembly tests
(`test_tex_assembly`) carried four copies of this writer between them by
2026-09-27. The name starts with an underscore so `unittest discover` never
collects it.
"""

from __future__ import annotations

from pathlib import Path


def write_bundle(tmp: str, files: dict[str, str]) -> Path:
    """Write each `name: body` under `<tmp>/bundle/` and return that directory.

    A name may carry a subdirectory (`sections/intro.tex`), as an unflattened
    arXiv source does; its parent directories are created.
    """
    directory = Path(tmp) / "bundle"
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return directory
