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

    def test_workflow_has_read_only_pr_and_master_only_save_and_pixel_e2e(self):
        ci = (Path(__file__).resolve().parents[1] /
              ".github/workflows/ci.yml").read_text()
        job = ci.split("  noctalia-sway-visual-e2e:\n", 1)[1].split(
            "\n  platform-tests:", 1)[0]
        self.assertIn("cache-mode: $" + "{{ github.event_name == 'push'", job)
        self.assertIn("actions/cache/restore@v4", job)
        self.assertIn("actions/cache/save@v4", job)
        self.assertIn("github.ref == 'refs/heads/master'", job)
        self.assertIn("tests/e2e/sway/noctalia_v5.py", job)
        self.assertIn("tests/e2e/sway/niri_noctalia.py", job)
        self.assertIn("6ef43e2bf2f3d5b4205ec72a72e34a2ab76ce3b4", job)
        self.assertIn("7fd585dd44ed67644977dd9561bb6e8b3837f8f7", job)


if __name__ == "__main__":
    unittest.main()
