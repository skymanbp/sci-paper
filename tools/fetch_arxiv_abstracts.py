"""Fetch dated arXiv corpora: abstracts, or complete LaTeX paper sources.

The default 2010--2021 interval supplies a pre-generative-AI reference set, and
broad astro-ph queries reduce dependence on one narrow topic. The date filter is
a provenance control, not proof of individual authorship. Records enter the
curated-field positive class of a compatibility task; the resulting model must
not be presented as an author detector.

Abstract mode (default) writes
``style-profile/<field>/human_abstracts_extra.jsonl`` (JSONL records with
``section``, ``text``, ``source``, ``year``). Full-text mode (``--fulltext``)
downloads each paper's e-print LaTeX source, keeps papers with at least three
``\\section`` commands, and stores one directory per paper under
``style-corpus/<field>/fulltext-arxiv/<id>/`` so complete-document calibration
treats each paper as ONE observation. Both outputs are local and gitignored.
Downloads are polite (>= 3 s between requests) per arXiv's rate guidance.
Network/API failures are reported explicitly.

Run: ``python tools/fetch_arxiv_abstracts.py --field wgl --per-query 400``
     ``python tools/fetch_arxiv_abstracts.py --field wgl --fulltext --max-papers 500``.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"

# Breadth: lensing/cluster terms + the main astro-ph subfields.
QUERIES = [
    "cat:astro-ph.CO AND abs:lensing",
    "cat:astro-ph.CO AND abs:cluster",
    "cat:astro-ph.CO AND abs:cosmology",
    "cat:astro-ph.GA",
    "cat:astro-ph.HE",
    "cat:astro-ph.SR",
    "cat:astro-ph.EP",
    # weak-lensing / cluster specifics (the target subfield)
    'cat:astro-ph.CO AND abs:"weak lensing"',
    'cat:astro-ph.CO AND abs:shear',
    'cat:astro-ph.CO AND abs:convergence',
    'cat:astro-ph.CO AND abs:"aperture mass"',
    'cat:astro-ph.CO AND abs:"mass map"',
]

# Target-author references: the advisor (Ian Dell'Antonio) plus widely cited
# weak-lensing / cluster-lensing authors. These records broaden the positive
# curated-field class; they do not turn the training task into authorship proof.
AUTHOR_QUERIES = [
    "au:Dell_Antonio_I",       # advisor
    "au:Hoekstra_H",
    "au:Mandelbaum_R",
    "au:Schneider_P AND cat:astro-ph.CO",
    "au:Bartelmann_M",
    "au:von_der_Linden_A",
    "au:Kaiser_N AND abs:lensing",
    "au:Applegate_D",
    "au:Umetsu_K",
    "au:Fu_L AND abs:lensing",
]


def fetch_page(query: str, start: int, n: int, date_lo: str, date_hi: str) -> list[dict]:
    q = f"({query}) AND submittedDate:[{date_lo} TO {date_hi}]"
    params = urllib.parse.urlencode({
        "search_query": q, "start": start, "max_results": n,
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    url = f"{API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "sci-paper-voice/0.13"})
    with urllib.request.urlopen(req, timeout=60) as r:
        xml = r.read().decode("utf-8", "replace")
    root = ET.fromstring(xml)
    out = []
    for e in root.findall(f"{ATOM}entry"):
        summ = e.findtext(f"{ATOM}summary") or ""
        pub = e.findtext(f"{ATOM}published") or ""
        aid = e.findtext(f"{ATOM}id") or ""
        text = " ".join(summ.split()).strip()
        year = int(pub[:4]) if pub[:4].isdigit() else 0
        arid = aid.rsplit("/", 1)[-1] if aid else ""
        if text and len(text.split()) >= 40:
            out.append({"section": "abstract", "text": text,
                        "source": f"arxiv:{arid}", "year": year})
    return out


# Full-text mode: field-specific queries give the closest genre match for the
# complete-document (dispersion) reference; the broad categories stay abstract-only.
FULLTEXT_QUERIES = [
    'cat:astro-ph.CO AND abs:"weak lensing"',
    "cat:astro-ph.CO AND abs:lensing",
    "cat:astro-ph.CO AND abs:cluster",
    "cat:astro-ph.CO AND abs:shear",
    "cat:astro-ph.CO AND abs:convergence",
    'cat:astro-ph.CO AND abs:"aperture mass"',
    'cat:astro-ph.CO AND abs:"mass map"',
]
EPRINT = "https://export.arxiv.org/e-print/"
MIN_FULLTEXT_SECTIONS = 3
MIN_FULLTEXT_WORDS = 1500
_SECTION_RE = re.compile(r"\\section\*?\{")


def _eprint_bytes(arxiv_id: str) -> bytes:
    req = urllib.request.Request(
        EPRINT + urllib.parse.quote(arxiv_id),
        headers={"User-Agent": "sci-paper-voice/0.14 (corpus builder)"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def _tex_members(raw: bytes) -> dict[str, str] | None:
    """Extract .tex files from an e-print payload; None if no LaTeX source.

    e-prints arrive as gzipped tarballs, gzipped single .tex files, or bare
    PDFs (no source). Tar extraction is member-filtered in memory, so no
    archive paths ever touch the filesystem.
    """
    if raw[:4] == b"%PDF":
        return None
    if raw[:2] == b"\x1f\x8b":
        try:
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
                out: dict[str, str] = {}
                for member in archive.getmembers():
                    if not member.isfile() or not member.name.lower().endswith(".tex"):
                        continue
                    handle = archive.extractfile(member)
                    if handle is None:
                        continue
                    name = Path(member.name).name  # strip any archive paths
                    out[name] = handle.read().decode("utf-8", "replace")
                return out or None
        except tarfile.ReadError:
            try:
                text = gzip.decompress(raw).decode("utf-8", "replace")
            except OSError:
                return None
            return {"main.tex": text} if "\\documentclass" in text else None
    if raw.lstrip()[:14].startswith(b"\\documentclass"):
        return {"main.tex": raw.decode("utf-8", "replace")}
    return None


_FIELD_RELEVANCE_RE = re.compile(
    r"(?i)\b(lensing|shear|convergence|aperture mass|mass map|cluster)\b")


def _candidate_ids(args) -> list[str]:
    """Candidate arXiv IDs for full-text download.

    Prefer the already-fetched local abstract corpus (no query-API traffic,
    which is rate-limited after a bulk abstract run): filter its records by
    field-relevant abstract keywords. Fall back to live queries only when the
    local corpus is absent.
    """
    jsonl = args.profile_root / args.field / "human_abstracts_extra.jsonl"
    if jsonl.exists():
        candidates: list[str] = []
        seen: set[str] = set()
        with jsonl.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if not _FIELD_RELEVANCE_RE.search(record.get("text", "")):
                    continue
                arxiv_id = str(record.get("source", "")).removeprefix("arxiv:")
                if arxiv_id and arxiv_id not in seen:
                    seen.add(arxiv_id)
                    candidates.append(arxiv_id)
        print(f"[fulltext] {len(candidates)} field-relevant candidates from "
              f"local {jsonl.name}", file=sys.stderr)
        return candidates
    candidates = []
    seen = set()
    for query in FULLTEXT_QUERIES:
        for start in range(0, args.per_query, args.page):
            try:
                page = fetch_page(query, start,
                                  min(args.page, args.per_query - start),
                                  args.date_lo, args.date_hi)
            except Exception as error:  # network/API hiccup: report, keep going
                print(f"[fulltext] {query!r} start={start} error: {error}",
                      file=sys.stderr)
                page = []
            for record in page:
                arxiv_id = record["source"].removeprefix("arxiv:")
                if arxiv_id and arxiv_id not in seen:
                    seen.add(arxiv_id)
                    candidates.append(arxiv_id)
            if not page:
                break
            time.sleep(args.sleep)
    print(f"[fulltext] {len(candidates)} candidate papers from "
          f"{len(FULLTEXT_QUERIES)} live queries", file=sys.stderr)
    return candidates


def fetch_fulltext(args) -> int:
    out_root = (REPO_ROOT / "style-corpus" / args.field / "fulltext-arxiv")
    out_root.mkdir(parents=True, exist_ok=True)
    candidates = _candidate_ids(args)

    kept = skipped = failed = 0
    for arxiv_id in candidates:
        if kept >= args.max_papers:
            break
        safe = arxiv_id.replace("/", "_")
        paper_dir = out_root / safe
        if paper_dir.exists() and any(paper_dir.glob("*.tex")):
            kept += 1  # resumable: already fetched and validated
            continue
        try:
            raw = _eprint_bytes(arxiv_id)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                # Rate-limited: one long backoff then one retry; a second 429
                # means today's budget is spent, so stop cleanly (resumable).
                print(f"[fulltext] 429 on {arxiv_id}; backing off 60 s",
                      file=sys.stderr)
                time.sleep(60)
                try:
                    raw = _eprint_bytes(arxiv_id)
                except Exception as retry_error:
                    print(f"[fulltext] still throttled ({retry_error}); "
                          f"stopping with kept={kept} (rerun later to resume)",
                          file=sys.stderr)
                    break
            else:
                print(f"[fulltext] {arxiv_id}: HTTP {error.code}", file=sys.stderr)
                failed += 1
                time.sleep(args.sleep)
                continue
        except Exception as error:  # per-paper failure must not kill the sweep
            print(f"[fulltext] {arxiv_id}: download error: {error}", file=sys.stderr)
            failed += 1
            time.sleep(args.sleep)
            continue
        members = _tex_members(raw)
        time.sleep(args.sleep)
        if not members:
            skipped += 1
            continue
        combined = "\n\n".join(members[name] for name in sorted(members))
        n_sections = len(_SECTION_RE.findall(combined))
        n_words = len(combined.split())
        if n_sections < MIN_FULLTEXT_SECTIONS or n_words < MIN_FULLTEXT_WORDS:
            skipped += 1
            continue
        paper_dir.mkdir(parents=True, exist_ok=True)
        for name in sorted(members):
            (paper_dir / Path(name).name).write_text(members[name],
                                                     encoding="utf-8")
        kept += 1
        if kept % 25 == 0:
            print(f"[fulltext] kept={kept} skipped={skipped} failed={failed}",
                  file=sys.stderr, flush=True)
    print(f"[fulltext] DONE kept={kept} skipped={skipped} failed={failed} "
          f"-> {out_root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--field", required=True)
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--per-query", type=int, default=400)
    p.add_argument("--page", type=int, default=100)
    p.add_argument("--date-lo", default="201001010000")
    p.add_argument("--date-hi", default="202112312359")
    p.add_argument("--sleep", type=float, default=3.0)
    p.add_argument("--fulltext", action="store_true",
                   help="download complete LaTeX paper sources (one directory "
                        "per paper) instead of abstracts")
    p.add_argument("--max-papers", type=int, default=300,
                   help="full-text mode: stop after this many kept papers")
    args = p.parse_args(argv)
    if args.sleep < 3.0:
        p.error("--sleep must be >= 3 seconds (arXiv rate guidance)")
    if args.fulltext:
        return fetch_fulltext(args)

    field_dir = args.profile_root / args.field
    field_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    recs: list[dict] = []
    # Topic/breadth queries first, then the authoritative-author queries.
    for query in QUERIES + AUTHOR_QUERIES:
        got = 0
        for start in range(0, args.per_query, args.page):
            try:
                page = fetch_page(query, start, min(args.page, args.per_query - start),
                                  args.date_lo, args.date_hi)
            except Exception as e:  # network/API hiccup on one page: report, keep going
                print(f"[fetch] {query!r} start={start} error: {e}", file=sys.stderr)
                page = []
            new = 0
            for r in page:
                if r["source"] not in seen:
                    seen.add(r["source"]); recs.append(r); new += 1; got += 1
            print(f"[fetch] {query!r} start={start}: +{new} (total {len(recs)})",
                  file=sys.stderr)
            if not page:
                break
            time.sleep(args.sleep)
        print(f"[fetch] {query!r}: {got} kept", file=sys.stderr)

    out = field_dir / "human_abstracts_extra.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    years = sorted({r["year"] for r in recs})
    print(f"[fetch] wrote {len(recs)} dated curated-field abstracts -> {out}")
    print(f"[fetch] year span: {years[0] if years else '-'}..{years[-1] if years else '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
