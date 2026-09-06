"""Dataset loaders for RAG evaluation.

A loader reads a source (local dir or HuggingFace dataset) and yields the shape
the downstream pipeline expects — `Document` for the corpus, `QAItem` for the
eval set — one record at a time so nothing is held in memory in bulk. `total()`
is a cheap scan (dir listing / line count / hub metadata) so a progress bar can
be sized before iteration begins.

`Document`/`Page` are pydantic-only (no db engine), safe to import at load time.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

from pydantic import BaseModel

from app.services.retrieval.document import Document, Page
from commands.eval_utils.utils import hf, io

HF_PREFIX = "hf:"


# ---- QA schema -------------------------------------------------------------

class Relevant(BaseModel):
    page: int | None = None
    section: str | None = None
    gold_text: str | None = None


class QAItem(BaseModel):
    id: str | None = None
    question: str
    question_paraphrase: str | None = None
    answer: str | None = None
    type: str | None = None
    relevant: list[Relevant] = []
    source_doc: str


def _to_document(row: dict, filename_field: str, chunks_field: str) -> Document:
    chunks = row.get(chunks_field) or []
    return Document(
        source=row.get(filename_field, ""),
        pages=[Page(index=c.get("seq", i), markdown=c["content"]) for i, c in enumerate(chunks)],
    )


# ---- corpus loaders --------------------------------------------------------

class CorpusLoader(ABC):
    """Streams the documents to be indexed."""

    @abstractmethod
    def total(self) -> int | None:
        """Document count for progress sizing, or None if unknowable."""

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[Document]: ...


class LocalCorpusLoader(CorpusLoader):
    """`<root>/texts/*.json`, each `{filename, chunks:[{seq, content}]}`."""

    def __init__(self, root: Path):
        self.dir = Path(root) / "texts"

    def _files(self) -> list[Path]:
        return sorted(self.dir.glob("*.json"))

    def total(self) -> int:
        return len(self._files())

    async def __aiter__(self) -> AsyncIterator[Document]:
        for path in self._files():
            row = await asyncio.to_thread(io.read_json, path)
            yield _to_document(row, "filename", "chunks")


class HFCorpusLoader(CorpusLoader):
    """A HuggingFace split whose rows carry `filename` + `chunks`."""

    def __init__(
        self,
        dataset_id: str,
        *,
        config: str | None = None,
        split: str = "corpus",
        filename_field: str = "filename",
        chunks_field: str = "chunks",
    ):
        self.dataset_id = dataset_id
        self.config = config
        self.split = split
        self.filename_field = filename_field
        self.chunks_field = chunks_field

    def total(self) -> int | None:
        return hf.split_size(self.dataset_id, self.config, self.split)

    async def __aiter__(self) -> AsyncIterator[Document]:
        for row in hf.stream(self.dataset_id, self.config, self.split):
            yield _to_document(row, self.filename_field, self.chunks_field)


# ---- qa loaders ------------------------------------------------------------

class QALoader(ABC):
    """Streams the eval questions with their gold relevance."""

    @abstractmethod
    def total(self) -> int | None: ...

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[QAItem]: ...


class LocalQALoader(QALoader):
    """`<root>/eval/*.jsonl`, one `QAItem` per line."""

    def __init__(self, root: Path, limit: int | None = None):
        self.dir = Path(root) / "eval"
        self.limit = limit

    def _files(self) -> list[Path]:
        return sorted(self.dir.glob("*.jsonl"))

    def total(self) -> int:
        n = sum(io.count_lines(f) for f in self._files())
        return min(n, self.limit) if self.limit else n

    async def __aiter__(self) -> AsyncIterator[QAItem]:
        seen = 0
        for path in self._files():
            for line in io.iter_jsonl(path):
                if self.limit and seen >= self.limit:
                    return
                seen += 1
                yield QAItem.model_validate_json(line)


class HFQALoader(QALoader):
    """A HuggingFace split whose rows carry `question`, `relevant`, `source_doc`."""

    def __init__(
        self,
        dataset_id: str,
        *,
        config: str | None = None,
        split: str = "eval",
        limit: int | None = None,
    ):
        self.dataset_id = dataset_id
        self.config = config
        self.split = split
        self.limit = limit

    def total(self) -> int | None:
        n = hf.split_size(self.dataset_id, self.config, self.split)
        if n is None:
            return None
        return min(n, self.limit) if self.limit else n

    async def __aiter__(self) -> AsyncIterator[QAItem]:
        for seen, row in enumerate(hf.stream(self.dataset_id, self.config, self.split)):
            if self.limit and seen >= self.limit:
                return
            yield QAItem.model_validate(row)


# ---- factories -------------------------------------------------------------

def build_corpus_loader(source: str) -> CorpusLoader:
    """`hf:<id>` → HuggingFace, otherwise a local dataset dir."""
    if source.startswith(HF_PREFIX):
        return HFCorpusLoader(source[len(HF_PREFIX):])
    return LocalCorpusLoader(Path(source))


def build_qa_loader(source: str, limit: int | None = None) -> QALoader:
    if source.startswith(HF_PREFIX):
        return HFQALoader(source[len(HF_PREFIX):], limit=limit)
    return LocalQALoader(Path(source), limit=limit)
