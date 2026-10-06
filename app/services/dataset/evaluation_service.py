import re

from app.schemas.experiment import Metric
from app.services.retrieval.retrieval_service import Retrieved

_THAI_TO_ARABIC = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+|\n+")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.translate(_THAI_TO_ARABIC))


class EvaluationService:
    """Scores one pair's retrieval against its `context`, split into gold sentences.
    A retrieved chunk is relevant when it comes from the pair's source file and
    contains at least one of them."""

    def score(
        self, retrieved: list[Retrieved], context: str, source: str, metrics: list[Metric]
    ) -> dict[str, float]:
        gold = [_normalize(s) for s in _SENTENCE_BREAK.split(context) if s.strip()]
        found = [self._gold_in(hit, gold, source) for hit in retrieved]
        first = next((rank for rank, hits in enumerate(found, start=1) if hits), 0)

        values = {
            Metric.CONTEXT_PRECISION: sum(map(bool, found)) / len(found) if found else 0.0,
            Metric.CONTEXT_RECALL: len(set().union(*found)) / len(gold) if gold else 0.0,
            Metric.HIT_RATE: float(first > 0),
            Metric.MRR: 1 / first if first else 0.0,
        }
        return {metric.value: values[metric] for metric in metrics}

    def average(self, scores: list[dict[str, float]]) -> dict[str, float]:
        if not scores:
            return {}
        return {metric: sum(s[metric] for s in scores) / len(scores) for metric in scores[0]}

    def _gold_in(self, hit: Retrieved, gold: list[str], source: str) -> set[int]:
        if hit.chunk is None or (hit.chunk.meta or {}).get("source") != source:
            return set()
        content = _normalize(hit.chunk.content)
        return {i for i, sentence in enumerate(gold) if sentence in content}
