# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause while D holds the request but has not sent its pull to P."""

import pytest

from tests.entrypoints.rl.state_transitions.new.conftest import (
    DECODE_TOKENS,
    FILLER_TOKENS,
    MAX_NUM_SEQS,
    STAGE_PROMPT_TOKENS,
    STAGE_TIMEOUT_S,
    PDDriver,
    Stage,
    kv_fetch,
    matrix_params,
    metrics,
    run_matrix_case,
    wait_for,
)


def _setup(driver: PDDriver) -> Stage:
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


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("d_waiting_to_start", ("both", "D"), with_nc=True),
)
def test_pause_at_d_waiting_to_start(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)
