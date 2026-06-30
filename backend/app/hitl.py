"""Human-in-the-loop approval queue.

Suggested actions that require approval land here. On-call can approve, edit,
override, or reject. Every decision is recorded in the signed audit log.
"""
from __future__ import annotations

import time
from typing import Optional

from .audit import audit
from .models import ApprovalIn, ApprovalItem, ApprovalDecision, SuggestedAction


class ApprovalQueue:
    def __init__(self) -> None:
        self.items: dict[str, ApprovalItem] = {}

    def enqueue(self, incident_id: str, action: SuggestedAction) -> ApprovalItem:
        item = ApprovalItem(
            incident_id=incident_id,
            action_id=action.id,
            action_title=action.title,
            action_detail=action.detail,
        )
        self.items[item.id] = item
        audit.record(
            actor="recall-agent",
            action="action.drafted",
            detail=f"{action.title}: {action.detail}",
            incident_id=incident_id,
        )
        return item

    def pending(self) -> list[ApprovalItem]:
        return [i for i in self.items.values() if i.status == "pending"]

    def all(self) -> list[ApprovalItem]:
        return sorted(self.items.values(), key=lambda i: i.created_at, reverse=True)

    def decide(self, item_id: str, decision: ApprovalIn) -> Optional[ApprovalItem]:
        item = self.items.get(item_id)
        if not item:
            return None
        item.status = decision.decision.value
        item.decided_by = decision.decided_by
        item.decided_at = time.time()
        if decision.decision == ApprovalDecision.edit and decision.edited_detail:
            item.edited_detail = decision.edited_detail

        executed = decision.decision in (
            ApprovalDecision.approve,
            ApprovalDecision.edit,
            ApprovalDecision.override,
        )
        audit.record(
            actor=decision.decided_by,
            action=f"action.{decision.decision.value}",
            detail=(item.edited_detail or item.action_detail)
            + (" [EXECUTED]" if executed else " [BLOCKED]"),
            incident_id=item.incident_id,
        )
        return item


queue = ApprovalQueue()
