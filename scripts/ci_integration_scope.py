"""Conservative native wpaperd E2E selection from Git changed paths.

Source contract: .github/workflows/ci.yml change-scope and
tests/e2e/sway/wpaperd_native.py. Docs-only does not require rebuilding pinned
wpaperd, but actual Sway/swaybg headless pixel tests remain unconditional.
CI/workflow changes always select native tests so a filter cannot self-skip.
"""
from __future__ import annotations

from collections.abc import Iterable

# All code that could affect output selection, path state, runtime ABI or
# shared native Sway helpers must retain real native daemon+framebuffer proof.
CODE_PREFIXES = ("src/", "crates/", "tests/e2e/sway/")
DIRECT_FILES = frozenset({
    ".github/workflows/ci.yml",
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain",
    "rust-toolchain.toml",
    "scripts/ci_integration_scope.py",
    "tests/test_ci_integration_scope.py",
    "tests/test_wpaperd_native_helpers.py",
    "tests/test_sway_e2e_helpers.py",
    "tests/test_sway_dual_helpers.py",
})


def requires_wpaperd_native(changed_paths: Iterable[str]) -> bool:
    """True if native IPC and virtual-screen pixel proof may be invalidated.

    Paths must come from Git's name-only diff, not from untrusted PR text.
    Deleted/renamed files appear as changed paths and are classified normally.
    """
    return any(
        path in DIRECT_FILES
        or path.startswith(CODE_PREFIXES)
        or path.endswith("/Cargo.toml")
        or path.endswith("/Cargo.lock")
        for path in changed_paths
    )
