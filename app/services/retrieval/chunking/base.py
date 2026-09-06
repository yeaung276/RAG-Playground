from abc import ABC
from typing import Protocol

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from app.db.ids import new_id
from app.services.retrieval.document import Chunk, Corpus, Document

# Child chunks have their own dedicated lengths, independent of the parent config.
CHILD_CHUNK_SIZE = 512
CHILD_CHUNK_OVERLAP = 40


class _DocSplitter(Protocol):
    def split_documents(self, documents: list[LCDocument]) -> list[LCDocument]: ...


class Chunker(ABC):
    """Two-step chunking. The parent splitter varies by strategy (subclasses set
    it); the child splitter is always an HTML-aware recursive splitter."""

    parent_splitter: _DocSplitter

    def __init__(self):
        self.child_splitter = RecursiveCharacterTextSplitter.from_language(
            Language.HTML, chunk_size=CHILD_CHUNK_SIZE, chunk_overlap=CHILD_CHUNK_OVERLAP
        )

    def chunk(self, document: Document, *, parent_as_child: bool = False) -> Corpus:
        # concat pages, recording each page's [start, end) span in the combined text
        spans, parts, pos = [], [], 0
        for page in document.pages:
            spans.append((pos, pos + len(page.markdown), page.index))
            parts.append(page.markdown)
            pos += len(page.markdown) + 2  # +2 for the "\n\n" join
        combined = "\n\n".join(parts)

        def pages_at(start: int, length: int) -> list[int]:
            end = start + length
            return [idx for s, e, idx in spans if s < end and start < e]

        corpus = Corpus()
        merged = LCDocument(page_content=combined)
        for parent in self.parent_splitter.split_documents([merged]):
            pid = new_id()
            p_start = parent.metadata["start_index"]
            corpus.parents.append(
                Chunk(
                    id=pid,
                    content=parent.page_content,
                    metadata={"pages": pages_at(p_start, len(parent.page_content))},
                )
            )

            if parent_as_child:
                corpus.children.append(
                    Chunk(id=new_id(), content=parent.page_content, parent_id=pid)
                )
            for child in self.child_splitter.split_documents([parent]):
                corpus.children.append(
                    Chunk(id=new_id(), content=child.page_content, parent_id=pid)
                )
        return corpus
