"""Command-line interface (Typer)."""

from __future__ import annotations

import asyncio
import getpass
import json
from pathlib import Path

import typer

from .config import Settings
from .services import AppContext, AuthService
from .services.releases_service import ReleasesService
from .storage import build_repository

app = typer.Typer(help="Prompt Workbench — local prompt management, versioning and evaluation.", no_args_is_help=True)


def _settings(data_dir: str, *, backend: str = "sqlite", demo: bool = False, provider_mode: str = "auto") -> Settings:
    return Settings(data_dir=Path(data_dir).expanduser().resolve(), storage_backend=backend, demo_mode=demo, provider_mode=provider_mode)


async def _with_repo(settings: Settings):
    repo = build_repository(settings)
    await repo.initialize()
    return repo, AppContext(settings, repo)


@app.command()
def init(
    data_dir: str = typer.Option("./data", help="Directory for the database and secrets."),
    backend: str = typer.Option("sqlite", help="Storage backend: sqlite (demo) or mongo (primary)."),
    username: str = typer.Option(None, help="First account username; prompts if omitted."),
):
    """Create the data store, JWT secret and the first local user."""
    settings = _settings(data_dir, backend=backend)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.resolved_jwt_secret()

    async def _run():
        repo, ctx = await _with_repo(settings)
        try:
            auth = AuthService(ctx)
            if await auth.count_users() > 0:
                typer.secho("Store already initialized (users exist). Refusing to reinitialize.", fg="yellow")
                raise typer.Exit(code=1)
            uname = username or typer.prompt("Username")
            password = getpass.getpass("Password: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                typer.secho("Passwords do not match.", fg="red")
                raise typer.Exit(code=1)
            await auth.create_user(uname, password)
            typer.secho(f"Initialized store at {settings.data_dir} with user {uname!r}.", fg="green")
        finally:
            await repo.close()

    asyncio.run(_run())


@app.command()
def serve(
    data_dir: str = typer.Option("./data", help="Data directory."),
    backend: str = typer.Option("sqlite", help="Storage backend."),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8765),
    provider_mode: str = typer.Option("auto", help="auto | mock | litellm"),
):
    """Start the API server and durable scheduler."""
    import uvicorn

    from .app import create_app

    settings = _settings(data_dir, backend=backend, provider_mode=provider_mode)
    settings.host, settings.port = host, port
    app_instance = create_app(settings)
    typer.secho(f"Prompt Workbench listening on http://{host}:{port}", fg="green")
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


@app.command()
def demo(
    data_dir: str = typer.Option("./demo-data", help="Demo data directory (SQLite)."),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8765),
):
    """Seed synthetic data and serve the demo (SQLite, mock provider, offline)."""
    import uvicorn

    from .app import create_app
    from .seed import DEMO_PASSWORD, DEMO_USERNAME

    settings = _settings(data_dir, backend="sqlite", demo=True, provider_mode="mock")
    settings.host, settings.port = host, port
    app_instance = create_app(settings)
    typer.secho("Demo mode — synthetic data only, no external model calls.", fg="cyan")
    typer.secho(f"Login: {DEMO_USERNAME} / {DEMO_PASSWORD}", fg="green")
    typer.secho(f"Open http://{host}:{port}", fg="green")
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


user_app = typer.Typer(help="Local account management (server must be stopped).")
app.add_typer(user_app, name="user")


@user_app.command("add")
def user_add(username: str, data_dir: str = typer.Option("./data"), backend: str = typer.Option("sqlite")):
    settings = _settings(data_dir, backend=backend)

    async def _run():
        repo, ctx = await _with_repo(settings)
        try:
            password = getpass.getpass("Password: ")
            await AuthService(ctx).create_user(username, password)
            typer.secho(f"Created user {username!r}.", fg="green")
        finally:
            await repo.close()

    asyncio.run(_run())


@user_app.command("reset-password")
def user_reset(username: str, data_dir: str = typer.Option("./data"), backend: str = typer.Option("sqlite")):
    settings = _settings(data_dir, backend=backend)

    async def _run():
        repo, ctx = await _with_repo(settings)
        try:
            password = getpass.getpass("New password: ")
            await AuthService(ctx).set_password(username, password)
            typer.secho(f"Password reset for {username!r}; existing tokens invalidated.", fg="green")
        finally:
            await repo.close()

    asyncio.run(_run())


@user_app.command("disable")
def user_disable(username: str, data_dir: str = typer.Option("./data"), backend: str = typer.Option("sqlite")):
    settings = _settings(data_dir, backend=backend)

    async def _run():
        repo, ctx = await _with_repo(settings)
        try:
            await AuthService(ctx).disable_user(username)
            typer.secho(f"Disabled {username!r}.", fg="green")
        finally:
            await repo.close()

    asyncio.run(_run())


bundle_app = typer.Typer(help="Release bundle utilities.")
app.add_typer(bundle_app, name="bundle")


@bundle_app.command("verify")
def bundle_verify(path: str):
    """Offline verification of an exported release bundle (no DB or model calls)."""
    result = ReleasesService.verify_bundle(path)
    typer.echo(json.dumps(result, indent=2))
    raise typer.Exit(code=0 if result["ok"] else 1)


@app.command()
def migrate(data_dir: str = typer.Option("./data"), backend: str = typer.Option("sqlite")):
    """Initialize/prepare the store (document collections are created on demand)."""
    settings = _settings(data_dir, backend=backend)

    async def _run():
        repo = build_repository(settings)
        await repo.initialize()
        await repo.close()
        typer.secho("Store prepared.", fg="green")

    asyncio.run(_run())


@app.command()
def eval(
    file: str = typer.Option(..., "--file", help="Path to a run-request JSON file."),
    base_url: str = typer.Option("http://127.0.0.1:8765", help="Running server base URL."),
    username: str = typer.Option(None, envvar="PROMPT_WORKBENCH_USERNAME"),
    password: str = typer.Option(None, envvar="PROMPT_WORKBENCH_PASSWORD"),
    api_key: str = typer.Option(None, envvar="PROMPT_WORKBENCH_API_KEY"),
    wait: bool = typer.Option(True, help="Wait for completion."),
    report: str = typer.Option(None, help="Write the JSON report to this path."),
):
    """Execute an evaluation via the running API and return a CI exit code.

    Exit codes: 0 = gate pass, 1 = completed quality/gate failure, 2 = setup/infra/incomplete.
    Credentials come from environment variables, never command-line values in CI logs.
    """
    import time

    import httpx

    run_request = json.loads(Path(file).read_text("utf-8"))

    try:
        with httpx.Client(base_url=base_url, timeout=30) as client:
            if api_key:
                headers = {"Authorization": f"Bearer {api_key}"}
            else:
                if not username or not password:
                    typer.secho("Provide PROMPT_WORKBENCH_API_KEY or username/password env vars.", fg="red")
                    raise typer.Exit(code=2)
                login = client.post("/api/v1/auth/login", json={"username": username, "password": password})
                if login.status_code != 200:
                    typer.secho("Authentication failed.", fg="red")
                    raise typer.Exit(code=2)
                headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            created = client.post("/api/v1/runs", json=run_request, headers=headers)
            if created.status_code not in (200, 202):
                typer.secho(f"Run rejected: {created.text}", fg="red")
                raise typer.Exit(code=2)
            run_id = created.json()["id"]

            status = created.json().get("status", "queued")
            if wait:
                for _ in range(600):
                    run = client.get(f"/api/v1/runs/{run_id}", headers=headers).json()
                    status = run["status"]
                    if status in ("succeeded", "failed", "completed_with_errors", "cancelled"):
                        break
                    typer.echo(f"  status: {status}")
                    time.sleep(1)

            result = client.get(f"/api/v1/runs/{run_id}/report", headers=headers).json()
    except httpx.HTTPError as exc:
        typer.secho(f"Could not reach server: {exc}", fg="red")
        raise typer.Exit(code=2) from exc

    typer.echo(json.dumps(result, indent=2))
    if report:
        Path(report).write_text(json.dumps(result, indent=2), "utf-8")
    raise typer.Exit(code=result.get("exit_code", 2))


if __name__ == "__main__":
    app()
