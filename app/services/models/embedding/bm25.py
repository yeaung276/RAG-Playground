import asyncio
import hashlib
import re
from collections import Counter

from pythainlp.tokenize import word_tokenize
from pythainlp.util import normalize
from qdrant_client import models

BM25_K1 = 1.2
BM25_B = 0.75
BM25_AVG_DOC_LEN = 256

# markup: tags between two terms must become separators, else
# `<td>12</td><td>12</td>` collapses into `1212` and `Nickel<br/>25` into `nickel25`.
# `<page_number>- ๒ -</page_number>` is the exception — header digits collide with
# denominations and B.E. years, so tag and content both go.
MARKUP_PAGE_NUMBER = re.compile(r"<page_number>.*?</page_number>", re.I | re.S)
MARKUP_LINE_BREAK = re.compile(r"<br\s*/?>", re.I)
MARKUP_CELL_END = re.compile(r"</t[dh]>", re.I)
MARKUP_ROW_END = re.compile(r"</tr>", re.I)
MARKUP_TAG = re.compile(r"<[^>]+>")
# `[^\S\n]` not `\s`: separator runs collapse, but `</td></tr>` keeps its newline
# instead of merging every row onto one line
MARKUP_PIPE_RUN = re.compile(r"[^\S\n]*(\|[^\S\n]*)+")
MARKUP_EDGE_PIPE = re.compile(r"^ \| | \| $", re.M)

# terms: corpus writes `พ.ศ. ๒๕๑๖` / `๑,๐๐๐`, queries write `พ.ศ. 2516` / `1,000`
TERM_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
TERM_DIGIT_GROUPING = re.compile(r"(?<=\d),(?=\d\d\d)")
# `ๆ` repeats the word before it — dropping it makes `ต่างๆ` and `ต่าง ๆ` agree
TERM_MAIYAMOK = re.compile(r"\s*ๆ")
# joins two terms rather than belonging to either: `Bi-metal`, `กรัม / gm.`
TERM_JOINER = re.compile(r"[-–—/\\]")
# edge only, so `พ.ศ.` -> `พ.ศ` and `96.5` keep their insides
TERM_EDGE = "\"'“”‘’()[]{}<>:;,.|/\\-–—…!?*=+#&~`"
# a slot is worth spending only on a Thai letter, a Latin letter or a digit
TERM_KEEP = re.compile(r"[ก-ฮะ-์a-zA-Z0-9]")


class Bm25Embedder:
    """Term vectors for a `bm25` sparse index.

    Values carry only BM25's term-frequency half: the collection declares
    `modifier=IDF`, so Qdrant supplies the corpus half at query time. `indices` are
    token hashes, so the tokenizer and hash here must match the ones used to encode
    a query, or the two vectors address different terms — hence blake2b rather than
    the builtin `hash`, which is salted per process.
    """

    def __init__(self, model: str = "bm25"):
        self.model = model

    async def embed(self, texts: list[str]) -> list[models.SparseVector]:
        if not texts:
            return []
        if len(texts) == 1:
            return [self._encode(texts[0])]
        # newmm runs ~2 ms per chunk
        return await asyncio.to_thread(lambda: [self._encode(t) for t in texts])

    def _encode(self, text: str) -> models.SparseVector:
        tokens = self._tokenize(text)
        counts = Counter(self._token_id(token) for token in tokens)
        norm = BM25_K1 * (1 - BM25_B + BM25_B * len(tokens) / BM25_AVG_DOC_LEN)
        return models.SparseVector(
            indices=list(counts),
            values=[tf * (BM25_K1 + 1) / (tf + norm) for tf in counts.values()],
        )

    def _tokenize(self, text: str) -> list[str]:
        text = normalize(self._linearize(text))
        text = TERM_DIGIT_GROUPING.sub("", text.translate(TERM_THAI_DIGITS))
        text = TERM_JOINER.sub(" ", TERM_MAIYAMOK.sub("", text))
        terms = (
            piece.strip(TERM_EDGE)
            for token in word_tokenize(text, engine="newmm", keep_whitespace=False)
            # newmm returns a few multi-word units; split them so a query naming
            # one of the words still hits
            for piece in token.split()
        )
        return [term.lower() for term in terms if TERM_KEEP.search(term)]

    def _linearize(self, text: str) -> str:
        """Extraction markup -> text: cells joined by ` | `, rows by newline."""
        text = MARKUP_PAGE_NUMBER.sub(" ", text)
        text = MARKUP_LINE_BREAK.sub(" ", text)
        text = MARKUP_CELL_END.sub(" | ", text)
        text = MARKUP_ROW_END.sub("\n", text)
        text = MARKUP_TAG.sub(" ", text)
        text = MARKUP_PIPE_RUN.sub(" | ", text)
        return MARKUP_EDGE_PIPE.sub("", text)

    def _token_id(self, token: str) -> int:
        return int.from_bytes(
            hashlib.blake2b(token.encode(), digest_size=4).digest(), "big"
        )