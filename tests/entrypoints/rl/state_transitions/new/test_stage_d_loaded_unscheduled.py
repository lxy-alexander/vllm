# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause after D loaded the request's KV but before it scheduled it."""

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


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("d_loaded_unscheduled", ("both", "D"), with_nc=True),
)
def test_pause_at_d_loaded_unscheduled(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)
