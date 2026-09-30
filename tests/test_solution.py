from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from src.procurement_tools import review_is_expired
from src.solution import handle_request


def risk_record(vendor_name: str, **overrides: object) -> dict:
    record = {
        "vendor_name": vendor_name,
        "risk_level": "low",
        "security_review_status": "approved",
        "last_review_date": "2026-06-20",
        "processes_personal_data": False,
        "stores_data_outside_region": False,
        "notes": "Test record",
    }
    record.update(overrides)
    return record


class SolutionTests(unittest.TestCase):
    @patch("src.procurement_tools.get_vendor_risk")
    def test_low_value_request_uses_manager_threshold(self, vendor_api):
        vendor_api.return_value = risk_record("SignFlow")
        decision = handle_request("REQ-1001", "single")
        self.assertEqual(decision.required_approvals, ["Manager"])
        self.assertNotIn("budget_insufficient", decision.risk_flags)
        self.assertEqual(decision.telemetry.llm_calls, 0)
        self.assertGreaterEqual(decision.telemetry.tool_calls, 3)

    @patch("src.procurement_tools.get_vendor_risk")
    def test_sensitive_new_vendor_routes_to_control_owners(self, vendor_api):
        vendor_api.return_value = risk_record(
            "GrowthForge",
            risk_level="high",
            security_review_status="not_completed",
            last_review_date=None,
            processes_personal_data=True,
            stores_data_outside_region=True,
        )
        decision = handle_request("REQ-1005", "single")
        for flag in (
            "budget_insufficient",
            "security_review_required",
            "privacy_review_required",
            "legal_review_required",
        ):
            self.assertIn(flag, decision.risk_flags)
        for approval in ("Finance", "Security", "Privacy", "Legal"):
            self.assertIn(approval, decision.required_approvals)

    @patch("src.procurement_tools.get_vendor_risk")
    def test_prompt_injection_is_data_and_missing_values_are_reported(self, vendor_api):
        vendor_api.return_value = risk_record("NeuralDesk", processes_personal_data=True)
        decision = handle_request("REQ-1006", "single")
        self.assertIn("prompt_injection_detected", decision.risk_flags)
        self.assertIn("annual cost", decision.missing_information)
        self.assertIn("user/license count", decision.missing_information)
        self.assertIn("data access level", decision.missing_information)
        self.assertNotIn("CFO", decision.required_approvals)

    @patch("src.procurement_tools.get_vendor_risk")
    def test_vendor_api_failure_fails_closed(self, vendor_api):
        vendor_api.side_effect = requests.ConnectionError("simulated outage")
        decision = handle_request("REQ-1009", "single")
        self.assertIn("vendor_risk_unavailable", decision.risk_flags)
        self.assertIn("Security", decision.required_approvals)
        self.assertIn("Hold", decision.recommendation)

    @patch("src.procurement_tools.get_vendor_risk")
    def test_architectures_apply_the_same_business_policy(self, vendor_api):
        vendor_api.return_value = risk_record("CodeMate", risk_level="medium", last_review_date="2026-08-20")
        single = handle_request("REQ-1003", "single")
        staged = handle_request("REQ-1003", "staged")
        self.assertEqual(single.required_approvals, staged.required_approvals)
        self.assertEqual(single.risk_flags, staged.risk_flags)
        self.assertEqual(single.missing_information, staged.missing_information)
        self.assertEqual(staged.telemetry.tool_calls, single.telemetry.tool_calls + 1)

    def test_reference_date_boundary(self):
        self.assertFalse(review_is_expired("2025-09-30"))
        self.assertTrue(review_is_expired("2025-09-29"))

    def test_unknown_architecture_is_rejected(self):
        with self.assertRaises(ValueError):
            handle_request("REQ-1001", "committee")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
