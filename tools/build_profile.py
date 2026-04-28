"""build_profile.py — one-shot orchestration: extract + train + warm cache.

Wraps the three independent tools:
  1. extract_style.py            → dossier + JSON stats + exemplar JSONL
  2. train_ai_ism_classifier.py  → ai_ism_classifier.joblib (optional)
  3. retrieve_exemplars.py       → pre-warm sentence-transformer embedding
                                   cache so the first /paper-style call is
                                   instant (optional)

Defaults: run all three. Skip any with the corresponding `--no-*` flag.
Field-aware via the same auto-detect rules; `--field <name>` overrides.

After this you can immediately use:
  - /sci-paper:paper-style discussion
  - python tools/retrieve_exemplars.py --section method --topic "..."
  - python tools/ai_ism_lint.py draft.tex --ai-classifier --summary
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--field", default=None,
                   help="Field name; auto-detected when only one exists.")
    p.add_argument("--profile-root", type=Path, default=DEFAULT_PROFILE_ROOT)
    p.add_argument("--no-train", action="store_true",
                   help="Skip ai_ism classifier training.")
    p.add_argument("--no-warm", action="store_true",
                   help="Skip pre-warming the sentence-transformers cache.")
    p.add_argument("--warm-section", default="method",
                   help="Section type used for the warm-up retrieval call "
                        "(default: method).")
    p.add_argument("--warm-topic", default="",
                   help="Topic phrase for the warm-up call (empty = section name).")
    args = p.parse_args(argv)

    py = sys.executable
    extract_cmd = [py, "tools/extract_style.py"]
    train_cmd = [py, "tools/train_ai_ism_classifier.py"]
    warm_cmd = [py, "tools/retrieve_exemplars.py",
                "--section", args.warm_section, "--k", "1"]
    if args.warm_topic:
        warm_cmd += ["--topic", args.warm_topic]
    if args.field:
        extract_cmd += ["--field", args.field]
        train_cmd += ["--field", args.field]
        warm_cmd += ["--field", args.field]

    timings: list[tuple[str, float, bool]] = []

    ok, t = run_step("Step 1/3: extract_style", extract_cmd)
    timings.append(("extract_style", t, ok))
    if not ok:
        print("\n[build_profile] Aborting: extract_style failed; "
              "fix corpus + retry.", file=sys.stderr)
        return 1

    if args.no_train:
        print("\n=== Step 2/3: train_ai_ism_classifier — SKIPPED (--no-train) ===")
    else:
        ok, t = run_step("Step 2/3: train_ai_ism_classifier", train_cmd)
        timings.append(("train_classifier", t, ok))
        if not ok:
            print("\n[build_profile] WARNING: classifier training failed; "
                  "continuing without classifier. Lint can still run "
                  "without --ai-classifier.", file=sys.stderr)

    if args.no_warm:
        print("\n=== Step 3/3: warm embedding cache — SKIPPED (--no-warm) ===")
    else:
        # Suppress retrieve output; we just want the cache to be built.
        # Send to /dev/null on Unix, NUL on Windows.
        warm_cmd_quiet = warm_cmd + []  # no extra; output is small for k=1
        ok, t = run_step("Step 3/3: warm sentence-transformers cache", warm_cmd_quiet)
        timings.append(("warm_cache", t, ok))
        if not ok:
            print("\n[build_profile] WARNING: cache warm-up failed; first "
                  "real /paper-style call will pay the model-load cost.",
                  file=sys.stderr)

    print("\n=== build_profile summary ===")
    total = sum(t for _, t, _ in timings)
    for label, t, ok in timings:
        status = "OK " if ok else "FAIL"
        print(f"  {status}  {label:24s} {t:>6.1f} s")
    print(f"  total: {total:.1f} s")
    print()

    fields = list_fields(args.profile_root)
    if fields:
        print(f"Profile(s) ready: {fields}")
        print()
        print("Next:")
        print("  - draft a section: /sci-paper:paper-style discussion")
        print(f"  - retrieve top-K: python tools/retrieve_exemplars.py "
              f"--section method --topic \"...\"")
        print(f"  - lint a draft:    python tools/ai_ism_lint.py "
              f"<draft.tex> --ai-classifier --summary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
