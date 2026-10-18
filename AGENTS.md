# Agent development contract — ezwallpaper

This is the authoritative map for coding agents, not a substitute for inspecting code. Applicable to every agent and task. Read more-specific AGENTS.md files if any are added later.

## Read first
1. README.md and Cargo.toml: product scope, CLI and dependencies.
2. docs/architecture.md: actual implementation and known gaps.
3. docs/agents/workflow.md: Issue, execution plan, PR, evidence and recovery.
4. docs/agents/testing.md: offline quality gates and platform-specific testing.
5. docs/adr/0001-core-cli-boundaries.md and the Issue-linked active plan.

## Core behavior and safety
- This is a Rust 2018 workspace: headless ezwallpaper-core manages sources and local wallpaper assets, and the ezwallpaper CLI integrates desktop backends. Core MUST NOT depend on wallpaper-rs, inspect GUI sessions or run OS wallpaper commands. Preserve existing flags/defaults unless a user-visible change is approved and tested.
- Bing and Pexels retrieval uses network and writes downloaded files. The wallpaper library changes the user's desktop. Never perform a live download or mutate desktop state during unit or required CI tests.
- Pexels API tokens are credentials. Never commit, display, log, store in fixtures or upload them as CI artifacts. Never send secrets to GitHub PRs or untrusted code.
- Validate paths, URLs and external responses at their boundaries. Do not allow an external image name to escape a configured download directory; make any new network tests deterministic with fixtures.
- OS/DE support includes native APIs and well-defined external ecosystem tools. Distinguish implemented adapters from validated desktop outcomes. Platform compatibility must be established by evidence. README currently reports manual Windows 10/11 usage; Linux CI compilation does not prove successful wallpaper setting on Windows, macOS or Wayland.
- Existing limitations (including unwraps, error handling and absent Cargo.lock) are not evidence of supported behavior. Do not silently rewrite unrelated code to clean up the baseline.

## Mandatory workflow
1. Inspect repository, Issue, tests and current PR/CI status.
2. For non-trivial changes create/continue a real open GitHub Issue and a docs/exec-plans/active/<work-id>.md from TEMPLATE.md **before** implementation.
3. Define measurable acceptance criteria, staged implementation, risks, test plan, and exactly one "Resume from here" action.
4. Implement one coherent slice at a time; keep plan checkpoints and commands current.
5. Run targeted deterministic tests, then all applicable CI-equivalent checks; record observed results instead of assuming success.
6. Open a PR with exactly one Issue: #N and one Plan: docs/exec-plans/active/<work-id>.md metadata line. PRs must not bypass this linkage, including governance PRs.
7. Review code, CI runs, resulting artifacts and user-facing semantics. Do not merge a failing, pending or unverified revision.
8. Archive a plan in completed/ only once its acceptance criteria and final revision evidence are complete; close the Issue **after** completion PR is merged.

For work interrupted at any step, keep the plan in active/ and record the exact tested commit, what failed, and the next action. Conversation memory is not an authoritative record. Documentation typo-only edits may omit a detailed plan locally but PRs still require Issue/Plan for consistent CI enforcement.

## Agent evidence discipline
- FACT: observed in source, a specific command output, CI run, artifact or official API specification.
- ASSUMPTION: labeled in plan or ADR and not claimed as verified.
- UNASSESSED: missing evidence (including not-yet-run OS integrations or CI).
- PROPOSAL: unimplemented design.

Never claim passing Rust tests if Cargo did not run. An HTTP response in a mock proves the mock contract, not the live provider. Failing or skipped checks are not passing checks.

## Changes requiring an ADR and human decision
- New privileged integrations, key handling, telemetry or persistent user data.
- Backward-incompatible CLI defaults/flag changes, on-disk file naming and retention.
- Redesign of provider boundaries, desktop side effects, supported OS matrix.
- New dependency/toolchain strategy that materially changes portability or maintenance.

Routine fixes, tests and small refactors inside accepted boundaries do not require separate human approval.

## Repository map
- src/main.rs — backward-compatible CLI parsing, core fetch and local apply/doctor orchestration.
- src/setter.rs — OS/DE/WM detection, wallpaper backend selection and external command glue.
- crates/ezwallpaper-core/src/lib.rs — headless WallpaperManager/WallpaperAsset and JSON WallpaperManifest v1 contract; non-destructive local catalog.
- crates/ezwallpaper-core/src/wp_provider/ — Bing/Pexels adapters, locale and resolution.
- crates/ezwallpaper-core/src/wp_selector.rs — existing wallpaper provider value type.
- .github/workflows/ci.yml — required checks.
- docs/architecture.md — verified architecture and risks.
- docs/agents/ — detailed execution, verification and GitHub governance.
- docs/exec-plans/ — active/completed work state.
- docs/adr/ — durable architecture decisions.
- scripts/validate_agent_plan.py, tests/test_agent_plan.py — local and PR governance checks.

## Definition of done
- Implementation satisfies the linked plan/Issue and adds relevant regression tests.
- Rust fmt, Clippy, tests and offline CLI verification pass for the final revision.
- CI plan integrity and contract self-tests pass; actual CI run URL is recorded.
- Any Windows desktop action is claimed validated only if independent Windows evidence exists.
- Plan, README and ADRs are reconciled; known gaps stay explicit.
- Protected master merges only through the reviewed PR process configured by administrator (see docs/agents/github-merge-gates.md).
