# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause while D's pulls wait on prefills P has not finished (R1)."""

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


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("d_pull_waiting", ("both", "P", "D"), with_nc=True),
)
def test_pause_at_d_pull_waiting(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)
