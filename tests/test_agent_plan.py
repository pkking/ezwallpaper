"""Deterministic, credential-free unit tests of GitHub plan invariants."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "validate_agent_plan.py"
spec = importlib.util.spec_from_file_location("validate_agent_plan", SOURCE)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

PLAN = """# Task

Issue: #3
Status: IMPLEMENTING

## Objective
An independently testable result.

## Non-goals
None.

## Current facts
Known baseline.

## Acceptance criteria
- [ ] CI green

## Implementation slices
- [ ] Implement

## Verification matrix
Test commands.

## Evidence log
No CI evidence yet.

## Resume from here
Run the next test command.

## Completion
Final commit: pending
CI run: pending
Remaining unassessed items: pending
"""


class AgentPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        path = self.root / "docs/exec-plans/active/task.md"
        path.parent.mkdir(parents=True)
        path.write_text(PLAN, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def event(self, body):
        return {"pull_request": {"number": 12, "body": body}}

    def validate(self, body):
        return validator.validate_event(
            self.event(body), self.root, "pkking/ezwallpaper", "", online=False
        )

    def test_valid_active_plan(self):
        value = self.validate("Issue: #3\nPlan: docs/exec-plans/active/task.md")
        self.assertIn("Issue #3", value)

    def test_missing_issue_or_plan_fails(self):
        for body in ("", "Issue: #3", "Plan: docs/exec-plans/active/task.md"):
            with self.subTest(body=body), self.assertRaises(validator.IntegrityError):
                self.validate(body)

    def test_duplicate_metadata_fails(self):
        with self.assertRaises(validator.IntegrityError):
            self.validate("Issue: #3\nIssue: #3\nPlan: docs/exec-plans/active/task.md")

    def test_mismatched_issue_fails(self):
        with self.assertRaises(validator.IntegrityError):
            self.validate("Issue: #9\nPlan: docs/exec-plans/active/task.md")

    def test_noncanonical_or_missing_path_fails(self):
        for path in ("../../secrets.md", "docs/exec-plans/active/missing.md",
                     "docs/exec-plans/active/../task.md"):
            with self.subTest(path=path), self.assertRaises(validator.IntegrityError):
                self.validate("Issue: #3\nPlan: " + path)

    def test_missing_resume_checkpoint_fails(self):
        path = self.root / "docs/exec-plans/active/task.md"
        path.write_text(PLAN.replace("Run the next test command.", "pending"), encoding="utf-8")
        with self.assertRaises(validator.IntegrityError):
            self.validate("Issue: #3\nPlan: docs/exec-plans/active/task.md")

    def test_completed_plan_requires_evidence(self):
        active = self.root / "docs/exec-plans/active/task.md"
        target = self.root / "docs/exec-plans/completed/task.md"
        target.parent.mkdir(parents=True)
        target.write_text(PLAN.replace("IMPLEMENTING", "COMPLETED"), encoding="utf-8")
        active.unlink()
        with self.assertRaises(validator.IntegrityError):
            self.validate("Issue: #3\nPlan: docs/exec-plans/completed/task.md")

    def test_valid_completed_plan(self):
        plan = (PLAN.replace("IMPLEMENTING", "COMPLETED")
                .replace("- [ ]", "- [x]")
                .replace("Final commit: pending", "Final commit: abcdef012345")
                .replace("CI run: pending", "CI run: https://github.com/pkking/ezwallpaper/actions/runs/1")
                .replace("Remaining unassessed items: pending", "Remaining unassessed items: none"))
        target = self.root / "docs/exec-plans/completed/task.md"
        target.parent.mkdir(parents=True)
        target.write_text(plan, encoding="utf-8")
        (self.root / "docs/exec-plans/active/task.md").unlink()
        self.assertIn("completed", self.validate("Issue: #3\nPlan: docs/exec-plans/completed/task.md"))

    def test_pr_must_update_its_own_plan(self):
        body = "Issue: #3\nPlan: docs/exec-plans/active/task.md"
        with self.assertRaises(validator.IntegrityError):
            validator.validate_event(
                self.event(body), self.root, "pkking/ezwallpaper", "",
                online=False, changed_files=["src/main.rs"]
            )
        result = validator.validate_event(
            self.event(body), self.root, "pkking/ezwallpaper", "",
            online=False, changed_files=["docs/exec-plans/active/task.md"]
        )
        self.assertIn("Issue #3", result)

    def test_duplicate_plan_metadata_fails(self):
        body = ("Issue: #3\nPlan: docs/exec-plans/active/task.md"
                "\nPlan: docs/exec-plans/active/task.md")
        with self.assertRaises(validator.IntegrityError):
            self.validate(body)

    def test_empty_token_fails_closed(self):
        with self.assertRaises(validator.IntegrityError):
            self.validate_online_without_token()

    def validate_online_without_token(self):
        return validator.validate_event(
            self.event("Issue: #3\nPlan: docs/exec-plans/active/task.md"),
            self.root, "pkking/ezwallpaper", "", online=True
        )


if __name__ == "__main__":
    unittest.main()
