"""Recall backend API.

FastAPI app wiring the Cognee memory layer, investigation agent, HITL approval
queue, and signed audit log into a small REST surface the Next.js UI consumes.
"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import demo as demo_mod
from .agent import agent
from .audit import audit
from .hitl import queue
from .memory import memory
from .models import (
    AlertIn,
    ApprovalIn,
    Incident,
    IncidentStatus,
    ResolveIn,
)

app = FastAPI(title="Recall — Cognee Incident Memory", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store of incidents (metadata only; the knowledge lives in Cognee).
INCIDENTS: dict[str, Incident] = {}


@app.on_event("startup")
async def _startup() -> None:
    await memory.setup()
    audit.record(actor="system", action="startup", detail=f"backend={memory.backend}")


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "memory_backend": memory.backend,
        "audit_chain_valid": audit.verify(),
        "incidents": len(INCIDENTS),
    }


@app.post("/api/incidents", response_model=Incident)
async def create_incident(alert: AlertIn) -> Incident:
    """Ingest an alert, run the investigation, and queue HITL actions."""
    brief = await agent.investigate(alert)
    incident = Incident(
        title=alert.title,
        service=alert.service,
        severity=alert.severity,
        description=alert.description,
        source=alert.source,
        status=IncidentStatus.awaiting_approval,
        brief=brief,
    )
    INCIDENTS[incident.id] = incident

    audit.record(
        actor="recall-agent",
        action="incident.investigated",
        detail=f"{incident.title} — recalled={brief.recalled_from_memory}, "
        f"ttc={brief.time_to_context_ms}ms",
        incident_id=incident.id,
    )
    for action in brief.suggested_actions:
        if action.requires_approval:
            queue.enqueue(incident.id, action)

    # Remember the raw alert so future investigations can recall it.
    await memory.remember(
        f"{incident.id} ({alert.severity.value}) {alert.service}: {alert.title}. "
        f"{alert.description}",
        source=incident.id,
        kind="incident",
    )
    return incident


@app.get("/api/incidents", response_model=list[Incident])
async def list_incidents() -> list[Incident]:
    return sorted(INCIDENTS.values(), key=lambda i: i.created_at, reverse=True)


@app.get("/api/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: str) -> Incident:
    incident = INCIDENTS.get(incident_id)
    if not incident:
        raise HTTPException(404, "incident not found")
    return incident


@app.post("/api/incidents/{incident_id}/resolve", response_model=Incident)
async def resolve_incident(incident_id: str, body: ResolveIn) -> Incident:
    """Resolve an incident; feed outcome to improve()/memify (compounding)."""
    incident = INCIDENTS.get(incident_id)
    if not incident:
        raise HTTPException(404, "incident not found")
    incident.status = IncidentStatus.resolved
    incident.resolved_at = time.time()
    incident.resolution = body.resolution
    incident.feedback_helpful = body.feedback_helpful

    # Remember the resolution and let memory compound.
    await memory.remember(
        f"{incident.id} resolved. {body.resolution}",
        source=incident.id,
        kind="postmortem",
    )
    helpful = (
        [c.source for c in (incident.brief.citations if incident.brief else [])]
        if body.feedback_helpful
        else None
    )
    await memory.improve(feedback=body.resolution, helpful_sources=helpful)

    audit.record(
        actor="on-call",
        action="incident.resolved",
        detail=f"helpful={body.feedback_helpful}: {body.resolution}",
        incident_id=incident.id,
    )
    return incident


# ---- HITL approval queue -------------------------------------------------
@app.get("/api/approvals")
async def list_approvals(only_pending: bool = False):
    return queue.pending() if only_pending else queue.all()


@app.post("/api/approvals/{item_id}")
async def decide_approval(item_id: str, body: ApprovalIn):
    item = queue.decide(item_id, body)
    if not item:
        raise HTTPException(404, "approval item not found")
    return item


# ---- Audit log -----------------------------------------------------------
@app.get("/api/audit")
async def get_audit(limit: int = 200):
    return {"valid": audit.verify(), "entries": audit.list(limit)}


# ---- Memory ops (forget) -------------------------------------------------
@app.post("/api/memory/forget")
async def forget(dataset: Optional[str] = None, source: Optional[str] = None):
    await memory.forget(dataset=dataset, source=source)
    audit.record(
        actor="on-call",
        action="memory.forget",
        detail=f"dataset={dataset} source={source}",
    )
    return {"ok": True}


# ---- Demo ----------------------------------------------------------------
@app.post("/api/demo/seed")
async def demo_seed():
    return await demo_mod.seed_runbooks_only()


@app.post("/api/demo/replay")
async def demo_replay():
    return await demo_mod.replay()
