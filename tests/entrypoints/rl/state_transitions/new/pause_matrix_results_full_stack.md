<!-- 18 cases: FAILED 3, PASSED 15 -->

# pause_abort_both

-   pause_abort_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_both_d_pull_waiting] PASSED
```

# pause_abort_nc_both

-   pause_abort_nc_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_nc_both_d_pull_waiting] PASSED
```

# pause_wait_both

-   pause_wait_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_wait_both_d_waiting_to_start] PASSED
```

-   pause_wait_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_both_d_pull_waiting] FAILED - AssertionError: /pause failed: D status None after 90.1s; target both, mode wait
```

# pause_wait_nc_both

-   pause_wait_nc_both_d_waiting_to_start

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_waiting_to_start.py::test_pause_at_d_waiting_to_start[pause_wait_nc_both_d_waiting_to_start] PASSED
```

-   pause_wait_nc_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_wait_nc_both_d_pull_waiting] FAILED - AssertionError: /pause failed: D status None after 90.0s; target both, mode wait
```

# pause_keep_clear_both

-   pause_keep_clear_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_keep_clear_both_p_done_unpulled] FAILED - AssertionError: keep dropped requests: [None]
```

-   pause_keep_clear_both_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_clear_both_d_pull_waiting] PASSED
```

-   pause_keep_clear_both_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_clear_both_transfer_active] PASSED
```

-   pause_keep_clear_both_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_keep_clear_both_d_loaded_unscheduled] PASSED
```

# pause_keep_nc_both

-   pause_keep_nc_both_p_done_unpulled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_done_unpulled.py::test_pause_at_p_done_unpulled[pause_keep_nc_both_p_done_unpulled] PASSED
```

# pause_abort_P

-   pause_abort_P_p_queued

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_queued.py::test_pause_at_p_queued[pause_abort_P_p_queued] PASSED
```

-   pause_abort_P_p_prefill

```python
tests/entrypoints/rl/state_transitions/new/test_stage_p_prefill.py::test_pause_at_p_prefill[pause_abort_P_p_prefill] PASSED
```

-   pause_abort_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_P_d_pull_waiting] PASSED
```

# pause_abort_nc_P

-   pause_abort_nc_P_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_abort_nc_P_d_pull_waiting] PASSED
```

# pause_keep_clear_D

-   pause_keep_clear_D_d_pull_waiting

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_pull_waiting.py::test_pause_at_d_pull_waiting[pause_keep_clear_D_d_pull_waiting] PASSED
```

-   pause_keep_clear_D_transfer_active

```python
tests/entrypoints/rl/state_transitions/new/test_stage_transfer_active.py::test_pause_at_transfer_active[pause_keep_clear_D_transfer_active] PASSED
```

-   pause_keep_clear_D_d_loaded_unscheduled

```python
tests/entrypoints/rl/state_transitions/new/test_stage_d_loaded_unscheduled.py::test_pause_at_d_loaded_unscheduled[pause_keep_clear_D_d_loaded_unscheduled] PASSED
```
