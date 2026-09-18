# syntax=docker/dockerfile:1

# ---- Stage 1: build the React frontend ----
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PROMPT_WORKBENCH_DATA_DIR=/data \
    PROMPT_WORKBENCH_HOST=0.0.0.0 \
    PROMPT_WORKBENCH_PORT=8765

# Non-root user
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY backend/ ./backend/
COPY runtime/ ./runtime/
RUN pip install ./backend ./runtime

# Bundle the compiled frontend so the app serves it from one origin.
COPY --from=frontend /frontend/dist/ /app/backend/src/prompt_workbench/static/

RUN mkdir -p /data && chown -R appuser:appuser /data /app
USER appuser
VOLUME ["/data"]
EXPOSE 8765

# Default: serve with the mock provider. Override PROMPT_WORKBENCH_PROVIDER_MODE and add
# provider key env vars for real model access.
CMD ["prompt-workbench", "serve", "--data-dir", "/data", "--host", "0.0.0.0", "--port", "8765"]
