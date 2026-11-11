"""Offline selected-native-E2E cache log evidence contract."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_native_cache_report as report  # noqa: E402


def output(component: str, decision: str) -> str:
    if decision == "hit":
        return component + " native cache HIT; skipping upstream compilation"
    return component + " native cache MISS; compiled pinned source"


class NativeCacheLogClassifierTests(unittest.TestCase):
    def test_successful_actual_native_job_distinguishes_warm_and_cold(self):
        for expected in ("hit", "miss"):
            with self.subTest(expected=expected):
                body = "\n".join([
                    "2026-11-11T02:44:44.6288957Z \x1b[36;1m"
                    'echo "Noctalia native cache HIT; skipping upstream compilation"\x1b[0m',
                    "2026-11-11T02:44:44.6288957Z \x1b[36;1m"
                    'echo "Noctalia native cache MISS; compiled pinned source"\x1b[0m',
                    "2026-11-11T02:44:44.7890514Z " + output("Noctalia", expected),
                    "2026-11-11T02:49:34.3722219Z " + output("niri", expected),
                ])
                result = report.classify(report.NATIVE_JOB, "success", body)
                self.assertEqual(result["components"], {
                    "noctalia": "verified_" + expected,
                    "niri": "verified_" + expected,
                })

    def test_failed_hit_never_counts_as_verified_native_pixels(self):
        log = output("Noctalia", "hit") + "\n"
        failed = report.classify(report.NATIVE_JOB, "failure", log)
        self.assertEqual(failed["components"], {
            "noctalia": "unverified_hit", "niri": "not_reached",
        })
        cancelled = report.classify(report.NATIVE_JOB, "cancelled", log)
        self.assertEqual(cancelled["components"]["noctalia"], "unverified_hit")
        skipped = report.classify(report.NATIVE_JOB, "skipped", log)
        self.assertEqual(skipped["components"], {
            "noctalia": "skipped", "niri": "skipped",
        })

    def test_success_without_explicit_marker_does_not_invent_hit(self):
        log = ('echo "Noctalia native cache HIT; skipping upstream compilation"\n'
               'echo "Noctalia native cache MISS; compiled pinned source"\n'
               "Cache hit for: unrelated-rust-build-cache\n")
        result = report.classify(report.NATIVE_JOB, "success", log)
        self.assertEqual(result["components"], {
            "noctalia": "not_reached", "niri": "not_reached",
        })

    def test_conflicting_duplicate_or_wrong_job_refused(self):
        with self.assertRaisesRegex(report.EvidenceError, "ambiguous"):
            report.classify(report.NATIVE_JOB, "success",
                            output("Noctalia", "hit") + "\n" +
                            output("Noctalia", "miss"))
        with self.assertRaisesRegex(report.EvidenceError, "unexpected_native_job"):
            report.classify("Rust quality", "success", output("Noctalia", "hit"))
        with self.assertRaisesRegex(report.EvidenceError, "invalid_job_conclusion"):
            report.classify(report.NATIVE_JOB, "pending", "")

    def test_read_log_bounds_symlink_utf8_and_cli_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            original = Path(root) / "job.log"
            original.write_text(output("Noctalia", "hit") + "\n", encoding="utf-8")
            self.assertIn("native cache HIT", report.read_log(original))
            alias = Path(root) / "alias.log"
            alias.symlink_to(original)
            with self.assertRaises(report.EvidenceError):
                report.read_log(alias)
            original.write_bytes(b"\xff")
            with self.assertRaisesRegex(report.EvidenceError, "utf8"):
                report.read_log(original)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            result = report.main(["--conclusion", "skipped"])
        self.assertEqual(result, 0)
        self.assertIn('"noctalia": "skipped"', out.getvalue())


if __name__ == "__main__":
    unittest.main()
