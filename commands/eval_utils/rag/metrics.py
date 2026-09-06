"""Retrieval metrics for the RAG eval.

Each metric is its own class — they do not share an interface, because they do
not aggregate the same way. Recall and Precision are ratios of running counts
across the whole dataset; MRR, MAP and nDCG average a per-question value. Every
metric keeps its tallies split by question `type` so results can be broken down
per category.

A retrieved chunk only counts for a question when it comes from that question's
`source_doc` — see `gold_sentences_in_chunk`.

Usage:
    m = Recall(k=5)
    for q in dataset:
        m.add(retrieve(q), q.relevant, q.type, q.source_doc)
    m.overall()    # single number over the whole dataset
    m.by_type()    # {"literal": .., "list": .., ...}
"""
from __future__ import annotations

import math
from collections import defaultdict

from app.services.retrieval.retrieval_service import Retrieved
from commands.eval_utils.rag.dataloaders import Relevant
from commands.eval_utils.utils.matching import gold_sentences_in_chunk


class Recall:
    """recall@k = gold sentences found in the top-k / all gold sentences."""

    key = "recall"

    def __init__(self, k: int):
        self.k = k
        self.found: dict[str, int] = defaultdict(int)
        self.total: dict[str, int] = defaultdict(int)

    def add(self, retrieved: list[Retrieved], relevant: list[Relevant], qtype: str,
            source_doc: str) -> None:
        gold = [r.gold_text for r in relevant]
        hits: set[int] = set()
        for result in retrieved[: self.k]:
            hits |= gold_sentences_in_chunk(result.chunk, gold, source_doc)
        self.found[qtype] += len(hits)
        self.total[qtype] += len(gold)

    def overall(self) -> float:
        found, total = sum(self.found.values()), sum(self.total.values())
        return found / total if total else 0.0

    def by_type(self) -> dict[str, float]:
        return {t: self.found[t] / self.total[t] for t in self.total if self.total[t]}


class Precision:
    """precision@k = correct chunks in the top-k / chunks retrieved."""

    key = "precision"

    def __init__(self, k: int):
        self.k = k
        self.correct: dict[str, int] = defaultdict(int)
        self.retrieved: dict[str, int] = defaultdict(int)

    def add(self, retrieved: list[Retrieved], relevant: list[Relevant], qtype: str,
            source_doc: str) -> None:
        gold = [r.gold_text for r in relevant]
        top = retrieved[: self.k]
        self.correct[qtype] += sum(1 for result in top if gold_sentences_in_chunk(result.chunk, gold, source_doc))
        self.retrieved[qtype] += len(top)

    def overall(self) -> float:
        correct, retrieved = sum(self.correct.values()), sum(self.retrieved.values())
        return correct / retrieved if retrieved else 0.0

    def by_type(self) -> dict[str, float]:
        return {t: self.correct[t] / self.retrieved[t] for t in self.retrieved if self.retrieved[t]}


class MRR:
    """1 / rank of the first correct chunk, averaged over questions."""

    key = "mrr"

    def __init__(self, k: int):
        self.k = k
        self.values: dict[str, list[float]] = defaultdict(list)

    def add(self, retrieved: list[Retrieved], relevant: list[Relevant], qtype: str,
            source_doc: str) -> None:
        gold = [r.gold_text for r in relevant]
        reciprocal = 0.0
        for rank, result in enumerate(retrieved[: self.k], start=1):
            if gold_sentences_in_chunk(result.chunk, gold, source_doc):
                reciprocal = 1.0 / rank
                break
        self.values[qtype].append(reciprocal)

    def overall(self) -> float:
        every = [v for values in self.values.values() for v in values]
        return sum(every) / len(every) if every else 0.0

    def by_type(self) -> dict[str, float]:
        return {t: sum(values) / len(values) for t, values in self.values.items() if values}


class MAP:
    """Average precision per question, averaged over questions."""

    key = "map"

    def __init__(self, k: int):
        self.k = k
        self.values: dict[str, list[float]] = defaultdict(list)

    def add(self, retrieved: list[Retrieved], relevant: list[Relevant], qtype: str,
            source_doc: str) -> None:
        gold = [r.gold_text for r in relevant]
        correct = 0
        running = 0.0
        for rank, result in enumerate(retrieved[: self.k], start=1):
            if gold_sentences_in_chunk(result.chunk, gold, source_doc):
                correct += 1
                running += correct / rank
        average_precision = running / min(len(gold), self.k) if gold else 0.0
        self.values[qtype].append(average_precision)

    def overall(self) -> float:
        every = [v for values in self.values.values() for v in values]
        return sum(every) / len(every) if every else 0.0

    def by_type(self) -> dict[str, float]:
        return {t: sum(values) / len(values) for t, values in self.values.items() if values}


class NDCG:
    """DCG / IDCG per question, averaged over questions."""

    key = "ndcg"

    def __init__(self, k: int):
        self.k = k
        self.values: dict[str, list[float]] = defaultdict(list)

    def add(self, retrieved: list[Retrieved], relevant: list[Relevant], qtype: str,
            source_doc: str) -> None:
        gold = [r.gold_text for r in relevant]
        dcg = 0.0
        for rank, result in enumerate(retrieved[: self.k]):
            if gold_sentences_in_chunk(result.chunk, gold, source_doc):
                dcg += 1.0 / math.log2(rank + 2)
        ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(gold), self.k)))
        self.values[qtype].append(dcg / ideal if ideal else 0.0)

    def overall(self) -> float:
        every = [v for values in self.values.values() for v in values]
        return sum(every) / len(every) if every else 0.0

    def by_type(self) -> dict[str, float]:
        return {t: sum(values) / len(values) for t, values in self.values.items() if values}


METRICS = {cls.key: cls for cls in (Recall, Precision, MRR, MAP, NDCG)}


def build_metrics(names: list[str], top_ks: list[int]) -> list:
    """One metric object per (name, k). Raises on an unknown metric name."""
    unknown = [n for n in names if n not in METRICS]
    if unknown:
        raise ValueError(f"Unknown metric(s): {unknown}. Known: {sorted(METRICS)}")
    return [METRICS[name](k) for name in names for k in top_ks]
