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

## Cassettes: pay once, replay forever

`ReplayHarness` manages any number of named recordings as
`<name>.jsonl` files under one root. The `replay_harness` pytest fixture
gives each test a scratch library.

```python
# capture: record a real run once (or a scripted run, for free authoring)
with replay_harness.capture("hinged-box", OpenAIModel()) as model:
    run(Agent(model, env).run("a hinged box"))

# set: install or transform a cassette without running anything
replay_harness.set("plain-box", [calls(tool_call("compile")), text("done")])

# replay: plug any recording into a run; strict mode fails on trajectory drift
artifacts = run_scenario("a box", model=replay_harness.replay("plain-box"))

# erase / clear
replay_harness.erase("plain-box")
```

Strict replay compares a structural fingerprint (roles, tool names, call
ids), not payload text, because tool outputs embed machine-specific run
paths. Rows installed by `set()` carry no fingerprint and match any request.

Curated regression cassettes belong in `tests/cassettes/` (git-ignored by
default; force-add the ones worth keeping). Scratch cassettes belong under
`tmp_path`.

## Known platform flakes

On macOS, a few exec-output timing tests can fail with empty captured output
even on a clean tree; they pass on Linux CI. Reproduce on Linux before
touching exec semantics, and do not weaken the assertions to make them pass
locally.
