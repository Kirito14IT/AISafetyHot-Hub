#!/usr/bin/env python3
"""Read-only, public Linux Actions smoke test for the pinned free CPU model."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

# Importing our helpers must not create bytecode caches inside the checkout.
sys.dont_write_bytecode = True

import run_translation_workflow as workflow
import translate_daily as core


class SmokeError(Exception):
    """A static diagnostic that is safe to expose in public workflow logs."""


def guard_smoke() -> None:
    if sys.platform != "linux":
        raise SmokeError("Model smoke inference requires a Linux runner.")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SmokeError("Model smoke inference is allowed only inside GitHub Actions.")
    if os.environ.get("TRANSLATION_REPOSITORY_PUBLIC") != "true":
        raise SmokeError("Model smoke inference requires a public repository.")
    if os.environ.get("GITHUB_EVENT_NAME") != "push":
        raise SmokeError("Model smoke inference is allowed only for a public push event.")


def _diagnostic(exc: Exception) -> str:
    if isinstance(exc, (core.TranslationError, SmokeError)):
        return str(exc)
    if isinstance(exc, workflow.WorkflowError):
        return "Pinned model setup or local server operation failed."
    return "Smoke inference or local source inspection failed."


def run(repo_root: Path, result: dict[str, Any]) -> bool:
    guard_smoke()
    repo_root = repo_root.resolve()
    sources = core.discover_sources(repo_root)
    source_date = max(sources)
    source = core.parse_daily(sources[source_date].read_bytes().decode("utf-8"), source_date)
    if len(source.items) < 2:
        raise SmokeError("The latest Chinese digest must have at least two main items.")
    keys = ["lead:title", "lead:summary"] + ["item:" + item["id"] + ":summary" for item in source.items[:2]]
    result.update({"date": source_date, "source_sha256": source.source_hash, "model": core.LOCAL_MODEL, "model_revision": core.MODEL_REVISION, "llama_cpp_release": core.LLAMA_CPP_RELEASE, "prompt_version": core.PROMPT_VERSION})
    temporary_base = Path(os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()).resolve()
    if temporary_base == repo_root or repo_root in temporary_base.parents:
        raise SmokeError("The model temporary directory must be outside the repository checkout.")
    process = None
    log = None
    all_valid = True
    with tempfile.TemporaryDirectory(prefix="aisafetyhot-smoke-", dir=temporary_base) as directory:
        try:
            process, log = workflow.start_server(Path(directory))
            client = core.Translator(max_api_calls=16, timeout=600, retries=0)
            for language in core.LANGUAGES:
                for key in keys:
                    original = source.units[key]
                    case: dict[str, Any] = {"key": key, "language": language, "source": original, "translation": None}
                    started = time.monotonic()
                    try:
                        translated = client.translate_batch({key: original}, language)[key]
                        core.validate_translation(original, translated)
                        case.update({"translation": translated, "valid": True})
                    except Exception as exc:
                        all_valid = False
                        case.update({"valid": False, "error": _diagnostic(exc)})
                    finally:
                        case["elapsed_seconds"] = round(time.monotonic() - started, 3)
                        result["cases"].append(case)
            result["local_requests"] = client.local_requests
        finally:
            if process is not None:
                workflow.stop_server(process, log)
    return all_valid


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    result: dict[str, Any] = {"mode": "read-only-smoke", "cases": [], "local_requests": 0, "valid": False}
    started = time.monotonic()
    try:
        result["valid"] = run(args.repo_root, result)
    except Exception as exc:
        result["error"] = _diagnostic(exc)
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        print("BEGIN_SMOKE_JSON", flush=True)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        print("END_SMOKE_JSON", flush=True)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
