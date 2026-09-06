import asyncio

from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker as LCSemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.retrieval.chunking.base import Chunker
from app.services.retrieval.embedding import TEIEmbedder

TEI_MAX_BATCH = 32


class _TEIEmbeddings(Embeddings):
    """Synchronous langchain Embeddings backed by the async TEIEmbedder (bge-m3).
    Embeds in batches of TEI_MAX_BATCH and returns vectors in input order. Callable
    from a worker thread; must be constructed on the event loop it dispatches to."""

    def __init__(self):
        self._embedder = TEIEmbedder("BAAI/bge-m3")
        self._loop = asyncio.get_running_loop()

    def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        return asyncio.run_coroutine_threadsafe(
            self._embedder.embed(batch), self._loop
        ).result()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), TEI_MAX_BATCH):
            out.extend(self._embed_batch(texts[i : i + TEI_MAX_BATCH]))
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class _CappedSemanticSplitter:
    """Semantic split, then hard-cap: re-split any oversized parent with a
    recursive splitter at max_chunk_size, preserving absolute start_index."""

    def __init__(self, embeddings: Embeddings, min_chunk_size: int, max_chunk_size: int):
        self._max = max_chunk_size
        self._semantic = LCSemanticChunker(
            embeddings, add_start_index=True, min_chunk_size=min_chunk_size
        )
        self._cap = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size, chunk_overlap=0, add_start_index=True
        )

    def split_documents(self, documents: list[LCDocument]) -> list[LCDocument]:
        out = []
        for doc in self._semantic.split_documents(documents):
            if len(doc.page_content) <= self._max:
                out.append(doc)
                continue
            base = doc.metadata["start_index"]
            for sub in self._cap.split_documents([doc]):
                # cap start_index is relative to the parent; make it absolute again
                sub.metadata["start_index"] = base + sub.metadata["start_index"]
                out.append(sub)
        return out


class SemanticChunker(Chunker):
    _embeddings: _TEIEmbeddings | None = None

    def __init__(self, max_chunk_size: int, min_chunk_size: int):
        super().__init__()
        if SemanticChunker._embeddings is None:
            SemanticChunker._embeddings = _TEIEmbeddings()
        self.parent_splitter = _CappedSemanticSplitter(
            SemanticChunker._embeddings,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
        )
