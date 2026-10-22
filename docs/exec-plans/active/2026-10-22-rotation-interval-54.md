# 2026-10-22-rotation-interval-54: explicit UTC minute-bucket rotation and safe retries

Issue: #54
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-22
Last checkpoint: 2026-10-22

## Objective

Extend the already-merged opt-in Noctalia v5 rotation CLI with **explicit --interval-minutes N** supporting bounded positive integer-minute UTC buckets (e.g. 30 minutes or 7 minutes) while preserving default hourly (60-minute) behavior and existing persisted hourly state JSON v1. Ensure same-bucket failures/retries don't advance acknowledged choices, each output commits independently after Noctalia IPC exact-path readback, and period changes cannot silently alias previously acknowledged hourly bucket numbers. User integration need: [dotfiles#84](https://github.com/pkking/dotfiles/issues/84), which requests a 30-minute **downstream deployment default** and any positive interval; upstream legacy CLI remains 60 for compatibility.

## Non-goals

No installed/enabled timers, no modifying dotfiles, Noctalia GUI state or real user Wayland session, no implicit download/refill, real GPU or hotplug claims. Do not change Core plan_rotation logic/shuffle, persistent state schema_version 1, CLI existing default behavior, lockfile name/retention, on-disk file naming or manifest v1. Do not use --force for retry (manual override only).

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; docs/exec-plans/TEMPLATE.md; Issue #54 latest checkpoint; [dotfiles#84](https://github.com/pkking/dotfiles/issues/84); docs/adr/0008-pure-rotation-planner.md, docs/adr/0009-locked-noctalia-rotation.md; src/rotation_cli.rs, src/main.rs; crates/ezwallpaper-core/src/rotation.rs; README.md; docs/examples/rotation-profile.json, docs/examples/ezwallpaper-rotation.service, docs/examples/ezwallpaper-rotation.timer; .github/workflows/ci.yml.

## Current facts

- Base/master: `950370647a74a24917b5cc1342eee8917ef3ddc9`, no OPEN PR on 2026-10-22 preflight. Existing Issue #54 Core planner #65 and CLI #66 merged, archive #67 merged, but period semantics not yet supported.
- Current CLI `rotate next` uses `current_utc_epoch()` with `seconds / 3600`. `--epoch` overrides integer UTC hour **for preview only**, and `--force` bypasses acknowledged epoch protection intentionally. Explicit `--apply` uses OS lock and atomic per-output state write only after Noctalia wallpaper-get exact path acknowledgement. Existing state JSON v1 includes `profile` canonical identity string and per-output `last_epoch`.
- dotfiles#84 requests its **own** default 30 minutes, arbitrary positive minutes and no additional image change on failed retries. No authorization to deploy this upstream change to that physical desktop.
- No new Core API or scheduled process required; current hours are UTC buckets, so the minimum change is to parameterize the CLI time source and persist period-separated profile identity without migrating state.

## Constraints and invariants

- Backward compatibility: `--interval-minutes` omitted => exactly old 60-minute epoch mapping and persisted profile canonical identity. `--epoch` remains preview-only but now means **bucket index at chosen interval**, old hourly index unchanged for default.
- `--interval-minutes N` requires N >= 1, calculated as floor(Unix UTC seconds / (60*N)) using checked multiplication and checked i64 conversion. No local timezone, DST adjustment, missed-tick replay or hidden scheduler; invalid 0/overflow must fail before any wallpaper effects.
- For N != 60, the persisted `profile` identity (same existing JSON schema v1 string field, **no new key/version**) is qualified with a stable non-default interval suffix. A non-hourly run with a state file used by hourly runs or by a different interval must **fail closed**; user selects a separate --state PATH or makes an explicit independent migration. No automatic deletion/migration/overwrite.
- Lock & atomic state publication behavior is unchanged; a failed IPC result never acknowledges a choice. With the same immutable candidate set and unchanged state, same-bucket retry selects the same candidate. Successful first-output state remains committed if second output fails; rerun only retries the second output. A changed pool between failures can change the pending proposal; do not promise durable reservation of unacknowledged content across pool mutations in this slice.
- Manual --force is a deliberate override, not the retry mechanism. No new user device operations in tests. Never call IPC or create state/lock paths in dry-run.
- No new architectural subsystem, Core/CLI division, stored schema or external integration. Clarify the existing ADR 0009 time policy and record its explicit Diagram impact: none rationale; the already-canonical architecture SVG remains unchanged because CLI/Core/state/desktop edges do not change. Document the profile identity isolation and limitations in README.

## Acceptance criteria

- [x] Additive CLI --interval-minutes opt-in, 60 minute default, explicit preview bucket index; zero and overflow rejected fail-closed (authored, pending CI).
- [x] Deterministic UTC fake-clock tests for 1, 7, 30, 60, 90-minute periods, adjacent boundaries, UTC day and DST-independent intervals, rollback/missed ticks (authored, pending CI).
- [x] Offline fake Noctalia acknowledgement tests: same 30-minute bucket restart/retry no extra switch, failure does not commit, two-output partial failure resumes only unacknowledged output, existing concurrent apply fixture still applies (authored, pending CI).
- [x] Existing hourly persisted state v1 exactly compatible; mixing a non-default interval with old state (or another non-default period) fails without changing accepted state. Empty/single pool degraded reporting unchanged (authored, pending CI).
- [x] Update README with explicit --interval-minutes 30 preview/apply examples and distinct state recommendation for nondefault interval, --force disclaimer, strict IPC vs real pixels evidence, no implicit timers; amend ADR 0009 without changing architecture.svg (authored, pending CI).
- [ ] Final PR HEAD all 8 CI jobs and required checks SUCCESS, record truthful HEAD/run and protect Issue #54 OPEN. Archive implementation plan in a separate future PR after actual verification.

## Implementation slices

- [x] 1. Exact UTC bucket helper, opt-in CLI flag and period-separated state identity without schema migration (code committed; CI pending).
- [x] 2. Fake-clock, retry, crash/partial/concurrency/legacy-state regression tests; offline CLI argument contracts, README and existing ADR 0009 clarification (code committed; CI pending).
- [ ] 3. Inspect exact-HEAD GitHub CI and artifacts, repair on same branch; squash merge through GitHub API only when all checks pass and evidence is valid; separate archival PR and Issue checkpoint.

## Verification matrix

| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Rust Core/CLI and fake clocks | cargo test --workspace --all-targets | current exact HEAD run | PENDING |
| Rust static | cargo fmt --all -- --check; cargo clippy --workspace --all-targets --all-features -- -D warnings -W clippy::unwrap_used | #39810022411 FAIL fmt, fixed at `0bfb02f`; latest HEAD pending | PENDING |
| Offline CLI contract | --help plus wrong intervals and preview | exact HEAD | PENDING |
| Governance and platforms | 8/8 GitHub checks, including Windows/macOS, plan | exact HEAD | PENDING |
| Real physical desktop | Noctalia/Niri session, timers, user dotfiles | not touched | UNASSESSED |

## Decision gates

No new human decision: feature is additive opt-in, hourly default unchanged, no on-disk format or filename change. Explicit state-file mismatch on non-default interval avoids silent migration; any request to default upstream to 30 minutes, automatically migrate existing hourly state or activate host timers would require a separate product/authorization decision.

## Evidence log

- 2026-10-22: [PR #82](https://github.com/pkking/ezwallpaper/pull/82) initial HEAD `d65cb6c2301c9a1f009400765829c619bb8b5a3e` triggered [CI #39810022411](https://github.com/pkking/ezwallpaper/actions/runs/39810022411). Rust quality failed on `cargo fmt --check` only; actual rustfmt diff was read from failed job #119933462323 and applied exactly across src/main.rs (5 hunks) and src/rotation_cli.rs (20 hunks) in commits `80d26d1faaebb7e02c2ef2d6b48711b7ba505427`, `0bfb02f71c770d130c15efc310db4c9d9676db8f`. Original head Rust tests/CLI smoke, Sway visual, macOS, integrity and contract checks had already succeeded when observed, but Windows/native E2E were still running; **overall old head FAIL** and must not be presented as pass. New exact-head [CI #39810281204](https://github.com/pkking/ezwallpaper/actions/runs/39810281204) started, at last check PENDING. Do not merge pending revision.
- 2026-10-22: implementation commits `d66070199596749d815aecefbd9533e9563c711c` UTC bucket and state isolation, `54045f65778bc0cc491521bc796ed689bb7ec975` opt-in CLI flag, `1b49a66f6cdfc644c5a6fb52ba5c69c9e5155ffe` fake-clock/partial retry/legacy tests, `4010a69d95201d29901c10c80d71d6a8e45ba9c9` CLI parsing tests, `5294f35952b9ed998595ca7ef89a1f39947fc493` README and `40f40f5059cdf5be7f2e523066c602ca88f49820` ADR 0009 note. **Not yet validated by CI**.
- 2026-10-22: verified master `950370647a74a24917b5cc1342eee8917ef3ddc9`, Issue #54 and dotfiles#84, existing rotation Core and CLI state. Created branch `agent/rotation-configurable-interval-54` from master. No CI claims for new code.

## Deviations and discoveries

The existing documented '--force' option deliberately bypasses same-epoch idempotency; it is **not** safe to use for service failure retries. Buckets are monotonically numbered for each interval, and the existing persisted `last_epoch` is otherwise ambiguous across interval changes; qualify the already-present profile identity, not last_epoch or state schema.

## Resume from here

Review latest PR #82 HEAD and its fresh exact-head CI; initial #39810022411 failed only rustfmt (format diff fixed on branch). Independently check all eight jobs and raw test results, correct same-branch if failure, then squash merge via GitHub API(expected_head_sha=latest SHA) on verified PASS. Separate completion archive PR and Issue #54 checkpoint. No real desktop writes.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline fixture only; real Noctalia desktop unassessed
Remaining unassessed items: source pool mutation between failed attempts, real display output lifecycle, automatic refill, hardware sessions/timers, lockscreen, 4K/GPU, live deployment.
