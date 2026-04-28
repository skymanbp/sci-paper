# style-corpus/wgl/

Weak-gravitational-lensing (WGL) field corpus. This is the only populated
field in v0.1; additional fields will live alongside it as
`style-corpus/<field>/` subdirectories (e.g. `cosmology/`, `ml-methods/`).

## Tiers

- `tier-1-top/` — Top-journal exemplars (ApJ, MNRAS, PRD, JCAP, Nature
  Astronomy). Default weight 0.5.
- `tier-2-mentor/` — Mentor's high-quality WGL papers. Default weight 0.3.
- `tier-3-reference/` — Other high-value WGL references (foundational
  weak-lensing methodology, cluster lensing, NFW fits, aperture-mass
  formalism, etc.). Default weight 0.2.

See `../README.md` (one level up) for general corpus rules.

## Building this field's profile

```bash
python tools/extract_style.py --field wgl
# (or just `python tools/extract_style.py` while wgl is the only field —
# the tool auto-detects single-field corpora.)
```

Outputs to `style-profile/wgl/{lexicon.json, sentence_stats.json,
transition_inventory.json, style_dossier.md}`.
