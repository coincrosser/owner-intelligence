# Owner Intelligence + Address Truth + Outreach Orchestrator

Python 3.11+ demo pipeline for oil & gas mineral acquisition workflows. The project focuses on owner identity resolution, address validation, compliance, and outreach orchestration with mock adapters.

## Features
- Canonical owner schema with source records, address history, contact points, compliance ledger, and hot lead routing.
- Modular pipeline: ingest → dedupe → address update → standardize → score → export for append → import appends → outreach queue → inbound AI handler → hot lead routing.
- Adapter interfaces for USPS/NCOA, CASS, append vendors, ringless voicemail, SMS, and email.
- SQLite persistence with migrations.
- CLI dashboard for stage counts and hot leads.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run demo
```bash
python app/run_demo.py
```

## Tests
```bash
pytest app/tests
```

## Project layout
```
app/
  main.py
  run_demo.py
  pipeline/
  models/
  adapters/
  ai/
  compliance/
  scoring/
  tests/
  sample_data/
```
