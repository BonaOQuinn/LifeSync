"""Deterministic stage-four workflow. Findings are fixtures, never live AI."""

from fastapi import HTTPException

from .adapters import ClientWorksAdapter, WealthboxAdapter, audit, bump, context, identifier, now, source_for_client
from .security import ACTOR, owned_record


def require_version(record, version):
    if record["version"] != version:
        raise HTTPException(409, "Version changed. Refresh before continuing.")


def touch(case):
    bump(case)
    case["updated_at"] = now()


def get_case(state, case_id):
    return owned_record(state, "cases", case_id)


def get_finding(case, finding_id):
    finding = next((item for item in case["findings"] if item["finding_id"] == finding_id), None)
    if not finding:
        raise HTTPException(404, "Finding unavailable.")
    return finding


def versions(state, case, refs):
    return {ref: source_for_client(state, ref, case["client_id"])["version"] for ref in set(refs)}


def stale_sources(state, case, saved):
    stale = []
    for ref, version in saved.items():
        try:
            if source_for_client(state, ref, case["client_id"])["version"] != version:
                stale.append(ref)
        except HTTPException:
            stale.append(ref)
    return stale


def ensure_editable(state, finding):
    draft = state["drafts"].get(finding.get("draft_id"))
    if draft and draft.get("request_id"):
        request = state["requests"][draft["request_id"]]
        if request["status"] != "Rejected":
            raise HTTPException(409, "A submitted or completed request cannot be edited or automatically rolled back.")


def confirm_event(state, client_id, payload):
    ClientWorksAdapter(state).get_client(client_id)
    if not payload.confirmed:
        raise HTTPException(409, "Advisor event confirmation is required.")
    if payload.event_type == "Death" and payload.affected_role not in {"account_owner", "beneficiary"}:
        raise HTTPException(422, "For a death event, explicitly identify account owner or beneficiary.")
    for ref in payload.evidence_refs:
        source_for_client(state, ref, client_id)
    if any(case["client_id"] == client_id for case in state["cases"].values()):
        raise HTTPException(409, "Resume the existing client case.")
    case_id = identifier("CASE")
    case = {"case_id": case_id, "client_id": client_id, "event": payload.model_dump(mode="json"),
            "confirmed_by": ACTOR["user_id"], "confirmed_at": now(), "owner": payload.owner,
            "version": 1, "source_id": f"LS:{case_id}", "refreshed_at": now(), "coverage": "complete",
            "created_at": now(), "updated_at": now(), "analysis_mode": "fixture", "analyzed_at": None,
            "analysis_label": "Seeded review fixture · no live AI", "findings": []}
    state["cases"][case_id] = case
    audit(state, client_id, "event_confirmed", payload.event_type, case_id, version=case["version"], evidence_refs=payload.evidence_refs,
          affected_person=payload.affected_person, affected_role=payload.affected_role)
    return case


def analyze_fixture(state, case):
    if case["analyzed_at"]:
        return case
    ctx = context(state, case["client_id"])
    client_id = case["client_id"]
    entries = []
    if not ctx["contact"]:
        entries = [("coverage", None, None, "CRM evidence is unavailable", "Explicit contact mapping is missing. Review is incomplete; no CRM facts were inferred.", [ctx["client"]["source_id"]], "Manual review")]
    elif (client_id == "C001" and case["event"]["event_type"] == "Divorce"
          and case["event"]["affected_role"] in {"client", "account_owner"}
          and case["event"]["affected_person"].casefold() == "maya bennett"):
        entries = [
            ("address", "A101", "address", "Mailing address needs review", "A101 has the old address. The newer client-call record confirms 92 Harbor Street; an earlier note conflicts. Confirm the client's explicit instructions.", ["CW:A101:snapshot", "WB:N001:note", "WB:N002:note"], "Needs information"),
            ("beneficiary", "A102", "beneficiaries", "Former spouse is still listed", "A102 lists Daniel Bennett. The client supplied no replacement instructions. Do not infer a replacement or the legal effect of the divorce.", ["CW:A102:snapshot", "WB:N001:note"], "Needs information")]
    elif (client_id == "C003" and case["event"]["event_type"] == "Death"
          and case["event"]["affected_role"] == "beneficiary"
          and case["event"]["affected_person"].casefold() == "luis ruiz"):
        entries = [("death", "A302", "beneficiaries", "Beneficiary death requires authority review", "The seeded note reports Luis Ruiz's death, while Elena, the account owner, is living. Sample servicing rules are unknown; obtain evidence and review authority.", ["CW:A302:snapshot", "WB:N004:note"], "Manual review")]
    else:
        entries = [("event", None, None, "Event-specific process needs manual review", "This secondary event has no annotated automatic servicing fixture. Obtain specific instructions and verify applicable rules.", case["event"]["evidence_refs"], "Manual review")]
    for label, account_id, field, title, reason, refs, status in entries:
        # Even fixtures must have authorized, resolvable references.
        saved = versions(state, case, refs)
        finding = {"finding_id": identifier(f"F-{label}"), "account_id": account_id, "field": field,
                   "title": title, "reason": reason, "evidence_refs": refs, "source_versions": saved,
                   "version": 1, "status": status, "reviewed": False, "decision": None, "instruction": None,
                   "draft_id": None, "fixture": True, "conflicting_evidence": label == "address"}
        case["findings"].append(finding)
    case["analyzed_at"] = now()
    case["coverage_report"] = ctx["coverage"]
    touch(case)
    audit(state, client_id, "fixture_review_loaded", "Deterministic fixture; no model called", case["case_id"], version=case["version"])
    return case


def decide_finding(state, case, finding, payload):
    require_version(finding, payload.expected_version)
    ensure_editable(state, finding)
    decision = {"disposition": payload.disposition, "reason": payload.reason,
                "actor": ACTOR["user_id"], "timestamp": now()}
    finding["decision"] = decision
    if payload.disposition == "reviewed":
        finding["reviewed"] = True
        finding["reviewed_versions"] = versions(state, case, finding["evidence_refs"])
    else:
        finding["reviewed"] = False
        finding["instruction"] = None
        if finding.get("draft_id"):
            draft = state["drafts"][finding["draft_id"]]
            draft.update(retired=True, approval=None, signatures={}, documents={})
            bump(draft)
            finding["draft_id"] = None
        finding["status"] = {"no_change": "No change", "manual_review": "Manual review", "needs_information": "Needs information"}[payload.disposition]
    if payload.disposition in {"needs_information", "manual_review"}:
        task = WealthboxAdapter(state).create_followup_task(case, finding, payload.reason, payload.task_owner,
                                                           payload.due_date.isoformat() if payload.due_date else None)
        finding["task_id"] = task["task_id"]
    if payload.disposition == "no_change":
        for task in state["tasks"].values():
            if task.get("case_id") == case["case_id"] and task.get("finding_id") == finding["finding_id"]:
                task["status"] = "Completed"
                bump(task)
    finding["version"] += 1
    touch(case)
    audit(state, case["client_id"], "finding_decision", payload.disposition, case["case_id"],
          finding_id=finding["finding_id"], reason=payload.reason, finding_version=finding["version"])
    return finding


def validated_value(finding, payload):
    if not payload.client_confirmed:
        raise HTTPException(409, "Explicit client-confirmed instructions are required.")
    if finding["field"] == "address":
        if not isinstance(payload.value, str) or len(payload.value.strip()) < 10 or len(payload.value) > 500:
            raise HTTPException(422, "Supply the complete client-confirmed address.")
        return payload.value.strip()
    if finding["field"] == "beneficiaries":
        if not isinstance(payload.value, list) or not payload.value or sum(item.percentage for item in payload.value) != 100:
            raise HTTPException(422, "Supply explicit named beneficiaries with percentages totaling 100.")
        return [item.model_dump() for item in payload.value]
    raise HTTPException(409, "Unknown servicing rules require manual review.")


def record_instruction(state, case, finding, payload):
    require_version(finding, payload.expected_version)
    ensure_editable(state, finding)
    if not finding["reviewed"]:
        raise HTTPException(409, "Review the finding and conflicting evidence before recording instructions.")
    if stale_sources(state, case, finding.get("reviewed_versions", {})):
        raise HTTPException(409, "Evidence changed. Review the finding again.")
    instruction_source = source_for_client(state, payload.source_ref, case["client_id"])
    value = validated_value(finding, payload)
    instruction = {"instruction_id": identifier("INS"), "actor": ACTOR["user_id"], "timestamp": now(),
                   "value": value, "source_ref": payload.source_ref, "source_version": instruction_source["version"],
                   "client_confirmed": True, "reason": payload.reason}
    finding["instruction"] = instruction
    finding["status"] = "Draft"
    finding["version"] += 1
    if finding["draft_id"]:
        draft = state["drafts"][finding["draft_id"]]
        rewrite_draft(state, case, finding, draft)
    touch(case)
    audit(state, case["client_id"], "client_instruction", "Confirmed", case["case_id"],
          finding_id=finding["finding_id"], instruction_id=instruction["instruction_id"], source_ref=payload.source_ref)
    return finding


def get_sample_requirements(case, finding, account):
    if case["event"]["event_type"] != "Divorce" or finding["field"] not in {"address", "beneficiaries"}:
        return None
    return {"rule_id": f"SAMPLE:{finding['field']}:v1", "simulation": True,
            "forms": ["Simulated address change form" if finding["field"] == "address" else "Simulated beneficiary designation form"],
            "documents": ["Client instruction record"], "signers": account["owners"],
            "label": "Sample prototype requirements; production process unverified"}


def rewrite_draft(state, case, finding, draft):
    account = ClientWorksAdapter(state).get_account_snapshot(finding["account_id"])
    draft.update(current_value=account[finding["field"]], proposed_value=finding["instruction"]["value"],
                 instruction_id=finding["instruction"]["instruction_id"], instruction_source=finding["instruction"]["source_ref"],
                 source_versions=versions(state, case, [*finding["evidence_refs"], finding["instruction"]["source_ref"]]),
                 approval=None, signatures={}, documents={}, request_id=None, retired=False, submission_error=None)
    bump(draft)


def prepare_draft(state, case, finding):
    ensure_editable(state, finding)
    if not finding["instruction"] or not finding["reviewed"]:
        raise HTTPException(409, "Reviewed evidence and explicit client instructions are required.")
    if stale_sources(state, case, finding.get("reviewed_versions", {})):
        raise HTTPException(409, "Evidence changed. Review and confirm instructions again.")
    instruction_source = source_for_client(state, finding["instruction"]["source_ref"], case["client_id"])
    if instruction_source["version"] != finding["instruction"]["source_version"]:
        raise HTTPException(409, "Instruction evidence changed. Reconfirm the client instruction.")
    account = ClientWorksAdapter(state).get_account_snapshot(finding["account_id"])
    requirements = get_sample_requirements(case, finding, account)
    if not requirements:
        raise HTTPException(409, "Unknown process or authority rules. Route to manual review.")
    if finding["draft_id"]:
        return state["drafts"][finding["draft_id"]]
    draft_id = identifier("DRAFT")
    draft = {"draft_id": draft_id, "client_id": case["client_id"], "case_id": case["case_id"],
             "finding_id": finding["finding_id"], "account_id": account["account_id"], "field": finding["field"],
             "requirements": requirements, "version": 0, "source_id": f"LS:{draft_id}", "coverage": "complete"}
    rewrite_draft(state, case, finding, draft)
    state["drafts"][draft_id] = draft
    finding["draft_id"] = draft_id
    finding["version"] += 1
    touch(case)
    audit(state, case["client_id"], "draft_prepared", "Awaiting approval", case["case_id"],
          draft_id=draft_id, draft_version=draft["version"], source_versions=draft["source_versions"])
    return draft


def validate_draft(state, draft):
    case = get_case(state, draft["case_id"])
    finding = get_finding(case, draft["finding_id"])
    errors = []
    if draft.get("retired") or not finding["instruction"] or finding["instruction"]["instruction_id"] != draft["instruction_id"]:
        errors.append("Draft no longer matches confirmed instructions.")
    if stale_sources(state, case, draft["source_versions"]):
        errors.append("Source evidence changed. Review and prepare a new draft version.")
    if not draft["approval"] or draft["approval"]["draft_version"] != draft["version"]:
        errors.append("Approval of this exact draft version is required.")
    if any(not draft["documents"].get(document) for document in draft["requirements"]["documents"]):
        errors.append("Required simulated documents are missing.")
    if any(not draft["signatures"].get(signer) for signer in draft["requirements"]["signers"]):
        errors.append("Required simulated signatures are missing.")
    return errors


def get_simulated_signature_status(draft):
    return {"source_id": f"SIM:SIGNATURE:{draft['draft_id']}", "version": draft["version"],
            "refreshed_at": draft["refreshed_at"], "coverage": "complete", "simulation": True,
            "signers": [{"signer": signer, "status": "Signed" if draft["signatures"].get(signer) else "Missing"}
                        for signer in draft["requirements"]["signers"]]}


def draft_view(state, draft):
    errors = validate_draft(state, draft)
    request = state["requests"].get(draft.get("request_id"))
    if request:
        status = request["status"]
    elif draft.get("retired") or any("Source evidence" in error for error in errors):
        status = "Manual review"
    elif not draft["approval"]:
        status = "Awaiting approval"
    elif errors:
        status = "Waiting for signature"
    else:
        status = "Ready to submit"
    return {**draft, "status": status, "blocked_reasons": errors, "request": request}


def case_view(state, case):
    findings = []
    drafts = []
    for finding in case["findings"]:
        draft = state["drafts"].get(finding.get("draft_id"))
        view = draft_view(state, draft) if draft else None
        findings.append({**finding, "status": view["status"] if view else finding["status"]})
        if view:
            drafts.append(view)
    resolved = sum(item["status"] in {"Completed", "No change"} for item in findings)
    status = "Confirmed" if not case["analyzed_at"] else ("Completed" if findings and resolved == len(findings) else "Open")
    return {**case, "findings": findings, "drafts": drafts, "status": status,
            "resolved_count": resolved, "unresolved_count": len(findings) - resolved,
            "tasks": [task for task in state["tasks"].values() if task.get("case_id") == case["case_id"]],
            "audit": [entry for entry in state["audit"] if entry["case_id"] == case["case_id"]]}


def submit_draft(state, draft, payload):
    # Authorize even when returning an existing request; never let a key grant access.
    case = get_case(state, draft["case_id"])
    key = f"submission:{payload.idempotency_key}"
    fingerprint = {"draft_id": draft["draft_id"], "version": payload.expected_version}
    existing = state["operations"].get(key)
    if existing:
        if existing["fingerprint"] != fingerprint:
            raise HTTPException(409, "This key is already bound to another draft version.")
        return state["requests"][existing["request_id"]]
    require_version(draft, payload.expected_version)
    if draft.get("request_id"):
        request = state["requests"][draft["request_id"]]
        if request["status"] != "Rejected":
            raise HTTPException(409, "This draft already has a logical request; use its original key.")
        raise HTTPException(409, "Correct and reapprove the rejected draft before resubmitting.")
    errors = validate_draft(state, draft)
    if errors:
        raise HTTPException(409, {"message": "Submission blocked by workflow gates.", "blocked_reasons": errors})
    if payload.simulate_failure:
        draft["submission_error"] = "Simulated transport failure. No institution request was created; retry safely."
        audit(state, case["client_id"], "submission_failed", "Transport failure; no request created", case["case_id"], draft_version=draft["version"])
        touch(case)
        return {"status": "Submission failed", "detail": draft["submission_error"]}
    request = ClientWorksAdapter(state).submit_change(draft, payload.idempotency_key)
    draft["request_id"] = request["request_id"]
    draft["submission_error"] = None
    state["operations"][key] = {"fingerprint": fingerprint, "request_id": request["request_id"]}
    touch(case)
    audit(state, case["client_id"], "request_submitted", "Simulated Submitted", case["case_id"],
          draft_id=draft["draft_id"], draft_version=draft["version"], request_id=request["request_id"], source_versions=draft["source_versions"])
    return request


def advance_request(state, request, payload):
    require_version(request, payload.expected_version)
    transitions = {"Submitted": {"Processing", "Rejected"}, "Processing": {"Completed", "Rejected"}}
    if payload.outcome not in transitions.get(request["status"], set()):
        raise HTTPException(409, "Invalid simulated institution status transition.")
    account = ClientWorksAdapter(state).get_account_snapshot(request["account_id"])
    if payload.outcome == "Completed":
        draft = state["drafts"][request["draft_id"]]
        expected = draft["source_versions"].get(account["source_id"])
        if account["version"] != expected:
            raise HTTPException(409, "Account changed after submission. Reject and correct the request instead of overwriting.")
        account[request["field"]] = request["value"]
        bump(account)
        request["receipt"] = {"receipt_id": identifier("SIM-RECEIPT"), "simulation": True, "timestamp": now(),
                              "masked_account": account["masked_number"], "account_version": account["version"],
                              "message": "Simulated institution confirmed this account update."}
        case = get_case(state, request["case_id"])
        for task in state["tasks"].values():
            if task.get("case_id") == case["case_id"] and task.get("finding_id") == draft["finding_id"]:
                task["status"] = "Completed"
                bump(task)
    request["status"] = payload.outcome
    request["outcome_reason"] = payload.reason
    bump(request)
    touch(get_case(state, request["case_id"]))
    audit(state, request["client_id"], "request_reconciled", f"Simulated {payload.outcome}", request["case_id"],
          request_id=request["request_id"], request_version=request["version"], reason=payload.reason)
    return request
