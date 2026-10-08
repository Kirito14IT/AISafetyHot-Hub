#!/usr/bin/env python3
"""Run the public-runner translation workflow with pinned local CPU inference."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib import error, request


SOURCE_REPOSITORY = "wuyoscar/AISafetyHot-Hub"
SOURCE_URL = "https://github.com/wuyoscar/AISafetyHot-Hub.git"
LLAMA_RELEASE = "b11499"
LLAMA_URL = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_RELEASE}/llama-{LLAMA_RELEASE}-bin-ubuntu-x64.tar.gz"
LLAMA_SHA256 = "19ce793dad78858ec5c89231975d0aa71de31219089bcd06dc5ebe01b403c00d"
MODEL_REVISION = "bb5d59e06d9551d752d08b292a50eb208b07ab1f"
MODEL_BASE_URL = f"https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/{MODEL_REVISION}"
MODEL_SHARDS = (
    ("qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf", 3993201344, "dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db"),
    ("qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf", 689872288, "539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a"),
)
MODEL_ALIAS = "Qwen2.5-7B-Instruct-Q4_K_M"
OUTPUT_PATHS = ("README.en.md", "README.ja.md", "daily/en", "daily/ja", "translations")
SAFE_CORE_DIAGNOSTICS = frozenset({
    "A translation is empty or has outer whitespace.",
    "A translation contains newlines or HTML.",
    "A long source has an implausibly short translation; refusing apparent truncation.",
    "A translation contains an unrestored placeholder.",
    "A translation changed numeric values or their multiplicity.",
    "A translation changed percentage or percentage-point units.",
    "A translation changed, removed, or introduced a URL.",
    "The model changed protected placeholders.",
    "The model introduced a malformed placeholder.",
    "Local inference did not finish normally; refusing a truncated result.",
    "Local inference returned invalid JSON; response body withheld.",
    "Local inference returned unexpected keys or value types.",
    "Maximum local inference request budget reached; validated cache progress is retained.",
})


class WorkflowError(Exception):
    pass


def command(args: list[str], *, cwd: Path | None = None, timeout: int = 300) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if result.returncode:
        # Forward only exact, static diagnostics from our trusted core. Do not
        # forward arbitrary stderr, response bodies, source text, or arguments.
        trusted_core = Path(__file__).with_name("translate_daily.py").resolve()
        if len(args) > 1 and args[0] == sys.executable and Path(args[1]).resolve() == trusted_core:
            for line in result.stderr.splitlines():
                if line.startswith("Translation failed: ") and line.removeprefix("Translation failed: ") in SAFE_CORE_DIAGNOSTICS:
                    print(line, file=sys.stderr)
                    break
        raise WorkflowError(f"Command failed ({result.returncode}): {Path(args[0]).name} {args[1] if len(args) > 1 else ''}")
    return result.stdout


def fetch_source(git_root: Path, stage: Path) -> tuple[str, set[str]]:
    """Read text blobs only; never check out or execute upstream scripts."""
    if not git_root.exists():
        command(["git", "init", "--bare", str(git_root)])
    command(["git", "-C", str(git_root), "fetch", "--depth=1", "--no-tags", SOURCE_URL, "refs/heads/main"], timeout=600)
    revision = command(["git", "-C", str(git_root), "rev-parse", "FETCH_HEAD"]).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise WorkflowError("The upstream revision is not a full Git SHA.")
    paths = command(["git", "-C", str(git_root), "ls-tree", "-r", "--name-only", revision, "--", "daily"]).splitlines()
    sources: dict[str, str] = {}
    for path in paths:
        match = re.fullmatch(r"daily/(\d{4})/(\d{4}-\d{2}-\d{2})\.md", path)
        if match and match.group(1) == match.group(2)[:4]:
            date.fromisoformat(match.group(2))
            sources[match.group(2)] = path
    if not sources:
        raise WorkflowError("No dated Chinese digests were found upstream.")
    cutoff = date.fromisoformat(max(sources)) - timedelta(days=6)
    recent = {key for key in sources if date.fromisoformat(key) >= cutoff}
    for key in sorted(recent):
        output = stage / sources[key]
        output.parent.mkdir(parents=True, exist_ok=True)
        text = command(["git", "-C", str(git_root), "show", f"{revision}:{sources[key]}"])
        output.write_text(text, encoding="utf-8", newline="\n")
    return revision, recent


def run_core(repo: Path, stage: Path, revision: str, *options: str, timeout: int = 240 * 60) -> dict:
    args = [sys.executable, str(repo / "scripts" / "translate_daily.py"), "--repo-root", str(repo), "--source-root", str(stage), "--source-repository", SOURCE_REPOSITORY, "--source-revision", revision, "--max-api-calls", "128", "--batch-size", "4", *options]
    result = command(args, cwd=repo, timeout=timeout)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        raise WorkflowError("The translation core returned an invalid report.") from None


def download(url: str, destination: Path, expected_sha: str, expected_size: int | None = None) -> None:
    digest = hashlib.sha256()
    size = 0
    with request.urlopen(request.Request(url, headers={"User-Agent": "AISafetyHot-Hub-free-translations"}), timeout=120) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if expected_size is not None and size > expected_size:
                raise WorkflowError("The pinned model download exceeded its expected size.")
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != expected_sha or (expected_size is not None and size != expected_size):
        raise WorkflowError("A pinned download failed SHA-256 or size verification.")


def start_server(temp_root: Path) -> tuple[subprocess.Popen, object]:
    if sys.platform != "linux":
        raise WorkflowError("Automatic model inference requires the standard Ubuntu CPU runner.")
    archive = temp_root / "llama.tar.gz"
    model = temp_root / MODEL_SHARDS[0][0]
    print("Downloading the pinned CPU binary and Apache-2.0 model; no external inference service is used.", flush=True)
    download(LLAMA_URL, archive, LLAMA_SHA256)
    for filename, expected_size, expected_sha in MODEL_SHARDS:
        download(MODEL_BASE_URL + "/" + filename, temp_root / filename, expected_sha, expected_size)
    binary_root = temp_root / "llama"
    binary_root.mkdir()
    with tarfile.open(archive, "r:gz") as bundle:
        bundle.extractall(binary_root, filter="data")
    servers = list(binary_root.rglob("llama-server"))
    if len(servers) != 1:
        raise WorkflowError("The verified binary bundle must contain exactly one llama-server.")
    server = servers[0]
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = str(server.parent) + (":" + environment["LD_LIBRARY_PATH"] if environment.get("LD_LIBRARY_PATH") else "")
    log = (temp_root / "llama-server.log").open("wb")
    process = subprocess.Popen([str(server), "--model", str(model), "--alias", MODEL_ALIAS, "--host", "127.0.0.1", "--port", "8080", "--threads", "4", "--threads-batch", "4", "--ctx-size", "8192", "--parallel", "1", "--n-gpu-layers", "0", "--reasoning", "off", "--jinja"], cwd=server.parent, env=environment, stdout=log, stderr=subprocess.STDOUT)
    opener = request.build_opener(request.ProxyHandler({}))
    deadline = time.monotonic() + 300
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise WorkflowError("The local inference server stopped before becoming healthy.")
            try:
                with opener.open("http://127.0.0.1:8080/health", timeout=5) as response:
                    if response.status == 200:
                        return process, log
            except (error.URLError, TimeoutError, OSError):
                pass
            time.sleep(5)
        raise WorkflowError("The local inference server did not become healthy within five minutes.")
    except BaseException:
        stop_server(process, log)
        raise


def stop_server(process: subprocess.Popen, log: object) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    log.close()


def guard_runtime() -> None:
    """Even inference without publication must use enabled public Actions."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    if os.environ.get("TRANSLATION_ENABLED") != "true" or os.environ.get("TRANSLATION_REPOSITORY_PUBLIC") != "true":
        raise WorkflowError("Actions inference requires an enabled workflow in a public repository.")
    branch = os.environ.get("TRANSLATION_DEFAULT_BRANCH", "")
    if not branch or os.environ.get("GITHUB_REF_NAME") != branch:
        raise WorkflowError("Actions inference is allowed only on the repository's default branch.")
    if os.environ.get("GITHUB_EVENT_NAME") not in ("schedule", "workflow_dispatch"):
        raise WorkflowError("Push and pull-request checks cannot run model inference.")


def guard_publish(repo: Path) -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise WorkflowError("Publication is allowed only from the protected Actions workflow.")
    guard_runtime()
    if command(["git", "status", "--porcelain"], cwd=repo).strip():
        raise WorkflowError("Publication requires a clean starting checkout.")


def publish(repo: Path) -> None:
    changed = command(["git", "diff", "--name-only", "-z"], cwd=repo).split("\0")
    if any(path and not any(path == allowed or path.startswith(allowed + "/") for allowed in OUTPUT_PATHS) for path in changed):
        raise WorkflowError("A tracked change is outside the translation output paths.")
    command(["git", "add", "--", *OUTPUT_PATHS], cwd=repo)
    command(["git", "diff", "--cached", "--check"], cwd=repo)
    if not command(["git", "diff", "--cached", "--name-only"], cwd=repo).strip():
        print("No translation changes to publish.")
        return
    command(["git", "config", "user.name", "github-actions[bot]"], cwd=repo)
    command(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], cwd=repo)
    command(["git", "commit", "-m", "发布：英文和日文 AI 安全日报"], cwd=repo)
    # A concurrent publisher's update rejects this normal push. Retry next run;
    # do not force, rebase over an unverified source, or modify Chinese exports.
    command(["git", "push", "origin", "HEAD:" + os.environ["TRANSLATION_DEFAULT_BRANCH"]], cwd=repo, timeout=300)


def run(args: argparse.Namespace) -> dict:
    repo = args.repo_root.resolve()
    if args.mode == "translate":
        guard_runtime()
    if args.publish:
        if args.mode != "translate":
            raise WorkflowError("A dry run cannot publish.")
        guard_publish(repo)
    temporary_base = os.environ.get("RUNNER_TEMP")
    deadline = time.monotonic() + 240 * 60

    def remaining() -> int:
        seconds = int(deadline - time.monotonic())
        if seconds <= 0:
            raise WorkflowError("The translation workflow exhausted its four-hour runtime budget.")
        return seconds

    with tempfile.TemporaryDirectory(prefix="aisafetyhot-translation-", dir=temporary_base) as directory:
        temp_root = Path(directory)
        git_root = temp_root / "source.git"
        stage = temp_root / "source-before"
        revision, dates = fetch_source(git_root, stage)
        plan = run_core(repo, stage, revision, "--dry-run", timeout=remaining())
        if args.mode == "dry-run":
            return plan
        print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
        process = None
        log = None
        result = {"mode": "translate", "dates": [], "local_requests": 0, "api_calls": 0}
        try:
            # Publish the newest digest first. Each date has a separate request
            # budget so a catch-up backlog cannot starve current daily updates.
            for day in sorted(plan["dates"], key=lambda value: value["date"], reverse=True):
                source_date = day["date"]
                missing = sum(language["missing_units"] for language in day["languages"].values())
                options = ["--date", source_date]
                if missing:
                    if process is None:
                        remaining()
                        process, log = start_server(temp_root)
                else:
                    print(f"{source_date}: complete cached texts; refresh offline without a model request.", flush=True)
                    options.append("--offline")
                day_result = run_core(repo, stage, revision, *options, timeout=remaining())
                remaining()
                latest_stage = temp_root / ("source-verified-" + source_date)
                latest_revision, latest_dates = fetch_source(git_root, latest_stage)
                if dates != latest_dates:
                    raise WorkflowError("The upstream digest dates changed during translation; do not publish this date, retry next run.")
                run_core(repo, latest_stage, latest_revision, "--date", source_date, "--verify-source", timeout=remaining())
                if args.publish:
                    publish(repo)
                result["dates"].extend(day_result["dates"])
                calls = day_result.get("local_requests", day_result.get("api_calls", 0))
                result["local_requests"] += calls
                result["api_calls"] += calls
        finally:
            if process is not None:
                stop_server(process, log)
        return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--mode", choices=("dry-run", "translate"), default="dry-run")
    parser.add_argument("--publish", action="store_true", help="Publish only from the enabled public default-branch workflow.")
    args = parser.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except WorkflowError as exc:
        print(f"Translation workflow failed: {exc} No further commit or push will be attempted.", file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError):
        print("Translation workflow failed; no further commit or push will be attempted. Check pinned downloads, local inference, source consistency, and branch concurrency.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
