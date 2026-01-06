from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import csv
import io
import os
import uuid
from typing import Dict, List, Any

app = FastAPI(
    title="Owner Intelligence API",
    version="1.0.1",
    description="Minimal working pipeline: ingest CSV -> dedupe -> list canonical owners"
)

# -------------------------
# In-memory storage (for now)
# -------------------------
RAW_RECORDS: List[Dict[str, Any]] = []
OWNERS: Dict[str, Dict[str, Any]] = {}

def normalize_name(name: str) -> str:
    if not name:
        return ""
    return " ".join(name.strip().lower().split())

def make_owner_key(record: Dict[str, Any]) -> str:
    """
    SUPER SIMPLE dedupe key:
    - normalized owner_name
    - if you have mailing_address, include it
    You can upgrade later, but this makes the app "do something" now.
    """
    name = normalize_name(record.get("owner_name", ""))
    addr = normalize_name(record.get("mailing_address", ""))
    if addr:
        return f"{name}|{addr}"
    return name

@app.get("/")
def root():
    return {
        "message": "Owner Intelligence API",
        "status": "running",
        "version": "1.0.1"
    }

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """
    Upload a CSV with at least:
      owner_name
    Optional:
      mailing_address
      county
      source
    """
    if not file.filename.lower().endswith(".csv"):
        return JSONResponse(status_code=400, content={"error": "Please upload a .csv file"})

    content = await file.read()
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Could not decode file as utf-8"})

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return JSONResponse(status_code=400, content={"error": "CSV appears empty or has no headers"})

    count = 0
    for row in reader:
        # Clean keys to lowercase
        cleaned = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }

        # Force required column
        if not cleaned.get("owner_name"):
            continue

        # Store raw record with an id
        cleaned["_record_id"] = str(uuid.uuid4())
        RAW_RECORDS.append(cleaned)
        count += 1

    return {
        "status": "ok",
        "ingested": count,
        "total_raw_records": len(RAW_RECORDS),
        "expected_headers": ["owner_name", "mailing_address", "county", "source"]
    }

@app.post("/dedupe/run")
def run_dedupe():
    """
    Collapses RAW_RECORDS into canonical OWNERS using make_owner_key().
    """
    global OWNERS
    OWNERS = {}

    duplicates_collapsed = 0

    for r in RAW_RECORDS:
        key = make_owner_key(r)
        if not key:
            continue

        if key not in OWNERS:
            owner_id = str(uuid.uuid4())
            OWNERS[key] = {
                "owner_id": owner_id,
                "owner_name": r.get("owner_name", ""),
                "mailing_address": r.get("mailing_address", ""),
                "counties": set([r.get("county", "")]) if r.get("county") else set(),
                "sources": set([r.get("source", "")]) if r.get("source") else set(),
                "records": [r["_record_id"]],
            }
        else:
            duplicates_collapsed += 1
            OWNERS[key]["records"].append(r["_record_id"])
            if r.get("county"):
                OWNERS[key]["counties"].add(r.get("county"))
            if r.get("source"):
                OWNERS[key]["sources"].add(r.get("source"))

    # Convert sets to lists for JSON
    for k in list(OWNERS.keys()):
        OWNERS[k]["counties"] = sorted([c for c in OWNERS[k]["counties"] if c])
        OWNERS[k]["sources"] = sorted([s for s in OWNERS[k]["sources"] if s])

    return {
        "status": "ok",
        "raw_records": len(RAW_RECORDS),
        "canonical_owners": len(OWNERS),
        "duplicates_collapsed": duplicates_collapsed
    }

@app.get("/owners")
def list_owners(limit: int = 50):
    """
    Lists canonical owners after /dedupe/run.
    """
    items = list(OWNERS.values())[: max(1, min(limit, 500))]
    return {
        "count": len(items),
        "owners": items
    }

@app.post("/reset")
def reset_all():
    """
    Clears in-memory records (useful for testing).
    """
    RAW_RECORDS.clear()
    OWNERS.clear()
    return {"status": "ok", "message": "cleared"}
