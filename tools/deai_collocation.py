"""Field-collocation feedback (L2): word pairs the field never writes; --glossary lists the recurring ones.

`deai_register` asks whether a WORD belongs to the field. This axis asks
whether two words that each belong to the field have ever been put next to
each other by it. The two questions have opposite evidence, and that is why
they are two axes: refereed papers carry MORE unattested single words than
machine drafts (rank AUC 0.174 under the v0.36.2 projection, EVALUATION
§23.1), because a real paper names real instruments, coins real terms and
cites real people; but they carry FEWER unattested pairs of common words
(document novel-pair fraction, machine over held-out AUC 0.704, §23.2),
because a writer who has read the field reaches for the field's own phrases.
A machine
draft assembles field words into combinations the field does not use --
`binned kernel`, `smoothed boundary`, say -- and the advisor who read such a
draft wrote "I don't know what this means" at exactly such places. This axis
finds them.

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
UNIT = "sentence"
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
    """The axis status, `degraded` with its reasons where it did not measure.

    `text` is what makes the status about THIS document: a paragraph in the
    `unknown` bucket (no heading, or a topic heading) has no reference and is
    skipped, and without the text the status could only describe the profile
    and reported `measured` over a document it had skipped whole.
    """
    bank = load_bank(field_profile_dir)
    baseline = load_baseline(field_profile_dir)
    if bank is None or baseline is None:
        missing = BANK_FILENAME if bank is None else BASELINE_FILENAME
        return feedback.axis_status(
            "L2.collocation", "unmeasured",
            reason=f"{missing} is unavailable", detector="deai_collocation")
    usable = reference.usable_buckets(baseline, FEATURE, ADVISORY_PERCENTILE,
                                      high=True, unit=UNIT)
    spans = None if text is None else reference.units(text)
    reasons = [None if usable else
               (f"no section bucket reaches the {MIN_REFERENCE_N}-sentence "
                "reference floor with spread above the gate"),
               reference.unit_reason(baseline, UNIT, spans)]
    evidence = None
    if text is not None:
        reasons.append(reference.unbucketed_reason(spans, "paragraph"))
        whole = document_novelty(text, bank)
        if whole[FEATURE] is not None:
            evidence = (f"document novel-pair fraction {whole[FEATURE]:.3f} over "
                        f"{whole['judged_pairs']} judged pairs (evidence, not a "
                        "percentile: the reference is per sentence)")
    return feedback.axis_status(
        "L2.collocation", "degraded" if any(reasons) else "measured",
        reason="; ".join(part for part in (*reasons, evidence) if part) or None,
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
    """One sentence's finding; `span` is the sentence's own line range."""
    reference_n = int(ref.get("n", 0))
    measured = reference_n >= MIN_REFERENCE_N
    strong = bool(measured and percentile > STRONG_PERCENTILE)
    n_passages = int(bank["n_passages"])
    pairs = _weighed(verdict["novel"], bank)
    excerpt = " ".join(sentence.split())
    frame = dict(kind="advisory", layer="L2", scope="sentence",
                 calibration_unit=UNIT, detector="deai_collocation",
                 rule=f"collocation-novel:{bucket}", section=bucket, path=path,
                 line=span[0], end_line=span[1],
                 strength="strong" if strong else "ordinary",
                 measurement_status="measured" if measured else "degraded")
    policy = dict(provenance=BASELINE_FILENAME, unit=UNIT,
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
    for start, _end, bucket, block in reference.units(text):
        ref = baseline.get(bucket)
        # A bucket under the sample floor still speaks, as a degraded finding;
        # one built at another unit does not speak at all (the status says why).
        if not isinstance(ref, dict) or not reference.unit_matches(ref, UNIT):
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
                span=reference.sentence_lines(block, start, sentence), path=path,
                field_profile_dir=field_profile_dir))
    return findings


# ---- the glossary reading (document scope) ----------------------------------
GLOSSARY_MIN_USES = 2
GLOSSARY_RULE = "collocation-glossary"
# A definition cue is read only in the words AFTER the pair, or as a
# parenthesis opening right after it: `the shear threshold, which we call the
# floor` and `the shear threshold (hereafter ...)` gloss the pair, while a
# `(Fig. 1)` or a `, the` anywhere else in the sentence does not -- read over
# the whole sentence, those marked one pair in six as defined in a manuscript
# under review.
RE_GLOSS_CUE = re.compile(
    r"\b(?:we call|called|which we call|define[sd]? as|defined|denote[sd]?|"
    r"that is|which is|i\.e\.|namely|meaning|hereafter)\b",
    re.IGNORECASE)
GLOSS_WINDOW_WORDS = 8
GLOSSARY_ACTION = (
    "A pair the field never joins that this manuscript uses more than once is "
    "most likely its own term, not a slip: the advisor's 'this is jargon and "
    "won't make sense to an astronomer' lands on exactly these. If it is the "
    "manuscript's term, give it its definition (or a plain gloss) where it is "
    "first used, or replace it by the field's own word; if it is ordinary "
    "phrasing that the corpus happens to lack, leave it.")


def _pair_pattern(pair: tuple[str, str]) -> str:
    """The pair as written: each stem with any suffix, the first with its 's."""
    return rf"\b{re.escape(pair[0])}(?:'s)?\w*\s+{re.escape(pair[1])}\w*"


def _line_of_pair(block: str, start: int, pair: tuple[str, str]) -> int:
    """Line of the pair's first appearance in the raw unit, else the unit's start.

    The pair words are normalized stems (a possessive 's is stripped by
    `register.normalize`), so each is matched with any suffix and the first
    may carry its 's; the fallback keeps the finding anchored to the unit
    when a macro or a line break sits between the words in the source.
    """
    hit = re.search(_pair_pattern(pair), block, re.IGNORECASE)
    return start + block[:hit.start()].count("\n") if hit else start


def glossed(sentence: str, pair: tuple[str, str]) -> bool:
    """Whether the sentence defines the pair where it uses it.

    A parenthesis opening right after the pair, or a cue among the
    `GLOSS_WINDOW_WORDS` words that follow it; a cue before the pair or later
    in the sentence is about something else.
    """
    hit = re.search(_pair_pattern(pair), sentence, re.IGNORECASE)
    if hit is None:
        return False
    after = sentence[hit.end():]
    if re.match(r"\s*\(", after):
        return True
    window = " ".join(after.split()[:GLOSS_WINDOW_WORDS])
    return bool(RE_GLOSS_CUE.search(window))


def glossary_axis_status(field_profile_dir: Path | None) -> dict[str, Any]:
    """The status of the glossary reading: it needs the bank and nothing else.

    No percentile is read, so the sentence reference is not consulted and
    its floor cannot degrade this reading; reporting `collocation_axis_status`
    beside a glossary list put "unmeasured" next to findings that had been
    measured against every passage of the bank.
    """
    bank = load_bank(field_profile_dir)
    if bank is None:
        return feedback.axis_status(
            "L2.collocation", "unmeasured",
            reason=f"{BANK_FILENAME} is unavailable", detector="deai_collocation")
    return feedback.axis_status(
        "L2.collocation", "measured",
        reason=(f"glossary reading: pairs unattested in {int(bank['n_passages']):,} "
                "passages, document scope, no percentile"),
        detector="deai_collocation")


def glossary_findings(text: str, field_profile_dir: Path | None,
                      path: str | Path | None = None) -> list[dict[str, Any]]:
    """Recurring unattested pairs, read as the manuscript's own terms.

    The sentence gate of `collocation_findings` asks whether ONE sentence
    stumbles. This reading aggregates every judged sentence of the document
    and lists the pairs the field never joins that the manuscript uses at
    least GLOSSARY_MIN_USES times: a coinage recurs, a figure of speech does
    not. Each candidate carries its uses (every occurrence, a sentence that
    joins the pair twice counting twice), the sections it appears in, its first-use
    line (the pair's first appearance in the raw unit, else the unit's start)
    and whether that sentence glosses it where it uses it (`glossed`), so the
    author can add the definition at first use or choose the field's word.
    No sentence-level gate and no percentile: this is a list to walk, not a
    verdict, and it is off by default in the unified linter.
    """
    bank = load_bank(field_profile_dir)
    if bank is None:
        return []
    seen: dict[str, dict[str, Any]] = {}
    for start, _end, bucket, block in reference.units(text):
        for sentence in es.sentences(es.latex_to_plain(block)):
            excerpt = " ".join(sentence.split())
            occurrences = Counter(content_pairs(sentence))
            for pair in _judged(occurrences, bank):
                if _attestations(pair, bank) != 0:
                    continue
                key = f"{pair[0]} {pair[1]}"
                item = seen.get(key)
                if item is None:
                    item = seen[key] = {
                        "pair": key, "uses": 0, "sections": [],
                        "first_line": _line_of_pair(block, start, pair),
                        "first_section": bucket,
                        "first_sentence": excerpt[:160],
                        "glossed_at_first_use": glossed(excerpt, pair),
                        "expected_copresent_passages": round(
                            expected_cooccurrence(pair, bank), 2)}
                item["uses"] += occurrences[pair]
                if bucket not in item["sections"]:
                    item["sections"].append(bucket)
    n_passages = int(bank["n_passages"])
    findings: list[dict[str, Any]] = []
    for key, item in sorted(seen.items(), key=lambda kv: (-kv[1]["uses"], kv[0])):
        if item["uses"] < GLOSSARY_MIN_USES:
            continue
        cue = ("a definition cue follows it there" if item["glossed_at_first_use"]
               else "no definition cue follows it there")
        message = (f"'{key}' is joined {item['uses']} times in the manuscript "
                   f"({', '.join(item['sections'])}) and in none of the field's "
                   f"{n_passages:,} passages; first use at line {item['first_line']}, {cue}.")
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2", scope="document",
            calibration_unit="document", detector="deai_collocation",
            rule=f"{GLOSSARY_RULE}:{item['first_section']}",
            section=item["first_section"], path=path, line=item["first_line"],
            strength="ordinary", measurement_status="measured",
            message=message, action=GLOSSARY_ACTION,
            confidence={"value": min(1.0, item["uses"] / 4.0),
                        "basis": f"{item['uses']} uses; a term recurs, a phrasing does not"},
            normalized_distance=0.0,
            evidence=[key, item["uses"], item["first_line"]],
            observed=item,
            reference=feedback.reference_block(
                field_profile_dir, bucket=item["first_section"], n=n_passages,
                provenance=BANK_FILENAME, unit="document",
                min_uses=GLOSSARY_MIN_USES)))
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


def calibrate(field_profile_dir: Path) -> dict[str, Any] | None:
    """Write the pair bank, then the per-bucket sentence reference (leave-one-out).

    None, with nothing written, when the banks hold no passage: an empty pair
    bank is not a calibration, and `axis_main` reports exit 2.
    """
    bank = build_bank(field_profile_dir)
    if not bank["n_passages"]:
        return None
    (field_profile_dir / BANK_FILENAME).write_text(
        json.dumps(bank, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    collected: dict[str, list[float]] = {}
    for bucket, text in _passages(field_profile_dir):
        for sentence in es.sentences(es.latex_to_plain(text)):
            verdict = judge_sentence(sentence, bank, own_passage=True)
            if verdict is not None:
                collected.setdefault(bucket, []).append(verdict[FEATURE])
    baseline = {bucket: {"n": len(values), "unit": UNIT,
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


def _glossary_report(text: str, field_dir: Path | None, path: str | Path) -> dict[str, Any]:
    findings = glossary_findings(text, field_dir, path)
    return feedback.build_report(path=path, findings=findings,
                                 axes=[glossary_axis_status(field_dir)])


def main(argv: list[str] | None = None) -> int:
    return cli_common.axis_main(
        __doc__, argv, tool="deai_collocation", calibrate=calibrate,
        summary=_written, report=_report, render=feedback.render_text,
        extra_arguments=lambda parser: parser.add_argument(
            "--glossary", action="store_true",
            help="list the recurring unattested pairs (document scope) instead "
                 "of the per-sentence findings"),
        check=lambda args: ("--glossary reads a document; it cannot be combined "
                            "with --calibrate" if args.glossary and args.calibrate
                            else None),
        report_for=lambda args: _glossary_report if args.glossary else _report)


if __name__ == "__main__":
    raise SystemExit(main())
