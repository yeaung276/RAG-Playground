"""Experiment scoring: the metrics, the pair's status, and where the golden text sits in
each retrieved chunk. Matching ignores whitespace and Thai digits, so highlights have to
map back onto the raw chunk text."""

import unittest

from app.schemas.experiment import Metric
from app.services.dataset.evaluation_service import EvaluationService, _normalize
from app.services.retrieval.retrieval_service import Retrieved

GOLD = "Refunds take 30 days. Contact billing."
SOURCE = "faq.md"


class FakeChunk:
    def __init__(self, content: str, source: str):
        self.content = content
        self.meta = {"source": source}


def hit(content: str, source: str = SOURCE) -> Retrieved:
    return Retrieved(chunk_id=content, chunk=FakeChunk(content, source))


class NormalizeTest(unittest.TestCase):
    def test_drops_whitespace_and_maps_thai_digits(self):
        self.assertEqual(_normalize("ภายใน ๓๐\nวัน")[0], "ภายใน30วัน")

    def test_index_points_back_into_the_raw_text(self):
        self.assertEqual(_normalize("a b\n c"), ("abc", [0, 2, 5]))


class ScoreTest(unittest.TestCase):
    def setUp(self):
        self.svc = EvaluationService()

    def score(self, retrieved, metrics=tuple(Metric)):
        return self.svc.score(retrieved, GOLD, SOURCE, list(metrics))

    def test_all_gold_found_is_full(self):
        scores, status, _ = self.score([hit("Refunds take 30 days."), hit("Contact billing.")])
        self.assertEqual(status, "full")
        self.assertEqual(
            scores,
            {"context_precision": 1.0, "context_recall": 1.0, "hit_rate": 1.0, "mrr": 1.0},
        )

    def test_some_gold_found_is_partial(self):
        scores, status, _ = self.score([hit("Unrelated."), hit("Refunds take 30 days.")])
        self.assertEqual(status, "partial")
        self.assertEqual(
            scores,
            {"context_precision": 0.5, "context_recall": 0.5, "hit_rate": 1.0, "mrr": 0.5},
        )

    def test_nothing_found_is_miss(self):
        scores, status, highlights = self.score([hit("Unrelated.")])
        self.assertEqual(status, "miss")
        self.assertEqual(set(scores.values()), {0.0})
        self.assertEqual(highlights, [[]])

    def test_nothing_retrieved_is_miss(self):
        scores, status, highlights = self.score([])
        self.assertEqual(status, "miss")
        self.assertEqual(set(scores.values()), {0.0})
        self.assertEqual(highlights, [])

    def test_gold_text_from_another_file_does_not_count(self):
        _, status, highlights = self.score([hit("Refunds take 30 days.", source="other.md")])
        self.assertEqual(status, "miss")
        self.assertEqual(highlights, [[]])

    def test_only_picked_metrics_are_returned(self):
        scores, _, _ = self.score([hit("Refunds take 30 days.")], metrics=[Metric.MRR])
        self.assertEqual(scores, {"mrr": 1.0})

    def test_status_does_not_depend_on_picked_metrics(self):
        _, status, _ = self.score([hit("Refunds take 30 days.")], metrics=[Metric.MRR])
        self.assertEqual(status, "partial")


class HighlightTest(unittest.TestCase):
    def setUp(self):
        self.svc = EvaluationService()

    def highlights(self, retrieved):
        return self.svc.score(retrieved, GOLD, SOURCE, [])[2]

    def test_span_covers_raw_text_across_whitespace_and_thai_digits(self):
        content = "Intro.\nRefunds  take\n๓๐ days. End."
        [[(start, end)]] = self.highlights([hit(content)])
        self.assertEqual(content[start:end], "Refunds  take\n๓๐ days.")

    def test_spans_are_in_chunk_order(self):
        content = "Contact billing. Refunds take 30 days."
        [spans] = self.highlights([hit(content)])
        self.assertEqual(
            [content[s:e] for s, e in spans], ["Contact billing.", "Refunds take 30 days."]
        )

    def test_one_list_per_retrieved_chunk(self):
        content = "Contact billing."
        empty, spans = self.highlights([hit("Unrelated."), hit(content)])
        self.assertEqual(empty, [])
        self.assertEqual([content[s:e] for s, e in spans], ["Contact billing."])


class AverageTest(unittest.TestCase):
    def test_means_each_metric_over_pairs(self):
        self.assertEqual(
            EvaluationService().average(
                [{"mrr": 1.0, "hit_rate": 1.0}, {"mrr": 0.0, "hit_rate": 1.0}]
            ),
            {"mrr": 0.5, "hit_rate": 1.0},
        )

    def test_no_pairs(self):
        self.assertEqual(EvaluationService().average([]), {})
