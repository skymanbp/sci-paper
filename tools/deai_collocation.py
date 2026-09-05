"""Field-collocation feedback for scientific prose (L2): word pairs the field never writes.

`deai_register` asks whether a WORD belongs to the field. This axis asks
whether two words that each belong to the field have ever been put next to
each other by it. The two questions have opposite evidence, and that is why
they are two axes: refereed papers carry MORE unattested single words than
machine drafts (rank AUC 0.242, EVALUATION §23), because a real paper names
real instruments, coins real terms and cites real people; but they carry FEWER
unattested pairs of common words (AUC 0.855, length-controlled), because a
writer who has read the field reaches for the field's own phrases. A machine
draft assembles field words into combinations the field does not use --
`calibrated blur`, `controlled grid`, `physical cells`, `detector axes` -- and
the advisor who read such a draft wrote "I don't know what this means" at
exactly those places. This axis finds them.

The unit is the SENTENCE. A single novel pair is ordinary (a human sentence
carries one in four judged pairs at the median); a sentence whose novel
fraction sits in the field's upper tail is the one a reader stumbles on.
Calibration is leave-one-out on the field's own passage banks: a pair counts
as attested for the sentence it came from only if a second passage also
carries it, so the reference distribution is what a field sentence looks like
to a bank that has not seen it. The document-level novel fraction is reported
as evidence and never as a percentile, because the reference is built from
sentences and a document is not one (`deai_reference`'s invariant).

Each novel pair carries its own weight: under independence the expected number
of passages holding BOTH words is lambda = df(a) * df(b) / N, and exp(-lambda)
the chance that none does. That is co-presence, not adjacency (the bank knows
which passages contain a word, not where), so it orders the pairs a finding
shows -- two frequent words the corpus never joins first, two marginal words
last -- and it gates nothing; the gate is the sentence's novel fraction.

Nothing here is an authorship claim. A novel pair may be the paper's own
coinage, and the action text says so: a coined term keeps its pair and needs
its definition at first use.
"""

from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import extract_style as es  # noqa: E402 because the sibling resolves only once TOOLS_DIR is on sys.path
import deai_register as register  # noqa: E402 because the sibling resolves only once TOOLS_DIR is on sys.path
import deai_reference as reference  # noqa: E402 because the sibling resolves only once TOOLS_DIR is on sys.path
import deai_feedback as feedback  # noqa: E402 because the sibling resolves only once TOOLS_DIR is on sys.path
import cli_common  # noqa: E402 because the sibling resolves only once TOOLS_DIR is on sys.path

BANK_FILENAME = "collocation_bank.json"
BASELINE_FILENAME = "collocation_baseline.json"
FEATURE = "novel_fraction"
ADVISORY_PERCENTILE = 0.90
STRONG_PERCENTILE = 0.95
MIN_REFERENCE_N = reference.MIN_REFERENCE_N
# A word is judged as a partner only when the field uses it at this document
# frequency or above: the pair rule is about COMMON words the field never
# joins, and a rare word's pairs are rare for a reason the register axis
# already reports. On the 41,710-passage `wgl` bank this admits 11,286 words
# (`--calibrate --field wgl`, 2026-09-04).
COMMON_RATE = 2e-4
# A sentence with fewer judged pairs than this cannot carry a fraction worth a
# percentile: one novel pair in two is 0.5 and means nothing.
MIN_JUDGED = 4
# Function words are not partners: `of the` is not a collocation and `map of`
# would be attested in every passage.
STOPWORDS = frozenset("""a an the of in on at to for from by with without and
or but nor as is are was were be been being that this these those it its we
our they their which who whom whose what than then there here where when while
if so such not no yes also both either each any all some more most less least
very can could may might must shall should will would do does did has have had
into onto over under between among through during before after above below up
down out off about against per via one two three four five six seven eight
nine ten first second third new old same other another only just even still
yet already however therefore thus hence because since although though whereas
unless until whether math cite figure table section fig ref
actually every neither how rather along back across well much many few several
own again always never often usually almost nearly quite too later further
indeed instead otherwise thereby whereby wherein within toward towards around
beyond once twice upon none nothing something anything everything itself
themselves ourselves them him her his she you your i me us""".split())

ACTION = (
    "Say the relation each pair compresses in the field's own words: a "
    "modifier standing in for a procedure names the procedure, a verb used "
    "figuratively is replaced by what is actually done, and a noun pair that "
    "abbreviates a longer phrase is written out once. A term this paper coins "
    "keeps its pair and needs its definition at first use. Never change a "
    "claim to dissolve a pair.")

load_bank = reference.baseline_loader(BANK_FILENAME)
load_baseline = reference.baseline_loader(BASELINE_FILENAME)


# A pair is two words the writer put side by side. Punctuation, a bracketed
# placeholder (`[math]`, `[CITE]`), a dash, a slash, a sentence-internal full
# stop or a number between them means they were not: `yields, separate` is two
# clauses, `alpha/beta` two alternatives, `alpha 500 beta` two neighbours of a
# quantity, not a collocation. The bank is built with the same rule.
RE_PAIR_BREAK = re.compile(r"[,;:()\"“”./]|\d+|\[[^\]]*\]|--|—|–")


def content_pairs(sentence: str) -> list[tuple[str, str]]:
    """Adjacent content-word pairs within one punctuation-free run of a sentence."""
    pairs: list[tuple[str, str]] = []
    for run in RE_PAIR_BREAK.split(sentence):
        words = [register.normalize(word) for word in register.RE_WORD.findall(run)]
        pairs.extend((a, b) for a, b in zip(words, words[1:])
                     if a not in STOPWORDS and b not in STOPWORDS
                     and len(a) >= 3 and len(b) >= 3)
    return pairs


def _judged(pairs: Iterable[tuple[str, str]], bank: dict[str, Any]) -> list[tuple[str, str]]:
    common = bank["unigram_df"]
    return [pair for pair in pairs if pair[0] in common and pair[1] in common]


def _attestations(pair: tuple[str, str], bank: dict[str, Any]) -> int:
    return int(bank["pair_df"].get(f"{pair[0]} {pair[1]}", 0))


def judge_sentence(sentence: str, bank: dict[str, Any], *, own_passage: bool = False
                   ) -> dict[str, Any] | None:
    """Judged and novel pairs of one sentence against the bank, or None.

    `own_passage=True` is the leave-one-out reading used at calibration time: a
    pair the bank saw in exactly one passage is this passage's own, so it is
    treated as unseen.
    """
    # Distinct pairs: a sentence that writes `bias runs` twice made one choice.
    judged = _judged(dict.fromkeys(content_pairs(sentence)), bank)
    if len(judged) < MIN_JUDGED:
        return None
    floor = 2 if own_passage else 1
    novel = [pair for pair in judged if _attestations(pair, bank) < floor]
    return {"judged": len(judged), "novel": novel,
            FEATURE: len(novel) / len(judged)}


def expected_cooccurrence(pair: tuple[str, str], bank: dict[str, Any]) -> float:
    """lambda = df(a) df(b) / N: passages expected to hold BOTH words by chance.

    Co-presence in a passage, not adjacency: the bank records which passages
    contain a word, not where, so this is the independence expectation for the
    two words sharing a passage and e^-lambda the chance no passage does. It
    orders the pairs a finding shows (a decisive absence first) and never
    gates; the gate is the sentence's novel fraction against the reference.
    """
    unigram = bank["unigram_df"]
    return int(unigram[pair[0]]) * int(unigram[pair[1]]) / max(1, int(bank["n_passages"]))


def document_novelty(text: str, bank: dict[str, Any]) -> dict[str, Any]:
    """Novel-pair fraction over every judged pair of the document, as evidence.

    Token fraction (a repeated novel pair counts each time), so the figure does
    not fall with length the way a type count does. Reported in the axis status
    and by the evaluator; never turned into a percentile here.
    """
    judged = novel = 0
    for _start, _end, _bucket, block in reference.units(text):
        for sentence in es.sentences(es.latex_to_plain(block)):
            for pair in _judged(content_pairs(sentence), bank):
                judged += 1
                novel += _attestations(pair, bank) == 0
    return {"judged_pairs": judged, "novel_pairs": novel,
            FEATURE: novel / judged if judged else None}


def collocation_axis_status(field_profile_dir: Path | None,
                            text: str | None = None) -> dict[str, Any]:
    bank = load_bank(field_profile_dir)
    baseline = load_baseline(field_profile_dir)
    if bank is None or baseline is None:
        missing = BANK_FILENAME if bank is None else BASELINE_FILENAME
        return feedback.axis_status(
            "L2.collocation", "unmeasured",
            reason=f"{missing} is unavailable", detector="deai_collocation")
    usable = reference.usable_buckets(baseline, FEATURE, ADVISORY_PERCENTILE, high=True)
    evidence = None
    if text is not None:
        whole = document_novelty(text, bank)
        if whole[FEATURE] is not None:
            evidence = (f"document novel-pair fraction {whole[FEATURE]:.3f} over "
                        f"{whole['judged_pairs']} judged pairs (evidence, not a "
                        "percentile: the reference is per sentence)")
    if not usable:
        floor = (f"no section bucket reaches the {MIN_REFERENCE_N}-sentence "
                 "reference floor with spread above the gate")
        return feedback.axis_status(
            "L2.collocation", "degraded",
            reason="; ".join(part for part in (floor, evidence) if part),
            detector="deai_collocation")
    return feedback.axis_status("L2.collocation", "measured", reason=evidence,
                                detector="deai_collocation")


def _weighed(novel: list[tuple[str, str]], bank: dict[str, Any]) -> list[dict[str, Any]]:
    """Each novel pair with its chance expectation, most decisive absence first."""
    weighed = []
    for pair in novel:
        lam = expected_cooccurrence(pair, bank)
        weighed.append({"pair": f"{pair[0]} {pair[1]}",
                        "expected_copresent_passages": round(lam, 2),
                        "p_copresence_absent": float(f"{math.exp(-lam):.2e}")})
    weighed.sort(key=lambda item: -item["expected_copresent_passages"])
    return weighed


def _sentence_finding(sentence: str, verdict: dict[str, Any], percentile: float, *,
                      bank: dict[str, Any], bucket: str, ref: dict[str, Any],
                      span: tuple[int, int], path: str | Path | None,
                      field_profile_dir: Path | None) -> dict[str, Any]:
    reference_n = int(ref.get("n", 0))
    measured = reference_n >= MIN_REFERENCE_N
    strong = bool(measured and percentile > STRONG_PERCENTILE)
    n_passages = int(bank["n_passages"])
    pairs = _weighed(verdict["novel"], bank)
    excerpt = " ".join(sentence.split())
    frame = dict(kind="advisory", layer="L2", scope="sentence",
                 calibration_unit="sentence", detector="deai_collocation",
                 rule=f"collocation-novel:{bucket}", section=bucket, path=path,
                 line=span[0], end_line=span[1],
                 strength="strong" if strong else "ordinary",
                 measurement_status="measured" if measured else "degraded")
    policy = dict(provenance=BASELINE_FILENAME, unit="sentence",
                  n_passages=n_passages, common_rate=COMMON_RATE,
                  advisory_percentile=ADVISORY_PERCENTILE,
                  strong_percentile=STRONG_PERCENTILE)
    # Eight judged pairs is a full sentence's worth; below that the fraction
    # is coarse and the confidence says so. The paragraph cap applies on top.
    confidence = {"value": min(1.0, verdict["judged"] / 8.0),
                  "basis": (f"{verdict['judged']} judged pairs in one sentence; "
                            f"{bucket} reference n={reference_n}")}
    shown = ", ".join(f"'{item['pair']}'" for item in pairs[:4])
    message = (f"{bucket} sentence joins words this field does not join: "
               f"{len(verdict['novel'])} of {verdict['judged']} adjacent "
               f"content-word pairs are unattested in {n_passages:,} passages "
               f"(p{percentile * 100:.0f}): {shown}.")
    return feedback.make_finding(
        **frame, message=message, action=ACTION, confidence=confidence,
        normalized_distance=percentile - ADVISORY_PERCENTILE,
        evidence=[excerpt[:80], verdict["judged"], len(verdict["novel"])],
        observed={"sentence": excerpt[:160],
                  "judged_pairs": verdict["judged"],
                  "novel_pairs": len(verdict["novel"]),
                  FEATURE: round(verdict[FEATURE], 4),
                  "percentile": round(percentile, 4),
                  "pairs": pairs},
        reference=feedback.reference_block(field_profile_dir, bucket=bucket,
                                           n=reference_n, **policy))


def collocation_findings(text: str, field_profile_dir: Path | None,
                         path: str | Path | None = None) -> list[dict[str, Any]]:
    """One finding per sentence whose novel-pair fraction sits in the field's upper tail."""
    bank = load_bank(field_profile_dir)
    baseline = load_baseline(field_profile_dir)
    if bank is None or baseline is None:
        return []
    findings: list[dict[str, Any]] = []
    for start, end, bucket, block in reference.units(text):
        ref = baseline.get(bucket)
        if not isinstance(ref, dict):
            continue
        if not reference.resolves_gate(ref, FEATURE, ADVISORY_PERCENTILE, high=True):
            continue
        for sentence in es.sentences(es.latex_to_plain(block)):
            verdict = judge_sentence(sentence, bank)
            if verdict is None:
                continue
            percentile = reference.percentile_of(ref, FEATURE, verdict[FEATURE])
            if percentile is None or percentile <= ADVISORY_PERCENTILE:
                continue
            findings.append(_sentence_finding(
                sentence, verdict, percentile, bank=bank, bucket=bucket, ref=ref,
                span=(start, end), path=path, field_profile_dir=field_profile_dir))
    return findings


def _passages(field_profile_dir: Path) -> Iterable[tuple[str, str]]:
    """(bucket, text) for every human passage the field's banks hold."""
    for _label, bucket, text, _source in reference._bank_records(
            reference.passage_banks(field_profile_dir)):
        if text.strip():
            yield bucket, text


def build_bank(field_profile_dir: Path) -> dict[str, Any]:
    """Unigram and pair document frequency over the field's passage banks."""
    unigram: Counter[str] = Counter()
    pairs: Counter[str] = Counter()
    n_passages = 0
    for _bucket, text in _passages(field_profile_dir):
        n_passages += 1
        seen_words: set[str] = set()
        seen_pairs: set[str] = set()
        for sentence in es.sentences(es.latex_to_plain(text)):
            words = [register.normalize(w) for w in register.RE_WORD.findall(sentence)]
            seen_words.update(w for w in words if len(w) >= 3)
            seen_pairs.update(f"{a} {b}" for a, b in content_pairs(sentence))
        unigram.update(seen_words)
        pairs.update(seen_pairs)
    floor = COMMON_RATE * n_passages
    common = {word: df for word, df in unigram.items() if df >= floor}
    pair_df = {pair: df for pair, df in pairs.items()
               if all(part in common for part in pair.split(" "))}
    return {"n_passages": n_passages, "common_rate": COMMON_RATE,
            "n_common_words": len(common), "n_pairs": len(pair_df),
            "unigram_df": dict(sorted(common.items())),
            "pair_df": dict(sorted(pair_df.items()))}


def calibrate(field_profile_dir: Path) -> dict[str, Any]:
    """Write the pair bank, then the per-bucket sentence reference (leave-one-out)."""
    bank = build_bank(field_profile_dir)
    (field_profile_dir / BANK_FILENAME).write_text(
        json.dumps(bank, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    collected: dict[str, list[float]] = {}
    for bucket, text in _passages(field_profile_dir):
        for sentence in es.sentences(es.latex_to_plain(text)):
            verdict = judge_sentence(sentence, bank, own_passage=True)
            if verdict is not None:
                collected.setdefault(bucket, []).append(verdict[FEATURE])
    baseline = {bucket: {"n": len(values), "unit": "sentence",
                         "sources": ["leave-one-out over the passage banks"],
                         "percentiles": {FEATURE: reference.quantiles(values)}}
                for bucket, values in collected.items()}
    (field_profile_dir / BASELINE_FILENAME).write_text(
        json.dumps(baseline, indent=2, sort_keys=True), encoding="utf-8")
    return {"bank": {key: bank[key] for key in
                     ("n_passages", "n_common_words", "n_pairs")},
            "baseline": baseline}


def _written(result: dict[str, Any], field_profile_dir: Path) -> str:
    bank = result["bank"]
    counts = ", ".join(f"{bucket}={ref['n']}"
                       for bucket, ref in sorted(result["baseline"].items()))
    return (f"bank written: {field_profile_dir / BANK_FILENAME} "
            f"({bank['n_passages']} passages, {bank['n_common_words']} common words, "
            f"{bank['n_pairs']} pairs); reference: "
            f"{field_profile_dir / BASELINE_FILENAME} ({counts})")


def _report(text: str, field_dir: Path | None, path: str | Path) -> dict[str, Any]:
    findings = collocation_findings(text, field_dir, path)
    status = collocation_axis_status(field_dir, text)
    return feedback.build_report(path=path, findings=findings, axes=[status])


def main(argv: list[str] | None = None) -> int:
    return cli_common.axis_main(__doc__, argv, tool="deai_collocation",
                                calibrate=calibrate, summary=_written,
                                report=_report, render=feedback.render_text)


if __name__ == "__main__":
    raise SystemExit(main())
