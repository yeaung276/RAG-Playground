"""Filesystem helpers shared across evaluation loaders."""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def count_lines(path: Path) -> int:
    """Non-blank line count via a single streaming scan (no full read)."""
    with path.open(encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def iter_jsonl(path: Path) -> Iterator[str]:
    """Yield non-blank, stripped lines one at a time."""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield line
