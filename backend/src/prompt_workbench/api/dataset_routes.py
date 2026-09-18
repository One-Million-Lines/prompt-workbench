"""Dataset and case routes, including import/export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from ..services import AppContext, DatasetsService
from .deps import get_context, get_principal
from .schemas import CaseCreate, CaseUpdate, DatasetCreate, ImportCommit

router = APIRouter(dependencies=[Depends(get_principal)])


@router.get("/datasets")
async def list_datasets(project_id: str, include_archived: bool = False, ctx: AppContext = Depends(get_context)):
    return await DatasetsService(ctx).list(project_id, include_archived=include_archived)


@router.post("/datasets", status_code=201)
async def create_dataset(body: DatasetCreate, ctx: AppContext = Depends(get_context)):
    return await DatasetsService(ctx).create(body.project_id, body.name, description=body.description, input_schema=body.input_schema, tags=body.tags)


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, ctx: AppContext = Depends(get_context)):
    return await DatasetsService(ctx).get(dataset_id)


@router.get("/datasets/{dataset_id}/cases")
async def list_cases(dataset_id: str, ctx: AppContext = Depends(get_context)):
    return await DatasetsService(ctx).list_cases(dataset_id)


@router.post("/datasets/{dataset_id}/cases", status_code=201)
async def add_case(dataset_id: str, body: CaseCreate, ctx: AppContext = Depends(get_context)):
    return await DatasetsService(ctx).add_case(
        dataset_id, name=body.name, inputs=body.inputs, expected=body.expected, tags=body.tags, critical=body.critical
    )


@router.patch("/datasets/{dataset_id}/cases/{case_id}")
async def update_case(dataset_id: str, case_id: str, body: CaseUpdate, ctx: AppContext = Depends(get_context)):
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    return await DatasetsService(ctx).update_case(dataset_id, case_id, changes)


@router.delete("/datasets/{dataset_id}/cases/{case_id}", status_code=204)
async def delete_case(dataset_id: str, case_id: str, ctx: AppContext = Depends(get_context)):
    await DatasetsService(ctx).delete_case(dataset_id, case_id)
    return None


@router.post("/datasets/{dataset_id}/import-preview")
async def import_preview(dataset_id: str, request: Request, fmt: str = "jsonl", ctx: AppContext = Depends(get_context)):
    raw = await request.body()
    valid, errors = DatasetsService(ctx).parse_import(raw, fmt)
    return {"valid_count": len(valid), "error_count": len(errors), "valid": valid[:50], "errors": errors[:50]}


@router.post("/datasets/{dataset_id}/imports", status_code=201)
async def commit_import(dataset_id: str, body: ImportCommit, ctx: AppContext = Depends(get_context)):
    return await DatasetsService(ctx).commit_import(dataset_id, body.rows, atomic=body.atomic)


@router.get("/datasets/{dataset_id}/export")
async def export_dataset(dataset_id: str, format: str = "jsonl", ctx: AppContext = Depends(get_context)):
    content = await DatasetsService(ctx).export(dataset_id, format)
    media = "application/x-ndjson" if format == "jsonl" else "application/json"
    return Response(content=content, media_type=media)
