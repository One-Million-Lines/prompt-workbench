# Deployment

Prompt Workbench targets a developer laptop or a single private development server.

## Configuration (environment variables, prefix `PROMPT_WORKBENCH_`)

| Variable | Default | Notes |
|---|---|---|
| `PROMPT_WORKBENCH_STORAGE_BACKEND` | `sqlite` | `sqlite` (demo) or `mongo` (primary). |
| `PROMPT_WORKBENCH_DATA_DIR` | `./data` | SQLite DB, JWT secret and release bundles. |
| `PROMPT_WORKBENCH_MONGO_URI` | `mongodb://127.0.0.1:27017` | Used when backend = mongo. |
| `PROMPT_WORKBENCH_MONGO_DB` | `prompt_workbench` | Mongo database name. |
| `PROMPT_WORKBENCH_HOST` / `_PORT` | `127.0.0.1` / `8765` | Bind address. |
| `PROMPT_WORKBENCH_JWT_SECRET` | (generated) | 32+ random bytes; auto-created in the data dir if unset. |
| `PROMPT_WORKBENCH_PROVIDER_MODE` | `auto` | `auto` \| `mock` \| `litellm`. |
| `PROMPT_WORKBENCH_CORS_ORIGINS` | Vite dev origins | JSON list for browser access. |

Provider credentials are supplied as their own environment variables and referenced by **name**
from a connection (e.g. a connection with `secret_env_name=OPENAI_API_KEY`).

## Local install

```bash
pip install -e backend
prompt-workbench init --data-dir ./data     # creates store + first user + JWT secret
prompt-workbench serve --data-dir ./data     # http://127.0.0.1:8765
```

Run entirely offline against the mock provider with `--provider-mode mock`.

## MongoDB (primary backend)

```bash
pip install -e 'backend[mongo]'
export PROMPT_WORKBENCH_STORAGE_BACKEND=mongo
export PROMPT_WORKBENCH_MONGO_URI="mongodb://127.0.0.1:27017"
prompt-workbench init  && prompt-workbench serve
```

## Docker

A multi-stage image builds the frontend with Node and serves everything from the Python process.

```bash
docker build -t prompt-workbench .
docker run --rm -p 127.0.0.1:8765:8765 \
  -e PROMPT_WORKBENCH_PROVIDER_MODE=mock \
  -v "$PWD/data:/data" prompt-workbench
```

Or with Compose (single service, loopback port, env-file secrets):

```bash
docker compose up
```

The container runs as a non-root user; SQLite data and exported releases live on the mounted
volume. For real model access, add provider key env vars and configure a connection.

## Exposing beyond localhost

Only behind an existing HTTPS reverse proxy / VPN with authentication. Set `PROMPT_WORKBENCH_HOST`
appropriately, restrict CORS origins, and never trust an unauthenticated identity header.
