"""Read-only smoke-test safeguards, using mocked inference and local fixtures.

No model is downloaded, no server is started, and no network is contacted.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import smoke_translation as smoke


PUBLIC_PUSH = {
    "GITHUB_ACTIONS": "true",
    "TRANSLATION_REPOSITORY_PUBLIC": "true",
    "GITHUB_EVENT_NAME": "push",
}
SOURCE_DATE = "2026-10-08"


class ReadOnlySmokeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "checkout"
        self.repo.mkdir()
        self.runner_temp = self.root / "runner-temp"
        self.runner_temp.mkdir()
        (self.repo / "README.md").write_bytes(b"Original Chinese README\r\n")
        self.source_file = self.repo / "daily" / "2026" / f"{SOURCE_DATE}.md"
        self.source_file.parent.mkdir(parents=True)
        self.source_file.write_text("Fixture Chinese source text\n", encoding="utf-8")
        self.source = SimpleNamespace(
            source_hash="a" * 64,
            items=[{"id": "first"}, {"id": "second"}],
            units={
                "lead:title": "测试标题",
                "lead:summary": "测试摘要1",
                "item:first:summary": "第一项摘要2",
                "item:second:summary": "第二项摘要3",
            },
        )
        self.process, self.log = mock.Mock(), mock.Mock()
        self.client = mock.Mock()
        self.client.local_requests = 0

        def translate(units, language):
            self.client.local_requests += 1
            key = next(iter(units))
            suffix = "" if key == "lead:title" else {"lead:summary": "1", "item:first:summary": "2", "item:second:summary": "3"}[key]
            return {key: (("Example " if language == "en" else "例 ") + suffix).rstrip()}

        self.client.translate_batch.side_effect = translate
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(os.environ, {**PUBLIC_PUSH, "RUNNER_TEMP": str(self.runner_temp)}, clear=True).start()
        mock.patch.object(smoke.sys, "platform", "linux").start()
        self.discover = mock.patch.object(smoke.core, "discover_sources", return_value={SOURCE_DATE: self.source_file}).start()
        self.parse = mock.patch.object(smoke.core, "parse_daily", return_value=self.source).start()
        self.start = mock.patch.object(smoke.workflow, "start_server", return_value=(self.process, self.log)).start()
        self.stop = mock.patch.object(smoke.workflow, "stop_server").start()
        self.translator = mock.patch.object(smoke.core, "Translator", return_value=self.client).start()
        mock.patch.object(smoke.workflow.request, "urlopen", side_effect=AssertionError("Live HTTP forbidden in smoke unit tests")).start()
        self.before = self.snapshot()

    def snapshot(self):
        return {path.relative_to(self.repo).as_posix(): path.read_bytes() for path in self.repo.rglob("*") if path.is_file()}

    @staticmethod
    def result():
        return {"mode": "read-only-smoke", "cases": [], "local_requests": 0, "valid": False}

    def test_private_non_linux_non_actions_and_non_push_are_rejected_before_model_start(self):
        cases = [
            ("platform", "win32"),
            ("TRANSLATION_REPOSITORY_PUBLIC", "false"),
            ("GITHUB_ACTIONS", "false"),
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_EVENT_NAME", "schedule"),
            ("GITHUB_EVENT_NAME", "workflow_dispatch"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                environment = {**PUBLIC_PUSH, "RUNNER_TEMP": str(self.runner_temp)}
                if key != "platform":
                    environment[key] = value
                with mock.patch.dict(os.environ, environment, clear=True):
                    with mock.patch.object(smoke.sys, "platform", value if key == "platform" else "linux"):
                        with self.assertRaises(smoke.SmokeError):
                            smoke.run(self.repo, self.result())
        self.start.assert_not_called()
        self.discover.assert_not_called()
        self.assertEqual(self.snapshot(), self.before)

    def test_eight_valid_cases_use_external_temp_and_preserve_every_checkout_file(self):
        def start(directory):
            self.assertTrue(directory.is_dir())
            self.assertEqual(directory.parent, self.runner_temp)
            self.assertNotIn(self.repo, directory.parents)
            return self.process, self.log

        self.start.side_effect = start
        result = self.result()
        valid = smoke.run(self.repo, result)
        self.assertTrue(valid)
        self.assertEqual(len(result["cases"]), 8)
        self.assertTrue(all(case["valid"] for case in result["cases"]))
        self.assertEqual({case["language"] for case in result["cases"]}, {"en", "ja"})
        self.assertEqual(result["local_requests"], 8)
        self.assertEqual(result["date"], SOURCE_DATE)
        self.assertEqual(result["source_sha256"], self.source.source_hash)
        self.assertEqual(result["model"], smoke.core.LOCAL_MODEL)
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(list(self.runner_temp.iterdir()), [])
        self.stop.assert_called_once_with(self.process, self.log)

    def test_failed_case_is_recorded_and_remaining_cases_continue_with_overall_failure(self):
        original_translate = self.client.translate_batch.side_effect
        attempt = 0

        def translate(units, language):
            nonlocal attempt
            attempt += 1
            if attempt == 2:
                self.client.local_requests += 1
                raise smoke.core.TranslationError("A translation changed numeric values or their multiplicity.")
            return original_translate(units, language)

        self.client.translate_batch.side_effect = translate
        result = self.result()
        valid = smoke.run(self.repo, result)
        self.assertFalse(valid)
        self.assertEqual(len(result["cases"]), 8)
        self.assertEqual(sum(case["valid"] for case in result["cases"]), 7)
        failed = result["cases"][1]
        self.assertEqual(failed["key"], "lead:summary")
        self.assertIsNone(failed["translation"])
        self.assertIn("changed numeric values", failed["error"])
        self.assertTrue(result["cases"][-1]["valid"])
        self.assertEqual(result["local_requests"], 8)
        self.assertEqual(self.snapshot(), self.before)
        self.stop.assert_called_once_with(self.process, self.log)

    def test_arbitrary_case_exception_is_sanitized_and_does_not_stop_other_cases(self):
        original_translate = self.client.translate_batch.side_effect
        attempt = 0

        def translate(units, language):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                self.client.local_requests += 1
                raise RuntimeError("Private provider response and credential marker")
            return original_translate(units, language)

        self.client.translate_batch.side_effect = translate
        result = self.result()
        self.assertFalse(smoke.run(self.repo, result))
        self.assertEqual(len(result["cases"]), 8)
        self.assertNotIn("Private provider", json.dumps(result))
        self.assertNotIn("credential marker", json.dumps(result))
        self.assertTrue(result["cases"][-1]["valid"])
        self.assertEqual(self.snapshot(), self.before)
        self.stop.assert_called_once_with(self.process, self.log)

    def test_client_initialization_failure_always_stops_started_server(self):
        self.translator.side_effect = RuntimeError("Injected translator initialization failure")
        with self.assertRaises(RuntimeError):
            smoke.run(self.repo, self.result())
        self.start.assert_called_once()
        self.stop.assert_called_once_with(self.process, self.log)
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(list(self.runner_temp.iterdir()), [])

    def test_server_start_failure_does_not_attempt_to_stop_unreturned_process(self):
        self.start.side_effect = smoke.workflow.WorkflowError("Injected setup failure")
        with self.assertRaises(smoke.workflow.WorkflowError):
            smoke.run(self.repo, self.result())
        self.translator.assert_not_called()
        self.stop.assert_not_called()
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(list(self.runner_temp.iterdir()), [])

    def test_temp_inside_checkout_is_rejected_before_model_download(self):
        for base in (self.repo, self.repo / "nested-temp"):
            with self.subTest(base=base):
                with mock.patch.dict(os.environ, {"RUNNER_TEMP": str(base)}):
                    with self.assertRaises(smoke.SmokeError):
                        smoke.run(self.repo, self.result())
        self.start.assert_not_called()
        self.translator.assert_not_called()
        self.assertEqual(self.snapshot(), self.before)

    def test_main_emits_failed_report_and_nonzero_exit_with_static_setup_diagnostic(self):
        self.start.side_effect = smoke.workflow.WorkflowError("Private download failure detail")
        output = io.StringIO()
        with redirect_stdout(output):
            code = smoke.main(["--repo-root", str(self.repo)])
        self.assertEqual(code, 1)
        report = output.getvalue().split("BEGIN_SMOKE_JSON\n", 1)[1].split("\nEND_SMOKE_JSON", 1)[0]
        result = json.loads(report)
        self.assertFalse(result["valid"])
        self.assertEqual(result["cases"], [])
        self.assertEqual(result["error"], "Pinned model setup or local server operation failed.")
        self.assertNotIn("Private download failure detail", output.getvalue())
        self.assertEqual(self.snapshot(), self.before)


if __name__ == "__main__":
    unittest.main()
