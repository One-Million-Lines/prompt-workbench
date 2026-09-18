"""Projects, connections and model-profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..services import AppContext, ConnectionsService, ModelProfilesService, ProjectsService
from .deps import get_context, get_principal
from .schemas import ConnectionCreate, ModelProfileCreate, ProjectCreate, ProjectSettingsUpdate

router = APIRouter(dependencies=[Depends(get_principal)])


@router.get("/projects")
async def list_projects(ctx: AppContext = Depends(get_context)):
    return await ProjectsService(ctx).list_projects()


@router.post("/projects", status_code=201)
async def create_project(body: ProjectCreate, ctx: AppContext = Depends(get_context)):
    return await ProjectsService(ctx).create(body.name, body.slug, body.settings)


@router.get("/projects/{project_id}")
async def get_project(project_id: str, ctx: AppContext = Depends(get_context)):
    return await ProjectsService(ctx).get(project_id)


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, body: ProjectSettingsUpdate, ctx: AppContext = Depends(get_context)):
    return await ProjectsService(ctx).update_settings(project_id, body.settings)


@router.get("/connections")
async def list_connections(ctx: AppContext = Depends(get_context)):
    return await ConnectionsService(ctx).list()


@router.post("/connections", status_code=201)
async def create_connection(body: ConnectionCreate, ctx: AppContext = Depends(get_context)):
    return await ConnectionsService(ctx).create(
        body.alias,
        body.provider,
        api_base=body.api_base,
        api_version=body.api_version,
        secret_env_name=body.secret_env_name,
        enabled=body.enabled,
    )


@router.get("/model-profiles")
async def list_profiles(project_id: str | None = None, ctx: AppContext = Depends(get_context)):
    return await ModelProfilesService(ctx).list(project_id)


@router.post("/model-profiles", status_code=201)
async def create_profile(body: ModelProfileCreate, ctx: AppContext = Depends(get_context)):
    return await ModelProfilesService(ctx).create(
        body.project_id,
        body.name,
        body.provider,
        body.model,
        connection_alias=body.connection_alias,
        parameters=body.parameters,
        timeout_seconds=body.timeout_seconds,
        retry_policy=body.retry_policy,
    )
