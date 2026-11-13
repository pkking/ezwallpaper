"""Fail-closed PR -> GitHub Issue -> execution plan integrity validator.

CI runs on pull_request with read-only permissions, never pull_request_target.
The PR controls its own workflow/validator: branch Ruleset is still required.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ISSUE_LINE = re.compile(r"Issue:\s*#([1-9][0-9]*)")
PLAN_LINE = re.compile(
    r"Plan:\s*(docs/exec-plans/(?:active|completed)/[a-zA-Z0-9][a-zA-Z0-9_-]*\.md)"
)
ACTIVE = {"PLANNING", "IMPLEMENTING", "VERIFYING", "PAUSED",
          "BLOCKED_DECISION", "BLOCKED_EVIDENCE", "READY_FOR_REVIEW"}
REQUIRED = (
    "Objective", "Non-goals", "Current facts", "Acceptance criteria",
    "Implementation slices", "Verification matrix", "Evidence log",
    "Resume from here", "Completion"
)


class IntegrityError(ValueError):
    """Evidence is absent, contradictory or invalid."""


def parse_metadata(body: str) -> tuple[int, str]:
    values = {}
    for key, regex in (("Issue", ISSUE_LINE), ("Plan", PLAN_LINE)):
        lines = re.findall(rf"(?m)^{key}:.*$", body)
        if len(lines) != 1:
            raise IntegrityError(f"PR must have exactly one {key}: metadata line")
        match = regex.fullmatch(lines[0].strip())
        if match is None:
            raise IntegrityError(f"Invalid {key}: metadata value")
        values[key] = match.group(1)
    return int(values["Issue"]), values["Plan"]


def section(content: str, heading: str) -> str:
    match = re.search(rf"(?m)^## {re.escape(heading)}\s*$", content)
    if match is None:
        raise IntegrityError(f"Plan missing section: {heading}")
    end = re.search(r"(?m)^## ", content[match.end():])
    return content[match.end():match.end() + end.start()] if end else content[match.end():]


def validate_plan(root: Path, relative: str, issue: int) -> str:
    if PLAN_LINE.fullmatch("Plan: " + relative) is None:
        raise IntegrityError("Plan must be a canonical active/completed Markdown path")
    plan = (root / relative).resolve()
    directory = plan.parent
    parents = [(root / "docs/exec-plans" / name).resolve()
               for name in ("active", "completed")]
    if directory not in parents or not plan.is_file():
        raise IntegrityError("Plan must exist directly inside active/ or completed/")
    content = plan.read_text(encoding="utf-8")
    issue_lines = re.findall(r"(?m)^Issue:.*$", content)
    if issue_lines != [f"Issue: #{issue}"]:
        raise IntegrityError("Plan Issue must match PR Issue exactly once")
    statuses = re.findall(r"(?m)^Status:\s*(\S+)\s*$", content)
    if len(statuses) != 1:
        raise IntegrityError("Plan must declare exactly one status")
    status = statuses[0]
    for heading in REQUIRED:
        section(content, heading)
    resume = section(content, "Resume from here").strip()
    if not resume or resume.lower() in {"pending", "todo", "tbd", "none"}:
        raise IntegrityError("Plan lacks an executable resume checkpoint")
    if directory == parents[0]:
        if status not in ACTIVE:
            raise IntegrityError("Active plan has an invalid status")
        return "active"
    if status != "COMPLETED":
        raise IntegrityError("Archived plan requires Status: COMPLETED")
    for heading in ("Acceptance criteria", "Implementation slices"):
        if re.search(r"(?m)^\s*- \[ \]", section(content, heading)):
            raise IntegrityError(f"Archived plan has unchecked {heading}")
    completion = section(content, "Completion")
    for label in ("Final commit", "CI run", "Remaining unassessed items"):
        found = re.search(rf"(?m)^{re.escape(label)}:\s*(.+)\s*$", completion)
        if not found or found.group(1).strip().lower() in {"", "pending", "tbd", "todo", "unknown"}:
            raise IntegrityError(f"Archived plan missing actual {label} evidence")
    return "completed"


GOAL_FIELDS = (
    "Epic", "Goal", "Contribution type", "Gap", "Acceptance criterion",
    "Before", "After", "Evidence plan", "Priority rationale",
    "Remaining unassessed",
)
GOAL_TYPES = {"USER_JOURNEY", "BLOCKER", "SECURITY", "MAINTENANCE"}
MEANINGFUL_GOAL_FIELDS = (
    "Gap", "Acceptance criterion", "Before", "After",
    "Evidence plan", "Priority rationale", "Remaining unassessed",
)


def goal_field(body: str, field: str) -> str:
    lines = re.findall(rf"(?m)^{re.escape(field)}:.*$", body)
    if len(lines) != 1:
        raise IntegrityError(f"PR must have exactly one {field}: goal field")
    value = lines[0].split(":", 1)[1].strip()
    if (not value or re.search(r"<[^>]+>", value) or
            value.lower() in {"pending", "tbd", "todo", "unknown", "n/a", "none"}):
        raise IntegrityError(f"PR {field}: goal field is missing or a placeholder")
    return value


def validate_goal_alignment(root: Path, body: str, plan_relative: str) -> str:
    """Validate traceable user-outcome declarations, not their semantic truth.

    The checked-out repository defines the known goal IDs. GitHub's protected
    branch Ruleset must independently require this check, as an untrusted PR
    can edit its own validator and workflow in the same branch.
    """
    values = {name: goal_field(body, name) for name in GOAL_FIELDS}
    for field in MEANINGFUL_GOAL_FIELDS:
        if len(values[field]) < 20:
            raise IntegrityError(f"PR {field}: must describe a specific outcome/evidence")
    kind = values["Contribution type"]
    if kind not in GOAL_TYPES:
        raise IntegrityError("Invalid contribution type")
    epic, gate = values["Epic"], values["Goal"]
    if epic == "#60":
        catalog = root / "docs/agents/goal-gates.md"
        try:
            known = set(re.findall(
                r"(?m)^\\|\\s*(G-[0-9]{2})\\s*\\|",
                catalog.read_text(encoding="utf-8"),
            ))
        except OSError as exc:
            raise IntegrityError(f"Missing goal gate catalog: {exc}") from exc
        if not known or gate not in known:
            raise IntegrityError(f"Unknown Epic #60 acceptance gate: {gate}")
        if re.findall(r"(?m)^Approved goal issue:.*$", body):
            raise IntegrityError("Epic #60 work must not declare an independent goal")
    elif epic == "independent" and gate == "INDEPENDENT":
        approval = goal_field(body, "Approved goal issue")
        if re.fullmatch(r"#[1-9][0-9]*", approval) is None:
            raise IntegrityError("Independent goal must link its approved Issue")
    else:
        raise IntegrityError("Epic and Goal must be #60/G-XX or independent/INDEPENDENT")

    blocking = re.findall(r"(?m)^Blocking issue:.*$", body)
    if kind == "BLOCKER":
        issue = goal_field(body, "Blocking issue")
        if re.fullmatch(r"#[1-9][0-9]*", issue) is None:
            raise IntegrityError("BLOCKER must reference a concrete blocking Issue")
    elif blocking:
        raise IntegrityError("Blocking issue is only valid on a BLOCKER PR")

    # Older archived plans remain legal. Resumed active plans must explicitly
    # adopt goal alignment on their next implementation PR.
    plan_text = (root / plan_relative).read_text(encoding="utf-8")
    declared_goals = re.findall(r"(?m)^Goal:\\s*(\\S+)\\s*$", plan_text)
    if plan_relative.startswith("docs/exec-plans/active/"):
        if "## Goal alignment" not in plan_text or declared_goals != [gate]:
            raise IntegrityError("Active plan goal must match the PR goal")
    elif declared_goals and declared_goals != [gate]:
        raise IntegrityError("Archived plan goal does not match the PR goal")
    return gate


def validate_issue(repository: str, issue: int, token: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise IntegrityError("Invalid GitHub repository")
    if not token:
        raise IntegrityError("GitHub token required to verify open Issue")
    url = f"https://api.github.com/repos/{repository}/issues/{issue}"
    request = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ezwallpaper-plan-integrity",
    })
    try:
        with urlopen(request, timeout=15) as response:
            data = json.load(response)
    except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
        raise IntegrityError(f"Could not independently verify Issue #{issue}: {exc}") from exc
    if data.get("number") != issue or data.get("state") != "open" or "pull_request" in data:
        raise IntegrityError(f"#{issue} must be an open Issue (not a PR)")


def validate_event(event: dict, root: Path, repository: str, token: str,
                   *, online: bool = True, changed_files: list[str] | None = None) -> str:
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        raise IntegrityError("Expected a pull_request event")
    body = pr.get("body")
    if not isinstance(body, str):
        raise IntegrityError("PR body is missing")
    issue, relative = parse_metadata(body)
    state = validate_plan(root, relative, issue)
    validate_goal_alignment(root, body, relative)
    if changed_files is not None and relative not in changed_files:
        raise IntegrityError("PR must update its own linked execution plan")
    if online:
        validate_issue(repository, issue, token)
    return f"Issue #{issue} -> {relative} ({state})"


def changed_paths(base_sha: str) -> list[str]:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", base_sha):
        raise IntegrityError("PR_BASE_SHA is required and must be a full commit SHA")
    try:
        return subprocess.check_output(
            ["git", "diff", "--name-only", f"{base_sha}...HEAD"],
            text=True, stderr=subprocess.STDOUT
        ).splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise IntegrityError(f"Unable to inspect PR changed paths: {exc}") from exc


ARCHITECTURE_SVG = "docs/architecture.svg"
ADR_FILE = re.compile(r"^docs/adr/[0-9]{4}-[a-zA-Z0-9][a-zA-Z0-9_-]*\.md$")

def _specific_reason(value: str) -> bool:
    reason = value.strip()
    return len(reason) >= 25 and reason.lower() not in {
        "n/a", "not applicable", "no impact", "no change", "unchanged",
        "documentation only", "none", "no architecture impact"
    }


def validate_architecture(root: Path, body: str, changed_files: list[str]) -> None:
    """Check README diagram validity and ADR/diagram synchronization for the PR."""
    readme = (root / "README.md").read_text(encoding="utf-8")
    if "![ezwallpaper Core and CLI architecture](docs/architecture.svg)" not in readme:
        raise IntegrityError("README must embed canonical docs/architecture.svg")

    try:
        svg = ET.parse(root / ARCHITECTURE_SVG).getroot()
    except (OSError, ET.ParseError) as exc:
        raise IntegrityError(f"Cannot parse architecture SVG: {exc}") from exc
    if svg.tag != "{http://www.w3.org/2000/svg}svg":
        raise IntegrityError("Architecture diagram must use the SVG namespace")
    label_text = " ".join(svg.itertext())
    for marker in ("ezwallpaper-core", "ezwallpaper CLI", "Third-party consumers",
                   "Bing", "Pexels", "Local files", "WallpaperAsset", "JSON manifest v1",
                   "Planned"):
        if marker not in label_text:
            raise IntegrityError(f"Architecture diagram missing: {marker}")

    changed_adrs = [p for p in changed_files if ADR_FILE.fullmatch(p)]
    if not changed_adrs:
        return
    if ARCHITECTURE_SVG in changed_files:
        if len(re.findall(r"(?m)^Architecture diagram: updated\s*$", body)) != 1:
            raise IntegrityError("ADR change with updated SVG must declare Architecture diagram: updated")
        return

    matches = re.findall(r"(?m)^Architecture diagram: unchanged - (.+)$", body)
    if len(matches) != 1 or not _specific_reason(matches[0]):
        raise IntegrityError(
            "ADR changed without SVG: update docs/architecture.svg in the same PR, "
            "or provide an explicit Architecture diagram: unchanged - <specific reason>"
        )
    for adr in changed_adrs:
        file = root / adr
        if not file.is_file():
            raise IntegrityError(f"Cannot evaluate removed ADR without diagram update: {adr}")
        impact = re.findall(r"(?m)^Diagram impact: none - (.+)$", file.read_text(encoding="utf-8"))
        if len(impact) != 1 or not _specific_reason(impact[0]):
            raise IntegrityError(
                f"{adr} must document Diagram impact: none - <specific reason> "
                "when its ADR changes without the diagram"
            )


def main() -> int:
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        changes = changed_paths(os.environ["PR_BASE_SHA"])
        message = validate_event(event, Path.cwd(),
                                 os.environ["GITHUB_REPOSITORY"],
                                 os.environ.get("GH_TOKEN", ""),
                                 changed_files=changes)
        validate_architecture(Path.cwd(), event["pull_request"]["body"], changes)
    except (IntegrityError, KeyError, OSError, ValueError) as exc:
        print(f"PLAN INTEGRITY FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"PLAN INTEGRITY OK: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
