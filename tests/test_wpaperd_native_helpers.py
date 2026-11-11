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



if __name__ == "__main__":
    unittest.main()
