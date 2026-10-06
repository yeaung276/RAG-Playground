import asyncio

import pytest
from langchain_core.documents import Document as LCDocument
from langchain_core.embeddings import Embeddings

from app.services.retrieval.chunking import (
    CHILD_CHUNK_SIZE,
    FixedSizeChunker,
    RecursiveChunker,
    SemanticChunker,
)
from app.services.retrieval.chunking.semantic import _CappedSemanticSplitter
from app.services.retrieval.document import Document, Page


def _doc(*markdowns: str) -> Document:
    return Document(pages=[Page(index=i, markdown=m) for i, m in enumerate(markdowns)])


def _by_id(chunks):
    return {c.id: c for c in chunks}


class FakeEmbeddings(Embeddings):
    """Deterministic vectors: a sentence mentioning 'TOPIC_B' is orthogonal to the
    rest, so the semantic splitter sees a hard breakpoint at the topic change."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 1.0] if "TOPIC_B" in t else [1.0, 0.0] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]


# ── two-step structure & parent/child links ─────────────────────────────────

def test_recursive_produces_parents_and_children():
    corpus = RecursiveChunker(max_chunk_size=500).chunk(_doc("A" * 400, "B" * 600))
    assert corpus.parents
    assert corpus.children


def test_parents_have_no_parent_id_children_do():
    corpus = RecursiveChunker(max_chunk_size=500).chunk(_doc("A" * 800))
    assert all(p.parent_id is None for p in corpus.parents)
    assert all(c.parent_id is not None for c in corpus.children)


def test_children_reference_existing_parents():
    corpus = RecursiveChunker(max_chunk_size=300).chunk(_doc("A" * 900, "B" * 900))
    parent_ids = {p.id for p in corpus.parents}
    assert corpus.children
    assert all(c.parent_id in parent_ids for c in corpus.children)


def test_every_parent_has_at_least_one_child():
    corpus = RecursiveChunker(max_chunk_size=300).chunk(_doc("A" * 900, "B" * 900))
    with_children = {c.parent_id for c in corpus.children}
    assert {p.id for p in corpus.parents} == with_children


def test_children_are_slices_of_their_parent():
    corpus = RecursiveChunker(max_chunk_size=400).chunk(_doc("hello world. " * 80))
    parents = _by_id(corpus.parents)
    assert all(c.content in parents[c.parent_id].content for c in corpus.children)


def test_ids_are_unique_across_parents_and_children():
    corpus = RecursiveChunker(max_chunk_size=300).chunk(_doc("A" * 900, "B" * 900))
    ids = [c.id for c in corpus.parents + corpus.children]
    assert len(ids) == len(set(ids))


# ── page tracking ────────────────────────────────────────────────────────────

def test_children_carry_no_page_metadata():
    corpus = RecursiveChunker(max_chunk_size=300).chunk(_doc("A" * 900))
    assert all(c.metadata == {} for c in corpus.children)


def test_single_page_parents_attributed_to_that_page():
    # large "\n\n"-separated pages -> the splitter cuts on the page joins,
    # so each parent lands entirely inside one page
    corpus = RecursiveChunker(max_chunk_size=400).chunk(_doc("A" * 350, "B" * 350))
    assert len(corpus.parents) == 2
    assert corpus.parents[0].metadata["pages"] == [0]
    assert corpus.parents[1].metadata["pages"] == [1]


def test_parent_that_merges_pages_spans_them():
    # small pages that all fit under max_chunk_size merge into one parent
    corpus = RecursiveChunker(max_chunk_size=1000).chunk(_doc("alpha", "beta", "gamma"))
    assert len(corpus.parents) == 1
    assert corpus.parents[0].metadata["pages"] == [0, 1, 2]


def test_parent_straddling_a_page_boundary_lists_both_pages():
    # max=650: pages 0+1 (300+2+300=602) merge, page 2 (300) is a second parent
    corpus = RecursiveChunker(max_chunk_size=650).chunk(_doc("A" * 300, "B" * 300, "C" * 300))
    assert [p.metadata["pages"] for p in corpus.parents] == [[0, 1], [2]]


def test_every_page_is_attributed_and_never_empty():
    corpus = RecursiveChunker(max_chunk_size=400).chunk(
        _doc("A" * 800, "B" * 800, "C" * 800)
    )
    seen = {idx for p in corpus.parents for idx in p.metadata["pages"]}
    assert seen == {0, 1, 2}
    assert all(p.metadata["pages"] for p in corpus.parents)


def test_page_attribution_uses_page_index_not_position():
    # non-contiguous Page.index values must propagate verbatim
    doc = Document(pages=[Page(index=5, markdown="alpha"), Page(index=9, markdown="beta")])
    corpus = RecursiveChunker(max_chunk_size=1000).chunk(doc)
    assert corpus.parents[0].metadata["pages"] == [5, 9]


# ── child sizing (HTML-aware splitter) ──────────────────────────────────────

def test_children_respect_dedicated_size():
    corpus = RecursiveChunker(max_chunk_size=4000).chunk(
        _doc("word " * 4000), parent_as_child=False
    )
    # child splitter caps around CHILD_CHUNK_SIZE (allow slack for the last token)
    assert max(len(c.content) for c in corpus.children) <= CHILD_CHUNK_SIZE + 50


def test_parent_is_also_indexed_as_a_child():
    corpus = RecursiveChunker(max_chunk_size=4000).chunk(
        _doc("word " * 200), parent_as_child=True
    )
    parent = corpus.parents[0]
    assert parent.content in [c.content for c in corpus.children]
    assert all(c.parent_id == parent.id for c in corpus.children)


def test_parent_as_child_can_be_disabled():
    corpus = RecursiveChunker(max_chunk_size=4000).chunk(
        _doc("word " * 200), parent_as_child=False
    )
    assert corpus.parents[0].content not in [c.content for c in corpus.children]


def test_html_table_content_is_chunked_without_error():
    html = "<table>" + "".join(f"<tr><td>row {i}</td></tr>" for i in range(200)) + "</table>"
    corpus = RecursiveChunker(max_chunk_size=2000).chunk(_doc(html))
    parents = _by_id(corpus.parents)
    assert corpus.children
    assert all(c.content in parents[c.parent_id].content for c in corpus.children)


# ── fixed-size strategy ──────────────────────────────────────────────────────

def test_fixed_size_chunker_runs():
    corpus = FixedSizeChunker(max_chunk_size=500).chunk(_doc("A" * 400, "B" * 600))
    assert corpus.parents
    assert all(c.parent_id is not None for c in corpus.children)


# ── empty input ──────────────────────────────────────────────────────────────

def test_empty_document_yields_empty_corpus():
    corpus = RecursiveChunker(max_chunk_size=500).chunk(_doc())
    assert corpus.parents == []
    assert corpus.children == []


# ── semantic: capped splitter (unit) ─────────────────────────────────────────

def test_capped_semantic_splitter_enforces_max():
    text = "the coin is round. " * 60  # one topic -> semantic keeps it whole
    splitter = _CappedSemanticSplitter(FakeEmbeddings(), min_chunk_size=50, max_chunk_size=300)
    docs = splitter.split_documents([LCDocument(page_content=text)])
    assert len(docs) > 1
    assert max(len(d.page_content) for d in docs) <= 300


def test_capped_semantic_splitter_keeps_absolute_offsets():
    text = "the coin is round. " * 60
    splitter = _CappedSemanticSplitter(FakeEmbeddings(), min_chunk_size=50, max_chunk_size=300)
    docs = splitter.split_documents([LCDocument(page_content=text)])
    # each chunk sits exactly where its start_index claims in the source
    assert all(
        text[d.metadata["start_index"]:d.metadata["start_index"] + len(d.page_content)]
        == d.page_content
        for d in docs
    )


# ── semantic chunker (mocked embedding model) ────────────────────────────────

class TopicEmbedder:
    """Async Embedder like ModelService resolves: 'TOPIC_B' sentences are orthogonal
    to the rest. Records every batch it is asked to embed."""

    def __init__(self, model: str = "topic"):
        self.model = model
        self.batches: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(texts)
        return [[0.0, 1.0] if "TOPIC_B" in t else [1.0, 0.0] for t in texts]


async def _semantic_chunk(embedder, document, **sizes):
    # built on the loop, run on a worker thread — the way IndexingService drives it
    chunker = SemanticChunker(embedder=embedder, **sizes)
    return await asyncio.to_thread(chunker.chunk, document)


async def test_semantic_chunker_splits_on_topic_change():
    alpha = "The coin is round. " * 4
    beta = "TOPIC_B is unrelated. " * 4
    corpus = await _semantic_chunk(
        TopicEmbedder(), _doc(alpha + beta), max_chunk_size=5000, min_chunk_size=10
    )
    # the topic change forces a break: first parent is pure topic-A, topic-B lands later
    assert len(corpus.parents) >= 2
    assert "TOPIC_B" not in corpus.parents[0].content
    assert "TOPIC_B" in corpus.parents[-1].content


async def test_semantic_chunker_caps_and_attributes_pages():
    corpus = await _semantic_chunk(
        TopicEmbedder(), _doc("the coin is round. " * 60),
        max_chunk_size=300, min_chunk_size=50,
    )
    assert corpus.parents
    assert max(len(p.content) for p in corpus.parents) <= 300
    assert all(p.metadata["pages"] == [0] for p in corpus.parents)


async def test_semantic_chunker_embeds_with_the_embedder_it_was_given():
    embedder = TopicEmbedder()
    await _semantic_chunk(
        embedder, _doc("The coin is round. TOPIC_B is unrelated. " * 3),
        max_chunk_size=5000, min_chunk_size=10,
    )
    assert embedder.batches
    assert all(isinstance(t, str) for batch in embedder.batches for t in batch)


async def test_semantic_chunkers_do_not_share_an_embedder():
    """Each KB brings its own chunking model, so one chunker must never reuse
    another's."""
    first, second = TopicEmbedder("first"), TopicEmbedder("second")
    await _semantic_chunk(first, _doc("The coin is round. " * 4), max_chunk_size=5000, min_chunk_size=10)
    await _semantic_chunk(second, _doc("The coin is round. " * 4), max_chunk_size=5000, min_chunk_size=10)
    assert first.batches and second.batches


async def test_semantic_chunker_surfaces_embedder_failures():
    class Failing(TopicEmbedder):
        async def embed(self, texts):
            raise RuntimeError("endpoint down")

    with pytest.raises(RuntimeError, match="endpoint down"):
        await _semantic_chunk(
            Failing(), _doc("The coin is round. TOPIC_B is unrelated. " * 3),
            max_chunk_size=5000, min_chunk_size=10,
        )
