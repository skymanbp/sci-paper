# style-corpus/wgl/

Weak-gravitational-lensing (WGL) field corpus. Other fields live alongside it
as `style-corpus/<field>/` subdirectories (e.g. `cosmology/`, `ml-methods/`).

## Tiers

- `tier-1-top/` — Top-journal exemplars (ApJ, MNRAS, PRD, JCAP, Nature
  Astronomy). Default weight 0.5.
- `tier-2-mentor/` — Mentor's high-quality WGL papers. Default weight 0.3.
- `tier-3-reference/` — Other high-value WGL references (foundational
  weak-lensing methodology, cluster lensing, NFW fits, aperture-mass
  formalism, etc.). Default weight 0.2.

See `../README.md` (one level up) for general corpus rules and the
`fulltext-*` pulls.

## Building this field's profile

```bash
python tools/extract_style.py --field wgl
# (`--field` may be omitted when one field is present — the tool auto-detects
# a single-field corpus; with several fields it is required.)
```

Its outputs, and every `--calibrate` step after it, are listed in
[`style-profile/README.md`](../../style-profile/README.md).
