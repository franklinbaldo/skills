from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claude_routing_adapter  # noqa: E402


class ClaudeRoutingAdapterTests(unittest.TestCase):
    def test_detects_target_skill_tool_use_and_model(self) -> None:
        lines = [
            '{"type":"system","subtype":"init","model":"claude-test","skills":["alpha","beta"]}',
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"alpha"}}]}}',
        ]
        invoked, model, offered = claude_routing_adapter.inspect_stream(lines, "alpha")
        self.assertTrue(invoked)
        self.assertTrue(offered)
        self.assertEqual(model, "claude-test")

    def test_offered_but_not_invoked_is_negative_observation(self) -> None:
        lines = [
            '{"type":"system","subtype":"init","model":"claude-test","skills":["alpha","beta"]}',
            '{"type":"assistant","message":{"content":[{"type":"text","text":"hello"}]}}',
        ]
        invoked, model, offered = claude_routing_adapter.inspect_stream(lines, "alpha")
        self.assertFalse(invoked)
        self.assertTrue(offered)
        self.assertEqual(model, "claude-test")

    def test_different_skill_does_not_count_as_target_trigger(self) -> None:
        lines = [
            '{"type":"system","subtype":"init","skills":["alpha","beta"]}',
            '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill","input":{"skill":"beta"}}]}}',
        ]
        invoked, _, offered = claude_routing_adapter.inspect_stream(lines, "alpha")
        self.assertFalse(invoked)
        self.assertTrue(offered)

    def test_missing_target_in_catalog_is_distinguishable_from_not_invoked(self) -> None:
        lines = [
            '{"type":"system","subtype":"init","skills":["beta"]}',
        ]
        invoked, _, offered = claude_routing_adapter.inspect_stream(lines, "alpha")
        self.assertFalse(invoked)
        self.assertFalse(offered)


if __name__ == "__main__":
    unittest.main()
