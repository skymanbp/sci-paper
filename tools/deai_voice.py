"""Score paragraphs with the optional learned field-similarity model.

The legacy training labels distinguish curated field prose from generated
negative examples. Their classifier probability is exposed only as a compatibility
score: it prioritizes inspection but does not estimate authorship. A bundle without
an explicit calibrated operating point is degraded evidence, and degraded evidence
is surfaced as rank-based triage (lowest-scoring paragraphs), never through a
universal probability cutoff.

  voice_score(text, field_dir) -> compatibility score in [0, 1], or None
      without a bundle or without the surprisal runtime the features need
  paragraph_hits(text, field_dir) -> compatibility tuple advisories

The score is never a paper gate or detector-evasion objective. Rewrite candidates
must first satisfy deterministic scientific-fidelity eligibility.

CLI:  python tools/deai_voice.py draft.tex --field wgl
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first
import deai_features as df   # noqa: E402  resolves only after the sys.path insert
import deai_feedback as feedback  # noqa: E402  shared finding contract
import deai_oracle as do  # noqa: E402  the surprisal runtime probe
import deai_reference as reference  # noqa: E402  the shared paragraph sweep
import extract_style as es   # noqa: E402  same reason

TRIAGE_RANK_COUNT = 3    # degraded mode surfaces this many lowest-ranked paragraphs
_MODEL_CACHE: dict = {}


def load_voice_model(field_profile_dir: Path | None):
    if field_profile_dir is None:
        return None
    key = str(field_profile_dir)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    path = field_profile_dir / "voice_model.joblib"
    if not path.exists():
        _MODEL_CACHE[key] = None
        return None
    try:
        # Imported inside the guard because joblib is an OPTIONAL dependency
        # (requirements.txt): with a bundle present but joblib uninstalled, a
        # module-level import raised ModuleNotFoundError straight through the
        # caller instead of degrading the L3 axis to unavailable.
        import joblib
        bundle = joblib.load(path)
    except Exception as error:
        # A truncated or corrupt bundle, or a missing joblib, must degrade to
        # "unavailable" so the axis reports unmeasured with a reason, never
        # crash the caller.
        print(f"[deai_voice] unreadable voice_model.joblib ({error}); "
              "treating the L3 axis as unavailable", file=sys.stderr)
        _MODEL_CACHE[key] = None
        return None
    # Feature-provenance guard, mirroring the training-side cache guard: a
    # bundle trained against a different feature list or schema would score
    # silently wrong (reorder) or crash (count change). Refuse to score it.
    bundle_names = list(bundle.get("feature_names") or [])
    bundle_schema = bundle.get("feature_schema")
    if bundle_names != df.FEATURE_NAMES or (
            bundle_schema is not None
            and bundle_schema != df.FEATURE_SCHEMA_VERSION):
        print("[deai_voice] voice_model.joblib feature provenance "
              f"({bundle_schema or 'unversioned'}, {len(bundle_names)} features) "
              "does not match the installed feature schema "
              f"({df.FEATURE_SCHEMA_VERSION}, {len(df.FEATURE_NAMES)} features); "
              "retrain with tools/train_voice_model.py", file=sys.stderr)
        _MODEL_CACHE[key] = None
        return None
    _MODEL_CACHE[key] = bundle
    return bundle


def bundle_measured(bundle) -> bool:
    """True only for a bundle with a measured, calibrated operating point."""
    return bool(
        bundle
        and "operating_point" in bundle
        and bundle.get("measurement_status") == "measured"
    )


def _positive_class_probability(bundle, feats_vec) -> float:
    """Return probability of the bundle's curated-reference class."""
    import numpy as np
    clf, scaler = bundle["clf"], bundle["scaler"]
    x = scaler.transform(np.asarray([feats_vec], float))
    column = list(clf.classes_).index(1)
    return float(clf.predict_proba(x)[0, column])


def runtime_reason() -> str | None:
    """Why no paragraph can be scored, or None when the runtime is present.

    The feature vector the bundle reads carries three token-surprisal entries,
    and `deai_features.features_vector` raises when the optional
    transformers/torch runtime that produces them is missing. Every entry
    point here probes first, so the L3 axis reports `unmeasured` with this
    reason instead of propagating that RuntimeError into the linter, the
    rewrite ranker or `--scores`.
    """
    available, reason = do.model_runtime_available()
    if available:
        return None
    return (f"{reason}; the bundle's features include token surprisal, so no "
            "paragraph can be scored")


def voice_score(text: str, field_profile_dir: Path | None,
                model_name: str | None = None, centroid=None) -> float | None:
    """Return a field-similarity compatibility score, or None if unavailable.

    None without a bundle and None without the surprisal runtime: the caller's
    status names which (`voice_axis_status`), and a rewrite ranker reading
    None weighs the term at nothing rather than at a nominal 0.0.
    """
    bundle = load_voice_model(field_profile_dir)
    if bundle is None or runtime_reason() is not None:
        return None
    model_name = model_name or bundle.get("model", do.DEFAULT_MODEL)
    if centroid is None and field_profile_dir is not None:
        centroid = df.corpus_centroid(field_profile_dir)
    vec = df.features_vector(text, field_profile_dir=field_profile_dir,
                             model_name=model_name, centroid=centroid)
    return _positive_class_probability(bundle, vec)


def voice_axis_status(field_profile_dir: Path | None) -> dict:
    bundle = load_voice_model(field_profile_dir)
    if bundle is None:
        return feedback.axis_status(
            "L3.voice", "unmeasured", reason="voice_model.joblib is unavailable",
            detector="deai_voice")
    reason = runtime_reason()
    if reason is not None:
        return feedback.axis_status("L3.voice", "unmeasured", reason=reason,
                                    detector="deai_voice")
    if not bundle_measured(bundle):
        return feedback.axis_status(
            "L3.voice", "degraded",
            reason="model bundle has no measured calibrated operating point; "
                   "rank-based triage only, no threshold findings",
            detector="deai_voice")
    return feedback.axis_status("L3.voice", "measured", detector="deai_voice")


def _finding_for(block_score: float, *, bucket: str, raw_label: str,
                 paragraph_start: int, paragraph_end: int,
                 path: str | Path | None, bundle, model_name: str,
                 calibrated: bool, distance: float, message: str) -> dict:
    return feedback.make_finding(
        kind="advisory", layer="L3", rule=f"voice-distance:{bucket}",
        scope="paragraph", calibration_unit="paragraph",
        line=paragraph_start, end_line=paragraph_end,
        section=raw_label, path=path, detector="deai_voice",
        detector_version=bundle.get("feature_schema") or "legacy-bundle",
        calibration_asset="voice_model_evaluation.json" if calibrated else None,
        measurement_status="measured" if calibrated else "degraded",
        strength="strong" if calibrated else "ordinary",
        observed={"compatibility_score": block_score},
        reference={"operating_point": (float(bundle["operating_point"])
                                       if calibrated else None),
                   "model": model_name,
                   "model_version": bundle.get("feature_cache_fingerprint"),
                   "evaluation_status": bundle.get(
                       "measurement_status", "degraded"),
                   "evaluation_record": "voice_model_evaluation.json",
                   "provenance": "voice_model.joblib"},
        normalized_distance=distance,
        confidence={"value": float(bundle.get("calibration_confidence", 0.5)),
                    "basis": ("model bundle metadata" if calibrated
                              else "uncalibrated rank-based triage")},
        message=message,
        action="Inspect L1/L2 evidence and rebuild the paragraph only if the "
               "rewrite preserves all scientific invariants.",
        evidence=round(block_score, 8),
    )


def voice_findings(text: str, field_profile_dir: Path | None,
                   threshold: float | None = None,
                   path: str | Path | None = None) -> list[dict]:
    """Structured L3 triage findings.

    Calibrated bundle: paragraphs below the bundle's measured operating point.
    Explicit ``threshold``: an author-chosen review point, applied as given.
    Degraded bundle with no explicit threshold: the ``TRIAGE_RANK_COUNT``
    lowest-scoring paragraphs are surfaced as rank-based triage; no universal
    probability cutoff is invented.
    """
    bundle = load_voice_model(field_profile_dir)
    if bundle is None or runtime_reason() is not None:
        return []
    calibrated = bundle_measured(bundle)
    model_name = bundle.get("model", do.DEFAULT_MODEL)
    centroid = df.corpus_centroid(field_profile_dir)
    scored: list[dict] = []
    for paragraph_start, paragraph_end, raw_label, bucket, block in reference.paragraphs(text):
        if len(es.words(es.latex_to_plain(block))) < 30:
            continue
        score = voice_score(block, field_profile_dir, model_name, centroid)
        if score is None:
            continue
        scored.append({"score": score, "bucket": bucket,
                       "raw_label": raw_label,
                       "start": paragraph_start, "end": paragraph_end})
    if not scored:
        return []

    findings: list[dict] = []
    if calibrated or threshold is not None:
        review_point = (float(bundle["operating_point"]) if calibrated
                        else float(threshold))
        basis = ("measured operating point" if calibrated
                 else "author-chosen review point")
        for item in scored:
            if item["score"] >= review_point:
                continue
            findings.append(_finding_for(
                item["score"], bucket=item["bucket"],
                raw_label=item["raw_label"], paragraph_start=item["start"],
                paragraph_end=item["end"], path=path, bundle=bundle,
                model_name=model_name, calibrated=calibrated,
                distance=review_point - item["score"],
                message=(f"Learned field-similarity score {item['score']:.2f} "
                         f"is below the {basis} {review_point:.2f}; this is "
                         "triage evidence, not an authorship claim.")))
        return findings

    # Degraded, no author threshold: rank-based triage relative to the
    # document itself. No probability cutoff exists or is implied.
    ranked = sorted(scored, key=lambda item: item["score"])
    document_median = ranked[len(ranked) // 2]["score"]
    for rank_index, item in enumerate(ranked[:TRIAGE_RANK_COUNT], 1):
        findings.append(_finding_for(
            item["score"], bucket=item["bucket"], raw_label=item["raw_label"],
            paragraph_start=item["start"], paragraph_end=item["end"],
            path=path, bundle=bundle, model_name=model_name, calibrated=False,
            distance=max(0.0, document_median - item["score"]),
            message=(f"Uncalibrated triage: field-similarity "
                     f"{item['score']:.2f} ranks {rank_index}/{len(ranked)} "
                     f"lowest in this document (median {document_median:.2f}); "
                     "no calibrated threshold exists and this is not an "
                     "authorship claim.")))
    return findings


def paragraph_hits(text: str, field_profile_dir: Path | None,
                   threshold: float | None = None) -> list[tuple[int, str, str]]:
    return feedback.tuple_hits(voice_findings(text, field_profile_dir, threshold))


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()
    p = cli_common.field_parser(__doc__)
    p.add_argument("file", type=Path)
    p.add_argument("--voice-threshold", type=float, default=None,
                   help="explicit author-chosen review point; default is the "
                        "bundle's measured operating point, or rank-based "
                        "triage when the bundle is uncalibrated")
    p.add_argument("--scores", action="store_true",
                   help="print the compatibility score for every paragraph")
    args = p.parse_args(argv)
    # No profile (no `--field` and not exactly one field) is the same exit 2
    # as a profile without a bundle; `profile_root / None` was a TypeError.
    field_dir = cli_common.optional_field_dir(args, tool="deai_voice")
    if field_dir is None or load_voice_model(field_dir) is None:
        print(f"[deai_voice] no voice_model.joblib in {field_dir or '<field>'}; "
              "train with `python tools/train_voice_model.py --field "
              f"{field_dir.name if field_dir else '<field>'}`.", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    if args.scores:
        status = voice_axis_status(field_dir)
        if status["status"] == "unmeasured":
            # The same line the report prints: without the surprisal runtime
            # there is no score to list, and the reason is the output.
            print(f"axis {status['axis']}: unmeasured: {status['reason']}")
            return 0
        # The same sweep the findings use, keyed by source lines, so a score
        # can be matched to a finding; a blank-line split of the raw text
        # numbered different paragraphs and its indices matched nothing.
        centroid = df.corpus_centroid(field_dir)
        for start, end, _label, _bucket, block in reference.paragraphs(text):
            score = voice_score(block, field_dir, None, centroid)
            if score is not None:
                print(f"  L{start}-{end} field_similarity={score:.3f}")
        return 0
    report = feedback.build_report(
        path=args.file,
        findings=voice_findings(text, field_dir, args.voice_threshold, args.file),
        axes=[voice_axis_status(field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
