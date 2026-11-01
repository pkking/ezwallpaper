"""Offline root-policy preflight fixtures; no privileged filesystem writes."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import preview_root_greeter_policy as policy  # noqa: E402


class PolicyPreflightTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.config_dir = self.root / "etc" / "ezwallpaper"
        self.config_dir.mkdir(parents=True)
        self.policy = self.config_dir / "greeter-import.json"
        self.data = {
            "schema_version": 1,
            "source_root": "/var/lib/ezwallpaper/greeter-inbox",
            "targets": {
                "sddm": "/usr/share/sddm/themes/example/background.png",
                "plymouth": "/usr/share/plymouth/themes/example/splash.png",
            },
        }
        self.write()

    def write(self):
        self.policy.write_text(json.dumps(self.data))
        self.policy.chmod(0o600)

    def inspect(self, kind="sddm", path=None):
        return policy.read_trusted_policy(
            self.policy if path is None else path, kind,
            trust_root=self.root, expected_uid=os.geteuid(),
        )

    def test_read_only_root_owned_contract_and_two_consumers(self):
        out = self.inspect()
        self.assertEqual(out["consumer"], "sddm")
        self.assertEqual(out["source_root"], policy.SOURCE_ROOT)
        self.assertEqual(out["status"], "READ_ONLY_POLICY_PREFLIGHT")
        self.assertEqual(out["approved_target"], self.data["targets"]["sddm"])
        self.assertFalse(out["writes_performed"])
        self.assertFalse(out["privileged_import_implemented"])
        self.assertEqual(self.inspect("plymouth")["consumer"], "plymouth")
        self.assertEqual(self.policy.read_text(), json.dumps(self.data))

    def test_path_traversal_and_unapproved_destination_refused(self):
        bad = (
            "/etc/passwd", "/usr/share/sddm/themes/../../outside.png",
            "/usr/share/plymouth/themes/other.png",
            "/usr/share/sddm/themes//background.png",
            "/usr/share/sddm/themes/example/../escape.png",
            "/usr/share/sddm/themes/example/nope.txt",
            "relative/filename.png",
        )
        for value in bad:
            with self.subTest(path=value):
                self.data["targets"]["sddm"] = value
                self.write()
                with self.assertRaises(policy.PolicyError):
                    self.inspect()
        self.data["targets"]["sddm"] = "/usr/share/sddm/themes/example/background.png"
        self.write()
        with self.assertRaisesRegex(policy.PolicyError, "invalid_consumer"):
            self.inspect("shell")

    def test_strict_schema_rejects_unknown_fields_and_duplicate_keys(self):
        for modified in ({"schema_version": True}, {"schema_version": 2},
                         {"source_root": "/home/user/wallpapers"},
                         {"unknown": "input"}, {"targets": {}}):
            with self.subTest(modified=modified):
                invalid = {**self.data, **modified}
                with self.assertRaises(policy.PolicyError):
                    policy.validate_policy(json.dumps(invalid).encode(), "sddm")
        raw = (b'{"schema_version":1,"schema_version":1,'
               b'"source_root":"/var/lib/ezwallpaper/greeter-inbox","targets":{}}')
        with self.assertRaisesRegex(policy.PolicyError, "duplicate_policy_key"):
            policy.validate_policy(raw, "sddm")

    def test_group_writable_policy_or_parent_refused(self):
        self.policy.chmod(0o666)
        with self.assertRaisesRegex(policy.PolicyError, "untrusted_policy_file"):
            self.inspect()
        self.policy.chmod(0o600)
        self.config_dir.chmod(0o777)
        with self.assertRaisesRegex(policy.PolicyError, "untrusted_policy_parent"):
            self.inspect()

    def test_policy_file_or_intermediate_directory_symlink_refused(self):
        other = self.root / "original.json"
        other.write_text(json.dumps(self.data))
        self.policy.unlink()
        try:
            self.policy.symlink_to(other)
        except (NotImplementedError, OSError):
            self.skipTest("no symlink support")
        with self.assertRaisesRegex(policy.PolicyError, "cannot_read_trusted_policy"):
            self.inspect()
        self.policy.unlink()
        self.write()
        link = self.root / "alias"
        link.symlink_to(self.config_dir, target_is_directory=True)
        with self.assertRaisesRegex(policy.PolicyError, "cannot_read_trusted_policy"):
            self.inspect(path=link / self.policy.name)

    def test_oversized_file_and_unsafe_root_path_refused(self):
        self.policy.write_bytes(b"x" * (policy.POLICY_BYTES_MAX + 1))
        with self.assertRaisesRegex(policy.PolicyError, "untrusted_policy_file"):
            self.inspect()
        self.write()
        with self.assertRaisesRegex(policy.PolicyError, "cannot_read_trusted_policy"):
            self.inspect(path=Path("/outside/greeter-import.json"))


if __name__ == "__main__":
    unittest.main()
