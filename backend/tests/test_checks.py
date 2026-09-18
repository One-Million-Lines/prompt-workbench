"""Deterministic checks (A16, A17 basics) and pointer resolution."""

from __future__ import annotations

from prompt_workbench.domain.checks import evaluate_check, resolve_pointer


def env(text=None, json_value=None, tool_calls=None):
    return {"text": text, "json": json_value, "tool_calls": tool_calls or []}


def test_json_valid():
    assert evaluate_check({"type": "json_valid"}, env(text='{"a":1}'), None).outcome == "pass"
    assert evaluate_check({"type": "json_valid"}, env(text="not json"), None).outcome == "fail"


def test_json_schema():
    schema = {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}
    assert evaluate_check({"type": "json_schema", "schema": schema}, env(text='{"a":1}'), None).outcome == "pass"
    assert evaluate_check({"type": "json_schema", "schema": schema}, env(text='{"a":"x"}'), None).outcome == "fail"


def test_equals_and_contains():
    assert evaluate_check({"type": "equals", "expected": "hi"}, env(text="hi"), None).outcome == "pass"
    assert evaluate_check({"type": "contains", "value": "wor"}, env(text="hello world"), None).outcome == "pass"
    assert evaluate_check({"type": "not_contains", "value": "zzz"}, env(text="hello"), None).outcome == "pass"


def test_json_pointer_equals_and_array_length():
    e = env(text='{"actions":[{"title":"a"},{"title":"b"}]}')
    assert evaluate_check({"type": "array_length", "pointer": "/actions", "min": 1}, e, None).outcome == "pass"
    assert evaluate_check({"type": "array_length", "pointer": "/actions", "max": 1}, e, None).outcome == "fail"
    chk = {"type": "json_pointer_equals", "actual_pointer": "/actions/0/title", "expected": "a"}
    assert evaluate_check(chk, e, None).outcome == "pass"


def test_tool_call_check():
    e = env(tool_calls=[{"name": "create_task", "arguments": {"title": "x"}}])
    ok = evaluate_check({"type": "tool_call", "name": "create_task", "count": 1}, e, None)
    assert ok.outcome == "pass"
    bad = evaluate_check({"type": "tool_call", "name": "other"}, e, None)
    assert bad.outcome == "fail"


def test_resolve_pointer_missing_path():
    import pytest

    from prompt_workbench.domain.checks import PointerError

    with pytest.raises(PointerError):
        resolve_pointer({"a": 1}, "/b")
