# 2026-10-18-gnome-plasma6-compat: robust Linux DE adapters

Issue: #12
Status: COMPLETED
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

- Implementation base master `b30d65f88a300d7847ce4dd282983456ca47c605` already has split core / CLI, catalog manifest, and adapter selection; last accepted Issue #9.
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

- [x] GNOME gsettings uses safe file URIs, handles dark key when available.
- [x] Plasma command adapter prefers qdbus6 over qdbus and parses multi-token desktop IDs.
- [x] Linux fallback, no-session and other-Unix behavior remain explicit and tested.
- [x] Documentation captures support mechanisms and evidence limits.
- [x] All four required PR checks pass at final HEAD.

## Implementation slices

- [x] 1. Explicit GNOME and Plasma command adapters with safe URI/script.
- [x] 2. Pure detection/test matrix, capability reporting and documentation.
- [x] 3. Final CI and review; archive after merge.

## Verification matrix

| Scope | Command / CI | Evidence | Status |
|---|---|---|---|
| Detection | cargo test --workspace --all-targets | GNOME/KDE/multi-value tests | CI #39096277905: passed |
| Formatting | cargo fmt --all -- --check | CI quality job | CI #39096277905: passed |
| Static quality | cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | CI quality job | CI #39096277905: passed |
| CLI smoke | doctor, apply missing file, list manifest | no network/GUI | CI #39096277905: passed |
| Governance | Agent plan and contract checks | CI jobs | CI #39096277905: passed |

## Decision gates

User explicitly approved broad ecosystem-program OS support and delegated implementation details. This is within established ADR; no new user-visible breaking flags, privileged integrations or persistent storage.

## Evidence log

- 2026-10-18: GNOME/Plasma adaptation committed; CI unassessed pending PR checks.
- 2026-10-18: inspected source and official GNOME/KDE/qdbus6 docs; created Issue #12 and plan.
- 2026-10-18: PR #13 head 3e23a7ddd4b1e678f9dd0c384eaf34ecbf739241 passed four jobs in https://github.com/pkking/ezwallpaper/actions/runs/39096277905 (Agent plan integrity; Agent contract self-tests; Rust quality; Rust tests and CLI smoke).
- 2026-10-18: PR #13 squash merged to master as 1aa5ca658a04398f594a3d7b9cc3a581ad24860a.

## Deviations and discoveries

The first PR #13 run failed rustfmt only; all identified formatting issues were corrected in 3e23a7d. The final four CI jobs passed. No live desktop integration was tested.

## Resume from here

Verify the completion-only archival PR CI on its final head, merge it if green, then close Issue #12.

## Completion

Final commit: 1aa5ca658a04398f594a3d7b9cc3a581ad24860a (squash merge of validated 3e23a7d)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39096277905
E2E artifact: offline CLI smoke under Rust tests and CLI smoke job (no live desktop)
Remaining unassessed items: real GNOME dark-mode and Plasma6 desktop integration, custom compositor process lifetime, full multi-monitor coverage
