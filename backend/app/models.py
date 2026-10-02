from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Versioned(Input):
    expected_version: int = Field(ge=1)


class ContactSync(Input):
    origin: Literal["clientworks", "wealthbox"]
    field: Literal["address", "primary_email"]
    value: str = Field(min_length=5, max_length=500)
    expected_version: int = Field(ge=1)
    target_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=100)
    approved: bool
    instruction_source: str = Field(min_length=8, max_length=500)

    @field_validator("value")
    @classmethod
    def no_controls(cls, value):
        if any(ord(character) < 32 for character in value):
            raise ValueError("Control characters are not allowed.")
        return value


class LinkContact(Versioned):
    client_id: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=100)


class EventConfirmation(Input):
    event_type: Literal["Divorce", "Marriage", "Death"]
    affected_person: str = Field(min_length=2, max_length=150)
    affected_role: Literal["client", "account_owner", "beneficiary", "spouse"]
    event_date: date | None = None
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    owner: Literal["advisor-01", "support-01"] = "advisor-01"
    confirmed: bool


class FindingDecision(Versioned):
    disposition: Literal["reviewed", "needs_information", "no_change", "manual_review"]
    reason: str = Field(min_length=8, max_length=1000)
    task_owner: Literal["advisor-01", "support-01"] = "advisor-01"
    due_date: date | None = None


class Beneficiary(Input):
    name: str = Field(min_length=2, max_length=150)
    relationship: str = Field(min_length=2, max_length=100)
    percentage: int = Field(ge=1, le=100)


class Instruction(Versioned):
    value: str | list[Beneficiary]
    source_ref: str = Field(min_length=3, max_length=100)
    client_confirmed: bool
    reason: str = Field(min_length=8, max_length=1000)


class DraftEdit(Instruction):
    pass


class DocumentCheck(Versioned):
    document: str
    provided: bool


class SignatureCheck(Versioned):
    signer: str
    signed: bool


class Submit(Versioned):
    idempotency_key: str = Field(min_length=8, max_length=100)
    simulate_failure: bool = False


class AdvanceRequest(Versioned):
    outcome: Literal["Processing", "Completed", "Rejected"]
    reason: str = Field(default="Simulated institution processing.", min_length=8, max_length=500)
