"""Offline-only memory transaction fault injection; no host files modified."""
from __future__ import annotations

import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rehearse_greeter_transaction as txn  # noqa: E402
from verify_noctalia_live import solid_png  # noqa: E402


class ImportTransactionRehearsalTests(unittest.TestCase):
    def setUp(self):
        self.old = solid_png((10, 20, 30))
        self.new = solid_png((40, 50, 60))
        self.old_id, self.new_id = txn.sha(self.old), txn.sha(self.new)

    def test_new_install_and_replacement_are_simulated_only(self):
        for old, old_id in ((None, None), (self.old, self.old_id)):
            with self.subTest(existing=old is not None):
                result = txn.rehearse(old, self.new, old_id, self.new_id)
                self.assertEqual(result["status"], "SIMULATED_COMMIT")
                self.assertEqual(result["final_content_id"], self.new_id)
                self.assertFalse(result["writes_performed"])
                self.assertFalse(result["privileged_import_implemented"])
                self.assertFalse(result["physical_result_verified"])

    def test_idempotent_same_content_has_no_backup(self):
        result = txn.rehearse(self.new, self.new, self.new_id, self.new_id)
        self.assertEqual(result["status"], "SIMULATED_NOOP")
        self.assertFalse(result["backup_verified"])

    def test_every_crash_point_recovers_exact_previous_image(self):
        for previous, previous_id in ((None, None), (self.old, self.old_id)):
            for fault in txn.FAULTS:
                with self.subTest(previous=previous_id, fault=fault):
                    result = txn.rehearse(previous, self.new, previous_id,
                                          self.new_id, fault_after=fault)
                    self.assertEqual(result["status"], "RECOVERED_PREVIOUS_TARGET")
                    self.assertEqual(result["final_content_id"], previous_id)
                    self.assertFalse(result["pending_after_recovery"])
                    self.assertFalse(result["writes_performed"])

    def test_wrong_or_malformed_content_ids_fail_before_transaction(self):
        for next_id in (self.old_id, "invalid", "sha256:"+"A"*64, ""):
            with self.subTest(next_id=next_id), self.assertRaises(txn.RehearsalError):
                txn.rehearse(self.old, self.new, self.old_id, next_id)
        with self.assertRaisesRegex(txn.RehearsalError, "input_digest_mismatch"):
            txn.rehearse(self.old, self.new, self.new_id, self.new_id)
        with self.assertRaisesRegex(txn.RehearsalError, "unknown_fault_point"):
            txn.rehearse(self.old, self.new, self.old_id, self.new_id,
                         fault_after="overwrite_backup")

    def test_corrupted_png_cannot_become_candidate(self):
        raw = bytearray(self.new)
        raw[-5] ^= 3
        candidate = bytes(raw)
        with self.assertRaisesRegex(txn.RehearsalError, "invalid_candidate_png"):
            txn.rehearse(self.old, candidate, self.old_id, txn.sha(candidate))

    def test_recovery_refuses_tampered_target_or_missing_backup(self):
        state = txn.MemoryFiles(target=b"unrecognized", backup=self.old,
                                pending=(self.old_id, self.new_id))
        with self.assertRaisesRegex(txn.RehearsalError, "unexpected_target_state"):
            txn.recover_model(state)
        self.assertIsNotNone(state.pending)
        state.target = self.new
        state.backup = b"modified"
        with self.assertRaisesRegex(txn.RehearsalError, "backup_unavailable"):
            txn.recover_model(state)
        self.assertEqual(state.target, self.new)

    def test_cli_is_read_only_and_root_execution_forbidden(self):
        with tempfile.TemporaryDirectory() as home:
            path = Path(home) / "next.png"
            path.write_bytes(self.new)
            before = path.read_bytes()
            args = ["--candidate-file", str(path),
                    "--candidate-content-id", self.new_id, "--fault-after", "after_publish"]
            output = io.StringIO()
            with patch.object(txn.os, "geteuid", return_value=1000), \
                 contextlib.redirect_stdout(output):
                status = txn.main(args)
            self.assertEqual(status, 0)
            self.assertIn("RECOVERED_PREVIOUS_TARGET", output.getvalue())
            self.assertEqual(path.read_bytes(), before)
            with patch.object(txn.os, "geteuid", return_value=0), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(txn.main(args), 2)

    def test_symlinked_source_not_followed(self):
        with tempfile.TemporaryDirectory() as home:
            original = Path(home) / "real.png"
            original.write_bytes(self.new)
            link = Path(home) / "linked.png"
            try:
                link.symlink_to(original)
            except (OSError, NotImplementedError):
                self.skipTest("symlink unavailable")
            with self.assertRaises(txn.RehearsalError):
                txn.read_bounded_user_file(link)


if __name__ == "__main__":
    unittest.main()
