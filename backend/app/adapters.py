"""Internal prototype contracts, not published LPL or Wealthbox API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from .security import ACTOR, authorize, contact_access, owned_record


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(prefix):
    return f"{prefix}-{uuid4().hex[:12]}"


def bump(record):
    record["version"] += 1
    record["refreshed_at"] = now()


def audit(state, client_id, action, outcome, case_id=None, **details):
    entry = {"audit_id": identifier("AUD"), "client_id": client_id,
             "actor": ACTOR["user_id"], "timestamp": now(), "action": action,
             "case_id": case_id, "outcome": outcome, "details": details}
    state["audit"].append(entry)
    return entry


class ClientWorksAdapter:
    def __init__(self, state):
        self.state = state

    def get_client(self, client_id):
        return authorize(self.state, client_id)

    def list_accounts(self, client_id):
        self.get_client(client_id)
        return [account for account in self.state["accounts"].values() if account["client_id"] == client_id]

    def get_account_snapshot(self, account_id):
        return owned_record(self.state, "accounts", account_id)

    def update_contact(self, client_id, field, value):
        client = self.get_client(client_id)
        client[field] = value
        bump(client)
        return client

    def submit_change(self, draft, key):
        self.get_account_snapshot(draft["account_id"])
        request_id = identifier("REQ")
        request = {"request_id": request_id, "external_request_id": f"SIM-{request_id}",
                   "client_id": draft["client_id"], "case_id": draft["case_id"],
                   "account_id": draft["account_id"], "draft_id": draft["draft_id"],
                   "draft_version": draft["version"], "idempotency_key": key,
                   "field": draft["field"], "value": draft["proposed_value"],
                   "status": "Submitted", "simulation": True, "receipt": None,
                   "version": 1, "source_id": f"CW:{request_id}:request",
                   "refreshed_at": now(), "coverage": "complete"}
        self.state["requests"][request_id] = request
        return request

    def get_request_status(self, request_id):
        return owned_record(self.state, "requests", request_id)


class WealthboxAdapter:
    def __init__(self, state):
        self.state = state

    def get_linked_contact(self, client_id):
        authorize(self.state, client_id)
        contact_id = self.state["links"].get(client_id)
        if not contact_id:
            return None
        contact, linked = contact_access(self.state, contact_id)
        if linked != client_id:
            raise HTTPException(409, "Ambiguous contact mapping requires review.")
        return contact

    def list_notes(self, client_id):
        contact = self.get_linked_contact(client_id)
        if not contact:
            return []
        return [note for note in self.state["notes"].values()
                if note["client_id"] == client_id and note["crm_contact_id"] == contact["crm_contact_id"]
                and ACTOR["user_id"] in note["permissions"]]

    def list_tasks(self, client_id):
        contact = self.get_linked_contact(client_id)
        if not contact:
            return []
        return [task for task in self.state["tasks"].values()
                if task["client_id"] == client_id and task["crm_contact_id"] == contact["crm_contact_id"]]

    def update_contact(self, client_id, field, value):
        contact = self.get_linked_contact(client_id)
        if not contact:
            raise HTTPException(409, "Contact is Unlinked.")
        contact[field] = value
        bump(contact)
        contact["synced_at"] = now()
        return contact

    def create_followup_task(self, case, finding, title, owner, due_date):
        existing = next((task for task in self.state["tasks"].values()
                         if task.get("finding_id") == finding["finding_id"] and task.get("case_id") == case["case_id"]), None)
        if existing:
            existing.update(title=title, owner=owner, due_date=due_date, status="Open")
            bump(existing)
            return existing
        task_id = identifier("TASK")
        contact = self.get_linked_contact(case["client_id"])
        task = {"task_id": task_id, "client_id": case["client_id"],
                "crm_contact_id": contact["crm_contact_id"] if contact else None,
                "case_id": case["case_id"], "finding_id": finding["finding_id"],
                "title": title, "owner": owner, "due_date": due_date, "status": "Open",
                "recorded_at": now(), "version": 1, "source_id": f"WB:{task_id}:task",
                "refreshed_at": now(), "coverage": "complete" if contact else "unlinked",
                "delivery": "Simulated CRM task" if contact else "LifeSync local follow-up (CRM unlinked)"}
        self.state["tasks"][task_id] = task
        return task


def source(state, source_id):
    for collection in ("clients", "accounts", "contacts", "notes", "tasks", "documents", "requests"):
        for record in state[collection].values():
            if record["source_id"] != source_id:
                continue
            if collection == "contacts":
                contact_access(state, record["crm_contact_id"])
            else:
                authorize(state, record["client_id"])
            if collection == "notes" and ACTOR["user_id"] not in record["permissions"]:
                raise HTTPException(403, "Source access denied.")
            return record
    raise HTTPException(404, "Source unavailable.")


def source_for_client(state, source_id, client_id):
    record = source(state, source_id)
    if "client_id" in record:
        if record["client_id"] != client_id:
            raise HTTPException(403, "Source access denied.")
    elif record.get("crm_contact_id") != state["links"].get(client_id):
        raise HTTPException(403, "Source access denied.")
    return record


def context(state, client_id):
    client = ClientWorksAdapter(state).get_client(client_id)
    crm = WealthboxAdapter(state)
    contact = crm.get_linked_contact(client_id)
    accounts = ClientWorksAdapter(state).list_accounts(client_id)
    notes, tasks = crm.list_notes(client_id), crm.list_tasks(client_id)
    documents = [record for record in state["documents"].values() if record["client_id"] == client_id]
    coverage = {"accounts": "complete", "crm_notes": "complete" if contact else "unavailable",
                "crm_tasks": "complete" if contact else "unavailable", "documents": "complete" if documents else "missing"}
    return {"client": client, "contact": contact, "accounts": accounts, "notes": notes,
            "tasks": tasks, "documents": documents, "sources": [client, *accounts, *notes, *tasks, *documents, *([contact] if contact else [])],
            "coverage": coverage, "errors": [] if contact else ["Wealthbox is Unlinked; CRM evidence has not been reviewed."],
            "source_id": f"CTX:{client_id}", "version": max([record["version"] for record in [client, *accounts, *notes, *tasks]]),
            "refreshed_at": now(), "simulation": True}


def sync_contact(state, client_id, payload):
    client = authorize(state, client_id)
    contact = WealthboxAdapter(state).get_linked_contact(client_id)
    if not contact:
        raise HTTPException(409, "Contact is Unlinked. Select an explicit mapping first.")
    if not payload.approved:
        raise HTTPException(409, "An approved client instruction is required for contact synchronization.")
    if payload.field == "primary_email" and ("@" not in payload.value or " " in payload.value):
        raise HTTPException(422, "Enter a valid primary email.")
    fingerprint = {"client_id": client_id, **payload.model_dump(exclude={"idempotency_key"})}
    key = f"sync:{payload.idempotency_key}"
    if key in state["operations"]:
        operation = state["operations"][key]
        if operation["fingerprint"] != fingerprint:
            raise HTTPException(409, "This deduplication key already belongs to a different contact update.")
        return operation["result"]
    origin, target = (client, contact) if payload.origin == "clientworks" else (contact, client)
    if origin["version"] != payload.expected_version or target["version"] != payload.target_version:
        conflict = {"conflict_id": identifier("CONFLICT"), "client_id": client_id, "status": "Needs review",
                    "origin": payload.origin, "field": payload.field, "proposed_value": payload.value,
                    "clientworks_version": client["version"], "wealthbox_version": contact["version"],
                    "timestamp": now(), "reason": "A contact version changed. Refresh and confirm a resolution."}
        state["sync_conflicts"].append(conflict)
        result = {"status": "conflict", "conflict": conflict, "detail": conflict["reason"]}
        state["operations"][key] = {"fingerprint": fingerprint, "result": result}
        audit(state, client_id, "contact_sync", "Conflict requires review", field=payload.field)
        return result
    event = {"event_id": identifier("SYNC"), "client_id": client_id, "origin": payload.origin,
             "field": payload.field, "timestamp": now(), "propagations": 1,
             "idempotency_key": payload.idempotency_key, "instruction_source": payload.instruction_source}
    ClientWorksAdapter(state).update_contact(client_id, payload.field, payload.value)
    WealthboxAdapter(state).update_contact(client_id, payload.field, payload.value)
    client["sync_event_id"] = contact["sync_event_id"] = event["event_id"]
    state["sync_events"].append(event)
    # One transaction and one shared event ID; no receiving-side echo handler.
    for conflict in state["sync_conflicts"]:
        if conflict["client_id"] == client_id and conflict["field"] == payload.field and conflict["status"] == "Needs review":
            conflict.update(status="Resolved", resolved_by=ACTOR["user_id"], resolved_at=now(), event_id=event["event_id"])
    result = {"status": "synced", "event": event, "client": client.copy(), "contact": contact.copy(),
              "message": "Contact records synchronized. Account servicing remains separate."}
    state["operations"][key] = {"fingerprint": fingerprint, "result": result}
    audit(state, client_id, "contact_sync", "Propagated once", event_id=event["event_id"], origin=payload.origin,
          clientworks_version=client["version"], wealthbox_version=contact["version"])
    return result
