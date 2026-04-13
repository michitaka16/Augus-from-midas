#!/usr/bin/env python3
"""Start the Midas API server with correct package paths."""

import sys
from pathlib import Path

# Add all package src dirs to path
_root = Path(__file__).parent.parent
for pkg_dir in (_root / "packages").iterdir():
    src = pkg_dir / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))
for app_dir in (_root / "apps").iterdir():
    src = app_dir / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))

from midas_api.__main__ import main
main()
