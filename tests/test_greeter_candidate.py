"""Offline-only greeter candidate checks; never access /etc, /usr or initramfs."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import preview_greeter_candidate as preview  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class GreeterCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.events = self.home / "events"
        self.events.mkdir()
        self.root = self.home / "images"
        self.root.mkdir()
        self.image = self.root / "first.png"
        self.image.write_bytes(solid_png((30, 100, 200)))
        self.event = {
            "schema_version": 1, "producer": "ezwallpaper", "output": "DP-1",
            "epoch": 99, "content_id": self.digest(),
            "image_path": str(self.image),
            "applied_path_observed": True, "visually_verified": False,
        }
        self.write_event()

    def digest(self):
        return "sha256:" + hashlib.sha256(self.image.read_bytes()).hexdigest()

    def write_event(self):
        (self.events / "DP-1.json").write_text(json.dumps(self.event))

    def inspect(self, **overrides):
        return preview.candidate(
            overrides.get("events_dir", self.events),
            overrides.get("output", "DP-1"),
            overrides.get("epoch", 99),
            overrides.get("allowed_source_root", self.root),
            overrides.get("kind", "sddm"),
        )

    def test_candidate_never_modifies_source_or_system(self):
        before = self.image.read_bytes()
        first = self.inspect()
        self.assertEqual(first["status"], "CANDIDATE_ONLY")
        self.assertEqual((first["width"], first["height"]), (32, 32))
        self.assertEqual(first["size_bytes"], len(before))
        self.assertFalse(first["system_import_verified"])
        self.assertFalse(first["writes_performed"])
        self.assertEqual(self.inspect(kind="plymouth")["consumer"], "plymouth")
        self.assertEqual(self.image.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [self.image])

    def test_wrong_digest_epoch_missing_and_corrupt_event_rejected(self):
        self.event["content_id"] = "sha256:" + "0" * 64
        self.write_event()
        with self.assertRaisesRegex(preview.CandidateError, "digest_mismatch"):
            self.inspect()
        self.event["content_id"] = self.digest()
        self.write_event()
        with self.assertRaisesRegex(preview.CandidateError, "invalid_event"):
            self.inspect(epoch=100)
        self.event["applied_path_observed"] = False
        self.write_event()
        with self.assertRaisesRegex(preview.CandidateError, "invalid_event"):
            self.inspect()

    def test_source_outside_allowlist_and_symlinks_rejected(self):
        other = self.home / "external.png"
        other.write_bytes(self.image.read_bytes())
        self.event["image_path"] = str(other)
        self.write_event()
        with self.assertRaisesRegex(preview.CandidateError, "outside_allowed_root"):
            self.inspect()
        link = self.root / "link.png"
        try:
            link.symlink_to(self.image)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unavailable")
        self.event["image_path"] = str(link)
        self.write_event()
        with self.assertRaisesRegex(preview.CandidateError, "unsafe_source"):
            self.inspect()
        alias = self.home / "root-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(preview.CandidateError, "invalid_allowed_root"):
            self.inspect(allowed_source_root=alias)

    def test_oversized_and_malformed_png_rejected(self):
        with self.image.open("r+b") as handle:
            handle.truncate(preview.MAX_IMAGE_BYTES + 1)
        with self.assertRaisesRegex(preview.CandidateError, "unsafe_source"):
            self.inspect()
        self.image.write_bytes(b"hello")
        self.event["content_id"] = self.digest()
        self.write_event()
        with self.assertRaisesRegex(preview.CandidateError, "png_signature_required"):
            self.inspect()
        data = bytearray(solid_png((1, 2, 3)))
        data[29] ^= 1
        self.image.write_bytes(data)
        self.event["content_id"] = self.digest()
        self.write_event()
        with self.assertRaisesRegex(preview.CandidateError, "invalid_png_header"):
            self.inspect()

    def test_cli_refusal_has_no_success_json(self):
        self.event["epoch"] = 50
        self.write_event()
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = preview.main([
                "--events-dir", str(self.events), "--output", "DP-1",
                "--epoch", "99", "--consumer", "plymouth",
                "--allowed-source-root", str(self.root),
            ])
        self.assertEqual((result, stdout.getvalue()), (2, ""))
        self.assertIn("refused:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
