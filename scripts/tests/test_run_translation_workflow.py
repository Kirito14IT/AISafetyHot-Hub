"""Offline tests for free-runner orchestration, guarded commits, and downloads.

All subprocesses, source fetches, HTTP requests, and model processes are mocked.
Run with: python -m unittest discover -s scripts/tests -v
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import run_translation_workflow as workflow


LATEST = "2026-10-08"
OLDER = "2026-10-07"
REVISION = "a" * 40
FRESH_REVISION = "b" * 40
PUBLIC_ENVIRONMENT = {
    "GITHUB_ACTIONS": "true",
    "TRANSLATION_ENABLED": "true",
    "TRANSLATION_REPOSITORY_PUBLIC": "true",
    "TRANSLATION_DEFAULT_BRANCH": "main",
    "GITHUB_REF_NAME": "main",
    "GITHUB_EVENT_NAME": "schedule",
}


def plan_for(*days: str, missing: int = 1) -> dict:
    return {
        "mode": "dry-run",
        "dates": [
            {"date": day, "languages": {"en": {"missing_units": missing}, "ja": {"missing_units": missing}}}
            for day in days
        ],
    }


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        self.readme = self.repo / "README.md"
        self.readme.write_bytes(b"Original Chinese publication bytes\r\n")
        self.before = {"README.md": self.readme.read_bytes()}
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(os.environ, {}, clear=True).start()
        self.http = mock.patch.object(workflow.request, "urlopen", side_effect=AssertionError("No live HTTP in tests")).start()
        self.subprocess = mock.patch.object(workflow.subprocess, "run", side_effect=AssertionError("No live subprocess in tests")).start()
        self.output = io.StringIO()
        self.stdout = redirect_stdout(self.output)
        self.stdout.__enter__()
        self.addCleanup(self.stdout.__exit__, None, None, None)

    def arguments(self, mode="translate", publish=False):
        return argparse.Namespace(repo_root=self.repo, mode=mode, publish=publish)

    def snapshot(self):
        return {str(path.relative_to(self.repo)): path.read_bytes() for path in self.repo.rglob("*") if path.is_file()}

    def test_dry_run_returns_plan_without_model_publication_or_repository_writes(self):
        plan = plan_for(LATEST)
        with mock.patch.object(workflow, "fetch_source", return_value=(REVISION, {LATEST})) as fetch:
            with mock.patch.object(workflow, "run_core", return_value=plan) as core:
                with mock.patch.object(workflow, "start_server") as start:
                    with mock.patch.object(workflow, "publish") as publish:
                        result = workflow.run(self.arguments(mode="dry-run"))
        self.assertEqual(result, plan)
        fetch.assert_called_once()
        self.assertEqual(core.call_args.args[3:], ("--dry-run",))
        self.assertGreater(core.call_args.kwargs["timeout"], 0)
        start.assert_not_called()
        publish.assert_not_called()
        self.assertEqual(self.snapshot(), self.before)

    def test_dry_run_with_publish_is_rejected_before_fetching_source(self):
        with mock.patch.object(workflow, "fetch_source") as fetch:
            with self.assertRaises(workflow.WorkflowError):
                workflow.run(self.arguments(mode="dry-run", publish=True))
        fetch.assert_not_called()

    def test_publication_guards_reject_private_disabled_non_default_and_unsafe_events(self):
        cases = [
            ("GITHUB_ACTIONS", "false"),
            ("TRANSLATION_ENABLED", "false"),
            ("TRANSLATION_ENABLED", ""),
            ("TRANSLATION_REPOSITORY_PUBLIC", "false"),
            ("TRANSLATION_DEFAULT_BRANCH", ""),
            ("GITHUB_REF_NAME", "docs/readme-en-ja"),
            ("GITHUB_EVENT_NAME", "pull_request"),
            ("GITHUB_EVENT_NAME", "pull_request_target"),
            ("GITHUB_EVENT_NAME", "push"),
        ]
        with mock.patch.object(workflow, "command") as command:
            for key, value in cases:
                with self.subTest(key=key, value=value):
                    environment = {**PUBLIC_ENVIRONMENT, key: value}
                    with mock.patch.dict(os.environ, environment, clear=True):
                        with self.assertRaises(workflow.WorkflowError):
                            workflow.guard_publish(self.repo)
        command.assert_not_called()

    def test_guards_accept_only_schedule_or_manual_public_default_branch_with_clean_checkout(self):
        with mock.patch.object(workflow, "command", return_value="") as command:
            for event in ("schedule", "workflow_dispatch"):
                with self.subTest(event=event):
                    with mock.patch.dict(os.environ, {**PUBLIC_ENVIRONMENT, "GITHUB_EVENT_NAME": event}, clear=True):
                        workflow.guard_publish(self.repo)
            self.assertEqual(command.call_count, 2)
            self.assertEqual(command.call_args.args[0], ["git", "status", "--porcelain"])
        with mock.patch.dict(os.environ, PUBLIC_ENVIRONMENT, clear=True):
            with mock.patch.object(workflow, "command", return_value=" M README.md\n"):
                with self.assertRaises(workflow.WorkflowError):
                    workflow.guard_publish(self.repo)

    def test_rejected_publication_guard_cannot_download_fetch_or_start_inference(self):
        with mock.patch.dict(os.environ, {**PUBLIC_ENVIRONMENT, "TRANSLATION_REPOSITORY_PUBLIC": "false"}, clear=True):
            with mock.patch.object(workflow, "fetch_source") as fetch:
                with mock.patch.object(workflow, "start_server") as start:
                    with self.assertRaises(workflow.WorkflowError):
                        workflow.run(self.arguments(publish=True))
        fetch.assert_not_called()
        start.assert_not_called()

    def test_all_actions_inference_is_guarded_even_without_publication(self):
        cases = [
            ("TRANSLATION_REPOSITORY_PUBLIC", "false"),
            ("TRANSLATION_ENABLED", "false"),
            ("GITHUB_REF_NAME", "docs/readme-en-ja"),
            ("GITHUB_EVENT_NAME", "push"),
            ("GITHUB_EVENT_NAME", "pull_request"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                with mock.patch.dict(os.environ, {**PUBLIC_ENVIRONMENT, key: value}, clear=True):
                    with mock.patch.object(workflow, "fetch_source") as fetch:
                        with mock.patch.object(workflow, "start_server") as start:
                            with self.assertRaises(workflow.WorkflowError):
                                workflow.run(self.arguments(publish=False))
                fetch.assert_not_called()
                start.assert_not_called()

    def test_local_non_actions_translation_without_publish_does_not_require_github_configuration(self):
        reports = [plan_for(LATEST, missing=0), {"dates": [{"date": LATEST}], "local_requests": 0}, {"mode": "verify-source"}]
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(workflow, "fetch_source", return_value=(REVISION, {LATEST})):
                with mock.patch.object(workflow, "run_core", side_effect=reports):
                    with mock.patch.object(workflow, "guard_publish") as guard:
                        result = workflow.run(self.arguments())
        self.assertEqual(result["local_requests"], 0)
        guard.assert_not_called()

    def test_local_publish_is_forbidden_even_with_other_configuration_present(self):
        with mock.patch.dict(os.environ, {**PUBLIC_ENVIRONMENT, "GITHUB_ACTIONS": "false"}, clear=True):
            with mock.patch.object(workflow, "fetch_source") as fetch:
                with self.assertRaises(workflow.WorkflowError):
                    workflow.run(self.arguments(publish=True))
        fetch.assert_not_called()

    def test_latest_digest_runs_first_each_date_is_freshly_verified_then_published(self):
        events = []
        process, log = mock.Mock(), mock.Mock()
        fetch_number = 0

        def fetch(git_root, stage):
            nonlocal fetch_number
            fetch_number += 1
            events.append(("fetch", fetch_number))
            return (REVISION if fetch_number == 1 else FRESH_REVISION, {OLDER, LATEST})

        def core(repo, stage, revision, *options, **kwargs):
            if "--dry-run" in options:
                events.append(("plan",))
                return plan_for(OLDER, LATEST)
            day = options[options.index("--date") + 1]
            if "--verify-source" in options:
                self.assertEqual(revision, FRESH_REVISION)
                events.append(("verify", day))
                return {"mode": "verify-source", "dates": []}
            self.assertEqual(revision, REVISION)
            events.append(("translate", day))
            return {"dates": [{"date": day}], "local_requests": 3}

        with mock.patch.object(workflow, "guard_publish") as guard:
            with mock.patch.object(workflow, "fetch_source", side_effect=fetch):
                with mock.patch.object(workflow, "run_core", side_effect=core):
                    with mock.patch.object(workflow, "start_server", return_value=(process, log)) as start:
                        with mock.patch.object(workflow, "stop_server") as stop:
                            with mock.patch.object(workflow, "publish", side_effect=lambda repo: events.append(("publish",))):
                                result = workflow.run(self.arguments(publish=True))
        guard.assert_called_once_with(self.repo)
        self.assertEqual(events, [
            ("fetch", 1), ("plan",), ("translate", LATEST), ("fetch", 2), ("verify", LATEST), ("publish",),
            ("translate", OLDER), ("fetch", 3), ("verify", OLDER), ("publish",),
        ])
        start.assert_called_once()
        stop.assert_called_once_with(process, log)
        self.assertEqual([day["date"] for day in result["dates"]], [LATEST, OLDER])
        self.assertEqual(result["local_requests"], 6)
        self.assertEqual(result["api_calls"], 6)

    def test_complete_cache_refresh_is_offline_without_model_download_or_start(self):
        reports = [plan_for(LATEST, missing=0), {"dates": [{"date": LATEST}], "local_requests": 0}, {"mode": "verify-source"}]
        with mock.patch.object(workflow, "fetch_source", return_value=(REVISION, {LATEST})):
            with mock.patch.object(workflow, "run_core", side_effect=reports) as core:
                with mock.patch.object(workflow, "download") as download:
                    with mock.patch.object(workflow, "start_server") as start:
                        result = workflow.run(self.arguments())
        self.assertEqual(core.call_args_list[1].args[3:], ("--date", LATEST, "--offline"))
        self.assertEqual(core.call_args_list[2].args[3:], ("--date", LATEST, "--verify-source"))
        self.assertEqual(result["local_requests"], 0)
        start.assert_not_called()
        download.assert_not_called()

    def test_empty_plan_does_not_start_model_or_publish(self):
        with mock.patch.object(workflow, "fetch_source", return_value=(REVISION, {LATEST})):
            with mock.patch.object(workflow, "run_core", return_value=plan_for()):
                with mock.patch.object(workflow, "start_server") as start:
                    with mock.patch.object(workflow, "publish") as publish:
                        result = workflow.run(self.arguments())
        self.assertEqual(result["dates"], [])
        start.assert_not_called()
        publish.assert_not_called()

    def test_older_failure_keeps_newest_publication_and_fails_entire_run(self):
        events = []
        process, log = mock.Mock(), mock.Mock()

        def core(repo, stage, revision, *options, **kwargs):
            if "--dry-run" in options:
                return plan_for(OLDER, LATEST)
            day = options[options.index("--date") + 1]
            if "--verify-source" in options:
                events.append(("verify", day))
                return {"mode": "verify-source"}
            events.append(("translate", day))
            if day == OLDER:
                raise workflow.WorkflowError("Older digest could not be translated.")
            return {"dates": [{"date": day}], "local_requests": 2}

        def publish(repo):
            events.append(("publish",))
            (repo / "README.en.md").write_text("Newest verified publication", encoding="utf-8")

        with mock.patch.object(workflow, "guard_publish"):
            with mock.patch.object(workflow, "fetch_source", return_value=(REVISION, {OLDER, LATEST})):
                with mock.patch.object(workflow, "run_core", side_effect=core):
                    with mock.patch.object(workflow, "start_server", return_value=(process, log)):
                        with mock.patch.object(workflow, "stop_server") as stop:
                            with mock.patch.object(workflow, "publish", side_effect=publish):
                                with self.assertRaises(workflow.WorkflowError):
                                    workflow.run(self.arguments(publish=True))
        self.assertEqual(events, [("translate", LATEST), ("verify", LATEST), ("publish",), ("translate", OLDER)])
        self.assertEqual((self.repo / "README.en.md").read_text(encoding="utf-8"), "Newest verified publication")
        self.assertEqual(self.readme.read_bytes(), self.before["README.md"])
        stop.assert_called_once_with(process, log)

    def test_new_latest_source_or_changed_window_rejects_current_date_before_publication(self):
        for dates in ({LATEST, "2026-10-09"}, {LATEST, "2026-10-06"}):
            with self.subTest(fresh_dates=dates):
                with mock.patch.object(workflow, "guard_publish"):
                    with mock.patch.object(workflow, "fetch_source", side_effect=[(REVISION, {LATEST}), (FRESH_REVISION, dates)]):
                        with mock.patch.object(workflow, "run_core", side_effect=[plan_for(LATEST, missing=0), {"dates": [{"date": LATEST}]}]) as core:
                            with mock.patch.object(workflow, "publish") as publish:
                                with self.assertRaises(workflow.WorkflowError):
                                    workflow.run(self.arguments(publish=True))
                self.assertEqual(core.call_count, 2)
                publish.assert_not_called()

    def test_changed_source_hash_rejected_by_verification_prevents_commit_and_push(self):
        with mock.patch.object(workflow, "guard_publish"):
            with mock.patch.object(workflow, "fetch_source", side_effect=[(REVISION, {LATEST}), (FRESH_REVISION, {LATEST})]):
                reports = [plan_for(LATEST, missing=0), {"dates": [{"date": LATEST}]}, workflow.WorkflowError("Source digest hash changed.")]
                with mock.patch.object(workflow, "run_core", side_effect=reports) as core:
                    with mock.patch.object(workflow, "publish") as publish:
                        with self.assertRaises(workflow.WorkflowError):
                            workflow.run(self.arguments(publish=True))
        self.assertEqual(core.call_args.args[2], FRESH_REVISION)
        self.assertIn("--verify-source", core.call_args.args)
        publish.assert_not_called()

    def test_failed_model_download_prevents_translation_and_publication(self):
        with mock.patch.object(workflow, "guard_publish"):
            with mock.patch.object(workflow, "fetch_source", return_value=(REVISION, {LATEST})):
                with mock.patch.object(workflow, "run_core", return_value=plan_for(LATEST)) as core:
                    with mock.patch.object(workflow, "start_server", side_effect=workflow.WorkflowError("Pinned model verification failed.")):
                        with mock.patch.object(workflow, "publish") as publish:
                            with mock.patch.object(workflow, "stop_server") as stop:
                                with self.assertRaises(workflow.WorkflowError):
                                    workflow.run(self.arguments(publish=True))
        core.assert_called_once()
        publish.assert_not_called()
        stop.assert_not_called()


class DownloadAndProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_model_download_verifies_exact_size_and_sha256(self):
        content = b"Offline pinned bytes"
        with mock.patch.object(workflow.request, "urlopen", return_value=io.BytesIO(content)) as http:
            workflow.download("https://example.invalid/model", self.root / "model", hashlib.sha256(content).hexdigest(), len(content))
        self.assertEqual((self.root / "model").read_bytes(), content)
        self.assertEqual(http.call_args.args[0].full_url, "https://example.invalid/model")
        self.assertEqual(http.call_args.kwargs["timeout"], 120)

    def test_bad_hash_undersize_and_oversize_are_rejected(self):
        content = b"Pinned bytes"
        digest = hashlib.sha256(content).hexdigest()
        for expected_sha, expected_size in (("0" * 64, len(content)), (digest, len(content) + 1), (digest, len(content) - 1)):
            with self.subTest(expected_sha=expected_sha, expected_size=expected_size):
                with mock.patch.object(workflow.request, "urlopen", return_value=io.BytesIO(content)):
                    with self.assertRaises(workflow.WorkflowError):
                        workflow.download("https://example.invalid/model", self.root / "model", expected_sha, expected_size)

    def test_binary_or_model_verification_failure_never_extracts_or_starts_server(self):
        for failed_download in (1, 2, 3):
            with self.subTest(failed_download=failed_download):
                effects = [None] * (failed_download - 1) + [workflow.WorkflowError("SHA-256 or shard size mismatch")]
                with mock.patch.object(workflow.sys, "platform", "linux"):
                    with mock.patch.object(workflow, "download", side_effect=effects) as download:
                        with mock.patch.object(workflow.tarfile, "open") as extract:
                            with mock.patch.object(workflow.subprocess, "Popen") as process:
                                with redirect_stdout(io.StringIO()):
                                    with self.assertRaises(workflow.WorkflowError):
                                        workflow.start_server(self.root)
                self.assertEqual(download.call_count, failed_download)
                extract.assert_not_called()
                process.assert_not_called()

    def test_both_pinned_model_shards_are_verified_before_extracting_and_starting_local_cpu_server(self):
        events = []
        process = mock.Mock()
        process.poll.return_value = None
        binary_root = self.root / "llama"
        server_path = binary_root / "release" / "llama-server"
        bundle = mock.MagicMock()
        bundle.__enter__.return_value = bundle

        def download(url, destination, expected_sha, expected_size=None):
            events.append(("download", url, destination, expected_sha, expected_size))

        def extract(destination, *, filter):
            self.assertEqual(destination, binary_root)
            self.assertEqual(filter, "data")
            events.append(("extract",))
            server_path.parent.mkdir(parents=True)
            server_path.write_bytes(b"Offline mocked executable")

        def start(arguments, **options):
            events.append(("start",))
            return process

        bundle.extractall.side_effect = extract
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        opener = mock.Mock()
        opener.open.return_value = response
        with mock.patch.object(workflow.sys, "platform", "linux"):
            with mock.patch.object(workflow, "download", side_effect=download) as downloads:
                with mock.patch.object(workflow.tarfile, "open", return_value=bundle):
                    with mock.patch.object(workflow.subprocess, "Popen", side_effect=start) as start_process:
                        with mock.patch.object(workflow.request, "build_opener", return_value=opener) as build_opener:
                            with redirect_stdout(io.StringIO()):
                                returned_process, log = workflow.start_server(self.root)
        self.addCleanup(log.close)
        self.assertIs(returned_process, process)
        self.assertEqual(len(workflow.MODEL_SHARDS), 2)
        self.assertEqual(downloads.call_count, 3)
        expected_downloads = [("download", workflow.LLAMA_URL, self.root / "llama.tar.gz", workflow.LLAMA_SHA256, None)]
        for filename, size, sha256 in workflow.MODEL_SHARDS:
            self.assertGreater(size, 0)
            self.assertRegex(sha256, r"^[0-9a-f]{64}$")
            expected_downloads.append(("download", workflow.MODEL_BASE_URL + "/" + filename, self.root / filename, sha256, size))
        self.assertEqual(events, [*expected_downloads, ("extract",), ("start",)])
        self.assertRegex(workflow.MODEL_REVISION, r"^[0-9a-f]{40}$")
        self.assertIn("/resolve/" + workflow.MODEL_REVISION, workflow.MODEL_BASE_URL)
        arguments = start_process.call_args.args[0]
        self.assertEqual(arguments[arguments.index("--model") + 1], str(self.root / workflow.MODEL_SHARDS[0][0]))
        self.assertEqual(arguments[arguments.index("--alias") + 1], workflow.MODEL_ALIAS)
        self.assertEqual(arguments[arguments.index("--host") + 1], "127.0.0.1")
        self.assertEqual(arguments[arguments.index("--n-gpu-layers") + 1], "0")
        opener.open.assert_called_once_with("http://127.0.0.1:8080/health", timeout=5)
        proxy_handlers = [handler for handler in build_opener.call_args.args if isinstance(handler, workflow.request.ProxyHandler)]
        self.assertEqual(len(proxy_handlers), 1)
        self.assertEqual(proxy_handlers[0].proxies, {})

    def test_local_model_runner_rejects_non_linux_before_downloading(self):
        with mock.patch.object(workflow.sys, "platform", "win32"):
            with mock.patch.object(workflow, "download") as download:
                with self.assertRaises(workflow.WorkflowError):
                    workflow.start_server(self.root)
        download.assert_not_called()

    def test_stop_server_terminates_and_kills_only_after_timeout(self):
        process, log = mock.Mock(), mock.Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("llama-server", 20), None]
        workflow.stop_server(process, log)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_args_list, [mock.call(timeout=20), mock.call(timeout=10)])
        log.close.assert_called_once()

    def test_command_error_does_not_expose_stdout_stderr_or_full_arguments(self):
        result = subprocess.CompletedProcess(["git", "fetch"], 1, stdout="Sensitive upstream body", stderr="credential marker")
        with mock.patch.object(workflow.subprocess, "run", return_value=result):
            with self.assertRaises(workflow.WorkflowError) as raised:
                workflow.command(["git", "fetch", "https://token-value@example.invalid"])
        self.assertNotIn("Sensitive upstream body", str(raised.exception))
        self.assertNotIn("credential marker", str(raised.exception))
        self.assertNotIn("token-value", str(raised.exception))

    def test_command_forwards_only_one_exact_static_diagnostic_from_trusted_core(self):
        trusted_core = Path(workflow.__file__).with_name("translate_daily.py").resolve()
        arguments = [sys.executable, str(trusted_core), "--offline"]
        safe = "A translation changed numeric values or their multiplicity."
        self.assertIn(safe, workflow.SAFE_CORE_DIAGNOSTICS)
        stderr = (
            "Source text and response body: private marker\n"
            f"Translation failed: {safe}\n"
            "Translation failed: A translation is empty or has outer whitespace.\n"
            "Credential marker at end\n"
        )
        result = subprocess.CompletedProcess(arguments, 1, stdout="Private stdout marker", stderr=stderr)
        output = io.StringIO()
        with mock.patch.object(workflow.subprocess, "run", return_value=result):
            with redirect_stderr(output):
                with self.assertRaises(workflow.WorkflowError):
                    workflow.command(arguments)
        self.assertEqual(output.getvalue(), f"Translation failed: {safe}\n")
        self.assertNotIn("private marker", output.getvalue())
        self.assertNotIn("Private stdout marker", output.getvalue())
        self.assertNotIn("Credential marker", output.getvalue())

    def test_command_never_forwards_unknown_extended_or_untrusted_core_diagnostics(self):
        trusted_core = Path(workflow.__file__).with_name("translate_daily.py").resolve()
        safe = "A translation changed numeric values or their multiplicity."
        cases = [
            ([sys.executable, str(trusted_core)], "Translation failed: private response body\n"),
            ([sys.executable, str(trusted_core)], f"Translation failed: {safe} Private suffix\n"),
            ([sys.executable, str(self.root / "translate_daily.py")], f"Translation failed: {safe}\n"),
            (["git", "fetch"], f"Translation failed: {safe}\n"),
        ]
        for arguments, stderr in cases:
            with self.subTest(arguments=arguments, stderr=stderr):
                output = io.StringIO()
                result = subprocess.CompletedProcess(arguments, 1, stdout="Private stdout", stderr=stderr)
                with mock.patch.object(workflow.subprocess, "run", return_value=result):
                    with redirect_stderr(output):
                        with self.assertRaises(workflow.WorkflowError):
                            workflow.command(arguments)
                self.assertEqual(output.getvalue(), "")


class SourceAndPublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_fetch_extracts_only_recent_seven_canonical_daily_texts(self):
        tree = "\n".join(
            [f"daily/2026/2026-10-{number:02d}.md" for number in range(1, 9)]
            + ["daily/en/2026/2026-10-08.md", "daily/2025/2026-10-08.md", "scripts/upstream.py"]
        )

        def command(args, **kwargs):
            if "rev-parse" in args:
                return REVISION + "\n"
            if "ls-tree" in args:
                return tree
            if "show" in args:
                return "Chinese source text\n"
            return ""

        with mock.patch.object(workflow, "command", side_effect=command) as commands:
            revision, dates = workflow.fetch_source(self.root / "source.git", self.root / "stage")
        self.assertEqual(revision, REVISION)
        self.assertEqual(dates, {f"2026-10-{number:02d}" for number in range(2, 9)})
        actual = {path.relative_to(self.root / "stage").as_posix() for path in (self.root / "stage").rglob("*") if path.is_file()}
        self.assertEqual(actual, {f"daily/2026/{day}.md" for day in dates})
        calls = [call.args[0] for call in commands.call_args_list]
        self.assertEqual(len([args for args in calls if "show" in args]), 7)
        self.assertTrue(all(args[0] == "git" for args in calls))
        self.assertFalse(any("checkout" in args for args in calls))
        self.assertIn(["git", "-C", str(self.root / "source.git"), "fetch", "--depth=1", "--no-tags", workflow.SOURCE_URL, "refs/heads/main"], calls)

    def test_fetch_rejects_unpinned_revision_or_absent_canonical_digests(self):
        for values in (["", "branch-name"], ["", REVISION, "daily/en/2026/2026-10-08.md\n"]):
            with self.subTest(values=values):
                with mock.patch.object(workflow, "command", side_effect=[*values]):
                    with self.assertRaises(workflow.WorkflowError):
                        workflow.fetch_source(self.root, self.root / "stage")

    def test_run_core_uses_checkout_script_and_supplied_source_stage_not_upstream_code(self):
        with mock.patch.object(workflow, "command", return_value='{"mode":"dry-run","dates":[]}') as command:
            result = workflow.run_core(self.root, self.root / "untrusted-source-stage", REVISION, "--dry-run", timeout=42)
        arguments = command.call_args.args[0]
        self.assertEqual(arguments[:2], [sys.executable, str(self.root / "scripts" / "translate_daily.py")])
        self.assertEqual(arguments[arguments.index("--source-root") + 1], str(self.root / "untrusted-source-stage"))
        self.assertEqual(arguments[arguments.index("--source-revision") + 1], REVISION)
        self.assertEqual(command.call_args.kwargs, {"cwd": self.root, "timeout": 42})
        self.assertEqual(result, {"mode": "dry-run", "dates": []})

    def test_invalid_core_report_is_rejected(self):
        with mock.patch.object(workflow, "command", return_value="not JSON"):
            with self.assertRaises(workflow.WorkflowError):
                workflow.run_core(self.root, self.root / "stage", REVISION, "--dry-run")

    def test_publish_stages_only_outputs_and_uses_normal_default_branch_push(self):
        calls = []

        def command(args, **kwargs):
            calls.append(args)
            if args == ["git", "diff", "--name-only", "-z"]:
                return "README.en.md\0daily/ja/2026/2026-10-08.md\0translations/en/2026/2026-10-08.json\0"
            if args == ["git", "diff", "--cached", "--name-only"]:
                return "README.en.md\n"
            return ""

        with mock.patch.dict(os.environ, {"TRANSLATION_DEFAULT_BRANCH": "main"}, clear=True):
            with mock.patch.object(workflow, "command", side_effect=command):
                workflow.publish(self.root)
        self.assertIn(["git", "add", "--", *workflow.OUTPUT_PATHS], calls)
        self.assertIn(["git", "diff", "--cached", "--check"], calls)
        self.assertIn(["git", "commit", "-m", "发布：英文和日文 AI 安全日报"], calls)
        self.assertEqual(calls[-1], ["git", "push", "origin", "HEAD:main"])
        self.assertFalse(any("--force" in args or "--force-with-lease" in args for args in calls))
        self.assertNotIn("README.md", workflow.OUTPUT_PATHS)
        self.assertNotIn("papers", workflow.OUTPUT_PATHS)
        self.assertNotIn("status.json", workflow.OUTPUT_PATHS)

    def test_publish_rejects_changes_outside_outputs_before_staging(self):
        for path in ("README.md", "status.json", "papers/2026/2026-10-08.md", "translations-malicious/file", "scripts/translate_daily.py"):
            with self.subTest(path=path):
                with mock.patch.object(workflow, "command", return_value=path + "\0") as command:
                    with self.assertRaises(workflow.WorkflowError):
                        workflow.publish(self.root)
                command.assert_called_once_with(["git", "diff", "--name-only", "-z"], cwd=self.root)

    def test_publish_empty_staging_does_not_commit_or_push(self):
        with mock.patch.object(workflow, "command", return_value="") as command:
            with redirect_stdout(io.StringIO()):
                workflow.publish(self.root)
        verbs = [call.args[0][1] for call in command.call_args_list]
        self.assertNotIn("commit", verbs)
        self.assertNotIn("push", verbs)

    def test_rejected_concurrent_push_is_not_retried_forced_or_rebased(self):
        calls = []

        def command(args, **kwargs):
            calls.append(args)
            if args == ["git", "diff", "--cached", "--name-only"]:
                return "README.en.md\n"
            if args[1] == "push":
                raise workflow.WorkflowError("Normal push rejected by concurrent publisher.")
            return ""

        with mock.patch.dict(os.environ, {"TRANSLATION_DEFAULT_BRANCH": "main"}, clear=True):
            with mock.patch.object(workflow, "command", side_effect=command):
                with self.assertRaises(workflow.WorkflowError):
                    workflow.publish(self.root)
        self.assertEqual([args for args in calls if args[1] == "push"], [["git", "push", "origin", "HEAD:main"]])
        self.assertFalse(any("rebase" in args or "--force" in args for args in calls))


if __name__ == "__main__":
    unittest.main()
