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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
# One source of truth for which directory extract_style.py reads as calibration
# breadth, so the held-out interlock below cannot drift away from the reader.
from extract_style import REFERENCE_DIR  # noqa: E402 -- same sys.path reason

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"

# Journal selection is done HERE, not in the API query: the API's jr: prefix
# is a loose token match, and jr:"Astronomy and Astrophysics" was observed to
# return "Research in Astronomy and Astrophysics" (a different journal). Each
# entry is (key, include, exclude) and the first match wins, so the Letters
# pattern must precede the main-journal pattern it is a substring of. The
# include forms are the literal shapes seen in live journal_ref values
# ("Astrophys. J. 934, no.2, 129 (2022)", "ApJ, 927, 101 (2022)",
# "The Astrophysical Journal Letters, Volume 924 (2022), Number 1, L3",
# "A&A 660, A114 (2022)"), not remembered canonical names.
JOURNAL_FILTERS = (
    ("apjl",
     re.compile(r"(?i)\b(?:ApJL|ApJ\.?\s*Lett\w*|Astrophys\w*\.?\s*J\w*\.?\s*Lett\w*)"),
     None),
    ("apj",
     re.compile(r"(?i)\b(?:ApJ|Astrophys\w*\.?\s*J\w*)"),
     re.compile(r"(?i)(?:Lett|Suppl|ApJS)")),
    ("aa",
     re.compile(r"(?i)(?:\bA&A\b|\bAstronomy\s*(?:&|and)\s*Astrophysics\b)"),
     re.compile(r"(?i)(?:Research\s+in\s+Astronomy|\bRAA\b|\bRev(?:iew)?s?\b"
                r"|New\s+Astronomy)")),
)


def classify_journal(journal_ref: str | None) -> str | None:
    """Return the journal key for a journal_ref string, or None if unmatched."""
    if not journal_ref:
        return None
    for key, include, exclude in JOURNAL_FILTERS:
        if include.search(journal_ref) and not (exclude and exclude.search(journal_ref)):
            return key
    return None

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
#
# The QUERY FORM was wrong until 2026-08-26: `Surname_Initial` is the arXiv
# LISTING url's format (/a/hoekstra_h_1), not the search API's `au:` syntax, so
# all ten returned 0 records and the `broad` set was silently ten queries short.
# `au:` then matches a SURNAME, which is not a person, so every entry below was
# checked against the names it returns. Nine resolve to one person; `Schneider,
# P` did not -- Donald P. Schneider (SDSS quasars) on 58 papers against Peter
# Schneider's 33 -- so that entry spells the given name out. `cat:astro-ph*` is
# the other half: unscoped, "Dell'Antonio" adds 20 math-ph records.
AUTHOR_QUERIES = [
    'au:"Dell\'Antonio" AND cat:astro-ph*',    # advisor
    'au:"Hoekstra, H" AND cat:astro-ph*',
    'au:"Mandelbaum, R" AND cat:astro-ph*',
    'au:"Schneider, Peter" AND cat:astro-ph*',
    'au:"Bartelmann, M" AND cat:astro-ph*',
    'au:"von der Linden, A" AND cat:astro-ph*',
    'au:"Kaiser, N" AND abs:lensing',
    'au:"Applegate, D" AND cat:astro-ph*',
    'au:"Umetsu, K" AND cat:astro-ph*',
    'au:"Fu, L" AND abs:lensing',
]

# Weak-lensing-only sweep, for a reference matched to THIS suite's subfield
# rather than to astro-ph at large. Used with --journals to keep only the
# refereed top-tier record; the breadth queries above stay the default.
WL_QUERIES = [
    'cat:astro-ph.CO AND abs:"weak lensing"',
    'cat:astro-ph.CO AND abs:"weak gravitational lensing"',
    'cat:astro-ph.CO AND abs:"cosmic shear"',
    'cat:astro-ph.CO AND abs:"shear catalog"',
    'cat:astro-ph.CO AND abs:"shear measurement"',
    'cat:astro-ph.CO AND abs:"aperture mass"',
    'cat:astro-ph.CO AND abs:"mass map"',
    'cat:astro-ph.CO AND abs:"convergence map"',
    'cat:astro-ph.CO AND abs:"lensing peak"',
    'cat:astro-ph.CO AND abs:"peak statistics"',
    'cat:astro-ph.CO AND abs:"cluster lensing"',
    'cat:astro-ph.CO AND abs:"mass reconstruction"',
    'cat:astro-ph.CO AND abs:lensing AND abs:substructure',
    'cat:astro-ph.CO AND abs:lensing AND abs:"halo mass"',
    'cat:astro-ph.GA AND abs:"weak lensing"',
    'cat:astro-ph.IM AND abs:"weak lensing"',
]
QUERY_SETS = {"broad": QUERIES + AUTHOR_QUERIES, "wl": WL_QUERIES}


class Throttled(Exception):
    """arXiv answered 429 and kept answering 429 after every backoff.

    Distinct from an ordinary network hiccup because the response differs: a
    hiccup is skipped and the sweep continues, whereas throttling means every
    later request will fail too, so the sweep must stop and SAY it stopped.
    """


# Escalating waits, in seconds, after a 429. Exhausting them raises Throttled.
BACKOFF_SCHEDULE = (60, 120, 240)


def urlopen_backoff(request: urllib.request.Request, timeout: int) -> bytes:
    """Single retry-on-429 path shared by the abstract and full-text modes.

    Both modes previously needed this and only the full-text one had it, so a
    throttled abstract sweep silently produced a truncated corpus that looked
    exactly like a complete one.
    """
    for attempt, wait in enumerate((*BACKOFF_SCHEDULE, None)):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code != 429 or wait is None:
                if error.code == 429:
                    raise Throttled(
                        f"429 after {attempt} backoffs "
                        f"totalling {sum(BACKOFF_SCHEDULE)} s") from error
                raise
            print(f"[fetch] HTTP 429; backing off {wait} s "
                  f"(attempt {attempt + 1}/{len(BACKOFF_SCHEDULE)})",
                  file=sys.stderr, flush=True)
            time.sleep(wait)
    raise Throttled("unreachable")  # the None sentinel always raises above


def fetch_page(query: str, start: int, n: int, date_lo: str, date_hi: str) -> list[dict]:
    q = f"({query}) AND submittedDate:[{date_lo} TO {date_hi}]"
    params = urllib.parse.urlencode({
        "search_query": q, "start": start, "max_results": n,
        "sortBy": "submittedDate", "sortOrder": "descending",
    })
    url = f"{API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "sci-paper-voice/0.13"})
    xml = urlopen_backoff(req, timeout=60).decode("utf-8", "replace")
    root = ET.fromstring(xml)
    out = []
    for e in root.findall(f"{ATOM}entry"):
        summ = e.findtext(f"{ATOM}summary") or ""
        pub = e.findtext(f"{ATOM}published") or ""
        aid = e.findtext(f"{ATOM}id") or ""
        text = " ".join(summ.split()).strip()
        year = int(pub[:4]) if pub[:4].isdigit() else 0
        # An old-style id is `archive/YYMMNNN` and the archive is PART of it:
        # the e-print endpoint 404s without it (7 of 19 in a measured sweep).
        arid = aid.split("/abs/", 1)[-1] if "/abs/" in aid else aid.rsplit("/", 1)[-1]
        # `published` dates v1; `summary` is the LATEST version's abstract, so
        # submittedDate alone does not date the text. Measured on a live
        # 2010-2021 weak-lensing page, 11 of 12 entries had updated > published
        # and two landed after 2022-11 — i.e. after the text could have been
        # revised with a public LLM. `updated` is what dates the abstract.
        updated = e.findtext(f"{ATOM}updated") or ""
        # journal_ref and doi live in the arXiv namespace, not Atom's, and only
        # ~37% of entries carry a journal_ref at all (measured on a live WL
        # query), so any journal-restricted run has to over-fetch.
        journal_ref = e.findtext(f"{ARXIV}journal_ref")
        if journal_ref:
            journal_ref = " ".join(journal_ref.split())
        # Team size, for the full-text author sweep's --max-authors. Only the
        # API carries a clean list: counting `\author` in the LaTeX picks up
        # template placeholder lines, and a live AASTeX source in this corpus
        # has one ("\author[xxxx-xxxx-xxxx-xxxx]{Author Name}").
        authors = [(person.findtext(f"{ATOM}name") or "").strip()
                   for person in e.findall(f"{ATOM}author")]
        if text and len(text.split()) >= 40:
            out.append({"section": "abstract", "text": text,
                        "source": f"arxiv:{arid}", "year": year,
                        "published": pub[:10], "updated": updated[:10],
                        "journal_ref": journal_ref,
                        "journal": classify_journal(journal_ref),
                        "authors": [name for name in authors if name],
                        "doi": e.findtext(f"{ARXIV}doi")})
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
    return urlopen_backoff(req, timeout=120)


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


RE_ARXIV_ID = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?_?\d{7})")


def _bare(arxiv_id: str) -> str:
    """An arXiv id without its version suffix, for identity comparisons."""
    return re.sub(r"v\d+$", "", arxiv_id.strip()).replace("/", "_")


def known_calibration_ids(args) -> set[str]:
    """Every arXiv id whose text already feeds a calibration bank.

    A held-out measurement is only held out if the paper contributed nothing to
    what the axes were calibrated on. `register_lexicon.json` and
    `salience_baseline.json` are both built from `exemplar_paragraphs.jsonl`
    (the weighted tiers plus the unweighted `fulltext-arxiv/` breadth pull) and
    `human_abstracts_extra.jsonl`, so an id reachable from any of those three
    places is disqualified. This matters at the observed scale rather than in
    principle: `deai_register.RARE_DF_RATE` is 1e-4, which on 41,559 passages
    puts the foreign-term threshold at four passages, so one paper's own
    contribution is enough to suppress its own flags.
    """
    known: set[str] = set()
    bank = args.profile_root / args.field / "human_abstracts_extra.jsonl"
    if bank.exists():
        with bank.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                source = str(json.loads(line).get("source", ""))
                if source.startswith("arxiv:"):
                    known.add(_bare(source.removeprefix("arxiv:")))
    corpus = REPO_ROOT / "style-corpus" / args.field
    if corpus.is_dir():
        for entry in corpus.glob("fulltext-*/*"):
            if entry.is_dir():
                known.add(_bare(entry.name))
        # Tier filenames carry the arXiv id of the paper they hold
        # ("...__astro-ph_9912508"), which is the only machine-readable link
        # between a curated PDF and the arXiv record a query would return.
        for tier in corpus.glob("tier-*/*"):
            for match in RE_ARXIV_ID.findall(tier.name):
                known.add(_bare(match))
    return known


def _candidate_ids(args, exclude: set[str] | None = None,
                   journals: set[str] | None = None) -> list[str]:
    """Candidate arXiv IDs for full-text download.

    Prefer the already-fetched local abstract corpus (no query-API traffic,
    which is rate-limited after a bulk abstract run): filter its records by
    field-relevant abstract keywords. Fall back to live queries only when the
    local corpus is absent.

    `exclude` disqualifies ids by bare form. When it is supplied the local
    shortcut is skipped outright rather than filtered: that shortcut reads
    `human_abstracts_extra.jsonl`, which is one of the banks `exclude` is built
    from, so every id it can offer is already disqualified. `journals` keeps
    only records whose `journal_ref` classifies into one of the given keys,
    which is what makes the resulting set *refereed* rather than merely
    on-arXiv -- the live path carries `journal_ref`, so this is only available
    there.

    `--author` replaces the topic queries with one author query and, like
    `exclude`, forces the live path. `--max-authors` then bounds team size from
    the API's author list, before any 3 s e-print download is spent.
    """
    exclude = exclude or set()
    # A bare name is quoted; a value already carrying a query operator passes
    # through, because `au:` alone is not field-scoped and often must be: 32 of
    # 100 `au:"Kaiser, N"` papers are nuclear theory, under the same spelling.
    author = args.author if ":" in args.author else f'au:"{args.author}"'
    queries = [author] if args.author else FULLTEXT_QUERIES
    max_authors = getattr(args, "max_authors", 0) or 0
    jsonl = args.profile_root / args.field / "human_abstracts_extra.jsonl"
    # `--author` names WHO; the local shortcut answers WHAT-about. It filters the
    # abstract bank on field keywords and never looks at an author, so taking it
    # for an author sweep would quietly return the wrong people's papers.
    if jsonl.exists() and not exclude and not args.author:
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
    identity = (re.compile(getattr(args, "author_is", "") or "", re.IGNORECASE)
                if getattr(args, "author_is", "") else None)
    dropped_known = dropped_journal = dropped_team = 0
    dropped_unknown_team = dropped_identity = 0
    for query in queries:
        for start in range(args.start_at, args.start_at + args.per_query,
                           args.page):
            try:
                page = fetch_page(query, start,
                                  min(args.page, args.per_query - start),
                                  args.date_lo, args.date_hi)
            except Throttled as error:
                print(f"[fulltext] THROTTLED building candidates: {error}; "
                      f"proceeding with {len(candidates)} found so far",
                      file=sys.stderr)
                return candidates
            except Exception as error:  # network/API hiccup: report, keep going
                print(f"[fulltext] {query!r} start={start} error: {error}",
                      file=sys.stderr)
                page = []
            for record in page:
                arxiv_id = record["source"].removeprefix("arxiv:")
                if not arxiv_id or arxiv_id in seen:
                    continue
                seen.add(arxiv_id)
                if _bare(arxiv_id) in exclude:
                    dropped_known += 1
                    continue
                if journals and record.get("journal") not in journals:
                    dropped_journal += 1
                    continue
                team = record.get("authors") or []
                # `au:` matches a SURNAME, and a surname is not a person, so the
                # identity test is separate from the search term rather than
                # folded into it.
                if identity and not any(identity.search(name) for name in team):
                    dropped_identity += 1
                    continue
                if max_authors:
                    # An unlisted team cannot be SHOWN to be within the limit,
                    # so it is dropped and counted rather than assumed small --
                    # the same reading the --updated-before filter applies to a
                    # record with no `updated` date.
                    if not team:
                        dropped_unknown_team += 1
                        continue
                    if len(team) > max_authors:
                        dropped_team += 1
                        continue
                candidates.append(arxiv_id)
            if not page:
                break
            time.sleep(args.sleep)
    print(f"[fulltext] {len(candidates)} candidate papers from "
          f"{len(queries)} live queries "
          f"(dropped {dropped_known} already-calibrated, "
          f"{dropped_journal} off-journal, {dropped_identity} not the named "
          f"author, {dropped_team} over {max_authors or '-'} authors, "
          f"{dropped_unknown_team} with no author list)", file=sys.stderr)
    return candidates


def fetch_fulltext(args) -> int:
    out_root = (REPO_ROOT / "style-corpus" / args.field / args.fulltext_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    exclude = known_calibration_ids(args) if args.exclude_known else set()
    journals = {k.strip().lower() for k in args.journals.split(",") if k.strip()}
    if exclude:
        print(f"[fulltext] holding out: {len(exclude)} arXiv ids already feed a "
              f"calibration bank", file=sys.stderr)
    candidates = _candidate_ids(args, exclude, journals)

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
        except Throttled as error:
            # Backoff is exhausted inside urlopen_backoff; today's budget is
            # spent, so stop cleanly. The per-paper directories make this
            # resumable on a later run.
            print(f"[fulltext] {error}; stopping with kept={kept} "
                  f"(rerun later to resume)", file=sys.stderr)
            break
        except urllib.error.HTTPError as error:
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
    cli_common.utf8_stdout()
    p = cli_common.field_parser(__doc__)
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
    p.add_argument("--fulltext-dir", default=REFERENCE_DIR,
                   help="full-text mode: directory name under "
                        f"style-corpus/<field>/ (default {REFERENCE_DIR!r}, "
                        "which extract_style.py reads as breadth calibration). "
                        "Any other fulltext-* name is held out of calibration "
                        "by construction and is what an evaluation set needs.")
    p.add_argument("--start-at", type=int, default=0,
                   help="full-text mode: first result offset per query. "
                        "Results come back newest-first, so an existing corpus "
                        "occupies a contiguous shallow band: measured on "
                        "'cat:astro-ph.CO AND abs:cluster', offsets 0-2000 were "
                        "100%% already-calibrated and 2000+ were ~85%% new. "
                        "Skipping that band is what makes a held-out sweep "
                        "affordable at 3 s per request.")
    p.add_argument("--author", default="",
                   help="full-text mode: fetch one author's papers instead of "
                        "the topic sweep -- a bare name (\"Dell'Antonio\") or a "
                        "whole query ('au:\"Kaiser, N\" AND cat:astro-ph*').")
    p.add_argument("--author-is", default="",
                   help="full-text mode: keep only papers with an author name "
                        "matching this regex; `au:` matches a surname, not a person.")
    p.add_argument("--max-authors", type=int, default=0,
                   help="full-text mode: keep only papers with at most this "
                        "many authors (0 = no limit). A paper the API lists no "
                        "authors for is dropped, not assumed small.")
    p.add_argument("--exclude-known", action="store_true",
                   help="full-text mode: drop every candidate whose text "
                        "already feeds a calibration bank (the abstract corpus, "
                        "fulltext-*/ pulls, or a tier filename's arXiv id), so "
                        "the result is a genuine held-out set")
    p.add_argument("--query-set", choices=sorted(QUERY_SETS), default="broad",
                   help="'broad' = astro-ph breadth + authoritative authors "
                        "(default); 'wl' = weak-lensing subfield only")
    p.add_argument("--journals", default="",
                   help="comma-separated journal keys to keep "
                        f"({', '.join(k for k, _, _ in JOURNAL_FILTERS)}); "
                        "empty keeps every record, refereed or not")
    p.add_argument("--out-name", default="human_abstracts_extra.jsonl",
                   help="output filename under the field profile directory. "
                        "A journal-restricted or subfield run MUST pass a "
                        "different name: the writer truncates its target, so "
                        "reusing the default would destroy the broad corpus.")
    p.add_argument("--updated-before", default="",
                   help="YYYY-MM-DD; drop records whose LATEST arXiv version "
                        "is dated on or after this. --date-hi bounds the v1 "
                        "submission, which does not date the returned "
                        "abstract; only this bounds the text itself.")
    p.add_argument("--resume", action="store_true",
                   help="seed from the existing --out-name file and keep its "
                        "records, so a run cut short by rate limiting is "
                        "extended rather than replaced")
    args = p.parse_args(argv)
    if args.sleep < 3.0:
        p.error("--sleep must be >= 3 seconds (arXiv rate guidance)")
    # Validated for BOTH modes: full-text mode used to skip this block entirely,
    # so `--fulltext --journals apjjl` silently kept nothing rather than failing.
    wanted = {k.strip().lower() for k in args.journals.split(",") if k.strip()}
    known = {key for key, _, _ in JOURNAL_FILTERS}
    if wanted - known:
        p.error(f"unknown journal key(s): {sorted(wanted - known)}; known: {sorted(known)}")
    if (args.author or args.max_authors or args.author_is) and not args.fulltext:
        p.error("--author/--author-is/--max-authors select whole papers, which "
                "only --fulltext downloads; the abstract sweep has --query-set")
    if args.fulltext:
        if "/" in args.fulltext_dir or "\\" in args.fulltext_dir:
            p.error("--fulltext-dir must be a bare directory name")
        if args.author and args.fulltext_dir == REFERENCE_DIR:
            p.error(f"--author writes a population you intend to MEASURE, but "
                    f"--fulltext-dir {REFERENCE_DIR!r} is the directory "
                    f"extract_style.py reads as calibration breadth. Papers in "
                    f"a calibration bank have their own vocabulary in the "
                    f"denominator: ~94% of register findings on an in-sample "
                    f"paper are suppressed by that membership (EVALUATION "
                    f"section 17.3), so the axis would go quiet on exactly the "
                    f"prose you fetched it to judge. Choose another "
                    f"fulltext-* name.")
        if args.exclude_known and args.fulltext_dir == REFERENCE_DIR:
            p.error(f"--exclude-known writes a held-out set, but "
                    f"--fulltext-dir {REFERENCE_DIR!r} is the directory "
                    f"extract_style.py reads as calibration breadth; the next "
                    f"rebuild would absorb the held-out papers and the set "
                    f"would stop being held out. Choose another fulltext-* name.")
        return fetch_fulltext(args)

    if (wanted or args.query_set != "broad") and \
            args.out_name == "human_abstracts_extra.jsonl":
        p.error("a journal-restricted or subfield run needs --out-name; "
                "writing to human_abstracts_extra.jsonl would truncate the "
                "broad corpus that the calibration baselines are built from")

    field_dir = args.profile_root / args.field
    field_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    recs: list[dict] = []
    dropped_no_ref = dropped_other = dropped_revised = 0
    if args.updated_before and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",
                                                args.updated_before):
        p.error("--updated-before must be YYYY-MM-DD")
    if args.resume:
        # Rate limiting makes a full sweep a multi-run affair, and the writer
        # truncates its target, so without this a rerun would shrink the corpus
        # instead of growing it.
        existing = field_dir / args.out_name
        if existing.exists():
            with existing.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)  # a pre-2026 bank stored year as str
                    year = str(record.get("year") or "")
                    record["year"] = int(year) if year.isdigit() else 0
                    if record.get("source") not in seen:
                        seen.add(record["source"])
                        recs.append(record)
            print(f"[fetch] resume: {len(recs)} records carried over from "
                  f"{existing.name}", file=sys.stderr)
    queries = QUERY_SETS[args.query_set]
    throttled_at: str | None = None
    incomplete_queries: list[str] = []
    for index, query in enumerate(queries):
        if throttled_at:
            break
        got = 0
        for start in range(0, args.per_query, args.page):
            try:
                page = fetch_page(query, start, min(args.page, args.per_query - start),
                                  args.date_lo, args.date_hi)
            except Throttled as e:
                # Not a hiccup: every later request would fail too. Stop the
                # sweep so the truncation is reported instead of being written
                # out as if it were the complete corpus.
                print(f"[fetch] THROTTLED on {query!r} start={start}: {e}",
                      file=sys.stderr)
                throttled_at = f"query {index + 1}/{len(queries)} {query!r} start={start}"
                break
            except Exception as e:
                # A failed page and an exhausted query both used to arrive here
                # as `page = []`, and the `if not page: break` below cannot tell
                # them apart -- so one hiccup silently ended that query's
                # pagination and the run still exited 0, reporting a short
                # corpus as a complete one. Record the query as incomplete and
                # stop paginating IT, without claiming the sweep succeeded.
                print(f"[fetch] {query!r} start={start} error: {e}", file=sys.stderr)
                incomplete_queries.append(f"{query!r} start={start}: {e}")
                break
            new = 0
            for r in page:
                if r["source"] in seen:
                    continue
                seen.add(r["source"])
                # ISO dates compare correctly as strings; a record with no
                # updated field cannot be shown to predate the cutoff, so it
                # is dropped rather than assumed clean.
                if args.updated_before and not (
                        r["updated"] and r["updated"] < args.updated_before):
                    dropped_revised += 1
                    continue
                if wanted:
                    if not r["journal_ref"]:
                        dropped_no_ref += 1
                        continue
                    if r["journal"] not in wanted:
                        dropped_other += 1
                        continue
                # The abstract bank is a PROSE corpus -- `voice_dataset`, the
                # register lexicon and the reference banks all read it as text.
                # Author names are not prose, so the list stays in the full-text
                # path that needs it rather than entering every record here.
                r.pop("authors", None)
                recs.append(r); new += 1; got += 1
            print(f"[fetch] {query!r} start={start}: +{new} (total {len(recs)})",
                  file=sys.stderr)
            if not page:
                break
            time.sleep(args.sleep)
        print(f"[fetch] {query!r}: {got} kept", file=sys.stderr)

    out = field_dir / args.out_name
    with out.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    years = sorted({r["year"] for r in recs})
    print(f"[fetch] wrote {len(recs)} dated curated-field abstracts -> {out}")
    print(f"[fetch] year span: {years[0] if years else '-'}..{years[-1] if years else '-'}")
    if wanted:
        by_journal: dict[str, int] = {}
        for r in recs:
            by_journal[r["journal"]] = by_journal.get(r["journal"], 0) + 1
        print(f"[fetch] journal filter {sorted(wanted)}: kept "
              f"{sorted(by_journal.items())}; dropped {dropped_no_ref} with no "
              f"journal_ref, {dropped_other} in other journals")
    if args.updated_before:
        print(f"[fetch] text-vintage filter updated < {args.updated_before}: "
              f"dropped {dropped_revised} records revised on or after it")
    if throttled_at:
        # Exit 2, not 0: a truncated corpus that reports success is how a
        # rate-limited run gets mistaken for an exhaustive one.
        print(f"[fetch] TRUNCATED — stopped at {throttled_at}; "
              f"{len(queries)} queries planned. Rerun later with --resume to "
              f"extend; records already written are valid.", file=sys.stderr)
        return 2
    if incomplete_queries:
        # Same principle at query granularity: these queries stopped early on a
        # transient error, so the corpus is short by an unknown amount. Naming
        # them and exiting 2 is the only way the caller can tell this run from
        # an exhaustive one.
        print(f"[fetch] INCOMPLETE — {len(incomplete_queries)} of "
              f"{len(queries)} queries stopped early on a page error:",
              file=sys.stderr)
        for entry in incomplete_queries:
            print(f"[fetch]   {entry}", file=sys.stderr)
        print("[fetch] Rerun with --resume to extend; records already written "
              "are valid.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
