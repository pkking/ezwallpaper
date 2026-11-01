# issue-56-png-payload-integrity: Issue #56

Issue: #56
Status: VERIFYING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

Strengthen all SDDM/Plymouth candidate and root-inbox preview validation with a reusable strict bounded static PNG chunk/CRC/IDAT check, rather than trusting only the 33-byte header and IEND substring. Do not claim a privileged decoder or support for arbitrary PNG variants.

## Non-goals

No root image import or policy installation, no sudo capability, no initramfs or login theme modification, no shell hooks, no actual lock or compositor mutation, no automatic claims of physical display validation.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/adr/0011-wallpaper-events.md, scripts/preview_greeter_candidate.py, scripts/verify_root_greeter_inbox.py, scripts/inspect_greeter_target.py, scripts/preview_root_greeter_policy.py, Issue #56.

## Current facts

- Master 70bf648909461f91263b4150737c94ede5048b9d checked; no open PR.
- Existing root-side source digest and metadata checks are read-only and fixed-path.
- Existing Python image validation reads only IHDR + a tail substring for IEND, unlike image-rs Core's full opt-in decoding.
- Trustworthy greeter installation, actual SDDM reload and Plymouth initramfs activation remain unimplemented.

## Constraints and invariants

- Strict bounds for bytes, pixels and resources. Never execute or implicitly trust unprivileged event JSON for root policy.
- Read-only default and tests, no /etc or /usr writes, no root-only CI.
- Fixed schema and conservative status names; no authorization-token output.
- One Issue and one plan per PR. Existing Rust and CI checks not weakened.

## Acceptance criteria

- [x] Positive and negative fixture tests authored; CI execution pending.
- [x] Read-only API and fixture checks without system writes.
- [x] Documented validation versus actual privileged import and real display boundaries.
- [ ] All required checks green on final exact HEAD.

## Implementation slices

- [x] Implemented source/protocol check.
- [x] Added offline tests and required CI gate.
- [x] Documentation complete; PR creation next and CI evidence pending.

## Verification matrix

| Gate | Evidence | State |
|---|---|---|
| Offline fixtures | required GitHub CI | pending |
| Rust, platform, Sway | GitHub CI | pending |
| Live SDDM/Plymouth | no execution | UNASSESSED |

## Decision gates

Privileged import/rollback mechanism requires separate security and user-visible OS policy approval. This PR changes only read-only validation or operator planning.

## Evidence log

- 2026-11-01: inspected master 70bf648909461f91263b4150737c94ede5048b9d and relevant scripts; no open PR.

## Deviations and discoveries

Implemented bounded static PNG full chunk CRC + zlib scanline-structure checker, integrated greeter read-only candidate/inbox, added corruption and bomb fixtures in required contract CI. No actual pixel reconstruction or privileged decoding.

## Resume from here

Inspect exact PR-head checks and fix failures. Merge only after all mandatory CI checks complete successfully and master remains compatible.

## Completion

Final commit: pending
CI run: pending
System import: UNASSESSED
