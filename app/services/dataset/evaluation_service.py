import re

from app.schemas.experiment import Metric, PairScoreStatus
from app.services.retrieval.retrieval_service import Retrieved

_THAI_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")


def _normalize(text: str) -> tuple[str, list[int]]:
    """Whitespace dropped, Thai digits made Arabic; plus each kept character's index in `text`."""
    kept = [(i, ch) for i, ch in enumerate(text.translate(_THAI_TO_ARABIC)) if not ch.isspace()]
    return "".join(ch for _, ch in kept), [i for i, _ in kept]


class EvaluationService:
    """Scores one pair's retrieval against its `context`, split into gold sentences.
    A retrieved chunk is relevant when it comes from the pair's source file and
    contains at least one of them."""

    def score(
        self, retrieved: list[Retrieved], context: str, source: str, metrics: list[Metric]
    ) -> tuple[dict[str, float], PairScoreStatus, list[list[tuple[int, int]]]]:
        gold = [_normalize(s)[0] for s in _SENTENCE_BREAK.split(context) if s.strip()]
        found = [self._gold_in(hit, gold, source) for hit in retrieved]
        first = next((rank for rank, hits in enumerate(found, start=1) if hits), 0)
        covered = len(set().union(*found))

        values = {
            Metric.CONTEXT_PRECISION: sum(map(bool, found)) / len(found) if found else 0.0,
            Metric.CONTEXT_RECALL: covered / len(gold) if gold else 0.0,
            Metric.HIT_RATE: float(first > 0),
            Metric.MRR: 1 / first if first else 0.0,
        }
        # Status reads the gold text directly, so it exists whichever metrics were picked.
        status = "full" if gold and covered == len(gold) else "partial" if covered else "miss"
        highlights = [sorted(spans.values()) for spans in found]
        return {metric.value: values[metric] for metric in metrics}, status, highlights

    def average(self, scores: list[dict[str, float]]) -> dict[str, float]:
        if not scores:
            return {}
        return {metric: sum(s[metric] for s in scores) / len(scores) for metric in scores[0]}

    def _gold_in(self, hit: Retrieved, gold: list[str], source: str) -> dict[int, tuple[int, int]]:
        """Gold sentences this chunk holds, each with its span in the chunk's raw text."""
        if hit.chunk is None or (hit.chunk.meta or {}).get("source") != source:
            return {}
        content, index = _normalize(hit.chunk.content)
        spans = {}
        for i, sentence in enumerate(gold):
            at = content.find(sentence)
            if at >= 0:
                spans[i] = (index[at], index[at + len(sentence) - 1] + 1)
        return spans
