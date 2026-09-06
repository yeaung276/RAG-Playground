"""Text normalization shared across evaluation matching."""
from __future__ import annotations

import re

_THAI_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def normalize(s: str) -> str:
    """Fold Thai digits to Arabic and strip all whitespace for robust containment."""
    return re.sub(r"\s+", "", s.translate(_THAI_TO_ARABIC))
