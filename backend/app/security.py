from datetime import date

from fastapi import HTTPException

# Deliberately server-owned, fixed local demo identity. Request headers cannot select
# another advisor. Production authentication is a separate integration boundary.
ACTOR = {"user_id": "advisor-01", "display_name": "Alex Morgan", "role": "advisor", "simulation": True}
OWNERS = {"advisor-01": "Alex Morgan", "support-01": "Taylor Chen"}


def authorize(state, client_id):
    client = state["clients"].get(client_id)
    today = date.today().isoformat()
    if (not client or client["assigned_user_id"] != ACTOR["user_id"]
            or today < client["access_from"] or today > client["access_until"]):
        raise HTTPException(403, "Client access denied.")
    return client


def owned_record(state, collection, record_id):
    record = state[collection].get(record_id)
    if not record:
        raise HTTPException(404, "Record unavailable.")
    authorize(state, record["client_id"])
    return record


def contact_access(state, contact_id):
    contact = state["contacts"].get(contact_id)
    if not contact or contact["assigned_user_id"] != ACTOR["user_id"]:
        raise HTTPException(403, "Contact access denied.")
    linked = next((cid for cid, wid in state["links"].items() if wid == contact_id), None)
    if linked:
        authorize(state, linked)
    return contact, linked
