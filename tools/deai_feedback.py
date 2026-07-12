"""Shared structured feedback contract for sci-paper detectors.

The public schema is ``sci-paper.feedback.v1``. Detectors create finding
objects with :func:`make_finding`; the linter ranks, summarizes, and serializes
those same objects. Human-readable output is a projection of the structured
objects, never a second independently assembled result.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "sci-paper.feedback.v1"
KINDS = {"integrity_blocker", "l0_target", "advisory"}
STATUSES = {"measured", "degraded", "unmeasured", "not_applicable"}
DISPOSITIONS = {"pending", "acted", "accepted", "rejected_as_false_positive"}

_KIND_RANK = {"integrity_blocker": 0, "l0_target": 1, "advisory": 2}
_LAYER_RANK = {"QD": 0, "L0": 1, "L2": 2, "L1": 3, "L4": 4, "L3": 5}
_EXPOSURE_RANK = {
    "abstract": 0,
    "introduction": 1,
    "intro": 1,
    "conclusion": 2,
    "discussion": 3,
    "results": 4,
    "method": 5,
    "methods": 5,
    "unknown": 6,
}


def _stable_id(detector: str, rule: str, path: str | None, line: int,
               evidence: Any) -> str:
    payload = json.dumps(
        [detector, rule, path or "", line, evidence],
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    return "spf-" + hashlib.sha256(payload).hexdigest()[:16]


def _confidence_value(confidence: dict[str, Any] | float | None) -> float:
    if isinstance(confidence, dict):
        value = confidence.get("value", 0.0)
    elif confidence is None:
        value = 0.0
    else:
        value = confidence
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _section_key(section: str | None) -> str:
    low = (section or "unknown").lower()
    for key in _EXPOSURE_RANK:
        if key in low:
            return key
    return "unknown"


def priority_components(finding: dict[str, Any]) -> dict[str, Any]:
    """Return visible lexicographic ranking components for one finding."""
    kind = finding["kind"]
    layer = finding["layer"]
    section = finding.get("location", {}).get("section")
    distance = finding.get("normalized_distance")
    distance_value = abs(float(distance)) if isinstance(distance, (int, float)) else 0.0
    confidence = _confidence_value(finding.get("confidence"))
    strength = finding.get("strength", "ordinary")
    strength_rank = {
        "verified": 0,
        "strong": 1,
        "target": 1,
        "suspected": 2,
        "ordinary": 3,
        "context": 4,
    }.get(strength, 3)
    return {
        "kind_rank": _KIND_RANK[kind],
        "strength_rank": strength_rank,
        "layer_rank": _LAYER_RANK.get(layer, 9),
        "exposure_rank": _EXPOSURE_RANK[_section_key(section)],
        "distance_rank": -distance_value,
        "confidence_rank": -confidence,
        "tie_break": [
            finding.get("location", {}).get("path") or "",
            int(finding.get("location", {}).get("start_line") or 0),
            finding.get("rule", ""),
            finding.get("detector", {}).get("name", ""),
        ],
    }


def priority_key(finding: dict[str, Any]) -> tuple[Any, ...]:
    p = finding.get("priority") or priority_components(finding)
    return (
        p["kind_rank"],
        p["strength_rank"],
        p["layer_rank"],
        p["exposure_rank"],
        p["distance_rank"],
        p["confidence_rank"],
        *p["tie_break"],
    )


def make_finding(
    *,
    kind: str,
    layer: str,
    rule: str,
    scope: str,
    message: str,
    action: str,
    detector: str,
    line: int = 1,
    end_line: int | None = None,
    section: str | None = None,
    path: str | Path | None = None,
    observed: dict[str, Any] | None = None,
    reference: dict[str, Any] | None = None,
    normalized_distance: float | None = None,
    confidence: dict[str, Any] | float | None = None,
    measurement_status: str = "measured",
    strength: str = "ordinary",
    strong_advisory: bool | None = None,
    source_trace: dict[str, Any] | None = None,
    disposition: str = "pending",
    evidence: Any = None,
    detector_version: str | None = None,
    calibration_asset: str | None = None,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise ValueError(f"unknown finding kind: {kind}")
    if measurement_status not in STATUSES:
        raise ValueError(f"unknown measurement status: {measurement_status}")
    if disposition not in DISPOSITIONS:
        raise ValueError(f"unknown disposition: {disposition}")
    # Single source of truth: strong_advisory is DERIVED from the strength
    # enum for advisories. An explicit conflicting value is a caller bug.
    derived_strong = kind == "advisory" and strength == "strong"
    if strong_advisory is not None and bool(strong_advisory) != derived_strong:
        raise ValueError(
            f"strong_advisory={strong_advisory} conflicts with "
            f"kind={kind!r}/strength={strength!r}")
    strong_advisory = derived_strong
    path_text = str(path) if path is not None else None
    observed = observed or {}
    detector_obj = {
        "name": detector,
        "version": detector_version or "v1",
        "configuration": {},
        "calibration_asset": calibration_asset,
    }
    finding: dict[str, Any] = {
        "finding_id": _stable_id(detector, rule, path_text, line,
                                 evidence if evidence is not None else observed),
        "kind": kind,
        "layer": layer,
        "rule": rule,
        "scope": scope,
        "location": {
            "path": path_text,
            "start_line": int(line),
            "end_line": int(end_line) if end_line is not None else None,
            "section": section,
        },
        "message": message,
        "observed": observed,
        "reference": reference,
        "normalized_distance": normalized_distance,
        "confidence": confidence if isinstance(confidence, dict) else {
            "value": _confidence_value(confidence),
            "basis": "detector default" if confidence is None else "detector estimate",
        },
        "measurement_status": measurement_status,
        "strength": strength,
        "strong_advisory": bool(strong_advisory),
        "priority": {},
        "recommended_action": action,
        "detector": detector_obj,
        "source_trace": source_trace,
        "disposition": disposition,
        "before_after": None,
    }
    finding["priority"] = priority_components(finding)
    return finding


def rank_findings(findings: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = list(findings)
    for finding in ranked:
        finding["priority"] = priority_components(finding)
    ranked.sort(key=priority_key)
    return ranked


def axis_status(axis: str, status: str, *, reason: str | None = None,
                detector: str | None = None) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError(f"unknown measurement status: {status}")
    return {"axis": axis, "status": status, "reason": reason,
            "detector": detector}


def summarize(findings: Iterable[dict[str, Any]],
              axes: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    items = list(findings)
    by_kind = Counter(f["kind"] for f in items)
    by_layer = Counter(f["layer"] for f in items)
    by_status = Counter(a["status"] for a in axes)
    return {
        "total_findings": len(items),
        "by_kind": {k: by_kind.get(k, 0) for k in sorted(KINDS)},
        "by_layer": dict(sorted(by_layer.items())),
        "strong_advisories": sum(
            1 for f in items if f["kind"] == "advisory" and f.get("strong_advisory")
        ),
        "pending_advisories": sum(
            1 for f in items
            if f["kind"] == "advisory" and f.get("disposition") == "pending"
        ),
        "axis_status": {k: by_status.get(k, 0) for k in sorted(STATUSES)},
    }


def build_report(*, path: str | Path, findings: Iterable[dict[str, Any]],
                 axes: Iterable[dict[str, Any]], top: int | None = None) -> dict[str, Any]:
    ranked = rank_findings(findings)
    axis_items = list(axes)
    emitted = ranked if top is None else ranked[:max(0, top)]
    return {
        "schema": SCHEMA_VERSION,
        "target": str(path),
        "summary": summarize(ranked, axis_items),
        "axes": axis_items,
        "findings": emitted,
        "emitted_findings": len(emitted),
        "total_findings": len(ranked),
        "truncated": len(emitted) < len(ranked),
    }


def tuple_hits(findings: Iterable[dict[str, Any]]) -> list[tuple[int, str, str]]:
    """Compatibility adapter for callers that still consume legacy tuples."""
    return [
        (int(f["location"]["start_line"]), f["rule"], f["message"])
        for f in findings
    ]


def dump_report(report: dict[str, Any], output: Path | None = None) -> str:
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if output is not None:
        output.write_text(text, encoding="utf-8")
    return text


def render_text(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        f"[sci-paper] {report['target']}",
        ("findings: "
         f"blockers={s['by_kind']['integrity_blocker']} "
         f"L0={s['by_kind']['l0_target']} "
         f"advisories={s['by_kind']['advisory']} "
         f"(strong={s['strong_advisories']})"),
    ]
    for axis in report["axes"]:
        detail = f": {axis['reason']}" if axis.get("reason") else ""
        lines.append(f"axis {axis['axis']}: {axis['status']}{detail}")
    if report["findings"]:
        lines.append("")
    for f in report["findings"]:
        loc = f["location"]
        label = f"{f['kind']} {f['layer']} {f['rule']}"
        strong = " strong" if f.get("strong_advisory") else ""
        lines.append(f"  L{loc['start_line']:>5} [{label}{strong}] {f['message']}")
        lines.append(f"          action: {f['recommended_action']}")
    if report["truncated"]:
        lines.append(
            f"... displayed {report['emitted_findings']} of {report['total_findings']} findings"
        )
    return "\n".join(lines)
