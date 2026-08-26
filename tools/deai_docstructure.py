"""Document-level paragraph and section shape feedback (L2).

This tool measures repeated rhetorical geometry, not repeated subject matter.
Calibration treats each complete source document as one observation to avoid
paragraph-level pseudoreplication.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deai_features as features  # noqa: E402  sibling import after path setup
import deai_feedback as feedback  # noqa: E402  shared finding contract
import deai_metrics as metrics  # noqa: E402  canonical section/paragraph ranges
import deai_structure as structure  # noqa: E402  sentence template features
import extract_style as es  # noqa: E402  canonical LaTeX cleanup/tokenizer

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"
BASELINE_NAME = "docstructure_baseline.json"
MIN_WORDS = 30
MIN_SECTIONS = 3
MIN_PARAGRAPHS_PER_SECTION = 2

# Document-shape measurement, the dispersion manifold, the conformal operating
# points and the baseline builder moved to deai_docshape.py on 2026-08-25 (this
# file could no longer be edited at its size). Re-exported because sibling tools
# and tests reach them as dds.<name>; unused in this module by design, which is
# what the F401 waiver records.
from deai_docshape import (  # noqa: F401 -- re-export, unused here by design
    BASELINE_NAME, CONFORMAL_ALPHA, CONFORMAL_SEED, CONFORMAL_STRATA,
    CONFORMAL_TRAIN_FRACTION, DISPERSION_FEATURE_NAMES,
    DISPERSION_HIGH_PERCENTILE, DISPERSION_LOW_PERCENTILE, DISPERSION_STAT,
    MANIFOLD_CLIP, MANIFOLD_EPS, MANIFOLD_PERCENTILE, MANIFOLD_RIDGE,
    METRIC_NAMES, MIN_CAL_PER_STRATUM, MIN_MANIFOLD_DOCUMENTS,
    MIN_PARAGRAPHS_PER_SECTION, MIN_SECTIONS, MIN_WORDS, ROLE_FACTORS,
    ROLE_LOW_PERCENTILE, ROLE_SCORING_FACTORS, _MATH_MARKER_RE,
    _bootstrap_quantile_ci, _conformal_p, _cosine, _fit_center_cov,
    _leave_one_document_out_low_flag_rate, _leave_one_out_flag_rate,
    _length_stratum, _log_ratio_vector, _mahalanobis, _mat_inv, _mean_vector,
    _pairwise_similarity, _paragraph_modelfree, _percentile, _quantile,
    _shape_vector, _stratum_calibration, calibrate, document_role_coupling,
    document_shape, fit_dispersion_manifold, manifold_distance,
    manifold_operating_point,
)

def load_baseline(field_profile_dir: Path | None) -> dict[str, Any] | None:
    if field_profile_dir is None:
        return None
    path = field_profile_dir / BASELINE_NAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def docstructure_axis_status(text: str, field_profile_dir: Path | None
                            ) -> dict[str, Any]:
    shape = document_shape(text)
    if shape["status"] != "measured":
        return feedback.axis_status("L2.document_structure", "unmeasured",
                                    reason=shape["reason"],
                                    detector="deai_docstructure")
    if load_baseline(field_profile_dir) is None:
        return feedback.axis_status(
            "L2.document_structure", "unmeasured",
            reason="docstructure_baseline.json is unavailable",
            detector="deai_docstructure",
        )
    return feedback.axis_status("L2.document_structure", "measured",
                                detector="deai_docstructure")


def document_findings(text: str, field_profile_dir: Path | None,
                      path: str | Path | None = None) -> list[dict[str, Any]]:
    shape = document_shape(text)
    baseline = load_baseline(field_profile_dir)
    if shape["status"] != "measured" or baseline is None:
        return []
    findings = []
    section_label = "(document)"
    for metric_name in METRIC_NAMES:
        observed = shape["metrics"].get(metric_name)
        reference = baseline.get("metrics", {}).get(metric_name, {})
        values = reference.get("values", [])
        if observed is None or not values:
            continue
        percentile = _percentile(values, float(observed))
        operating_point = float(baseline.get("strong_percentile", 0.95))
        if percentile < operating_point:
            continue
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2", rule=f"document-shape:{metric_name}",
            scope="document", calibration_unit="document", line=1, section=section_label, path=path,
            detector="deai_docstructure", measurement_status="measured",
            strength="strong", strong_advisory=True,
            observed={"value": observed, "empirical_percentile": percentile,
                      "n_sections": shape["n_sections"],
                      "n_paragraphs": shape["n_paragraphs"]},
            reference={"n_documents": baseline["n_documents"],
                       "strong_percentile": operating_point,
                       "strong_threshold": reference.get("strong_threshold"),
                       "bootstrap_95_ci": reference.get("bootstrap_95_ci"),
                       "leave_one_document_out_flag_rate": reference.get(
                           "leave_one_document_out_flag_rate"),
                       "provenance": BASELINE_NAME},
            normalized_distance=percentile - operating_point,
            confidence={"value": min(1.0, baseline["n_documents"] / 30.0),
                        "basis": f"{baseline['n_documents']} complete reference documents"},
            message=(f"Document-level {metric_name.replace('_', ' ')} is "
                     f"{observed:.3f}, at empirical percentile {percentile:.3f} "
                     "of the complete-document reference."),
            action=("Inspect repeated paragraph and section shapes; vary only "
                    "needless rhetorical symmetry while preserving logical organization."),
            evidence=[metric_name, round(float(observed), 8)],
        ))
    # Dispersion-band findings: human documents occupy a per-feature BAND of
    # cross-paragraph dispersion. Below the low tail = over-uniform (the
    # natural-AI direction); above the high tail = over-dispersed (measured on
    # text written to force raggedness, which overshoots the band). Held-out
    # validation: one-sided scoring is at chance against a shape adversary;
    # the band view recovers it (EVALUATION.md section 9).
    dispersion = shape.get("dispersion", {})
    # Joint manifold statistic first: ONE calibrated aggregate. When it is
    # available, the correlated per-feature band flags demote to ordinary
    # context so one uniform document is not reported as ~8 strong findings.
    manifold = baseline.get("dispersion_manifold")
    flat_row = {name: dispersion[name][DISPERSION_STAT]
                for name in dispersion
                if dispersion.get(name, {}).get(DISPERSION_STAT) is not None}
    per_feature_strength = "ordinary"
    conformal = baseline.get("conformal")
    if not manifold:
        per_feature_strength = "strong"
    else:
        operating = manifold_operating_point(baseline, flat_row,
                                             shape["n_paragraphs"])
        if operating is not None:
            distance = operating["distance"]
            p_value = operating["p_value"]
            if operating["alpha"] is not None:
                alpha = operating["alpha"]
                cal_basis = operating["calibration_basis"]
                n_cal = operating["n_calibration"]
                flagged = p_value <= alpha
                op_reference = {"operating_point": operating["operating_point"],
                                "alpha": alpha,
                                "n_calibration": n_cal,
                                "calibration_basis": cal_basis,
                                "n_train": operating.get("n_train"),
                                "provenance": BASELINE_NAME}
                op_margin = alpha - p_value
                op_confidence = {
                    "value": min(1.0, n_cal / 100.0),
                    "basis": (f"split-conformal p against {n_cal} held-out "
                              f"human papers ({cal_basis}); P(false flag) <= "
                              f"{alpha:g} finite-sample for exchangeable "
                              "human documents")}
                op_clause = (f"conformal p = {p_value:.4f} <= alpha {alpha:g} "
                             f"against {n_cal} held-out human papers "
                             f"({cal_basis})")
            else:  # legacy baseline without a conformal block
                flagged = operating["flagged"]
                op_reference = {"operating_point": "in-sample percentile",
                                "n_documents": manifold["n_documents"],
                                "threshold": manifold["threshold"],
                                "percentile": manifold["percentile"],
                                "leave_one_document_out_flag_rate": manifold[
                                    "leave_one_document_out_flag_rate"],
                                "provenance": BASELINE_NAME}
                op_margin = distance - float(manifold["threshold"])
                op_confidence = {
                    "value": min(1.0, manifold["n_documents"] / 100.0),
                    "basis": (f"{manifold['n_documents']} complete reference "
                              "documents; joint band distance in log "
                              "dispersion-ratio space")}
                op_clause = (f"reference {manifold['percentile']:.0%} "
                             f"threshold {float(manifold['threshold']):.2f}")
            if flagged:
                findings.append(feedback.make_finding(
                    kind="advisory", layer="L2",
                    rule="document-dispersion-manifold",
                    scope="document", calibration_unit="document", line=1, section=section_label, path=path,
                    detector="deai_docstructure",
                    detector_version="sci-paper.docstructure-baseline.v2",
                    calibration_asset=BASELINE_NAME,
                    measurement_status="measured", strength="strong",
                    observed={"mahalanobis_distance": distance,
                              "p_value": p_value,
                              "n_sections": shape["n_sections"],
                              "n_paragraphs": shape["n_paragraphs"]},
                    reference=op_reference,
                    normalized_distance=op_margin,
                    confidence=op_confidence,
                    message=(f"The document's joint cross-paragraph dispersion "
                             f"sits {distance:.2f} Mahalanobis units from the "
                             f"human center ({op_clause}): its paragraph-shape "
                             "variation pattern departs from the human band as "
                             "a whole. Per-feature detail follows as ordinary "
                             "context; this is a measured deviation, not an AI "
                             "verdict."),
                    action=("Read the per-feature context findings to see which "
                            "shape dimensions depart, then adjust only where the "
                            "argument permits."),
                    evidence=["manifold", round(distance, 6)],
                ))
    # Role-coupled dispersion (orthogonal to the manifold): humans vary
    # paragraph shape where the argument demands it, so shape variance is
    # partly explained by rhetorical role. Both AI failure modes — uniform
    # AND forced-ragged — decouple shape from role; the shape adversary that
    # narrows the manifold's margin scores at 0.850 held-out AUC here
    # (EVALUATION.md section 9.4), because random variety cannot fake
    # role-coupling. Detection is the LOW tail of the permutation z.
    role_reference = baseline.get("role_coupling")
    # Drift guard: a baseline calibrated with different scoring factors would
    # compare a current-code score against thresholds fit on another quantity;
    # skip the axis instead (same pattern as the voice-model schema guard).
    if role_reference and (role_reference.get("scoring_factors")
                           != list(ROLE_SCORING_FACTORS)):
        role_reference = None
    if role_reference:
        role = document_role_coupling(shape)
        role_values = role_reference.get("values", [])
        low_threshold = role_reference.get("low_threshold")
        role_axis = (conformal or {}).get("role")
        if (role_axis and role_axis.get("scoring_factors")
                != list(ROLE_SCORING_FACTORS)):
            role_axis = None
        flagged = False
        if role["score"] is not None:
            score = float(role["score"])
            if role_axis and role_axis.get("calibration"):
                stratum = _length_stratum(shape["n_paragraphs"],
                                          conformal["strata_edges"])
                cal, cal_basis = _stratum_calibration(role_axis, stratum)
                alpha = float(conformal.get("alpha", CONFORMAL_ALPHA))
                # calibration stores NEGATED z (higher = more nonconforming)
                p_value = _conformal_p(cal, -score)
                flagged = p_value <= alpha
                op_reference = {"operating_point": "split-conformal",
                                "alpha": alpha,
                                "n_calibration": len(cal),
                                "calibration_basis": cal_basis,
                                "scoring_factors": list(ROLE_SCORING_FACTORS),
                                "provenance": BASELINE_NAME}
                op_margin = alpha - p_value
                op_confidence = {
                    "value": min(1.0, len(cal) / 100.0),
                    "basis": (f"split-conformal p against {len(cal)} human "
                              f"calibration papers ({cal_basis}); P(false "
                              f"flag) <= {alpha:g} finite-sample for "
                              "exchangeable human documents; length strata "
                              "absorb the measured short-paper bias")}
                op_clause = (f"conformal p = {p_value:.4f} <= alpha {alpha:g} "
                             f"against {len(cal)} human papers ({cal_basis})")
                op_observed_extra = {"conformal_p": p_value}
            elif low_threshold is not None and role_values:
                flagged = score < float(low_threshold)
                percentile = _percentile(role_values, score)
                op_reference = {"operating_point": "in-sample percentile",
                                "n_documents": len(role_values),
                                "low_percentile": role_reference.get(
                                    "low_percentile"),
                                "low_threshold": low_threshold,
                                "bootstrap_95_ci": role_reference.get(
                                    "bootstrap_95_ci"),
                                "leave_one_document_out_flag_rate":
                                    role_reference.get(
                                        "leave_one_document_out_flag_rate"),
                                "scoring_factors": role_reference.get(
                                    "scoring_factors"),
                                "provenance": BASELINE_NAME}
                op_margin = float(low_threshold) - score
                op_confidence = {
                    "value": min(1.0, len(role_values) / 100.0),
                    "basis": (f"{len(role_values)} complete reference "
                              "documents; permutation-normalized within "
                              "each document, validated held-out against "
                              "natural, de-AI'd, and shape-adversarial "
                              "AI document sets")}
                op_clause = (f"below the human 5th-percentile threshold "
                             f"{float(low_threshold):.2f}")
                op_observed_extra = {"empirical_percentile": percentile}
            if flagged:
                findings.append(feedback.make_finding(
                    kind="advisory", layer="L2",
                    rule="document-role-decoupling",
                    scope="document", calibration_unit="document", line=1, section=section_label, path=path,
                    detector="deai_docstructure",
                    detector_version="sci-paper.docstructure-baseline.v2",
                    calibration_asset=BASELINE_NAME,
                    measurement_status="measured", strength="strong",
                    observed={"role_coupling_z": role["score"],
                              "factors": role["factors"],
                              "n_sections": shape["n_sections"],
                              "n_paragraphs": shape["n_paragraphs"],
                              **op_observed_extra},
                    reference=op_reference,
                    normalized_distance=op_margin,
                    confidence=op_confidence,
                    message=(f"Paragraph-shape variation is decoupled from "
                             f"rhetorical role: coupling z is "
                             f"{role['score']:.2f} ({op_clause}). Human papers "
                             "vary paragraph shape where the argument demands "
                             "it (across sections and between citing/"
                             "derivation/prose paragraphs); here the variation "
                             "is unrelated to role. This is a measured "
                             "deviation, not an AI verdict."),
                    action=("Where the argument changes register (setup vs "
                            "derivation vs results), let the paragraph shape "
                            "follow it; do not add variety at random, tie it "
                            "to content."),
                    evidence=["role_coupling", round(score, 6)],
                ))
    for feature_name, reference in baseline.get("dispersion", {}).items():
        observed = dispersion.get(feature_name, {}).get(DISPERSION_STAT)
        low_threshold = reference.get("low_threshold")
        high_threshold = reference.get("high_threshold")
        values = reference.get("values", [])
        if observed is None or low_threshold is None or not values:
            continue
        value = float(observed)
        if value < float(low_threshold):
            tail, rule_name = "low", "document-uniformity"
            threshold, distance = low_threshold, float(low_threshold) - value
            direction = "below the human low-tail"
            advice = ("Check whether the paragraphs are more uniform than the "
                      "argument needs; vary this feature where the science allows "
                      "(mix a list, a long-argument, and a terse paragraph) without "
                      "manufacturing variety that harms clarity.")
        elif high_threshold is not None and value > float(high_threshold):
            tail, rule_name = "high", "document-overdispersion"
            threshold, distance = high_threshold, value - float(high_threshold)
            direction = "above the human high-tail"
            advice = ("Check whether paragraph shapes swing more than the argument "
                      "motivates; forced or erratic variation reads as noise and "
                      "also departs from the human band.")
        else:
            continue
        percentile = _percentile(values, value)
        findings.append(feedback.make_finding(
            kind="advisory", layer="L2",
            rule=f"{rule_name}:{feature_name}",
            scope="document", calibration_unit="document", line=1, section=section_label, path=path,
            detector="deai_docstructure",
            detector_version="sci-paper.docstructure-baseline.v2",
            calibration_asset=BASELINE_NAME,
            measurement_status="measured", strength=per_feature_strength,
            observed={"dispersion_std": observed,
                      "empirical_percentile": percentile,
                      "band_tail": tail,
                      "n_sections": shape["n_sections"],
                      "n_paragraphs": shape["n_paragraphs"]},
            reference={"n_documents": baseline["n_documents"],
                       "low_percentile": baseline.get("dispersion_low_percentile"),
                       "high_percentile": baseline.get("dispersion_high_percentile"),
                       "low_threshold": low_threshold,
                       "high_threshold": high_threshold,
                       "bootstrap_95_ci": reference.get("bootstrap_95_ci"),
                       "leave_one_document_out_flag_rate": reference.get(
                           "leave_one_document_out_flag_rate"),
                       "provenance": BASELINE_NAME},
            normalized_distance=distance,
            confidence={"value": min(1.0, baseline["n_documents"] / 30.0),
                        "basis": (f"{baseline['n_documents']} complete reference "
                                  "documents; band semantics validated held-out "
                                  "against natural, de-AI'd, and shape-adversarial "
                                  "AI document sets")},
            message=(f"Cross-paragraph variation in {feature_name.replace('_', ' ')} "
                     f"is {value:.3f}, {direction} {float(threshold):.3f}: the "
                     "document departs from the complete-human dispersion band for "
                     "this feature. This is a measured deviation, not an AI verdict."),
            action=advice,
            evidence=[tail, feature_name, round(value, 8)],
        ))
    return findings


def _paper_documents(corpus_dir: Path) -> list[tuple[str, str]]:
    """One document per paper, in document order (see `es.corpus_documents`).

    Grouping a bundle into one observation was always right; concatenating it
    in sorted FILENAME order was not. This axis measures section arc and
    paragraph sequence, and sorted order puts `Conclusion.tex` before
    `Introduction.tex`: 122 of the 500 `wgl` bundles hold more than one `.tex`,
    12 of them provably out of order, and all 122 also folded appendices,
    acknowledgements, author lists and the journal's own class documentation in
    as body prose.
    """
    return es.corpus_documents(corpus_dir)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, nargs="?")
    parser.add_argument("--field", required=True)
    parser.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--corpus-dir", type=Path,
                        help="directory of complete human .tex/.md source documents")
    parser.add_argument("--strong-percentile", type=float, default=0.95)
    args = parser.parse_args(argv)
    field_dir = args.profile_root / args.field
    if args.calibrate:
        if args.corpus_dir is None or not args.corpus_dir.exists():
            print("[deai_docstructure] --calibrate requires --corpus-dir", file=sys.stderr)
            return 2
        try:
            baseline = calibrate(_paper_documents(args.corpus_dir), field_dir,
                                 args.strong_percentile)
        except ValueError as error:
            print(f"[deai_docstructure] {error}", file=sys.stderr)
            return 2
        print(f"[deai_docstructure] baseline written from {baseline['n_documents']} complete documents")
        return 0
    if args.file is None or not args.file.exists():
        print(f"[deai_docstructure] file not found: {args.file}", file=sys.stderr)
        return 2
    text = args.file.read_text(encoding="utf-8", errors="replace")
    report = feedback.build_report(
        path=args.file,
        findings=document_findings(text, field_dir, args.file),
        axes=[docstructure_axis_status(text, field_dir)],
    )
    print(feedback.render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
