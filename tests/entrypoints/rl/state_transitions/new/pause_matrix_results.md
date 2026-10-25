<!-- 90 cases: FAILED 18, PASSED 72 -->

# pause_abort_both

-   pause_abort_both_p_queued

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_queued.py::test_pause_at_p_queued[pause_abort_both_p_queued] PASSED
```

-   pause_abort_both_p_prefill

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_prefill.py::test_pause_at_p_prefill[pause_abort_both_p_prefill] PASSED
```

-   pause_abort_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_abort_both_p_done_unpulled] PASSED
```

-   pause_abort_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_abort_both_d_waiting_to_start] PASSED
```

-   pause_abort_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_both_d_pull_waiting] FAILED - AssertionError: /pause failed: D status None after 90.1s; target both, mode abort
```

-   pause_abort_both_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_abort_both_transfer_active] PASSED
```

-   pause_abort_both_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_abort_both_d_loaded_unscheduled] PASSED
```

-   pause_abort_both_d_decode

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_decode.py::test_pause_at_d_decode[pause_abort_both_d_decode] PASSED
```

# pause_abort_nc_both

-   pause_abort_nc_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_abort_nc_both_p_done_unpulled] PASSED
```

-   pause_abort_nc_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_abort_nc_both_d_waiting_to_start] PASSED
```

-   pause_abort_nc_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_nc_both_d_pull_waiting] FAILED - AssertionError: /pause failed: D status None after 90.1s; target both, mode abort
```

-   pause_abort_nc_both_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_abort_nc_both_transfer_active] PASSED
```

-   pause_abort_nc_both_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_abort_nc_both_d_loaded_unscheduled] PASSED
```

# pause_wait_both

-   pause_wait_both_p_queued

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_queued.py::test_pause_at_p_queued[pause_wait_both_p_queued] PASSED
```

-   pause_wait_both_p_prefill

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_prefill.py::test_pause_at_p_prefill[pause_wait_both_p_prefill] PASSED
```

-   pause_wait_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_wait_both_p_done_unpulled] PASSED
```

-   pause_wait_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_wait_both_d_waiting_to_start] FAILED - AssertionError: /pause failed: P status None after 90.0s; target both, mode wait
```

-   pause_wait_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_both_d_pull_waiting] FAILED - AssertionError: /pause failed: D status None after 90.1s; target both, mode wait
```

-   pause_wait_both_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_wait_both_transfer_active] PASSED
```

-   pause_wait_both_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_wait_both_d_loaded_unscheduled] PASSED
```

-   pause_wait_both_d_decode

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_decode.py::test_pause_at_d_decode[pause_wait_both_d_decode] PASSED
```

# pause_wait_nc_both

-   pause_wait_nc_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_wait_nc_both_p_done_unpulled] PASSED
```

-   pause_wait_nc_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_wait_nc_both_d_waiting_to_start] FAILED - AssertionError: /pause failed: P status None after 90.0s; target both, mode wait
```

-   pause_wait_nc_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_nc_both_d_pull_waiting] FAILED - AssertionError: /pause failed: D status None after 90.1s; target both, mode wait
```

-   pause_wait_nc_both_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_wait_nc_both_transfer_active] PASSED
```

-   pause_wait_nc_both_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_wait_nc_both_d_loaded_unscheduled] PASSED
```

# pause_keep_clear_both

-   pause_keep_clear_both_p_queued

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_queued.py::test_pause_at_p_queued[pause_keep_clear_both_p_queued] PASSED
```

-   pause_keep_clear_both_p_prefill

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_prefill.py::test_pause_at_p_prefill[pause_keep_clear_both_p_prefill] PASSED
```

-   pause_keep_clear_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_keep_clear_both_p_done_unpulled] FAILED - AssertionError: /pause failed: P status None after 90.0s; target both, mode keep
```

-   pause_keep_clear_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_keep_clear_both_d_waiting_to_start] PASSED
```

-   pause_keep_clear_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_clear_both_d_pull_waiting] FAILED - AssertionError: /pause failed: D status 500 after 0.0s; target both, mode keep
```

-   pause_keep_clear_both_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_clear_both_transfer_active] FAILED - AssertionError: /pause failed: D status 500 after 0.0s; target both, mode keep
```

-   pause_keep_clear_both_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_keep_clear_both_d_loaded_unscheduled] FAILED - AssertionError: /pause failed: D status 500 after 0.0s; target both, mode keep
```

-   pause_keep_clear_both_d_decode

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_decode.py::test_pause_at_d_decode[pause_keep_clear_both_d_decode] PASSED
```

# pause_keep_nc_both

-   pause_keep_nc_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_keep_nc_both_p_done_unpulled] FAILED - AssertionError: /pause failed: P status None after 90.1s; target both, mode keep
```

-   pause_keep_nc_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_keep_nc_both_d_waiting_to_start] PASSED
```

-   pause_keep_nc_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_nc_both_d_pull_waiting] PASSED
```

-   pause_keep_nc_both_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_nc_both_transfer_active] PASSED
```

-   pause_keep_nc_both_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_keep_nc_both_d_loaded_unscheduled] PASSED
```

# pause_abort_P

-   pause_abort_P_p_queued

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_queued.py::test_pause_at_p_queued[pause_abort_P_p_queued] FAILED - AssertionError: 1 requests still open 180s after resume
```

-   pause_abort_P_p_prefill

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_prefill.py::test_pause_at_p_prefill[pause_abort_P_p_prefill] FAILED - AssertionError: 1 requests still open 180s after resume
```

-   pause_abort_P_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_abort_P_p_done_unpulled] PASSED
```

-   pause_abort_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_P_d_pull_waiting] FAILED - AssertionError: 4 requests still open 180s after resume
```

-   pause_abort_P_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_abort_P_transfer_active] PASSED
```

# pause_abort_nc_P

-   pause_abort_nc_P_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_abort_nc_P_p_done_unpulled] PASSED
```

-   pause_abort_nc_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_nc_P_d_pull_waiting] FAILED - AssertionError: 4 requests still open 180s after resume
```

-   pause_abort_nc_P_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_abort_nc_P_transfer_active] PASSED
```

# pause_wait_P

-   pause_wait_P_p_queued

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_queued.py::test_pause_at_p_queued[pause_wait_P_p_queued] PASSED
```

-   pause_wait_P_p_prefill

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_prefill.py::test_pause_at_p_prefill[pause_wait_P_p_prefill] PASSED
```

-   pause_wait_P_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_wait_P_p_done_unpulled] PASSED
```

-   pause_wait_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_P_d_pull_waiting] PASSED
```

-   pause_wait_P_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_wait_P_transfer_active] PASSED
```

# pause_wait_nc_P

-   pause_wait_nc_P_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_wait_nc_P_p_done_unpulled] PASSED
```

-   pause_wait_nc_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_nc_P_d_pull_waiting] PASSED
```

-   pause_wait_nc_P_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_wait_nc_P_transfer_active] PASSED
```

# pause_keep_clear_P

-   pause_keep_clear_P_p_queued

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_queued.py::test_pause_at_p_queued[pause_keep_clear_P_p_queued] PASSED
```

-   pause_keep_clear_P_p_prefill

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_prefill.py::test_pause_at_p_prefill[pause_keep_clear_P_p_prefill] PASSED
```

-   pause_keep_clear_P_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_keep_clear_P_p_done_unpulled] PASSED
```

-   pause_keep_clear_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_clear_P_d_pull_waiting] PASSED
```

-   pause_keep_clear_P_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_clear_P_transfer_active] PASSED
```

# pause_keep_nc_P

-   pause_keep_nc_P_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_keep_nc_P_p_done_unpulled] PASSED
```

-   pause_keep_nc_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_nc_P_d_pull_waiting] PASSED
```

-   pause_keep_nc_P_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_nc_P_transfer_active] PASSED
```

# pause_abort_D

-   pause_abort_D_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_abort_D_d_waiting_to_start] PASSED
```

-   pause_abort_D_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_D_d_pull_waiting] PASSED
```

-   pause_abort_D_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_abort_D_transfer_active] PASSED
```

-   pause_abort_D_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_abort_D_d_loaded_unscheduled] PASSED
```

-   pause_abort_D_d_decode

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_decode.py::test_pause_at_d_decode[pause_abort_D_d_decode] PASSED
```

# pause_abort_nc_D

-   pause_abort_nc_D_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_abort_nc_D_d_waiting_to_start] PASSED
```

-   pause_abort_nc_D_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_nc_D_d_pull_waiting] PASSED
```

-   pause_abort_nc_D_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_abort_nc_D_transfer_active] PASSED
```

-   pause_abort_nc_D_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_abort_nc_D_d_loaded_unscheduled] PASSED
```

# pause_wait_D

-   pause_wait_D_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_wait_D_d_waiting_to_start] PASSED
```

-   pause_wait_D_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_D_d_pull_waiting] PASSED
```

-   pause_wait_D_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_wait_D_transfer_active] PASSED
```

-   pause_wait_D_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_wait_D_d_loaded_unscheduled] PASSED
```

-   pause_wait_D_d_decode

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_decode.py::test_pause_at_d_decode[pause_wait_D_d_decode] PASSED
```

# pause_wait_nc_D

-   pause_wait_nc_D_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_wait_nc_D_d_waiting_to_start] PASSED
```

-   pause_wait_nc_D_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_nc_D_d_pull_waiting] PASSED
```

-   pause_wait_nc_D_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_wait_nc_D_transfer_active] PASSED
```

-   pause_wait_nc_D_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_wait_nc_D_d_loaded_unscheduled] PASSED
```

# pause_keep_clear_D

-   pause_keep_clear_D_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_keep_clear_D_d_waiting_to_start] PASSED
```

-   pause_keep_clear_D_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_clear_D_d_pull_waiting] FAILED - AssertionError: /pause failed: D status 500 after 0.0s; target D, mode keep
```

-   pause_keep_clear_D_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_clear_D_transfer_active] FAILED - AssertionError: /pause failed: D status 500 after 0.0s; target D, mode keep
```

-   pause_keep_clear_D_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_keep_clear_D_d_loaded_unscheduled] FAILED - AssertionError: /pause failed: D status 500 after 0.0s; target D, mode keep
```

-   pause_keep_clear_D_d_decode

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_decode.py::test_pause_at_d_decode[pause_keep_clear_D_d_decode] PASSED
```

# pause_keep_nc_D

-   pause_keep_nc_D_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_keep_nc_D_d_waiting_to_start] PASSED
```

-   pause_keep_nc_D_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_nc_D_d_pull_waiting] PASSED
```

-   pause_keep_nc_D_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_nc_D_transfer_active] PASSED
```

-   pause_keep_nc_D_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_keep_nc_D_d_loaded_unscheduled] PASSED
```
