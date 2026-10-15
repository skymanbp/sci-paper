# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 0.39.x | yes |
| < 0.39 | no: upgrade first |

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private reporting:
[Security → Report a vulnerability](https://github.com/skymanbp/sci-paper/security/advisories/new).

Include the plugin version, the Python version, which optional packages
from requirements.txt are installed, and a reproduction: the command or
skill, the input it was given, and what it did.

## What counts as a vulnerability here

sci-paper reads manuscripts, PDFs and corpora and runs linters, validators
and models over them. The following count:

- A crafted manuscript, PDF or corpus file that makes a tool execute code,
  or read or write a path outside the ones it was given.
- A path by which the text under analysis leaves the machine other than
  through a model endpoint the user configured.
- A report, score or finding that an input can forge without the
  underlying check having run: the evaluation record must say what was
  measured, and "unmeasured" must stay visible.
- A download or a dependency that is not what the documentation says it is.

## What does not count

- A measurement that is wrong because an optional package is missing: by
  design the result is reported as unmeasured or degraded, not as zero.
- A local user with the same filesystem rights reading the project's own
  caches and profiles.
