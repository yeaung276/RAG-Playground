"""Snippets below are copied verbatim from datasets/thai-treasury/, one per markup
or term pattern that actually occurs in the corpus. Expected term lists are the
ones a BM25 index wants — not a claim about ideal Thai segmentation."""

import unittest

from app.services.retrieval.embedding import Bm25Embedder
from app.services.retrieval.embedding.bm25 import BM25_AVG_DOC_LEN, BM25_B, BM25_K1


class TokenizeMarkupTest(unittest.TestCase):
    """Table markup carries most of the corpus' facts, so it has to survive."""

    def setUp(self):
        self.embedder = Bm25Embedder()

    def test_cells_stay_separate_terms(self):
        self.assertEqual(
            self.embedder._tokenize(
                "<tr><td>น้ำหนัก / Weight (กรัม / gm.)</td><td>12</td><td>12</td></tr>"
            ),
            ["น้ำหนัก", "weight", "กรัม", "gm", "12", "12"],
        )

    def test_rows_stay_separate_lines(self):
        linearized = self.embedder._linearize(
            "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>"
        )
        self.assertEqual(
            [line.strip() for line in linearized.split("\n")], ["a | b", "c | d", ""]
        )

    def test_span_attributes_leak_no_digits(self):
        self.assertEqual(
            self.embedder._tokenize(
                '<td rowspan="2">ราคา / Denomination (บาท / Baht)</td><td>600</td>'
            ),
            ["ราคา", "denomination", "บาท", "baht", "600"],
        )

    def test_header_cells_behave_like_cells(self):
        self.assertEqual(
            self.embedder._tokenize('<th colspan="2">โลหะสองสี Bi-metal</th>'),
            ["โลหะ", "สอง", "สี", "bi", "metal"],
        )

    def test_line_break_inside_cell_separates(self):
        self.assertEqual(
            self.embedder._tokenize("<td>นิกเกิล / Nickel<br/>25</td>"),
            ["นิกเกิล", "nickel", "25"],
        )

    def test_empty_and_placeholder_cells_yield_nothing(self):
        self.assertEqual(self.embedder._tokenize("<tr><td></td><td>-</td></tr>"), [])

    def test_page_number_content_is_dropped_with_its_tag(self):
        self.assertEqual(
            self.embedder._tokenize("<page_number>- ๒ -</page_number>\nมาตรา ๖"),
            ["มาตรา", "6"],
        )
        self.assertEqual(
            self.embedder._tokenize("<page_number>51</page_number>เหรียญ ๑๐ บาท"),
            ["เหรียญ", "10", "บาท"],
        )

    def test_figure_caption_is_kept(self):
        self.assertEqual(
            self.embedder._tokenize(
                "<figure>\nA gold-colored coin featuring a portrait of "
                "King Chulalongkorn.\n</figure>"
            ),
            ["a", "gold", "colored", "coin", "featuring", "a", "portrait",
             "of", "king", "chulalongkorn"],
        )


class TokenizeTermTest(unittest.TestCase):
    """Corpus and query spell the same fact differently; terms must still collide."""

    def setUp(self):
        self.embedder = Bm25Embedder()

    def test_thai_and_arabic_digits_give_the_same_terms(self):
        self.assertEqual(
            self.embedder._tokenize("มาตรา ๔ แห่งพระราชบัญญัติเงินตรา พ.ศ. ๒๕๐๑"),
            self.embedder._tokenize("มาตรา 4 แห่งพระราชบัญญัติเงินตรา พ.ศ. 2501"),
        )

    def test_section_reference_terms(self):
        self.assertEqual(
            self.embedder._tokenize("มาตรา ๔ แห่งพระราชบัญญัติเงินตรา พ.ศ. ๒๕๐๑"),
            ["มาตรา", "4", "แห่ง", "พระราชบัญญัติ", "เงินตรา", "พ.ศ", "2501"],
        )

    def test_grouped_and_plain_numbers_give_the_same_term(self):
        for text in ("๑,๐๐๐,๐๐๐ บาท", "1,000,000 บาท", "1000000 บาท"):
            with self.subTest(text=text):
                self.assertEqual(self.embedder._tokenize(text), ["1000000", "บาท"])

    def test_decimals_keep_their_point(self):
        self.assertEqual(self.embedder._tokenize("๘.๕ กรัม"), ["8.5", "กรัม"])
        self.assertEqual(
            self.embedder._tokenize("เงิน / Silver 92.50"), ["เงิน", "silver", "92.50"]
        )

    def test_list_marker_becomes_its_number(self):
        self.assertEqual(
            self.embedder._tokenize("(๑) รายจ่ายที่หักนั้น"),
            ["1", "รายจ่าย", "ที่", "หัก", "นั้น"],
        )

    def test_ranges_split_into_endpoints(self):
        self.assertEqual(
            self.embedder._tokenize("๒๐-๒๑ ตุลาคม ๒๕๔๖"), ["20", "21", "ตุลาคม", "2546"]
        )

    def test_maiyamok_spelling_does_not_matter(self):
        self.assertEqual(self.embedder._tokenize("ต่าง ๆ"), ["ต่าง"])
        self.assertEqual(self.embedder._tokenize("ต่างๆ"), ["ต่าง"])

    def test_abbreviations_keep_their_inner_dots(self):
        # only the trailing dot goes; `ป.ร.` is not in newmm's dictionary and does
        # split, which costs nothing here — the royal cipher is never queried
        self.assertEqual(
            self.embedder._tokenize("ให้ไว้ ณ วันที่ ๓๐ พฤษภาคม พ.ศ. ๒๕๑๖"),
            ["ให้", "ไว้", "ณ", "วันที่", "30", "พฤษภาคม", "พ.ศ", "2516"],
        )

    def test_latin_is_lowercased_and_digits_kept(self):
        self.assertEqual(
            self.embedder._tokenize('มีอักษรโรมันว่า "12th AUGUST 1980 THAILAND"'),
            ["มี", "อักษร", "โรมัน", "ว่า", "12th", "august", "1980", "thailand"],
        )

    def test_quotes_and_markdown_emphasis_are_stripped(self):
        self.assertEqual(
            self.embedder._tokenize('**Obverse:** "ค่าเสมอภาค” หมายความว่า'),
            ["obverse", "ค่าเสมอภาค", "หมายความว่า"],
        )

    def test_no_text_yields_no_terms(self):
        for text in ("", "   \n\t ", "<table><tr><td></td></tr></table>"):
            with self.subTest(text=text):
                self.assertEqual(self.embedder._tokenize(text), [])


class TokenizeInvariantTest(unittest.TestCase):
    """Properties that must hold for every term, whatever newmm decides."""

    CORPUS = [
        "<table><tr><td>รายละเอียด Specification</td><td>เงินขัดเงา Proof Silver</td>"
        "</tr><tr><td>ส่วนผสม / Composition (%)</td><td>เงิน / Silver 92.50</td></tr>"
        "</table>",
        "<td>โลหะสีขาว (วงนอก)<br/>White Metal (Ring)</td><td>นิกเกิล / Nickel<br/>25"
        "</td>",
        "<page_number>- ๒ -</page_number>\n\nมาตรา ๖ ให้ยกเลิกความในมาตรา ๑๐ แห่ง"
        "พระราชบัญญัติเงินคงคลัง พ.ศ. ๒๔๙๑ และให้ใช้ความต่อไปนี้แทน",
        "๑,๐๐๐,๐๐๐ บาท ชนิดราคา ๑ บาท ไม่เกิน ๓๐,๐๐๐ บาท",
        "มาตรา ๔ ให้เพิ่มความต่อไปนี้เป็นมาตรา ๓๔/๑ และมาตรา ๓๔/๒",
        "https://ecommerce.treasury.go.th/",
        '"๒๐-๒๑ ตุลาคม ๒๕๔๖ กรุงเทพฯ"\n\n**Obverse:**\nA portrait of King Bhumibol '
        "Adulyadej, with the legends \"King Bhumibol Adulyadej\" and \"Thailand\".",
    ]

    def setUp(self):
        self.terms = [
            term
            for text in self.CORPUS
            for term in Bm25Embedder()._tokenize(text)
        ]

    def test_terms_are_non_empty(self):
        self.assertTrue(self.terms)
        self.assertNotIn("", self.terms)

    def test_no_term_carries_markup(self):
        for term in self.terms:
            with self.subTest(term=term):
                self.assertNotRegex(term, r"[<>|]")

    def test_no_term_carries_whitespace(self):
        for term in self.terms:
            with self.subTest(term=term):
                self.assertNotRegex(term, r"\s")

    def test_no_term_is_pure_punctuation(self):
        for term in self.terms:
            with self.subTest(term=term):
                self.assertRegex(term, r"[ก-ฮะ-์a-z0-9]")

    def test_no_term_holds_thai_digits(self):
        for term in self.terms:
            with self.subTest(term=term):
                self.assertNotRegex(term, r"[๐-๙]")

    def test_no_term_is_uppercase(self):
        self.assertEqual(self.terms, [t.lower() for t in self.terms])


class TokenIdTest(unittest.TestCase):
    def setUp(self):
        self.embedder = Bm25Embedder()

    def test_token_id_is_stable_across_instances(self):
        self.assertEqual(
            Bm25Embedder()._token_id("qdrant"), Bm25Embedder()._token_id("qdrant")
        )

    def test_token_id_is_stable_across_runs(self):
        # Pinned: index-time and query-time ids must agree across processes, so this
        # value is part of the on-disk format. Changing it silently zeroes recall on
        # every existing collection.
        self.assertEqual(self.embedder._token_id("qdrant"), 3738887970)

    def test_token_id_differs_between_tokens(self):
        ids = {self.embedder._token_id(t) for t in ("alpha", "beta", "gamma", "delta")}
        self.assertEqual(len(ids), 4)

    def test_token_id_fits_u32(self):
        for token in ("a", "zz", "qdrant", "ยินดี", "เหรียญกษาปณ์"):
            with self.subTest(token=token):
                self.assertTrue(0 <= self.embedder._token_id(token) < 2**32)


class WeightingTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.embedder = Bm25Embedder()

    async def test_repeated_term_collapses_to_one_index(self):
        vector = (await self.embedder.embed(["เหรียญ เหรียญ เหรียญ"]))[0]
        self.assertEqual(len(vector.indices), 1)
        self.assertEqual(len(vector.values), 1)

    async def test_term_frequency_saturates_below_ceiling(self):
        values = [
            (await self.embedder.embed([" ".join(["เหรียญ"] * n)]))[0].values[0]
            for n in (1, 2, 5, 50)
        ]
        self.assertEqual(values, sorted(values))  # monotonic in tf
        self.assertTrue(all(v < BM25_K1 + 1 for v in values))  # never reaches k1 + 1

    async def test_longer_document_discounts_the_same_term(self):
        short = (await self.embedder.embed(["เหรียญ กษาปณ์"]))[0]
        long = (await self.embedder.embed(["เหรียญ " + "ทองแดง " * 200]))[0]
        term = self.embedder._token_id("เหรียญ")
        self.assertLess(
            long.values[long.indices.index(term)],
            short.values[short.indices.index(term)],
        )

    async def test_weight_matches_the_bm25_tf_formula(self):
        text = "เหรียญ กษาปณ์ เหรียญ"
        vector = (await self.embedder.embed([text]))[0]
        length = len(self.embedder._tokenize(text))
        norm = BM25_K1 * (1 - BM25_B + BM25_B * length / BM25_AVG_DOC_LEN)
        expected = 2 * (BM25_K1 + 1) / (2 + norm)  # "เหรียญ" occurs twice
        self.assertEqual(
            vector.values[vector.indices.index(self.embedder._token_id("เหรียญ"))],
            expected,
        )

    async def test_distinct_terms_each_get_an_index(self):
        vector = (await self.embedder.embed(["เหรียญ ทองแดง นิกเกิล"]))[0]
        self.assertEqual(len(vector.indices), 3)


class EmbedBatchTest(unittest.IsolatedAsyncioTestCase):
    """A batch is threaded off, a single query is not — both must agree."""

    def setUp(self):
        self.embedder = Bm25Embedder()

    async def test_returns_one_vector_per_text_in_order(self):
        vectors = await self.embedder.embed(["เหรียญ", "ธนบัตร", "เหรียญ"])
        self.assertEqual(len(vectors), 3)
        self.assertEqual(vectors[0].indices, vectors[2].indices)
        self.assertNotEqual(vectors[0].indices, vectors[1].indices)

    async def test_batched_and_single_encoding_agree(self):
        text = "<td>น้ำหนัก / Weight (กรัม / gm.)</td><td>๑๒</td>"
        single = (await self.embedder.embed([text]))[0]
        batched = (await self.embedder.embed([text, "filler"]))[0]
        self.assertEqual(single.indices, batched.indices)
        self.assertEqual(single.values, batched.values)

    async def test_empty_text_yields_empty_vector(self):
        vector = (await self.embedder.embed([""]))[0]
        self.assertEqual(vector.indices, [])
        self.assertEqual(vector.values, [])

    async def test_empty_batch(self):
        self.assertEqual(await self.embedder.embed([]), [])

    def test_model_name_defaults_to_bm25(self):
        self.assertEqual(Bm25Embedder().model, "bm25")


class QueryMatchesCorpusTest(unittest.TestCase):
    """The pairs that motivate the tokenizer: real eval questions against the gold
    text they should retrieve. Each asserts the query's content terms are present in
    the passage, which is what BM25 scores on."""

    PAIRS = [
        (
            "พระราชบัญญัติเงินตรา (ฉบับที่ 4) พ.ศ. 2516 ตราขึ้นเมื่อวันที่เท่าใด",
            "ให้ไว้ ณ วันที่ ๓๐ พฤษภาคม พ.ศ. ๒๕๑๖\nเป็นปีที่ ๒๘ ในรัชกาลปัจจุบัน",
            ["พ.ศ", "2516", "วันที่"],
        ),
        (
            'ตามมาตรา 4 คำว่า "ค่าเสมอภาค" หมายความว่าอย่างไร',
            '"ค่าเสมอภาค” หมายความว่า ค่าของหน่วยเงินตราสกุลใดสกุลหนึ่งเทียบกับ'
            "น้ำหนักทองคำบริสุทธิ์",
            ["ค่าเสมอภาค", "หมายความว่า"],
        ),
        (
            "เหรียญกษาปณ์ทองคำราคา 16,000 บาท มีน้ำหนักเท่าใด",
            "(๑) เหรียญกษาปณ์ ทองคำ</td><td>๑๖,๐๐๐ บาท</td><td>ทองคำร้อยละ ๙๖.๕</td>"
            "<td>๑๕ กรัม</td>",
            ["เหรียญ", "กษาปณ์", "ทองคำ", "16000", "บาท"],
        ),
        (
            "เหรียญมีจำนวนผลิตกี่เหรียญ และเส้นผ่าศูนย์กลางเท่าใด",
            "<td>เส้นผ่าศูนย์กลาง / Diameter (มม. / mm.)</td><td>30</td></tr>"
            "<tr><td>จำนวนผลิต / Mintage (เหรียญ / Coins)</td><td>23,000</td></tr>",
            ["เส้นผ่าศูนย์กลาง", "จำนวน", "ผลิต", "เหรียญ"],
        ),
    ]

    def test_query_terms_appear_in_gold_text(self):
        embedder = Bm25Embedder()
        for question, gold, shared in self.PAIRS:
            with self.subTest(question=question):
                query_terms = set(embedder._tokenize(question))
                gold_terms = set(embedder._tokenize(gold))
                self.assertTrue(set(shared) <= query_terms, query_terms)
                self.assertTrue(set(shared) <= gold_terms, gold_terms)


if __name__ == "__main__":
    unittest.main()
