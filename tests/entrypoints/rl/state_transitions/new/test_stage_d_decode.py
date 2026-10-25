# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Pause while D decodes the request with KV loaded from P."""

import pytest

from tests.entrypoints.rl.state_transitions.new.conftest import (
    DECODE_TOKENS,
    STAGE_TIMEOUT_S,
    PDDriver,
    Stage,
    matrix_params,
    run_matrix_case,
    wait_for,
)


def _setup(driver: PDDriver) -> Stage:
    req = driver.new(32)
    driver.prefill(req)
    driver.decode(req, max_tokens=DECODE_TOKENS)

    def reached() -> bool:
        return req.tokens >= 8 and not req.decode_done.is_set()

    wait_for(reached, "D decoding", STAGE_TIMEOUT_S)
    return Stage(reached)


@pytest.mark.parametrize(
    ("target", "mode", "clear_cache"),
    matrix_params("d_decode", ("both", "D"), with_nc=False),
)
def test_pause_at_d_decode(pd_urls, target, mode, clear_cache):
    run_matrix_case(pd_urls, target, mode, clear_cache, _setup)
