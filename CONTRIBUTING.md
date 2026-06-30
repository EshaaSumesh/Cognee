# Contributing & the Cognee Open-Source PR Side-Track

Recall is built entirely on **open-source, self-hosted Cognee**. Beyond the main
"Best Use of Open Source" build prize, the hackathon runs a separate
**$100-per-PR track (top 20 submissions)** for contributions to the Cognee repos.

## How to land a qualifying PR

1. Find an issue in [`topoteretes/cognee`](https://github.com/topoteretes/cognee/issues)
   (look for `good-first-issue` / `good-first-pr`) or
   [`topoteretes/cognee-integrations`](https://github.com/topoteretes/cognee-integrations).
2. **Comment on the issue** saying you'd like to work on it and tag the maintainers.
3. **Wait for assignment** before starting.
4. Submit the PR. Do not spam maintainers for review.
5. **Max 5 PRs per person.** More than 5 = ban. No AI-generated PR spam.

## Natural PR ideas that fall out of this project

This repo is structured to be a reusable Cognee example, which makes for clean,
non-spam contributions:

- An **incident-memory example** under `cognee/examples/` mirroring
  `backend/app/memory.py` (remember → recall → improve → forget over runbooks
  and incidents).
- A small **LangGraph integration example** showing
  `get_sessionized_cognee_tools(user_id)` driving an investigation agent
  (`backend/app/agent.py`).
- Docs/typo/quickstart fixes you hit while wiring up self-hosted Cognee.

Keep each PR small, focused, and tied to an assigned issue.

## Local development

- Backend: `cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`
- Run tests: `SEED_DIR=$(pwd)/data python -m tests.test_flow`
- Frontend: `cd frontend && npm install && npm run dev`
