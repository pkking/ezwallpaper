# Configurable timer unit for hourly evidence — Issue #319

## Context

- Issue: [#319](https://github.com/pkking/ezwallpaper/issues/319), which reports that the read-only hourly evidence collector hard-codes a timer unit name that does not match the installed user timer.
- Goal: G-01 (Epic #60); contribution type: **BLOCKER** for Issue #54's real-hour evidence.
- Related blocker evidence: [#54 comment](https://github.com/pkking/ezwallpaper/issues/54#issuecomment-6881895945).
- The report identifies `ezwallpaper-rotate.timer` as the local name, while existing repository examples use `ezwallpaper-rotation.timer`.

## Scope and acceptance

Add an optional `capture --timer-unit UNIT` observer override, preserving the existing `ezwallpaper-rotation.timer` default. Pass the unit as one argv element to `systemctl show`; reject empty, whitespace-containing, NUL-containing and leading-dash values before external commands. No shell interpolation, timer/service modifications, or changes to rotation behavior.

Acceptance: offline tests verify the unchanged default, custom timer argv, and invalid values rejected before the fake runner is called; Python syntax/AST, both focused unittest suites, CLI help, and `git diff --check` pass.

## Verification and limits

Run only offline tests and help. Do not run real `capture`, host `systemctl`, or start/change any timer. This change enables collection only; actual timer-trigger correlation, a remaining 24-hour run, released-niri/Noctalia operation and physical display evidence remain unassessed. CI is not run here. Publication and push remain deferred for independent review and authorization.
