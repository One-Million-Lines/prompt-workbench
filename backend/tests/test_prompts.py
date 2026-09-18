"""Prompt draft/revision/label semantics (A03, A04, A05, A06, A07)."""

from __future__ import annotations

import pytest

from prompt_workbench.services import ConflictError, ProjectsService, PromptsService
from prompt_workbench.services.context import Principal

ACTOR = Principal(kind="user", id="u1", username="tester")


async def _prompt(ctx):
    project = await ProjectsService(ctx).create("P")
    prompts = PromptsService(ctx)
    prompt = await prompts.create(project["id"], "Greeter", "greeter", actor=ACTOR)
    return prompts, prompt


@pytest.mark.asyncio
async def test_autosave_changes_draft_only_then_explicit_revision(ctx):
    prompts, prompt = await _prompt(ctx)
    draft = await prompts.get_draft(prompt["id"])
    assert await prompts.latest_revision(prompt["id"]) is None

    content = draft["content"]
    content["messages"][1]["content"] = "Hello {{ name }}"
    content["input_schema"] = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    await prompts.update_draft(prompt["id"], content, draft["edit_sequence"], actor=ACTOR)
    assert await prompts.latest_revision(prompt["id"]) is None  # draft did not publish

    rev = await prompts.save_revision(prompt["id"], "first", actor=ACTOR)
    assert rev["version"] == 1


@pytest.mark.asyncio
async def test_stale_draft_returns_conflict(ctx):
    prompts, prompt = await _prompt(ctx)
    draft = await prompts.get_draft(prompt["id"])
    await prompts.update_draft(prompt["id"], draft["content"], draft["edit_sequence"], actor=ACTOR)
    with pytest.raises(ConflictError) as exc:
        await prompts.update_draft(prompt["id"], draft["content"], draft["edit_sequence"], actor=ACTOR)
    assert exc.value.code == "stale_draft"


@pytest.mark.asyncio
async def test_unchanged_save_does_not_consume_version(ctx):
    prompts, prompt = await _prompt(ctx)
    r1 = await prompts.save_revision(prompt["id"], "note1", actor=ACTOR)
    r2 = await prompts.save_revision(prompt["id"], "note2", actor=ACTOR)
    assert r2.get("unchanged") is True
    assert r2["version"] == r1["version"]


@pytest.mark.asyncio
async def test_label_conflict_and_ownership(ctx):
    prompts, prompt = await _prompt(ctx)
    await prompts.save_revision(prompt["id"], "v1", actor=ACTOR)
    await prompts.set_label(prompt["id"], "production", 1, None, actor=ACTOR)
    # stale expected-previous -> conflict
    with pytest.raises(ConflictError):
        await prompts.set_label(prompt["id"], "production", 1, None, actor=ACTOR)


@pytest.mark.asyncio
async def test_restore_creates_new_revision_without_changing_history(ctx):
    prompts, prompt = await _prompt(ctx)
    draft = await prompts.get_draft(prompt["id"])
    c = draft["content"]
    c["messages"][1]["content"] = "one"
    await prompts.update_draft(prompt["id"], c, draft["edit_sequence"], actor=ACTOR)
    await prompts.save_revision(prompt["id"], "v1", actor=ACTOR)

    draft = await prompts.get_draft(prompt["id"])
    c = draft["content"]
    c["messages"][1]["content"] = "two"
    await prompts.update_draft(prompt["id"], c, draft["edit_sequence"], actor=ACTOR)
    await prompts.save_revision(prompt["id"], "v2", actor=ACTOR)

    draft = await prompts.get_draft(prompt["id"])
    await prompts.restore_draft(prompt["id"], 1, draft["edit_sequence"], actor=ACTOR)
    rev3 = await prompts.save_revision(prompt["id"], "restore v1", actor=ACTOR)
    assert rev3["version"] == 3
    original = await prompts.get_revision(prompt["id"], 1)
    assert original["content"]["messages"][1]["content"] == "one"
