"""Fail-closed PR -> GitHub Issue -> execution plan integrity validator.

CI runs on pull_request with read-only permissions, never pull_request_target.
The PR controls its own workflow/validator: branch Ruleset is still required.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
                   *, online: bool = True) -> str:
    pr = event.get("pull_request")
    if not isinstance(pr, dict):
        raise IntegrityError("Expected a pull_request event")
    body = pr.get("body")
    if not isinstance(body, str):
        raise IntegrityError("PR body is missing")
    issue, relative = parse_metadata(body)
    state = validate_plan(root, relative, issue)
    if online:
        validate_issue(repository, issue, token)
    return f"Issue #{issue} -> {relative} ({state})"


def main() -> int:
    try:
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        message = validate_event(event, Path.cwd(),
                                 os.environ["GITHUB_REPOSITORY"],
                                 os.environ.get("GH_TOKEN", ""))
    except (IntegrityError, KeyError, OSError, ValueError) as exc:
        print(f"PLAN INTEGRITY FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"PLAN INTEGRITY OK: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
