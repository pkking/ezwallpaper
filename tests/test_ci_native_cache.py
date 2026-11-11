"""CI native cache safety contract: offline, no desktop or network."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_native_cache as cache  # noqa: E402


class PinnedNativeCacheTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.component = "noctalia"
        self.key = cache.key_for("noctalia", b"trixie packages and compiler versions")
        self.binary = self.root / "upstream-noctalia"
        self.binary.write_bytes(b"trusted compiled executable bytes")
        self.binary.chmod(0o755)
        self.source = self.root / "source-sha"
        self.source.write_text(cache.PINNED[self.component]["source_sha"] + "\n")
        self.directory = self.root / "cache"

    def seal(self):
        return cache.seal(self.component, self.key, self.binary, self.source,
                          self.directory)

    def restore(self):
        return cache.restore(self.component, self.key, self.directory,
                             self.root / "installed" / "noctalia",
                             self.root / "artifacts" / "source-sha.txt")

    def test_keys_bound_to_upstream_recipe_and_installed_package_fingerprint(self):
        self.assertEqual(self.key, cache.key_for(self.component,
                         b"trixie packages and compiler versions"))
        self.assertNotEqual(self.key, cache.key_for(self.component,
                            b"trixie packages and compiler versions\nnew version"))
        self.assertNotEqual(self.key, cache.key_for("niri",
                            b"trixie packages and compiler versions"))
        self.assertRaises(cache.CacheError, cache.key_for, self.component, b"")
        self.assertRaises(cache.CacheError, cache.key_for, "unknown", b"machine")
        self.assertRaises(cache.CacheError, cache.key_for, self.component,
                          b"a" * (cache.MAX_FINGERPRINT_BYTES + 1))

    def test_seal_restore_round_trip_with_executable_and_verified_sha(self):
        manifest = self.seal()
        self.assertEqual(manifest["source_sha"], cache.PINNED[self.component]["source_sha"])
        self.assertEqual(manifest, cache.inspect(self.component, self.key, self.directory))
        result = self.restore()
        self.assertEqual(result, manifest)
        target = self.root / "installed/noctalia"
        self.assertEqual(target.read_bytes(), self.binary.read_bytes())
        self.assertTrue(os.access(target, os.X_OK))
        self.assertEqual((self.root / "artifacts/source-sha.txt").read_text(),
                         cache.PINNED[self.component]["source_sha"] + "\n")
        with self.assertRaisesRegex(cache.CacheError, "target_already_exists"):
            self.restore()

    def test_existing_identity_output_never_clobbered_on_restore(self):
        self.seal()
        target = self.root / "installed/noctalia"
        sha_file = self.root / "artifacts/source-sha.txt"
        sha_file.parent.mkdir(parents=True)
        sha_file.write_text("previous identity\\n")
        with self.assertRaisesRegex(cache.CacheError, "source_identity_already_exists"):
            self.restore()
        self.assertEqual(sha_file.read_text(), "previous identity\\n")
        self.assertFalse(target.exists())

        sha_file.unlink()
        protected = self.root / "protected-source.txt"
        protected.write_text("do not overwrite\\n")
        sha_file.symlink_to(protected)
        with self.assertRaisesRegex(cache.CacheError, "source_identity_already_exists"):
            self.restore()
        self.assertEqual(protected.read_text(), "do not overwrite\\n")
        self.assertFalse(target.exists())

    def test_niri_seal_and_restore_preserves_exact_source_and_executable(self):
        # A separate pinned Rust toolchain and native IPC binary must never
        # accidentally inherit Noctalia's manifest/source identity.
        component = "niri"
        key = cache.key_for(component, b"debian trixie niri clang rustc-1.99.1")
        binary = self.root / "niri-native"
        binary.write_bytes(b"niri experimental pinned native executable")
        binary.chmod(0o755)
        observed = self.root / "niri-source-sha"
        observed.write_text(cache.PINNED[component]["source_sha"] + "\n")
        directory = self.root / "niri-cache"

        sealed = cache.seal(component, key, binary, observed, directory)
        self.assertEqual(sealed["component"], "niri")
        self.assertEqual(sealed["source_sha"], cache.PINNED["niri"]["source_sha"])
        self.assertNotEqual(sealed["recipe"], cache.PINNED["noctalia"]["recipe"])
        self.assertEqual(cache.inspect(component, key, directory), sealed)
        with self.assertRaises(cache.CacheError):
            cache.inspect("noctalia", self.key, directory)

        target = self.root / "niri-restored/niri"
        sha_file = self.root / "niri-artifacts/upstream-commit.txt"
        restored = cache.restore(component, key, directory, target, sha_file)
        self.assertEqual(restored, sealed)
        self.assertEqual(target.read_bytes(), binary.read_bytes())
        self.assertTrue(os.access(target, os.X_OK))
        self.assertEqual(sha_file.read_text(),
                         cache.PINNED[component]["source_sha"] + "\n")

    def test_niri_source_mismatch_fails_before_sealing_binary(self):
        component = "niri"
        binary = self.root / "niri-native"
        binary.write_bytes(b"niri native bytes")
        binary.chmod(0o755)
        sha_file = self.root / "niri-sha"
        sha_file.write_text(cache.PINNED["noctalia"]["source_sha"] + "\n")
        output = self.root / "rejected-niri-cache"
        with self.assertRaisesRegex(cache.CacheError, "upstream_source_sha_mismatch"):
            cache.seal(component, cache.key_for(component, b"trixie"), binary,
                       sha_file, output)
        self.assertFalse(output.exists())

    def test_cache_manifest_or_binary_corruption_never_restores(self):
        for field, invalid in [
            ("component", "niri"),
            ("source_sha", cache.PINNED["niri"]["source_sha"]),
            ("cache_key", "ezw-native-v1-noctalia-" + "0" * 64),
            ("recipe", "unsafe build flags"),
            ("schema_version", True),
            ("binary_sha256", "0" * 64),
            ("unexpected", 1),
        ]:
            with self.subTest(field=field):
                if self.directory.exists():
                    shutil.rmtree(self.directory)
                manifest = self.seal()
                manifest[field] = invalid
                (self.directory / "manifest.json").write_text(json.dumps(manifest))
                with self.assertRaises(cache.CacheError):
                    self.restore()
                self.assertFalse((self.root / "installed/noctalia").exists())
        shutil.rmtree(self.directory)
        self.seal()
        (self.directory / "binary").write_bytes(b"tampered")
        with self.assertRaisesRegex(cache.CacheError, "cache_binary_integrity_failed"):
            self.restore()

    def test_parser_recursion_failure_fails_closed_without_restoring(self):
        self.seal()
        # A bounded manifest can still trigger a parser recursion failure on
        # interpreters with lower recursion limits. Inject that failure directly
        # rather than depending on a platform-specific JSON nesting threshold.
        with mock.patch.object(cache.json, "loads", side_effect=RecursionError):
            with self.assertRaisesRegex(cache.CacheError, "invalid_cache_manifest_json"):
                self.restore()
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = cache.main([
                    "restore", "--component", self.component, "--key", self.key,
                    "--cache-dir", str(self.directory),
                    "--target", str(self.root / "installed/noctalia"),
                    "--sha-file", str(self.root / "artifacts/source-sha.txt"),
                ])
        self.assertFalse((self.root / "installed/noctalia").exists())
        self.assertFalse((self.root / "artifacts/source-sha.txt").exists())
        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("refused: invalid_cache_manifest_json", stderr.getvalue())

    def test_duplicate_manifest_fields_and_symlink_executables_fail_closed(self):
        self.seal()
        original = (self.directory / "manifest.json").read_text()
        (self.directory / "manifest.json").write_text(
            original.rstrip().removesuffix("}") + ', "component": "noctalia"}'
        )
        with self.assertRaisesRegex(cache.CacheError, "duplicate_cache_manifest_field"):
            self.restore()
        (self.directory / "manifest.json").write_text(original)
        (self.directory / "binary").unlink()
        (self.directory / "binary").symlink_to(self.binary)
        with self.assertRaisesRegex(cache.CacheError, "unsafe_binary_file"):
            self.restore()

    def test_source_identity_symlink_and_nonexecutable_seal_refused(self):
        self.source.write_text("different-revision\n")
        with self.assertRaisesRegex(cache.CacheError, "upstream_source_sha_mismatch"):
            self.seal()
        self.source.write_text(cache.PINNED[self.component]["source_sha"] + "\n")
        self.binary.chmod(0o644)
        with self.assertRaisesRegex(cache.CacheError, "binary_not_executable"):
            self.seal()
        self.binary.chmod(0o755)
        self.binary.unlink()
        self.binary.symlink_to(self.source)
        with self.assertRaisesRegex(cache.CacheError, "unsafe_binary_file"):
            self.seal()

    def test_cache_directory_symlink_and_wrong_component_are_rejected(self):
        self.seal()
        alias = self.root / "alias"
        alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaisesRegex(cache.CacheError, "unsafe_cache_directory"):
            cache.inspect(self.component, self.key, alias)
        with self.assertRaises(cache.CacheError):
            cache.inspect("niri", self.key, self.directory)

    def test_cli_failure_is_nonzero_and_does_not_claim_cache_hit(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = cache.main([
                "restore", "--component", self.component, "--key", self.key,
                "--cache-dir", str(self.directory),
                "--target", str(self.root / "installed/noctalia"),
                "--sha-file", str(self.root / "artifacts/source-sha.txt"),
            ])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("refused:", stderr.getvalue())

    def test_wpaperd_cache_is_source_pinned_and_never_accepts_wrong_abi(self):
        component = "wpaperd"
        pinned = cache.PINNED[component]["source_sha"]
        self.assertEqual(pinned, "9e71fdd10e1f2d94532edaf0f54402aac3c0b01c")
        fingerprint = b"ubuntu-24.04 rustc+wayland runtime package versions"
        key = cache.key_for(component, fingerprint)
        self.assertNotEqual(key, cache.key_for(component, fingerprint + b"new-ABI"))
        self.assertNotEqual(key, self.key)
        binary = self.root / "wpaperd-binary"
        binary.write_bytes(b"pinned wpaperd executable fixture")
        binary.chmod(0o755)
        sha_file = self.root / "wpaperd-source"
        sha_file.write_text(pinned + "\n", encoding="ascii")
        cache_dir = self.root / "wpaperd-cache"
        sealed = cache.seal(component, key, binary, sha_file, cache_dir)
        self.assertEqual(sealed["component"], "wpaperd")
        self.assertEqual(sealed["source_sha"], pinned)
        self.assertEqual(cache.inspect(component, key, cache_dir), sealed)

        target = self.root / "wpaperd-native/wpaperd"
        sha_target = self.root / "wpaperd-artifacts/source.txt"
        cache.restore(component, key, cache_dir, target, sha_target)
        self.assertEqual(target.read_bytes(), binary.read_bytes())
        self.assertEqual(sha_target.read_text(), pinned + "\n")

        with self.assertRaises(cache.CacheError):
            cache.inspect(component, cache.key_for(component, b"different-ABI"), cache_dir)
        with self.assertRaises(cache.CacheError):
            cache.inspect("noctalia", self.key, cache_dir)
        (cache_dir / "binary").write_bytes(b"corrupted executable")
        with self.assertRaises(cache.CacheError):
            cache.inspect(component, key, cache_dir)

    def test_wpaperd_workflow_only_saves_after_real_pixel_e2e_on_master(self):
        ci = (Path(__file__).resolve().parents[1] /
              ".github/workflows/ci.yml").read_text()
        job = ci.split("  sway-visual-e2e:\n", 1)[1].split(
            "\n  noctalia-sway-visual-e2e:", 1)[0]
        self.assertNotIn("pull_request_target", ci)
        self.assertNotIn("restore-keys:", job)
        self.assertNotIn("cache-mode: write", job)
        self.assertIn("actions/cache/restore@v4", job)
        self.assertIn("actions/cache/save@v4", job)
        self.assertIn("if: success() && needs.change-scope.outputs.wpaperd == 'true' && github.event_name == 'push' && github.ref == 'refs/heads/master'", job)
        source_check = job.index("grep -Fx '9e71fdd10e1f2d94532edaf0f54402aac3c0b01c'")
        cache_restore = job.index("python3 scripts/ci_native_cache.py restore --component wpaperd")
        native_pixels = job.index("Verify real wpaperd native IPC and two-output rendered pixels")
        master_save = job.index("Save verified wpaperd cache from trusted master only")
        self.assertLess(source_check, cache_restore)
        self.assertLess(cache_restore, native_pixels)
        self.assertLess(native_pixels, master_save)
        self.assertIn("scripts/ci_native_cache.py seal --component wpaperd", job)
        self.assertIn("sha256sum .github/workflows/ci.yml scripts/ci_native_cache.py", job)
        self.assertIn("tests/e2e/sway/wpaperd_native.py", job)
        self.assertIn("Observe actual composited Sway wallpaper", job)
        self.assertIn("Observe isolated two-output Sway framebuffer separation", job)
        self.assertIn("Always preserve native wpaperd source, IPC and framebuffer evidence", job)

    def test_wpaperd_exact_key_fingerprint_is_retained_without_relaxing_abi(self):
        """Artifacts preserve the bytes hashed as the wpaperd cache key."""
        ci = (Path(__file__).resolve().parents[1] /
              ".github/workflows/ci.yml").read_text()
        job = ci.split("  sway-visual-e2e:\n", 1)[1].split(
            "\n  noctalia-sway-visual-e2e:", 1)[0]
        start = job.index("- name: Fingerprint pinned wpaperd source build and ABI")
        end = job.index("- name: Restore trusted wpaperd executable cache")
        fingerprint = job[start:end]
        original = "} > /tmp/ezw-wpaperd-build-fingerprint"
        copied = 'cp /tmp/ezw-wpaperd-build-fingerprint "$diagnostics/fingerprint.txt"'
        checked = 'cmp /tmp/ezw-wpaperd-build-fingerprint "$diagnostics/fingerprint.txt"'
        digest = '(cd "$diagnostics" && sha256sum fingerprint.txt > sha256.txt)'
        key = "scripts/ci_native_cache.py key --component wpaperd --fingerprint /tmp/ezw-wpaperd-build-fingerprint"
        self.assertIn("diagnostics=artifacts/wpaperd-native-e2e/cache-fingerprint", fingerprint)
        for record in (
            "ubuntu-24.04|wpaperd-1.3.0|cargo-locked-release-p-wpaperd",
            "uname -sm", "rustc -vV", "cargo --version",
            "dpkg-query -W -f=", "libwayland-dev", "libegl-dev",
            "libgles-dev", "libxkbcommon-dev", "libssl-dev",
            "libgbm1", "libgl1-mesa-dri", "LC_ALL=C sort",
            "sha256sum .github/workflows/ci.yml scripts/ci_native_cache.py",
            original, copied, checked, digest, key,
        ):
            with self.subTest(record=record):
                self.assertIn(record, fingerprint)
        self.assertLess(fingerprint.index("dpkg-query -W"), fingerprint.index(
            "sha256sum .github/workflows/ci.yml scripts/ci_native_cache.py"))
        self.assertLess(fingerprint.index(original), fingerprint.index(copied))
        self.assertLess(fingerprint.index(copied), fingerprint.index(checked))
        self.assertLess(fingerprint.index(checked), fingerprint.index(digest))
        self.assertLess(fingerprint.index(digest), fingerprint.index(key))
        self.assertIn("Always preserve native wpaperd source, IPC and framebuffer evidence", job)
        self.assertIn("path: artifacts/wpaperd-native-e2e/", job)
        self.assertIn("Verify real wpaperd native IPC and two-output rendered pixels", job)
        self.assertIn("Save verified wpaperd cache from trusted master only", job)
        self.assertNotIn("restore-keys:", job)

    def test_native_cache_fingerprint_evidence_preserves_full_key_inputs(self):
        ci = (Path(__file__).resolve().parents[1] /
              ".github/workflows/ci.yml").read_text()
        job = ci.split("  noctalia-sway-visual-e2e:\n", 1)[1].split(
            "\n  platform-tests:", 1)[0]
        for component, pretty in (("noctalia", "Noctalia"), ("niri", "niri")):
            block = job.split(
                f"- name: Fingerprint pinned {pretty} build and ABI", 1
            )[1].split("- name: Restore trusted", 1)[0]
            evidence = f"artifacts/{'noctalia-sway-e2e' if component == 'noctalia' else 'niri-noctalia-e2e'}/cache-fingerprint"
            fingerprint = f"/tmp/ezw-{component}-build-fingerprint"
            self.assertIn(f"diagnostics={evidence}", block)
            self.assertIn("dpkg-query -W -f=", block)
            self.assertIn("LC_ALL=C sort > \"$diagnostics/installed-packages.txt\"", block)
            self.assertIn('} > "$diagnostics/toolchain-and-workflow.txt"', block)
            self.assertIn("dpkg --print-architecture", block)
            self.assertIn("c++ --version", block)
            self.assertIn("sha256sum .github/workflows/ci.yml", block)
            self.assertIn(
                'cat "$diagnostics/installed-packages.txt" "$diagnostics/toolchain-and-workflow.txt" > '
                + fingerprint, block,
            )
            self.assertIn(
                f'sha256sum "$diagnostics/installed-packages.txt" "$diagnostics/toolchain-and-workflow.txt" {fingerprint}',
                block,
            )
            self.assertIn(
                f"scripts/ci_native_cache.py key --component {component} --fingerprint {fingerprint}",
                block,
            )
            self.assertLess(
                block.index("dpkg-query -W"), block.index('cat "$diagnostics/installed-packages.txt"')
            )
            self.assertLess(
                block.index('cat "$diagnostics/installed-packages.txt"'),
                block.index("scripts/ci_native_cache.py key"),
            )
            self.assertNotIn("restore-keys:", job)
            self.assertNotIn("pull_request_target", ci)
        self.assertIn("meson --version", job)
        self.assertIn("pkg-config --modversion wayland-protocols", job)
        self.assertIn("rustc +1.99.1 --version", job)
        self.assertIn("cargo +1.99.1 --version", job)
        self.assertIn("path: artifacts/noctalia-sway-e2e/", job)
        self.assertIn("path: artifacts/niri-noctalia-e2e/", job)
        self.assertIn("Test actual native IPC and dual output rendered pixels", job)
        self.assertIn("Verify real niri + Noctalia dual-output framebuffer", job)

    def test_workflow_has_read_only_pr_and_master_only_save_and_pixel_e2e(self):
        ci = (Path(__file__).resolve().parents[1] /
              ".github/workflows/ci.yml").read_text()
        job = ci.split("  noctalia-sway-visual-e2e:\n", 1)[1].split(
            "\n  platform-tests:", 1)[0]
        self.assertNotIn("cache-mode: write", job)
        self.assertNotIn("pull_request_target", ci)
        self.assertIn("if: github.event_name == 'push' && github.ref == 'refs/heads/master'", job)
        self.assertIn("actions/cache/restore@v4", job)
        self.assertIn("actions/cache/save@v4", job)
        self.assertIn("github.ref == 'refs/heads/master'", job)
        self.assertIn("tests/e2e/sway/noctalia_v5.py", job)
        self.assertIn("tests/e2e/sway/niri_noctalia.py", job)
        # The native Noctalia executable reads fonts/translations at runtime.
        # A cache-hit binary without the pinned source assets is NOT valid E2E.
        checkout = job.index("Checkout exact Noctalia source and runtime assets")
        build = job.index("Build pinned upstream native Noctalia")
        self.assertLess(checkout, build)
        self.assertIn("test -s /tmp/noctalia-v5.2.1/assets/fonts/noctalia-tabler.ttf", job)
        self.assertIn("test -s /tmp/noctalia-v5.2.1/assets/translations/en.json", job)
        self.assertIn("test -s /tmp/noctalia-v5.2.1/assets/templates/builtin.toml", job)
        # Only native E2E-successful binaries may enter trusted master cache.
        first_pixels = job.index("Test actual native IPC and dual output rendered pixels")
        second_pixels = job.index("Verify real niri + Noctalia dual-output framebuffer")
        noctalia_save = job.index("Save verified Noctalia cache from trusted master only")
        niri_save = job.index("Save verified niri cache from trusted master only")
        self.assertLess(first_pixels, second_pixels)
        self.assertLess(second_pixels, noctalia_save)
        self.assertLess(second_pixels, niri_save)
        self.assertIn("6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4", job)
        self.assertIn("7fd585dd44ed67644977dd9561bb6e8b3837f8f7", job)


# Existing CI runs this named cache-safety module. Include the new read-only
# artifact comparison regressions here without editing ci.yml: changing the
# workflow hash would invalidate all source-pinned native executable caches.
from test_cache_fingerprint_diff import NativeCacheFingerprintDiffTests  # noqa: E402,F401


if __name__ == "__main__":
    unittest.main()
