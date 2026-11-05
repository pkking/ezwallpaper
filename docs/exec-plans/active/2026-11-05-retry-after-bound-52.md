# Respect bounded Retry-After for provider 429 responses

Issue: #52
Status: IMPLEMENTING
Owner: agent
Started: 2026-11-05
Last checkpoint: 2026-11-05

## Objective
When an HTTP provider reports a numeric Retry-After rate-limit delay, respect a small bounded delay; do not hammer the endpoint with fixed 100ms retries, and refuse unreasonably long waits rather than blocking the CLI.

## Non-goals
No new persistent format, privilege, desktop integration, live network downloads, or changes to default commands.

## Must-read context
AGENTS.md; README.md; docs/agents/workflow.md; docs/agents/testing.md; crates/ezwallpaper-core/src/wp_provider/mod.rs; docs/adr/0005-provider-source-capabilities.md; Issue #52.

## Current facts
- Baseline: master f6fe95249b47eab59ee71a99b73159cb1d5eeb7f; open PRs: none.
- Observed code validation gap: When an HTTP provider reports a numeric Retry-After rate-limit delay, respect a small bounded delay; do not hammer the endpoint with fixed 100ms retries, and refuse unreasonably long waits rather than blocking the CLI.
- New CI and desktop evidence: UNASSESSED pending new PR.
- Architecture diagram: unchanged — same component and accepted data flow, internal safety boundary only.

## Constraints and invariants
Only numeric delta-seconds are supported; HTTP-date uses existing bounded fallback. Retry cap 5 seconds, at most two retries, no new dependency/public API, and never log tokens.

## Acceptance criteria
- [ ] Retry-After: 0..5 seconds guides 429 retry delays; a larger numeric delay returns a clear bounded error without another attempt
- [ ] Malformed or absent Retry-After falls back to existing bounded exponential retry delays
- [ ] Fixture tests exercise success and refusal without external network or credentials
- [ ] All required CI gates successful on the final PR head.

## Implementation slices
- [ ] Add internal validation/guard without new public interface.
- [ ] Add deterministic offline positive, failure and boundary tests.
- [ ] Validate PR latest-head CI and review failures.

## Verification matrix
| Scope | Gate | Evidence | Status |
|---|---|---|---|
| Rust quality | cargo fmt/clippy | GitHub Rust quality | UNASSESSED |
| Unit/offline | cargo test and relevant Python unittest | GitHub Rust/Agent tests | UNASSESSED |
| Platform | Windows/macOS | GitHub platform matrix | UNASSESSED |
| Integration | Sway / scoped Noctalia | GitHub CI | UNASSESSED |

## Decision gates
None: routine internal behavior within the accepted ADR and no persistent or user-facing default change.

## Evidence log
- 2026-11-05: inspected code at f6fe95249b47eab59ee71a99b73159cb1d5eeb7f; created Issue #52 plan before changing source. CI pending.

## Deviations and discoveries
None at creation.

## Resume from here
Inspect the latest PR head and its CI run; fix the first failing gate, then rerun the final revision without bypassing checks.

## Completion
Final commit: pending
CI run: pending
E2E artifact: pending
Remaining unassessed items: physical desktops and any untested provider integrations
