# 2026-10-23-wallpaper-backend-gnome-global-83: GNOME global setter adapter extraction

Issue: #83
Status: COMPLETED
Owner: agent
Started: 2026-10-23
Last checkpoint: 2026-10-23

## Objective

Extract the existing GNOME GSettings wallpaper setter from the legacy setter facade into a dedicated CLI-owned `src/backend/gnome.rs` module. Implement the already-accepted `WallpaperBackend` adapter contract as **GlobalOnly** with **CommandAccepted** acknowledgement and a single global target; preserve exact existing one-shot CLI/default selection, URI encoding, light/dark handling and error semantics. Use deterministic injected fake subprocess contracts for offline tests. Keep the Noctalia-only acknowledged Rotation Controller unchanged: a global GSettings command exit is not exact wallpaper-path readback or pixel proof.

## Non-goals

No new GNOME rotation support, no physical GNOME session, no privilege/persistent timer, no display enumeration, no user configuration change in CI, no BackendRegistry rotation selection change, no Core changes, no Plasma/Sway/Hyprpaper/Portal implementation, no new dependencies or state contract.

## Must-read context

AGENTS.md; Issue #83 latest checkpoint; docs/adr/0010-wallpaper-backend-adapter-contract.md; docs/agents/workflow.md; docs/agents/testing.md; docs/architecture.{md,svg}; src/setter.rs; src/backend/{mod,registry,noctalia}.rs; src/rotation_cli.rs; README.md; tests/test_desktop_adapter_contract.py. B1 PR #86 exact-head CI #39823542531 8/8 SUCCESS and merge SHA `b8bb928adf1595ae0d3e1b653540ed6c06c07a91`. B1 archive PR #87 independently passed 8/8 CI #39879466386 and was squash merged into master at `1a54f865d5971bfec1f340f7cf1af7fa72434c24`.

## Current facts

- Base master: `b8bb928adf1595ae0d3e1b653540ed6c06c07a91`, exact B1 tested HEAD `99405ff04c1bd5e3b9655dfaaec7c28713176d10` run #39823542531 8/8 SUCCESS.
- GNOME currently uses `Adapter::GnomeGsettings` in `src/setter.rs`, reads `file_uri`, sets `org.gnome.desktop.background picture-uri`, probes `gsettings writable picture-uri-dark` and sets dark only if writable; reports `Submitted`, never `PathObserved`.
- B1 `WallpaperBackend` currently accepts a named output string; GNOME **GlobalOnly** is deliberately ineligible for per-output rotation and must not be registered as Noctalia replacement. Keep production target selection and default CLI unchanged.
- Issue #79 download limit is independently worked on outside this branch, not in scope.

## Constraints and invariants

- Preserve subprocess argv (no shell), JSON/GVariant encoded file URI and default light + conditional dark behavior. A failed picture-uri set must not continue to dark. If dark-probe exits nonzero, do not attempt dark; if it fails to launch, report the existing error. Never log a secret or mutate a real desktop in CI.
- GNOME backend applies to explicit global target only; reject named outputs, report GlobalOnly/CommandAccepted. No rotation state commit can result from Submitted.
- Legacy `apply` should call the concrete GNOME module and keep `Submitted` result. Existing Noctalia and other setter paths untouched; avoid import cycle between backend module and setter.
- Tests must simulate gsettings success/failure, dark key writable/unwritable, unsafe output scope, URI escaping and no real desktop operations. Current README/diagram should mark the GNOME module **implemented only for global one-shot setting**, not for automatic rotation; remaining platforms stay PLANNED. The ADR 0010 architecture decision is unchanged; synchronize docs/architecture.svg if depicting this newly implemented backend.
- Never imply native GNOME screen pixels were verified by fake commands or headless GitHub Actions.

## Acceptance criteria

- [x] `backend/gnome.rs` implements GlobalOnly / CommandAccepted with explicit global target, no independent output enumeration or false path readback.
- [x] Existing `setter.rs` GNOME one-shot delegates to the concrete module without altering auto/default selection, gsettings sequence or outward Submitted result.
- [x] Offline injected-command tests validate URI, light, optional dark, write failure, missing process, named-target refusal and no actual host execution.
- [x] Update README, architecture.md, SVG with truthful GNOME one-shot module status; Core, registry, rotation state and 60-minute default remain unchanged.
- [x] Latest exact PR HEAD 8/8 CI checks SUCCESS, including Windows/macOS and virtual Noctalia E2E; no live GNOME claims.
- [x] Record actual SHA, CI and scope; after successful implementation merge, archive in independent completion PR and keep Issue #83 OPEN.

## Implementation slices

- [x] GNOME module plus unit/fake runner tests and setter facade delegation authored; latest-head CI not yet run.
- [x] Architecture/README diagram synchronized and static regression check authored; validation pending CI.
- [x] Exact-head CI #39919213934 8/8 SUCCESS on `2ff1ca5f764a00c43e11bd7ae5fee948cbb26f7d`; GitHub API squash merge `ebfc4b3b488c852ef0570dc8580354e5a6013b8d`; independent archive PR follows.

## Verification matrix

| Scope | Gate | Verified result |
|---|---|---|
| Rust quality | cargo fmt + strict Clippy | **SUCCESS**, exact HEAD CI #39919213934, Rust quality job #120300100107 |
| GNOME offline behavior | Rust unit + CLI smoke + adapter boundary tests | **SUCCESS**, Rust tests and CLI smoke job #120300100135; fake subprocess only |
| Noctalia existing behavior | native Noctalia v5.2.1 + Sway dual-render E2E | **SUCCESS**, job #120300100162, artifact #12488025456; Sway visual artifact #12485494708 |
| Cross-platform/governance | Windows, macOS, Agent plan integrity, contract self-tests | **SUCCESS**, all eight exact-head jobs and check runs |
| Experimental niri | pinned unmerged virtual-output PR test | **SUCCESS** in CI; artifact #12487517064, does not establish released niri |
| Real GNOME output | actual GNOME physical session | **UNASSESSED** (not exercised by CI) |

## Decision gates

None: additive internal extraction fits already-accepted ADR 0010. Any new GNOME rotation or change of public CLI/OS support policy needs its own separately reviewed design.

## Evidence log

- 2026-10-23: B1 implementation #86 merged and validated. This B2 plan created before code changes.
- 2026-10-23: authored `src/backend/gnome.rs` GlobalOnly / CommandAccepted backend and injected GSettings fake-runner tests, registered module, rewired existing one-shot GNOME setter through the private trait (no direct controller change); static guard, README/architecture.md/architecture.svg reflect GNOME global one-shot implementation only. GitHub implementation commit range starts `85fd4e3ff30923ad4cc85832d042a3cdbd94c256`; **no Cargo/rustfmt or CI executed locally**, no physical GNOME evidence or live setter invocation.
- 2026-10-23: after applying four rustfmt hunks from initial CI, checked cross-platform GNOME URI test assumptions. Replaced test-only Unix `/tmp/...` URI fixture paths with `std::env::temp_dir().join(name)` in commit `7a51ed11628c5ac3e744a54d05f8850cc4c04fb1`; named-output refusal still avoids invoking a host command. This prevents Windows URL-path parsing false failures without modifying production GNOME logic. New exact-head 8/8 CI still required; first CI failure is retained below.
- 2026-10-23: [PR #88](https://github.com/pkking/ezwallpaper/pull/88) initial HEAD `25c02f127d1f0e2bb57cd41dca3ce55b754aac52` [CI #39880133431](https://github.com/pkking/ezwallpaper/actions/runs/39880133431) showed **Rust quality FORMAT FAILURE** (Rust job #120175251934) in four `src/backend/gnome.rs` formatting hunks. Read actual job log and applied all four precise rustfmt recommendations in commit `8062cacdf8c5cc9c27d6247e77261c2d21c236d0`, preserving tests and runtime semantics. Initial run is **not** passing evidence; exact latest-head rerun is mandatory. All other initial jobs observed completed except Windows and native Noctalia still in progress at first check. Real GNOME remains UNASSESSED.

## Deviations and discoveries

URI fixtures must represent valid native absolute paths on all tested hosts, not assume Unix paths on Windows; updated fake-only test fixture accordingly. No GNOME host interactions.

The CI runner's rustfmt 4-line/diff diagnostics were required to normalize injected GSettings fixture assertions and URI error formatting. This is formatting-only; do not weaken Rust quality or assume a passing test from the failed initial run.

## Resume from here

B2 implementation is complete and merged. This file is archived by an independent completion PR. Continue Issue #83 only through separate plans/PRs for Plasma, Sway, Hyprpaper or Portal; do not interpret GNOME GSettings command submission as acknowledged path/pixels or per-output rotation. No live desktop, timer or dotfiles were modified.

## Completion

Final commit: `ebfc4b3b488c852ef0570dc8580354e5a6013b8d` (PR #88 squash merge; exact tested HEAD `2ff1ca5f764a00c43e11bd7ae5fee948cbb26f7d`)
CI run: https://github.com/pkking/ezwallpaper/actions/runs/39919213934 — 8/8 jobs SUCCESS, 8/8 check runs SUCCESS, required 4/4 SUCCESS
E2E evidence: native Noctalia+Sway artifact #12488025456 (`noctalia-result.json` PASS; 4 stages pixel_fraction=1.0 >= 0.9; ephemeral cleanup complete), experimental niri #12487517064, Sway visual #12485494708, Rust CLI offline #12486897309; these do not prove live GNOME
Remaining unassessed items: real GNOME desktop, all GNOME multi-output/rotation, Plasma/Sway/Hyprpaper/Portal dedicated backends, physical 4K/GPU/hotplug/PAM, persistent system timer. Issue #83 remains OPEN.

## Final implementation checkpoint — 2026-10-23

- [PR #88](https://github.com/pkking/ezwallpaper/pull/88) final tested HEAD `2ff1ca5f764a00c43e11bd7ae5fee948cbb26f7d`; [CI #39919213934](https://github.com/pkking/ezwallpaper/actions/runs/39919213934) **8/8 jobs and 8/8 check runs SUCCESS**, required checks **4/4 SUCCESS**, no reviews required; mergeable true.
- Earlier run #39880133431 failed rustfmt and Windows URI fixture; run #39880411979 failed strict Clippy `collapsible_if`. These failures were repaired in the same implementation branch without relaxing gates. The final exact-head run, not earlier runs, is completion evidence.
- GitHub `merge_pull_request(merge_method=squash,expected_head_sha=2ff1ca5f764a00c43e11bd7ae5fee948cbb26f7d)` succeeded, master squash commit `ebfc4b3b488c852ef0570dc8580354e5a6013b8d` independently verified.
- Scope: CLI-only `GnomeBackend` **GlobalOnly/CommandAccepted**, global one-shot GNOME light/dark GSettings `Submitted`; rotation registry still Noctalia-only with exact path readback. Unit tests inject commands and never touch the real desktop. No live GNOME, physical display, 4K/GPU/hotplug, multi-output or timer verification is claimed.
