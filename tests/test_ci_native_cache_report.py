"""Offline selected-native-E2E cache log evidence contract."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_native_cache_report as report  # noqa: E402
import ci_native_cache_metrics as metrics  # noqa: E402


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


    def _metrics_fixture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "warm.log").write_text(
            'echo "Noctalia native cache MISS; compiled pinned source"\n'
            + output("Noctalia", "hit") + "\n"
            + output("niri", "hit") + "\n", encoding="utf-8")
        (root / "cold.log").write_text(
            output("Noctalia", "miss") + "\n" + output("niri", "miss") + "\n",
            encoding="utf-8")
        (root / "failed.log").write_text(
            output("Noctalia", "hit") + "\n", encoding="utf-8")
        return root

    @staticmethod
    def _metrics_job(run_id, log, conclusion="success",
                     started="2026-11-11T00:00:02Z",
                     completed="2026-11-11T00:00:12Z"):
        return {
            "run_id": run_id, "attempt": 1, "job_id": 1000 + run_id,
            "event": "pull_request", "head_sha": "a" * 40,
            "job_name": report.NATIVE_JOB, "conclusion": conclusion,
            "created_at": "2026-11-11T00:00:00Z",
            "started_at": started, "completed_at": completed, "log": log,
        }

    def test_batch_metrics_success_failed_skip_and_nearest_rank(self):
        root = self._metrics_fixture()
        job = self._metrics_job
        records = [
            job(1, "warm.log"),
            job(2, "cold.log", completed="2026-11-11T00:00:42Z"),
            job(3, "failed.log", conclusion="failure"),
            job(4, None, conclusion="skipped", started=None, completed=None),
        ]
        observed = metrics.summarize(records, root)
        noctalia = observed["components"]["noctalia"]
        self.assertEqual(
            (noctalia["verified_hit"], noctalia["verified_miss"],
             noctalia["unverified_hit"], noctalia["skipped"]), (1, 1, 1, 1))
        self.assertEqual(noctalia["verified_hit_rate"], .5)
        self.assertEqual(observed["components"]["niri"]["not_reached"], 1)
        self.assertEqual(observed["successful_job_wall_seconds"],
                         {"n": 2, "p50": 10, "p90": 40})
        self.assertEqual(observed["observed_native_job_execution"], {
            "n": 3, "total_seconds": 60.0, "runner_minutes": 1.0,
        })
        self.assertIn("excludes queue", observed["runner_minutes_scope"])
        self.assertEqual(observed["successful_job_queue_seconds"],
                         {"n": 2, "p50": 2, "p90": 2})
        self.assertIsNone(observed["runs"][-1]["wall_seconds"])
        empty = metrics.summarize([], root)
        self.assertIsNone(empty["components"]["niri"]["verified_hit_rate"])
        self.assertIsNone(empty["successful_job_wall_seconds"]["p50"])
        self.assertEqual(empty["observed_native_job_execution"], {
            "n": 0, "total_seconds": 0, "runner_minutes": 0.0,
        })


    def test_batch_metrics_cohorts_do_not_conflate_master_hits_with_warm_prs(self):
        root = self._metrics_fixture()
        (root / "mixed.log").write_text(
            output("Noctalia", "hit") + "\n" + output("niri", "miss") + "\n",
            encoding="utf-8")
        (root / "incomplete.log").write_text(
            output("Noctalia", "hit") + "\n", encoding="utf-8")
        job = self._metrics_job
        records = [
            {**job(11, "warm.log", completed="2026-11-11T00:00:05Z"),
             "event": "push"},
            job(12, "cold.log", completed="2026-11-11T00:00:42Z"),
            job(13, "mixed.log", completed="2026-11-11T00:00:18Z"),
            job(14, "incomplete.log", completed="2026-11-11T00:00:14Z"),
            job(15, "failed.log", conclusion="failure"),
            job(16, None, conclusion="skipped", started=None, completed=None),
        ]
        result = metrics.summarize(records, root)
        cohorts = result["successful_native_cache_cohorts"]
        self.assertEqual(
            cohorts["all_events"]["both_hit"]["wall_seconds"],
            {"n": 1, "p50": 3, "p90": 3})
        self.assertEqual(
            cohorts["pull_request"]["both_hit"]["wall_seconds"],
            {"n": 0, "p50": None, "p90": None})
        self.assertEqual(
            cohorts["push"]["both_hit"]["queue_seconds"],
            {"n": 1, "p50": 2, "p90": 2})
        self.assertEqual(
            cohorts["pull_request"]["both_miss"]["wall_seconds"]["p50"], 40)
        self.assertEqual(
            cohorts["pull_request"]["mixed"]["wall_seconds"]["p50"], 16)
        self.assertEqual(
            cohorts["pull_request"]["incomplete"]["wall_seconds"]["p50"], 12)
        self.assertEqual(
            [row["cache_cohort"] for row in result["runs"]],
            ["both_hit", "both_miss", "mixed", "incomplete", None, None])
        self.assertEqual(
            sum(cohorts["all_events"][c]["wall_seconds"]["n"]
                for c in metrics.SUCCESS_COHORTS), 4)
        self.assertEqual(result["conclusions"]["failure"], 1)
        self.assertEqual(result["conclusions"]["skipped"], 1)

    def test_batch_metrics_distinct_heads_do_not_count_pr_reruns_twice(self):
        root = self._metrics_fixture()
        job = self._metrics_job
        records = [
            job(41, "warm.log"),
            job(42, "warm.log", completed="2026-11-11T00:00:22Z"),
            {**job(43, "warm.log"), "head_sha": "b" * 40},
            {**job(44, "warm.log"), "event": "push", "head_sha": "b" * 40},
            {**job(45, "failed.log", conclusion="failure"), "head_sha": "c" * 40},
            job(46, None, conclusion="skipped", started=None, completed=None),
        ]
        result = metrics.summarize(records, root)
        cohorts = result["successful_native_cache_cohorts"]
        self.assertEqual(cohorts["pull_request"]["both_hit"]["wall_seconds"]["n"], 3)
        self.assertEqual(cohorts["pull_request"]["both_hit"]["distinct_head_shas"], 2)
        self.assertEqual(cohorts["push"]["both_hit"]["distinct_head_shas"], 1)
        self.assertEqual(cohorts["all_events"]["both_hit"]["distinct_head_shas"], 2)
        self.assertEqual(cohorts["pull_request"]["both_miss"]["distinct_head_shas"], 0)
        self.assertEqual(result["components"]["noctalia"]["verified_hit"], 4)
        # Successful executions remain observable, but two attempts from one
        # PR head never become two independent tested revisions.

    @staticmethod
    def _native_steps(noctalia_build="skipped", niri_build="skipped"):
        def entry(alias, conclusion, start, end):
            return {
                "name": metrics.STEP_NAMES[alias], "conclusion": conclusion,
                "started_at": f"2026-11-11T00:00:{start:02d}Z",
                "completed_at": f"2026-11-11T00:00:{end:02d}Z",
            }

        return [
            entry("noctalia_build", noctalia_build, 3,
                  23 if noctalia_build == "success" else 3),
            entry("noctalia_pixels", "success", 24 if noctalia_build == "success" else 4,
                  25 if noctalia_build == "success" else 5),
            entry("niri_build", niri_build, 26 if noctalia_build == "success" else 6,
                  37 if niri_build == "success" else
                  (26 if noctalia_build == "success" else 6)),
            entry("niri_pixels", "success", 38 if niri_build == "success" else
                  (27 if noctalia_build == "success" else 8),
                  40 if niri_build == "success" else
                  (29 if noctalia_build == "success" else 9)),
        ]

    def test_optional_real_step_times_preserve_old_manifest_and_skip_semantics(self):
        root = self._metrics_fixture()
        warm = {
            **self._metrics_job(71, "warm.log"),
            "steps": self._native_steps(),
        }
        cold = {
            **self._metrics_job(72, "cold.log",
                                completed="2026-11-11T00:00:42Z"),
            "head_sha": "b" * 40,
            "steps": self._native_steps("success", "success"),
        }
        result = metrics.summarize([warm, cold], root)
        step = result["successful_native_step_seconds"]["pull_request"]
        self.assertEqual(
            step["both_hit"]["noctalia_build"],
            {"n": 0, "p50": None, "p90": None},
        )
        self.assertEqual(
            step["both_hit"]["niri_pixels"],
            {"n": 1, "p50": 1, "p90": 1},
        )
        self.assertEqual(
            step["both_miss"]["noctalia_build"],
            {"n": 1, "p50": 20, "p90": 20},
        )
        self.assertEqual(
            step["both_miss"]["niri_build"],
            {"n": 1, "p50": 11, "p90": 11},
        )
        self.assertIsNone(result["runs"][0]["step_seconds"]["noctalia_build"])
        self.assertEqual(result["runs"][1]["step_seconds"]["niri_pixels"], 2)
        self.assertEqual(result["successful_job_wall_seconds"]["n"], 2)
        self.assertIn("skipped cache-hit builds excluded", result["step_timing_scope"])
        legacy = metrics.summarize([self._metrics_job(73, "warm.log")], root)
        self.assertIsNone(legacy["runs"][0]["step_seconds"])
        self.assertEqual(
            legacy["successful_native_step_seconds"]["pull_request"]["both_hit"][
                "noctalia_pixels"]["n"], 0,
        )

    def test_optional_native_step_timestamps_reject_missing_or_forged_evidence(self):
        root = self._metrics_fixture()
        warm = {**self._metrics_job(81, "warm.log"),
                "steps": self._native_steps()}
        bad = []
        missing = self._native_steps()[:-1]
        bad.append((missing, "incomplete_native_step"))
        duplicate = self._native_steps()
        duplicate[1] = dict(duplicate[0])
        bad.append((duplicate, "unknown_or_duplicate"))
        forged_build = self._native_steps()
        forged_build[0] = {**forged_build[0], "conclusion": "success"}
        bad.append((forged_build, "native_cache_step_conflicts"))
        skipped_pixels = self._native_steps()
        skipped_pixels[1] = {**skipped_pixels[1], "conclusion": "skipped"}
        bad.append((skipped_pixels, "native_pixel_step_not_verified"))
        after_job = self._native_steps()
        after_job[-1] = {
            **after_job[-1],
            "completed_at": "2026-11-11T00:00:13Z",
        }
        bad.append((after_job, "native_step_outside_job_clock"))
        wrong_fields = self._native_steps()
        wrong_fields[0] = {**wrong_fields[0], "untrusted": True}
        bad.append((wrong_fields, "invalid_native_step_fields"))
        for steps, reason in bad:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(report.EvidenceError, reason):
                    metrics.summarize([{**warm, "steps": steps}], root)
        with self.assertRaisesRegex(report.EvidenceError,
                                    "step_evidence_requires_successful_job"):
            metrics.summarize([{
                **self._metrics_job(82, "failed.log", conclusion="failure"),
                "steps": self._native_steps(),
            }], root)

    def test_batch_metrics_rejects_wrong_identity_and_unverified_times(self):
        root = self._metrics_fixture()
        job = self._metrics_job
        invalid = [
            ([job(1, None)], "missing_job_log"),
            ([job(1, "warm.log"), job(1, "cold.log")], "duplicate"),
            ([job(1, "warm.log"), {**job(2, "warm.log"), "job_id": 1001}], "duplicate"),
            ([{**job(1, "warm.log"), "job_name": "Rust quality"}], "unexpected_native_job"),
            ([{**job(1, "warm.log"), "run_id": True}], "invalid_or_duplicate"),
            ([{**job(1, "warm.log"), "event": []}], "invalid_run_identity"),
            ([{**job(1, "warm.log"), "conclusion": []}], "invalid_job_conclusion"),
            ([{**job(1, "warm.log"), "unexpected": True}], "fields"),
            ([{**job(1, "warm.log"), "started_at": "2026-11-10T23:59:58Z"}],
             "nonmonotonic"),
            ([{**job(1, "warm.log"), "completed_at": "wrong"}], "invalid_job_timestamp"),
            ([job(1, "warm.log", conclusion="skipped", started=None, completed=None)],
             "skipped_job"),
        ]
        for records, reason in invalid:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(report.EvidenceError, reason):
                    metrics.summarize(records, root)

    def test_batch_metrics_refuses_untrusted_log_paths_and_ambiguous_markers(self):
        root = self._metrics_fixture()
        (root / "ambiguous.log").write_text(
            output("Noctalia", "hit") + "\n" + output("Noctalia", "miss"),
            encoding="utf-8")
        (root / "alias.log").symlink_to(root / "warm.log")
        (root / "alias-dir").symlink_to(root, target_is_directory=True)
        for path in ("../warm.log", "/tmp/unrelated", "alias.log",
                     "alias-dir/warm.log", "ambiguous.log"):
            with self.subTest(path=path):
                with self.assertRaises(report.EvidenceError):
                    metrics.summarize([self._metrics_job(1, path)], root)

    def test_batch_metrics_json_refuses_duplicate_fields_and_nonfinite_values(self):
        root = self._metrics_fixture()
        manifest = root / "untrusted-jobs.json"
        original = json.dumps([self._metrics_job(1, "warm.log")])
        invalid = [
            (original.replace('"conclusion": "success"',
                              '"conclusion": "failure", "conclusion": "success"'),
             "duplicate_manifest_json_field"),
            (original.replace('"log": "warm.log"',
                              '"log": "failed.log", "log": "warm.log"'),
             "duplicate_manifest_json_field"),
            (original.replace('"event": "pull_request"',
                              '"event": {"note": 1, "note": 2}'),
             "duplicate_manifest_json_field"),
            (original.replace('"attempt": 1', '"attempt": NaN'),
             "nonfinite_manifest_number"),
            (original.replace('"attempt": 1', '"attempt": Infinity'),
             "nonfinite_manifest_number"),
        ]
        for raw, reason in invalid:
            with self.subTest(reason=reason, raw=raw):
                manifest.write_text(raw, encoding="utf-8")
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as raised:
                        metrics.main(["--manifest", str(manifest)])
                self.assertEqual(raised.exception.code, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("refused: " + reason, stderr.getvalue())
        manifest.write_text(original, encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(metrics.main(["--manifest", str(manifest)]), 0)
        self.assertEqual(json.loads(stdout.getvalue())["components"]["noctalia"]
                         ["verified_hit"], 1)

    def test_batch_metrics_cli_reads_bounded_offline_manifest(self):
        root = self._metrics_fixture()
        manifest = root / "jobs.json"
        manifest.write_text(json.dumps([self._metrics_job(1, "warm.log")]),
                            encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(metrics.main(["--manifest", str(manifest)]), 0)
        parsed = json.loads(stdout.getvalue())
        self.assertEqual(parsed["components"]["niri"]["verified_hit"], 1)
        manifest.write_bytes(b"x" * (metrics.MAX_MANIFEST_BYTES + 1))
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                metrics.main(["--manifest", str(manifest)])
        self.assertEqual(raised.exception.code, 2)

if __name__ == "__main__":
    unittest.main()
