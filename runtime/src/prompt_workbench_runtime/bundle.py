"""Load, verify and render Prompt Workbench release bundles — no DB, no network."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .canonical import sha256_bytes
from .renderer import RenderedRequest, render_prompt


class BundleError(Exception):
    pass


class Bundle:
    def __init__(self, root: Path, manifest: dict[str, Any]):
        self.root = root
        self.manifest = manifest

    @classmethod
    def load(cls, path: str | Path, verify: bool = True) -> "Bundle":
        root = Path(path)
        manifest_path = root / "manifest.json"
        if not manifest_path.exists():
            raise BundleError("manifest.json not found")
        manifest = json.loads(manifest_path.read_text("utf-8"))
        if manifest.get("format_version") != 1:
            raise BundleError(f"unsupported format_version: {manifest.get('format_version')}")
        bundle = cls(root, manifest)
        if verify:
            problems = bundle.verify()
            if problems:
                raise BundleError("bundle verification failed: " + "; ".join(problems))
        return bundle

    def verify(self) -> list[str]:
        problems: list[str] = []
        for rel_path, expected in self.manifest.get("files", {}).items():
            if ".." in rel_path or Path(rel_path).is_absolute():
                problems.append(f"unsafe path: {rel_path}")
                continue
            target = self.root / rel_path
            if not target.exists():
                problems.append(f"missing file: {rel_path}")
                continue
            if sha256_bytes(target.read_bytes()) != expected:
                problems.append(f"hash mismatch: {rel_path}")
        return problems

    def _resolve_entrypoint(self, ref: str) -> dict[str, Any]:
        prompts = self.manifest.get("entrypoints", {}).get("prompts", {})
        if ref in prompts:
            return prompts[ref]
        for entry in prompts.values():
            if entry.get("slug") == ref:
                return entry
        raise BundleError(f"unknown entrypoint: {ref}")

    def load_prompt(self, ref: str) -> dict[str, Any]:
        entry = self._resolve_entrypoint(ref)
        return json.loads((self.root / entry["path"]).read_text("utf-8"))

    def render(self, ref: str, inputs: dict[str, Any]) -> RenderedRequest:
        portable = self.load_prompt(ref)
        return render_prompt(portable, inputs)

    def entrypoints(self) -> list[str]:
        return [entry["slug"] for entry in self.manifest.get("entrypoints", {}).get("prompts", {}).values()]
