# 2026-11-18-326-rollback-integrity: qualify bounded actual-tag rollback chain

Issue: #326
Status: READY_FOR_REVIEW
Owner: agent
Started: 2026-11-18
Last checkpoint: 2026-11-20

## Objective
Record bounded isolated Stable → published-tag-source Beta → Alpha → Stable rollback evidence and distinguish same-bucket replay from natural new-bucket continuation.

## Goal alignment
Epic: #60
Goal: G-01
Contribution type: BLOCKER
Gap: Cross-version rollback evidence needed a provenance-correct, independently reviewed record of setter/getter operations and state/data integrity.
Before: Earlier chain evidence was ambiguous about Beta provenance and a later run lacked the expected mock IPC ledger/getter evidence; neither established independent backend readback for the actual published tag.
After: Canonical [#326 qualification comment](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7017556549) records a bounded isolated actual-tag-source chain PASS, its independently reviewed evidence, and its limits.
Evidence plan: Use the private manifest-verified report and independent review; do not rerun already-passed suites or infer pixels/natural new-bucket behavior.
Priority rationale: #326 is a named #319 lifecycle/data-integrity qualification input.
Remaining unassessed: Natural new-bucket continuation, live IPC/pixels, production/user-manager behavior, and historical isolation of the earlier failed run.

## Non-goals and constraints
No production profile, timer, alias, state, user data or desktop mutation. No release authorization. Keep raw artifacts private; publish only safe summary, digest and canonical URL.

## Qualified candidate and evidence
- Stable source baseline: `36aca9e0df5c3f21f22c42ae266006f2bbdb5413`, binary SHA-256 `7681ff93540096f9c451f7eee5067df29d29fdb4c6813b56e2c4d3b84a55312e`.
- Published Beta is GitHub tag [`v0.3.0-beta.1`](https://github.com/pkking/ezwallpaper/releases/tag/v0.3.0-beta.1), source SHA `a3ae57c5a845a612f6bfe49ce10250c89092717e`. Beta binary was built from this exact tag source with locally resolved offline dependencies because the tag has no Cargo.lock; this is **not** a recovered published executable. Binary SHA-256 `00dac8f177b8b2cae158acdedb33bf6ff11a5725fc931c7ef80a290ddc6944e7`. `d6598ae0…` is a post-beta fix, not the tag.
- Alpha source `4e72605fe788f1c1da1cb9aeba103353df547838`; binary SHA-256 `7cd1ac81d8b1ddc1716f6ebc775d0dc5f938f22bfad8c11f47719b86e03de95c`.
- Actual-provenance sequence: Stable force → Beta read → Beta force → Alpha read → Alpha force → Stable read → Stable force → Stable same-bucket read. **8/8** invocations exited 0; the independently captured mock ledger contains **24 actual run-marked rows**. Per-version force set/get: Stable 4/4, Beta 2/2, Alpha 2/2. ACK/state/schema/content, profile and image-inventory snapshots establish the bounded integrity assertions; missing-token and mismatched-getter negative cases each exited 1 without ACK/state commit. Same-bucket replay left state/ACK unchanged.
- Independent Luna review: PASS for bounded isolated rollback acceptance; 36/36 manifest entries verified. Evidence manifest digest: `45eca77d0cbc266d7caf8aa1c5d8efa2f346a6d20f865527617eae7761bb4471`; independent-review manifest digest: `44f5e9458718391c8bd549d16aedf9e741977b32b92510c6413529a39429a918`.
- Canonical public evidence: [#326 comment 7017556549](https://github.com/pkking/ezwallpaper/issues/326#issuecomment-7017556549). Earlier incomplete replay is excluded. Its subprocess provenance is insufficient to establish mock or real-desktop execution; historical isolation is **UNKNOWN**, and no claim is made that production was untouched by that earlier run.

## Acceptance and observed result
- [x] Actual published-tag-source chain, bounded isolated scope: PASS; 8/8 commands and 24 recorded mock IPC rows with independent per-version set/get evidence.
- [x] State/schema/content and fixture continuity: PASS within the captured isolated snapshots; no live-pixel claim.
- [x] Negative missing-token and getter-mismatch cases fail closed without state/ACK commit.
- [x] Published-tag Beta standalone replay is distinct from the chain; its source-built provenance is explicitly disclosed.
- [x] Same-bucket replay/idempotency PASS within this fixture.
- [ ] Natural new-bucket continuation: NOT TESTED (not implied by same-bucket replay).
- [ ] Live IPC, physical pixels, and production/user-manager rollback: UNASSESSED.

## Verification matrix
| Assertion | Evidence | Status |
|---|---|---|
| Stable → exact published-tag-source Beta → Alpha → Stable | 8/8 isolated invocations; 24 recorded mock IPC rows; per-version set/get and read/write snapshots | PASS within bounded fixture scope |
| State/schema/content integrity | State, ACK, image, pool/profile snapshots and hashes | PASS within captured scope |
| Missing token / mismatched getter | Each negative case exits 1 without state/ACK commit | PASS (negative assertions) |
| Same-bucket replay | Final same-bucket read leaves state and ACK unchanged | PASS; not a new bucket |
| Natural new-bucket continuation | No natural bucket awaited | NOT TESTED |
| Live desktop IPC/pixels; production/user-manager behavior | Not exercised | UNASSESSED |
| Earlier failed replay isolation | Process env/PATH/socket provenance unavailable | UNKNOWN; excluded, no production-untouched claim |

## Evidence and provenance
Private evidence: `/home/lcr/.local/state/dotfiles-submission/actual-beta-qualified-20261119T174000Z/REPORT.md`; independent review: `/home/lcr/.local/state/dotfiles-submission/luna-review-actual-beta-qualified-20261119T174000Z/REPORT.md`. Private raw artifacts remain access-restricted. Manifest digest: `45eca77d0cbc266d7caf8aa1c5d8efa2f346a6d20f865527617eae7761bb4471`.

## Deviations and discoveries
The earlier actual-tag-source replay without mock ledger/getter is excluded and its historical isolation remains UNKNOWN. The newly qualified chain uses the exact published tag's source but a local source build, not a recovered release binary. Same-bucket replay is not new-bucket progression. No live IPC/pixel or wholly-synthetic fixture-image provenance claim is made.

## Resume from here
Main may synchronize the canonical evidence summary and decide #332 closure after independent review. Keep #329 Draft / `RELEASE_BLOCKED`; this bounded #326 PASS is not STABLE_GO or merge/release authorization. Do not repeat the passed chain solely to create more evidence.

## Completion
Qualified chain: Stable `36aca9e0` → published Beta tag source `a3ae57c5` → Alpha `4e72605f` → Stable. Evidence manifest digest `45eca77d0cbc266d7caf8aa1c5d8efa2f346a6d20f865527617eae7761bb4471`; independent-review manifest digest `44f5e9458718391c8bd549d16aedf9e741977b32b92510c6413529a39429a918`. Natural new-bucket progression remains NOT TESTED; live/production behavior remains UNASSESSED.
