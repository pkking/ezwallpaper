"""Offline tests for native CI cache provenance comparison; no desktop or network."""
from __future__ import annotations

import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compare_native_cache_fingerprints as diff  # noqa: E402


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sample_toolchain(version="12.2.0"):
    return (
        f"amd64\nc++ (Debian {version}) {version}\n"
        "meson 1.10.0\n1.47\n"
        + "a" * 64 + "  .github/workflows/ci.yml\n"
    ).encode()


def make_evidence(directory: Path, packages: bytes, toolchain: bytes,
                  component="noctalia") -> None:
    directory.mkdir()
    (directory / "installed-packages.txt").write_bytes(packages)
    (directory / "toolchain-and-workflow.txt").write_bytes(toolchain)
    artifact = (
        "noctalia-sway-e2e" if component == "noctalia" else "niri-noctalia-e2e"
    )
    source = f"artifacts/{artifact}/cache-fingerprint"
    checksums = (
        f"{digest(packages)}  {source}/installed-packages.txt\n"
        f"{digest(toolchain)}  {source}/toolchain-and-workflow.txt\n"
        f"{digest(packages + toolchain)}  /tmp/ezw-{component}-build-fingerprint\n"
    )
    (directory / "sha256.txt").write_text(checksums, encoding="ascii")


class NativeCacheFingerprintDiffTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.before = self.root / "before"
        self.after = self.root / "after"
        self.packages = b"libfoo:amd64=1.2-3\nmeson=1.10.0\n"
        self.toolchain = sample_toolchain()

    def test_matching_artifacts_report_no_drift(self):
        make_evidence(self.before, self.packages, self.toolchain)
        make_evidence(self.after, self.packages, self.toolchain)
        result = diff.compare(
            diff.load_evidence(self.before), diff.load_evidence(self.after)
        )
        self.assertFalse(result["fingerprint_changed"])
        self.assertEqual(result["packages"],
                         {"added": {}, "removed": {}, "version_changed": {}})
        self.assertFalse(result["toolchain_and_workflow"]["changed"])
        self.assertEqual(result["toolchain_and_workflow"]["diff"], [])

    def test_added_removed_upgraded_packages_are_separate(self):
        new_packages = b"extra=3.0\nlibfoo:amd64=2.0-1\n"
        make_evidence(self.before, self.packages, self.toolchain)
        make_evidence(self.after, new_packages, self.toolchain)
        result = diff.compare(
            diff.load_evidence(self.before), diff.load_evidence(self.after)
        )
        self.assertTrue(result["fingerprint_changed"])
        self.assertEqual(result["packages"]["added"], {"extra": "3.0"})
        self.assertEqual(result["packages"]["removed"], {"meson": "1.10.0"})
        self.assertEqual(
            result["packages"]["version_changed"],
            {"libfoo:amd64": {"before": "1.2-3", "after": "2.0-1"}},
        )
        self.assertFalse(result["toolchain_and_workflow"]["changed"])
        self.assertNotEqual(
            result["fingerprint_sha256"]["before"],
            result["fingerprint_sha256"]["after"],
        )

    def test_compiler_drift_reports_exact_changed_lines(self):
        make_evidence(self.before, self.packages, self.toolchain)
        make_evidence(self.after, self.packages, sample_toolchain("13.1.0"))
        result = diff.compare(
            diff.load_evidence(self.before), diff.load_evidence(self.after)
        )
        self.assertTrue(result["fingerprint_changed"])
        self.assertTrue(result["toolchain_and_workflow"]["changed"])
        self.assertIn("-c++ (Debian 12.2.0) 12.2.0",
                      result["toolchain_and_workflow"]["diff"])
        self.assertIn("+c++ (Debian 13.1.0) 13.1.0",
                      result["toolchain_and_workflow"]["diff"])
        self.assertEqual(result["packages"]["version_changed"], {})

    def test_checksum_or_unexpected_sha_path_fails_closed(self):
        for mutation in ("alter_package", "alter_digest", "alter_path"):
            with self.subTest(mutation=mutation):
                folder = self.root / mutation
                make_evidence(folder, self.packages, self.toolchain)
                if mutation == "alter_package":
                    (folder / "installed-packages.txt").write_bytes(
                        b"libfoo:amd64=9.9\nmeson=1.10.0\n"
                    )
                else:
                    sha_file = folder / "sha256.txt"
                    sha = sha_file.read_text()
                    if mutation == "alter_digest":
                        sha = "0" + sha[1:]
                    else:
                        sha = sha.replace("/installed-packages.txt",
                                          "/wrong.txt")
                    sha_file.write_text(sha)
                with self.assertRaises(diff.FingerprintError):
                    diff.load_evidence(folder)

    def test_duplicate_or_malformed_package_inventory_fails_even_with_matching_sha(self):
        invalid = (
            b"meson=1.0\nmeson=1.1\n",
            b"meson\n",
            b"meson=\n",
            b"../other=1\n",
            b"meson=1\nbad",
            b"\xff\n",
        )
        for number, packages in enumerate(invalid):
            with self.subTest(number=number):
                folder = self.root / f"invalid-{number}"
                make_evidence(folder, packages, self.toolchain)
                with self.assertRaises(diff.FingerprintError):
                    diff.load_evidence(folder)

    def test_symlink_missing_and_oversize_evidence_are_rejected(self):
        make_evidence(self.before, self.packages, self.toolchain)
        source = self.before / "installed-packages.txt"
        alias = self.root / "alias"
        alias.symlink_to(self.before, target_is_directory=True)
        with self.assertRaisesRegex(diff.FingerprintError,
                                    "invalid_evidence_directory"):
            diff.load_evidence(alias)
        source.unlink()
        source.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(diff.FingerprintError,
                                    "invalid_evidence_file"):
            diff.load_evidence(self.before)
        source.unlink()
        source.write_bytes(b"x" * (diff.MAX_EVIDENCE_BYTES + 1))
        with self.assertRaisesRegex(diff.FingerprintError,
                                    "invalid_evidence_file"):
            diff.load_evidence(self.before)

    def test_non_utf8_toolchain_does_not_report_plausible_drift(self):
        make_evidence(self.before, self.packages, b"\xff\n")
        with self.assertRaisesRegex(diff.FingerprintError,
                                    "invalid_toolchain_encoding"):
            diff.load_evidence(self.before)

    def test_cli_refusal_does_not_print_success_json(self):
        make_evidence(self.before, self.packages, self.toolchain)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = diff.main([str(self.before), str(self.after)])
        self.assertEqual(result, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("refused: missing_evidence_directory", err.getvalue())


if __name__ == "__main__":
    unittest.main()
