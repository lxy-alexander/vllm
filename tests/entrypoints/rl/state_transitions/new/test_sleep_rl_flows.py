# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""1P1D sleep/wake_up in the call orders RL drivers use, over Mooncake.

verl's vLLMPDReplica (verl/workers/rollout/vllm_rollout/) sleeps a replica by
draining servers[0], which is P, and then sleeping every server at once, so D
can still have requests in flight when its sleep arrives. Its weight sync and
admission gate are outside vLLM; level 2 cases write the weights again with
reload_weights instead of a sync from a trainer.
"""

import os
import subprocess
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from tests.entrypoints.rl.conftest import gen, is_sleeping, ok, resume, wake
from tests.entrypoints.rl.state_transitions.new.conftest import (
    DRAIN_TIMEOUT_S,
    PROBE_PROMPTS,
    STAGE_TIMEOUT_S,
    PDDriver,
    PDRequest,
    assert_idle_and_probes_match,
    assert_logs_clean,
    assert_pauses_ok,
    join_all,
    metrics,
    num_requests,
    probe_texts,
    reload_weights,
    timed_post,
    wait_for,
)

LOAD_REQUESTS = 8
LOAD_PROMPT_TOKENS = 2000
LOAD_DECODE_TOKENS = 512
# Seconds a request sent while one side still sleeps must stay unanswered.
ASLEEP_HOLD_S = 5
LONG_SLEEP_S = float(os.environ.get("PD_LONG_SLEEP_S", 600))
# CUDA_VISIBLE_DEVICES of P and D in pd_stack.
GPU = {"P": 0, "D": 1}
MIN_FREED_MIB = 1024


class Case:
    def __init__(self, urls: tuple[str, str, str]):
        self.prefill_url, self.decode_url, self.proxy_url = urls
        self.urls = {"P": self.prefill_url, "D": self.decode_url}
        self.reference = probe_texts(self.proxy_url)
        assert None not in self.reference, self.reference
        self.driver = PDDriver(self.prefill_url, self.decode_url)

    def load(self) -> list[PDRequest]:
        reqs = [self.driver.new(LOAD_PROMPT_TOKENS) for _ in range(LOAD_REQUESTS)]
        for req in reqs:
            self.driver.prefill(req)
            self.driver.decode(req, max_tokens=LOAD_DECODE_TOKENS)
        return reqs

    def decoding(self) -> bool:
        return any(req.tokens for req in self.driver.requests)

    def on(self, names: tuple[str, ...], fn: Callable[[str], object]) -> list:
        """Call fn on each named instance at once, as verl's gather does."""
        with ThreadPoolExecutor(max_workers=len(names)) as pool:
            return list(pool.map(lambda name: fn(self.urls[name]), names))

    def sleep(self, names: tuple[str, ...], level: int, **params):
        sleeps = self.on(
            names, lambda url: timed_post(url, "/sleep", level=level, **params)
        )
        assert_logs_clean()
        assert_pauses_ok(sleeps, f"level {level}", names, "/sleep")
        assert all(self.on(names, is_sleeping)), "not sleeping after /sleep"

    def wake(self, names: tuple[str, ...], level: int, tags=None):
        assert self.on(names, lambda url: wake(url, tags)) == [200] * len(names)
        if level == 2 and (tags is None or "weights" in tags):
            self.on(names, reload_weights)

    def finish(self):
        """Every request ends, both sides go idle, and outputs are right."""
        stuck = join_all(self.driver.threads(), DRAIN_TIMEOUT_S)
        assert_logs_clean()
        assert not stuck, f"{stuck} requests still open {DRAIN_TIMEOUT_S}s after wake"
        assert_idle_and_probes_match(
            self.prefill_url, self.decode_url, self.proxy_url, self.reference
        )
        assert_logs_clean()


def gpu_used_mib(gpu: int) -> int:
    out = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=memory.used",
            "--format=csv,noheader,nounits",
            "-i",
            str(gpu),
        ],
        text=True,
    )
    return int(out.strip())


def background_probe(proxy_url: str) -> tuple[threading.Thread, dict]:
    """Send PROBE_PROMPTS[0] as probe_texts does; the reply lands in result."""
    result: dict = {}

    def run():
        result["response"] = gen(
            proxy_url, prompt=PROBE_PROMPTS[0], max_tokens=16, timeout=300
        )

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, result


def assert_probe_answered(case: Case, thread: threading.Thread, result: dict):
    thread.join(DRAIN_TIMEOUT_S)
    response = result.get("response")
    assert ok(response), f"request sent while asleep failed: {response}"
    assert response["choices"][0]["text"] == case.reference[0]


# ---------------------------------------------------------------------------
# A1: verl's PD sleep: drain P only, then sleep P and D together
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", [1, 2], ids=["sleep1", "sleep2"])
def test_verl_pd_sleep(pd_sleep_urls, level, record_property):
    case = Case(pd_sleep_urls)
    reqs = case.load()
    wait_for(
        lambda: all(req.prefill_done.is_set() for req in reqs)
        and num_requests(metrics(case.prefill_url)) == 0,
        "P drained",
        DRAIN_TIMEOUT_S,
    )
    # verl drains P only; D usually still decodes or loads here.
    record_property("d_requests_at_sleep", num_requests(metrics(case.decode_url)))
    # verl passes no mode, so the sleep aborts what D still runs.
    case.sleep(("P", "D"), level)
    case.wake(("P", "D"), level, tags=["kv_cache", "weights"])
    for url in case.urls.values():
        response = requests.post(
            f"{url}/reset_prefix_cache", params={"reset_external": True}, timeout=30
        )
        assert response.json() == {"success": True}, response.text
    case.finish()


# ---------------------------------------------------------------------------
# A2: pause(abort) first, then sleep the paused engines
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", [1, 2], ids=["sleep1", "sleep2"])
def test_pause_then_sleep(pd_sleep_urls, level):
    case = Case(pd_sleep_urls)
    case.load()
    wait_for(case.decoding, "D decoding", STAGE_TIMEOUT_S)
    pauses = case.on(("P", "D"), lambda url: timed_post(url, "/pause", mode="abort"))
    assert_pauses_ok(pauses, "pause before sleep")
    case.sleep(("P", "D"), level)
    case.wake(("P", "D"), level)
    # wake_up resumes the scheduler; the user's pause ends with it.
    assert case.on(("P", "D"), resume) == [200, 200]
    case.finish()


# ---------------------------------------------------------------------------
# A3: sleep with nothing in flight; the memory must really go
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", [1, 2], ids=["sleep1", "sleep2"])
def test_drain_then_sleep(pd_sleep_urls, level):
    case = Case(pd_sleep_urls)
    case.load()
    assert not join_all(case.driver.threads(), DRAIN_TIMEOUT_S), "load did not finish"
    before = {name: gpu_used_mib(gpu) for name, gpu in GPU.items()}
    case.sleep(("P", "D"), level)
    after = {name: gpu_used_mib(gpu) for name, gpu in GPU.items()}
    freed = {name: before[name] - after[name] for name in GPU}
    assert all(mib >= MIN_FREED_MIB for mib in freed.values()), (
        f"sleep freed too little GPU memory (MiB): {freed}"
    )
    case.wake(("P", "D"), level)
    case.finish()


# ---------------------------------------------------------------------------
# A4: verl's release_kv_cache: wake the weights first, the KV cache later
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("traffic", [False, True], ids=["idle", "traffic"])
@pytest.mark.parametrize("level", [1, 2], ids=["sleep1", "sleep2"])
def test_release_kv_split_wake(pd_sleep_urls, level, traffic):
    case = Case(pd_sleep_urls)
    case.sleep(("P", "D"), level)
    case.wake(("P", "D"), level, tags=["weights"])
    assert all(case.on(("P", "D"), is_sleeping)), "awake with the KV cache asleep"
    probe = None
    if traffic:
        # Nothing may run until the KV cache is back.
        probe = background_probe(case.proxy_url)
        time.sleep(ASLEEP_HOLD_S)
        assert probe[0].is_alive(), f"answered with the KV cache asleep: {probe[1]}"
    case.wake(("P", "D"), level, tags=["kv_cache"])
    assert not any(case.on(("P", "D"), is_sleeping)), "still sleeping after full wake"
    if probe is not None:
        assert_probe_answered(case, *probe)
    case.finish()


# ---------------------------------------------------------------------------
# B2: one side sleeps first, with requests in flight between them
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("first", ["P", "D"], ids=["P_first", "D_first"])
def test_sleep_one_side_first(pd_sleep_urls, first):
    case = Case(pd_sleep_urls)
    case.load()
    wait_for(case.decoding, "D decoding", STAGE_TIMEOUT_S)
    other = "D" if first == "P" else "P"
    case.sleep((first,), 1)
    time.sleep(ASLEEP_HOLD_S)
    case.sleep((other,), 1)
    case.wake(("P", "D"), 1)
    case.finish()


# ---------------------------------------------------------------------------
# B3: one side wakes first; a request sent then waits for the other
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("first", ["P", "D"], ids=["P_first", "D_first"])
def test_wake_one_side_first(pd_sleep_urls, first):
    case = Case(pd_sleep_urls)
    case.sleep(("P", "D"), 1)
    other = "D" if first == "P" else "P"
    case.wake((first,), 1)
    thread, result = background_probe(case.proxy_url)
    time.sleep(ASLEEP_HOLD_S)
    assert is_sleeping(case.urls[other]), f"{other} woke on its own"
    case.wake((other,), 1)
    assert_probe_answered(case, thread, result)
    case.finish()


# ---------------------------------------------------------------------------
# A8: a training step's worth of sleep
# ---------------------------------------------------------------------------


@pytest.mark.slow_test
def test_long_sleep_both(pd_sleep_urls):
    case = Case(pd_sleep_urls)
    case.sleep(("P", "D"), 1)
    time.sleep(LONG_SLEEP_S)
    case.wake(("P", "D"), 1)
    case.finish()
