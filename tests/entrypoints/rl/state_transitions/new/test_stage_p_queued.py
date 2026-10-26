# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause or sleep while P still queues the request and D has not received it."""

import pytest

from tests.entrypoints.rl.state_transitions.new.conftest import (
    STAGE_PROMPT_TOKENS,
    STAGE_TIMEOUT_S,
    PDDriver,
    Stage,
    matrix_params,
    metrics,
    run_matrix_case,
    run_sleep_case,
    sleep_matrix_params,
    wait_for,
)


def _setup(driver: PDDriver) -> Stage:
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


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("p_queued"),
)
def test_pause_at_p_queued(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)


@pytest.mark.parametrize(
    ("level", "mode", "target"),
    sleep_matrix_params("p_queued"),
)
def test_sleep_at_p_queued(pd_sleep_urls, level, mode, target):
    run_sleep_case(pd_sleep_urls, target, level, mode, _setup)
