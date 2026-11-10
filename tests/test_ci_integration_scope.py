"""No-network selector tests: preserve wpaperd CI on relevant source changes."""
from pathlib import Path
import unittest

from scripts.ci_integration_scope import requires_wpaperd_native


class NativeWpaperdScopeTests(unittest.TestCase):
    def test_documentation_and_unrelated_tests_do_not_run_native_build(self):
        for changed in (
            [],
            ["README.md"],
            ["docs/architecture.md", "docs/architecture.svg"],
            ["docs/exec-plans/completed/archive.md"],
            ["tests/test_agent_plan.py"],
            ["scripts/validate_agent_plan.py", "docs/exec-plans/active/task.md"],
        ):
            with self.subTest(changed=changed):
                self.assertFalse(requires_wpaperd_native(changed))

    def test_production_and_shared_rust_changes_force_real_native_e2e(self):
        for path in (
            "src/main.rs",
            "src/backend/wpaperd.rs",
            "src/backend/registry.rs",
            "src/rotation_cli.rs",
            "src/backend/mod.rs",
            "crates/ezwallpaper-core/src/lib.rs",
            "crates/ezwallpaper-core/Cargo.toml",
            "Cargo.toml",
            "Cargo.lock",
            "rust-toolchain.toml",
        ):
            with self.subTest(path=path):
                self.assertTrue(requires_wpaperd_native([path]))

    def test_integration_helpers_workflow_and_scope_code_force_native(self):
        for path in (
            ".github/workflows/ci.yml",
            "scripts/ci_integration_scope.py",
            "tests/test_ci_integration_scope.py",
            "tests/test_wpaperd_native_helpers.py",
            "tests/test_sway_e2e_helpers.py",
            "tests/test_sway_dual_helpers.py",
            "tests/e2e/sway/wpaperd_native.py",
            "tests/e2e/sway/dual.py",
            "tests/e2e/sway/run.py",
            "tests/e2e/sway/sway-dual.conf",
        ):
            with self.subTest(path=path):
                self.assertTrue(requires_wpaperd_native([path]))

    def test_mixed_changes_trigger_and_docs_only_do_not(self):
        self.assertTrue(requires_wpaperd_native(["README.md", "src/backend/wpaperd.rs"]))
        self.assertTrue(requires_wpaperd_native(["docs/x.md", ".github/workflows/ci.yml"]))
        self.assertFalse(requires_wpaperd_native(["docs/x.md", "docs/y.md"]))

    def test_native_wpaperd_sway_toolchain_is_date_pinned_without_gate_relaxation(self):
        # CI build compiler identity is part of the exact native executable
        # cache key: a rolling nightly makes even unchanged source miss daily.
        ci = (Path(__file__).resolve().parents[1] /
              ".github/workflows/ci.yml").read_text(encoding="utf-8")
        job = ci.split("\n  sway-visual-e2e:\n", 1)[1].split(
            "\n  noctalia-sway-visual-e2e:\n", 1
        )[0]
        self.assertIn("          toolchain: nightly-2026-11-09\n", job)
        self.assertNotIn("          toolchain: nightly\n", job)
        for required in (
            "rustc -vV",
            "cargo --version",
            "dpkg-query -W",
            "sha256sum .github/workflows/ci.yml scripts/ci_native_cache.py",
            "actions/cache/restore@v4",
            "actions/cache/save@v4",
            "github.event_name == 'push'",
            "github.ref == 'refs/heads/master'",
            "scripts/ci_native_cache.py restore --component wpaperd",
            "grep -Fx '9e71fdd10e1f2d94532edaf0f54402aac3c0b01c'",
            "Verify real wpaperd native IPC and two-output rendered pixels",
            "Observe isolated two-output Sway framebuffer separation",
        ):
            with self.subTest(required=required):
                self.assertIn(required, job)
        self.assertNotIn("restore-keys:", job)
        self.assertNotIn("pull_request_target", ci)

    def test_deletion_or_rename_paths_are_conservatively_classified(self):
        # Git --name-only includes removed paths, or both sides under rename handling.
        self.assertTrue(requires_wpaperd_native(["src/backend/old.rs"]))
        self.assertTrue(
            requires_wpaperd_native(
                ["docs/archive.md", "tests/e2e/sway/wpaperd_native.py"]
            )
        )


if __name__ == "__main__":
    unittest.main()
