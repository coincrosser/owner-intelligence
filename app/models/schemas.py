from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConfidenceLevel(float, Enum):
    low = 0.3
    medium = 0.6
    high = 0.9


class SourceType(str, Enum):
    lease = "lease"
    permit = "permit"


class ContactChannel(str, Enum):
    sms = "sms"
    email = "email"
    ringless_voicemail = "ringless_voicemail"
    phone_call = "phone_call"


class IntentLabel(str, Enum):
    interested = "interested"
    curious = "curious"
    not_now = "not_now"
    never = "never"
    stop = "stop"


class Owner(BaseModel):
    id: str
    canonical_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    score: float = 0.0


class SourceRecord(BaseModel):
    id: str
    owner_name: str
    source_type: SourceType
    source_id: str
    address_line1: str
    city: str
    state: str
    postal_code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Address(BaseModel):
    id: str
    owner_id: str
    line1: str
    city: str
    state: str
    postal_code: str
    confidence: float
    is_deliverable: bool = True
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContactPoint(BaseModel):
    id: str
    owner_id: str
    value: str
    contact_type: str
    phone_type: Optional[str] = None
    confidence: float
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ContactAttempt(BaseModel):
    id: str
    owner_id: str
    channel: ContactChannel
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SuppressionEntry(BaseModel):
    owner_id: str
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HotLead(BaseModel):
    owner_id: str
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
