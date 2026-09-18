"""Run scoring semantics via the demo seed (A18, A27) and capture dedupe (A34)."""

from __future__ import annotations

import pytest

from prompt_workbench.seed.demo_seed import ensure_demo_data
from prompt_workbench.services import CapturesService, ConflictError, RunsService
from prompt_workbench.services.context import Principal

ACTOR = Principal(kind="user", id="u1", username="tester")


@pytest.mark.asyncio
async def test_demo_run_scoring_baseline_passes_regressed_fails(ctx):
    info = await ensure_demo_data(ctx)
    runs = await RunsService(ctx).list_runs(info["project_id"])
    assert runs, "demo should create at least one run"
    run = runs[0]
    assert run["status"] == "succeeded"
    by_label = {c["label"]: c for c in run["summary"]["candidates"]}
    assert by_label["Baseline"]["pass_rate"] == 1.0
    assert by_label["Regressed"]["pass_rate"] == 0.0
    # regression makes the baseline gate pass and the regressed gate fail
    assert by_label["Baseline"]["gate_pass"] is True
    assert by_label["Regressed"]["gate_pass"] is False


@pytest.mark.asyncio
async def test_no_required_checks_is_unscored_not_full_pass(ctx):
    info = await ensure_demo_data(ctx)
    project_id = info["project_id"]
    runs_service = RunsService(ctx)
    prompts = await ctx.repo.find_many("prompts", {"project_id": project_id})
    action = next(p for p in prompts if p["slug"] == "extract-actions")
    dataset = (await ctx.repo.find_many("datasets", {"project_id": project_id}))[0]
    profile = (await ctx.repo.find_many("model_profiles", {"project_id": project_id}))[0]
    run = await runs_service.create_run(
        {
            "project_id": project_id,
            "kind": "evaluation",
            "dataset_id": dataset["id"],
            "candidates": [{"label": "A", "target": {"kind": "prompt", "id": action["id"], "selector": {"revision": 2}}, "model_profile_id": profile["id"]}],
            "checks": [],
            "repeats": 1,
        },
        actor=ACTOR,
        background=False,
    )
    summary = run["summary"]
    assert summary["has_required_checks"] is False
    assert summary["candidates"][0]["pass_rate"] is None


@pytest.mark.asyncio
async def test_capture_idempotency(ctx):
    info = await ensure_demo_data(ctx)
    captures = CapturesService(ctx)
    body = {"project_id": info["project_id"], "source": "test", "mode": "rendered",
            "rendered_messages": [{"role": "user", "content": "hi"}], "output": {"text": "ok"}}
    first, status1 = await captures.ingest(dict(body), "key-1", ACTOR)
    again, status2 = await captures.ingest(dict(body), "key-1", ACTOR)
    assert status1 == 201 and status2 == 200
    assert first["id"] == again["id"]
    with pytest.raises(ConflictError):
        await captures.ingest({**body, "output": {"text": "different"}}, "key-1", ACTOR)
