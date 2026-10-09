from langchain.agents.middleware import AgentMiddleware, ModelCallLimitMiddleware, hook_config

from app.metrics import agent_step_limit_total


class _StepLimit(ModelCallLimitMiddleware):
    def __init__(self, limit: int, agent: str):
        super().__init__(run_limit=limit, exit_behavior="end")
        self.agent = agent

    @hook_config(can_jump_to=["end"])
    def before_model(self, state, runtime):
        result = super().before_model(state, runtime)
        if result is not None:
            agent_step_limit_total.labels(self.agent).inc()
        return result


def max_step(limit: int, agent: str) -> AgentMiddleware:
    """Ends the run once the agent has made `limit` model calls."""
    return _StepLimit(limit, agent)
