from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware, Runtime, after_model


def transfer_alone(transfers: set[str]) -> AgentMiddleware:
    """Keeps a transfer call as the only call on its message."""

    @after_model
    def strip_siblings(state: AgentState, runtime: Runtime) -> dict | None:
        message = state["messages"][-1]
        calls = getattr(message, "tool_calls", None) or []
        if len(calls) < 2:
            return None
        transfer = next((c for c in calls if c["name"] in transfers), None)
        if transfer is None:
            return None
        return {"messages": [message.model_copy(update={"tool_calls": [transfer]})]}

    return strip_siblings
