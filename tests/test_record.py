from __future__ import annotations

import json

from mini_articraft.record import Record, append_conversation, read_conversation


def test_record_saves_slim_run_summary(tmp_path) -> None:
    path = tmp_path / "record.json"
    record = Record(run_id="run_1", status="success", result="result/model.usdz")

    record.save(path)

    payload = json.loads(path.read_text())
    assert payload == {
        "run_id": "run_1",
        "status": "success",
        "attempts": 0,
        "error": "",
        "result": "result/model.usdz",
        "cost": 0.0,
        "token_usage": {},
    }

    loaded = Record.load(path)
    assert loaded.run_id == "run_1"
    assert loaded.status == "success"


def test_conversation_jsonl_is_append_only(tmp_path) -> None:
    path = tmp_path / "conversation.jsonl"

    append_conversation(path, {"role": "user", "content": "make a drawer"})
    append_conversation(path, {"role": "compiler", "status": "success"})

    events = read_conversation(path)
    assert [event["role"] for event in events] == ["user", "compiler"]
    assert events[0]["content"] == "make a drawer"
    assert events[1]["status"] == "success"
