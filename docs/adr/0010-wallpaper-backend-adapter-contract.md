# ADR 0010: CLI-owned wallpaper backend adapters for cross-desktop rotation

Status: Accepted — target architecture; adapter extraction and desktop-specific implementations are **not yet implemented**
Date: 2026-10-22
Issue: #83
Extends: ADR 0001 (headless Core / CLI boundary), ADR 0004 (Noctalia v5 IPC), ADR 0008 (pure rotation plans), ADR 0009 (locked opt-in rotation)

## Context

A growing list of concrete desktop operations is currently concentrated in `src/setter.rs`: GNOME `gsettings`, KDE/Plasma `qdbus[6]`, LXQt, Noctalia, `swaybg`, `feh`, and wallpaper-rs. The established `src/rotation_cli.rs` executes its already-correct Core shuffle plan but calls `Capability::detect_with(Setter::Noctalia, Some(output))` directly. Cross-desktop rotation therefore cannot reuse the controller without introducing more desktop-special cases into rotation code. One large `match`/command dispatcher or a separate scheduler per desktop would produce divergent state semantics, fake success and competing wallpaper renderers.

The same command accepted by different desktops conveys different evidence: Noctalia v5 can confirm a connector's exact wallpaper path via `wallpaper-get`; GNOME GSettings is global rather than per-monitor; Plasma's desktop/containment mapping differs from connector names; `swaybg` process launch alone is not proof of compositor pixels. XDG Desktop Portal Wallpaper may provide a user-mediated global wallpaper operation when supported by an installed portal backend; it is **not** an acknowledged per-monitor rotation API. Current documented platform capabilities are implementation paths, **not** physical desktop proof.

In-flight PR #82 adds UTC minute-bucket selection and maintains schema v1 state; this architecture is explicitly independent of the #82 implementation and must preserve its eventual final contract.

## Decision — ports and adapters within CLI, not Core

### Module boundaries and dependency direction

```text
ezwallpaper-core (pure) — catalog / content IDs / plan_rotation
                   ↑
src/rotation_cli.rs — controller (UTC epoch, profile, state, lock, commit)
                   ↓
src/backend/mod.rs — WallpaperBackend port + typed evidence/capabilities
                   ↑
src/backend/{noctalia,plasma,gnome,sway,hyprpaper,portal}.rs
                   ↑
src/backend/registry.rs — selects only an explicitly valid implementation
```

Here the vertical abstraction arrow represents the dependency of the controller on the *port*, not on a concrete desktop. Registry constructs/provides the selected implementation; concrete modules know their own IPC/DBus/CLI details. Existing `src/setter.rs` may remain a compatibility facade during migration, but **must not** become a growing command router. In the final design, adding a backend must never require editing Core's planner or the controller's plan/commit algorithm.

No desktop operation, shell command, DBus dependency, Wayland session detection or timer belongs in `ezwallpaper-core`. The adapter port is a **private CLI-owned Rust interface** until explicit API stability requirements justify promotion to a public crate. No new dependency is required by this decision.

### Object-safe port (illustrative target, not implemented)

```rust
trait WallpaperBackend {
    fn id(&self) -> BackendId;
    fn capabilities(&self) -> BackendCapabilities;
    fn list_outputs(&self) -> Result<OutputInventory>;
    fn apply(&mut self, target: &WallpaperTarget, image: &Path) -> Result<ApplyReceipt>;
    fn readback(&mut self, target: &WallpaperTarget) -> Result<Readback>;
}
```

Use a closed `WallpaperTarget` (`GlobalDesktop` or `OutputId`) and typed `BackendCapabilities`. An `OutputId` names the backend's own connector/desktop containment and **is not** assumed to be a universal Wayland/Plasma/GNOME identifier. `OutputInventory` can explicitly report `Unsupported` or `Unavailable`; it must never synthesize a monitor from desktop environment variables.

Minimum capability dimensions:
- **Scope**: `GlobalOnly` vs `PerOutput`; including whether multiple independent outputs can be addressed.
- **Acknowledgement**: `None`, `CommandAccepted` or `ExactPathReadback`. Any pixel evidence is supplied only by dedicated E2E, never guessed from exit codes.
- **Lifecycle**: whether the backend owns a long-lived renderer process, needs an existing desktop/session, or owns no process.
- **Inventory / fit behavior**: named-output discovery supported/unsupported, existing wallpaper rendering/fit-mode support only if proven.

The real implementation may refine method names/types to match Rust's type system and current status values. Keep the trait object-safe: no generic trait methods, associated type requirements at the caller, or concrete backend types exposed to Rotation Controller. Do not erase errors into a `bool`; include typed failures such as `UnsupportedScope`, `AmbiguousRenderer`, `UnreachableSession`, `ReadbackUnavailable`.

### Evidence and state-commit invariant

Three distinct result layers must not be conflated:
1. **Submitted / process launched** — an adapter issued a command; no observed wallpaper.
2. **PathObserved** — the backend can read back the exact local path associated with the target; stronger than command success, still *not* a pixel result.
3. **PixelVerified** — separate compositor framebuffer or actual-screen evidence with source/revision/monitor recorded. Runtime must not label a mere path readback this way.

During the first migration preserve the existing `Submitted`, `LaunchedUnverified`, `PathObserved` runtime statuses and the strict rotation rule: advance durable per-output state **only for verified exact-path acknowledgements**. A backend that supports only `Submitted` is valid for the existing one-shot `apply` path but **ineligible for acknowledged unattended rotation** until it gains a truthful, independently tested readback. Do not treat a successful D-Bus method return as a path readback automatically.

Each output's state is committed after its own acknowledgement under the existing exclusive OS lock, staged atomic save and profile identity validation. Failures never mark the proposed choice applied. Partial multi-output failures retain prior acknowledgements; resuming the same epoch with stable content IDs must not reapply a previously acknowledged output. Preserve #82's selected interval and identity namespace when later merged.

### Fail-closed selection policy

The `BackendRegistry` must separate read-only detection from mutation:
1. Detect active desktop/session and renderer ownership (non-mutating checks only). `auto` must never silently choose a second wallpaper renderer while an existing shell owns the background.
2. Validate required target scope, per-output identity mapping, and required acknowledgement **for all outputs before the first apply**. A `GlobalOnly` GNOME/Portal adapter cannot satisfy a two-named-output profile, even if a single global command would appear to set something. Reject this **before any wallpaper side effect or durable state write**.
3. Select an explicit backend when ambiguity exists. If explicit Noctalia is unavailable, fail; **no fallback to swaybg**, no persistent duplicate background process.
4. For a supported target, validate local file and binary/session prerequisites; delegate apply and optional readback to one concrete adapter.
5. Do not claim a persistent renderer survives user logout, compositor restart or hotplug without its own lifecycle policy and tests.

Existing `ezwallpaper apply` auto-selection/defaults remain unchanged until a separate compatibility-tested PR explicitly migrates that path. This decision grants **no authorization** to change installed timer state or automatically rewrite a user's desktop settings.

### Proposed concrete module slices

- **B1 (first code PR after #82 settles)**: introduce CLI-side `backend::mod` trait/capabilities/evidence and tiny registry; move Noctalia protocol into `backend::noctalia`; inject a `dyn WallpaperBackend` into rotation, retaining Noctalia as the only eligible rotation backend. Offline fakes enforce global-only mismatch, no false acknowledgements, per-output failure/partial retry and unchanged state; pinned native Noctalia E2E must still pass. No new desktop support claim.
- **B2**: migrate GNOME global and Plasma container mapping as separate adapters with distinct capability/evidence levels. Allow one-shot global `apply` without assuming multi-output rotation eligibility.
- **B3**: Sway/Hyprpaper separate adapters and a lifecycle policy for any persistent renderer; portal is optional and global-only with consent constraints. One backend per reviewable PR.
- **Guardrails**: CI/test static boundary check forbids `noctalia`, `gsettings`, `qdbus`, `swaybg`, `hyprctl` and raw `Command` in controller/Core code, while permitting them only in concrete integration modules. Offline capability matrix must reject unsupported/output mismatches before invoking any test fake backend. The registry may know backend identifiers; it must not contain protocol command strings.

## Alternatives rejected

- **One large desktop-specific `match` in Rotation Controller**: creates a monolith, leaks IPC into state transactions, duplicates error handling and tempts silent fallback.
- **Independent rotation scheduler and state per DE**: diverges in epoch/locking/idempotency and breaks the long-standing content-ID Core contract.
- **XDG Desktop Portal only**: not a universal per-output API, may require consent and depends on installed portal backend; insufficient for arbitrary unattended two-output rotation.
- **Writing a new Wayland wallpaper renderer for all compositors**: competing renderer ownership, lifecycle and GPU burden, contrary to the existing Noctalia integration decision.
- **Promoting desktop port into ezwallpaper-core**: violates headless Core boundary and increases dependency/portability cost.

## Consequences / migration safety

Adds a small private interface and test surface; individual backend modules may contain unavoidable desktop-specific complexity without spreading it into Core or the controller. Migration can proceed through small PRs. The target introduces additional classification such as global-only/ineligible-for-rotation, and may report an explicit unsupported capability rather than silently applying wallpaper globally. That is intentional fail-closed behavior; any user-visible default change still needs a separate compatibility decision.

Historical native niri/Noctalia CI evidence remains scoped to pinned virtual displays. GNOME, Plasma, Sway, Hyprpaper, Portal, real displays, login sessions and physical hotplug remain **UNASSESSED for new rotation integration** until real backend-specific tests are executed.

## References

- [Issue #83](https://github.com/pkking/ezwallpaper/issues/83) — explicit user-approved Adapter Pattern architecture
- [ADR 0001](0001-core-cli-boundaries.md), [ADR 0004](0004-noctalia-v5-ipc.md), [ADR 0008](0008-pure-rotation-planner.md), [ADR 0009](0009-locked-noctalia-rotation.md)
- [XDG Wallpaper Portal](https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Wallpaper.html) — optional global/consent-aware integration
- [KDE Plasma Scripting](https://develop.kde.org/docs/plasma/scripting/api/)
- [Hyprpaper](https://wiki.hypr.land/hypr-ecosystem/user/hyprpaper/)

## Architecture diagram impact

Architecture diagram: updated

Changes CLI internal architecture and future OS/DE setter dependency edges: `docs/architecture.svg` and `docs/architecture.md` updated **in this same PR**, with the interface/registry/individual backend modules explicitly **PLANNED**, whereas existing `setter.rs` paths and Noctalia-only rotation remain clearly **IMPLEMENTED**. No ADR change is represented as already-executed source refactoring.
