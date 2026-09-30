from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.contracts import ProcurementDecision, RunTelemetry
from src.policy_engine import policy_tool
from src.procurement_tools import (
    EvidencePacket,
    budget_tool,
    catalog_tool,
    purchase_history_tool,
    request_context_tool,
    vendor_tool,
)
from src.telemetry import RunTelemetryCounter


def _gather(request_id: str, telemetry: RunTelemetryCounter) -> EvidencePacket:
    packet = request_context_tool(request_id, telemetry)
    budget_tool(packet, telemetry)
    catalog_tool(packet, telemetry)
    vendor_tool(packet, telemetry)
    purchase_history_tool(packet, telemetry)
    return packet


def _recommendation(packet: EvidencePacket, review: dict[str, Any]) -> tuple[str, str]:
    flags = set(review["risk_flags"])
    approvals = review["required_approvals"]
    if review["missing_information"]:
        return (
            "Request clarification before procurement review",
            "Ask the requester for the listed missing information, then rerun the evidence checks.",
        )
    if "budget_insufficient" in flags:
        return (
            "Pause purchase and route for budget exception review",
            "Send the evidence package to Finance and the other required reviewers; no purchase may proceed until humans approve an exception.",
        )
    if "vendor_risk_unavailable" in flags or "conflicting_vendor_evidence" in flags:
        return (
            "Hold for manual evidence verification",
            "Security must verify the vendor evidence, after which the request can continue through the listed human approvals.",
        )
    if "existing_tool_overlap" in flags:
        return (
            "Review existing capability before a new purchase",
            "The requester and Procurement should confirm the documented gap, then obtain the listed human approvals if the purchase is still justified.",
        )
    roles = ", ".join(approvals) if approvals else "the appropriate owner"
    return (
        "Proceed to required human reviews",
        f"Send the grounded evidence package to {roles}; the copilot does not approve or purchase software.",
    )


def _decision(
    packet: EvidencePacket,
    review: dict[str, Any],
    telemetry: RunTelemetryCounter,
) -> ProcurementDecision:
    recommendation, next_step = _recommendation(packet, review)
    return ProcurementDecision(
        request_id=str(packet.request["request_id"]),
        recommendation=recommendation,
        evidence=packet.evidence,
        required_approvals=review["required_approvals"],
        missing_information=review["missing_information"],
        risk_flags=review["risk_flags"],
        next_step=next_step,
        human_review_required=True,
        telemetry=RunTelemetry(
            llm_calls=telemetry.llm_calls,
            tool_calls=telemetry.tool_calls,
            tool_names=telemetry.tool_names,
        ),
    )


def run_single_agent(request_id: str) -> ProcurementDecision:
    """One orchestrator gathers evidence, applies policy, and drafts the handoff."""
    telemetry = RunTelemetryCounter()
    packet = _gather(request_id, telemetry)
    review = policy_tool(packet, telemetry)
    return _decision(packet, review, telemetry)


def run_staged_agents(request_id: str) -> ProcurementDecision:
    """An analyst creates an evidence pack; a reviewer independently reapplies policy."""
    telemetry = RunTelemetryCounter()
    analyst_packet = _gather(request_id, telemetry)
    analyst_review = policy_tool(analyst_packet, telemetry, tool_name="analyst_policy_tool")

    # The handoff is copied to prevent the reviewer from mutating analyst state.
    reviewer_packet = deepcopy(analyst_packet)
    reviewer_review = policy_tool(
        reviewer_packet,
        telemetry,
        tool_name="independent_policy_review_tool",
    )
    if reviewer_review != analyst_review:
        reviewer_review["risk_flags"] = list(
            dict.fromkeys(reviewer_review["risk_flags"] + ["agent_review_disagreement"])
        )
    # Keep one audit item for each stage while returning the reviewer's result.
    analyst_packet.evidence.append(reviewer_packet.evidence[-1])
    return _decision(analyst_packet, reviewer_review, telemetry)
