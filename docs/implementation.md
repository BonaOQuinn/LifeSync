# Stages 1–4 implementation

Scope follows the supplied development plan stages 1–4 and RAD version 2.0. Their stage-5 Bedrock work and release packaging do not expand the requested implementation.

## Requirement mapping

| RAD | Implementation | Verification |
| --- | --- | --- |
| LS01 · Assigned access | Server-owned advisor, effective assignment dates, ownership checks, same-client source references, contact assignment checks, access rechecked on retries. | Changed client/account/source/contact IDs; forged identity headers; assignment revocation after approval. |
| LS02 · Confirmed event | Advisor confirmation, explicit affected person/role, optional date, selected evidence, and owner persisted before findings. | Missing confirmation and cross-client evidence rejected; beneficiary death separated from owner death. |
| LS03 · Evidence/coverage | Source IDs, versions, dates, conflicting original notes, coverage report, evidence dialog, and labeled fixture findings. | References resolve; unlinked CRM is unavailable and yields manual review. Live AI remains stage 5. |
| LS04 · Specific intent | Reviewed evidence, client confirmation, exact values, evidence/reason, owned follow-ups, documented no change. | No draft without instructions; beneficiary remains unknown; owner and Needs date survive restart. |
| LS05 · Validated drafts | Current/proposed comparison, sample rule/forms/documents/signers, instruction and account/evidence versions. | Known divorce samples; unknown event/authority rules require manual review. |
| LS06 · Review gates | Exact-version approval, simulated documents/signatures, current sources/instructions/access; edits invalidate prior gates. | Direct missing-gate submissions; edited approval; stale sources; revoked assignment. |
| LS07 · Account outcomes | Atomic deduplication, separate account requests, statuses, receipts, retry after transport failure. | Ten concurrent retries create one request; completion changes account separately from contact; unresolved findings keep case open. |
| LS08 · Resume/audit | SQLite transactions persist cases/tasks/requests/conflicts. Application audit is append-only, with actor/reason/time/version. | Restart persistence, follow-ups, no-change history, no audit edit/delete route. |

## Contracts and persistence

`ClientWorksAdapter`: `get_client`, `list_accounts`, `get_account_snapshot`, `update_contact`, `submit_change`, `get_request_status`.

`WealthboxAdapter`: `get_linked_contact`, `list_notes`, `list_tasks`, `update_contact`, `create_followup_task`.

Rules: `get_sample_requirements`, `validate_draft`, `get_simulated_signature_status`. `analyze_fixture` is deterministic and labeled. It is the replacement point for authorized structured Bedrock analysis; no AWS SDK or model is called.

Source records carry `source_id`, `version`, `refreshed_at`, and `coverage`. Context reports coverage by source class. These are internal prototype contracts, not published LPL/Wealthbox endpoints.

SQLite stores the small synthetic dataset in one JSON state row. `BEGIN IMMEDIATE` serializes competing writes across threads/workers; transactions roll back on failed gates. This is local durable prototype storage, not the proposed DynamoDB/S3 deployment. No production identity, electronic signatures, legal document verification, or institution API is established.

Contact writes use origin/target expected versions and a deduplication key. One transaction updates both records under one event ID, with no receiving-side echo handler. A saved conflict changes neither record; a newly approved current-version operation resolves it. Reusing a key for different content fails. Links are explicit; no name/SSN matching is performed.

Only address and primary email synchronize. Financial accounts are projected read-only into CRM. Account changes require separate servicing submission and a completion receipt. Original dated notes are retained.

Workflow writes use expected content/finding versions. Approval/documents/signatures attach to that content version; editing creates a new version and clears prior gates. Tasks deduplicate by case/finding; draft preparation reuses the active draft. Request keys bind one immutable draft/version. A completed-request retry returns the original receipt despite the advanced account version.

## API overview

OpenAPI at `/docs` lists full schemas.

| Route | Purpose |
| --- | --- |
| `GET /api/clients`, `/api/clients/{id}`, `/api/accounts/{id}` | Assigned ClientWorks records. |
| `GET /api/clients/{id}/context`, `/api/sources/{source_id}` | Authorized context/evidence. |
| `GET /api/contacts`, `/api/contacts/{id}` | CRM and account projection. |
| `PUT /api/contacts/{id}/link` | Explicit mapping. |
| `POST /api/clients/{id}/contact-sync`, `GET .../sync` | Approved update, conflicts, events. |
| `GET/POST /api/clients/{id}/case` | Resume or confirm event. |
| `POST /api/cases/{id}/analyze-fixture` | Load annotated findings once. |
| `PATCH /api/cases/{id}/findings/{finding_id}` | Review, follow-up, manual review, no change. |
| `POST .../instruction`, `POST .../draft` | Confirm intent, prepare draft. |
| `PUT /api/drafts/{id}` | Edit/reconfirm and invalidate gates. |
| `POST /api/drafts/{id}/approve`, `/documents`, `/signatures` | Exact-version review controls. |
| `GET /api/drafts/{id}/signature-status` | Metadata-bearing simulated status. |
| `POST /api/drafts/{id}/submit` | Idempotent submission. |
| `POST /api/requests/{id}/advance` | Explicit simulated institution outcome. |

Identity is server-owned local simulation. Arbitrary identity headers are ignored, no message endpoint exists, and browser credentials are absent. Audit events cannot be edited through application APIs; an operator can still change the local SQLite file.

## States and correction

Needs information / Manual review → Draft → Awaiting approval → Waiting for signature → Ready to submit → Submitted → Processing → Completed or Rejected. No change is a recorded resolution. Missing documents are explicit blocking reasons alongside signature requirements. Stale evidence yields Manual review until reviewed/reconfirmed.

A transport failure records `submission_error` and creates no request; it is distinct from an institution rejection. Retrying the same key is safe. A rejected draft must be edited, reapproved, and signed before a new request version. Submitted/completed requests cannot be edited or automatically rolled back. Completion checks the original account version before applying the update, preventing late overwrites.

Case status derives from all findings. Completed/No change resolve items; missing beneficiary intent, manual review, and rejection keep the case open. Refresh preserves work.

## Remaining stages

Backend tests cover exit gates and the relevant portions of RAD A01–A10. Browser checks cover client/search context, evidence, missing signatures, receipts/resume, explicit links, contact sync/conflicts, and mobile overflow. These do not certify regulatory compliance or production authentication.

Stage 5: verify permitted Bedrock access; retrieve authorized sources; validate structured findings/references; expose AI timeout/invalid-output errors; measure latency. Stage 6: broader release verification, human usability review, preparation-time measurement, cloud persistence/deployment if chosen, and submission packaging.
