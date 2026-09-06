"""HuggingFace dataset helpers shared across evaluation loaders.

`datasets` is imported lazily so the package stays importable without it.
"""
from __future__ import annotations

from collections.abc import Iterator


def split_size(dataset_id: str, config: str | None, split: str) -> int | None:
    """Row count from hub metadata only — no data download. None if unavailable."""
    try:
        from datasets import load_dataset_builder

        info = load_dataset_builder(dataset_id, config).info.splits.get(split)
        return info.num_examples if info else None
    except Exception:
        return None


def stream(dataset_id: str, config: str | None, split: str) -> Iterator[dict]:
    """Iterate a split row-by-row in streaming mode (nothing held in memory)."""
    from datasets import load_dataset

    return iter(load_dataset(dataset_id, config, split=split, streaming=True))
