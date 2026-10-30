# 2026-10-30-wpaperd-runtime-socket-114 — pinned native socket path correction

Issue: #114
Status: IMPLEMENTING
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

- [ ] Correct production socket path to the upstream 1.3.0 root socket; document exact source evidence.
- [ ] Add deterministic regression checking path construction and absent-socket rejection without touching ambient XDG environment or a real daemon.
- [ ] README path corrected; no other runtime behavior change.
- [ ] Final source PR exact-head 8/8 completed/success, workflow completed/success, mergeable=true, diff/security reviewed, expected-head squash merged.
- [ ] Separate docs-only completion archive PR has its own exact-head 8/8 success before #114 closes; parent #83 remains OPEN.

## Implementation slices

- [x] Inspect pinned upstream path chain, real native CI failure, merged source and README.
- [ ] Add production path correction, deterministic regression and README fix in this branch.
- [ ] Run exact-head eight-job source CI, review and merge only after gates.
- [ ] Archive through independent completion PR; close #114 only after archive merges.

## Verification matrix

| Scope | Gate | Status |
|---|---|---|
| Upstream path | Fixed wpaperd 1.3.0 source + xdg 3.0.0 source | CODE reviewed |
| Offline regression | Rust test for exact runtime root socket and absent endpoint | UNASSESSED |
| Full CI | Eight jobs on latest exact PR HEAD | UNASSESSED |
| Native pixels | #111 separate actual compositor evidence | UNASSESSED |

## Decision gates

User already approved A. Correcting a verified integration path is a routine bug fix, not a change in product policy.

## Evidence log

- 2026-10-30: upstream source, xdg 3.0.0 source and CI #41116832430 artifact #13007420138 inspected; wpaperd.log empty, Sway log shows two native layer surfaces, test failed waiting for nested socket. No user desktop touched.

## Deviations and discoveries

Merged mock-only CI #109 was green despite a wrong production socket path; this is why native E2E must not be represented as proven by fixtures.

## Resume from here

Update `src/backend/wpaperd.rs` to use the raw XDG_RUNTIME_DIR root socket, add a deterministic regression, fix README path, then open a linked PR and inspect its new exact-head eight-job CI.

## Completion

Final commit: pending
CI run: pending
E2E artifact: #111 separate
Remaining unassessed items: native wpaperd IPC/pixels, physical monitors, hotplug, GPU/4K, released niri.
