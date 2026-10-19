# ADR 0008: Pure deterministic content-ID rotation planner

Status: Accepted (additive, non-mutating headless Core API)
Date: 2026-10-19
Issue: #54
Extends: ADR 0001, ADR 0004 and ADR 0007

## Context

Hourly wallpaper rotation must select **different content bytes**, not merely refetch a daily provider URL or launch the same path again. Coordinating two or more output pools requires a stable identity, a durable state proposal, and a clear boundary between planning and observed desktop application. niri/Noctalia already owns rendering and can have its own rotation schedule; ezwallpaper must not silently introduce a second authority.

## Decision

- Add a headless, pure planning function plan_rotation(output, utc_epoch, content_ids, previous_state, force). It reads no files, calls no providers or clocks and never modifies desktop state. It produces a status plus an optional candidate and proposed next state.
- Identify candidates by exact lowercase sha256:<64 hex> content IDs; remove duplicate IDs. Cap each pool and saved bag at 4,096 entries; reject invalid state version and malformed fields.
- Deterministic per-output shuffle-bag rank is SHA-256 of a versioned domain prefix, output name, cycle counter and content ID, with stable tie-breaking. Refill on exhaustion, avoid immediate repeat across bag boundaries and when a pool changes. A single current candidate yields no_alternative; no candidates yields empty_pool.
- An already-acknowledged UTC epoch, or backward clock movement, yields already_applied unless explicitly forced. A large forward gap consumes one selection, not a replay of missed hours. Caller defines the duration/epoch (e.g. UTC Unix seconds divided by 3600); no local-time/DST assumptions enter Core.
- State is schema_version 1, with last acknowledged epoch, last content ID, next bag and cycle. A proposal contains proposed_state but never persists it. **Only the caller**, after confirming an appropriate application result, may atomically persist that new state. Failure/no-change leaves the acknowledged state intact. Pure library tests may simulate acknowledgement by adopting the proposal; that is not a claim that pixels changed.
- This slice adds no CLI rotation command, timer, profile parser, system state mutation, credential handling or IPC call. Future integration must use an opt-in single rotation authority, isolate per-output state and provide filesystem locks/atomic update/recovery semantics in a separate follow-up design.

## Tradeoffs and limitations

- Deterministic shuffle is reproducible and dependency-free, not cryptographically secret, uniformly random over every permutation or a full recent-history policy. Different outputs with overlapping identical pools may select the same image; distinct-orientation pools should be configured by the caller.
- This is a plan and proposed state only; actual backend success, stale file content, hotplug and visual pixel observations require CLI orchestration and integration evidence. The same candidate ID may be associated with missing paths and needs fresh verification before apply.
- No network requests, no user-file deletion and no new default desktop behavior.

## Test strategy

Offline unit tests cover 48 UTC epochs, adjacent no-repeat, deterministic retry, restore via JSON, empty/single pool, force/rollback, independent outputs, duplicate IDs, pool shrink and invalid input. Linux/Windows/macOS CI still validates this **pure API**, not real wallpaper rotation.

## Architecture diagram impact

Changed: the Core asset/catalog layer now exports an additional content-ID selection planner and state proposal for future consumers. Update docs/architecture.svg and docs/architecture.md in the same PR; desktop orchestration remains explicitly planned.
