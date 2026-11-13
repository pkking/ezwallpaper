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

## Goal alignment
Epic: #60
Goal: G-00

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


GOAL = """Epic: #60
Goal: G-00
Contribution type: MAINTENANCE
Gap: The repository does not require each PR to declare a user acceptance gate.
Acceptance criterion: Issue #305 requires outcome-specific traceability in every PR.
Before: Only Issue and Plan references are checked, not goal acceptance evidence.
After: Each new PR must name a goal, before and after outcomes, and test evidence.
Evidence plan: Run the agent contract suite and all applicable CI jobs at final HEAD.
Priority rationale: Governance protects scarce implementation effort for unfinished P0 scenarios.
Remaining unassessed: Structural declarations do not prove actual user-visible outcomes.
"""


class AgentPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        path = self.root / "docs/exec-plans/active/task.md"
        path.parent.mkdir(parents=True)
        path.write_text(PLAN, encoding="utf-8")
        goal_catalog = self.root / "docs/agents/goal-gates.md"
        goal_catalog.parent.mkdir(parents=True)
        goal_catalog.write_text("| Goal | Priority |\n| --- | --- |\n| G-00 | Governance |\n| G-01 | P0 |\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def event(self, body, goal=GOAL):
        return {"pull_request": {"number": 12, "body": body + "\n" + goal}}

    def validate(self, body):
        return validator.validate_event(
            self.event(body), self.root, "pkking/ezwallpaper", "", online=False
        )

    def test_goal_gate_and_maintenance_allowed(self):
        value = self.validate("Issue: #3\nPlan: docs/exec-plans/active/task.md")
        self.assertIn("Issue #3", value)

    def test_goal_catalog_and_epic_mismatch_rejected(self):
        for broken in (
            GOAL.replace("Goal: G-00", "Goal: G-99"),
            GOAL.replace("Goal: G-00", "Goal: INDEPENDENT"),
            GOAL.replace("Epic: #60", "Epic: independent"),
            GOAL.replace("Goal: G-00", "Goal: none"),
        ):
            with self.subTest(broken=broken.splitlines()[:2]):
                with self.assertRaises(validator.IntegrityError):
                    validator.validate_event(
                        self.event("Issue: #3\nPlan: docs/exec-plans/active/task.md", goal=broken),
                        self.root, "pkking/ezwallpaper", "", online=False,
                    )

    def test_goal_fields_require_specific_nonplaceholder_text(self):
        for field, replacement in (
            ("Gap", "pending"),
            ("Acceptance criterion", "<goal placeholder>"),
            ("Before", "only a test"),
            ("After", "todo"),
            ("Evidence plan", "n/a"),
            ("Priority rationale", "because"),
            ("Remaining unassessed", "none"),
        ):
            value = next(line for line in GOAL.splitlines() if line.startswith(field + ":"))
            broken = GOAL.replace(value, field + ": " + replacement)
            with self.subTest(field=field), self.assertRaises(validator.IntegrityError):
                validator.validate_event(
                    self.event("Issue: #3\nPlan: docs/exec-plans/active/task.md", goal=broken),
                    self.root, "pkking/ezwallpaper", "", online=False,
                )

    def test_blocker_requires_concrete_issue(self):
        blocker = GOAL.replace("Contribution type: MAINTENANCE", "Contribution type: BLOCKER")
        with self.assertRaises(validator.IntegrityError):
            validator.validate_event(
                self.event("Issue: #3\nPlan: docs/exec-plans/active/task.md", goal=blocker),
                self.root, "pkking/ezwallpaper", "", online=False,
            )
        valid = blocker + "Blocking issue: #54\n"
        self.assertIn("Issue #3", validator.validate_event(
            self.event("Issue: #3\nPlan: docs/exec-plans/active/task.md", goal=valid),
            self.root, "pkking/ezwallpaper", "", online=False,
        ))

    def test_independent_goal_needs_approval_issue_and_matching_plan(self):
        path = self.root / "docs/exec-plans/active/task.md"
        path.write_text(PLAN.replace("Epic: #60", "Epic: independent")
                        .replace("Goal: G-00", "Goal: INDEPENDENT"), encoding="utf-8")
        independent = (GOAL.replace("Epic: #60", "Epic: independent")
                       .replace("Goal: G-00", "Goal: INDEPENDENT"))
        with self.assertRaises(validator.IntegrityError):
            validator.validate_event(
                self.event("Issue: #3\nPlan: docs/exec-plans/active/task.md", goal=independent),
                self.root, "pkking/ezwallpaper", "", online=False,
            )
        independent += "Approved goal issue: #15\n"
        self.assertIn("Issue #3", validator.validate_event(
            self.event("Issue: #3\nPlan: docs/exec-plans/active/task.md", goal=independent),
            self.root, "pkking/ezwallpaper", "", online=False,
        ))

    def test_active_plan_must_adopt_matching_goal(self):
        path = self.root / "docs/exec-plans/active/task.md"
        path.write_text(PLAN.replace("Goal: G-00", "Goal: G-01"), encoding="utf-8")
        with self.assertRaises(validator.IntegrityError):
            self.validate("Issue: #3\nPlan: docs/exec-plans/active/task.md")

    def test_valid_historical_archive_without_goal_section(self):
        text = (PLAN.replace("IMPLEMENTING", "COMPLETED")
                .replace("## Goal alignment\nEpic: #60\nGoal: G-00\n\n", "")
                .replace("- [ ]", "- [x]")
                .replace("Final commit: pending", "Final commit: abcdef012345")
                .replace("CI run: pending", "CI run: https://github.com/pkking/ezwallpaper/actions/runs/1")
                .replace("Remaining unassessed items: pending", "Remaining unassessed items: none"))
        target = self.root / "docs/exec-plans/completed/task.md"
        target.parent.mkdir(parents=True)
        target.write_text(text, encoding="utf-8")
        (self.root / "docs/exec-plans/active/task.md").unlink()
        self.assertIn("completed", self.validate("Issue: #3\nPlan: docs/exec-plans/completed/task.md"))

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



class ArchitectureSyncTests(unittest.TestCase):
    """Check diagram health and automatic same-PR ADR synchronization policy."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        origin = Path(__file__).resolve().parents[1]
        self.diagram = self.root / "docs/architecture.svg"
        self.diagram.parent.mkdir(parents=True)
        self.diagram.write_bytes((origin / "docs/architecture.svg").read_bytes())
        (self.root / "README.md").write_text(
            (origin / "README.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        self.adr = self.root / "docs/adr/0002-sample.md"
        self.adr.parent.mkdir(parents=True)
        self.adr.write_text("# Sample architecture decision\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def check(self, body="", changed=None):
        validator.validate_architecture(self.root, body, changed or [])

    def test_valid_readme_diagram(self):
        self.check()

    def test_changed_adr_and_diagram_in_same_pr(self):
        self.check("Architecture diagram: updated",
                   ["docs/adr/0002-sample.md", "docs/architecture.svg"])

    def test_adrs_missing_diagram_and_justification_rejected(self):
        with self.assertRaises(validator.IntegrityError):
            self.check("Architecture diagram: not applicable", ["docs/adr/0002-sample.md"])

    def test_changed_adr_requires_updated_marker_when_diagram_changed(self):
        with self.assertRaises(validator.IntegrityError):
            self.check("Architecture diagram: unchanged - Existing diagram matches the interface",
                       ["docs/adr/0002-sample.md", "docs/architecture.svg"])

    def test_no_diagram_impact_requires_reason_in_both_places(self):
        text = ("This ADR fixes a spelling mistake and does not change sources, "
                "assets, interfaces or any existing data flows.")
        self.adr.write_text("# Sample\n\nDiagram impact: none - " + text + "\n",
                            encoding="utf-8")
        self.check("Architecture diagram: unchanged - " + text,
                   ["docs/adr/0002-sample.md"])

    def test_no_diagram_impact_without_adr_reason_rejected(self):
        reason = ("Only prose is corrected; no source, core, consumer "
                  "or desktop integration contracts change.")
        with self.assertRaises(validator.IntegrityError):
            self.check("Architecture diagram: unchanged - " + reason,
                       ["docs/adr/0002-sample.md"])

    def test_vague_reason_rejected(self):
        self.adr.write_text("# Sample\n\nDiagram impact: none - no impact\n",
                            encoding="utf-8")
        with self.assertRaises(validator.IntegrityError):
            self.check("Architecture diagram: unchanged - no impact",
                       ["docs/adr/0002-sample.md"])

    def test_svg_missing_or_invalid_fails(self):
        self.diagram.write_text("<svg>broken", encoding="utf-8")
        with self.assertRaises(validator.IntegrityError):
            self.check()

    def test_readme_embed_removed_fails(self):
        p = self.root / "README.md"
        p.write_text(p.read_text(encoding="utf-8").replace(
            "![ezwallpaper Core and CLI architecture](docs/architecture.svg)", "Architecture"
        ), encoding="utf-8")
        with self.assertRaises(validator.IntegrityError):
            self.check()

    def test_adr_readme_change_does_not_force_svg_edit(self):
        self.check(changed=["docs/adr/README.md"])

    def test_architecture_semantic_marker_missing_fails(self):
        self.diagram.write_text(
            self.diagram.read_text(encoding="utf-8").replace(
                "Third-party consumers", "Someone else"
            ), encoding="utf-8"
        )
        with self.assertRaises(validator.IntegrityError):
            self.check()


if __name__ == "__main__":
    unittest.main()
