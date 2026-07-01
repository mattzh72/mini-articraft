from __future__ import annotations

import json

from mini_articraft.record import Record, append_conversation, read_conversation


def test_record_saves_slim_run_summary(tmp_path) -> None:
    path = tmp_path / "record.json"
    record = Record(run_id="run_1", status="success", result="result/model.usdz")

    record.save(path)

    # Save/load round-trips the whole record via dataclass equality.
    assert Record.load(path) == record
    # The on-disk summary stays slim: pin the field set, not every value.
    assert set(json.loads(path.read_text())) == {
        "run_id",
        "status",
        "attempts",
        "error",
        "result",
        "cost",
        "token_usage",
    }


def test_conversation_jsonl_is_append_only(tmp_path) -> None:
    path = tmp_path / "conversation.jsonl"

    append_conversation(path, {"role": "user", "content": "make a drawer"})
    append_conversation(path, {"role": "compiler", "status": "success"})

    events = read_conversation(path)
    assert [event["role"] for event in events] == ["user", "compiler"]
    assert events[0]["content"] == "make a drawer"
    assert events[1]["status"] == "success"
