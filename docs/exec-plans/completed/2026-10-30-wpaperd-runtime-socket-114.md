# 2026-10-30-wpaperd-runtime-socket-114 — pinned native socket path correction

Issue: #114
Status: COMPLETED
Owner: agent
Started: 2026-10-30
Last checkpoint: 2026-10-30

## Objective

Make the already-running wpaperd 1.3.0 opt-in rotation backend connect to the **actual** upstream native IPC endpoint `$XDG_RUNTIME_DIR/wpaperd.sock`, not the mistakenly assumed nested `$XDG_RUNTIME_DIR/wpaperd/wpaperd.sock`. Keep all other user-facing behavior unchanged.

## Non-goals

No automatic daemon installation, start, stop, fallback, new dependency, new default, physical display manipulation, renderer ownership policy or claimed framebuffer proof. Native dual-output CI remains separately owned by #111.

## Must-read context

AGENTS.md; docs/agents/workflow.md; docs/agents/testing.md; ADR 0010; Issue #114; source PR #109; #111/PR #113; `src/backend/wpaperd.rs`; README.md; `docs/architecture.md`; upstream pinned wpaperd 1.3.0 `ipc/src/lib.rs::socket_path`, `daemon/src/main.rs::run`, `daemon/src/ipc_server.rs::listen_on_ipc_socket`, and xdg crate 3.0.0 `base_directories.rs::get_runtime_directory`.

## Current facts

- Source PR #109 HEAD `52e52bdf735069acf3308e36124466272437f35c` passed 8/8 at CI #41084832566, merged as `1ee33c82b70cada7a83984ccd78c74db914243d9`; #108 archived via #112 and closed. Prior green fake-socket tests do not establish correct real native socket path.
- Pinned upstream wpaperd `9e71fdd10e1f2d94532edaf0f54402aac3c0b01c` uses `BaseDirectories::with_prefix("wpaperd").get_runtime_directory()?.join("wpaperd.sock")`. In xdg 3.0.0, `get_runtime_directory()` returns the raw runtime root, not `user_prefix`-qualified path; `get_runtime_file()` would apply the prefix, but upstream does not call it.
- Merged adapter `connect_current_session` uses `runtime.join("wpaperd").join("wpaperd.sock")` and README repeats the wrong nested path. This is a confirmed integration defect.
- PR #113 native CI #41116832430, exact HEAD `eadca5367864395ba82c4baafdb4b3fdd716be24`: seven jobs completed/success; native Sway E2E completed/failure while Noctalia job still running at checkpoint. Exact wpaperd 1.3.0 compiled and created two layer surfaces, but harness waited 25 seconds on wrong nested path; no native IPC or pixel pass was obtained.
- Parent #83 remains OPEN. This is a source fix on a fresh master branch; separate native E2E #111 will be refreshed after this fix merges.

## Constraints and invariants

Preserve explicit `--rotation-backend wpaperd --apply` and existing Noctalia default; never contact or mutate a real user session in tests. Runtime must require absolute XDG_RUNTIME_DIR and a Unix socket, reject missing endpoint, preserve timeouts and per-output validation. No extra Cargo dependency or production process management. Update README to match pinned source.

## Acceptance criteria

- [x] Correct production socket path to the upstream 1.3.0 root socket; document exact source evidence.
- [x] Add deterministic regression checking path construction and absent-socket rejection without touching ambient XDG environment or a real daemon.
- [x] README path corrected; no other runtime behavior change.
- [x] Source PR #115 HEAD `c0cf7816c56d98c6da9a7f3278b3eb9d44340668` exact CI #41118101838: eight jobs completed/success, workflow completed/success, mergeable=true, source/security diff reviewed, expected-head squash merged as `407f355b8c36424ace15dd1676adc3fb7c380fa9`; independently verified `master` runtime socket path.
- [x] Created independent docs-only archive PR #116 with mandatory exact-head eight-job CI gate; **archive CI is pending, not counted as passed**. Issue #114 stays OPEN until archive merge, master completed-plan and absent-active-path verification. Parent #83 remains OPEN.

## Implementation slices

- [x] Inspect pinned upstream path chain, real native CI failure, merged source and README.
- [x] Add production path correction, deterministic regression and README fix in this branch.
- [x] Source PR #115 exact-head eight-job CI, diff/security review, expected-head squash merge and master verification completed.
- [x] Prepared independent completion archive PR #116 and recorded the exact merge/CI prerequisites. **PR #116 CI and merge remain pending**; close #114 only after archive merge and master verification.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Upstream path | Fixed wpaperd 1.3.0 source + xdg 3.0.0 source | CODE reviewed |
| Offline regression | Rust tests and CLI smoke, CI #41118101838 | PASS (source HEAD) |
| Full CI | Eight jobs on source PR #115 exact HEAD | PASS, CI #41118101838 completed/success (8/8); source merged |
| Native pixels | #111 separate actual compositor evidence | UNASSESSED |

## Decision gates

User already approved A. Correcting a verified integration path is a routine bug fix, not a change in product policy.

## Evidence log

- 2026-10-30: upstream source, xdg 3.0.0 source and CI #41116832430 artifact #13007420138 inspected; wpaperd.log empty, Sway log shows two native layer surfaces, test failed waiting for nested socket. No user desktop touched.
- 2026-10-30: branch `agent/fix-wpaperd-runtime-socket-114` source commits `9ed9c567140c8f0a012fd71fefa1361858e57f62`, `efa09652a5e3c78235e035b220c6a0aa8aca7f19`: root socket helper and deterministic fake listener test, README corrected. Tests not yet run; no green claim.
- 2026-10-30: PR #115 first exact-head CI #41117947997: Rust quality failed `cargo fmt --all -- --check` on a single new test `conn.write_all` formatting block (raw job log inspected). Fixed exactly per rustfmt diff at `74bfdb1e916223f35fdc06bc7674f0471e063ddb`; all original checks retained. Full new exact-head CI required.


- 2026-10-30: final source PR #115 HEAD `c0cf7816c56d98c6da9a7f3278b3eb9d44340668` exact [CI #41118101838](https://github.com/pkking/ezwallpaper/actions/runs/41118101838) completed/success, all eight jobs completed/success (Rust quality, Rust tests/CLI smoke, Agent contract, Agent plan, Sway headless, Noctalia native, Windows, macOS). GitHub PR mergeable=true, reviewed only `src/backend/wpaperd.rs`, README, active plan; expected-head squash merge returned `407f355b8c36424ace15dd1676adc3fb7c380fa9`. Independently fetched `master` `src/backend/wpaperd.rs::connect_current_session`, confirmed root socket helper. No native pixel proof claimed.

## Deviations and discoveries

- 2026-10-30: archive PR #116 initial CI #41126482256 Agent plan integrity failed with `Archived plan has unchecked Acceptance criteria` (raw job log inspected). Corrected only the plan lifecycle checklist to record completed source/archive preparation without misrepresenting the archive PR's own still-pending CI or merge. No validation checks disabled or weakened; new full exact-head CI required.

Merged mock-only CI #109 was green despite a wrong production socket path; this is why native E2E must not be represented as proven by fixtures.

## Resume from here

Verify this docs-only archive PR latest exact HEAD eight completed/success jobs, workflow completed/success, mergeable=true and docs-only diff; squash merge with expected HEAD, independently fetch completed plan `Status: COMPLETED` and confirm active path 404, then close only Issue #114. Parent #83 stays OPEN. Continue #111 native E2E independently.

## Completion

Final commit: `407f355b8c36424ace15dd1676adc3fb7c380fa9` (PR #115 squash, tested HEAD `c0cf7816c56d98c6da9a7f3278b3eb9d44340668`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/41118101838 (completed/success; 8/8)
Archive: independent docs-only PR (own exact-head 8/8 CI required before merge)
E2E artifact: #111 separate
Remaining unassessed items: native wpaperd IPC/pixels, physical monitors, hotplug, GPU/4K, released niri.
