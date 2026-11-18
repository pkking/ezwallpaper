# 2026-11-20-versioned-export-contract-56: Issue #56

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-20
Last checkpoint: 2026-11-20

## Objective

Record a reviewable, safe integration contract and evidence-backed gap assessment for the SDDM/Plymouth portion of #56. Do not claim a privileged importer or complete G-03; provide a bounded next implementation slice because current upstream code has substantial event/consumer prework but no authorized root transaction.

## Goal alignment

Epic: #60
Goal: G-03
Contribution type: USER_JOURNEY
Gap: The user-owned per-output event mechanism exists, but does not establish safe system import or real SDDM/Plymouth outcome.
Before: At `c98640e0a8a928bffacb6f5fd92eb254880b9bf9`, `src/rotation_event.rs` publishes one versioned `<output>.json` per acknowledged output; `src/rotation_cli.rs::run_rotation` commits state before event and attempts guarded same-epoch event recovery. `scripts/read_wallpaper_events.py` can validate a requested multi-output epoch. `docs/examples/root-greeter-import-policy.md` documents read-only policy/target/source preflights and explicitly reports `privileged_import_implemented: false`.
After: A new adapter contract document maps implemented behavior, missing manifest/hook/importer pieces and SDDM/Plymouth operational semantics without implying live greeter/Plymouth verification or performing privileged actions.
Evidence plan: Rust and Python offline tests, formatting/lint checks, plan-integrity validation; PR CI. No system path or actual greeter/initramfs tests.
Priority rationale: G-03 is the named user journey and its existing implementation is explicitly partial. This slice clarifies the safe architecture boundary and the next acceptance work; it does not outrank or claim closure of outstanding G-01/G-02 evidence.
Remaining unassessed: Trusted root-owned importer transaction, real SDDM cache/reload behavior on supported theme, Plymouth initramfs update/next-boot feasibility, opt-in device evidence, and full #56 end-to-end acceptance.

## Non-goals

No root helper, systemd/system service, sudo, `/etc` or `/usr` writes, initramfs rebuild, theme mutation, SDDM restart, post-change hook executor, or assertion of physical pixels. No claim that user-writable event files authorize privileged writes.

## Must-read context

`AGENTS.md`; `docs/agents/goal-gates.md`; `docs/adr/0011-wallpaper-events.md`; `src/rotation_event.rs`; `src/rotation_cli.rs`; `scripts/read_wallpaper_events.py`; `docs/examples/root-greeter-import-policy.md`; `docs/examples/README.md`; private design input `/home/lcr/.local/share/chezmoi/docs/sddm-wallpaper-sync.md`.

## Current facts / gap matrix

- Event code: versioned per-output changed record, epoch, raw content ID and source path; exact-path acknowledgement only; no derived artifact metadata, wall-clock update timestamp, aggregate current manifest, fixed-argv hooks, timeout/exit handling or hook idempotency key.
- Apply: durable per-output rotation state precedes atomic event publication. Explicit same-epoch reconciliation validates source bytes and backend path; this repairs missing/stale event files without a second setter call. Multi-output event snapshot helper validates a requested same epoch but is not a producer-side cross-file atomic transaction.
- Consumer work: unprivileged read-only and user-owned sandbox/staging consumers exist. Root policy, target and inbox tools currently perform preflight only; documentation states `privileged_import_implemented: false`.
- Architecture: Rust workspace has headless `ezwallpaper-core` and CLI root package. Event publication is CLI-only (`src/rotation_event.rs`, `src/rotation_cli.rs`); no privileged integration belongs in Core.
- CI boundary: fixture tests only, no writes to `/etc`, `/usr`, or initramfs.

## Constraints and invariants

Preserve legacy behavior; all event output is explicit opt-in and user-owned. Never execute data from JSON. A future root adapter must independently require root-owned non-writable policy, enumerated consumer and fixed destinations, pinned/revalidated source snapshot, bounded image validation, target no-follow checks and staged atomic replacement preserving old target on pre-commit failure. No user-writable script may be executed as root. SDDM atomic file replacement does not promise a running greeter refresh; Plymouth update semantics are next-boot only after separately authorized initramfs rebuild.

## Acceptance criteria

- [x] Pin and record actual baseline/repository call chain and current/missing contract matrix.
- [x] Document staged follow-up and explicit SDDM/Plymouth cache/initramfs boundaries.
- [ ] Offline tests, Rust formatting/Clippy/tests, plan-integrity, and final CI.
- [ ] Open PR; leave Issue open and explicitly mark overall acceptance partial.

## Verification matrix

| Scope | Command / gate | Expected evidence | Status |
|---|---|---|---|
| Rust quality | `cargo fmt --check`; `cargo clippy --workspace --all-targets -- -D warnings`; `cargo test --workspace` | local output | pending |
| Python contracts | `python3 -m unittest discover -s tests` | local output | pending |
| Governance | `python3 scripts/validate_agent_plan.py --help` and relevant tests | local output | pending |
| CI | `gh pr checks --watch --fail-fast` bounded 600s | final PR head checks | pending |

## Evidence log

- 2026-11-20: `git fetch origin master`; baseline `origin/master=c98640e0a8a928bffacb6f5fd92eb254880b9bf9`; working branch created from this commit. Existing workspace artifacts were untracked `Cargo.lock`, `scripts/__pycache__/`, `tests/__pycache__/`; preserved.
- 2026-11-20: inspected event producer, CLI commit/recovery sequence, goal gates, existing root policy doc, consumer overview and local SDDM synchronization runbook.
- 2026-11-20: `cargo fmt --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace` passed (209 tests reported across five suites). Full Python unittest discovery has one unrelated baseline static assertion failure in `tests/test_adapter_boundaries.py::test_protocol_and_registry_are_isolated` (expects old `noctalia_ipc(&set_args)?` call shape while current `src/backend/noctalia.rs` routes through `apply_noctalia_with`); remaining result not represented as all-green. Plan validator cannot run standalone without CI `GITHUB_EVENT_PATH`/`PR_BASE_SHA`/repo env.

## Resume from here

Add contract document and link from `docs/examples/README.md`, run listed checks, then open a non-merge PR with G-03 partial-scope fields and explicit remaining unassessed requirements.

## Completion

Final commit: pending
CI run: pending
E2E artifact: not applicable; this is a contract/gap documentation slice only.
Remaining unassessed items: see Goal alignment.
