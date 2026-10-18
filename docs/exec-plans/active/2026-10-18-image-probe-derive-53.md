# 2026-10-18-image-probe-derive-53: strict local image inspection and optional derivation

Issue: #53
Status: IMPLEMENTING
Owner: agent
Started: 2026-10-18
Last checkpoint: 2026-10-18

## Objective

Provide optional, independent headless image decoding/probe with resource bounds, EXIF orientation, actual pixel dimensions and repeatable landscape/portrait cover/contain derivation; preserve original file/manifest v1 and existing legacy CLI.

## Non-goals

No implicit decode during legacy list/fetch; no symlink-follow recursive catalog (deferred), no image-store automatic import/GC, no OS wallpaper setter writes, no live network, no claimed niri visual proof, no animations.

## Must-read context

AGENTS.md, docs/agents/workflow.md, docs/agents/testing.md, docs/adr/0001-core-cli-boundaries.md, docs/adr/0005-provider-source-capabilities.md, docs/architecture.md, crates/ezwallpaper-core/src/lib.rs, src/main.rs, Cargo manifests.

## Current facts

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

- [ ] probe gives decoded dimensions, recognized format, orientation, source content ID, bounded resource errors; corrupt/fake extension rejected.
- [ ] derive cover/contain to requested pixel geometry with EXIF normalization, preserves originals and no-clobber output.
- [ ] offline deterministic fixtures for landscape, portrait, PNG transparency, corrupted files, huge header/memory, duplicate/overwrite and pixel layout.
- [ ] Core API, CLI commands, versioned new JSON contracts and docs/ADR/diagram.
- [ ] final PR-head CI green.

## Implementation slices

- [ ] 1. Add image-rs subset and bounded Core decode/probe.
- [ ] 2. Derive API (cover/contain, PNG/JPEG) and fixture tests.
- [ ] 3. CLI probe/derive, docs/ADR/diagram, CI verification.

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

- 2026-10-18: inspected issue and upstream ImageReader/Limits/EXIF docs; base #62 CI seven checks success. Local cargo unavailable; CI is primary verification.

## Deviations and discoveries

Image-rs docs say max_alloc is best-effort, but width and height caps are strict. Enforce independent pixel/byte constraints before decoding. Explicit derive doesn't yet implement persistent cache/recursive catalog, so #53 remains open after this bounded slice.

## Resume from here

Implement and test image probe/derive on agent/issue-53-image-probe-derive; submit PR and fix CI failures before merge.

## Completion

Final commit: pending
CI run: pending
E2E artifact: offline image fixtures expected
Remaining unassessed items: deterministic derivative cache/history and recursive symlink catalog, real displays, image bomb pathological codec behavior.
