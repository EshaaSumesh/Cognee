"""Demo seed + replay scenario.

Proves the hero claim: with memory, incident #2 resolves with full cited context
that incident #1 had to discover from scratch.

Flow:
  1. seed(): load runbooks (but NOT INC-001) so the first incident is a cold start.
  2. replay():
     a. Incident A (payments 5xx) — cold: little/no prior incident memory.
        After "resolving" it, we remember() the outcome + improve()/memify.
     b. Incident B (payments 5xx again, slightly different wording) — warm:
        recall() now surfaces INC-A's root cause + fix with citations, faster.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .agent import agent
from .memory import memory
from .models import AlertIn, Severity

_SEED_PATHS = [
    Path(os.getenv("SEED_DIR", "/app/seed_data")) / "seed.json",
    Path(__file__).resolve().parent.parent / "data" / "seed.json",
]


def _load_seed() -> dict[str, Any]:
    for p in _SEED_PATHS:
        if p.exists():
            return json.loads(p.read_text())
    raise FileNotFoundError("seed.json not found in expected locations")


async def seed_runbooks_only() -> dict[str, Any]:
    """Cold-start seed: only runbooks + raw events, no prior incident memory."""
    data = _load_seed()
    count = 0
    for rb in data.get("runbooks", []):
        await memory.remember(rb["text"], source=rb["source"], kind=rb["kind"])
        count += 1
    for ev in data.get("events", []):
        await memory.remember(ev["text"], source=ev["source"], kind=ev["kind"])
        count += 1
    return {"seeded": count, "backend": memory.backend}


async def replay() -> dict[str, Any]:
    """Run two similar incidents and surface the compounding metric."""
    # Reset prior demo-incident memory so the cold start is honestly cold.
    # (Runbooks/events from seed remain; only past incident memory is pruned.)
    await memory.forget(source="INC-A")
    await memory.forget(source_prefix="INC")

    # --- Incident A: cold start ---
    alert_a = AlertIn(
        title="payments-api 5xx spike on /charge",
        service="payments-api",
        severity=Severity.sev2,
        description="Elevated 500s and p99 latency after the afternoon deploy.",
        source="sentry",
    )
    brief_a = await agent.investigate(alert_a)

    # On-call resolves it; we remember the outcome and let memory compound.
    resolution_a = (
        "INC-A resolved: root cause was payments-db connection pool exhaustion from "
        "PR-482 raising concurrency. Fix: scaled pgbouncer pool 20 -> 60 and rolled "
        "payments-api. Time to resolve: 44m."
    )
    await memory.remember(
        f"INC-A (SEV2) payments-api 5xx. {resolution_a}",
        source="INC-A",
        kind="incident",
    )
    await memory.improve(
        feedback=resolution_a,
        helpful_sources=["runbook:payments-db", "github:PR-482", "sentry:PAY-9921"],
    )

    # --- Incident B: warm, same class of problem, different wording ---
    alert_b = AlertIn(
        title="charge endpoint returning 500s, db connections maxed",
        service="payments-api",
        severity=Severity.sev2,
        description="Customers report failed payments; connection slots reserved errors.",
        source="pagerduty",
    )
    brief_b = await agent.investigate(alert_b)

    # --- Incident C: a DIFFERENT service, proving memory generalizes ---
    alert_c = AlertIn(
        title="checkout cart reads timing out, redis CPU pegged",
        service="checkout",
        severity=Severity.sev3,
        description="Cart reads slow during flash sale; redis at 100% CPU.",
        source="datadog",
    )
    brief_c = await agent.investigate(alert_c)

    improvement = None
    if brief_a.time_to_context_ms > 0:
        improvement = round(
            100 * (brief_a.time_to_context_ms - brief_b.time_to_context_ms)
            / max(brief_a.time_to_context_ms, 1),
            1,
        )

    return {
        "backend": memory.backend,
        "incident_a": {
            "alert": alert_a.model_dump(),
            "brief": brief_a.model_dump(),
        },
        "incident_b": {
            "alert": alert_b.model_dump(),
            "brief": brief_b.model_dump(),
        },
        "incident_c": {
            "alert": alert_c.model_dump(),
            "brief": brief_c.model_dump(),
        },
        "compounding": {
            "cold_recalled_from_memory": brief_a.recalled_from_memory,
            "warm_recalled_from_memory": brief_b.recalled_from_memory,
            "cold_similar_incidents": brief_a.similar_incidents,
            "warm_similar_incidents": brief_b.similar_incidents,
            "cold_time_to_context_ms": brief_a.time_to_context_ms,
            "warm_time_to_context_ms": brief_b.time_to_context_ms,
            "time_to_context_improvement_pct": improvement,
            "headline": (
                "Incident B recalled the root cause and fix from Incident A with "
                "citations — memory compounded."
                if brief_b.similar_incidents
                else "Run seed first, then replay."
            ),
        },
    }
