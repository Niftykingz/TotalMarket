"""TotalMarket AI newsroom: one Boss (editor-in-chief) coordinating specialist agents.

Phase 1 (this package): Boss, News Research, Content Writer, Independent Fact Checker and
Graphic Designer agents, a SQLite store, a free deterministic mock AI provider and a local
demo. Nothing here publishes, deploys, merges or spends money; production publishing is
disabled in code (see permissions.PRODUCTION_PUBLISHING).

Run the demo:   py -m newsroom demo        (Windows)
                python3 -m newsroom demo   (Linux/macOS)
"""
__version__ = "0.1.0-phase1"

import sys as _sys
from pathlib import Path as _Path

_ROOT = str(_Path(__file__).resolve().parent.parent)
if _ROOT not in _sys.path:  # site modules (cover_templates, tmdate) live in the repo root
    _sys.path.insert(0, _ROOT)
