"""fetch_arxiv_abstracts: the sweep paths (audit 2026-09-27, D1-D5, D12, D13, D24).

The parser, backoff, vintage, resume and held-out tests are in
`test_fetch_arxiv_abstracts.py`; the harness both files share is
`_fetch_harness.py`.
"""

from __future__ import annotations

import gzip
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from _fetch_harness import (ARXIV_NS, ATOM_NS, LENSING, SOURCE, _bank, _candidate_args, _fulltext,
                            _offline, _pages_once, _record, _sweep, _throttle, _write_bank, fetch)


OLD_ID_FEED = f"""<feed xmlns="{ATOM_NS}" xmlns:arxiv="{ARXIV_NS}">
  <entry>
    <id>http://arxiv.org/abs/astro-ph/9403003v1</id>
    <published>1994-03-01T00:00:00Z</published>
    <updated>1994-03-01T00:00:00Z</updated>
    <summary>{' word' * 60}</summary>
    <author><name>Ian P. Dell'Antonio</name></author>
    <author><name>J. Anthony Tyson</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2001.00009v1</id>
    <published>2020-01-01T00:00:00Z</published>
    <updated>2020-01-01T00:00:00Z</updated>
    <summary>{' word' * 60}</summary>
  </entry>
</feed>"""


def _parse(feed: str) -> list[dict]:
    real = fetch.urlopen_backoff
    fetch.urlopen_backoff = lambda *a, **k: feed.encode("utf-8")
    try:
        return fetch.fetch_page("q", 0, 10, "199001010000", "202512312359")
    finally:
        fetch.urlopen_backoff = real


class OldStyleIdTest(unittest.TestCase):
    """An `archive/YYMMNNN` id must keep its archive.

    The e-print endpoint 404s without it, and the failure is silent in the worst
    way: the sweep reports `failed=N` and carries on, so the corpus is short by
    however many old papers the query returned. Measured on a live 1990-2021
    author sweep before the fix, 7 of 19 candidates were lost this way.
    """

    def test_the_archive_prefix_survives(self) -> None:
        self.assertEqual(_parse(OLD_ID_FEED)[0]["source"],
                         "arxiv:astro-ph/9403003v1")

    def test_a_new_style_id_is_unaffected(self) -> None:
        self.assertEqual(_parse(OLD_ID_FEED)[1]["source"], "arxiv:2001.00009v1")

    def test_the_slashed_id_still_normalises_for_identity(self) -> None:
        # Everything downstream was already built for the slash; only the parser
        # never produced one. This is the join that keeps held-out bookkeeping
        # working now that it does.
        self.assertEqual(fetch._bare("astro-ph/9403003v1"), "astro-ph_9403003")


class AuthorListTest(unittest.TestCase):
    """Team size comes from the API, never from counting `\author` in LaTeX."""

    def test_authors_are_extracted_in_order(self) -> None:
        self.assertEqual(_parse(OLD_ID_FEED)[0]["authors"],
                         ["Ian P. Dell'Antonio", "J. Anthony Tyson"])

    def test_an_entry_with_no_authors_yields_an_empty_list(self) -> None:
        self.assertEqual(_parse(OLD_ID_FEED)[1]["authors"], [])

    def test_the_abstract_writer_drops_the_list(self) -> None:
        # The abstract bank is a prose corpus that other tools read as text.
        with tempfile.TemporaryDirectory() as name:
            record = {**_record("arxiv:2001.00001", "2020-01-01", None), "authors": ["A. Author"]}
            _sweep(Path(name), ["--query-set", "wl", "--out-name", "a.jsonl",
                                "--per-query", "100"], [record])
            self.assertNotIn("authors", _bank(Path(name) / "wgl" / "a.jsonl")[0])


class AuthorQueryFormTest(unittest.TestCase):
    """`Surname_Initial` is the listing URL's format, not the search API's.

    Every one of the ten author queries carried that shape until 2026-08-26 and
    returned exactly 0 records, so the `broad` set was silently ten queries
    short while its comment claimed they broadened the corpus. A dead query
    leaves no trace in the output, which is why this is a test and not a note.
    """

    def test_no_author_query_uses_the_dead_underscore_initial_form(self) -> None:
        import re as _re
        dead = _re.compile(r"au:[A-Za-z]+_[A-Za-z](?:\b|$)")
        for query in fetch.AUTHOR_QUERIES:
            self.assertIsNone(dead.search(query), f"dead listing-URL form: {query}")

    def test_every_author_query_quotes_its_name(self) -> None:
        for query in fetch.AUTHOR_QUERIES:
            self.assertIn('au:"', query, f"unquoted author term: {query}")

    def test_surname_only_queries_are_scoped_to_the_field(self) -> None:
        # `au:` matches a SURNAME, and a surname is not a person: unscoped,
        # "Dell'Antonio" also returns a mathematical physicist's math-ph work.
        for query in fetch.AUTHOR_QUERIES:
            self.assertTrue("cat:" in query or "abs:" in query,
                            f"unscoped author query: {query}")


class AuthorQueryConstructionTest(unittest.TestCase):
    """`--author` takes a name OR a whole query, and the difference matters.

    `au:` matches a surname in every archive, not just the field's, and the
    identity filter cannot fix that: 32 of 100 `au:"Kaiser, N"` papers are
    nuclear theory under the SAME spelling of the name an `--author-is` regex
    would match. Scoping has to live in the query, so a value that already
    carries a query operator is passed through untouched.
    """

    def queries_for(self, author: str) -> list[str]:
        stub = _pages_once([])
        with tempfile.TemporaryDirectory() as name, _offline(Path(name), fetch_page=stub):
            fetch._candidate_ids(_candidate_args(Path(name), author=author), {"x"}, None)
        return [call[0] for call in stub.calls]

    def test_a_bare_name_is_quoted(self) -> None:
        self.assertEqual(self.queries_for("Dell'Antonio"), ['au:"Dell\'Antonio"'])

    def test_a_whole_query_passes_through_untouched(self) -> None:
        whole = 'au:"Kaiser, N" AND cat:astro-ph*'
        self.assertEqual(self.queries_for(whole), [whole])

    def test_no_author_falls_back_to_the_topic_sweep(self) -> None:
        self.assertEqual(self.queries_for(""), list(fetch.FULLTEXT_QUERIES))


class LocalShortcutJournalTest(unittest.TestCase):
    """D1: the local full-text shortcut honours --journals and counts its drops.

    It ignored the flag, so the "refereed" breadth corpus calibrate §2 asks for
    was refereed only when the abstract bank happened to be absent.
    """

    def _candidates(self, tmp: Path, journals: set[str] | None) -> tuple[list[str], str]:
        _write_bank(tmp, [_record("arxiv:2001.00001v1", "2020-01-01", text=LENSING),
                          _record("arxiv:2001.00002v1", "2020-01-01", "MNRAS 500, 1 (2021)",
                                  text=LENSING)])
        with _offline(tmp) as (_, err):
            found, throttled = fetch._candidate_ids(_candidate_args(tmp), set(), journals)
        self.assertFalse(throttled)
        return found, err.getvalue()

    def test_off_journal_records_are_dropped_and_counted(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            found, err = self._candidates(Path(name), {"apj"})
        self.assertEqual(found, ["2001.00001v1"])
        self.assertIn("1 off-journal dropped", err)

    def test_no_journal_filter_keeps_both(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            found, err = self._candidates(Path(name), None)
        self.assertEqual(found, ["2001.00001v1", "2001.00002v1"])
        self.assertIn("0 off-journal dropped", err)


class StartAtPageSizeTest(unittest.TestCase):
    """D2: a --start-at band sizes its pages from where the band began.

    With --start-at 2000 (the held-out pull's documented offset) every request
    used to ask for max_results = per_query - 2000, a negative number.
    """

    def test_pages_are_sized_from_the_band_start(self) -> None:
        stub = _pages_once([_record("arxiv:2001.00001v1", "2020-01-01")])
        with tempfile.TemporaryDirectory() as name, _offline(Path(name), fetch_page=stub):
            fetch._candidate_ids(_candidate_args(
                Path(name), query=["abs:x"], start_at=2000, per_query=150, page=100))
        self.assertEqual([(start, n) for _, start, n, *_ in stub.calls],
                         [(2000, 100), (2100, 50)])


class FieldResolutionTest(unittest.TestCase):
    """D3: omitting --field is a message and exit 2, never `Path / None`."""

    def test_no_profile_says_pass_field(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            status, err = _sweep(Path(name), [], field=None)
        self.assertEqual(status, 2)
        self.assertIn("pass --field", err)

    def test_two_profiles_say_choose(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            for field in ("wgl", "condmat"):
                (Path(name) / field).mkdir()
            status, err = _sweep(Path(name), [], field=None)
        self.assertEqual(status, 2)
        self.assertIn("Multiple fields", err)

    def test_a_single_profile_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            (Path(name) / "wgl").mkdir()
            self.assertEqual(_sweep(Path(name), [], field=None)[0], 0)
            self.assertTrue((Path(name) / "wgl" / fetch.BANK).exists())

    def test_a_named_new_field_is_created_not_refused(self) -> None:
        # calibrate §2 runs this tool before extract_style creates the profile
        # directory, so a named field must not be required to exist yet.
        with tempfile.TemporaryDirectory() as name:
            self.assertEqual(_sweep(Path(name), [], field="condmat")[0], 0)
            self.assertTrue((Path(name) / "condmat" / fetch.BANK).exists())


class FulltextThrottleTest(unittest.TestCase):
    """D4: a throttled full-text run reports TRUNCATED and exits 2, as the
    abstract sweep does. It used to print DONE and exit 0 from either stop."""

    def test_throttled_candidate_search_is_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            status, log, _ = _fulltext(Path(name), [], fetch_page=lambda *a, **k: _throttle(""))
        self.assertEqual(status, 2)
        self.assertIn("TRUNCATED", log)

    def test_throttled_download_is_truncated(self) -> None:
        pages = [_record("arxiv:2001.00001v1", "2020-01-01")]
        with tempfile.TemporaryDirectory() as name:
            status, log, _ = _fulltext(Path(name), [], pages, _eprint_bytes=_throttle)
        self.assertEqual(status, 2)
        self.assertIn("TRUNCATED", log)
        self.assertNotIn("DONE", log)

    def test_a_complete_run_is_done_under_the_bare_id(self) -> None:
        # D13 as well: the directory is named by the bare id, not `...v2`.
        pages = [_record("arxiv:2001.00001v2", "2021-01-01")]
        with tempfile.TemporaryDirectory() as name:
            status, log, out = _fulltext(Path(name), [], pages, _eprint_bytes=lambda i: SOURCE)
            self.assertEqual((status, sorted(p.name for p in out.iterdir())), (0, ["2001.00001"]))
        self.assertIn("DONE kept=1", log)


class FulltextVintageTest(unittest.TestCase):
    """D5: --updated-before applies in full-text mode, and the abstract-only
    flags are refused there instead of being accepted and ignored."""

    def test_live_candidates_revised_after_the_cutoff_are_dropped(self) -> None:
        pages = [_record("arxiv:2001.00001v3", "2023-04-01"),
                 _record("arxiv:2001.00002v1", "2020-01-01")]
        with tempfile.TemporaryDirectory() as name:
            with _offline(Path(name), fetch_page=_pages_once(pages)) as (_, err):
                found, _ = fetch._candidate_ids(
                    _candidate_args(Path(name), updated_before="2022-11-01"))
        self.assertEqual(found, ["2001.00002v1"])
        self.assertIn("1 revised on/after --updated-before", err.getvalue())

    def test_the_local_shortcut_is_not_taken_with_a_cutoff(self) -> None:
        # The bank's `updated` is a stale copy; only the live one dates what is
        # downloaded, so the shortcut must yield to the API.
        stub = _pages_once([])
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            _write_bank(tmp, [_record("arxiv:2001.00001v1", "2020-01-01", text=LENSING)])
            with _offline(tmp, fetch_page=stub):
                found, _ = fetch._candidate_ids(_candidate_args(tmp, updated_before="2022-11-01"))
        self.assertEqual((found, len(stub.calls)), ([], len(fetch.FULLTEXT_QUERIES)))

    def test_abstract_only_flags_are_refused_with_fulltext(self) -> None:
        for extra in (["--resume"], ["--query-set", "wl"], ["--out-name", "x.jsonl"],
                      ["--updated-before", "2022"]):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as name:
                with _offline(Path(name)), self.assertRaises(SystemExit):
                    fetch.main(["--field", "wgl", "--fulltext",
                                "--fulltext-dir", "fulltext-test"] + extra)


def _targz(members: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, text in members.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class TexMembersTest(unittest.TestCase):
    """D12: what counts as a LaTeX source. A document marker anywhere in a single
    file (pre-1995 sources say \\documentstyle; many open with a comment), and a
    tarball's colliding basenames are both kept rather than one overwriting."""

    def test_documentstyle_and_comment_led_single_files_are_sources(self) -> None:
        for text in ("\\documentstyle[12pt]{article}\n\\begin{document}x",
                     "% arXiv source\n\\documentclass{article}"):
            with self.subTest(text=text[:14]):
                self.assertEqual(fetch._tex_members(gzip.compress(text.encode())),
                                 {"main.tex": text})
                self.assertEqual(fetch._tex_members(text.encode()), {"main.tex": text})

    def test_text_without_a_document_marker_is_not_a_source(self) -> None:
        self.assertIsNone(fetch._tex_members(b"<html>e-print not available</html>"))
        self.assertIsNone(fetch._tex_members(gzip.compress(b"plain notes")))

    def test_colliding_basenames_in_a_tarball_are_both_kept(self) -> None:
        members = fetch._tex_members(_targz({"sections/intro.tex": "A", "appendix/intro.tex": "B",
                                             "main.tex": "\\documentclass{article}"}))
        self.assertEqual(sorted(members.values()), ["A", "B", "\\documentclass{article}"])
        self.assertEqual(len(members), 3)


class BareIdIdentityTest(unittest.TestCase):
    """D13: one paper, one copy. Candidate dedup and the output directory key on
    the bare id, so a version bump between runs does not fetch `…v2` beside `…v1`."""

    def test_two_versions_of_one_paper_are_one_candidate(self) -> None:
        pages = [_record("arxiv:2001.00001v1", "2020-01-01"),
                 _record("arxiv:2001.00001v2", "2021-01-01")]
        with tempfile.TemporaryDirectory() as name:
            with _offline(Path(name), fetch_page=_pages_once(pages)):
                found, _ = fetch._candidate_ids(_candidate_args(Path(name), query=["abs:x"]))
        self.assertEqual(found, ["2001.00001v1"])

    def test_a_versioned_directory_from_an_earlier_run_counts_as_fetched(self) -> None:
        downloads: list[str] = []
        with tempfile.TemporaryDirectory() as name:
            old = Path(name) / "style-corpus" / "wgl" / "fulltext-test" / "2001.00001v1"
            old.mkdir(parents=True)
            (old / "main.tex").write_text("x", encoding="utf-8")
            status, log, _ = _fulltext(Path(name), [], [_record("arxiv:2001.00001v2", "2021-01-01")],
                                       _eprint_bytes=lambda i: downloads.append(i) or SOURCE)
        self.assertEqual((status, downloads), (0, []))
        self.assertIn("kept=1", log)


class CustomQueryTest(unittest.TestCase):
    """D24: `--query` is how a field other than weak lensing uses the fetcher. It
    replaces the [WGL] built-in sets in both modes and bypasses the [WGL] keyword
    shortcut, and it cannot be combined with the built-in selectors."""

    def test_query_replaces_the_abstract_query_set(self) -> None:
        stub = _pages_once([])
        with tempfile.TemporaryDirectory() as name:
            _sweep(Path(name), ["--query", "cat:cond-mat.str-el", "--query", "abs:magnon"],
                   fetch_page=stub)
        self.assertEqual([call[0] for call in stub.calls], ["cat:cond-mat.str-el", "abs:magnon"])

    def test_query_forces_the_live_path_past_the_keyword_shortcut(self) -> None:
        stub = _pages_once([])
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            _write_bank(tmp, [_record("arxiv:2001.00001v1", "2020-01-01", text=LENSING)])
            with _offline(tmp, fetch_page=stub):
                found, _ = fetch._candidate_ids(_candidate_args(tmp, query=["cat:cond-mat"]))
        self.assertEqual((found, [call[0] for call in stub.calls]), ([], ["cat:cond-mat"]))

    def test_query_conflicts_are_refused(self) -> None:
        for extra in (["--query-set", "wl"],
                      ["--fulltext", "--fulltext-dir", "fulltext-test", "--author", "X"]):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as name:
                with _offline(Path(name)), self.assertRaises(SystemExit):
                    fetch.main(["--field", "wgl", "--query", "abs:x"] + extra)

    def test_query_over_an_existing_default_bank_needs_resume_or_out_name(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            self.assertEqual(_sweep(tmp, ["--query", "abs:x"])[0], 0)  # a new field's first bank
            with self.assertRaises(SystemExit):                        # would truncate it
                _sweep(tmp, ["--query", "abs:x"])
            self.assertEqual(_sweep(tmp, ["--query", "abs:x", "--resume"])[0], 0)
            self.assertEqual(_sweep(tmp, ["--query", "abs:x", "--out-name", "q.jsonl"])[0], 0)


if __name__ == "__main__":
    unittest.main()
