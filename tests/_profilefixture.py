"""A throwaway `style-profile/<field>/` directory holding one exemplar bank.

Every calibrated axis is tested the same way: write a small bank of records,
calibrate against it, then assert on what the axis does. Two test files spelled
that setup out record by record, and the copies had already drifted apart on
whether a record carries a `source` -- which decides whether a section-unit
reference can be built at all, so the difference was silent and load-bearing.

The name starts with an underscore so `unittest discover` never collects it.
"""

from __future__ import annotations

import contextlib
import json
import tempfile
from pathlib import Path


def write_bank(directory: Path, records) -> Path:
    """Write `records` as the field's exemplar bank and return its path."""
    path = directory / "exemplar_paragraphs.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    return path


def uniform(text: str, count: int, *, section: str = "abstract") -> list[dict]:
    """`count` copies of one passage: a reference with no spread in either tail.

    The degenerate case every percentile reader has to survive. Each record gets
    its own `source`, so the same bank is usable at section granularity.
    """
    return [{"section": section, "source": f"paper-{index:03d}.tex", "text": text}
            for index in range(count)]


@contextlib.contextmanager
def temp_profile(records, *, prefix: str = "profile-"):
    """A profile directory pre-loaded with `records`, removed on exit."""
    with tempfile.TemporaryDirectory(prefix=prefix) as raw:
        profile = Path(raw)
        write_bank(profile, records)
        yield profile
