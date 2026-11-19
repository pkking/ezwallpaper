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
- Stable runtime source baseline: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413`, unchanged at #329 historical head `177630a5a86e09a6650938d55897c614cdac622c`; Stable binary SHA-256 `7681ff93540096f9c451f7eee5067df29d29fdb4c6813b56e2c4d3b84a55312e`.
- The published Beta is GitHub tag [`v0.3.0-beta.1`](https://github.com/pkking/ezwallpaper/releases/tag/v0.3.0-beta.1), exact source SHA `a3ae57c5a845a612f6bfe49ce10250c89092717e`. `d6598ae0d867890f42f0f0186efbae27a9ea6627` is the later #324 fix commit, not the published Beta tag. Earlier public [#326 comment 7011310990](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7011310990) mislabeled/overstated the provenance of the continuous rollback chain and is corrected here; it must not be silently repeated as a verified actual-tag chain.
- Published-tag Beta was source-built from that tag with offline-resolved dependencies because the tag has no committed Cargo.lock; no release binary was recovered. Binary SHA-256 `00dac8f177b8b2cae158acdedb33bf6ff11a5725fc931c7ef80a290ddc6944e7`. Its isolated standalone replay17 had 17 passing assertions; it is not a cross-version chain.
- Alpha source revision `4e72605fe788f1c1da1cb9aeba103353df547838`; binary SHA-256 `7cd1ac81d8b1ddc1716f6ebc775d0dc5f938f22bfad8c11f47719b86e03de95c`.
- Actual-provenance Stable → published-tag-source Beta → Alpha → Stable execution: eight `rotate next --apply` commands exit 0, but expected mock IPC ledger was not created and mock getter state remained empty. Therefore independent set/get readback was not evidenced. The chain is **INCOMPLETE / NOT PASS**; do not count output labels or exit 0 as independent ACK verification. Per-command state snapshots exist; new-bucket continuation is NOT TESTED.
- Prior canonical public summaries: [#326 comment 7011310990](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7011310990) and [#327 comment 7011311708](https://github.com/pkking/ezwallpaper/issues/327#issuecomment-7011311708). A new correction comment URL will be supplied only by Main after publication.

## Acceptance and observed result
- [ ] The actual-published-Beta-provenance chain is incomplete: eight invocations exit 0 but expected mock IPC ledger/getter evidence is absent; do not claim independent setter/readback verification or chain PASS.
- [x] Exact published-tag-source Beta standalone replay17 is separate evidence: 17 assertions passed for isolated apply/idempotent replay, but it does not establish a continuous Stable→Beta→Alpha→Stable chain.
- [x] State snapshots and binary provenance are recorded. The attempted chain retained state/profile/pool hashes; absence of the mock ledger means backend ACK verification is not evidenced.
- [x] Per-output event behavior traced to source: `src/rotation_event.rs::publish` stages JSON in the target directory, flushes/syncs it, then atomically replaces `<output>.json`; `src/rotation_cli.rs` invokes this after state persistence. Existing regression `rotation_event::tests::opt_in_publish_is_atomic_and_per_output` covers atomic per-output publication. These files are the latest acknowledged record, not append-only history.
- [ ] A new-bucket continuation was not tested. Same-bucket idempotency is not evidence of new-bucket rotation.
- [ ] Main's correction of prior public overclaim and publication of exact evidence/status remain to be done; no link is fabricated.

## Verification matrix
| Assertion | Evidence | Status |
|---|---|---|
| Actual published-Beta-provenance chain | Eight isolated invocations exit 0; mock IPC/getter ledger absent | INCOMPLETE / NOT PASS |
| Published-tag Beta standalone replay | Source-built tag binary; 17 independent assertions | PASS (standalone replay only; not chain) |
| State/schema/content integrity in actual-provenance chain | State/profile/pool snapshots retained, but missing backend ledger prevents independent ACK/readback proof | PARTIAL evidence; not chain PASS |
| Prior chain using d6598ae0 post-beta fix binary | Six prior invocations claimed successful in prior evidence; this was not the published Beta tag | Does not establish published-beta provenance |
| Existing ACK idempotency | Same-bucket replay only | PASS only within previously evidenced fixture scope; not new bucket |
| New-bucket continuation | No natural bucket awaited | NOT TESTED |
| Event history append-only | Source and `--force` prove atomic replacement of one latest record per output | NOT APPLICABLE / not promised |
| Production/user-manager rollback | Not exercised | UNASSESSED |

## Evidence and provenance
Private evidence: access-restricted local artifacts retained for authorized audit; location intentionally omitted from public documentation.
Manifest SHA-256: `a95ad8aa938b3d829d06446b57057ff13a80384565650038181c0d79f41fd13d`.
Canonical published summary: [#326](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7011310990).

## Deviations and discoveries
The previous plan's “continued rotation” criterion conflated same-bucket command/idempotency with advancement to a new UTC bucket. Corrected: only same-bucket idempotency is measured. Event files are per-output atomic latest-ACK records, not event history. No new runtime behavior or regression was necessary: source and existing regression already establish the contract.

## Resume from here
Main independently reviews this corrected provenance and records the missing mock-ledger/getter evidence as INCOMPLETE / NOT PASS in final public synchronization. Do not repeat old six-command suites or claim standalone replay is a chain. Keep #329 Draft / `RELEASE_BLOCKED`; exact-head CI and maintainer STABLE_GO/merge/release authorization remain separate gates.

## Completion
Historical Stable baseline: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413`; runtime source unchanged at #329 `177630a5a86e09a6650938d55897c614cdac622c`.
Prior #326/#327 evidence manifests: `a95ad8aa938b3d829d06446b57057ff13a80384565650038181c0d79f41fd13d`; `ca769e0087f17a258952eff77ddc0ac3874f09024d5ead131ca4fc6e207b2918`. Actual-beta audit manifest: `8fb27bf9c09397d34f15542f020430168983852ce7498273d92db5b2e890f714`.
Remaining unassessed: actual-tag full-chain independent backend readback (this attempt incomplete); new-bucket continuation; live user-manager/production behavior.
