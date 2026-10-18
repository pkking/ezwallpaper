# ADR 0006: Optional bounded image decoding and safe static derivation

Status: Accepted (additive Core operation, no default behavior change)
Date: 2026-10-18
Issue: #53
Supersedes: None (extends ADRs 0001, 0003 and 0005)

## Context

Filename-extension catalog and provider metadata cannot prove image decodability or orientation. Multimonitor and downstream SDDM/Plymouth consumers need actual pixel dimensions, safe portrait/landscape cover/contain transformations and immutable original images. Decoding untrusted images is resource-sensitive; full codecs and unrestricted dynamic plugin or external GUI tools are unnecessary.

## Decision

- Reuse image-rs/image 0.25.10, a maintained pure-Rust imaging library, with default features disabled and only png/jpeg/webp/bmp support. The dependency remains strictly in headless Core, independent of wallpaper-rs and OS/DE state.
- Only explicit probe_image/derive_image (CLI probe/derive) decode image bytes. Existing list/fetch/hash, manifest v1 and opted-in owned-store remain unchanged. The new JSON outputs each have their own schema_version 1.
- Detect format from bytes, perform real decoder check and EXIF orientation extraction; apply orientation before target geometry calculations and encoding. Report both raw dimensions and display dimensions.
- Reject inputs larger than 64 MiB, raw dimensions over 16,384 each, pixel count over 32 million, outputs exceeding 8,192 per dimension or 16 million pixels, or unknown formats. Apply image::Limits width/height and max_alloc, explicitly noting max_alloc is best-effort rather than a hard memory sandbox.
- Cover preserves aspect ratio and crops; contain preserves aspect ratio and letterboxes onto a transparent PNG canvas or opaque JPEG representation; no stretch. Use a fixed Lanczos3 filter.
- Derive writes to a NamedTempFile staged in the destination directory and publishes via persist_noclobber; it does not overwrite source files or existing output/symlink paths. Failure discards the staged file.
- Neither operation launches desktop programs, reaches network, modifies system wallpaper settings, nor grants privileges. Do not auto-import outputs into CAS or delete user images.
- Extension mismatches do not determine format; use bytes and report the actual format. No recursive symlink traversal (deferred), no animated frame pipeline, no guarantees against hostile concurrent source or parent-path swaps.

## Alternatives

- Rely on service-provided width/height or file extensions: fails for corrupt/fake files and EXIF rotated portraits.
- Shell out to ImageMagick/ffmpeg for all images: introduces external binaries and potential portability/decode mismatch; a mature Rust codec is simpler for bounded static formats.
- Decode every catalog item implicitly: unexpected time/memory cost and incompatible with filename-only v1 contract.
- Always overwrite derived path: unsafe for external consumers and original file paths.

## Consequences

New decoder dependency increases build time and codec security maintenance exposure; pin feature subset and rely on upstream fixes. Image-rs uses strict dimension limits but does not promise complete memory containment. Explicit Core image metadata and conversion are now independently consumable; reusable deterministic cache keys/automatic lookup, richer focal-point crops and optional linked recursive catalog remain future Issue #53 slices. Physical niri visual proof remains Issue #59.

## References

- https://docs.rs/image/0.25.10/image/struct.ImageReader.html
- https://docs.rs/image/0.25.10/image/struct.Limits.html
- https://docs.rs/image/0.25.10/image/trait.ImageDecoder.html
- https://docs.rs/image/0.25.10/image/enum.DynamicImage.html
- https://docs.rs/tempfile/latest/tempfile/struct.NamedTempFile.html

## Architecture diagram impact

Changed: Headless Core now offers opt-in image decode/probe/derive in addition to the legacy catalog and provider layer. Update docs/architecture.svg and docs/architecture.md in this same PR; desktop consumers unchanged.
