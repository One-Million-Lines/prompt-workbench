"""Prompt-version analytics aggregated from run cells and captures."""

from __future__ import annotations

from decimal import Decimal

from ..storage import Collections
from .context import AppContext


class AnalyticsService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.repo = ctx.repo

    async def prompt_analytics(self, prompt_id: str) -> dict:
        """Group execution metrics by exact prompt revision and model."""
        runs = await self.repo.find_many(Collections.RUNS, {}, sort=[("created_at", -1)])
        relevant_candidates: dict[str, dict] = {}
        for run in runs:
            for candidate in run.get("candidates", []):
                target = candidate.get("target", {})
                if target.get("kind") == "prompt" and target.get("id") == prompt_id:
                    relevant_candidates[candidate["id"]] = {"run_id": run["id"], "candidate": candidate}

        groups: dict[tuple, dict] = {}
        for cand_id, info in relevant_candidates.items():
            cells = await self.repo.find_many(Collections.RUN_CELLS, {"run_id": info["run_id"], "candidate_id": cand_id})
            provenance = info["candidate"].get("content_provenance", {})
            model = info["candidate"].get("model_snapshot", {})
            key = (provenance.get("version", "draft"), model.get("name", "unknown"))
            group = groups.setdefault(
                key,
                {
                    "revision": provenance.get("version", "draft"),
                    "model": model.get("name", "unknown"),
                    "calls": 0,
                    "success": 0,
                    "errors": 0,
                    "passed": 0,
                    "scored": 0,
                    "known_cost": Decimal("0"),
                    "unknown_cost_count": 0,
                    "latencies": [],
                },
            )
            for cell in cells:
                group["calls"] += 1
                if cell["status"] == "succeeded":
                    group["success"] += 1
                    if cell["quality_status"] in ("pass", "fail"):
                        group["scored"] += 1
                    if cell["quality_status"] == "pass":
                        group["passed"] += 1
                    latency = (cell.get("timing") or {}).get("duration_ms")
                    if latency is not None:
                        group["latencies"].append(latency)
                    cost = (cell.get("cost") or {}).get("amount")
                    if cost:
                        group["known_cost"] += Decimal(cost)
                    else:
                        group["unknown_cost_count"] += 1
                elif cell["status"] == "failed":
                    group["errors"] += 1

        result = []
        for group in groups.values():
            latencies = sorted(group["latencies"])
            result.append(
                {
                    "revision": group["revision"],
                    "model": group["model"],
                    "calls": group["calls"],
                    "success": group["success"],
                    "errors": group["errors"],
                    "pass_rate": (group["passed"] / group["scored"]) if group["scored"] else None,
                    "known_cost": f"{group['known_cost']:.6f}",
                    "unknown_cost_count": group["unknown_cost_count"],
                    "p50_latency_ms": latencies[len(latencies) // 2] if latencies else None,
                }
            )
        return {"prompt_id": prompt_id, "groups": result}
