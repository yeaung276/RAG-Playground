from langchain.agents.middleware import AgentMiddleware, wrap_model_call

from app.metrics import agent_model_call_duration_seconds


def model_timer(agent: str) -> AgentMiddleware:
    """Records how long each model call made by this agent takes."""

    @wrap_model_call
    async def time_model_call(request, handler):
        with agent_model_call_duration_seconds.labels(agent).time():
            return await handler(request)

    return time_model_call
