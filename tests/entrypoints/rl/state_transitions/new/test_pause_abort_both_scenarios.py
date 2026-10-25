# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""pause_abort_both under real proxy traffic (1P1D, Mooncake over TCP).

Requests take the production path through the example proxy, so which
transfer stage each one is in at pause time is not controlled; the test only
makes sure the load has reached D and is still moving KV when P and D abort
together. test_pause_resume.py::test_pause_abort_both_at_stage pins the stage.
"""

import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pytest
import requests

from tests.entrypoints.rl.conftest import resume
from tests.entrypoints.rl.state_transitions.new.conftest import (
    DRAIN_TIMEOUT_S,
    STAGE_TIMEOUT_S,
    assert_idle_and_probes_match,
    assert_pauses_ok,
    join_all,
    kv_fetch,
    metrics,
    num_requests,
    probe_texts,
    timed_pause,
    token_prompt,
    wait_for,
)

PROMPT_TOKENS = 1024
MAX_TOKENS = 256


@dataclass
class ProxyStream:
    thread: threading.Thread | None = None
    finish_reason: str | None = None
    error: str | None = None


def _stream(proxy_url: str, prompt: list[int], result: ProxyStream):
    try:
        with requests.post(
            f"{proxy_url}/v1/completions",
            json={
                "model": "m",
                "prompt": prompt,
                "max_tokens": MAX_TOKENS,
                "temperature": 0,
                "ignore_eos": True,
                "stream": True,
            },
            stream=True,
            timeout=(5, 600),
        ) as response:
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: {"):
                    choice = json.loads(line[6:])["choices"][0]
                    result.finish_reason = (
                        choice.get("finish_reason") or result.finish_reason
                    )
    except requests.RequestException as error:
        result.error = type(error).__name__


def _load_in_flight(decode_url: str, streams: list[ProxyStream]) -> bool:
    """Every live request reached D, which is loading KV and decoding."""
    values = metrics(decode_url)
    live = sum(s.thread is not None and s.thread.is_alive() for s in streams)
    return (
        num_requests(values) >= live
        and kv_fetch(values, "in_progress") > 0
        and values.get("vllm:num_requests_running", 0) > 0
    )


@pytest.mark.parametrize(
    "load", [8, 96], ids=lambda n: f"pause_abort_both_proxy_load_{n}"
)
def test_pause_abort_both_proxy_load(pd_urls, load):
    """Abort P and D together while proxy traffic is mid-transfer.

    Passes when both pauses return 200 within PAUSE_LIMIT_S, every stream
    ends, both engines go idle, and greedy probes match the pre-pause output.
    """
    prefill_url, decode_url, proxy_url = pd_urls
    reference = probe_texts(proxy_url)
    assert None not in reference, reference

    streams = [ProxyStream() for _ in range(load)]
    for stream in streams:
        stream.thread = threading.Thread(
            target=_stream,
            args=(proxy_url, token_prompt(PROMPT_TOKENS), stream),
            daemon=True,
        )
        stream.thread.start()
    wait_for(
        lambda: _load_in_flight(decode_url, streams),
        "proxy load reaching D with KV still in flight",
        STAGE_TIMEOUT_S,
    )
    at_pause = metrics(decode_url)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            pauses = list(pool.map(timed_pause, (prefill_url, decode_url)))
    finally:
        assert resume(prefill_url) == 200
        assert resume(decode_url) == 200

    assert_pauses_ok(
        pauses,
        f"D at pause: {kv_fetch(at_pause, 'in_progress'):.0f} loading, "
        f"{at_pause.get('vllm:num_requests_running', 0):.0f} running",
    )
    stuck = join_all([s.thread for s in streams], DRAIN_TIMEOUT_S)
    ends = Counter(s.error or s.finish_reason for s in streams)
    assert not stuck, f"{stuck}/{load} streams still open after resume: {ends}"

    assert_idle_and_probes_match(prefill_url, decode_url, proxy_url, reference)
