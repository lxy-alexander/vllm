# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Control calls out of order around sleep/wake_up, on one engine.

A driver that retries, recovers from an error or resumes too early sends these.
Each must answer (200 or a clear 4xx), never hang or 500, and must not run
requests on memory that is still asleep.
"""

import pytest
import requests

from tests.entrypoints.rl.conftest import (
    gen,
    is_paused,
    is_sleeping,
    ok,
    pause,
    resume,
    server,
    sleep,
    wake,
)

REJECTED = (400, 409)


@pytest.fixture
def url():
    with server() as url:
        yield url


def assert_serves(url: str):
    assert not is_sleeping(url), "still sleeping"
    response = gen(url, max_tokens=8, timeout=60)
    assert ok(response), f"generation failed: {response}"


def post(url: str, path: str, **kwargs) -> int:
    return requests.post(f"{url}{path}", timeout=60, **kwargs).status_code


@pytest.mark.parametrize(
    "wake_tags", [None, ["weights"]], ids=["asleep", "kv_cache_asleep"]
)
def test_resume_while_asleep(url, wake_tags):
    """/resume must not schedule while the KV cache is still asleep."""
    assert sleep(url, level=1) == 200
    if wake_tags:
        assert wake(url, wake_tags) == 200
    status = resume(url)
    still_asleep = is_sleeping(url)
    # Whatever the answer, the engine must not run on discarded memory.
    response = gen(url, max_tokens=8, timeout=10) if not still_asleep else None
    assert status in REJECTED, (
        f"/resume returned {status} while asleep; is_sleeping={still_asleep}, "
        f"a request sent then got {response}"
    )
    assert still_asleep, "/resume ended the sleep"
    assert wake(url) == 200
    assert_serves(url)


def test_double_sleep(url):
    assert sleep(url, level=1) == 200
    assert sleep(url, level=1) == 200
    assert wake(url) == 200
    assert_serves(url)


def test_wake_without_sleep(url):
    assert wake(url) == 200
    assert_serves(url)


@pytest.mark.parametrize(
    ("path", "kwargs"),
    [
        ("/pause", {"params": {"mode": "abort"}}),
        ("/abort_requests", {"json": {}}),
        ("/reset_prefix_cache", {}),
        ("/release_kv_cache_memory", {}),
    ],
    ids=["pause", "abort_requests", "reset_prefix_cache", "release_kv_cache_memory"],
)
def test_control_while_asleep(url, path, kwargs):
    assert sleep(url, level=1) == 200
    status = post(url, path, **kwargs)
    assert is_sleeping(url), f"{path} ended the sleep"
    assert wake(url) == 200
    if path == "/pause":
        # The pause outlives the sleep it was sent during.
        assert resume(url) == 200
    assert_serves(url)
    assert status == 200 or status in REJECTED, f"{path} returned {status}"


@pytest.mark.xfail(reason="semantics undecided: does wake_up end a user pause?")
def test_wake_keeps_user_pause(url):
    assert pause(url, mode="keep") == 200
    assert wake(url) == 200
    paused = is_paused(url)
    resume(url)
    assert paused, "wake_up ended a pause it did not start"
