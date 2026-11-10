# 2026-11-10: Durably publish opt-in Noctalia restoration manifest before applying wallpaper

Issue: #59
Status: PLANNING
Owner: agent
Started: 2026-11-10
Last checkpoint: 2026-11-10

## Objective

Before the consent-gated niri+Noctalia physical dual-output verifier issues any wallpaper setter, persist the private original-wallpaper recovery manifest and relevant directory entries to disk using an explicit directory fsync barrier. If persistence fails, abort with a stable non-sensitive error and never modify either desktop output.

## Non-goals

No default desktop changes, new CLI flags, generic filesystem transaction framework, automatic recovery after reboot, power-loss guarantee for all remote/unsupported filesystems, persistent new user data, or physical testing in CI. No assumption that virtual Wayland framebuffer evidence proves physical 4K/GPU/hotplug behavior.

## Must-read context

AGENTS.md; README.md; Cargo.toml; docs/agents/workflow.md; docs/agents/testing.md; docs/adr/0001-core-cli-boundaries.md; docs/exec-plans/TEMPLATE.md; Issue #59; scripts/verify_noctalia_live.py (verify_dual, recovery.json creation and finally restoration); tests/test_noctalia_live_verification.py (FakeDesktop, recovery permissions and offline safety fixtures).

## Current facts

- Base master: `795fc8eda970b24813dab8d34782747a4d28213b`; latest completed master push [run 42836230370](https://github.com/pkking/ezwallpaper/actions/runs/42836230370) SUCCESS. Zero open PRs at inspection.
- The helper creates a new 0700 proof directory and 0600 `recovery.json`, flushes and `fsync`s the JSON **file**, then proceeds to capture baseline images and potentially apply fixture wallpaper. It does **not** fsync the newly created proof directory nor its parent. A process/power failure can therefore leave directory entries not durably committed even if file contents were fsynced, depending on filesystem semantics.
- Existing restoration protects against stale connector topology, other clients' wallpaper paths, stdout UTF-8, nested interrupts and oversized screenshots; separate prior PRs completed these slices. Do not recreate or weaken them.
- Real hardware, GPU/4K/hotplug, and lockscreen remain UNASSESSED. All new tests must use an injected fake desktop and temporary files only.

## Constraints and invariants

- Preserve exact existing opt-in/TTY requirements, output path ownership and topology checks, isolated fixture behavior, privacy/permissions and failure artifacts.
- Use Linux/POSIX directory fsync: fsync manifest file first, proof directory for `recovery.json` entry, then proof directory's parent for newly created proof-dir entry. Keep file/directory descriptors closed on every path.
- Fail closed with a stable error `cannot_persist_recovery_manifest` on any write, flush, file fsync or required directory fsync failure, **before** first wallpaper-set. Do not include user paths, device serials, or credentials in reportable errors.
- Do not claim generic power-loss atomicity on network or exotic filesystems; fsync is a reasonable local-filesystem durability barrier, not a physical hardware test.

## Acceptance criteria

- [ ] Successful fake desktop path executes manifest file, proof directory and parent fsync before first wallpaper apply; recovers/restores two outputs with prior JSON/permission behavior unchanged.
- [ ] Failure to fsync a directory raises stable `VerificationError`, issues zero wallpaper setters and leaves original wallpaper untouched.
- [ ] Failure to fsync the manifest file similarly issues zero setters; no sensitive paths leak in error string.
- [ ] Final-head Python Noctalia safety tests and all applicable Rust, Sway, Windows/macOS, agent-plan, and native virtual framebuffer CI checks pass.

## Implementation slices

- [ ] Add a small Linux-only durability helper and fail-closed publication barrier to opt-in `verify_dual`.
- [ ] Add fake-desktop file/dir/parent fsync order and failure-injection regressions.
- [ ] Run applicable exact-head CI and merge tested head only after all gates pass.

## Verification matrix

| Scope | Required evidence | Status |
|---|---|---|
| Noctalia safety | `python3 -m unittest discover -s tests -p 'test_noctalia_live_verification.py' -v` | PENDING |
| Rust/platform | Full CI fmt/clippy/tests, Windows/macOS | PENDING |
| Virtual pixels | Noctalia native Sway and niri dual-output framebuffer + Sway | PENDING |
| Governance | PR agent plan integrity and self-tests | PENDING |

## Decision gates

None: opt-in verifier safety fix. No product runtime, default, privilege, persistent schema or Core/CLI adapter interface changes. Architecture diagram: unchanged - only restoration evidence durability in a test helper, no Core/consumer source boundary or accepted ADR change.

## Evidence log

- 2026-11-10: inspected current master, open PR/Issues and exact recovery record creation. Baseline CI 42836230370 SUCCESS; no new branch tests executed yet.

## Deviations and discoveries

None.

## Resume from here

Implement file/child/parent fsync barrier in `scripts/verify_noctalia_live.py`, add fully offline failure-injection tests, then open Issue #59-linked PR and verify its exact head CI. Never run on a real user session.

## Completion

Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical GPU/4K/hotplug/lockscreen, external filesystem power-loss behavior, IPC ownership race after last check.
