# Rotation candidate-probing performance qualification (PR #324)

Date: 2026-11-16 UTC. Scope: measure the existing `selected_candidates()` implementation, which fully probes every candidate on every preview/rotation. No optimization was made.

## Method

Built `target/release/ezwallpaper` and ran one-output `rotate next --epoch 123 --json` previews with an isolated `--state` path. Dry-run means the benchmark includes profile/pool inventory, complete image probe, planning, and process startup, but no state write or desktop IPC/setter. Timed wall-clock externally with Python `time.monotonic`; peak process RSS was read from Linux `/proc/<pid>/status` `VmHWM` every 5ms. Machine: Linux 6.18.55-2-cachyos-lts x86_64, 16 logical CPUs. Two separate invocations per fixture. Run 1 / run 2 are first/repeat passes over the same files, **not** cold-cache / hot-cache measurements: page cache was neither cleared nor controlled. Fixture generation and release build are excluded.

Images are original-free procedural RGB PNGs with distinct deterministic pixel values. `small` means every file is 256×256. `mixed` means 95% 256×256 and 5% 1024×768 (rounded down; one larger image at 100). The separate 21-image synthetic production-shaped pool uses dimensions spanning 3840×2160–6048×3402 (8.29–20.58MP), 295.8MP total, based on the real-pool characteristics in `~/.local/state/dotfiles-submission/sddm-approved-envelope-512-20261113T192028Z/REPORT.md`: 21 files, 16 JPEG / 5 PNG, 8.29–20.58MP, mixed JPEG/PNG. The report's real files were not copied or read by this benchmark; the synthetic production-shaped fixture is all PNG.

| Pool | Files | Total decoded pixels | Run 1 wall / peak RSS | Run 2 wall / peak RSS |
|---|---:|---:|---:|---:|
| Small | 100 | 6.55MP | 0.016s / 10.0MiB | 0.016s / 10.0MiB |
| Mixed | 100 | 10.16MP | 0.021s / 12.1MiB | 0.027s / 9.9MiB |
| Small | 1,000 | 65.54MP | 0.145s / 10.2MiB | 0.144s / 10.4MiB |
| Mixed | 1,000 | 101.58MP | 0.154s / 12.5MiB | 0.154s / 12.5MiB |
| Small | 4,096 | 268.44MP | 0.565s / 12.3MiB | 0.564s / 11.3MiB |
| Mixed | 4,096 | 415.50MP | 0.610s / 13.6MiB | 0.615s / 13.6MiB |
| Production-shaped synthetic | 21 | 295.80MP | 0.204s / 94.1MiB | 0.171s / 94.2MiB |

## Conclusion and limits

On these tested pools, candidate preparation takes 0.17–0.62s, well below a 5s per-setter IPC timeout and a 10s hourly-rotation budget. The 4,096-file mixed case is 0.61s despite 415.5MP cumulative decoded pixels. Selection is therefore acceptable for hourly use at the measured sizes; actual setter latency remains separate and the 5s IPC timeout is not a budget for scanning.

This does **not** bound worst-case 4,096 × 64MiB inputs: fixtures are highly compressible, and there was no adversarial-compression or 64MiB-per-file stress test. The production-shaped synthetic pool also differs from the actual JPEG/PNG mixture. Do not infer worst-case memory or latency from these results. If that envelope needs a guarantee, measure representative large/less-compressible files before considering a cache/health-list optimization; no speculative optimization is included here.

Raw per-run logs, fixture generator, pool profiles/images, machine-readable summary, and test evidence are retained in the private evidence directory `/home/lcr/.local/state/dotfiles-submission/m3-defect-fix-r2-20261116T170432Z/` (not checked into the repository).
