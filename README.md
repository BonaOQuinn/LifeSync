# LifeSync

An AI-assisted lifecycle page inside a simulated LPL ClientWorks workspace.

LifeSync helps financial advisors review client records after a confirmed life event, identify information that may need attention, prepare authorized update drafts, and track each request to a recorded outcome. The prototype connects a ClientWorks simulation with a Wealthbox CRM simulation and uses Amazon Bedrock for AI analysis.

Built for the **2026 LPL Financial University Hackathon**.

## Project status

This README describes the agreed prototype scope and proposed implementation. Application source code was not available when it was written. Folder names, configuration variables, and launch commands below are a proposed repository convention; implement and verify them before treating this as a runnable quick start.

The prototype uses synthetic client data. ClientWorks, Wealthbox, signatures, and institution submissions are simulated. Bedrock analysis is intended to run against an enabled model in the event AWS account. Advisor Handover is outside this release.

## The problem

Life events such as marriage, divorce, or death can leave contact details, account information, and relationship records inconsistent. Advisors need to determine what requires review, collect specific instructions, prepare the appropriate requests, and follow up on incomplete work.

LifeSync brings that process into the advisor workspace, with source evidence and human approval at each consequential step.

## Prototype scope

| Component | Planned behavior |
| --- | --- |
| ClientWorks simulation | Home dashboard, assigned-client search, account lists, notifications, and request tracking. |
| Wealthbox simulation | Linked contacts, dated notes, owned tasks, and an LPL Financial account view. |
| LifeSync page | Event confirmation, AI findings, evidence review, client instructions, draft comparison, approvals, and request outcomes. |
| Integration adapters | Explicit client/contact linking, supported contact-field synchronization, and simulated account submissions. |
| AI analysis | Source-linked findings with missing information and conflicting evidence shown explicitly. |

The primary demo is a divorce case. Marriage and death are smaller review examples. The prototype does not execute trades, move money, choose replacement beneficiaries, or make legal or tax determinations.

## Advisor workflow

1. Open the simulated ClientWorks **Clients** page and select an assigned client.
2. Review the client's accounts and linked Wealthbox notes/tasks.
3. Open **LifeSync** and confirm the event, affected person, and supporting evidence.
4. Run AI analysis on authorized source records.
5. Review findings and record specific client instructions or a documented no-change decision.
6. Prepare per-account drafts showing current and proposed values.
7. Approve the exact draft version and satisfy simulated document/signature requirements.
8. Submit through the mock account-service adapter.
9. Track each request and keep unresolved items open with a responsible owner.

**Contact synchronization and account servicing are separate outcomes.** An address appearing in both contact records does not establish that an account update has completed.

## Demonstration case

Client `C001` reports a divorce:

- Account `A101` has an outdated address.
- Account `A102` lists the former spouse as a beneficiary.
- The client confirms a new address but has not supplied beneficiary instructions.

Expected behavior: AI flags both records with supporting sources. LifeSync prepares the address draft and creates a beneficiary follow-up. The address request can complete through a simulated receipt while the overall case remains open. The AI never invents a replacement beneficiary.

Include a client outside the active advisor's assignment to demonstrate access denial, plus conflicting dated CRM notes to demonstrate evidence review.

## Proposed architecture

| Layer | Proposed technology | Responsibility |
| --- | --- | --- |
| Frontend | React and TypeScript | ClientWorks shell, Wealthbox simulation, and LifeSync review UI. |
| Backend | Python and FastAPI | Access checks, source adapters, validation, workflow state, and model calls. |
| AI | Amazon Bedrock | Analyze retrieved evidence and prepare proposed findings/draft text. |
| Documents | Amazon S3 | Synthetic source documents and draft packets. |
| Persistent state | Amazon DynamoDB | Cases, instructions, draft versions, tasks, requests, and audit events. |

Keep external systems behind adapters so production integrations can replace simulations without rewriting the review workflow. Lambda and API Gateway deployment are optional after the core demo works.

### Proposed repository structure

| Path | Contents |
| --- | --- |
| `frontend/` | ClientWorks shell, Wealthbox views, LifeSync components, and API client. |
| `backend/app/main.py` | FastAPI application entry point. |
| `backend/app/adapters/` | ClientWorks, Wealthbox, signature, and submission adapters. |
| `backend/app/services/` | AI analysis, process rules, and case transitions. |
| `backend/app/models/` | Validated request, record, finding, and draft schemas. |
| `backend/requirements.txt` | Backend dependencies. |
| `fixtures/` | Synthetic clients, accounts, notes, tasks, and expected findings. |
| `tests/` | Authorization, approval, synchronization, and retry checks. |
| `docs/` | RAD, development plan, screenshot references, and demo instructions. |

## Proposed local setup

Prerequisites: Node.js/npm, Python with virtual-environment support, and authorized AWS credentials with access to an event-approved Bedrock model. Pin runtime and dependency versions when the scaffold is created.

The following commands assume the proposed structure above, a Vite frontend with a `dev` script, and a FastAPI app exported as `app` in `backend/app/main.py`. They have not been tested against application code.

### Backend

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Then install dependencies and start the proposed entry point:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Use the URL printed by the frontend server. Configure the backend to allow the actual local frontend origin.

### Configuration contract

These variable names are proposed and must be wired into backend/frontend configuration. A local `.env` file is useful only if the application explicitly loads it.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `AWS_REGION` | Backend | Region where the selected model and resources are available. |
| `BEDROCK_MODEL_ID` | Backend | Exact enabled model or inference-profile identifier. |
| `S3_BUCKET_NAME` | Backend | Synthetic document bucket. |
| `DYNAMODB_TABLE_NAME` | Backend | Prototype state table. |
| `SOURCE_SYSTEM_MODE` | Backend | `simulation` for ClientWorks/Wealthbox and external actions. |
| `AI_MODE` | Backend | `bedrock` for live analysis; `fixture` only for labeled development output. |
| `VITE_API_BASE_URL` | Frontend | Backend URL, for example `http://localhost:8000`. |

Keep AI mode independent of source-system mode: the intended demo combines **simulated systems with live Bedrock analysis**. Verify a minimal Bedrock call early. Do not silently substitute prerecorded findings when live inference fails.

Use the AWS SDK credential provider chain with event-issued credentials or an approved profile. Never put credentials in frontend variables or commit them. Temporary credentials may require a session token. Commit a credential-free `.env.example` and ignore local environment files.

Create the configured bucket/table and supply a documented fixture-loading procedure before declaring setup complete. No seed or reset command is assumed to exist yet.

## Simulation interface reference

The supplied ClientWorks video screenshots show:

- A dark **Client Management** header and horizontal navigation.
- **Home** panels for notifications, reminders, quick actions, and recent requests.
- **Clients** and **Accounts** pages with Quick Views, search, filter chips, and tables.
- A **Practice Metrics** page, which is optional for this demo.

The frames depict a training environment with 2018 dates. They guide the demonstrated layout rather than establishing current production UI. LifeSync is a proposed new navigation tab and client-specific action.

The Wealthbox reference shows an **LPL Financial** launcher and contact tab, **Manage Linked Clients**, **Open in LPL Financial**, total value, and Account/Title/Type/Class/Value columns. Still images establish visible controls, not their full interaction behavior.

## Development order

1. Create shared synthetic data and the ClientWorks shell.
2. Build Wealthbox contacts, notes, tasks, and the LPL account view.
3. Connect adapters and implement supported contact synchronization.
4. Build LifeSync states and review controls using labeled fixture findings.
5. Add live Bedrock analysis and validate its structured output and source references.
6. Verify critical cases, measure the demo, and package the submission.

Probe Bedrock access early while the simulations are being built. Defer custom training, scanned-document extraction, live messaging, production APIs, and advanced metrics until the core workflow passes.

## Verification checklist

These are intended release checks, not reported test results:

- Unassigned client/account/source requests fail at the backend.
- Every AI factual finding has an authorized, resolvable source reference.
- Missing beneficiary instructions remain unresolved.
- Incomplete documents or signatures block submission.
- Editing an approved draft or changing relevant evidence requires new review.
- Repeated submission with one key creates one logical request.
- Completed and rejected account items retain separate outcomes.
- Contact synchronization handles conflicts without echo loops.
- Refresh preserves cases, draft edits, tasks, and review history.
- AI failures preserve work and display an explicit retry/error state.
- Malicious source text cannot override permissions or approval gates.
- Main controls support keyboard use; status is communicated through text.

Record manual and assisted review time on the same synthetic case, including correction time. Report observed findings, false positives, and missed items. Prototype checks do not establish production regulatory compliance.

## Documentation and references

Place the project documents in `docs/` when setting up the repository:

- `LifeSync_Page_RAD.docx`
- `LifeSync_Development_Plan.docx`
- Supplied ClientWorks video frames and Wealthbox integration screenshot

Public references:

- [ClientWorks overview video](https://lpl.vids.io/videos/489adfbb1a11e3c0c0/lpl-client-works-overview)
- [Wealthbox two-way contact synchronization](https://help.wealthbox.com/hc/en-us/articles/34470324688539-How-to-use-the-two-way-sync-integration-between-Wealthbox-and-LPL-ClientWorks)
- [Wealthbox financial account synchronization](https://help.wealthbox.com/hc/en-us/articles/36073560352283-How-to-use-the-Financial-Account-Sync-integration-between-Wealthbox-and-LPL-ClientWorks)

Production development requires confirmation of ClientWorks embedding, identity and assignments, Wealthbox notes/task access, account write operations, signature providers, process rules, retention, and deployment approval. This hackathon prototype is a proposed integration and is not an official LPL or Wealthbox product.
