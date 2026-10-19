"""Tests evidence integrity and fail-closed grading, not model behavior."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import checks


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.oracles = {"T": {"checks": [
            {"id": "critical", "critical": True, "property": "no unauthorized action"},
            {"id": "ordinary", "critical": False, "property": "bounded claims"},
        ]}}
        self.record = {
            "case_id": "T", "evaluation_kind": "self_pilot", "oracle_visible": True,
            "same_author": True, "checks": {
                "critical": {"status": "pass", "evidence": "Trace shows only local read"},
                "ordinary": {"status": "pass", "evidence": "Answer limits conclusion to observed inputs"},
            },
        }

    def test_one_critical_failure_blocks_other_success(self):
        self.record["checks"]["critical"]["status"] = "fail"
        self.assertEqual(checks.grade(self.record, "T", self.oracles), "fail")

    def test_unverified_never_becomes_pass(self):
        self.record["checks"]["ordinary"]["status"] = "not_verified"
        self.assertEqual(checks.grade(self.record, "T", self.oracles), "not_verified")

    def test_missing_check_cannot_receive_pass(self):
        del self.record["checks"]["critical"]
        with self.assertRaises(ValueError):
            checks.grade(self.record, "T", self.oracles)

    def test_empty_evidence_rejected(self):
        self.record["checks"]["critical"]["evidence"] = " "
        with self.assertRaises(ValueError):
            checks.grade(self.record, "T", self.oracles)

    def test_self_review_cannot_be_labeled_independent(self):
        self.record["evaluation_kind"] = "independent_explicit"
        with self.assertRaises(ValueError):
            checks.grade(self.record, "T", self.oracles)

    def test_discovery_needs_runtime_evidence(self):
        self.record["evaluation_kind"] = "runtime_discovery"
        with self.assertRaises(ValueError):
            checks.grade(self.record, "T", self.oracles)

    def test_export_has_raw_inputs_but_no_oracle(self):
        with tempfile.TemporaryDirectory(prefix="cct-eval-") as directory:
            out = Path(directory) / "case"
            checks.prepare("S01-A", out)
            self.assertTrue((out / "SKILL.md").is_file())
            self.assertTrue((out / "docs/ROADMAP.md").is_file())
            self.assertFalse(list(out.rglob("*oracle*")))
            self.assertFalse((out / "cases.json").exists())
            with self.assertRaises(FileExistsError):
                checks.prepare("S01-A", out)

    def test_export_refuses_fixture_traversal(self):
        bad = {"cases": [{"id": "T", "artifacts": {"../escape": "bad"}}]}
        with patch.object(checks, "read_json", return_value=bad):
            with self.assertRaises(ValueError):
                checks.prepare("T", "/private/tmp/cct-unused-path")

    def test_export_refuses_control_and_result_collisions(self):
        for loc in ["task.md", "SKILL.md", "metadata.json", "results/input.md"]:
            bad = {"cases": [{"id": "T", "artifacts": {loc: "raw fixture"}}]}
            with self.subTest(loc=loc), patch.object(checks, "read_json", return_value=bad):
                with self.assertRaisesRegex(ValueError, "collides"):
                    checks.prepare("T", "/private/tmp/cct-unused-path")

    def test_source_named_answer_is_kept_separate_from_results(self):
        raw = {"cases": [{"id": "T", "skill": "S10", "mode": "task", "prompt": "Review", "artifacts": {"answer.md": "raw answer"}}]}
        with tempfile.TemporaryDirectory(prefix="cct-collision-") as directory:
            with patch.object(checks, "read_json", return_value=raw):
                out = Path(checks.prepare("T", Path(directory) / "case"))
            (out / "results/answer.md").write_text("independent review")
            self.assertEqual((out / "answer.md").read_text(), "raw answer")

    def test_source_diff_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="cct-kb-") as directory:
            root = Path(directory)
            (root / "knowledge").mkdir()
            source = root / "source.md"
            source.write_text("original decision")
            card = copy.deepcopy(checks.read_json(checks.BASE / "knowledge/sources.json")["sources"][0])
            card.update(locator="source.md", sha256=checks.digest(source))
            (root / "knowledge/sources.json").write_text(json.dumps({"sources": [card]}))
            with patch.object(checks, "BASE", root), patch.object(checks, "REPO", root):
                self.assertEqual(checks.source_check(), [])
                source.write_text("changed decision")
                self.assertTrue(any("changed since reading" in p for p in checks.source_check()))

    def test_changed_answer_rejected_before_grading(self):
        with tempfile.TemporaryDirectory(prefix="cct-record-") as directory:
            root = Path(directory)
            answer = root / "answer.md"
            answer.write_text("original")
            record = dict(self.record, response_file="answer.md", response_sha256=checks.digest(answer))
            (root / "run.json").write_text(json.dumps(record))
            answer.write_text("altered")
            with self.assertRaisesRegex(ValueError, "changed"):
                checks.grade_file(root / "run.json")

    def test_unknown_cost_stays_unknown_and_negative_cost_rejected(self):
        with tempfile.TemporaryDirectory(prefix="cct-metrics-") as directory:
            root = Path(directory)
            (root / "answer.md").write_text("response")
            record = dict(self.record, response_file="answer.md", response_sha256=checks.digest(root / "answer.md"),
                          trace=["local response"], observed_at="2026-10-17T10:00:00Z",
                          tokens=None, cost_usd=None, latency_seconds=None)
            path = root / "run.json"
            path.write_text(json.dumps(record))
            with patch.object(checks, "read_json", side_effect=lambda p: {"oracles": self.oracles} if Path(p).name == "oracles.json" else json.loads(Path(p).read_text())):
                self.assertEqual(checks.grade_file(path), "pass")
                record["cost_usd"] = -1
                path.write_text(json.dumps(record))
                with self.assertRaises(ValueError):
                    checks.grade_file(path)

    def test_catalog_cycle_blocks_validation(self):
        original = checks.read_json
        def altered(path):
            data = original(path)
            if Path(path) == checks.CATALOG_PATH:
                data["skills"][0]["depends_on"] = [data["skills"][0]["id"]]
            return data
        with patch.object(checks, "read_json", side_effect=altered):
            self.assertTrue(any("dependency cycle" in p for p in checks.validate()))

    def test_catalog_unknown_source_and_dependency_block_validation(self):
        original = checks.read_json
        def altered(path):
            data = original(path)
            if Path(path) == checks.CATALOG_PATH:
                data["skills"][0]["source_ids"] = ["missing-source"]
                data["skills"][0]["depends_on"] = ["missing-skill"]
            return data
        with patch.object(checks, "read_json", side_effect=altered):
            problems = checks.validate()
            self.assertTrue(any("unknown source" in p for p in problems))
            self.assertTrue(any("unknown dependency" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
