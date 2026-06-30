# Limitations, Placeholders & Roadmap

This document is an honest accounting of what Recall does **not** yet do, what is
**simulated/placeholder** for the demo, and what would need to be built for
production. It is intentionally candid — judges and contributors should know
exactly where the real engineering is versus where the seams are.

> TL;DR: the **Cognee memory lifecycle (remember → recall → improve → forget),
> the cited-brief logic, the HITL queue, and the signed audit log are real**.
> The **data connectors, the LLM-narrated synthesis, persistence of app state,
> auth, and action execution are placeholders/simulated** for the hackathon demo.

---

## 1. Placeholders & simulated pieces (demo scaffolding)

### 1.1 Data sources are seeded fixtures, not live connectors
- Incidents, postmortems, runbooks, and "events" (Sentry/GitHub/Slack) come from
  [`backend/data/seed.json`](backend/data/seed.json) and the hardcoded scenarios in
  [`backend/app/demo.py`](backend/app/demo.py).
- **There are no real integrations** with Sentry, PagerDuty, GitHub, Slack,
  Datadog, etc. The `source` field on an alert (e.g. `"sentry"`, `"pagerduty"`)
  is just a label; nothing is fetched from those systems.
- **Yet to build:** real webhook receivers and API pollers for each source, with
  auth, pagination, and rate-limit handling.

### 1.2 The investigation agent is rule-based, not LLM-reasoned
- [`backend/app/agent.py`](backend/app/agent.py) builds the brief with deterministic
  string extraction (`_extract()` pulls the sentence after keywords like
  "root cause" / "fix"). It does **not** call an LLM to reason over the recalled
  context.
- The `cognee-integration-langgraph` import exists and is detected
  (`_HAS_LANGGRAPH_INTEGRATION`), but the **LangGraph agent graph is not wired
  into the request path** — `investigate()` calls `memory.recall()` directly.
- **Yet to build:** an actual LangGraph agent that uses
  `get_sessionized_cognee_tools(user_id)` and an LLM to synthesize the brief,
  pick actions, and write the narrative.

### 1.3 Cognee runs, but the demo defaults to the in-memory fallback
- [`backend/app/memory.py`](backend/app/memory.py) uses **real Cognee** when the
  package + `LLM_API_KEY` are available (via `docker compose`). Without them it
  **transparently falls back to an in-memory keyword store**, clearly flagged as
  `memory: in-memory-fallback` in the UI badge.
- The fallback `recall()` is **keyword-overlap matching**, not hybrid
  graph-vector retrieval. It is good enough to demonstrate the compounding
  behaviour but is **not** representative of Cognee's real retrieval quality.
- `forget()` on real Cognee is **best-effort** — it tries `prune.prune_data` and
  falls back to `prune_system` because the prune API surface varies across Cognee
  versions (see comment in `memory.py`). Source-level forget is only exact in the
  fallback store.

### 1.4 Suggested actions are drafted but never executed
- Approving an action in the HITL queue marks it `[EXECUTED]` in the audit log,
  but **nothing actually happens** — no Slack message is posted, no pod is scaled,
  no ticket is opened.
- **Yet to build:** real action executors (Slack/PagerDuty/GitHub/kubectl) behind
  the approval gate.

### 1.5 The "memory compounding" chart uses a synthetic visual scale
- [`frontend/components/CompoundingChart.tsx`](frontend/components/CompoundingChart.tsx)
  notes this explicitly: at sub-millisecond fallback timings the wall-clock
  `time_to_context_ms` is ~0, so the bar **heights are derived from whether memory
  was recalled**, not from measured latency. The qualitative win (cold = no recall,
  warm = recalled prior incident with citations) is real; the bar *heights* are
  illustrative.

---

## 2. Not yet developed (missing for production)

### 2.1 Persistence of application state
- Incidents (`INCIDENTS` dict in [`backend/app/main.py`](backend/app/main.py)), the
  approval queue, and the audit log are **in-process memory only**. They are lost
  on backend restart. Only the Cognee knowledge graph persists (in Postgres).
- **Yet to build:** persist incidents/approvals/audit to Postgres (or reconstruct
  them from Cognee + a relational table).

### 2.2 Authentication, authorization & multi-tenancy
- No login, no API auth, no per-team isolation. `CORS` is wide open
  (`allow_origins=["*"]`). The audit log records a hardcoded `decided_by:
  "on-call"` from the UI rather than a real authenticated user.
- Cognee supports tenant/user isolation; **Recall does not use it yet**.

### 2.3 Configurable HITL policy
- Approval thresholds are hardcoded heuristics in `agent._build_actions()`
  (e.g. SEV1 requires approval for the notify action). There is **no rules engine
  / no UI to configure gates** (unlike the Manthan-style policy sliders the README
  aspires to).

### 2.4 Real LLM provider wiring beyond OpenAI defaults
- `.env.example` lists OpenAI defaults. Other providers are documented by Cognee
  but **not tested here**.

### 2.5 Tests are a single smoke test
- [`backend/tests/test_flow.py`](backend/tests/test_flow.py) covers the happy-path
  flow on the fallback backend only. **No unit tests** for the agent's extraction
  logic, the audit chain edge cases, or the real-Cognee path. **No frontend tests.**

### 2.6 Neo4j graph visualization is wired but unused by the UI
- `docker-compose.yml` has a `neo4j` profile and `.env.example` has the config,
  but the **frontend "memory graph" is a self-drawn SVG hub-and-spoke**
  ([`MemoryGraph.tsx`](frontend/components/MemoryGraph.tsx)) built from citations —
  it does **not** render Cognee's actual graph from Neo4j.

### 2.7 Observability & ops
- No structured logging, metrics, tracing, healthchecks beyond `/api/health`, or
  deployment manifests beyond local `docker compose`.

---

## 3. Known correctness caveats

- **Demo "cold start" purity:** `demo.replay()` calls `forget(source="INC-A")` and
  `forget(source_prefix="INC")` to reset incident memory so Incident #1 is honestly
  "cold". If you trigger live alerts and *then* run the demo on the real Cognee
  backend (where prefix-forget is best-effort), Incident #1 may already show
  "recalled". The dedicated replay on a fresh backend always shows the clean
  contrast.
- **Citation snippets are truncated** to 220 chars (`_truncate`) and de-duplication
  of incident vs postmortem sources is a simple `split("-postmortem")` heuristic.

---

## 4. What IS fully real (so the seams are clear)

- The Cognee lifecycle wrapper and its mapping to `add`/`cognify`/`search`/`prune`
  ([`memory.py`](backend/app/memory.py)).
- The compounding loop: resolutions are `remember()`-ed and fed to `improve()`
  ([`main.py`](backend/app/main.py) `resolve_incident`).
- Source-cited briefs with traceable citations ([`agent.py`](backend/app/agent.py)).
- The HITL approval queue ([`hitl.py`](backend/app/hitl.py)).
- The hash-chained, HMAC-signed, verifiable audit log
  ([`audit.py`](backend/app/audit.py)) with real integrity verification.
- The full Next.js UI and the `docker compose` self-hosted, open-source setup.

---

## 5. Priority roadmap (if continued)

1. Wire the LangGraph + LLM agent into `investigate()` (replace rule-based synthesis).
2. Persist incidents/approvals/audit to Postgres.
3. One real connector end-to-end (GitHub or Sentry webhook → `remember()`).
4. Auth + per-team tenancy using Cognee's isolation.
5. Real action executors behind the HITL gate.
6. Render Cognee's actual graph (Neo4j/Kuzu) in the UI.
7. Expand the test suite (agent extraction, audit edge cases, real-Cognee path).
