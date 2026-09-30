from __future__ import annotations

from src.architectures import run_single_agent, run_staged_agents
from src.contracts import Architecture, ProcurementDecision


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter.

    Keep this function callable by the public/hidden evaluation harness.
    Your internal implementation may use any framework, modules, agents, tools,
    deterministic checks, or orchestration strategy.
    """
    if architecture == "single":
        return run_single_agent(request_id)
    if architecture == "staged":
        return run_staged_agents(request_id)
    raise ValueError(f"Unsupported architecture: {architecture!r}")
