"""Fetch dated arXiv corpora: abstracts, or complete LaTeX paper sources.

The default 2010--2021 interval supplies a pre-generative-AI reference set. The date
filter is a provenance control, not proof of individual authorship; records enter the
curated-field positive class of a compatibility task, and the model must not be
presented as an author detector. The built-in query sets, keyword filter and journal
table are ``[WGL]``: broad astro-ph queries keep the corpus from depending on one
narrow topic. Any other field passes its own ``--query`` terms, which replace them.

Abstract mode (default) writes ``style-profile/<field>/human_abstracts_extra.jsonl``
(JSONL records with ``section``, ``text``, ``source``, ``year``). Full-text mode
(``--fulltext``) downloads each paper's e-print LaTeX source, keeps papers with at
least three ``\\section`` commands, and stores one directory per bare arXiv id under
``style-corpus/<field>/fulltext-arxiv/<id>/``, so complete-document calibration
treats each paper as ONE observation. Both outputs are local and gitignored.
Downloads are polite (>= 3 s between requests) per arXiv's rate guidance; failures
are reported, and a throttled run exits 2 in either mode.

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
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
# One source of truth for which directory extract_style.py reads as calibration
# breadth, so the held-out interlock below cannot drift away from the reader.
from extract_style import REFERENCE_DIR  # noqa: E402 -- same sys.path reason
from tex_assembly import RE_TEX_DOC_MARKER  # noqa: E402 -- same sys.path reason

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
API = "http://export.arxiv.org/api/query"
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
BANK = "human_abstracts_extra.jsonl"  # the abstract bank every downstream reader opens

# [WGL] Journal keys for --journals. Selection is done HERE, not in the API query: the
# API's jr: prefix is a loose token match, and jr:"Astronomy and Astrophysics" was
# observed to return "Research in Astronomy and Astrophysics" (a different journal).
# Each entry is (key, include, exclude) and the first match wins, so the Letters
# pattern must precede the main-journal pattern it is a substring of. The include forms
# are the literal shapes seen in live journal_ref values ("Astrophys. J. 934, no.2, 129
# (2022)", "ApJ, 927, 101 (2022)", "The Astrophysical Journal Letters, Volume 924
# (2022), Number 1, L3", "A&A 660, A114 (2022)"), not remembered canonical names.
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

# [WGL] Breadth: lensing/cluster terms + the main astro-ph subfields.
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

# [WGL] Target-author references: the advisor (Ian Dell'Antonio) plus widely
# cited weak-lensing / cluster-lensing authors. These records broaden the
# positive curated-field class; they do not turn the task into authorship proof.
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

# [WGL] Weak-lensing-only sweep (--query-set wl), for a reference matched to
# THIS suite's subfield rather than to astro-ph at large. Used with --journals
# to keep only the refereed top-tier record; the breadth set stays the default.
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
    """arXiv answered 429 through every backoff. Unlike a hiccup, which is skipped,
    every later request will fail too, so the sweep must stop and SAY it stopped."""


# Escalating waits, in seconds, after a 429. Exhausting them raises Throttled.
BACKOFF_SCHEDULE = (60, 120, 240)


def urlopen_backoff(request: urllib.request.Request, timeout: int) -> bytes:
    """Single retry-on-429 path shared by both modes. Only the full-text mode
    had it before, so a throttled abstract sweep silently produced a truncated
    corpus that looked exactly like a complete one."""
    for attempt, wait in enumerate((*BACKOFF_SCHEDULE, None)):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code != 429 or wait is None:
                if error.code == 429:
                    raise Throttled(f"429 after {attempt} backoffs totalling "
                                    f"{sum(BACKOFF_SCHEDULE)} s") from error
                raise
            print(f"[fetch] HTTP 429; backing off {wait} s (attempt {attempt + 1}/"
                  f"{len(BACKOFF_SCHEDULE)})", file=sys.stderr, flush=True)
            time.sleep(wait)
    raise Throttled("unreachable")  # the None sentinel always raises above


def fetch_page(query: str, start: int, n: int, date_lo: str, date_hi: str) -> list[dict]:
    q = f"({query}) AND submittedDate:[{date_lo} TO {date_hi}]"
    params = urllib.parse.urlencode({
        "search_query": q, "start": start, "max_results": n,
        "sortBy": "submittedDate", "sortOrder": "descending"})
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
        # `published` dates v1; `summary` is the LATEST version's abstract, so `updated`
        # dates the text. On a live 2010-2021 weak-lensing page, 11 of 12 entries had
        # updated > published and two landed after 2022-11, i.e. after a public LLM existed.
        updated = e.findtext(f"{ATOM}updated") or ""
        # journal_ref and doi live in the arXiv namespace, not Atom's; only ~37% of
        # entries carry one (measured on a live WL query), so journal runs over-fetch.
        journal_ref = e.findtext(f"{ARXIV}journal_ref")
        if journal_ref:
            journal_ref = " ".join(journal_ref.split())
        # Team size for --max-authors. Only the API carries a clean list:
        # counting `\author` in the LaTeX picks up template placeholders, and a
        # live AASTeX source here has one ("\author[xxxx-xxxx-xxxx-xxxx]{Author Name}").
        authors = [(person.findtext(f"{ATOM}name") or "").strip()
                   for person in e.findall(f"{ATOM}author")]
        if text and len(text.split()) >= 40:
            out.append({"section": "abstract", "text": text, "source": f"arxiv:{arid}",
                        "year": year, "published": pub[:10], "updated": updated[:10],
                        "journal_ref": journal_ref, "journal": classify_journal(journal_ref),
                        "authors": [name for name in authors if name],
                        "doi": e.findtext(f"{ARXIV}doi")})
    return out


# [WGL] Full-text mode: subfield queries give the closest genre match for the
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
_SECTION_RE = re.compile(r"\\section\*?\s*\{")  # `\section {` is legal; 0707.0484 spaces 7 of 8


def _eprint_bytes(arxiv_id: str) -> bytes:
    req = urllib.request.Request(
        EPRINT + urllib.parse.quote(arxiv_id),
        headers={"User-Agent": "sci-paper-voice/0.14 (corpus builder)"})
    return urlopen_backoff(req, timeout=120)


def _tex_members(raw: bytes) -> dict[str, str] | None:
    """Extract .tex files from an e-print payload; None if no LaTeX source.

    e-prints arrive as gzipped tarballs, gzipped single .tex files, or bare PDFs
    (no source). Tar extraction is member-filtered in memory, so no archive paths
    ever touch the filesystem. A single file is a source when `RE_TEX_DOC_MARKER`
    matches ANYWHERE: pre-1995 sources say `\\documentstyle`, and many open with
    a comment line rather than the marker.
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
                    if name in out:  # sections/intro.tex vs appendix/intro.tex: keep both
                        name = "__".join(Path(member.name).parts)
                    out[name] = handle.read().decode("utf-8", "replace")
                return out or None
        except tarfile.ReadError:
            try:
                text = gzip.decompress(raw).decode("utf-8", "replace")
            except OSError:
                return None
            return {"main.tex": text} if RE_TEX_DOC_MARKER.search(text) else None
    text = raw.decode("utf-8", "replace")
    return {"main.tex": text} if RE_TEX_DOC_MARKER.search(text) else None


# [WGL] Keyword filter of the local full-text shortcut; --query bypasses it.
_FIELD_RELEVANCE_RE = re.compile(
    r"(?i)\b(lensing|shear|convergence|aperture mass|mass map|cluster)\b")

RE_ARXIV_ID = re.compile(r"(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?_?\d{7})")


def _bare(arxiv_id: str) -> str:
    """An arXiv id without its version suffix, for identity comparisons."""
    return re.sub(r"v\d+$", "", arxiv_id.strip()).replace("/", "_")


def known_calibration_ids(args) -> set[str]:
    """Every arXiv id whose text already feeds a calibration bank.

    A held-out measurement is only held out if the paper contributed nothing to what
    the axes were calibrated on. `register_lexicon.json` and `salience_baseline.json`
    are both built from `exemplar_paragraphs.jsonl` (the weighted tiers plus the
    unweighted `fulltext-arxiv/` breadth pull) and `human_abstracts_extra.jsonl`, so
    an id reachable from any of those three places is disqualified. This matters at
    the observed scale, not only in principle: `deai_register.RARE_DF_RATE` = 1e-4 on
    41,559 passages puts the foreign-term threshold at four passages, so one paper's
    own contribution is enough to suppress its own flags.
    """
    known: set[str] = set()
    bank = args.profile_root / args.field / BANK
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
                   journals: set[str] | None = None) -> tuple[list[str], bool]:
    """Candidate arXiv IDs for full-text download, plus whether arXiv throttled the
    search (the caller then reports TRUNCATED and exits 2, never DONE).

    Prefer the already-fetched local abstract corpus (no query-API traffic, which is
    rate-limited after a bulk abstract run), filtered by the [WGL] abstract keywords
    and by `journals` -- the key set that makes the result *refereed* rather than
    merely on-arXiv. Both paths carry `journal`; the local copy can only be stale in
    the safe direction (a paper published since the sweep is dropped and counted,
    never wrongly kept). Five things force the live path: `exclude` (bare ids) is
    built from the very bank the shortcut reads, so all it could offer is already
    disqualified; `--author` names WHO and the shortcut only answers WHAT-about;
    `--query` is the caller's own term set, which the [WGL] keyword filter cannot
    stand in for; `--updated-before` dates the text that will be DOWNLOADED, and only
    the live `updated` sees a revision made since the sweep; `--author-is` and
    `--max-authors` need the API's author list, which the bank does not keep. Ids
    are deduplicated on their bare form, one entry per paper.
    """
    exclude = exclude or set()
    # A bare name is quoted; a value already carrying a query operator passes
    # through, because `au:` alone is not field-scoped and often must be: 32 of
    # 100 `au:"Kaiser, N"` papers are nuclear theory, under the same spelling.
    author = args.author if ":" in args.author else f'au:"{args.author}"'
    queries = [author] if args.author else (args.query or FULLTEXT_QUERIES)
    max_authors = getattr(args, "max_authors", 0) or 0
    identity = (re.compile(getattr(args, "author_is", "") or "", re.IGNORECASE)
                if getattr(args, "author_is", "") else None)
    jsonl = args.profile_root / args.field / BANK
    candidates: list[str] = []
    seen: set[str] = set()
    dropped_known = dropped_journal = dropped_team = dropped_revised = 0
    dropped_unknown_team = dropped_identity = 0
    if jsonl.exists() and not (exclude or args.author or args.query
                               or args.updated_before or max_authors or identity):
        with jsonl.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if not _FIELD_RELEVANCE_RE.search(record.get("text", "")):
                    continue
                if journals and record.get("journal") not in journals:
                    dropped_journal += 1
                    continue
                arxiv_id = str(record.get("source", "")).removeprefix("arxiv:")
                if arxiv_id and _bare(arxiv_id) not in seen:
                    seen.add(_bare(arxiv_id))
                    candidates.append(arxiv_id)
        print(f"[fulltext] {len(candidates)} field-relevant candidates from local "
              f"{jsonl.name} ({dropped_journal} off-journal dropped)", file=sys.stderr)
        return candidates, False
    throttled = False
    for query in queries:
        for start in range(args.start_at, args.start_at + args.per_query,
                           args.page):
            try:
                # Sized from where the band BEGAN: --start-at never asks for max_results < 0.
                page = fetch_page(query, start,
                                  min(args.page, args.start_at + args.per_query - start),
                                  args.date_lo, args.date_hi)
            except Throttled as error:
                print(f"[fulltext] THROTTLED building candidates: {error}; proceeding "
                      f"with {len(candidates)} found so far", file=sys.stderr)
                throttled = True
                break
            except Exception as error:  # network/API hiccup: report, keep going
                print(f"[fulltext] {query!r} start={start} error: {error}", file=sys.stderr)
                page = []
            for record in page:
                arxiv_id = record["source"].removeprefix("arxiv:")
                bare = _bare(arxiv_id)
                if not arxiv_id or bare in seen:
                    continue
                seen.add(bare)
                if bare in exclude:
                    dropped_known += 1
                    continue
                if journals and record.get("journal") not in journals:
                    dropped_journal += 1
                    continue
                # No `updated` cannot be shown to predate the cutoff; drop, do not assume clean.
                if args.updated_before and not (
                        record.get("updated") and record["updated"] < args.updated_before):
                    dropped_revised += 1
                    continue
                team = record.get("authors") or []
                # `au:` matches a SURNAME, and a surname is not a person, so the
                # identity test is separate from the search term rather than
                # folded into it.
                if identity and not any(identity.search(name) for name in team):
                    dropped_identity += 1
                    continue
                if max_authors:
                    # An unlisted team cannot be SHOWN to be within the limit, so
                    # it is dropped and counted rather than assumed small -- the
                    # reading --updated-before applies to a record with no date.
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
        if throttled:
            break
    print(f"[fulltext] {len(candidates)} candidate papers from {len(queries)} live "
          f"queries (dropped {dropped_known} already-calibrated, {dropped_journal} "
          f"off-journal, {dropped_revised} revised on/after --updated-before, "
          f"{dropped_identity} not the named author, {dropped_team} over "
          f"{max_authors or '-'} authors, {dropped_unknown_team} with no author list)",
          file=sys.stderr)
    return candidates, throttled


def fetch_fulltext(args) -> int:
    out_root = (REPO_ROOT / "style-corpus" / args.field / args.fulltext_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    exclude = known_calibration_ids(args) if args.exclude_known else set()
    journals = {k.strip().lower() for k in args.journals.split(",") if k.strip()}
    if exclude:
        print(f"[fulltext] holding out: {len(exclude)} arXiv ids already feed a "
              f"calibration bank", file=sys.stderr)
    candidates, throttled = _candidate_ids(args, exclude, journals)

    kept = skipped = failed = 0
    for arxiv_id in candidates:
        if kept >= args.max_papers:
            break
        # One directory per BARE id, so a paper that gained a version between runs
        # is not fetched beside its old copy (pre-2026-09 runs named it with the version).
        safe = _bare(arxiv_id)
        paper_dir = out_root / safe
        if any(paper_dir.glob("*.tex")) or any(
                any(old.glob("*.tex")) for old in out_root.glob(f"{safe}v[0-9]*")):
            kept += 1  # resumable: already fetched and validated
            continue
        try:
            raw = _eprint_bytes(arxiv_id)
        except Throttled as error:
            # Backoff is exhausted inside urlopen_backoff; today's budget is
            # spent. The per-paper directories make a later run resume here.
            print(f"[fulltext] {error}; stopping with kept={kept}", file=sys.stderr)
            throttled = True
            break
        except Exception as error:  # per-paper failure must not kill the sweep
            code = getattr(error, "code", None)  # an HTTPError names its status
            what = f"HTTP {code}" if code else f"download error: {error}"
            print(f"[fulltext] {arxiv_id}: {what}", file=sys.stderr)
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
            (paper_dir / Path(name).name).write_text(members[name], encoding="utf-8")
        kept += 1
        if kept % 25 == 0:
            print(f"[fulltext] kept={kept} skipped={skipped} failed={failed}",
                  file=sys.stderr, flush=True)
    print(f"[fulltext] {'TRUNCATED' if throttled else 'DONE'} kept={kept} "
          f"skipped={skipped} failed={failed} -> {out_root}")
    if throttled:  # exit 2, as the abstract sweep does: a run cut short is not exhaustive
        print("[fulltext] TRUNCATED — arXiv throttled the run; rerun later to resume, "
              "papers already kept are valid.", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    p = cli_common.field_parser(__doc__)
    p.add_argument("--per-query", type=int, default=400)
    p.add_argument("--page", type=int, default=100)
    p.add_argument("--date-lo", default="201001010000")
    p.add_argument("--date-hi", default="202112312359")
    p.add_argument("--sleep", type=float, default=3.0)
    p.add_argument("--query", action="append", default=[], metavar="TERM",
                   help="an arXiv search_query term, repeatable. Replaces the [WGL] "
                        "built-in query sets in both modes and, in full-text mode, "
                        "the [WGL] keyword shortcut over the local abstract bank: a "
                        "field other than weak lensing must pass its own terms. Over "
                        "an existing default bank, pass --resume or --out-name.")
    p.add_argument("--fulltext", action="store_true",
                   help="download complete LaTeX paper sources (one directory "
                        "per paper) instead of abstracts")
    p.add_argument("--max-papers", type=int, default=300,
                   help="full-text mode: stop after this many kept papers")
    p.add_argument("--fulltext-dir", default=REFERENCE_DIR,
                   help="full-text mode: directory name under style-corpus/<field>/ "
                        f"(default {REFERENCE_DIR!r}, which extract_style.py reads as "
                        "breadth calibration). Any other fulltext-* name is held out of "
                        "calibration by construction and is what an evaluation set needs.")
    p.add_argument("--start-at", type=int, default=0,
                   help="full-text mode: first result offset per query. Results "
                        "are newest-first, so an existing corpus is a contiguous "
                        "shallow band: on 'cat:astro-ph.CO AND abs:cluster', "
                        "offsets 0-2000 were 100%% already-calibrated and 2000+ "
                        "~85%% new; skipping the band makes a held-out sweep "
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
                   help="full-text mode: drop every candidate whose text already feeds "
                        "a calibration bank (the abstract corpus, fulltext-*/ pulls, or "
                        "a tier filename's arXiv id): a genuine held-out set")
    p.add_argument("--query-set", choices=sorted(QUERY_SETS), default="broad",
                   help="[WGL] built-in set: 'broad' = astro-ph breadth + authoritative "
                        "authors (default); 'wl' = weak-lensing subfield only")
    p.add_argument("--journals", default="",
                   help="[WGL] comma-separated journal keys to keep "
                        f"({', '.join(k for k, _, _ in JOURNAL_FILTERS)}); "
                        "empty keeps every record, refereed or not")
    p.add_argument("--out-name", default=BANK,
                   help="output filename under the field profile directory. A "
                        "journal-restricted, subfield or --query run MUST pass a "
                        "different name (--query may --resume instead): the writer "
                        "truncates its target, so the default would lose the broad corpus.")
    p.add_argument("--updated-before", default="",
                   help="YYYY-MM-DD; drop records whose LATEST arXiv version "
                        "is dated on or after this. --date-hi bounds the v1 "
                        "submission, which does not date the returned text; "
                        "only this bounds the text itself, in either mode.")
    p.add_argument("--resume", action="store_true",
                   help="seed from the existing --out-name file and keep its records, so "
                        "a run cut short by rate limiting is extended rather than replaced")
    args = p.parse_args(argv)
    try:
        # A named field is taken as given: this tool is what first populates
        # style-profile/<field>/, so requiring the directory would refuse a new
        # field. An OMITTED one is resolved: a message and exit 2, not a TypeError.
        args.field = args.field or cli_common.resolve_field(
            None, args.profile_root, tool="fetch_arxiv_abstracts",
            empty_hint="pass --field <name>")
    except SystemExit as error:
        print(error, file=sys.stderr)
        return 2
    if args.sleep < 3.0:
        p.error("--sleep must be >= 3 seconds (arXiv rate guidance)")
    if args.updated_before and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.updated_before):
        p.error("--updated-before must be YYYY-MM-DD")
    # Validated for BOTH modes: full-text mode used to skip this block entirely,
    # so `--fulltext --journals apjjl` silently kept nothing rather than failing.
    wanted = {k.strip().lower() for k in args.journals.split(",") if k.strip()}
    known = {key for key, _, _ in JOURNAL_FILTERS}
    if wanted - known:
        p.error(f"unknown journal key(s): {sorted(wanted - known)}; known: {sorted(known)}")
    # A flag the chosen mode accepts but would never read is refused, not ignored.
    if args.query and (args.query_set != "broad" or args.author):
        p.error("--query replaces the built-in query set; drop --query-set/--author")
    if (args.author or args.max_authors or args.author_is) and not args.fulltext:
        p.error("--author/--author-is/--max-authors select whole papers, which "
                "only --fulltext downloads; the abstract sweep has --query-set")
    if args.fulltext and (args.query_set != "broad" or args.resume or args.out_name != BANK):
        p.error("--query-set/--out-name/--resume shape the abstract sweep, which "
                "--fulltext does not run; full-text mode resumes by itself")
    if args.fulltext:
        if "/" in args.fulltext_dir or "\\" in args.fulltext_dir:
            p.error("--fulltext-dir must be a bare directory name")
        if args.author and args.fulltext_dir == REFERENCE_DIR:
            p.error(f"--author writes a population you intend to MEASURE, but "
                    f"--fulltext-dir {REFERENCE_DIR!r} is what extract_style.py reads "
                    f"as calibration breadth. A paper in a calibration bank has its "
                    f"own vocabulary in the denominator: ~94% of register findings on "
                    f"an in-sample paper are suppressed by that membership (EVALUATION "
                    f"section 17.3), so the axis would go quiet on exactly the prose "
                    f"you fetched it to judge. Choose another fulltext-* name.")
        if args.exclude_known and args.fulltext_dir == REFERENCE_DIR:
            p.error(f"--exclude-known writes a held-out set, but "
                    f"--fulltext-dir {REFERENCE_DIR!r} is the directory "
                    f"extract_style.py reads as calibration breadth; the next "
                    f"rebuild would absorb the held-out papers and the set "
                    f"would stop being held out. Choose another fulltext-* name.")
        return fetch_fulltext(args)

    field_dir = args.profile_root / args.field
    if args.out_name == BANK and (wanted or args.query_set != "broad" or (
            args.query and (field_dir / BANK).exists() and not args.resume)):
        p.error("a journal-restricted, subfield or --query run needs --out-name "
                "(--query may --resume instead): writing to the default bank would "
                "truncate the broad corpus the calibration baselines are built from")
    field_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()  # bare ids, so a revised paper is not banked twice
    recs: list[dict] = []
    dropped_no_ref = dropped_other = dropped_revised = 0
    if args.resume:
        # Rate limiting makes a full sweep a multi-run affair, and the writer
        # truncates its target: without this a rerun would shrink the corpus.
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
                    if _bare(record["source"]) not in seen:
                        seen.add(_bare(record["source"]))
                        recs.append(record)
            print(f"[fetch] resume: {len(recs)} records carried over from "
                  f"{existing.name}", file=sys.stderr)
    queries = args.query or QUERY_SETS[args.query_set]
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
                # Not a hiccup: every later request would fail too. Stop, so the
                # truncation is reported rather than written out as complete.
                print(f"[fetch] THROTTLED on {query!r} start={start}: {e}", file=sys.stderr)
                throttled_at = f"query {index + 1}/{len(queries)} {query!r} start={start}"
                break
            except Exception as e:
                # A failed page and an exhausted query both used to arrive here
                # as `page = []`, which `if not page: break` cannot tell apart,
                # so one hiccup silently ended that query and the run still
                # exited 0 with a short corpus. Record IT as incomplete instead.
                print(f"[fetch] {query!r} start={start} error: {e}", file=sys.stderr)
                incomplete_queries.append(f"{query!r} start={start}: {e}")
                break
            new = 0
            for r in page:
                if _bare(r["source"]) in seen:
                    continue
                seen.add(_bare(r["source"]))
                # ISO dates compare as strings; a record with no `updated` cannot be
                # shown to predate the cutoff, so it is dropped, not assumed clean.
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
                # The abstract bank is a PROSE corpus (`voice_dataset`, the register
                # lexicon and the reference banks all read it as text); author names
                # are not prose, so the list stays in the full-text path that needs it.
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
        by_journal = sorted(Counter(r["journal"] for r in recs).items())
        print(f"[fetch] journal filter {sorted(wanted)}: kept {by_journal}; dropped "
              f"{dropped_no_ref} with no journal_ref, {dropped_other} in other journals")
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
        # them and exiting 2 is how the caller tells this run from an exhaustive one.
        print(f"[fetch] INCOMPLETE — {len(incomplete_queries)} of {len(queries)} queries "
              f"stopped early on a page error:", file=sys.stderr)
        for entry in incomplete_queries:
            print(f"[fetch]   {entry}", file=sys.stderr)
        print("[fetch] Rerun with --resume to extend; records already written "
              "are valid.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
