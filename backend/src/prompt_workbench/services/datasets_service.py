"""Datasets and input-set cases with immutable case revisions and snapshots."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from ..domain import content_digest, new_uuid, utcnow, validate_schema_document
from ..domain.schema import SchemaValidationError, validate_instance
from ..storage import Collections
from .context import AppContext, Principal
from .errors import NotFoundError, ValidationError

MAX_IMPORT_ROWS = 5000


class DatasetsService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo

    async def list(self, project_id: str, *, include_archived: bool = False) -> list[dict]:
        flt: dict[str, Any] = {"project_id": project_id}
        if not include_archived:
            flt["archived_at"] = None
        return await self.repo.find_many(Collections.DATASETS, flt, sort=[("created_at", 1)])

    async def get(self, dataset_id: str) -> dict:
        dataset = await self.repo.find_one(Collections.DATASETS, {"id": dataset_id})
        if not dataset:
            raise NotFoundError(f"Dataset {dataset_id} not found")
        return dataset

    async def create(self, project_id: str, name: str, *, description: str = "", input_schema: dict | None = None, tags: list[str] | None = None) -> dict:
        schema = input_schema or {"type": "object", "properties": {}, "required": []}
        validate_schema_document(schema)
        dataset = {
            "id": new_uuid(),
            "project_id": project_id,
            "name": name,
            "description": description,
            "input_schema": schema,
            "tags": tags or [],
            "revision": 1,
            "archived_at": None,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.DATASETS, dataset)
        return dataset

    async def _bump_revision(self, dataset: dict) -> int:
        dataset["revision"] = int(dataset.get("revision", 1)) + 1
        dataset["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.DATASETS, {"id": dataset["id"]}, dataset)
        return dataset["revision"]

    # --- cases -------------------------------------------------------------
    async def list_cases(self, dataset_id: str, *, include_deleted: bool = False) -> list[dict]:
        flt: dict[str, Any] = {"dataset_id": dataset_id}
        if not include_deleted:
            flt["deleted_at"] = None
        return await self.repo.find_many(Collections.CASES, flt, sort=[("created_at", 1)])

    async def add_case(self, dataset_id: str, *, name: str, inputs: dict, expected: Any = None, tags: list[str] | None = None, critical: bool = False, source_capture_id: str | None = None, validate: bool = True) -> dict:
        dataset = await self.get(dataset_id)
        if validate:
            self._validate_case_inputs(dataset, inputs)
        revision = await self._bump_revision(dataset)
        case = {
            "id": new_uuid(),
            "dataset_id": dataset_id,
            "name": name,
            "inputs": inputs,
            "expected": expected,
            "tags": tags or [],
            "critical": critical,
            "source_capture_id": source_capture_id,
            "version": 1,
            "content_sha256": content_digest({"inputs": inputs, "expected": expected}),
            "dataset_revision": revision,
            "deleted_at": None,
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        await self.repo.insert_one(Collections.CASES, case)
        await self._append_case_revision(case)
        return case

    async def update_case(self, dataset_id: str, case_id: str, changes: dict) -> dict:
        dataset = await self.get(dataset_id)
        case = await self.repo.find_one(Collections.CASES, {"id": case_id, "dataset_id": dataset_id})
        if not case or case.get("deleted_at"):
            raise NotFoundError(f"Case {case_id} not found")
        for key in ("name", "inputs", "expected", "tags", "critical"):
            if key in changes:
                case[key] = changes[key]
        if "inputs" in changes:
            self._validate_case_inputs(dataset, case["inputs"])
        case["version"] = int(case.get("version", 1)) + 1
        case["content_sha256"] = content_digest({"inputs": case["inputs"], "expected": case.get("expected")})
        case["dataset_revision"] = await self._bump_revision(dataset)
        case["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.CASES, {"id": case_id}, case)
        await self._append_case_revision(case)
        return case

    async def delete_case(self, dataset_id: str, case_id: str) -> None:
        dataset = await self.get(dataset_id)
        case = await self.repo.find_one(Collections.CASES, {"id": case_id, "dataset_id": dataset_id})
        if not case or case.get("deleted_at"):
            raise NotFoundError(f"Case {case_id} not found")
        case["deleted_at"] = utcnow()
        case["dataset_revision"] = await self._bump_revision(dataset)
        await self.repo.replace_one(Collections.CASES, {"id": case_id}, case)

    async def _append_case_revision(self, case: dict) -> None:
        await self.repo.insert_one(
            Collections.CASE_REVISIONS,
            {
                "id": new_uuid(),
                "case_id": case["id"],
                "dataset_id": case["dataset_id"],
                "version": case["version"],
                "payload": {"inputs": case["inputs"], "expected": case.get("expected"), "name": case["name"]},
                "content_sha256": case["content_sha256"],
                "dataset_revision": case["dataset_revision"],
                "created_at": utcnow(),
            },
        )

    def _validate_case_inputs(self, dataset: dict, inputs: dict) -> None:
        schema = dataset.get("input_schema")
        if not schema or not schema.get("properties"):
            return
        try:
            validate_instance(schema, inputs)
        except SchemaValidationError as exc:
            raise ValidationError("Case inputs do not match dataset schema", code="invalid_case", details={"errors": exc.errors}) from exc

    # --- snapshot ----------------------------------------------------------
    async def snapshot_cases(self, dataset_id: str, case_ids: list[str] | None = None) -> dict:
        """Freeze the exact case payloads for a run so later edits cannot change results."""
        dataset = await self.get(dataset_id)
        cases = await self.list_cases(dataset_id)
        if case_ids is not None:
            wanted = set(case_ids)
            cases = [c for c in cases if c["id"] in wanted]
        frozen = [
            {
                "case_id": c["id"],
                "name": c["name"],
                "inputs": c["inputs"],
                "expected": c.get("expected"),
                "critical": c.get("critical", False),
                "tags": c.get("tags", []),
                "version": c.get("version", 1),
            }
            for c in cases
        ]
        snapshot = {
            "id": new_uuid(),
            "dataset_id": dataset_id,
            "dataset_revision": dataset.get("revision"),
            "frozen_cases": frozen,
            "content_sha256": content_digest(frozen),
            "created_at": utcnow(),
        }
        return snapshot

    # --- import / export ---------------------------------------------------
    def parse_import(self, raw: bytes, fmt: str, *, mapping: dict | None = None) -> tuple[list[dict], list[dict]]:
        """Return (valid_rows, errors) as case dicts without persisting."""
        if len(raw) > 10 * 1024 * 1024:
            raise ValidationError("Import exceeds 10 MiB", code="import_too_large", status_code=413)
        if fmt == "json":
            records = json.loads(raw.decode("utf-8"))
            if not isinstance(records, list):
                raise ValidationError("JSON import must be an array of cases", code="invalid_import")
        elif fmt == "jsonl":
            records = []
            errors: list[dict] = []
            for i, line in enumerate(raw.decode("utf-8").splitlines()):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    errors.append({"row": i + 1, "error": str(exc)})
            return self._normalize_records(records, errors)
        elif fmt == "csv":
            return self._parse_csv(raw, mapping or {})
        else:
            raise ValidationError(f"Unsupported import format {fmt!r}", code="invalid_format")
        return self._normalize_records(records, [])

    def _normalize_records(self, records: list[dict], errors: list[dict]) -> tuple[list[dict], list[dict]]:
        if len(records) > MAX_IMPORT_ROWS:
            raise ValidationError(f"Import exceeds {MAX_IMPORT_ROWS} rows", code="import_too_large", status_code=413)
        valid = []
        for i, record in enumerate(records):
            if not isinstance(record, dict) or "inputs" not in record:
                errors.append({"row": i + 1, "error": "missing 'inputs' object"})
                continue
            valid.append(
                {
                    "name": record.get("name", f"case-{i + 1}"),
                    "inputs": record["inputs"],
                    "expected": record.get("expected"),
                    "tags": record.get("tags", []),
                    "critical": bool(record.get("critical", False)),
                }
            )
        return valid, errors

    def _parse_csv(self, raw: bytes, mapping: dict) -> tuple[list[dict], list[dict]]:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        json_columns = set(mapping.get("json_columns", []))
        valid, errors = [], []
        for i, row in enumerate(reader):
            inputs: dict[str, Any] = {}
            for column, value in row.items():
                if column is None:
                    continue
                if column in json_columns:
                    try:
                        inputs[column] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        errors.append({"row": i + 1, "error": f"column {column} is not valid JSON"})
                        inputs[column] = value
                else:
                    inputs[column] = value  # strings by default, preserving leading zeros
            valid.append({"name": f"case-{i + 1}", "inputs": inputs, "expected": None, "tags": [], "critical": False})
        return valid, errors

    async def commit_import(self, dataset_id: str, rows: list[dict], *, atomic: bool = True) -> dict:
        dataset = await self.get(dataset_id)
        created = 0
        for row in rows:
            self._validate_case_inputs(dataset, row["inputs"])
        for row in rows:
            await self.add_case(dataset_id, name=row["name"], inputs=row["inputs"], expected=row.get("expected"), tags=row.get("tags", []), critical=row.get("critical", False), validate=False)
            created += 1
        return {"created": created}

    async def export(self, dataset_id: str, fmt: str = "jsonl") -> str:
        cases = await self.list_cases(dataset_id)
        if fmt == "jsonl":
            return "\n".join(json.dumps({"name": c["name"], "inputs": c["inputs"], "expected": c.get("expected"), "tags": c.get("tags", []), "critical": c.get("critical", False)}, ensure_ascii=False) for c in cases)
        if fmt == "json":
            return json.dumps([{"name": c["name"], "inputs": c["inputs"], "expected": c.get("expected")} for c in cases], ensure_ascii=False, indent=2)
        raise ValidationError(f"Unsupported export format {fmt!r}", code="invalid_format")
