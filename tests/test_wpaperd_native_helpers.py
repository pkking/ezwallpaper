"""Offline negative/positive contracts for native wpaperd E2E helper parsing.

No compositor, daemon, network or desktop side effects.
"""
import contextlib
import io
import json
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent / "e2e" / "sway"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from run import E2EFailure  # noqa: E402
import ci_wpaperd_cache_report as cache_report  # noqa: E402
import ci_wpaperd_cache_metrics as cache_metrics  # noqa: E402
from wpaperd_native import (  # noqa: E402
    decode_ok, initial_paths_match, parse_cli_outcomes, parse_current, parse_inventory,
)


class WpaperdNativeHelperTests(unittest.TestCase):
    def test_exact_two_named_outputs(self):
        reply = {"Ok": {"AllWallpapers": {"entries": [
            ["HEADLESS-1", "/tmp/red.png"], ["HEADLESS-2", "/tmp/blue.png"]
        ]}}}
        self.assertEqual(parse_inventory(decode_ok(json.dumps(reply).encode())), {
            "HEADLESS-1": "/tmp/red.png", "HEADLESS-2": "/tmp/blue.png"
        })

    def test_initial_ipc_inventory_and_readback_must_agree_with_both_outputs(self):
        expected = {
            "HEADLESS-1": Path("/tmp/red.png"),
            "HEADLESS-2": Path("/tmp/blue.png"),
        }
        correct = {name: str(path) for name, path in expected.items()}
        self.assertTrue(initial_paths_match(correct, correct, expected))
        for inventory, current in (
            ({"HEADLESS-1": "/tmp/old.png", "HEADLESS-2": "/tmp/blue.png"},
             correct),
            ({"HEADLESS-1": "/tmp/blue.png", "HEADLESS-2": "/tmp/red.png"},
             correct),
            ({"HEADLESS-1": "/tmp/red.png"}, correct),
            ({**correct, "UNEXPECTED-3": "/tmp/other.png"}, correct),
            (correct, {"HEADLESS-1": "/tmp/red.png",
                       "HEADLESS-2": "/tmp/old.png"}),
            (correct, {"HEADLESS-1": "/tmp/red.png"}),
        ):
            with self.subTest(inventory=inventory, current=current):
                self.assertFalse(initial_paths_match(inventory, current, expected))

    def test_current_wallpaper_is_typed(self):
        self.assertEqual(parse_current(decode_ok(
            b'{"Ok":{"CurrentWallpaper":{"path":"/tmp/red.png"}}}'
        )), "/tmp/red.png")
        for value in [{"Ok": "Ok"}, {"Ok": {"CurrentWallpaper": {"bad": "path"}}},
                      {"Err": {"MonitorNotFound": {"monitor": "x"}}}]:
            with self.assertRaises(E2EFailure):
                parse_current(decode_ok(json.dumps(value).encode()))

    def test_rejects_duplicate_or_unexpected_inventory(self):
        for entries in [
            [["HEADLESS-1", "/a"], ["HEADLESS-1", "/b"]],
            [["HEADLESS-1", "/a"], ["NOT-HEADLESS-2", "/b"]],
            [["HEADLESS-1", "/a"]],
            [["HEADLESS-1", "/a"], ["HEADLESS-2", 42]],
        ]:
            with self.assertRaises(E2EFailure):
                parse_inventory({"AllWallpapers": {"entries": entries}})

    def test_rotation_cli_schema_v1_envelope(self):
        # src/main.rs serializes {schema_version: 1, outputs: Vec<RotationOutcome>}.
        valid = {"schema_version": 1, "outputs": [
            {"output": "HEADLESS-1", "applied_path_observed": True},
            {"output": "HEADLESS-2", "applied_path_observed": False},
        ]}
        parsed = parse_cli_outcomes(valid)
        self.assertTrue(parsed["HEADLESS-1"]["applied_path_observed"])
        self.assertFalse(parsed["HEADLESS-2"]["applied_path_observed"])
        for invalid in [valid["outputs"], {"schema_version": 2, "outputs": valid["outputs"]},
                        {"schema_version": 1, "outputs": valid["outputs"][:1]},
                        {"schema_version": 1, "outputs": [valid["outputs"][0]] * 2},
                        {"schema_version": 1, "outputs": [valid["outputs"][0], {"output": "other"}]}]:
            with self.assertRaises(E2EFailure):
                parse_cli_outcomes(invalid)

    def test_rotation_cli_requires_strict_version_and_boolean_apply_flags(self):
        valid_outputs = [
            {"output": "HEADLESS-1", "applied_path_observed": True},
            {"output": "HEADLESS-2", "applied_path_observed": False},
        ]
        for invalid_version in (True, 1.0, "1", None):
            with self.subTest(schema_version=invalid_version):
                with self.assertRaises(E2EFailure):
                    parse_cli_outcomes({
                        "schema_version": invalid_version, "outputs": valid_outputs
                    })
        for invalid_flag in ("false", "true", 1, 0, None, {}, []):
            for index in (0, 1):
                with self.subTest(flag=invalid_flag, index=index):
                    outputs = [dict(item) for item in valid_outputs]
                    outputs[index]["applied_path_observed"] = invalid_flag
                    with self.assertRaises(E2EFailure):
                        parse_cli_outcomes({
                            "schema_version": 1, "outputs": outputs
                        })
        for index in (0, 1):
            with self.subTest(missing_flag_index=index):
                outputs = [dict(item) for item in valid_outputs]
                del outputs[index]["applied_path_observed"]
                with self.assertRaises(E2EFailure):
                    parse_cli_outcomes({"schema_version": 1, "outputs": outputs})

    def test_malformed_or_remote_error_never_passes(self):
        for data in [b"", b"broken", b"{}", b'{"Err":"bad"}',
                     b'{"Ok":"Ok","Err":"bad"}', b"x" * 65537]:
            with self.assertRaises(E2EFailure):
                decode_ok(data)


class WpaperdNativeCacheReportTests(unittest.TestCase):
    def test_verified_native_cache_outcomes_require_both_successes(self):
        for kind in ("HIT; skipping upstream compilation",
                     "MISS; compiled pinned source"):
            with self.subTest(kind=kind):
                emitted = "2026-11-11T09:00:01.1234567Z wpaperd native cache " + kind
                source = ("2026-11-11T09:00:00.0000000Z \x1b[36;1m"
                          "printf 'wpaperd native cache HIT; skipping upstream compilation'\x1b[0m")
                expected = "verified_hit" if kind.startswith("HIT") else "verified_miss"
                result = cache_report.classify(
                    cache_report.SWAY_JOB, "success", "success", source + "\n" + emitted)
                self.assertEqual(result["cache"], expected)
                failed = cache_report.classify(
                    cache_report.SWAY_JOB, "failure", "success", emitted)
                self.assertEqual(failed["cache"], expected.replace("verified", "unverified"))
                failed_step = cache_report.classify(
                    cache_report.SWAY_JOB, "failure", "failure", emitted)
                self.assertEqual(failed_step["cache"], expected.replace("verified", "unverified"))

    def test_skipped_wpaperd_is_not_a_cache_hit_even_if_sway_succeeds(self):
        self.assertEqual(cache_report.classify(
            cache_report.SWAY_JOB, "success", "skipped", "")["cache"],
            "skipped_or_not_reached")
        self.assertEqual(cache_report.classify(
            cache_report.SWAY_JOB, "failure", "skipped", "")["cache"],
            "skipped_or_not_reached")
        with self.assertRaisesRegex(cache_report.EvidenceError, "skipped_native_step"):
            cache_report.classify(
                cache_report.SWAY_JOB, "success", "skipped",
                "wpaperd native cache HIT; skipping upstream compilation")
        self.assertEqual(cache_report.classify(
            cache_report.SWAY_JOB, "success", "success", "")["cache"], "not_reached")

    def test_ambiguous_wrong_job_or_inconsistent_success_fails_closed(self):
        hit = "wpaperd native cache HIT; skipping upstream compilation"
        miss = "wpaperd native cache MISS; compiled pinned source"
        with self.assertRaisesRegex(cache_report.EvidenceError, "ambiguous"):
            cache_report.classify(
                cache_report.SWAY_JOB, "success", "success", hit + "\n" + miss)
        with self.assertRaisesRegex(cache_report.EvidenceError, "unexpected_sway_job"):
            cache_report.classify("Rust quality", "success", "success", hit)
        with self.assertRaisesRegex(cache_report.EvidenceError, "inconsistent"):
            cache_report.classify(cache_report.SWAY_JOB, "success", "failure", hit)
        with self.assertRaisesRegex(cache_report.EvidenceError, "invalid"):
            cache_report.classify(cache_report.SWAY_JOB, "pending", "success", hit)

    def test_cli_uses_bounded_job_log_and_only_emits_success_on_valid_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            native = Path(root) / "wpaperd.log"
            native.write_text("wpaperd native cache HIT; skipping upstream compilation\n",
                              encoding="utf-8")
            args = ["--conclusion", "success", "--native-step-conclusion", "success",
                    "--log", str(native)]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cache_report.main(args), 0)
            self.assertEqual(json.loads(output.getvalue())["cache"], "verified_hit")
            alias = Path(root) / "alias.log"
            alias.symlink_to(native)
            args[-1] = str(alias)
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as refusal:
                    cache_report.main(args)
            self.assertEqual(refusal.exception.code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("refused:", stderr.getvalue())

    def test_workflow_records_evidence_without_changing_selected_native_gates(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/ci.yml").read_text()
        sway = workflow.split("  sway-visual-e2e:\n", 1)[1].split(
            "  noctalia-sway-visual-e2e:\n", 1)[0]
        hit = "wpaperd native cache HIT; skipping upstream compilation"
        miss = "wpaperd native cache MISS; compiled pinned source"
        self.assertIn(hit, sway)
        self.assertIn(miss, sway)
        self.assertEqual(sway.count(hit), 1)
        self.assertEqual(sway.count(miss), 1)
        self.assertLess(sway.index("python3 scripts/ci_native_cache.py restore --component wpaperd"),
                        sway.index(hit))
        self.assertLess(sway.index("python3 scripts/ci_native_cache.py seal --component wpaperd"),
                        sway.index(miss))
        self.assertLess(sway.index(miss),
                        sway.index("Verify real wpaperd native IPC and two-output rendered pixels"))
        self.assertLess(sway.index("Verify real wpaperd native IPC and two-output rendered pixels"),
                        sway.index("Save verified wpaperd cache from trusted master only"))
        self.assertIn("github.event_name == 'push'", sway)
        self.assertIn("needs.change-scope.outputs.wpaperd == 'true'", sway)
        self.assertNotIn("pull_request_target", workflow)



class WpaperdSelectedNativeCacheMetricsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "cold.log").write_text(
            "2026-11-11T00:00:01.1Z \x1b[36;1m"
            "printf 'wpaperd native cache HIT; skipping upstream compilation'\x1b[0m\n"
            "2026-11-11T00:00:25.1Z wpaperd native cache MISS; compiled pinned source\n",
            encoding="utf-8",
        )
        (self.root / "warm.log").write_text(
            "wpaperd native cache HIT; skipping upstream compilation\n", encoding="utf-8"
        )
        (self.root / "conflict.log").write_text(
            "wpaperd native cache HIT; skipping upstream compilation\n"
            "wpaperd native cache MISS; compiled pinned source\n",
            encoding="utf-8",
        )

    @staticmethod
    def row(run, log, event="pull_request", native_conclusion="success"):
        return {
            "run_id": run, "attempt": 1, "job_id": 1000 + run,
            "event": event, "head_sha": "a" * 40,
            "job_name": cache_report.SWAY_JOB, "conclusion": "success",
            "native_step_conclusion": native_conclusion,
            "build_step_conclusion": "success" if native_conclusion != "skipped" else "skipped",
            "created_at": "2026-11-11T00:00:00Z",
            "started_at": "2026-11-11T00:00:02Z",
            "completed_at": "2026-11-11T00:00:50Z",
            "build_started_at": ("2026-11-11T00:00:05Z" if native_conclusion != "skipped"
                                 else None),
            "build_completed_at": ("2026-11-11T00:00:25Z" if native_conclusion != "skipped"
                                   else None),
            "native_started_at": ("2026-11-11T00:00:27Z" if native_conclusion != "skipped"
                                  else None),
            "native_completed_at": ("2026-11-11T00:00:35Z" if native_conclusion != "skipped"
                                    else None),
            "log": log,
        }

    def test_batch_reports_only_successful_selected_native_pixel_hit_miss(self):
        cold = self.row(1, "cold.log")
        warm = self.row(2, "warm.log", event="push")
        skipped = self.row(3, None, native_conclusion="skipped")
        failed = {**self.row(4, "warm.log", native_conclusion="failure"),
                  "conclusion": "failure"}
        data = cache_metrics.summarize([cold, warm, skipped, failed], self.root)
        self.assertEqual(data["sample_count"], 4)
        self.assertEqual(
            [row["verdict"] for row in data["runs"]],
            ["verified_miss", "verified_hit", "skipped_or_not_reached", "unverified_hit"])
        pr = data["cohorts"]["pull_request"]
        self.assertEqual(pr["statuses"]["verified_miss"], 1)
        self.assertEqual(pr["statuses"]["verified_hit"], 0)
        self.assertEqual(pr["statuses"]["unverified_hit"], 1)
        self.assertEqual(pr["statuses"]["skipped_or_not_reached"], 1)
        self.assertEqual(pr["verified_hit_rate"], 0)
        self.assertEqual(data["cohorts"]["push"]["verified_hit_rate"], 1)
        self.assertEqual(
            data["cohorts"]["all_events"]["latency"]["verified_hit"]["build_seconds"],
            {"n": 1, "p50": 20, "p90": 20})
        self.assertEqual(
            data["cohorts"]["all_events"]["latency"]["verified_miss"]["pixel_seconds"],
            {"n": 1, "p50": 8, "p90": 8})
        self.assertEqual(
            data["cohorts"]["all_events"]["latency"]["verified_hit"]["job_seconds"],
            {"n": 1, "p50": 48, "p90": 48})
        self.assertIsNone(pr["latency"]["verified_hit"]["build_seconds"]["p50"])
        self.assertIsNone(cache_metrics.summarize([], self.root)["cohorts"]
                          ["push"]["verified_hit_rate"])

    def test_batch_distinct_heads_do_not_inflate_from_same_sha_reruns(self):
        records = [
            self.row(41, "warm.log"),
            self.row(42, "warm.log"),
            {**self.row(43, "cold.log"), "head_sha": "b" * 40},
            {**self.row(44, "warm.log", event="push"), "head_sha": "b" * 40},
            {**self.row(45, "warm.log", native_conclusion="failure"),
             "conclusion": "failure", "head_sha": "c" * 40},
            self.row(46, None, native_conclusion="skipped"),
        ]
        result = cache_metrics.summarize(records, self.root)
        pr = result["cohorts"]["pull_request"]
        push = result["cohorts"]["push"]
        all_events = result["cohorts"]["all_events"]

        self.assertEqual(pr["statuses"]["verified_hit"], 2)
        self.assertEqual(pr["distinct_head_shas"], {
            "verified_hit": 1, "verified_miss": 1,
        })
        self.assertEqual(pr["verified_selected_distinct_head_shas"], 2)
        self.assertEqual(push["distinct_head_shas"]["verified_hit"], 1)
        self.assertEqual(push["verified_selected_distinct_head_shas"], 1)
        self.assertEqual(all_events["distinct_head_shas"], {
            "verified_hit": 2, "verified_miss": 1,
        })
        # One SHA can be a hit in one run and a miss in another; do not
        # sum those buckets to invent extra independent source revisions.
        self.assertEqual(all_events["verified_selected_distinct_head_shas"], 2)
        self.assertEqual(pr["statuses"]["unverified_hit"], 1)
        self.assertEqual(pr["statuses"]["skipped_or_not_reached"], 1)
        self.assertEqual(
            pr["independent_head_latency"]["verified_hit"]["job_seconds"]["n"], 1)
        self.assertEqual(
            all_events["independent_head_verdict_counts"],
            {"verified_hit": 2, "verified_miss": 0},
            "latest push of the same head replaces its earlier PR miss")

    def test_independent_head_wpaperd_latency_selects_latest_verified_attempt(self):
        first = self.row(61, "warm.log")
        latest = {
            **self.row(62, "cold.log"),
            "completed_at": "2026-11-11T00:01:02Z",
        }
        other = {
            **self.row(63, "warm.log"), "head_sha": "b" * 40,
        }
        failed = {
            **self.row(64, "warm.log", native_conclusion="failure"),
            "conclusion": "failure", "head_sha": "c" * 40,
        }
        records = [first, other, failed, latest]
        observed = cache_metrics.summarize(records, self.root)
        reversed_observed = cache_metrics.summarize(list(reversed(records)), self.root)
        selected = observed["cohorts"]["pull_request"]
        self.assertEqual(
            selected["independent_head_latency"],
            reversed_observed["cohorts"]["pull_request"]["independent_head_latency"],
        )
        self.assertEqual(selected["independent_head_verdict_counts"],
                         {"verified_hit": 1, "verified_miss": 1})
        self.assertEqual(
            selected["independent_head_latency"]["verified_hit"]["job_seconds"],
            {"n": 1, "p50": 48, "p90": 48})
        self.assertEqual(
            selected["independent_head_latency"]["verified_miss"]["job_seconds"],
            {"n": 1, "p50": 60, "p90": 60})
        self.assertEqual(
            selected["latency"]["verified_hit"]["job_seconds"]["n"], 2,
            "legacy job-level cohort remains unchanged")
        self.assertEqual(
            selected["independent_head_latency"]["verified_miss"]["pixel_seconds"],
            {"n": 1, "p50": 8, "p90": 8})
        self.assertIn("Latest successful", observed["independent_head_selection"])

    def test_batch_retains_failed_build_when_native_pixels_never_ran(self):
        # Real selected build failures skip the conditional native pixel step;
        # they are neither cache MISSES nor unselected successful Sway jobs.
        (self.root / "failed-build.log").write_text(
            "2026-11-11T00:00:10Z pinned upstream compiler failed\n",
            encoding="utf-8")
        failed = {
            **self.row(5, "failed-build.log", native_conclusion="skipped"),
            "conclusion": "failure",
            "build_step_conclusion": "failure",
            "build_started_at": "2026-11-11T00:00:05Z",
            "build_completed_at": "2026-11-11T00:00:25Z",
        }
        result = cache_metrics.summarize([failed], self.root)
        entry = result["runs"][0]
        self.assertEqual(entry["verdict"], "build_failed_before_native_pixels")
        self.assertEqual(entry["build_seconds"], 20)
        self.assertIsNone(entry["pixel_seconds"])
        self.assertEqual(
            result["cohorts"]["pull_request"]["statuses"]
            ["build_failed_before_native_pixels"], 1)
        self.assertEqual(result["cohorts"]["pull_request"]
                         ["verified_selected_observations"], 0)
        self.assertIsNone(result["cohorts"]["pull_request"]["verified_hit_rate"])

        failures = [
            ({**failed, "conclusion": "success"}, "inconsistent_skipped_native_step"),
            ({**failed, "build_step_conclusion": "cancelled"},
             "inconsistent_skipped_native_step"),
            ({**failed, "log": None}, "missing_wpaperd_job_log"),
            ({**failed, "build_started_at": None}, "missing_native_step_timestamps"),
            ({**failed, "native_started_at": "2026-11-11T00:00:26Z"},
             "skipped_native_step_has_timestamps"),
            ({**failed, "log": "warm.log"}, "cache_marker_for_skipped_native_step"),
        ]
        for record, reason in failures:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(cache_report.EvidenceError, reason):
                    cache_metrics.summarize([record], self.root)
        unselected = {
            **self.row(6, None, native_conclusion="skipped"),
            "build_started_at": "2026-11-11T00:00:05Z",
        }
        with self.assertRaisesRegex(cache_report.EvidenceError,
                                    "skipped_native_step_has_timestamps"):
            cache_metrics.summarize([unselected], self.root)

    def test_batch_refuses_ambiguous_wrong_or_out_of_order_evidence(self):
        original = self.row(1, "warm.log")
        failures = [
            ([original, original], "duplicate"),
            ([original, {**self.row(2, "warm.log"), "job_id": 1001}], "duplicate"),
            ([{**original, "run_id": True}], "identity"),
            ([{**original, "event": "workflow_dispatch"}], "run_identity"),
            ([{**original, "job_name": "Rust quality"}], "unexpected_sway_job"),
            ([{**original, "native_step_conclusion": "skipped"}], "skipped_native"),
            ([{**original, "build_step_conclusion": "skipped"}], "skipped_native_step"),
            ([{**original, "build_step_conclusion": "skipped",
               "build_started_at": None, "build_completed_at": None}], "native_pixels"),
            ([{**original, "native_started_at": "2026-11-11T00:00:24Z"}], "pixel_test"),
            ([{**original, "native_completed_at": "2026-11-11T00:00:55Z"}], "outside_job"),
            ([{**original, "created_at": "2026-11-11T00:00:03Z"}], "nonmonotonic"),
            ([{**original, "log": "../warm.log"}], "unsafe"),
            ([{**original, "log": "conflict.log"}], "ambiguous"),
            ([{**original, "log": None}], "missing_wpaperd"),
            ([{**original, "unrecognized": True}], "fields"),
        ]
        for rows, reason in failures:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(cache_report.EvidenceError, reason):
                    cache_metrics.summarize(rows, self.root)
        (self.root / "linked.log").symlink_to(self.root / "warm.log")
        with self.assertRaises(cache_report.EvidenceError):
            cache_metrics.summarize([self.row(1, "linked.log")], self.root)

    def test_batch_cli_rejects_duplicate_json_members_and_nonfinite_literals(self):
        file = self.root / "manifest.json"
        original = json.dumps([self.row(1, "warm.log")])
        file.write_text(original, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cache_metrics.main(["--manifest", str(file)]), 0)
        self.assertEqual(json.loads(out.getvalue())["cohorts"]["pull_request"]
                         ["statuses"]["verified_hit"], 1)
        invalid = (
            original.replace('"conclusion": "success"',
                             '"conclusion": "failure", "conclusion": "success"'),
            original.replace('"job_id": 1001', '"job_id": NaN'),
            "[] trailing data",
        )
        for raw in invalid:
            with self.subTest(raw=raw[:60]):
                file.write_text(raw, encoding="utf-8")
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as refusal:
                        cache_metrics.main(["--manifest", str(file)])
                self.assertEqual(refusal.exception.code, 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("refused:", stderr.getvalue())



if __name__ == "__main__":
    unittest.main()
