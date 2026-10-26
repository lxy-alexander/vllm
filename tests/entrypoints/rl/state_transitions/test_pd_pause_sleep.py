# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause/resume and sleep/wake_up of a 1P1D pair over MooncakeConnector (TCP).

The cases are grouped first by the entry point's arguments, then by the
transfer stage a request is at when the call arrives:

    test_pause_resume    /pause  3 mode  x 2 clear_cache x 3 target x 8 stage = 144
    test_sleep_wake_up   /sleep  3 level x 3 mode        x 3 target x 8 stage = 216

target is P, D or both (both are called at once, as an RL driver does).
Each case drives requests straight to P and D, waits until they sit at the
stage, stops the target, starts it again (/resume or /wake_up; after a level
2 sleep: wake the weights, reload_weights, then wake the KV cache), and checks
that every request ends, wait and keep drop nothing, both sides go idle, and
greedy probes through the proxy still match their output from before the case.

Needs 2 GPUs and the mooncake-transfer-engine package. Knobs:
    PD_REUSE_STACK=1      reuse P/D across cases that pass and leave it clean
    PD_PAUSE_LIMIT_S      longest a /pause or /sleep may take (default 60)
    PD_PAUSE_TIMEOUT_S    HTTP timeout of /pause and /sleep (default 90)
    PD_DRAIN_TIMEOUT_S    time for requests to end after the restart (180)
    PD_TEST_LOG_DIR       keep P, D and proxy logs per case
"""

import contextlib
import itertools
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import requests

from tests.entrypoints.rl.conftest import (
    MODEL_NAME,
    gen,
    is_paused,
    is_sleeping,
    ok,
    resume,
    wake,
)

P_PORT = 8810
D_PORT = 8811
BOOTSTRAP_PORT = 8898
PROXY_PORT = 8812

# P prefills in small chunks so a long prompt stays in prefill for seconds,
# long enough to pause while a request is still at a given transfer stage.
P_PREFILL_CHUNK = 32
MAX_MODEL_LEN = 8192
MAX_NUM_SEQS = 32

# A pause or sleep that works returns within seconds; a stuck pull hangs for
# 480 s, so a run can shorten these limits to give up on failures sooner.
PAUSE_LIMIT_S = float(os.environ.get("PD_PAUSE_LIMIT_S", 60))
PAUSE_TIMEOUT_S = float(os.environ.get("PD_PAUSE_TIMEOUT_S", 90))
STAGE_TIMEOUT_S = 60
DRAIN_TIMEOUT_S = float(os.environ.get("PD_DRAIN_TIMEOUT_S", 180))
IDLE_TIMEOUT_S = 30
PROBE_PROMPTS = [
    "The capital of France is",
    "Water boils at a temperature of",
    "The largest planet in the solar system is",
]


def _free_port(port: int) -> bool:
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _wait_for_server(
    url: str,
    process: subprocess.Popen,
    timeout: float = 180,
    path: str = "/health",
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = ""
            if process.stderr is not None:
                process.stderr.seek(0)
                stderr = process.stderr.read().decode(errors="replace")
            raise RuntimeError(
                f"server exited with code {process.returncode}:\n{stderr}"
            )
        try:
            if requests.get(f"{url}{path}", timeout=3).status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise TimeoutError(f"server did not become ready: {url}")


def case_log_dir() -> Path | None:
    """This test's log directory under PD_TEST_LOG_DIR, or None when unset."""
    log_dir = os.environ.get("PD_TEST_LOG_DIR")
    if not log_dir:
        return None
    test = os.environ.get("PYTEST_CURRENT_TEST", "pd").split(" ")[0]
    return Path(log_dir) / re.sub(r"[^\w.-]+", "_", test)


@contextmanager
def pd_stack(sleep_mode: bool = False, log_dir: Path | None = None):
    for port in (P_PORT, D_PORT, BOOTSTRAP_PORT, PROXY_PORT):
        if not _free_port(port):
            raise RuntimeError(f"required test port is busy: {port}")

    env = {**os.environ, "VLLM_SERVER_DEV_MODE": "1", "MC_FORCE_TCP": "1"}
    base_args = [
        "--dtype",
        "bfloat16",
        "--max-model-len",
        str(MAX_MODEL_LEN),
        "--max-num-seqs",
        str(MAX_NUM_SEQS),
        "--gpu-memory-utilization",
        "0.35",
        "--enforce-eager",
        "--enable-prefix-caching",
    ]
    if sleep_mode:
        base_args.append("--enable-sleep-mode")
    p_config = json.dumps(
        {"kv_connector": "MooncakeConnector", "kv_role": "kv_producer"}
    )
    d_config = json.dumps(
        {"kv_connector": "MooncakeConnector", "kv_role": "kv_consumer"}
    )
    processes = []
    with contextlib.ExitStack() as logs:

        def _output(name: str):
            """(stdout, stderr) for a server; kept under log_dir when set,
            else discarded."""
            if log_dir is None:
                return subprocess.DEVNULL, logs.enter_context(tempfile.TemporaryFile())
            log_dir.mkdir(parents=True, exist_ok=True)
            return logs.enter_context(open(log_dir / f"{name}.log", "wb")), (
                subprocess.STDOUT
            )

        try:
            for gpu, port, config, role in (
                ("0", P_PORT, p_config, "prefill"),
                ("1", D_PORT, d_config, "decode"),
            ):
                role_env = {**env, "CUDA_VISIBLE_DEVICES": gpu}
                role_args = []
                if role == "prefill":
                    role_env["VLLM_MOONCAKE_BOOTSTRAP_PORT"] = str(BOOTSTRAP_PORT)
                    role_args = ["--max-num-batched-tokens", str(P_PREFILL_CHUNK)]
                # A file, not a pipe: nothing drains a pipe while the test runs,
                # and a full pipe would block the server like a real hang.
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "vllm.entrypoints.openai.api_server",
                        "--model",
                        MODEL_NAME,
                        "--port",
                        str(port),
                        "--served-model-name",
                        "m",
                        *base_args,
                        *role_args,
                        "--kv-transfer-config",
                        config,
                    ],
                    env=role_env,
                    stdout=(output := _output(role))[0],
                    stderr=output[1],
                )
                processes.append(process)

            p_url = f"http://127.0.0.1:{P_PORT}"
            d_url = f"http://127.0.0.1:{D_PORT}"
            _wait_for_server(p_url, processes[0])
            _wait_for_server(d_url, processes[1])
            proxy = subprocess.Popen(
                [
                    sys.executable,
                    "examples/disaggregated/mooncake_connector/mooncake_connector_proxy.py",
                    "--prefill",
                    p_url,
                    str(BOOTSTRAP_PORT),
                    "--decode",
                    d_url,
                    "--port",
                    str(PROXY_PORT),
                ],
                env=env,
                stdout=(output := _output("proxy"))[0],
                stderr=output[1],
            )
            processes.append(proxy)
            _wait_for_server(f"http://127.0.0.1:{PROXY_PORT}", proxy, path="/")
            # A server that lost a port race exits, while /health is answered
            # by whoever holds the port; only our own live processes count.
            exited = [p.args[-1] for p in processes if p.poll() is not None]
            assert not exited, f"servers exited during startup: {exited}"
            yield p_url, d_url, f"http://127.0.0.1:{PROXY_PORT}"
        finally:
            for process in reversed(processes):
                process.terminate()
            for process in reversed(processes):
                with contextlib.suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=10)
                if process.poll() is None:
                    process.kill()


@dataclass
class _Stack:
    """A running P/D pair with its logs."""

    sleep_mode: bool
    urls: tuple[str, str, str]
    log_dir: Path | None
    close: Callable[[], None]
    # Log sizes when the current case started; scan_logs reads past them.
    log_offsets: dict[str, int] = field(default_factory=dict)

    def mark_logs(self):
        if self.log_dir is not None:
            for name in ("prefill", "decode"):
                path = self.log_dir / f"{name}.log"
                self.log_offsets[name] = path.stat().st_size if path.exists() else 0


# By default every case gets a fresh pair: a transfer stuck by one case (a
# pull held for VLLM_MOONCAKE_ABORT_REQUEST_TIMEOUT) must not fail the cases
# after it. PD_REUSE_STACK=1 keeps a pair across cases that pass and leave it
# clean, and starts a fresh one after any failure.
_REUSE_STACK = os.environ.get("PD_REUSE_STACK") == "1"
# One pair at a time: they share the ports.
_idle_stack: _Stack | None = None
_current_stack: _Stack | None = None


def _start_stack(sleep_mode: bool, log_dir: Path | None) -> _Stack:
    stack = pd_stack(sleep_mode, log_dir)
    urls = stack.__enter__()
    return _Stack(sleep_mode, urls, log_dir, lambda: stack.__exit__(None, None, None))


def _is_clean(urls: tuple[str, str, str]) -> bool:
    """Both sides serve, run nothing, hold no transfer, and reset their cache."""
    try:
        for url in urls[:2]:
            if requests.get(f"{url}/health", timeout=5).status_code != 200:
                return False
            if is_paused(url) or is_sleeping(url):
                return False
            values = metrics(url)
            stages = ("waiting_to_start", "in_progress", "completed_waiting")
            if num_requests(values) or any(kv_fetch(values, s) for s in stages):
                return False
            response = requests.post(
                f"{url}/reset_prefix_cache", params={"reset_external": True}, timeout=30
            )
            if response.json() != {"success": True}:
                return False
    except (requests.RequestException, ValueError, KeyError):
        return False
    return True


@pytest.fixture(scope="module", autouse=True)
def _close_idle_stack():
    """Stop the pair PD_REUSE_STACK kept once the last case has run."""
    global _idle_stack
    yield
    if _idle_stack is not None:
        _idle_stack.close()
        _idle_stack = None


def _pd_fixture(request: pytest.FixtureRequest, sleep_mode: bool):
    global _idle_stack, _current_stack
    stack, _idle_stack = _idle_stack, None
    if stack is not None and (
        stack.sleep_mode != sleep_mode or not _is_clean(stack.urls)
    ):
        stack.close()
        stack = None
    if stack is None:
        stack = _start_stack(sleep_mode, case_log_dir())
    stack.mark_logs()
    if stack.log_dir is not None:
        request.node.user_properties.append(("pd_log_dir", str(stack.log_dir)))
    _current_stack = stack
    failed_before = request.session.testsfailed
    try:
        yield stack.urls
    finally:
        _current_stack = None
        # The call phase is reported before fixtures tear down, so a failed
        # case has already raised testsfailed here.
        if _REUSE_STACK and request.session.testsfailed == failed_before:
            _idle_stack = stack
        else:
            stack.close()


@pytest.fixture
def pd_urls(request):
    yield from _pd_fixture(request, sleep_mode=False)


@pytest.fixture
def pd_sleep_urls(request, tmp_path, monkeypatch):
    """pd_urls with --enable-sleep-mode; logs are always kept, since the sleep
    cases scan them for crashes a 200 response can hide."""
    if not os.environ.get("PD_TEST_LOG_DIR"):
        monkeypatch.setenv("PD_TEST_LOG_DIR", str(tmp_path))
    yield from _pd_fixture(request, sleep_mode=True)


_METRIC_RE = re.compile(r"^(vllm:[a-z_]+)\{([^}]*)\} (\S+)$", re.M)
_STAGE_RE = re.compile(r'stage="([a-z_]+)"')


def metrics(url: str) -> dict[str, float]:
    """Sum Prometheus samples by name, keyed `name:stage` when staged."""
    values: dict[str, float] = {}
    text = requests.get(f"{url}/metrics", timeout=5).text
    for name, labels, value in _METRIC_RE.findall(text):
        stage = _STAGE_RE.search(labels)
        key = f"{name}:{stage.group(1)}" if stage else name
        values[key] = values.get(key, 0.0) + float(value)
    return values


def kv_fetch(values: dict[str, float], stage: str) -> float:
    return values.get(f"vllm:num_requests_kv_fetch_by_stage:{stage}", 0.0)


def num_requests(values: dict[str, float]) -> float:
    return values.get("vllm:num_requests_running", 0.0) + values.get(
        "vllm:num_requests_waiting", 0.0
    )


def wait_for(condition: Callable[[], bool], what: str, timeout: float):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.02)
    pytest.fail(f"timed out after {timeout}s waiting for: {what}")


_prompt_ids = itertools.count()


def token_prompt(num_tokens: int) -> list[int]:
    # Token ids give an exact length; a unique first token keeps P's prefix
    # cache from turning a later prefill into an instant hit.
    return [1000 + next(_prompt_ids)] + [2000] * (num_tokens - 1)


def timed_post(url: str, path: str, **params) -> tuple[int | None, float]:
    start = time.monotonic()
    try:
        status = requests.post(
            f"{url}{path}", params=params, timeout=PAUSE_TIMEOUT_S
        ).status_code
    except requests.RequestException:
        status = None
    return status, time.monotonic() - start


def timed_pause(
    url: str, mode: str = "abort", clear_cache: bool = True
) -> tuple[int | None, float]:
    return timed_post(url, "/pause", mode=mode, clear_cache=clear_cache)


def reload_weights(url: str):
    """Write the weights again after a level 2 sleep discarded them."""
    requests.post(
        f"{url}/collective_rpc", json={"method": "reload_weights"}, timeout=300
    ).raise_for_status()


@dataclass(frozen=True)
class Control:
    """The stop/start pair a case drives: pause/resume, or sleep/wake_up."""

    name: str
    # None for pause; the sleep level otherwise.
    level: int | None = None

    @property
    def stop_path(self) -> str:
        return "/pause" if self.level is None else "/sleep"

    def stop(self, url: str, mode: str, clear_cache: bool):
        if self.level is None:
            return timed_pause(url, mode, clear_cache)
        # A sleep clears the cache by its level, not by clear_cache.
        return timed_post(url, "/sleep", level=self.level, mode=mode)

    def stopped(self, url: str) -> bool:
        return is_paused(url) if self.level is None else is_sleeping(url)

    def start(self, url: str) -> int:
        if self.level is None:
            return resume(url)
        if self.level == 0:
            # A level 0 sleep only paused scheduling.
            return wake(url, ["scheduling"])
        if self.level == 1:
            return wake(url)
        # Level 2 discarded the weights: write them back before the KV cache
        # wakes, since a full wake_up resumes the scheduler.
        status = wake(url, ["weights"])
        if status != 200:
            return status
        reload_weights(url)
        return wake(url, ["kv_cache"])


PAUSE = Control("pause")

# Crashes a sleep can cause by freeing KV memory a transfer still uses. A
# control call can still return 200 while one of these happens.
FATAL_LOG_RE = re.compile(
    r"illegal memory access|CUDA error|Segmentation fault|core dumped|"
    r"EngineDeadError|EngineCore encountered a fatal error|"
    r"Error in Mooncake sender thread",
    re.I,
)
# Transfers that failed. Expected when one side aborts, so they are reported
# but do not fail a case on their own.
TRANSFER_ERROR_RE = re.compile(
    r"Sending to \S+ failed|pulling kv_caches for .* failed", re.I
)


def scan_logs() -> tuple[list[str], int]:
    """(fatal lines, transfer error count) in P's and D's logs since this
    test started."""
    stack = _current_stack
    fatal: list[str] = []
    transfer_errors = 0
    if stack is None or stack.log_dir is None:
        return fatal, transfer_errors
    for name in ("prefill", "decode"):
        path = stack.log_dir / f"{name}.log"
        if not path.exists():
            continue
        with open(path, "rb") as f:
            f.seek(stack.log_offsets.get(name, 0))
            text = f.read().decode(errors="replace")
        for line in text.splitlines():
            if FATAL_LOG_RE.search(line):
                fatal.append(f"{name}: {line.strip()[:200]}")
            elif TRANSFER_ERROR_RE.search(line):
                transfer_errors += 1
    return fatal, transfer_errors


def assert_logs_clean(record_property: Callable[[str, object], None] | None = None):
    fatal, transfer_errors = scan_logs()
    if record_property is not None:
        record_property("transfer_errors", transfer_errors)
    assert not fatal, f"fatal errors in logs: {fatal[:5]}"


def probe_texts(proxy_url: str) -> list[str | None]:
    texts = []
    for prompt in PROBE_PROMPTS:
        response = gen(proxy_url, prompt=prompt, max_tokens=16, timeout=60)
        texts.append(response["choices"][0]["text"] if ok(response) else None)
    return texts


def assert_pauses_ok(
    pauses: list[tuple[int | None, float]],
    context: str,
    names: tuple[str, ...] = ("P", "D"),
    op: str = "/pause",
):
    """Every control call returned 200 within PAUSE_LIMIT_S."""
    failed = [
        f"{name} status {status} after {seconds:.1f}s"
        for name, (status, seconds) in zip(names, pauses)
        if status != 200 or seconds > PAUSE_LIMIT_S
    ]
    assert not failed, f"{op} failed: {'; '.join(failed)}; {context}"


def join_all(threads: list[threading.Thread], timeout: float) -> int:
    """Join threads against one shared deadline; return how many still run."""
    deadline = time.monotonic() + timeout
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    return sum(thread.is_alive() for thread in threads)


def assert_idle_and_probes_match(
    prefill_url: str, decode_url: str, proxy_url: str, reference: list[str | None]
):
    wait_for(
        lambda: num_requests(metrics(prefill_url)) == 0
        and num_requests(metrics(decode_url)) == 0,
        "P and D idle after resume",
        IDLE_TIMEOUT_S,
    )
    assert probe_texts(proxy_url) == reference


@dataclass
class PDRequest:
    """One request driven straight to P and D, as the example proxy does."""

    prompt: list[int]
    transfer_id: str
    prefill_done: threading.Event = field(default_factory=threading.Event)
    decode_sent: threading.Event = field(default_factory=threading.Event)
    decode_done: threading.Event = field(default_factory=threading.Event)
    tokens: int = 0
    finish_reason: str | None = None
    threads: list[threading.Thread] = field(default_factory=list)

    @property
    def stage(self) -> str:
        if self.decode_done.is_set():
            return "done"
        if self.tokens:
            return "d_decode"
        if self.prefill_done.is_set():
            return "transfer_active" if self.decode_sent.is_set() else "p_done"
        if self.decode_sent.is_set():
            return "d_pull_waiting"
        return "p_prefill"


class PDDriver:
    def __init__(self, prefill_url: str, decode_url: str):
        self.prefill_url = prefill_url
        self.decode_url = decode_url
        bootstrap = f"http://127.0.0.1:{BOOTSTRAP_PORT}"
        engines = requests.get(f"{bootstrap}/query", timeout=10).json()
        self.decode_params = {
            "do_remote_decode": False,
            "do_remote_prefill": True,
            "remote_bootstrap_addr": bootstrap,
            "remote_engine_id": engines["0"]["engine_id"],
        }
        self.requests: list[PDRequest] = []
        self.locals: list[PDRequest] = []

    def new(self, num_tokens: int) -> PDRequest:
        req = PDRequest(token_prompt(num_tokens), f"xfer-{len(self.requests)}")
        self.requests.append(req)
        return req

    def local(self, url: str, num_tokens: int, max_tokens: int) -> PDRequest:
        """A plain request served by one instance, with no KV transfer."""
        req = PDRequest(token_prompt(num_tokens), transfer_id="")
        self.locals.append(req)

        def run():
            with contextlib.suppress(requests.RequestException):
                requests.post(
                    f"{url}/v1/completions",
                    json={
                        "model": "m",
                        "prompt": req.prompt,
                        "max_tokens": max_tokens,
                        "temperature": 0,
                        "ignore_eos": True,
                    },
                    timeout=600,
                )
            req.decode_done.set()

        self._spawn(req, run)
        return req

    def threads(self) -> list[threading.Thread]:
        return [t for req in self.requests + self.locals for t in req.threads]

    def _spawn(self, req: PDRequest, target: Callable[[], None]):
        thread = threading.Thread(target=target, daemon=True)
        req.threads.append(thread)
        thread.start()

    def prefill(self, req: PDRequest):
        def run():
            with contextlib.suppress(requests.RequestException):
                requests.post(
                    f"{self.prefill_url}/v1/completions",
                    json={
                        "model": "m",
                        "prompt": req.prompt,
                        "max_tokens": 1,
                        "temperature": 0,
                        "kv_transfer_params": {
                            "do_remote_decode": True,
                            "do_remote_prefill": False,
                            "transfer_id": req.transfer_id,
                        },
                    },
                    timeout=600,
                )
            req.prefill_done.set()

        self._spawn(req, run)

    def decode(self, req: PDRequest, max_tokens: int):
        def run():
            try:
                with requests.post(
                    f"{self.decode_url}/v1/completions",
                    json={
                        "model": "m",
                        "prompt": req.prompt,
                        "max_tokens": max_tokens,
                        "temperature": 0,
                        "ignore_eos": True,
                        "stream": True,
                        "kv_transfer_params": {
                            **self.decode_params,
                            "transfer_id": req.transfer_id,
                        },
                    },
                    stream=True,
                    timeout=(5, 600),
                ) as response:
                    req.decode_sent.set()
                    for line in response.iter_lines(decode_unicode=True):
                        if not line.startswith("data: {"):
                            continue
                        choice = json.loads(line[6:])["choices"][0]
                        if choice.get("text"):
                            req.tokens += 1
                        req.finish_reason = (
                            choice.get("finish_reason") or req.finish_reason
                        )
            except requests.RequestException:
                pass
            finally:
                req.decode_sent.set()
                req.decode_done.set()

        self._spawn(req, run)

    def stages(self) -> list[str]:
        return [req.stage for req in self.requests]

    def count(self, stage: str) -> int:
        return self.stages().count(stage)

    def d_pulls_started(self) -> bool:
        """Every request sent to D has been scheduled and issued its pull."""
        values = metrics(self.decode_url)
        sent = sum(req.decode_sent.is_set() for req in self.requests)
        finished = sum(req.decode_done.is_set() for req in self.requests)
        return (
            num_requests(values) >= sent - finished
            and kv_fetch(values, "waiting_to_start") == 0
        )

    def transfer_in_flight(self) -> bool:
        """D is loading KV for a request whose prefill already finished."""
        values = metrics(self.decode_url)
        return self.count("transfer_active") > 0 and kv_fetch(
            values, "in_progress"
        ) > self.count("d_pull_waiting")


# ---------------------------------------------------------------------------
# Pause cases: (P, D or both) x /pause's (mode, clear_cache) at a stage
# ---------------------------------------------------------------------------

STAGE_PROMPT_TOKENS = 4000
DECODE_TOKENS = 256
FILLER_TOKENS = 512

_CELLS = {
    ("abort", True): "abort",
    ("abort", False): "abort_nc",
    ("wait", True): "wait",
    ("wait", False): "wait_nc",
    ("keep", True): "keep_clear",
    ("keep", False): "keep_nc",
}


@dataclass
class Stage:
    """A request state to pause at, checked again right before pausing."""

    reached: Callable[[], bool]
    # Requests the proxy has sent to P but whose D half is still on its way;
    # it reaches D once the pause has started on every target.
    late_decodes: list[PDRequest] = field(default_factory=list)


def pause_params(stage: str):
    """Every pause case at `stage`: /pause's mode and
    clear_cache on each target.

    No target or nc cell is left out: a keep pause queues requests instead of
    rejecting them, so a late D half reaches a paused D, and P still holds KV
    that a D which has not pulled yet will ask for.
    """
    return [
        pytest.param(
            target,
            mode,
            clear_cache,
            id=f"pause_{_CELLS[mode, clear_cache]}_{target}_{stage}",
        )
        for target in ("both", "P", "D")
        for mode in ("abort", "wait", "keep")
        for clear_cache in (True, False)
    ]


def run_case(
    pd_urls: tuple[str, str, str],
    target: str,
    mode: str,
    clear_cache: bool,
    setup: Callable[[PDDriver], Stage],
    control: Control = PAUSE,
):
    """Stop `target` at the stage `setup` reaches (pause, or sleep with
    `control`), start it again, check recovery."""
    prefill_url, decode_url, proxy_url = pd_urls
    reference = probe_texts(proxy_url)
    assert None not in reference, reference

    driver = PDDriver(prefill_url, decode_url)
    stage = setup(driver)
    urls = {"P": prefill_url, "D": decode_url}
    names = ("P", "D") if target == "both" else (target,)
    reached = stage.reached()
    sent_before_pause = [req for req in driver.requests if req.decode_sent.is_set()]
    with ThreadPoolExecutor(max_workers=len(names)) as pool:
        try:
            futures = [
                pool.submit(control.stop, urls[name], mode, clear_cache)
                for name in names
            ]
            wait_for(
                lambda: all(
                    future.done() or control.stopped(urls[name])
                    for name, future in zip(names, futures)
                ),
                "pause state set on every target",
                STAGE_TIMEOUT_S,
            )
            for req in stage.late_decodes:
                driver.decode(req, max_tokens=DECODE_TOKENS)
            pauses = [future.result() for future in futures]
        finally:
            resumed = [control.start(urls[name]) for name in names]

    assert reached, "setup error: the stage was gone at pause time"
    if control.level is not None:
        # A crash shows up as a timeout below; report its cause instead.
        assert_logs_clean()
    assert_pauses_ok(pauses, f"target {target}, mode {mode}", names, control.stop_path)
    assert resumed == [200] * len(names), resumed

    stuck = join_all(driver.threads(), DRAIN_TIMEOUT_S)
    assert not stuck, f"{stuck} requests still open {DRAIN_TIMEOUT_S}s after resume"
    if mode == "keep":
        # keep freezes requests; none may be dropped.
        ends = [
            req.finish_reason for req in driver.requests if req.decode_sent.is_set()
        ]
        assert all(end == "length" for end in ends), f"keep dropped requests: {ends}"
    elif mode == "wait":
        # wait finishes what reached D before the pause; later ones get a 503.
        # A sleep queues later ones instead, so all of them must finish.
        waited = sent_before_pause if control.level is None else driver.requests
        ends = [req.finish_reason for req in waited if req.decode_sent.is_set()]
        assert all(end == "length" for end in ends), f"wait dropped requests: {ends}"
    assert_idle_and_probes_match(prefill_url, decode_url, proxy_url, reference)
    if control.level is not None:
        assert_logs_clean()


# ---------------------------------------------------------------------------
# Sleep cases: (P, D or both) x /sleep's (level, mode) at a stage
# ---------------------------------------------------------------------------


def sleep_params(stage: str):
    """Every sleep case at `stage`: /sleep's level and mode on
    each target.

    Unlike pause, no target or level is left out. A sleep queues
    requests instead of rejecting them, so a late D half reaches a sleeping D,
    and level 0 still differs from pause nc in what it accepts meanwhile.
    """
    return [
        pytest.param(level, mode, target, id=f"sleep{level}_{mode}_{target}_{stage}")
        for target in ("both", "P", "D")
        for level in (0, 1, 2)
        for mode in ("abort", "wait", "keep")
    ]


def run_sleep_case(
    pd_urls: tuple[str, str, str],
    target: str,
    level: int,
    mode: str,
    setup: Callable[[PDDriver], Stage],
):
    """Sleep `target` at the stage `setup` reaches, wake it, check recovery."""
    run_case(
        pd_urls,
        target,
        mode,
        level >= 1,
        setup,
        control=Control(f"sleep{level}", level=level),
    )


# ---------------------------------------------------------------------------
# Stages: each setup drives requests to one transfer stage and returns a
# check that they are still there
# ---------------------------------------------------------------------------


def _stage_p_queued(driver: PDDriver) -> Stage:
    """Pause or sleep while P still queues the request and D has not received it."""
    # A plain prefill takes P's whole per-step token budget, so the target
    # waits in P's queue behind it.
    driver.local(driver.prefill_url, STAGE_PROMPT_TOKENS, max_tokens=1)
    wait_for(
        lambda: metrics(driver.prefill_url).get("vllm:num_requests_running", 0) >= 1,
        "P running the blocking prefill",
        STAGE_TIMEOUT_S,
    )
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)

    def reached() -> bool:
        waiting = metrics(driver.prefill_url).get("vllm:num_requests_waiting", 0)
        return not req.prefill_done.is_set() and waiting >= 1

    wait_for(reached, "target queued on P", STAGE_TIMEOUT_S)
    return Stage(reached, late_decodes=[req])


def _stage_p_prefill(driver: PDDriver) -> Stage:
    """Pause or sleep while P computes the request's KV and D has not received it."""
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)

    def reached() -> bool:
        running = metrics(driver.prefill_url).get("vllm:num_requests_running", 0)
        return not req.prefill_done.is_set() and running >= 1

    wait_for(reached, "P prefilling the request", STAGE_TIMEOUT_S)
    return Stage(reached, late_decodes=[req])


def _stage_p_done_unpulled(driver: PDDriver) -> Stage:
    """Pause or sleep after P finished the KV but before D received the request."""
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)

    def reached() -> bool:
        # P returned and holds the blocks for a pull D has not sent.
        return (
            req.prefill_done.is_set()
            and not req.decode_sent.is_set()
            and num_requests(metrics(driver.prefill_url)) == 0
        )

    wait_for(reached, "P done, KV not pulled", STAGE_TIMEOUT_S)
    return Stage(reached, late_decodes=[req])


def _stage_d_waiting_to_start(driver: PDDriver) -> Stage:
    """Pause or sleep while D holds the request but has not sent its pull to P."""
    # D skips connector matching while every run slot is taken, so a new
    # request stays waiting_to_start until a slot frees.
    for _ in range(MAX_NUM_SEQS):
        driver.local(driver.decode_url, 16, max_tokens=FILLER_TOKENS)
    wait_for(
        lambda: metrics(driver.decode_url).get("vllm:num_requests_running", 0)
        >= MAX_NUM_SEQS,
        "D run slots full",
        STAGE_TIMEOUT_S,
    )
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)
    driver.decode(req, max_tokens=DECODE_TOKENS)

    def reached() -> bool:
        return kv_fetch(metrics(driver.decode_url), "waiting_to_start") >= 1

    wait_for(reached, "D holding the request before its pull", STAGE_TIMEOUT_S)
    return Stage(reached)


def _stage_d_pull_waiting(driver: PDDriver) -> Stage:
    """Pause or sleep while D's pulls wait on prefills P has not finished."""
    reqs = [driver.new(STAGE_PROMPT_TOKENS) for _ in range(4)]
    for req in reqs:
        driver.prefill(req)
    wait_for(
        lambda: metrics(driver.prefill_url).get("vllm:num_requests_running", 0) >= 1,
        "P prefilling",
        STAGE_TIMEOUT_S,
    )
    for req in reqs:
        driver.decode(req, max_tokens=128)

    def reached() -> bool:
        return driver.count("d_pull_waiting") == len(reqs) and driver.d_pulls_started()

    wait_for(reached, "D pulling requests P has not finished", STAGE_TIMEOUT_S)
    return Stage(reached)


def _stage_transfer_active(driver: PDDriver) -> Stage:
    """Pause or sleep while P sends the request's KV to D."""
    # One request: with more, P finishes them one at a time and the later
    # ones still wait on P while the first transfers.
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)
    driver.decode(req, max_tokens=DECODE_TOKENS)
    wait_for(driver.transfer_in_flight, "P sending KV to D", STAGE_TIMEOUT_S)
    return Stage(driver.transfer_in_flight)


def _stage_d_loaded_unscheduled(driver: PDDriver) -> Stage:
    """Pause or sleep after D loaded the request's KV but before it scheduled it."""
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)
    driver.decode(req, max_tokens=DECODE_TOKENS)
    wait_for(
        lambda: kv_fetch(metrics(driver.decode_url), "in_progress") >= 1,
        "D loading the request",
        STAGE_TIMEOUT_S,
    )
    # Fill D's run slots while the load runs, so the loaded request queues.
    for _ in range(MAX_NUM_SEQS):
        driver.local(driver.decode_url, 16, max_tokens=FILLER_TOKENS)

    def reached() -> bool:
        return kv_fetch(metrics(driver.decode_url), "completed_waiting") >= 1

    wait_for(reached, "D loaded, request not scheduled", STAGE_TIMEOUT_S)
    return Stage(reached)


def _stage_d_decode(driver: PDDriver) -> Stage:
    """Pause or sleep while D decodes the request with KV loaded from P."""
    req = driver.new(32)
    driver.prefill(req)
    driver.decode(req, max_tokens=DECODE_TOKENS)

    def reached() -> bool:
        return req.tokens >= 8 and not req.decode_done.is_set()

    wait_for(reached, "D decoding", STAGE_TIMEOUT_S)
    return Stage(reached)


STAGES: dict[str, Callable[[PDDriver], Stage]] = {
    "p_queued": _stage_p_queued,
    "p_prefill": _stage_p_prefill,
    "p_done_unpulled": _stage_p_done_unpulled,
    "d_waiting_to_start": _stage_d_waiting_to_start,
    "d_pull_waiting": _stage_d_pull_waiting,
    "transfer_active": _stage_transfer_active,
    "d_loaded_unscheduled": _stage_d_loaded_unscheduled,
    "d_decode": _stage_d_decode,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache", "stage"),
    [
        pytest.param(*param.values, stage, id=f"{param.id}")
        for stage in STAGES
        for param in pause_params(stage)
    ],
)
def test_pause_resume(pd_urls, target, mode, clear_cache, stage):
    """/pause?mode=&clear_cache= on `target` at `stage`, then /resume."""
    run_case(pd_urls, target, mode, clear_cache, STAGES[stage])


@pytest.mark.parametrize(
    ("level", "mode", "target", "stage"),
    [
        pytest.param(*param.values, stage, id=f"{param.id}")
        for stage in STAGES
        for param in sleep_params(stage)
    ],
)
def test_sleep_wake_up(pd_sleep_urls, level, mode, target, stage):
    """/sleep?level=&mode= on `target` at `stage`, then /wake_up."""
    run_sleep_case(pd_sleep_urls, target, level, mode, STAGES[stage])
