# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause while P computes the request's KV and D has not received it."""

import pytest

from tests.entrypoints.rl.state_transitions.new.conftest import (
    STAGE_PROMPT_TOKENS,
    STAGE_TIMEOUT_S,
    PDDriver,
    Stage,
    matrix_params,
    metrics,
    run_matrix_case,
    wait_for,
)


def _setup(driver: PDDriver) -> Stage:
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)

    def reached() -> bool:
        running = metrics(driver.prefill_url).get("vllm:num_requests_running", 0)
        return not req.prefill_done.is_set() and running >= 1

    wait_for(reached, "P prefilling the request", STAGE_TIMEOUT_S)
    return Stage(reached, late_decodes=[req])


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("p_prefill", ("both", "P"), with_nc=False),
)
def test_pause_at_p_prefill(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)
