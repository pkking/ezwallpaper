# source-only uninstall documentation and isolated evidence

Issue: #326
Status: READY_FOR_REVIEW
Owner: agent
Started: 2026-11-16
Last checkpoint: 2026-11-16

## Objective

Document a safe, reproducible source-only uninstall that removes only the ezwallpaper executable, defaults to retaining user data and user-authored systemd units, and records isolated evidence without touching the production user manager or desktop.

## Goal alignment

Epic: #60
Goal: G-00
Contribution type: MAINTENANCE
Gap: Issue #326's M3 lifecycle gate has no source-only uninstall procedure separating the Cargo binary from user-owned units, profiles, state, and wallpaper pools.
Before: At baseline d6598ae, README explains opt-in installation of user-authored timer examples but has no uninstall procedure; program and user data retention/removal boundaries are not gathered in one place.
After: README gives distinct Cargo-root and manually versioned-layout removal steps, makes service/timer and user-data cleanup separate explicit choices, and defines post-uninstall checks.
Evidence plan: Install into disposable HOME/XDG paths and a private Cargo root, hash seeded user data around the documented uninstall, test binary absence and retained fixtures, inspect user-unit commands without invoking the production `systemctl --user` manager, then record final-head CI/PR checks.
Priority rationale: This is the explicitly scoped M3 lifecycle acceptance in open Issue #326, complementing source-only clean-install evidence and preventing accidental user-data loss; it does not claim to resolve higher-priority G-01/G-02 physical acceptance.
Remaining unassessed: Live user-manager timer shutdown, physical wallpaper rendering/preservation, real user's shell aliases, custom install roots, and upgrade/rollback paths beyond the isolated uninstall fixture.

## Non-goals

- No changes to runtime code, install automation, systemd units, aliases, user profiles, or desktop settings.
- No production user-systemd commands, desktop mutation, or user-data deletion during tests.
- No claim that deleting the executable automatically disables user-authored timers.

## Must-read context

- Issue #326, README timer example documentation, `docs/exec-plans/TEMPLATE.md`, `AGENTS.md`, and `.github/PULL_REQUEST_TEMPLATE.md`.
- `docs/agents/goal-gates.md` (G-00 mapping) and `scripts/validate_agent_plan.py`.

## Current facts

- Repository/head SHA: `/home/lcr/.local/state/dotfiles-submission/ezwallpaper-timer-fix-work2-20261115T133517Z/repo`, base `d6598ae0d867890f42f0f0186efbae27a9ea6627` (origin/master).
- CI checks actually observed: local plan tests only; GitHub CI pending.
- Supported platforms vs unassessed: source-only procedures are portable documentation with user-systemd specifics; actual live user manager behavior is unassessed here.
- Existing behavior and limitations: Cargo-managed binary may be uninstalled via Cargo or exact root binary removed; manually installed version directories/aliases and example user units are user-managed. Rotation state/config/materials are user data and not removed by the executable.

## Constraints and invariants

- Only remove an executable known to belong to ezwallpaper; never recursively remove Cargo roots, shared directories, unit directories, or unverified symlink targets.
- Default path retains all user data and user-authored units. Stop/disable/delete units and delete data are separate explicit decisions.
- Do not use a temporary HOME as justification to invoke `systemctl --user`; the user manager can still be production. Fixture-level checks must be described honestly.
- Evidence directory and logs must be private (0700 directories, 0600 files); never retain personal data.

## Acceptance criteria

- [x] README distinguishes Cargo install-root and manually versioned source layouts, including exact executable-removal options and ownership caution.
- [x] README defaults to retaining config/state/materials and user-authored units; documents separate opt-in unit and data cleanup with confirmation/backup language.
- [x] Isolated installation/uninstall records command exits, binary non-executability, and before/after hashes proving fixture data retention; no production manager or wallpaper is touched.
- [ ] Plan integrity and relevant CI checks pass, and PR metadata links this Issue/plan exactly once.

## Implementation slices

- [x] 1. Confirm baseline d6598ae and create linked active plan.
- [x] 2. Add README uninstall guidance and run isolated Cargo-root and manual-version-layout fixtures.
- [ ] 3. Complete final plan/CI verification, commit and open PR; leave unmerged.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Isolated source install/uninstall | `cargo install --path <repo> --root <private-root>`; `cargo uninstall --root <private-root> ezwallpaper` | both exit 0; binary version then exact path absent and PATH lookup fails; private evidence log | pass |
| Data retention | SHA manifests for XDG config/state/events/share/material/pictures and unit fixture files | manifests byte-identical; SHA-256 `0fb742a06b7824e925037cf914e0a1dfaeca19363e2e8ae86dadbcbdfe4cc2fd` | pass |
| Manual version layout | delete only isolated `<sha>` fixture dir | target absent; alias deliberately left separate; unrelated version sentinel SHA unchanged | pass |
| User unit boundary | file fixtures only | no production `systemctl --user` invocation; runtime timer shutdown unassessed | pass with boundary |
| Repository governance | plan unittest suite and `git diff --check` | 29 tests pass; diff clean | pass |
| CI | GitHub required checks for exact PR head | final-head status recorded | pending |

## Decision gates

None. `systemctl --user disable --now` is only documented as a user-confirmed action in the user's own session; it is not run in this evidence workflow.

## Evidence log

- 2026-11-16: fetched `origin/master`; exact base `d6598ae0d867890f42f0f0186efbae27a9ea6627`; Issue #326 is open. Existing workspace has unrelated untracked `Cargo.lock`; leave it untouched.
- 2026-11-16: README uninstall guidance added at lines 211-230. Isolated Cargo install/version/uninstall verified; binary removed and data manifest unchanged. Manual version-dir fixture removed only its exact version; unrelated sentinel preserved. Plan tests 29/29 and `git diff --check` pass. Evidence report: `/home/lcr/.local/state/dotfiles-submission/upstream-uninstall-docs-20261116T175602Z/REPORT.md`. No user manager or real wallpaper tested.

## Deviations and discoveries

- The checkout arrived detached at the required baseline. Created branch `docs/uninstall-source-only-326` from that baseline without altering the unrelated untracked `Cargo.lock`.
- The `scripts/validate_agent_plan.py` entry point expects GitHub event environment variables rather than a `--help` flag; the first exploratory invocation reported missing `GITHUB_EVENT_PATH`. No repository files were changed by that failed invocation.

## Resume from here

Run final local plan/PR metadata checks, then stage only README and this plan; commit/push non-force and open the Issue #326 PR. Record exact PR head and bounded CI results in the private checkpoint without merging.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable; isolated uninstall evidence at `/home/lcr/.local/state/dotfiles-submission/upstream-uninstall-docs-20261116T175602Z/REPORT.md`
Remaining unassessed items: live user-manager timer shutdown, physical wallpaper preservation, custom user aliases/roots, and full upgrade/rollback matrix
