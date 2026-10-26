# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""1P1D pause/resume lifecycle tests using Mooncake over TCP."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests

from tests.entrypoints.rl.conftest import gen, ok, pause, resume
from tests.entrypoints.rl.state_transitions.new.conftest import (
    DRAIN_TIMEOUT_S,
    STAGE_TIMEOUT_S,
    PDDriver,
    assert_idle_and_probes_match,
    assert_pauses_ok,
    join_all,
    metrics,
    probe_texts,
    timed_pause,
    wait_for,
)

LONG_PROMPT_TOKENS = 6000
# MooncakeConnectorWorker.num_sender_tasks with the default num_workers=10.
NUM_SENDER_TASKS = 20


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    [
        pytest.param(
            target,
            mode,
            clear,
            id=f"pause_{mode}_{'clear' if clear else 'nc'}_{target}",
        )
        for target in ("both", "P", "D")
        for mode, clear in (
            ("abort", True),
            ("abort", False),
            ("wait", True),
            ("wait", False),
            ("keep", True),
            ("keep", False),
        )
    ],
)
def test_pause_resume_1p1d(pd_urls, target, mode, clear_cache):
    prefill_url, decode_url, proxy_url = pd_urls
    assert resume(prefill_url) == 200
    assert resume(decode_url) == 200

    response = requests.post(
        f"{proxy_url}/v1/completions",
        json={
            "model": "m",
            "prompt": "Count upward slowly: one, two, three,",
            "max_tokens": 128,
            "temperature": 0,
            "ignore_eos": True,
            "stream": True,
        },
        stream=True,
        timeout=(5, 120),
    )
    response.raise_for_status()
    try:
        targets = {
            "P": (prefill_url,),
            "D": (decode_url,),
            "both": (prefill_url, decode_url),
        }[target]
        with ThreadPoolExecutor(max_workers=len(targets)) as pool:
            pause_results = list(
                pool.map(
                    lambda url: pause(url, mode=mode, clear_cache=clear_cache),
                    targets,
                )
            )
        assert pause_results == [200] * len(targets)
    finally:
        if target in ("P", "both"):
            assert resume(prefill_url) == 200
        if target in ("D", "both"):
            assert resume(decode_url) == 200
        response.close()

    probe = gen(proxy_url, max_tokens=4, timeout=60)
    assert ok(probe), probe


# ---------------------------------------------------------------------------
# pause_abort_both at a chosen transfer stage
# ---------------------------------------------------------------------------


def _stage_p_prefill(driver: PDDriver):
    req = driver.new(LONG_PROMPT_TOKENS)
    driver.prefill(req)
    wait_for(
        lambda: metrics(driver.prefill_url).get("vllm:num_requests_running", 0) >= 1,
        "P prefilling the request",
        STAGE_TIMEOUT_S,
    )


def _stage_d_pull_waiting(driver: PDDriver):
    reqs = [driver.new(LONG_PROMPT_TOKENS) for _ in range(8)]
    for req in reqs:
        driver.prefill(req)
    for req in reqs:
        driver.decode(req, max_tokens=128)
    wait_for(
        lambda: driver.count("d_pull_waiting") == len(reqs)
        and driver.d_pulls_started(),
        "D pulling requests P has not finished",
        STAGE_TIMEOUT_S,
    )


def _stage_transfer_active(driver: PDDriver):
    # One request: with more, P finishes them one at a time and the later ones
    # still wait on P (d_pull_waiting) while the first transfers.
    req = driver.new(LONG_PROMPT_TOKENS)
    driver.prefill(req)
    driver.decode(req, max_tokens=256)
    wait_for(
        driver.transfer_in_flight,
        "P sending KV to D",
        STAGE_TIMEOUT_S,
    )


def _stage_d_decode(driver: PDDriver):
    req = driver.new(32)
    driver.prefill(req)
    driver.decode(req, max_tokens=2048)
    wait_for(lambda: req.tokens >= 8, "D decoding", STAGE_TIMEOUT_S)


def _stage_mixed(driver: PDDriver):
    _stage_d_decode(driver)
    xfer = driver.new(LONG_PROMPT_TOKENS)
    driver.prefill(xfer)
    driver.decode(xfer, max_tokens=256)
    wait_for(xfer.prefill_done.is_set, "P finishing a prefill", STAGE_TIMEOUT_S)
    pull = driver.new(LONG_PROMPT_TOKENS)
    driver.prefill(pull)
    driver.decode(pull, max_tokens=256)
    driver.prefill(driver.new(LONG_PROMPT_TOKENS))
    wait_for(
        lambda: driver.d_pulls_started() and driver.transfer_in_flight(),
        "requests at every stage at once",
        STAGE_TIMEOUT_S,
    )


def _stage_high_load(driver: PDDriver):
    reqs = [driver.new(512) for _ in range(96)]
    for req in reqs:
        driver.prefill(req)
    # P prefills in arrival order, so pull the newest first: those stay
    # unfinished on P longest.
    # Every request goes to D as well, as the proxy would send it: a request
    # P finished but D never pulls holds P's pause until it expires.
    for req in reversed(reqs):
        driver.decode(req, max_tokens=128)
        # D batches the pulls it schedules in one step into one message to P;
        # one step per request makes each pull hold its own P sender task.
        wait_for(driver.d_pulls_started, "D issuing a pull", STAGE_TIMEOUT_S)
    if driver.count("d_pull_waiting") <= NUM_SENDER_TASKS:
        pytest.fail(
            f"stage not reached: {driver.count('d_pull_waiting')} pulls waiting "
            f"on P, need more than {NUM_SENDER_TASKS}"
        )


_ANY_STAGE = {"p_prefill", "d_pull_waiting", "transfer_active", "d_decode", "done"}

# scenario -> (setup, stages required at pause, stages allowed at pause)
STAGES: dict[str, tuple[Callable[[PDDriver], None], set[str], set[str]]] = {
    "p_prefill": (_stage_p_prefill, {"p_prefill"}, {"p_prefill"}),
    "d_pull_waiting": (
        _stage_d_pull_waiting,
        {"d_pull_waiting"},
        {"d_pull_waiting"},
    ),
    "transfer_active": (
        _stage_transfer_active,
        {"transfer_active"},
        {"transfer_active"},
    ),
    "d_decode": (_stage_d_decode, {"d_decode"}, {"d_decode"}),
    "mixed": (
        _stage_mixed,
        {"p_prefill", "d_pull_waiting", "transfer_active", "d_decode"},
        _ANY_STAGE - {"done"},
    ),
    "high_load": (_stage_high_load, {"d_pull_waiting"}, _ANY_STAGE),
}


@pytest.mark.parametrize(
    "scenario", list(STAGES), ids=lambda s: f"pause_abort_both_{s}"
)
def test_pause_abort_both_at_stage(pd_urls, scenario):
    """Abort P and D together while requests sit at a given transfer stage.

    Passes when both pauses return 200 within PAUSE_LIMIT_S, every request
    ends, both engines go idle, and greedy probes match the pre-pause output.
    """
    prefill_url, decode_url, proxy_url = pd_urls
    reference = probe_texts(proxy_url)
    assert None not in reference, reference

    driver = PDDriver(prefill_url, decode_url)
    setup, required_stages, allowed_stages = STAGES[scenario]
    setup(driver)
    stages_at_pause = driver.stages()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            pauses = list(pool.map(timed_pause, (prefill_url, decode_url)))
    finally:
        assert resume(prefill_url) == 200
        assert resume(decode_url) == 200

    seen = set(stages_at_pause)
    assert required_stages <= seen <= allowed_stages, (
        f"setup error, stages at pause: {stages_at_pause}"
    )
    assert_pauses_ok(pauses, f"stages at pause: {stages_at_pause}")

    join_all([t for req in driver.requests for t in req.threads], DRAIN_TIMEOUT_S)
    stuck = [r.stage for r in driver.requests if any(t.is_alive() for t in r.threads)]
    assert not stuck, f"{len(stuck)} requests still open after resume: {stuck}"

    assert_idle_and_probes_match(prefill_url, decode_url, proxy_url, reference)
