# ADR 0005: Bounded provider acquisition and orientation negotiation

Status: Accepted
Date: 2026-10-18
Issue: #52
Supersedes: None (extends ADR 0001)

## Context

Existing CLI fetches one Bing/Pexels image, hardcodes Bing idx 0 and Pexels landscape. On 4K landscape and 1080x1920 portrait displays, different source assets and batch prefetch are needed. Providers have substantially different upstream capabilities and retention limits.

## Decision

- Keep headless Core responsible for provider-specific queries and downloads. Add public Wallhaven SFW provider alongside Bing and Pexels, with an explicit landscape/portrait type; CLI accepts --count, --orientation, --query, --page, --bing-offset, --min-width/--min-height.
- Bing's public recent archive is bounded to idx 0..7, 1..8 images, and rejects out-of-range combinations. No unsupported promise of complete past history. Bing cannot honor orientation or search.
- Pexels uses documented search orientation, query, pagination and locale; it checks width/height advertised by the API before download. Pexels size=large is an upstream megapixel category, NOT exact physical-pixel guarantee.
- Wallhaven uses public SFW search (purity 100, general category), ratio filters, min resolution and bounded pagination; it also checks actual API-reported dimensions locally. Unverified endpoint data is not equivalent to image decoding.
- Limit batch sizes and pagination. Shared HTTP client has connection/request timeouts and at most two retries on transient 429/5xx/connect/timeout failures; preserve complete staged downloads and filesystem protections.
- Restrict provider-returned image URLs to HTTPS and designated source CDN hosts before downloading. Do not put Pexels tokens in URLs or logs. Token precedence: legacy --token, optional --token-file with private permissions, environment variable EZWALLPAPER_PEXELS_TOKEN.
- Retain old --backend choice/default and legacy flag-only fetch+apply as before; no changes to JSON manifest v1, desktop setter or owned CAS. Content IDs and any rotation history are separate concerns.

## Alternatives

- Download every hour directly from Bing: same-day duplicates are expected; does not guarantee rotation.
- Pretend all providers support identical filters: rejected, would mislead callers and produce wrong display orientation.
- Add a new background daemon and database: defer until rotation Issue #54.
- Bypass external service APIs with scraping: unnecessary, fragile and risks terms/compliance.
- Treat reported remote dimensions as trusted decoded dimensions: rejected; validation and pixel-safe derivation are Issue #53.

## Consequences

One additional headless Core source plus opt-in acquisition flags; test surface expands but default CLI remains compatible. Provider HTTP metadata remains untrusted. Offline tests can verify parsing/requests and local safety but not current live quotas; no GUI side effects are introduced by fetch subcommand.

## References

- Microsoft Q&A on Bing HPImageArchive constraints: https://learn.microsoft.com/en-us/answers/questions/1473961/bing-hpimagearchive-aspx-question
- Pexels Search Photos official docs: https://www.pexels.com/api/documentation/
- Wallhaven v1 API documentation: https://wallhaven.cc/help/api

## Architecture diagram impact

Changed: headless Core now has a third provider (Wallhaven); docs/architecture.svg must mark Wallhaven implemented rather than a planned external source.
