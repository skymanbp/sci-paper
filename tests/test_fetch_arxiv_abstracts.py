from __future__ import annotations

import json
import sys
import tempfile
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
import urllib.error
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import fetch_arxiv_abstracts as fetch


class ClassifyJournalTest(unittest.TestCase):
    """Journal keys are decided from the literal journal_ref shapes seen live.

    The API's own jr: prefix is a loose token match and was observed to return
    "Research in Astronomy and Astrophysics" for a jr:"Astronomy and
    Astrophysics" query, so selection happens here and the near-miss journals
    are pinned as explicit negatives.
    """

    def test_apj_abbreviated_and_spelled_out_forms(self) -> None:
        for ref in ("Astrophys. J. 934, no.2, 129 (2022)",
                    "Astrophys. J., 911, 82 (2021)",
                    "ApJ, 927, 101 (2022)",
                    "2026, ApJ, 1006: 61 (11pp)",
                    "ApJ 1005 (2026) 211",
                    "The Astrophysical Journal, Volume 900, Issue 1 (2020)"):
            with self.subTest(ref=ref):
                self.assertEqual(fetch.classify_journal(ref), "apj")

    def test_letters_wins_over_the_main_journal_it_contains(self) -> None:
        # "ApJL" and "Astrophys. J. Lett." both contain the ApJ pattern, so an
        # unordered table would file every Letter under apj.
        for ref in ("The Astrophysical Journal Letters, Volume 924 (2022), Number 1, L3",
                    "ApJL 900, L12 (2020)",
                    "Astrophys. J. Lett. 875, L1 (2019)"):
            with self.subTest(ref=ref):
                self.assertEqual(fetch.classify_journal(ref), "apjl")

    def test_aa_abbreviated_and_spelled_out_forms(self) -> None:
        for ref in ("A&A 660, A114 (2022)",
                    "Astronomy and Astrophysics, 655, A115 (2021)",
                    "Astronomy & Astrophysics 660, A9 (2022)"):
            with self.subTest(ref=ref):
                self.assertEqual(fetch.classify_journal(ref), "aa")

    def test_research_in_astronomy_and_astrophysics_is_not_aa(self) -> None:
        # The exact false positive the live API probe produced.
        for ref in ("Research in Astronomy and Astrophysics 26, 084012 (2026)",
                    "Research in Astronomy and Astrophysics, 25 (2025) 065013"):
            with self.subTest(ref=ref):
                self.assertIsNone(fetch.classify_journal(ref))

    def test_supplement_and_review_series_are_excluded(self) -> None:
        for ref in ("ApJS 250, 12 (2020)",
                    "The Astrophysical Journal Supplement Series 245, 1",
                    "A&A Review 30, 3 (2022)"):
            with self.subTest(ref=ref):
                self.assertIsNone(fetch.classify_journal(ref))

    def test_other_journals_are_unmatched(self) -> None:
        for ref in ("MNRAS, 514, 5905 (2022)",
                    "Monthly Notices of the Royal Astronomical Society, Volume 516",
                    "JCAP11(2022)020",
                    "Phys. Rev. D 106 (2022) 023530",
                    "New Astronomy 90, 101665 (2022)",
                    "Astrophysics and Space Science 365, 44"):
            with self.subTest(ref=ref):
                self.assertIsNone(fetch.classify_journal(ref))

    def test_missing_journal_ref_is_unmatched_not_an_error(self) -> None:
        self.assertIsNone(fetch.classify_journal(None))
        self.assertIsNone(fetch.classify_journal(""))


ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"

FEED = f"""<feed xmlns="{ATOM_NS}" xmlns:arxiv="{ARXIV_NS}">
  <entry>
    <id>http://arxiv.org/abs/2001.00001v1</id>
    <published>2020-01-01T00:00:00Z</published>
    <updated>2023-04-01T00:00:00Z</updated>
    <summary>{' word' * 60}</summary>
    <arxiv:journal_ref>A&amp;A 660,
    A114 (2022)</arxiv:journal_ref>
    <arxiv:doi>10.1051/0004-6361/202142000</arxiv:doi>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2001.00002v1</id>
    <published>2019-05-05T00:00:00Z</published>
    <updated>2019-05-05T00:00:00Z</updated>
    <summary>{' word' * 60}</summary>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2001.00003v1</id>
    <published>2018-05-05T00:00:00Z</published>
    <updated>2018-05-05T00:00:00Z</updated>
    <summary>too short</summary>
  </entry>
</feed>"""


class ParseEntryTest(unittest.TestCase):
    """Exercises the real fetch_page against a canned feed, not a copy of it."""

    def parse(self) -> list[dict]:
        real = fetch.urlopen_backoff
        fetch.urlopen_backoff = lambda *a, **k: FEED.encode("utf-8")
        try:
            return fetch.fetch_page("q", 0, 10, "201001010000", "202112312359")
        finally:
            fetch.urlopen_backoff = real

    def test_wrapped_journal_ref_is_whitespace_normalised(self) -> None:
        rows = self.parse()
        self.assertEqual(rows[0]["journal_ref"], "A&A 660, A114 (2022)")
        self.assertEqual(rows[0]["journal"], "aa")

    def test_entry_without_journal_ref_yields_none_not_a_crash(self) -> None:
        rows = self.parse()
        self.assertIsNone(rows[1]["journal_ref"])
        self.assertIsNone(rows[1]["journal"])

    def test_short_abstract_is_dropped(self) -> None:
        self.assertEqual(len(self.parse()), 2)

    def test_published_dates_v1_but_updated_dates_the_returned_text(self) -> None:
        # The record the vintage filter exists for: submitted 2020, abstract
        # text as last revised in 2023.
        row = self.parse()[0]
        self.assertEqual(row["published"], "2020-01-01")
        self.assertEqual(row["updated"], "2023-04-01")
        self.assertEqual(row["year"], 2020)


class QuerySetTest(unittest.TestCase):
    def test_broad_set_is_the_pre_existing_query_list(self) -> None:
        self.assertEqual(fetch.QUERY_SETS["broad"],
                         fetch.QUERIES + fetch.AUTHOR_QUERIES)

    def test_wl_set_is_weak_lensing_only(self) -> None:
        self.assertTrue(fetch.QUERY_SETS["wl"])
        for query in fetch.QUERY_SETS["wl"]:
            with self.subTest(query=query):
                self.assertIn("cat:astro-ph", query)
                self.assertTrue(any(term in query for term in
                                    ("lensing", "shear", "convergence",
                                     "aperture mass", "mass map",
                                     "mass reconstruction", "peak statistics")),
                                f"{query!r} carries no weak-lensing term")


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://example", code, "err", {}, None)


class BackoffTest(unittest.TestCase):
    """A throttled sweep must stop loudly, never write a silent partial corpus.

    The live run that motivated this lost 11 of 16 queries to HTTP 429, wrote
    195 records, and exited 0 - indistinguishable from a complete sweep.
    """

    def setUp(self) -> None:
        self.slept: list[float] = []
        self._real_sleep = fetch.time.sleep
        fetch.time.sleep = self.slept.append   # never actually wait in tests
        self.addCleanup(setattr, fetch.time, "sleep", self._real_sleep)

    def _run(self, responses: list) -> bytes:
        calls = iter(responses)

        def fake_urlopen(request, timeout=None):
            item = next(calls)
            if isinstance(item, Exception):
                raise item
            return _FakeResponse(item)

        real = fetch.urllib.request.urlopen
        fetch.urllib.request.urlopen = fake_urlopen
        try:
            return fetch.urlopen_backoff(
                urllib.request.Request("http://example"), timeout=5)
        finally:
            fetch.urllib.request.urlopen = real

    def test_succeeds_without_sleeping_when_not_throttled(self) -> None:
        self.assertEqual(self._run([b"payload"]), b"payload")
        self.assertEqual(self.slept, [])

    def test_retries_after_429_and_returns_the_eventual_payload(self) -> None:
        got = self._run([_http_error(429), _http_error(429), b"payload"])
        self.assertEqual(got, b"payload")
        self.assertEqual(self.slept, list(fetch.BACKOFF_SCHEDULE[:2]))

    def test_raises_throttled_once_the_schedule_is_exhausted(self) -> None:
        attempts = [_http_error(429)] * (len(fetch.BACKOFF_SCHEDULE) + 1)
        with self.assertRaises(fetch.Throttled):
            self._run(attempts)
        self.assertEqual(self.slept, list(fetch.BACKOFF_SCHEDULE))

    def test_non_429_http_error_propagates_and_is_not_retried(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self._run([_http_error(503)])
        self.assertEqual(caught.exception.code, 503)
        self.assertEqual(self.slept, [])

    def test_throttled_is_not_a_generic_exception_subclass_catch(self) -> None:
        # The abstract sweep distinguishes the two: a hiccup is skipped, a
        # Throttled stops the sweep. That only works if it is its own type.
        self.assertTrue(issubclass(fetch.Throttled, Exception))
        self.assertFalse(issubclass(fetch.Throttled, urllib.error.HTTPError))


def _record(source: str, updated: str, journal_ref: str = "ApJ, 927, 101 (2021)") -> dict:
    return {"section": "abstract", "text": "word " * 60, "source": source,
            "year": 2020, "published": "2020-01-01", "updated": updated,
            "journal_ref": journal_ref,
            "journal": fetch.classify_journal(journal_ref), "doi": None}


class TextVintageFilterTest(unittest.TestCase):
    """--date-hi bounds the v1 submission; only --updated-before dates the text.

    48% of the existing 13,642-record human bank are non-v1, and a live probe
    found latest-version dates as late as 2023-04 among 2021 submissions, so
    submission date alone does not establish a pre-LLM abstract.
    """

    def _run(self, page: list[dict], extra: list[str]) -> list[dict]:
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            (tmp / "wgl").mkdir(parents=True)
            real = fetch.fetch_page
            calls = {"n": 0}

            def one_page(*a, **k):
                calls["n"] += 1
                return page if calls["n"] == 1 else []

            fetch.fetch_page = one_page
            try:
                # The CLI's progress log is the suite's only stdout noise and
                # prints an absolute temp path; capture it so a test run stays
                # readable, the same technique validate_plugin.py uses.
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    fetch.main(["--field", "wgl", "--profile-root", str(tmp),
                                "--query-set", "wl", "--out-name", "v.jsonl",
                                "--per-query", "100"] + extra)
            finally:
                fetch.fetch_page = real
            text = (tmp / "wgl" / "v.jsonl").read_text(encoding="utf-8").strip()
            return [json.loads(line) for line in text.splitlines() if line]

    def test_record_revised_after_the_cutoff_is_dropped(self) -> None:
        page = [_record("arxiv:2001.1v3", "2023-04-01"),
                _record("arxiv:2001.2v1", "2020-01-01")]
        kept = self._run(page, ["--updated-before", "2022-11-01"])
        self.assertEqual([r["source"] for r in kept], ["arxiv:2001.2v1"])

    def test_no_cutoff_keeps_the_revised_record(self) -> None:
        page = [_record("arxiv:2001.1v3", "2023-04-01")]
        self.assertEqual(len(self._run(page, [])), 1)

    def test_missing_updated_is_dropped_not_assumed_clean(self) -> None:
        page = [_record("arxiv:2001.1v1", "")]
        self.assertEqual(self._run(page, ["--updated-before", "2022-11-01"]), [])

    def test_malformed_cutoff_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            self._run([], ["--updated-before", "2022"])


class IncompleteSweepTest(unittest.TestCase):
    """A page error must not masquerade as an exhausted query.

    A failed page and an empty page both arrived as `page = []`, and the
    `if not page: break` that ends pagination cannot tell them apart — so one
    transient error silently truncated that query while the run still exited 0,
    reporting a short corpus as a complete one.
    """

    def _run(self, pages) -> tuple[int, list[dict]]:
        with tempfile.TemporaryDirectory() as temporary:
            tmp = Path(temporary)
            calls = {"n": 0}

            def flaky(*args, **kwargs):
                calls["n"] += 1
                if calls["n"] == 1:
                    return pages
                raise RuntimeError("simulated transient API failure")

            real = fetch.fetch_page
            fetch.fetch_page = flaky
            try:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err:
                    status = fetch.main([
                        "--field", "wgl", "--profile-root", str(tmp),
                        "--query-set", "wl", "--out-name", "v.jsonl",
                        "--per-query", "100", "--page", "1",
                    ])
            finally:
                fetch.fetch_page = real
            self.assertIn("INCOMPLETE", err.getvalue())
            written = tmp / "wgl" / "v.jsonl"
            records = []
            if written.exists():
                records = [json.loads(line) for line
                           in written.read_text(encoding="utf-8").splitlines() if line]
            return status, records

    def test_page_error_reports_incomplete_and_exits_two(self):
        status, records = self._run([_record("arxiv:2001.1v1", "ApJ, 927, 101 (2021)")])
        self.assertEqual(status, 2)
        # Records fetched before the error are still valid and still written.
        self.assertEqual(len(records), 1)


class ResumeTest(unittest.TestCase):
    """A rerun after rate limiting must extend the corpus, never shrink it."""

    def _run_main(self, tmp: Path, extra: list[str]) -> int:
        real = fetch.fetch_page
        fetch.fetch_page = lambda *a, **k: []      # no network in tests
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return fetch.main(["--field", "wgl", "--profile-root", str(tmp),
                                   "--query-set", "wl", "--journals", "apj",
                                   "--out-name", "carry.jsonl",
                                   "--per-query", "100"] + extra)
        finally:
            fetch.fetch_page = real

    def _seed(self, tmp: Path) -> Path:
        field = tmp / "wgl"
        field.mkdir(parents=True)
        out = field / "carry.jsonl"
        with out.open("w", encoding="utf-8") as handle:
            for i in range(3):
                handle.write(json.dumps({
                    "section": "abstract", "text": "word " * 60,
                    "source": f"arxiv:20{i:02d}.00001", "year": 2020,
                    "journal_ref": "ApJ, 927, 101 (2021)", "journal": "apj",
                    "doi": None}) + "\n")
        return out

    def test_resume_keeps_existing_records_when_the_sweep_finds_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            out = self._seed(tmp)
            self.assertEqual(self._run_main(tmp, ["--resume"]), 0)
            self.assertEqual(len(out.read_text(encoding="utf-8").strip().splitlines()), 3)

    def test_without_resume_the_writer_truncates(self) -> None:
        # Documents the destructive default that --resume exists to avoid.
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            out = self._seed(tmp)
            self.assertEqual(self._run_main(tmp, []), 0)
            self.assertEqual(out.read_text(encoding="utf-8").strip(), "")

    def test_resume_deduplicates_against_carried_sources(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            out = self._seed(tmp)
            duplicate = {"section": "abstract", "text": "word " * 60,
                         "source": "arxiv:2000.00001", "year": 2020,
                         "journal_ref": "ApJ, 927, 101 (2021)",
                         "journal": "apj", "doi": None}
            real = fetch.fetch_page
            calls = {"n": 0}

            def one_page(*a, **k):
                calls["n"] += 1
                return [duplicate] if calls["n"] == 1 else []

            fetch.fetch_page = one_page
            try:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                    fetch.main(["--field", "wgl", "--profile-root", str(tmp),
                                "--query-set", "wl", "--journals", "apj",
                                "--out-name", "carry.jsonl", "--per-query", "100",
                                "--resume"])
            finally:
                fetch.fetch_page = real
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 3, "carried source must not be re-added")


if __name__ == "__main__":
    unittest.main()
