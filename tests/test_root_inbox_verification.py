"""Offline root-owned inbox verification: never touches actual /var or /usr."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import verify_root_greeter_inbox as inbox  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class TrustedInboxTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.inbox = self.root / "var/lib/ezwallpaper/greeter-inbox"
        self.inbox.mkdir(parents=True)
        self.target_parent = self.root / "usr/share/sddm/themes/demo"
        self.target_parent.mkdir(parents=True)
        self.payload = solid_png((25, 35, 45))
        self.sha = hashlib.sha256(self.payload).hexdigest()
        self.digest = "sha256:" + self.sha
        self.file = self.inbox / (self.sha + ".png")
        self.file.write_bytes(self.payload)
        self.file.chmod(0o600)
        self.policy = {
            "schema_version": 1, "status": "READ_ONLY_POLICY_PREFLIGHT",
            "source_root": "/var/lib/ezwallpaper/greeter-inbox",
            "consumer": "sddm",
            "approved_target": "/usr/share/sddm/themes/demo/background.png",
        }

    def verify(self, digest=None):
        return inbox.inspect_inbox(
            self.policy, self.digest if digest is None else digest,
            trust_root=self.root, expected_uid=os.geteuid(),
        )

    def test_read_only_composed_source_and_target_preflight(self):
        result = self.verify()
        self.assertEqual(result["status"], "READ_ONLY_INBOX_VERIFIED")
        self.assertEqual(result["content_id"], self.digest)
        self.assertEqual(result["size_bytes"], len(self.payload))
        self.assertEqual((result["width"], result["height"]), (32, 32))
        self.assertFalse(result["target_exists"])
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["privileged_import_implemented"])
        self.assertFalse(result["image_fully_decoded"])
        self.assertEqual(self.file.read_bytes(), self.payload)

    def test_wrong_digest_or_mutated_image_fails_closed(self):
        with self.assertRaisesRegex(inbox.InboxError, "cannot_open_trusted_inbox"):
            self.verify("sha256:" + "0" * 64)
        self.file.write_bytes(solid_png((1, 2, 3)))
        with self.assertRaisesRegex(inbox.InboxError, "content_id_mismatch"):
            self.verify()

    def test_bad_digest_format_and_policy_rejected_before_open(self):
        for value in ("", self.sha, "sha256:../outside", "sha256:" + "A"*64,
                      "sha256:"+"a"*64+"x"):
            with self.subTest(value=value), self.assertRaisesRegex(
                    inbox.InboxError, "invalid_content_id_or_policy"):
                self.verify(value)
        self.policy["source_root"] = "/home/user/inbox"
        with self.assertRaisesRegex(inbox.InboxError, "invalid_content_id_or_policy"):
            self.verify()

    def test_symbolic_links_to_source_parent_or_leaf_refused(self):
        outside = self.root / "untrusted"
        outside.mkdir()
        alt = outside / (self.sha + ".png")
        alt.write_bytes(self.payload)
        self.file.unlink()
        try:
            self.file.symlink_to(alt)
        except (NotImplementedError, OSError):
            self.skipTest("symlinks unsupported")
        with self.assertRaisesRegex(inbox.InboxError, "cannot_open_trusted_inbox"):
            self.verify()
        self.file.unlink()
        self.file.write_bytes(self.payload)
        self.file.chmod(0o600)
        old = self.root / "var/lib/ezwallpaper/greeter-inbox-old"
        self.inbox.rename(old)
        self.inbox.symlink_to(old, target_is_directory=True)
        with self.assertRaisesRegex(inbox.InboxError, "cannot_open_trusted_inbox"):
            self.verify()

    def test_mutable_parent_or_unsafe_leaf_refused(self):
        self.inbox.chmod(0o777)
        with self.assertRaisesRegex(inbox.InboxError, "unsafe_inbox_parent"):
            self.verify()
        self.inbox.chmod(0o755)
        self.file.chmod(0o666)
        with self.assertRaisesRegex(inbox.InboxError, "unsafe_inbox_image"):
            self.verify()
        self.file.chmod(0o600)
        other = self.root / "hardlink.png"
        os.link(self.file, other)
        with self.assertRaisesRegex(inbox.InboxError, "unsafe_inbox_image"):
            self.verify()

    def test_invalid_png_after_matching_digest_and_oversize(self):
        self.file.unlink()
        raw = b"fake, not png"
        badsha = hashlib.sha256(raw).hexdigest()
        bad = self.inbox / (badsha + ".png")
        bad.write_bytes(raw)
        bad.chmod(0o600)
        with self.assertRaisesRegex(inbox.InboxError, "invalid_png_header"):
            self.verify("sha256:" + badsha)
        bad.unlink()
        with self.file.open("wb") as f:
            f.truncate(inbox.MAX_IMAGE_BYTES + 1)
        with self.assertRaisesRegex(inbox.InboxError, "unsafe_inbox_image"):
            self.verify()

    def test_unsafe_target_fails_before_image_trust_claim(self):
        self.target_parent.chmod(0o777)
        with self.assertRaisesRegex(inbox.InboxError, "unsafe_target"):
            self.verify()
        self.target_parent.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
