"""Which of a question's gold sentences does a retrieved chunk contain?

Returns the gold-sentence indices found in the chunk's text (empty if none).
Matching is text-only: a normalized gold sentence appearing in the normalized
chunk content counts as a hit.

When `source_doc` is given, a chunk from any other document scores nothing even
if its text matches. Thai legal boilerplate repeats verbatim across acts and
regulations, so without that check a chunk from an unrelated law counts as a hit.
"""
from __future__ import annotations

from commands.eval_utils.utils.text import normalize


def gold_sentences_in_chunk(chunk, gold_texts: list[str], source_doc: str | None = None) -> set[int]:
    if source_doc is not None and (chunk.meta or {}).get("source") != source_doc:
        return set()
    content = normalize(chunk.content)
    return {i for i, sentence in enumerate(gold_texts) if sentence and normalize(sentence) in content}
