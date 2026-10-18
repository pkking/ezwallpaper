# 2026-10-18-core-catalog-manifest: non-destructive core catalog API

Issue: #9
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Give headless consumers of the independent core a deterministic local image directory listing and stable versioned JSON manifests for local and fetched assets. Preserve legacy apply behavior.

## Non-goals

No persistent database/cache/index/retention, image decoding, deletion, recursive folder scan or global filesystem monitoring. No live provider/API calls in required CI.

## Must-read context

AGENTS.md, docs/adr/0001-core-cli-boundaries.md, docs/architecture.md, crates/ezwallpaper-core/src/lib.rs, src/main.rs, .github/workflows/ci.yml and Issue #9.

## Current facts

- master: `801077333da7b3fc7b554ad683676ffdcad690ca`.
- ADR 0001 accepted; core/CLI split shipped via PR #7 and archived Issue #6.
- Core manager provides fetch and open_local returning absolute regular-file paths with source; no catalog or manifest yet.
- CI already runs workspace Rust checks plus offline doctor/apply negative smoke.

## Constraints and invariants

- Core does not use wallpaper-rs, XDG session state or OS setters.
- list reads only direct regular files, skips symlinks, only image-like extensions; extension is not proof of content validity.
- Stable JSON schema `schema_version = 1`, no secrets or provider API tokens.
- `fetch` must never apply to desktop. Existing no-subcommand invocation continues fetch-then-apply.
- Never auto-delete, rename, mutate, recursively traverse or cache-scavenge user's files.

## Acceptance criteria

- [ ] Core asset metadata and versioned JSON manifest are implemented.
- [ ] Nonrecursive sorted local list is safe, filter documented and tested.
- [ ] CLI list and fetch subcommands output manifest/human data and preserve flag-only behavior.
- [ ] Deterministic offline tests and CLI smoke prove JSON output with no network or desktop setter.
- [ ] Four required checks pass at final PR head.

## Implementation slices

- [x] 1. Core non-destructive catalog, manifest schema and unit tests.
- [x] 2. CLI list/fetch output commands and CI/offline acceptance.
- [ ] 3. Documentation, review, full CI and checkpoint.

## Verification matrix

| Scope | Command / CI gate | Expected evidence | Status |
|---|---|---|---|
| Core | cargo test -p ezwallpaper-core | filters, sorting, JSON | pending |
| Workspace | cargo test --workspace --all-targets | all offline Rust tests | pending |
| Quality | cargo fmt and strict clippy | CI job Rust quality | pending |
| CLI | offline list --json, fetch --help | JSON v1, no GUI/network | pending |
| Governance | Agent plan integrity and contract self-tests | CI jobs | pending |

## Decision gates

User accepted publishing core outputs to OS consumers and agent-driven continuation. No permanent/persistent user-data semantics introduced. Any retention or cleanup policy remains a separate human decision.

## Evidence log

- 2026-10-18: initial implementation submitted; Rust format/compile/test evidence remains UNASSESSED until Actions.
- 2026-10-18: main baseline `801077333da7b3fc7b554ad683676ffdcad690ca`; created Issue #9 and plan-first branch.

## Deviations and discoveries

No additional deviations observed yet.

## Resume from here

Implement core directory catalog and JSON manifest plus CLI commands on `agent/core-catalog-manifest`. Open PR with Issue #9 and this plan; use latest GitHub Actions head SHA to resolve all failing gates.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (offline catalog and CLI smoke)
Remaining unassessed items: image decoding, durable cache index/retention, live DE and providers
