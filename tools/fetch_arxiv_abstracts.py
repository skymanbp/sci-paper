"""fetch_arxiv_abstracts.py — harvest CLEAN human scientific prose at scale.

Pulls astro-ph abstracts from the arXiv API to widen the voice model's HUMAN
positive set beyond the curated corpus. Two deliberate choices:

  * PRE-2022 ONLY (default 2010-2021). After ChatGPT, a growing fraction of
    abstracts are LLM-assisted (Kobak et al., Science Advances 2025: >=10 % of
    2024 abstracts). Restricting to pre-2022 guarantees the positives are
    genuinely human — otherwise we would train the voice model on contaminated
    "human" data.
  * BROAD subfields (cosmology, galaxies, high-energy, stellar, exoplanets,
    plus lensing/cluster terms) so the model learns human VOICE across
    astrophysics, not one narrow topic.

Output: style-profile/<field>/human_abstracts_extra.jsonl
  {"section": "abstract", "text": ..., "source": "arxiv:<id>", "year": <int>}

Stdlib only (urllib + xml.etree); respects the arXiv API 3 s rate guidance.

Run:  python tools/fetch_arxiv_abstracts.py --field wgl --per-query 400
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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

# Authoritative authors: the advisor (Ian Dell'Antonio) + widely-cited
# weak-lensing / cluster-lensing authors. These are the highest-value HUMAN
# positives — the voice we actually want the model to recognize as human.
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
    args = p.parse_args(argv)

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
    print(f"[fetch] wrote {len(recs)} clean-human abstracts -> {out}")
    print(f"[fetch] year span: {years[0] if years else '-'}..{years[-1] if years else '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
