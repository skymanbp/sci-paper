"""Build the basic descriptive profile and optional legacy retrieval assets.

This convenience wrapper runs three independent steps:

1. ``extract_style.py`` builds the descriptive dossier, JSON statistics, and
   exemplar JSONL.
2. ``train_ai_ism_classifier.py`` optionally builds the legacy word-ngram style
   classifier.
3. ``retrieve_exemplars.py`` optionally warms the sentence-transformer cache.

The wrapper does not create calibrated distribution, sentence-structure,
whole-document, UID, or learned field-similarity policy. Build those assets with
their dedicated tools and record their provenance in ``EVALUATION.md``. Missing
assets remain unmeasured or degraded.

Defaults: run all three basic steps. Skip optional steps with ``--no-train`` or
``--no-warm``. Field resolution follows the delegated tools; ``--field <name>``
overrides auto-detection.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"


def list_fields(profile_root: Path) -> list[str]:
    if not profile_root.exists():
        return []
    return sorted(
        p.name for p in profile_root.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def run_step(label: str, cmd: list[str]) -> tuple[bool, float]:
    """Stream a subprocess. Return (ok, elapsed_seconds)."""
    print(f"\n=== {label} ===")
    print(f"$ {' '.join(cmd)}")
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    elapsed = time.perf_counter() - t0
    ok = proc.returncode == 0
    print(f"--- {label}: {'OK' if ok else f'FAILED (exit {proc.returncode})'} "
          f"in {elapsed:.1f} s ---")
    return ok, elapsed


def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()

    p = cli_common.field_parser(__doc__)
    p.add_argument("--no-train", action="store_true",
                   help="Skip legacy word-ngram classifier training.")
    p.add_argument("--no-warm", action="store_true",
                   help="Skip pre-warming the sentence-transformer cache.")
    p.add_argument("--warm-section", default="method",
                   help="Section type used for the warm-up retrieval call "
                        "(default: method).")
    p.add_argument("--warm-topic", default="",
                   help="Topic phrase for the warm-up call (empty = section name).")
    args = p.parse_args(argv)

    py = sys.executable
    profile_args = ["--profile-root", str(args.profile_root)]
    extract_cmd = [py, "tools/extract_style.py", *profile_args]
    train_cmd = [py, "tools/train_ai_ism_classifier.py", *profile_args]
    warm_cmd = [py, "tools/retrieve_exemplars.py", *profile_args,
                "--section", args.warm_section, "--k", "1"]
    if args.warm_topic:
        warm_cmd += ["--topic", args.warm_topic]
    if args.field:
        extract_cmd += ["--field", args.field]
        train_cmd += ["--field", args.field]
        warm_cmd += ["--field", args.field]

    timings: list[tuple[str, float, bool]] = []

    ok, elapsed = run_step("Step 1/3: extract descriptive style profile", extract_cmd)
    timings.append(("extract_style", elapsed, ok))
    if not ok:
        print("\n[build_profile] Aborting: extraction failed; fix the corpus "
              "or extractor and retry.", file=sys.stderr)
        return 1

    if args.no_train:
        print("\n=== Step 2/3: legacy word-ngram classifier — "
              "SKIPPED (--no-train) ===")
    else:
        ok, elapsed = run_step(
            "Step 2/3: train legacy word-ngram classifier", train_cmd)
        timings.append(("legacy_classifier", elapsed, ok))
        if not ok:
            print("\n[build_profile] WARNING: legacy classifier training "
                  "failed; continuing without that optional advisory axis.",
                  file=sys.stderr)

    if args.no_warm:
        print("\n=== Step 3/3: warm exemplar embedding cache — "
              "SKIPPED (--no-warm) ===")
    else:
        ok, elapsed = run_step(
            "Step 3/3: warm sentence-transformer exemplar cache", warm_cmd)
        timings.append(("warm_exemplar_cache", elapsed, ok))
        if not ok:
            print("\n[build_profile] WARNING: cache warm-up failed; semantic "
                  "retrieval remains unavailable until its dependency/model "
                  "loads successfully.", file=sys.stderr)

    print("\n=== build_profile summary ===")
    total = sum(elapsed for _, elapsed, _ in timings)
    for label, elapsed, ok in timings:
        status = "OK " if ok else "FAIL"
        print(f"  {status}  {label:24s} {elapsed:>6.1f} s")
    print(f"  total: {total:.1f} s")
    print()

    fields = list_fields(args.profile_root)
    if fields:
        print(f"Basic profile(s) present: {fields}")
        print("This command did not create calibrated operating points.")
        print()
        print("Next:")
        print("  - draft with evidence: /sci-paper:de-ai discussion")
        print("  - retrieve exemplars: python tools/retrieve_exemplars.py "
              "--section method --topic \"...\"")
        print("  - unified feedback: python tools/ai_ism_lint.py "
              "<draft.tex> --field <name> --format json")
        print("  - calibration map: see style-profile/README.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
