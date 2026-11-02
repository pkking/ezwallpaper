# Provider download byte ceiling (Issue #79)

The Bing, Pexels, and Wallhaven image download paths now stage each
response with a **64 MiB per-response hard limit** by default. The downloader
reads at most the remaining allowed bytes and probes one additional byte
at the boundary. That extra byte is **never written** to the staged file.
A rejected or interrupted response automatically removes its temporary
file; the previous wallpaper remains available, and no incomplete file is
published.

To override the default for an explicit provider fetch:

```sh
ezwallpaper --backend bing --max-download-bytes 16777216 --download-only
ezwallpaper --backend wallhaven --max-download-bytes 33554432 fetch --json
```

The value is in bytes and must be positive. Each provider's public builder
also accepts `with_max_download_bytes(bytes)`. A download writes the source
stream in bounded chunks and reports the **actual staged byte count** in
non-secret debug diagnostics. Response `Content-Length`, whether absent,
wrong or forged, is not a bypass. This setting bounds each individual active
image-response stage, **not the aggregate across parallel downloads**, nor
the HTTP metadata response, provider's old published files, the separate
CAS store or overall filesystem occupancy. No global temporary-space quota
or concurrency reservation is implemented. This is distinct from Issue #57
persistent store retention/GC; do not equate a pool's disk cap with its
in-flight staging budget.

Offline synthetic reader tests cover exact limit, limit+1, interrupted,
empty, oversized, retry and no-partial-publication cases. They do not prove
live provider behavior or concurrent space accounting. The default value is
not a recommendation for all image sizes; choose a smaller explicit ceiling
for constrained machines. No downloaded contents or credentials are logged.
