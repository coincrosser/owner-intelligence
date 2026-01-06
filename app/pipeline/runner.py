from __future__ import annotations

from pathlib import Path

from app.adapters.mock import (
    MockAddressStandardizer,
    MockAddressUpdateProvider,
    MockAppendVendorClient,
)
from app.ai.inbound_handler import IntentClassifier, ResponseGenerator, SchedulingLink
from app.db.database import DB_PATH, get_connection, run_migrations
from app.pipeline.steps import (
    PipelineConfig,
    ai_inbound_handler,
    address_standardize,
    address_update,
    dashboard,
    dedupe_identity,
    export_for_append,
    import_appends,
    ingest,
    hot_lead_router,
    outreach_queue,
    score_owners,
)


def run_pipeline(sample_dir: Path) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    run_migrations()
    ingest([sample_dir / "leases.csv", sample_dir / "permits.csv"])
    dedupe_identity()
    address_update(MockAddressUpdateProvider())
    address_standardize(MockAddressStandardizer())
    score_owners()
    config = PipelineConfig()
    payload = export_for_append(
        MockAppendVendorClient(),
        sample_dir / "append_export.json",
        config.address_confidence_threshold,
    )
    import_appends(MockAppendVendorClient(), payload)
    outreach_queue(config)
    with get_connection() as conn:
        owner_ids = [
            row["id"] for row in conn.execute("SELECT id FROM owners").fetchall()
        ]
    inbound_messages = []
    if owner_ids:
        inbound_messages.append(
            {
                "owner_id": owner_ids[0],
                "channel": "sms",
                "message": "Interested - can you call me?",
            }
        )
    if len(owner_ids) > 1:
        inbound_messages.append(
            {
                "owner_id": owner_ids[1],
                "channel": "sms",
                "message": "Not now, maybe later.",
            }
        )
    if len(owner_ids) > 2:
        inbound_messages.append(
            {
                "owner_id": owner_ids[2],
                "channel": "sms",
                "message": "STOP",
            }
        )
    ai_inbound_handler(
        IntentClassifier(),
        ResponseGenerator(SchedulingLink(url="https://cal.example.com")),
        inbound_messages,
    )
    hot_lead_router()
    results = dashboard(config)
    print("Pipeline Dashboard")
    print(f"Source records: {results.source_records}")
    print(f"Owners: {results.owner_count}")
    print(f"Addresses: {results.addresses}")
    print(f"Contacts: {results.contacts}")
    print(f"Outreach queued: {results.outreach_queued}")
    print(f"Deliverable addresses: {results.deliverable_addresses}")
    print(f"Mobile confirmed: {results.mobile_confirmed}")
    print(f"Daily hot leads: {results.daily_hot_leads}")
