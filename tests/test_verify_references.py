"""verify_references: BibTeX reading, record comparison, and the exit contract.

Every registry call is replaced by a canned `fetch`, so the suite never
touches the network; the live behaviour it stands in for was taken on the
two manuscripts' bibliographies on 2026-09-05 (CrossRef title/subtitle
split, the print/online year seam, `&amp;` against `\\&`, DataCite fallback
for a Zenodo DOI).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _toolpath import TOOLS  # noqa: F401,E402 -- because importing it is what puts tools/ on sys.path

import verify_references as vr

BIB = r"""
% a comment line with @article{not_an_entry, inside it
@string{apj = "The Astrophysical Journal"}

@article{schneider1996,
  author  = {Schneider, Peter and van Waerbeke, Ludovic},
  title   = {{B-modes} in cosmic shear: the {Garching-Bonn} survey},
  journal = {Monthly Notices of the Royal Astronomical Society},
  volume  = {283},
  pages   = {837--853},
  year    = {1996},
  doi     = {https://doi.org/10.1093/mnras/283.3.837}
}
@ARTICLE(fan2010,
  author = "Fan, Zuhui and Shan, Huanyuan",
  title = "Noisy weak-lensing convergence peak statistics near clusters",
  year = 2010,
  eprint = {1006.5121v2},
)
@misc{ho2020,
  author = {Ho, Jonathan},
  title = {Denoising diffusion},
  year = {2020}
}
@software{code2025,
  author = {Doe, Jane},
  title = {A pipeline},
  year = {2025},
  doi = {10.5281/zenodo.1234567}
}
"""

CROSSREF = {
    "message": {
        "author": [{"family": "Schneider", "given": "Peter"}],
        "issued": {"date-parts": [[1997, 1, 1]]},
        "title": ["B-modes in cosmic shear"],
        "subtitle": ["the Garching-Bonn survey"],
        "container-title": ["Monthly Notices of the Royal Astronomical Society"],
        "short-container-title": ["MNRAS"],
        "volume": "283", "page": "837-853",
    }
}
DATACITE = {"data": {"attributes": {
    "creators": [{"familyName": "Doe", "name": "Doe, Jane"}],
    "publicationYear": 2025, "titles": [{"title": "A pipeline"}],
    "container": {}}}}
ARXIV_FEED = (
    '<feed xmlns="http://www.w3.org/2005/Atom"><entry>'
    '<id>http://arxiv.org/abs/1006.5121v2</id><published>2010-06-26T00:00:00Z</published>'
    '<title>Noisy weak-lensing convergence peak statistics</title>'
    '<author><name>Zuhui Fan</name></author><author><name>Huanyuan Shan</name></author>'
    '</entry></feed>')
ARXIV_EMPTY = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Error</title></entry></feed>'


def canned(responses: dict[str, tuple[int, bytes] | Exception]):
    """A `fetch` that answers by URL prefix, so a test names every registry call."""
    calls: list[str] = []

    def fetch(url: str, timeout: int = 30):
        calls.append(url)
        for prefix, answer in responses.items():
            if url.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError(f"unexpected registry call {url}")
    fetch.calls = calls
    return fetch


class ParseBibTests(unittest.TestCase):
    def test_entries_fields_and_lines(self):
        entries = vr.parse_bib(BIB)
        self.assertEqual([e["key"] for e in entries],
                         ["schneider1996", "fan2010", "ho2020", "code2025"])
        first = entries[0]
        self.assertEqual((first["type"], first["line"]), ("article", 5))
        self.assertEqual(first["fields"]["pages"], "837--853")
        self.assertEqual(first["fields"]["title"],
                         "{B-modes} in cosmic shear: the {Garching-Bonn} survey")

    def test_parenthesised_entry_with_quoted_and_bare_values(self):
        fan = vr.parse_bib(BIB)[1]["fields"]
        self.assertEqual((fan["author"], fan["year"], fan["eprint"]),
                         ("Fan, Zuhui and Shan, Huanyuan", "2010", "1006.5121v2"))

    def test_unbalanced_entry_is_a_value_error(self):
        with self.assertRaises(ValueError):
            vr.parse_bib("@article{broken,\n title = {never closed\n")


class NormalizationTests(unittest.TestCase):
    """Table-driven: each row is (function, input, expected)."""

    ROWS = (
        (vr.normalize, r"{\'E}rben, M\"{u}ller \& {B-modes}", "erbenmullerbmodes"),
        (vr.normalize, "Émile Düsseldorf &amp; co", "emiledusseldorfco"),
        (vr.first_author_family, "van Waerbeke, Ludovic and Mellier, Y.", "vanwaerbeke"),
        (vr.first_author_family, "Peter Schneider and Y. Mellier", "schneider"),
        (vr.first_author_family, "", ""),
        (vr.first_page, "1408--1420", "1408"),
        (vr.first_page, "1408–1420", "1408"),
        (vr.first_page, "A114", "a114"),
        (vr.first_page, None, ""),
        (vr._journal_name, "The Annals of Statistics", "annalsofstatistics"),
    )

    def test_rows(self):
        for function, given, expected in self.ROWS:
            with self.subTest(function=function.__name__, given=given):
                self.assertEqual(function(given), expected)

    def test_identifier_prefers_doi_and_strips_the_resolver_url(self):
        entries = {e["key"]: e["fields"] for e in vr.parse_bib(BIB)}
        identifiers = {key: vr.entry_identifier(fields) for key, fields in entries.items()}
        self.assertEqual(identifiers, {"schneider1996": "doi:10.1093/mnras/283.3.837",
                                       "fan2010": "arxiv:1006.5121", "ho2020": None,
                                       "code2025": "doi:10.5281/zenodo.1234567"})

    def test_cite_keys_with_optional_arguments_and_lists(self):
        text = r"\citep[e.g.,][]{a, b}\citet{c}\Citealt*{d} \cite {e}"
        self.assertEqual(vr.cite_keys(text), {"a", "b", "c", "d", "e"})


class CompareTests(unittest.TestCase):
    def setUp(self):
        self.record = vr._crossref_record(CROSSREF["message"])
        self.fields = vr.parse_bib(BIB)[0]["fields"]

    def issues(self, **overrides) -> dict[str, str]:
        return {issue["field"]: issue["strength"]
                for issue in vr.compare(dict(self.fields, **overrides), self.record)}

    def test_subtitle_joins_the_title_and_the_print_online_seam_is_ordinary(self):
        self.assertEqual(self.issues(), {"year": "ordinary"})

    def test_wrong_first_author_title_and_distant_year_are_strong(self):
        found = self.issues(author="Mellier, Yannick", year="1990",
                            title="Cosmic microwave background anisotropies")
        self.assertEqual(found, {"first_author": "strong", "year": "strong", "title": "strong"})

    def test_journal_short_form_matches_and_volume_page_are_ordinary(self):
        found = self.issues(journal="MNRAS", volume="284", pages="838--853", year="1997")
        self.assertEqual(found, {"volume": "ordinary", "page": "ordinary"})

    def test_missing_fields_on_either_side_are_not_compared(self):
        self.assertEqual(vr.compare({"author": "Schneider, P."}, {"first_author": "", "title": ""}), [])


class VerifyTests(unittest.TestCase):
    def run_verify(self, fetch, tex: str | None = None, cache: Path | None = None):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bib = root / "refs.bib"
            bib.write_text(BIB, encoding="utf-8")
            argv = [str(bib), "--pause", "0", "--format", "json",
                    "--output", str(root / "out.json")]
            if tex is not None:
                (root / "main.tex").write_text(tex, encoding="utf-8")
                argv += ["--tex", str(root / "main.tex")]
            if cache is not None:
                argv += ["--cache", str(cache)]
            real = vr.fetch
            vr.fetch = fetch
            try:
                code = vr.main(argv)
            finally:
                vr.fetch = real
            return code, json.loads((root / "out.json").read_text(encoding="utf-8"))

    def registries(self, **overrides):
        answers = {
            vr.CROSSREF + "10.1093": (200, json.dumps(CROSSREF).encode()),
            vr.CROSSREF + "10.5281": (404, b""),
            vr.DATACITE + "10.5281": (200, json.dumps(DATACITE).encode()),
            vr.ARXIV: (200, ARXIV_FEED.encode()),
        }
        answers.update(overrides)
        return canned(answers)

    def test_clean_bibliography_exits_zero_with_states_and_unmeasured_entry(self):
        code, report = self.run_verify(self.registries())
        self.assertEqual(code, 0)
        self.assertEqual(report["reference_states"],
                         {"schneider1996": "verified", "fan2010": "verified",
                          "ho2020": "no_identifier", "code2025": "verified"})
        rules = sorted(f["rule"] for f in report["findings"])
        self.assertEqual(rules, ["reference-metadata-mismatch:year", "reference-no-identifier"])
        self.assertEqual(report["axes"][0]["status"], "measured")
        unmeasured = next(f for f in report["findings"] if f["rule"] == "reference-no-identifier")
        self.assertEqual(unmeasured["measurement_status"], "unmeasured")

    def test_unresolved_doi_is_a_blocker_and_exits_one(self):
        fetch = self.registries(**{vr.DATACITE + "10.5281": (404, b"")})
        code, report = self.run_verify(fetch)
        self.assertEqual(code, 1)
        blocker = next(f for f in report["findings"] if f["kind"] == "integrity_blocker")
        self.assertEqual(blocker["rule"], "reference-identifier-unresolved")
        self.assertEqual(blocker["observed"]["identifier"], "doi:10.5281/zenodo.1234567")

    def test_unknown_arxiv_identifier_is_a_blocker(self):
        code, report = self.run_verify(self.registries(**{vr.ARXIV: (200, ARXIV_EMPTY.encode())}))
        self.assertEqual((code, report["reference_states"]["fan2010"]), (1, "unresolved"))

    def test_registry_outage_degrades_the_axis_instead_of_reading_clean(self):
        fetch = self.registries(**{vr.CROSSREF + "10.1093": vr.RegistryUnavailable("HTTP 503")})
        code, report = self.run_verify(fetch)
        self.assertEqual((code, report["reference_states"]["schneider1996"]), (0, "unmeasured"))
        self.assertEqual(report["axes"][0]["status"], "degraded")
        failed = next(f for f in report["findings"] if f["rule"] == "reference-lookup-failed")
        self.assertEqual(failed["measurement_status"], "unmeasured")

    def test_tex_cross_check_finds_missing_entries_and_uncited_ones(self):
        tex = r"\cite{schneider1996,ghost2001} \citep[see][]{fan2010}"
        code, report = self.run_verify(self.registries(), tex=tex)
        self.assertEqual(code, 1)
        by_rule = {f["rule"]: f for f in report["findings"]}
        self.assertEqual(by_rule["reference-missing-entry"]["kind"], "integrity_blocker")
        self.assertEqual(by_rule["reference-missing-entry"]["observed"]["key"], "ghost2001")
        uncited = sorted(f["observed"]["key"] for f in report["findings"]
                         if f["rule"] == "reference-uncited")
        self.assertEqual(uncited, ["code2025", "ho2020"])

    def test_cache_is_written_and_then_spares_the_registries(self):
        with tempfile.TemporaryDirectory() as raw:
            cache = Path(raw) / "cache.json"
            first = self.registries()
            self.run_verify(first, cache=cache)
            self.assertEqual(len(first.calls), 4)      # crossref, crossref 404, datacite, arxiv
            saved = json.loads(cache.read_text(encoding="utf-8"))
            self.assertEqual(saved["doi:10.5281/zenodo.1234567"]["source"], "datacite")
            second = self.registries()
            code, report = self.run_verify(second, cache=cache)
            self.assertEqual((second.calls, code), ([], 0))
            self.assertEqual(report["reference_states"]["code2025"], "verified")

    def test_missing_files_are_configuration_failures(self):
        self.assertEqual(vr.main(["no-such.bib"]), 2)
        with tempfile.TemporaryDirectory() as raw:
            bib = Path(raw) / "refs.bib"
            bib.write_text(BIB, encoding="utf-8")
            self.assertEqual(vr.main([str(bib), "--tex", str(Path(raw) / "no.tex")]), 2)


if __name__ == "__main__":
    unittest.main()
