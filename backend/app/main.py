import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import workflow as flow
from .adapters import ClientWorksAdapter, WealthboxAdapter, audit, bump, context, now, source, sync_contact
from .models import (AdvanceRequest, ContactSync, DocumentCheck, DraftEdit, EventConfirmation,
                     FindingDecision, Instruction, LinkContact, SignatureCheck, Submit, Versioned)
from .security import ACTOR, OWNERS, authorize, contact_access, owned_record
from .store import Store


def create_app(database_path: str | Path | None = None):
    store = Store(database_path or os.getenv("LIFESYNC_DB_PATH", str(Path(__file__).resolve().parents[1] / "data" / "state.sqlite3")))
    app = FastAPI(title="LifeSync · stages 1–4 simulation", version="0.4.0")
    app.state.store = store
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST", "PUT", "PATCH"], allow_headers=["Content-Type"])

    def visible_clients(state):
        clients = []
        for client_id in state["clients"]:
            try:
                clients.append(authorize(state, client_id))
            except HTTPException:
                continue
        return clients

    def contact_view(state, contact_id):
        contact, client_id = contact_access(state, contact_id)
        return {**contact, "client_id": client_id, "link_status": "Linked" if client_id else "Unlinked",
                "accounts": ClientWorksAdapter(state).list_accounts(client_id) if client_id else [],
                "notes": WealthboxAdapter(state).list_notes(client_id) if client_id else [],
                "tasks": WealthboxAdapter(state).list_tasks(client_id) if client_id else [],
                "financial_projection": "Read-only simulated ClientWorks account data"}

    @app.get("/api/health")
    def health():
        return {"status": "ok", "source_system_mode": "simulation", "ai_mode": "fixture", "storage": "sqlite", "stages": [1, 2, 3, 4]}

    @app.get("/api/session")
    def session():
        return {**ACTOR, "owners": OWNERS, "identity_mode": "Fixed server-side demo advisor; no production authentication"}

    @app.get("/api/clients")
    def list_clients():
        state = store.snapshot()
        return [{**client, "account_count": len(ClientWorksAdapter(state).list_accounts(client["client_id"])),
                 "total_value": sum(account["value"] for account in ClientWorksAdapter(state).list_accounts(client["client_id"])),
                 "crm_contact_id": state["links"].get(client["client_id"])} for client in visible_clients(state)]

    @app.get("/api/clients/{client_id}")
    def get_client(client_id: str):
        state = store.snapshot()
        client = ClientWorksAdapter(state).get_client(client_id)
        return {**client, "crm_contact_id": state["links"].get(client_id)}

    @app.get("/api/clients/{client_id}/accounts")
    def list_accounts(client_id: str):
        return ClientWorksAdapter(store.snapshot()).list_accounts(client_id)

    @app.get("/api/accounts/{account_id}")
    def get_account(account_id: str):
        return ClientWorksAdapter(store.snapshot()).get_account_snapshot(account_id)

    @app.get("/api/clients/{client_id}/context")
    def get_context(client_id: str):
        return context(store.snapshot(), client_id)

    @app.get("/api/sources/{source_id:path}")
    def get_source(source_id: str):
        return source(store.snapshot(), source_id)

    @app.get("/api/contacts")
    def list_contacts():
        state = store.snapshot()
        contacts = []
        for contact_id in state["contacts"]:
            try:
                contacts.append(contact_view(state, contact_id))
            except HTTPException:
                continue
        return contacts

    @app.get("/api/contacts/{contact_id}")
    def get_contact(contact_id: str):
        return contact_view(store.snapshot(), contact_id)

    @app.put("/api/contacts/{contact_id}/link")
    def link_contact(contact_id: str, payload: LinkContact):
        with store.transaction() as state:
            contact, previous_client = contact_access(state, contact_id)
            if payload.client_id:
                authorize(state, payload.client_id)
            key = f"link:{payload.idempotency_key}"
            fingerprint = {"contact_id": contact_id, **payload.model_dump(exclude={"idempotency_key"})}
            if key in state["operations"]:
                if state["operations"][key]["fingerprint"] != fingerprint:
                    raise HTTPException(409, "Link key already used for a different operation.")
                return state["operations"][key]["result"]
            flow.require_version(contact, payload.expected_version)
            if payload.client_id and state["links"].get(payload.client_id) not in {None, contact_id}:
                raise HTTPException(409, "The selected client already has a mapping. Unlink it explicitly first.")
            if previous_client:
                del state["links"][previous_client]
            if payload.client_id:
                state["links"][payload.client_id] = contact_id
            bump(contact)
            result = contact_view(state, contact_id)
            state["operations"][key] = {"fingerprint": fingerprint, "result": result}
            if previous_client or payload.client_id:
                audit(state, payload.client_id or previous_client, "contact_mapping", "Linked" if payload.client_id else "Unlinked", contact_id=contact_id)
            return result

    @app.get("/api/clients/{client_id}/sync")
    def get_sync(client_id: str):
        state = store.snapshot()
        client = authorize(state, client_id)
        contact = WealthboxAdapter(state).get_linked_contact(client_id)
        return {"client": client, "contact": contact, "supported_fields": ["address", "primary_email"],
                "conflicts": [item for item in state["sync_conflicts"] if item["client_id"] == client_id],
                "events": [item for item in state["sync_events"] if item["client_id"] == client_id],
                "source_id": f"SYNC:{client_id}", "version": client["version"], "refreshed_at": now(), "coverage": "complete" if contact else "unlinked"}

    @app.post("/api/clients/{client_id}/contact-sync")
    def update_contact(client_id: str, payload: ContactSync):
        with store.transaction() as state:
            result = sync_contact(state, client_id, payload)
        return JSONResponse(status_code=409 if result["status"] == "conflict" else 200, content=result)

    @app.get("/api/clients/{client_id}/case")
    def client_case(client_id: str):
        state = store.snapshot()
        authorize(state, client_id)
        case = next((case for case in state["cases"].values() if case["client_id"] == client_id), None)
        return flow.case_view(state, case) if case else None

    @app.post("/api/clients/{client_id}/case")
    def create_case(client_id: str, payload: EventConfirmation):
        with store.transaction() as state:
            case = flow.confirm_event(state, client_id, payload)
            return flow.case_view(state, case)

    @app.get("/api/cases/{case_id}")
    def get_case(case_id: str):
        state = store.snapshot()
        return flow.case_view(state, flow.get_case(state, case_id))

    @app.post("/api/cases/{case_id}/analyze-fixture")
    def analyze_fixture(case_id: str):
        with store.transaction() as state:
            case = flow.analyze_fixture(state, flow.get_case(state, case_id))
            return flow.case_view(state, case)

    @app.patch("/api/cases/{case_id}/findings/{finding_id}")
    def decide_finding(case_id: str, finding_id: str, payload: FindingDecision):
        with store.transaction() as state:
            case = flow.get_case(state, case_id)
            return flow.decide_finding(state, case, flow.get_finding(case, finding_id), payload)

    @app.post("/api/cases/{case_id}/findings/{finding_id}/instruction")
    def record_instruction(case_id: str, finding_id: str, payload: Instruction):
        with store.transaction() as state:
            case = flow.get_case(state, case_id)
            return flow.record_instruction(state, case, flow.get_finding(case, finding_id), payload)

    @app.post("/api/cases/{case_id}/findings/{finding_id}/draft")
    def prepare_draft(case_id: str, finding_id: str, payload: Versioned):
        with store.transaction() as state:
            case = flow.get_case(state, case_id)
            finding = flow.get_finding(case, finding_id)
            flow.require_version(finding, payload.expected_version)
            return flow.draft_view(state, flow.prepare_draft(state, case, finding))

    @app.get("/api/drafts/{draft_id}")
    def get_draft(draft_id: str):
        state = store.snapshot()
        return flow.draft_view(state, owned_record(state, "drafts", draft_id))

    @app.put("/api/drafts/{draft_id}")
    def edit_draft(draft_id: str, payload: DraftEdit):
        with store.transaction() as state:
            draft = owned_record(state, "drafts", draft_id)
            flow.require_version(draft, payload.expected_version)
            case = flow.get_case(state, draft["case_id"])
            finding = flow.get_finding(case, draft["finding_id"])
            corrected = payload.model_copy(update={"expected_version": finding["version"]})
            flow.record_instruction(state, case, finding, corrected)
            return flow.draft_view(state, draft)

    @app.post("/api/drafts/{draft_id}/approve")
    def approve_draft(draft_id: str, payload: Versioned):
        with store.transaction() as state:
            draft = owned_record(state, "drafts", draft_id)
            flow.require_version(draft, payload.expected_version)
            case = flow.get_case(state, draft["case_id"])
            finding = flow.get_finding(case, draft["finding_id"])
            flow.ensure_editable(state, finding)
            if draft.get("retired") or not finding["reviewed"] or not finding["instruction"] or finding["instruction"]["instruction_id"] != draft["instruction_id"]:
                raise HTTPException(409, "Draft does not match reviewed, confirmed instructions.")
            if flow.stale_sources(state, case, draft["source_versions"]):
                raise HTTPException(409, "Sources changed. Review evidence and re-confirm instructions.")
            draft["approval"] = {"actor": ACTOR["user_id"], "timestamp": now(), "draft_version": draft["version"]}
            flow.touch(case)
            audit(state, case["client_id"], "draft_approved", "Exact version approved", case["case_id"], draft_id=draft_id, draft_version=draft["version"])
            return flow.draft_view(state, draft)

    @app.post("/api/drafts/{draft_id}/documents")
    def record_document(draft_id: str, payload: DocumentCheck):
        with store.transaction() as state:
            draft = owned_record(state, "drafts", draft_id)
            flow.require_version(draft, payload.expected_version)
            case = flow.get_case(state, draft["case_id"])
            flow.ensure_editable(state, flow.get_finding(case, draft["finding_id"]))
            if draft.get("retired") or payload.document not in draft["requirements"]["documents"]:
                raise HTTPException(422, "Document is not applicable to this active draft.")
            draft["documents"][payload.document] = payload.provided
            flow.touch(case)
            audit(state, case["client_id"], "simulated_document", "Provided" if payload.provided else "Removed", case["case_id"], draft_id=draft_id, draft_version=draft["version"], document=payload.document)
            return flow.draft_view(state, draft)

    @app.post("/api/drafts/{draft_id}/signatures")
    def record_signature(draft_id: str, payload: SignatureCheck):
        with store.transaction() as state:
            draft = owned_record(state, "drafts", draft_id)
            flow.require_version(draft, payload.expected_version)
            case = flow.get_case(state, draft["case_id"])
            flow.ensure_editable(state, flow.get_finding(case, draft["finding_id"]))
            if draft.get("retired") or payload.signer not in draft["requirements"]["signers"]:
                raise HTTPException(422, "Signer is not applicable to this active draft.")
            draft["signatures"][payload.signer] = payload.signed
            flow.touch(case)
            audit(state, case["client_id"], "simulated_signature", "Signed" if payload.signed else "Removed", case["case_id"], draft_id=draft_id, draft_version=draft["version"], signer=payload.signer)
            return flow.draft_view(state, draft)

    @app.post("/api/drafts/{draft_id}/submit")
    def submit_draft(draft_id: str, payload: Submit):
        with store.transaction() as state:
            return flow.submit_draft(state, owned_record(state, "drafts", draft_id), payload)

    @app.get("/api/requests")
    def list_requests():
        state = store.snapshot()
        ids = {client["client_id"] for client in visible_clients(state)}
        return [request for request in state["requests"].values() if request["client_id"] in ids]

    @app.get("/api/requests/{request_id}")
    def get_request(request_id: str):
        return ClientWorksAdapter(store.snapshot()).get_request_status(request_id)

    @app.post("/api/requests/{request_id}/advance")
    def advance_request(request_id: str, payload: AdvanceRequest):
        with store.transaction() as state:
            return flow.advance_request(state, owned_record(state, "requests", request_id), payload)

    @app.get("/api/dashboard")
    def dashboard():
        state = store.snapshot()
        clients = visible_clients(state)
        ids = {client["client_id"] for client in clients}
        cases = [flow.case_view(state, case) for case in state["cases"].values() if case["client_id"] in ids]
        requests = [request for request in state["requests"].values() if request["client_id"] in ids]
        tasks = [task for task in state["tasks"].values() if task["client_id"] in ids and task["status"] == "Open"]
        return {"client_count": len(clients), "account_count": sum(account["client_id"] in ids for account in state["accounts"].values()),
                "total_value": sum(account["value"] for account in state["accounts"].values() if account["client_id"] in ids),
                "open_cases": sum(case["status"] != "Completed" for case in cases), "cases": cases,
                "notifications": tasks, "recent_requests": list(reversed(requests))[:5],
                "source_id": "CW:advisor-01:dashboard", "version": len(state["audit"]) + 1, "refreshed_at": now(), "coverage": "complete"}

    return app


app = create_app()
