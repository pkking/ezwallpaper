# 2026-10-23-wallpaper-backend-gnome-global-83: GNOME global setter adapter extraction

Issue: #83
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-23
Last checkpoint: 2026-10-23

## Objective

Extract the existing GNOME GSettings wallpaper setter from the legacy setter facade into a dedicated CLI-owned `src/backend/gnome.rs` module. Implement the already-accepted `WallpaperBackend` adapter contract as **GlobalOnly** with **CommandAccepted** acknowledgement and a single global target; preserve exact existing one-shot CLI/default selection, URI encoding, light/dark handling and error semantics. Use deterministic injected fake subprocess contracts for offline tests. Keep the Noctalia-only acknowledged Rotation Controller unchanged: a global GSettings command exit is not exact wallpaper-path readback or pixel proof.

## Non-goals

No new GNOME rotation support, no physical GNOME session, no privilege/persistent timer, no display enumeration, no user configuration change in CI, no BackendRegistry rotation selection change, no Core changes, no Plasma/Sway/Hyprpaper/Portal implementation, no new dependencies or state contract.

## Must-read context

AGENTS.md; Issue #83 latest checkpoint; docs/adr/0010-wallpaper-backend-adapter-contract.md; docs/agents/workflow.md; docs/agents/testing.md; docs/architecture.{md,svg}; src/setter.rs; src/backend/{mod,registry,noctalia}.rs; src/rotation_cli.rs; README.md; tests/test_desktop_adapter_contract.py. B1 PR #86 exact-head CI #39823542531 8/8 SUCCESS and merge SHA `b8bb928adf1595ae0d3e1b653540ed6c06c07a91`. B1 archive PR #87 is independently running CI; do not incorrectly claim it merged.

## Current facts

- Base master: `b8bb928adf1595ae0d3e1b653540ed6c06c07a91`, exact B1 tested HEAD `99405ff04c1bd5e3b9655dfaaec7c28713176d10` run #39823542531 8/8 SUCCESS.
- GNOME currently uses `Adapter::GnomeGsettings` in `src/setter.rs`, reads `file_uri`, sets `org.gnome.desktop.background picture-uri`, probes `gsettings writable picture-uri-dark` and sets dark only if writable; reports `Submitted`, never `PathObserved`.
- B1 `WallpaperBackend` currently accepts a named output string; GNOME **GlobalOnly** is deliberately ineligible for per-output rotation and must not be registered as Noctalia replacement. Keep production target selection and default CLI unchanged.
- Issue #79 download limit is independently worked on outside this branch, not in scope.

## Constraints and invariants

- Preserve subprocess argv (no shell), JSON/GVariant encoded file URI and default light + conditional dark behavior. A failed picture-uri set must not continue to dark. If dark-probe exits nonzero, do not attempt dark; if it fails to launch, report the existing error. Never log a secret or mutate a real desktop in CI.
- GNOME backend applies to explicit global target only; reject named outputs, report GlobalOnly/CommandAccepted. No rotation state commit can result from Submitted.
- Legacy `apply` should call the concrete GNOME module and keep `Submitted` result. Existing Noctalia and other setter paths untouched; avoid import cycle between backend module and setter.
- Tests must simulate gsettings success/failure, dark key writable/unwritable, unsafe output scope, URI escaping and no real desktop operations. Current README/diagram should mark the GNOME module **implemented only for global one-shot setting**, not for automatic rotation; remaining platforms stay PLANNED. The ADR 0010 architecture decision is unchanged; synchronize docs/architecture.svg if depicting this newly implemented backend.
- Never imply native GNOME screen pixels were verified by fake commands or headless GitHub Actions.

## Acceptance criteria

- [ ] `backend/gnome.rs` implements GlobalOnly / CommandAccepted with explicit global target, no independent output enumeration or false path readback.
- [ ] Existing `setter.rs` GNOME one-shot delegates to the concrete module without altering auto/default selection, gsettings sequence or outward Submitted result.
- [ ] Offline injected-command tests validate URI, light, optional dark, write failure, missing process, named-target refusal and no actual host execution.
- [ ] Update README, architecture.md, SVG with truthful GNOME one-shot module status; Core, registry, rotation state and 60-minute default remain unchanged.
- [ ] Latest exact PR HEAD 8/8 CI checks SUCCESS, including Windows/macOS and virtual Noctalia E2E; no live GNOME claims.
- [ ] Record actual SHA, CI and scope; after successful implementation merge, archive in independent completion PR and keep Issue #83 OPEN.

## Implementation slices

- [x] GNOME module plus unit/fake runner tests and setter facade delegation authored; latest-head CI not yet run.
- [x] Architecture/README diagram synchronized and static regression check authored; validation pending CI.
- [ ] Exact-head CI, repair as needed, GitHub API squash merge and separate archive.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Rust quality | cargo fmt + strict clippy | PENDING |
| GNOME offline behavior | Rust unit + desktop contract tests | PENDING |
| Noctalia existing behavior | isolated Noctalia+Sway native E2E | PENDING |
| Platform and governance | latest-head 8/8 CI | PENDING |
| Real GNOME output | manual opt-in actual GNOME | UNASSESSED |

## Decision gates

None: additive internal extraction fits already-accepted ADR 0010. Any new GNOME rotation or change of public CLI/OS support policy needs its own separately reviewed design.

## Evidence log

- 2026-10-23: B1 implementation #86 merged and validated. This B2 plan created before code changes.
- 2026-10-23: authored `src/backend/gnome.rs` GlobalOnly / CommandAccepted backend and injected GSettings fake-runner tests, registered module, rewired existing one-shot GNOME setter through the private trait (no direct controller change); static guard, README/architecture.md/architecture.svg reflect GNOME global one-shot implementation only. GitHub implementation commit range starts `85fd4e3ff30923ad4cc85832d042a3cdbd94c256`; **no Cargo/rustfmt or CI executed locally**, no physical GNOME evidence or live setter invocation.

## Deviations and discoveries

None yet.

## Resume from here

Create Issue #83-linked implementation PR from `agent/wallpaper-backend-gnome-global-83` with this active plan, inspect new exact-head all 8 GitHub Actions CI jobs. Diagnose compile/Rustfmt/Clippy or test errors from actual logs; repair original PR branch and rerun before merging. GNOME must stay GlobalOnly/Submitted, no new unattended rotation or real desktop writes.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable to live GNOME; virtual regression gate pending
Remaining unassessed items: real GNOME desktop, all GNOME multi-output/rotation, Plasma and other desktop adapters.
