# 2026-10-18-core-cli-workspace: split wallpaper management from desktop integration

Issue: #6
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Provide a headless-safe reusable wallpaper core, preserve the ezwallpaper command, and add explicit OS/DE diagnostic and local-file application capabilities. Treat ecosystem wallpaper executables as valid supported adapters when their prerequisites and observed behavior are documented.

## Non-goals

No new persistent cache database, no daemon, no breaking change to existing `--backend/--resolution/--locale/--dir/--token/--download-only` default behavior, no live provider or desktop test in CI, no claim of verified platform compatibility without platform CI.

## Must-read context

AGENTS.md, docs/architecture.md, docs/agents/testing.md, docs/agents/workflow.md, docs/adr/README.md, current src/main.rs, src/wp_provider/*, src/wp_selector.rs, .github/workflows/ci.yml.

## Current facts

- Original master: `12752764dd927ab4609755279eac566c8bba649d`.
- Single Rust 2018 binary currently downloads via Bing or Pexels and calls wallpaper::set_from_path directly.
- README only claims manual Windows 10/11 usage; Actions Ubuntu CI exercises offline CLI but not desktop.
- wallpaper crate v3.2.0 supports certain XDG desktops via system executables, fallback swaybg/feh but not robust capability detection or outcome verification.
- Cargo.lock is not tracked, so builds are not fully reproducible. No local Cargo toolchain in agent container; use GitHub Actions as Rust evidence.

## Constraints and invariants

- Core cannot depend on wallpaper crate or read XDG/OS session state or invoke desktop wallpaper setters.
- Core source and file paths remain separately testable from network; never perform real downloads or desktop changes in CI.
- No secrets, Pexels tokens, user wallpaper paths or untrusted files in logs.
- Default CLI flags and behavior remain compatible; additive commands must not break flag-only invocations.
- No implicit filename/path traversal or cache deletion introduced by this architectural slice.
- External backends must document prerequisites and distinguish command/process launch from verified desktop effect.

## Acceptance criteria

- [ ] ADR documents capability-based OS/DE support and core/CLI responsibilities.
- [ ] Core is independently buildable/testable and exports source, asset and manager interfaces without OS setter.
- [ ] Existing flag-only command still fetches and applies (or download-only).
- [ ] CLI includes offline doctor and apply of local path with explicit error semantics.
- [ ] Detection and core boundary unit tests plus CLI smoke run without network or GUI.
- [ ] All four required PR checks pass for final implementation HEAD and evidence is logged.

## Implementation slices

- [x] 1. Architecture ADR, workspace wiring and core migration.
- [x] 2. CLI setter adapter + doctor + offline tests.
- [ ] 3. CI integration, documentation and final validation.

## Verification matrix

| Scope | Command / CI gate | Expected evidence | Status |
|---|---|---|---|
| Plan validator | Agent plan integrity | Issue #6 metadata/updated plan | pending |
| Core | cargo test -p ezwallpaper-core | mock providers and asset checks | pending |
| Rust | cargo fmt / clippy -D warnings -W clippy::unwrap_used | deterministic quality | pending |
| CLI | cargo test --all-targets | detection and adapter tests | pending |
| Offline acceptance | CLI --help, --version, --backend bad, doctor and apply bad path | no network/desktop mutation | pending |
| Final CI | 4 required jobs | final SHA, URLs/artifacts | pending |

## Decision gates

User approved the two-part core/CLI model and widened OS support definition; routine implementation choices delegated. Any breaking change to existing flags, persisted cache/retention, or privileged integrations requires a fresh decision.

## Evidence log

- 2026-10-18: workspace/core extraction and CLI detection committed as `f074e8fedc13af54e689a0edd8138bac8c7b90d9`; tests remain UNASSESSED pending GitHub Actions.
- 2026-10-18: baseline commit `12752764dd927ab4609755279eac566c8bba649d`; inspected current code and CI using linked GitHub connection.
- 2026-10-18: Issue #6 created; following branch and plan-first governance.

## Deviations and discoveries

Initial architecture can preserve providers' old GetImgUrl and WallPaper shapes inside core while introducing a stable WallpaperAsset/WallpaperManager boundary; richer catalog schemas are staged later.

## Resume from here

Open PR from agent/core-cli-workspace; run full GitHub Actions checks. Fix first failing formatter/compiler/contract gate and rerun. Archive only after final head CI succeeds.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (offline CLI evidence)
Remaining unassessed items: real Windows/macOS/Wayland desktop integrations, online API integration and durable cache/retention
