"""Release build + verification + portable runtime rendering (A38, A40)."""

from __future__ import annotations

import pytest

from prompt_workbench.seed.demo_seed import ensure_demo_data
from prompt_workbench.services import ReleasesService
from prompt_workbench_runtime import Bundle, BundleError


@pytest.mark.asyncio
async def test_release_builds_verifies_and_renders_offline(ctx):
    info = await ensure_demo_data(ctx)
    release = (await ctx.repo.find_many("releases", {}))[0]

    # Verify via the service (offline, no DB access to prompt content).
    result = ReleasesService.verify_bundle(release["bundle_dir"])
    assert result["ok"], result["problems"]

    # Load and render with the fully independent runtime package.
    bundle = Bundle.load(release["bundle_dir"], verify=True)
    assert "extract-actions" in bundle.entrypoints()
    request = bundle.render("extract-actions", {"email_text": "Send the report."})
    assert request.messages[0]["role"] == "system"
    assert "Send the report." in request.messages[1]["content"]
    assert request.output["mode"] == "json"


@pytest.mark.asyncio
async def test_tampered_bundle_fails_verification(ctx, tmp_path):
    await ensure_demo_data(ctx)
    release = (await ctx.repo.find_many("releases", {}))[0]
    from pathlib import Path

    bundle_dir = Path(release["bundle_dir"])
    target = next(bundle_dir.glob("prompts/*/v*.json"))
    target.write_text(target.read_text("utf-8") + "\n// tampered", "utf-8")
    with pytest.raises(BundleError):
        Bundle.load(bundle_dir, verify=True)
