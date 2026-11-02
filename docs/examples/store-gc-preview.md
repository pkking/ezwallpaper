# Owned CAS read-only retention preview (Issue #57)

This is **not a garbage collector**. Use only a separately initialized
`ezwallpaper store --root` directory (ADR 0003), never the legacy
`--dir` or a user-managed Pictures folder. The command reads the existing
verified CAS inventory and estimates capacity pressure without modifying
files, the index or store metadata.

```sh
ezwallpaper store --root ./managed-wallpapers gc-preview \\
  --max-bytes 500000000 --pin sha256:REPLACE_WITH_REAL_EXISTING_DIGEST --json
```

The selected `--pin` IDs **must exist** and pass SHA-256 validation. Repeat
`--pin` for each current/rotation/greeter/video-dependent asset you have
independently identified. Without complete reference discovery, unknown
external consumer references are **not protected**. The command cannot
determine whether a candidate is safe for deletion. It therefore emits
`READ_ONLY_UNSAFE_TO_DELETE_PREVIEW`,
`deletes_performed: false`, and
`active_references_verified: false`.

The preview sorts only explicitly unpinned entries by descending verified
byte size and then by content ID. It suggests enough candidates to reach
`--max-bytes` if possible; it reports retained pin bytes and any remaining
pressure if protected entries alone exceed the budget. This is not an LRU or
age-based retention policy, nor a promised cleanup order. `--max-bytes`
is an **ephemeral planning target**, not a disk quota, temp-stage budget, or
new persistent CAS configuration. No command for actual deletion is added.

Future GC requires a separately reviewed provenance/reference schema,
transaction-safe pin tracking, concurrency coordination with import and
rotation, a migration/rollback design, and an explicit ADR. Until then, do
not automatically delete these suggested entries.
