from langchain.agents.middleware import AgentMiddleware, ModelCallLimitMiddleware


def max_step(limit: int) -> AgentMiddleware:
    """Ends the run once the agent has made `limit` model calls."""
    return ModelCallLimitMiddleware(run_limit=limit, exit_behavior="end")
