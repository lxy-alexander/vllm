# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause or sleep after P finished the KV but before D received the request."""

import pytest

from tests.entrypoints.rl.state_transitions.new.conftest import (
    STAGE_PROMPT_TOKENS,
    STAGE_TIMEOUT_S,
    PDDriver,
    Stage,
    matrix_params,
    metrics,
    num_requests,
    run_matrix_case,
    run_sleep_case,
    sleep_matrix_params,
    wait_for,
)


def _setup(driver: PDDriver) -> Stage:
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


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("p_done_unpulled"),
)
def test_pause_at_p_done_unpulled(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)


@pytest.mark.parametrize(
    ("level", "mode", "target"),
    sleep_matrix_params("p_done_unpulled"),
)
def test_sleep_at_p_done_unpulled(pd_sleep_urls, level, mode, target):
    run_sleep_case(pd_sleep_urls, target, level, mode, _setup)
