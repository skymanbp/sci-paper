"""Put `tools/` on `sys.path` so a test can import the module it exercises.

The suite is plain `unittest discover` with no package and no conftest, so each
test file opened with the same four-line path preamble. `import _toolpath`
replaces it; the name starts with an underscore so discovery (`test_*.py`) never
collects it as a test module.

`TOOLS` is re-exported for the handful of tests that read a tool's source rather
than import it -- the line-budget and unbound-name contracts, for instance.
"""

from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
