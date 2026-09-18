"""Run engine: playground and evaluation comparison, checks, scoring and gates.

A *run* freezes an explicit set of candidates (prompt/chain snapshot + model snapshot) and
a dataset snapshot, then executes every (candidate × case × repeat) cell through the
provider abstraction. Execution is durable (cells persisted before/after each call),
respects global/per-connection concurrency, honours a best-effort budget ceiling and
cooperative cancellation, and separates execution outcome from quality outcome exactly as
specified in section 10.4.
"""

from __future__ import annotations

import asyncio
import statistics
from decimal import Decimal
from typing import Any

from ..domain import evaluate_check, new_uuid, render_prompt, utcnow
from ..domain.checks import CheckResult
from ..domain.rendering import TemplateError
from ..providers import ModelRequest, ModelResult, ProviderError
from ..storage import Collections
from .context import AppContext, Principal
from .datasets_service import DatasetsService
from .errors import NotFoundError, ValidationError
from .projects_service import ConnectionsService, ModelProfilesService
from .prompts_service import PromptsService

TERMINAL_RUN_STATES = {"succeeded", "failed", "cancelled", "completed_with_errors"}
MAX_GENERATION_CALLS = 5000


class RunsService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo
        self.prompts = PromptsService(ctx)
        self.profiles = ModelProfilesService(ctx)
        self.connections = ConnectionsService(ctx)
        self.datasets = DatasetsService(ctx)
        self._global_sem = asyncio.Semaphore(ctx.settings.max_global_concurrency)
        self._conn_sems: dict[str, asyncio.Semaphore] = {}

    # --- preview -----------------------------------------------------------
    async def preview(self, request: dict) -> dict:
        candidates, dataset_snapshot = await self._resolve_plan(request)
        repeats = int(request.get("repeats", 1))
        case_count = len(dataset_snapshot["frozen_cases"]) if dataset_snapshot else 1
        generation_calls = len(candidates) * max(case_count, 1) * repeats
        if generation_calls > MAX_GENERATION_CALLS:
            raise ValidationError(f"Plan needs {generation_calls} calls; limit is {MAX_GENERATION_CALLS}. Split the run.", code="plan_too_large")
        return {
            "candidate_count": len(candidates),
            "case_count": case_count,
            "repeats": repeats,
            "generation_calls": generation_calls,
            "candidates": [{"label": c["label"], "model": c["model_snapshot"]["name"]} for c in candidates],
        }

    # --- create + execute --------------------------------------------------
    async def create_run(self, request: dict, actor: Principal | None = None, *, background: bool = True) -> dict:
        candidates, dataset_snapshot = await self._resolve_plan(request)
        repeats = int(request.get("repeats", 1))
        if repeats < 1 or repeats > 5:
            raise ValidationError("repeats must be between 1 and 5", code="invalid_repeats")

        run_id = new_uuid()
        run = {
            "id": run_id,
            "project_id": request["project_id"],
            "kind": request.get("kind", "evaluation"),
            "status": "queued",
            "definition_snapshot": {
                "checks": request.get("checks", []),
                "gate": request.get("gate"),
                "baseline_label": request.get("baseline_label"),
                "repeats": repeats,
            },
            "dataset_snapshot": dataset_snapshot,
            "budget": request.get("budget", {"max_usd": None, "strict": False}),
            "candidates": [_public_candidate(c) for c in candidates],
            "parent_run_id": request.get("parent_run_id"),
            "summary": None,
            "submitted_by": actor.id if actor else None,
            "created_at": utcnow(),
            "updated_at": utcnow(),
            "cancel_requested_at": None,
        }
        await self.repo.insert_one(Collections.RUNS, run)

        cells = self._plan_cells(run, candidates, dataset_snapshot, repeats)
        for cell in cells:
            await self.repo.insert_one(Collections.RUN_CELLS, cell)

        await self.ctx.log_event(actor, "run.create", "run", run_id, run["project_id"], {"kind": run["kind"], "cells": len(cells)})

        if background:
            asyncio.create_task(self._safe_execute(run_id, candidates))
        else:
            await self._execute_run(run_id, candidates)
        return await self.get_run(run_id)

    def _plan_cells(self, run: dict, candidates: list[dict], dataset_snapshot: dict | None, repeats: int) -> list[dict]:
        cells = []
        cases = dataset_snapshot["frozen_cases"] if dataset_snapshot else [{"case_id": "adhoc", "name": "ad-hoc", "inputs": run.get("adhoc_inputs", {}), "expected": None}]
        for candidate in candidates:
            for case in cases:
                for repeat in range(repeats):
                    cells.append(
                        {
                            "id": new_uuid(),
                            "run_id": run["id"],
                            "candidate_id": candidate["id"],
                            "case_id": case["case_id"],
                            "case_name": case["name"],
                            "repeat_index": repeat,
                            "status": "queued",
                            "quality_status": "unscored",
                            "input_snapshot": case["inputs"],
                            "expected_snapshot": case.get("expected"),
                            "output": None,
                            "usage": None,
                            "cost": None,
                            "timing": None,
                            "checks": [],
                            "error": None,
                            "provenance": None,
                            "created_at": utcnow(),
                        }
                    )
        return cells

    async def _safe_execute(self, run_id: str, candidates: list[dict]) -> None:
        try:
            await self._execute_run(run_id, candidates)
        except Exception as exc:  # noqa: BLE001 - never crash the scheduler loop
            run = await self.repo.find_one(Collections.RUNS, {"id": run_id})
            if run and run["status"] not in TERMINAL_RUN_STATES:
                run["status"] = "failed"
                run["summary"] = {"error": str(exc)}
                run["updated_at"] = utcnow()
                await self.repo.replace_one(Collections.RUNS, {"id": run_id}, run)

    async def _execute_run(self, run_id: str, candidates: list[dict]) -> None:
        run = await self.repo.find_one(Collections.RUNS, {"id": run_id})
        if not run:
            return
        run["status"] = "running"
        run["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.RUNS, {"id": run_id}, run)

        checks = run["definition_snapshot"].get("checks", [])
        candidate_by_id = {c["id"]: c for c in candidates}
        budget = run.get("budget") or {}
        max_usd = Decimal(str(budget["max_usd"])) if budget.get("max_usd") not in (None, "") else None
        strict = bool(budget.get("strict"))
        spent = Decimal("0")

        cells = await self.repo.find_many(Collections.RUN_CELLS, {"run_id": run_id}, sort=[("created_at", 1)])
        tasks = []
        for cell in cells:
            candidate = candidate_by_id.get(cell["candidate_id"])
            if candidate is None:
                continue
            tasks.append(self._run_cell(run_id, cell, candidate, checks))

        # Bounded execution honouring global concurrency (per-cell also grabs conn sem).
        for coro in tasks:
            fresh_run = await self.repo.find_one(Collections.RUNS, {"id": run_id})
            if fresh_run and fresh_run.get("cancel_requested_at"):
                break
            if max_usd is not None and spent >= max_usd:
                break
            cell_cost = await coro
            if cell_cost is not None:
                spent += cell_cost

        await self._finalize_run(run_id)

    async def _run_cell(self, run_id: str, cell: dict, candidate: dict, checks: list[dict]) -> Decimal | None:
        cell["status"] = "running"
        cell["started_at"] = utcnow()
        await self.repo.replace_one(Collections.RUN_CELLS, {"id": cell["id"]}, cell)

        content = candidate["content"]
        model = candidate["model_snapshot"]
        try:
            rendered = render_prompt(content, cell["input_snapshot"])
        except TemplateError as exc:
            return await self._fail_cell(cell, "failed", {"code": exc.code, "message": str(exc), "details": exc.details})

        request = ModelRequest(
            messages=[{"role": m.role, "content": m.content} for m in rendered.messages],
            provider=model["provider"],
            model=model["model"],
            parameters=model.get("parameters", {}),
            output_mode=(content.get("output") or {}).get("mode", "text"),
            output_schema=(content.get("output") or {}).get("schema"),
            tools=content.get("tools", []),
            tool_choice=content.get("tool_choice", "auto"),
            timeout_seconds=model.get("timeout_seconds", 120),
            connection=candidate.get("connection", {}),
        )
        provider = self.ctx.providers.for_request(request)
        conn_sem = self._connection_sem(model.get("connection_alias"))
        retries = int((model.get("retry_policy") or {}).get("max_retries", 1))

        result: ModelResult | None = None
        error: dict | None = None
        async with self._global_sem, conn_sem:
            attempt = 0
            while True:
                try:
                    result = await provider.complete(request)
                    break
                except ProviderError as exc:
                    if exc.retryable and attempt < retries:
                        attempt += 1
                        await asyncio.sleep(min(2**attempt * 0.1, 2))
                        continue
                    error = {"code": exc.code, "message": str(exc), "retryable": exc.retryable}
                    break
                except Exception as exc:  # noqa: BLE001
                    error = {"code": "provider_error", "message": str(exc)}
                    break

        if error is not None or result is None:
            return await self._fail_cell(cell, "failed", error or {"code": "unknown", "message": "no result"})

        envelope = result.to_envelope()
        check_results = _run_checks(checks, envelope, cell.get("expected_snapshot"))
        quality = _quality_status(checks, check_results, execution_ok=True)

        cell["status"] = "succeeded"
        cell["quality_status"] = quality
        cell["output"] = envelope
        cell["usage"] = {
            "input_tokens": result.usage.input_tokens,
            "output_tokens": result.usage.output_tokens,
            "total_tokens": result.usage.total_tokens,
        }
        cell["cost"] = {"amount": result.cost.amount, "source": result.cost.source}
        cell["timing"] = {"duration_ms": result.duration_ms}
        cell["checks"] = check_results
        cell["provenance"] = {
            "resolved_model": result.resolved_model,
            "provider_request_id": result.provider_request_id,
            "candidate_label": candidate["label"],
            "config_digest": candidate.get("config_digest"),
        }
        cell["ended_at"] = utcnow()
        await self.repo.replace_one(Collections.RUN_CELLS, {"id": cell["id"]}, cell)
        return Decimal(result.cost.amount) if result.cost.amount else None

    async def _fail_cell(self, cell: dict, status: str, error: dict) -> None:
        cell["status"] = status
        cell["quality_status"] = "error" if status == "failed" else cell.get("quality_status", "unscored")
        cell["error"] = error
        cell["ended_at"] = utcnow()
        await self.repo.replace_one(Collections.RUN_CELLS, {"id": cell["id"]}, cell)
        return None

    def _connection_sem(self, alias: str | None) -> asyncio.Semaphore:
        key = alias or "__default__"
        if key not in self._conn_sems:
            self._conn_sems[key] = asyncio.Semaphore(self.ctx.settings.max_connection_concurrency)
        return self._conn_sems[key]

    # --- finalize + summary ------------------------------------------------
    async def _finalize_run(self, run_id: str) -> None:
        run = await self.repo.find_one(Collections.RUNS, {"id": run_id})
        if not run:
            return
        cells = await self.repo.find_many(Collections.RUN_CELLS, {"run_id": run_id})
        # Mark any never-started cells as skipped (budget/cancel).
        for cell in cells:
            if cell["status"] in ("queued", "running"):
                cell["status"] = "skipped"
                await self.repo.replace_one(Collections.RUN_CELLS, {"id": cell["id"]}, cell)
        cells = await self.repo.find_many(Collections.RUN_CELLS, {"run_id": run_id})

        summary = self._summarize(run, cells)
        has_exec_error = any(c["status"] == "failed" for c in cells)
        cancelled = bool(run.get("cancel_requested_at"))
        if cancelled:
            run["status"] = "cancelled"
        elif has_exec_error:
            run["status"] = "completed_with_errors"
        else:
            run["status"] = "succeeded"
        run["summary"] = summary
        run["updated_at"] = utcnow()
        await self.repo.replace_one(Collections.RUNS, {"id": run_id}, run)

    def _summarize(self, run: dict, cells: list[dict]) -> dict:
        checks = run["definition_snapshot"].get("checks", [])
        has_required = any(c.get("required", True) for c in checks)
        per_candidate: dict[str, dict] = {}
        for candidate in run["candidates"]:
            per_candidate[candidate["id"]] = {
                "label": candidate["label"],
                "planned": 0,
                "completed": 0,
                "passed": 0,
                "errors": 0,
                "known_cost": Decimal("0"),
                "unknown_cost_count": 0,
                "latencies": [],
            }
        for cell in cells:
            bucket = per_candidate.get(cell["candidate_id"])
            if bucket is None:
                continue
            bucket["planned"] += 1
            if cell["status"] == "succeeded":
                bucket["completed"] += 1
                if cell["quality_status"] == "pass":
                    bucket["passed"] += 1
                if cell.get("timing", {}).get("duration_ms") is not None:
                    bucket["latencies"].append(cell["timing"]["duration_ms"])
            if cell["status"] == "failed":
                bucket["errors"] += 1
            cost = (cell.get("cost") or {}).get("amount")
            if cost:
                bucket["known_cost"] += Decimal(cost)
            elif cell["status"] == "succeeded":
                bucket["unknown_cost_count"] += 1

        candidates_summary = []
        gate = run["definition_snapshot"].get("gate")
        overall_gate_pass = True
        for cid, bucket in per_candidate.items():
            planned = bucket["planned"] or 1
            pass_rate = bucket["passed"] / planned if has_required else None
            latencies = sorted(bucket["latencies"])
            candidate_summary = {
                "candidate_id": cid,
                "label": bucket["label"],
                "planned": bucket["planned"],
                "completed": bucket["completed"],
                "passed": bucket["passed"],
                "errors": bucket["errors"],
                "pass_rate": pass_rate,
                "completion_rate": bucket["completed"] / planned,
                "known_cost": f"{bucket['known_cost']:.6f}",
                "unknown_cost_count": bucket["unknown_cost_count"],
                "p50_latency_ms": _percentile(latencies, 50),
                "p95_latency_ms": _percentile(latencies, 95),
            }
            if gate:
                candidate_summary["gate_pass"] = _evaluate_gate(gate, candidate_summary, has_required, bucket["errors"])
                overall_gate_pass = overall_gate_pass and candidate_summary["gate_pass"]
            candidates_summary.append(candidate_summary)

        return {
            "candidates": candidates_summary,
            "gate": gate,
            "gate_pass": overall_gate_pass if gate else None,
            "has_required_checks": has_required,
        }

    # --- reads -------------------------------------------------------------
    async def get_run(self, run_id: str) -> dict:
        run = await self.repo.find_one(Collections.RUNS, {"id": run_id})
        if not run:
            raise NotFoundError(f"Run {run_id} not found")
        return run

    async def list_runs(self, project_id: str, *, limit: int = 50) -> list[dict]:
        return await self.repo.find_many(Collections.RUNS, {"project_id": project_id}, sort=[("created_at", -1)], limit=limit)

    async def list_cells(self, run_id: str) -> list[dict]:
        return await self.repo.find_many(Collections.RUN_CELLS, {"run_id": run_id}, sort=[("created_at", 1)])

    async def cancel(self, run_id: str) -> dict:
        run = await self.get_run(run_id)
        if run["status"] not in TERMINAL_RUN_STATES:
            run["cancel_requested_at"] = utcnow()
            await self.repo.replace_one(Collections.RUNS, {"id": run_id}, run)
        return run

    async def add_review(self, run_id: str, cell_id: str, verdict: str, note: str, actor: Principal) -> dict:
        event = {
            "id": new_uuid(),
            "run_id": run_id,
            "cell_id": cell_id,
            "actor_id": actor.id,
            "verdict": verdict,
            "note": note,
            "created_at": utcnow(),
        }
        await self.repo.insert_one(Collections.REVIEW_EVENTS, event)
        return event

    async def report(self, run_id: str) -> dict:
        run = await self.get_run(run_id)
        summary = run.get("summary") or {}
        gate = summary.get("gate")
        gate_pass = summary.get("gate_pass")
        has_error = run["status"] in ("completed_with_errors", "failed")
        if has_error:
            exit_code = 2
        elif gate is not None and gate_pass is False:
            exit_code = 1
        else:
            exit_code = 0
        return {"run_id": run_id, "status": run["status"], "summary": summary, "exit_code": exit_code}

    # --- plan resolution ---------------------------------------------------
    async def _resolve_plan(self, request: dict) -> tuple[list[dict], dict | None]:
        candidates = []
        for entry in request.get("candidates", []):
            target = entry["target"]
            if target["kind"] != "prompt":
                raise ValidationError("Only prompt candidates are supported in this run kind", code="unsupported_target")
            content, provenance = await self.prompts.resolve_content(target["id"], target.get("selector", {}))
            model_snapshot = await self.profiles.snapshot(entry["model_profile_id"])
            connection = await self._connection_for_snapshot(model_snapshot)
            from ..domain import content_digest

            config_digest = content_digest({"content_digest": provenance.get("digest"), "model": model_snapshot})
            candidates.append(
                {
                    "id": new_uuid(),
                    "label": entry["label"],
                    "target": target,
                    "content": content,
                    "content_provenance": provenance,
                    "model_snapshot": model_snapshot,
                    "connection": connection,
                    "config_digest": config_digest,
                    "baseline": entry["label"] == request.get("baseline_label"),
                }
            )
        if not candidates:
            raise ValidationError("At least one candidate is required", code="no_candidates")

        dataset_snapshot = None
        if request.get("dataset_id"):
            dataset_snapshot = await self.datasets.snapshot_cases(request["dataset_id"], request.get("case_ids"))
        return candidates, dataset_snapshot

    async def _connection_for_snapshot(self, model_snapshot: dict) -> dict:
        alias = model_snapshot.get("connection_alias")
        if not alias:
            return {}
        connection = await self.repo.find_one(Collections.CONNECTIONS, {"alias": alias})
        if not connection:
            return {}
        return {
            "provider": connection["provider"],
            "api_base": connection.get("api_base"),
            "api_version": connection.get("api_version"),
            "secret_env_name": connection.get("secret_env_name"),
        }


def _run_checks(checks: list[dict], envelope: dict, expected: Any) -> list[dict]:
    results = []
    for check in checks:
        if check.get("type") == "rubric":
            # Rubric requires a judge model; recorded as unscored when not executed here.
            results.append({"id": check.get("id"), "type": "rubric", "outcome": "unscored", "required": check.get("required", True)})
            continue
        result: CheckResult = evaluate_check(check, envelope, expected)
        results.append(
            {
                "id": check.get("id"),
                "type": check.get("type"),
                "outcome": result.outcome,
                "score": result.score,
                "required": check.get("required", True),
                "evidence": result.evidence,
            }
        )
    return results


def _quality_status(checks: list[dict], results: list[dict], *, execution_ok: bool) -> str:
    if not execution_ok:
        return "error"
    required = [r for r in results if r.get("required", True) and r["type"] != "rubric"]
    if not required:
        return "unscored"
    if any(r["outcome"] == "error" for r in required):
        return "error"
    if all(r["outcome"] == "pass" for r in required):
        return "pass"
    return "fail"


def _percentile(sorted_values: list[float], pct: float) -> float | None:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100)
    lower = int(k)
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (k - lower)


def _evaluate_gate(gate: dict, candidate_summary: dict, has_required: bool, errors: int) -> bool:
    if not has_required:
        return False  # a run with no checks cannot satisfy an automated gate
    if errors > 0:
        return False
    min_pass = gate.get("min_pass_rate")
    if min_pass is not None and (candidate_summary["pass_rate"] or 0) < min_pass:
        return False
    return True


def _public_candidate(candidate: dict) -> dict:
    return {
        "id": candidate["id"],
        "label": candidate["label"],
        "target": candidate["target"],
        "model_snapshot": candidate["model_snapshot"],
        "content_provenance": candidate["content_provenance"],
        "config_digest": candidate["config_digest"],
        "baseline": candidate["baseline"],
    }
