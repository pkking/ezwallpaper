# 2026-10-18-image-probe-derive-53: strict local image inspection and optional derivation

Issue: #53
Status: VERIFYING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-19

## Objective

Provide optional, independent headless image decoding/probe with resource bounds, EXIF orientation, actual pixel dimensions and repeatable landscape/portrait cover/contain derivation; preserve original file/manifest v1 and existing legacy CLI.

## Non-goals

No implicit decode during legacy list/fetch; no unbounded or default symlink recursion, no image-store automatic import/GC, no OS wallpaper setter writes, no live network, no claimed niri visual proof, no animations.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/adr/0001-core-cli-boundaries.md, docs/adr/0005-provider-source-capabilities.md, docs/architecture.md, crates/ezwallpaper-core/src/lib.rs, src/main.rs, Cargo manifests.

## Current facts

- Latest master 3c51eac46981627c2c3b0842d9ed8956f01773c1 (PR #63 merged); master CI https://github.com/pkking/ezwallpaper/actions/runs/39147086219 completed success. #53 remains open for recursive-root catalog and optional caching.
- Follow-up scope (2026-10-19): opt-in recursive catalog with optional symlink following, canonical allowed-root confinement, directory cycle detection, deduplicated link targets and deterministic ordering. Legacy `list` without new flags and manifest v1 stay unchanged.
- Base master f2b9dbc91083c8c1c3117fe89afe919f521de0f0 (PR #62 merged, final PR CI https://github.com/pkking/ezwallpaper/actions/runs/39146039524 green).
- Core currently validates regular files, not image bytes. Manifest v1 is a stable separate output.
- Proposed reuse: image-rs/image 0.25.x via pure-Rust png/jpeg/webp/bmp feature subset; ImageReader with_guessed_format, image::Limits, ImageDecoder::orientation, DynamicImage::apply_orientation. Official docs https://docs.rs/image/latest/image/struct.ImageReader.html and https://docs.rs/image/latest/image/struct.Limits.html.
- Default CI tests are offline, not real compositor integration.

## Constraints and invariants

- Explicit probe/derive only; never decode implicit legacy list.
- No image input > 64 MiB, decoded pixel count > 32 million, dimension > 16,384 or unbounded output. Treat image::Limits.max_alloc as best effort and cap dimensions/pixels explicitly.
- No modifying source file; staging in destination parent, no-clobber output, fail closed on corruption/mismatched formats. No unsafe temp root fallbacks or GUI side effects.
- Capture EXIF orientation and apply before using dimensions/crop to avoid portrait distortion.
- Only PNG/JPEG/WebP/BMP inputs. PNG/JPEG outputs. Explicit fit cover/contain without stretching. No program execution in headless core.
- Adding mature image crate should be documented in ADR and scope-limited (no toolchain overhaul). Update architecture.svg in same PR.

## Acceptance criteria

- [ ] New `list --recursive [--follow-symlinks]` and Core API enumerate nested local images, return only canonical paths inside requested root, reject outside/broken links in follow mode, prevent loops and duplicate targets; default behavior unchanged.
- [ ] Offline cross-platform recursion tests plus conditional Unix symlink escape, duplicate and cycle fixtures; CLI command contract documented and exercised.
- [ ] probe gives decoded dimensions, recognized format, orientation, source content ID, bounded resource errors; corrupt/fake extension rejected.
- [ ] derive cover/contain to requested pixel geometry with EXIF normalization, preserves originals and no-clobber output.
- [ ] offline deterministic fixtures for landscape, portrait, PNG transparency, corrupted files, huge header/memory, duplicate/overwrite and pixel layout.
- [ ] Core API, CLI commands, versioned new JSON contracts and docs/ADR/diagram.
- [ ] final PR-head CI green.

## Implementation slices

- [x] 4. Add bounded rooted recursive walk and opt-in CLI flags with offline tests; update README/architecture and checkpoint CI (execution unverified until PR CI).
- [x] 1. Add image-rs subset and bounded Core decode/probe.
- [x] 2. Derive API (cover/contain, PNG/JPEG) and fixture tests.
- [x] 3. CLI probe/derive, docs/ADR/diagram, CI verification pending.

## Verification matrix

| Scope | Command / gate | Evidence | Status |
|---|---|---|---|
| rustfmt/Clippy | cargo fmt/clippy | CI logs | pending |
| Core and CLI | cargo test --workspace --all-targets | CI logs | pending |
| Offline CLI | real binary nonmutating contracts | CI logs | pending |
| Platform matrix | Windows/macOS | CI logs | pending |
| Real desktop | niri/Noctalia dual monitor | separate Issue #59, unassessed |

## Decision gates

Pure Rust image codec dependency is intentionally scoped to four common image formats and isolated to headless Core; no new privilege, storage migration, or toolchain policy. If CI uncovers portability tradeoffs that require a materially different dependency/format strategy, seek human decision only then.

## Evidence log

- 2026-10-19: branch 0b24254ee708bddd8c4eaae45cd5096145d667c0 includes opt-in recursive Core/CLI code, 2 deterministic Core tests, CLI flag test, ADR 0007, architecture SVG and README. Local Rust/Cargo unavailable; PR CI must validate the branch before any merge.
- 2026-10-19: verified #63 on master and its successful CI run 39147086219; inspected list_local, CLI list, AGENTS.md, #53 and ADR 0006. New slice branch agent/issue-53-rooted-recursive-catalog; no local Cargo toolchain (UNASSESSED until CI).
- 2026-10-18: inspected issue and upstream ImageReader/Limits/EXIF docs; base #62 CI seven checks success. Local cargo unavailable; CI is primary verification.
- 2026-10-18: added image-rs feature-scoped dependency, image_assets.rs, Core exports, CLI probe/derive, offline binary fixtures, ADR 0006 and diagram/README changes. New code not yet CI-tested.

## Deviations and discoveries

Image-rs docs say max_alloc is best-effort, but width and height caps are strict. Enforce independent pixel/byte constraints before decoding. Explicit derive doesn't yet implement persistent cache/recursive catalog, so #53 remains open after this bounded slice.

## Resume from here

Open a PR from agent/issue-53-rooted-recursive-catalog to master with Issue #53 and this Plan metadata; inspect all final-head CI jobs, fix any failures and merge only after they are green. Local Rust toolchain unavailable.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline image fixtures expected
Remaining unassessed items: deterministic derivative cache/history, real displays, image bomb pathological codec behavior; new recursion CI pending.
