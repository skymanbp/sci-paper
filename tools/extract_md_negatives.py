"""extract_md_negatives.py — harvest LLM-drafted PAPER PROSE from existing
markdown. Strictly paper-voice prose, NOT documentation.

Source-quality matters MORE than quantity. Empirically (2026-04-28 test
on D:/Projects/weak-gravitational-lensing/instructions/), feeding the
classifier compact technical-documentation prose drops CV F1 from 0.88
to 0.71 because doc-voice and paper-voice are different distributions —
the model has to span both as "AI-ish" and gets confused.

GOOD sources:
  - Old or rejected paper drafts that you know were heavily LLM-assisted
    (full sections in journal voice)
  - Standalone Claude/GPT outputs of "write me a paper introduction on…"
    style prompts
  - Public AI-generated paper datasets (CheckGPT-corpora, etc.)

BAD sources:
  - Project documentation (ARCHITECTURE.md, design notes) — wrong voice
  - Code comments / docstrings — wrong voice
  - Mixed-author docs where some paragraphs are user-written

Strips markdown structure (headers / code fences / tables / list items /
blockquotes / inline code / link/image syntax / bold-italic markers) and
keeps paragraphs that look like prose (30–400 words, ≥ 60% alphabetic,
< 15% digits to filter out tables-as-prose).

Output is appended to `style-profile/<field>/ai_ism_negatives_extracted.txt`
(gitignored — content comes from your private project files and shouldn't
ship with the plugin).

Run with:
  python tools/extract_md_negatives.py --source-dir <path/to/dir-of-md-files>
                                       [--field <name>] [--max <N>]

Combined with the handcrafted set, the training script will load both and
you can re-train via `python tools/train_ai_ism_classifier.py`. **After
re-training, verify CV F1 has not degraded** — if it has, your source
dir wasn't paper-voice and should be removed.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cli_common  # noqa: E402 -- because the sys.path insert above must run first

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_ROOT = REPO_ROOT / "style-profile"

# Strip ordering matters: code fences first (they may contain # / | / -),
# then headers / blockquotes / tables / lists, then inline syntax.
RE_FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
RE_INLINE_CODE = re.compile(r"`[^`\n]+`")
RE_ATX_HEADER = re.compile(r"^#{1,6}\s.*$", re.MULTILINE)
RE_BLOCKQUOTE = re.compile(r"^>.*$", re.MULTILINE)
RE_HRULE = re.compile(r"^[-=_*]{3,}\s*$", re.MULTILINE)
RE_TABLE_ROW = re.compile(r"^\s*\|.*\|.*$", re.MULTILINE)
RE_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s.*$", re.MULTILINE)
RE_IMG = re.compile(r"!\[[^\]]*\]\([^)]+\)")
RE_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
RE_BOLD = re.compile(r"\*\*([^*]+)\*\*")
RE_ITAL = re.compile(r"\*([^*]+)\*")


def strip_md(text: str) -> str:
    text = RE_FENCED_CODE.sub("", text)
    text = RE_ATX_HEADER.sub("", text)
    text = RE_BLOCKQUOTE.sub("", text)
    text = RE_HRULE.sub("", text)
    text = RE_TABLE_ROW.sub("", text)
    text = RE_LIST_ITEM.sub("", text)
    text = RE_IMG.sub("", text)
    text = RE_LINK.sub(r"\1", text)
    text = RE_BOLD.sub(r"\1", text)
    text = RE_ITAL.sub(r"\1", text)
    text = RE_INLINE_CODE.sub(" ", text)
    return text


def chunk_paragraphs(text: str) -> list[str]:
    paras = re.split(r"\n\s*\n", text)
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        p = re.sub(r"\s+", " ", p)
        out.append(p)
    return out


def is_prose(text: str, min_words: int = 30, max_words: int = 400) -> bool:
    """Filters out fragments / tables / mostly-symbolic content."""
    n_words = len(text.split())
    if n_words < min_words or n_words > max_words:
        return False
    alpha = sum(1 for c in text if c.isalpha())
    if alpha / max(1, len(text)) < 0.6:
        return False
    # Reject paragraphs that are mostly numbers / hex / file paths
    digits = sum(1 for c in text if c.isdigit())
    if digits / max(1, len(text)) > 0.15:
        return False
    return True


def list_fields(profile_root: Path) -> list[str]:
    return cli_common.list_fields(profile_root)


def resolve_field(arg_field: str | None, profile_root: Path) -> str:
    return cli_common.resolve_field(
        arg_field, profile_root, tool="extract_md_negatives")




def main(argv: list[str] | None = None) -> int:
    cli_common.utf8_stdout()

    p = cli_common.field_parser(__doc__)
    p.add_argument("--source-dir", type=Path, required=True,
                   help="Directory tree to scan for .md / .txt files.")
    p.add_argument("--max", type=int, default=300,
                   help="Cap the number of extracted paragraphs (default 300).")
    p.add_argument("--append", action="store_true",
                   help="Append to existing extracted file; default is to overwrite.")
    args = p.parse_args(argv)

    if not args.source_dir.exists():
        raise SystemExit(f"[extract_md_negatives] {args.source_dir} not found.")

    field = resolve_field(args.field, args.profile_root)
    field_profile_dir = args.profile_root / field
    out_path = field_profile_dir / "ai_ism_negatives_extracted.txt"

    md_files = sorted(
        p for p in args.source_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".txt"}
    )
    if not md_files:
        raise SystemExit(
            f"[extract_md_negatives] No .md/.txt files under {args.source_dir}/."
        )

    print(f"[extract_md_negatives] field={field!r}")
    print(f"[extract_md_negatives] scanning {len(md_files)} markdown/text files in {args.source_dir}")

    paragraphs: list[tuple[str, str]] = []  # (source_relpath, text)
    for f in md_files:
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  WARN: couldn't read {f}: {e}", file=sys.stderr)
            continue
        stripped = strip_md(raw)
        for chunk in chunk_paragraphs(stripped):
            if is_prose(chunk):
                paragraphs.append((str(f.relative_to(args.source_dir)), chunk))

    if len(paragraphs) > args.max:
        # Take a uniform sample — preserves source diversity better than first-N.
        step = len(paragraphs) / args.max
        paragraphs = [paragraphs[int(i * step)] for i in range(args.max)]

    print(f"[extract_md_negatives] extracted {len(paragraphs)} prose paragraphs")

    mode = "a" if args.append and out_path.exists() else "w"
    with out_path.open(mode, encoding="utf-8") as f:
        if mode == "w":
            f.write(
                "# Auto-extracted AI-ism negative samples.\n"
                f"# Source dir: {args.source_dir}\n"
                f"# Files scanned: {len(md_files)}\n"
                f"# Paragraphs after filter (30-400 words, >= 60% alpha, < 15% digits): "
                f"{len(paragraphs)}\n"
                "# Lines starting with '#' are skipped by the loader.\n"
                "# Generated by tools/extract_md_negatives.py — do not edit by hand;\n"
                "# regenerate by re-running the extractor.\n\n"
            )
        for src, para in paragraphs:
            f.write(f"# source: {src}\n{para}\n\n")

    print(f"[extract_md_negatives] OK. → {out_path}")
    print(
        f"\nNext: re-train the classifier to use these negatives:\n"
        f"  python tools/train_ai_ism_classifier.py --field {field}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
