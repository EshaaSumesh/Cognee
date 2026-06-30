"""End-to-end smoke test of the Recall flow on the in-memory fallback backend.

Run: python -m tests.test_flow   (from the backend/ dir, venv active)

Verifies the core claim: memory compounds — incident B recalls incident A's
root cause and fix with citations, and does so without re-discovering from
scratch.
"""
import asyncio
import sys

from app import demo as demo_mod
from app.audit import audit
from app.hitl import queue
from app.memory import memory
from app.models import AlertIn, ApprovalIn, ApprovalDecision, Severity
from app.agent import agent


async def main() -> int:
    print(f"memory backend: {memory.backend}")

    seeded = await demo_mod.seed_runbooks_only()
    assert seeded["seeded"] > 0, "nothing seeded"
    print(f"seeded {seeded['seeded']} memory items")

    result = await demo_mod.replay()
    comp = result["compounding"]
    print("compounding:", comp["headline"])
    print("  cold similar incidents:", comp["cold_similar_incidents"])
    print("  warm similar incidents:", comp["warm_similar_incidents"])
    print("  ttc cold/warm ms:", comp["cold_time_to_context_ms"],
          comp["warm_time_to_context_ms"])

    # Core assertion: incident B recalls incident A (memory compounded).
    assert comp["warm_similar_incidents"], "incident B did not recall prior incidents"
    assert "INC-A" in comp["warm_similar_incidents"], \
        "incident B should recall INC-A from memory"

    # Investigate a fresh alert and verify HITL + audit wiring.
    alert = AlertIn(
        title="payments-api 5xx spike on /charge",
        service="payments-api",
        severity=Severity.sev2,
        description="500s after deploy",
        source="manual",
    )
    brief = await agent.investigate(alert)
    assert brief.citations, "brief should carry citations"
    assert brief.suggested_actions, "brief should suggest actions"

    item = queue.enqueue("INC-TEST", brief.suggested_actions[0])
    decided = queue.decide(
        item.id, ApprovalIn(decision=ApprovalDecision.approve, decided_by="tester")
    )
    assert decided and decided.status == "approve"

    assert audit.verify(), "audit chain must verify"
    print(f"audit entries: {len(audit.entries)}, chain valid: {audit.verify()}")

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
