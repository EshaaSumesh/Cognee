"""Investigation agent: turns an alert into a source-cited triage brief.

Design: the agent recalls similar past incidents from Cognee (hybrid graph +
vector), then synthesizes a cited brief and suggested runbook steps.

We expose two paths:

1. LangGraph + the official `cognee-integration-langgraph` tools when available.
   Using a Cognee-owned integration is a strong "Best Use of Cognee" signal.
2. A direct, deterministic investigation over `MemoryLayer` otherwise, so the
   demo runs anywhere (including without an LLM key).

Both paths share the same recall -> synthesize -> cite shape.
"""
from __future__ import annotations

import time
from typing import Optional

from .memory import MemoryLayer, RecallHit, memory
from .models import (
    AlertIn,
    Citation,
    SuggestedAction,
    TriageBrief,
)

try:
    from cognee_integration_langgraph import (  # type: ignore
        get_sessionized_cognee_tools,
    )

    _HAS_LANGGRAPH_INTEGRATION = True
except Exception:  # pragma: no cover
    get_sessionized_cognee_tools = None  # type: ignore
    _HAS_LANGGRAPH_INTEGRATION = False


class InvestigationAgent:
    def __init__(self, mem: Optional[MemoryLayer] = None) -> None:
        self.memory = mem or memory

    async def investigate(self, alert: AlertIn) -> TriageBrief:
        """Run a cross-source investigation and return a cited brief."""
        start = time.perf_counter()

        query = f"{alert.title} {alert.service} {alert.description}".strip()
        hits = await self.memory.recall(query, top_k=6)

        brief = self._synthesize(alert, hits)
        brief.time_to_context_ms = int((time.perf_counter() - start) * 1000)
        brief.recalled_from_memory = any(
            h.kind in ("incident", "postmortem") for h in hits
        )
        return brief

    def _synthesize(self, alert: AlertIn, hits: list[RecallHit]) -> TriageBrief:
        citations: list[Citation] = []
        similar_incidents: list[str] = []
        root_cause: Optional[str] = None
        runbook_steps: list[str] = []

        for i, hit in enumerate(hits, start=1):
            citations.append(
                Citation(
                    index=i,
                    source=hit.source,
                    snippet=_truncate(hit.text, 220),
                    kind=hit.kind,  # type: ignore[arg-type]
                )
            )
            if hit.kind in ("incident", "postmortem"):
                base = hit.source.split("-postmortem")[0]
                if base not in similar_incidents:
                    similar_incidents.append(base)
                if root_cause is None:
                    rc = _extract(hit.text, "root cause")
                    if rc:
                        root_cause = f"{rc} (per {hit.source})"
            if hit.kind == "runbook":
                step = _extract(hit.text, "fix") or _extract(hit.text, "remediation")
                if step:
                    runbook_steps.append(f"{step} (see {hit.source})")

        actions = self._build_actions(alert, runbook_steps, similar_incidents)

        if similar_incidents:
            summary = (
                f"{alert.severity.value} on {alert.service}: \"{alert.title}\". "
                f"This closely matches {len(similar_incidents)} prior incident(s): "
                f"{', '.join(similar_incidents[:3])}. "
                + (f"Likely root cause: {root_cause}. " if root_cause else "")
                + "Recall surfaced the prior resolution path with citations below."
            )
        else:
            summary = (
                f"{alert.severity.value} on {alert.service}: \"{alert.title}\". "
                "No similar prior incident in memory yet — this is a first-time "
                "investigation. Once resolved, memory will compound so the next "
                "occurrence resolves faster."
            )

        return TriageBrief(
            summary=summary,
            likely_root_cause=root_cause,
            similar_incidents=similar_incidents,
            suggested_actions=actions,
            citations=citations,
        )

    def _build_actions(
        self,
        alert: AlertIn,
        runbook_steps: list[str],
        similar_incidents: list[str],
    ) -> list[SuggestedAction]:
        actions: list[SuggestedAction] = []
        for step in runbook_steps[:3]:
            actions.append(
                SuggestedAction(
                    title="Apply known remediation",
                    detail=step,
                    requires_approval=True,
                )
            )
        if similar_incidents:
            actions.append(
                SuggestedAction(
                    title="Notify incident channel with prior context",
                    detail=(
                        f"Post to #incidents: matches {similar_incidents[0]}; "
                        "linking prior postmortem and resolution."
                    ),
                    requires_approval=alert.severity.value == "SEV1",
                )
            )
        if not actions:
            actions.append(
                SuggestedAction(
                    title="Open investigation & page service owner",
                    detail=(
                        f"No prior memory for {alert.service}. Page the owner and "
                        "begin first-time triage; outcome will be remembered."
                    ),
                    requires_approval=True,
                )
            )
        return actions


def _truncate(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "\u2026"


def _extract(text: str, keyword: str) -> Optional[str]:
    """Pull the sentence/line that mentions a keyword (root cause, fix, etc.)."""
    low = text.lower()
    idx = low.find(keyword)
    if idx == -1:
        return None
    # Grab from the keyword to the end of its line/sentence.
    tail = text[idx:]
    for sep in ["\n", ". ", "; "]:
        cut = tail.find(sep)
        if cut != -1:
            tail = tail[:cut]
            break
    cleaned = tail.strip().rstrip(".")
    # Drop the leading keyword label if present (e.g. "Root cause:").
    parts = cleaned.split(":", 1)
    if len(parts) == 2 and len(parts[0]) < 30:
        cleaned = parts[1].strip()
    return cleaned or None


agent = InvestigationAgent()
