"""Load a figure-local module by file path — one loader for every figure build.

Figures load their panel renderers (and data generators load benchmark model/env
classes) by file path, so nothing depends on sys.path ordering and editors do not
flag the imports as unresolved. Defined once here; previously each make_figure.py
carried its own copy.

``register=True`` inserts the module into ``sys.modules`` under ``name`` BEFORE
executing it. Use it when the module must be importable by that name afterwards —
above all when ``torch.load`` has to unpickle classes that were pickled under that
module name (the benchmark-code convention, see REPO_LAYOUT.md).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def load_module(name: str, path: Path, *, register: bool = False) -> ModuleType:
    """Load ``path`` as module ``name``; optionally register it in ``sys.modules``."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load module {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    if register:
        sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
