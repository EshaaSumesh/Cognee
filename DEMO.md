# Recall — Demo Walkthrough

This is the 60-second story that proves the hero claim: **Cognee memory compounds — incident #2 resolves with context that incident #1 had to discover from scratch.**

## One-time setup

```bash
cp .env.example .env            # set LLM_API_KEY
docker compose up --build       # postgres (pgvector) + backend on :8000
cd frontend && npm install && npm run dev   # UI on :3000
```

> No LLM key handy? The backend transparently falls back to an in-memory store
> (flagged as `memory: in-memory-fallback` in the UI) so the whole demo still
> runs and the compounding behaviour is identical.

## 60-second script

1. **Open `http://localhost:3000`.** Read the one-line pitch: on-call wakes up
   with no memory; Recall fixes that with self-hosted Cognee.

2. **Click "Run the compounding demo."** This calls two endpoints:
   - `POST /api/demo/seed` — `remember()` seeds runbooks + raw events (no prior
     incidents). Cold start.
   - `POST /api/demo/replay` — runs three incidents:
     - **Incident #1 (payments 5xx, cold):** no similar incident in memory →
       first-time investigation. We `remember()` the resolution + `improve()`.
     - **Incident #2 (payments 5xx, different wording, warm):** `recall()` now
       surfaces Incident #1's root cause and fix **with citations** — the
       "Memory compounding" panel lights up.
     - **Incident #3 (checkout/redis, different service):** shows the memory
       generalizes across services, recalling the right runbook.

3. **Click "Trigger an alert."** A live SEV2 lands in the feed. Open it:
   - The **case brief** names the likely root cause *(per INC-A)*.
   - The **memory graph** shows the alert hub linked to each cited memory node.
   - **Citations [1]–[4]** trace every claim to a source (runbook, Sentry,
     GitHub PR, prior incident).

4. **Approve an action in the HITL queue.** It executes and disappears.

5. **Open the "Audit log" tab.** Every step — `incident.investigated`,
   `action.drafted`, `action.approve [EXECUTED]` — is hash-chained and
   HMAC-signed. The header reads **"Chain integrity: verified."**

6. **Click "Mark resolved → improve()"** on the open incident to feed the
   outcome back into Cognee. The next matching alert resolves even faster.

## What to point the judges at (Best Use of Cognee)

- `remember()` / `recall()` / `improve()` / `forget()` are each used distinctly
  in `backend/app/memory.py`.
- `improve()` (memify) is the **hero**: it's what makes incident #2 faster.
- Hybrid graph + vector recall powers the citations and the memory graph.
- 100% self-hosted, open-source Cognee — `memory: cognee` in the badge when run
  with the real engine via `docker compose`.

## Recording the clip

Record steps 1–6 above in one take (~60s). Keep the "Memory compounding" panel
and the "memory recalled" badge in frame — those two visuals are the whole pitch.
