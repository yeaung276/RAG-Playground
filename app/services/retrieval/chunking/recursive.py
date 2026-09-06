from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.retrieval.chunking.base import Chunker


class RecursiveChunker(Chunker):
    def __init__(self, max_chunk_size: int):
        super().__init__()
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chunk_size, chunk_overlap=0, add_start_index=True
        )
