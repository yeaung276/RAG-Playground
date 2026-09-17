from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.schemas.dataset import Category

CATEGORY_GUIDE = {
    Category.SIMPLE: "answerable from a single passage, no inference needed",
    Category.REASONING: "needs several inference steps over the passage to answer",
    Category.MULTI_CONTEXT: "needs facts from two or more distant parts of the text",
    Category.CONDITIONAL: "the answer depends on a condition stated in the question",
}

SYSTEM_PROMPT = """You write question/answer pairs for evaluating a retrieval system.

Rules:
- Produce exactly one sample per requested slot, in the same order, matching the
  category asked for in that slot.
- `context` is the verbatim excerpt from the source text the answer comes from.
- `question` must be answerable from `context` alone and must not refer to "the
  text" or "the document" — it should read as a standalone user question.
- `answer` is grounded in `context`; never invent facts.
- `labels` are the tags from the allowed list that apply to the sample. Assign
  every label that applies, or none if none do. Use no other label."""


class Sample(BaseModel):
    context: str = Field(description="Verbatim excerpt the answer is drawn from")
    question: str
    answer: str
    category: Category
    labels: list[str] = Field(default_factory=list)


class SampleBatch(BaseModel):
    samples: list[Sample]


class DataGenerationService:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def create_samples(
        self, text: str, samples: list[Category], lables: list[str]
    ) -> list[Sample]:
        """One pair per entry in `samples`, each of that entry's category."""
        if not samples:
            return []

        slots = "\n".join(
            f"{i}. {category} — {CATEGORY_GUIDE[category]}"
            for i, category in enumerate(samples, start=1)
        )
        allowed = ", ".join(lables) if lables else "(none — leave labels empty)"

        result = await self.llm.with_structured_output(SampleBatch).ainvoke(
            [
                SystemMessage(SYSTEM_PROMPT),
                HumanMessage(
                    f"Allowed labels: {allowed}\n\n"
                    f"Generate {len(samples)} samples, one per slot:\n{slots}\n\n"
                    f"Source text:\n{text}"
                ),
            ]
        )

        permitted = set(lables)
        return [
            sample.model_copy(
                update={
                    "category": category,
                    "labels": [l for l in sample.labels if l in permitted],
                }
            )
            for sample, category in zip(result.samples, samples)
        ]
