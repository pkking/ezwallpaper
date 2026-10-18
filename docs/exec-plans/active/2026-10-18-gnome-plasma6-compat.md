# 2026-10-18-gnome-plasma6-compat: robust Linux DE adapters

Issue: #12
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Improve Linux desktop native compatibility via ecosystem commands, including GNOME light/dark wallpaper and Plasma 6 qdbus6, with accurate command and desktop detection and no false integration claims.

## Non-goals

No live desktop, online, swaybg daemon state or multi-monitor setting in CI. No persistent data, new background daemon or user privacy exposure.

## Must-read context

AGENTS.md, docs/adr/0001-core-cli-boundaries.md, docs/architecture.md, src/setter.rs, src/main.rs, Cargo.toml, .github/workflows/ci.yml.

## Current facts

- Current master `b30d65f88a300d7847ce4dd282983456ca47c605` already has split core / CLI, catalog manifest, and adapter selection; last accepted Issue #9.
- wallpaper-rs 3.2.0 GNOME only sets `picture-uri`; upstream KDE adapter calls `qdbus` and requires exact `KDE`.
- GNOME 42+ supports `picture-uri-dark`; KDE documents `evaluateScript`; Qt6 systems ship `qdbus6`.
- CI Ubuntu does not operate a real user desktop; all OS integration results unassessed until a platform runner tests visible outcomes.

## Constraints and invariants

- Keep original CLI flags and headless core independent; integrate only in CLI setter.
- Use OS-ecosystem commands, detect actual executable and session, escape file URI/script safely.
- Preserve Gnome systems that do not expose picture-uri-dark; do not silently report verified visual outcome.
- No network or desktop mutation in CI; test pure resolvers and pure script generation.
- Do not claim full Plasma 6 or GNOME validation solely from command availability.

## Acceptance criteria

- [ ] GNOME gsettings uses safe file URIs, handles dark key when available.
- [ ] Plasma command adapter prefers qdbus6 over qdbus and parses multi-token desktop IDs.
- [ ] Linux fallback, no-session and other-Unix behavior remain explicit and tested.
- [ ] Documentation captures support mechanisms and evidence limits.
- [ ] All four required PR checks pass at final HEAD.

## Implementation slices

- [ ] 1. Explicit GNOME and Plasma command adapters with safe URI/script.
- [ ] 2. Pure detection/test matrix, capability reporting and documentation.
- [ ] 3. Final CI and review; archive after merge.

## Verification matrix

| Scope | Command / CI | Evidence | Status |
|---|---|---|---|
| Detection | cargo test --workspace --all-targets | GNOME/KDE/multi-value tests | pending |
| Formatting | cargo fmt --all -- --check | CI quality job | pending |
| Static quality | cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | CI quality job | pending |
| CLI smoke | doctor, apply missing file, list manifest | no network/GUI | pending |
| Governance | Agent plan and contract checks | CI jobs | pending |

## Decision gates

User explicitly approved broad ecosystem-program OS support and delegated implementation details. This is within established ADR; no new user-visible breaking flags, privileged integrations or persistent storage.

## Evidence log

- 2026-10-18: inspected source and official GNOME/KDE/qdbus6 docs; created Issue #12 and plan. CI pending.

## Deviations and discoveries

No material deviations yet.

## Resume from here

Implement adapters on `agent/gnome-plasma6-compat`, open PR, inspect latest four CI checks and fix any failure before merge. Archive plan in completion-only PR after merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending (offline CLI only)
Remaining unassessed items: real GNOME dark-mode and Plasma6 desktop integration, custom compositor process lifetime, full multi-monitor coverage
