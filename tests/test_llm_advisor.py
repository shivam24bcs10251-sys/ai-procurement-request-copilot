from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

import requests

from src.llm_advisor import add_need_interpretation
from src.procurement_tools import EvidencePacket
from src.telemetry import RunTelemetryCounter


class LlmAdvisorTests(unittest.TestCase):
    @patch.dict(os.environ, {"OLLAMA_MODEL": "test-model"})
    @patch("src.llm_advisor.requests.post")
    def test_success_records_real_call_and_bounded_output(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"message": {"content": "  A concise\nsummary.  "}}
        post.return_value = response
        packet = EvidencePacket(request={"request_id": "REQ-X"})
        telemetry = RunTelemetryCounter()

        add_need_interpretation(packet, telemetry)

        self.assertEqual(telemetry.llm_calls, 1)
        self.assertEqual(telemetry.tool_names, ["llm_need_interpreter"])
        self.assertEqual(packet.evidence[0].finding, "AI interpretation of submitted need: A concise summary.")

    @patch.dict(os.environ, {"OLLAMA_MODEL": "test-model"})
    @patch("src.llm_advisor.requests.post")
    def test_model_outage_preserves_deterministic_fallback(self, post):
        post.side_effect = requests.ConnectionError("offline")
        packet = EvidencePacket(request={"request_id": "REQ-X"})
        telemetry = RunTelemetryCounter()

        add_need_interpretation(packet, telemetry)

        self.assertEqual(telemetry.llm_calls, 0)
        self.assertEqual(telemetry.tool_calls, 1)
        self.assertEqual(packet.evidence, [])


if __name__ == "__main__":
    unittest.main()
