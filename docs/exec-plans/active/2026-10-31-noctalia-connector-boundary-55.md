# Noctalia connector boundary parity

Issue: #55
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-31
Last checkpoint: 2026-10-31

## Objective

Reject overlong named Noctalia connector identifiers in one-shot apply at the same 128-byte boundary as rotation profile validation, before issuing any IPC call.

## Non-goals

No desktop mutation in tests, protocol redesign, renderer fallback, source/provider changes, changes to default CLI behavior, or claim of pixel evidence.

## Must-read context

AGENTS.md; docs/agents/workflow.md; src/backend/noctalia.rs; src/rotation_cli.rs; docs/adr/0004-noctalia-v5-ipc.md; Issue #55.

## Current facts

- Baseline master: e3d2bc3c4fb50802090ab45d2dd7179b96f26dd9.
- Open PRs: none at inspection.
- Rotation profile validation: src/rotation_cli.rs valid_connector limits output to 128 bytes.
- Noctalia backend validate_connector currently checks token characters but does not bound length.
- Actual niri + Noctalia physical pixel state remains unassessed.

## Constraints and invariants

- Noctalia alone owns rendering. No swaybg fallback.
- Valid connector spellings, IPC argv, one-shot/global semantics and acknowledged-only rotation remain unchanged.
- Reject overlong connectors prior to subprocess invocation and without touching state.
- Reuse existing adapter, avoid new dependency and ADR.

## Acceptance criteria

- [ ] Noctalia validates names of 1–128 ASCII token bytes and rejects 129.
- [ ] Unit regressions prove rejection before fake IPC, including global and per-output compatibility.
- [ ] Exact-head required CI passes; no claim of live pixel coverage.

## Implementation slices

- [ ] Add parity bound and focused Rust test.
- [ ] Review PR CI at exact head; archive in separate completion PR after passing evidence.

## Verification matrix

| Scope | Command / gate | Status |
|---|---|---|
| Rust fmt | cargo fmt --all -- --check | pending CI |
| Rust tests | cargo test --workspace --all-targets | pending CI |
| Clippy | cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | pending CI |
| Governance | CI plan-integrity | pending CI |

## Decision gates

None. Limit already exists in rotation profile validation; align one-shot adapter.

## Evidence log

- 2026-10-31: inspected master e3d2bc3c4fb50802090ab45d2dd7179b96f26dd9 and Noctalia adapter; 128-byte mismatch confirmed from source. No tests run in this work item yet.

## Deviations and discoveries

None.

## Resume from here

Inspect the new PR's exact-head CI and fix any failures before merging. Real niri / Noctalia dual-output verification remains tracked by #59.

## Completion

Final commit: pending
CI run: pending
E2E artifact: unassessed (physical compositor)
