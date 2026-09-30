from __future__ import annotations

from typing import Any

from src.contracts import EvidenceItem
from src.procurement_tools import (
    EvidencePacket,
    PII_DATA,
    SENSITIVE_DATA,
    contains_prompt_injection,
    review_is_expired,
)
from src.telemetry import RunTelemetryCounter


def _add_unique(items: list[str], *values: str) -> None:
    for value in values:
        if value not in items:
            items.append(value)


def _financial_approvals(cost: float | int) -> list[str]:
    if cost <= 1_000:
        return ["Manager"]
    if cost <= 10_000:
        return ["Department Head", "Procurement"]
    if cost <= 25_000:
        return ["Department Head", "Finance", "Procurement"]
    return ["Department Head", "Finance", "CFO", "Procurement"]


def policy_tool(
    packet: EvidencePacket,
    telemetry: RunTelemetryCounter,
    *,
    tool_name: str = "deterministic_policy_tool",
) -> dict[str, Any]:
    """Apply policy rules. This tool never grants approval or mutates source data."""
    telemetry.record_tool_call(tool_name)
    request = packet.request
    missing: list[str] = []
    flags: list[str] = []
    approvals: list[str] = []

    required_fields = {
        "requester_id": "requester",
        "product_name": "product",
        "vendor_name": "vendor",
        "annual_cost_usd": "annual cost",
        "user_count": "user/license count",
        "business_justification": "business purpose",
        "data_access_level": "data access level",
        "requested_integrations": "required integrations",
    }
    for field, label in required_fields.items():
        value = request.get(field)
        if value is None or (isinstance(value, str) and (not value.strip() or value.lower() == "unknown")):
            missing.append(label)
    if packet.employee is None:
        _add_unique(missing, "requester and department")
    if packet.budget is None:
        _add_unique(missing, "department budget")
    if missing:
        _add_unique(flags, "missing_information")

    cost = request.get("annual_cost_usd")
    if isinstance(cost, (int, float)):
        _add_unique(approvals, *_financial_approvals(cost))
        if packet.budget and cost > packet.budget["available_usd"]:
            _add_unique(flags, "budget_insufficient")
            _add_unique(approvals, "Finance")

    if packet.overlaps:
        _add_unique(flags, "existing_tool_overlap")

    if contains_prompt_injection(request):
        _add_unique(flags, "prompt_injection_detected")

    access = str(request.get("data_access_level") or "unknown").lower()
    integrations = " ".join(str(v).lower() for v in request.get("requested_integrations") or [])
    sensitive_use = access in SENSITIVE_DATA or any(
        token in integrations for token in ("production", "cloud account", "git", "repository")
    )
    if sensitive_use:
        _add_unique(flags, "security_review_required")
        _add_unique(approvals, "Security")
    if access in PII_DATA:
        _add_unique(flags, "privacy_review_required")
        _add_unique(approvals, "Privacy")

    registry = packet.vendor_registry or {}
    risk = packet.vendor_risk or {}
    registry_status = str(registry.get("security_status") or "missing").lower()
    api_status = str(risk.get("security_review_status") or "missing").lower()
    registry_date = registry.get("security_review_date")
    api_date = risk.get("last_review_date")
    registry_expired = review_is_expired(registry_date)
    api_expired = review_is_expired(api_date)

    if packet.vendor_error:
        _add_unique(flags, "vendor_risk_unavailable", "security_review_required")
        _add_unique(approvals, "Security")
    if (
        registry_status in {"missing", "pending", "unknown", "not_completed", "expired"}
        or api_status in {"missing", "pending", "unknown", "not_completed", "expired"}
        or registry_expired
        or api_expired
    ):
        _add_unique(flags, "security_review_required")
        _add_unique(approvals, "Security")
    if registry_expired or api_expired or "expired" in {registry_status, api_status}:
        _add_unique(flags, "vendor_review_expired")

    # Pending and not_completed describe the same incomplete state. Keep
    # approved-vs-expired as a conflict so stale registry records are visible.
    comparable_registry = "incomplete" if registry_status in {"pending", "not_completed"} else registry_status
    comparable_api = "incomplete" if api_status in {"pending", "not_completed"} else api_status
    if packet.vendor_risk and comparable_registry != comparable_api:
        _add_unique(flags, "conflicting_vendor_evidence", "security_review_required")
        _add_unique(approvals, "Security")

    outside_region = bool(risk.get("stores_data_outside_region"))
    if outside_region and (access in PII_DATA or sensitive_use):
        _add_unique(flags, "privacy_review_required", "legal_review_required")
        _add_unique(approvals, "Privacy", "Legal")

    vendor_is_new = str(registry.get("procurement_status") or "missing").lower() != "approved"
    legal_terms_ok = str(registry.get("legal_terms_status") or "missing").lower() == "approved"
    if (vendor_is_new and isinstance(cost, (int, float)) and cost >= 10_000) or not legal_terms_ok:
        _add_unique(flags, "legal_review_required")
        _add_unique(approvals, "Legal")

    packet.evidence.append(
        EvidenceItem(
            source=tool_name,
            finding=(
                f"Policy 2026.09 applied using reference date 2026-09-30; "
                f"{len(approvals)} approval role(s), {len(flags)} risk flag(s), "
                f"and {len(missing)} missing item(s) identified."
            ),
            reference="procurement_policy.md",
        )
    )
    return {"required_approvals": approvals, "missing_information": missing, "risk_flags": flags}
