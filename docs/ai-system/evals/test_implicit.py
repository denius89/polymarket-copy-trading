import json
import unittest
from run_implicit import analyze_trace, observed_reads


def trace(*events):
    return "\n".join(json.dumps(e) for e in events)


class ImplicitEvidenceTests(unittest.TestCase):
    def test_successful_native_read_is_positive_evidence(self):
        data = trace({"type": "item.completed", "item": {"type": "command_execution", "command": "cat .agents/skills/cct-ai-quality/SKILL.md", "exit_code": 0, "aggregated_output": "---\nname: cct-ai-quality\ndescription: test\n---\n"}}, {"type": "turn.completed", "usage": {"input_tokens": 10}})
        self.assertEqual(analyze_trace(data, ["cct-ai-quality"], True)["status"], "pass")

    def test_printed_command_is_not_a_read(self):
        names, uncertain = observed_reads("printf '%s\\n' 'cat cct-ai-quality/SKILL.md'", "cat cct-ai-quality/SKILL.md")
        self.assertFalse(names)
        self.assertFalse(uncertain)

    def test_newline_command_cannot_spoof_read(self):
        names, uncertain = observed_reads("cat /dev/null\nprintf -- '---\\nname: cct-ai-quality\\n---\\n' cct-ai-quality/SKILL.md", "---\nname: cct-ai-quality\n---")
        self.assertFalse(names)
        self.assertTrue(uncertain)

    def test_masked_failure_is_not_proof(self):
        names, uncertain = observed_reads("cat /nonexistent/cct-ai-quality/SKILL.md || true", "")
        self.assertFalse(names)
        self.assertTrue(uncertain)

    def test_unsupported_python_read_is_unverified(self):
        names, uncertain = observed_reads("python3 -c \"print(open('cct-ai-quality/SKILL.md').read())\"", "---\nname: cct-ai-quality\n---")
        self.assertFalse(names)
        self.assertTrue(uncertain)

    def test_normalized_path_and_shell_wrapper(self):
        names, uncertain = observed_reads("/bin/bash -lc 'cat cct-ai-quality/./SKILL.md'", "---\nname: cct-ai-quality\n---")
        self.assertEqual(names, {"cct-ai-quality"})
        self.assertFalse(uncertain)

    def test_missing_manifest_output_is_unverified(self):
        data = trace({"type": "item.completed", "item": {"type": "command_execution", "command": "cat cct-ai-quality/SKILL.md", "exit_code": 0}}, {"type": "turn.completed"})
        self.assertEqual(analyze_trace(data, ["cct-ai-quality"], True)["status"], "not_verified")

    def test_claim_and_failed_read_are_not_activation_proof(self):
        data = trace({"type": "item.completed", "item": {"type": "agent_message", "text": "Used cct-ai-quality/SKILL.md"}}, {"type": "item.completed", "item": {"type": "command_execution", "command": "cat cct-ai-quality/SKILL.md", "exit_code": 1}}, {"type": "turn.completed"})
        self.assertEqual(analyze_trace(data, ["cct-ai-quality"], True)["status"], "fail")

    def test_process_failure_is_unverified_not_routing_failure(self):
        self.assertEqual(analyze_trace('{"type":"turn.failed"}', ["cct-ai-quality"], True, 1)["status"], "not_verified")

    def test_negative_control_does_not_need_a_skill_read(self):
        data = trace({"type": "item.completed", "item": {"type": "agent_message", "text": "68"}}, {"type": "turn.completed"})
        self.assertEqual(analyze_trace(data, [], False)["status"], "pass")


if __name__ == "__main__":
    unittest.main()
