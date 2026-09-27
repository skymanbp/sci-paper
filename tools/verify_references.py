"""Verify a BibTeX bibliography against the records its identifiers resolve to.

Every entry that carries a DOI (in its `doi` field or as a doi.org `url`) is
resolved through CrossRef (DataCite as the fallback for the DOI prefixes
CrossRef does not register) and its author, year, title, journal, volume and
first page are compared with the fetched record; an entry with only an arXiv
identifier is resolved through the arXiv API. The comparison is the
mechanical half of paper-review dimension F (citation existence): a DOI that
resolves nowhere is an `integrity_blocker` and a first author, year or title
that disagrees with the record is a strong advisory, both under
`sci-paper.feedback.v1`. Journal, volume and page disagreements are ordinary
advisories, since abbreviations and article numbers vary by house style. An
entry the network could not answer for, or answered in a shape the record
readers do not expect, is reported as unmeasured, never as clean, and the
axis is `degraded`.

With `--tex`, the assembled document's citation keys are cross-checked: a key
with no bibliography entry is a blocker, an entry no sentence cites is an
ordinary advisory. The citing commands of LaTeX, natbib and biblatex are
recognised (`\\cite`, `\\citep`, `\\parencite`, `\\cites{a}{b}`, ...), a
`\\nocite{*}` cites every entry, and a citation inside a `%` comment is text.
Exit status follows the linter's narrow contract: 0 means no blocker, 1 means
a blocker is present, 2 means invalid input or execution failure. `--cache`
keeps fetched records in a JSON file so a repeated review round does not
re-query the registries; a registry miss is never cached, so an identifier
the registries are late to index is asked again next round, and a finding
built from a cached record says so (`observed.cached`). A 429 or 5xx answer
is asked once more; `SCI_PAPER_MAILTO` names a contact in the User-Agent.
"""

from __future__ import annotations

import argparse
import difflib
import html
import http.client
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_feedback as feedback  # noqa: E402  shared finding contract
import tex_assembly  # noqa: E402  the assembled document and comment pattern for --tex

USER_AGENT = "sci-paper-verify-references/1.0"
MAILTO_ENV = "SCI_PAPER_MAILTO"  # contact address for CrossRef's polite pool
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
RETRY_WAIT_DEFAULT = 2.0  # seconds, when the registry names no Retry-After
RETRY_WAIT_CAP = 30.0     # seconds; a longer Retry-After is waited out only this long
CROSSREF = "https://api.crossref.org/works/"
DATACITE = "https://api.datacite.org/dois/"
ARXIV = "https://export.arxiv.org/api/query?id_list="
ATOM = "{http://www.w3.org/2005/Atom}"
TITLE_MATCH_RATIO = 0.85
# Print and online publication years of one article differ by one for a
# large share of journal papers; that seam is reported, not escalated.
YEAR_SEAM = 1

# Anchored at line start: an `@article{` inside a `%` comment line is text.
RE_ENTRY_HEAD = re.compile(r"^[ \t]*@(\w+)\s*([{(])\s*([^,\s]+)\s*,",
                           re.IGNORECASE | re.MULTILINE)
RE_STRING_HEAD = re.compile(r"^[ \t]*@string\s*([{(])", re.IGNORECASE | re.MULTILINE)
# A field name is any run BibTeX allows (BibDesk writes `Bdsk-Url-1`), a bare
# value a number or a `@string` name; whitespace and commas between fields
# are skipped, `#` joins the pieces of one value, and a value must be
# followed by a comma or the end of the entry.
RE_FIELD_SKIP = re.compile(r"[\s,]*")
RE_FIELD_HEAD = re.compile(r"""([^\s"#%'(),={}]+)\s*=\s*""")
RE_BARE_VALUE = re.compile(r"""[^\s,#{}"]+""")
RE_CONCAT = re.compile(r"\s*#\s*")
RE_FIELD_END = re.compile(r"\s*(?=,|\Z)")
# The citing commands of LaTeX, natbib and biblatex: an optional biblatex
# prefix, `cite`, a suffix (`p`, `t`, `alt`, `author`; `s` marks the
# multicite forms), an optional star, up to two [pre][post] notes, then the
# key group. Case-insensitive for the sentence-initial `\Citep`, `\Textcite`.
RE_CITE = re.compile(
    r"\\(?P<prefix>no|paren|text|auto|smart|foot|super|full|footfull)?"
    r"cite(?P<suffix>[a-z]*)\*?(?:\s*\[[^\]]*\]){0,2}\s*\{(?P<keys>[^}]*)\}",
    re.IGNORECASE)
# A multicite command (`\cites{a}{b}`, `\parencites[p]{a}[q]{b}`) carries
# one key group per citation; the tail is consumed group by group.
RE_CITE_GROUP = re.compile(r"\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}")
MULTICITE_SUFFIXES = ("s", "texts")
RE_AUTHOR_SEP = re.compile(r"\s+and\s+", re.IGNORECASE)
RE_ACCENT = re.compile(r"\\[`'^\"~=.uvHtcdbk]\s*\{?\\?([A-Za-z])\}?")
RE_LATEX_CMD = re.compile(r"\\[A-Za-z]+")
RE_ARXIV_ID = re.compile(r"(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?")
RE_DOI_URL = re.compile(r"^(?:https?://)?(?:dx\.)?doi\.org/", re.IGNORECASE)
RE_PAGE_SEP = re.compile(r"\s*-{1,3}\s*|\s*[\u2013\u2014]\s*")


# ---------------------------------------------------------------------------
# BibTeX reading
# ---------------------------------------------------------------------------

def _group_end(text: str, start: int, close: str) -> int:
    """Index just past the group opening at `start`, braces nested inside."""
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        if depth == 0 and char == close:
            return index + 1
    raise ValueError(f"unbalanced entry from offset {start}")


def _quoted_end(body: str, start: int) -> int:
    """Index just past the `"` closing the quoted value opening at `start`.

    Braces nest inside a quoted value, and a `"` inside them or escaped as
    `\\"` does not close it: `"M{\\"u}ller"` and `"a \\"quoted\\" word"` are
    one value each. Stopping at the first `"` cut such a value short and
    silently dropped every field after it, DOI included.
    """
    depth = 0
    for index in range(start + 1, len(body)):
        char = body[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char == '"' and depth == 0 and body[index - 1] != "\\":
            return index + 1
    raise ValueError(f"unterminated quoted value from offset {start}")


def _value_piece(body: str, position: int, strings: dict[str, str]) -> tuple[str, int]:
    """(text, end) of one value piece: a braced or quoted group, a number,
    or a macro name expanded from the `@string` definitions read so far (an
    undefined name stays as written, so the comparison shows it)."""
    if position < len(body) and body[position] == "{":
        end = _group_end(body, position, "}")
        return body[position + 1:end - 1], end
    if position < len(body) and body[position] == '"':
        end = _quoted_end(body, position)
        return body[position + 1:end - 1], end
    bare = RE_BARE_VALUE.match(body, position)
    if not bare:
        raise ValueError(f"missing field value at offset {position}")
    return strings.get(bare.group().lower(), bare.group()), bare.end()


def _parse_fields(body: str, strings: dict[str, str] | None = None) -> dict[str, str]:
    """`name = value` pairs of an entry body, whitespace collapsed.

    A value is one or more pieces joined with `#`; each piece is a braced or
    quoted group, a number, or a `@string` name. Text the grammar cannot
    place raises ValueError: BibTeX itself skips the rest of such an entry,
    and dropping the fields silently once turned a DOI-bearing entry into a
    "no identifier" advisory.
    """
    strings = strings if strings is not None else {}
    fields: dict[str, str] = {}
    position = RE_FIELD_SKIP.match(body).end()
    while position < len(body):
        head = RE_FIELD_HEAD.match(body, position)
        if not head:
            raise ValueError(f"unreadable field at offset {position}: "
                             f"{body[position:position + 40].strip()!r}")
        name, position = head.group(1).lower(), head.end()
        pieces = []
        while True:
            piece, position = _value_piece(body, position, strings)
            pieces.append(piece)
            concat = RE_CONCAT.match(body, position)
            if not concat:
                break
            position = concat.end()
        fields[name] = " ".join("".join(pieces).split())
        end = RE_FIELD_END.match(body, position)
        if not end:
            raise ValueError(f"expected ',' or the end of the entry at offset {position}: "
                             f"{body[position:position + 40].strip()!r}")
        position = RE_FIELD_SKIP.match(body, end.end()).end()
    return fields


def parse_strings(text: str) -> dict[str, str]:
    """`@string{name = value}` definitions, names lowercased, in file order;
    a definition may use the ones before it (`apjl = apj # " Letters"`)."""
    strings: dict[str, str] = {}
    for head in RE_STRING_HEAD.finditer(text):
        close = "}" if head.group(1) == "{" else ")"
        end = _group_end(text, head.start(1), close)
        strings.update(_parse_fields(text[head.end():end - 1], strings))
    return strings


def parse_bib(text: str) -> list[dict[str, Any]]:
    """Every `@type{key, field = value, ...}` entry, `@string` names expanded
    in its values; `@comment` and `@preamble` blocks are skipped."""
    strings = parse_strings(text)
    entries = []
    for head in RE_ENTRY_HEAD.finditer(text):
        kind = head.group(1).lower()
        if kind in ("comment", "string", "preamble"):
            continue
        close = "}" if head.group(2) == "{" else ")"
        end = _group_end(text, head.start(2), close)
        key, line = head.group(3), text[:head.start()].count("\n") + 1
        try:
            fields = _parse_fields(text[head.end():end - 1], strings)
        except ValueError as error:
            raise ValueError(f"entry {key!r} (line {line}): {error}") from error
        entries.append({"key": key, "type": kind, "line": line, "fields": fields})
    return entries


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _fold(text: str | None) -> str:
    """Lowercase text with LaTeX accents, commands, braces and combining
    marks removed; separators are kept so a name still splits into parts."""
    if not text:
        return ""
    # CrossRef serves `&amp;` where a bibliography writes `\&`; both are "&".
    text = RE_ACCENT.sub(r"\1", html.unescape(str(text)))
    text = RE_LATEX_CMD.sub(" ", text).replace("{", "").replace("}", "")
    text = unicodedata.normalize("NFKD", text)
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def normalize(text: str | None) -> str:
    """Lowercase alphanumerics only, LaTeX accents and braces removed."""
    return re.sub(r"[^a-z0-9]+", "", _fold(text))


def _name_tokens(text: str | None) -> set[str]:
    """The parts of a family name at least four letters long: particles
    (`van`, `de`) are shared by unrelated names and count for nothing."""
    return {token for token in re.split(r"[^a-z0-9]+", _fold(text)) if len(token) >= 4}


def same_family(entry: str | None, record: str | None) -> bool:
    """Whether two family names agree: equal once normalized, or sharing a
    part of four or more letters (`van Waerbeke` / `Waerbeke`, `Smith-Jones`
    / `Smith`). A bare substring test let `Li` pass for `Lin` and `Ma` for
    `Mandelbaum`, so a wrong first author on a short name went unreported.
    """
    return (normalize(entry) == normalize(record)
            or bool(_name_tokens(entry) & _name_tokens(record)))


def first_author(authors: str) -> str:
    """The first name of a BibTeX author list, split on ` and ` in any case."""
    return RE_AUTHOR_SEP.split(authors)[0].strip()


def family_name(author: str) -> str:
    """The family part as written: before the comma of `Family, Given`,
    else the last word of `Given Family`."""
    if "," in author:
        return author.split(",")[0].strip()
    tokens = author.split()
    return tokens[-1] if tokens else ""


def first_author_family(authors: str) -> str:
    return normalize(family_name(first_author(authors)))


def _journal_name(name: str | None) -> str:
    """Normalized journal name without a leading article ("The Annals of ...")."""
    normalized = normalize(name)
    return normalized[3:] if normalized.startswith("the") else normalized


def first_page(pages: str | None) -> str:
    return normalize(RE_PAGE_SEP.split(pages.strip())[0]) if pages else ""


def arxiv_id(fields: dict[str, str]) -> str | None:
    for name in ("eprint", "arxivid", "url", "note", "journal"):
        value = fields.get(name, "")
        match = RE_ARXIV_ID.search(value)
        if match and (name in ("eprint", "arxivid") or "arxiv" in value.lower()):
            return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Registry lookups
# ---------------------------------------------------------------------------

class RegistryUnavailable(RuntimeError):
    """A registry could not be reached, answered outside 200/404, or served
    a body the record readers cannot use; the entry stays unmeasured."""


def _retry_wait(error: urllib.error.HTTPError) -> float | None:
    """Seconds before the one retry a transient answer earns, or None.

    A 429 or a 5xx says nothing about the identifier, and without a retry one
    rate-limit blip left an entry unmeasured and the axis `degraded`. The
    registry's Retry-After is honoured up to RETRY_WAIT_CAP seconds.
    """
    if error.code not in RETRY_STATUSES:
        return None
    header = error.headers.get("Retry-After") if error.headers else None
    try:
        wait = float(header) if header else RETRY_WAIT_DEFAULT
    except ValueError:  # because an HTTP-date Retry-After is legal; wait the default
        wait = RETRY_WAIT_DEFAULT
    return min(max(wait, 0.0), RETRY_WAIT_CAP)


def fetch(url: str, timeout: int = 30) -> tuple[int, bytes]:
    """(HTTP status, body). 404 is an answer, not an error; the rest raise,
    a 429 or 5xx after one retry (`_retry_wait`). A contact address in
    SCI_PAPER_MAILTO rides in the User-Agent, which CrossRef routes to its
    polite pool."""
    mailto = os.environ.get(MAILTO_ENV, "").strip()
    agent = f"{USER_AGENT} (mailto:{mailto})" if mailto else USER_AGENT
    request = urllib.request.Request(url, headers={"User-Agent": agent,
                                                   "Accept": "application/json"})
    retried = False
    while True:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return 404, b""
            wait = None if retried else _retry_wait(error)
            if wait is None:
                raise RegistryUnavailable(
                    f"HTTP {error.code} from {url.split('?')[0]}") from error
            retried = True
            time.sleep(wait)  # because the registry asked for the pause, or a 5xx is transient
        except (http.client.HTTPException, OSError) as error:
            # URLError and TimeoutError are OSError subclasses; IncompleteRead,
            # BadStatusLine and RemoteDisconnected are HTTPException and are not.
            raise RegistryUnavailable(f"{error} ({url.split('?')[0]})") from error


def _first(value: Any, default: Any = "") -> Any:
    """The first element of a list-valued registry field, the value itself
    when the registry served a scalar, `default` when it served nothing.
    CrossRef's `issued.date-parts` arrives as `[[]]` or `[[null]]` for an
    undated work, and indexing it blindly was an IndexError traceback."""
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


def _answer(body: bytes, *keys: str) -> dict[str, Any]:
    """The object at `keys` in a JSON registry answer. Any other shape -- a
    body that is not JSON, a missing key, a record that is not an object --
    is an answer outside the contract and leaves the entry unmeasured."""
    try:
        value: Any = json.loads(body.decode("utf-8"))
        for key in keys:
            value = value[key]
    except (ValueError, LookupError, TypeError) as error:
        raise RegistryUnavailable(
            f"unreadable registry answer: {type(error).__name__}: {error}") from error
    if not isinstance(value, dict):
        raise RegistryUnavailable("unreadable registry answer: the record is not an object")
    return value


def _crossref_record(message: dict[str, Any]) -> dict[str, Any]:
    author = _first(message.get("author"), {})
    author = author if isinstance(author, dict) else {}
    issued = message.get("issued")
    date_parts = issued.get("date-parts") if isinstance(issued, dict) else None
    subtitle = message.get("subtitle") or []
    return {
        "source": "crossref",
        "first_author": author.get("family") or author.get("name") or "",
        "year": _first(_first(date_parts, []), None),
        # CrossRef splits "GaBoDS: the Garching-Bonn Deep Survey. IX. A sample
        # of ..." into title and subtitle; a bibliography carries both as one.
        "title": " ".join(str(part) for part in [_first(message.get("title"))]
                          + (subtitle if isinstance(subtitle, list) else [subtitle])),
        "journal": str(_first(message.get("container-title"))),
        "journal_short": str(_first(message.get("short-container-title"))),
        "volume": message.get("volume") or "",
        "page": message.get("page") or message.get("article-number") or "",
    }


def _datacite_record(attributes: dict[str, Any]) -> dict[str, Any]:
    creator = _first(attributes.get("creators"), {})
    creator = creator if isinstance(creator, dict) else {}
    title = _first(attributes.get("titles"), {})
    container = attributes.get("container")
    container = container if isinstance(container, dict) else {}
    return {
        "source": "datacite",
        "first_author": (creator.get("familyName")
                         or str(creator.get("name") or "").split(",")[0]),
        "year": attributes.get("publicationYear"),
        "title": (title.get("title") or "") if isinstance(title, dict) else str(title),
        "journal": container.get("title") or "",
        "journal_short": "",
        "volume": container.get("volume") or "",
        "page": container.get("firstPage") or "",
    }


def resolve_doi(doi: str) -> dict[str, Any] | None:
    """The record a DOI resolves to, or None when neither registry knows it."""
    status, body = fetch(CROSSREF + urllib.parse.quote(doi, safe="/"))
    if status == 200:
        return _crossref_record(_answer(body, "message"))
    status, body = fetch(DATACITE + urllib.parse.quote(doi, safe="/"))
    if status == 200:
        return _datacite_record(_answer(body, "data", "attributes"))
    return None


def resolve_arxiv(identifier: str) -> dict[str, Any] | None:
    status, body = fetch(ARXIV + urllib.parse.quote(identifier))
    if status != 200:
        return None
    try:
        entry = ET.fromstring(body.decode("utf-8", "replace")).find(f"{ATOM}entry")
    except ET.ParseError as error:
        raise RegistryUnavailable(f"unreadable arXiv answer: {error}") from error
    # An unknown identifier still returns a feed, with one entry that has no id.
    if entry is None or entry.findtext(f"{ATOM}id") is None:
        return None
    published = entry.findtext(f"{ATOM}published") or ""
    names = [author.findtext(f"{ATOM}name") or "" for author in entry.findall(f"{ATOM}author")]
    return {
        "source": "arxiv",
        "first_author": names[0].split()[-1] if names and names[0].split() else "",
        "year": int(published[:4]) if published[:4].isdigit() else None,
        "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
        "journal": "", "journal_short": "", "volume": "", "page": "",
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare(fields: dict[str, str], record: dict[str, Any]) -> list[dict[str, Any]]:
    """Each disagreement between the entry and the record.

    Returns dicts with `field`, `entry`, `record` and `strength`; an empty list
    means every comparable field agrees. A field absent on either side is not
    compared: silence is not agreement, and the caller reports what it saw.
    """
    issues: list[dict[str, Any]] = []
    author = first_author(fields.get("author", ""))
    family, record_family = family_name(author), str(record.get("first_author") or "")
    if normalize(family) and normalize(record_family) \
            and not same_family(family, record_family):
        issues.append({"field": "first_author", "entry": author,
                       "record": record.get("first_author"), "strength": "strong"})
    year, record_year = fields.get("year", ""), str(record.get("year") or "")
    if year.isdigit() and record_year.isdigit():
        gap = abs(int(year) - int(record_year))
        if gap:
            issues.append({"field": "year", "entry": year, "record": record["year"],
                           "strength": "strong" if gap > YEAR_SEAM else "ordinary"})
    title, record_title = normalize(fields.get("title")), normalize(record.get("title"))
    if title and record_title and not (title.startswith(record_title)
                                       or record_title.startswith(title)):
        ratio = difflib.SequenceMatcher(None, title, record_title).ratio()
        if ratio < TITLE_MATCH_RATIO:
            issues.append({"field": "title", "entry": fields.get("title"),
                           "record": record.get("title"), "strength": "strong",
                           "similarity": round(ratio, 3)})
    journal = _journal_name(fields.get("journal"))
    journals = {_journal_name(record.get("journal")),
                _journal_name(record.get("journal_short"))} - {""}
    if journal and journals and journal not in journals:
        issues.append({"field": "journal", "entry": fields.get("journal"),
                       "record": record.get("journal"), "strength": "ordinary"})
    volume, record_volume = normalize(fields.get("volume")), normalize(record.get("volume"))
    if volume and record_volume and volume != record_volume:
        issues.append({"field": "volume", "entry": fields.get("volume"),
                       "record": record.get("volume"), "strength": "ordinary"})
    page, record_page = first_page(fields.get("pages")), first_page(str(record.get("page") or ""))
    if page and record_page and page != record_page:
        issues.append({"field": "page", "entry": fields.get("pages"),
                       "record": record.get("page"), "strength": "ordinary"})
    return issues


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

def _finding(*, path: Path, key: str, line: int, rule: str, kind: str, strength: str,
             observed: dict[str, Any], message: str, action: str,
             status: str = "measured") -> dict[str, Any]:
    return feedback.make_finding(
        kind=kind, layer="F", rule=rule, scope="citation", path=path, line=line,
        section=key, detector="verify_references", strength=strength,
        observed={"key": key, **observed},
        reference={"provenance": "paper-review dimension F: citation existence",
                   "registries": "CrossRef, DataCite, arXiv"},
        normalized_distance=None,
        confidence={"value": 1.0 if status == "measured" else 0.0,
                    "basis": "registry record comparison"},
        measurement_status=status, message=message, action=action,
        evidence=[rule, observed],
    )


def entry_identifier(fields: dict[str, str]) -> str | None:
    """`doi:<doi>` from the `doi` field or a doi.org `url`, else `arxiv:<id>`,
    else None. A DOI that lives only in the `url` field (`https://doi.org/...`,
    as several exporters write it) is an identifier all the same."""
    for name in ("doi", "url"):
        value = fields.get(name, "").strip()
        if value and (name == "doi" or RE_DOI_URL.match(value)):
            doi = RE_DOI_URL.sub("", value)
            if doi:
                return "doi:" + (urllib.parse.unquote(doi) if name == "url" else doi)
    arxiv = arxiv_id(fields)
    return ("arxiv:" + arxiv) if arxiv else None


def verify_entry(entry: dict[str, Any], path: Path, cache: dict[str, Any],
                 pause: float) -> tuple[list[dict[str, Any]], str]:
    """(findings, state); state is verified / unresolved / unmeasured / no_identifier.

    `cache` maps identifiers to fetched records and is updated in place. A
    miss (None) is never stored: a DOI the registries are late to index
    would otherwise stay a blocker in every later round without a query.
    """
    fields, key, line = entry["fields"], entry["key"], entry["line"]
    identifier = entry_identifier(fields)
    if identifier is None:
        return [_finding(
            path=path, key=key, line=line, rule="reference-no-identifier", kind="advisory",
            strength="ordinary", status="unmeasured", observed={"fields": sorted(fields)},
            message=f"Entry {key!r} carries neither a DOI nor an arXiv identifier, "
                    "so no registry can confirm it.",
            action="Add the DOI or arXiv identifier, or verify the entry against the "
                   "publisher page by hand and record that in the review.")], "no_identifier"
    record, cached = cache.get(identifier), True
    if record is None:
        cached = False
        scheme, _, value = identifier.partition(":")
        try:
            record = resolve_doi(value) if scheme == "doi" else resolve_arxiv(value)
        except RegistryUnavailable as error:
            return [_finding(
                path=path, key=key, line=line, rule="reference-lookup-failed",
                kind="advisory", strength="ordinary", status="unmeasured",
                observed={"identifier": identifier, "error": str(error)},
                message=f"Entry {key!r}: the registry gave no usable answer ({error}).",
                action="Re-run when the network allows; the entry is unverified, "
                       "not clean.")], "unmeasured"
        if record is not None:
            cache[identifier] = record
        if pause:
            time.sleep(pause)
    if record is None:
        registries = "CrossRef, DataCite" if identifier.startswith("doi:") else "arXiv"
        return [_finding(
            path=path, key=key, line=line, rule="reference-identifier-unresolved",
            kind="integrity_blocker", strength="strong", observed={"identifier": identifier},
            message=f"Entry {key!r}: {identifier} resolves in no registry ({registries}).",
            action="Locate the work on the publisher page and correct the identifier, or "
                   "remove the citation; an unresolvable identifier supports no claim."
        )], "unresolved"
    findings = []
    for issue in compare(fields, record):
        strong = issue["strength"] == "strong"
        findings.append(_finding(
            path=path, key=key, line=line,
            rule=f"reference-metadata-mismatch:{issue['field']}", kind="advisory",
            strength=issue["strength"],
            observed={"identifier": identifier, "record_source": record["source"],
                      "cached": cached, **issue},
            message=(f"Entry {key!r}: {issue['field']} reads {issue['entry']!r} "
                     f"but the {record['source']} record says {issue['record']!r}."),
            action=("Correct the entry from the record, or confirm the identifier "
                    "points at the intended work." if strong else
                    "Confirm the house-style abbreviation or article number "
                    "matches the record."),
        ))
    return findings, "verified"


def cite_lines(text: str) -> dict[str, int]:
    """Each cited key with the first line citing it, `%` comments removed.

    A citation inside a comment is text (the pattern is the one
    `tex_assembly` strips before resolving includes), and natbib's
    `\\citetext{...}` holds prose, not keys. Lines count in the text given:
    the assembled document, whose numbering is the root file's own until the
    first spliced `\\input`. `\\nocite{*}` yields the key `*`; `cross_check`
    reads it as citing every entry.
    """
    lines: dict[str, int] = {}
    text = tex_assembly.RE_TEX_COMMENT.sub("", text)
    for match in RE_CITE.finditer(text):
        suffix = match.group("suffix").lower()
        if suffix == "text" and not match.group("prefix"):
            continue
        groups, end = [match.group("keys")], match.end()
        if suffix in MULTICITE_SUFFIXES:
            while (more := RE_CITE_GROUP.match(text, end)) is not None:
                groups.append(more.group(1))
                end = more.end()
        line = text.count("\n", 0, match.start()) + 1
        for key in (key.strip() for group in groups for key in group.split(",")):
            if key:
                lines.setdefault(key, line)
    return lines


def cite_keys(text: str) -> set[str]:
    return set(cite_lines(text))


def cross_check(entries: list[dict[str, Any]], tex_text: str, bib_path: Path,
                tex_path: Path) -> list[dict[str, Any]]:
    """Keys the document cites without an entry, and entries nothing cites.

    A missing-entry finding points at the line of the citing command; an
    uncited-entry finding points at the entry in the bibliography.
    """
    known = {entry["key"]: entry for entry in entries}
    cited = cite_lines(tex_text)
    everything = cited.pop("*", None)  # \nocite{*}: every entry is cited
    if everything is not None:
        for key in known:
            cited.setdefault(key, everything)
    findings = [_finding(
        path=tex_path, key=key, line=cited[key], rule="reference-missing-entry",
        kind="integrity_blocker", strength="strong",
        observed={"bibliography": bib_path.name},
        message=f"\\cite{{{key}}} has no entry in {bib_path.name}.",
        action="Add the entry or fix the key; the build prints [?] for it.")
        for key in sorted(cited.keys() - known.keys())]
    findings.extend(_finding(
        path=bib_path, key=key, line=known[key]["line"], rule="reference-uncited",
        kind="advisory", strength="ordinary", observed={"bibliography": bib_path.name},
        message=f"Entry {key!r} is cited nowhere in the assembled document.",
        action="Remove the dead entry unless the bibliography is shared across papers.")
        for key in sorted(known.keys() - cited.keys()))
    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(report: dict[str, Any]) -> str:
    states = report["reference_states"]
    counts = {state: sum(1 for value in states.values() if value == state)
              for state in ("verified", "unresolved", "unmeasured", "no_identifier")}
    return (f"verify_references: {report['target']}\nentries: "
            + ", ".join(f"{name} {count}" for name, count in counts.items())
            + "\n" + feedback.render_text(report))


def build_parser() -> argparse.ArgumentParser:
    parser = cli_common.base_parser(__doc__)
    parser.add_argument("bib", type=Path, help="the .bib file to verify")
    parser.add_argument("--tex", type=Path, default=None,
                        help="document root; its assembled citation keys are cross-checked")
    parser.add_argument("--cache", type=Path, default=None,
                        help="JSON file of fetched records, read and updated; "
                             "a registry miss is not kept")
    parser.add_argument("--pause", type=float, default=0.2,
                        help="seconds between registry requests (default 0.2)")
    return cli_common.report_options(parser)


def load_cache(path: Path | None) -> dict[str, Any]:
    """The records a previous round fetched, keyed by identifier. Only
    records are kept: a `null` an earlier version wrote for a registry miss,
    or anything else that is not a record, is re-queried rather than trusted."""
    if path is None or not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"cache {path} is not a JSON object")
    return {key: value for key, value in loaded.items()
            if isinstance(value, dict) and "source" in value}


def verify(args: argparse.Namespace) -> dict[str, Any]:
    entries = parse_bib(args.bib.read_text(encoding="utf-8"))
    cache = load_cache(args.cache)
    findings: list[dict[str, Any]] = []
    states: dict[str, str] = {}
    for entry in entries:
        entry_findings, states[entry["key"]] = verify_entry(entry, args.bib, cache, args.pause)
        findings.extend(entry_findings)
    if args.cache is not None:
        args.cache.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                              encoding="utf-8")
    if args.tex is not None:
        findings.extend(cross_check(entries, tex_assembly.read_tex_document(args.tex),
                                    args.bib, args.tex))
    unmeasured = sum(1 for state in states.values() if state == "unmeasured")
    axes = [feedback.axis_status(
        "F.reference_existence", "degraded" if unmeasured else "measured",
        reason=f"{unmeasured} entries unanswered by the registries" if unmeasured else None,
        detector="verify_references")]
    report = feedback.build_report(path=args.bib, findings=findings, axes=axes)
    report["reference_states"] = states
    return report


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    args = build_parser().parse_args(argv)
    for path in (args.bib, args.tex):
        if path is not None and not path.is_file():
            print(f"[verify_references] file not found: {path}", file=sys.stderr)
            return 2
    try:
        report = verify(args)
    except Exception as error:
        # Deliberately broad, as in ai_ism_lint: exit 1 is reserved for "a
        # blocker is present", and an uncaught traceback also exits 1, so a
        # crash -- an unreadable .bib or cache, a registry answer the record
        # readers do not expect, an HTTP-layer error a narrow tuple missed --
        # would read as a blocker verdict. KeyboardInterrupt and SystemExit
        # are BaseException and still propagate.
        print(f"[verify_references] execution failed: {type(error).__name__}: {error}",
              file=sys.stderr)
        return 2
    cli_common.emit_report(report, args, render=render, tool="verify_references")
    return 1 if any(f["kind"] == "integrity_blocker" for f in report["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
