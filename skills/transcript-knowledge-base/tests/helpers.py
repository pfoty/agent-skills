"""Shared test helpers: ensure the package is importable and make temp folders."""

from __future__ import annotations

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def temp_dir() -> str:
    return tempfile.mkdtemp(prefix="tkb_test_")


def write(folder: str, name: str, content: str) -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path
