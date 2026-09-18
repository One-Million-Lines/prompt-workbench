"""Renderer + canonical JSON conformance (A08, A09, A10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prompt_workbench.domain.canonical import canonical_json
from prompt_workbench.domain.rendering import TemplateError, render_prompt, render_string

FIXTURES = json.loads((Path(__file__).parents[2] / "examples" / "javascript" / "fixtures.json").read_text("utf-8"))


@pytest.mark.parametrize("case", FIXTURES["canonical"])
def test_canonical_fixtures(case):
    assert canonical_json(case["value"]) == case["expected"]


@pytest.mark.parametrize("case", FIXTURES["render"])
def test_render_fixtures(case):
    assert render_string(case["template"], case["values"], set(case["declared"])) == case["expected"]


def test_undeclared_variable_fails():
    with pytest.raises(TemplateError) as exc:
        render_string("{{ ghost }}", {}, set())
    assert exc.value.code == "template_undeclared_variable"


def test_unsupported_expression_rejected():
    for expr in ["{{ user.name }}", "{{ a|b }}", "{{ f() }}"]:
        with pytest.raises(TemplateError):
            render_string(expr, {"a": "x"}, {"a"})


def test_missing_variable_before_model_call():
    defn = {"kind": "chat", "messages": [{"role": "user", "content": "{{ x }}"}],
            "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}}
    with pytest.raises(TemplateError):
        render_prompt(defn, {})


def test_wrong_type_rejected():
    defn = {"kind": "chat", "messages": [{"role": "user", "content": "{{ n }}"}],
            "input_schema": {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}}
    with pytest.raises(Exception):
        render_prompt(defn, {"n": "not-an-int"})


def test_extra_input_rejected_additional_properties():
    defn = {"kind": "chat", "messages": [{"role": "user", "content": "hi"}],
            "input_schema": {"type": "object", "properties": {}, "required": []}}
    with pytest.raises(Exception):
        render_prompt(defn, {"unexpected": 1})
