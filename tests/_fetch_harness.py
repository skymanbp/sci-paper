"""The offline harness the fetch_arxiv_abstracts tests share.

Every CLI-level test runs `fetch` with a temporary repository root, no
sleeping and no network: `urlopen_backoff`, `fetch_page` and `_eprint_bytes`
fail the test unless a stub is named. Two test files use it (the tool's tests
outgrew the 750-line budget on 2026-09-27 and were split by subject), so the
harness lives here once.

The name starts with an underscore so `unittest discover` never collects it.
"""

from __future__ import annotations

import io
import json
import types
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

from _toolpath import TOOLS  # noqa: E402,F401 -- because importing it is what puts tools/ on sys.path

import fetch_arxiv_abstracts as fetch  # noqa: E402

ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

def _record(source: str, updated: str, journal_ref: str | None = "ApJ, 927, 101 (2021)",
            text: str = "word " * 60) -> dict:
    return {"section": "abstract", "text": text, "source": source,
            "year": 2020, "published": "2020-01-01", "updated": updated,
            "journal_ref": journal_ref,
            "journal": fetch.classify_journal(journal_ref), "doi": None}


LENSING = "weak lensing shear " * 20   # an abstract the [WGL] keyword shortcut keeps
# A bare (uncompressed) e-print that clears both full-text keep thresholds.
SOURCE = ("\\documentclass{article}\n\\section{A}\n" + "word " * 1600
          + "\\section{B}\n\\section{C}\n").encode("utf-8")


def _no_network(*args, **kwargs):
    raise AssertionError("a test reached the network layer")


def _throttle(arxiv_id: str) -> bytes:
    raise fetch.Throttled("429 after 3 backoffs totalling 420 s")


def _pages_once(pages: list[dict] | None):
    """A fetch_page stub: `pages` on the first call, an empty page after. The
    positional arguments of every call are kept on `stub.calls`."""
    def stub(*args, **kwargs):
        stub.calls.append(args)
        return list(pages or []) if len(stub.calls) == 1 else []
    stub.calls = []
    return stub


@contextmanager
def _offline(tmp: Path, **stubs):
    """Run `fetch` with `tmp` as the repository root, no sleeping and no network:
    `urlopen_backoff`, `fetch_page` and `_eprint_bytes` fail the test unless a
    stub is named here. Yields the captured (stdout, stderr) buffers."""
    stubs = {"REPO_ROOT": tmp, "urlopen_backoff": _no_network,
             "fetch_page": _no_network, "_eprint_bytes": _no_network, **stubs}
    saved = {name: getattr(fetch, name) for name in stubs}
    real_sleep, fetch.time.sleep = fetch.time.sleep, lambda seconds: None
    for name, stub in stubs.items():
        setattr(fetch, name, stub)
    try:
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            yield out, err
    finally:
        fetch.time.sleep = real_sleep
        for name, value in saved.items():
            setattr(fetch, name, value)


def _sweep(tmp: Path, argv: list[str], pages: list[dict] | None = None,
           field: str | None = "wgl", **stubs) -> tuple[int, str]:
    """Run the abstract sweep offline against `tmp` as the profile root; returns
    (exit status, stderr). A parser error propagates as SystemExit."""
    stubs.setdefault("fetch_page", _pages_once(pages))
    with _offline(tmp, **stubs) as (_, err):
        status = fetch.main(["--profile-root", str(tmp)]
                            + (["--field", field] if field else []) + argv)
    return status, err.getvalue()


def _fulltext(tmp: Path, argv: list[str], pages: list[dict] | None = None,
              **stubs) -> tuple[int, str, Path]:
    """Run --fulltext offline into tmp/style-corpus/wgl/fulltext-test; returns
    (exit status, stdout + stderr, that directory)."""
    stubs.setdefault("fetch_page", _pages_once(pages))
    with _offline(tmp, **stubs) as (out, err):
        status = fetch.main(["--field", "wgl", "--profile-root", str(tmp), "--fulltext",
                             "--fulltext-dir", "fulltext-test"] + argv)
    return status, out.getvalue() + err.getvalue(), tmp / "style-corpus" / "wgl" / "fulltext-test"


def _write_bank(tmp: Path, records: list[dict], name: str = fetch.BANK) -> Path:
    """Seed tmp/wgl/<name> with JSONL records, as an earlier sweep would have."""
    field = tmp / "wgl"
    field.mkdir(parents=True, exist_ok=True)
    out = field / name
    out.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return out


def _bank(path: Path) -> list[dict]:
    """The JSONL records a sweep wrote, or [] when the file does not exist."""
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _candidate_args(tmp: Path, **over) -> types.SimpleNamespace:
    """The argparse namespace `_candidate_ids` reads, with offline defaults."""
    base = dict(author="", author_is="", max_authors=0, query=[], updated_before="",
                profile_root=tmp, field="wgl", per_query=1, page=1, start_at=0,
                date_lo="201001010000", date_hi="202112312359", sleep=0)
    return types.SimpleNamespace(**{**base, **over})
