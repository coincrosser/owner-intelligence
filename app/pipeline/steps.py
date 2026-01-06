from __future__ import annotations

import csv
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from app.adapters.base import (
    AddressStandardizer,
    AddressUpdateProvider,
    AppendVendorClient,
)
from app.ai.inbound_handler import IntentClassifier, ResponseGenerator
from app.compliance.rules import is_suppressed, should_allow_outreach
from app.db.database import get_connection
from app.models.schemas import Address, IntentLabel
from app.scoring.address import address_score
from app.scoring.dedupe import dedupe_score, normalize_name
from app.scoring.hot_lead import is_hot_lead


@dataclass
class PipelineConfig:
    max_attempts: int = 2
    window_days: int = 7
    sms_confidence_threshold: float = 0.7
    address_confidence_threshold: float = 0.6


@dataclass
class PipelineResult:
    source_records: int
    owner_count: int
    addresses: int
    contacts: int
    outreach_queued: int
    deliverable_addresses: int
    mobile_confirmed: int
    daily_hot_leads: int


def ingest(csv_paths: list[Path]) -> None:
    with get_connection() as conn:
        for path in csv_paths:
            with path.open() as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    record_id = f"src-{uuid.uuid4()}"
                    conn.execute(
                        """
                        INSERT INTO source_records (
                            id, owner_name, source_type, source_id, address_line1,
                            city, state, postal_code, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            record_id,
                            row["owner_name"],
                            row["source_type"],
                            row["source_id"],
                            row["address_line1"],
                            row["city"],
                            row["state"],
                            row["postal_code"],
                            datetime.utcnow().isoformat(),
                        ),
                    )
        conn.commit()


def dedupe_identity() -> None:
    with get_connection() as conn:
        records = conn.execute("SELECT * FROM source_records").fetchall()
        owners = []
        owner_map: dict[str, str] = {}
        for record in records:
            name = record["owner_name"]
            normalized = normalize_name(name)
            existing_owner_id = None
            for key, owner_id in owner_map.items():
                if dedupe_score(normalized, key) >= 0.9:
                    existing_owner_id = owner_id
                    break
            if existing_owner_id is None:
                owner_id = f"own-{uuid.uuid4()}"
                owner_map[normalized] = owner_id
                owners.append((owner_id, name, datetime.utcnow().isoformat(), 0.0))
            else:
                owner_id = existing_owner_id
            address_id = f"addr-{uuid.uuid4()}"
            conn.execute(
                """
                INSERT INTO addresses (
                    id, owner_id, line1, city, state, postal_code,
                    confidence, is_deliverable, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    address_id,
                    owner_id,
                    record["address_line1"],
                    record["city"],
                    record["state"],
                    record["postal_code"],
                    0.5,
                    1,
                    datetime.utcnow().isoformat(),
                ),
            )
        conn.executemany(
            "INSERT INTO owners (id, canonical_name, created_at, score) VALUES (?, ?, ?, ?)",
            owners,
        )
        conn.commit()


def address_update(provider: AddressUpdateProvider) -> None:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM addresses").fetchall()
        addresses = [
            Address(
                id=row["id"],
                owner_id=row["owner_id"],
                line1=row["line1"],
                city=row["city"],
                state=row["state"],
                postal_code=row["postal_code"],
                confidence=row["confidence"],
                is_deliverable=bool(row["is_deliverable"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]
        updated = provider.update(addresses)
        for address in updated:
            conn.execute(
                """
                UPDATE addresses
                SET line1 = ?, city = ?, state = ?, postal_code = ?, confidence = ?,
                    is_deliverable = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    address.line1,
                    address.city,
                    address.state,
                    address.postal_code,
                    address.confidence,
                    int(address.is_deliverable),
                    address.updated_at.isoformat(),
                    address.id,
                ),
            )
        conn.commit()


def address_standardize(standardizer: AddressStandardizer) -> None:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM addresses").fetchall()
        addresses = [
            Address(
                id=row["id"],
                owner_id=row["owner_id"],
                line1=row["line1"],
                city=row["city"],
                state=row["state"],
                postal_code=row["postal_code"],
                confidence=row["confidence"],
                is_deliverable=bool(row["is_deliverable"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]
        standardized = standardizer.standardize(addresses)
        for address in standardized:
            conn.execute(
                """
                UPDATE addresses
                SET line1 = ?, city = ?, state = ?, postal_code = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    address.line1,
                    address.city,
                    address.state,
                    address.postal_code,
                    address.updated_at.isoformat(),
                    address.id,
                ),
            )
        conn.commit()


def score_owners() -> None:
    with get_connection() as conn:
        owners = conn.execute("SELECT id FROM owners").fetchall()
        for owner in owners:
            address_rows = conn.execute(
                "SELECT * FROM addresses WHERE owner_id = ?", (owner["id"],)
            ).fetchall()
            if not address_rows:
                continue
            scores = []
            for row in address_rows:
                address = Address(
                    id=row["id"],
                    owner_id=row["owner_id"],
                    line1=row["line1"],
                    city=row["city"],
                    state=row["state"],
                    postal_code=row["postal_code"],
                    confidence=row["confidence"],
                    is_deliverable=bool(row["is_deliverable"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                scores.append(address_score(address))
            conn.execute(
                "UPDATE owners SET score = ? WHERE id = ?",
                (max(scores), owner["id"]),
            )
        conn.commit()


def export_for_append(
    client: AppendVendorClient, output_path: Path, confidence_threshold: float
) -> str:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM addresses WHERE confidence >= ? AND is_deliverable = 1",
            (confidence_threshold,),
        ).fetchall()
        addresses = [
            Address(
                id=row["id"],
                owner_id=row["owner_id"],
                line1=row["line1"],
                city=row["city"],
                state=row["state"],
                postal_code=row["postal_code"],
                confidence=row["confidence"],
                is_deliverable=bool(row["is_deliverable"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
            for row in rows
        ]
        payload = client.export_payload(addresses)
    output_path.write_text(payload)
    return payload


def import_appends(client: AppendVendorClient, payload: str) -> None:
    contacts = client.import_appends(payload)
    with get_connection() as conn:
        for contact in contacts:
            conn.execute(
                """
                INSERT OR REPLACE INTO contacts (
                    id, owner_id, value, contact_type, phone_type, confidence, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contact.id,
                    contact.owner_id,
                    contact.value,
                    contact.contact_type,
                    contact.phone_type,
                    contact.confidence,
                    contact.updated_at.isoformat(),
                ),
            )
        conn.commit()


def outreach_queue(config: PipelineConfig) -> None:
    with get_connection() as conn:
        owners = conn.execute("SELECT id FROM owners").fetchall()
        suppression = {
            row["owner_id"]: row["reason"]
            for row in conn.execute("SELECT owner_id, reason FROM suppression")
        }
        for owner in owners:
            owner_id = owner["id"]
            if is_suppressed(suppression, owner_id):
                continue
            attempts = conn.execute(
                "SELECT created_at FROM contact_attempts WHERE owner_id = ?",
                (owner_id,),
            ).fetchall()
            attempt_times = [
                datetime.fromisoformat(row["created_at"]) for row in attempts
            ]
            if not should_allow_outreach(
                attempt_times, config.max_attempts, config.window_days
            ):
                continue
            contact_rows = conn.execute(
                "SELECT * FROM contacts WHERE owner_id = ?", (owner_id,)
            ).fetchall()
            for contact in contact_rows:
                if contact["contact_type"] == "phone":
                    if (
                        contact["phone_type"] == "mobile"
                        and contact["confidence"] >= config.sms_confidence_threshold
                    ):
                        queue_outreach(
                            conn,
                            owner_id,
                            "sms",
                            {"phone": contact["value"]},
                        )
                    queue_outreach(
                        conn,
                        owner_id,
                        "ringless_voicemail",
                        {"phone": contact["value"]},
                    )
                if contact["contact_type"] == "email":
                    queue_outreach(
                        conn,
                        owner_id,
                        "email",
                        {"email": contact["value"]},
                    )
        conn.commit()


def queue_outreach(conn, owner_id: str, channel: str, payload: dict[str, str]) -> None:
    queue_id = f"queue-{uuid.uuid4()}"
    conn.execute(
        """
        INSERT INTO outreach_queue (id, owner_id, channel, payload, scheduled_for, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            queue_id,
            owner_id,
            channel,
            json.dumps(payload),
            (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            "queued",
        ),
    )


def ai_inbound_handler(
    classifier: IntentClassifier,
    responder: ResponseGenerator,
    inbound_messages: list[dict[str, str]],
) -> None:
    with get_connection() as conn:
        for inbound in inbound_messages:
            owner_id = inbound["owner_id"]
            message = inbound["message"]
            intent = classifier.classify(message)
            conn.execute(
                "INSERT INTO inbound_messages (id, owner_id, channel, message, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    f"inbound-{uuid.uuid4()}",
                    owner_id,
                    inbound["channel"],
                    message,
                    datetime.utcnow().isoformat(),
                ),
            )
            if intent in {IntentLabel.stop, IntentLabel.never}:
                conn.execute(
                    "INSERT OR REPLACE INTO suppression (owner_id, reason, created_at)"
                    " VALUES (?, ?, ?)",
                    (owner_id, intent.value, datetime.utcnow().isoformat()),
                )
                conn.execute(
                    "DELETE FROM outreach_queue WHERE owner_id = ?", (owner_id,)
                )
            response = responder.draft(intent)
            conn.execute(
                "INSERT INTO contact_attempts (id, owner_id, channel, status, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    f"attempt-{uuid.uuid4()}",
                    owner_id,
                    inbound["channel"],
                    f"auto_reply:{response}",
                    datetime.utcnow().isoformat(),
                ),
            )
        conn.commit()


def hot_lead_router() -> None:
    with get_connection() as conn:
        inbound = conn.execute(
            "SELECT owner_id, message FROM inbound_messages"
        ).fetchall()
        counts = defaultdict(int)
        intents: dict[str, IntentLabel] = {}
        classifier = IntentClassifier()
        for message in inbound:
            owner_id = message["owner_id"]
            counts[owner_id] += 1
            intents[owner_id] = classifier.classify(message["message"])
        for owner_id, count in counts.items():
            intent = intents[owner_id]
            if is_hot_lead(intent, count):
                conn.execute(
                    "INSERT OR REPLACE INTO hot_leads (owner_id, reason, created_at)"
                    " VALUES (?, ?, ?)",
                    (
                        owner_id,
                        f"intent:{intent.value}|messages:{count}",
                        datetime.utcnow().isoformat(),
                    ),
                )
        conn.commit()


def dashboard(config: PipelineConfig) -> PipelineResult:
    with get_connection() as conn:
        source_records = conn.execute(
            "SELECT COUNT(*) as count FROM source_records"
        ).fetchone()["count"]
        owners = conn.execute("SELECT COUNT(*) as count FROM owners").fetchone()["count"]
        addresses = conn.execute(
            "SELECT COUNT(*) as count FROM addresses"
        ).fetchone()["count"]
        contacts = conn.execute(
            "SELECT COUNT(*) as count FROM contacts"
        ).fetchone()["count"]
        outreach_queued = conn.execute(
            "SELECT COUNT(*) as count FROM outreach_queue"
        ).fetchone()["count"]
        deliverable = conn.execute(
            "SELECT COUNT(*) as count FROM addresses WHERE confidence >= ? AND is_deliverable = 1",
            (config.address_confidence_threshold,),
        ).fetchone()["count"]
        mobile = conn.execute(
            "SELECT COUNT(*) as count FROM contacts WHERE contact_type = 'phone'"
            " AND phone_type = 'mobile' AND confidence >= ?",
            (config.sms_confidence_threshold,),
        ).fetchone()["count"]
        hot_leads = conn.execute(
            "SELECT COUNT(*) as count FROM hot_leads WHERE created_at >= ?",
            ((datetime.utcnow() - timedelta(days=1)).isoformat(),),
        ).fetchone()["count"]
        return PipelineResult(
            source_records=source_records,
            owner_count=owners,
            addresses=addresses,
            contacts=contacts,
            outreach_queued=outreach_queued,
            deliverable_addresses=deliverable,
            mobile_confirmed=mobile,
            daily_hot_leads=hot_leads,
        )
