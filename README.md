# LifeSync

A working lifecycle review prototype inside a simulated ClientWorks workspace, built from the supplied RAD and development plan for the 2026 LPL Financial University Hackathon.

**Development stages 1–4 are implemented.** Findings are labeled deterministic fixtures. ClientWorks, Wealthbox, contact synchronization, signatures, documents, institution requests, and receipts use synthetic data and simulated actions. Live Bedrock analysis belongs to stage 5 and is not called by this build.

## What works

| Stage | Delivered behavior |
| --- | --- |
| 1 · ClientWorks | Client Management shell, Home notifications and recent requests, assigned-client search and Quick Views, profiles, masked account tables/details, and client-specific LifeSync navigation. |
| 2 · Wealthbox | Separate CRM shell, contacts, dated notes, owned tasks, explicit mapping controls, Unlinked state, and the read-only LPL Financial account tab and launcher. |
| 3 · Adapters | Two-way address/email synchronization, expected-version checks, deduplication keys, one propagation per origin event, visible conflicts, and independent account request tracking. |
| 4 · LifeSync | Event confirmation, source evidence and coverage, fixture findings, client instructions, draft comparisons, exact-version approval, simulated document/signature gates, reconciliation, receipts, resume, and audit history. |

Advisor Handover and unrelated ClientWorks tabs are outside this build. Unavailable controls are explicitly disabled.

## Run locally

Use Node.js 22.12+ or 24 and Python 3.11+. Checked with Node 24 and Python 3.14. No AWS credentials, bucket, or table are needed for these stages.

From the `LifeSync` repository, start the backend in one PowerShell terminal:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open **http://127.0.0.1:5173**. API documentation: **http://127.0.0.1:8000/docs**. Vite proxies `/api` to port 8000. On macOS/Linux use `.venv/bin/python` and `npm`.

Cases, drafts, signatures, tasks, requests, sync conflicts, and audit events persist in `backend/data/state.sqlite3`. Refreshing or restarting resumes saved work. SQLite is the local implementation of the proposed persistence boundary; AWS storage adapters remain future work.

The backend uses a **fixed, server-owned simulated advisor**, Alex Morgan (`advisor-01`). Request headers cannot select another identity. Every client/account/source/case operation checks current assignment and effective access dates. This is local demo identity, not production authentication; bind to loopback.

## Demo

1. Open **Clients → Maya Bennett (C001) → Financial accounts**. Inspect A101's old address and A102's former-spouse beneficiary.
2. Open the linked **Wealthbox** contact. Inspect both dated address notes, owned tasks, and **LPL Financial** account projection. Avery Park (W004) demonstrates **Unlinked**.
3. Open **LifeSync**, confirm Divorce with Maya as the affected client, select evidence, and leave the event date unknown if not supplied. Click **Load fixture findings**.
4. Open both conflicting note sources. Mark address evidence reviewed and record the client-confirmed address `92 Harbor Street, Portland, OR 97209`, evidence `DOC:D001`, a reason, and client confirmation. Prepare the draft.
5. For the beneficiary finding, create a follow-up owned by Taylor Chen. Leave the date blank to demonstrate **Needs date**. No replacement is inferred.
6. In **Drafts & approvals**, compare current/proposed values. Approve the exact version and mark the simulated document received. Submission stays blocked until Maya's simulated signature is supplied. An edit clears prior approval, documents, and signatures.
7. Submit once. **Retry same submission** returns the same logical request. In **Requests**, simulate Processing, then Completed. Inspect or download the simulated receipt.
8. Refresh. The address finding is Completed; the beneficiary remains Needs information and the case remains Open.
9. Separately approve a supported contact update in Wealthbox's **LPL Financial** tab. **Demonstrate version conflict** deliberately submits a mismatched version. Review the fresh versions and synchronize the intended value to resolve it. Switch origin to Wealthbox for the reverse direction.

Elena Ruiz (C003) provides a beneficiary-death review. The affected beneficiary is Luis Ruiz; Elena is living. Unknown authority/process rules require manual review. Jordan Lee (C002) is seeded for marriage and denied to the active advisor.

## Verify

From the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend build and browser checks:

```powershell
cd frontend
npm.cmd run build
npm.cmd run test:e2e
```

Browser tests use installed Microsoft Edge. Set `PLAYWRIGHT_CHANNEL=chrome` for installed Chrome, or install Playwright Chromium and use `PLAYWRIGHT_CHANNEL=chromium`. Ensure the Python visible to Playwright has backend dependencies installed (activate `backend/.venv` if needed).

Browser tests start servers on 5174 and 8001, use separate `backend/data/e2e.sqlite3` state, and save screenshots/traces to ignored `frontend/test-results/`. They leave the normal demo database intact. Backend tests use isolated temporary databases.

## Reset the synthetic demo

Stop the backend, then run from `backend`:

```powershell
.\.venv\Scripts\python.exe seed.py --reset
```

This intentionally replaces saved work and audit history with fresh fixtures. Without `--reset`, existing work is preserved. There is no browser reset endpoint.

## Repository

```text
backend/app/       FastAPI routes, security, adapters, workflow rules, SQLite store
frontend/src/      React/TypeScript ClientWorks, Wealthbox, and LifeSync
fixtures/seed.json Three clients, six accounts, linked records, and evidence
tests/             Backend acceptance and concurrency checks
frontend/tests/    Browser journey and responsive layout checks
docs/              Supplied RAD/plan and implemented requirements
```

See [implementation and acceptance mapping](docs/implementation.md). Configuration is documented in `.env.example`; environment variables are read from the shell, and `.env` is not loaded automatically.

The UI follows layout patterns described in the documents. Original screenshot assets were not supplied in this workspace; this is an interpretation of documented patterns, not a verified reproduction of current production screens.

Framework references: [React](https://react.dev/learn), [Vite](https://vite.dev/guide/), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/).
