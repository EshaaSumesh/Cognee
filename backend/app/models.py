"""Pydantic models shared across the Recall backend."""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _now() -> float:
    return time.time()


class Severity(str, Enum):
    sev1 = "SEV1"
    sev2 = "SEV2"
    sev3 = "SEV3"


class IncidentStatus(str, Enum):
    investigating = "investigating"
    awaiting_approval = "awaiting_approval"
    resolved = "resolved"


class Citation(BaseModel):
    """A single numbered source reference inside a brief."""
    index: int
    source: str  # e.g. "INC-001", "runbook:payments", "github:PR-482"
    snippet: str
    kind: Literal["incident", "postmortem", "runbook", "event"] = "event"


class SuggestedAction(BaseModel):
    id: str = Field(default_factory=lambda: _id("act"))
    title: str
    detail: str
    requires_approval: bool = True


class TriageBrief(BaseModel):
    """The cited triage brief produced by the investigation agent."""
    summary: str
    likely_root_cause: Optional[str] = None
    similar_incidents: list[str] = Field(default_factory=list)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    # Hero metric: how long the agent took to assemble context this session.
    time_to_context_ms: int = 0
    recalled_from_memory: bool = False


class AlertIn(BaseModel):
    """Incoming alert/webhook payload that starts an investigation."""
    title: str
    service: str
    severity: Severity = Severity.sev2
    description: str = ""
    source: str = "manual"  # sentry | pagerduty | github | manual
    raw: dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: _id("INC"))
    title: str
    service: str
    severity: Severity
    description: str
    source: str
    status: IncidentStatus = IncidentStatus.investigating
    created_at: float = Field(default_factory=_now)
    resolved_at: Optional[float] = None
    brief: Optional[TriageBrief] = None
    # Resolution feedback used to feed improve()/memify.
    resolution: Optional[str] = None
    feedback_helpful: Optional[bool] = None


class ResolveIn(BaseModel):
    resolution: str
    feedback_helpful: bool = True


class ApprovalDecision(str, Enum):
    approve = "approve"
    edit = "edit"
    override = "override"
    reject = "reject"


class ApprovalItem(BaseModel):
    id: str = Field(default_factory=lambda: _id("appr"))
    incident_id: str
    action_id: str
    action_title: str
    action_detail: str
    status: Literal["pending", "approve", "edit", "override", "reject"] = "pending"
    decided_by: Optional[str] = None
    decided_at: Optional[float] = None
    edited_detail: Optional[str] = None
    created_at: float = Field(default_factory=_now)


class ApprovalIn(BaseModel):
    decision: ApprovalDecision
    decided_by: str = "on-call"
    edited_detail: Optional[str] = None


class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: _id("audit"))
    ts: float = Field(default_factory=_now)
    actor: str
    action: str
    incident_id: Optional[str] = None
    detail: str = ""
    prev_hash: str = ""
    hash: str = ""
