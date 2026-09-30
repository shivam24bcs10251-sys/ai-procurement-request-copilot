from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any

import requests

from src.contracts import EvidenceItem
from src.data_access import (
    get_request,
    load_budgets,
    load_employees,
    load_purchase_history,
    load_software_catalog,
    load_vendors,
)
from src.telemetry import RunTelemetryCounter
from src.vendor_client import get_vendor_risk


REFERENCE_DATE = date(2026, 9, 30)
SENSITIVE_DATA = {
    "source_code",
    "production_data",
    "production_telemetry",
    "confidential_documents",
    "employee_pii",
    "customer_pii",
    "credentials",
    "secrets",
}
PII_DATA = {"employee_pii", "customer_pii"}
INJECTION_PATTERNS = (
    r"ignore\s+(all|any|the|previous|prior).*\b(rule|instruction|policy)",
    r"\b(cfo|manager|security|procurement)[ -]?approved\b",
    r"\bapprove (it|this|the request) immediately\b",
    r"\bbypass\b.*\b(control|policy|review|approval)\b",
    r"\b(system|developer) (message|instruction|prompt)\b",
)


@dataclass
class EvidencePacket:
    request: dict[str, Any]
    employee: dict[str, Any] | None = None
    budget: dict[str, Any] | None = None
    overlaps: list[dict[str, Any]] = field(default_factory=list)
    vendor_registry: dict[str, Any] | None = None
    vendor_risk: dict[str, Any] | None = None
    vendor_error: str | None = None
    purchases: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)


def _records(frame: Any) -> list[dict[str, Any]]:
    return frame.where(frame.notna(), None).to_dict(orient="records")


def _normal(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def request_context_tool(request_id: str, telemetry: RunTelemetryCounter) -> EvidencePacket:
    telemetry.record_tool_call("request_context_tool")
    request = get_request(request_id)
    employee = next(
        (row for row in _records(load_employees()) if row["employee_id"] == request.get("requester_id")),
        None,
    )
    packet = EvidencePacket(request=request, employee=employee)
    if employee:
        packet.evidence.append(
            EvidenceItem(
                source="request_context_tool",
                finding=f"Requester {employee['name']} belongs to {employee['department']}.",
                reference=str(employee["employee_id"]),
            )
        )
    else:
        packet.evidence.append(
            EvidenceItem(
                source="request_context_tool",
                finding="Requester could not be matched to an employee record.",
                reference=request_id,
            )
        )
    return packet


def budget_tool(packet: EvidencePacket, telemetry: RunTelemetryCounter) -> None:
    telemetry.record_tool_call("budget_tool")
    department = packet.employee.get("department") if packet.employee else None
    packet.budget = next(
        (row for row in _records(load_budgets()) if row["department"] == department),
        None,
    )
    if packet.budget:
        cost = packet.request.get("annual_cost_usd")
        cost_text = "unknown" if cost is None else f"${cost:,.0f}"
        packet.evidence.append(
            EvidenceItem(
                source="budget_tool",
                finding=(
                    f"{department} has ${packet.budget['available_usd']:,.0f} available; "
                    f"the annual request is {cost_text}."
                ),
                reference=f"department_budgets.csv:{department}",
            )
        )
    else:
        packet.evidence.append(
            EvidenceItem(
                source="budget_tool",
                finding="No department budget record was found.",
                reference=str(department or "unknown department"),
            )
        )


def catalog_tool(packet: EvidencePacket, telemetry: RunTelemetryCounter) -> None:
    telemetry.record_tool_call("catalog_tool")
    request = packet.request
    product = _normal(request.get("product_name"))
    vendor = _normal(request.get("vendor_name"))
    category = _normal(request.get("category"))
    overlaps: list[dict[str, Any]] = []
    for row in _records(load_software_catalog()):
        row_product = _normal(row.get("product_name"))
        same_vendor = vendor and vendor == _normal(row.get("vendor_name"))
        same_category = category and category == _normal(row.get("category"))
        product_related = product and (product in row_product or row_product in product)
        if same_vendor or same_category or product_related:
            overlaps.append(row)
    packet.overlaps = overlaps
    if overlaps:
        summary = ", ".join(f"{r['product_name']} ({r['scope']})" for r in overlaps[:4])
        packet.evidence.append(
            EvidenceItem(
                source="catalog_tool",
                finding=f"Approved catalog options with product, vendor, or category overlap: {summary}.",
                reference=", ".join(str(r["software_id"]) for r in overlaps[:4]),
            )
        )
    else:
        packet.evidence.append(
            EvidenceItem(
                source="catalog_tool",
                finding="No approved catalog option matched the product, vendor, or category.",
                reference="software_catalog.csv",
            )
        )


def vendor_tool(packet: EvidencePacket, telemetry: RunTelemetryCounter) -> None:
    telemetry.record_tool_call("vendor_registry_tool")
    vendor_name = str(packet.request.get("vendor_name") or "")
    packet.vendor_registry = next(
        (row for row in _records(load_vendors()) if row["vendor_name"] == vendor_name),
        None,
    )
    registry = packet.vendor_registry
    if registry:
        packet.evidence.append(
            EvidenceItem(
                source="vendor_registry_tool",
                finding=(
                    f"Registry status: procurement {registry['procurement_status']}, security "
                    f"{registry['security_status']}, legal terms {registry['legal_terms_status']}."
                ),
                reference=str(registry["vendor_id"]),
            )
        )
    else:
        packet.evidence.append(
            EvidenceItem(
                source="vendor_registry_tool",
                finding="Vendor is absent from the internal registry.",
                reference=vendor_name,
            )
        )

    telemetry.record_tool_call("vendor_risk_api_tool")
    try:
        packet.vendor_risk = get_vendor_risk(vendor_name)
    except (requests.RequestException, ValueError) as exc:
        packet.vendor_error = f"{type(exc).__name__}: {exc}"
        packet.evidence.append(
            EvidenceItem(
                source="vendor_risk_api_tool",
                finding="Vendor risk service was unavailable; current external risk status was not verified.",
                reference=vendor_name,
            )
        )
    else:
        risk = packet.vendor_risk
        packet.evidence.append(
            EvidenceItem(
                source="vendor_risk_api_tool",
                finding=(
                    f"External risk level is {risk.get('risk_level')}; security review is "
                    f"{risk.get('security_review_status')} (last review: "
                    f"{risk.get('last_review_date') or 'none'})."
                ),
                reference=vendor_name,
            )
        )


def purchase_history_tool(packet: EvidencePacket, telemetry: RunTelemetryCounter) -> None:
    telemetry.record_tool_call("purchase_history_tool")
    vendor_name = packet.request.get("vendor_name")
    product_name = _normal(packet.request.get("product_name"))
    purchases = [
        row
        for row in _records(load_purchase_history())
        if row["vendor_name"] == vendor_name
        or _normal(row["product_name"]) in product_name
        or product_name in _normal(row["product_name"])
    ]
    packet.purchases = purchases
    if purchases:
        latest = sorted(purchases, key=lambda row: str(row["purchase_date"]), reverse=True)[0]
        packet.evidence.append(
            EvidenceItem(
                source="purchase_history_tool",
                finding=(
                    f"Prior purchase found: {latest['product_name']} for "
                    f"${latest['annual_amount_usd']:,.0f}, status {latest['status']}."
                ),
                reference=str(latest["purchase_id"]),
            )
        )
    else:
        packet.evidence.append(
            EvidenceItem(
                source="purchase_history_tool",
                finding="No prior purchase for this product or vendor was found.",
                reference="purchase_history.csv",
            )
        )


def contains_prompt_injection(request: dict[str, Any]) -> bool:
    business_text = " ".join(
        str(request.get(field) or "")
        for field in ("business_justification", "product_name", "vendor_name")
    )
    return any(re.search(pattern, business_text, flags=re.IGNORECASE) for pattern in INJECTION_PATTERNS)


def review_is_expired(review_date: Any) -> bool:
    if not review_date:
        return False
    try:
        reviewed = date.fromisoformat(str(review_date))
    except ValueError:
        return True
    return (REFERENCE_DATE - reviewed).days > 365
