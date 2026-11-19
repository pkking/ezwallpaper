# 2026-11-18-326-rollback-integrity: close rollback evidence gaps

Issue: #326
Status: READY_FOR_REVIEW
Owner: agent
Started: 2026-11-18
Last checkpoint: 2026-11-19

## Objective
Record bounded isolated Stable → Beta → Alpha → Stable rollback-chain evidence without overstating a new-bucket rotation or event history semantics.

## Goal alignment
Epic: #60
Goal: G-01
Contribution type: BLOCKER
Gap: Candidate rollback commands succeeded, but intermediate integrity bookkeeping was incomplete.
Before: Rollback commands had passed; per-stage state/schema/ACK and fixture preservation were PARTIAL.
After: The exact isolated chain, per-stage hashes and limitations are recorded; no production behavior or new-bucket continuation is inferred.
Evidence plan: Private manifest-verified run; public-safe summary in [#326 final evidence](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7011310990).
Priority rationale: #326 is a #319 release qualification gate.
Remaining unassessed: A new natural bucket after rollback; live user-manager or production data behavior.

## Non-goals and constraints
No production profile, timer, alias, state, user data or desktop mutation. No release authorization. Keep raw artifacts private (directory 0700/files 0600); publish only safe summary, digest and canonical URL.

## Candidate and evidence
- Tested candidate source revision: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413`, source-equivalent to #329 tested runtime code; PR #329 head is `65c686a73407531cb91bff58e9a48516510a309e`.
- Stable binary SHA-256: `7681ff93540096f9c451f7eee5067df29d29fdb4c6813b56e2c4d3b84a55312e`.
- Beta executable provenance is `d6598ae0…` (post-beta fix commit); it is not the published beta tag. Published `v0.3.0-beta.1` tag resolves to `a3ae57c5a845a612f6bfe49ce10250c89092717e`; do not conflate these revisions.
- Alpha executable revision: `4e72605f…` (read-only).
- Canonical public result: [#326 comment 7011310990](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7011310990).

## Acceptance and observed result
- [x] Six isolated invocations: Stable write, Beta idempotent read, Beta `--force`, Alpha idempotent read, Stable idempotent read, and Stable post-rollback invocation; all exited 0.
- [x] State schema-v1 fields, output ACK/content references, fixture profile and pool assets verified; all content IDs resolve to matching asset SHA-256. Before/after state and event hashes were captured; input profile/assets remained unchanged.
- [x] Rollback operation did not require state reinitialization. The final Stable invocation reports `already_applied` for both outputs with no state advance.
- [x] Per-output event behavior traced to source: `src/rotation_event.rs::publish` stages JSON in the target directory, flushes/syncs it, then `NamedTempFile::persist(&target)` atomically replaces `<output>.json`; `src/rotation_cli.rs` invokes this after state persistence. Existing regression `rotation_event::tests::opt_in_publish_is_atomic_and_per_output` covers atomic per-output publication. `--force` changes the current ACK record at that path. These files are the latest acknowledged record, not append-only history.
- [ ] A new-bucket continuation was not tested. Same-bucket idempotency is not evidence of new-bucket rotation; do not mark that assertion PASS.
- [ ] Maintainer review of bounded evidence and documented latest-ACK semantics remains separate from this technical record.

## Verification matrix
| Assertion | Evidence | Status |
|---|---|---|
| Rollback chain command success | Six isolated commands, each exit 0 | PASS |
| State/schema/content integrity | Per-stage snapshots; profile/pool stable; content IDs hash-match assets | PASS |
| Existing ACK idempotency | Alpha/stable reads and post-rollback same-bucket invocation | PASS (same bucket only) |
| New-bucket continuation | No natural bucket awaited | NOT TESTED |
| Event history append-only | Source and `--force` prove atomic replacement of one latest record per output | NOT APPLICABLE / not promised |
| Production/user-manager rollback | Not exercised | UNASSESSED |

## Evidence and provenance
Private evidence directory: `~/.local/state/dotfiles-submission/final-326-rollback-suite-20261119T132607Z/` (private path for authorized audit; do not copy into public comments).
Manifest SHA-256: `a95ad8aa938b3d829d06446b57057ff13a80384565650038181c0d79f41fd13d`.
Canonical published summary: [#326](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7011310990).

## Deviations and discoveries
The previous plan's “continued rotation” criterion conflated same-bucket command/idempotency with advancement to a new UTC bucket. Corrected: only same-bucket idempotency is measured. Event files are per-output atomic latest-ACK records, not event history. No new runtime behavior or regression was necessary: source and existing regression already establish the contract.

## Resume from here
Maintainer reviews the public-safe result and accepts or requests a separately scoped follow-up for any new-bucket evidence; keep Stable release blocked pending all #319 gates.

## Completion
Final source candidate: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413` (PR #329 head source-equivalent)
Evidence manifest digest: `a95ad8aa938b3d829d06446b57057ff13a80384565650038181c0d79f41fd13d`
Remaining unassessed: new-bucket continuation; live user-manager/production behavior.
