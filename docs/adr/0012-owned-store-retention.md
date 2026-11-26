# ADR 0012: Owned-store admission and reference-aware retention

Status: Proposed
Date: 2026-11-26
Issue: #57
Extends: ADR 0003

## Context

The opt-in Core-owned CAS deduplicates content by SHA-256 and supports import, inspect, export, verified inventory and read-only GC preview. Preview protects only explicitly supplied pins; it does not establish safety for deletion. The legacy download directory is user-owned. Issue #57 and dotfiles#84 request a persistent pool budget of 500,000,000 bytes, independent of provider transfer budgets (#79).

## Decision (proposed)

- Reuse the existing version-marked CAS and its verified inventory. Require an explicit store root and opt-in retention policy. Never adopt or delete legacy download directories or user exports.
- Account quota as the sum of unique verified payload bytes, not filesystem allocation, index overhead, temporary bytes or network traffic. Default policy when enabled: reject new unique imports that would exceed the configured limit; existing content remains readable and rotation continues. Deduplicated imports consume no additional logical payload quota.
- Keep provenance (provider, acquisition time, source URL when available, and original/derived relationships) separate from immutable bytes. Multiple origins may point to one content ID. Never persist tokens or authorization headers. Define versioned metadata and migration before rollout.
- Protect explicit pins plus durable consumer leases/references for current, pending and configured recent rotation images and any store-backed exported or playing assets. A copy exported outside the store is not owned by GC. Missing or inconsistent reference metadata must fail closed, not imply an empty reference set.
- GC is a separate explicit operation. Preview lists candidate IDs, reclaimable logical bytes, reasons and protected references without changing files. Capacity and optional age retention are evaluated with deterministic ordering (oldest eligible first, content ID as tie-breaker). Default admission does not trigger deletion.
- Serialize quota admission, import commit, reference updates and deletion with a store-scoped lock shared by all cooperating processes. Recalculate eligibility under the lock immediately before deletion; never execute a stale preview blindly.
- Before enabling deletion, verify cacache's index and blob removal semantics against the pinned dependency, including deduplicated content and interrupted operations. Do not directly unlink internal paths or accept deletion paths from metadata. A failed operation must not silently corrupt inventory or release a live reference; journal/reconcile partial operations and fail closed on uncertainty.
- Implement in independent slices: non-mutating policy/metadata and preview; locked quota admission; durable reference integration; explicit deletion only after all preceding gates pass. No automatic expiry or daemon is required.

## Alternatives

- Reuse legacy --dir for retention: rejected because ownership and external references cannot be established.
- Evict on every import: rejected as default because acquisition must not implicitly destroy content.
- New database/CAS: defer; evaluate only if existing backend and versioned metadata cannot satisfy verified transaction/recovery requirements.

## Consequences

Existing default behavior stays unchanged. A full managed pool stops new unique imports until the user explicitly frees eligible content. Persistent logical capacity, in-flight transfer limits and physical disk usage remain separate metrics. Reference discovery is an explicit consumer responsibility, not an assumption that every external consumer can be detected.

## Acceptance

Offline fixtures must prove deduplication accounting, exact/over-limit admission, preservation of existing assets, deterministic preview, active-reference protection, stale preview rejection, concurrent mutation serialization and crash recovery. Actual deletion remains gated on backend-specific verification and independent review. Tests must never mutate a real desktop or user files.

Diagram impact: none - the existing architecture figure already depicts the isolated Core-owned CAS and future garbage collection; this proposed policy introduces no new component, dependency direction or implemented data flow. Update the figure when an approved implementation changes its depicted contracts.

## Evidence/References

- ADR 0003: independent opt-in content store
- Issue #57 and downstream dotfiles#84: persistent pool retention requirements
- Issue #79: separate provider streaming and batch limits
- `crates/ezwallpaper-core/src/store.rs`: verified inventory and read-only preview
