"""Verify a BibTeX bibliography against the records its identifiers resolve to.

Every entry that carries a DOI is resolved through CrossRef (DataCite as the
fallback for the DOI prefixes CrossRef does not register) and its author,
year, title, journal, volume and first page are compared with the fetched
record; an entry with only an arXiv identifier is resolved through the arXiv
API. The comparison is the mechanical half of paper-review dimension F
(citation existence): a DOI that resolves nowhere is an `integrity_blocker`
and a first author, year or title that disagrees with the record is a strong
advisory, both under `sci-paper.feedback.v1`. Journal, volume and page
disagreements are ordinary advisories, since abbreviations and article
numbers vary by house style. An entry the network could not answer for is
reported as unmeasured, never as clean, and the axis is `degraded`.

With `--tex`, the assembled document's `\\cite` keys are cross-checked: a key
with no bibliography entry is a blocker, an entry no sentence cites is an
ordinary advisory. Exit status follows the linter's narrow contract: 0 means
no blocker, 1 means a blocker is present, 2 means invalid input or execution
failure. `--cache` keeps fetched records in a JSON file so a repeated review
round does not re-query the registries.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
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
import tex_assembly  # noqa: E402  the assembled document for --tex

USER_AGENT = "sci-paper-verify-references/1.0"
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
RE_FIELD_HEAD = re.compile(r"\s*,?\s*(\w+)\s*=\s*")
RE_BARE_VALUE = re.compile(r"[^,}]*")
RE_CITE = re.compile(r"\\[cC]ite[a-zA-Z*]*(?:\[[^\]]*\]){0,2}\s*\{([^}]+)\}")
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


def _parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    position = 0
    while True:
        head = RE_FIELD_HEAD.match(body, position)
        if not head or head.end() >= len(body):
            return fields
        name, position = head.group(1).lower(), head.end()
        if body[position] == "{":
            end = _group_end(body, position, "}")
            value = body[position + 1:end - 1]
        elif body[position] == '"':
            end = body.index('"', position + 1) + 1
            value = body[position + 1:end - 1]
        else:
            end = RE_BARE_VALUE.match(body, position).end()
            value = body[position:end]
        fields[name] = " ".join(value.split())
        position = end


def parse_bib(text: str) -> list[dict[str, Any]]:
    """Every `@type{key, field = value, ...}` entry; comments and @string skipped."""
    entries = []
    for head in RE_ENTRY_HEAD.finditer(text):
        kind = head.group(1).lower()
        if kind in ("comment", "string", "preamble"):
            continue
        close = "}" if head.group(2) == "{" else ")"
        end = _group_end(text, head.start(2), close)
        entries.append({"key": head.group(3), "type": kind,
                        "line": text[:head.start()].count("\n") + 1,
                        "fields": _parse_fields(text[head.end():end - 1])})
    return entries


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize(text: str | None) -> str:
    """Lowercase alphanumerics only, LaTeX accents and braces removed."""
    if not text:
        return ""
    # CrossRef serves `&amp;` where a bibliography writes `\&`; both are "&".
    text = RE_ACCENT.sub(r"\1", html.unescape(str(text)))
    text = RE_LATEX_CMD.sub(" ", text).replace("{", "").replace("}", "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def first_author_family(authors: str) -> str:
    first = authors.split(" and ")[0].strip()
    if "," in first:
        return normalize(first.split(",")[0])
    tokens = first.split()
    return normalize(tokens[-1]) if tokens else ""


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
    """A registry could not be reached or answered outside 200/404."""


def fetch(url: str, timeout: int = 30) -> tuple[int, bytes]:
    """(HTTP status, body). 404 is an answer, not an error; the rest raise."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return 404, b""
        raise RegistryUnavailable(f"HTTP {error.code} from {url.split('?')[0]}") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise RegistryUnavailable(f"{error} ({url.split('?')[0]})") from error


def _crossref_record(message: dict[str, Any]) -> dict[str, Any]:
    authors = message.get("author") or []
    issued = (message.get("issued") or {}).get("date-parts") or [[None]]
    return {
        "source": "crossref",
        "first_author": (authors[0].get("family") or authors[0].get("name", "")) if authors else "",
        "year": issued[0][0],
        # CrossRef splits "GaBoDS: the Garching-Bonn Deep Survey. IX. A sample
        # of ..." into title and subtitle; a bibliography carries both as one.
        "title": " ".join((message.get("title") or [""])[:1]
                          + (message.get("subtitle") or [])),
        "journal": (message.get("container-title") or [""])[0],
        "journal_short": (message.get("short-container-title") or [""])[0],
        "volume": message.get("volume", ""),
        "page": message.get("page") or message.get("article-number") or "",
    }


def _datacite_record(attributes: dict[str, Any]) -> dict[str, Any]:
    creators = attributes.get("creators") or [{}]
    container = attributes.get("container") or {}
    return {
        "source": "datacite",
        "first_author": creators[0].get("familyName") or creators[0].get("name", "").split(",")[0],
        "year": attributes.get("publicationYear"),
        "title": (attributes.get("titles") or [{}])[0].get("title", ""),
        "journal": container.get("title", ""),
        "journal_short": "",
        "volume": container.get("volume", ""),
        "page": container.get("firstPage", ""),
    }


def resolve_doi(doi: str) -> dict[str, Any] | None:
    """The record a DOI resolves to, or None when neither registry knows it."""
    status, body = fetch(CROSSREF + urllib.parse.quote(doi, safe="/"))
    if status == 200:
        return _crossref_record(json.loads(body.decode("utf-8"))["message"])
    status, body = fetch(DATACITE + urllib.parse.quote(doi, safe="/"))
    if status == 200:
        return _datacite_record(json.loads(body.decode("utf-8"))["data"]["attributes"])
    return None


def resolve_arxiv(identifier: str) -> dict[str, Any] | None:
    status, body = fetch(ARXIV + urllib.parse.quote(identifier))
    if status != 200:
        return None
    entry = ET.fromstring(body.decode("utf-8", "replace")).find(f"{ATOM}entry")
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
    author = first_author_family(fields.get("author", ""))
    record_author = normalize(record.get("first_author"))
    if author and record_author and author != record_author \
            and author not in record_author and record_author not in author:
        issues.append({"field": "first_author", "entry": fields["author"].split(" and ")[0],
                       "record": record.get("first_author"), "strength": "strong"})
    year = fields.get("year", "")
    if year.isdigit() and record.get("year"):
        gap = abs(int(year) - int(record["year"]))
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
    """`doi:<doi>`, else `arxiv:<id>`, else None."""
    doi = RE_DOI_URL.sub("", fields.get("doi", "").strip())
    if doi:
        return "doi:" + doi
    arxiv = arxiv_id(fields)
    return ("arxiv:" + arxiv) if arxiv else None


def verify_entry(entry: dict[str, Any], path: Path, cache: dict[str, Any],
                 pause: float) -> tuple[list[dict[str, Any]], str]:
    """(findings, state); state is verified / unresolved / unmeasured / no_identifier."""
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
    if identifier in cache:
        record = cache[identifier]
    else:
        scheme, _, value = identifier.partition(":")
        try:
            record = resolve_doi(value) if scheme == "doi" else resolve_arxiv(value)
        except RegistryUnavailable as error:
            return [_finding(
                path=path, key=key, line=line, rule="reference-lookup-failed",
                kind="advisory", strength="ordinary", status="unmeasured",
                observed={"identifier": identifier, "error": str(error)},
                message=f"Entry {key!r}: the registry did not answer ({error}).",
                action="Re-run when the network allows; the entry is unverified, "
                       "not clean.")], "unmeasured"
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
            observed={"identifier": identifier, "record_source": record["source"], **issue},
            message=(f"Entry {key!r}: {issue['field']} reads {issue['entry']!r} "
                     f"but the {record['source']} record says {issue['record']!r}."),
            action=("Correct the entry from the record, or confirm the identifier "
                    "points at the intended work." if strong else
                    "Confirm the house-style abbreviation or article number "
                    "matches the record."),
        ))
    return findings, "verified"


def cite_keys(text: str) -> set[str]:
    return {key.strip() for match in RE_CITE.finditer(text)
            for key in match.group(1).split(",") if key.strip()}


def cross_check(entries: list[dict[str, Any]], tex_text: str, bib_path: Path,
                tex_path: Path) -> list[dict[str, Any]]:
    """Keys the document cites without an entry, and entries nothing cites."""
    known = {entry["key"]: entry for entry in entries}
    cited = cite_keys(tex_text)
    findings = [_finding(
        path=tex_path, key=key, line=1, rule="reference-missing-entry",
        kind="integrity_blocker", strength="strong",
        observed={"bibliography": bib_path.name},
        message=f"\\cite{{{key}}} has no entry in {bib_path.name}.",
        action="Add the entry or fix the key; the build prints [?] for it.")
        for key in sorted(cited - known.keys())]
    findings.extend(_finding(
        path=bib_path, key=key, line=known[key]["line"], rule="reference-uncited",
        kind="advisory", strength="ordinary", observed={"bibliography": bib_path.name},
        message=f"Entry {key!r} is cited nowhere in the assembled document.",
        action="Remove the dead entry unless the bibliography is shared across papers.")
        for key in sorted(known.keys() - cited))
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
                        help="document root; its assembled \\cite keys are cross-checked")
    parser.add_argument("--cache", type=Path, default=None,
                        help="JSON file of fetched records, read and updated")
    parser.add_argument("--pause", type=float, default=0.2,
                        help="seconds between registry requests (default 0.2)")
    return cli_common.report_options(parser)


def verify(args: argparse.Namespace) -> dict[str, Any]:
    entries = parse_bib(args.bib.read_text(encoding="utf-8"))
    cache: dict[str, Any] = {}
    if args.cache is not None and args.cache.is_file():
        cache = json.loads(args.cache.read_text(encoding="utf-8"))
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
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError,
            ET.ParseError) as error:
        print(f"[verify_references] execution failed: {error}", file=sys.stderr)
        return 2
    cli_common.emit_report(report, args, render=render, tool="verify_references")
    return 1 if any(f["kind"] == "integrity_blocker" for f in report["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
