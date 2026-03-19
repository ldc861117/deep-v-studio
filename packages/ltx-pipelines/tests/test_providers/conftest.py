"""conftest for provider tests — patches torch-dependent imports.

On macOS (no CUDA), the top-level ltx_pipelines.__init__ imports
pipeline modules that require torch + numpy with CUDA support.
This conftest pre-loads a stub ltx_pipelines package that only
exposes the providers subpackage, so provider tests run cleanly.
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

# Compute the real source path for ltx_pipelines
_src_dir = Path(__file__).resolve().parents[2] / "src" / "ltx_pipelines"

# Pre-populate sys.modules with a stub ltx_pipelines package
# that points __path__ to the real source dir, but skips __init__.py
# (which would trigger torch imports).
if "ltx_pipelines" not in sys.modules:
    _stub = types.ModuleType("ltx_pipelines")
    _stub.__path__ = [str(_src_dir)]  # type: ignore[attr-defined]
    _stub.__package__ = "ltx_pipelines"
    _stub.__file__ = str(_src_dir / "__init__.py")
    sys.modules["ltx_pipelines"] = _stub

# Mock httpx at the top level so it's always available for provider tests
# even if not installed in the current venv
if "httpx" not in sys.modules:
    try:
        import httpx  # noqa: F401
    except ImportError:
        sys.modules["httpx"] = MagicMock()
