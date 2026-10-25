# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Shared 1P1D (MooncakeConnector over TCP) harness for the pause tests."""

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

from tests.entrypoints.rl.conftest import MODEL_NAME, gen, is_paused, ok, resume

P_PORT = 8810
D_PORT = 8811
BOOTSTRAP_PORT = 8898
PROXY_PORT = 8812

# P prefills in small chunks so a long prompt stays in prefill for seconds,
# long enough to pause while a request is still at a given transfer stage.
P_PREFILL_CHUNK = 32
MAX_MODEL_LEN = 8192
MAX_NUM_SEQS = 32

PAUSE_LIMIT_S = 60
PAUSE_TIMEOUT_S = 90
STAGE_TIMEOUT_S = 60
DRAIN_TIMEOUT_S = 180
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


@contextmanager
def pd_stack():
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
    p_config = json.dumps(
        {"kv_connector": "MooncakeConnector", "kv_role": "kv_producer"}
    )
    d_config = json.dumps(
        {"kv_connector": "MooncakeConnector", "kv_role": "kv_consumer"}
    )
    processes = []
    with contextlib.ExitStack() as logs:

        def _output(name: str):
            """(stdout, stderr) for a server; kept per test under
            PD_TEST_LOG_DIR when set, else discarded."""
            log_dir = os.environ.get("PD_TEST_LOG_DIR")
            if not log_dir:
                return subprocess.DEVNULL, logs.enter_context(tempfile.TemporaryFile())
            test = os.environ.get("PYTEST_CURRENT_TEST", "pd").split(" ")[0]
            case_dir = Path(log_dir) / re.sub(r"[^\w.-]+", "_", test)
            case_dir.mkdir(parents=True, exist_ok=True)
            return logs.enter_context(open(case_dir / f"{name}.log", "wb")), (
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


# A fresh pair per test: a transfer stuck by one case (e.g. R1 holds D for
# VLLM_MOONCAKE_ABORT_REQUEST_TIMEOUT) must not fail the cases after it.
@pytest.fixture
def pd_urls():
    with pd_stack() as urls:
        yield urls


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


def timed_pause(
    url: str, mode: str = "abort", clear_cache: bool = True
) -> tuple[int | None, float]:
    start = time.monotonic()
    try:
        status = requests.post(
            f"{url}/pause",
            params={"mode": mode, "clear_cache": clear_cache},
            timeout=PAUSE_TIMEOUT_S,
        ).status_code
    except requests.RequestException:
        status = None
    return status, time.monotonic() - start


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
):
    """Every /pause call returned 200 within PAUSE_LIMIT_S."""
    failed = [
        f"{name} status {status} after {seconds:.1f}s"
        for name, (status, seconds) in zip(names, pauses)
        if status != 200 or seconds > PAUSE_LIMIT_S
    ]
    assert not failed, f"/pause failed: {'; '.join(failed)}; {context}"


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
# Pause matrix: (P, D or both) x (abort, wait, keep) x (clear, nc) at a stage
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


def matrix_params(stage: str, targets: tuple[str, ...], with_nc: bool):
    """Cells of the pause matrix that exercise `stage`.

    nc only differs from clear while transfers hold KV blocks, so stages that
    hold none run with clear_cache=True only.
    """
    return [
        pytest.param(
            target,
            mode,
            clear_cache,
            id=f"pause_{_CELLS[mode, clear_cache]}_{target}_{stage}",
        )
        for target in targets
        for mode in ("abort", "wait", "keep")
        for clear_cache in ((True, False) if with_nc else (True,))
    ]


def run_matrix_case(
    pd_urls: tuple[str, str, str],
    target: str,
    mode: str,
    clear_cache: bool,
    setup: Callable[[PDDriver], Stage],
):
    """Pause `target` at the stage `setup` reaches, resume, check recovery."""
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
                pool.submit(timed_pause, urls[name], mode, clear_cache)
                for name in names
            ]
            wait_for(
                lambda: all(
                    future.done() or is_paused(urls[name])
                    for name, future in zip(names, futures)
                ),
                "pause state set on every target",
                STAGE_TIMEOUT_S,
            )
            for req in stage.late_decodes:
                driver.decode(req, max_tokens=DECODE_TOKENS)
            pauses = [future.result() for future in futures]
        finally:
            resumed = [resume(urls[name]) for name in names]

    assert reached, "setup error: the stage was gone at pause time"
    assert_pauses_ok(pauses, f"target {target}, mode {mode}", names)
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
        ends = [req.finish_reason for req in sent_before_pause]
        assert all(end == "length" for end in ends), f"wait dropped requests: {ends}"
    assert_idle_and_probes_match(prefill_url, decode_url, proxy_url, reference)
