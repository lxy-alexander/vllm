# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause or sleep while P sends the request's KV to D."""

import pytest

from tests.entrypoints.rl.state_transitions.new.conftest import (
    DECODE_TOKENS,
    STAGE_PROMPT_TOKENS,
    STAGE_TIMEOUT_S,
    PDDriver,
    Stage,
    matrix_params,
    run_matrix_case,
    run_sleep_case,
    sleep_matrix_params,
    wait_for,
)


def _setup(driver: PDDriver) -> Stage:
    # One request: with more, P finishes them one at a time and the later
    # ones still wait on P while the first transfers.
    req = driver.new(STAGE_PROMPT_TOKENS)
    driver.prefill(req)
    driver.decode(req, max_tokens=DECODE_TOKENS)
    wait_for(driver.transfer_in_flight, "P sending KV to D", STAGE_TIMEOUT_S)
    return Stage(driver.transfer_in_flight)


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("transfer_active"),
)
def test_pause_at_transfer_active(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)


@pytest.mark.parametrize(
    ("level", "mode", "target"),
    sleep_matrix_params("transfer_active"),
)
def test_sleep_at_transfer_active(pd_sleep_urls, level, mode, target):
    run_sleep_case(pd_sleep_urls, target, level, mode, _setup)
