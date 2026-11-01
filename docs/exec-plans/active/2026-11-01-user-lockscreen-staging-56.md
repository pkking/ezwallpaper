# lockscreen - Issue #56

Issue: #56
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-01
Last checkpoint: 2026-11-01

## Objective

A manually invoked unprivileged lockscreen asset stage: read one exact-epoch acknowledged event, verify source SHA-256 from opened file, and atomically stage the PNG into a caller-prepared user directory. No change to actual compositor or lock-screen config.

## Non-goals

No root service, SDDM/Plymouth modification, initramfs rebuild, executable hooks, real lockscreen/screen mutation, automatic schedule, background daemon or unsupported decoder security claim.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; scripts/read_wallpaper_events.py; tests/test_wallpaper_events_consumer.py; docs/adr/0011-wallpaper-events.md; docs/examples/README.md; Issue #56.

## Current facts

- Master SHA e579c6ff13ef39345c30a2b8497e4332903eca19.
- Event read-only contract already validates strict JSON, requested epoch, output and acknowledgement but does not open the image or verify source digest.
- No privileged importer exists, existing event files and image paths remain user-controlled.
- PR #147 is open and touches niri rotation; this branch avoids its files.

## Constraints and invariants

- Reuse `read_wallpaper_events.snapshot()` and strict CLI argument handling; never execute event strings.
- Open source no-follow, bound reads at 64 MiB, hash actual bytes; mismatched digest must fail.
- Default non-invasive and deterministic local-fixture-only tests.
- Admit neither physical lockscreen nor SDDM/Plymouth visual success from a content check.
- Avoid editing source Core or niri rotation code.

## Acceptance criteria

- [ ] Specified functionality and negative/boundary fixture tests.
- [ ] CI executes added tests; no existing gates disabled.
- [ ] Documentation gives exact explicit opt-in invocation and limitations.
- [ ] All exact HEAD required CI checks pass.

## Implementation slices

- [ ] Implement minimal standalone command reusing snapshot reader.
- [ ] Add deterministic mocks and required CI coverage.
- [ ] Update guide and evidence; submit separate PR.

## Verification matrix

| Gate | Evidence | Status |
|---|---|---|
| Offline Python | unit fixture output, bad hash, oversize, symlink, malformed | pending |
| CI contract & plan | workflow run | pending |
| Linux Wayland UI | no live test authorized | UNASSESSED |
| Windows/macOS and compositor E2E | existing required CI | pending |

## Decision gates

Existing user-level opt-in consumer event boundary applies. Actual SDDM/Plymouth privileged importer remains blocked pending a separately reviewed trust and target policy.

## Evidence log

- 2026-11-01: inspected master e579c6ff13ef39345c30a2b8497e4332903eca19; no system modifications planned.

## Deviations and discoveries

None.

## Resume from here

Inspect the PR exact-head CI; fix failures, merge only with all applicable gates completed successfully.

## Completion

Final commit: pending
CI run: pending
Privileged import: UNASSESSED
