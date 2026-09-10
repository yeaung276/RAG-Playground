import asyncio
from collections.abc import AsyncIterator
from functools import wraps

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import get_settings
from app.metrics import generation_duration_seconds, generation_requests_total
from app.schemas.messages import TokenFrame, ToolCallFrame
from app.utils.image import resize_incoming_base64_image


class GenerationService:
    def __init__(self, agent: str | None = None):
        settings = get_settings()
        self.agent = agent or settings.AGENT_NAME

    @staticmethod
    def _track(stream):
        @wraps(stream)
        async def wrapper(*args, **kwargs):
            with (
                generation_duration_seconds.time(),
                generation_requests_total.labels(status="error").count_exceptions(),
            ):
                async for frame in stream(*args, **kwargs):
                    yield frame
            generation_requests_total.labels(status="success").inc()

        return wrapper

    @_track
    async def stream_reply(
        self, message: str | None = None, img_b64: str | None = None
    ) -> AsyncIterator[TokenFrame | ToolCallFrame]:
        """Yields the agent's reply one frame at a time."""
        content: list[dict] = []
        if message:
            content.append({"type": "text", "text": message})
        if img_b64:
            b64 = resize_incoming_base64_image(img_b64)
            url = f"data:image/png;base64,{b64}"
            content.append({"type": "image_url", "image_url": {"url": url}})
            
        yield ToolCallFrame(name="calling tool 1...")
        await asyncio.sleep(1)
        yield ToolCallFrame(name="calling tool 2...")
        await asyncio.sleep(1)
        for t in (
            "Here's what I found in the knowledge base:\n\n"
            "1. **Land appraisal prices** can be looked up with the title deed "
            "number and the province.\n"
            "2. **Commemorative coins** are ordered through the coin exchange "
            "counter or online.\n\n"
            "Let me know which one you'd like more detail on."
        ):
            yield TokenFrame(delta=t)
            await asyncio.sleep(0.02)
            

        # async for chunk in self.llm.astream([HumanMessage(content)]):  # pyright: ignore[reportArgumentType]
        #     if chunk.text:
        #         yield TokenFrame(delta=chunk.text)
        #     for call in chunk.tool_call_chunks:
        #         if call["name"]:
        #             yield ToolCallFrame(name=call["name"])
