from __future__ import annotations

import json
from datetime import datetime
from typing import Iterable

from app.adapters.base import (
    AddressStandardizer,
    AddressUpdateProvider,
    AppendVendorClient,
    EmailClient,
    RinglessVoicemailClient,
    SMSClient,
)
from app.models.schemas import Address, ContactPoint


class MockAddressUpdateProvider(AddressUpdateProvider):
    def update(self, addresses: Iterable[Address]) -> list[Address]:
        updated = []
        for address in addresses:
            updated.append(
                address.model_copy(
                    update={
                        "confidence": min(address.confidence + 0.1, 0.95),
                        "updated_at": datetime.utcnow(),
                    }
                )
            )
        return updated


class MockAddressStandardizer(AddressStandardizer):
    def standardize(self, addresses: Iterable[Address]) -> list[Address]:
        standardized = []
        for address in addresses:
            standardized.append(
                address.model_copy(
                    update={
                        "line1": address.line1.upper(),
                        "city": address.city.upper(),
                        "state": address.state.upper(),
                        "updated_at": datetime.utcnow(),
                    }
                )
            )
        return standardized


class MockAppendVendorClient(AppendVendorClient):
    def export_payload(self, addresses: Iterable[Address]) -> str:
        rows = [address.model_dump() for address in addresses]
        return json.dumps(rows)

    def import_appends(self, payload: str) -> list[ContactPoint]:
        data = json.loads(payload)
        contacts = []
        for row in data:
            owner_id = row["owner_id"]
            contacts.append(
                ContactPoint(
                    id=f"phone-{owner_id}",
                    owner_id=owner_id,
                    value=f"555{owner_id[-4:]}",
                    contact_type="phone",
                    phone_type="mobile",
                    confidence=0.85,
                )
            )
            contacts.append(
                ContactPoint(
                    id=f"email-{owner_id}",
                    owner_id=owner_id,
                    value=f"{owner_id[:6]}@example.com",
                    contact_type="email",
                    confidence=0.8,
                )
            )
        return contacts


class MockRinglessVoicemailClient(RinglessVoicemailClient):
    def send(self, owner_id: str, phone: str, message: str) -> str:
        return f"rv-{owner_id}-{int(datetime.utcnow().timestamp())}"


class MockSMSClient(SMSClient):
    def send(self, owner_id: str, phone: str, message: str) -> str:
        return f"sms-{owner_id}-{int(datetime.utcnow().timestamp())}"


class MockEmailClient(EmailClient):
    def send(self, owner_id: str, email: str, message: str) -> str:
        return f"email-{owner_id}-{int(datetime.utcnow().timestamp())}"
