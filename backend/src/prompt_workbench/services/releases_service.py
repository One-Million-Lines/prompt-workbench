"""Publishing: build immutable, portable release bundles and verify them."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from ..domain import canonical_json, content_digest, new_uuid, sha256_bytes, utcnow
from ..storage import Collections
from .context import AppContext, Principal
from .errors import NotFoundError, ValidationError
from .prompts_service import PromptsService

BUNDLE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Prompt Workbench release bundle manifest",
    "type": "object",
    "required": ["format_version", "release_id", "entrypoints", "files", "semantic_sha256"],
}


class ReleasesService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo
        self.prompts = PromptsService(ctx)

    def _releases_dir(self) -> Path:
        path = self.ctx.settings.data_dir / "releases"
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def build(self, project_id: str, name: str, selection: dict, actor: Principal | None = None) -> dict:
        prompt_selections = selection.get("prompts", [])
        if not prompt_selections:
            raise ValidationError("A release must select at least one prompt", code="empty_selection")

        release_id = new_uuid()
        entrypoints: dict[str, Any] = {"prompts": {}, "chains": {}}
        required_connections: set[str] = set()
        files: dict[str, str] = {}
        semantic_parts: list[Any] = []

        build_dir = self._releases_dir() / release_id
        if build_dir.exists():
            shutil.rmtree(build_dir)
        (build_dir / "prompts").mkdir(parents=True, exist_ok=True)

        for entry in prompt_selections:
            prompt = await self.prompts.get(entry["prompt_id"])
            content, provenance = await self.prompts.resolve_content(entry["prompt_id"], entry.get("selector", {}))
            version = provenance.get("version")
            if version is None:
                raise ValidationError("Release selections must resolve to a saved revision", code="draft_not_publishable")
            portable = _portable_prompt(prompt, content, version)
            rel_path = f"prompts/{prompt['id']}/v{version}.json"
            file_bytes = (canonical_json(portable) + "\n").encode("utf-8")
            target = build_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(file_bytes)
            files[rel_path] = sha256_bytes(file_bytes)
            entrypoints["prompts"][prompt["id"]] = {"slug": prompt["slug"], "revision": version, "path": rel_path}
            semantic_parts.append(portable)
            model = content.get("default_model") or {}
            if model.get("connection_alias"):
                required_connections.add(model["connection_alias"])

        # schema + readme files
        schema_bytes = (json.dumps(BUNDLE_SCHEMA, indent=2) + "\n").encode("utf-8")
        (build_dir / "schemas").mkdir(parents=True, exist_ok=True)
        (build_dir / "schemas" / "bundle.schema.json").write_bytes(schema_bytes)
        files["schemas/bundle.schema.json"] = sha256_bytes(schema_bytes)

        readme = _bundle_readme(name, release_id, sorted(required_connections))
        readme_bytes = readme.encode("utf-8")
        (build_dir / "README.md").write_bytes(readme_bytes)
        files["README.md"] = sha256_bytes(readme_bytes)

        semantic_digest = content_digest(semantic_parts)
        manifest = {
            "format_version": 1,
            "template_engine": "simple-v1",
            "release_id": release_id,
            "project_id": project_id,
            "name": name,
            "created_at": utcnow(),
            "entrypoints": entrypoints,
            "required_connections": sorted(required_connections),
            "files": files,
            "semantic_sha256": semantic_digest,
        }
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
        (build_dir / "manifest.json").write_bytes(manifest_bytes)

        # Deterministic ZIP (sorted paths).
        zip_path = self._releases_dir() / f"{release_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted([*files.keys(), "manifest.json"]):
                zf.write(build_dir / file_path, file_path)

        release = {
            "id": release_id,
            "project_id": project_id,
            "name": name,
            "status": "ready",
            "selection_snapshot": selection,
            "manifest": manifest,
            "semantic_sha256": semantic_digest,
            "artifact_path": str(zip_path),
            "bundle_dir": str(build_dir),
            "created_by": actor.id if actor else None,
            "created_at": utcnow(),
        }
        await self.repo.insert_one(Collections.RELEASES, release)
        await self.ctx.log_event(actor, "release.build", "release", release_id, project_id, {"name": name, "digest": semantic_digest})
        return _public_release(release)

    async def list(self, project_id: str) -> list[dict]:
        rows = await self.repo.find_many(Collections.RELEASES, {"project_id": project_id}, sort=[("created_at", -1)])
        return [_public_release(r) for r in rows]

    async def get(self, release_id: str) -> dict:
        release = await self.repo.find_one(Collections.RELEASES, {"id": release_id})
        if not release:
            raise NotFoundError(f"Release {release_id} not found")
        return release

    async def artifact_path(self, release_id: str) -> Path:
        release = await self.get(release_id)
        if release["status"] != "ready":
            raise ValidationError("Release is not ready for download", code="not_ready")
        return Path(release["artifact_path"])

    @staticmethod
    def verify_bundle(bundle_dir: str | Path) -> dict:
        """Offline verification: recompute file hashes and check the manifest."""
        bundle = Path(bundle_dir)
        manifest_path = bundle / "manifest.json"
        if not manifest_path.exists():
            raise ValidationError("manifest.json is missing", code="invalid_bundle")
        manifest = json.loads(manifest_path.read_text("utf-8"))
        problems = []
        for rel_path, expected in manifest.get("files", {}).items():
            target = bundle / rel_path
            if ".." in rel_path or Path(rel_path).is_absolute():
                problems.append(f"unsafe path: {rel_path}")
                continue
            if not target.exists():
                problems.append(f"missing file: {rel_path}")
                continue
            actual = sha256_bytes(target.read_bytes())
            if actual != expected:
                problems.append(f"hash mismatch: {rel_path}")
        return {"ok": not problems, "problems": problems, "release_id": manifest.get("release_id")}


def _portable_prompt(prompt: dict, content: dict, version: int) -> dict:
    return {
        "format_version": 1,
        "template_engine": "simple-v1",
        "prompt_id": prompt["id"],
        "slug": prompt["slug"],
        "revision": version,
        "kind": content.get("kind"),
        "messages": content.get("messages"),
        "text": content.get("text"),
        "input_schema": content.get("input_schema"),
        "output": content.get("output"),
        "tools": content.get("tools", []),
        "tool_choice": content.get("tool_choice"),
        "model": content.get("default_model"),
    }


def _bundle_readme(name: str, release_id: str, connections: list[str]) -> str:
    conns = "\n".join(f"- `{c}`" for c in connections) or "- (none)"
    return f"""# Release: {name}

Release ID: `{release_id}`

This is a self-contained Prompt Workbench release bundle. It renders with the workbench
stopped and requires no database.

## Required connection aliases
{conns}

## Load in Python
```python
from prompt_workbench_runtime import Bundle
bundle = Bundle.load("./{release_id}", verify=True)
request = bundle.render("<slug>", {{"variable": "value"}})
```

Format: `simple-v1`. Verify integrity with `prompt-workbench bundle verify ./{release_id}`.
"""


def _public_release(release: dict) -> dict:
    return {
        "id": release["id"],
        "project_id": release["project_id"],
        "name": release["name"],
        "status": release["status"],
        "semantic_sha256": release["semantic_sha256"],
        "manifest": release.get("manifest"),
        "created_at": release["created_at"],
    }
