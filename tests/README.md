# Test environment

This suite verifies the generation loop without paid model calls.
`tests/harness.py` is the shared kit; prefer it over per-file fakes.

## The lanes

| Lane | Cost | Use for |
| --- | --- | --- |
| Unit | ~0s | pure functions: SDK checks, `compile_feedback`, signals |
| Scripted agent | seconds per run | the full agent loop via `ScriptedModel` + `run_scenario` |

```python
from harness import run_scenario, calls, text, tool_call

artifacts = run_scenario(
    "a box",
    [
        calls(tool_call("write", {"path": "main.py", "content": GOOD_MAIN_PY})),
        calls(tool_call("compile")),
        text("done"),
    ],
    tmp_path=tmp_path,
)
assert artifacts.record.status == "success"
```

A scripted step can also be a callable `(ModelQuery) -> Response`, so the
"model" can assert on what the agent sent and react to earlier tool outputs.
See `tests/test_agent_scenarios.py` for end-to-end examples (repair loops,
repeat-failure guidance, allowances).

## Known platform flakes

On macOS, a few exec-output timing tests can fail with empty captured output
even on a clean tree; they pass on Linux CI. Reproduce on Linux before
touching exec semantics, and do not weaken the assertions to make them pass
locally.
